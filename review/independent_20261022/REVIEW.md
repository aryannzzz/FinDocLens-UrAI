# Independent research review of the integrated submission

Reviewed submission: `3695030` (`integration-v1`), with fin1 extraction provenance pointing to `afcfb56`. Review branch: `review/independent-20261022`. Reproducibility fixes: `fb8481d5b1ce8e032e1fc34bda332860e56457f1`.

**Verdict: technically credible as an internship research prototype, with substantial evaluation and reliability weaknesses.** The code, real model runs, preserved failures, and unusually candid integrated report support a positive technical assessment. The evidence supports an in-sample engineering improvement on Daiwabo. It does not establish generalization, complete table reconstruction, calibrated confidence, or VLM research experience. I would advance the applicant to a technical discussion, but would not accept the benchmark as an independent accuracy estimate or the parser as safe for unattended financial extraction.

This is an independent AI review, not human certification of gold. No original annotations, baseline files, measurements, RESULTS.md, or generated results tables were replaced. Fresh measurements have separate run IDs. Only the five reproducibility files listed below were changed in existing code.

**What I independently executed and verified**

- Original suite: **82/82 pass**, including a subprocess running all **25 frozen baseline tests**. After one reproduction regression test was added: **83/83 pass**. Frozen baseline hash checks pass; `git diff v2-frozen -- baseline_v2` is empty.
- Independently rescored **450 fin1 predictions**, checked the structural contract, compared cold/warm canonical data, and verified **264 raw-artifact hashes**: no differences or hash failures. Recomputed **25 cohort summaries**: no differences. This validates internal accounting against the existing drafts, not the drafts themselves.
- Fresh runs: native_grid on all 18 available benchmark pages; Docling matching on/off and Docling+RapidOCR on all three real digital pages; RapidOCR on both issuer raster derivatives; region ablation on Daiwabo; router on Daiwabo and the ELECOM raster. **32 page/backend combinations, 122 cold/warm trials**, with no differences from the corresponding fin1 extraction tables, statuses, issues, or accuracy metrics. The optional medium OCR model and the complete model/control matrix were not freshly rerun; their saved artifacts were included in the 450-prediction audit.
- Exported the tracked submission to an isolated `/tmp` tree, supplied the cached full-source PDFs and their recorded acquisition metadata, reconstructed selected pages offline, and ran the documented native demo. The original demo failed on missing raster derivatives; after the fixes it completed, including tests, all native backends, contract reporting, and viewer generation. The direct results/contract commands also completed in that isolated tree. Original output paths in the main workspace were preserved.
- Four new synthetic PDF cases, six evaluator mutations, two router probes, a merged-body-label mapping probe, and an equal-span nested-header probe. Inputs and outputs are retained; none was added to the original benchmark denominator.

Evidence: [audit.json](audit.json), [additional_probes.json](additional_probes.json), [commands.md](commands.md), test/demo logs alongside this report, and `runs/<backend>/<document>/independent_review_20261022_{main,adv,raster}/`. Full source PDFs were cached; I did not independently repeat internet acquisition or establish whether OMRON is accessible now.

**1. High — new ordinary inputs can silently lose financial data while the parser and router report success. Unfixed.**

The two-column synthetic control scores 8/8. Changing only its first data row to amounts `2025` and `2026` produces **6/8**, drops the entire 現金 row, emits no issue, and still returns canonical `success`. `read_words()` excludes every bare integer from 1900 through 2099 from numeric tokens (`findoclens/backends/native_grid.py:94`). The classifier cannot distinguish those amounts from years based on token content alone. Because they are excluded before the unassigned-token audit, that audit does not catch the loss.

A standalone four-row, one-financial-column table abstains at **0/4**. Placing that same table beside the working two-column table yields **8/12**, only one of two tables, four missing rows, and `success`. The seed rule requires at least two numeric columns (`native_grid.py:227`). Dropped numeric tokens receive only an informational `unassigned_numeric_tokens` issue. This contradicts the advertised arbitrary-column capability, including the project requirement to handle one-column tables explicitly.

Both defective PDFs also get router status `ok` and `route=native_accept`; the mixed-table example even logs disagreement with v2 before accepting native output. Router suspicion checks do not cover these omissions. Evidence: `audit.json:native_probes`, `additional_probes.json:router`, and the four `runs/native_grid/review_*/independent_review_20261022/` directories, including source PDFs and synthetic truth.

These are high-priority parser fixes. They were left visible because resolving header/body classification and one-column detection requires a separate implementation change and regression study, beyond the narrowly scoped reproduction repair in this review.

**2. High — semantic and reliability metrics have exploitable blind spots. Unfixed.**

Fixed gold denominators and one-to-one matching are sound in the tested deletion/duplicate cases. Nevertheless, the new mutations show:

| Mutation of the original reference-shaped prediction | Evaluator result |
|---|---|
| Change every cell's period to 1900, role to composition_pct, and header link to a nonexistent ID; keep leaf headers intact | 74/74 raw and typed; false_assurance=false |
| Reverse all 43 rows and reindex them | 74/74 raw; order 1/43; false_assurance=false |
| Put every cell evidence box at `[0,0,1,1]` and add an extra leaf header | 74/74 raw and typed; false_assurance=false |
| Delete the last row | 72/74; two silent omissions |
| Add an `omitted_table` warning for an unrelated region to that deletion | Still 72/74, but silent omissions fall to zero |
| Add an unmatched duplicate table | Extra table is correctly penalized, but leaf-header precision remains 2/2, ignoring its two extra headers |

`semantic()` compares only value and status (`benchmark/evaluate.py:102`); leaf headers are scored separately, so incorrect per-cell associations are invisible to typed accuracy. `false_assurance` omits order, evidence localization, extra headers, and cell associations (`evaluate.py:282`). Omission warnings ignore their region/bbox and suppress unrelated omissions when no label is supplied (`evaluate.py:128`). Predicted-header denominators are accumulated only inside matched gold tables (`evaluate.py:192`). No localization metric checks the correctness of cell evidence boxes.

The report correctly discloses that generic `partial` statuses make false-assurance rates incomparable: all Docling outputs are downgraded for missing hierarchy. “No silent omissions” can also mean a sufficiently broad warning, not successful recovery. Neither reliability metric is a calibrated assurance estimate. Evidence: `audit.json:evaluator_probes`.

**3. High — independent validation remains absent; the nominal holdouts were used for development. Unfixed.**

Every reference still has `ai_draft`, zero human-checked cells, and no named reviewer. ELECOM/Daiwabo references use the same PyMuPDF text layer as the native methods, creating common-mode glyph/omission risk. The original TSV is also an AI transcription. Completeness flags are drafter assertions; passing `benchmark.validate` cannot establish source completeness.

`native_grid` was designed with ELECOM, Daiwabo, and another ELECOM page in view. Integration tuned ELECOM hierarchy using the “holdout” reference; Daiwabo also motivated the region-omission warning. The manifest still labels the issuer pages `holdout`, so machine-readable cohorts can be mistaken for blind test results even though RESULTS.md explicitly discloses the contamination. Source-family split isolation is implemented and passes; it does not undo design-time exposure. Raster derivatives share source families and are not additional independent examples.

This is disclosed development leakage, not evidence of fabricated runs or covert loading of gold in workers. The integrated README/RESULTS/memo handle the limitation responsibly. The next credible accuracy claim needs independently reviewed annotations and a new issuer/template frozen before any code changes. The review gates “independent gold” and “out-of-template behavior” remain unmet.

**4. High — merged-cell and nested-header support is materially narrower than the schema suggests. Unfixed.**

No reference header has `rowspan > 1`; the `merged_headers` fixture tests nested horizontal groups, not vertical header merges. The successful grouped-header scores were obtained after tuning on those same synthetic fixtures. The unavailable OMRON page supplies no real grouped-header evidence.

Two mapper probes expose missing relations:

- A Docling body label spanning rows 1–2 survives in the saved raw grid as `r0=1,r1=3`, but `_map_table()` indexes only starting offsets. Its second numeric row has `label=None` with no explicit span relation. Raw evidence is retained in direct adapter runs, but the semantic rows lose the association.
- An outer group and inner year group spanning the same two columns lose their group-parent link. The leaf headers attach to the outer group, skipping the year group. `_leaf_and_groups.parent_of()` rejects equal column sets and breaks equal-width ties toward the earlier group (`adapters/canonical.py`).

Evidence: `additional_probes.json:spans`. These are deterministic normalization probes, not claims about a fresh model's recognition of a real merged-cell page.

**5. Medium — Daiwabo's gain is real, but 63/63 is not complete reconstruction. Unfixed; already partly disclosed.**

The rendered slide visibly contains the 8 asset rows, 9 liabilities/equity rows, and 4 lower explanatory rows represented in the draft. I inspected its full-page rendering and compared the labels, signs, and numeric tuples with the stored and fresh output. The native parser associates all 63 numeric values with the correct labeled rows and physical numeric columns in three separate regions. This is substantially stronger than token recall.

| Daiwabo path | Aligned numeric cells | Raw cells including explanation text | Tables | Leaf headers | Hierarchy |
|---|---:|---:|---:|---:|---:|
| Frozen v2 | 2/63 | 2/67 | 1/3 | 0/10 | 0/7 |
| native_grid | 63/63 | 63/67 | 3/3 | 6/10 | 0/7 |
| Docling matching on | 0/63 | 0/67 | 1/3 | 3/10 | 0/7 |
| Docling matching off | 0/63 | 0/67 | 1/3; abstains | 0/10 | 0/7 |
| Native regions + Docling | 51/63 | 51/67 | 2/3 | 6/10 | 0/7 |

Residual issues matter: two native table units are null; the lower numeric cells lack periods; hierarchy is absent; arrows physically between the first and second amounts are relocated into trailing explanation strings (`→主に…`), causing the four raw text mismatches. The draft omits those arrows from its explanation cells and invents unprinted period/role headers by inheritance. Those annotation conventions need adjudication, not automatic “repair” to favor either side. A 0.1 table-IoU threshold and no cell-localization scoring also make “3/3” a coarse region match.

Monetary signs on the measured native pages are preserved, including `△0`, `－`, and explicit plus. OCR dash losses and synthetic Docling dash substitutions are present in the stored scores, not hidden by zero-filling. Negative-sign fidelity on unseen/noisy sources remains unproven.

**6. Medium — performance and backend comparisons support direction, not precise rankings or causal conclusions. Unfixed.**

Native and model paths use the same gold denominators, but the native parser was tuned and Docling was untuned. The region ablation also receives proposals from that tuned parser. Crop inference changes scale/context as well as region selection: its improvement implicates the page-level pipeline but does not prove that TableFormer is generally “not the culprit.” One OCR size comparison does not establish that the remaining problem is “not a capacity problem.”

Fresh runs confirm the broad CPU cost difference and OCR behavior: ELECOM raster 34/56 aligned cells; Daiwabo raster 0/63 despite substantial token recall. Timing varies materially: fresh Daiwabo Docling matching-on cold was 15.5 s versus about 11 s reported, and regions cold 24.5 s versus about 13.5 s. The warm native/model gap remains large, but single cold samples and uncontrolled desktop load do not support a constant 70× ratio or a reliable 12% cell-matching speed advantage. Rendering and cold PNG writing are included; warm RSS is a cumulative process high-water mark. These scopes are disclosed.

Router memory is split across processes. Fresh ELECOM raster auto reports about 113 MB parent RSS and about 2,010 MB child peak, not a 113 MB total footprint. Moreover, `adapters/auto.py` deletes its temporary model artifacts; `route()` discards the returned model manifest. The retained router run has no raw Docling document or precise loaded checkpoint revision of its own. Direct model runs provide that evidence separately. No GPU allocation or VLM measurement exists, and the integrated report does not pretend otherwise.

**7. Reproducibility blocker — fixed, with original failures retained.**

The raster manifest/gold were tracked, but the referenced PDFs were ignored. `benchmark.raster_variants` immediately exited because the manifest existed. In the isolated export, the original demo reached a missing raster PDF and crashed. It could not be reproduced from the tracked submission even with the real source PDFs cached.

`fb8481d` changes only:

1. `benchmark/raster_variants.py`: rebuild missing raster PDFs into temporary files; compare against frozen hashes before installing them; verify existing inputs/reference locks; reject and retain corrupted files. Existing manifests/annotations are never regenerated. The documented no-argument command now materializes when a manifest exists; `--materialize` is explicit.
2. `run_demo.sh`: materialize/check adversarial and raster inputs on every invocation, including partially cached checkouts.
3. `scripts/contract_report.py` and `scripts/make_results.py`: add the repository root to the script import path. The README's direct command previously raised `ModuleNotFoundError: adapters` without `PYTHONPATH`.
4. `tests/test_raster_reproduction.py`: verify missing-input recovery, pinned output bytes, idempotence, unchanged annotations/manifests, and preservation/rejection of corrupt cached input.

Validation: all 83 tests pass; the fixed isolated demo completes; direct contract reporting checks 450 predictions; direct results generation processes 154 result rows and 17 before-change rows. These generators were run in the isolated tree, so the submission's original results remain unchanged. Raster reconstruction intentionally rejects bytes that differ under another rendering version; use the pinned native PyMuPDF environment.

**Lower-priority auditability issues, not modified**

- `benchmark.validate` and the original split-isolation test omit the raster manifest and its separate lock file. The new materializer checks its reference locks, and this review checked saved raster run hashes; comprehensive validation should cover all manifests in one command.
- The viewer hard-codes ten of eighteen available pages and omits `vertical_spacing`, the native parser's known silent regression. It also displays a “warm” value from one repetition, where the benchmark requires at least three for a median claim. The report/control appendix is more complete than the demo.
- Older CLAUDE_* reports remain alongside the integrated report and use token-recall claims and older counts (e.g. “lost 4/63” versus the integrated token diagnostic's eight absent tokens). Version labeling and a prominent archival pointer would reduce conflicting interpretations.

**Highest-impact remaining work**

First adjudicate the actual source references with a human, including arrows, implicit headers, hierarchy, units, signs and all table boundaries. Then freeze a genuinely unseen issuer/template before implementation. Repair year-like amount loss, one-column table handling and router omission checks, and measure those changes under a new run ID. Extend evaluation to cell associations, scoped omission warnings, localization and real rowspans; make abstention/partial behavior independently assessable. Preserve the current artifacts as the development record. A noisy-scan/OCR or VLM comparison becomes meaningful after these foundation issues are addressed.
