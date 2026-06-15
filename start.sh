#!/usr/bin/env bash
# Create data directory if it doesn't exist
mkdir -p /opt/render/project/src/data
# Start the app
uvicorn main:app --host 0.0.0.0 --port $PORT
