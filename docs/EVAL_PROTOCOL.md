# Minimum evaluation contract

## Common representation
`document_id`, `source_sha256`, `backend`, `model_revision`, `page`, `page_bbox`, `tables[]`.
For each table: `table_id`, `bbox`, `reading_order`, `headers[]` (text, period, role, bbox, colspan,rowspan), `rows[]` (row_index,label,raw_label,parent_path,bbox,type,cells[]), `issues[]`.
For each cell: `column_index`, `header_id`, `period`, `role` (amount, composition_pct, change_amount, other), `raw`, `value` (typed or null), `status` (observed, negative_zero, not_reported, absent_text_cell, unreadable, uncertain), `bbox`, `backend`, `evidence_kind` (native_pdf, ocr, vlm, human).

Some engines cannot supply bbox or headers: record null plus a capability/status field. Preserve original model/native result as well; normalization must not quietly invent missing fields. A table grid is independent of financial semantic enrichment.

## Metrics and denominators
- Detection: tables found/true tables (P/R), plus extra table count. Separate normal doc-table vs chart/slide.
- Row extraction: one-to-one matching within table using exact/normalized Japanese label and reading order, with miss/spurious row counts. Never duplicate a gold row to improve scores.
- Raw cell exact: exact source symbols and digits after a declared whitespace policy, matched to gold by table+row+column role. Report `correct/total_gold` and `correct/matched_pred`; do not evaluate only recognized cells.
- Parsed cell semantics: correctly sign/special null/negative-zero/percentage typed status.
- Header accuracy: period+amount-vs-percentage-vs-delta role exact, separately from value accuracy.
- Hierarchy edge F1: directed parent-child relations on evaluated labels, distinguishing identical `その他` under different parents.
- OCR/CER and table TEDS/GriTS optional only when ground truth and appropriate libraries exist; benchmarks aren't interchangeable.
- Reliability: abstention rate, correct abstention on injected missing values, silent-omission rate, false assurance rate. Report warnings separately.
- Performance: include PDF rendering, backend selection, preprocessing, model loading (cold), inference (warm median over ≥3 if practical), and normalization. GPU allocated/peak using a compatible method and actual hardware. Costs only if prices actually known.

## Split leakage
Original PDF and its scaled/cropped/scan/repositioned variants share a source and MUST be in the same split. Out-of-template means a different issuer/template, not a different rendering of an existing example. A human must verify source images for gold; a model-transcribed reference with no human verification remains AI-drafted reference.

## Financial validation
Balance-sheet totals can legitimately differ by a few displayed units due to rounding/truncation. A check is a diagnostic and must not overwrite a cell or automatically label an extraction wrong. Absence of arithmetic violations does not establish correctness.

## Experiment manifest fields
`run_id`, UTC timestamp, git commit, source URL, source SHA, page index, backend name/version/model_revision, package versions, CPU/GPU/RAM/VRAM, cold or warm, time_ms, peak_memory_mb (if actually measured), status, error text, prediction path, metrics path, and human-audit status.
