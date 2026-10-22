"""Adaptive routing: simple, inspectable rules; no learned confidence.

Signals (all logged in `meta.routing.signals`):
  glyph_count / glyph_density, numeric_tokens, repeated right-edge anchors (columns with >=3 numeric tokens),
  image_area_fraction (raster-likeness), native_grid table/row counts, label contamination,
  agreement between native_v2 and native_grid, arithmetic checks, optional model-backend agreement.
Policy:
  raster-like page            -> visual backend (OCR); result is never auto-verified
  native clean                -> accept native_grid (provenance: native_pdf)
  native suspicious / --verify-> run Docling, compare; native glyphs are NEVER overwritten.
                                 unresolved value disagreements -> status `needs_visual_review`
  native has no tables but Docling has -> Docling result, status `partial`
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import fitz

from .backends import native_grid, native_v2
from .compare import compare_pair, norm_label
from .runinfo import ROOT
from .schema import sha256_file
from .validator import validate_prediction

MODEL_PYTHON = os.environ.get("FINDOCLENS_MODEL_PYTHON", str(ROOT / ".venv-docling" / "bin" / "python"))
NUMERIC_IN_LABEL = re.compile(r"[△▲+＋]?\d{1,3}(?:,\d{3})+|[+＋△▲]\d")


def page_signals(pdf, page_index):
    page = fitz.open(str(pdf))[page_index]
    words = page.get_text("words")
    glyphs = sum(len(w[4]) for w in words)
    area = page.rect.width * page.rect.height
    img_area = 0.0
    try:
        for im in page.get_image_info():
            b = fitz.Rect(im["bbox"]) & page.rect
            img_area += max(0, b.width) * max(0, b.height)
    except Exception:
        pass
    return {"glyph_count": glyphs, "glyph_density_per_kpt2": round(glyphs / area * 1000, 3), "words": len(words),
            "image_area_fraction": round(min(1.0, img_area / area), 3)}


def native_flags(pred):
    flags = []
    if not pred["tables"]:
        flags.append("no_tables")
    for t in pred["tables"]:
        for r in t["rows"]:
            if r["label"] and NUMERIC_IN_LABEL.search(r["label"]):
                flags.append(f"label_contains_amount:{t['table_id']}:{r['row_index']}")
        if t["rows"]:
            cells = [c for r in t["rows"] if r["type"] != "section" for c in r["cells"] if c["column_index"] >= 0]
            absent = sum(c["status"] == "absent_text_cell" for c in cells)
            if cells and absent / len(cells) > .25:
                flags.append(f"many_absent_cells:{t['table_id']}")
    if any(i["code"] == "arithmetic_violation" for i in pred["issues"]):
        flags.append("arithmetic_violation")
    return flags


def run_model_backend(backend, pdf, page_index, out_root, opts=None, timeout=1800):
    """Run a model backend in the optional venv; returns (prediction dict | None, manifest | None, error)."""
    if not Path(MODEL_PYTHON).exists():
        return None, None, f"model interpreter not found: {MODEL_PYTHON} (see docs/SETUP_MODELS.md)"
    cmd = [MODEL_PYTHON, "-m", "findoclens.runner", backend, str(pdf), str(page_index), "--out", str(out_root)]
    for k, v in (opts or {}).items():
        cmd += ["-o", f"{k}={json.dumps(v)}"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT),
                       env={**os.environ, "PYTHONPATH": str(ROOT)})
    if r.returncode != 0:
        return None, None, (r.stderr or r.stdout)[-1500:]
    info = json.loads(r.stdout.strip().splitlines()[-1])
    out = Path(info["out"])
    return json.loads((out / "prediction.json").read_text()), json.loads((out / "run_manifest.json").read_text()), None


def route(pdf, page_index=0, out_root="runs", verify=False, allow_models=True, visual_backend="ocr_rapid"):
    t0 = time.perf_counter()
    pdf = str(pdf)
    sig = page_signals(pdf, page_index)
    log = {"signals": sig, "decisions": [], "steps": []}
    raster_like = sig["glyph_count"] < 20 or (sig["image_area_fraction"] > .6 and sig["glyph_count"] < 100)
    g = validate_prediction(native_grid.extract(pdf, page_index).to_dict())
    v2 = native_v2.extract(pdf, page_index).to_dict()
    log["steps"].append({"backend": "native_grid", "status": g["status"], "tables": len(g["tables"])})
    log["steps"].append({"backend": "native_v2", "status": v2["status"], "tables": len(v2["tables"])})
    final = g
    final["backend"] = "auto"
    final["meta"]["component_backends"] = ["native_grid", "native_v2"]
    if raster_like:
        log["decisions"].append("raster_like_page: native text absent -> visual backend required")
        final["meta"]["native_grid_status"] = g["status"]
        if allow_models:
            p, m, err = run_model_backend(visual_backend, pdf, page_index, out_root)
            log["steps"].append({"backend": visual_backend, "ran": err is None, "error": err})
            if p is not None and p["tables"]:
                p = validate_prediction(p)
                bad = any(i["code"] == "arithmetic_violation" for i in p["issues"])
                checked = any(c["status"] in ("pass", "within_rounding") for t in p["tables"] for c in t["checks"])
                p["backend"] = f"auto({visual_backend})"
                p["status"] = "partial" if (checked and not bad) else "needs_visual_review"
                p["issues"].append({"severity": "warning", "code": "single_visual_source",
                                    "message": "OCR/visual output has no independent second source on this page; not verified"})
                final = p
                log["decisions"].append(f"accepted {visual_backend} output as `{p['status']}` (arithmetic checks"
                                        f"{' pass' if checked and not bad else ' absent or failing'})")
            else:
                final = g
                final["backend"] = "auto"
                final["status"] = "needs_visual_review"
                final["issues"].append({"severity": "error", "code": "visual_backend_unavailable_or_empty",
                                        "message": err or f"{visual_backend} returned no tables"})
                log["decisions"].append("visual backend failed/empty -> needs_visual_review (no data invented)")
        else:
            final["status"] = "needs_visual_review"
            final["issues"].append({"severity": "error", "code": "needs_visual_fallback", "message": "models disabled"})
    else:
        flags = native_flags(g)
        cmp_v2 = compare_pair(g, v2) if v2["tables"] else None
        v2_agrees = bool(cmp_v2 and cmp_v2["n_value_mismatch"] == 0 and len(v2["tables"]) == len(g["tables"]))
        sus_v2 = native_flags(v2)
        if v2["tables"] and not v2_agrees:
            log["decisions"].append("native_v2 disagrees with native_grid "
                                    f"({cmp_v2['n_value_mismatch']} mismatches, {len(v2['tables'])} vs {len(g['tables'])} tables); "
                                    + ("v2 labels contain amounts (false assurance)" if sus_v2 else "see meta.cmp_native_v2"))
        final["meta"]["cmp_native_v2"] = None if cmp_v2 is None else {k: cmp_v2[k] for k in ("matched_tables", "n_value_mismatch", "unmatched_tables_a", "unmatched_tables_b")}
        need = bool(flags) or verify
        if flags:
            log["decisions"].append(f"native flags: {flags[:6]}")
        if not need:
            log["decisions"].append("native_grid clean: accepted without model backend (route=native_accept)")
        elif allow_models:
            p, m, err = run_model_backend("docling", pdf, page_index, out_root)
            log["steps"].append({"backend": "docling", "ran": err is None, "error": err})
            if p is None:
                final["issues"].append({"severity": "warning", "code": "checker_unavailable", "message": err})
                if flags:
                    final["status"] = "needs_visual_review"
            else:
                c = compare_pair(g, p)
                final["meta"]["cmp_docling"] = {k: c[k] for k in ("matched_tables", "n_value_mismatch", "unmatched_tables_a", "unmatched_tables_b")}
                final["meta"]["disagreements"] = c["disagreements"][:200]
                if not g["tables"] and p["tables"]:
                    p["backend"] = "auto(docling)"
                    p["status"] = "partial"
                    final = validate_prediction(p)
                    log["decisions"].append("native found no tables; using docling result as partial")
                elif c["n_value_mismatch"]:
                    final["status"] = "needs_visual_review"
                    log["decisions"].append(f"docling disagrees on {c['n_value_mismatch']} items; native glyphs kept, flagged for review")
                else:
                    log["decisions"].append("docling agrees with native on all compared cells")
        else:
            final["status"] = "needs_visual_review" if flags else final["status"]
    final["meta"]["routing"] = log
    final["meta"]["routing"]["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return final
