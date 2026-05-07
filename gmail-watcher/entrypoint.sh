#!/bin/bash
set -e

STATE=/app/ingatlan/state.json
[ -f "$STATE" ] || echo '{"processed_ids": []}' > "$STATE"

# Env vars írása .env fájlba — a cron nem örökli a Docker környezetet
cat > /app/ingatlan/.env << EOF
TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
OLLAMA_URL=${OLLAMA_URL:-http://192.168.31.104:30068}
OLLAMA_MODEL=${OLLAMA_MODEL:-qwen3.5:cloud}
EOF

touch /var/log/cron.log
exec cron -f
