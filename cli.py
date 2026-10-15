"""Command Line Interface for Panela.Build wine bottle pipeline.

Usage:
    python cli.py --image tests/fixtures/sample_bottle.jpg
    python cli.py --image front.jpg --image back.jpg
    python cli.py --eval
"""

from __future__ import annotations
import argparse
import asyncio
import json
from pathlib import Path
from typing import List
from app.pipeline.orchestrator import WinePipeline
from eval.harness import run_evaluation


def load_env_file():
    """Load key-value pairs from .env into os.environ if present."""
    import os
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and val:
                        os.environ[key] = val


load_env_file()




async def process_images_cli(image_paths: List[Path]):
    valid_paths = [p for p in image_paths if p.exists()]
    if not valid_paths:
        print(f"[!] Error: None of the provided image paths exist: {image_paths}")
        return

    print(f"\n[*] Processing {len(valid_paths)} wine bottle photo(s): {[p.name for p in valid_paths]}...")
    pipeline = WinePipeline()

    images_bytes: List[bytes] = []
    for p in valid_paths:
        with open(p, "rb") as f:
            images_bytes.append(f.read())

    response = await pipeline.process_images(images_bytes)

    print("\n" + "=" * 64)
    print("  PANELA.BUILD - WINE EXPLANATION REPORT (PHASE 1)")
    print("=" * 64)
    print(f"HEADLINE:        {response.summary.headline}")
    print(f"CONFIDENCE TIER: {response.summary.tier.value.upper()}")
    print(f"TIER RATIONALE:  {response.summary.tier_explanation}")
    if response.summary.vintage:
        print(f"VINTAGE:         {response.summary.vintage}")
    if response.summary.appellation:
        print(f"APPELLATION:     {response.summary.appellation} ({response.summary.region}, {response.summary.country})")
    if response.summary.grapes:
        print(f"GRAPES:          {', '.join(response.summary.grapes)}")

    # Capture Guidance / Second photo analysis
    print("\n" + "-" * 64)
    print("  CAPTURE GUIDANCE (Camera Ingestion Analysis)")
    print("-" * 64)
    ca = response.capture_advice
    if ca.needs_second_photo:
        print(f"  [!] Second photo requested: YES (Type: {ca.suggested_label_type})")
        print(f"  Reason: {ca.reason}")
        print(f"  Prompt to User: \"{ca.user_prompt_message}\"")
    else:
        print(f"  [✓] Second photo requested: NO")
        print(f"  Status: {ca.user_prompt_message or 'Photo sufficient for confident assessment.'}")

    if response.drinking_guide:
        dg = response.drinking_guide
        print("\n" + "-" * 64)
        print("  1. HOW TO DRINK IT")
        print("-" * 64)
        print(f"  Temperature:   {dg.temperature.display_c} ({dg.temperature.display_f})")
        print(f"  Glassware:     {dg.glass_type}")
        print(f"  Decanting:     {'Yes (' + str(dg.decanting.duration_minutes) + ' mins)' if dg.decanting.recommended else 'No / Optional'} - {dg.decanting.rationale}")
        print(f"  Drink Window:  {dg.drink_window.window_years or 'Ready now'} ({dg.drink_window.rationale})")

    if response.tasting_notes:
        tn = response.tasting_notes
        print("\n" + "-" * 64)
        print("  2. TASTING PROFILE (Derived strictly from grape & terroir)")
        print("-" * 64)
        print(f"  Structure:     Acidity: {tn.structure.acidity}/5 | Tannin: {tn.structure.tannin or 'N/A'}/5 | Body: {tn.structure.body}/5 | Sweetness: {tn.structure.sweetness}/5")
        print(f"  Primary Notes: {', '.join([n.descriptor for n in tn.primary_notes])}")
        print(f"  Educational:   {tn.narrative}")

    if response.food_pairings:
        fp = response.food_pairings
        print("\n" + "-" * 64)
        print("  3. FOOD PAIRINGS (Chemical & sensory balance)")
        print("-" * 64)
        print("  Recommended:")
        for r in fp.recommended:
            print(f"    • {r.dish} [{r.pairing_rule}]: {r.why_it_works}")
        print("  To Avoid:")
        for a in fp.avoid:
            print(f"    ⚠ {a.dish_category}: {a.conflict_reason}")

    print("\n" + "-" * 64)
    print("  UNCERTAINTIES & MISSING FACTS")
    print("-" * 64)
    if response.uncertainties:
        for u in response.uncertainties:
            print(f"  • {u}")
    else:
        print("  None detected; all target fields resolved.")

    print("\n" + "-" * 64)
    print(f"  METRICS: Latency = {response.metrics.total_pipeline_ms}ms | Cost = ${response.metrics.estimated_cost_usd:.5f}")
    print("=" * 64 + "\n")

    print("[*] Strict JSON Output:")
    print(response.model_dump_json(indent=2))


def main():
    parser = argparse.ArgumentParser(description="Panela.Build Wine Explanation CLI")
    parser.add_argument("--image", "-i", action="append", type=Path, help="Path to bottle image (can specify multiple times)")
    parser.add_argument("--eval", action="store_true", help="Run full evaluation harness")
    parser.add_argument("--backend", choices=["mock", "gemini"], default="mock", help="Extraction backend for eval (mock or gemini)")
    parser.add_argument("--split", choices=["all", "dev", "test", "synthetic"], default="all", help="Dataset split to evaluate")

    args = parser.parse_args()

    if args.eval:
        asyncio.run(run_evaluation(backend=args.backend, split=args.split))
    elif args.image:
        asyncio.run(process_images_cli(args.image))
    else:
        sample = Path(__file__).resolve().parent / "tests" / "fixtures" / "sample_bottle.jpg"
        asyncio.run(process_images_cli([sample]))


if __name__ == "__main__":
    main()
