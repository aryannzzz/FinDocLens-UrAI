# Ur AI / FinDocLens — second-pass source-image reference audit

**Audit scope:** supplied corrected Japanese balance sheet, ELECOM page 9, and Daiwabo Holdings slide/page 10. **Method:** independent *second AI visual pass* on the rendered source PDFs, plus manual (model-authored) transcription of the visible rows and values into `visual_transcription_check.py`. No OCR model was used as the arbiter. After transcription, the independently entered values were compared programmatically against the provided draft gold JSON. The gold references had already been seen in the conversation, so the check is **not blinded**; it is also **not a human annotation/sign-off**. **Do not set `human_checked_cells` above zero on this evidence alone.** All current gold files were left unchanged.

## Source identity and extent

Each input PDF's SHA-256 matches the `input_sha256` recorded in its reference. This audit covers the selected page from each document; it does not verify completeness of the entire company filing. The page display was inspected, not merely the embedded PDF text layer.

| Source | Tables / table-like regions | Rows visually compared | Cells visually compared | Exact visible-content disagreements with AI draft | Source units |
|---|---:|---:|---:|---:|---|
| Original Ur AI page | 1 | 43 (37 monetary + 6 sections) | 74 | 0 | 千円 (thousands of yen) |
| ELECOM page | 1 | 34 (28 monetary + 6 sections) | 56 | 0 | 百万円 (millions of yen) |
| Daiwabo page | 3 (2 upper tables + 1 lower explanatory grid) | 21 | 67 (63 numerical + 4 explanations) | 0 | 百万円 (millions of yen), printed once at the upper-left |
| **TOTAL** | **5** | **98** | **197** | **0** | |

**What a 197/197 match means:** A second visually composed transcription matched the AI draft **in literal cell content and row sequence**. It does **not** establish 197 independently human-verified cells, document-level generalization, table-schema correctness or an unbiased benchmark. The 37 high-risk sign / plus / dash / negative-zero cells were individually compared to the source image (12 original, 2 ELECOM, 23 Daiwabo). Source-row contact sheets accompany this report.

## Findings that affect the reference semantics

### B1 + B9 — Daiwabo bottom block has **no printed column headers**

The two upper tables print `2025/3`, `2025/12` and `増減`. The bottom four-row grid prints values and explanatory prose but **does not print those three headers again**. The draft gold attaches date/change roles and periods to c0/c1/c2 anyway. Those are reasonable **inferences from context**, not source-observed header cells. Similarly, day `31` is a normalized interpretation of the printed `2025/3` and `2025/12`, not literally printed in the headings.

**Recommendation:** keep a separate inferred semantic mapping and evaluate explicit table-header reconstruction separately. For visible-text/header accuracy, the lower grid has **zero printed leaf headers**. Do not penalize native-grid's null periods on those twelve lower-grid numeric cells as errors in printed-period extraction. If you want to score contextual inference, create a distinct `inferred_period` metric, not an exact visible-header metric.

### B2 — arrows are between the earlier and later values, **not prefixes of explanation sentences**

The bottom grid has a printed `→` **between the 2025/3 and 2025/12 amounts in each of four rows**. The drafted explanation strings correctly omit that character. The arrow is a source-visible separate transition/separator. Preserve the arrow as layout/row metadata (`transition_symbol="→"`), or as a separate column if the task requires lossless graphical/text content. Do **not** prepend it to the explanation text or to the second-period numeric value. The current 4 explanation-text values match the actual displayed prose.

### B3 — three table-like areas are visually defensible

Two upper side-by-side tables are clearly distinct. Below their separator rule is a four-row, headerless explanatory grid with shaded label cells and aligned amounts. Treating it as a third table-like region is defensible; calling it an explanatory subtable is more precise than claiming it has four explicit headers. Its delimiters and row boxes differ from the main tables.

### B4 — seven Daiwabo hierarchy edges are plausible **visual inferences**

Indented child rows align with the proposed groups: 3 under `流動資産`, 2 under `流動負債`, 1 under `固定負債`, and 1 under `純資産合計`. These seven edges are contextually consistent with the image. But there are no explicit parent pointers in the source. Mark `inferred_from_indent_and_financial_semantics` rather than a printed fact. The existing 0/7 hierarchy score should be explained as a structural-inference failure under this chosen convention, not a literal transcription error.

### B5 — difference semantics supported, but inferred

`増減` is printed and arithmetic supports **current minus previous**. Of the 17 upper-table rows, 12 changes match exactly and 5 differ by one million yen. That is consistent with comparing individually rounded amounts. Do not replace the source's changes with recalculated differences. The formula `2025-12-31_vs_2025-03-31` is an inferred normalization, not verbatim PDF content.

### B6 — unit inheritance

`（百万円）` appears once in the upper-left of the page; this unit reasonably governs the other table and explanatory grid as page-level financial context. Keep `million_JPY` but distinguish `printed_near_first_table` from `inherited_context` for the other two. Do not claim the unit label is printed in all three regions.

### B7 — ELECOM disputed child hierarchy

`その他（純額）` is visually indented to the same depth as the other `有形固定資産` members, including `建設仮勘定`; it should be a **sibling** of `建設仮勘定`, under `有形固定資産`. The draft reference has this correct. The old v2 attachment elsewhere is a parser defect.

### B8 — original's three particularly fragile symbols

The source visibly prints `－` for prior-year `建設仮勘定` and prior-year `長期貸付金`; these mean an unreported/not-applicable cell, **not numeric 0**. It also visibly prints `△0` for current-year `貸倒引当金`, which must retain raw negative-zero typography. All nine other original triangle-prefixed depreciation/allowance tokens are also source-matched. ELECOM's two `△4` amounts are source-matched.

## Important qualification

This second AI visual check is valuable error-reduction evidence, but the application's reference status must **remain `ai_draft`** until a person performs and records the independent sign-off. No gold JSON, tests, existing result runs, or manifests were modified here. OMRON was absent from the supplied package and was not reviewed. This review is also not a new holdout because both model development and gold inspection involved these documents.

## Recommended integration

1. Copy the audit evidence and findings into your project under a new path such as `review/second_ai_visual_audit/`, without overwriting `benchmark/gold/`.
2. Use `PROPOSED_ANNOTATION_DECISIONS.json` as a review/discussion checklist. Do not make automatic gold changes based solely on the model reviewer.
3. Have a human inspect the source-row evidence sheets or the existing `benchmark/review/index.html`; the 37 high-risk cells can be signed off first.
4. For a formal evaluation revision, version any annotation changes (including inferred vs observed periods), preserve original hashes and rerun the evaluator under a new run ID. Separate pre-review AI-draft metrics from post-review metrics.

## Artifacts

- `ai_visual_check_per_cell.json`: source SHA, row IDs, exact raw values, bounding boxes, and AI-review status for all 197 cells.
- `original_sign_evidence.png`, `elecom_p9_sign_evidence.png`, `daiwabo_p10_sign_evidence.png`: source pixel crops, grouped by row.
- `visual_transcription_check.py`: independent manual-by-vision transcription and reproducible comparison code. It expects the three gold JSON files under `benchmark/gold/` in the containing project.
- `PROPOSED_ANNOTATION_DECISIONS.json`: recommendations for human adjudication, not changes to frozen gold.
