#!/bin/bash
cd /home/ubuntu/apps/fazri-analyzer/backend/migrations
source ../venv/bin/activate
while true; do
    echo "$(date): Running realtime update..."
    python3 simple_zone_migration3.py
    echo "$(date): Sleeping 5 minutes..."
    sleep 300
done