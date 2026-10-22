#!/usr/bin/env bash
# Integrated demo: tests -> native backends on every benchmark page (scored) -> viewer.
#   bash run_demo.sh [RUN_ID]            native backends only (needs PyMuPDF; ~1 min)
#   WITH_MODELS=1 bash run_demo.sh       also Docling + Docling/RapidOCR (needs .venv-docling, see docs/SETUP_MODELS.md; ~15 min on CPU)
# Run ids are create-only; the default is a fresh timestamp. Outputs: runs/<backend>/<doc>/<RUN_ID>_<set>/, benchmark/reports/, viewer/.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PY:-.venv/bin/python}"; [ -x "$PY" ] || PY=python3
RUN="${1:-demo$(date -u +%Y%m%dT%H%M%S)}"
export PYTHONPATH="$PWD" PYTHONDONTWRITEBYTECODE=1

if [ ! -f benchmark/data/elecom_p9/page.pdf ]; then
  echo "[setup] fetching and cutting source pages (OMRON is expected to fail with HTTP 403)"
  "$PY" -m benchmark.dataset || true
fi
# These PDFs are ignored even though their manifests are tracked. Check every
# input on each invocation, including checkouts with only some cached pages.
"$PY" -m benchmark.adversarial --materialize
"$PY" -m benchmark.raster_variants --materialize
"$PY" -m benchmark.validate && "$PY" -m benchmark.check
"$PY" -m unittest discover -s tests -q            # includes the 25 frozen baseline tests in a temp copy

BACKENDS=(v2 native_v2 native_grid)
for b in "${BACKENDS[@]}"; do scripts/run_integration.sh "$b" "$RUN" "$PY" 1 1 1; done
RUNS=(); for b in "${BACKENDS[@]}"; do RUNS+=(--run "$b=$RUN"); done
if [ "${WITH_MODELS:-0}" = 1 ] && [ -x .venv-docling/bin/python ]; then
  for b in docling_cmtrue docling_cmfalse docling_rapidocr; do
    scripts/run_integration.sh "$b" "$RUN" .venv-docling/bin/python 1 1 1; RUNS+=(--run "$b=$RUN")
  done
fi
"$PY" scripts/contract_report.py "$RUN"
"$PY" scripts/build_viewer.py "${RUNS[@]}"
echo "Viewer: open viewer/index.html (local file; no server needed)"
