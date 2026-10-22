"""Synthetic variants of a source page for backend stress tests (same-source: never an independent-template claim)."""
from __future__ import annotations
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
VAR_DIR = ROOT / "data" / "variants"


def raster_pdf(pdf, page_index, dpi=200, name=None, jpeg=False):
    """Single-page image-only PDF (no text layer) rendered from `pdf[page_index]`."""
    VAR_DIR.mkdir(parents=True, exist_ok=True)
    src = fitz.open(str(pdf))
    pg = src[page_index]
    pix = pg.get_pixmap(dpi=dpi, alpha=False)
    out = fitz.open()
    p = out.new_page(width=pg.rect.width, height=pg.rect.height)
    p.insert_image(p.rect, stream=pix.tobytes("jpeg" if jpeg else "png"))
    target = VAR_DIR / f"{name or Path(pdf).stem}_raster{dpi}.pdf"
    out.save(str(target))
    return target
