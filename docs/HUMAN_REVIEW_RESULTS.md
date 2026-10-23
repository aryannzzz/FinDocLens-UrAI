# Human-reviewed reference v1 — 23 October 2026

Reviewer: **Aryan Jain**. Export timestamp: `2026-10-23T06:51:52.884Z`. Export SHA-256: `a930cc5a4d5f38454f86caf78855b0c454b7785dbdb217b2270d7c0b2f573ac9`.

**This is human-reviewed content on development-exposed source pages, not a blind test.** Original `benchmark/gold/` files remain byte-for-byte AI drafts. The separately versioned dataset is [`benchmark/human_gold/v1/`](../benchmark/human_gold/v1/manifest.json). It is `partially_human_verified`: values and row labels have been accepted, while headers, periods, roles/header links, units, hierarchy, geometry, and completeness have not been certified.

## What the reviewer accepted

The export was found at repository-root `human_review_decisions.json` and copied byte-for-byte to [`review/human_signoff/human_review_decisions.json`](../review/human_signoff/human_review_decisions.json). It contains **51 explicitly accepted cells and 146 unreviewed cells**, with no corrections, unreadable or unresolved entries. Its original states and timestamps remain unchanged.

The reviewer subsequently stated that every label was reviewed and explicitly clarified **“Also accept all unmarked cell values I reviewed.”** This is recorded separately in [`attestation_v1.json`](../review/human_signoff/attestation_v1.json), bound to the export hash. The 146 formerly unmarked values are effective acceptances **by reviewer attestation**, not invented UI clicks. Each derived cell/ledger entry preserves its exported state and records the effective decision and acceptance basis. The 98 row labels are accepted by that same direct reviewer statement; parent paths and hierarchy are not implied by label acceptance.

| Source | Relationship / kind | Explicit exported acceptances | Later bulk acceptances | Reviewed financial cells | Reviewed text cells | Reviewed row-label occurrences |
|---|---|---:|---:|---:|---:|---:|
| Original supplied page | same issuer / source; development | 31 | 43 | 74 | 0 | 43 |
| ELECOM PDF page 9 | independent issuer / source; design-exposed | 20 | 36 | 56 | 0 | 34 |
| Daiwabo PDF page 10 | independent issuer / source; design-exposed | 0 | 67 | 63 | 4 | 21 |
| **Total** | **3 source pages, no new independent test** | **51** | **146** | **193** | **4** | **98** |

The exact value denominator is **197 cells = 193 financial-column cells + 4 explanatory text cells**. Financial-column cells include the two printed dash placeholders (`－`, typed null / `not_reported`); they are not silently changed to zero. The label denominator is **98 row occurrences**, including repeated labels in different source contexts. The accepted subset covers all existing annotated content slots; it does not prove that the AI reference contains every possible source table, row or relationship.

There are **zero human-certified header, period, unit, hierarchy-edge, table-boundary or localization denominators**. Those inherited AI fields remain visible as alignment context. We do not set completeness flags to true merely to pass the full-table evaluator. The dedicated subset evaluator scores only accepted fields. Original source observations and typed values are retained separately from their human acceptance provenance.

## Results from stored predictions, without inference

Raw content equality removes Unicode whitespace only and preserves Japanese glyphs, signs, digits, commas, decimals and arrows. Typed content compares value plus status; it is explicitly **not** a claim of correct period/role/header semantics. Tables match one-to-one at IoU >= 0.1; rows require label equality after whitespace removal, with geometry/order for ties; cells use physical column indexes. Values are never used to find a matching row. Missing accepted cells count as incorrect against the full reviewed denominator. Geometry is inherited AI context and has not become a human localization score.

The frozen `fin1` and post-fix selections produce identical human content/label scores on these three pages:

| Backend | Financial raw exact | Financial value + status | All-cell raw exact | Matched reviewed labels |
|---|---:|---:|---:|---:|
| frozen `v2` | 132/193 | 132/193 | 132/197 | 78/98 |
| `native_v2` | 132/193 | 132/193 | 132/197 | 78/98 |
| `native_grid` | **193/193** | **193/193** | **193/197** | **98/98** |
| `docling_cmtrue` | 130/193 | 130/193 | 130/197 | 77/98 |
| `docling_cmfalse` | 130/193 | 130/193 | 130/197 | 78/98 |
| `docling_rapidocr` | 130/193 | 130/193 | 130/197 | 77/98 |
| `docling_regions` | 181/193 | 181/193 | 181/197 | 94/98 |
| `auto` | **193/193** | **193/193** | **193/197** | **98/98** |

These are micro counts across the three digital source pages, not raster/OCR robustness estimates. Numeric-role and all-cell denominators are deliberately separate. All four explanatory text cells still mismatch, because the native output folds the source's relation arrows into the explanation strings; no value/reference was edited to improve that score.

The per-document financial denominators are **74 original, 56 ELECOM, 63 Daiwabo** for every backend. Each backend gets 74/74 original and 56/56 ELECOM; Daiwabo separates their behavior:

| Daiwabo path | Financial raw exact | All-cell raw exact | Matched reviewed labels |
|---|---:|---:|---:|
| frozen `v2` / `native_v2` | 2/63 | 2/67 | 1/21 |
| `native_grid` / `auto` | 63/63 | 63/67 | 21/21 |
| Docling matching on / RapidOCR | 0/63 | 0/67 | 0/21 |
| Docling matching off | 0/63 | 0/67 | 1/21 |
| Native regions + Docling | 51/63 | 51/67 | 17/21 |

The region/row/physical-column alignment requirement prevents a merged Daiwabo table from earning full credit just because its numeric tokens are present. A targeted test also verifies that flattening an otherwise correct Daiwabo prediction loses reconstruction credit. Detection/hierarchy/header accuracy are not newly human-certified by these numbers.

Stored prediction paths and hashes are explicit in [`evaluation_v1.json`](../review/human_signoff/evaluation_v1.json). `fin1` uses the original cold predictions. `postfix` uses `p0fix2_main`, except Docling matching-off on Daiwabo uses `p0fix3_main`, the separately retained fix for label duplication in empty grid rows. This substitution is declared rather than silently selecting a latest directory. **48 stored page/backend predictions** were rescored (2 selections × 8 backends × 3 pages). No backend was loaded or re-executed. Original latency, hardware and memory measurements were not replaced or reinterpreted.

Machine-readable scores and per-cell errors: [`results/human_v1/summary.json`](../results/human_v1/summary.json), with per-document reports under `results/human_v1/reports/` and a separate SHA-256 lock file.

## Daiwabo periods: observed content versus inferred associations

The lower explanation table prints no period headers. Its **12 reviewed financial values** are in the content denominator. The copied period associations remain **inferred and unreviewed**, so they are not human period gold. The four unprinted lower-table header records also remain unreviewed; accepting their row labels or values does not turn them into observed source headers.

For transparent comparison only, the evaluator retains three **unverified period-context diagnostics**:

| Period context across source pages | Context denominator | Post-fix native_grid agreement | Human period certification |
|---|---:|---:|---|
| Association with printed period headers | 164 financial cells | 164/164 | None; no header/association sign-off was exported |
| Constructed change interval (`later_vs_earlier`) | 17 Daiwabo cells | 17/17 | Inferred semantics, not a literally printed period |
| Inherited, unprinted lower-table periods | 12 Daiwabo cells | 0/12 | Inferred/unreviewed; excluded from human period metrics |

These diagnostics are labeled `unverified_period_diagnostics`, not human accuracy. There are **0 human period slots**. A parser retaining null periods in the lower block is not declared wrong against a human-observed header that does not exist.

## Reproduce / validate

```bash
.venv/bin/python -m benchmark.human_reference --check benchmark/human_gold/v1
.venv/bin/python -m benchmark.human_evaluate \
  --reference benchmark/human_gold/v1 \
  --config review/human_signoff/evaluation_v1.json \
  --out results/human_v1 --verify
.venv/bin/python -m unittest tests.test_human_reference -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m benchmark.validate
```

To create a new version/output, select new directories; existing versions and scores are create-only:

```bash
.venv/bin/python -m benchmark.human_reference \
  --decisions review/human_signoff/human_review_decisions.json \
  --attestation review/human_signoff/attestation_v1.json \
  --out /tmp/my-human-reference/v1
.venv/bin/python -m benchmark.human_evaluate \
  --reference /tmp/my-human-reference/v1 \
  --config review/human_signoff/evaluation_v1.json \
  --out /tmp/my-human-scores
```

Validation: **16 focused tests pass; 149 full tests pass**, including the subprocess execution of all 25 frozen baseline tests. Tests rebuild the derived references and all score outputs **byte-for-byte** in temporary directories. They cover pending/unreadable/unresolved decisions surviving bulk acceptance, missing exports staying excluded, finalized structured corrections, wrong source/reference hashes, raw glyph fidelity, fixed failure denominators, and separation of inferred periods. No archived AI reference or prediction is modified. Logs and command/device/code metadata are in `runs/human_review/import_and_score/v1/`.

## Interpretation and remaining work

Human image acceptance now supports the scoped content/label accuracy claims above and resolves the former “zero human-reviewed content” limitation for these source pages. It does not remove development exposure: original is development data, ELECOM/Daiwabo are independent issuers used during design, and none is a blind holdout. No synthetic/control/raster reference is automatically promoted by this import. Full structural adjudication and a new issuer/template frozen before further tuning remain necessary for an independent generalization estimate.
