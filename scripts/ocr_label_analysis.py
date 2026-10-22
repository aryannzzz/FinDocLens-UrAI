"""OCR label-error and flag analysis over stored final runs -> docs/logs/ocr_label_analysis.json (+ stdout).
Rows are paired to references by their exact numeric tuple (label-free), then the label is compared. A flag is useful only if it marks a
wrong label; 'suggestion == gold' counts flagged rows whose suggested Japanese form restores the reference label exactly (never applied)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmark.diagnostics import _norm, _tuple

CASES = [("scan_200", "benchmark/gold/adversarial/scan_200.json", "adv"), ("scan_150", "benchmark/gold/adversarial/scan_150.json", "adv"),
         ("text_layer_deleted", "benchmark/gold/adversarial/text_layer_deleted.json", "adv"),
         ("elecom_p9_scan200", "benchmark/gold/raster/elecom_p9_scan200.json", "raster"), ("daiwabo_p10_scan200", "benchmark/gold/raster/daiwabo_p10_scan200.json", "raster")]


def main(prefix="fin1"):
    out = []
    for backend in ("docling_rapidocr", "docling_rapidocr_medium"):
        for doc, gp, split in CASES:
            pp = ROOT / f"runs/{backend}/{doc}/{prefix}_{split}/cold/prediction.json"
            if not pp.exists():
                continue
            pred, gold = json.loads(pp.read_text()), json.loads((ROOT / gp).read_text())
            flagged = {i["label"]: i["suspected_japanese_forms"] for t in pred["tables"] for i in t["issues"] if i["code"] == "ocr_suspect_variant_glyph"}
            ink = [(i["label"], i["columns"]) for t in pred["tables"] for i in t["issues"] if i["code"] == "ocr_possible_dropped_placeholder"]
            prow = {}
            for t in pred["tables"]:
                for r in t["rows"]:
                    tp = _tuple(r)
                    if tp:
                        prow.setdefault(tp, []).append(r)
            n = wrong = hit = fixed = 0
            unflagged = []
            for t in gold["tables"]:
                for r in t["rows"]:
                    tp = _tuple(r)
                    if not tp or tp not in prow:
                        continue
                    n += 1
                    pl = prow[tp][0]["label"]
                    if _norm(pl) != _norm(r["label"]):
                        wrong += 1
                        if pl in flagged:
                            hit += 1
                            fixed += "".join(flagged[pl].get(c, c) for c in pl) == r["label"]
                        else:
                            unflagged.append([r["label"], pl])
            out.append(dict(backend=backend, doc=doc, rows_paired_by_numeric_tuple=n, label_wrong=wrong, wrong_and_flagged=hit,
                            flagged_suggestion_equals_reference=fixed, wrong_not_flagged=unflagged, variant_flags_total=len(flagged),
                            ink_flags=ink))
    (ROOT / "docs/logs/ocr_label_analysis.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for o in out:
        print({k: v for k, v in o.items() if k != "wrong_not_flagged"})


if __name__ == "__main__":
    main(*sys.argv[1:])
