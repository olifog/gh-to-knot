#!/bin/sh
INTERVAL="${SYNC_INTERVAL:-3600}"

while true; do
    python3 /app/sync.py
    sleep "$INTERVAL"
done
