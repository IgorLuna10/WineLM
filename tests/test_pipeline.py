"""Unit tests for Panela.Build wine pipeline."""

import asyncio
from app.schemas.extraction import ExtractionOutput, ConfidenceField, LabelQuality, WineType
from app.schemas.response import ConfidenceTier, FinalResponse
from app.data.db import SqliteWineDatabase
from app.pipeline.extraction import merge_extractions
from app.pipeline.identification import IdentificationStage
from app.pipeline.knowledge import KnowledgeStage
from app.pipeline.validator import HallucinationValidator
from app.pipeline.generation import GenerationStage
from app.pipeline.orchestrator import WinePipeline
from app.models.gemini import GeminiFlashVLM


def test_end_to_end_pipeline():
    pipeline = WinePipeline()
    dummy_bytes = b"fake_bottle_image_bytes"
    response = asyncio.run(pipeline.process_image(dummy_bytes))

    assert isinstance(response, FinalResponse)
    assert response.summary.tier == ConfidenceTier.IDENTIFIED_WINE
    assert response.summary.headline is not None
    assert response.drinking_guide is not None
    assert response.drinking_guide.temperature.min_c <= response.drinking_guide.temperature.max_c
    assert response.tasting_notes is not None
    assert response.food_pairings is not None
    assert len(response.uncertainties) > 0
    assert len(response.traceability_log) > 0
    assert response.capture_advice is not None


def test_identification_barcode_sqlite():
    id_stage = IdentificationStage()
    extraction = ExtractionOutput(
        barcode=ConfidenceField(value="3256228001010", confidence=0.99),
    )
    match_info, ref_data, _ = id_stage.run(extraction)
    assert match_info is not None
    assert match_info.matched_id == "ref_faiveley_mercurey_2020"
    assert match_info.match_source == "sqlite_ean_barcode_index"
    assert match_info.match_confidence >= 0.95


def test_identification_fuzzy_sqlite():
    id_stage = IdentificationStage()
    extraction = ExtractionOutput(
        producer=ConfidenceField(value="Domaine Faiveley", confidence=0.9),
        wine_name=ConfidenceField(value="Mercurey 1er Cru Myglands", confidence=0.85),
        vintage=ConfidenceField(value=2020, confidence=0.95),
    )
    match_info, ref_data, _ = id_stage.run(extraction)
    assert match_info is not None
    assert match_info.matched_id == "ref_faiveley_mercurey_2020"
    assert match_info.match_source == "sqlite_fts_fuzzy_match"


def test_multi_image_fusion_front_and_back():
    # Front label has clear producer & appellation, but no barcode or ABV
    front_label = ExtractionOutput(
        producer=ConfidenceField(value="Château Lynch-Bages", confidence=0.98),
        appellation=ConfidenceField(value="Pauillac", confidence=0.95),
        vintage=ConfidenceField(value=2018, confidence=0.90),
        barcode=ConfidenceField(value=None, confidence=0.0),
        abv=ConfidenceField(value=None, confidence=0.0),
        label_quality=LabelQuality.HIGH,
    )

    # Back label has barcode and ABV, but producer is tiny/absent
    back_label = ExtractionOutput(
        producer=ConfidenceField(value=None, confidence=0.0),
        appellation=ConfidenceField(value="Pauillac", confidence=0.60),
        barcode=ConfidenceField(value="3348120018012", confidence=0.99),
        abv=ConfidenceField(value=14.5, confidence=0.98),
        back_label_text=ConfidenceField(value="Elevé en fûts de chêne français", confidence=0.95),
        label_quality=LabelQuality.MEDIUM,
    )

    fused = merge_extractions(front_label, back_label)

    # Fused record must contain best of both
    assert fused.producer.value == "Château Lynch-Bages"
    assert fused.producer.confidence == 0.98
    assert fused.barcode.value == "3348120018012"
    assert fused.barcode.confidence == 0.99
    assert fused.abv.value == 14.5
    assert fused.back_label_text.value == "Elevé en fûts de chêne français"
    assert fused.label_quality == LabelQuality.HIGH


def test_capture_advice_requests_back_label_when_vintage_barcode_missing():
    gen_stage = GenerationStage()
    kb_stage = KnowledgeStage()

    # Front label only: known appellation, but missing vintage and barcode
    partial_extraction = ExtractionOutput(
        producer=ConfidenceField(value="Domaine Inconnu", confidence=0.8),
        appellation=ConfidenceField(value="Mercurey", confidence=0.85),
        vintage=ConfidenceField(value=None, confidence=0.0),
        barcode=ConfidenceField(value=None, confidence=0.0),
    )
    knowledge, _ = kb_stage.run(partial_extraction, None, None)
    response, _ = gen_stage.run(partial_extraction, None, knowledge, photo_count=1)

    assert response.capture_advice.needs_second_photo is True
    assert response.capture_advice.suggested_label_type == "back_label"
    assert "back label" in response.capture_advice.user_prompt_message.lower()


def test_capture_advice_satisfied_when_multi_photos_provided():
    gen_stage = GenerationStage()
    kb_stage = KnowledgeStage()

    partial_extraction = ExtractionOutput(
        producer=ConfidenceField(value="Domaine Inconnu", confidence=0.8),
        appellation=ConfidenceField(value="Mercurey", confidence=0.85),
    )
    knowledge, _ = kb_stage.run(partial_extraction, None, None)
    # When 2 photos were already submitted:
    response, _ = gen_stage.run(partial_extraction, None, knowledge, photo_count=2)

    assert response.capture_advice.needs_second_photo is False


def test_tier_unidentified_when_label_unreadable():
    gen_stage = GenerationStage()
    kb_stage = KnowledgeStage()

    unreadable_extraction = ExtractionOutput(
        label_quality=LabelQuality.UNREADABLE,
        uncertainties=["Image too blurry to read."],
    )
    knowledge, _ = kb_stage.run(unreadable_extraction, None, None)
    response, _ = gen_stage.run(unreadable_extraction, None, knowledge)

    assert response.summary.tier == ConfidenceTier.UNIDENTIFIED
    assert response.drinking_guide is None
    assert response.tasting_notes is None
    assert response.capture_advice.needs_second_photo is True
    assert response.capture_advice.suggested_label_type == "clearer_shot"


def test_validator_catches_hallucinated_grapes():
    validator = HallucinationValidator()
    gen_stage = GenerationStage(validator=validator)
    kb_stage = KnowledgeStage()

    extraction = ExtractionOutput(
        appellation=ConfidenceField(value="Chablis", confidence=0.95),
        wine_type=ConfidenceField(value=WineType.WHITE, confidence=0.9),
    )
    knowledge, _ = kb_stage.run(extraction, None, None)
    response, _ = gen_stage.run(extraction, None, knowledge)

    # Inject unauthorized grape
    response.tasting_notes.narrative += " Rich hints of cabernet sauvignon."
    is_valid, violations, _ = validator.validate(response, extraction, knowledge)

    assert not is_valid
    assert any("cabernet sauvignon" in v for v in violations)


def test_gemini_flash_fallback():
    # When no API key is set, falls back to MockVLMBackend cleanly without raising
    client = GeminiFlashVLM(api_key=None)
    result = asyncio.run(client.extract_label(b"fake_image", "prompt", "system"))
    assert "producer" in result


def test_lynch_bages_cabernet_franc_supported_claims():
    """Task 2 test: Lynch-Bages allowed claims derived from catalog/KB
    must include Cabernet Franc and not be flagged as hallucinated or unsupported."""
    from eval.dataset import load_benchmark_suite
    from eval.metrics import compute_allowed_claims_for_case, evaluate_case

    suite = load_benchmark_suite()
    lb_cases = [c for c in suite if "lynch_bages" in c.case_id]
    assert len(lb_cases) > 0, "Lynch-Bages benchmark case not found"
    lb_case = lb_cases[0]

    # Verify hand-written verified_claims was removed for identified wine
    assert len(lb_case.verified_claims) == 0, "Hand-maintained verified_claims must be empty for identified wine"

    # Compute allowed claims automatically from catalog record + KB
    allowed = compute_allowed_claims_for_case(lb_case)
    allowed_lower = {str(c).lower().strip() for c in allowed}

    # Verify Cabernet Franc is included from canonical blend / Pauillac KB
    assert any("cabernet franc" in c for c in allowed_lower), f"Cabernet Franc must be in allowed claims: {allowed_lower}"
    assert any("cabernet sauvignon" in c for c in allowed_lower)
    assert any("merlot" in c for c in allowed_lower)

    # Verify evaluating a narrative mentioning Cabernet Franc produces 0 unsupported claims
    extraction = ExtractionOutput(
        producer=ConfidenceField(value="Château Lynch-Bages", confidence=0.98),
        wine_name=ConfidenceField(value="Grand Cru Classé", confidence=0.95),
        appellation=ConfidenceField(value="Pauillac", confidence=0.95),
        vintage=ConfidenceField(value=2018, confidence=0.95),
        wine_type=ConfidenceField(value=WineType.RED, confidence=0.95),
    )
    id_stage = IdentificationStage()
    match_info, ref_data, _ = id_stage.run(extraction)
    kb_stage = KnowledgeStage()
    knowledge, _ = kb_stage.run(extraction, match_info, ref_data)
    gen_stage = GenerationStage()
    response, _ = gen_stage.run(extraction, match_info, knowledge)

    # Narrative explicitly mentions Cabernet Franc
    response.tasting_notes.narrative += " Notes of blackcurrant supported by Cabernet Franc."
    eval_res = evaluate_case(lb_case, extraction, response)

    assert eval_res["unsupported_claims_count"] == 0, f"Expected 0 unsupported claims, got {eval_res['unsupported_claims_count']}"
    assert eval_res["total_checkable_claims"] >= 1


def test_annotation_workflow_validation():
    """Task 3 test: Validate draft CSV and conversion to benchmark cases."""
    from pathlib import Path
    from scripts.csv_to_benchmark import process_csv_to_benchmark

    draft_csv = Path("annotations/draft.csv")
    assert draft_csv.exists(), "annotations/draft.csv must exist"

    # Validate draft.csv in validate-only mode
    code = process_csv_to_benchmark(
        csv_path=draft_csv,
        benchmark_path=Path("eval/data/benchmark_cases.json"),
        output_path=Path("eval/data/benchmark_cases.json"),
        validate_only=True,
    )
    assert code == 0, "Validation on draft.csv must pass"

