# FinDocLens — Japanese financial-statement table extraction prototype (Ur AI take-home)

A small, auditable research prototype: it extracts balance-sheet-style tables from single PDF pages into one schema
(exact printed glyphs + typed value + explicit status + source boxes), with five interchangeable backends, one independent evaluator
and a lightweight viewer. **No model was trained. All references are AI drafts with zero human-verified cells.**
The measured results, their limits and the failure analysis are in [`RESULTS.md`](RESULTS.md); what a human must still check is in
[`docs/MANUAL_REVIEW_QUEUE.md`](docs/MANUAL_REVIEW_QUEUE.md).

## Backends (all CPU; no GPU was usable)
| name (`adapters.<name>`) | what it is |
|---|---|
| `native_v2` / `v2` | frozen baseline parser (`baseline_v2/`, untouched), projected by `findoclens` / by the benchmark's own loss-disclosing projection |
| `native_grid` | generalised text-layer parser: N numeric columns, several tables per page, grouped headers, left/right/centre alignment |
| `docling_cmtrue`, `docling_cmfalse` | Docling layout + TableFormer (ACCURATE) on the text layer, `do_cell_matching` on / off |
| `docling_rapidocr` | Docling + RapidOCR (PP-OCRv6, Japanese) for raster pages |
| `auto` | rule-based router over the above (native first, models only when needed) |
| ablations | `docling_regions` (native table proposals → Docling per region), `docling_rapidocr_medium` |

## Setup
```bash
python -m venv --system-site-packages .venv && .venv/bin/python -m pip install -r requirements.txt        # PyMuPDF, Pillow (native backends + harness)
# optional model environment (CPU wheels, ~1.7 GB; never touches system Python/CUDA) – see docs/SETUP_MODELS.md and docs/ENVIRONMENT.md
uv venv .venv-docling --python 3.12 && uv pip install --python .venv-docling/bin/python \
    --extra-index-url https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match -r requirements-models.txt
```
Source pages are downloaded locally and are **not** redistributed (`data/`, `benchmark/data/` are git-ignored; hashes are in
`benchmark/manifest.jsonl`). OMRON could not be downloaded (HTTP 403) and is absent from every result.
```bash
.venv/bin/python -m benchmark.dataset              # fetch ELECOM / Daiwabo (OMRON fails with 403), verify hashes, cut the selected pages
.venv/bin/python -m benchmark.adversarial --materialize && .venv/bin/python -m benchmark.raster_variants    # controls + raster derivatives (create-once)
```

## Reproduce
```bash
bash run_demo.sh                                   # tests, native runs on every page, viewer build (≈1 min, no models needed)
python -m unittest discover -s tests -q            # 82 tests; includes the 25 frozen baseline tests in a temp copy
scripts/run_integration.sh native_grid RUNID       # one backend over main + adversarial + raster manifests (create-only run ids)
scripts/run_integration.sh docling_cmtrue RUNID .venv-docling/bin/python 3 1 3
python scripts/make_results.py --set native_grid=RUNID ...      # tables → results/ ; see RESULTS.md §10 for the exact command used
python scripts/build_viewer.py --run native_grid=RUNID ... && xdg-open viewer/index.html
```
Single page, any backend: `python -m findoclens parse <pdf> --page <zero-based> --backend auto|native_grid|docling|ocr_rapid --format json,md,png`.

## Layout
`baseline_v2/` frozen · `findoclens/` backends, router, validator · `adapters/` projection to the benchmark contract + per-backend entrypoints + contract checker ·
`benchmark/` evaluator, harness, references (`gold/`), controls, diagnostics · `scripts/` runners, reports, probes · `viewer/` static viewer ·
`runs/<backend>/<doc>/<run_id>/{cold,warm_N}/` raw + canonical predictions, metrics, measurements (immutable) · `docs/` setup, protocol, analysis, evidence.
