"""Extraction schemas for VLM label parsing.

Every extracted field is explicitly wrapped with a confidence score (0.0 to 1.0)
and an optional source_text showing the exact string snippet detected on the bottle.
Missing fields MUST be null with 0.0 confidence, never inferred.
"""

from __future__ import annotations
from enum import Enum
from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field, model_validator

T = TypeVar("T")


class WineType(str, Enum):
    RED = "red"
    WHITE = "white"
    ROSE = "rose"
    SPARKLING = "sparkling"
    SWEET = "sweet"
    FORTIFIED = "fortified"


class LabelQuality(str, Enum):
    HIGH = "high"          # Clear, fully legible, flat or well-lit
    MEDIUM = "medium"      # Moderate glare, curvature, or small text
    LOW = "low"            # Heavy glare, severe occlusion, damaged label
    UNREADABLE = "unreadable"  # Cannot extract meaningful wine data


class ConfidenceField(BaseModel, Generic[T]):
    """Wraps an extracted value with its calibration score and raw evidence."""
    value: Optional[T] = Field(
        default=None,
        description="The extracted value, or null if absent/unreadable."
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence between 0.0 (absent/pure guess) and 1.0 (crystal clear)."
    )
    source_text: Optional[str] = Field(
        default=None,
        description="Verbatim text fragment detected on the bottle that supports this field."
    )

    def is_reliable(self, threshold: float = 0.6) -> bool:
        """Helper to test if field has non-null value above confidence threshold."""
        return self.value is not None and self.confidence >= threshold


class ExtractionOutput(BaseModel):
    """Strict structured JSON returned by Stage 1 (VLM Extraction)."""

    @model_validator(mode="before")
    @classmethod
    def normalize_vlm_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        confidence_scalar_fields = [
            "producer", "wine_name", "cuvee", "appellation", "region", "country",
            "vintage", "abv", "volume_ml", "wine_type", "barcode", "back_label_text"
        ]

        def _to_confidence_dict(val: Any) -> Any:
            if isinstance(val, ConfidenceField):
                return val
            if val is None:
                return {"value": None, "confidence": 0.0, "source_text": None}
            if isinstance(val, dict):
                return val
            return {"value": val, "confidence": 0.9, "source_text": str(val)}

        for f in confidence_scalar_fields:
            if f in data:
                data[f] = _to_confidence_dict(data[f])

        for list_f in ["classifications", "grape_varieties"]:
            if list_f in data and isinstance(data[list_f], list):
                data[list_f] = [_to_confidence_dict(item) for item in data[list_f]]

        return data

    producer: ConfidenceField[str] = Field(
        default_factory=ConfidenceField,
        description="Winery, estate, château, or domaine name (e.g. 'Château Margaux', 'Domaine Leflaive')."
    )
    wine_name: ConfidenceField[str] = Field(
        default_factory=ConfidenceField,
        description="Commercial name of the wine if distinct from producer (e.g. 'Le Volte', 'Sassicaia')."
    )
    cuvee: ConfidenceField[str] = Field(
        default_factory=ConfidenceField,
        description="Specific cuvée, plot, or parcel name (e.g. 'Les Pucelles', 'Vieilles Vignes')."
    )
    grape_varieties: List[ConfidenceField[str]] = Field(
        default_factory=list,
        description="Explicitly printed grape varieties. ONLY include if literally printed on label. DO NOT guess."
    )
    appellation: ConfidenceField[str] = Field(
        default_factory=ConfidenceField,
        description="Geographical indication or appellation (e.g. 'Bordeaux Superieur', 'Chablis Premier Cru', 'Rioja')."
    )
    region: ConfidenceField[str] = Field(
        default_factory=ConfidenceField,
        description="Broad macro-region (e.g. 'Bordeaux', 'Bourgogne', 'Toscana', 'Mendoza')."
    )
    country: ConfidenceField[str] = Field(
        default_factory=ConfidenceField,
        description="Country of origin (e.g. 'France', 'Italy', 'Spain')."
    )
    vintage: ConfidenceField[int] = Field(
        default_factory=ConfidenceField,
        description="Harvest year (e.g. 2020). Null if non-vintage (NV) or obscured."
    )
    abv: ConfidenceField[float] = Field(
        default_factory=ConfidenceField,
        description="Alcohol by volume percentage (e.g. 13.5). Null if not visible."
    )
    volume_ml: ConfidenceField[int] = Field(
        default_factory=ConfidenceField,
        description="Bottle volume in milliliters (e.g. 750, 1500). Null if not visible."
    )
    wine_type: ConfidenceField[WineType] = Field(
        default_factory=ConfidenceField,
        description="Wine category: red, white, rose, sparkling, sweet, fortified."
    )
    classifications: List[ConfidenceField[str]] = Field(
        default_factory=list,
        description="Official classification terms visible on label (e.g. 'AOC', 'AOP', 'DOCG', 'Grand Cru', 'Reserva', 'Crianza', 'IGP')."
    )
    barcode: ConfidenceField[str] = Field(
        default_factory=ConfidenceField,
        description="EAN-13 or UPC barcode digits if visible on front or back label."
    )
    back_label_text: ConfidenceField[str] = Field(
        default_factory=ConfidenceField,
        description="Verbatim winemaking, barrel ageing, or soil notes found on label text."
    )
    label_quality: LabelQuality = Field(
        default=LabelQuality.MEDIUM,
        description="Overall legibility assessment based on angle, curve, lighting, glare."
    )
    raw_ocr_tokens: List[str] = Field(
        default_factory=list,
        description="Raw recognized text fragments for fuzzy match backup."
    )
    uncertainties: List[str] = Field(
        default_factory=list,
        description="Observations regarding missing, cut-off, or ambiguous text."
    )
