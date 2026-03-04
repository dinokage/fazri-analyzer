#!/bin/bash
# Runs zone updater inside the fazri-api Docker container every 5 minutes
CONTAINER="fazri-api"

while true; do
    echo "$(date): Running realtime update..."
    docker exec "$CONTAINER" python3 /app/migrations/simple_zone_migration3.py
    echo "$(date): Sleeping 5 minutes..."
    sleep 300
done