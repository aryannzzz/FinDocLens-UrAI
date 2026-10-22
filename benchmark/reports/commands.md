# Reproduction and execution audit

Final end-to-end command, completed successfully from implementation commit `7369ec36197b7adc425981833e679c8e445aa358`:

```bash
BENCHMARK_OFFLINE=1 bash run_benchmark.sh final-v1
```

The exact invoked subcommands are in `run_benchmark.sh`; stdout/stderr are preserved in `end_to_end.txt`. This used original downloaded bytes in the local cache, rebuilt all 13 controls against their frozen reference/input hashes, validated evidence and split isolation, passed 39 root tests (including the wrapper executing all 25 unchanged v2 tests), and ran one cold plus three same-process warm trials for each of 16 available documents/controls. OMRON remains one explicitly unavailable candidate. Raw predictions were identical across the four trials of each available input; `prediction_stability.json` records every digest.

Final summaries:

- `v2_independent_final-v1.json`: original development page, two independent issuer pages, one unavailable source.
- `v2_adversarial_final-v1.json`: 13 synthetic development controls.
- `measured.md`: per-document measured scores, cold/warm timing, CPU RSS, failures, limitations and human review gates.
- `tests.json` / `tests.txt`: command, elapsed time, commit, test-file digests and pass/fail transcript.

Earlier commands actually run during implementation:

```bash
python -m benchmark.dataset
.venv/bin/python -m benchmark.dataset --offline
.venv/bin/python -m benchmark.annotate --document original
.venv/bin/python -m benchmark.annotate --document elecom_p9
.venv/bin/python -m benchmark.annotate --document daiwabo_p10
.venv/bin/python -m benchmark.adversarial
.venv/bin/python -m benchmark.adversarial --materialize
.venv/bin/python -m benchmark.run --run-id independent-v1
.venv/bin/python -m benchmark.run --run-id independent-v1 --resume
.venv/bin/python -m benchmark.run --manifest benchmark/adversarial_manifest.jsonl --run-id adversarial-v1
.venv/bin/python -m benchmark.check
.venv/bin/python -m benchmark.validate
```

An initial sandbox network probe failed DNS resolution. Downloads then ran with approved network access. ELECOM and Daiwabo original response headers, timestamps, byte counts and hashes are in `../sources/`; the retry record in `../sources/omron_p13_access_attempts.json` preserves the actual HTTP 403 access failure. Offline manifest acquisition timestamps denote cache/availability checks, not new HTTP requests. Full original PDFs remain local-only pending redistribution review.

The first Daiwabo acquisition saved its PDF but failed JSON serialization on image bytes. The acquisition code was corrected to exclude image payloads from native text metadata, and the source bytes were retained. The first independent-v1 summary writer had a missing dictionary key; all completed trial artifacts were retained and `--resume` rebuilt the summary without rerunning inference. A control-materialization check detected generator drift for nested headers; the generator was restored to match the already frozen reference, and every input hash then reproduced. No gold labels changed. Preliminary v1 trials ran during uncommitted development and are retained as exploratory evidence with code digests; the final committed-code trials are the reproducible results used in `measured.md`.

The initial frozen tests were executed in a temporary copy using `python -m unittest discover -s tests -v`; their complete 25-test transcript is `frozen_tests_initial.txt`. The root suite performs that same isolation on every run. `nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader` returned exit code 9 and could not communicate with the driver. GPU memory was not measured, and no model frameworks, system Python, CUDA or drivers were installed or changed. The environment inherited already installed packages through a virtualenv; exact versions are recorded in each run.
