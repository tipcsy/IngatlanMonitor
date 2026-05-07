#!/bin/bash
set -e

STATE=/app/ingatlan/state.json
[ -f "$STATE" ] || echo '{"processed_ids": []}' > "$STATE"

exec python "$@"
