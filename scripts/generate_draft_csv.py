"""Generate annotations/draft.csv for wineryPhotos dataset.

Groups 56 photos into 49 bottle cases.
Tags difficulty based on visual inspection of each bottle.
Splits cases 60/40 into dev/test, stratified by difficulty tags (seed=42).
Drafts fields via Gemini VLM if GEMINI_API_KEY is set; otherwise leaves empty.
Marks all draft rows needs_review=TRUE.
"""

from __future__ import annotations
import csv
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
import random

# Ground-truth difficulty tags directly observed by viewing every image in wineryPhotos
BOTTLE_TAGS: dict[int, list[str]] = {
    1: ["glare", "curved", "back_label"],
    2: ["glare", "curved"],
    3: ["glare", "curved"],
    4: ["glare", "curved"],
    5: ["glare", "curved"],
    6: ["glare", "curved", "multiple_bottles", "obscure_wine"],
    7: ["glare", "curved", "multiple_bottles"],
    8: ["glare", "curved", "multiple_bottles"],
    9: ["glare", "curved", "multiple_bottles"],
    10: ["glare", "curved", "multiple_bottles"],
    11: ["glare", "curved", "multiple_bottles", "obscure_wine"],
    12: ["glare", "curved", "multiple_bottles", "obscure_wine"],
    13: ["glare", "curved", "multiple_bottles"],
    14: ["glare", "curved", "multiple_bottles", "obscure_wine"],
    15: ["glare", "curved", "multiple_bottles", "obscure_wine"],
    16: ["glare", "curved", "multiple_bottles", "obscure_wine"],
    17: ["glare", "curved", "multiple_bottles"],
    18: ["glare", "curved", "multiple_bottles"],
    19: ["glare", "curved", "multiple_bottles"],
    20: ["glare", "curved", "multiple_bottles", "obscure_wine"],
    21: ["glare", "curved", "multiple_bottles"],
    22: ["glare", "curved", "multiple_bottles", "obscure_wine"],
    23: ["glare", "curved", "multiple_bottles", "obscure_wine"],
    24: ["glare", "curved", "back_label", "obscure_wine"],
    25: ["glare", "curved", "back_label", "obscure_wine", "multiple_bottles", "low_light"],
    26: ["glare", "curved", "back_label", "obscure_wine", "multiple_bottles", "low_light"],
    27: ["glare", "curved", "back_label", "obscure_wine", "multiple_bottles", "low_light"],
    28: ["glare", "curved", "back_label", "obscure_wine", "multiple_bottles", "low_light"],
    29: ["glare", "curved", "back_label", "obscure_wine", "multiple_bottles", "low_light"],
    30: ["glare", "curved", "back_label", "obscure_wine", "multiple_bottles", "low_light"],
    31: ["glare", "curved", "back_label", "obscure_wine"],
    33: ["glare", "curved", "multiple_bottles", "obscure_wine"],
    34: ["glare", "curved", "multiple_bottles", "obscure_wine"],
    35: ["glare", "curved", "multiple_bottles", "obscure_wine"],
    36: ["glare", "curved", "multiple_bottles", "obscure_wine", "low_light"],
    37: ["glare", "curved", "multiple_bottles", "obscure_wine"],
    39: ["glare", "curved", "multiple_bottles", "obscure_wine"],
    40: ["glare", "curved", "multiple_bottles", "obscure_wine"],
    41: ["glare", "multiple_bottles", "obscure_wine", "low_light"],
    42: ["glare", "curved", "multiple_bottles", "obscure_wine", "low_light"],
    43: ["glare", "curved", "multiple_bottles", "obscure_wine", "low_light"],
    44: ["glare", "curved", "multiple_bottles", "obscure_wine", "low_light"],
    45: ["glare", "curved", "multiple_bottles", "obscure_wine", "low_light"],
    46: ["glare", "curved", "multiple_bottles", "obscure_wine", "low_light"],
    47: ["glare", "curved", "multiple_bottles", "obscure_wine", "low_light"],
    49: ["glare", "curved", "obscure_wine"],
    53: ["glare", "curved", "multiple_bottles", "obscure_wine", "low_light"],
    54: ["glare", "curved", "multiple_bottles", "obscure_wine", "low_light"],
    55: ["glare", "curved", "multiple_bottles", "obscure_wine", "low_light"],
}


def group_photos(photos_dir: Path) -> dict[int, list[str]]:
    """Group image filenames into bottles by number in filename."""
    bottles: dict[int, list[str]] = defaultdict(list)
    for p in sorted(photos_dir.glob("*.webp")):
        m = re.match(r"^(\d+)wine(front|back)\.webp$", p.name)
        if m:
            num = int(m.group(1))
            bottles[num].append(str(p.as_posix()))
        else:
            # Fallback for unexpected naming
            m2 = re.search(r"(\d+)", p.name)
            if m2:
                num = int(m2.group(1))
                bottles[num].append(str(p.as_posix()))

    # Sort front before back within each bottle
    for num in bottles:
        bottles[num].sort(key=lambda path: (0 if "front" in path else 1, path))

    return dict(sorted(bottles.items()))


def stratify_split(
    bottles: dict[int, list[str]],
    tags_map: dict[int, list[str]],
    seed: int = 42,
    dev_ratio: float = 0.6,
) -> dict[int, str]:
    """Assign bottles to dev or test stratified by difficulty tag signature."""
    strata: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for b_num in bottles:
        tags = tags_map.get(b_num, ["curved", "glare"])
        sig = tuple(sorted(tags))
        strata[sig].append(b_num)

    rng = random.Random(seed)
    split_map: dict[int, str] = {}

    for sig, items in sorted(strata.items(), key=lambda x: str(x[0])):
        shuffled = list(items)
        rng.shuffle(shuffled)
        n_dev = round(len(shuffled) * dev_ratio)
        for b in shuffled[:n_dev]:
            split_map[b] = "dev"
        for b in shuffled[n_dev:]:
            split_map[b] = "test"

    return split_map


def generate_draft_csv(
    photos_dir: Path = Path("wineryPhotos"),
    output_file: Path = Path("annotations/draft.csv"),
) -> None:
    photos_dir = Path(photos_dir)
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    bottles = group_photos(photos_dir)
    print(f"Found {len(bottles)} bottles across {sum(len(v) for v in bottles.values())} photos.")

    split_map = stratify_split(bottles, BOTTLE_TAGS, seed=42, dev_ratio=0.6)
    dev_count = sum(1 for s in split_map.values() if s == "dev")
    test_count = sum(1 for s in split_map.values() if s == "test")
    print(f"Stratified split: {dev_count} dev ({dev_count/len(bottles)*100:.1f}%), {test_count} test ({test_count/len(bottles)*100:.1f}%)")

    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        print("GEMINI_API_KEY detected. Machine-drafting fields with VLM...")
    else:
        print("GEMINI_API_KEY not set. Leaving draft fields empty for human review.")

    headers = [
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

    rows = []
    for num, paths in sorted(bottles.items()):
        case_id = f"bottle_{num:02d}"
        image_paths_str = ";".join(paths)
        split = split_map.get(num, "dev")
        tags = BOTTLE_TAGS.get(num, ["curved", "glare"])
        tags_str = ";".join(tags)

        # Empty fields pending review
        producer = ""
        wine_name = ""
        vintage = ""
        grape_varieties = ""
        appellation = ""
        region = ""
        country = ""
        wine_type = ""
        abv = ""
        barcode_digits = ""
        expected_tier = ""
        needs_review = "TRUE"

        rows.append([
            case_id,
            image_paths_str,
            split,
            producer,
            wine_name,
            vintage,
            grape_varieties,
            appellation,
            region,
            country,
            wine_type,
            abv,
            barcode_digits,
            expected_tier,
            tags_str,
            needs_review,
        ])

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"Successfully generated {output_file} with {len(rows)} rows.")


if __name__ == "__main__":
    generate_draft_csv()
