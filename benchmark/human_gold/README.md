# Field-scoped human reference versions

Each version is separate from immutable AI-drafted `benchmark/gold/`. A version contains per-document accepted content, the complete decision ledger, reviewer provenance, source/reference hashes, explicit issuer/source classification, and its own manifest/SHA-256 lock.

`partially_human_verified` means the named fields are reviewed; it does not certify the complete financial table schema. v1 accepts `raw`, `value`, `status` for 197 cells and `label`/`raw_label` for 98 row occurrences. Header/period/role/link, unit, hierarchy, source-box and completeness assertions remain inherited AI context. Scope flags deliberately remain false, so these documents cannot accidentally pass as complete gold in the normal full-table evaluator.

Use `python -m benchmark.human_reference --check benchmark/human_gold/v1` and the separate `benchmark.human_evaluate` masked evaluator. Never score copied inferred periods as human-observed headers. A new import needs a new output/version; no existing version is overwritten. Review/export fields cannot silently change source identity or monetary glyphs, and pending decisions stay in the ledger rather than entering score denominators.

The original source pages and every stored prediction remain development-exposed. Human verification changes reference confidence, not split exposure. Full details: [`docs/HUMAN_REVIEW_RESULTS.md`](../../docs/HUMAN_REVIEW_RESULTS.md).
