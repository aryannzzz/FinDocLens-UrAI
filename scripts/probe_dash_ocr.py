"""Why are `－` placeholders lost by Docling+RapidOCR? Probe RapidOCR directly on (a) the full 200-dpi page and (b) padded cell crops.
.venv-docling/bin/python scripts/probe_dash_ocr.py  -> prints what the engine returns around the two `－` cells of the original page."""
import json
import sys

import fitz
import numpy as np
from rapidocr import RapidOCR

gold = json.load(open("benchmark/gold/original.json"))
cells = [(r["label"], c) for t in gold["tables"] for r in t["rows"] for c in r["cells"] if c["status"] == "not_reported"]
page = fitz.open("baseline_v2/source.pdf")[0]
zoom = 200 / 72
engine = RapidOCR(params={"Rec.lang_type": "japan", "Rec.ocr_version": "PP-OCRv6"}) if False else RapidOCR()
res = {}
for label, c in cells:
    x0, y0, x1, y1 = c["bbox"]
    out = {}
    for name, pad, scale in (("tight", 0, 1), ("pad6", 6, 1), ("pad12_x3", 12, 3)):
        clip = fitz.Rect(x0 - pad, y0 - pad, x1 + pad, y1 + pad)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom * scale, zoom * scale), clip=clip, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        r = engine(img)
        out[name] = [(t, round(float(s), 3)) for t, s in zip(r.txts or [], r.scores or [])]
    res[f"{label} col {c['column_index']}"] = dict(gold_raw=c["raw"], gold_bbox=[round(v, 1) for v in c["bbox"]], ocr=out)
print(json.dumps(res, ensure_ascii=False, indent=1))
