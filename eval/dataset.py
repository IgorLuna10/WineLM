"""Evaluation dataset schema and loaders.

Supports difficulty tags:
- 'glare': direct light reflection on bottle glass
- 'curved': perspective distortion from cylinder shape
- 'back_label': barcode and fine print present
- 'multiple_bottles': clutter / adjacent bottles in frame
- 'obscure_wine': artisanal or rare cave bottle not in standard supermarket databases
"""

from __future__ import annotations
import json
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DifficultyTag(str, Enum):
    GLARE = "glare"
    CURVED = "curved"
    BACK_LABEL = "back_label"
    MULTIPLE_BOTTLES = "multiple_bottles"
    OBSCURE_WINE = "obscure_wine"
    LOW_LIGHT = "low_light"
    STANDARD = "standard"


class GroundTruthExtraction(BaseModel):
    producer: Optional[str] = None
    wine_name: Optional[str] = None
    appellation: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    vintage: Optional[int] = None
    abv: Optional[float] = None
    wine_type: Optional[str] = None
    grape_varieties: List[str] = Field(default_factory=list)
    barcode: Optional[str] = None


class BenchmarkCase(BaseModel):
    case_id: str
    image_path: Optional[str] = None
    image_paths: List[str] = Field(default_factory=list)
    difficulty_tags: List[DifficultyTag]
    split: str = "synthetic"  # 'synthetic', 'dev', 'test'
    ground_truth_extraction: GroundTruthExtraction
    expected_tier: str  # 'identified_wine', 'identified_style', 'unidentified'
    expected_canonical_id: Optional[str] = None
    verified_claims: List[str] = Field(
        default_factory=list,
        description="List of verified facts that are acceptable to mention."
    )

    def model_post_init(self, __context: Any) -> None:
        if not self.image_paths and self.image_path:
            self.image_paths = [self.image_path]
        elif self.image_paths and not self.image_path:
            self.image_path = self.image_paths[0]


def load_benchmark_suite(file_path: Optional[Path] = None) -> List[BenchmarkCase]:
    if file_path is None:
        file_path = Path(__file__).resolve().parent / "data" / "benchmark_cases.json"
    
    if not file_path.exists():
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return [BenchmarkCase.model_validate(c) for c in data.get("cases", [])]
