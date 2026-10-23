# Archived AI visual cross-check, not human verification

These two files are exact copies of the pre-existing `ur_ai_visual_audit/` report and per-cell AI check. They support the provenance of the 146 bulk-approved cells. They do **not** establish individual human review or a blind annotation pass. The report explicitly states that references had previously been seen.

The audit JSON's `source_sha256` field hashes the **selected one-page PDF**, corresponding to `input_sha256` in the benchmark manifest; it does not hash the full issuer filing. The v2 classifier checks this identity and raw cell text before assigning `bulk_user_approved_ai_cross_checked`. The archived bytes and original field names are preserved. No AI model/version was recorded in these audit files, so none is invented here.

All 197 cells were AI-checked according to this record; only the separate 51 accepted export entries have individual human source-review evidence. The remaining 146 are user-approved AI references. Source-image crops in the original local directory remain local; they are not needed to rerun this provenance classification.
