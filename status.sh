#!/bin/bash
# Ifcoder Userbot Holatini Tekshirish Skripti

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

PID_FILE="tmp/userbot.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "🟢 Userbot FAOL (PID: $PID)"
        echo "--- Oxirgi 10 ta log yozuvi ---"
        tail -n 10 tmp/userbot.log 2>/dev/null
        exit 0
    fi
fi

PIDS=$(pgrep -f "manage.py run_userbot")
if [ -n "$PIDS" ]; then
    echo "🟢 Userbot FAOL (PID(lar): $PIDS)"
    echo "--- Oxirgi 10 ta log yozuvi ---"
    tail -n 10 tmp/userbot.log 2>/dev/null
else
    echo "🔴 Userbot NOFAOL (ishlamayapti)"
fi
