#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo 'Create .venv and install requirements first; see README.md.'
  exit 1
fi
exec .venv/bin/python -m rahamasin "$@"
