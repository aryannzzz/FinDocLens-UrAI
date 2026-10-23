# Review provenance correction v2 — 23 October 2026

**51 cells were individually reviewed by Aryan Jain against source images. The other 146 were bulk user-approved AI-drafted annotations that had an AI visual cross-check. They are not 197 independently human-verified ground-truth cells.**

The earlier v1 wording conflated approval with individual review. v1 JSON and its original audit ledger remain frozen for replay, with deprecation notices. The original export, its per-cell decisions/timestamps, the earlier attestation, AI references, stored predictions and frozen baseline are unchanged. The correction is a separately versioned classification, not a fabricated review event.

Current manifest: [`benchmark/human_gold/v2/manifest.json`](../benchmark/human_gold/v2/manifest.json). Reviewer clarification: [`clarification_v2.json`](../review/human_signoff/clarification_v2.json). Exact CSV: [`individually_reviewed_cells.csv`](../benchmark/human_gold/v2/individually_reviewed_cells.csv). Full cell catalog: [`cell_catalog.json`](../benchmark/human_gold/v2/cell_catalog.json).

## Confidence classes and exact denominators

| Source | Individually reviewed cells | Bulk-approved AI-checked cells | Full user-approved comparison | Individually reviewed row contexts |
|---|---:|---:|---:|---:|
| original | 31 | 43 | 74 | 16 |
| elecom_p9 | 20 | 36 | 56 | 10 |
| daiwabo_p10 | 0 | 67 | 67 | 0 |
| **Total** | **51** | **146** | **197** | **26** |

The 51-cell accuracy denominator contains **51 financial cells, 0 explanatory text cells**. The 146-cell bulk agreement denominator contains **142 financial cells + 4 text cells**. The full agreement denominator is **193 financial cells + 4 text cells = 197**. Printed dash placeholders count as financial-column slots with null/not_reported semantics, never as zero.

**Daiwabo has 0 individually reviewed cells. Its individual accuracy is N/A (0/0, rate null), not 100%.** No Daiwabo reconstruction or complex-table accuracy claim is established by the 51-cell sample. Original and ELECOM are development-exposed too; all results here are in-sample source-page evidence, not blind holdouts.

The 51 inspections were one reviewer accepting existing AI-drafted cells, not a blind second transcription or a randomly selected test sample. All-backend 51/51 agreement should be interpreted with that selection and confirmation-bias limit.

The previous **98-label user attestation** is preserved separately. The export contains no standalone per-label review decisions, so v2 reports **0 individually documented label-review decisions** and does not publish 98/98 as independent human label accuracy. The 26 row contexts below identify where reviewed cells sit; they are not a new structural sign-off.

All **14 header annotations** (10 printed, 4 implicit/unprinted), **193 numeric period associations**, hierarchy, units, geometry and completeness remain structurally unreviewed. In particular, the **12 Daiwabo lower-table numeric periods** are inferred from context; their values are bulk-approved, and their period assignments are not human-observed headers. The 17 upper-table change intervals are inferred semantic constructions too. None enters human period accuracy.

The archived [AI visual audit](../review/second_ai_visual_audit/README.md) is explicitly AI-only and not blinded; its model/version was not recorded. Its field named `source_sha256` hashes the selected one-page PDF, and v2 checks it against the benchmark input hash. It cannot increase human review counts.

## Metrics: individual accuracy versus approved-reference agreement

Only stored predictions are read. Matching remains one-to-one by table geometry, reviewed/approved label context and physical column; values are not used to find rows. Geometry and structure remain AI-derived alignment context. Raw matching removes whitespace only; typed content means value + status, not correct period/role/header semantics.

The fin1 and post-fix selections have identical content scores in all three confidence strata. Counts below apply per backend per selection; repeated backend comparisons do not create additional reviewed source cells.

| Backend | Individual raw accuracy | Individual value/status accuracy | Bulk raw agreement | Full 197-cell raw agreement | Full financial raw agreement |
|---|---:|---:|---:|---:|---:|
| v2 | 51/51 | 51/51 | 81/146 | 132/197 | 132/193 |
| native_v2 | 51/51 | 51/51 | 81/146 | 132/197 | 132/193 |
| native_grid | 51/51 | 51/51 | 142/146 | 193/197 | 193/193 |
| docling_cmtrue | 51/51 | 51/51 | 79/146 | 130/197 | 130/193 |
| docling_cmfalse | 51/51 | 51/51 | 79/146 | 130/197 | 130/193 |
| docling_rapidocr | 51/51 | 51/51 | 79/146 | 130/197 | 130/193 |
| docling_regions | 51/51 | 51/51 | 130/146 | 181/197 | 181/193 |
| auto | 51/51 | 51/51 | 142/146 | 193/197 | 193/193 |

**All eight backends score 51/51 on the individually reviewed sample.** This sample is restricted to two comparatively simple native pages and is not evidence that all eight handle Daiwabo correctly. The existing 197-cell numbers are retained as **agreement with user-approved references**, not fully human-verified accuracy. Four native explanation-string disagreements involve arrow placement; they remain disagreements with the approved draft, not errors established by individual human inspection.

Machine-readable scores: [`results/human_v2/summary.json`](../results/human_v2/summary.json). Every one of 48 stored page/backend predictions has three separately named scope reports. Post-fix selection remains p0fix2, except Docling matching-off Daiwabo uses the explicitly pinned p0fix3 prediction. No inference, source value edit, parser-output edit, or latency remeasurement occurred. Old results/human_v1 numeric comparisons remain unchanged.

## Exact individually reviewed rows and cells

The following table lists every selected cell, grouped into 26 row contexts. Column indexes are zero-based physical columns. A cell in the same row is not accepted into the individual subset merely because its neighbor was checked; **original assets_r016 column 0 remains bulk-approved while column 1 is individually reviewed**. No Daiwabo row appears.

| Source | Table / row ID | Source row label | Column 0 individually reviewed raw | Column 1 individually reviewed raw |
|---|---|---|---|---|
| original | assets / assets_r003 | 現金及び預金 | `2,002,429` | `608,281` |
| original | assets / assets_r004 | 受取手形 | `20,659` | `26,333` |
| original | assets / assets_r005 | 売掛金 | `2,019,476` | `884,339` |
| original | assets / assets_r006 | 電子記録債権 | `564,667` | `370,468` |
| original | assets / assets_r007 | 商品及び製品 | `589,488` | `1,019,663` |
| original | assets / assets_r008 | 仕掛品 | `186,748` | `55,344` |
| original | assets / assets_r009 | 原材料及び貯蔵品 | `370,403` | `136,082` |
| original | assets / assets_r010 | 短期貸付金 | `7,530` | `30,000` |
| original | assets / assets_r011 | その他 | `105,260` | `246,895` |
| original | assets / assets_r012 | 貸倒引当金 | `△2,979` | `△0` |
| original | assets / assets_r013 | 流動資産合計 | `5,863,684` | `3,377,407` |
| original | assets / assets_r016 | 建物及び構築物 | (not individually reviewed) | `1,880,082` |
| original | assets / assets_r017 | 減価償却累計額 | `△1,923,585` | `△1,640,253` |
| original | assets / assets_r018 | 建物及び構築物（純額） | `197,775` | `239,828` |
| original | assets / assets_r019 | 機械装置及び運搬具 | `4,024,922` | `2,250,799` |
| original | assets / assets_r020 | 減価償却累計額 | `△3,634,165` | `△1,914,091` |
| elecom_p9 | assets / assets_r003 | 現金及び預金 | `43,718` | `58,497` |
| elecom_p9 | assets / assets_r004 | 受取手形及び売掛金 | `21,033` | `27,294` |
| elecom_p9 | assets / assets_r005 | 有価証券 | `11,199` | `12,387` |
| elecom_p9 | assets / assets_r006 | 商品及び製品 | `11,937` | `15,339` |
| elecom_p9 | assets / assets_r007 | 仕掛品 | `498` | `662` |
| elecom_p9 | assets / assets_r008 | 原材料及び貯蔵品 | `1,603` | `2,190` |
| elecom_p9 | assets / assets_r009 | 返品資産 | `380` | `378` |
| elecom_p9 | assets / assets_r010 | 為替予約 | `2,292` | `2,782` |
| elecom_p9 | assets / assets_r011 | その他 | `1,558` | `1,769` |
| elecom_p9 | assets / assets_r012 | 流動資産合計 | `94,222` | `121,302` |

The CSV additionally preserves each exact key (`document:row:column`), review timestamp, raw string, typed value/status, and source page index. Source page indexes are zero-based (original 0, ELECOM 8); the export hash is `a930cc5a4d5f38454f86caf78855b0c454b7785dbdb217b2270d7c0b2f573ac9`.

## Reproduce without inference

```bash
.venv/bin/python -m benchmark.review_provenance --check benchmark/human_gold/v2
.venv/bin/python -m benchmark.review_scoring --reference benchmark/human_gold/v2 --config review/human_signoff/evaluation_v2.json --out results/human_v2 --verify
.venv/bin/python -m unittest tests.test_review_provenance -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m benchmark.validate
```

To rebuild in fresh directories, run `benchmark.review_provenance --clarification review/human_signoff/clarification_v2.json --out /tmp/new-review/v2`, then `benchmark.review_scoring --reference /tmp/new-review/v2 --config review/human_signoff/evaluation_v2.json --out /tmp/new-review-scores`. Versions/score outputs are create-only. Tests compare regenerated references and scores byte-for-byte, check the original ledger/export hashes, enforce the 51/146 split, and preserve missing-cell denominators. Original AI reference hashes and the frozen baseline remain unchanged.

Verification completed: **10 focused tests and 159 full tests passed**, including the frozen baseline subprocess tests. Provenance/scoring replay and original reference hash checks passed. Commands, package/code versions and pure-CPU verification metadata are retained under `runs/review_provenance/source_pages/v2/`; no inference was invoked.

## Remaining submission work

See [`SUBMISSION_STATUS.md`](SUBMISSION_STATUS.md) for requirement-by-requirement evidence. The main validation gaps are **0 individually checked Daiwabo values**, **31 of 37 high-risk sign/dash/plus/negative-zero cells still only bulk-approved**, and unreviewed structure/inferred periods. The entire 146-cell bulk set is not required to be individually reviewed just to report approval agreement, but it cannot be relabeled human-verified without actual source inspection.

The complete AI chat transcripts are separately required by the project instructions; `AI_COLLABORATION.md` and reports are not substitutes. No complete transcript exports were found in the repository. The original application email is not included, so deadline, upload format and any additional email-specific requirements must be confirmed with that email. A screencast script exists; an actual recording is not evidenced and is optional under the local integration task unless the email says otherwise.
