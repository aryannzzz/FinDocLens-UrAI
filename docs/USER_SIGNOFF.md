# Human ground-truth sign-off

**Corrected provenance, 23 October 2026:** Aryan Jain individually inspected **51 cells** against source images (31 original, 20 ELECOM, 0 Daiwabo). The export is unchanged at `review/human_signoff/human_review_decisions.json` (timestamp `2026-10-23T06:51:52.884Z`, SHA-256 `a930cc5a4d5f38454f86caf78855b0c454b7785dbdb217b2270d7c0b2f573ac9`). It still has 51 accepted and 146 unreviewed exported states. The remaining **146** were later **bulk user-approved AI drafts**, not individually inspected cells. This clarification is recorded in `clarification_v2.json`; earlier attestations/ledger remain untouched.

Current v2 has **51 individually source-reviewed financial cells**, **142 bulk-approved financial cells + 4 bulk-approved text cells**, and **unreviewed structure/inferred periods**. Full 197-cell numbers are agreement with user-approved references, not fully human-verified ground truth. The prior 98-label attestation is preserved, but no individual label-review records are exported and no independent 98/98 label-accuracy claim is made. v1 confidence metadata is superseded, while its ledger/JSON remains frozen. Original AI reference counts remain zero. See [HUMAN_REVIEW_RESULTS.md](HUMAN_REVIEW_RESULTS.md) for exact cells/metrics and [SUBMISSION_STATUS.md](SUBMISSION_STATUS.md) for remaining requirements.

Further sign-off template: check an item only after the corresponding source inspection. Cell approval does not automatically verify its parent/account context or headers. The combined boxes below remain unticked.

Original Ur AI supplied page: [ ] All labels/periods/units   [ ] all 74 monetary tokens
ELECOM page 9: [ ] selected table bbox   [ ] 20+ cell tokens + rows + headers
OMRON page 13: [ ] table count/group headers  [ ] 20+ amount/percentage/change cells
Daiwabo page 10: [ ] 3 distinct regions  [ ] 20+ tokens across side-by-side tables

Report each incorrect draft gold as a correction with source crop. Do not silently modify gold after viewing model errors. If not fully inspected, label scope and sample size explicitly (e.g. `human_checked_cells=20/44`).
