"""Render the visual failure gallery from stored final runs: docs/gallery/*.png (+ docs/FAILURE_GALLERY.md with the scored facts).

    python scripts/make_gallery.py fin1
Boxes: every returned cell bbox (green native text, orange OCR, red uncertain/unreadable), table boxes in dark red. Images show pages of
third-party filings and are therefore git-ignored; regenerate them with this script (see docs/FAILURE_GALLERY.md).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from findoclens.render import draw_evidence

ITEMS = [
    # (id, backend, doc, split, caption)
    ("G1", "native_v2", "daiwabo_p10", "main", "Frozen v2 on the Daiwabo slide: one table, left table / deltas / lower table silently absent while the run is not an abstention."),
    ("G2", "docling_cmtrue", "daiwabo_p10", "main", "Docling cell_matching=True: three tables flattened into one 8-column grid (label column of table 2 becomes a data column)."),
    ("G3", "docling_cmfalse", "daiwabo_p10", "main", "Docling cell_matching=False: a table box with almost no cell text (text-line cells span whole rows on this slide)."),
    ("G4", "docling_regions", "daiwabo_p10", "main", "Ablation: native_grid region proposals + Docling per region. The two upper tables are separated; the unruled lower table is not detected."),
    ("G5", "native_grid", "daiwabo_p10", "main", "native_grid on the same slide: 3 tables, 63 numeric cells, but the third table has no printed header (roles/periods stay null)."),
    ("G6", "docling_rapidocr", "scan_200", "adv", "Docling+RapidOCR on a 200-dpi raster of the original: the two `－` cells are boxed in red (ink present, OCR returned nothing)."),
    ("G7", "docling_rapidocr", "elecom_p9_scan200", "raster", "Docling+RapidOCR on the ELECOM raster: digits correct, kanji labels misread (產, 壳); affected rows carry ocr_suspect_variant_glyph."),
    ("G8", "docling_cmtrue", "rotation_90", "adv", "Docling on a page with /Rotate 90 metadata: status success but rows do not match the reference."),
    ("G9", "native_grid", "grouped_two", "adv", "native_grid on the left-aligned grouped-header control (spans are inferred and flagged, not read from rules)."),
    ("G10", "native_grid", "vertical_spacing", "adv", "native_grid on vertically stacked CJK labels: numbers captured, labels fragmented into pieces."),
]


def main(prefix):
    out = ROOT / "docs/gallery"
    out.mkdir(parents=True, exist_ok=True)
    entries = {}
    for f in ("manifest", "adversarial_manifest", "raster_manifest"):
        for line in (ROOT / f"benchmark/{f}.jsonl").read_text().splitlines():
            e = json.loads(line)
            entries[e["document_id"]] = e
    lines = ["# Visual failure gallery", "",
             f"Rendered from stored runs `{prefix}_*` by `scripts/make_gallery.py`. Boxes are the backend's returned cell boxes; red = uncertain/unreadable. "
             "Images show third-party filings and are git-ignored (regenerate with the script; decide separately whether to ship them).", ""]
    for gid, backend, doc, split, caption in ITEMS:
        run = ROOT / "runs" / backend / doc / f"{prefix}_{split}"
        pred_path = run / "cold/prediction.json"
        if not pred_path.exists():
            lines += [f"## {gid} — {backend} / {doc}", "", f"*run missing: {run.relative_to(ROOT)}*", ""]
            continue
        pred = json.loads(pred_path.read_text())
        e = entries[doc]
        draw_evidence(ROOT / e["input_path"], 0, pred, out / f"{gid}_{backend}_{doc}.png", dpi=90)
        m = json.loads((run / "cold/metrics.json").read_text())["metrics"] if (run / "cold/metrics.json").exists() else None
        facts = ""
        if m:
            facts = (f"status `{pred['status']}`; tables {m['tables']['matched']}/{m['tables']['gold']} (+{m['extra_tables']} extra); rows {m['rows']['matched']}/{m['rows']['gold']}; "
                     f"numeric cells exact {m['numeric_raw_exact']['correct']}/{m['numeric_raw_exact']['total']}; silent omissions {m['silent_omission_rate']['correct']}/{m['silent_omission_rate']['total']}; "
                     f"false assurance: {'yes' if m['false_assurance'] else 'no'}.")
        lines += [f"## {gid} — {backend} / {doc}", "", caption, "", f"![{gid}](gallery/{gid}_{backend}_{doc}.png)", "", facts,
                  f"Source: `{pred_path.relative_to(ROOT)}`.", ""]
    (ROOT / "docs/FAILURE_GALLERY.md").write_text("\n".join(lines), encoding="utf-8")
    print("gallery written")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "fin1")
