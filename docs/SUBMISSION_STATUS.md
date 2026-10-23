# Remaining submission requirements — evidence checked 23 October 2026

This checklist uses the repository's `00_START_HERE.md`, `TASKS/01_CODEX_BENCHMARK.md`, `TASKS/03_REVIEW_AND_INTEGRATE.md`, `AGENTS.md` and `docs/EVAL_PROTOCOL.md`. The original applicant email is not present here. Its deadline, submission address/platform, archive/link format and any email-specific deliverables must be checked against that email; they are not invented below.

## Current review confidence

| Evidence | Original | ELECOM | Daiwabo | Total |
|---|---:|---:|---:|---:|
| Individually source-reviewed cells | 31 | 20 | 0 | **51** |
| Bulk user-approved AI-cross-checked cells | 43 | 36 | 67 | **146** |
| Individually reviewed row contexts | 16 | 10 | 0 | **26** |
| High-risk sign/placeholder cells still only bulk-approved | 6 | 2 | 23 | **31** |

The entire export and prior approval ledger are preserved. The exact 51-cell list is `benchmark/human_gold/v2/individually_reviewed_cells.csv`; all classifications are in `cell_catalog.json`. The 31 outstanding high-risk keys are in `review/human_signoff/remaining_sign_review_v2.csv`. There are **37** such cases overall, of which **6** were individually reviewed. Both original `－` placeholders, both ELECOM `△4` cells, and all 23 Daiwabo signed cases remain in the bulk-approved group. AI visual checking is not human sign-off.

## Outstanding validation gates from the project instructions

1. **Daiwabo's minimum human value sample is not met.** `00_START_HERE.md` and `benchmark/README.md` ask for at least 20 numeric cells per available independent page, with signs/dashes, headers and boundaries checked. ELECOM has 20; Daiwabo has 0. Review at least 20 Daiwabo financial cells against the source and record actual inspection, rather than merely bulk-approving them. Seven complete three-value rows would provide 21 cells. Alternatively, inspecting all 23 outstanding Daiwabo signed cells covers this value-count minimum while addressing the high-risk queue.
2. **The independent-document transcription target is not yet individually verified.** `TASKS/01_CODEX_BENCHMARK.md` prioritizes 15+ financially meaningful rows and 30+ numeric cells across independent sources. Individual evidence currently covers only ELECOM's 10 rows / 20 cells on the added independent issuers. Seven Daiwabo rows / 21 cells would raise this to 17 independent-source row contexts / 41 values. Original-source review does not turn into additional independent-issuer evidence.
3. **Finish the negative-sign/dash gate and structural scope.** There are 31 high-risk cases left above, plus unreviewed headers, periods/roles, units, table extents and hierarchy. The current reference contains 14 header annotations, of which 4 lower-table Daiwabo headers are unprinted/inferred; all remain structurally unreviewed. Its 5 table-like extents and 82 parent-path edges are also unreviewed context. Record source-observed header review separately from contextual interpretation. Never describe the 12 inferred lower-table periods as printed dates. The old 98-label attestation remains a user statement, not 98 exported individual label decisions or verification of parent paths.
4. **Out-of-template/blind performance remains unestablished.** Original is development data; ELECOM and Daiwabo were used during parser design. A new issuer/template frozen before further tuning is needed to claim blind generalization. This is a research review gate, not a reason to invent a score or rerun models on the same pages. If submitting the current prototype, explicitly retain this limitation and the known silent failures (including `vertical_spacing`).

The other 146 cells do not all need new individual clicks merely to keep the *user-approved agreement* comparison. They **do** need genuine source inspection before they can be described as individually human-verified. Full original-page inspection and full-page gold are preferable under `00_START_HERE.md`; the original still has 43 cells without individual inspection. An attestation can record inspections that really happened, but bulk acceptance of AI drafts is not that evidence.

## Outstanding submission packaging / applicant actions

- **Export and attach the complete AI chat logs separately.** `00_START_HERE.md` workflow item 5 and `TASKS/03_REVIEW_AND_INTEGRATE.md` item 5 explicitly require the full logs, not a summary. `AI_COLLABORATION.md` is the disclosure, not a transcript. No complete transcript exports were identified among repository submission files. Include the relevant baseline, Codex, Claude/integration, review and follow-up sessions; availability outside this repository is unverified.
- **Prepare the deliverable from the final committed state and check the documented entrypoints.** Include code, frozen original results, current v2 reference classification/individual cell list, stratified scores, manifests, environment pins, raw backend artifacts, failure analysis, technical memo and AI disclosure. Include a usable path for obtaining source PDFs and generating images. PDFs, source PNGs, virtualenvs and model caches are intentionally ignored/local; a checkout alone does not include them. Do not package `.venv`/large caches as a substitute for setup instructions, and do not redistribute full third-party filings without the source-rights review called for in the project notes.
- **Run a final smoke check in the environment the recipient will use.** The repo provides `run_demo.sh`, `benchmark.review --serve`, pinned native/model setup instructions and checks. The current provenance correction needs only stored-prediction replay; no new expensive model inference is required. A clean-checkout/clean-environment delivery smoke test is a packaging check, not a new generalization experiment. Existing source-review repair tests already demonstrate recovery of ignored assets from cached PDFs.
- **Check the actual application email for any additional format/deadline requirements.** The local integration task asks for a two-minute screencast script and says to record it only if actually made. The script exists; no recorded video was identified. An actual video is conditional on the applicant/email, not falsely marked complete or newly declared mandatory here.

## Artifacts already present

- Reusable parser/backends, adapter contract, frozen baseline and tests, benchmark harness with failures retained, source manifest/hashes, cold/warm CPU measurements, package/checkpoint records and explicit missing GPU/VLM results.
- Current numerical provenance: 51-cell individual accuracy, 146-cell bulk agreement and unchanged 197-cell approved-reference agreement in `results/human_v2/`; no Daiwabo individual accuracy is claimed.
- Exact cells, source-review UI, source evidence generation, regression tests, failure gallery, `RESULTS.md`, updated technical memo, setup/environment docs, `run_demo.sh`, screencast script and AI collaboration disclosure.
- Original exported decisions, old ledger and v1 snapshots preserved for audit, with v1 confidence labels explicitly superseded. No parser output or frozen baseline changed during this correction.

Passing tests and available artifacts do not silently close the human-review or blind-evaluation gates above. A credible final narrative should state exactly which requirements are met, which remain unverified, and which are optional or email-dependent.
