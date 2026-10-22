# Research note — Reliable financial-table reconstruction from Japanese PDFs

**Ur AI — Document Intelligence & VLM R&D take-home** | October 22, 2026

## Executive answer

The most defensible approach for a corpus with both text-native and image-only financial filings is **route by document modality**, use an **evidence-preserving layout engine**, then apply **domain-aware structural and numerical validation**. For the supplied digital PDF, a lightweight, unsupervised geometric extractor is both faster and more lossless than OCR. Complex tables and scans warrant a learned table-structure model or VLM. A validator is an error detector, not a data-repair mechanism.

This submission implements and tests the first branch, plus a visual-review interface. It intentionally does not claim an end-to-end pretrained-VLM experiment.

## 1. Improvements by stage

| Stage | Common failure | Implemented v2 improvement | Next model-assisted experiment |
|---|---|---|---|
| Modality detection | Scans yield empty native text | Explicit `needs_visual_fallback` (abstention) | Route textless/low-confidence pages to a Japanese-supporting OCR/VLM pipeline |
| Table/column discovery | Fixed x cutoffs break on resize/reposition | Cluster repeated right edges of numeral spans, infer anchors dynamically | Train/use Table Transformer (TATR) or Docling TableFormer for irregular/merged layouts |
| Row segmentation | Native PDF splits `△` from following digits; positional lines fragmented | Merge physical text rows and adjacent numeric spans based on geometry; retain bounding boxes | Learned line/row detectors where bounding-box logic fails |
| Text recognition | OCR misreads CJK, punctuation, digits | Direct PDF glyph extraction; separate pdfplumber transcription agreement | PaddleOCR-VL full layout+recognition pipeline on scans; normalize per-script OCR confidences |
| Header/semantic mapping | Reversed years, lost `千円` unit | Extract year-end dates, map to visual column order, preserve original unit | Header graph prediction for multi-row/merged/spanning headings |
| Structure | Flat CSV loses category/asset family relations | Indentation hierarchy, category totals, gross/depreciation/net associations | Table cell relation graph/HTML structure model + constrained schema parsing |
| Values | `△0` silently becomes positive zero; `－` becomes zero | Store both verbatim token and parsed typed value, including explicit negative-zero/dash flags | Fine-grained sign/dash anomaly model; force visual review on disagreements |
| Validation | Wrong cells assigned to a plausible subtotal | Subtotal, total-asset and net-asset checks, return signed differences | Learn calibrated risk thresholds from held-out human-labelled errors |
| Explainability | Can't find origin of a reported number | Every label/cell has page-coordinate bbox; annotated audit image | Interactive reviewer with crop and source/candidate diff |
| Evaluation | A single PDF demo looks deceptively perfect | Human-readable TSV reference + exact glyph/semantic/path metrics + mutation scenarios | Out-of-template tests across independent companies and years, TEDS/GriTS for structural models |

## 2. Model/backend investigation

- **Docling / TableFormer**: official documentation describes accurate vs fast table-structure modes and optional mapping of recognized cells to the underlying PDF text. Excellent candidate for complex *digital* table structure, which should be independently compared against our glyph-preserving baseline. Source: https://docling-project.github.io/docling/usage/advanced_options/
- **Microsoft Table Transformer / PubTables-1M**: separates table detection and structure recognition, with full cell/word bounding boxes. Critically, **its structure model does not by itself perform OCR**; input text must be supplied separately. The official repository includes GriTS evaluation and pretrained weights, including models trained on FinTabNet-like layouts. Sources: https://github.com/microsoft/table-transformer and https://www.microsoft.com/en-us/research/publication/pubtables-1m/
- **PaddleOCR-VL (including VL-1.6)**: an official full pipeline combines layout analysis with a VLM to interpret cropped document regions; it supports Japanese. Its own documentation warns that running only the 0.9B base VLM is not equivalent to running the full parsing system. Strong candidate for scanned Japanese pages, skewed and visually complex sources. Source: https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/PaddleOCR-VL.md
- **MinerU**: provides a richer PDF layout/table parsing pipeline, including cross-page table merging. Attractive as an integrated comparator; needs an empirical accuracy/speed evaluation on the target collection. Source: https://github.com/opendatalab/mineru
- **Marker**: document conversion with optional model correction and a table-only converter; useful for a second baseline. Source: https://github.com/VikParuchuri/marker

**Key scientific decision:** do not promote benchmark numbers from vendors/repositories into claims about Japanese balance-sheet accuracy. The evaluation set and outputs here are distinct.

## 3. Algorithm implemented

1. Use PyMuPDF to get each PDF span's Unicode and PDF-coordinate rectangle.
2. Merge spatially coincident spans into rows; merge `△`/`▲`/`−` plus adjacent digits into *one raw monetary token*. Parse `－` as `null`/not reported and preserve literal `△0`.
3. Select candidate numeric rows and infer their two monetary column right-edge anchors by repeated endpoint clustering. Reject unstable anchors.
4. Parse the complete header line for both Japanese fiscal dates, then associate columns in left-to-right order. Preserve `（単位：千円）`.
5. Infer table extent from the data rows' measured pitch, excluding unrelated page title/footer. Detect partial rows and retain missing cells with warning status.
6. Build category paths from indentation; total rows attach to their named ancestor section; associate depreciation and net rows with their correct gross asset.
7. Preserve exact account names and raw tokens. Export wide CSV for humans and semantically richer JSON with bounding boxes, provenance and status flags.
8. Check subtotal/total arithmetic, respecting inevitable displayed rounding differences; do **not** change the source data. Fail as a *warning*, not a fabricated correction.
9. Cross-check each cell against pdfplumber's independently implemented *PDF-native text extraction*. It is not independent OCR or ground truth.
10. If a failure is flagged, create a cropped image and a strict, provenance-focused review request; no automatic model or correction is claimed.

## 4. Observed quantitative results

| Test | Frozen v1 extracted monetary rows | V2 extracted monetary rows | V2 raw cells vs reference |
|---|---:|---:|---:|
| Supplied original PDF | 37 | 37 | 74/74 |
| Uniformly scaled to 79% on enlarged canvas | 37 | 37 | 74/74 |
| Uniformly scaled to 123% on enlarged canvas | 0 | 37 | 74/74 |
| Shifted horizontally on enlarged canvas | 0 | 37 | 74/74 |
| Scaled + unrelated numeric footer | 10 | 37 | 74/74 |
| Duplicated as two pages | 74 | 74 | 148/148 combined |

Additional perturbations: deleting one original cell yielded **73 extracted values and a missing-cell warning**; deleting a `△` negative sign yielded **73/74 correct raw strings, and a financial-reconciliation warning**. A raster-only version yielded **no made-up rows** and an explicit visual-backend-needed error. On the original, both independent PDF text libraries agreed on **74/74** cells. **25 unit/integration tests pass.** Script runtimes on the container are roughly 10 ms for this specific page (excluding setup, manual visual review and external VLM inference).

**Important validity warning:** every document perturbation here is a *transformed copy of one provided page*, not an independent unseen company or layout. All reference labels and values were transcribed during this task by the AI assistant and should be separately checked by the applicant. Perfect results on this single page do not estimate real-world generalized accuracy.

## 5. What "correct" should mean on a proper holdout

Evaluate at several levels, not just readable Markdown.

**Exact-cell score**: fraction of gold cells with byte-for-byte exact monetary glyphs after only a published whitespace policy (preserve `△` and `－`). **Semantic numeric score**: per-cell normalized signed value match, and separate accuracy for negative-zero/dash convention. **Row alignment F1**: match unique line items with order and parent context. **Hierarchy edge F1**: correct category/account relationships, critical for repeated `その他` and `減価償却累計額` entries. **Column-header association**: correct previous/current dates and currency unit. **Table structure**: TEDS or GriTS for merged/spanning cells. **Coverage/abstention**: not only accuracy on extracted cells, but how often the engine silently misses a row or flags a genuine ambiguous region. **Financial consistency**: rate and magnitude of arithmetic violations; never treat it as sufficient for correctness.

Split by **company/template** rather than random page because same-source documents share layout, styles, and vocabulary. Report paired bootstrap intervals for a sufficiently large corpus. Include scans, rotation, low resolution, negative symbols, parenthetical notes, multiple tables, spanning headings, cross-page continuation, and confusable glyphs in the holdout.

## 6. Recommended next experiment (not executed)

1. Collect 10–20 additional public Japanese filings from different issuers and layouts; manually annotate 2–3 pages of each (or at least 200–500 cell entries), with bounding boxes and structural edges. Avoid using those for heuristic development.
2. Compare **native v2** vs **Docling TableFormer accurate** vs **PaddleOCR-VL full pipeline**; optionally compare MinerU. Fix model versions and prompts. Reconstruct to a common schema and compute same metrics.
3. Choose a **router** from text density, suspicious native glyphs, alignment regularity, cell disagreement, and visual page layout. Then invoke the slower model **only when expected uncertainty justifies its cost**.
4. Use hard constraints from accounting identities as alarms. For low-confidence cells, visualize original/independent extraction/model predictions side by side, and require human confirmation before acceptance. Measure cost per resolved error, not just model accuracy.
5. Failure-mode study: corrupt one glyph, truncate a column, remove a subtotal, create wrong date headers, add side notes and change page rotation. Quantify detector recall on these controlled failures.

## 7. Limitations and responsible presentation

No downloaded or executed Docling/TableFormer/PaddleOCR-VL/MinerU weights are part of this deliverable. No claim that we trained an ML model. The implemented algorithm is **a stronger parameter-free geometry-and-rules model** for this family of pages. Every model-assisted backend in the above roadmap is only a researched option, not a validated result. Some checks assume Japanese balance-sheet headings and two numerical columns. No quality claims are made for unknown multi-table images, handwriting, or rotated charts.

Full AI chat-log disclosure must be included by the applicant as required by Arun's email; this note is not a substitute.
