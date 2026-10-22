#!/usr/bin/env bash
# Run one backend through the benchmark harness on the main (original/ELECOM/Daiwabo/OMRON), adversarial and raster manifests.
#   scripts/run_integration.sh BACKEND RUN_ID [PYTHON] [WARM_MAIN] [WARM_ADV] [WARM_RASTER]
# BACKEND: v2 native_v2 native_grid docling_cmtrue docling_cmfalse docling_rapidocr docling_regions docling_rapidocr_medium
# Model backends need PYTHON=.venv-docling/bin/python. ONLY=raster|main|adv restricts to one manifest. Run IDs are create-only.
set -euo pipefail
cd "$(dirname "$0")/.."
B="$1"; ID="$2"; PY="${3:-.venv/bin/python}"; WM="${4:-3}"; WA="${5:-3}"; WR="${6:-3}"
export HF_HOME="${HF_HOME:-$PWD/.cache/hf}" HF_HUB_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD"
EP=(); [[ "$B" != "v2" ]] && EP=(--entrypoint "adapters.$B:extract")
run() { "$PY" -m benchmark.run --backend "$B" "${EP[@]}" --manifest "$1" --run-id "${ID}_$2" --warm "$3" --timeout 3000; }
[[ -z "${ONLY:-}" || "$ONLY" == main   ]] && run benchmark/manifest.jsonl main "$WM"
[[ -z "${ONLY:-}" || "$ONLY" == adv    ]] && run benchmark/adversarial_manifest.jsonl adv "$WA"
[[ -z "${ONLY:-}" || "$ONLY" == raster ]] && run benchmark/raster_manifest.jsonl raster "$WR"
exit 0
