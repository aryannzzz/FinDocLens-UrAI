"""Run native_grid on every page of a PDF (no gold; counts only) -> runs/native_grid_page_sweep.json.
Counts show where the parser *claims* a table; they are NOT accuracy and are not human-checked."""
import json
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from findoclens.backends import native_grid

out = {}
for name in ("elecom", "daiwabo"):
    pdf = ROOT / "data" / "pdfs" / f"{name}.pdf"
    pages = []
    for i in range(len(fitz.open(str(pdf)))):
        p = native_grid.extract(pdf, i)
        pages.append({"page": i, "status": p.status, "tables": [{"rows": len(t.rows), "cols": t.n_data_columns, "unit": t.unit,
                      "issues": sorted({x["code"] for x in t.issues})} for t in p.tables],
                      "unassigned_numeric_tokens": len(p.meta.get("unassigned_numeric_tokens", []))})
    out[name] = {"pages": len(pages), "pages_with_tables": [x["page"] for x in pages if x["tables"]], "detail": pages}
(ROOT / "runs" / "native_grid_page_sweep.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print({k: (v["pages"], v["pages_with_tables"]) for k, v in out.items()})
