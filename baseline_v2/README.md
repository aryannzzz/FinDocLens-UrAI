# Ur AI R&D Take-Home — Adaptive, Auditable Japanese Balance-Sheet Parser

**Status:** implemented and tested native-PDF baseline (v2). **No VLM inference or OCR has been executed.** This is a research prototype, **not** a generally validated PDF understanding model.

## Deliverable contents

- `parser_v2.py`: complete runnable layout-adaptive parser, PDF-coordinate evidence, semantic grouping, validation, output export, annotated visual evidence.
- `source.pdf`: exact sample balance-sheet PDF shared in the take-home.
- `output/table.json`, `output/table.csv`: results, hierarchy, units, periods, raw glyphs, numerical values, and bounding boxes.
- `output/evidence_page_1.png`: highlighted geometry: blue boxes for labels, green for values.
- `verify_evidence.py`: second native-PDF extractor cross-check using pdfplumber.
- `evaluate.py` + `tests/gold_rows.tsv`: explicit manually transcribed reference and reproducible evaluation.
- `benchmark.py`: controlled document transformations, an erased cell and a missing minus sign.
- `compare_baseline.py` + `tests/baseline_parser.py`: frozen original v1 comparator.
- `make_review_pack.py`: selectively renders suspect rows/pages and writes a VLM/human review prompt; **does not call a model**.
- `tests/test_v2.py`: 25 deterministic automated checks.
- `RESEARCH_REPORT.md`: detailed research, measured results, tradeoffs and roadmap.
- `AI_COLLABORATION.md`: disclosure; see note about full required chat history.

## Run

Python >=3.10, install dependencies (no model weights required):

```bash
python -m pip install -r requirements.txt
python parser_v2.py source.pdf --out output --visualize
python evaluate.py source.pdf --gold tests/gold_rows.tsv --out output/evaluation.json
python verify_evidence.py source.pdf --out output/cross_engine.json
python benchmark.py
python compare_baseline.py
python -m unittest discover -s tests -p 'test_*.py' -v
```

A runnable demo of selective review preparation:

```bash
python make_review_pack.py tests/generated/missing_value.pdf --out output/review_example
```

For a different PDF: `python parser_v2.py path/to/document.pdf --out other_output --visualize` (it may flag unsupported layouts; do not treat an empty output as a successful parse).

## Why this approach

The PDF contains **native Japanese text**, two repeated right-aligned monetary columns, no grid lines between most row/cell boundaries, indentation hierarchy, fiscal-date headings, `△` negative markers, `△0` and `－`. Native text with spatial coordinates can preserve the exact displayed glyphs without incurring OCR recognition error.

V1 hard-coded positions (`x=290/422`, `y=145..800`), causing silent loss after basic repositioning. V2 infers right-aligned columns by repeated right-edge clustering, computes table region from row-pitch estimates, groups adjacent sign and number spans, reconstructs section paths, attaches gross/depreciation/net families, and emits exact source bounding boxes. It **abstains** on raster-only PDF files and flags absent cells.

## Correctness definition and measurements

1. **Content:** Japanese labels and monetary strings, including negative signs, negative zero, and dash placeholders.
2. **Structure:** complete rows, column order, fiscal dates, unit, hierarchical paths and relations.
3. **Provenance:** source PDF page/coordinate bounding box for each recorded label and cell.
4. **Auditability:** accounting checks report but **never rewrite** discrepant numbers; missing/ambiguous cases enter review.

On the single supplied page: **43/43 rows and their paths; 74/74 raw monetary tokens; 74/74 cells agreed with pdfplumber's embedded-PDF text extraction.** The reference was manually transcribed for this assignment by the AI assistant, not verified by an independent blind annotator. **These are in-sample measurements**, not unseen-template generalization estimates.

Controlled tests: scale 79%, scale 123%, translate horizontally, insert an unrelated numeric footer, and duplicate into two pages. V2 recovered **37/37 monetary rows** on all five one-page variants and 74/74 on the duplicate's two pages. The same frozen V1 extracted **0 rows after scaling to 123%, 0 after the translation, and 10 after the footer transformation** (the specific transformation combines scale plus footer). The missing-cell case retains 37 records, preserves its second value and reports one missing cell. The deliberately removed negative sign triggers a financial-reconciliation warning. Raster-only PDF produces explicit `needs_visual_fallback` rather than invented table data. **All 25 tests pass.** These transformed copies come from one source and should never be called a multi-template benchmark.

## Caveats

- **No scanned-page extraction in v2:** a Japanese-capable OCR/VLM backend is recommended next; downloading external pretrained weights was not available in the execution environment.
- **Column structure:** repeated right-aligned numeric columns only, currently two dates; heterogeneous multi-column tables, merged cells, multiple tables and rotated pages need separate table detection/layout recognition.
- **Semantic rules:** Japanese balance-sheet sections and gross/depreciation/net conventions. Other genres need different semantic parsers.
- **Evaluation:** manual reference should receive separate human review and be expanded to truly independent companies/layouts. Cross-engine agreement is not independent visual truth because both engines read the same embedded PDF text layer.
- **Accounting reconciliation:** the original reported values have small legitimate differences, possibly from individual-value rounding/truncation. Reporting a discrepancy does not imply the parser is wrong, and a balanced total does not prove exact transcription.
- **Safety of review:** VLM output is *never* auto-accepted. Compare raw glyphs/coordinates and require human verification for ambiguous financial cells.

## AI transparency

Developed with ChatGPT GPT-6 on October 22, 2026 in response to the applicant's request. Code, manual reference, engineering hypotheses, benchmark scenarios, tests, and narrative were AI-assisted. This package is NOT a substitute for the **complete AI chat log**, which Ur AI specifically requires. Export the full conversation and include it alongside the submission. No claims of training a new VLM, pretrained VLM execution or independent test sets are made.
