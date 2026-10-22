"""Build viewer/data.js (+ page images) from stored benchmark runs. Reads predictions, metrics and AI-draft references only.

    python scripts/build_viewer.py --run native_grid=int2 --run docling_cmtrue=int1 ...   (RUN is the run-id prefix: <prefix>_main / _adv / _raster)
Nothing is recomputed or repaired; every number shown in the viewer comes from the stored metrics.json / measurement.json.
"""
import argparse
import json
import statistics
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = {"main": "benchmark/manifest.jsonl", "adv": "benchmark/adversarial_manifest.jsonl", "raster": "benchmark/raster_manifest.jsonl"}
SHOW = ["original", "elecom_p9", "daiwabo_p10", "elecom_p9_scan200", "daiwabo_p10_scan200", "scan_200", "footnote_marker",
        "rotation_90", "grouped_two", "side_by_side"]


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def compact_metrics(m):
    keep = ["tables", "extra_tables", "rows", "spurious_rows", "raw_label_exact", "row_order_accuracy", "cell_coverage", "numeric_raw_exact",
            "numeric_semantic_exact", "header_role_accuracy", "hierarchy_edges", "silent_omission_rate", "false_assurance"]
    return {k: m["metrics"][k] for k in keep}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", default=[], help="backend=run_prefix")
    ap.add_argument("--out", default="viewer")
    ap.add_argument("--dpi", type=int, default=110)
    a = ap.parse_args()
    out = ROOT / a.out
    (out / "pages").mkdir(parents=True, exist_ok=True)
    entries = {}
    for split, path in MANIFESTS.items():
        if (ROOT / path).exists():
            for line in (ROOT / path).read_text().splitlines():
                e = json.loads(line)
                if e.get("status") == "available":
                    entries[e["document_id"]] = (split, e)
    docs = []
    for did in SHOW:
        if did not in entries:
            continue
        split, e = entries[did]
        gold_path = ROOT / e.get("gold_path", f"benchmark/gold/{did}.json")
        gold = load(gold_path) if gold_path.exists() else None
        pdf = fitz.open(ROOT / e["input_path"])
        page = pdf[0]
        img = f"pages/{did}.jpg"
        page.get_pixmap(dpi=a.dpi, alpha=False).save(out / img, jpg_quality=72)
        reference = None
        if gold:
            reference = dict(status=gold.get("annotation_status"), human_checked_cells=gold.get("human_checked_cells", 0),
                             tables=[dict(rows=[dict(cells=[dict(bbox=c.get("bbox")) for c in r["cells"]]) for r in t["rows"]]) for t in gold["tables"]])
        doc = dict(id=did, title=f"{did} ({e.get('source_kind', 'source')}, {e['split']})", img=img, pageW=page.rect.width,
                   pageH=page.rect.height, reference=reference, backends={})
        for spec in a.run:
            backend, prefix = spec.split("=")
            folder = ROOT / "runs" / backend / did / f"{prefix}_{split}"
            if not (folder / "cold/prediction.json").exists() or not (folder / "metadata.json").exists():
                continue
            pred = load(folder / "cold/prediction.json")
            meta = load(folder / "metadata.json")
            mp = folder / "cold/metrics.json"
            metrics = load(mp) if mp.exists() else None
            warm = [m["time_ms"] for m in meta.get("measurements", [])[1:] if m.get("time_ms") is not None and m.get("status") in ("success", "partial", "abstained")]
            doc["backends"][backend] = dict(
                run_id=f"{prefix}_{split}", status=pred.get("status"), backend_status=pred.get("backend_status"), issues=pred.get("issues", []),
                tables=pred.get("tables", []), cold_ms=meta.get("cold_time_ms"), warm_ms=statistics.median(warm) if warm else None,
                rss_mb=meta["measurements"][0].get("peak_memory_mb") if meta.get("measurements") else None,
                metrics=compact_metrics(metrics) if metrics else None, errors=metrics["errors"][:200] if metrics else [])
        if doc["backends"]:
            docs.append(doc)
    (out / "data.js").write_text("window.DATA = " + json.dumps(dict(docs=docs), ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"{len(docs)} documents, {sum(len(d['backends']) for d in docs)} backend views, data.js {(out / 'data.js').stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
