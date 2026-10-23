# Review provenance versions — current v2

Each version is separate from immutable AI-drafted `benchmark/gold/`. [`CURRENT.json`](CURRENT.json) selects v2: **51 individually human-reviewed cells**, **146 bulk user-approved AI-cross-checked cells**, and unreviewed structure/inferred periods. Only the 51-cell subset supports individual human-reviewed accuracy. The full 197-cell comparison is approved-reference agreement.

The export and v1 decision ledger remain unchanged. v2 layers the reviewer's clarification over them and lists the exact 51 cell keys/values in `v2/individually_reviewed_cells.csv`. Its `human_checked_cells` totals 51, not 197. The earlier 98-label user attestation remains recorded; it is not treated as 98 individually exported label-review events. Header/period/role/link, unit, hierarchy, source-box and completeness assertions remain unreviewed context. Inferred Daiwabo lower-table periods are never promoted by approving their values.

Use `python -m benchmark.review_provenance --check benchmark/human_gold/v2` and `benchmark.review_scoring`. Both have create-only writers and hash/replay checks. v1 JSON retains its historical, superseded confidence fields solely for audit replay; its old `human_checked_cells=197` must not be cited as 197 individually reviewed cells. The legacy commands print a deprecation warning. Original v1 numerical comparisons remain available, now explicitly labeled user-approved agreement.

The original source pages and every stored prediction remain development-exposed. Human verification changes reference confidence, not split exposure. Full details: [`docs/HUMAN_REVIEW_RESULTS.md`](../../docs/HUMAN_REVIEW_RESULTS.md).
