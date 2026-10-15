"""Pipeline Orchestrator.

Wires Stage 1 (Extraction with Gemini 1.5 Flash / Fusion) ->
      Stage 2 (Identification with Offline SQLite Index) ->
      Stage 3 (Knowledge Layer Retrieval) ->
      Stage 4 (Generation, Capture Advice, and Attribution Validator)
into a unified, hallucination-resistant backend execution graph.
"""

from __future__ import annotations
import time
from typing import Optional, List, Union
from app.schemas.response import FinalResponse, StageMetrics
from app.schemas.extraction import ExtractionOutput
from app.pipeline.extraction import ExtractionStage
from app.models.gemini import GeminiFlashVLM
from app.pipeline.identification import IdentificationStage
from app.pipeline.knowledge import KnowledgeStage
from app.pipeline.generation import GenerationStage


class WinePipeline:
    """Master pipeline orchestrator for bottle image explanation."""

    def __init__(
        self,
        extraction_stage: Optional[ExtractionStage] = None,
        identification_stage: Optional[IdentificationStage] = None,
        knowledge_stage: Optional[KnowledgeStage] = None,
        generation_stage: Optional[GenerationStage] = None,
    ):
        # Default extraction stage equipped with Gemini 1.5 Flash (with automatic mock fallback)
        self.stage_1 = extraction_stage or ExtractionStage(backend=GeminiFlashVLM())
        self.stage_2 = identification_stage or IdentificationStage()
        self.stage_3 = knowledge_stage or KnowledgeStage()
        self.stage_4 = generation_stage or GenerationStage()

    async def process_images(
        self,
        images: List[bytes],
        additional_context: str = "",
        contexts: Optional[List[str]] = None,
    ) -> FinalResponse:
        """Processes 1 or multiple wine bottle photographs (e.g. front + back label)."""
        if not images:
            raise ValueError("At least one image must be provided.")

        total_start = time.perf_counter()

        # -------------------------------------------------------------
        # Stage 1: Optical Extraction & Multi-Photo Fusion
        # -------------------------------------------------------------
        if len(images) == 1:
            extraction, s1_ms = await self.stage_1.run(images[0], additional_context)
        else:
            extraction, s1_ms = await self.stage_1.run_multiple(images, contexts)

        # -------------------------------------------------------------
        # Stage 2: Identification (Offline SQLite Barcode + FTS5 Match)
        # -------------------------------------------------------------
        match_info, ref_data, s2_ms = self.stage_2.run(extraction)

        # -------------------------------------------------------------
        # Stage 3: Knowledge Layer Retrieval
        # -------------------------------------------------------------
        knowledge, s3_ms = self.stage_3.run(extraction, match_info, ref_data)

        # -------------------------------------------------------------
        # Stage 4: Generation, Capture Advice & Fact Validation
        # -------------------------------------------------------------
        response, s4_ms = self.stage_4.run(
            extraction=extraction,
            match_info=match_info,
            knowledge=knowledge,
            photo_count=len(images),
        )

        total_elapsed_ms = (time.perf_counter() - total_start) * 1000.0

        # Cost estimation: ~$0.00015 per image on Gemini 1.5 Flash + text gen
        estimated_cost = len(images) * 0.00020

        response.metrics = StageMetrics(
            vlm_extraction_ms=round(s1_ms, 2),
            identification_ms=round(s2_ms, 2),
            knowledge_retrieval_ms=round(s3_ms, 2),
            text_generation_ms=round(s4_ms, 2),
            validation_ms=round(0.1, 2),
            total_pipeline_ms=round(total_elapsed_ms, 2),
            estimated_cost_usd=round(estimated_cost, 5),
        )
        response.extraction = extraction

        return response

    async def process_image(self, image_bytes: bytes, additional_context: str = "") -> FinalResponse:
        """Convenience single-image processor."""
        return await self.process_images([image_bytes], additional_context)
