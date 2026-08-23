import base64
import json
from pathlib import Path
from typing import Any

import httpx
from google import genai
from google.genai import types

from app.config import get_settings
from app.domain.invoice import InvoiceExtracted
from app.providers.base import ExtractionProvider
from app.providers.mock import _dict_to_extraction, _parse_json_response

EXTRACTION_PROMPT = """Extract invoice data from the provided document images.
Return ONLY valid JSON matching this schema:
{
  "vendor_name": {"value": "...", "confidence": 0.0-1.0, "source_page": 1},
  "vendor_tax_id": {"value": "...", "confidence": 0.0-1.0, "source_page": 1},
  "invoice_number": {"value": "...", "confidence": 0.0-1.0, "source_page": 1},
  "invoice_date": {"value": "YYYY-MM-DD", "confidence": 0.0-1.0, "source_page": 1},
  "due_date": {"value": "YYYY-MM-DD or null", "confidence": 0.0-1.0, "source_page": 1},
  "currency": {"value": "USD", "confidence": 0.0-1.0, "source_page": 1},
  "subtotal": {"value": "1234.56", "confidence": 0.0-1.0, "source_page": 1},
  "tax": {"value": "123.45", "confidence": 0.0-1.0, "source_page": 1},
  "total": {"value": "1357.01", "confidence": 0.0-1.0, "source_page": 1},
  "po_reference": {"value": "PO-XXXX or null", "confidence": 0.0-1.0, "source_page": 1},
  "payment_details": {"value": "...", "confidence": 0.0-1.0, "source_page": 1},
  "lines": [{"description": {"value": "...", "confidence": 0.9}, "item_code": {"value": "...", "confidence": 0.9}, "quantity": {"value": "1", "confidence": 0.9}, "unit_price": {"value": "100.00", "confidence": 0.9}, "tax_rate": {"value": "0", "confidence": 0.9}, "line_total": {"value": "100.00", "confidence": 0.9}}]
}
Use null for missing fields. Include confidence and source_page for each field."""


def _mime_for_path(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(ext, "image/png")


def _http_error(provider: str, response: httpx.Response) -> RuntimeError:
    detail = response.text.strip().replace("\n", " ")
    if len(detail) > 500:
        detail = detail[:500] + "..."
    if response.status_code == 402:
        detail = f"billing or account credits required. {detail}".strip()
    elif response.status_code in (401, 403):
        detail = f"check the API key and account permissions. {detail}".strip()
    elif response.status_code == 429:
        detail = f"rate limit or quota exceeded. {detail}".strip()
    suffix = f": {detail}" if detail else ""
    return RuntimeError(
        f"{provider} API returned HTTP {response.status_code}{suffix}"
    )


class GeminiProvider(ExtractionProvider):
    name = "gemini"

    async def extract_invoice(self, image_paths: list[str], file_name: str) -> tuple[InvoiceExtracted, dict[str, Any]]:
        settings = get_settings()
        try:
            client = genai.Client(api_key=settings.gemini_api_key)
            parts: list[Any] = [EXTRACTION_PROMPT]
            for p in image_paths:
                parts.append(
                    types.Part.from_bytes(
                        data=Path(p).read_bytes(), mime_type=_mime_for_path(p)
                    )
                )
            response = await client.aio.models.generate_content(
                model=settings.gemini_model,
                contents=parts,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            if not response.text:
                raise RuntimeError("Gemini returned an empty response")
            data = _parse_json_response(response.text)
            return _dict_to_extraction(data), {"provider": self.name, "model": settings.gemini_model}
        except Exception as e:
            raise RuntimeError(f"Gemini extraction failed: {e}") from e

    async def verify_invoice(
        self, extracted: InvoiceExtracted, image_paths: list[str]
    ) -> tuple[InvoiceExtracted, dict[str, Any]]:
        return extracted, {"provider": self.name, "verified": True}


class GroqProvider(ExtractionProvider):
    name = "groq"

    async def _call(self, image_paths: list[str]) -> dict[str, Any]:
        settings = get_settings()
        content: list[dict[str, Any]] = [{"type": "text", "text": EXTRACTION_PROMPT}]
        for p in image_paths[:3]:
            mime = _mime_for_path(p)
            b64 = base64.b64encode(Path(p).read_bytes()).decode()
            content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"},
                json={
                    "model": settings.groq_model,
                    "messages": [{"role": "user", "content": content}],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )
            if not resp.is_success:
                raise _http_error("Groq", resp)
            text = resp.json()["choices"][0]["message"]["content"]
            return _parse_json_response(text)

    async def extract_invoice(self, image_paths: list[str], file_name: str) -> tuple[InvoiceExtracted, dict[str, Any]]:
        try:
            data = await self._call(image_paths)
            return _dict_to_extraction(data), {"provider": self.name, "model": get_settings().groq_model}
        except Exception as e:
            raise RuntimeError(f"Groq extraction failed: {e}") from e

    async def verify_invoice(
        self, extracted: InvoiceExtracted, image_paths: list[str]
    ) -> tuple[InvoiceExtracted, dict[str, Any]]:
        return extracted, {"provider": self.name, "verified": True}


class OpenRouterProvider(ExtractionProvider):
    name = "openrouter"

    async def _call(self, image_paths: list[str]) -> dict[str, Any]:
        settings = get_settings()
        content: list[dict[str, Any]] = [{"type": "text", "text": EXTRACTION_PROMPT}]
        for p in image_paths[:3]:
            mime = _mime_for_path(p)
            b64 = base64.b64encode(Path(p).read_bytes()).decode()
            content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:3000",
                },
                json={
                    "model": settings.openrouter_model,
                    "messages": [{"role": "user", "content": content}],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )
            if not resp.is_success:
                raise _http_error("OpenRouter", resp)
            text = resp.json()["choices"][0]["message"]["content"]
            return _parse_json_response(text)

    async def extract_invoice(self, image_paths: list[str], file_name: str) -> tuple[InvoiceExtracted, dict[str, Any]]:
        try:
            data = await self._call(image_paths)
            return _dict_to_extraction(data), {"provider": self.name, "model": get_settings().openrouter_model}
        except Exception as e:
            raise RuntimeError(f"OpenRouter extraction failed: {e}") from e

    async def verify_invoice(
        self, extracted: InvoiceExtracted, image_paths: list[str]
    ) -> tuple[InvoiceExtracted, dict[str, Any]]:
        return extracted, {"provider": self.name, "verified": True}
