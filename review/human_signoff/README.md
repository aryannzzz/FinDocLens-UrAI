# Human sign-off inputs and import policy

**Current: v3 completed personal visual review of all 197 cell contents, bulk recorded from explicit author declaration.** See the final section below. The v1/v2 discussion records earlier history and is superseded for current confidence.

`human_review_decisions.json` is the exact exported file supplied by Aryan Jain (found initially at repository root). SHA-256: `a930cc5a4d5f38454f86caf78855b0c454b7785dbdb217b2270d7c0b2f573ac9`. It retains 51 `accepted` and 146 `unreviewed` decisions. It has not been edited to manufacture additional clicks or timestamps.

`attestation_v1.json` is the unchanged earlier bulk-approval statement. **The later `clarification_v2.json` supersedes its interpretation as individual source review:** only the 51 exported acceptances were individually inspected; the other 146 were bulk-approved AI-drafted/AI-visually-cross-checked cells. The old 98-label attestation is preserved without inventing individually logged label events. Headers, periods, units, hierarchy, geometry and completeness remain unreviewed. Approving a value does not verify an inferred period.

Every derived cell retains its prior content, exported decision and acceptance basis. The full exported record is also preserved in each versioned reference's `decision_ledger`. Exported evidence URLs such as `assets/original_page.png` are relative to **`benchmark/review/`**, not to this archive directory. The source PDF path and hash, original page index, selected-PDF identity, and source bbox are preserved so images can be regenerated without models.

`evaluation_v1.json` pins the old 48 comparisons. `evaluation_v2.json` preserves those exact predictions/hashes and binds the corrected provenance. Its two selections are fin1 and post-fix; the latter uses p0fix2 except Docling matching-off Daiwabo uses p0fix3. v2 reports individual 51-cell accuracy, 146-cell bulk agreement, and full 197-cell approved-reference agreement separately. No inference is required. All sources are development-exposed, not blind holdouts.

The importer preserves unreadable, unresolved, missing-export and correction-needed states. Free-text correction notes are not automatically parsed into gold. A finalized correction must explicitly use `decision="corrected"` and a `correction` object containing exactly `raw`, `value`, and `status`; otherwise it remains unresolved. Bulk acceptance never overrides these unresolved states. The supplied export contains none of them, so no value corrections were made in v1.

Current references: `benchmark/human_gold/v2/`. Current scores: `results/human_v2/`. The exact individual list is `benchmark/human_gold/v2/individually_reviewed_cells.csv`; 31 remaining high-risk cases are in `remaining_sign_review_v2.csv`. v1 references, approval ledger and numeric comparisons remain frozen with deprecation notices. Both versions have separate SHA-256 locks. Original `benchmark/gold/`, source manifests, parser outputs and frozen baseline files remain unchanged.

See [`docs/HUMAN_REVIEW_RESULTS.md`](../../docs/HUMAN_REVIEW_RESULTS.md) for exact denominators, results and reproducibility commands. Later decisions or changes of scope require a new attestation/reference version; do not edit these archived inputs in place.

## Current status — completed personal review v3

The paragraphs above describe the preserved v1/v2 history. **`declaration_v3.json` now records Aryan Jain's explicit declaration that he personally inspected all 197 cell contents against the original PDF images.** Current references are `benchmark/human_gold/v3/`; scores are `results/human_v3/`; all decisions are accepted. The recording method is bulk entry from that declaration, not bulk approval without inspection and not fabricated dropdown events. No inspection times were supplied; only the repository declaration-recording time is recorded.

`evaluation_v3.json` reuses all 48 stored predictions/hashes. V3 keeps the original export and ledger, adds `accepted_decisions.json` and a declaration-bound acceptance record, and retains historical per-cell v2 classification. The earlier 31-case sign queue is historical; all its cell contents are covered by the new declaration. Structure, links/spans and inferred Daiwabo periods remain unreviewed. No reference value, parser output, historical result or frozen baseline was changed.
