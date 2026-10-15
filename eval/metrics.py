"""Evaluation metrics computation.

Measures:
1. Field extraction accuracy (per field).
2. Identification top-1 accuracy.
3. Confident-but-wrong rate (confidence >= 0.80 but false value).
4. Unsupported claim rate (hallucination rate on generated text).
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Set
from rapidfuzz import fuzz
from app.schemas.extraction import ExtractionOutput
from app.schemas.response import FinalResponse
from eval.dataset import BenchmarkCase, GroundTruthExtraction
from app.data.db import SqliteWineDatabase
from app.pipeline.knowledge import KnowledgeBaseRepository

_SHARED_DB: Optional[SqliteWineDatabase] = None
_SHARED_KB: Optional[KnowledgeBaseRepository] = None


def get_shared_db() -> SqliteWineDatabase:
    global _SHARED_DB
    if _SHARED_DB is None:
        _SHARED_DB = SqliteWineDatabase()
    return _SHARED_DB


def get_shared_kb() -> KnowledgeBaseRepository:
    global _SHARED_KB
    if _SHARED_KB is None:
        _SHARED_KB = KnowledgeBaseRepository()
    return _SHARED_KB


def compute_allowed_claims_for_case(
    case: BenchmarkCase,
    db: Optional[SqliteWineDatabase] = None,
    kb: Optional[KnowledgeBaseRepository] = None,
) -> Set[str]:
    """Computes the allowed claim set for a benchmark case.

    For identified wines:
      Derives claims automatically from the matched catalog record (wines.sqlite)
      and knowledge base entries (canonical blend grapes, appellation facts, authorized grapes).

    For cases with no catalog match:
      Uses the hand-written case.verified_claims plus any ground truth grape varieties.
    """
    allowed_claims: Set[str] = set()
    gt = case.ground_truth_extraction

    if case.expected_canonical_id:
        database = db or get_shared_db()
        wine_rec = database.get_by_id(case.expected_canonical_id)
        k_repo = kb or get_shared_kb()

        if wine_rec:
            for field in ["canonical_producer", "canonical_wine_name", "cuvee", "region", "country", "wine_type"]:
                val = wine_rec.get(field)
                if val:
                    allowed_claims.add(str(val))
            if wine_rec.get("vintage"):
                allowed_claims.add(str(wine_rec["vintage"]))
            if wine_rec.get("appellation"):
                allowed_claims.add(str(wine_rec["appellation"]))

            # All grapes in canonical blend
            for g in wine_rec.get("grapes", []):
                allowed_claims.add(str(g))

            app_name = (wine_rec.get("appellation") or gt.appellation or "").lower()
            if app_name and app_name in k_repo.appellations:
                app_prof = k_repo.appellations[app_name]
                for ag in app_prof.authorized_grapes:
                    allowed_claims.add(str(ag))
                allowed_claims.add(app_prof.name)
                allowed_claims.add(app_prof.region)
                allowed_claims.add(app_prof.country)

            # Grape synonyms
            for claim_item in list(allowed_claims):
                g_lower = claim_item.lower()
                if g_lower in k_repo.grapes:
                    g_prof = k_repo.grapes[g_lower]
                    allowed_claims.add(g_prof.name)
                    for syn in g_prof.synonyms:
                        allowed_claims.add(syn)

        for g in gt.grape_varieties:
            allowed_claims.add(str(g))
    else:
        # Non-matched / style cases: keep hand-written verified_claims
        for vc in case.verified_claims:
            allowed_claims.add(str(vc))
        for g in gt.grape_varieties:
            allowed_claims.add(str(g))
        if gt.appellation:
            allowed_claims.add(str(gt.appellation))
            k_repo = kb or get_shared_kb()
            app_lower = gt.appellation.lower()
            if app_lower in k_repo.appellations:
                app_prof = k_repo.appellations[app_lower]
                for ag in app_prof.authorized_grapes:
                    allowed_claims.add(str(ag))

    return allowed_claims


def compare_scalar(extracted_val: Any, gt_val: Any) -> bool:
    if extracted_val is None and gt_val is None:
        return True
    if extracted_val is None or gt_val is None:
        return False
    
    if isinstance(gt_val, (int, float)):
        try:
            return abs(float(extracted_val) - float(gt_val)) < 0.2
        except (ValueError, TypeError):
            return False

    # String fuzzy comparison
    str_extracted = str(extracted_val).lower().strip()
    str_gt = str(gt_val).lower().strip()
    return fuzz.token_set_ratio(str_extracted, str_gt) >= 85


def evaluate_case(
    case: BenchmarkCase,
    extraction: ExtractionOutput,
    response: FinalResponse,
    db: Optional[SqliteWineDatabase] = None,
    kb: Optional[KnowledgeBaseRepository] = None,
) -> Dict[str, Any]:
    gt = case.ground_truth_extraction
    results = {}

    # 1. Field-by-field accuracy
    fields_to_check = {
        "producer": (extraction.producer.value, gt.producer, extraction.producer.confidence),
        "wine_name": (extraction.wine_name.value, gt.wine_name, extraction.wine_name.confidence),
        "appellation": (extraction.appellation.value, gt.appellation, extraction.appellation.confidence),
        "vintage": (extraction.vintage.value, gt.vintage, extraction.vintage.confidence),
        "abv": (extraction.abv.value, gt.abv, extraction.abv.confidence),
        "barcode": (extraction.barcode.value, gt.barcode, extraction.barcode.confidence),
    }

    field_correctness = {}
    confident_but_wrong = []

    for f_name, (ext_v, gt_v, conf) in fields_to_check.items():
        is_correct = compare_scalar(ext_v, gt_v)
        field_correctness[f_name] = is_correct

        # Check safety metric: Confident-but-wrong
        if conf >= 0.80 and not is_correct and gt_v is not None:
            confident_but_wrong.append(f_name)

    results["field_correctness"] = field_correctness
    results["confident_but_wrong_fields"] = confident_but_wrong

    # 2. Identification top-1 check
    matched_id = response.summary.match_info.matched_id if response.summary.match_info else None
    if case.expected_canonical_id is None:
        # Expected no match
        results["identification_top1"] = matched_id is None
    else:
        results["identification_top1"] = (matched_id == case.expected_canonical_id)

    # 3. Tier correctness
    results["tier_correct"] = (response.summary.tier.value == case.expected_tier)

    # 4. Faithfulness / Unsupported Claim Rate check
    # Check if narrative contains unauthorized grape names not in ground truth or allowed claims
    unsupported_claims_count = 0
    total_checkable_claims = 0

    allowed_claims = compute_allowed_claims_for_case(case, db=db, kb=kb)
    allowed_claims_lower = {str(c).lower().strip() for c in allowed_claims}

    if response.tasting_notes:
        narrative = response.tasting_notes.narrative.lower()
        common_grapes = [
            "merlot", "cabernet sauvignon", "cabernet franc", "cabernet",
            "pinot noir", "syrah", "chardonnay", "sauvignon blanc", "sauvignon",
            "riesling", "viognier", "melon de bourgogne", "nero d'avola",
            "grenache", "savagnin", "poulsard", "petit verdot"
        ]
        for g in common_grapes:
            if g in narrative:
                total_checkable_claims += 1
                # Must be supported by allowed claims
                is_supported = any(g in c or c in g for c in allowed_claims_lower)
                if not is_supported:
                    unsupported_claims_count += 1

    results["unsupported_claims_count"] = unsupported_claims_count
    results["total_checkable_claims"] = total_checkable_claims

    return results


class BenchmarkReport:
    """Aggregates benchmark metrics across the test suite."""

    def __init__(self):
        self.total_cases = 0
        self.field_hits: Dict[str, int] = {}
        self.field_totals: Dict[str, int] = {}
        self.id_top1_hits = 0
        self.tier_hits = 0
        self.confident_but_wrong_count = 0
        self.total_confident_fields = 0
        self.unsupported_claims = 0
        self.total_claims = 0
        self.total_latency_ms = 0.0

    def add_case_result(self, case_eval: Dict[str, Any], latency_ms: float):
        self.total_cases += 1
        self.total_latency_ms += latency_ms

        for f_name, is_correct in case_eval["field_correctness"].items():
            self.field_totals[f_name] = self.field_totals.get(f_name, 0) + 1
            if is_correct:
                self.field_hits[f_name] = self.field_hits.get(f_name, 0) + 1

        if case_eval["identification_top1"]:
            self.id_top1_hits += 1

        if case_eval["tier_correct"]:
            self.tier_hits += 1

        cbw = len(case_eval["confident_but_wrong_fields"])
        self.confident_but_wrong_count += cbw

        self.unsupported_claims += case_eval["unsupported_claims_count"]
        self.total_claims += case_eval["total_checkable_claims"]

    def compute_summary(self) -> Dict[str, Any]:
        field_accuracies = {
            f: round(self.field_hits.get(f, 0) / max(1, self.field_totals.get(f, 1)), 3)
            for f in self.field_totals
        }

        unsupported_rate = (
            round(self.unsupported_claims / self.total_claims, 3)
            if self.total_claims > 0 else 0.0
        )

        return {
            "total_cases_evaluated": self.total_cases,
            "field_extraction_accuracy": field_accuracies,
            "field_hits": dict(self.field_hits),
            "field_totals": dict(self.field_totals),
            "identification_top1_accuracy": round(self.id_top1_hits / max(1, self.total_cases), 3),
            "identification_top1_hits": self.id_top1_hits,
            "tier_assignment_accuracy": round(self.tier_hits / max(1, self.total_cases), 3),
            "tier_hits": self.tier_hits,
            "confident_but_wrong_rate": round(self.confident_but_wrong_count / max(1, self.total_cases), 3),
            "confident_but_wrong_count": self.confident_but_wrong_count,
            "unsupported_claim_rate": unsupported_rate,
            "unsupported_claims_count": self.unsupported_claims,
            "total_checkable_claims": self.total_claims,
            "mean_pipeline_latency_ms": round(self.total_latency_ms / max(1, self.total_cases), 2),
        }
