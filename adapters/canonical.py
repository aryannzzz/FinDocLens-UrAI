"""Projection of a `findoclens-0.1` DocumentPrediction onto the `benchmark-1.0` canonical result.

This module is a pure function of the backend output. It never reads gold, never edits a printed token and never
repairs a value. Everything it adds is either (a) a rename/re-indexing, or (b) a documented convention that the
evaluation contract requires. Each non-trivial step records why in `capability_status` / `notes` / `issues`:

* status mapping: findoclens page status -> contract run status (`ok` with only info issues -> `success`;
  any warning/error issue, or a table-level `hierarchy_not_inferred` declaration -> `partial`; `failed`/`no_tables` -> `abstained`; `needs_visual_review` -> `partial`).
* periods: `YYYY-MM` is written as the month-end date (`2025-03` -> `2025-03-31`), the contract's period form.
  A `change_amount` column without a period gets `<later>_vs_<earlier>` ONLY if the table has exactly two distinct
  amount periods (inferred from sibling columns; flagged in the header's `capability_status`).
* headers: one leaf per physical data column (single-column header cell nearest the data) plus one `group` per
  multi-column header cell, with `parent_id` to the smallest enclosing group. Columns without a header cell get a
  leaf with `role=None` and `capability_status=no_header_cell_found` (the role is NOT guessed at header level).
* section rows (heading rows without values) carry zero cells, as the contract allows: the backend's placeholder
  `absent_text_cell` slots of such rows are not forwarded (they do not stand for a missing printed value).
* `column_index=-1` text cells (notes/arrows beside the data columns) are numbered after the last data column in
  left-to-right order; their typed `value` is the raw string (contract rule for `other` cells).
"""
from __future__ import annotations
import calendar
import hashlib
import json
import re
from copy import deepcopy

SCHEMA_VERSION = "benchmark-1.0"
MONTH = re.compile(r"^(\d{4})-(\d{2})$")


def month_end(period):
    if not isinstance(period, str):
        return period
    m = MONTH.match(period)
    if not m:
        return period
    y, mo = int(m.group(1)), int(m.group(2))
    return f"{y:04d}-{mo:02d}-{calendar.monthrange(y, mo)[1]:02d}" if 1 <= mo <= 12 else period


def map_status(native_status, issues):
    if native_status in ("failed", "no_tables", "skipped"):
        return "abstained"
    if native_status in ("needs_visual_review", "partial"):
        return "partial"
    if native_status == "ok":
        return "partial" if any(i.get("severity") in ("warning", "error") for i in issues) else "success"
    return "error"


def _leaf_and_groups(table, ncols, col_meta):
    """Build contract headers for one table. Returns (headers, notes)."""
    raw = table.get("headers", [])
    cand = [h for h in raw if h.get("column_indices")]
    groups = [h for h in cand if len(h["column_indices"]) > 1]
    headers, leaf_by_col = [], {}
    for k in range(ncols):
        singles = [h for h in cand if h["column_indices"] == [k]]
        period, role, text = col_meta.get(k, (None, None, None))[:3]
        if singles:
            h = max(singles, key=lambda x: (x.get("row_start") or 0))      # the header cell nearest the data
            leaf = dict(header_id=f"{table['table_id']}_c{k}", kind="leaf", column_index=k, text=h["text"],
                        period=month_end(h.get("period") or period), role=h.get("role") or role, bbox=h.get("bbox"),
                        colspan=h.get("colspan", 1), rowspan=h.get("rowspan", 1), native_header_id=h["header_id"])
        else:
            leaf = dict(header_id=f"{table['table_id']}_c{k}", kind="leaf", column_index=k, text=None,
                        period=month_end(period), role=None, bbox=None, colspan=None, rowspan=None,
                        capability_status="no_header_cell_found; role and text not inferred at header level")
        headers.append(leaf)
        leaf_by_col[k] = leaf
    gh = []
    for g in groups:
        c0 = min(g["column_indices"])
        gh.append(dict(header_id=f"{table['table_id']}_g{g['header_id']}", kind="group", column_index=c0, text=g["text"],
                       period=month_end(g.get("period")), role=None, bbox=g.get("bbox"), colspan=len(g["column_indices"]),
                       rowspan=g.get("rowspan", 1), native_header_id=g["header_id"],
                       _cols=set(g["column_indices"]), _row=g.get("row_start") or 0))
    def parent_of(cols, row, own=None):
        # smallest enclosing group above `row`; groups over the same columns (outer group + year group) nest by header row,
        # so among equal spans the nearest row above wins (never the group itself)
        enclosing = [x for x in gh if cols <= x["_cols"] and x["_row"] < row and x is not own]
        return min(enclosing, key=lambda x: (len(x["_cols"]), -x["_row"]))["header_id"] if enclosing else None
    for k, leaf in leaf_by_col.items():
        src = next((h for h in cand if h["header_id"] == leaf.get("native_header_id")), None)
        pid = parent_of({k}, (src.get("row_start") or 0) if src else 10**6)
        if pid:
            leaf["parent_id"] = pid
    for g in gh:
        pid = parent_of(g["_cols"], g["_row"], own=g)
        if pid:
            g["parent_id"] = pid
    for g in gh:
        g.pop("_cols"), g.pop("_row")
    # change columns lacking a period: later_vs_earlier only when unambiguous
    amount_periods = sorted({l["period"] for l in headers if l["role"] == "amount" and l["period"] and "_vs_" not in l["period"]})
    for l in headers:
        if l["role"] == "change_amount" and not l["period"] and len(amount_periods) == 2:
            l["period"] = f"{amount_periods[1]}_vs_{amount_periods[0]}"
            l["capability_status"] = "change period inferred from the table's two amount periods"
    return headers + gh


def convert(native, context, *, backend, page_bbox=None, provenance=None):
    native = deepcopy(native)
    tables, doc_issues = [], list(native.get("issues", []))
    for ti, t in enumerate(native.get("tables", [])):
        rows = t.get("rows", [])
        ncols = t.get("n_data_columns") or 0
        col_meta = {}
        for r in rows:
            for c in r["cells"]:
                if c["column_index"] >= 0:
                    col_meta.setdefault(c["column_index"], (c.get("period"), c.get("role"), None))
        # Docling-style tables may have header-less columns: keep the physical index from the cells
        ncols = max([ncols] + [k + 1 for k in col_meta])
        headers = _leaf_and_groups(t, ncols, col_meta)
        out_rows = []
        for r in rows:
            cells, extra = [], []
            for c in r["cells"]:
                cell = {k: c[k] for k in ("column_index", "header_id", "period", "role", "raw", "value", "status",
                                          "bbox", "backend", "evidence_kind")}
                cell["period"] = month_end(cell["period"])
                if cell["column_index"] >= 0:
                    cell["header_id"] = f"{t['table_id']}_c{cell['column_index']}"
                    if c.get("notes"):
                        cell["notes"] = c["notes"]
                    cells.append(cell)
                else:
                    extra.append(cell)
            if r["type"] == "section":
                cells = [c for c in cells if c["status"] != "absent_text_cell"]
            extra.sort(key=lambda c: (c["bbox"] or [1e9])[0])
            for j, cell in enumerate(extra):
                cell.update(column_index=ncols + j, header_id=None, role="other", value=cell["raw"], status="observed",
                            notes=["text outside the numeric columns; column numbered after the last data column"])
                cells.append(cell)
            out_rows.append(dict(row_id=f"{t['table_id']}_r{r['row_index']}", row_index=r["row_index"], label=r["label"],
                                 raw_label=r["raw_label"], parent_path=r["parent_path"], bbox=r.get("bbox"),
                                 bbox_status=None if r.get("bbox") else "backend supplies no row geometry",
                                 type=r["type"], cells=cells))
        for h in headers:
            if h["kind"] == "leaf":
                h.setdefault("period", None)
        t_issues = list(t.get("issues", []))
        out = dict(table_id=t["table_id"], page=1, bbox=t.get("bbox"), reading_order=t.get("reading_order", ti),
                   headers=headers, rows=out_rows, issues=t_issues, unit=t.get("unit"),
                   capability_status=t.get("capabilities"))
        if t.get("grid") is not None:
            out["native_grid_cells"] = len(t["grid"])
        tables.append(out)
    t_issues = [i for t in native.get("tables", []) for i in t.get("issues", [])]
    status = map_status(native.get("status"), doc_issues + t_issues)
    if status == "success" and any(i.get("code") == "hierarchy_not_inferred" for i in t_issues):
        status = "partial"      # the backend itself declares part of the contract (account hierarchy) was not produced
    if not any(t["rows"] for t in tables):
        status = "abstained"
    # Explicit review-required marker. The contract's run statuses have no "needs review" value, so `partial` carries it and
    # these two extra fields say why; `success` means no warning/error issue and no declared limitation was raised.
    reasons = sorted({i["code"] for i in doc_issues + t_issues if i.get("severity") in ("warning", "error")})
    if native.get("status") == "needs_visual_review":
        reasons.append("needs_visual_review")
    if any(i.get("code") == "hierarchy_not_inferred" for i in t_issues):
        reasons.append("hierarchy_not_inferred(declared limitation)")
    if status != "success" and not reasons:
        reasons.append(f"backend_status:{native.get('status')}")
    return dict(schema_version=SCHEMA_VERSION, document_id=context["document_id"], source_sha256=context["source_sha256"],
                input_sha256=context["input_sha256"], backend=backend, model_revision=native.get("model_revision"),
                page_bbox=page_bbox or native.get("page_bbox"), status=status, backend_status=native.get("status"),
                review_required=status != "success", review_reasons=reasons if status != "success" else [],
                issues=doc_issues, tables=tables, capabilities=native.get("capabilities"), provenance=provenance or {})


def sha256_json(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
