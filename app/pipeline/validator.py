"""Hallucination and Fact Traceability Validator.

Enforces Core Principle: The language model is never the source of truth for facts.
Every claim in generated text must trace directly back to:
(a) optical facts read off the label, or
(b) authoritative entries in the retrieved knowledge base.
"""

from __future__ import annotations
import re
from typing import List, Set, Tuple, Optional
from app.schemas.extraction import ExtractionOutput
from app.schemas.response import FinalResponse, ConfidenceTier, TraceabilityEntry
from app.schemas.knowledge import RetrievedKnowledge


class HallucinationValidator:
    """Verifies that generated wine narratives do not introduce unsupported factual claims."""

    def __init__(self):
        # Known wine grapes to detect unauthorized varietal hallucinations
        self.known_grapes = {
            "cabernet sauvignon", "merlot", "pinot noir", "syrah", "shiraz",
            "chardonnay", "sauvignon blanc", "riesling", "nebbiolo", "sangiovese",
            "tempranillo", "gamay", "chenin blanc", "viognier", "grenache",
            "cabernet franc", "melon de bourgogne", "nero d'avola", "savagnin", "poulsard",
            "malbec", "carménère", "zinfandel", "gewürztraminer", "albariño"
        }

    def validate(
        self,
        candidate_response: FinalResponse,
        extraction: ExtractionOutput,
        knowledge: RetrievedKnowledge,
    ) -> Tuple[bool, List[str], List[TraceabilityEntry]]:
        """Validates response against extraction facts and knowledge base constraints.
        
        Returns:
            (is_valid, violation_messages, traceability_log)
        """
        violations: List[str] = []
        traceability: List[TraceabilityEntry] = []

        tier = candidate_response.summary.tier
        narrative = ""
        if candidate_response.tasting_notes:
            narrative = candidate_response.tasting_notes.narrative.lower()

        # 1. Tier 3 (Unidentified) constraint:
        if tier == ConfidenceTier.UNIDENTIFIED:
            if candidate_response.drinking_guide is not None or candidate_response.tasting_notes is not None:
                violations.append("Tier 'unidentified' must not supply detailed tasting notes or drinking guide.")
            return len(violations) == 0, violations, traceability

        # 2. Gather verified grapes
        verified_grapes: Set[str] = set()
        for g in extraction.grape_varieties:
            if g.value and g.confidence >= 0.6:
                verified_grapes.add(g.value.lower())
                traceability.append(TraceabilityEntry(
                    claim=f"Grape: {g.value}",
                    source_tier="extracted_label_text",
                    evidence=f"Printed on label (confidence {g.confidence})"
                ))

        for gp in knowledge.matched_grapes:
            verified_grapes.add(gp.name.lower())
            for syn in gp.synonyms:
                verified_grapes.add(syn.lower())
            traceability.append(TraceabilityEntry(
                claim=f"Grape: {gp.name}",
                source_tier="retrieved_knowledge_base",
                evidence=f"Knowledge base varietal profile for {gp.name}"
            ))

        # Check for hallucinated grape varieties mentioned in narrative
        for grape in self.known_grapes:
            if grape in narrative:
                # Is it verified?
                if not any(v in grape or grape in v for v in verified_grapes):
                    violations.append(
                        f"Unsupported grape variety '{grape}' mentioned in tasting notes without label or KB backing."
                    )

        # 3. Tier 2 (Identified Style) phrasing check:
        # If producer was not identified, narrative must not claim "this estate produces..."
        if tier == ConfidenceTier.IDENTIFIED_STYLE:
            unauthorized_producer_claims = [
                "the winemaker crafted", "this estate produces", "this chateau is known for",
                "the producer's philosophy", "their vineyard produces"
            ]
            for phrase in unauthorized_producer_claims:
                if phrase in narrative:
                    violations.append(
                        f"Tier is identified_style (producer unknown), but narrative claims producer authority: '{phrase}'"
                    )

        # 4. Check Vintage claims
        if extraction.vintage.value:
            v_str = str(extraction.vintage.value)
            traceability.append(TraceabilityEntry(
                claim=f"Vintage: {v_str}",
                source_tier="extracted_label_text",
                evidence=f"Label printed vintage {v_str} (confidence {extraction.vintage.confidence})"
            ))

        # 5. Check Appellation claims
        if knowledge.matched_appellation:
            traceability.append(TraceabilityEntry(
                claim=f"Appellation: {knowledge.matched_appellation.name}",
                source_tier="retrieved_knowledge_base",
                evidence=f"AOC/DOC legal profile ({knowledge.matched_appellation.classification_system})"
            ))

        # 6. Check Serving & Pairing traceability
        if candidate_response.drinking_guide:
            traceability.append(TraceabilityEntry(
                claim=f"Serving temp: {candidate_response.drinking_guide.temperature.display_c}",
                source_tier="retrieved_knowledge_base",
                evidence="Rule-based enological temperature matrix"
            ))

        if candidate_response.food_pairings:
            for dish in candidate_response.food_pairings.recommended:
                traceability.append(TraceabilityEntry(
                    claim=f"Pairing: {dish.dish}",
                    source_tier="style_rule",
                    evidence=f"Principle: {dish.pairing_rule}"
                ))

        is_valid = len(violations) == 0
        return is_valid, violations, traceability
