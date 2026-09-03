#!/bin/bash
# Ifcoder Userbot To'xtatish Skripti

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

PID_FILE="tmp/userbot.pid"
STOPPED=0

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "🛑 Userbot to'xtatilmoqda (PID: $PID)..."
        kill "$PID" 2>/dev/null
        sleep 2
        if ps -p "$PID" > /dev/null 2>&1; then
            kill -9 "$PID" 2>/dev/null
        fi
        STOPPED=1
    fi
    rm -f "$PID_FILE"
fi

PIDS=$(pgrep -f "manage.py run_userbot")
if [ -n "$PIDS" ]; then
    echo "🛑 Fonda qolgan Userbot jarayonlari to'xtatilmoqda..."
    pkill -f "manage.py run_userbot"
    STOPPED=1
fi

if [ $STOPPED -eq 1 ]; then
    echo "✅ Userbot muvaffaqiyatli to'xtatildi."
else
    echo "ℹ️ Ishlayotgan Userbot topilmadi."
fi
