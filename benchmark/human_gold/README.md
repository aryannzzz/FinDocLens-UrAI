# Human content reference versions — current v3

`CURRENT.json` selects **v3: 197 cell contents personally source-verified by Aryan Jain's explicit declaration**. Entry was bulk recorded from the declaration; this does not imply 197 UI clicks or known inspection times. V3 contains 193 financial-column slots and 4 explanatory text cells. All structure and inferred periods remain unreviewed. See [report](../../docs/HUMAN_REVIEW_RESULTS.md).

Historical v1 and v2 are frozen. V1 conflated approval with inspection; v2 correctly classified the then-known evidence as 51 individually reviewed / 146 bulk-approved AI-cross-checked cells. The new declaration records completed personal inspection of all 197 prospectively. It does not rewrite that history. Original export and decision ledger remain unchanged; v3 adds a separate acceptance record and retains each cell's historical v2 review metadata. The previous 98-label attestation is separate from new cell verification; no new label/structure certification is inferred.

V3 provides `manifest.json`, `cell_catalog.json`, `accepted_decisions.json`, three document snapshots and `SHA256.json`. Use `python -m benchmark.human_declaration --check benchmark/human_gold/v3` and `benchmark.declared_scoring`. Writers are create-only; tests regenerate reference and stored-prediction scores byte-for-byte. Original AI-drafted `benchmark/gold/`, parser outputs and `baseline_v2/` remain unchanged.

All evaluated source pages are development-exposed. Human verification does not make them blind holdouts or certify full table reconstruction. V1/v2 replay tools and scores remain available as historical records.
