"""Gemini VLM Integration with Vertex AI / AI Studio Support.

Targets active Gemini multimodal flash models via Google AI Studio Developer API:
- Primary: gemini-3.7-flash (active tier, fast ~6s response)
- Fallbacks: gemini-3.5-flash, gemini-3.1-flash-lite, gemini-3.8-flash
Configures thinkingBudget: 0 for fast response and structured JSON extraction.
Features exponential backoff retry on transient HTTP 503/429 spikes, and intelligent
fallback when a specific model's daily quota is exhausted.
Falls back safely to mock backend when GEMINI_API_KEY is not configured.
"""

from __future__ import annotations
import asyncio
import base64
import os
from pathlib import Path
from typing import Optional, List
import httpx
from app.pipeline.extraction import VLMBackend, MockVLMBackend

# Primary model requested
DEFAULT_MODEL = "gemini-3.7-flash"
FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-flash-latest"]
DEFAULT_PROJECT = "738731032656"
DEFAULT_LOCATION = "us-central1"


def get_mime_type(image_bytes: bytes) -> str:
    """Detect MIME type from image magic bytes."""
    if image_bytes.startswith(b"\x89PNG"):
        return "image/png"
    if image_bytes.startswith(b"RIFF") and b"WEBP" in image_bytes[:16]:
        return "image/webp"
    return "image/jpeg"


class GeminiFlashVLM(VLMBackend):
    """Production Gemini Flash client via async REST."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        project_id: Optional[str] = None,
        location: str = DEFAULT_LOCATION,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT", DEFAULT_PROJECT)
        self.location = location
        self.fallback = MockVLMBackend()

    async def extract_label(self, image_bytes: bytes, prompt: str, system_prompt: str) -> str:
        if not self.api_key:
            # Fallback for local offline tests and development without API key
            return await self.fallback.extract_label(image_bytes, prompt, system_prompt)

        mime_type = get_mime_type(image_bytes)
        b64_data = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_data,
                            }
                        },
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0,
                "thinkingConfig": {
                    "thinkingBudget": 0
                }
            }
        }

        # Candidate models to try in order
        candidate_models = list(dict.fromkeys([self.model] + FALLBACK_MODELS))

        async with httpx.AsyncClient(timeout=60.0) as client:
            last_error: Optional[Exception] = None

            for model_id in candidate_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent"
                headers = {
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key,
                }

                max_retries = 3
                for attempt in range(1, max_retries + 1):
                    try:
                        resp = await client.post(url, json=payload, headers=headers)
                        if resp.status_code == 200:
                            data = resp.json()
                            candidates = data.get("candidates", [])
                            if candidates and "content" in candidates[0]:
                                parts = candidates[0]["content"].get("parts", [])
                                if parts and "text" in parts[0]:
                                    return parts[0]["text"]
                            return resp.text
                        elif resp.status_code == 404:
                            # Model not found on this endpoint, try next model
                            break
                        elif resp.status_code in (503, 429):
                            wait_s = float(attempt * 4)
                            if resp.status_code == 429:
                                retry_delay = None
                                try:
                                    for d in resp.json().get("error", {}).get("details", []):
                                        if "retryDelay" in d:
                                            retry_delay = float(d["retryDelay"].rstrip("s"))
                                except Exception:
                                    pass
                                if retry_delay and retry_delay > 120:
                                    print(f"[*] Quota limit reached for {model_id} (retryDelay: {retry_delay:.0f}s). Switching to fallback model...")
                                    break
                                elif retry_delay:
                                    wait_s = max(retry_delay + 1.0, wait_s)

                            print(f"[*] Gemini ({model_id}) returned HTTP {resp.status_code} (attempt {attempt}/{max_retries}). Retrying in {wait_s:.1f}s...")
                            await asyncio.sleep(wait_s)
                            continue
                        elif "API_KEY_SERVICE_BLOCKED" in resp.text:
                            print(f"[!] API_KEY_SERVICE_BLOCKED on generativelanguage for {model_id}")
                            break
                        else:
                            print(f"[!] Gemini ({model_id}) returned HTTP {resp.status_code}: {resp.text[:300]}")
                            last_error = RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                            break
                    except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                        wait_s = float(attempt * 3)
                        print(f"[*] Network/timeout error calling {model_id} (attempt {attempt}/{max_retries}): {net_err}. Retrying in {wait_s:.1f}s...")
                        last_error = net_err
                        await asyncio.sleep(wait_s)

            if last_error:
                raise last_error
            raise RuntimeError(f"Gemini API call failed for models: {candidate_models}")
