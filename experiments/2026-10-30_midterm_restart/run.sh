#!/bin/sh
# Existing project environment; reuse its OpenMP library for LightGBM on macOS.
set -eu
task_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(CDPATH= cd -- "$task_dir/../.." && pwd)
python_bin="$repo_dir/research/2026-09-22_plan_support/.venv/bin/python"
if [ "$(uname -s)" = Darwin ]; then
  export DYLD_FALLBACK_LIBRARY_PATH="$repo_dir/research/2026-09-22_plan_support/.venv/lib/python3.12/site-packages/torch/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
fi
script=$1
shift
exec "$python_bin" -u "$task_dir/$script" "$@"
