# Human source-verification sign-off — v3

Aryan Jain, the user/project author, explicitly declares completed personal visual comparison of **all 197 annotated cell contents** against actual original PDF images: original Ur AI balance sheet 74, ELECOM page 9 56, Daiwabo page 10 67. He confirms all contents correct. This declaration covers 193 financial slots and 4 text cells; reference values, Japanese labels and printed symbols are unchanged.

Verification method: **direct visual comparison with original source PDF images**. Recording method: **bulk entry based on explicit user declaration**, because repetitive dropdown entry was skipped. No new per-cell clicks or inspection timestamps are asserted. `review/human_signoff/declaration_v3.json` preserves the statement and a repository recording time (not an inspection time). V3 decisions are `benchmark/human_gold/v3/accepted_decisions.json`; the original UI restores all 197 acceptances and exports their provenance.

The earlier export remains untouched (51 accepted / 146 unreviewed; SHA-256 `a930cc5a4d5f38454f86caf78855b0c454b7785dbdb217b2270d7c0b2f573ac9`). Earlier attestations, v1 ledger and v2 51-reviewed/146-bulk classification remain frozen. [Prior sign-off](history/USER_SIGNOFF_v2.md) records that earlier stage. This declaration updates current confidence, without rewriting earlier events.

**Verified:** all annotated cell contents, including signs, dash placeholders, negative zero and Daiwabo explanatory text. All 37 high-risk sign/placeholder cases are covered by the declaration.

**Still unreviewed:** hierarchy, header links, merged-cell spans, geometry, units, period/role assignments, table/row completeness and structural annotations. In particular, 12 Daiwabo lower-table numeric periods remain inferred/unprinted; 17 upper change intervals remain inferred. The old 98-label attestation is separate; no new per-label events or structural accuracy claims are made. OMRON remains unavailable and has no sign-off.

See [results](HUMAN_REVIEW_RESULTS.md) for exact denominators, [submission status](SUBMISSION_STATUS.md) for remaining work. All source pages remain development-exposed, not blind holdouts.
