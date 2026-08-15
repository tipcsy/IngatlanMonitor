#!/bin/bash
set -e

STATE=/app/ingatlan/state.json
[ -f "$STATE" ] || echo '{"processed_ids": []}' > "$STATE"

# Env vars írása .env fájlba — a cron nem örökli a Docker környezetet.
# Alapértelmezést itt SZÁNDÉKOSAN nem adunk: a titkok a projekt .env fájljából
# jönnek a compose-on keresztül. Ha hiányoznak, a konténer hangosan elszáll,
# nem pedig csendben, rossz beállításokkal fut tovább.
: "${DB_PASSWORD:?hianyzik - add meg a projekt .env fajljaban}"
: "${DB_HOST:?hianyzik - add meg a projekt .env fajljaban}"

umask 077
cat > /app/ingatlan/.env << EOF
TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
OLLAMA_URL=${OLLAMA_URL}
OLLAMA_MODEL=${OLLAMA_MODEL}
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT:-3306}
DB_USER=${DB_USER:-ingatlan}
DB_PASSWORD=${DB_PASSWORD}
DB_NAME=${DB_NAME:-ingatlan}
EOF

touch /var/log/cron.log
exec cron -f
