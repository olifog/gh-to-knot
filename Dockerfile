FROM python:3.12-slim

RUN apt-get update && apt-get install -y git docker.io && rm -rf /var/lib/apt/lists/*

COPY github-mirror.py /app/sync.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
