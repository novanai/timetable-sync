#!/bin/bash

rm -rf "${PROMETHEUS_MULTIPROC_DIR}/*"
mkdir -p "${PROMETHEUS_MULTIPROC_DIR}"

exec uv run granian --interface asgi src.main:app --loop uvloop --workers 4 --host 0.0.0.0 --port 2000
