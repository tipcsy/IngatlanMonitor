#!/bin/bash
# Ingatlan Program Docker Runner — cron job script
# Beállítás: crontab -e
#   */30 * * * * /opt/IngatlanMonitor/run-ingatlan-docker.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$PROJECT_DIR/ingatlan-cron.log"

echo "========================================" >> "$LOG_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') — indítás" >> "$LOG_FILE"

cd "$PROJECT_DIR"

if docker compose run --rm ingatlan >> "$LOG_FILE" 2>&1; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') — sikeres futtatás" >> "$LOG_FILE"
else
    EXIT_CODE=$?
    echo "$(date '+%Y-%m-%d %H:%M:%S') — HIBA, exit code: $EXIT_CODE" >> "$LOG_FILE"
    exit $EXIT_CODE
fi
