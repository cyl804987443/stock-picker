#!/usr/bin/env bash
# Create data directory for SQLite database
mkdir -p data
# Start the app
uvicorn main:app --host 0.0.0.0 --port $PORT
