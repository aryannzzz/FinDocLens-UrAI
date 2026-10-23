# Independent benchmark and red-team workstream

This is a runnable benchmark, not a model leaderboard. `baseline_v2/` is immutable. The extraction/model workstream is separate. Start with [the audit](audit.md), [the measured report](reports/measured.md), and [the adapter contract](../docs/BENCHMARK_ADAPTER_CONTRACT.md).

Original benchmark evidence: two downloaded independent issuer pages (ELECOM and Daiwabo), OMRON blocked by HTTP 403, 13 synthetic development controls, and immutable AI-drafted reference annotations. The two independent pages have 55 rows, 119 numeric cells, and four explanation text cells. These issuers were exposed during parser design, not blind holdouts. The original page is development evidence only. Full original PDFs, selected PDFs, page renders and image crops are local artifacts under `data/` or `review/assets/`, excluded from Git pending redistribution review. Original download response metadata and hashes are tracked in `sources/` and `manifest.jsonl`.

**Current v3:** Aryan Jain explicitly declares that he personally compared all **197 annotated cell contents** (74 original, 56 ELECOM, 67 Daiwabo) with the original PDF images. Decisions are **bulk recorded from that declaration**, without invented dropdown clicks or per-cell inspection times. Structure, header links, merged spans and inferred periods remain unreviewed. The earlier 51/146 v2 history is preserved; these pages remain development-exposed, not blind holdouts. Current references: `human_gold/v3/`; scores: `results/human_v3/`. Check with `python -m benchmark.human_declaration --check benchmark/human_gold/v3`; replay with `benchmark.declared_scoring`. [Report](../docs/HUMAN_REVIEW_RESULTS.md).

## Reproduce

Use a virtualenv; do not change global Python, CUDA or drivers:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r benchmark/requirements.txt
bash run_benchmark.sh my_unique_run
```

The measured development session used an inherited-site-packages virtualenv with the same pinned PyMuPDF/Pillow versions; no packages or drivers were installed. Python and installed package versions are recorded per run. The script attempts source downloads, rebuilds deterministic controls against frozen hashes, validates references, runs tests (including all 25 frozen tests in a temporary copy), measures fresh/warm inference, writes JSON metrics/Markdown, and makes the review sheet. It never regenerates gold. On an unavailable source, the manifest records the failure; known available sources continue. If no independent source is accessible, only development/control results are possible, with that limitation explicit. `BENCHMARK_OFFLINE=1 bash run_benchmark.sh ID` uses cached PDFs and records uncached sources as unavailable.

Individual commands:

```bash
.venv/bin/python -m benchmark.dataset                # first download, real response metadata
.venv/bin/python -m benchmark.dataset --offline      # reconstruct selected pages from cached originals
.venv/bin/python -m benchmark.adversarial --materialize
.venv/bin/python -m benchmark.validate
.venv/bin/python -m benchmark.check
.venv/bin/python -m benchmark.run --run-id independent_ID
.venv/bin/python -m benchmark.run --manifest benchmark/adversarial_manifest.jsonl --run-id adversarial_ID
.venv/bin/python -m benchmark.review --failures benchmark/reports/v2_independent_ID.json
.venv/bin/python -m benchmark.report --summary benchmark/reports/v2_independent_ID.json benchmark/reports/v2_adversarial_ID.json
```

Run IDs are create-only. `benchmark.run --run-id ID --resume` rebuilds a missing summary from completed artifacts without rerunning or rescoring models. Use a new run ID after implementation changes. `runs/<backend>/<doc_id>/<run_id>/metadata.json` records command, source/download hashes, UTC time, Git commit, worktree-dirty flag, exact benchmark code digests, model/checkpoint metadata, package/hardware probe, cold/warm outcomes and artifact paths. Each trial stores unchanged `original_result.json`, canonical `prediction.json`, `measurement.json`, and `metrics.json`. Cold source screenshots are local-only PNGs. Failure trials retain error/OOM/timeout status and full known-gold denominators. The worker never reads gold.

## Reference review

From the repository root, run `.venv/bin/python -m benchmark.review --serve` and open **http://127.0.0.1:8765/benchmark/review/**. This builds/checks the ignored source images from already cached PDFs, then starts a localhost-only server. No downloads or models are used. `benchmark/review/assets/` is deliberately Git-ignored; a tracked HTML file alone does not include its images, and assets in another Git worktree are not shared.

The interface shows the actual 200dpi source page beside exact reference values, labels, hierarchy and headers. Select original, ELECOM or Daiwabo; click a row, cell or header to highlight and magnify its source region. Both image panels support zoom and scrolling. Enter your name, choose `accepted`, `correction_needed` or `unreadable`, add correction/reason notes, and export JSON. Browser drafts survive reload where local storage is available; export before closing to keep a portable copy. Export never modifies gold or human verification counts. `review/audit_template.json` remains an unreviewed template.

`.venv/bin/python -m benchmark.review --check` detects missing/corrupt images, broken source URLs, changed PDFs/references, and embedded annotations that differ from gold. `benchmark/review/index.html` also works as a direct local file **after building**, without remote scripts or fetch requests. More detail: [`review/README.md`](review/README.md). The optional failure contact sheet is still generated with `--failures`; it is separate from the source verification interface.

Prioritize all table boundaries, all headers/units, exact Japanese labels, all signs/dashes/negative-zero and at least 20 numeric cells per independent page; preferably review the complete references. Preserve the existing version, crop evidence, old/new token, reason, reviewer, timestamp and prior gold hash for every correction. Partial review must remain `partially_human_verified` with an exact count and scope. `--require-human` rejects AI drafts. Only complete independently reviewed references may be `human_verified`. Do not change gold to match model output. Any new reference needs a separately versioned lock manifest and reevaluation report, not replacement of an existing run.

`annotate.py` is a source-only, create-once bootstrap for the three available reference pages, using explicit draft regions and the frozen original TSV. It never reads holdout predictions. The original reference inherits the disclosed AI transcription. Independent references use native PDF text, so common text-layer errors remain possible despite AI image inspection. `annotation_template.json` is a scaffold for OMRON or a new issuer; it is intentionally incomplete and cannot be scored. Table/header/row/cell counts in the references are AI assertions awaiting human confirmation.

## Metrics and controls

All metrics expose numerator and denominator (P/R/F1 include matched/gold/predicted). Raw cell exactness removes only Unicode whitespace; signs, digits, plus, commas, decimals and monetary glyphs stay exact. Numeric typed/status equality is separate and never reparses predicted raw to repair a wrong typed value. All-cell scores include explanatory text; numeric-only scores exclude it. Failed and abstained pages score zero against every known gold slot. OMRON has no known reference and is counted in candidate availability, not an invented cell denominator. Micro summaries are separated by development/holdout, source/synthetic, issuer relation and annotation confidence; per-document scores are primary.

Matching is one-to-one, without assuming equal row counts/order or matching IDs. Tables require page and bbox IoU >= .1; rows require whitespace-normalized label equality, with geometry/context/order for repeated labels. Cells use physical financial column indexes. Missing geometry is disclosed and penalizes localization. Metrics include table/row completeness, spurious predictions, exact raw labels, row order, raw/typed numeric fidelity, header period/role, grouped spans and parent links, full-path hierarchy edges, abstention, correct injected-missing abstention, missing/silent cell slots, and false assurance. An unrelated financial warning does not excuse an omission. No TEDS/GriTS/CER is claimed.

Controls: one digitally erased cell; erased negative marker; 300dpi rasterization removing the text layer while retaining visible content; 90-degree PDF rotation metadata; 150/200dpi scans; tiny CJK via 50% scaling; appended footnote marker; two/three subcolumns per year; nested merged headers; side-by-side synthetic tables; vertical CJK spacing. Every transformation records whether it changes visible truth. Modified-cell/sign/footnote references are separate derived files. All original-source variants share the development source family; synthetic layouts also stay in development. PDF metadata rotation success does not establish rotated-raster recognition.

## Limits and handoff

The native CPU parser succeeds on a similar independent layout and fails severely on a financial slide. No OCR, Docling or VLM inference was performed by this workstream. Their independently owned outputs can use the contract without changing this evaluator. Cold means fresh worker process, not flushed filesystem cache. Warm medians use three same-process repetitions; cold also exports evidence PNGs. CPU RSS is a process high-water mark, cumulative in warm trials. GPU driver probing failed; GPU allocation/VRAM peaks are unmeasured. AI-drafted gold, two available issuers, native-engine common-mode error, coarse table IoU, and strict label matching prevent strong generalization claims. Financial reconciliation is diagnostic only and never edits a value.
