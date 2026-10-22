"""Frozen v2 native parser wrapped as a backend. `baseline_v2/` is imported unmodified."""
from __future__ import annotations
import importlib.util
import time
from pathlib import Path

import fitz

from ..schema import (Cell, DocumentPrediction, Header, Row, Table, sha256_file)

_ROOT = Path(__file__).resolve().parents[2]
_mod = None


def _v2():
    global _mod
    if _mod is None:
        spec = importlib.util.spec_from_file_location("parser_v2_frozen", _ROOT / "baseline_v2" / "parser_v2.py")
        _mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_mod)
    return _mod


def extract(pdf, page_index=0, **_):
    t0 = time.perf_counter()
    pdf = str(pdf)
    doc = fitz.open(pdf)
    page = doc[page_index]
    pred = DocumentPrediction(
        document_id=Path(pdf).stem, source_sha256=sha256_file(pdf), backend="native_v2",
        model_revision="baseline_v2 (tag v2-frozen), PyMuPDF " + fitz.__version__,
        page=page_index, page_bbox=[0.0, 0.0, round(page.rect.width, 2), round(page.rect.height, 2)],
        capabilities={"cell_bbox": True, "headers": "dates_only", "multi_table": False, "ocr": False,
                      "n_columns": "exactly_2", "unit_detection": "thousand_JPY_only"})
    try:
        r = _v2().parse_page(page, page_index + 1)
    except Exception as e:  # never swallow: surface as failed
        pred.status = "failed"
        pred.issues.append({"severity": "error", "code": "backend_exception", "message": repr(e)})
        pred.meta["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        return pred
    pred.issues.extend({"source": "native_v2", **i} for i in r["issues"])
    pred.meta["native_result_summary"] = {k: r[k] for k in ("column_anchors", "periods", "unit", "anchor_diagnostics")}
    if not r["rows"]:
        pred.status = "failed" if any(i["code"] == "needs_visual_fallback" for i in r["issues"]) else "no_tables"
    else:
        boxes = [x["bbox"] for x in r["rows"] if x["bbox"]]
        tbl_bbox = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
        t = Table(table_id="t0", bbox=[round(v, 2) for v in tbl_bbox], reading_order=0, unit=r["unit"],
                  n_data_columns=len(r["periods"]), capabilities=pred.capabilities,
                  checks=r["checks"])
        for ci, p in enumerate(r["periods"]):
            t.headers.append(Header(header_id=f"h{ci}", text=p or "", period=p, role="amount", bbox=None,
                                    col_start=ci, column_indices=[ci]))
        for x in r["rows"]:
            row = Row(row_index=x["row"] - 1, label=x["label"], raw_label=x["label"], parent_path=x["path"][:-1],
                      bbox=x["label_bbox"] and x["bbox"], type=x["type"])
            for c in x["cells"]:
                row.cells.append(Cell(column_index=c["column"], header_id=f"h{c['column']}", period=c["period"],
                                      role="amount", raw=c["raw"], value=c["value"], status=c["status"],
                                      bbox=c["bbox"], backend="native_v2", evidence_kind="native_pdf"))
            if x["review"]:
                t.issues.append({"row_index": row.row_index, "codes": x["review"]})
            t.rows.append(row)
        t.n_data_columns = len(r["periods"])
        pred.tables.append(t)
        pred.status = "partial" if any(i["severity"] == "error" for i in r["issues"]) else "ok"
    pred.meta["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return pred
