#!/bin/bash
set -e

cd "$(dirname "$0")"

# Stop any previous Flask process
pkill -f 'python app.py' || true
sleep 1

# Start app in background
nohup python app.py > app.log 2>&1 &
PID=$!

# Save PID
echo $PID > app.pid
echo "Started Flask app with PID: $PID"

# Verify it's running
sleep 2
if kill -0 $PID 2>/dev/null; then
    echo "App is running successfully!"
    exit 0
else
    echo "App failed to start. Check app.log"
    exit 1
fi
