"""Run the experiment matrix and write runs/summary.json + runs/summary.md.

    python scripts/run_matrix.py [--only backend,...] [--repeat 3]

Every cell of the matrix is a subprocess (model backends in the optional venv), so crashes/timeouts are
recorded as results, not hidden. Metrics:
  * text-layer token recall/precision: reference = every numeric word in the PDF text layer of the *digital* page
    (bottom 6% page-number zone excluded). Valid for digital pages and rasterisations of the same page;
    says nothing about structure/labels/roles and is NOT a human gold
  * dev-gold exact match (source.pdf only; AI-drafted gold)
"""
import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from findoclens.backends import native_grid
from findoclens.compare import text_layer_reference, token_recall
from findoclens.goldcheck import score_against_gold
from findoclens.router import MODEL_PYTHON
from findoclens.variants import raster_pdf

DOCS = {"source": (ROOT / "baseline_v2/source.pdf", 0), "elecom": (ROOT / "data/pdfs/elecom.pdf", 8),
        "daiwabo": (ROOT / "data/pdfs/daiwabo.pdf", 9)}
CONFIGS = [  # name, backend, extra args, variants
    ("native_v2", "native_v2", [], ["digital", "raster200"]),
    ("native_grid", "native_grid", [], ["digital", "raster200"]),
    ("docling_cmtrue", "docling", ["-o", "cell_matching=true", "--tag", "cmtrue"], ["digital", "raster200"]),
    ("docling_cmfalse", "docling", ["-o", "cell_matching=false", "--tag", "cmfalse"], ["digital"]),
    ("docling_ocr_rapid", "ocr_rapid", ["--tag", "rapid"], ["raster200"]),
    ("auto", "auto", [], ["digital", "raster200"]),
    ("auto_verify", "auto", ["--verify"], ["digital"]),
]


def run_one(cfg, doc, variant, repeat, outdir="runs"):
    name, backend, extra, _ = cfg
    pdf, page = DOCS[doc]
    if variant == "raster200":
        pdf, page = raster_pdf(pdf, page, 200, doc), 0
    doc_id = f"{doc}_{variant}"
    if backend == "auto":
        return run_auto(name, doc, variant, pdf, page, extra, outdir)
    py = MODEL_PYTHON if backend in ("docling", "ocr_rapid") else sys.executable
    cmd = [py, "-m", "findoclens.runner", backend, str(pdf), str(page), "--out", outdir, "--repeat", str(repeat),
           "--doc-id", doc_id, *extra]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=2400, env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"})
    except subprocess.TimeoutExpired:
        return {"config": name, "doc": doc, "variant": variant, "status": "timeout"}
    tag = None
    for i, a in enumerate(extra):
        if a == "--tag":
            tag = extra[i + 1]
    d = ROOT / outdir / (backend + (f"_{tag}" if tag else "")) / doc_id
    if r.returncode != 0 or not (d / "prediction.json").exists():
        return {"config": name, "doc": doc, "variant": variant, "status": "runner_crash", "error": (r.stderr or r.stdout)[-600:]}
    pred = json.loads((d / "prediction.json").read_text())
    man = json.loads((d / "run_manifest.json").read_text())
    ref = text_layer_reference(*DOCS[doc])
    rec = token_recall(pred, ref)
    row = {"config": name, "doc": doc, "variant": variant, "status": pred["status"], "tables": len(pred["tables"]),
           "rows": sum(r["type"] != "section" for t in pred["tables"] for r in t["rows"]),
           "numeric_cells": rec["predicted_tokens"], "token_recall": rec["recall"], "token_precision": rec["precision"],
           "ref_tokens": rec["reference_tokens"], "missing_sample": rec["missing"][:8], "spurious_sample": rec["spurious"][:8],
           "checks": dict(Counter(c["status"] for t in pred["tables"] for c in t["checks"])),
           "cold_ms": man["cold_time_ms"], "warm_ms_median": man["warm_time_ms_median"],
           "peak_rss_mb": man["peak_memory_mb"]["process_peak_rss_mb"], "dir": str(d.relative_to(ROOT)),
           "issues": sorted({i.get("code") for i in pred["issues"]})}
    if doc == "source":
        g = score_against_gold(pred)
        row["dev_gold_cells_correct"] = f"{g['cells_correct']}/{g['gold_cells']}"
    return row


def run_auto(name, doc, variant, pdf, page, extra, outdir):
    import time
    out_root = f"{outdir}/{name}"
    t0 = time.perf_counter()
    r = subprocess.run([sys.executable, "-m", "findoclens", "parse", str(pdf), "--page", str(page), "--backend", "auto",
                        "--out", out_root, "--format", "json,md", *extra], capture_output=True, text=True, cwd=ROOT, timeout=2400,
                       env={**__import__("os").environ, "PYTHONPATH": str(ROOT)})
    wall = round((time.perf_counter() - t0) * 1000, 1)
    d = ROOT / out_root / "auto" / f"{Path(pdf).stem}_p{page}"
    if not (d / "prediction.json").exists():
        return {"config": name, "doc": doc, "variant": variant, "status": "runner_crash", "error": (r.stderr or r.stdout)[-600:]}
    pred = json.loads((d / "prediction.json").read_text())
    ref = text_layer_reference(*DOCS[doc])
    rec = token_recall(pred, ref)
    row = {"config": name, "doc": doc, "variant": variant, "status": pred["status"], "tables": len(pred["tables"]),
           "rows": sum(r["type"] != "section" for t in pred["tables"] for r in t["rows"]), "numeric_cells": rec["predicted_tokens"],
           "token_recall": rec["recall"], "token_precision": rec["precision"], "ref_tokens": rec["reference_tokens"],
           "missing_sample": rec["missing"][:8], "spurious_sample": rec["spurious"][:8],
           "checks": dict(Counter(c["status"] for t in pred["tables"] for c in t["checks"])),
           "cold_ms": wall, "warm_ms_median": None, "peak_rss_mb": None, "dir": str(d.relative_to(ROOT)),
           "issues": sorted({i.get("code") for i in pred["issues"]}), "backend_used": pred["backend"],
           "routing": pred["meta"]["routing"]["decisions"]}
    if doc == "source":
        g = score_against_gold(pred)
        row["dev_gold_cells_correct"] = f"{g['cells_correct']}/{g['gold_cells']}"
    return row


def md_table(rows):
    cols = ["config", "doc", "variant", "status", "tables", "rows", "numeric_cells", "token_recall", "token_precision",
            "dev_gold_cells_correct", "cold_ms", "warm_ms_median", "peak_rss_mb"]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join("" if r.get(c) is None else str(r.get(c)) for c in cols) + " |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--docs", default=",".join(DOCS))
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--out", default="runs")
    ap.add_argument("--summary", default="runs/summary")
    ap.add_argument("--variants", default="", help="restrict to these variants (digital,raster200)")
    a = ap.parse_args()
    only = set(filter(None, a.only.split(",")))
    rows = []
    for cfg in CONFIGS:
        if only and cfg[0] not in only:
            continue
        for doc in a.docs.split(","):
            for variant in cfg[3]:
                if a.variants and variant not in a.variants.split(","):
                    continue
                print("running", cfg[0], doc, variant, flush=True)
                row = run_one(cfg, doc, variant, a.repeat, a.out)
                print("  ->", {k: row.get(k) for k in ("status", "tables", "rows", "token_recall", "cold_ms", "warm_ms_median", "error")}, flush=True)
                rows.append(row)
    sj = Path(a.summary + ".json")
    old = json.loads(sj.read_text()) if sj.exists() else []
    key = lambda r: (r["config"], r["doc"], r["variant"])
    merged = {key(r): r for r in old}
    merged.update({key(r): r for r in rows})
    order = {c[0]: i for i, c in enumerate(CONFIGS)}
    allrows = sorted(merged.values(), key=lambda r: (order.get(r["config"], 99), list(DOCS).index(r["doc"]), r["variant"]))
    sj.write_text(json.dumps(allrows, ensure_ascii=False, indent=1))
    Path(a.summary + ".md").write_text(md_table(allrows) + "\n")


if __name__ == "__main__":
    main()
