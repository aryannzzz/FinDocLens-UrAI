# Human ground-truth sign-off

**Imported review, 23 October 2026:** Aryan Jain's source-image review is archived at `review/human_signoff/human_review_decisions.json` (export timestamp `2026-10-23T06:51:52.884Z`, SHA-256 `a930cc5a4d5f38454f86caf78855b0c454b7785dbdb217b2270d7c0b2f573ac9`). The export has 51 accepted cells and 146 unreviewed states. The reviewer's later explicit statement accepts those unmarked values too, and all 98 row labels; see `attestation_v1.json`. The export itself was not edited.

The separate `benchmark/human_gold/v1/` records **197 reviewed content cells = 193 financial + 4 text**, plus **98 reviewed row labels**. It remains partially verified by field: no header/period/unit/hierarchy/box/completeness sign-off is inferred. The combined checkboxes below are deliberately not ticked because they ask for broader certification. Original AI reference counts remain zero; new counts apply only to the separately versioned dataset. No unreadable, pending correction or unresolved decisions were supplied; the importer preserves such decisions if present. Results and commands: [HUMAN_REVIEW_RESULTS.md](HUMAN_REVIEW_RESULTS.md).

I inspected the rendered original Japanese financial statement (not merely a model-generated table), and verified the following independent cells and their parent/account context:

Original Ur AI supplied page: [ ] All labels/periods/units   [ ] all 74 monetary tokens
ELECOM page 9: [ ] selected table bbox   [ ] 20+ cell tokens + rows + headers
OMRON page 13: [ ] table count/group headers  [ ] 20+ amount/percentage/change cells
Daiwabo page 10: [ ] 3 distinct regions  [ ] 20+ tokens across side-by-side tables

Report each incorrect draft gold as a correction with source crop. Do not silently modify gold after viewing model errors. If not fully inspected, label scope and sample size explicitly (e.g. `human_checked_cells=20/44`).
