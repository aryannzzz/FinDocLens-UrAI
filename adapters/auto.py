"""Contract entrypoint: the rule-based router (`findoclens.router.route`) = native_grid + native_v2 cross-check, Docling only
when native output is suspicious, Docling+RapidOCR for raster-like pages. Models run in a subprocess of the model venv
($FINDOCLENS_MODEL_PYTHON, default .venv-docling) per call, so cold == warm for pages that need a model; the harness RSS covers only
the router process, so child peak RSS is recorded separately in provenance (RUSAGE_CHILDREN high-water mark)."""
import os
import resource
import tempfile
from pathlib import Path

from adapters._base import CODE_STATE, base_metadata, sha256_json
from adapters.canonical import convert
from findoclens.router import route
from findoclens.validator import validate_prediction

BENCHMARK_METADATA = base_metadata("auto", backend_version="findoclens-0.1 router (native_grid, native_v2; Docling / Docling+RapidOCR on demand)",
                                   null_reason="router; model checkpoints (when invoked) are those of docling / docling_rapidocr",
                                   model_revision="on demand: see provenance.backend_meta.routing")
_calls = dict(n=0)


def extract(input_path, *, context):
    trial = "cold" if _calls["n"] == 0 else f"warm_{_calls['n']}"
    _calls["n"] += 1
    before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024
    with tempfile.TemporaryDirectory(prefix="fdl-auto-") as tmp:
        d = validate_prediction(route(str(input_path), 0, tmp, verify=False, allow_models=True))
    child_peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024
    provenance = dict(adapter="adapters.canonical.convert", native_schema=d.get("schema_version"), native_backend=d.get("backend"),
                      native_prediction_sha256=sha256_json(d), code=CODE_STATE, trial=trial, native_status=d.get("status"),
                      backend_meta=d.get("meta", {}), child_process_peak_rss_mb=child_peak if child_peak > before else None,
                      note="child peak is a process-lifetime high-water mark of waited-for children (model subprocess)")
    return convert(d, context, backend="auto", provenance=provenance)
