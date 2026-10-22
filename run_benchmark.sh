#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
BENCHMARK_PYTHON="${BENCHMARK_PYTHON:-.venv/bin/python}"
BENCHMARK_RUN_ID="${1:-$(date -u +%Y%m%dT%H%M%SZ)}"
if [[ "${BENCHMARK_OFFLINE:-0}" == "1" ]]; then
  "$BENCHMARK_PYTHON" -m benchmark.dataset --offline
else
  "$BENCHMARK_PYTHON" -m benchmark.dataset
fi
"$BENCHMARK_PYTHON" -m benchmark.adversarial --materialize
"$BENCHMARK_PYTHON" -m benchmark.validate
"$BENCHMARK_PYTHON" -m benchmark.check
"$BENCHMARK_PYTHON" -m benchmark.run --run-id "independent_${BENCHMARK_RUN_ID}"
"$BENCHMARK_PYTHON" -m benchmark.run --manifest benchmark/adversarial_manifest.jsonl --run-id "adversarial_${BENCHMARK_RUN_ID}"
"$BENCHMARK_PYTHON" -m benchmark.review --failures "benchmark/reports/v2_independent_${BENCHMARK_RUN_ID}.json"
"$BENCHMARK_PYTHON" -m benchmark.report --summary "benchmark/reports/v2_independent_${BENCHMARK_RUN_ID}.json" "benchmark/reports/v2_adversarial_${BENCHMARK_RUN_ID}.json"
