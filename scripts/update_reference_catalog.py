"""Script to merge curated winery annotations into reference_wines.json and re-seed SQLite."""

import csv
import json
import sqlite3
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "annotations" / "draft.csv"
REF_JSON_PATH = BASE_DIR / "app" / "data" / "reference_wines.json"
DB_PATH = BASE_DIR / "app" / "data" / "wines.sqlite"


def slugify(text: str) -> str:
    cleaned = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    ).lower()
    return "".join(c if c.isalnum() else "_" for c in cleaned).strip("_")


def main():
    with open(REF_JSON_PATH, "r", encoding="utf-8") as f:
        ref_data = json.load(f)

    existing_wines = ref_data.get("wines", [])
    existing_ids = {w["id"] for w in existing_wines}

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    added = 0
    for r in rows:
        prod = r.get("producer", "").strip()
        wine = r.get("wine_name", "").strip()
        app = r.get("appellation", "").strip()
        vint_str = r.get("vintage", "").strip()
        vint = int(vint_str) if vint_str.isdigit() else None

        if not prod and not wine:
            continue

        raw_slug = f"{prod}_{wine}_{app}_{vint_str}".strip("_")
        wine_id = f"ref_{slugify(raw_slug)}"[:45]

        if wine_id in existing_ids:
            continue

        grapes = [g.strip() for g in r.get("grape_varieties", "").split(";") if g.strip()]
        barcode = r.get("barcode_digits", "").strip() or None
        abv_str = r.get("abv", "").strip()
        abv = float(abv_str) if abv_str and abv_str.replace(".", "", 1).isdigit() else None

        new_entry = {
            "id": wine_id,
            "barcode": barcode,
            "canonical_producer": prod or wine,
            "canonical_wine_name": wine or prod,
            "cuvee": None,
            "vintage": vint,
            "country": r.get("country", "").strip() or "France",
            "region": r.get("region", "").strip() or None,
            "appellation": app or None,
            "wine_type": r.get("wine_type", "").strip() or "red",
            "grapes": grapes,
            "abv": abv,
            "source": "winery_annotations",
        }

        existing_wines.append(new_entry)
        existing_ids.add(wine_id)
        added += 1

    ref_data["wines"] = existing_wines
    with open(REF_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(ref_data, f, indent=2, ensure_ascii=False)

    print(f"Added {added} new wines to {REF_JSON_PATH}. Total wines in catalog: {len(existing_wines)}")

    # Re-seed SQLite
    if DB_PATH.exists():
        DB_PATH.unlink()
    from app.data.db import SqliteWineDatabase
    db = SqliteWineDatabase(DB_PATH)
    print(f"Re-initialized SQLite index at {DB_PATH}. Total wines in DB: {len(db.get_all_wines(1000))}")


if __name__ == "__main__":
    main()
