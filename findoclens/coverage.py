"""Source-token coverage: which numeric tokens of the PDF text layer ended up in the extracted structure?

This is a *completeness diagnostic*, not a correctness check, and it does not assume every number on a page is a financial cell.
An unassigned numeric token is `significant` only when it is structurally part of something table-like:
  * it lies inside the footprint of an extracted table (x-extent, and y-extent widened by one row pitch), or
  * it is part of a vertical stack: >=2 unassigned tokens sharing a column alignment (right/left/centre edge) at regular spacing, or
  * it shares a text row with another unassigned numeric token.
Everything else (a page number, a lone amount in prose, a date) is `isolated` and reported at info level only.
Bare 1900-2099 integers are period-header candidates; they only count when they sit in a table footprint but in no cell or header.
Without a text layer (raster pages) nothing can be reconciled and the caller must treat completeness as unverified.
"""
from __future__ import annotations
import statistics

import fitz

from .amounts import is_placeholder
from .backends.native_grid import anchor, read_words


def page_numeric_tokens(page):
    """Numeric tokens of the text layer, including bare-year candidates (flagged `yearlike`)."""
    from .amounts import looks_numeric
    toks = []
    for w in read_words(page):
        if w["numeric"] or (w.get("yearlike") and looks_numeric(w["text"])):
            toks.append(dict(raw=w["text"], bbox=[round(v, 2) for v in w["bbox"]], cy=w["cy"], h=w["h"], yearlike=bool(w.get("yearlike"))))
    return toks


def _center(b):
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


def _inside(point, box, pad=1.0):
    return box[0] - pad <= point[0] <= box[2] + pad and box[1] - pad <= point[1] <= box[3] + pad


def classify_unassigned(tokens, footprints, pitch, tol):
    """Split unassigned tokens into (significant, isolated). `footprints` are table boxes [x0,y0,x1,y1].
    A bare dash is a placeholder only inside a table; elsewhere it is punctuation (e.g. a "- 4 -" page footer), so dashes
    never form stacks/rows on their own and never make their neighbours significant."""
    significant, isolated = [], []
    real = [t for t in tokens if not is_placeholder(t["raw"])]
    for k, t in enumerate(tokens):
        cx, cy = _center(t["bbox"])
        reason = None
        for f in footprints:
            if f[0] - 5 <= cx <= f[2] + 5 and f[1] - pitch <= cy <= f[3] + pitch:
                reason = "inside_table_region"
                break
        if reason is None:
            for m in ("right", "left", "center"):
                a = anchor({"bbox": t["bbox"]}, m)
                peers = [o for o in real if o is not t and abs(anchor({"bbox": o["bbox"]}, m) - a) <= tol
                         and abs(_center(o["bbox"])[1] - cy) <= pitch * 3.5]
                if peers:
                    reason = f"column_stack_{m}"
                    break
        if reason is None and not is_placeholder(t["raw"]) and \
                any(o is not t and abs(_center(o["bbox"])[1] - cy) <= max(1.5, t["h"] * .38) for o in real):
            reason = "same_row_as_another_unassigned_token"
        (significant if reason else isolated).append(dict(raw=t["raw"], bbox=t["bbox"], reason=reason) if reason else dict(raw=t["raw"], bbox=t["bbox"]))
    key = lambda d: (round(d["bbox"][1]), d["bbox"][0])
    return sorted(significant, key=key), sorted(isolated, key=key)


def _typical_pitch(boxes):
    ys = sorted(_center(b)[1] for b in boxes)
    gaps = [b - a for a, b in zip(ys, ys[1:]) if b - a > 2]
    return statistics.median(gaps) if gaps else 12.0


def reconcile_prediction(pdf, pred, page_index=0):
    """Reconcile the text layer's numeric tokens with ANY prediction dict (findoclens-0.1 or benchmark-1.0 shaped).
    A token is covered when its centre lies in a cell box or header box of the prediction (cells without a box cannot cover)."""
    page = fitz.open(str(pdf))[page_index]
    tokens = page_numeric_tokens(page)
    cover, footprints = [], []
    for t in pred.get("tables", []):
        if t.get("bbox"):
            footprints.append(t["bbox"])
        cover += [h["bbox"] for h in t.get("headers", []) if h.get("bbox")]
        for r in t.get("rows", []):
            cover += [c["bbox"] for c in r.get("cells", []) if c.get("bbox")]
            if r.get("bbox") and not r.get("cells"):
                cover.append(r["bbox"])
    pitch = _typical_pitch([t["bbox"] for t in tokens]) if len(tokens) > 1 else 12.0
    tol = max(3.0, page.rect.width * .006)
    covered, unassigned = 0, []
    for t in tokens:
        c = _center(t["bbox"])
        if any(_inside(c, b) for b in cover):
            covered += 1
        elif t["yearlike"] and not any(f[0] - 5 <= c[0] <= f[2] + 5 and f[1] - pitch <= c[1] <= f[3] + pitch for f in footprints):
            continue                      # a bare year outside every table is page text
        else:
            unassigned.append(t)
    significant, isolated = classify_unassigned(unassigned, footprints, pitch, tol)
    return dict(total=len(tokens), covered=covered, unassigned=len(unassigned), significant=significant, isolated=isolated)
