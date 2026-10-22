"""Prediction-vs-prediction agreement and text-layer token recall.

IMPORTANT: agreement between two backends is not accuracy. `reference_tokens` from the PDF text layer is a
legitimate reference only for numeric *strings* on digital pages (and for rasterised copies of those pages).
"""
from __future__ import annotations
import difflib
import re
import unicodedata
from collections import Counter


def norm_raw(s):
    return None if s is None else re.sub(r"\s+", "", s)


_PREFIX = re.compile(r"^[→⇒➔➡▶>＞]+")


def numeric_token(raw):
    """Whitespace-free numeric string (leading arrow glyphs ignored) or None if the text is not numeric."""
    from .amounts import looks_numeric
    if raw is None:
        return None
    t = _PREFIX.sub("", norm_raw(raw))
    return t if t and looks_numeric(t) else None


def norm_label(s):
    return re.sub(r"[\s　・]", "", unicodedata.normalize("NFKC", s or ""))


def numeric_cells(pred):
    """[(table_id, row_index, label, column_index, raw)] for cells carrying numeric text."""
    out = []
    for t in pred["tables"]:
        for r in t["rows"]:
            for c in r["cells"]:
                tok = numeric_token(c["raw"]) if c["column_index"] >= 0 and c["role"] != "other" else None
                if tok is not None and c["status"] in ("observed", "negative_zero", "not_reported", "uncertain"):
                    out.append((t["table_id"], r["row_index"], r["label"], c["column_index"], tok))
    return out


def reference_tokens(pred):
    return Counter(x[-1] for x in numeric_cells(pred))


def token_recall(pred, ref: Counter):
    got = Counter(x[-1] for x in numeric_cells(pred))
    hit = sum((got & ref).values())
    return {"reference_tokens": sum(ref.values()), "predicted_tokens": sum(got.values()), "matched": hit,
            "recall": round(hit / max(1, sum(ref.values())), 4), "precision": round(hit / max(1, sum(got.values())), 4),
            "missing": sorted((ref - got).elements())[:40], "spurious": sorted((got - ref).elements())[:40]}


def match_tables(a, b):
    """Greedy one-to-one match of tables by numeric-token overlap. Returns [(ta,tb,jaccard)]."""
    pairs = []
    for ta in a["tables"]:
        ca = Counter(x[-1] for x in numeric_cells({"tables": [ta]}))
        for tb in b["tables"]:
            cb = Counter(x[-1] for x in numeric_cells({"tables": [tb]}))
            inter = sum((ca & cb).values())
            union = sum((ca | cb).values())
            if inter:
                pairs.append((inter / union, ta, tb))
    pairs.sort(key=lambda p: -p[0])
    used_a, used_b, res = set(), set(), []
    for j, ta, tb in pairs:
        if ta["table_id"] in used_a or tb["table_id"] in used_b:
            continue
        used_a.add(ta["table_id"]); used_b.add(tb["table_id"])
        res.append((ta, tb, round(j, 3)))
    return res


def row_cells(t):
    rows = []
    for r in t["rows"]:
        vals = [c for c in r["cells"] if c["column_index"] >= 0 and c["role"] != "other"]
        if any(c["raw"] is not None for c in vals):
            rows.append((norm_label(r["label"]), r, vals))
    return rows


def compare_pair(a, b):
    """Cell-level agreement of `a` (primary) against `b` (checker). Returns summary + disagreement list."""
    summary = {"tables_a": len(a["tables"]), "tables_b": len(b["tables"]), "matched_tables": [], "disagreements": [],
               "unmatched_tables_a": [], "unmatched_tables_b": []}
    pairs = match_tables(a, b)
    ma = {x[0]["table_id"] for x in pairs}
    mb = {x[1]["table_id"] for x in pairs}
    summary["unmatched_tables_a"] = [t["table_id"] for t in a["tables"] if t["table_id"] not in ma]
    summary["unmatched_tables_b"] = [t["table_id"] for t in b["tables"] if t["table_id"] not in mb]
    for ta, tb, jac in pairs:
        ra, rb = row_cells(ta), row_cells(tb)
        used = set()
        n_cmp = n_eq = n_unmatched = 0
        for la, row_a, ca in ra:
            best, bs = None, 0.0
            for k, (lb, row_b, cb) in enumerate(rb):
                if k in used:
                    continue
                s = difflib.SequenceMatcher(None, la, lb).ratio() if la != lb else 1.0
                if s > bs:
                    best, bs = k, s
            if best is None or bs < 0.6:
                n_unmatched += 1
                summary["disagreements"].append({"table": ta["table_id"], "row_index": row_a["row_index"], "label": row_a["label"],
                                                 "kind": "row_not_found_in_checker"})
                continue
            used.add(best)
            cb = rb[best][2]
            da = {c["column_index"]: c for c in ca}
            db = {c["column_index"]: c for c in cb}
            if sorted(k for k, c in da.items() if c["raw"] is not None) != sorted(k for k, c in db.items() if c["raw"] is not None):
                summary["disagreements"].append({"table": ta["table_id"], "row_index": row_a["row_index"], "label": row_a["label"],
                                                 "kind": "column_count", "a": [c["raw"] for c in ca], "b": [c["raw"] for c in cb]})
            for k in sorted(set(da) & set(db)):
                x, y = da[k], db[k]
                if x["raw"] is None and y["raw"] is None:
                    continue
                n_cmp += 1
                if norm_raw(x["raw"]) == norm_raw(y["raw"]):
                    n_eq += 1
                elif x["value"] is not None and x["value"] == y["value"]:
                    n_eq += 1
                    summary["disagreements"].append({"table": ta["table_id"], "row_index": row_a["row_index"], "label": row_a["label"],
                                                     "kind": "glyph_variant_same_value", "a": x["raw"], "b": y["raw"], "column": k})
                else:
                    summary["disagreements"].append({"table": ta["table_id"], "row_index": row_a["row_index"], "label": row_a["label"],
                                                     "kind": "value_mismatch", "a": x["raw"], "b": y["raw"], "column": k,
                                                     "bbox_a": x["bbox"]})
        summary["matched_tables"].append({"a": ta["table_id"], "b": tb["table_id"], "jaccard": jac, "cells_compared": n_cmp,
                                          "cells_equal": n_eq, "rows_unmatched": n_unmatched, "rows_a": len(ra), "rows_b": len(rb)})
    summary["n_value_mismatch"] = sum(d["kind"] in ("value_mismatch", "column_count", "row_not_found_in_checker") for d in summary["disagreements"])
    return summary


def text_layer_reference(pdf, page_index, footer_frac=0.06):
    """Independent-of-table-assembly reference: every numeric word in the PDF text layer except the bottom
    `footer_frac` of the page (page-number zone; declared policy). Valid for digital pages and for
    rasterisations of them. NOT human gold: it says nothing about structure, labels, roles or hierarchy."""
    import fitz
    from .backends.native_grid import read_words
    page = fitz.open(str(pdf))[page_index]
    H = page.rect.height
    return Counter(norm_raw(w["text"]) for w in read_words(page) if w["numeric"] and w["bbox"][3] < H * (1 - footer_frac))
