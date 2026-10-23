# Human visual verification v3

**Aryan Jain, the user/project author, explicitly declares completed personal visual comparison of all 197 annotated cell contents against the original PDF images. All 197 decisions are accepted.**

Verification method: direct visual comparison with original source PDF images. Recording method: **bulk entry based on explicit user declaration**, not 197 dropdown clicks. No new per-cell click events or inspection timestamps are asserted. The declaration has a repository recording time; the actual inspection times were not supplied.

This is a new completed-review declaration. The earlier export (51 accepted / 146 unreviewed), v1 approval ledger, v2 clarification (51 personally reviewed / 146 bulk-approved at that stage), AI drafts, predictions and frozen baseline are unchanged. Their historical statements remain valid for that stage. See the [archived v2 report](history/HUMAN_REVIEW_RESULTS_v2.md).

Current [manifest](../benchmark/human_gold/v3/manifest.json), [reviewer declaration](../review/human_signoff/declaration_v3.json), [all accepted decisions](../benchmark/human_gold/v3/accepted_decisions.json), and [exact cell catalog](../benchmark/human_gold/v3/cell_catalog.json). The catalog identifies every document, table, row label/ID, column, raw/value/status and source identity.

## Exact content denominator

| Source | Human-verified contents | Financial slots | Explanatory text | Row contexts with cells | Source PDF page |
|---|---:|---:|---:|---:|---:|
| daiwabo_p10 | 67 | 63 | 4 | 21 | 10 |
| elecom_p9 | 56 | 56 | 0 | 28 | 9 |
| original | 74 | 74 | 0 | 37 | 1 |

**197 = 193 financial-column slots + 4 explanatory text cells.** Dash placeholders are included with null/not_reported semantics; `－` is not zero, and `△0` remains negative_zero. Repeated backend/run comparisons do not increase the 197-cell source denominator.

## Stored-prediction content accuracy

Both fin1 and post-fix selections have the same scores below. These are source-page, development-exposed results, **not blind holdouts**. Human review improves reference confidence; it does not change exposure or establish independent blind transcription. One project-author reviewer verified existing AI drafts, with the associated confirmation-bias limitation.

| Backend | Raw content | Value/status | Financial raw | Text raw |
|---|---:|---:|---:|---:|
| v2 | 132/197 (67.01%) | 132/197 (67.01%) | 132/193 (68.39%) | 0/4 (0.00%) |
| native_v2 | 132/197 (67.01%) | 132/197 (67.01%) | 132/193 (68.39%) | 0/4 (0.00%) |
| native_grid | 193/197 (97.97%) | 193/197 (97.97%) | 193/193 (100.00%) | 0/4 (0.00%) |
| docling_cmtrue | 130/197 (65.99%) | 130/197 (65.99%) | 130/193 (67.36%) | 0/4 (0.00%) |
| docling_cmfalse | 130/197 (65.99%) | 130/197 (65.99%) | 130/193 (67.36%) | 0/4 (0.00%) |
| docling_rapidocr | 130/197 (65.99%) | 130/197 (65.99%) | 130/193 (67.36%) | 0/4 (0.00%) |
| docling_regions | 181/197 (91.88%) | 181/197 (91.88%) | 181/193 (93.78%) | 0/4 (0.00%) |
| auto | 193/197 (97.97%) | 193/197 (97.97%) | 193/193 (100.00%) | 0/4 (0.00%) |

All backends match original 74/74 and ELECOM 56/56 cell contents. On Daiwabo, native_grid/auto match **63/63 financial cells but 63/67 total contents**; frozen v2/native_v2 match 2/63 financial cells (2/67 total), Docling page paths 0/63 (0/67 total), and docling_regions 51/63 (51/67 total). Four native explanation-string errors involve arrow placement; reference strings and predictions remain unchanged.

Matching is one-to-one by table geometry, normalized row label and physical column, without using values to locate rows. Missing cells remain in the denominator, including abstentions. Raw comparison removes whitespace only. Value/status does not verify roles, periods or header semantics. AI-derived label/geometry context supports alignment but is not newly certified structure. Scores are cell-content accuracy, not full table reconstruction accuracy.

[Machine-readable summary](../results/human_v3/summary.json) and 48 page/backend reports pin the same prediction paths and SHA-256 hashes as v2. Post-fix uses p0fix2, except matching-off Docling Daiwabo uses the pinned p0fix3. No inference or latency remeasurement occurred. The historical [v2 full 197-cell approved-reference agreement](../results/human_v2/summary.json) is preserved; v3 changes confidence provenance, not its numerical counts.

## Structural annotations remain unreviewed

The declaration verifies cell contents only. It does **not** certify the 14 header annotations (10 printed, 4 implicit), 193 numeric period associations, 82 hierarchy edges, 5 table-like regions, label hierarchy, header links, merged-cell spans, units, geometry, roles or completeness. Prior 98-label attestation remains separate; no additional individual label-review events or structural scores are invented.

**Daiwabo lower-table 12 numeric period assignments remain inferred/unprinted**, separately from verified values and printed headers. The 17 upper-table change intervals are also inferred semantics. Even the 164 printed-header associations remain unreviewed links. Their diagnostic scores are explicitly unverified context and are excluded from human structural accuracy.

## Review UI and reproducibility

The original `benchmark/review/index.html` embeds the v3 accepted decisions while retaining the original AI annotation tables unchanged. A declaration-specific browser draft namespace prevents earlier unreviewed browser states overriding the new declaration; the old namespace is preserved. Later edits persist in the new namespace and export as decisions without rewriting snapshots.

```bash
.venv/bin/python -m benchmark.human_declaration --check benchmark/human_gold/v3
.venv/bin/python -m benchmark.declared_scoring --reference benchmark/human_gold/v3 --config review/human_signoff/evaluation_v3.json --out results/human_v3 --verify
.venv/bin/python scripts/report_human_declaration.py --check
.venv/bin/python -m benchmark.review --check
.venv/bin/python -m unittest tests.test_human_declaration tests.test_review_provenance tests.test_human_reference tests.test_review_site -v
.venv/bin/python -m benchmark.review --serve --port 8765
```

Open **http://127.0.0.1:8765/benchmark/review/index.html**. All 197 decisions restore as accepted by default; the header explains their declaration basis and structural limits. JSON export includes the declaration and export creation time, without fabricating per-cell inspection times. Source assets are reused from cached PDFs; no network/model download is needed.

Create-only regeneration into a fresh destination uses `benchmark.human_declaration --declaration review/human_signoff/declaration_v3.json --out /tmp/REFERENCE/v3`, then `benchmark.declared_scoring --reference /tmp/REFERENCE/v3 --config review/human_signoff/evaluation_v3.json --out /tmp/SCORES`. Existing versions are never overwritten. See [submission status](SUBMISSION_STATUS.md) for remaining research/packaging requirements.
