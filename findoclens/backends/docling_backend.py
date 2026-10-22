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

from ..amounts import looks_numeric, parse_token
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


def get_converter(cell_matching=True, ocr=None, mode="accurate", threads=None):
    key = (cell_matching, ocr, mode, threads)
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
        opts.ocr_options.force_full_page_ocr = True
    if threads:
        from docling.datamodel.accelerator_options import AcceleratorOptions
        opts.accelerator_options = AcceleratorOptions(num_threads=threads, device="cpu")
    conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    _CONVERTERS[key] = conv
    return conv, (time.perf_counter() - t0) * 1000


def _ocr_options(engine):
    if engine == "rapidocr":
        from docling.datamodel.pipeline_options import RapidOcrOptions
        return RapidOcrOptions()
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


def extract(pdf, page_index=0, out_dir=None, cell_matching=True, ocr=None, mode="accurate", threads=None, **_):
    pdf = str(pdf)
    t_all = time.perf_counter()
    import fitz
    page_rect = fitz.open(pdf)[page_index].rect
    pred = DocumentPrediction(
        document_id=Path(pdf).stem, source_sha256=sha256_file(pdf), backend="docling" + ("_ocr" if ocr else ""),
        model_revision=None, page=page_index, page_bbox=[0.0, 0.0, round(page_rect.width, 2), round(page_rect.height, 2)],
        capabilities={"cell_bbox": True, "headers": "tableformer column_header flags", "multi_table": True,
                      "ocr": bool(ocr), "n_columns": "any", "cell_matching": cell_matching})
    conv, load_ms = get_converter(cell_matching, ocr, mode, threads)
    t0 = time.perf_counter()
    res = conv.convert(pdf, page_range=(page_index + 1, page_index + 1))
    infer_ms = (time.perf_counter() - t0) * 1000
    doc = res.document
    pred.meta.update({"device": "cpu", "converter_load_ms": round(load_ms, 1), "convert_ms": round(infer_ms, 1),
                      "versions": _versions(), "table_structure_mode": mode, "do_cell_matching": cell_matching,
                      "ocr_engine": ocr, "docling_status": str(getattr(res, "status", None))})
    if out_dir:
        out_dir = Path(out_dir)
        (out_dir / "docling_document.json").write_text(json.dumps(doc.export_to_dict(), ensure_ascii=False), encoding="utf-8")
        md = []
        for i, t in enumerate(doc.tables):
            md.append(f"## docling table {i}\n\n" + t.export_to_markdown(doc))
        (out_dir / "docling_tables.md").write_text("\n\n".join(md), encoding="utf-8")
        pred.meta["raw_artifacts"] = ["docling_document.json", "docling_tables.md"]
    for ti, item in enumerate(doc.tables):
        prov = item.prov[0] if item.prov else None
        page_no = prov.page_no if prov else 1
        page_h = doc.pages[page_no].size.height if page_no in doc.pages else page_rect.height
        pred.tables.append(_map_table(item, ti, page_h, ocr))
    pred.status = "ok" if pred.tables else "no_tables"
    if not pred.tables:
        pred.issues.append({"severity": "warning", "code": "no_tables_found", "message": "Docling layout/TableFormer found no table"})
    pred.meta["elapsed_ms"] = round((time.perf_counter() - t_all) * 1000, 1)
    return pred


def extract_ocr(pdf, page_index=0, out_dir=None, engine="rapidocr", **kw):
    return extract(pdf, page_index, out_dir=out_dir, ocr=engine, **kw)


def _map_table(item, ti, page_h, ocr):
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
    # which columns are numeric data columns?
    ncount = {}
    for (r, c), cell in grid.items():
        if r >= first_body and cell.text.strip():
            n, tot = ncount.get(c, (0, 0))
            ncount[c] = (n + looks_numeric(cell.text), tot + 1)
    data_cols = [c for c in range(nc) if ncount.get(c, (0, 0))[1] and ncount[c][0] / ncount[c][1] >= .5]
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
    if not tbl.headers:
        tbl.issues.append({"severity": "warning", "code": "no_header_cells_found"})
    for r in range(first_body, nr):
        row_cells = [grid.get((r, c)) for c in range(nc)]
        label = "".join(grid[(r, c)].text.strip() for c in label_cols if (r, c) in grid)
        out = []
        for k, c in enumerate(data_cols):
            cell = grid.get((r, c))
            text = cell.text.strip() if cell else ""
            hid_ = col_hdr[c][-1].header_id if col_hdr[c] else None
            if not text:
                out.append(Cell(k, hid_, col_period[c], col_role[c] or "amount", None, None, "absent_text_cell",
                                _box(cell.bbox, page_h) if cell else None, "docling", ek))
            elif looks_numeric(text):
                v, st, hint = parse_token(text)
                out.append(Cell(k, hid_, col_period[c], col_role[c] or ("composition_pct" if hint == "composition_pct" else "amount"),
                                text, v, st, _box(cell.bbox, page_h), "docling", ek))
            else:
                out.append(Cell(k, hid_, col_period[c], col_role[c] or "amount", text, None, "uncertain",
                                _box(cell.bbox, page_h), "docling", ek, ["non_numeric_text_in_data_column"]))
        has = any(c.status != "absent_text_cell" for c in out)
        typ = "section" if not has else ("total" if re.search(r"合計$|総計$|小計$", label) else "item")
        boxes = [x.bbox for x in out if x.bbox]
        tbl.rows.append(Row(r - first_body, label or None, label or None, [], None, typ, out))
        del boxes
    return tbl
