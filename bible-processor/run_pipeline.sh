#!/usr/bin/env bash
#
# Fase 1 pipeline: candidates -> classify -> sanitize.
# Run this to (re)build promesas.db from scratch.
#
#   ./run_pipeline.sh            # full run
#   ./run_pipeline.sh --limit 50 # smoke test on the first 50 candidates
#
set -euo pipefail
cd "$(dirname "$0")"

EXTRA=("${@:-}")

echo "[1/3] Filtering candidate verses..."
python3 candidates.py

echo "[2/3] Classifying candidates with Ollama..."
python3 classify.py "${EXTRA[@]}"

echo "[3/3] Sanitizing tags..."
python3 sanitize.py --db promesas.db

echo "Pipeline complete. promesas.db is ready."
