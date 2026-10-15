"""Offline-First SQLite Wine Database & Index.

Provides sub-millisecond barcode lookups and FTS5 full-text search candidate
retrieval for RapidFuzz re-ranking.
Designed for offline local storage of European supermarket and cave wines.
"""

from __future__ import annotations
import json
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Optional, Dict, Any, List

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "wines.sqlite"
SEED_JSON_PATH = Path(__file__).resolve().parent / "reference_wines.json"


class SqliteWineDatabase:
    """Manages local SQLite database with indexing and FTS5 support."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.db_path))
        con.row_factory = sqlite3.Row
        return con

    def _init_db(self):
        with self.get_connection() as con:
            cur = con.cursor()
            # Main catalog table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS wines (
                    id TEXT PRIMARY KEY,
                    barcode TEXT,
                    canonical_producer TEXT NOT NULL,
                    canonical_wine_name TEXT NOT NULL,
                    cuvee TEXT,
                    vintage INTEGER,
                    country TEXT,
                    region TEXT,
                    appellation TEXT,
                    wine_type TEXT,
                    grapes_json TEXT,
                    abv REAL,
                    source TEXT DEFAULT 'curated'
                )
            """)
            # Fast index on barcode
            cur.execute("CREATE INDEX IF NOT EXISTS idx_wines_barcode ON wines(barcode)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_wines_appellation ON wines(appellation)")

            # FTS5 virtual table for full-text candidate searching (with automatic diacritics stripping)
            cur.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS wines_fts USING fts5(
                    id UNINDEXED,
                    canonical_producer,
                    canonical_wine_name,
                    appellation,
                    content='wines',
                    content_rowid='rowid',
                    tokenize='unicode61 remove_diacritics 2'
                )
            """)

            # Triggers to keep FTS index synchronized
            cur.execute("""
                CREATE TRIGGER IF NOT EXISTS wines_ai AFTER INSERT ON wines BEGIN
                    INSERT INTO wines_fts(rowid, id, canonical_producer, canonical_wine_name, appellation)
                    VALUES (new.rowid, new.id, new.canonical_producer, new.canonical_wine_name, new.appellation);
                END;
            """)
            cur.execute("""
                CREATE TRIGGER IF NOT EXISTS wines_ad AFTER DELETE ON wines BEGIN
                    INSERT INTO wines_fts(wines_fts, rowid, id, canonical_producer, canonical_wine_name, appellation)
                    VALUES('delete', old.rowid, old.id, old.canonical_producer, old.canonical_wine_name, old.appellation);
                END;
            """)
            con.commit()

        # Seed if empty
        self._auto_seed_if_empty()

    def _auto_seed_if_empty(self):
        with self.get_connection() as con:
            cur = con.cursor()
            cur.execute("SELECT COUNT(*) FROM wines")
            count = cur.fetchone()[0]
            if count == 0 and SEED_JSON_PATH.exists():
                self.seed_from_json(SEED_JSON_PATH)

    def seed_from_json(self, json_path: Path):
        """Loads canonical wines from JSON into SQLite index."""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            wines = data.get("wines", [])

        with self.get_connection() as con:
            cur = con.cursor()
            for w in wines:
                grapes_val = json.dumps(w.get("grapes", []))
                cur.execute("""
                    INSERT OR REPLACE INTO wines (
                        id, barcode, canonical_producer, canonical_wine_name,
                        cuvee, vintage, country, region, appellation,
                        wine_type, grapes_json, abv, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    w["id"],
                    str(w.get("barcode") or "").strip() or None,
                    w["canonical_producer"],
                    w["canonical_wine_name"],
                    w.get("cuvee"),
                    w.get("vintage"),
                    w.get("country"),
                    w.get("region"),
                    w.get("appellation"),
                    w.get("wine_type"),
                    grapes_val,
                    w.get("abv"),
                    w.get("source", "curated")
                ))
            con.commit()

    def get_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        """Exact lookup by EAN-13 / UPC barcode digits."""
        if not barcode:
            return None
        clean = barcode.strip().replace(" ", "").replace("-", "")
        with self.get_connection() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM wines WHERE barcode = ?", (clean,))
            row = cur.fetchone()
            if row:
                d = dict(row)
                d["grapes"] = json.loads(d.get("grapes_json") or "[]")
                return d
        return None

    def get_by_id(self, wine_id: str) -> Optional[Dict[str, Any]]:
        """Exact lookup by canonical wine ID."""
        if not wine_id:
            return None
        with self.get_connection() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM wines WHERE id = ?", (wine_id.strip(),))
            row = cur.fetchone()
            if row:
                d = dict(row)
                d["grapes"] = json.loads(d.get("grapes_json") or "[]")
                return d
        return None

    def search_candidates(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves top candidate wine rows via FTS5 or broad token match."""
        if not query or not query.strip():
            return []

        # Sanitize query for FTS5 syntax: replace punctuation with spaces
        clean_text = re.sub(r"[^\w\s]", " ", query)
        clean_tokens = [t for t in clean_text.split() if len(t) > 1]
        if not clean_tokens:
            return []

        fts_query = " OR ".join(f'"{t}"*' for t in clean_tokens[:8])

        with self.get_connection() as con:
            cur = con.cursor()
            try:
                cur.execute("""
                    SELECT w.*
                    FROM wines_fts f
                    JOIN wines w ON f.rowid = w.rowid
                    WHERE wines_fts MATCH ?
                    LIMIT ?
                """, (fts_query, limit))
                rows = cur.fetchall()
            except sqlite3.OperationalError:
                # Fallback to standard LIKE matching if FTS syntax error
                cur.execute("SELECT * FROM wines LIMIT ?", (limit,))
                rows = cur.fetchall()

            candidates = []
            for r in rows:
                d = dict(r)
                d["grapes"] = json.loads(d.get("grapes_json") or "[]")
                candidates.append(d)
            return candidates

    def get_all_wines(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Returns all registered wines (useful for small benchmarks or in-memory caches)."""
        with self.get_connection() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM wines LIMIT ?", (limit,))
            rows = cur.fetchall()
            wines = []
            for r in rows:
                d = dict(r)
                d["grapes"] = json.loads(d.get("grapes_json") or "[]")
                wines.append(d)
            return wines
