"""Docling (TableFormer) backend, run in the optional model venv.

`extract`      : DocumentConverter + PdfPipelineOptions(do_table_structure=True, TableFormerMode.ACCURATE),
                 OCR off (digital PDFs: text comes from the PDF text layer), `do_cell_matching` selectable.
`extract_ocr`  : same pipeline with full-page OCR forced (for image-only pages).
The raw DoclingDocument JSON and per-table Markdown are saved next to the normalised prediction;
the normalisation (grid -> common schema) never adds fields Docling did not produce.
"""
from __future__ import annotations
import json
import re
import time
from pathlib import Path

import os
os.environ.setdefault("HF_HOME", str(Path(__file__).resolve().parents[2] / ".cache" / "hf"))   # keep weights repo-local/removable

from ..amounts import looks_numeric, parse_token
from ..ocr_flags import suspect_variant_chars
from ..schema import Cell, DocumentPrediction, Header, Row, Table, sha256_file
from .native_grid import CHANGE_RE, PCT_RE, UNIT_RE, UNIT_CTX, parse_period

_CONVERTERS = {}
_LAST_LOAD_MS = {}


def _versions():
    import importlib.metadata as md
    out = {}
    for n in ("docling", "docling-core", "docling-ibm-models", "docling-parse", "torch", "rapidocr", "easyocr"):
        try:
            out[n] = md.version(n)
        except md.PackageNotFoundError:
            pass
    return out


def get_converter(cell_matching=True, ocr=None, mode="accurate", threads=None, ocr_model_size=None):
    key = (cell_matching, ocr, mode, threads, ocr_model_size)
    if key in _CONVERTERS:
        return _CONVERTERS[key], 0.0
    t0 = time.perf_counter()
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
    from docling.document_converter import DocumentConverter, PdfFormatOption
    opts = PdfPipelineOptions()
    opts.do_table_structure = True
    opts.table_structure_options.do_cell_matching = cell_matching
    opts.table_structure_options.mode = TableFormerMode.ACCURATE if mode == "accurate" else TableFormerMode.FAST
    opts.do_ocr = bool(ocr)
    if ocr:
        opts.ocr_options = _ocr_options(ocr)
        if ocr_model_size:
            opts.ocr_options.model_size = ocr_model_size
        opts.ocr_options.force_full_page_ocr = True
    if threads:
        from docling.datamodel.accelerator_options import AcceleratorOptions
        opts.accelerator_options = AcceleratorOptions(num_threads=threads, device="cpu")
    conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    _CONVERTERS[key] = conv
    return conv, (time.perf_counter() - t0) * 1000


def _arrow_numeric(text):
    parts = text.split()
    return len(parts) > 1 and looks_numeric(parts[-1]) and all(not re.search(r"[\w\u3040-\u9fff]", p) for p in parts[:-1])


def _ocr_options(engine):
    if engine == "rapidocr":
        from docling.datamodel.pipeline_options import RapidOcrOptions
        return RapidOcrOptions(lang=[os.environ.get("FINDOCLENS_RAPID_LANG", "iso:ja")])
    if engine == "easyocr":
        from docling.datamodel.pipeline_options import EasyOcrOptions
        return EasyOcrOptions(lang=["ja", "en"])
    if engine == "tesseract":
        from docling.datamodel.pipeline_options import TesseractCliOcrOptions
        return TesseractCliOcrOptions(lang=["jpn", "eng"])
    raise ValueError(engine)


def _box(bb, page_h):
    if bb is None:
        return None
    try:
        bb = bb.to_top_left_origin(page_h)
    except Exception:
        pass
    return [round(float(bb.l), 2), round(float(bb.t), 2), round(float(bb.r), 2), round(float(bb.b), 2)]


def extract(pdf, page_index=0, out_dir=None, cell_matching=True, ocr=None, mode="accurate", threads=None, ocr_model_size=None, **_):
    pdf = str(pdf)
    t_all = time.perf_counter()
    import fitz
    page_rect = fitz.open(pdf)[page_index].rect
    pred = DocumentPrediction(
        document_id=Path(pdf).stem, source_sha256=sha256_file(pdf), backend="docling" + ("_ocr" if ocr else ""),
        model_revision=None, page=page_index, page_bbox=[0.0, 0.0, round(page_rect.width, 2), round(page_rect.height, 2)],
        capabilities={"cell_bbox": True, "headers": "tableformer column_header flags", "multi_table": True,
                      "ocr": bool(ocr), "n_columns": "any", "cell_matching": cell_matching})
    conv, load_ms = get_converter(cell_matching, ocr, mode, threads, ocr_model_size)
    t0 = time.perf_counter()
    res = conv.convert(pdf, page_range=(page_index + 1, page_index + 1))
    infer_ms = (time.perf_counter() - t0) * 1000
    doc = res.document
    pred.meta.update({"device": "cpu", "converter_load_ms": round(load_ms, 1), "convert_ms": round(infer_ms, 1),
                      "versions": _versions(), "table_structure_mode": mode, "do_cell_matching": cell_matching,
                      "ocr_engine": ocr, "ocr_model_size": ocr_model_size, "docling_status": str(getattr(res, "status", None))})
    if out_dir:
        out_dir = Path(out_dir)
        (out_dir / "docling_document.json").write_text(json.dumps(doc.export_to_dict(), ensure_ascii=False), encoding="utf-8")
        md = []
        for i, t in enumerate(doc.tables):
            md.append(f"## docling table {i}\n\n" + t.export_to_markdown(doc))
        (out_dir / "docling_tables.md").write_text("\n\n".join(md), encoding="utf-8")
        pred.meta["raw_artifacts"] = ["docling_document.json", "docling_tables.md"]
    gray, gscale = (None, 1.0)
    if ocr:
        try:
            gray, gscale = _page_gray(pdf, page_index)
        except Exception as exc:      # the ink check is optional evidence; its absence is recorded
            pred.issues.append({"severity": "info", "code": "ink_check_unavailable", "message": repr(exc)[:200]})
    for ti, item in enumerate(doc.tables):
        prov = item.prov[0] if item.prov else None
        page_no = prov.page_no if prov else 1
        page_h = doc.pages[page_no].size.height if page_no in doc.pages else page_rect.height
        pred.tables.append(_map_table(item, ti, page_h, ocr, gray, gscale))
    pred.status = "ok" if pred.tables else "no_tables"
    empty = [t.table_id for t in pred.tables if not any(c.status != "absent_text_cell" and c.column_index >= 0 for r in t.rows for c in r.cells)]
    if empty:
        pred.issues.append({"severity": "error", "code": "table_without_numeric_cells", "tables": empty})
        pred.status = "failed" if len(empty) == len(pred.tables) else "partial"
    if not pred.tables:
        pred.issues.append({"severity": "warning", "code": "no_tables_found", "message": "Docling layout/TableFormer found no table"})
    pred.meta["elapsed_ms"] = round((time.perf_counter() - t_all) * 1000, 1)
    return pred


def extract_ocr(pdf, page_index=0, out_dir=None, engine="rapidocr", **kw):
    return extract(pdf, page_index, out_dir=out_dir, ocr=engine, **kw)


def _page_gray(pdf, page_index, dpi=200):
    import fitz
    import numpy as np
    pix = fitz.open(pdf)[page_index].get_pixmap(dpi=dpi, colorspace=fitz.csGRAY, alpha=False)
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w), dpi / 72.0


def _flag_ink_in_empty_slots(tbl, gray, scale):
    """OCR detectors do not box a lone thin `－`, so a printed placeholder looks like an empty cell. For an empty slot in a row
    that has data, look at the page pixels where the slot should be (column x-extent from the other cells of that column,
    row y-extent from the other cells of that row, 20 % trimmed top/bottom to avoid rules). Ink there turns the slot from
    `absent_text_cell` into `uncertain` with a review issue. No glyph is guessed: raw stays null."""
    import statistics
    col_boxes = {}
    for r in tbl.rows:
        for c in r.cells:
            if c.column_index >= 0 and c.bbox:
                col_boxes.setdefault(c.column_index, []).append(c.bbox)
    for r in tbl.rows:
        row_boxes = [c.bbox for c in r.cells if c.column_index >= 0 and c.bbox]
        if r.type == "section" or not row_boxes:
            continue
        top, bot = statistics.median(b[1] for b in row_boxes), statistics.median(b[3] for b in row_boxes)
        flagged = []
        for c in r.cells:
            if c.column_index < 0 or c.status != "absent_text_cell" or c.column_index not in col_boxes:
                continue
            x0 = statistics.median(b[0] for b in col_boxes[c.column_index])
            x1 = statistics.median(b[2] for b in col_boxes[c.column_index])
            y0, y1 = top + .2 * (bot - top), bot - .2 * (bot - top)
            crop = gray[int(y0 * scale):int(y1 * scale) + 1, int(x0 * scale):int(x1 * scale) + 1]
            if crop.size and int((crop < 200).sum()) >= 8:      # thin anti-aliased strokes are light grey, not black
                c.status = "uncertain"
                c.bbox = [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)]
                c.notes.append("ink_in_empty_ocr_slot:possible_dropped_placeholder; bbox derived from sibling cells")
                flagged.append(c.column_index)
        if flagged:
            for i in list(tbl.issues):      # the slot is no longer "absent": it is reported by the ink issue instead
                if i.get("code") == "partial_data_row" and i.get("row_index") == r.row_index:
                    i["absent_columns"] = [k for k in i["absent_columns"] if k not in flagged]
                    if not i["absent_columns"]:
                        tbl.issues.remove(i)
            tbl.issues.append({"severity": "warning", "code": "ocr_possible_dropped_placeholder", "row_index": r.row_index,
                               "label": r.label, "columns": flagged,
                               "message": "page pixels show ink where OCR returned no text (e.g. a thin － placeholder); verify against the image"})


def _map_table(item, ti, page_h, ocr, gray=None, gscale=1.0):
    data = item.data
    nr, nc = data.num_rows, data.num_cols
    ek = "ocr" if ocr else "native_pdf"
    seen, cells = set(), []
    for c in data.table_cells:
        key = (c.start_row_offset_idx, c.start_col_offset_idx)
        if key in seen:
            continue
        seen.add(key)
        cells.append(c)
    grid = {}
    for c in cells:
        grid[(c.start_row_offset_idx, c.start_col_offset_idx)] = c
    hdr_rows = sorted({c.start_row_offset_idx for c in cells if getattr(c, "column_header", False)})
    first_body = (max(hdr_rows) + 1) if hdr_rows else 0
    tbl = Table(table_id=f"t{ti}", bbox=_box(item.prov[0].bbox, page_h) if item.prov else None, reading_order=ti,
                capabilities={"cell_bbox": True, "headers": "tableformer column_header flags", "raw_grid": f"{nr}x{nc}"})
    tbl.grid = [{"r0": c.start_row_offset_idx, "r1": c.end_row_offset_idx, "c0": c.start_col_offset_idx, "c1": c.end_col_offset_idx,
                 "text": c.text, "header": bool(getattr(c, "column_header", False)), "bbox": _box(c.bbox, page_h)} for c in cells]
    # which columns are numeric data columns?
    ncount = {}
    for (r, c), cell in grid.items():
        if r >= first_body and cell.text.strip():
            n, tot = ncount.get(c, (0, 0))
            ncount[c] = (n + looks_numeric(cell.text), tot + 1)
    data_cols = [c for c in range(nc) if ncount.get(c, (0, 0))[1] and ncount[c][0] / ncount[c][1] >= .5]
    # A numeric body cell merged over several columns/rows only has its start slot in the grid. The columns it covers are
    # data columns too (otherwise the merged value would silently shrink the table); the covered slots stay empty + flagged.
    owner = {}
    for c in cells:
        for rr in range(c.start_row_offset_idx, c.end_row_offset_idx):
            for cc in range(c.start_col_offset_idx, c.end_col_offset_idx):
                if (rr, cc) != (c.start_row_offset_idx, c.start_col_offset_idx):
                    owner[(rr, cc)] = c
    for c in cells:
        if c.start_row_offset_idx >= first_body and c.text.strip() and looks_numeric(c.text) and c.start_col_offset_idx in data_cols:
            data_cols = sorted(set(data_cols) | set(range(c.start_col_offset_idx, c.end_col_offset_idx)))
    label_cols = [c for c in range(nc) if c not in data_cols and c < (data_cols[0] if data_cols else nc)]
    tbl.n_data_columns = len(data_cols)
    col_hdr = {c: [] for c in data_cols}
    hid = 0
    for (r, c), cell in sorted(grid.items()):
        if r < first_body and cell.text.strip():
            span_cols = list(range(cell.start_col_offset_idx, cell.end_col_offset_idx))
            idx = [data_cols.index(x) for x in span_cols if x in data_cols]
            h = Header(header_id=f"t{ti}h{hid}", text=cell.text.strip(), period=parse_period(cell.text), role=None,
                       bbox=_box(cell.bbox, page_h), colspan=cell.end_col_offset_idx - cell.start_col_offset_idx,
                       rowspan=cell.end_row_offset_idx - cell.start_row_offset_idx, row_start=r, col_start=c, column_indices=idx)
            hid += 1
            tbl.headers.append(h)
            for k in idx:
                col_hdr[data_cols[k]].append(h)
    col_period, col_role = {}, {}
    for c in data_cols:
        txt = "".join(h.text for h in col_hdr[c])
        col_period[c] = next((h.period for h in col_hdr[c] if h.period), None)
        col_role[c] = "change_amount" if CHANGE_RE.search(txt) else ("composition_pct" if PCT_RE.search(txt) else None)
    for h in tbl.headers:
        h.role = next((col_role[data_cols[k]] for k in h.column_indices if col_role[data_cols[k]]), "amount")
    tbl.issues.append({"severity": "info", "code": "hierarchy_not_inferred",
                       "message": "Docling/TableFormer output carries no account hierarchy; parent_path left empty"})
    if not tbl.headers:
        tbl.issues.append({"severity": "warning", "code": "no_header_cells_found"})
    htexts = [h.text for h in tbl.headers if h.row_start == (min(h2.row_start for h2 in tbl.headers))]
    if len(htexts) != len(set(htexts)):
        tbl.issues.append({"severity": "warning", "code": "repeated_header_text_possible_side_by_side_tables",
                           "message": "identical header text appears more than once in the top header row"})
    other_cols = [c for c in range(nc) if c not in data_cols and c not in label_cols]
    # merged body cells: report every span explicitly. A label merged over rows is inherited by the covered rows (marked, raw_label
    # null: the covered row does not print it); a merged data cell is NOT copied into the covered slots (they stay empty) and is flagged.
    for c in cells:
        if c.start_row_offset_idx < first_body or not c.text.strip():
            continue
        rows_span = list(range(c.start_row_offset_idx, c.end_row_offset_idx))
        cols_span = list(range(c.start_col_offset_idx, c.end_col_offset_idx))
        if len(rows_span) == 1 and len(cols_span) == 1:
            continue
        if any(x in label_cols for x in cols_span) and len(rows_span) > 1:
            tbl.issues.append({"severity": "warning", "code": "body_rowspan_label_inherited", "label": c.text.strip(),
                               "rows": [x - first_body for x in rows_span],
                               "message": "label cell merged over several rows: covered rows inherit the label text (raw_label null); association inferred from the grid span"})
        if any(x in data_cols for x in cols_span):
            tbl.issues.append({"severity": "warning", "code": "body_cell_span_unsupported", "text": c.text.strip(),
                               "rows": [x - first_body for x in rows_span], "columns": [data_cols.index(x) for x in cols_span if x in data_cols],
                               "message": "data cell merged over several rows/columns: the value is kept in its first slot only; covered slots are left empty, not copied"})
    for r in range(first_body, nr):
        row_cells = [grid.get((r, c)) for c in range(nc)]
        own = [grid[(r, c)].text.strip() for c in label_cols if (r, c) in grid]
        # only a label that STARTS ABOVE this row (a row span) is inherited; a column span in this same row is already in `own`
        inherited, seen_owner = [], set()
        for c in label_cols:
            o = owner.get((r, c))
            if (r, c) not in grid and o is not None and first_body <= o.start_row_offset_idx < r and id(o) not in seen_owner:
                seen_owner.add(id(o))
                inherited.append(o.text.strip())
        label = "".join(own + inherited) if inherited else "".join(own)
        raw_label = "".join(own) or None
        out = []
        for k, c in enumerate(data_cols):
            cell = grid.get((r, c))
            text = cell.text.strip() if cell else ""
            hid_ = col_hdr[c][-1].header_id if col_hdr[c] else None
            if not text:
                out.append(Cell(k, hid_, col_period[c], col_role[c] or "amount", None, None, "absent_text_cell",
                                _box(cell.bbox, page_h) if cell else None, "docling", ek))
            elif looks_numeric(text) or _arrow_numeric(text):
                core = text if looks_numeric(text) else text.split()[-1]
                v, st, hint = parse_token(core)
                out.append(Cell(k, hid_, col_period[c], col_role[c] or ("composition_pct" if hint == "composition_pct" else "amount"),
                                text, v, st, _box(cell.bbox, page_h), "docling", ek,
                                [] if core == text else ["raw_has_non_numeric_prefix_glyph"]))
            else:
                out.append(Cell(k, hid_, col_period[c], col_role[c] or "amount", text, None, "uncertain",
                                _box(cell.bbox, page_h), "docling", ek, ["non_numeric_text_in_data_column"]))
        n_data_cells = sum(c.status != "absent_text_cell" for c in out)
        for c in other_cols:        # text outside label/data columns is kept, never dropped
            cell = grid.get((r, c))
            if cell and cell.text.strip():
                out.append(Cell(-1, None, None, "other", cell.text.strip(), None, "observed", _box(cell.bbox, page_h), "docling", ek,
                                [f"grid_col={c}"]))
        has = n_data_cells > 0
        typ = "section" if not has else ("total" if re.search(r"合計$|総計$|小計$", label) else "item")
        boxes = [x.bbox for x in out if x.bbox]
        tbl.rows.append(Row(r - first_body, label or None, raw_label, [], None, typ, out))
        del boxes
        absent = [c.column_index for c in out if c.status == "absent_text_cell"]
        if has and typ != "section" and absent:       # same explicit signal native_grid gives for a row with an empty slot
            tbl.issues.append({"severity": "warning", "code": "partial_data_row", "row_index": r - first_body, "label": label,
                               "absent_columns": absent})
        flagged = suspect_variant_chars(label) if ocr else {}
        if flagged:
            tbl.issues.append({"severity": "warning", "code": "ocr_suspect_variant_glyph", "row_index": r - first_body, "label": label,
                               "suspected_japanese_forms": flagged,
                               "message": "recognised glyph is a non-Japanese kanji form; raw text left unchanged for review"})
    if ocr and gray is not None:
        _flag_ink_in_empty_slots(tbl, gray, gscale)
    return tbl


def _shift(box, dx, dy):
    return None if box is None else [round(box[0] + dx, 2), round(box[1] + dy, 2), round(box[2] + dx, 2), round(box[3] + dy, 2)]


def extract_regions(pdf, page_index=0, out_dir=None, cell_matching=True, pad=6.0, **kw):
    """Hybrid ablation: native_grid proposes table regions from the text layer; Docling TableFormer runs once per region.

    Tests whether Docling's table *flattening* comes from page-level region detection (one layout box over several tables)
    or from the structure model. Needs a text layer for proposals; without one it falls back to the whole page and says so.
    Region crops keep the vector text layer (`show_pdf_page(clip=...)`); all coordinates are shifted back to page space.
    """
    import tempfile
    import fitz
    from . import native_grid
    pdf = str(pdf)
    t_all = time.perf_counter()
    src = fitz.open(pdf)
    page = src[page_index]
    props = native_grid.extract(pdf, page_index)
    pred = DocumentPrediction(
        document_id=Path(pdf).stem, source_sha256=sha256_file(pdf), backend="docling_regions", model_revision=None, page=page_index,
        page_bbox=[0.0, 0.0, round(page.rect.width, 2), round(page.rect.height, 2)],
        capabilities={"cell_bbox": True, "headers": "tableformer column_header flags", "multi_table": True, "ocr": False,
                      "region_proposals": "native_grid text-layer tables (needs a text layer)", "cell_matching": cell_matching})
    regions = [t.bbox for t in props.tables if t.bbox]
    pred.meta.update({"device": "cpu", "versions": _versions(), "region_proposals": regions, "proposal_backend": "native_grid"})
    if not regions:
        pred.issues.append({"severity": "warning", "code": "no_region_proposals_whole_page_fallback"})
        sub = extract(pdf, page_index, out_dir=out_dir, cell_matching=cell_matching, **kw)
        sub.backend, sub.issues = "docling_regions", pred.issues + sub.issues
        return sub
    with tempfile.TemporaryDirectory(prefix="fdl-regions-") as tmp:
        for k, bb in enumerate(regions):
            r = fitz.Rect(bb) + (-pad, -pad, pad, pad)
            r &= page.rect
            dst = fitz.open()
            p = dst.new_page(width=r.width, height=r.height)
            p.show_pdf_page(p.rect, src, page_index, clip=r)
            path = Path(tmp) / f"region_{k}.pdf"
            dst.save(path)
            sub_out = None
            if out_dir:
                sub_out = Path(out_dir) / f"region_{k}"
                sub_out.mkdir(parents=True, exist_ok=True)
            sub = extract(path, 0, out_dir=sub_out, cell_matching=cell_matching, **kw)
            for j, t in enumerate(sub.tables):
                t.table_id = f"r{k}t{j}"
                t.reading_order = len(pred.tables)
                t.bbox = _shift(t.bbox, r.x0, r.y0)
                for h in t.headers:
                    h.bbox = _shift(h.bbox, r.x0, r.y0)
                for row in t.rows:
                    for c in row.cells:
                        c.bbox = _shift(c.bbox, r.x0, r.y0)
                for g in t.grid or []:
                    g["bbox"] = _shift(g["bbox"], r.x0, r.y0)
                pred.tables.append(t)
            if not sub.tables:
                pred.issues.append({"severity": "warning", "code": "omitted_table", "region": k, "bbox": [round(v, 2) for v in r],
                                    "message": "text-layer table region proposed by native_grid; Docling returned no table for it"})
            pred.issues += [dict(i, region=k) for i in sub.issues]
            pred.meta.setdefault("region_runs", []).append({"region": k, "bbox": [round(v, 2) for v in r], "convert_ms": sub.meta.get("convert_ms"),
                                                              "tables_returned": len(sub.tables)})
    pred.status = "ok" if pred.tables else "no_tables"
    if any(i["code"] == "table_without_numeric_cells" for i in pred.issues):
        pred.status = "partial"
    pred.meta["elapsed_ms"] = round((time.perf_counter() - t_all) * 1000, 1)
    return pred
