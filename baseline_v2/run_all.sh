#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python parser_v2.py source.pdf --out output --visualize
python evaluate.py source.pdf --gold tests/gold_rows.tsv --out output/evaluation.json
python verify_evidence.py source.pdf --out output/cross_engine.json
python benchmark.py
python compare_baseline.py
python -m unittest discover -s tests -p 'test_*.py' -v
