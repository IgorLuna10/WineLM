"""Final API response schemas for Panela.Build wine explanation.

Structured, hallucination-resistant contract supporting three confidence tiers:
- 'identified_wine': Producer, wine, vintage matched.
- 'identified_style': Grape/region known, specific bottling unmatched.
- 'unidentified': Label illegible or insufficient data.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.extraction import WineType, ExtractionOutput


class ConfidenceTier(str, Enum):
    IDENTIFIED_WINE = "identified_wine"
    IDENTIFIED_STYLE = "identified_style"
    UNIDENTIFIED = "unidentified"


class MatchInfo(BaseModel):
    """Details of the reference dataset or barcode lookup match."""
    matched_id: Optional[str] = None
    canonical_producer: Optional[str] = None
    canonical_wine_name: Optional[str] = None
    canonical_vintage: Optional[int] = None
    match_source: str = Field(description="e.g. 'ean_barcode_lookup', 'fuzzy_reference_match', 'none'")
    match_confidence: float = Field(ge=0.0, le=1.0)


class WineSummary(BaseModel):
    """Core headline and identification rationale."""
    headline: str = Field(
        description="Clean, factual title (e.g. '2019 Domaine Faiveley Mercurey' or 'Dry French White (Chardonnay Style)')."
    )
    tier: ConfidenceTier
    tier_explanation: str = Field(
        description="Transparent explanation of how and why this confidence tier was assigned."
    )
    wine_type: Optional[WineType] = None
    vintage: Optional[int] = None
    country: Optional[str] = None
    region: Optional[str] = None
    appellation: Optional[str] = None
    grapes: List[str] = Field(default_factory=list)
    match_info: Optional[MatchInfo] = None


class TemperatureRange(BaseModel):
    min_c: float
    max_c: float
    display_c: str
    display_f: str


class DecantingAdvice(BaseModel):
    recommended: bool
    duration_minutes: Optional[int] = None
    rationale: str


class DrinkWindow(BaseModel):
    status: str = Field(description="'ready_to_drink', 'can_age', 'past_peak', or 'unspecified'")
    window_years: Optional[str] = None
    rationale: str


class DrinkingGuide(BaseModel):
    """How to drink it: serving temp, glass, decanting, drink window."""
    temperature: TemperatureRange
    glass_type: str
    decanting: DecantingAdvice
    drink_window: DrinkWindow


class StructuralProfile(BaseModel):
    """Objective 1-5 structural indicators (derived from grape and appellation data)."""
    acidity: int = Field(ge=1, le=5, description="1 (low) to 5 (high)")
    tannin: Optional[int] = Field(default=None, ge=1, le=5, description="1 (supple/none) to 5 (heavy)")
    body: int = Field(ge=1, le=5, description="1 (light) to 5 (full)")
    sweetness: int = Field(ge=1, le=5, description="1 (bone dry) to 5 (sweet)")


class FlavorDescriptor(BaseModel):
    descriptor: str
    source_factor: str = Field(description="'grape_variety', 'terroir_soil_climate', 'winemaking_ageing', 'style_typical'")


class TastingNotes(BaseModel):
    """Tasting notes strictly grounded in grape, terroir, and vinification facts."""
    structure: StructuralProfile
    primary_notes: List[FlavorDescriptor]
    narrative: str = Field(
        description="Factual, educational explanation strictly restricted to confirmed facts or clearly qualified style tendencies."
    )


class DishPairing(BaseModel):
    dish: str
    pairing_rule: str
    why_it_works: str


class FoodClash(BaseModel):
    dish_category: str
    conflict_reason: str


class FoodPairings(BaseModel):
    """Chemical and sensory food pairing recommendations."""
    recommended: List[DishPairing]
    avoid: List[FoodClash]


class TraceabilityEntry(BaseModel):
    """Audit log verifying the factual foundation of each statement."""
    claim: str
    source_tier: str = Field(description="'extracted_label_text', 'retrieved_knowledge_base', or 'style_rule'")
    evidence: str


class StageMetrics(BaseModel):
    vlm_extraction_ms: float = 0.0
    identification_ms: float = 0.0
    knowledge_retrieval_ms: float = 0.0
    text_generation_ms: float = 0.0
    validation_ms: float = 0.0
    total_pipeline_ms: float = 0.0
    estimated_cost_usd: float = 0.0


class CaptureAdvice(BaseModel):
    """Analyzes photo completeness and instructs mobile client whether a second shot is needed."""
    needs_second_photo: bool = Field(
        default=False,
        description="True if key identifying details (vintage, estate, barcode) were missing or ambiguous."
    )
    suggested_label_type: Optional[str] = Field(
        default=None,
        description="'back_label' (for barcode/ABV), 'front_label' (for producer/AOC), or 'clearer_shot' (glare/blur)."
    )
    reason: Optional[str] = Field(
        default=None,
        description="Technical reason why a follow-up photo would improve confidence."
    )
    user_prompt_message: Optional[str] = Field(
        default=None,
        description="Calm, user-facing prompt (e.g. 'Tip: Snapping the back label will confirm the exact vintage and estate.')."
    )


class FinalResponse(BaseModel):
    """Complete user-facing response payload for Phase 1 backend."""
    summary: WineSummary
    capture_advice: CaptureAdvice = Field(default_factory=CaptureAdvice)
    drinking_guide: Optional[DrinkingGuide] = None
    tasting_notes: Optional[TastingNotes] = None
    food_pairings: Optional[FoodPairings] = None
    uncertainties: List[str] = Field(
        default_factory=list,
        description="Explicit list of missing, obscured, or unverifiable facts."
    )
    traceability_log: List[TraceabilityEntry] = Field(default_factory=list)
    metrics: StageMetrics = Field(default_factory=StageMetrics)
    extraction: Optional[ExtractionOutput] = Field(
        default=None,
        description="Raw structured extraction facts from Stage 1."
    )
