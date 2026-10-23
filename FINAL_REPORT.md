# FinDocLens: auditable Japanese financial-table extraction

Aryan Jain · Ur AI Document Intelligence & VLM R&D internship take-home · 23 October 2026

## Problem and conclusion

The assignment supplies a Japanese consolidated balance-sheet page and asks for a parser and a defensible definition of correctness. FinDocLens is a reusable single-page prototype with native PDF geometry, pretrained document models and explicit source evidence. No model was trained and no VLM was executed.

The narrow finding is that separating table regions and financial columns matters more than recovering digits alone. On three development-exposed source pages, native-grid matches **193/197 human-reviewed cell contents**, compared with **181/197** for native proposals plus Docling and **132/197** for the frozen baseline. This supports an in-sample engineering improvement, not blind generalization or complete table reconstruction.

## Architecture and implementation

`findoclens/` implements extraction and routing; `adapters/` projects backend outputs into `benchmark-1.0`; `benchmark/` handles fixed references, scoring and resource measurement. CLI JSON/Markdown and a local evidence viewer expose results, warnings and coordinates. Native/model predictions are retained separately from references.

Each cell preserves its exact `raw` glyph string, typed `value`, explicit `status`, page/table/row/column identity and evidence box. `△0` retains negative-zero status; `－` is null/not_reported, not zero. Arithmetic checks warn without rewriting amounts. Empty/failed extraction does not count as success.

**Native-grid.** PyMuPDF words are grouped by text-line geometry; adjacent signs are joined with numeric tokens. Repeated right, left or centre edges identify financial columns, with right alignment winning ties. A nonnumeric segment after amounts starts a new label segment, separating side-by-side tables. Rows attach to column-pattern table proposals; header lines above the body provide periods/roles and candidate spans. Ambiguous inferred spans and missing content are flagged. The frozen baseline assumes one two-period table; native-grid supports multiple regions and variable columns, including one-column cases covered by subsequent regression fixes. These are geometric heuristics, not learned structure or guaranteed arbitrary-layout support.

**Docling/TableFormer and OCR.** The pretrained layout model proposes table regions; TableFormer ACCURATE predicts grids. Experiments compare cell matching on/off, RapidOCR Japanese recognition for rendered pages, and native region proposals followed by Docling per region. Raw backend output is kept before normalization. Model checkpoints, package pins and options are recorded in `docs/ENVIRONMENT.md` and `requirements-models.lock.txt`.

**Hybrid router.** Logged text/image-density signals, native-grid versus baseline disagreement, amount-like labels, missing slots, completeness warnings and arithmetic alarms guide routing. Clean native pages avoid model calls; raster-like pages require OCR; suspicious native output can be cross-checked by Docling. Native glyphs are not silently replaced by model guesses. Disagreement remains reviewable. These rules are not calibrated confidence; agreement is not proof of correctness.

## Evaluation and V3 provenance

The three sources are the supplied page, ELECOM PDF page 9 and Daiwabo PDF page 10. ELECOM and Daiwabo are independent issuers but were exposed during development. Original derivatives remain in the same source-family cohort; synthetic layouts are separate controls. OMRON acquisition failed and contributes no score. There is no genuinely unseen test set.

The author personally compared **all 197 annotated cell contents** with original PDF images and declared them correct: 74 original, 56 ELECOM, 67 Daiwabo. Decisions were **bulk recorded from this explicit declaration**, without inventing dropdown events or per-cell inspection times. V3 is a separate locked snapshot; original AI drafts, v1/v2 decisions and experimental outputs are preserved. One author reviewing existing drafts carries confirmation-bias limitations.

The denominator is **193 financial-column slots plus 4 explanatory text cells**. One-to-one matching uses table geometry, normalized row label and physical column, never values to choose a row. Missing/abstained cells stay in the denominator. Raw comparison removes whitespace only; typed accuracy compares value and status. Token recall is a separate diagnostic: the baseline finds 18/63 Daiwabo numeric tokens but places only 2/63 financial cells correctly.

| Backend | Raw content | Value/status | Financial raw |
|---|---:|---:|---:|
| Frozen v2 / native_v2 | 132/197 (67.01%) | 132/197 | 132/193 |
| Native-grid / auto | **193/197 (97.97%)** | 193/197 | **193/193** |
| Docling, matching on | 130/197 (65.99%) | 130/197 | 130/193 |
| Docling, matching off | 130/197 (65.99%) | 130/197 | 130/193 |
| Docling + RapidOCR, digital pages | 130/197 (65.99%) | 130/197 | 130/193 |
| Native proposals + Docling regions | **181/197 (91.88%)** | 181/197 | 181/193 |

Both stored fin1 and post-fix selections yield these content counts; V3 rescoring invokes no inference. All paths match original 74/74 and ELECOM 56/56. Daiwabo accounts for the differences: native-grid 63/67, regions 51/67, baseline 2/67, page Docling paths 0/67. The four native-grid mismatches are **explanatory text/arrow placement**, not financial digit errors.

Content accuracy is conditional on the retained label/geometry alignment context. It does **not** certify segmentation, hierarchy, header links, row/column spans, units, roles or completeness. All 14 header annotations, 193 numeric period associations and 82 hierarchy edges remain structurally unreviewed. Twelve Daiwabo lower-table numeric periods are inferred/unprinted; 17 upper change intervals are inferred semantics. Historical structural scores remain AI-draft diagnostics, never human-certified accuracy. TEDS/GriTS were not claimed without suitable grid/span gold.

## Resource measurements and ablations

Historical fin1 CPU measurements used an Intel i5-12450H, 15.7 GiB RAM and constrained available memory. GPU/VRAM results are N/A: no GPU was usable. Cold means the first call in a fresh worker, including model loading, rendering, extraction and serialization; warm is repeated calls in that worker with reopening/rerendering. OS caches were not flushed. Main-page runs used three warm repetitions; there is one cold sample per page and no confidence interval. The rows below are medians over the three source pages; RSS is the maximum worker peak over pages.

| Backend | Cold | Warm | Peak worker RSS |
|---|---:|---:|---:|
| Frozen v2 | 160 ms | 31 ms | 84 MB |
| Native-grid | 173 ms | 34 ms | 85 MB |
| Docling matching on / off | 11.7 / 13.6 s | 7.5 / 6.6 s | 1427 / 1422 MB |
| Docling + RapidOCR | 17.2 s | 10.3 s | 2080 MB |
| Native regions + Docling | 13.5 s | 7.3 s | 1367 MB |
| Auto | 271 ms | 69 ms | 85 MB |

Timings are not new V3 measurements. Model calls use a separate CPU environment; router child-process memory is recorded separately and is not represented by the 85 MB native-only main-page number. Background load varied; speed ratios are descriptive, not controlled hardware-wide claims.

Region proposals improve Daiwabo from 0/63 to 51/63 financial matches for Docling; the unruled lower table remains missing and explicitly warned. This implicates page-level region detection, without proving TableFormer correct on every crop. Matching-off failures trace to whole-row PDF text lines not fitting individual cell rectangles. A larger Japanese OCR model added 139 MB of weights and was about five times slower without materially resolving kanji-label errors. Raster scores are from clean PDF renders, not real noisy scans; their references remain derived AI drafts, outside V3's 197-cell human scope.

## Failure analysis and limits

- **Silent omission:** the baseline drops 65/67 Daiwabo cells while returning partial output. Native-grid still fragments vertically stacked Japanese labels on `vertical_spacing`, losing 16/16 strictly aligned cells despite retaining numbers. This known regression remains visible.
- **Structure:** wide left-aligned headers can create ambiguous spans. Real merged-cell/grouped-header coverage is limited; numeric body spans are flagged rather than replicated. Lower-table periods must not be guessed into gold.
- **OCR:** digits can be recovered while Japanese labels differ. A lone `－` may have no detection box. Ink-based warnings flag possible dropped placeholders without guessing a glyph, with false positives on flattened structural slots.
- **Evaluation/reliability:** fixed denominators prevent success by omission, but matching depends on draft structure. Partial-status/warning conventions affect silent-omission and false-assurance rates; they are not calibrated safety probabilities. Independent AI review found flaws, prompted scoped fixes, and did not independently certify the gold.

The submission is an auditable research prototype, suitable for technical discussion, with explicit unsupported cases. It does not establish unseen-layout accuracy, full structural correctness, real-scan robustness, GPU performance or VLM capability. Implementation is frozen for delivery; no further research is required to reproduce the packaged evidence. See `START_HERE.md`, `docs/HUMAN_REVIEW_RESULTS.md`, `RESULTS.md` and the independent review reports for commands, exact counts and history.
