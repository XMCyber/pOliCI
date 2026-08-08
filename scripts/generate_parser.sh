#!/usr/bin/env bash
# Generate ANTLR Python parser from grammar. Requires Java and antlr4-tools in venv.
set -e
cd "$(dirname "$0")/.."
mkdir -p grammar/gen grammar/gen/grammar
# Prefer env, fallback to .venv (uv)
if [ -x "./env/bin/antlr4" ]; then
  ANTLR4=./env/bin/antlr4
elif [ -x "./.venv/bin/antlr4" ]; then
  ANTLR4=./.venv/bin/antlr4
else
  echo "Install antlr4-tools in a venv: uv sync --extra dev  (or pip install antlr4-tools in env/)"
  exit 1
fi
$ANTLR4 -Dlanguage=Python3 -visitor -o grammar/gen grammar/OciPolicy.g4
# ANTLR may create grammar/gen/grammar/ when grammar is in grammar/; ensure files are there for imports
if [ -f grammar/gen/OciPolicyLexer.py ] && [ ! -f grammar/gen/grammar/OciPolicyLexer.py ]; then
  mv grammar/gen/OciPolicy*.py grammar/gen/grammar/ 2>/dev/null || true
  mv grammar/gen/OciPolicy*.tokens grammar/gen/grammar/ 2>/dev/null || true
  mv grammar/gen/OciPolicy*.interp grammar/gen/grammar/ 2>/dev/null || true
fi
echo "Generated parser in grammar/gen/grammar/"
