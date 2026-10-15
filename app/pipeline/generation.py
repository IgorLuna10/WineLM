"""Stage 4: Text Generation and Response Synthesis.

Synthesizes extracted facts, matched reference data, and retrieved enological
knowledge into calm, factual, educational explanations.
Never hallucinates: words claims according to confidence tiers.
"""

from __future__ import annotations
import json
import re
import time
from typing import Optional, Dict, Any, List, Protocol
from app.schemas.extraction import ExtractionOutput, LabelQuality, WineType
from app.schemas.response import (
    FinalResponse,
    ConfidenceTier,
    WineSummary,
    DrinkingGuide,
    TastingNotes,
    FoodPairings,
    TemperatureRange,
    DecantingAdvice,
    DrinkWindow,
    StructuralProfile,
    FlavorDescriptor,
    DishPairing,
    FoodClash,
    MatchInfo,
    CaptureAdvice,
)
from app.schemas.knowledge import RetrievedKnowledge
from app.pipeline.validator import HallucinationValidator


class LLMBackend(Protocol):
    """Protocol for text generation model (e.g. Gemini Flash, Llama, GPT-4o-mini)."""
    async def generate_response(self, prompt: str, system_prompt: str) -> str:
        ...


def evaluate_capture_completeness(
    extraction: ExtractionOutput,
    match_info: Optional[MatchInfo],
    photo_count: int,
) -> CaptureAdvice:
    """Evaluates whether the user's photo is sufficient or if a second photo should be requested."""
    if photo_count > 1:
        return CaptureAdvice(
            needs_second_photo=False,
            user_prompt_message="Multiple angles provided. Label data fused successfully."
        )

    # 1. Image unreadable / low quality
    if extraction.label_quality in (LabelQuality.LOW, LabelQuality.UNREADABLE):
        return CaptureAdvice(
            needs_second_photo=True,
            suggested_label_type="clearer_shot",
            reason="Image quality is degraded by glare, blur, or severe curvature distortion.",
            user_prompt_message="The label was hard to read due to lighting or glare. Please snap a clearer, glare-free photo."
        )

    # 2. Exact match verified: single photo was completely sufficient!
    if match_info and match_info.match_confidence >= 0.85:
        return CaptureAdvice(
            needs_second_photo=False,
            user_prompt_message="First photo was sufficient for complete identification."
        )

    # 3. Barcode / technical info detected, but producer branding missing (typical back label)
    if extraction.barcode.is_reliable() and not extraction.producer.is_reliable():
        return CaptureAdvice(
            needs_second_photo=True,
            suggested_label_type="front_label",
            reason="Barcode was detected (typical of back label), but main estate name was not found.",
            user_prompt_message="Technical info detected. Please snap the front label to confirm the estate name."
        )

    # 4. Front label with appellation or producer, but missing vintage and barcode
    has_identity = extraction.appellation.is_reliable() or extraction.producer.is_reliable()
    missing_critical = not extraction.vintage.is_reliable() and not extraction.barcode.is_reliable()
    if has_identity and missing_critical:
        return CaptureAdvice(
            needs_second_photo=True,
            suggested_label_type="back_label",
            reason="Front label identified the style/appellation, but vintage and barcode are missing.",
            user_prompt_message="Wine style identified! Snapping the back label will capture the barcode and confirm the exact vintage."
        )

    return CaptureAdvice(
        needs_second_photo=False,
        user_prompt_message="Label details are sufficient for this wine style."
    )


class RuleBasedGenerator:
    """Deterministic, zero-hallucination baseline generator.
    
    Acts as the grounding anchor: formats extracted facts and KB nodes directly
    into the strict schema without free-form LLM factual drift.
    """

    @staticmethod
    def generate(
        extraction: ExtractionOutput,
        match_info: Optional[MatchInfo],
        knowledge: RetrievedKnowledge,
        tier: ConfidenceTier,
        photo_count: int = 1,
    ) -> FinalResponse:
        uncertainties: List[str] = list(extraction.uncertainties)
        capture_advice = evaluate_capture_completeness(extraction, match_info, photo_count)

        # -------------------------------------------------------------
        # TIER 3: UNIDENTIFIED
        # -------------------------------------------------------------
        if tier == ConfidenceTier.UNIDENTIFIED:
            uncertainties.append("Label is unreadable or insufficient data to determine style or producer.")
            return FinalResponse(
                summary=WineSummary(
                    headline="Unidentified Bottle",
                    tier=tier,
                    tier_explanation="The bottle label could not be reliably deciphered. Lighting, angle, or glare may be obscuring key text.",
                    wine_type=None,
                    vintage=None,
                    country=None,
                    region=None,
                    appellation=None,
                    grapes=[],
                    match_info=None,
                ),
                capture_advice=capture_advice,
                drinking_guide=None,
                tasting_notes=None,
                food_pairings=None,
                uncertainties=uncertainties,
            )

        # -------------------------------------------------------------
        # TIER 1 & TIER 2 COMMON RESOLUTION
        # -------------------------------------------------------------
        vintage = None
        if match_info and match_info.canonical_vintage:
            vintage = match_info.canonical_vintage
        elif extraction.vintage.is_reliable():
            vintage = extraction.vintage.value

        if not vintage:
            uncertainties.append("Vintage year not visible on label; assuming typical youthful release.")

        # Resolve grapes
        display_grapes = [g.name for g in knowledge.matched_grapes]
        if not display_grapes:
            extracted_g = [g.value for g in extraction.grape_varieties if g.value]
            display_grapes = extracted_g

        if not extraction.grape_varieties and knowledge.matched_appellation:
            uncertainties.append(
                f"Grape varieties not printed on label; derived from legal {knowledge.matched_appellation.classification_system} regulations for {knowledge.matched_appellation.name}."
            )

        # Resolve Appellation / Region / Country
        app_name = (
            knowledge.matched_appellation.name if knowledge.matched_appellation
            else (extraction.appellation.value or None)
        )
        region_name = (
            knowledge.matched_appellation.region if knowledge.matched_appellation
            else (extraction.region.value or None)
        )
        country_name = (
            knowledge.matched_appellation.country if knowledge.matched_appellation
            else (extraction.country.value or None)
        )

        # -------------------------------------------------------------
        # TIER 1 vs TIER 2 HEADLINE & TIER EXPLANATION
        # -------------------------------------------------------------
        if tier == ConfidenceTier.IDENTIFIED_WINE:
            prod = match_info.canonical_producer if match_info else (extraction.producer.value or "")
            wine_title = match_info.canonical_wine_name if match_info else (extraction.wine_name.value or app_name or "")
            v_prefix = f"{vintage} " if vintage else ""
            headline = f"{v_prefix}{prod} {wine_title}".strip()
            tier_exp = f"Verified specific bottling via {match_info.match_source if match_info else 'optical reading'} (confidence: {match_info.match_confidence if match_info else 0.95})."
        else:
            # Identified Style
            v_prefix = f"{vintage} " if vintage else ""
            grapes_summary = f" ({', '.join(display_grapes[:2])})" if display_grapes else ""
            headline = f"{v_prefix}{app_name or region_name or 'European'} Style Wine{grapes_summary}".strip()
            tier_exp = "Appellation and grape style verified, but specific estate bottling could not be matched with high certainty."
            if not extraction.producer.value:
                uncertainties.append("Producer name could not be cleanly extracted from label.")

        # -------------------------------------------------------------
        # DRINKING GUIDE
        # -------------------------------------------------------------
        srv = knowledge.serving
        drinking_guide = DrinkingGuide(
            temperature=TemperatureRange(
                min_c=srv.temperature_min_c,
                max_c=srv.temperature_max_c,
                display_c=f"{srv.temperature_min_c:.0f}–{srv.temperature_max_c:.0f}°C",
                display_f=f"{(srv.temperature_min_c * 9/5) + 32:.0f}–{(srv.temperature_max_c * 9/5) + 32:.0f}°F",
            ),
            glass_type=srv.recommended_glass,
            decanting=DecantingAdvice(
                recommended=srv.decanting_needed,
                duration_minutes=srv.decanting_minutes,
                rationale=srv.decanting_rationale,
            ),
            drink_window=DrinkWindow(
                status="ready_to_drink",
                window_years=srv.typical_drink_window_years,
                rationale=f"Based on typical ageing potential for {app_name or 'this wine style'}.",
            )
        )

        # -------------------------------------------------------------
        # TASTING NOTES (Strictly derived from grape, terroir, winemaking)
        # -------------------------------------------------------------
        avg_acidity = 3
        avg_tannin = 3
        avg_body = 3
        avg_sweetness = 1
        primary_notes: List[FlavorDescriptor] = []

        if knowledge.matched_grapes:
            acids = [g.acidity for g in knowledge.matched_grapes]
            avg_acidity = round(sum(acids) / len(acids))
            
            tanns = [g.tannin for g in knowledge.matched_grapes if g.tannin is not None]
            avg_tannin = round(sum(tanns) / len(tanns)) if tanns else 1

            bodies = [g.body for g in knowledge.matched_grapes]
            avg_body = round(sum(bodies) / len(bodies))

            for g in knowledge.matched_grapes:
                for aroma in g.primary_aromas[:2]:
                    primary_notes.append(FlavorDescriptor(descriptor=aroma, source_factor="grape_variety"))
                for wm in g.winemaking_markers[:1]:
                    primary_notes.append(FlavorDescriptor(descriptor=wm, source_factor="winemaking_ageing"))

        if knowledge.matched_appellation:
            primary_notes.append(
                FlavorDescriptor(
                    descriptor=f"Mineral imprint from {knowledge.matched_appellation.soil_type.split(',')[0]}",
                    source_factor="terroir_soil_climate"
                )
            )

        # Build narrative with strict tier phrasing
        aromas_str = ", ".join([p.descriptor for p in primary_notes[:4]])
        if tier == ConfidenceTier.IDENTIFIED_WINE:
            narrative = (
                f"This {headline} reflects classic enological attributes. "
                f"Driven by {', '.join(display_grapes) if display_grapes else 'its terroir'}, "
                f"it typically exhibits notes of {aromas_str}. "
                f"The palate presents medium-to-firm structure with balanced acidity."
            )
        else:
            narrative = (
                f"Typical for {app_name or 'wines of this region'}: driven by {', '.join(display_grapes) if display_grapes else 'regional grape varieties'}, "
                f"this style typically displays notes of {aromas_str}. "
                f"The structure offers balanced acidity characteristic of the {region_name or 'regional'} climate."
            )

        tasting_notes = TastingNotes(
            structure=StructuralProfile(
                acidity=avg_acidity,
                tannin=avg_tannin if extraction.wine_type.value != WineType.WHITE else None,
                body=avg_body,
                sweetness=avg_sweetness,
            ),
            primary_notes=primary_notes,
            narrative=narrative,
        )

        # -------------------------------------------------------------
        # FOOD PAIRINGS
        # -------------------------------------------------------------
        dishes: List[DishPairing] = []
        for p in knowledge.pairings:
            dishes.append(DishPairing(
                dish=p.dish_name,
                pairing_rule=p.pairing_rule,
                why_it_works=p.rationale,
            ))

        clashes: List[FoodClash] = []
        for c in knowledge.conflicts:
            clashes.append(FoodClash(
                dish_category=c.dish_category,
                conflict_reason=c.chemical_conflict,
            ))

        food_pairings = FoodPairings(
            recommended=dishes,
            avoid=clashes,
        )

        return FinalResponse(
            summary=WineSummary(
                headline=headline,
                tier=tier,
                tier_explanation=tier_exp,
                wine_type=extraction.wine_type.value,
                vintage=vintage,
                country=country_name,
                region=region_name,
                appellation=app_name,
                grapes=display_grapes,
                match_info=match_info,
            ),
            capture_advice=capture_advice,
            drinking_guide=drinking_guide,
            tasting_notes=tasting_notes,
            food_pairings=food_pairings,
            uncertainties=uncertainties,
        )


class GenerationStage:
    """Stage 4 runner: generates candidate explanation and verifies through HallucinationValidator."""

    def __init__(self, validator: Optional[HallucinationValidator] = None):
        self.validator = validator or HallucinationValidator()

    def run(
        self,
        extraction: ExtractionOutput,
        match_info: Optional[MatchInfo],
        knowledge: RetrievedKnowledge,
        photo_count: int = 1,
    ) -> tuple[FinalResponse, float]:
        start = time.perf_counter()

        # Determine Confidence Tier
        if extraction.label_quality == LabelQuality.UNREADABLE or (
            not extraction.producer.value and not extraction.appellation.value and not extraction.grape_varieties
        ):
            tier = ConfidenceTier.UNIDENTIFIED
        elif match_info is not None and match_info.match_confidence >= 0.82:
            tier = ConfidenceTier.IDENTIFIED_WINE
        else:
            tier = ConfidenceTier.IDENTIFIED_STYLE

        # Generate candidate output
        candidate = RuleBasedGenerator.generate(
            extraction=extraction,
            match_info=match_info,
            knowledge=knowledge,
            tier=tier,
            photo_count=photo_count,
        )

        # Validate against hallucination rules
        is_valid, violations, trace_log = self.validator.validate(
            candidate_response=candidate,
            extraction=extraction,
            knowledge=knowledge,
        )

        if not is_valid:
            # Strip invalid claims or downgrade
            candidate.uncertainties.extend([f"Validator correction: {v}" for v in violations])

            if candidate.tasting_notes and candidate.tasting_notes.narrative:
                clean_narrative = candidate.tasting_notes.narrative
                for v in violations:
                    # Strip unsupported grape variety mentions
                    match = re.search(r"Unsupported grape variety '([^']+)'", v)
                    if match:
                        bad_grape = match.group(1)
                        clean_narrative = re.sub(
                            rf"\b{re.escape(bad_grape)}\b(,\s*|\s+and\s+)?",
                            "",
                            clean_narrative,
                            flags=re.IGNORECASE
                        )
                    # Strip unauthorized producer authority claims
                    match_prod = re.search(r"narrative claims producer authority: '([^']+)'", v)
                    if match_prod:
                        bad_phrase = match_prod.group(1)
                        clean_narrative = clean_narrative.replace(bad_phrase, "wines of this style often exhibit")

                # Clean up punctuation and spacing
                clean_narrative = re.sub(r"\s+", " ", clean_narrative).strip()
                clean_narrative = re.sub(r",\s*,", ",", clean_narrative)
                clean_narrative = re.sub(r",\s*\.", ".", clean_narrative)
                candidate.tasting_notes.narrative = clean_narrative

            # Re-verify after sanitation
            is_valid_again, remaining_violations, trace_log = self.validator.validate(
                candidate_response=candidate,
                extraction=extraction,
                knowledge=knowledge,
            )
            if not is_valid_again and candidate.tasting_notes:
                # Ultimate conservative fallback
                app_or_style = (
                    knowledge.matched_appellation.name if knowledge.matched_appellation
                    else (extraction.appellation.value or "regional")
                )
                wtype = extraction.wine_type.value or "classic"
                candidate.tasting_notes.narrative = (
                    f"Typical for {app_or_style}: a {wtype} wine offering balanced enological structure characteristic of its origin."
                )

        candidate.traceability_log = trace_log
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        return candidate, elapsed_ms
