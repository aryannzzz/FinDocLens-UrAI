"""Run one backend on one page, write artifacts + run manifest to runs/<backend>/<doc_id>/.

    python -m findoclens.runner <backend> <pdf> <page_index> [--out runs] [--repeat N] [--tag suffix] [--doc-id id] [-o key=val]

`--repeat N` runs extract N times in the same process: run 1 is the cold run (includes model load),
runs 2..N are warm. All timings are wall-clock `perf_counter`; peak RSS is process `ru_maxrss`.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
import traceback
import uuid
from pathlib import Path

from . import backends
from .render import to_markdown
from .runinfo import ROOT, git_commit, hardware, load_source_manifest, peak_rss_mb, pkg_versions, utc_now
from .schema import DocumentPrediction, n_numeric_cells, sha256_file
from .validator import validate_prediction

PKGS = ["PyMuPDF", "docling", "docling-core", "docling-ibm-models", "docling-parse", "torch", "torchvision", "rapidocr",
        "onnxruntime", "easyocr", "paddleocr", "paddlepaddle", "transformers", "numpy", "pdfplumber"]


def run_backend(backend, pdf, page_index, out_root="runs", repeat=1, opts=None, doc_id=None, tag=None):
    """Artifacts go to runs/<backend>[_<tag>]/<doc_id>/ (doc_id should already encode page/variant)."""
    opts = dict(opts or {})
    pdf = str(pdf)
    doc_id = doc_id or f"{Path(pdf).stem}_p{page_index}"
    out = Path(out_root) / (backend + (f"_{tag}" if tag else "")) / doc_id
    out.mkdir(parents=True, exist_ok=True)
    fn = backends.get(backend)
    timings, pred, err = [], None, None
    for k in range(repeat):
        t0 = time.perf_counter()
        try:
            pred = fn(pdf, page_index, out_dir=out, **opts)
            if not isinstance(pred, DocumentPrediction):
                raise TypeError("backend did not return DocumentPrediction")
        except Exception as e:     # a crash is a recorded status, never a silent skip
            err = "".join(traceback.format_exception_only(type(e), e)).strip() + "\n" + traceback.format_exc()[-1500:]
            pred = DocumentPrediction(document_id=doc_id, source_sha256=sha256_file(pdf), backend=backend, model_revision=None,
                                      page=page_index, page_bbox=None, status="failed",
                                      issues=[{"severity": "error", "code": "backend_exception", "message": err[:400]}])
        timings.append({"run": k + 1, "kind": "cold" if k == 0 else "warm", "time_ms": round((time.perf_counter() - t0) * 1000, 1)})
    d = validate_prediction(pred.to_dict())
    if d["status"] in ("ok", "partial") and n_numeric_cells(d) == 0:      # an empty extraction is never a success
        d["status"] = "failed"
        d["issues"].append({"severity": "error", "code": "empty_extraction", "message": "no numeric cells extracted"})
    src = next((v for v in load_source_manifest().get("documents", {}).values() if v.get("sha256") == d["source_sha256"]), {})
    manifest = {
        "run_id": uuid.uuid4().hex[:12], "timestamp_utc": utc_now(), "git_commit": git_commit(),
        "source_url": src.get("source_url"), "source_sha256": d["source_sha256"], "page_index": page_index,
        "split_label": src.get("split"), "backend": backend, "model_revision": d["model_revision"],
        "options": {k: v for k, v in opts.items() if k != "out_dir"}, "tag": tag, "package_versions": pkg_versions(PKGS),
        "hardware": hardware(), "device": d["meta"].get("device", "cpu"), "timings": timings,
        "cold_time_ms": timings[0]["time_ms"], "warm_time_ms_median": (sorted(t["time_ms"] for t in timings[1:])[len(timings[1:]) // 2]
                                                                         if len(timings) > 1 else None),
        "peak_memory_mb": {"process_peak_rss_mb": peak_rss_mb(), "gpu_peak_allocated_mb": d["meta"].get("gpu_peak_mb")},
        "status": d["status"], "error_text": err, "prediction_path": str(out / "prediction.json"),
        "metrics_path": None, "human_audit_status": "none: automatic extraction, not human-verified",
        "backend_meta": d["meta"],
    }
    (out / "prediction.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "tables.md").write_text(to_markdown(d), encoding="utf-8")
    return d, manifest, out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("backend")
    ap.add_argument("pdf")
    ap.add_argument("page", type=int)
    ap.add_argument("--out", default="runs")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--doc-id")
    ap.add_argument("--tag", help="suffix for the run directory, e.g. cmtrue / cmfalse")
    ap.add_argument("-o", "--opt", action="append", default=[], help="backend option key=value (json-parsed)")
    a = ap.parse_args(argv)
    opts = {}
    for kv in a.opt:
        k, v = kv.split("=", 1)
        try:
            opts[k] = json.loads(v)
        except json.JSONDecodeError:
            opts[k] = v
    d, m, out = run_backend(a.backend, a.pdf, a.page, a.out, a.repeat, opts, a.doc_id, a.tag)
    print(json.dumps({"out": str(out), "status": d["status"], "tables": len(d["tables"]), "timings": m["timings"],
                      "peak_rss_mb": m["peak_memory_mb"]["process_peak_rss_mb"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
