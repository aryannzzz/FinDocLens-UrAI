# FinDocLens — track B (backends, router, schema, validator)

Status: research prototype. **No model was trained.** Frozen `baseline_v2/` is untouched (25 original tests still pass).
Measured results, blockers and the model comparison are in `docs/CLAUDE_RESULTS.md`; the pre-work audit/plan is in
`docs/CLAUDE_AUDIT_AND_MATRIX.md`; hand-off notes for integration are in `docs/CLAUDE_HANDOFF.md`.

## Quick start
```bash
python -m pip install -r baseline_v2/requirements.txt            # native backends only (PyMuPDF)
python -m unittest discover -s tests -v                           # new tests (holdout tests skip if PDFs absent)
python -m unittest discover -s baseline_v2/tests -p 'test_*.py'   # frozen original regression
python -m findoclens parse baseline_v2/source.pdf --page 0 --backend auto --format json,md,png
python -m findoclens parse data/pdfs/daiwabo.pdf --page 9 --backend native_grid --format json,md,png
```
Model backends need the optional venv (`docs/SETUP_MODELS.md`):
```bash
python -m findoclens parse data/pdfs/elecom.pdf --page 8 --backend docling --format json,md
python -m findoclens parse data/pdfs/elecom.pdf --page 8 --backend auto --verify      # router + Docling cross-check
python scripts/run_matrix.py                                                              # full matrix -> runs/summary.{json,md}
```
Artifacts: `runs/<backend>[_<tag>]/<doc>_<variant|pN>/{prediction.json,tables.md,run_manifest.json,...}`.

## Layout
| path | role |
|---|---|
| `findoclens/schema.py` | common schema per `docs/EVAL_PROTOCOL.md` (DocumentPrediction → Table → Header/Row → Cell) |
| `findoclens/amounts.py` | exact token semantics (`△`, `△0` negative_zero, `－` not_reported ≠ 0, `+`, decimals, `%`) |
| `findoclens/backends/native_v2.py` | frozen v2 wrapped as `extract(pdf, page_index) -> DocumentPrediction` (imports `baseline_v2/parser_v2.py` unmodified) |
| `findoclens/backends/native_grid.py` | generalised text-layer parser: N columns, multiple tables/page, headers w/ colspan, roles, units, wrapped labels |
| `findoclens/backends/docling_backend.py` | Docling TableFormer ACCURATE (`do_cell_matching` True/False) and Docling+OCR; raw DoclingDocument JSON saved |
| `findoclens/validator.py` | conservative arithmetic diagnostics (delta, subtotal, assets=liabilities+equity); never edits a cell |
| `findoclens/router.py` | inspectable routing rules (`--backend auto`) |
| `findoclens/compare.py`, `goldcheck.py` | agreement / text-layer token recall / dev-gold exact match |
| `findoclens/runner.py`, `runinfo.py` | one-backend runner + run manifest (cold/warm, peak RSS, versions, hardware, git commit) |
| `scripts/run_matrix.py`, `scripts/make_crops.py` | experiment matrix and evidence crops |

## Invariants honoured
`raw` is never rewritten; `value`/`status` are derived beside it. Dash ≠ zero. Every row/cell keeps page coordinates and
`backend`/`evidence_kind`. Failed/empty extractions return `status=failed|no_tables|needs_visual_review`, never `ok`.
Validator output is diagnostic only. Model predictions never overwrite native glyphs; disagreements are listed.
