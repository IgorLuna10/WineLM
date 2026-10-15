"""Stage 1: VLM Extraction Pipeline.

Extracts structured facts from wine bottle images using a Vision-Language Model.
Enforces confidence scoring, explicit nulls, and schema validation.
"""

from __future__ import annotations
import json
import time
from typing import Optional, Protocol, Dict, Any, List
from app.schemas.extraction import ExtractionOutput, ConfidenceField, LabelQuality, WineType
from app.pipeline.prompts import SYSTEM_PROMPT_EXTRACTION, build_extraction_user_prompt


class VLMBackend(Protocol):
    """Protocol for pluggable VLM providers (API or local open-weights)."""
    async def extract_label(self, image_bytes: bytes, prompt: str, system_prompt: str) -> str:
        ...


class MockVLMBackend:
    """Deterministic mock backend for testing, eval harnesses, and offline verification."""

    def __init__(self, predefined_responses: Optional[Dict[str, ExtractionOutput]] = None):
        self.predefined_responses = predefined_responses or {}

    async def extract_label(self, image_bytes: bytes, prompt: str, system_prompt: str) -> str:
        # Check if an identifier is embedded or default to a standard high-quality Bordeaux
        key = getattr(self, "current_mock_key", "default_bordeaux")
        if key in self.predefined_responses:
            return self.predefined_responses[key].model_dump_json()

        # Default high-fidelity extraction
        default_output = ExtractionOutput(
            producer=ConfidenceField(value="Château Lynch-Bages", confidence=0.98, source_text="CHÂTEAU LYNCH-BAGES"),
            wine_name=ConfidenceField(value="Grand Cru Classé", confidence=0.90, source_text="GRAND CRU CLASSÉ"),
            cuvee=ConfidenceField(value=None, confidence=0.0, source_text=None),
            grape_varieties=[],  # Intentionally empty: AOC labels omit grapes!
            appellation=ConfidenceField(value="Pauillac", confidence=0.96, source_text="PAUILLAC"),
            region=ConfidenceField(value="Bordeaux", confidence=0.92, source_text="BORDEAUX"),
            country=ConfidenceField(value="France", confidence=0.99, source_text="FRANCE"),
            vintage=ConfidenceField(value=2018, confidence=0.99, source_text="2018"),
            abv=ConfidenceField(value=14.5, confidence=0.95, source_text="14.5% vol"),
            volume_ml=ConfidenceField(value=750, confidence=0.95, source_text="750ml"),
            wine_type=ConfidenceField(value=WineType.RED, confidence=0.95, source_text=None),
            classifications=[
                ConfidenceField(value="Grand Cru Classé", confidence=0.98, source_text="GRAND CRU CLASSÉ"),
                ConfidenceField(value="AOC", confidence=0.95, source_text="APPELLATION PAUILLAC CONTRÔLÉE")
            ],
            barcode=ConfidenceField(value="3348120018012", confidence=0.92, source_text="3348120018012"),
            back_label_text=ConfidenceField(value="Mis en bouteille au château. Elevé en fûts de chêne.", confidence=0.90, source_text="Mis en bouteille..."),
            label_quality=LabelQuality.HIGH,
            raw_ocr_tokens=["CHÂTEAU", "LYNCH-BAGES", "PAUILLAC", "2018", "14.5%", "750ml"],
            uncertainties=["Grape varieties not printed on label (typical for Pauillac AOC)."]
        )
        return default_output.model_dump_json()


def merge_confidence_field(f1: ConfidenceField[T], f2: ConfidenceField[T]) -> ConfidenceField[T]:
    """Arbitrates two readings of the same field, favoring higher calibrated confidence."""
    if f1.value is None and f2.value is not None:
        return f2
    if f2.value is None and f1.value is not None:
        return f1
    return f1 if f1.confidence >= f2.confidence else f2


def merge_extractions(e1: ExtractionOutput, e2: ExtractionOutput) -> ExtractionOutput:
    """Fuses two label extractions (e.g. front label + back label) into a unified factual record."""
    # Merge lists
    grapes_map: Dict[str, ConfidenceField[str]] = {}
    for g in e1.grape_varieties + e2.grape_varieties:
        if g.value:
            key = g.value.lower().strip()
            if key not in grapes_map or g.confidence > grapes_map[key].confidence:
                grapes_map[key] = g

    classes_map: Dict[str, ConfidenceField[str]] = {}
    for c in e1.classifications + e2.classifications:
        if c.value:
            key = c.value.lower().strip()
            if key not in classes_map or c.confidence > classes_map[key].confidence:
                classes_map[key] = c

    # Determine overall quality
    order = [LabelQuality.HIGH, LabelQuality.MEDIUM, LabelQuality.LOW, LabelQuality.UNREADABLE]
    merged_quality = e1.label_quality
    if order.index(e2.label_quality) < order.index(e1.label_quality):
        merged_quality = e2.label_quality

    # Combine OCR tokens and uncertainties without duplicates
    merged_tokens = list(dict.fromkeys(e1.raw_ocr_tokens + e2.raw_ocr_tokens))
    merged_uncertainties = list(dict.fromkeys(e1.uncertainties + e2.uncertainties))

    return ExtractionOutput(
        producer=merge_confidence_field(e1.producer, e2.producer),
        wine_name=merge_confidence_field(e1.wine_name, e2.wine_name),
        cuvee=merge_confidence_field(e1.cuvee, e2.cuvee),
        grape_varieties=list(grapes_map.values()),
        appellation=merge_confidence_field(e1.appellation, e2.appellation),
        region=merge_confidence_field(e1.region, e2.region),
        country=merge_confidence_field(e1.country, e2.country),
        vintage=merge_confidence_field(e1.vintage, e2.vintage),
        abv=merge_confidence_field(e1.abv, e2.abv),
        volume_ml=merge_confidence_field(e1.volume_ml, e2.volume_ml),
        wine_type=merge_confidence_field(e1.wine_type, e2.wine_type),
        classifications=list(classes_map.values()),
        barcode=merge_confidence_field(e1.barcode, e2.barcode),
        back_label_text=merge_confidence_field(e1.back_label_text, e2.back_label_text),
        label_quality=merged_quality,
        raw_ocr_tokens=merged_tokens,
        uncertainties=merged_uncertainties,
    )


class ExtractionStage:
    """Coordinates optical extraction with schema validation, error fallback, and multi-photo fusion."""

    def __init__(self, backend: Optional[VLMBackend] = None):
        self.backend = backend or MockVLMBackend()

    async def run(self, image_bytes: bytes, additional_context: str = "") -> tuple[ExtractionOutput, float]:
        start = time.perf_counter()
        user_prompt = build_extraction_user_prompt(additional_context)

        raw_json_str = await self.backend.extract_label(
            image_bytes=image_bytes,
            prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT_EXTRACTION,
        )

        elapsed_ms = (time.perf_counter() - start) * 1000.0

        try:
            parsed = ExtractionOutput.model_validate_json(raw_json_str)
        except Exception as err:
            parsed = ExtractionOutput(
                label_quality=LabelQuality.UNREADABLE,
                uncertainties=[f"Failed to parse structured VLM output: {str(err)}"]
            )

        return parsed, elapsed_ms

    async def run_multiple(self, images: List[bytes], contexts: Optional[List[str]] = None) -> tuple[ExtractionOutput, float]:
        """Runs extractions across multiple images (e.g. front + back label) and merges facts."""
        if not images:
            return ExtractionOutput(label_quality=LabelQuality.UNREADABLE), 0.0

        if len(images) == 1:
            ctx = contexts[0] if contexts else ""
            return await self.run(images[0], ctx)

        total_ms = 0.0
        extractions: List[ExtractionOutput] = []

        for idx, img in enumerate(images):
            ctx = contexts[idx] if contexts and idx < len(contexts) else f"Photo {idx + 1}"
            ext, ms = await self.run(img, ctx)
            total_ms += ms
            extractions.append(ext)

        # Fuse sequentially
        fused = extractions[0]
        for next_ext in extractions[1:]:
            fused = merge_extractions(fused, next_ext)

        return fused, total_ms
