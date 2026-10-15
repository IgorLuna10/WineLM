"""Stage 2: Identification Pipeline (Offline-First SQLite).

Resolves extracted label facts against local SQLite index.
Execution order:
1. Exact Barcode (EAN-13) lookup via indexed SQLite query (<1ms).
2. Candidate retrieval via SQLite FTS5 + RapidFuzz token-set re-ranking.
"""

from __future__ import annotations
import re
import time
import unicodedata
from typing import Optional, Dict, Any, List
from rapidfuzz import fuzz
from app.schemas.extraction import ExtractionOutput
from app.schemas.response import MatchInfo
from app.data.db import SqliteWineDatabase


def normalize_text(text: str) -> str:
    """Strips accents and punctuation for robust cross-lingual wine matching."""
    if not text:
        return ""
    no_punct = re.sub(r"[^\w\s]", " ", text)
    return "".join(
        c for c in unicodedata.normalize("NFD", no_punct)
        if unicodedata.category(c) != "Mn"
    ).lower()


class IdentificationStage:
    """Stage 2 runner: resolves extracted bottle against offline SQLite database."""

    def __init__(self, db: Optional[SqliteWineDatabase] = None):
        self.db = db or SqliteWineDatabase()

    def run(self, extraction: ExtractionOutput) -> tuple[Optional[MatchInfo], Optional[Dict[str, Any]], float]:
        start = time.perf_counter()

        # Step 1: Exact Barcode (EAN-13) Lookup in SQLite index
        if extraction.barcode.is_reliable(threshold=0.8):
            bc = extraction.barcode.value
            matched = self.db.get_by_barcode(bc)
            if matched:
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                match_info = MatchInfo(
                    matched_id=matched["id"],
                    canonical_producer=matched["canonical_producer"],
                    canonical_wine_name=matched["canonical_wine_name"],
                    canonical_vintage=matched.get("vintage"),
                    match_source="sqlite_ean_barcode_index",
                    match_confidence=0.98,
                )
                return match_info, matched, elapsed_ms

        # Step 2: Full-Text Candidate Search + RapidFuzz Re-ranking
        query_parts = []
        if extraction.producer.value:
            query_parts.append(extraction.producer.value)
        if extraction.wine_name.value:
            query_parts.append(extraction.wine_name.value)
        if extraction.appellation.value:
            query_parts.append(extraction.appellation.value)

        query_str = " ".join(query_parts).strip()
        query_vintage = extraction.vintage.value

        best_score = 0.0
        best_match: Optional[Dict[str, Any]] = None

        if query_str:
            # First try FTS5 candidates
            candidates = self.db.search_candidates(query_str, limit=50)
            if not candidates:
                # Fallback to catalog
                candidates = self.db.get_all_wines(limit=100)

            for candidate in candidates:
                cand_str = f"{candidate['canonical_producer']} {candidate['canonical_wine_name']} {candidate.get('appellation', '')}"
                string_sim = fuzz.token_set_ratio(normalize_text(query_str), normalize_text(cand_str)) / 100.0

                # Vintage compatibility penalty or bonus
                cand_vintage = candidate.get("vintage")
                if query_vintage and cand_vintage:
                    if query_vintage == cand_vintage:
                        final_score = string_sim
                    else:
                        final_score = string_sim * 0.85  # vintage mismatch penalty
                else:
                    final_score = string_sim * 0.95

                if final_score > best_score:
                    best_score = final_score
                    best_match = candidate

        elapsed_ms = (time.perf_counter() - start) * 1000.0

        # Exact/High confidence threshold for "identified_wine"
        if best_match and best_score >= 0.82:
            match_info = MatchInfo(
                matched_id=best_match["id"],
                canonical_producer=best_match["canonical_producer"],
                canonical_wine_name=best_match["canonical_wine_name"],
                canonical_vintage=best_match.get("vintage"),
                match_source="sqlite_fts_fuzzy_match",
                match_confidence=round(best_score, 3),
            )
            return match_info, best_match, elapsed_ms

        return None, None, elapsed_ms
