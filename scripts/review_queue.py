"""Write docs/MANUAL_REVIEW_QUEUE.md: what a human must check in the AI-drafted references, ordered by risk.

    python scripts/review_queue.py fin1
Reads references and stored predictions only. It never edits a reference and does not decide who is right: where independent
readers disagree with a draft, both values are listed. Row ids match benchmark/review/index.html (`python -m benchmark.review`).
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmark.diagnostics import _norm, _num_cells


def load(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


def special(c):
    raw = c.get("raw") or ""
    return any(k in raw for k in ("△", "▲", "+", "＋", "－", "−")) or c["status"] in ("negative_zero", "not_reported", "absent_text_cell")


def main(prefix):
    docs = [("original", "benchmark/gold/original.json", "main"), ("elecom_p9", "benchmark/gold/elecom_p9.json", "main"),
            ("daiwabo_p10", "benchmark/gold/daiwabo_p10.json", "main")]
    out = ["# Manual review queue for the AI-drafted references", "",
           "**Status of every reference: `ai_draft`, `human_checked_cells = 0`.** Nothing below was verified by a person, and this queue was "
           "generated, not reviewed. Open `benchmark/review/index.html` (regenerate with `python -m benchmark.review`), enter your name, inspect the "
           "rendered crops, export decisions, and tick the matching lines in `docs/USER_SIGNOFF.md` only for what you actually inspected. "
           "Do not edit a reference to match a model: record a versioned correction with crop, old/new token and reason (see `benchmark/README.md`).", ""]
    # A: glyph-critical cells
    out += ["## A. Must check: signs, dashes, plus signs, negative zero (project gate: negative-sign/dash fidelity)", "",
            "A native text layer can carry a wrong glyph or lose a thin mark without any tool noticing, and all four extractors read the same layer. "
            "These cells are where a silent error costs the most. Compare the crop with `raw` character by character.", "",
            "| doc | row id | label | col | draft raw | draft status |", "|---|---|---|---|---|---|"]
    counts = Counter()
    for did, gp, _ in docs:
        g = load(gp)
        for t in g["tables"]:
            for r in t["rows"]:
                for c in r["cells"]:
                    if c.get("role") != "other" and special(c):
                        counts[did] += 1
                        out.append(f"| {did} | `{r['row_id']}` | {r['raw_label']} | {c['column_index']} | `{c['raw']}` | {c['status']} |")
    out += ["", "Counts: " + ", ".join(f"{k} {v}" for k, v in counts.items()) + f" (total {sum(counts.values())}). Plain digits are in section D.", ""]
    # B: structural assertions
    g = load("benchmark/gold/daiwabo_p10.json")
    expl = next(t for t in g["tables"] if t["table_id"] == "explanation")
    texts = [(r["row_id"], c["raw"]) for r in expl["rows"] for c in r["cells"] if c["role"] == "other"]
    out += ["## B. Structural assertions in the drafts that no extractor can confirm", "",
            "| # | doc | assertion in the draft | why it is uncertain | evidence |", "|---|---|---|---|---|",
            f"| B1 | daiwabo_p10 | The lower table has headers `c0..c3` with the periods/roles of the two upper tables (2025-03-31, 2025-12-31, change, text). | The slide prints no header over this table; the draft copied the periods from the tables above. Every backend that reads only what is printed leaves these columns without a header. | `benchmark/gold/daiwabo_p10.json` table `explanation`; native_grid header score 6/10 is exactly these 4 leaves |",
            f"| B2 | daiwabo_p10 | The four explanation texts are cells without the leading arrow: " + "; ".join(f"`{t}`" for _, t in texts) + ". | The PDF text layer prints `→` before each text and the extractors keep it (`→主に…`). Whether the arrow belongs to the cell text decides 4 cells (`raw_cell_exact`). | cell mismatches in `runs/native_grid/daiwabo_p10/fin1_main/cold/metrics.json` |",
            "| B3 | daiwabo_p10 | The page has exactly 3 tables (assets, liabilities+equity, explanation) and the draft's table/row boxes are right. | The explanation block has no ruling or header; a different annotator may call it a note or two tables. Table matching uses bbox IoU ≥ 0.1 so box choices matter. | review sheet, section `daiwabo_p10` |",
            "| B4 | daiwabo_p10 | 7 hierarchy edges (e.g. `現金及び預金` under `流動資産`). | The slide has no section-heading rows; the parent assignment was inferred from indentation by the drafter. Every backend scores 0/7. | `parent_path` in the reference |",
            "| B5 | daiwabo_p10 | Change column `増減` has period `2025-12-31_vs_2025-03-31` (current minus previous). | Convention chosen by the drafter; the validator's 17 delta checks on tables 1–2 (12 exact, 5 within rounding, 0 violations) support current−previous, but the header text only says 増減 and table 3 has no check. | `findoclens` validator checks, `docs/CLAUDE_RESULTS.md` §4 |",
            "| B6 | daiwabo_p10 | Unit `million_JPY` for all three tables. | Printed once (`（百万円）`, above table 1 only). Tables 2–3 inherit it in the draft. | page crop |",
            "| B7 | elecom_p9 | `その他（純額）` is a child of `有形固定資産`, not of `建設仮勘定`. | Frozen v2 (a text-geometry parser) attaches it elsewhere; the draft follows the source layout. Only the indentation in the crop can settle it (1 hierarchy edge). | `benchmark/reports/measured.md` |",
            "| B8 | original | `建設仮勘定` and `長期貸付金` have a `－` in the prior-period column (status `not_reported`, value null); `貸倒引当金` has `△0` (negative zero). | These are the three cells where a human must confirm that the page really prints a dash / a triangle-zero (an OCR engine cannot see the dash at all, see `docs/FAILURE_GALLERY.md` G6). | section A |", ""]
    # C: reader disagreement
    out += ["## C. Where an image-based reader disagrees with the draft (label-independent)", "",
            "Docling+RapidOCR reads pixels, not the text layer, so it is the only reader that is not common-mode with the draft's native-text bootstrap. "
            "Gold numeric tokens that the OCR run did not return anywhere on the page (multiset comparison; location- and label-free):", ""]
    rows_c = []
    for did, gp, split in [("scan_200", "benchmark/gold/adversarial/scan_200.json", "adv"), ("elecom_p9_scan200", "benchmark/gold/raster/elecom_p9_scan200.json", "raster"),
                           ("daiwabo_p10_scan200", "benchmark/gold/raster/daiwabo_p10_scan200.json", "raster")]:
        pp = ROOT / f"runs/docling_rapidocr/{did}/{prefix}_{split}/cold/prediction.json"
        if not pp.exists():
            out.append(f"* {did}: OCR run `{prefix}_{split}` not found")
            continue
        gold, pred = load(gp), json.loads(pp.read_text())
        gt = Counter(_norm(c["raw"]) for t in gold["tables"] for r in t["rows"] for c in _num_cells(r) if c.get("raw"))
        pt = Counter(_norm(c["raw"]) for t in pred["tables"] for r in t["rows"] for c in _num_cells(r) if c.get("raw"))
        miss, extra = gt - pt, pt - gt
        out.append(f"* **{did}**: gold {sum(gt.values())} tokens; OCR returned {sum(pt.values())}; absent from OCR: "
                   + (", ".join(f"`{k}`×{v}" for k, v in miss.items()) or "none") + "; produced by OCR but not in the draft: "
                   + (", ".join(f"`{k}`×{v}" for k, v in extra.items()) or "none") + ".")
    out += ["", "A token in the first list is either an OCR miss (expected for lone `－`, see the dash probe) or a draft error. "
            "A token in the second list is an OCR misread or a draft omission. Check each against the crop before concluding either way. "
            "In the stored run the Daiwabo entries are explained by structure, not by digits: OCR fuses the printed arrow with the number (`→12,410`) and returns the four explanation "
            "texts, which the draft stores as text cells; the digits themselves agree. ELECOM and the original page show no digit disagreement except the two lone `－`.", ""]
    # D: counts
    n = {d: sum(len(r["cells"]) for t in load(gp)["tables"] for r in t["rows"]) for d, gp, _ in docs}
    out += ["## D. Everything else", "",
            "Project minimum (`AGENTS.md`, `benchmark/README.md`): all table boundaries, all headers/units, exact Japanese labels, all signs/dashes (section A), "
            "and at least 20 numeric cells per independent page; preferably the complete references.", "",
            "| doc | rows | cells | suggested scope |", "|---|---|---|---|"]
    for did, gp, _ in docs:
        g = load(gp)
        out.append(f"| {did} | {sum(len(t['rows']) for t in g['tables'])} | {n[did]} | "
                   + {"original": "all 43 labels + all 74 tokens (this is the page the baseline was tuned on)", "elecom_p9": "all 34 labels; ≥ 20 tokens incl. both `△`; table box and unit",
                      "daiwabo_p10": "3 table boxes; all 21 labels; ≥ 20 tokens across the three tables; items B1–B6"}[did] + " |")
    out += ["", "Raster derivatives and synthetic/perturbed controls inherit their parent's reference or are generated with known truth; "
            "reviewing the parent pages covers them (the derived references are listed in `benchmark/gold/raster/SHA256.json`).", ""]
    (ROOT / "docs/MANUAL_REVIEW_QUEUE.md").write_text("\n".join(out), encoding="utf-8")
    print("review queue written")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "fin1")
