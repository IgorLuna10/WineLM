"""CLI Evaluation Harness.

Runs the wine explanation pipeline against benchmark test cases.
Computes and reports:
- Per-field extraction accuracy
- Identification Top-1 accuracy
- Confident-but-wrong rate (Critical Safety Guardrail)
- Hallucination / Unsupported claim rate
- Per-stage latency and token cost
"""

from __future__ import annotations
import asyncio
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.schemas.extraction import ExtractionOutput, ConfidenceField, LabelQuality, WineType
from app.schemas.response import FinalResponse, WineSummary, ConfidenceTier
from app.pipeline.orchestrator import WinePipeline
from app.pipeline.extraction import ExtractionStage, MockVLMBackend
from eval.dataset import load_benchmark_suite, BenchmarkCase
from eval.metrics import evaluate_case, BenchmarkReport


class BenchmarkMockVLM(MockVLMBackend):
    """Feeds ground-truth simulated VLM outputs for benchmark testing."""

    def __init__(self, cases: List[BenchmarkCase]):
        super().__init__()
        self.case_map: Dict[str, BenchmarkCase] = {c.case_id: c for c in cases}
        self.active_case_id: Optional[str] = None

    async def extract_label(self, image_bytes: bytes, prompt: str, system_prompt: str) -> str:
        if self.active_case_id and self.active_case_id in self.case_map:
            case = self.case_map[self.active_case_id]
            gt = case.ground_truth_extraction

            if case.expected_tier == "unidentified":
                out = ExtractionOutput(
                    label_quality=LabelQuality.UNREADABLE,
                    uncertainties=["Label obscured by excessive glare."]
                )
                return out.model_dump_json()

            grapes_conf = [
                ConfidenceField(value=g, confidence=0.95, source_text=g)
                for g in gt.grape_varieties
            ]
            wtype = WineType(gt.wine_type) if gt.wine_type else None

            out = ExtractionOutput(
                producer=ConfidenceField(value=gt.producer, confidence=0.95 if gt.producer else 0.0, source_text=gt.producer),
                wine_name=ConfidenceField(value=gt.wine_name, confidence=0.90 if gt.wine_name else 0.0, source_text=gt.wine_name),
                appellation=ConfidenceField(value=gt.appellation, confidence=0.95 if gt.appellation else 0.0, source_text=gt.appellation),
                region=ConfidenceField(value=gt.region, confidence=0.90 if gt.region else 0.0, source_text=gt.region),
                country=ConfidenceField(value=gt.country, confidence=0.95 if gt.country else 0.0, source_text=gt.country),
                vintage=ConfidenceField(value=gt.vintage, confidence=0.95 if gt.vintage else 0.0, source_text=str(gt.vintage) if gt.vintage else None),
                abv=ConfidenceField(value=gt.abv, confidence=0.90 if gt.abv else 0.0, source_text=f"{gt.abv}%" if gt.abv else None),
                wine_type=ConfidenceField(value=wtype, confidence=0.90 if wtype else 0.0, source_text=None),
                grape_varieties=grapes_conf,
                barcode=ConfidenceField(value=gt.barcode, confidence=0.98 if gt.barcode else 0.0, source_text=gt.barcode),
                label_quality=LabelQuality.HIGH if "standard" in [t.value for t in case.difficulty_tags] else LabelQuality.MEDIUM,
                uncertainties=[] if gt.producer else ["Producer not fully distinguishable."]
            )
            return out.model_dump_json()

        return await super().extract_label(image_bytes, prompt, system_prompt)


async def run_evaluation(
    output_report_path: Optional[Path] = None,
    backend: str = "mock",
    split: str = "all",
) -> Dict[str, Any]:
    all_cases = load_benchmark_suite()
    if not all_cases:
        print("[!] No benchmark cases found.")
        return {}

    if split != "all":
        cases = [c for c in all_cases if c.split == split]
    else:
        cases = all_cases

    if not cases:
        print(f"[!] No benchmark cases found for split: '{split}'.")
        return {}

    is_mock = (backend == "mock")
    if backend == "gemini":
        import os
        if not os.environ.get("GEMINI_API_KEY"):
            print("\n[!] Error: GEMINI_API_KEY is not set in environment.")
            print("    Cannot run evaluation with '--backend gemini' without an API key.\n")
            return {}
        from app.models.gemini import GeminiFlashVLM
        vlm_backend = GeminiFlashVLM()
        pipeline = WinePipeline(extraction_stage=ExtractionStage(backend=vlm_backend))
    elif backend == "mock":
        mock_vlm = BenchmarkMockVLM(cases)
        pipeline = WinePipeline(extraction_stage=ExtractionStage(backend=mock_vlm))
    else:
        raise ValueError(f"Unknown backend: {backend}. Allowed: 'mock', 'gemini'")

    report = BenchmarkReport()
    case_results = []

    print(f"\n=======================================================")
    print(f"  PANELA.BUILD WINE BACKEND EVALUATION HARNESS")
    print(f"  Backend: {backend.upper()} ({'SIMULATED EXTRACTION' if is_mock else 'LIVE VLM API'})")
    print(f"  Split:   {split.upper()}")
    print(f"  Benchmark Cases Evaluated: {len(cases)} (suite count; excludes unreviewed disk photos)")
    print(f"=======================================================\n")

    for case in cases:
        # Load image bytes if available, else fallback to mock bytes
        image_bytes_list: List[bytes] = []
        for img_p_str in case.image_paths or ([case.image_path] if case.image_path else []):
            p = Path(img_p_str)
            if p.exists():
                with open(p, "rb") as f:
                    image_bytes_list.append(f.read())

        if not image_bytes_list:
            image_bytes_list = [b"RIFF....WEBPVP8 ... fake_bytes"]

        start = time.perf_counter()
        if is_mock:
            mock_vlm.active_case_id = case.case_id
            response = await pipeline.process_images(image_bytes_list)
            extraction = ExtractionOutput.model_validate_json(
                await mock_vlm.extract_label(image_bytes_list[0], "", "")
            )
        else:
            try:
                response = await pipeline.process_images(image_bytes_list)
                extraction = response.extraction or ExtractionOutput(
                    label_quality=LabelQuality.UNREADABLE,
                    uncertainties=["Pipeline returned response without Stage 1 extraction facts."]
                )
            except Exception as err:
                print(f"[!] Evaluation failed on case {case.case_id}: {err}")
                response = FinalResponse(
                    summary=WineSummary(
                        headline="Unidentified Bottle",
                        tier=ConfidenceTier.UNIDENTIFIED,
                        tier_explanation=f"Pipeline exception during evaluation: {err}",
                    ),
                    uncertainties=[f"Exception: {err}"],
                )
                extraction = ExtractionOutput(
                    label_quality=LabelQuality.UNREADABLE,
                    uncertainties=[f"Exception during extraction: {err}"]
                )

        latency_ms = (time.perf_counter() - start) * 1000.0

        eval_res = evaluate_case(case, extraction, response)
        report.add_case_result(eval_res, latency_ms)

        tags_str = ",".join([t.value for t in case.difficulty_tags])
        if is_mock:
            # Under mock backend, never report PASS
            status = "SIMULATED"
        else:
            status = "PASS" if eval_res["tier_correct"] and eval_res["identification_top1"] and not eval_res["confident_but_wrong_fields"] else "FAIL"

        print(f"[{status:<9}] Case: {case.case_id:<32} Split: {case.split:<9} Tags: [{tags_str:<22}] Tier: {response.summary.tier.value:<16} Latency: {latency_ms:.1f}ms")

        case_results.append({
            "case_id": case.case_id,
            "split": case.split,
            "tags": [t.value for t in case.difficulty_tags],
            "expected_tier": case.expected_tier,
            "actual_tier": response.summary.tier.value,
            "latency_ms": latency_ms,
            "metrics": eval_res,
        })

        if not is_mock:
            await asyncio.sleep(2.0)

    summary = report.compute_summary()

    print("\n-------------------------------------------------------")
    print(f"  SUMMARY EVALUATION METRICS (Backend: {backend.upper()}{' - SIMULATED' if is_mock else ''})")
    print("-------------------------------------------------------")
    print(f"  Total Cases Evaluated:       {summary['total_cases_evaluated']} (n={summary['total_cases_evaluated']})")
    print(f"  Identification Top-1 Acc:    {summary['identification_top1_accuracy'] * 100:.1f}% ({summary['identification_top1_hits']}/{summary['total_cases_evaluated']})")
    print(f"  Tier Assignment Acc:         {summary['tier_assignment_accuracy'] * 100:.1f}% ({summary['tier_hits']}/{summary['total_cases_evaluated']})")
    print(f"  Confident-But-Wrong Rate:    {summary['confident_but_wrong_rate'] * 100:.1f}% ({summary['confident_but_wrong_count']}/{summary['total_cases_evaluated']}) (Safety guardrail)")
    print(f"  Unsupported Claim Rate:      {summary['unsupported_claim_rate'] * 100:.1f}% ({summary['unsupported_claims_count']}/{summary['total_checkable_claims']} claims) (Hallucination)")
    print(f"  Mean Pipeline Latency:       {summary['mean_pipeline_latency_ms']:.1f}ms")
    print(f"  Field Extraction Accuracy ({'SIMULATED - NEVER REPORT AS PASS' if is_mock else 'LIVE VLM'}):")
    for f, acc in summary["field_extraction_accuracy"].items():
        hits = summary["field_hits"].get(f, 0)
        tot = summary["field_totals"].get(f, 0)
        sim_tag = " [SIMULATED]" if is_mock else ""
        print(f"    - {f:<15}: {acc * 100:.1f}% ({hits}/{tot}){sim_tag}")
    print("-------------------------------------------------------\n")

    if output_report_path:
        with open(output_report_path, "w", encoding="utf-8") as f:
            json.dump({
                "backend": backend,
                "split": split,
                "summary": summary,
                "case_results": case_results
            }, f, indent=2)
        print(f"[+] Saved evaluation report to {output_report_path}")

    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Eval Harness")
    parser.add_argument("--backend", choices=["mock", "gemini"], default="mock")
    parser.add_argument("--split", choices=["all", "dev", "test", "synthetic"], default="all")
    args = parser.parse_args()
    asyncio.run(run_evaluation(backend=args.backend, split=args.split))
