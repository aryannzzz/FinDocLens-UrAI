"""Gold-free structural check of a canonical prediction against docs/BENCHMARK_ADAPTER_CONTRACT.md.

Returns a list of violations (empty = schema-compliant). It checks shape, vocabularies and internal consistency only;
it says nothing about correctness. Used by tests and by scripts/contract_report.py over every stored prediction.
"""
import math

RUN_STATUS = {"success", "partial", "abstained", "error", "oom", "timeout", "unavailable"}
CELL_STATUS = {"observed", "negative_zero", "not_reported", "absent_text_cell", "unreadable", "uncertain", "unparseable"}
ROLES = {"amount", "composition_pct", "change_amount", "other"}
DOC_KEYS = ("schema_version", "document_id", "source_sha256", "input_sha256", "backend", "model_revision", "page_bbox",
            "status", "issues", "tables")
TABLE_KEYS = ("table_id", "page", "bbox", "reading_order", "headers", "rows", "issues")
HEADER_KEYS = ("header_id", "kind", "column_index", "text", "period", "role", "bbox", "colspan", "rowspan")
ROW_KEYS = ("row_id", "row_index", "label", "raw_label", "parent_path", "bbox", "type", "cells")
CELL_KEYS = ("column_index", "header_id", "period", "role", "raw", "value", "status", "bbox", "backend", "evidence_kind")


def _box_ok(b):
    return b is None or (isinstance(b, list) and len(b) == 4 and all(isinstance(v, (int, float)) and math.isfinite(v) for v in b))


def check_prediction(p):
    v = []
    for k in DOC_KEYS:
        if k not in p:
            v.append(f"document missing {k}")
    if p.get("schema_version") != "benchmark-1.0":
        v.append("schema_version != benchmark-1.0")
    if p.get("status") not in RUN_STATUS:
        v.append(f"run status {p.get('status')!r} outside contract")
    if p.get("status") in ("success", "partial") and not any(t.get("rows") for t in p.get("tables", [])):
        v.append("success/partial without rows (empty extraction must abstain)")
    for t in p.get("tables", []):
        tid = t.get("table_id")
        v += [f"{tid}: table missing {k}" for k in TABLE_KEYS if k not in t]
        if not _box_ok(t.get("bbox")):
            v.append(f"{tid}: bad table bbox")
        ids = {h.get("header_id") for h in t.get("headers", [])}
        leaf_cols = set()
        for h in t.get("headers", []):
            v += [f"{tid}/{h.get('header_id')}: header missing {k}" for k in HEADER_KEYS if k not in h]
            if h.get("kind") not in ("leaf", "group"):
                v.append(f"{tid}: header kind {h.get('kind')!r}")
            if h.get("kind") == "leaf":
                if h["column_index"] in leaf_cols:
                    v.append(f"{tid}: duplicate leaf column {h['column_index']}")
                leaf_cols.add(h["column_index"])
            if h.get("parent_id") is not None and h["parent_id"] not in ids:
                v.append(f"{tid}: dangling parent_id {h['parent_id']}")
            if h.get("role") not in ROLES | {None}:
                v.append(f"{tid}: header role {h.get('role')!r}")
            if not _box_ok(h.get("bbox")):
                v.append(f"{tid}: bad header bbox")
        for i, r in enumerate(t.get("rows", [])):
            v += [f"{tid} row {i}: missing {k}" for k in ROW_KEYS if k not in r]
            if r.get("row_index") != i:
                v.append(f"{tid} row {i}: row_index {r.get('row_index')}")
            if not _box_ok(r.get("bbox")):
                v.append(f"{tid} row {i}: bad bbox")
            cols = [c.get("column_index") for c in r.get("cells", [])]
            if len(cols) != len(set(cols)):
                v.append(f"{tid} row {i}: duplicate column slot")
            for c in r.get("cells", []):
                v += [f"{tid} row {i}: cell missing {k}" for k in CELL_KEYS if k not in c]
                if c.get("status") not in CELL_STATUS:
                    v.append(f"{tid} row {i}: cell status {c.get('status')!r}")
                if c.get("role") not in ROLES:
                    v.append(f"{tid} row {i}: cell role {c.get('role')!r}")
                if c.get("status") in ("not_reported", "absent_text_cell", "unreadable") and c.get("value") is not None:
                    v.append(f"{tid} row {i}: null-status cell carries a value")
                if c.get("status") == "observed" and c.get("role") != "other" and c.get("value") is None:
                    v.append(f"{tid} row {i}: observed numeric cell with null value")
                if not _box_ok(c.get("bbox")):
                    v.append(f"{tid} row {i}: bad cell bbox")
            if r.get("type") != "section" and leaf_cols:
                missing = {c for c in leaf_cols if c not in cols} - {h["column_index"] for h in t["headers"]
                                                                       if h.get("kind") == "leaf" and h.get("role") == "other"}
                if missing:
                    v.append(f"{tid} row {i}: missing slots {sorted(missing)}")
    return v
