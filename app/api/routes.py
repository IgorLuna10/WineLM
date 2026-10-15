"""FastAPI routes for wine bottle explanation.

Endpoints:
- POST /api/v1/explain: Upload bottle image (multipart/form-data) -> returns FinalResponse
- GET /health: Healthcheck and component status
"""

from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from app.schemas.response import FinalResponse
from app.pipeline.orchestrator import WinePipeline

router = APIRouter()

# Default singleton pipeline instance
_pipeline_instance: Optional[WinePipeline] = None


def get_pipeline() -> WinePipeline:
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = WinePipeline()
    return _pipeline_instance


@router.get("/health", tags=["system"])
async def health_check():
    """Health check verifying pipeline readiness."""
    return {
        "status": "healthy",
        "service": "Panela.Build Wine Explanation Pipeline",
        "phase": 1,
        "features": {
            "hallucination_control": "strict",
            "confidence_tiers": ["identified_wine", "identified_style", "unidentified"],
            "ratings_enabled": False,
            "social_features": False,
        }
    }


@router.post("/api/v1/explain", response_model=FinalResponse, tags=["explanation"])
async def explain_wine(
    files: List[UploadFile] = File(default=[], description="One or more wine bottle images (e.g. front + back label)"),
    file: Optional[UploadFile] = File(default=None, description="Single image upload fallback"),
    additional_context: Optional[str] = Form(default="", description="Optional hint (e.g. 'Front label' or 'Back label')"),
    pipeline: WinePipeline = Depends(get_pipeline),
):
    """Processes 1 or multiple wine bottle photographs through the 4-stage pipeline.
    
    If a single photo is passed, the response includes `capture_advice` indicating
    whether that photo was sufficient or if a second photo (e.g. back label) is recommended.
    """
    upload_list: List[UploadFile] = []
    if files:
        upload_list.extend(files)
    if file:
        upload_list.append(file)

    if not upload_list:
        raise HTTPException(status_code=400, detail="At least one image file must be uploaded.")

    image_bytes_list: List[bytes] = []
    for f in upload_list:
        if not f.content_type or not f.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"File '{f.filename}' must be a valid image.")
        b = await f.read()
        if len(b) == 0:
            raise HTTPException(status_code=400, detail=f"Uploaded file '{f.filename}' is empty.")
        image_bytes_list.append(b)

    try:
        response = await pipeline.process_images(
            images=image_bytes_list,
            additional_context=additional_context or "",
        )
        return response
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline processing failed: {str(exc)}")
