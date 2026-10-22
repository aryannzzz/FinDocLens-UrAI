"""Deterministic synthetic table pages for the P0 regression tests (text layer only, right-aligned amounts).

Truth is declared here, before any parser runs. Nothing in this module reads a backend or an evaluator.
"""
from pathlib import Path

import fitz

PERIODS = ("2025/3", "2026/3")
ISO = ("2025-03-31", "2026-03-31")
LABELS = ("現金", "売掛金", "棚卸資産", "その他")


def default_rows(ncol, first_row=None, labels=LABELS):
    rows = []
    for i, label in enumerate(labels):
        vals = [str(310 + i * 30 + k * 11) for k in range(ncol)]
        if i == 0 and first_row:
            vals = list(first_row)
        rows.append((label, vals))
    return rows


def make_pdf(path, tables, width=800, height=500):
    """tables: list of dict(x0, ncol, rows=[(label, [raw,...])], headers=[...]|None, extra_header=[...]|None,
    header_label=None, y_first=120, pitch=55). Returns the declared truth: {table_tag: [(label, [raw...])]}."""
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    font = fitz.Font("japan")

    def put(x_right_or_left, y, s, right=False):
        w = font.text_length(s, fontsize=11)
        x = x_right_or_left - w if right else x_right_or_left
        page.insert_text((x, y), s, fontname="japan", fontsize=11)
        return [x, y - 11 * font.ascender, x + w, y - 11 * font.descender]

    truth = {}
    for ti, t in enumerate(tables):
        x0, ncol = t["x0"], t["ncol"]
        pitch = t.get("pitch", 55)
        y_first = t.get("y_first", 120)
        put(x0, 45, "（百万円）")
        for k, text in enumerate(t.get("headers") or []):
            put(x0 + 200 + k * 85, y_first - pitch * .8, text, right=True)
        if t.get("extra_header"):
            hy = y_first - pitch * .8 - 22
            if t.get("header_label"):
                put(x0, hy, t["header_label"])
            for k, text in enumerate(t["extra_header"]):
                put(x0 + 200 + k * 85, hy, text, right=True)
        for i, (label, vals) in enumerate(t["rows"]):
            y = y_first + i * pitch
            put(x0, y, label)
            for k, raw in enumerate(vals):
                put(x0 + 200 + k * 85, y, raw, right=True)
        truth[t.get("tag", f"t{ti}")] = t["rows"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path), no_new_id=True)
    doc.close()
    return truth


def native_cells(pred):
    """{label: [raw per data column]} of every table in a findoclens/native_grid prediction dict."""
    out = {}
    for t in pred["tables"]:
        for r in t["rows"]:
            out[(t["table_id"], r["label"])] = [c["raw"] for c in r["cells"] if c["column_index"] >= 0]
    return out
