"""Local OCR: Tesseract reads the text, and labelled lines become ARGUS's identity fields.

Needs the Tesseract program and the `ocr` dependency group (`pytesseract`, Pillow); without
either, or for an image Tesseract cannot read, the document is unavailable, so the calling tool
falls back and says so. The container image has neither: deployments use Document Intelligence.

The documents ARGUS reads locally are the synthetic ones from
`data/synthetic/generate_ocr_documents.py`, which print one `Label: value` pair per line.
"""

from __future__ import annotations

import io
from typing import Any

from argus.data_plane.base import DataPlaneUnavailable

# Each document label, lower-cased, and the field name ARGUS uses for it: the same names the
# Azure implementation maps Document Intelligence's ID fields to.
LABELS = {
    "surname / given names": "full_name",
    "full name": "full_name",
    "name": "full_name",
    "entity name": "entity_name",
    "date of birth": "date_of_birth",
    "nationality": "nationality",
    "passport number": "document_number",
    "licence number": "document_number",
    "id number": "document_number",
    "expiry date": "expiry_date",
    "issuing country": "issuing_country",
    "address": "address",
}


def extract_fields(image: bytes) -> dict[str, dict]:
    """Return `{field_name: {"value": str, "confidence": float}}` read from the image."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise DataPlaneUnavailable("Local OCR needs the `ocr` dependency group") from exc
    try:
        page = Image.open(io.BytesIO(image))
        page.load()  # decode now: a truncated image fails here, not somewhere inside Tesseract
        data = pytesseract.image_to_data(page, output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractNotFoundError as exc:  # an OSError too, so it comes first
        raise DataPlaneUnavailable("Tesseract is not installed") from exc
    except (OSError, pytesseract.TesseractError) as exc:  # OSError: Pillow cannot read it
        raise DataPlaneUnavailable(f"Tesseract could not read the document: {exc}") from exc
    return labelled_fields(text_lines(data))


def text_lines(data: dict[str, list[Any]]) -> list[tuple[str, float]]:
    """Tesseract's words joined into lines, each with its words' mean confidence (0 to 1)."""
    lines: dict[tuple[int, int, int], list[tuple[str, float]]] = {}
    for i, word in enumerate(data["text"]):
        confidence = float(data["conf"][i])
        if not str(word).strip() or confidence < 0:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append((str(word), confidence))
    return [
        (" ".join(w for w, _ in words), sum(c for _, c in words) / len(words) / 100)
        for words in lines.values()
    ]


def labelled_fields(lines: list[tuple[str, float]]) -> dict[str, dict]:
    """Fields from `Label: value` lines with a known label; the first occurrence of each wins."""
    fields: dict[str, dict] = {}
    for text, confidence in lines:
        label, colon, value = text.partition(":")
        name = LABELS.get(" ".join(label.lower().split()))
        if colon and name and value.strip() and name not in fields:
            fields[name] = {"value": value.strip(), "confidence": round(confidence, 3)}
    return fields
