"""Markdown export and evidence overlays (PyMuPDF only; run from any env)."""
from __future__ import annotations
from pathlib import Path

import fitz

COLORS = {"native_pdf": (0.1, 0.55, 0.2), "ocr": (0.9, 0.5, 0.0), "table_model": (0.1, 0.2, 0.8), "vlm": (0.6, 0.1, 0.6)}


def _esc(x):
    return "" if x is None else str(x).replace("|", "\\|").replace("\n", " ")


def to_markdown(pred: dict) -> str:
    out = [f"# {pred['document_id']} p{pred['page']} — backend `{pred['backend']}` — status `{pred['status']}`", ""]
    for i in pred["issues"]:
        out.append(f"- **{i.get('severity','info')}** `{i.get('code')}` {i.get('message','')}")
    for t in pred["tables"]:
        out += ["", f"## Table {t['table_id']} (unit: {t.get('unit')}, data columns: {t['n_data_columns']})", ""]
        hdr = ["label"] + [" / ".join(_esc(h["text"]) for h in t["headers"] if k in h["column_indices"]) or f"col{k}"
                           for k in range(t["n_data_columns"])]
        out.append("| " + " | ".join(hdr) + " |")
        out.append("|" + "---|" * len(hdr))
        for r in t["rows"]:
            cells = {c["column_index"]: c for c in r["cells"]}
            vals = []
            for k in range(t["n_data_columns"]):
                c = cells.get(k)
                vals.append("" if c is None else (_esc(c["raw"]) if c["raw"] is not None else f"*{c['status']}*"))
            out.append("| " + " | ".join([("  " * len(r["parent_path"])) + _esc(r["label"])] + vals) + " |")
        for c in t.get("checks", []):
            if c["status"] in ("violation",):
                out.append(f"\n> arithmetic diagnostic `{c['name']}`: reported {c['reported']} vs calculated {c['calculated']} (Δ{c['difference']})")
    return "\n".join(out) + "\n"


def draw_evidence(pdf, page_index, pred: dict, out_png, dpi=130, crop=None):
    doc = fitz.open(str(pdf))
    page = doc[page_index]
    sh = page.new_shape()
    for t in pred["tables"]:
        if t["bbox"]:
            sh.draw_rect(fitz.Rect(t["bbox"]))
            sh.finish(color=(0.8, 0.1, 0.1), width=1.2)
        for r in t["rows"]:
            for c in r["cells"]:
                if c["bbox"]:
                    col = (0.9, 0.0, 0.0) if c["status"] in ("uncertain", "unreadable") else COLORS.get(c["evidence_kind"], (0, 0, 0))
                    sh.draw_rect(fitz.Rect(c["bbox"]))
                    sh.finish(color=col, width=.7)
    sh.commit()
    pix = page.get_pixmap(dpi=dpi, clip=fitz.Rect(crop) if crop else None)
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out_png))
    return str(out_png)
