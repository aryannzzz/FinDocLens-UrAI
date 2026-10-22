"""Render the evidence crops referenced by docs/CLAUDE_RESULTS.md into docs/evidence/ (needs runs/ from run_matrix)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from findoclens.backends import native_grid
from findoclens.render import draw_evidence

OUT = ROOT / "docs" / "evidence"
OUT.mkdir(parents=True, exist_ok=True)
DAI, ELE, SRC = ROOT / "data/pdfs/daiwabo.pdf", ROOT / "data/pdfs/elecom.pdf", ROOT / "baseline_v2/source.pdf"


def pred(path):
    return json.loads((ROOT / path / "prediction.json").read_text())


def main():
    # F1 frozen v2 on Daiwabo: reports status ok but merges the two tables (false assurance)
    draw_evidence(DAI, 9, pred("runs/native_v2/daiwabo_digital"), OUT / "F1_native_v2_daiwabo_false_assurance.png", dpi=110)
    # F2 Docling TableFormer cell_matching=True: three tables flattened into one 8-column grid
    draw_evidence(DAI, 9, pred("runs/docling_cmtrue/daiwabo_digital"), OUT / "F2_docling_cmtrue_daiwabo_merged.png", dpi=110)
    # F3 Docling cell_matching=False on the same page: table found, no text in any cell
    draw_evidence(DAI, 9, pred("runs/docling_cmfalse/daiwabo_digital"), OUT / "F3_docling_cmfalse_daiwabo_empty.png", dpi=110)
    # F4 Docling+RapidOCR on the rasterised original: the two `－` placeholder cells are missing (rows with absent cells)
    p = pred("runs/ocr_rapid_rapid/source_raster200")
    boxes = [r for t in p["tables"] for r in t["rows"] if r["type"] != "section" and any(c["status"] == "absent_text_cell" for c in r["cells"])]
    lab = [r["label"] for r in boxes]
    draw_evidence(ROOT / "data/variants/source_raster200.pdf", 0, p, OUT / "F4_ocr_source_raster_missing_dash.png", dpi=110)
    (OUT / "F4_rows_with_absent_cells.json").write_text(json.dumps(lab, ensure_ascii=False))
    # S3 native_grid on ELECOM p13 (equity statement, out-of-template stress page; known defect: header words leak into one section row, centred spanning headers get single-column spans)
    g = native_grid.extract(ELE, 12).to_dict()
    draw_evidence(ELE, 12, g, OUT / "S3_native_grid_elecom_p13_equity_statement.png", dpi=110)
    # S1 success example with boxes: native_grid on Daiwabo (3 tables, roles, signs)
    draw_evidence(DAI, 9, pred("runs/native_grid/daiwabo_digital"), OUT / "S1_native_grid_daiwabo.png", dpi=110)
    draw_evidence(ELE, 8, pred("runs/native_grid/elecom_digital"), OUT / "S2_native_grid_elecom.png", dpi=110)
    print(sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
