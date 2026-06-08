"""Generate synthetic OCR document assets for ARGUS demos.

Produces a full matrix of:
  doc_types  × (passport | drivers_license | id_card | tax_invoice)
  quality    × (clean | slightly_noisy | degraded | low_contrast | photocopy | skewed)
  format     × (PNG | PDF)

Total: 4 doc types × 6 quality variants × 2 formats = 48 documents.

Faker generates realistic field values; Pillow renders the PNG variants with
noise, blur, contrast and rotation transforms; ReportLab renders PDF variants.
A JSONL manifest is written with ground-truth field values so the existing
ocr_processor / identity_validator pipeline can cross-check extracted fields.

Does NOT replace or re-architect the existing OCR pipeline.
Only produces demo documents that can be fed to the identity agent.

Usage (local, no upload):
    python data/synthetic/generate_ocr_documents.py --no-upload

Usage (with blob upload):
    python data/synthetic/generate_ocr_documents.py
    # Requires AZURE_STORAGE_CONNECTION_STRING in .env

Optional env vars:
    AZURE_STORAGE_CONNECTION_STRING   Azure Storage connection string
    OCR_STORAGE_CONTAINER             Container name (default: argus-ocr-docs)
    OCR_STORAGE_PREFIX                Blob prefix   (default: ocr-documents)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import textwrap
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from faker import Faker
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

try:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4, letter, landscape
    from reportlab.pdfgen import canvas as rl_canvas
    _REPORTLAB = True
except Exception:
    HexColor = None          # type: ignore[assignment]
    A4 = letter = None       # type: ignore[assignment]
    landscape = None         # type: ignore[assignment]
    rl_canvas = None         # type: ignore[assignment]
    _REPORTLAB = False

DATA_DIR = Path(__file__).parent
DEFAULT_OUTPUT_DIR = DATA_DIR / "ocr_documents"          # images / PDFs
DEFAULT_MANIFEST    = DATA_DIR / "ocr_documents_manifest.jsonl"  # stays in data/synthetic/
DEFAULT_CONTAINER = os.getenv("OCR_STORAGE_CONTAINER", "argus-ocr-docs")
DEFAULT_PREFIX = os.getenv("OCR_STORAGE_PREFIX", "ocr-documents")
DEFAULT_CONN = os.getenv("OCR_STORAGE_CONNECTION_STRING") or os.getenv("AZURE_STORAGE_CONNECTION_STRING")

# ── Quality definitions ───────────────────────────────────────────────────────
QUALITY_STYLES: dict[str, dict] = {
    "clean":          {"noise": 0,   "blur": 0.0, "contrast": 1.00, "rotate": 0.0,  "brightness": 1.00},
    "slightly_noisy": {"noise": 18,  "blur": 0.2, "contrast": 0.95, "rotate": 0.0,  "brightness": 0.98},
    "degraded":       {"noise": 34,  "blur": 0.5, "contrast": 0.85, "rotate": -2.0, "brightness": 0.92},
    "low_contrast":   {"noise": 24,  "blur": 0.3, "contrast": 0.70, "rotate": 1.0,  "brightness": 0.88},
    "photocopy":      {"noise": 44,  "blur": 0.8, "contrast": 0.65, "rotate": 0.0,  "brightness": 0.80},
    "skewed":         {"noise": 20,  "blur": 0.3, "contrast": 0.88, "rotate": -4.5, "brightness": 0.90},
}

DOC_TYPES = ("passport", "drivers_license", "id_card", "tax_invoice")


@dataclass
class OCRDocument:
    doc_id: str
    doc_type: str
    layout: str
    quality: str
    format: str
    file_name: str
    local_path: str
    blob_name: str | None
    blob_url: str | None
    entity_name: str
    entity_type: str
    jurisdiction: str
    ground_truth: dict[str, Any]


class DocFactory:
    def __init__(self, output_dir: Path, seed: int = 20260608) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fake = Faker()
        self.fake.seed_instance(seed)
        random.seed(seed)

    # ── Font helpers ─────────────────────────────────────────────────────────

    def _font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        candidates = (
            ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"] if bold
            else ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]
        )
        for name in candidates:
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                pass
        return ImageFont.load_default()

    # ── Image quality transforms ─────────────────────────────────────────────

    def _apply_quality(self, img: Image.Image, quality: str) -> Image.Image:
        s = QUALITY_STYLES[quality]
        if s["noise"] > 0:
            draw = ImageDraw.Draw(img)
            w, h = img.size
            for _ in range(s["noise"] * 30):
                x1 = random.randint(0, w - 1)
                y1 = random.randint(0, h - 1)
                x2 = min(w - 1, x1 + random.randint(-20, 20))
                y2 = min(h - 1, y1 + random.randint(-20, 20))
                shade = random.randint(100, 220)
                draw.line((x1, y1, x2, y2), fill=(shade, shade, shade), width=1)
        if s["blur"] > 0:
            img = img.filter(ImageFilter.GaussianBlur(s["blur"]))
        if s["contrast"] != 1.0:
            img = ImageEnhance.Contrast(img).enhance(s["contrast"])
        if s["brightness"] != 1.0:
            img = ImageEnhance.Brightness(img).enhance(s["brightness"])
        if s["rotate"] != 0.0:
            img = img.rotate(s["rotate"], resample=Image.Resampling.BICUBIC, expand=True, fillcolor="white")
        return img

    # ── PNG renderer ─────────────────────────────────────────────────────────

    def _render_png(
        self,
        *,
        file_name: str,
        title: str,
        subtitle: str,
        lines: list[str],
        accent: str,
        size: tuple[int, int],
        quality: str,
    ) -> Path:
        img = Image.new("RGB", size, "#f8fafc")
        draw = ImageDraw.Draw(img)
        w, h = size

        draw.rectangle([0, 0, w, 62], fill=accent)
        draw.text((18, 12), title, font=self._font(24, bold=True), fill="white")
        draw.text((w - 260, 18), subtitle, font=self._font(13), fill="white")

        body = self._font(19)
        label_f = self._font(17)
        y = 84
        for line in lines:
            if ": " in line:
                lbl, val = line.split(": ", 1)
                draw.text((20, y), lbl + ": ", font=label_f, fill="#6b7280")
                tw = draw.textlength(lbl + ": ", font=label_f)
                draw.text((20 + tw, y), val, font=body, fill="#111827")
            else:
                draw.text((20, y), line, font=body, fill="#374151")
            y += 31

        draw.rectangle([14, h - 52, w - 14, h - 14], outline=accent, width=2)
        draw.text((24, h - 42), "SYNTHETIC DOCUMENT — FOR OCR DEMOS ONLY — NOT A REAL DOCUMENT",
                  font=self._font(13), fill=accent)

        img = self._apply_quality(img, quality)
        path = self.output_dir / file_name
        img.save(path, format="PNG", optimize=True)
        return path

    # ── PDF renderer ─────────────────────────────────────────────────────────

    def _render_pdf(
        self,
        *,
        file_name: str,
        title: str,
        subtitle: str,
        lines: list[str],
        accent: str,
        pagesize: Any,
    ) -> Path:
        if not _REPORTLAB:
            raise RuntimeError("reportlab not installed — run: pip install reportlab")
        path = self.output_dir / file_name
        c = rl_canvas.Canvas(str(path), pagesize=pagesize)
        w, h = pagesize

        c.setFillColor(HexColor(accent))
        c.rect(0, h - 66, w, 66, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(20, h - 46, title)
        c.setFont("Helvetica-Oblique", 10)
        c.drawRightString(w - 20, h - 42, subtitle)

        c.setFillColorRGB(0.09, 0.09, 0.09)
        y = h - 92
        for line in lines:
            for chunk in (textwrap.wrap(line, 88) or [line]):
                if ": " in chunk:
                    lbl, rest = chunk.split(": ", 1)
                    c.setFont("Helvetica-Bold", 10)
                    c.drawString(22, y, lbl + ": ")
                    lw = c.stringWidth(lbl + ": ", "Helvetica-Bold", 10)
                    c.setFont("Helvetica", 10)
                    c.drawString(22 + lw, y, rest)
                else:
                    c.setFont("Helvetica", 10)
                    c.drawString(22, y, chunk)
                y -= 16
            y -= 4

        c.setStrokeColor(HexColor(accent))
        c.rect(18, 34, w - 36, 36, fill=0, stroke=1)
        c.setFont("Helvetica-Oblique", 9)
        c.setFillColorRGB(0.45, 0.45, 0.45)
        c.drawString(26, 48, "Synthetic document for OCR robustness testing. Not a real document.")
        c.save()
        return path

    # ── Field data builders ───────────────────────────────────────────────────

    def _passport_data(self) -> tuple[list[str], dict]:
        name = self.fake.name()
        dob = self.fake.date_of_birth(minimum_age=22, maximum_age=60).isoformat()
        nat = self.fake.country_code()
        num = self.fake.bothify(text="??#######").upper()
        exp = self.fake.date_this_decade(before_today=False, after_today=True).isoformat()
        iss = self.fake.country_code()
        lines = [
            f"Surname / Given names: {name}",
            f"Date of birth: {dob}",
            f"Nationality: {nat}",
            f"Passport number: {num}",
            f"Expiry date: {exp}",
            f"Issuing country: {iss}",
        ]
        return lines, {"full_name": name, "date_of_birth": dob, "nationality": nat,
                       "passport_number": num, "expiry_date": exp, "issuing_country": iss}

    def _license_data(self) -> tuple[list[str], dict]:
        name = self.fake.name()
        dob = self.fake.date_of_birth(minimum_age=18, maximum_age=75).isoformat()
        num = self.fake.bothify(text="D####-####-###")
        exp = self.fake.date_this_decade(before_today=False, after_today=True).isoformat()
        addr = self.fake.address().replace("\n", ", ")
        state = self.fake.state_abbr()
        lines = [
            f"Name: {name}",
            f"Date of birth: {dob}",
            f"Licence number: {num}",
            f"Expiry date: {exp}",
            f"Address: {addr}",
            f"Issuing state: {state}",
        ]
        return lines, {"full_name": name, "date_of_birth": dob, "licence_number": num,
                       "expiry_date": exp, "address": addr, "issuing_state": state}

    def _id_card_data(self) -> tuple[list[str], dict]:
        name = self.fake.name()
        dob = self.fake.date_of_birth(minimum_age=18, maximum_age=70).isoformat()
        nat = self.fake.country_code()
        num = self.fake.bothify(text="ID-####-####").upper()
        exp = self.fake.date_this_decade(before_today=False, after_today=True).isoformat()
        lines = [
            f"Full name: {name}",
            f"Date of birth: {dob}",
            f"Nationality: {nat}",
            f"ID number: {num}",
            f"Expiry date: {exp}",
        ]
        return lines, {"full_name": name, "date_of_birth": dob, "nationality": nat,
                       "id_number": num, "expiry_date": exp}

    def _invoice_data(self) -> tuple[list[str], dict]:
        company = self.fake.company()
        tax_id = self.fake.bothify(text="TAX-########").upper()
        addr = self.fake.address().replace("\n", ", ")
        inv_num = self.fake.bothify(text="INV-#######").upper()
        date = self.fake.date_this_year().isoformat()
        amount = f"{float(self.fake.pydecimal(left_digits=4, right_digits=2, positive=True)):.2f}"
        lines = [
            f"Entity name: {company}",
            f"Tax ID: {tax_id}",
            f"Address: {addr}",
            f"Invoice number: {inv_num}",
            f"Date: {date}",
            f"Amount: USD {amount}",
        ]
        return lines, {"entity_name": company, "tax_id": tax_id, "address": addr,
                       "invoice_number": inv_num, "date": date, "amount": f"USD {amount}"}

    _DOC_META: dict[str, dict] = {
        "passport":       {"title": "PASSENGER PASSPORT",   "accent": "#1d4ed8", "size": (900,  580), "entity_type": "individual", "ps": "A4"},
        "drivers_license":{"title": "DRIVER'S LICENSE",     "accent": "#0f766e", "size": (1020, 620), "entity_type": "individual", "ps": "letter"},
        "id_card":        {"title": "NATIONAL ID CARD",     "accent": "#7c3aed", "size": (860,  530), "entity_type": "individual", "ps": "A4"},
        "tax_invoice":    {"title": "TAX INVOICE",          "accent": "#b45309", "size": (1200, 820), "entity_type": "corporate",  "ps": "letter_landscape"},
    }

    def _pagesize(self, key: str) -> Any:
        if key == "A4":      return A4
        if key == "letter":  return letter
        return landscape(letter) if landscape else letter

    def _data_for(self, doc_type: str) -> tuple[list[str], dict]:
        return {
            "passport":        self._passport_data,
            "drivers_license": self._license_data,
            "id_card":         self._id_card_data,
            "tax_invoice":     self._invoice_data,
        }[doc_type]()

    # ── Full matrix ───────────────────────────────────────────────────────────

    def create_documents(self, prefix: str = "ocr-documents") -> list[OCRDocument]:
        records: list[OCRDocument] = []
        for doc_type in DOC_TYPES:
            meta = self._DOC_META[doc_type]
            jur = self.fake.country_code()
            for quality in QUALITY_STYLES:
                # PNG
                lines, gt = self._data_for(doc_type)
                entity_name = gt.get("full_name") or gt.get("entity_name", "")
                fname_png = f"{doc_type}_{quality}.png"
                try:
                    path_png = self._render_png(
                        file_name=fname_png,
                        title=meta["title"],
                        subtitle=f"{quality.replace('_', ' ')} — PNG",
                        lines=lines,
                        accent=meta["accent"],
                        size=meta["size"],
                        quality=quality,
                    )
                    records.append(OCRDocument(
                        doc_id=path_png.stem, doc_type=doc_type, layout="png",
                        quality=quality, format="png", file_name=fname_png,
                        local_path=str(path_png), blob_name=f"{prefix}/{fname_png}",
                        blob_url=None, entity_name=entity_name,
                        entity_type=meta["entity_type"], jurisdiction=jur, ground_truth=gt,
                    ))
                    print(f"  ✓ {fname_png}")
                except Exception as exc:
                    print(f"  ✗ {fname_png}: {exc}")

                # PDF
                if _REPORTLAB:
                    lines_pdf, gt_pdf = self._data_for(doc_type)
                    ename_pdf = gt_pdf.get("full_name") or gt_pdf.get("entity_name", "")
                    fname_pdf = f"{doc_type}_{quality}.pdf"
                    try:
                        path_pdf = self._render_pdf(
                            file_name=fname_pdf,
                            title=meta["title"],
                            subtitle=f"{quality.replace('_', ' ')} — PDF",
                            lines=lines_pdf,
                            accent=meta["accent"],
                            pagesize=self._pagesize(meta["ps"]),
                        )
                        records.append(OCRDocument(
                            doc_id=path_pdf.stem, doc_type=doc_type, layout="pdf",
                            quality=quality, format="pdf", file_name=fname_pdf,
                            local_path=str(path_pdf), blob_name=f"{prefix}/{fname_pdf}",
                            blob_url=None, entity_name=ename_pdf,
                            entity_type=meta["entity_type"], jurisdiction=jur, ground_truth=gt_pdf,
                        ))
                        print(f"  ✓ {fname_pdf}")
                    except Exception as exc:
                        print(f"  ✗ {fname_pdf}: {exc}")
                else:
                    print(f"  [skip PDF] reportlab not installed — run: pip install reportlab")
        return records


# ── Blob upload ───────────────────────────────────────────────────────────────

def upload_documents(
    records: list[OCRDocument],
    connection_string: str,
    container_name: str,
) -> list[OCRDocument]:
    from azure.storage.blob import BlobServiceClient, ContentSettings

    svc = BlobServiceClient.from_connection_string(connection_string)
    container = svc.get_container_client(container_name)
    try:
        container.create_container()
    except Exception:
        pass

    for record in records:
        ct = "application/pdf" if record.format == "pdf" else "image/png"
        blob = container.get_blob_client(record.blob_name)
        with open(record.local_path, "rb") as fh:
            blob.upload_blob(fh, overwrite=True, content_settings=ContentSettings(content_type=ct))
        record.blob_url = blob.url
        print(f"  ↑ uploaded {record.file_name}")
    return records


# ── Manifest ──────────────────────────────────────────────────────────────────

def write_manifest(records: list[OCRDocument], manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic OCR documents (all doc types × all quality levels × PNG + PDF)"
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--manifest", default=None,
                        help="Path for manifest JSONL (default: data/synthetic/ocr_documents_manifest.jsonl)")
    parser.add_argument("--seed", type=int, default=20260608)
    parser.add_argument("--no-upload", action="store_true",
                        help="Skip Azure Blob upload even if a connection string is set")
    parser.add_argument("--container", default=DEFAULT_CONTAINER)
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = (Path(args.manifest) if args.manifest else DEFAULT_MANIFEST)

    n_types = len(DOC_TYPES)
    n_quality = len(QUALITY_STYLES)
    n_formats = 2 if _REPORTLAB else 1
    print(f"Generating {n_types} doc types × {n_quality} quality levels × {n_formats} formats "
          f"= {n_types * n_quality * n_formats} documents …")

    factory = DocFactory(output_dir=output_dir, seed=args.seed)
    records = factory.create_documents(prefix=args.prefix)

    conn = None if args.no_upload else DEFAULT_CONN
    if conn:
        print(f"\nUploading {len(records)} documents to container '{args.container}' …")
        records = upload_documents(records, conn, args.container)
        uploaded = sum(1 for r in records if r.blob_url)
        print(f"Uploaded {uploaded}/{len(records)} documents.")
    else:
        print("\nNo storage connection string found — documents saved locally only.")
        print("To upload: set AZURE_STORAGE_CONNECTION_STRING in .env then re-run.")

    write_manifest(records, manifest_path)
    total_png = sum(1 for r in records if r.format == "png")
    total_pdf = sum(1 for r in records if r.format == "pdf")
    print(f"\nTotal: {len(records)} documents ({total_png} PNG, {total_pdf} PDF)")
    print(f"Output  : {output_dir}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
