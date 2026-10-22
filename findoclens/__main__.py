"""python -m findoclens parse <pdf> --page N --backend auto|native_v2|native_grid|docling|ocr_rapid --format json,md"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from . import backends
from .render import draw_evidence, to_markdown
from .router import route, run_model_backend
from .runner import run_backend
from .validator import validate_prediction


def main(argv=None):
    ap = argparse.ArgumentParser(prog="findoclens")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("parse", help="extract tables from one PDF page")
    p.add_argument("pdf")
    p.add_argument("--page", type=int, default=0, help="zero-based page index")
    p.add_argument("--backend", default="auto", choices=["auto", *backends.REGISTRY])
    p.add_argument("--format", default="json,md", help="comma list of json,md,png")
    p.add_argument("--out", default="runs")
    p.add_argument("--verify", action="store_true", help="auto: always cross-check with Docling")
    p.add_argument("--no-models", action="store_true", help="auto: never launch model backends")
    p.add_argument("--repeat", type=int, default=1, help="non-auto: repeat in-process to separate cold/warm")
    a = ap.parse_args(argv)
    fmts = set(a.format.split(","))
    if a.backend == "auto":
        d = route(a.pdf, a.page, a.out, verify=a.verify, allow_models=not a.no_models)
        out = Path(a.out) / "auto" / f"{Path(a.pdf).stem}_p{a.page}"
        out.mkdir(parents=True, exist_ok=True)
        (out / "prediction.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        (out / "tables.md").write_text(to_markdown(d), encoding="utf-8")
    else:
        d, m, out = run_backend(a.backend, a.pdf, a.page, a.out, a.repeat)
    if "png" in fmts:
        import fitz  # noqa
        draw_evidence(a.pdf, a.page, d, out / "evidence.png")
    summary = {"out": str(out), "backend": d["backend"], "status": d["status"], "tables": len(d["tables"]),
               "rows": sum(len(t["rows"]) for t in d["tables"]),
               "issues": [i.get("code") for i in d["issues"]]}
    if a.backend == "auto":
        summary["routing"] = d["meta"]["routing"]["decisions"]
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0 if d["status"] in ("ok", "partial") else 2


if __name__ == "__main__":
    sys.exit(main())
