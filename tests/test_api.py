"""Test FastAPI HTTP endpoints."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["features"]["ratings_enabled"] is False
    assert data["features"]["social_features"] is False


def test_explain_endpoint_with_image():
    with open("tests/fixtures/sample_bottle.jpg", "rb") as f:
        img_bytes = f.read()

    response = client.post(
        "/api/v1/explain",
        files={"file": ("sample_bottle.jpg", img_bytes, "image/jpeg")},
        data={"additional_context": "Front label"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "summary" in body
    assert body["summary"]["tier"] == "identified_wine"
    assert "drinking_guide" in body
    assert "tasting_notes" in body
    assert "food_pairings" in body
    assert "uncertainties" in body
    assert "traceability_log" in body
    assert "capture_advice" in body
    assert "metrics" in body


def test_explain_endpoint_with_multiple_images():
    with open("tests/fixtures/sample_bottle.jpg", "rb") as f:
        img_bytes = f.read()

    # Pass 2 images simultaneously (representing front + back label)
    response = client.post(
        "/api/v1/explain",
        files=[
            ("files", ("front.jpg", img_bytes, "image/jpeg")),
            ("files", ("back.jpg", img_bytes, "image/jpeg")),
        ],
        data={"additional_context": "Front and back labels"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["tier"] == "identified_wine"
    assert body["capture_advice"]["needs_second_photo"] is False
