from __future__ import annotations

import base64

import httpx

from app.config import settings

GEMINI_IMAGE_URL = "https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict"


async def generate_image(prompt: str, width: int = 1024, height: int = 1024) -> bytes:
    _ = (width, height)
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{GEMINI_IMAGE_URL}?key={settings.google_ai_api_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "instances": [{"prompt": prompt}],
                    "parameters": {
                        "sampleCount": 1,
                        "aspectRatio": "1:1",
                    },
                },
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise RuntimeError("Image generation is currently unavailable. Please try again.") from exc

    try:
        b64_data = payload["predictions"][0]["bytesBase64Encoded"]
        return base64.b64decode(b64_data)
    except Exception as exc:
        raise ValueError("Image generation returned an invalid payload") from exc
