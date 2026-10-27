"""
Extracts key details (bill amount, units consumed, etc.) from an uploaded
electricity bill image or PDF using an NVIDIA NIM vision-language model.

Supported inputs: JPG, PNG, WEBP images, and PDF (first page only, requires
the system package `poppler-utils` for pdf2image to work).

This always returns a structured dict rather than raising, so the route
layer can give the frontend a clean success/failure response every time.
"""
import base64
import io
import json
import os
import re

import requests
from PIL import Image

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")
# Free vision-capable model on build.nvidia.com. Override via env if needed.
NVIDIA_VISION_MODEL = os.environ.get("NVIDIA_VISION_MODEL", "meta/llama-3.2-11b-vision-instruct")

REQUEST_TIMEOUT_SECONDS = 30
MAX_BASE64_BYTES = 170_000  # stay under NIM's ~180KB embedded-image limit

EXTRACTION_PROMPT = (
    "You are looking at a photo or scan of an electricity bill, possibly "
    "from a Pakistani electricity provider (LESCO, K-Electric, IESCO, "
    "PESCO, etc). Extract the following fields and respond with ONLY a "
    "single JSON object, no markdown, no explanation:\n\n"
    "{\n"
    '  "monthly_bill": <total payable amount as a plain number, no currency symbol or commas>,\n'
    '  "units_consumed": <electricity units in kWh as a plain number, or null if not visible>,\n'
    '  "customer_name": <account holder name as printed, or null>,\n'
    '  "bill_month": <billing month/period as printed, e.g. "March 2026", or null>,\n'
    '  "due_date": <payment due date as printed, or null>,\n'
    '  "confidence": <"high", "medium", or "low" based on how clearly you could read the bill>\n'
    "}\n\n"
    "If you cannot find a field, use null. If the image doesn't look like "
    "an electricity bill at all, set monthly_bill to null and confidence "
    'to "low".'
)


def is_configured() -> bool:
    return bool(NVIDIA_API_KEY)


def _compress_image(raw_bytes: bytes) -> bytes:
    """Resize/recompress so the base64 payload stays under NIM's inline limit."""
    img = PIL.Image.open(io.BytesIO(raw_bytes))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    quality = 85
    max_dim = 1600
    while True:
        resized = img.copy()
        resized.thumbnail((max_dim, max_dim))
        buf = io.BytesIO()
        resized.save(buf, format="JPEG", quality=quality)
        data = buf.getvalue()
        encoded_len = len(base64.b64encode(data))
        if encoded_len <= MAX_BASE64_BYTES or (quality <= 35 and max_dim <= 700):
            return data
        quality = max(35, quality - 15)
        max_dim = max(700, int(max_dim * 0.8))


def _pdf_first_page_to_image(raw_bytes: bytes) -> bytes:
    """Convert page 1 of a PDF bill to a JPEG. Requires poppler-utils installed."""
    from pdf2image import convert_from_bytes  # optional dep, imported lazily

    pages = convert_from_bytes(raw_bytes, dpi=200, first_page=1, last_page=1)
    buf = io.BytesIO()
    pages[0].save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _extract_json(text: str) -> dict:
    """Pull a JSON object out of the model's reply, tolerating stray text/fences."""
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model response.")
    return json.loads(match.group(0))


def _to_number(v):
    if v is None:
        return None
    try:
        cleaned = re.sub(r"[^\d.]", "", str(v))
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def extract_bill_details(file_bytes: bytes, mime_type: str, filename: str = "") -> dict:
    """
    Returns {"success": True, "data": {...}} or {"success": False, "error": "..."}.
    Never raises.
    """
    if not NVIDIA_API_KEY:
        return {
            "success": False,
            "error": "Bill scanning isn't configured yet (missing NVIDIA_API_KEY).",
        }

    try:
        is_pdf = (mime_type == "application/pdf") or filename.lower().endswith(".pdf")
        if is_pdf:
            try:
                image_bytes = _pdf_first_page_to_image(file_bytes)
            except Exception:
                return {
                    "success": False,
                    "error": (
                        "Couldn't read this PDF. Please upload a photo or "
                        "screenshot of your bill instead (JPG/PNG)."
                    ),
                }
        else:
            image_bytes = file_bytes

        compressed = _compress_image(image_bytes)
        b64 = base64.b64encode(compressed).decode("utf-8")

        payload = {
            "model": NVIDIA_VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": EXTRACTION_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    ],
                }
            ],
            "temperature": 0.1,
            "max_tokens": 400,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json",
        }
        resp = requests.post(NVIDIA_API_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        raw_text = resp.json()["choices"][0]["message"]["content"]
        parsed = _extract_json(raw_text)

        data = {
            "monthly_bill": _to_number(parsed.get("monthly_bill")),
            "units_consumed": _to_number(parsed.get("units_consumed")),
            "customer_name": parsed.get("customer_name") or None,
            "bill_month": parsed.get("bill_month") or None,
            "due_date": parsed.get("due_date") or None,
            "confidence": parsed.get("confidence") if parsed.get("confidence") in ("high", "medium", "low") else "low",
        }

        if data["monthly_bill"] is None:
            return {
                "success": False,
                "error": "Couldn't find a bill amount in this image. Please enter it manually.",
            }

        return {"success": True, "data": data}

    except requests.exceptions.RequestException as exc:
        print(f"[bill_ocr] NVIDIA API request failed: {exc}")
        return {"success": False, "error": "Couldn't reach the AI service. Please try again or enter manually."}
    except Exception as exc:
        print(f"[bill_ocr] extraction failed: {exc}")
        return {"success": False, "error": "Couldn't read this bill. Please enter the amount manually."}
