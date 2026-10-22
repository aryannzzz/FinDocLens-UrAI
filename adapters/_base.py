"""Shared entrypoint factory: findoclens backend -> `extract(input_path, *, context)` of the benchmark contract.

The callable never receives gold. Model backends load lazily on the first call (disclosed in provenance as
`lazy_load_on_first_call`; the harness's cold trial therefore includes model construction) and are cached for warm calls.
Raw native output is written under $BENCHMARK_RUN_DIR/raw/<trial>/ when the harness provides it.
"""
import hashlib
import importlib.metadata as md
import json
import os
import subprocess
from pathlib import Path

from adapters.canonical import convert, sha256_json
from findoclens import backends
from findoclens.validator import validate_prediction

HF_HUB = Path(os.environ.get("HF_HOME", Path(__file__).resolve().parents[1] / ".cache/hf")) / "hub"


def snapshot(repo):
    d = HF_HUB / f"models--{repo.replace('/', '--')}" / "snapshots"
    return sorted(p.name for p in d.iterdir())[0] if d.exists() and any(d.iterdir()) else None


def pkg(name):
    try:
        return md.version(name)
    except md.PackageNotFoundError:
        return None


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


ROOT = Path(__file__).resolve().parents[1]


def code_state():
    """Commit of the extraction code and whether code paths (not run artifacts) have uncommitted edits."""
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain", "--", "findoclens", "adapters", "benchmark", "baseline_v2", "tests",
                                         ":(exclude)benchmark/reports", ":(exclude)benchmark/review"],
                                        cwd=ROOT, text=True).strip()
        return dict(commit=head, code_dirty=bool(dirty), code_dirty_paths=dirty.splitlines()[:20])
    except Exception as exc:       # recorded, never silent
        return dict(commit=None, code_dirty=None, error=str(exc))


CODE_STATE = code_state()


def make_extract(public_name, native_name, opts=None, raw_files=()):
    state = dict(calls=0)
    opts = dict(opts or {})

    def extract(input_path, *, context):
        trial = "cold" if state["calls"] == 0 else f"warm_{state['calls']}"
        state["calls"] += 1
        run_dir = os.environ.get("BENCHMARK_RUN_DIR")
        raw_dir = Path(run_dir) / "raw" / trial if run_dir else None
        if raw_dir and trial == "cold":     # raw model output is stored once per run; later trials are hashed only
            raw_dir.mkdir(parents=True, exist_ok=True)
        fn = backends.get(native_name)
        native = fn(str(input_path), 0, out_dir=raw_dir if (raw_dir and trial == "cold") else None, **opts)
        native = validate_prediction(native.to_dict())
        native_sha = sha256_json(native)
        raw_paths = {}
        if raw_dir and trial == "cold":
            (raw_dir / "native_findoclens_prediction.json").write_text(json.dumps(native, ensure_ascii=False, indent=1), encoding="utf-8")
            raw_paths = {str(p.relative_to(raw_dir)): dict(path=str(p.relative_to(run_dir)), sha256=file_sha(p)) for p in sorted(raw_dir.rglob('*')) if p.is_file()}
        provenance = dict(adapter="adapters.canonical.convert", native_schema=native.get("schema_version"),
                          native_backend=native.get("backend"), native_prediction_sha256=native_sha,
                          native_options=opts, raw_artifacts=raw_paths, code=CODE_STATE,
                          lazy_load_on_first_call=native_name in backends.MODEL_BACKENDS,
                          backend_meta={k: v for k, v in native.get("meta", {}).items() if k not in ("routing",)},
                          native_status=native.get("status"), trial=trial)
        return convert(native, context, backend=public_name, provenance=provenance)

    return extract


def base_metadata(native_name, **extra):
    meta = dict(device="cpu", backend_version=f"findoclens-0.1 ({native_name})", model_revision=None, checkpoint_id=None,
                null_reason="rule-based native backend: no model checkpoint", findoclens_packages={"PyMuPDF": pkg("PyMuPDF")})
    meta.update(extra)
    return meta


def docling_metadata(native_name, ocr=False, **extra):
    layout = snapshot("docling-project/docling-layout-heron")
    tables = snapshot("docling-project/docling-models")
    meta = dict(device="cpu", backend_version=f"docling {pkg('docling')} / docling-ibm-models {pkg('docling-ibm-models')}",
                model_revision=f"layout={layout}; tableformer={tables}",
                checkpoint_id="docling-project/docling-layout-heron + docling-project/docling-models (TableFormer ACCURATE)",
                packages={n: pkg(n) for n in ("docling", "docling-core", "docling-ibm-models", "docling-parse", "torch",
                                               "rapidocr", "onnxruntime", "PyMuPDF")})
    if ocr:
        meta["ocr"] = "RapidOCR lang=iso:ja, PP-OCRv6 small det/rec onnx (force_full_page_ocr)"
    meta.update(extra)
    return meta
