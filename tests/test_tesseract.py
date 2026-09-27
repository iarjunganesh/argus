"""Local OCR through Tesseract: text lines, labelled fields, and every way it can be unavailable."""

import io
import shutil
import sys

import pytesseract
import pytest
from PIL import Image, ImageDraw, ImageFont

from argus.data_plane import DataPlaneUnavailable, tesseract
from argus.data_plane.local import LocalOCR


def png(lines: list[str] | None = None) -> bytes:
    """A white document image with one line of black text per entry."""
    image = Image.new("RGB", (1100, 90 + 60 * len(lines or [])), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=32)
    for i, line in enumerate(lines or []):
        draw.text((40, 40 + 60 * i), line, font=font, fill="black")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def tesseract_data(*lines: list[tuple[str, int]]) -> dict[str, list]:
    """Tesseract's `image_to_data` dictionary for lines of (word, confidence) pairs."""
    data: dict[str, list] = {"text": [], "conf": [], "block_num": [], "par_num": [], "line_num": []}
    for number, words in enumerate(lines, start=1):
        for word, confidence in words:
            data["text"].append(word)
            data["conf"].append(str(confidence))
            data["block_num"].append(1)
            data["par_num"].append(1)
            data["line_num"].append(number)
    return data


def test_words_are_joined_into_lines_with_their_mean_confidence():
    data = tesseract_data(
        [("Full", 90), ("name:", 80), ("Ada", 70), ("Synthetic", 60)],
        [("", -1), ("   ", 95)],  # layout rows and blanks carry no text
        [("Nationality:", 100), ("NL", 100), ("?", -1)],
    )

    assert tesseract.text_lines(data) == [
        ("Full name: Ada Synthetic", 0.75),
        ("Nationality: NL", 1.0),
    ]


def test_known_labels_become_fields_and_the_first_occurrence_wins():
    lines = [
        ("Surname / Given  names: Ada Synthetic", 0.9),
        ("DATE OF BIRTH : 1990-01-01", 0.8),
        ("Passport number: X1234567", 0.95),
        ("Name: Someone Else", 0.9),  # full_name is already read
        ("Favourite colour: blue", 0.9),  # not an identity field
        ("Expiry date:", 0.9),  # no value
        ("PASSENGER PASSPORT", 0.9),  # no label
    ]

    assert tesseract.labelled_fields(lines) == {
        "full_name": {"value": "Ada Synthetic", "confidence": 0.9},
        "date_of_birth": {"value": "1990-01-01", "confidence": 0.8},
        "document_number": {"value": "X1234567", "confidence": 0.95},
    }


async def test_local_ocr_reads_the_fields_tesseract_finds(monkeypatch):
    seen = []

    def image_to_data(image, output_type):
        seen.append((image.size, output_type))
        return tesseract_data([("ID", 90), ("number:", 90), ("ID-1234-5678", 70)])

    monkeypatch.setattr(pytesseract, "image_to_data", image_to_data)

    fields = await LocalOCR().extract(png(), "id_card")

    assert fields == {"document_number": {"value": "ID-1234-5678", "confidence": 0.833}}
    assert seen == [((1100, 90), pytesseract.Output.DICT)]


@pytest.mark.parametrize(
    "error,reason",
    [
        (pytesseract.TesseractNotFoundError(), "not installed"),
        (pytesseract.TesseractError(1, "bad"), "could not read"),
    ],
)
def test_tesseract_failures_make_the_document_unavailable(monkeypatch, error, reason):
    def fail(image, output_type):
        raise error

    monkeypatch.setattr(pytesseract, "image_to_data", fail)

    with pytest.raises(DataPlaneUnavailable, match=reason):
        tesseract.extract_fields(png())


def test_what_is_not_an_image_is_unavailable():
    with pytest.raises(DataPlaneUnavailable, match="could not read"):
        tesseract.extract_fields(b"not an image")


def test_without_the_ocr_group_local_ocr_is_unavailable(monkeypatch):
    monkeypatch.setitem(sys.modules, "pytesseract", None)

    with pytest.raises(DataPlaneUnavailable, match="`ocr` dependency group"):
        tesseract.extract_fields(png())


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract is not installed")
def test_real_tesseract_reads_a_synthetic_passport():
    image = png(
        [
            "Surname / Given names: Ada Synthetic",
            "Date of birth: 1990-01-15",
            "Passport number: XK1234567",
        ]
    )

    fields = tesseract.extract_fields(image)

    assert {name: f["value"] for name, f in fields.items()} == {
        "full_name": "Ada Synthetic",
        "date_of_birth": "1990-01-15",
        "document_number": "XK1234567",
    }
    assert all(0 < f["confidence"] <= 1 for f in fields.values())
