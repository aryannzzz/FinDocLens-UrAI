"""Common prediction schema (docs/EVAL_PROTOCOL.md). Plain dataclasses -> JSON-ready dicts."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional, List

SCHEMA_VERSION = "findoclens-0.1"
CELL_STATUS = {"observed", "negative_zero", "not_reported", "absent_text_cell", "unreadable", "uncertain"}
ROLES = {"amount", "composition_pct", "change_amount", "other"}
EVIDENCE = {"native_pdf", "ocr", "vlm", "human", "table_model"}


@dataclass
class Cell:
    column_index: int
    header_id: Optional[str]
    period: Optional[str]
    role: str
    raw: Optional[str]
    value: Optional[float]
    status: str
    bbox: Optional[List[float]]
    backend: str
    evidence_kind: str
    notes: List[str] = field(default_factory=list)


@dataclass
class Header:
    header_id: str
    text: str
    period: Optional[str]
    role: Optional[str]
    bbox: Optional[List[float]]
    colspan: int = 1
    rowspan: int = 1
    row_start: Optional[int] = None
    col_start: Optional[int] = None
    column_indices: List[int] = field(default_factory=list)  # data columns this header governs


@dataclass
class Row:
    row_index: int
    label: Optional[str]
    raw_label: Optional[str]
    parent_path: List[str]
    bbox: Optional[List[float]]
    type: str                      # item | total | section | header | other
    cells: List[Cell] = field(default_factory=list)


@dataclass
class Table:
    table_id: str
    bbox: Optional[List[float]]
    reading_order: int
    headers: List[Header] = field(default_factory=list)
    rows: List[Row] = field(default_factory=list)
    issues: List[dict] = field(default_factory=list)
    unit: Optional[str] = None
    n_data_columns: int = 0
    capabilities: dict = field(default_factory=dict)   # e.g. {"cell_bbox": true, "headers": "partial"}
    checks: List[dict] = field(default_factory=list)


@dataclass
class DocumentPrediction:
    document_id: str
    source_sha256: str
    backend: str
    model_revision: Optional[str]
    page: int                      # zero-based
    page_bbox: Optional[List[float]]
    tables: List[Table] = field(default_factory=list)
    status: str = "ok"             # ok | partial | no_tables | failed | skipped | needs_visual_review
    issues: List[dict] = field(default_factory=list)
    capabilities: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)       # timing, device, versions, raw artifacts
    schema_version: str = SCHEMA_VERSION

    def to_dict(self):
        return asdict(self)


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def n_numeric_cells(pred: dict) -> int:
    return sum(1 for t in pred["tables"] for r in t["rows"] for c in r["cells"]
               if c["status"] in ("observed", "negative_zero", "not_reported"))
