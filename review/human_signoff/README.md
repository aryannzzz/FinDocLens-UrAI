# Human sign-off inputs and import policy

`human_review_decisions.json` is the exact exported file supplied by Aryan Jain (found initially at repository root). SHA-256: `a930cc5a4d5f38454f86caf78855b0c454b7785dbdb217b2270d7c0b2f573ac9`. It retains 51 `accepted` and 146 `unreviewed` decisions. It has not been edited to manufacture additional clicks or timestamps.

`attestation_v1.json` separately records the reviewer's direct statement that all row labels were reviewed and the explicit clarification “Also accept all unmarked cell values I reviewed.” It is hash-bound to the export. This authorizes effective acceptance of the 146 unmarked values, with `basis=reviewer_bulk_attestation`. All 98 row-label occurrences are accepted by the statement. Their hierarchy, headers, periods, units, geometry and completeness are not signed off by implication.

Every derived cell retains its prior content, exported decision and acceptance basis. The full exported record is also preserved in each versioned reference's `decision_ledger`. Exported evidence URLs such as `assets/original_page.png` are relative to **`benchmark/review/`**, not to this archive directory. The source PDF path and hash, original page index, selected-PDF identity, and source bbox are preserved so images can be regenerated without models.

`evaluation_v1.json` pins 48 stored prediction files and hashes. Its two explicit selections are fin1 and post-fix; the latter uses p0fix2 except Docling matching-off Daiwabo uses p0fix3. No inference is required. Both selections evaluate development-exposed sources, not blind holdouts.

The importer preserves unreadable, unresolved, missing-export and correction-needed states. Free-text correction notes are not automatically parsed into gold. A finalized correction must explicitly use `decision="corrected"` and a `correction` object containing exactly `raw`, `value`, and `status`; otherwise it remains unresolved. Bulk acceptance never overrides these unresolved states. The supplied export contains none of them, so no value corrections were made in v1.

Derived references: `benchmark/human_gold/v1/`. Scoped scores: `results/human_v1/`. Both have separate SHA-256 locks and create-only writers. Original `benchmark/gold/`, source manifests, raw model outputs and frozen baseline files remain unchanged.

See [`docs/HUMAN_REVIEW_RESULTS.md`](../../docs/HUMAN_REVIEW_RESULTS.md) for exact denominators, results and reproducibility commands. Later decisions or changes of scope require a new attestation/reference version; do not edit these archived inputs in place.
