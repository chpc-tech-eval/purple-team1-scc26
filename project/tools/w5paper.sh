#!/usr/bin/env bash
# Regenerate the Week-5 paper/poster outputs from every committed run directory.
#
#   project/tools/w5paper.sh                 # all runs -> paper/figures/week5/
#   project/tools/w5paper.sh <run-dir> ...   # only these runs
#
# A run directory is project/runs/<run-id>/ with a manifest.yaml that passes
# `w5run.py validate --stage final`. Writes metrics.tex/.md, phases.pdf/.png and
# one timeline-<run-id>.pdf/.png per run (see w5figures.py). paper/main.tex picks
# them up automatically; with no runs it shows "no run recorded yet", never
# placeholder numbers.
set -euo pipefail

root=$(cd "$(dirname "$0")/../.." && pwd)
cd "$root"
out=paper/figures/week5
py=${PYTHON:-python3}

if [ "$#" -gt 0 ]; then
  runs=("$@")
else
  runs=()
  for m in project/runs/*/manifest.yaml; do
    [ -e "$m" ] || continue
    case "$m" in project/runs/_template/*) continue ;; esac
    runs+=("$(dirname "$m")")
  done
fi

if [ "${#runs[@]}" -eq 0 ]; then
  echo "No run directories with a manifest.yaml under project/runs/; nothing to render." >&2
  echo "Preview with synthetic data: $py project/tools/w5figures.py project/tools/testdata/example-run -o /tmp/w5preview" >&2
  exit 0
fi

for r in "${runs[@]}"; do
  "$py" project/tools/w5run.py validate "$r/manifest.yaml" --stage final
done
"$py" project/tools/w5figures.py "${runs[@]}" -o "$out"
echo "Commit $out/ with the run directories it was generated from (provenance: paper/figures/README.md)."
