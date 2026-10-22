"""Re-score STORED predictions with the current evaluator (version 2) and compare with the metrics stored at run time (version 1).

Nothing is re-extracted and nothing stored is modified: the output is a new file. This isolates the evaluator's effect (same
predictions, two evaluators) from the extractors' effect (compare `fin1` with `p0fix1` under the same evaluator).

    python scripts/p0_rescore.py --run fin1 --out results/p0/rescored_fin1.json
Only cold trials are scored. AI-drafted references stay AI-drafted: this script never changes `annotation_status`.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmark.evaluate import evaluate, EVALUATOR_VERSION

MANIFESTS = {"main": "benchmark/manifest.jsonl", "adv": "benchmark/adversarial_manifest.jsonl", "raster": "benchmark/raster_manifest.jsonl"}
BACKENDS = ["v2", "native_v2", "native_grid", "docling_cmtrue", "docling_cmfalse", "docling_rapidocr", "docling_regions", "auto"]
NEW_AXES = ("cell_period_accuracy", "cell_role_accuracy", "cell_header_link_accuracy", "cell_structure_exact", "cell_evidence_localization")


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def entries():
    out = []
    for split, path in MANIFESTS.items():
        if (ROOT / path).exists():
            out += [dict(json.loads(l), _set=split) for l in (ROOT / path).read_text().splitlines() if l.strip()]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="run-id prefix, e.g. fin1 (folders <prefix>_main/_adv/_raster)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit(f"refusing to overwrite {args.out}")
    rows = []
    for e in entries():
        gp = ROOT / e.get("gold_path", f"benchmark/gold/{e['document_id']}.json")
        if not gp.exists():
            continue
        gold = load(gp)
        for b in BACKENDS:
            cold = ROOT / "runs" / b / e["document_id"] / f"{args.run}_{e['_set']}" / "cold"
            if not (cold / "metrics.json").exists():
                continue
            old = load(cold / "metrics.json")
            new = evaluate(gold, load(cold / "prediction.json"))
            m1, m2 = old["metrics"], new["metrics"]
            rows.append(dict(backend=b, document=e["document_id"], set=e["_set"], reference_status=new["reference_status"],
                             run_status=new["run_status"], evaluator_stored=old.get("evaluator_version", 1), evaluator_now=EVALUATOR_VERSION,
                             stored=dict(false_assurance=m1["false_assurance"], silent=m1["silent_omission_rate"],
                                         numeric_raw=m1["numeric_raw_exact"], header_precision=m1["header_role_precision"]),
                             rescored=dict(false_assurance=m2["false_assurance"], reasons=m2["false_assurance_reasons"],
                                           silent=m2["silent_omission_rate"], numeric_raw=m2["numeric_raw_exact"],
                                           header_precision=m2["header_role_precision"], unscoped=m2["unscoped_omission_warnings"],
                                           **{k: m2[k] for k in NEW_AXES}),
                             unchanged_value_axes=all(m1[k] == m2[k] for k in ("numeric_raw_exact", "numeric_semantic_exact", "raw_cell_exact", "cell_coverage",
                                                                               "rows", "tables", "hierarchy_edges"))))
    agg = defaultdict(lambda: defaultdict(int))
    for r in rows:
        a = agg[r["backend"]]
        a["pages"] += 1
        a["false_assurance_stored"] += r["stored"]["false_assurance"]
        a["false_assurance_rescored"] += r["rescored"]["false_assurance"]
        a["silent_stored"] += r["stored"]["silent"]["correct"]
        a["silent_rescored"] += r["rescored"]["silent"]["correct"]
        a["value_axes_changed"] += not r["unchanged_value_axes"]
        for k in NEW_AXES:
            a[k + "_correct"] += r["rescored"][k]["correct"]
            a[k + "_total"] += r["rescored"][k]["total"]
    out = dict(run_prefix=args.run, evaluator_version=EVALUATOR_VERSION, note="Same stored predictions scored by the stored (v1) and current (v2) evaluator; "
               "reference_status of every row is preserved as reported by the reference file (ai_draft).",
               by_backend={b: dict(v) for b, v in agg.items()}, rows=rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(out["by_backend"], indent=1))


if __name__ == "__main__":
    main()
