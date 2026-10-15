"""Stage 3: Knowledge Layer Retrieval.

Retrieves verified viticultural, enological, serving, and food-pairing data
from the curated, versioned knowledge base.
All facts supplied to Stage 4 generation originate here.
"""

from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from rapidfuzz import fuzz
from app.schemas.extraction import ExtractionOutput, WineType
from app.schemas.response import MatchInfo
from app.schemas.knowledge import (
    GrapeProfile,
    AppellationProfile,
    ServingGuideline,
    PairingRecommendation,
    PairingConflict,
    RetrievedKnowledge,
)


class KnowledgeBaseRepository:
    """Loads and indexes the versioned knowledge base files."""

    def __init__(self, kb_dir: Optional[Path] = None):
        if kb_dir is None:
            kb_dir = Path(__file__).resolve().parent.parent / "knowledge_base"
        
        self.grapes: Dict[str, GrapeProfile] = {}
        self.appellations: Dict[str, AppellationProfile] = {}
        self.serving_profiles: Dict[str, ServingGuideline] = {}
        self.pairing_rules: List[Dict[str, Any]] = []

        self._load(kb_dir)

    def _load(self, kb_dir: Path):
        # Grapes
        grapes_file = kb_dir / "grapes.json"
        if grapes_file.exists():
            with open(grapes_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("grapes", []):
                    profile = GrapeProfile.model_validate(item)
                    self.grapes[profile.name.lower()] = profile
                    for syn in profile.synonyms:
                        self.grapes[syn.lower()] = profile

        # Appellations
        app_file = kb_dir / "appellations.json"
        if app_file.exists():
            with open(app_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("appellations", []):
                    profile = AppellationProfile.model_validate(item)
                    self.appellations[profile.name.lower()] = profile

        # Serving rules
        srv_file = kb_dir / "serving_rules.json"
        if srv_file.exists():
            with open(srv_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for key, val in data.get("serving_profiles", {}).items():
                    self.serving_profiles[key] = ServingGuideline.model_validate(val)

        # Pairing matrix
        pair_file = kb_dir / "pairing_matrix.json"
        if pair_file.exists():
            with open(pair_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.pairing_rules = data.get("structural_rules", [])

    def find_appellation(self, name: str) -> Optional[AppellationProfile]:
        if not name:
            return None
        clean = name.lower().strip()
        if clean in self.appellations:
            return self.appellations[clean]
        
        # Fuzzy match appellations
        for app_name, profile in self.appellations.items():
            if fuzz.ratio(clean, app_name) >= 80:
                return profile
        return None

    def find_grape(self, name: str) -> Optional[GrapeProfile]:
        if not name:
            return None
        clean = name.lower().strip()
        if clean in self.grapes:
            return self.grapes[clean]
        
        for grape_name, profile in self.grapes.items():
            if fuzz.ratio(clean, grape_name) >= 80:
                return profile
        return None


class KnowledgeStage:
    """Stage 3 runner: pulls authoritative viticultural and enological rules."""

    def __init__(self, repo: Optional[KnowledgeBaseRepository] = None):
        self.repo = repo or KnowledgeBaseRepository()

    def run(
        self,
        extraction: ExtractionOutput,
        match_info: Optional[MatchInfo],
        reference_data: Optional[Dict[str, Any]],
    ) -> tuple[RetrievedKnowledge, float]:
        start = time.perf_counter()

        matched_appellation: Optional[AppellationProfile] = None
        matched_grapes: List[GrapeProfile] = []
        appellation_candidate = ""

        # 1. Determine Appellation
        if reference_data and reference_data.get("appellation"):
            appellation_candidate = reference_data["appellation"]
        elif extraction.appellation.is_reliable(threshold=0.6):
            appellation_candidate = extraction.appellation.value or ""

        if appellation_candidate:
            matched_appellation = self.repo.find_appellation(appellation_candidate)

        # 2. Determine Wine Type
        wine_type = None
        if reference_data and reference_data.get("wine_type"):
            wine_type = reference_data["wine_type"]
        elif extraction.wine_type.value:
            wine_type = extraction.wine_type.value.value if hasattr(extraction.wine_type.value, "value") else str(extraction.wine_type.value)

        # 3. Determine Grape Varieties
        grape_names: List[str] = []
        if reference_data and reference_data.get("grapes"):
            grape_names = reference_data["grapes"]
        else:
            # Check explicitly extracted grapes
            extracted_valid_grapes = [
                g.value for g in extraction.grape_varieties
                if g.value and g.confidence >= 0.6
            ]
            if extracted_valid_grapes:
                grape_names = extracted_valid_grapes
            elif matched_appellation and matched_appellation.authorized_grapes:
                # Appellation rules provide authorized grape varieties
                if wine_type in ("red", "white"):
                    filtered_grapes = []
                    for cg in matched_appellation.authorized_grapes:
                        gp = self.repo.find_grape(cg)
                        if gp:
                            gp_type = gp.default_wine_type.value if hasattr(gp.default_wine_type, "value") else str(gp.default_wine_type)
                            if gp_type == wine_type:
                                filtered_grapes.append(cg)
                        else:
                            filtered_grapes.append(cg)
                    grape_names = filtered_grapes if filtered_grapes else matched_appellation.authorized_grapes
                else:
                    grape_names = matched_appellation.authorized_grapes

        for gname in grape_names:
            profile = self.repo.find_grape(gname)
            if profile and profile not in matched_grapes:
                matched_grapes.append(profile)

        # Classify serving profile key
        profile_key = "red_full_bodied"
        if wine_type == "white":
            # Check if oaked chardonnay or crisp white
            is_oaked_chardonnay = any(g.name == "Chardonnay" for g in matched_grapes) and (
                "fûts" in (extraction.back_label_text.value or "").lower() or
                "oak" in (extraction.back_label_text.value or "").lower()
            )
            profile_key = "white_oaked_full" if is_oaked_chardonnay else "white_crisp"
        elif wine_type == "sparkling":
            profile_key = "sparkling_traditional"
        elif wine_type == "rose":
            profile_key = "rose_dry"
        else:
            # Red wine: check body / tannin
            avg_tannin = 3
            if matched_grapes:
                tannins = [g.tannin for g in matched_grapes if g.tannin is not None]
                if tannins:
                    avg_tannin = sum(tannins) / len(tannins)
            profile_key = "red_full_bodied" if avg_tannin >= 3.5 else "red_light_medium"

        serving = self.repo.serving_profiles.get(
            profile_key,
            ServingGuideline(
                temperature_min_c=14.0,
                temperature_max_c=16.0,
                recommended_glass="Universal wine glass",
                decanting_needed=False,
                decanting_rationale="Serve at cellar temperature in a standard glass.",
                typical_drink_window_years="2 to 5 years from vintage"
            )
        )

        # 4. Resolve Food Pairings based on chemistry triggers
        pairings: List[PairingRecommendation] = []
        conflicts: List[PairingConflict] = []

        active_triggers = []
        if profile_key == "red_full_bodied":
            active_triggers.append("high_tannin")
        elif profile_key in ("white_crisp", "white_oaked_full"):
            active_triggers.append("high_acidity_white")
        elif profile_key == "red_light_medium":
            active_triggers.append("light_medium_red")

        for rule in self.repo.pairing_rules:
            if rule.get("trigger") in active_triggers:
                for rec in rule.get("recommended_dishes", []):
                    pairings.append(PairingRecommendation.model_validate(rec))
                for c in rule.get("conflicts", []):
                    conflicts.append(PairingConflict.model_validate(c))

        elapsed_ms = (time.perf_counter() - start) * 1000.0

        retrieved = RetrievedKnowledge(
            matched_appellation=matched_appellation,
            matched_grapes=matched_grapes,
            serving=serving,
            pairings=pairings[:3],
            conflicts=conflicts[:2],
            general_style_notes=[f"Serving archetype: {profile_key}"]
        )

        return retrieved, elapsed_ms
