# Audit of frozen v2 evaluation

The initial repository commit is `cd27035` (`v2-frozen`). `benchmark/frozen_sha256.json` hashes every supplied baseline file, including the original PDF, 43-row TSV, predictions, CSV, diagnostics, and original evidence image. No baseline source/results are changed. The initial isolated run passes all 25 original tests; its transcript is `reports/frozen_tests_initial.txt`. Tests create PDF variants, so they must run in a temporary copy rather than under the immutable directory.

Concrete limitations in `baseline_v2/evaluate.py`:

- The docstring calls the reference independent, but the original README explicitly discloses AI transcription. It is in-sample, not independent human gold.
- Rows are paired with `pred[i]`, not matched by table, identity or evidence. A missing row shifts later comparisons. Duplicate `その他` or depreciation labels do not have independent one-to-one alignment.
- `row_labels` compares a full predicted path with only the last gold path component and is unused. The separately returned label/path counters are meaningful only when sequences already align.
- `evaluated_cells` and semantic counts iterate only over paired non-section rows. **Raw accuracy does retain the full 74-cell gold denominator**, which should not be misrepresented as a recognized-only denominator. Other coverage/error denominators, extra predictions, absent rows, and table/header matching remain missing.
- `sequence_complete` checks length equality, not identity or completeness. One missing and one spurious row can satisfy it.
- Typed semantic evaluation reuses the parser's normalizer on raw strings. It does not validate the actual predicted `value`/`status` fields, creating common-code error risk. It supports neither decimals nor plus/percentage roles.
- `benchmark.py` scores only the first page; its duplicate-page test is not an independent source. Raster-only outcomes have `scores=None`, preventing an ordinary failed-page accuracy denominator. Controlled source perturbations do not support cross-issuer claims.
- A redacted minus is scored against unchanged original gold in the old robustness script. That can diagnose change sensitivity but cannot be called extraction error against the edited visual source. New controls have distinct, explicitly changed references.
- Timing combines native parsing in an already-imported process. It records no model load, render stages, CPU/GPU memory, versions, checkpoint, timeout, or errors. Cross-engine embedded-text agreement is not independent visual truth.

New evaluation fixes these counting problems while retaining originals verbatim. Tables use maximum one-to-one geometric overlap matching (page equal, IoU >= 0.1); rows require whitespace-normalized label equality, with geometry/context/order for duplicate-label ties. No numeric value is used to align rows. Physical columns are scored independently of predicted header roles. Missing/failed/abstained pages keep complete known-gold denominators; spurious tables/rows/cells remain in precision denominators. Bbox-less predicted tables are counted as unlocalizable, with no invented location. The generous IoU threshold measures coarse region localization, not grid accuracy.

Holdout draft references were bootstrapped from native source text in declared regions, with AI visual inspection, before predictions were scored. They share a PDF text engine with v2 and may share text-layer errors. No human has certified them. Immutable reference digests are in `gold/SHA256.json`, and every scored trial stores its reference digest. Corrections must preserve the old version and include independent crop evidence and a reason; prediction disagreement alone is not a reason to change gold.

The measured evidence is deliberately small: two independent issuers, one inaccessible candidate, and 13 development controls. Header/period hypotheses in Daiwabo's unprinted lower table are AI-drafted semantic associations and need review. Synthetic controls share source families and stay in development. No thresholds or extraction code were tuned on the holdout references, and no parser/adapters were edited in this workstream.
