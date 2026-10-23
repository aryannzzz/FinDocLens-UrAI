# Ur AI take-home — evaluator guide

**Read `FINAL_REPORT.md` first.** The implementation is frozen; the submission is an auditable prototype, not a complete financial-document product. The original email's objective and deadline are transcribed in `docs/ORIGINAL_ASSIGNMENT.md`.

V3 contains **197 author-verified cell contents**, accepted by explicit personal source-image verification declaration and bulk recorded without invented clicks/times. Native-grid/auto: **193/197**; native proposals + Docling: **181/197**; frozen v2: **132/197**. Four native-grid mismatches concern Daiwabo explanation text/arrow placement. Structure remains unreviewed; all three source pages are development-exposed, not blind tests.

## 1. Quick offline inspection

Unzip and `cd` into `ur_ai_submission/`. Open `FINAL_REPORT.md` (or its printable HTML/PDF), `results/human_v3/summary.json` and `viewer/index.html`.

The ZIP viewer is immediately usable offline for the **supplied original page and its controls/synthetic pages**, with source images, clickable evidence, tables, warnings, JSON and Markdown. It shows stored historical AI-draft metrics, not newly human-certified structure; V3 content scores are in the report. ELECOM/Daiwabo source images are intentionally not bundled. Their predictions/results are included as JSON. The original human-review UI for all three documents becomes available after step 4.

## 2. Small native environment and read-only result replay

Python **3.13** was used for native runs; Python **3.12** for the optional model environment. PyMuPDF's pinned version matters for byte-identical rendered/source-derived artifacts. No CUDA or system-driver changes are needed.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-delivery.lock.txt
.venv/bin/python scripts/submission_check.py
.venv/bin/python -m benchmark.adversarial --materialize
.venv/bin/python -m unittest tests.test_frozen tests.test_benchmark tests.test_adapters tests.test_p0_regressions -v
```

`submission_check.py` verifies the frozen baseline, V1/V2/V3 snapshot locks, original decision export, declaration, package-file hashes, and **48 stored V3 content comparisons**. It uses the existing evaluator, never a model. It can run without the additional source PDFs. This is replay from locked snapshots; full source-PDF-backed import reproduction is step 4. The test subset includes the 25 original tests in an isolated copy and requires no third-party source download or model weights. Materializing original-page controls first avoids two otherwise optional control skips. Exact tested counts are in `submission/VALIDATION.md`.

For a fully offline computer, install these dependencies from a prepared wheelhouse; no virtualenv or installed package is bundled. `requirements-models.lock.txt` and `docs/SETUP_MODELS.md` preserve the historical model environment for optional later work. Model reproduction is not needed to inspect/replay this submission and was not rerun for delivery.

## 3. CLI demo on the supplied assignment page

```bash
.venv/bin/python -m findoclens parse baseline_v2/source.pdf --page 0 --backend native_grid --format json,md,png --out runs/evaluator_demo
.venv/bin/python -m findoclens parse baseline_v2/source.pdf --page 0 --backend auto --no-models --format json,md --out runs/evaluator_router
```

The native CLI writes `runs/evaluator_demo/native_grid/source_p0/{prediction.json,tables.md,evidence.png,run_manifest.json}`. Auto writes under `runs/evaluator_router/auto/source_p0/`. Use a fresh output directory to preserve earlier samples. JSON contains exact glyphs, typed values/status, boxes and warnings; Markdown is a convenient view, not the lossless reference. Small pre-generated samples are in `submission/sample_outputs/`. These smoke checks are not new benchmark measurements.

The static viewer also works from `file://`. If preferred:

```bash
.venv/bin/python -m http.server 8765 --bind 127.0.0.1
```

Open **http://127.0.0.1:8765/viewer/index.html**. It does not call models or send data anywhere.

## 4. Optional complete source-backed checks and human-review UI

Added issuer source PDFs and their rendered images are omitted pending redistribution review. `benchmark/manifest.jsonl` records URLs, page indexes, hashes and historic unavailable status. The supplied assignment PDF is included. OMRON failed acquisition and is excluded; never count it as a successful test. Choose one source-restoration method:

```bash
# Prefer an existing cache: DIR/elecom_p9/page.pdf and DIR/daiwabo_p10/page.pdf,
# or corresponding original.pdf files. Relative cache paths are supported.
.venv/bin/python scripts/restore_submission_sources.py --cache source_cache

# Alternative: explicitly download only the two available public source PDFs.
# No models are downloaded. Network/source availability is not guaranteed.
.venv/bin/python scripts/restore_submission_sources.py --fetch
```

Run only one alternative. The helper checks frozen hashes and installs ignored selected-page PDFs without rewriting manifests, references or predictions. Corrupt/different bytes are rejected. Then:

```bash
.venv/bin/python -m benchmark.adversarial --materialize
.venv/bin/python -m benchmark.raster_variants --materialize
.venv/bin/python -m benchmark.validate
.venv/bin/python -m benchmark.human_declaration --check benchmark/human_gold/v3
.venv/bin/python -m benchmark.declared_scoring --reference benchmark/human_gold/v3 --config review/human_signoff/evaluation_v3.json --out results/human_v3 --verify
.venv/bin/python scripts/report_human_declaration.py --check
.venv/bin/python -m benchmark.review
.venv/bin/python -m benchmark.review --check
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m benchmark.review --serve --port 8765
```

With only selected-page PDFs restored, the full suite runs 170 tests with **7 optional legacy full-filing tests skipped**; V3/source-review tests still run. Those legacy tests use `data/pdfs/elecom.pdf` and `data/pdfs/daiwabo.pdf`, whose full-source hashes are in `data/manifest.json`. Supplying those exact full filings enables all 170 tests (as tested locally). Do not mistake optional asset skips for passing tests.

Stop the static HTTP server from step 3 before binding the same port. Open **http://127.0.0.1:8765/benchmark/review/index.html**. The original, ELECOM page 9 and Daiwabo page 10 load at 200 dpi; all **197/197 decisions restore as accepted**, with the declaration basis visible. Zoom rows/cells and export JSON; later browser edits do not silently rewrite snapshots. Regeneration needs no model inference.

## Package map and limits

- `findoclens/`, `adapters/`, `baseline_v2/`: implementation and immutable original regression snapshot.
- `tests/`, `benchmark/`: test/evaluation framework, source/exposure manifests, original AI drafts and separate human V1/V2/V3 snapshots.
- `results/`, selected `runs/`: stored comparisons, measurements, raw output and compact provenance. `submission/PACKAGE_MANIFEST.json` lists included files and omitted run paths; original repository history is preserved.
- `FINAL_REPORT.*`, `RESULTS.md`, `docs/`, `review/`: concise report, detailed historical measurements, resource/model records, independent review, failures and human provenance.
- `viewer/`: ready offline evidence viewer for redistributable inputs; `scripts/build_viewer.py` can regenerate a full local viewer after source restoration.
- `AI_COLLABORATION.md` and `submission/TRANSCRIPT_CHECKLIST.md`: assistance disclosure and **required separate full-transcript attachments**, not fabricated transcript content.

No blind generalization, full structural certification, real noisy-scan robustness, GPU measurements or VLM result is claimed. Header links, spans, hierarchy and inferred periods remain unreviewed research limitations; they do not block delivering the honestly scoped prototype.
