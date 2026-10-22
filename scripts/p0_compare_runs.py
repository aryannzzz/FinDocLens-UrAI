"""Compare two stored run prefixes (default fin1 -> p0fix2) page by page: extraction differences and metric differences.
Reads artifacts only. `fin1` metrics were scored by evaluator v1 at run time; `p0fix2` by evaluator v2, so value axes are compared
(they must be identical unless the extraction changed) and the v2-only axes are reported from p0fix2 and from the v2 re-score of fin1
(`results/p0/rescored_fin1.json`).

    python scripts/p0_compare_runs.py --out results/p0/fin1_vs_p0fix2.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MANIFESTS = {"main": "benchmark/manifest.jsonl", "adv": "benchmark/adversarial_manifest.jsonl", "raster": "benchmark/raster_manifest.jsonl"}
BACKENDS = ["v2", "native_v2", "native_grid", "docling_cmtrue", "docling_cmfalse", "docling_rapidocr", "docling_regions", "auto"]
VALUE_AXES = ("numeric_raw_exact", "numeric_semantic_exact", "raw_cell_exact", "cell_coverage", "rows", "tables", "hierarchy_edges",
              "header_role_accuracy", "grouped_headers", "silent_omission_rate", "missing_cells")


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def sig(pred):
    return [[(r["label"], [(c["column_index"], c["raw"], c["status"]) for c in r["cells"]]) for r in t["rows"]] for t in pred["tables"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", default="fin1")
    ap.add_argument("--after", default="p0fix2")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit(f"refusing to overwrite {args.out}")
    rescored = {(r["backend"], r["document"]): r for r in load(ROOT / "results/p0/rescored_fin1.json")["rows"]}
    rows, missing = [], []
    for split, path in MANIFESTS.items():
        for line in (ROOT / path).read_text().splitlines():
            e = json.loads(line)
            did = e["document_id"]
            for b in BACKENDS:
                a = ROOT / "runs" / b / did / f"{args.after}_{split}" / "cold"
                o = ROOT / "runs" / b / did / f"{args.before}_{split}" / "cold"
                if not (a / "prediction.json").exists() or not (o / "prediction.json").exists():
                    missing.append(f"{b}/{did}")
                    continue
                pa, po = load(a / "prediction.json"), load(o / "prediction.json")
                ma = load(a / "metrics.json")["metrics"] if (a / "metrics.json").exists() else None
                mo = load(o / "metrics.json")["metrics"] if (o / "metrics.json").exists() else None
                differing = [k for k in VALUE_AXES if ma and mo and ma[k] != mo[k]]
                rs = rescored.get((b, did))
                rows.append(dict(
                    backend=b, document=did, set=split, status_before=po["status"], status_after=pa["status"],
                    review_required_after=pa.get("review_required"), review_reasons_after=pa.get("review_reasons"),
                    extraction_identical=sig(pa) == sig(po), value_axes_that_differ=differing,
                    false_assurance_before_v2=rs["rescored"]["false_assurance"] if rs else None,
                    false_assurance_after=ma["false_assurance"] if ma else None,
                    structure_before_v2=rs["rescored"]["cell_structure_exact"] if rs else None,
                    structure_after=ma["cell_structure_exact"] if ma else None,
                    period_before_v2=rs["rescored"]["cell_period_accuracy"] if rs else None,
                    period_after=ma["cell_period_accuracy"] if ma else None,
                    silent_before=mo["silent_omission_rate"]["correct"] if mo else None,
                    silent_after=ma["silent_omission_rate"]["correct"] if ma else None))
    out = dict(before=args.before, after=args.after, pages=len(rows), not_available=missing, rows=rows,
               changed_extraction=[f"{r['backend']}/{r['document']}" for r in rows if not r["extraction_identical"]],
               changed_status=[f"{r['backend']}/{r['document']}: {r['status_before']}->{r['status_after']}" for r in rows if r["status_before"] != r["status_after"]],
               changed_value_axes=[f"{r['backend']}/{r['document']}: {r['value_axes_that_differ']}" for r in rows if r["value_axes_that_differ"]])
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("pages", "not_available", "changed_extraction", "changed_status", "changed_value_axes")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
