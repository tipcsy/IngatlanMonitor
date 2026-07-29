#!/bin/bash
set -e

STATE=/app/ingatlan/state.json
[ -f "$STATE" ] || echo '{"processed_ids": []}' > "$STATE"

# Env vars írása .env fájlba — a cron nem örökli a Docker környezetet
cat > /app/ingatlan/.env << EOF
TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
OLLAMA_URL=${OLLAMA_URL:-http://192.168.31.104:30068}
OLLAMA_MODEL=${OLLAMA_MODEL:-minimax-m3:cloud}
DB_HOST=${DB_HOST:-192.168.31.104}
DB_PORT=${DB_PORT:-3306}
DB_USER=${DB_USER:-root}
DB_PASSWORD=${DB_PASSWORD:-Pagoda}
DB_NAME=${DB_NAME:-ingatlan}
EOF

touch /var/log/cron.log
exec cron -f
