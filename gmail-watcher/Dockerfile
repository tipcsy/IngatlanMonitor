FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends cron \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/ingatlan

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/ingatlan

# RULES.md a konténer gyökerébe kell (BASE_DIR.parent = /app)
RUN cp /app/ingatlan/RULES.md /app/RULES.md

# Adatbázis mappa
ENV DATA_DIR=/app/data

# Cron job: 30 percenként fut
RUN echo "PATH=/usr/local/bin:/usr/bin:/bin" > /etc/cron.d/ingatlan \
    && echo "*/30 * * * * root cd /app/ingatlan && python gmail_watcher.py >> /var/log/cron.log 2>&1" \
    >> /etc/cron.d/ingatlan \
    && chmod 0644 /etc/cron.d/ingatlan

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
