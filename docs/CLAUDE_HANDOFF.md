# Track B hand-off (for Codex benchmark + task 03 integration)

Branch `claude-backends` (worktree `/home/aryannzzz/findoclens-claude`). Base: `cd27035` (tag `v2-frozen`). `git diff v2-frozen -- baseline_v2` is empty.
Final commit hash: see the last line of this file's git log (`git log -1 --format=%H claude-backends`); the report in chat states it.

## What exists
`findoclens/` (schema, amounts, 3 CPU backends + Docling OCR path, validator, router, CLI, runner, compare), `scripts/` (matrix, crops, sweep, Paddle preflight),
`tests/test_findoclens.py` (25 tests, all pass; holdout tests skip if `data/pdfs/*.pdf` missing), `runs/` (predictions + run manifests + `summary.{json,md}`),
`docs/CLAUDE_{AUDIT_AND_MATRIX,RESULTS,RESEARCH_MEMO,HANDOFF}.md`, `docs/evidence/*.png`, `docs/logs/paddleocr_vl_preflight.json`, `data/manifest.json`, `run_demo.sh`, `README_BACKENDS.md`.
Not touched: `baseline_v2/`, `docs/EVAL_PROTOCOL.md`, `docs/USER_SIGNOFF.md` (no sign-off boxes ticked; no human verification was done), anything of the Codex benchmark/gold/metric code.

## How Codex's evaluator can consume predictions
`runs/<backend>[_<tag>]/<doc>_<variant>/prediction.json` is a `DocumentPrediction` (see `findoclens/schema.py`): `document_id, source_sha256, backend, model_revision, page (ZERO-based), page_bbox, tables[]`
plus `status, issues, capabilities, meta`. Table: `table_id, bbox, reading_order, headers[], rows[], issues[], unit, n_data_columns, checks[], grid`. Header: `header_id,text,period,role,bbox,colspan,rowspan,row_start,col_start,column_indices`.
Row: `row_index,label,raw_label,parent_path,bbox,type(item|total|section),cells[]`. Cell: `column_index,header_id,period,role,raw,value,status,bbox,backend,evidence_kind,notes`.
Deviations/extensions to be aware of (not hidden in the data): (1) `raw_label==label` (no normalisation applied); (2) cells with `column_index=-1`, `role=other` hold arrows/notes/text outside data columns and must be ignored for amount scoring; (3) `evidence_kind="table_model"` is unused — Docling cells are `native_pdf` (text layer) or `ocr`; (4) `status` vocabulary for a *page*: `ok|partial|no_tables|failed|needs_visual_review`; an extraction with zero numeric cells is forced to `failed`; (5) `grid` (Docling only) is the engine's lossless span grid; (6) `parent_path` is empty when `hierarchy_not_inferred` appears in table issues; Docling/OCR rows never carry hierarchy.
Provenance per run: `run_manifest.json` (run_id, UTC time, git commit with `+dirty` flag, URL via `data/manifest.json`, SHA, page, backend/model revision, package versions, CPU/RAM/GPU text, cold/warm timings, peak RSS, status, error, human-audit status `none`).

## Run it
```bash
python -m unittest discover -s baseline_v2/tests -p 'test_*.py' -q && python -m unittest discover -s tests -q
python -m findoclens parse <pdf> --page <zero-based> --backend auto|native_v2|native_grid|docling|ocr_rapid --format json,md,png [--verify] [--no-models]
python scripts/run_matrix.py    # needs .venv-docling (docs/SETUP_MODELS.md); `--rescore` recomputes metrics without running models
```
Environment variables: `FINDOCLENS_MODEL_PYTHON` (interpreter with Docling), `HF_HOME` (default repo-local `.cache/hf`), `FINDOCLENS_RAPID_LANG` (default `iso:ja`).

## Outstanding integration work (honest list)
1. Score all backends against Codex's independent gold for original/ELECOM/Daiwabo; my numbers are text-layer token agreement only (`CLAUDE_RESULTS.md` §6).
2. **OMRON p13**: download manually (server blocked automated access), then run the matrix; `%`/composition-pct and grouped-header paths are unmeasured on a real page.
3. Human sign-off of gold cells (`docs/USER_SIGNOFF.md` untouched); crop F1–F4/S1–S3 were checked by eye by the agent, which is not applicant verification.
4. `native_grid` was developed with the ELECOM idx 8 / Daiwabo idx 9 / ELECOM idx 12 pages in view → treat those scores as in-sample for it; ask for at least one more issuer (e.g. NTT Finance) that nobody has looked at.
5. Known `native_grid` defects: header words can leak into a `section` row on dense multi-line headers (ELECOM idx 12, table t1 row 0); centred spanning headers get single-column spans; no unit inheritance across sibling tables; bare 4-digit years are never treated as amounts; right-aligned numeric columns only; indentation hierarchy only when heading rows exist.
6. Router gaps: no selective crop re-run; OCR-only output always `needs_visual_review`; the "Docling token present in text layer but missing from native table ⇒ review" rule has no natural test case yet (logic only).
7. PaddleOCR-VL-1.6 not run (disk/RAM/GPU). If the applicant frees ≥8 GB and wants it: separate `.venv-paddle`, then `PaddleOCRVL().predict(...)`; add a backend with the same `extract` signature.
8. `.gitignore` is new on this branch (ignores `data/pdfs/`, `data/variants/`, `.venv*/`, `.cache/`, evidence PNGs under `runs/`); if Codex adds its own, merge as a union. Both branches may add `tests/`; my test module is `tests/test_findoclens.py` (no `__init__.py`).
9. Disk: `/` was 99 % full during this work (1.3 GB free). `.venv-docling` (1.5 GB) and `.cache/hf` (0.5 GB) are removable and gitignored.
