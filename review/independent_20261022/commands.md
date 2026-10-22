# Commands and artifact boundaries

Submission inspected: `3695030`. Review branch: `review/independent-20261022`. Critical reproduction repair commit: `fb8481d`. No extraction algorithm, evaluator, original result, or reference was changed.

All commands below ran from the repository root unless stated otherwise. Model commands used the existing optional environment and local model cache; no packages, CUDA, drivers, or system Python were changed. Model invocations were sequential. All fresh run IDs were create-only. Hardware, Python/package versions, checkpoint metadata, stages, elapsed times and CPU RSS are recorded in run metadata/measurement files; GPU measurements remain unavailable. New synthetic truth is generated explicitly, AI-authored, and separate from the reference corpus.

**Tests / immutability**

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m benchmark.validate
git diff v2-frozen -- baseline_v2
git diff --check
```

Initial result: 82 tests pass, including the test that runs 25 frozen tests in an isolated copy. After the reproduction regression was added: 83 tests pass. Logs: `tests_initial.log`, `raster_regression.log`, `tests_final.log`, `tests_after_fixes.log`, `validation_initial.log`, `validation_final.log`. `benchmark.check` was also executed by the isolated demo; it writes only the isolated copy's test reports.

**Saved-artifact and adversarial audit**

```bash
PYTHONPATH=. .venv/bin/python review/independent_20261022/audit.py \
  --out review/independent_20261022/audit.json
PYTHONPATH=. .venv/bin/python review/independent_20261022/additional_probes.py \
  --out review/independent_20261022/additional_probes.json
```

These outputs already exist and must not be overwritten. To repeat the first command, choose a new `--out` and a new `--probe-run-id`; for the second, choose a new `--out`. The scripts check saved metrics/hashes, generate new synthetic PDFs with declared truth, mutate predictions in memory, and test mapping/routing logic. They never edit the original references or scores. Initial one-off router, span and cohort probes were also saved as `router_probes.json`, `span_probes.json`, and `cohort_audit.json`; `additional_probes.py` reproduces those checks.

**Fresh extraction runs**

```bash
scripts/run_integration.sh native_grid independent_review_20261022 .venv/bin/python 3 3 3
ONLY=main scripts/run_integration.sh docling_cmtrue independent_review_20261022 .venv-docling/bin/python 3 0 0
ONLY=main scripts/run_integration.sh docling_cmfalse independent_review_20261022 .venv-docling/bin/python 3 0 0
ONLY=main scripts/run_integration.sh docling_rapidocr independent_review_20261022 .venv-docling/bin/python 3 0 0
ONLY=raster scripts/run_integration.sh docling_rapidocr independent_review_20261022 .venv-docling/bin/python 0 0 3

HF_HUB_OFFLINE=1 .venv-docling/bin/python -m benchmark.run \
  --backend docling_regions --entrypoint adapters.docling_regions:extract \
  --documents daiwabo_p10 --run-id independent_review_20261022_main --warm 3 --timeout 300
HF_HUB_OFFLINE=1 .venv/bin/python -m benchmark.run \
  --backend auto --entrypoint adapters.auto:extract \
  --documents daiwabo_p10 --run-id independent_review_20261022_main --warm 0 --timeout 300
HF_HUB_OFFLINE=1 .venv/bin/python -m benchmark.run --manifest benchmark/raster_manifest.jsonl \
  --backend auto --entrypoint adapters.auto:extract \
  --documents elecom_p9_scan200 --run-id independent_review_20261022_raster --warm 0 --timeout 300
```

Result: 32 scored page/backend combinations and 122 trials; all fresh cold extraction tables/statuses/issues and accuracy metrics equal corresponding fin1 data. OMRON remains explicitly unavailable in the cached manifest. The router's two sample runs have no warm estimate. Logs named by backend alongside this file; detailed artifacts are in `runs/` and summaries in `benchmark/reports/*independent_review*`. Most runs preceded `fb8481d`; some record review-code dirtiness. Extraction/adapter/evaluator logic was never modified.

**Tracked-tree reproduction, isolated from original measurements**

```bash
mkdir -p /tmp/findoclens-review-clean-20261022
git archive 3695030 | tar -x -C /tmp/findoclens-review-clean-20261022
```

Copied only cached `benchmark/data/{elecom_p9,daiwabo_p10}/{original.pdf,download.json}` and the cached OMRON failure metadata into that tree. For Git metadata reads, a `.git` text pointer referenced the local repository; no writes to that repository were made by the isolated tests. In the isolated tree, using the absolute native interpreter path:

```bash
python -m benchmark.dataset --offline
python -m benchmark.adversarial --materialize
PY=/absolute/path/to/.venv/bin/python bash run_demo.sh independent_clean_initial
python -m benchmark.raster_variants
```

Original results: selected sources/controls reconstructed; the demo failed on a missing issuer raster; the raster command refused because its tracked manifest already existed. Logs: `clean_dataset_initial.log`, `clean_controls_initial.log`, `clean_demo_initial.log`, `clean_raster_initial.log`.

Copied the five repair files into the isolated tree, then ran:

```bash
PY=/absolute/path/to/.venv/bin/python bash run_demo.sh independent_clean_fixed
python scripts/contract_report.py fin1
python scripts/make_results.py \
  --set v2=fin1 --set native_v2=fin1 --set native_grid=fin1 \
  --set docling_cmtrue=fin1 --set docling_cmfalse=fin1 --set docling_rapidocr=fin1 \
  --set docling_regions=fin1 --set docling_rapidocr_medium=fin1 --set auto=fin1 \
  --before native_grid=int1
python -m benchmark.raster_variants
```

All complete successfully. Logs: `clean_demo_fixed.log`, `direct_contract_fixed2.log`, `direct_results_fixed2.log`, `raster_cli_fixed.log`. The demo used all three native backends across all manifests; its viewer intentionally contains only the ten hard-coded display pages. Result generators write only inside the isolated tree. The original direct contract command's import failure is retained in `contracts_fin1.log`; an additional attempt before the fixed scripts were copied is retained in `direct_contract_fixed.log`. The direct results CLI `--help` check is in `results_cli_fixed.log`.

**Review modifications**

Existing code changes: only `benchmark/raster_variants.py`, `run_demo.sh`, `scripts/contract_report.py`, `scripts/make_results.py`, and new `tests/test_raster_reproduction.py`, committed as `fb8481d`. Everything else added by this review is a report, reproducible probe, log, or separately named run artifact. Known parser/evaluator defects are documented, not patched or rescored into the original measurements.
