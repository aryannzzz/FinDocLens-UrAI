"""Generalized native-PDF table backend (N data columns, multiple tables per page).

Unlike frozen v2 it does not assume two columns or a balance-sheet hierarchy.
Method (all geometry from the PDF text layer, no OCR):
  1. numeric tokens = words matching exact amount/percent grammar (sign glyphs merged),
  2. right edges of numeric tokens are clustered into columns,
  3. each text row is split into *segments* (label + numeric tokens); a non-numeric word after
     numbers starts a new segment, which is how side-by-side tables are separated,
  4. segments with >=2 numerics seed tables keyed by their column set; other rows are attached
     afterwards; headers are collected above the first data row (colspan from word extent).
Limits (declared in `capabilities`): right-aligned numeric columns only; no rotated text; no ruling-line use.
"""
from __future__ import annotations
import re
import statistics
import time
import unicodedata
from pathlib import Path

import fitz

from ..amounts import looks_numeric, parse_token, FRAGMENT_RE
from ..schema import Cell, DocumentPrediction, Header, Row, Table, sha256_file

BACKEND = "native_grid"
JP = re.compile(r"[぀-ヿ㐀-鿿]")
LETTER = re.compile(r"[A-Za-z぀-ヿ㐀-鿿]")
UNIT_RE = re.compile(r"(百万円|千円|万円|円|million\s*yen|thousand\s*yen|JPY|USD|\$)", re.I)
UNIT_CTX = re.compile(r"単位|[（(]\s*(?:百万円|千円|万円|円)\s*[）)]|million|thousand", re.I)
CHANGE_RE = re.compile(r"増減|差異|前期比|前年同期比|前年比|変動|change|diff", re.I)
PCT_RE = re.compile(r"構成比|[%％]|比率|composition", re.I)


def _norm(s):
    return unicodedata.normalize("NFKC", s)


def parse_period(text):
    t = _norm(text).replace(" ", "")
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", t)
    if m:
        return f"{int(m[1]):04d}-{int(m[2]):02d}-{int(m[3]):02d}"
    m = re.search(r"(\d{4})/(\d{1,2})(?:/(\d{1,2}))?", t)
    if m:
        return f"{int(m[1]):04d}-{int(m[2]):02d}" + (f"-{int(m[3]):02d}" if m[3] else "")
    m = re.search(r"(\d{4})年(\d{1,2})月期?", t)
    if m:
        return f"{int(m[1]):04d}-{int(m[2]):02d}"
    return None


def _join(words):
    out = ""
    for w in words:
        if out and not (JP.search(out[-1]) or JP.search(w[0])):
            out += " "
        out += w
    return out


def _union(boxes):
    boxes = [b for b in boxes if b]
    if not boxes:
        return None
    return [round(min(b[0] for b in boxes), 2), round(min(b[1] for b in boxes), 2),
            round(max(b[2] for b in boxes), 2), round(max(b[3] for b in boxes), 2)]


def read_words(page):
    ws = []
    for x0, y0, x1, y1, text, *_ in page.get_text("words"):
        text = text.strip()
        if text:
            ws.append({"text": text, "bbox": [x0, y0, x1, y1], "cy": (y0 + y1) / 2, "h": y1 - y0})
    # merge a bare sign glyph with an adjacent numeric word
    ws.sort(key=lambda w: (round(w["cy"] / 2), w["bbox"][0]))
    merged, skip = [], set()
    for i, w in enumerate(ws):
        if i in skip:
            continue
        if re.fullmatch(r"[△▲−\-+＋]", w["text"]) and i + 1 < len(ws):
            n = ws[i + 1]
            if abs(n["cy"] - w["cy"]) < w["h"] * .5 and 0 <= n["bbox"][0] - w["bbox"][2] < max(2.5, w["h"] * .35) \
                    and looks_numeric(w["text"] + n["text"]):
                merged.append({"text": w["text"] + n["text"], "bbox": [w["bbox"][0], min(w["bbox"][1], n["bbox"][1]),
                               n["bbox"][2], max(w["bbox"][3], n["bbox"][3])], "cy": (w["cy"] + n["cy"]) / 2,
                               "h": max(w["h"], n["h"])})
                skip.add(i + 1)
                continue
        merged.append(w)
    for w in merged:
        w["numeric"] = looks_numeric(w["text"]) and not re.fullmatch(r"(?:19|20)\d{2}", w["text"])
    return merged


def group_rows(words):
    words = sorted(words, key=lambda w: w["cy"])
    rows = []
    for w in words:
        if rows and abs(w["cy"] - rows[-1]["cy"]) <= max(1.5, min(w["h"], rows[-1]["h"]) * .38):
            r = rows[-1]
            r["words"].append(w)
            r["cy"] = statistics.median(x["cy"] for x in r["words"])
            r["h"] = statistics.median(x["h"] for x in r["words"])
        else:
            rows.append({"cy": w["cy"], "h": w["h"], "words": [w]})
    for r in rows:
        r["words"].sort(key=lambda w: w["bbox"][0])
    return rows


def split_segments(row):
    """Split one physical row into [{label_words, nums, trailing_text}] segments."""
    segs, cur = [], {"label": [], "nums": [], "notes": []}
    for w in row["words"]:
        if w["numeric"]:
            cur["nums"].append(w)
        elif not LETTER.search(w["text"]) and FRAGMENT_RE.fullmatch(w["text"]) is None:
            cur["notes"].append(w)          # separator glyphs such as → : kept, not dropped
        else:
            if cur["nums"]:
                segs.append(cur)
                cur = {"label": [], "nums": [], "notes": []}
            cur["label"].append(w)
    segs.append(cur)
    return [s for s in segs if s["label"] or s["nums"]]


def cluster_edges(values, tol):
    groups = []
    for v in sorted(values):
        if groups and abs(v - statistics.mean(groups[-1])) <= tol:
            groups[-1].append(v)
        else:
            groups.append([v])
    return [{"edge": statistics.median(g), "n": len(g)} for g in groups]


def _header_between(rows, cols, y0, y1, colset):
    """True if a row strictly between y0 and y1 has non-numeric text centred over the data columns."""
    edges = sorted(cols[j]["edge"] for j in colset)
    step = edges[1] - edges[0] if len(edges) > 1 else 60
    lo, hi = edges[0] - step * .45, edges[-1] + 12
    for r in rows:
        if y0 + 1 < r["cy"] < y1 - 1:
            hw = [w for w in r["words"] if not w["numeric"] and lo <= (w["bbox"][0] + w["bbox"][2]) / 2 <= hi
                  and w["bbox"][0] >= lo - step * .5 and LETTER.search(w["text"])]
            if hw and not any(w["numeric"] for w in r["words"]):
                return True
    return False


def extract(pdf, page_index=0, **_):
    t0 = time.perf_counter()
    pdf = str(pdf)
    doc = fitz.open(pdf)
    page = doc[page_index]
    W, H = page.rect.width, page.rect.height
    pred = DocumentPrediction(
        document_id=Path(pdf).stem, source_sha256=sha256_file(pdf), backend=BACKEND,
        model_revision="findoclens native_grid 0.1, PyMuPDF " + fitz.__version__, page=page_index,
        page_bbox=[0.0, 0.0, round(W, 2), round(H, 2)],
        capabilities={"cell_bbox": True, "headers": "text+period+role+colspan", "multi_table": True, "ocr": False,
                      "n_columns": "any (right-aligned numeric)", "hierarchy": "indentation heuristic, optional"})
    words = read_words(page)
    n_glyphs = sum(len(w["text"]) for w in words)
    pred.meta["native_glyph_count"] = n_glyphs
    if n_glyphs < 20:
        pred.status = "failed"
        pred.issues.append({"severity": "error", "code": "needs_visual_fallback",
                            "message": f"only {n_glyphs} extractable glyphs; OCR/visual backend required"})
        pred.meta["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        return pred
    rows = group_rows(words)
    nums = [w for w in words if w["numeric"]]
    tol = max(3.0, W * .006)
    cols = [c for c in cluster_edges([w["bbox"][2] for w in nums], tol) if c["n"] >= 3]
    for r in rows:
        r["segs"] = split_segments(r)
        for s in r["segs"]:
            for n in s["nums"]:
                d = [abs(n["bbox"][2] - c["edge"]) for c in cols]
                j = min(range(len(cols)), key=d.__getitem__) if cols else None
                n["col"] = j if j is not None and d[j] <= tol else None
    # ---- pass 1: seed tables from segments with >=2 columned numerics
    tables = []

    def seg_cols(s):
        return {n["col"] for n in s["nums"] if n["col"] is not None}

    def seg_x(s):
        ws = s["label"] + s["nums"]
        return min(w["bbox"][0] for w in ws), max(w["bbox"][2] for w in ws)

    pitch_guess = statistics.median([b["cy"] - a["cy"] for a, b in zip(rows, rows[1:]) if b["cy"] - a["cy"] > 2] or [12])
    for r in rows:
        for s in r["segs"]:
            cs = seg_cols(s)
            if len(cs) < 2:
                continue
            x0, x1 = seg_x(s)
            best = None
            for t in tables:
                if r["cy"] < t["last_y"]:
                    continue
                gap = r["cy"] - t["last_y"]
                if gap > pitch_guess * 3.5:
                    # sparse wide tables (equity statements): identical >=4-column set may bridge a long run of
                    # single-value rows, but never across a header-like text line (that starts a new table)
                    if not (cs == t["cols"] and len(cs) >= 4 and gap <= pitch_guess * 14
                            and not _header_between(rows, cols, t["last_y"], r["cy"], cs)):
                        continue
                if not (x0 <= t["x1"] + 5 and x1 >= t["x0"] - 5):
                    continue
                if cs <= t["cols"] or cs > t["cols"]:
                    ov = len(cs & t["cols"])
                    if ov == min(len(cs), len(t["cols"])) and (best is None or ov > best[0]):
                        best = (ov, t)
            if best:
                t = best[1]
                t["cols"] |= cs
                t["x0"], t["x1"] = min(t["x0"], x0), max(t["x1"], x1)
            else:
                t = {"cols": set(cs), "x0": x0, "x1": x1, "rows": [], "first_y": r["cy"], "last_y": r["cy"]}
                tables.append(t)
            t["rows"].append((r, s))
            t["last_y"] = r["cy"]
    # keep candidates with >=3 seed rows, or a single wide (>=4 column) seed row that pass 2 may extend;
    # candidates are re-checked (>=3 rows) after attachment and every drop is reported, never silent
    kept = [t for t in tables if len(t["rows"]) >= 3 or (len(t["cols"]) >= 4 and len(t["rows"]) >= 1)]
    tables = sorted(kept, key=lambda t: (round(t["first_y"] / (pitch_guess * 2)), t["x0"]))
    # ---- pass 2: attach other rows (single-value rows, label-only rows) that fall inside the table body
    used_ids = {id(s) for t in tables for _, s in t["rows"]}
    for t in tables:
        ys = [r["cy"] for r, _ in t["rows"]]
        pitch = statistics.median([b - a for a, b in zip(ys, ys[1:]) if b - a > 2] or [pitch_guess])
        t["pitch"] = pitch
        for r in rows:
            if not (t["first_y"] - pitch * .9 <= r["cy"] <= t["last_y"] + pitch * .9):
                continue
            for s in r["segs"]:
                if id(s) in used_ids:
                    continue
                cs = seg_cols(s)
                if cs and not cs <= t["cols"]:
                    continue
                if not cs and any(n["col"] is None for n in s["nums"]):
                    continue
                x0, x1 = seg_x(s)
                if not (x0 <= t["x1"] + 5 and x0 >= t["x0"] - 5):
                    continue
                if not cs and not s["label"]:
                    continue
                t["rows"].append((r, s))
                used_ids.add(id(s))
        t["rows"].sort(key=lambda rs: rs[0]["cy"])
        t["first_y"], t["last_y"] = t["rows"][0][0]["cy"], t["rows"][-1][0]["cy"]
        ys = [r["cy"] for r, _ in t["rows"]]
        t["pitch"] = statistics.median([b - a for a, b in zip(ys, ys[1:]) if b - a > 2] or [pitch])   # all rows, not just seeds
    final = []
    for t in tables:
        if len(t["rows"]) >= 3:
            final.append(t)
        else:
            pred.issues.append({"severity": "info", "code": "discarded_small_candidate", "rows": len(t["rows"]),
                                "bbox": [round(t["x0"], 1), round(t["first_y"], 1), round(t["x1"], 1), round(t["last_y"], 1)]})
    tables = sorted(final, key=lambda t: (round(t["first_y"] / (pitch_guess * 2)), t["x0"]))
    # unassigned numerics are reported, never dropped silently
    assigned = {id(n) for t in tables for _, s in t["rows"] for n in s["nums"]}
    stray = [{"raw": n["text"], "bbox": [round(v, 2) for v in n["bbox"]]} for n in nums if id(n) not in assigned]
    if stray:
        pred.meta["unassigned_numeric_tokens"] = stray
        pred.issues.append({"severity": "info", "code": "unassigned_numeric_tokens", "count": len(stray)})
    for ti, t in enumerate(tables):
        pred.tables.append(build_table(t, ti, rows, cols, words, tables, W))
    pred.status = "ok" if pred.tables else "no_tables"
    if not pred.tables:
        pred.issues.append({"severity": "warning", "code": "no_tables_found",
                            "message": "text layer present but no right-aligned multi-column numeric table found"})
    pred.meta["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return pred


def build_table(t, ti, rows, cols, words, all_tables, W):
    colids = sorted(t["cols"], key=lambda j: cols[j]["edge"])
    edges = [cols[j]["edge"] for j in colids]
    # column cells span (previous right edge, own right edge]; header text is centred over the *cell*, not the
    # right-aligned number, so the first cell is extended left by one column step.
    step = (edges[1] - edges[0]) if len(edges) > 1 else 60
    bounds = [edges[0] - step] + edges
    pitch = t["pitch"]
    body = t["rows"]
    first_y = t["first_y"]
    # --- headers: non-numeric words above first row, below the previous table's bottom (if x-overlapping)
    floor = first_y - pitch * 5.2
    for o in all_tables:
        if o is not t and o["last_y"] < first_y and o["x0"] <= t["x1"] and o["x1"] >= t["x0"]:
            floor = max(floor, o["last_y"] + pitch * .6)
    cand = [r for r in rows if floor <= r["cy"] < first_y - pitch * .45]
    in_cols = lambda w: bounds[0] - 4 <= (w["bbox"][0] + w["bbox"][2]) / 2 <= bounds[-1] + 12
    # walk upward from the first data row: label-only heading rows first (body), then header lines,
    # stopping at the first vertical gap that is too large (slide titles, section captions)
    hdr_rows, prev_y, seen_hdr = [], first_y, False
    for r in sorted(cand, key=lambda r: -r["cy"]):
        ws = [w for w in r["words"] if not UNIT_CTX.search(w["text"])]
        hw = [w for w in ws if not w["numeric"] and in_cols(w)]
        if not hw:
            if not seen_hdr and ws and prev_y - r["cy"] <= pitch * 1.75:
                prev_y = r["cy"]
            continue
        if prev_y - r["cy"] > pitch * (1.3 if seen_hdr else 1.75):
            break
        hdr_rows.append(r)
        seen_hdr = True
        prev_y = r["cy"]
    hdr_words = [w for r in hdr_rows for w in r["words"] if not w["numeric"] and in_cols(w) and not UNIT_CTX.search(w["text"])]
    hdr_lines = group_rows([dict(w) for w in hdr_words])
    last_hdr_cy = hdr_lines[-1]["cy"] if hdr_lines else None
    tbl = Table(table_id=f"t{ti}", bbox=None, reading_order=ti, n_data_columns=len(colids),
                capabilities={"cell_bbox": True, "headers": "text+period+role+colspan"})
    ncol = len(colids)
    col_header_text = [[] for _ in range(ncol)]
    hid = 0
    for li, line in enumerate(hdr_lines):
        pieces = []   # (words, covered)
        for w in line["words"]:
            x0, x1 = w["bbox"][0], w["bbox"][2]
            covered = [j for j in range(ncol) if x0 < bounds[j + 1] - 1 and x1 > bounds[j] + 1 and
                       (min(x1, bounds[j + 1]) - max(x0, bounds[j])) > min((bounds[j + 1] - bounds[j]) * .25, (x1 - x0) * .6)]
            if not covered:
                continue
            if pieces and pieces[-1][1] == covered and x0 - pieces[-1][0][-1]["bbox"][2] < w["h"] * .8:
                pieces[-1][0].append(w)
            else:
                pieces.append(([w], covered))
        for ws, covered in pieces:
            text = _join([w["text"] for w in ws])
            h = Header(header_id=f"t{ti}h{hid}", text=text, period=parse_period(text),
                       role=None, bbox=_union([w["bbox"] for w in ws]), colspan=len(covered), rowspan=1,
                       row_start=li, col_start=covered[0], column_indices=covered)
            hid += 1
            tbl.headers.append(h)
            for j in covered:
                col_header_text[j].append((li, h))
    # unit: look wider (above table, near it)
    ctx = [w for r in rows if first_y - pitch * 8 <= r["cy"] < first_y for w in r["words"]
           if bounds[0] - 150 <= w["bbox"][0] <= bounds[-1] + 40]
    unit_text = _join([w["text"] for w in ctx])
    if UNIT_CTX.search(unit_text):
        m = UNIT_RE.search(unit_text)
        tbl.unit = m.group(1) if m else None
    col_period, col_role = [], []
    col_inferred = [False] * ncol
    for j in range(ncol):
        txt = "".join(h.text for _, h in sorted(col_header_text[j], key=lambda z: z[0]))
        per = next((h.period for _, h in col_header_text[j] if h.period), None) or parse_period(txt)
        role = "change_amount" if CHANGE_RE.search(txt) else ("composition_pct" if PCT_RE.search(txt) else None)
        col_period.append(per)
        col_role.append(role)
    for k in range(ncol):
        if col_role[k] is None and not col_header_text[k]:
            toks = [n["text"] for _, sg in body for n in sg["nums"] if n["col"] == colids[k]]
            if len(toks) >= 3 and all(re.search(r"[%％]$", x) for x in toks):
                col_role[k] = "composition_pct"
            elif len(toks) >= 3 and sum(x[0] in "+＋△▲" for x in toks) >= .6 * len(toks):
                col_role[k] = "change_amount"
            col_inferred[k] = col_role[k] is not None
    for h in tbl.headers:
        h.role = next((col_role[j] for j in h.column_indices if col_role[j]), "amount" if h.text else None)
        if h.period is None:
            h.period = next((col_period[j] for j in h.column_indices if col_period[j]), None)
    if not tbl.headers:
        tbl.issues.append({"severity": "warning", "code": "no_header_cells_found"})
    if tbl.unit is None:
        tbl.issues.append({"severity": "warning", "code": "unit_not_detected"})
    # --- body rows (label-only heading rows between the header block and the first data row belong to the body)
    seg_ids = {id(s) for _, s in body}
    pre = []
    for r in rows:
        if r["cy"] >= first_y - pitch * .3 or r["cy"] < floor:
            continue
        if last_hdr_cy is not None and r["cy"] <= last_hdr_cy + pitch * .3:
            continue
        for sg in r["segs"]:
            if sg["nums"] or not sg["label"] or id(sg) in seg_ids:
                continue
            x0 = min(w["bbox"][0] for w in sg["label"])
            owned = any(o is not t and o["x0"] - 5 <= x0 <= o["x1"] + 5 and o["first_y"] - pitch <= r["cy"] <= o["last_y"] + pitch
                        for o in all_tables)
            x1 = max(w["bbox"][2] for w in sg["label"])
            if not owned and x0 < bounds[0] and x1 <= bounds[0] + 2 and not UNIT_CTX.search(_join([w["text"] for w in sg["label"]])):
                pre.append((r, sg))
    body = _merge_wrapped(sorted(pre + body, key=lambda rs: rs[0]["cy"]), pitch)
    label_x = []
    for ri, (r, s) in enumerate(body):
        label = _join([w["text"] for w in s["label"]])
        lb = _union([w["bbox"] for w in s["label"]])
        by_col = {}
        for n in s["nums"]:
            by_col.setdefault(n["col"], []).append(n)
        cells = []
        for k, j in enumerate(colids):
            toks = by_col.get(j, [])
            hdr = next((h for _, h in col_header_text[k]), None)
            hid_ = None
            for _, h in sorted(col_header_text[k], key=lambda z: -z[0]):
                hid_ = h.header_id
                break
            if len(toks) > 1:
                cells.append(Cell(k, hid_, col_period[k], col_role[k] or "amount", " ".join(n["text"] for n in toks),
                                  None, "uncertain", _union([n["bbox"] for n in toks]), BACKEND, "native_pdf",
                                  ["multiple_tokens_in_cell"]))
            elif toks:
                n = toks[0]
                val, status, hint = parse_token(n["text"])
                has_hdr = bool(col_header_text[k])
                role = col_role[k] or ("composition_pct" if hint == "composition_pct" else None) or "amount"
                cells.append(Cell(k, hid_, col_period[k], role, n["text"], val, status,
                                  [round(v, 2) for v in n["bbox"]], BACKEND, "native_pdf",
                                  (["role_inferred_from_column_signs"] if col_inferred[k] else []) if (col_role[k] or has_hdr) else ["role_default_amount"]))
            else:
                cells.append(Cell(k, hid_, col_period[k], col_role[k] or "amount", None, None, "absent_text_cell", None,
                                  BACKEND, "native_pdf"))
        for n in s["nums"]:
            if n["col"] is None:
                cells.append(Cell(-1, None, None, "other", n["text"], None, "uncertain", [round(v, 2) for v in n["bbox"]],
                                  BACKEND, "native_pdf", ["numeric_token_off_column_grid"]))
        trailing = [w for w in s["notes"]]
        used = {id(sg) for tt in all_tables for _, sg in tt["rows"]}
        for sg in r["segs"]:
            if sg is not s and not sg["nums"] and id(sg) not in used and sg["label"] and \
                    min(w["bbox"][0] for w in sg["label"]) >= max(w["bbox"][2] for w in s["nums"] or s["label"]) - 1:
                trailing += sg["label"]
                used.add(id(sg))
        if trailing:
            cells.append(Cell(-1, None, None, "other", _join([w["text"] for w in trailing]), None, "observed",
                              _union([w["bbox"] for w in trailing]), BACKEND, "native_pdf", ["separator_or_note_text"]))
        has_val = any(c.status != "absent_text_cell" and c.column_index >= 0 for c in cells)
        typ = "section" if not has_val else ("total" if re.search(r"合計$|総計$|^計$|小計$", label) else "item")
        row = Row(ri, label or None, label or None, [], _union([w["bbox"] for w in s["label"] + s["nums"] + trailing]),
                  typ, cells)
        if has_val and typ != "section":
            absent = [c.column_index for c in cells if c.status == "absent_text_cell"]
            if absent:
                tbl.issues.append({"severity": "warning", "code": "partial_data_row", "row_index": ri, "label": label,
                                   "absent_columns": absent})
        if lb:
            label_x.append((ri, lb[0]))
        if not label:
            tbl.issues.append({"severity": "warning", "code": "row_without_label", "row_index": ri})
        tbl.rows.append(row)
    _hierarchy(tbl, label_x)
    tbl.bbox = _union([r.bbox for r in tbl.rows] + [h.bbox for h in tbl.headers])
    return tbl


def _merge_wrapped(body, pitch):
    """Attach label-only lines to the nearest number-bearing line when closer than 0.75 pitch.
    Wrapped labels (two text lines) have their numbers vertically centred on the cell, so the label lines can sit
    above *and* below the numeric line; distance, not reading order, decides. Ties go to the following row."""
    numeric = [(r, sg) for r, sg in body if sg["nums"]]
    if not numeric:
        return body
    extra = {id(sg): [] for _, sg in numeric}
    keep = []
    for r, sg in body:
        if sg["nums"]:
            keep.append((r, sg))
            continue
        best = min(numeric, key=lambda rs: (abs(rs[0]["cy"] - r["cy"]), -rs[0]["cy"]))
        if abs(best[0]["cy"] - r["cy"]) < pitch * .75 and sg["label"]:
            extra[id(best[1])].append(sg)
        else:
            keep.append((r, sg))
    out = []
    for r, sg in keep:
        if sg["nums"] and extra[id(sg)]:
            words = sg["label"] + [w for e in extra[id(sg)] for w in e["label"]]
            sg = {"label": sorted(words, key=lambda w: (round(w["cy"], 0), w["bbox"][0])), "nums": sg["nums"],
                  "notes": sg["notes"], "wrapped": True}
        out.append((r, sg))
    return out


def _hierarchy(tbl, label_x):
    xs = sorted(x for _, x in label_x)
    levels = cluster_edges(xs, 2.0)
    has_sections = any(r.type == "section" for r in tbl.rows)
    if len(levels) > 6 or len(levels) < 2 or not has_sections:
        tbl.issues.append({"severity": "info", "code": "hierarchy_not_inferred",
                           "message": f"{len(levels)} label indents, section rows={has_sections}; "
                                      "indentation hierarchy needs heading rows as anchors; parent_path left empty"})
        return
    stack = []   # (x, label)
    xmap = dict(label_x)
    for row in tbl.rows:
        if row.row_index not in xmap:
            continue
        x = xmap[row.row_index]
        while stack and stack[-1][0] >= x - 2.0:
            stack.pop()
        row.parent_path = [lbl for _, lbl in stack]
        stack.append((x, row.label))
