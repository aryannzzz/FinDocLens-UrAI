#!/usr/bin/env bash
# Track-B demo. Native steps need only PyMuPDF; model steps need .venv-docling (docs/SETUP_MODELS.md) and skip otherwise.
set -euo pipefail
cd "$(dirname "$0")"
python -m unittest discover -s baseline_v2/tests -p 'test_*.py' -q          # frozen original regression
python -m unittest discover -s tests -q                                       # track-B tests (holdout tests skip if PDFs absent)
python -m findoclens parse baseline_v2/source.pdf --page 0 --backend auto --format json,md,png --out runs/demo
for spec in "data/pdfs/elecom.pdf 8" "data/pdfs/daiwabo.pdf 9"; do
  set -- $spec
  if [ -f "$1" ]; then python -m findoclens parse "$1" --page "$2" --backend auto --format json,md,png --out runs/demo; fi
done
if [ -x .venv-docling/bin/python ]; then
  python -m findoclens parse baseline_v2/source.pdf --page 0 --backend docling --format json,md --out runs/demo
  python -c "from findoclens.variants import raster_pdf; print(raster_pdf('baseline_v2/source.pdf',0,200,'source'))"
  python -m findoclens parse data/variants/source_raster200.pdf --page 0 --backend auto --format json,md --out runs/demo
else
  echo "[skip] model backends: .venv-docling not found"
fi
