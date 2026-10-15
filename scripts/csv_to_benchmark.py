"""Convert reviewed rows from annotations/draft.csv to eval/data/benchmark_cases.json.

Validates:
- Required CSV columns
- Allowed values for split, difficulty_tags, expected_tier, wine_type, vintage, abv
- Tier consistency (identified_wine requires producer; unidentified has no producer)
- Existence of image files on disk

Converts:
- Only rows with needs_review=FALSE into BenchmarkCase objects
- Preserves the existing synthetic cases tagged 'synthetic'
- Writes updated benchmark suite to eval/data/benchmark_cases.json
"""

from __future__ import annotations
import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

# Ensure project root is in path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from eval.dataset import BenchmarkCase, GroundTruthExtraction, DifficultyTag

REQUIRED_COLUMNS = [
    "case_id",
    "image_paths",
    "split",
    "producer",
    "wine_name",
    "vintage",
    "grape_varieties",
    "appellation",
    "region",
    "country",
    "wine_type",
    "abv",
    "barcode_digits",
    "expected_tier",
    "difficulty_tags",
    "needs_review",
]

ALLOWED_SPLITS = {"dev", "test", "synthetic"}
ALLOWED_TIERS = {"identified_wine", "identified_style", "unidentified"}
ALLOWED_WINE_TYPES = {"red", "white", "rose", "rosé", "sparkling", "sweet", "fortified"}
ALLOWED_TAGS = {t.value for t in DifficultyTag}


def parse_bool(val: str) -> bool:
    clean = val.strip().lower()
    return clean in {"true", "1", "yes", "t"}


def validate_row(
    row: dict[str, str],
    row_idx: int,
    base_dir: Path,
) -> tuple[bool, list[str]]:
    """Validate a single CSV row. Returns (is_valid, error_messages)."""
    errors: list[str] = []
    case_id = row.get("case_id", f"row_{row_idx}")

    # Check image paths
    raw_paths = [p.strip() for p in row.get("image_paths", "").split(";") if p.strip()]
    if not raw_paths:
        errors.append(f"Row {row_idx} ({case_id}): 'image_paths' is empty.")
    else:
        for p in raw_paths:
            full_p = base_dir / p
            if not full_p.exists():
                errors.append(f"Row {row_idx} ({case_id}): Image path does not exist: {p}")

    # Check split
    split = row.get("split", "").strip().lower()
    if split not in ALLOWED_SPLITS:
        errors.append(f"Row {row_idx} ({case_id}): Invalid split '{split}'. Allowed: {ALLOWED_SPLITS}")

    # Check difficulty tags
    tags = [t.strip().lower() for t in row.get("difficulty_tags", "").split(";") if t.strip()]
    for t in tags:
        if t not in ALLOWED_TAGS:
            errors.append(f"Row {row_idx} ({case_id}): Invalid difficulty tag '{t}'. Allowed: {ALLOWED_TAGS}")

    # Check needs_review
    needs_review_raw = row.get("needs_review", "").strip()
    if not needs_review_raw:
        errors.append(f"Row {row_idx} ({case_id}): 'needs_review' must be specified.")
    
    needs_review = parse_bool(needs_review_raw)

    # If needs_review is FALSE, it is claimed to be ground truth: validate consistency
    if not needs_review:
        tier = row.get("expected_tier", "").strip()
        if not tier:
            # Auto-infer tier from presence of producer / appellation
            prod = row.get("producer", "").strip()
            app = row.get("appellation", "").strip()
            wname = row.get("wine_name", "").strip()
            grp = row.get("grape_varieties", "").strip()
            if prod and (wname or app or grp):
                tier = "identified_wine"
            elif app or grp or row.get("wine_type", "").strip():
                tier = "identified_style"
            else:
                tier = "unidentified"
            row["expected_tier"] = tier

        if tier not in ALLOWED_TIERS:
            errors.append(f"Row {row_idx} ({case_id}): Invalid or missing expected_tier '{tier}' for reviewed row.")


        # Vintage
        vintage_str = row.get("vintage", "").strip()
        if vintage_str:
            try:
                v = int(vintage_str)
                if v < 1900 or v > 2100:
                    errors.append(f"Row {row_idx} ({case_id}): Vintage out of plausible range: {v}")
            except ValueError:
                errors.append(f"Row {row_idx} ({case_id}): Vintage must be an integer, got '{vintage_str}'")

        # ABV
        abv_str = row.get("abv", "").strip()
        if abv_str:
            try:
                a = float(abv_str)
                if a < 0.0 or a > 100.0:
                    errors.append(f"Row {row_idx} ({case_id}): ABV out of range: {a}")
            except ValueError:
                errors.append(f"Row {row_idx} ({case_id}): ABV must be a float, got '{abv_str}'")

        # Wine type
        wt = row.get("wine_type", "").strip().lower()
        if wt and wt not in ALLOWED_WINE_TYPES:
            errors.append(f"Row {row_idx} ({case_id}): Invalid wine_type '{wt}'. Allowed: {ALLOWED_WINE_TYPES}")

        # Tier consistency
        producer = row.get("producer", "").strip()
        wine_name = row.get("wine_name", "").strip()
        appellation = row.get("appellation", "").strip()
        grapes = [g.strip() for g in row.get("grape_varieties", "").split(";") if g.strip()]

        if tier == "identified_wine":
            if not producer:
                errors.append(f"Row {row_idx} ({case_id}): 'identified_wine' requires non-empty producer.")
            if not (wine_name or appellation or grapes):
                errors.append(f"Row {row_idx} ({case_id}): 'identified_wine' requires wine_name, appellation, or grape_varieties.")
        elif tier == "identified_style":
            if not (appellation or grapes or wt):
                errors.append(f"Row {row_idx} ({case_id}): 'identified_style' requires appellation, grape_varieties, or wine_type.")
        elif tier == "unidentified":
            if producer or wine_name:
                errors.append(f"Row {row_idx} ({case_id}): 'unidentified' tier should not specify producer or wine_name.")

    return len(errors) == 0, errors


def convert_row_to_case(row: dict[str, str], base_dir: Path) -> BenchmarkCase:
    """Convert a reviewed CSV row into a BenchmarkCase."""
    case_id = row["case_id"].strip()
    image_paths = [p.strip() for p in row["image_paths"].split(";") if p.strip()]
    split = row["split"].strip().lower()
    raw_tags = [t.strip().lower() for t in row["difficulty_tags"].split(";") if t.strip()]
    difficulty_tags = [DifficultyTag(t) for t in raw_tags]

    vintage_str = row.get("vintage", "").strip()
    vintage = int(vintage_str) if vintage_str else None

    abv_str = row.get("abv", "").strip()
    abv = float(abv_str) if abv_str else None

    wt_str = row.get("wine_type", "").strip().lower()
    wine_type = "rose" if wt_str in {"rose", "rosé"} else (wt_str if wt_str else None)

    grape_varieties = [g.strip() for g in row.get("grape_varieties", "").split(";") if g.strip()]
    barcode = row.get("barcode_digits", "").strip() or None

    gt = GroundTruthExtraction(
        producer=row.get("producer", "").strip() or None,
        wine_name=row.get("wine_name", "").strip() or None,
        appellation=row.get("appellation", "").strip() or None,
        region=row.get("region", "").strip() or None,
        country=row.get("country", "").strip() or None,
        vintage=vintage,
        abv=abv,
        wine_type=wine_type,
        grape_varieties=grape_varieties,
        barcode=barcode,
    )

    return BenchmarkCase(
        case_id=case_id,
        image_paths=image_paths,
        difficulty_tags=difficulty_tags,
        split=split,
        ground_truth_extraction=gt,
        expected_tier=row.get("expected_tier", "").strip(),
        expected_canonical_id=None,
        verified_claims=[],
    )


def process_csv_to_benchmark(
    csv_path: Path,
    benchmark_path: Path,
    output_path: Path,
    validate_only: bool = False,
) -> int:
    csv_path = Path(csv_path)
    benchmark_path = Path(benchmark_path)
    output_path = Path(output_path)
    base_dir = ROOT_DIR

    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}", file=sys.stderr)
        return 1

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        missing_cols = [c for c in REQUIRED_COLUMNS if c not in header]
        if missing_cols:
            print(f"Error: CSV missing required columns: {missing_cols}", file=sys.stderr)
            return 1
        rows = list(reader)

    print(f"Loaded {len(rows)} rows from {csv_path}")

    all_errors: list[str] = []
    reviewed_rows: list[dict[str, str]] = []
    pending_review_count = 0

    for idx, row in enumerate(rows, start=2):
        is_valid, errors = validate_row(row, idx, base_dir)
        if not is_valid:
            all_errors.extend(errors)

        if parse_bool(row.get("needs_review", "TRUE")):
            pending_review_count += 1
        else:
            reviewed_rows.append(row)

    if all_errors:
        print(f"\n[VALIDATION FAILED] Found {len(all_errors)} error(s):", file=sys.stderr)
        for err in all_errors[:20]:
            print(f"  - {err}", file=sys.stderr)
        if len(all_errors) > 20:
            print(f"  ... and {len(all_errors) - 20} more errors.", file=sys.stderr)
        return 1

    print("\n[VALIDATION PASSED]")
    print(f"  - Total rows: {len(rows)}")
    print(f"  - Needs review (pending): {pending_review_count}")
    print(f"  - Reviewed rows (ready): {len(reviewed_rows)}")

    if validate_only:
        print("\nValidate-only mode: no files written.")
        return 0

    # Load existing benchmark cases
    synthetic_cases: list[dict[str, Any]] = []
    if benchmark_path.exists():
        with open(benchmark_path, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
            for c in existing_data.get("cases", []):
                # Preserve synthetic cases
                if c.get("split") == "synthetic" or str(c.get("case_id", "")).startswith("case_"):
                    c["split"] = "synthetic"
                    synthetic_cases.append(c)

    print(f"  - Preserved synthetic benchmark cases: {len(synthetic_cases)}")

    # Convert reviewed rows into benchmark cases
    converted_cases = [convert_row_to_case(r, base_dir).model_dump(mode="json") for r in reviewed_rows]
    print(f"  - Converted real benchmark cases: {len(converted_cases)}")

    # Final cases list
    final_cases = synthetic_cases + converted_cases

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out_payload = {
        "version": "1.0.0",
        "cases": final_cases,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(out_payload, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Wrote {len(final_cases)} benchmark cases to {output_path}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert reviewed draft CSV to benchmark JSON.")
    parser.add_argument("--csv", type=Path, default=ROOT_DIR / "annotations" / "draft.csv", help="Path to input CSV.")
    parser.add_argument("--benchmark", type=Path, default=ROOT_DIR / "eval" / "data" / "benchmark_cases.json", help="Existing benchmark JSON.")
    parser.add_argument("--output", type=Path, default=ROOT_DIR / "eval" / "data" / "benchmark_cases.json", help="Output benchmark JSON.")
    parser.add_argument("--validate-only", action="store_true", help="Only validate CSV without updating JSON.")

    args = parser.parse_args()
    code = process_csv_to_benchmark(
        csv_path=args.csv,
        benchmark_path=args.benchmark,
        output_path=args.output,
        validate_only=args.validate_only,
    )
    sys.exit(code)


if __name__ == "__main__":
    main()
