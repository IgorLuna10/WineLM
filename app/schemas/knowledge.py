"""Curated knowledge base entity schemas.

These schemas define the factual building blocks retrieved during Stage 3.
All LLM explanations must be strictly grounded in instances of these models.
"""

from __future__ import annotations
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from app.schemas.extraction import WineType


class GrapeProfile(BaseModel):
    """Authoritative sensory and viticultural profile of a grape variety."""
    name: str
    synonyms: List[str] = Field(default_factory=list)
    default_wine_type: WineType
    acidity: int = Field(ge=1, le=5, description="1 (very low) to 5 (very high)")
    tannin: Optional[int] = Field(default=None, ge=1, le=5, description="1 to 5 for reds; null/1 for whites")
    body: int = Field(ge=1, le=5, description="1 (light) to 5 (full)")
    sweetness: int = Field(ge=1, le=5, description="1 (bone dry) to 5 (dessert)")
    primary_aromas: List[str] = Field(description="Typical fruit/herbal/spice notes derived from varietal chemistry")
    winemaking_markers: List[str] = Field(
        default_factory=list,
        description="Descriptors arising from common vinification methods (e.g. malolactic, oak aging, lees stirring)"
    )


class AppellationProfile(BaseModel):
    """Authoritative terroir and legal guidelines for a protected designation."""
    name: str
    country: str
    region: str
    classification_system: str = Field(description="e.g. AOC, DOCG, DO, AVA")
    authorized_grapes: List[str]
    climate: str
    soil_type: str
    typical_styles: List[str]
    mandatory_ageing_months: Optional[int] = None


class ServingGuideline(BaseModel):
    """Serving recommendations based on wine style and structural attributes."""
    temperature_min_c: float
    temperature_max_c: float
    recommended_glass: str
    decanting_needed: bool
    decanting_minutes: Optional[int] = None
    decanting_rationale: str
    typical_drink_window_years: Optional[str] = None


class PairingRecommendation(BaseModel):
    """Rule-based food pairing recommendation based on structural balance."""
    dish_name: str
    category: str
    pairing_rule: str
    rationale: str


class PairingConflict(BaseModel):
    """Clash warning based on wine chemistry (e.g. high tannins clashing with fish oils)."""
    dish_category: str
    chemical_conflict: str


class RetrievedKnowledge(BaseModel):
    """Aggregated verified factual payload passed into Stage 4 (Text Generation)."""
    matched_appellation: Optional[AppellationProfile] = None
    matched_grapes: List[GrapeProfile] = Field(default_factory=list)
    serving: ServingGuideline
    pairings: List[PairingRecommendation] = Field(default_factory=list)
    conflicts: List[PairingConflict] = Field(default_factory=list)
    general_style_notes: List[str] = Field(default_factory=list)
