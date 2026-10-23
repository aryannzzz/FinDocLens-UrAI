# FinDocLens — Japanese financial-statement table extraction prototype (Ur AI take-home)

A small, auditable research prototype: it extracts balance-sheet-style tables from single PDF pages into one schema
(exact printed glyphs + typed value + explicit status + source boxes), with five interchangeable backends, one independent evaluator
and a lightweight viewer. **No model was trained. Original benchmark references remain immutable AI drafts.**
**Current v3:** Aryan Jain explicitly declares that he personally compared all **197 annotated cell contents** (74 original, 56 ELECOM, 67 Daiwabo) with the original PDF images. Decisions are **bulk recorded from that declaration**, without invented dropdown clicks or per-cell inspection times. Structure, header links, merged spans and inferred periods remain unreviewed. The earlier 51/146 v2 history is preserved; these pages remain development-exposed, not blind holdouts. See [current results and provenance](docs/HUMAN_REVIEW_RESULTS.md).
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
python -m unittest discover -s tests -q            # includes the 25 frozen baseline tests in a temp copy and the P0 regression tests
scripts/run_integration.sh native_grid RUNID       # one backend over main + adversarial + raster manifests (create-only run ids)
scripts/run_integration.sh docling_cmtrue RUNID .venv-docling/bin/python 3 1 3
python scripts/make_results.py --set native_grid=RUNID ...      # tables → results/ ; see RESULTS.md §10 for the exact command used
python scripts/build_viewer.py --run native_grid=RUNID ... && xdg-open viewer/index.html
```
Single page, any backend: `python -m findoclens parse <pdf> --page <zero-based> --backend auto|native_grid|docling|ocr_rapid --format json,md,png`.

## Manually verify the reference annotations

Run `.venv/bin/python -m benchmark.review --serve` from the repository root, then open **http://127.0.0.1:8765/benchmark/review/**.
The launcher regenerates/checks local source images from the cached PDFs; it downloads nothing. View the original, ELECOM and Daiwabo pages beside their annotations, click rows/cells to zoom, record decisions, and export JSON. Neither generation nor export changes references or human verification counts. Images are intentionally Git-ignored, so use this launcher after switching worktrees. See [`benchmark/review/README.md`](benchmark/review/README.md).

The original export, earlier bulk approval and v2 clarification remain archived under `review/human_signoff/`. The new `declaration_v3.json` records completed personal inspection of all 197 contents. Current references: `benchmark/human_gold/v3/`; scores: `results/human_v3/`. Check without inference with `.venv/bin/python -m benchmark.human_declaration --check benchmark/human_gold/v3` and the commands in [`docs/HUMAN_REVIEW_RESULTS.md`](docs/HUMAN_REVIEW_RESULTS.md). V1/v2 snapshots and historical ledgers remain frozen. See [`docs/SUBMISSION_STATUS.md`](docs/SUBMISSION_STATUS.md) for remaining requirements.

## P0 correctness pass (after the independent review)
Silent-loss, evaluator, merged-cell and exposure fixes with before/after evidence: [`docs/P0_FIXES.md`](docs/P0_FIXES.md); the generated table is
[`docs/P0_BEFORE_AFTER.md`](docs/P0_BEFORE_AFTER.md) (`python scripts/p0_before_after.py --out-json … --out-md …`); regression tests `tests/test_p0_regressions.py`.
`RESULTS.md` keeps the pre-fix `fin1` numbers as the development record; post-fix runs are `p0fix2_*`.

## Layout
`baseline_v2/` frozen · `findoclens/` backends, router, validator · `adapters/` projection to the benchmark contract + per-backend entrypoints + contract checker ·
`benchmark/` evaluator, harness, references (`gold/`), controls, diagnostics · `scripts/` runners, reports, probes · `viewer/` static viewer ·
`runs/<backend>/<doc>/<run_id>/{cold,warm_N}/` raw + canonical predictions, metrics, measurements (immutable) · `docs/` setup, protocol, analysis, evidence.
