FROM python:3.11-slim

WORKDIR /app/ingatlan

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/ingatlan

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gmail_watcher.py"]
