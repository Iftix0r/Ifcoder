#!/bin/bash
# Ifcoder Userbot Ishga Tushirish Skripti

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Python interpreter aniqlash
if [ -f "venv/bin/python" ]; then
    PYTHON_BIN="venv/bin/python"
elif command -v python3 &> /dev/null; then
    PYTHON_BIN="python3"
else
    PYTHON_BIN="python"
fi

PID_FILE="tmp/userbot.pid"
LOG_FILE="tmp/userbot.log"
mkdir -p tmp

# Oldingi jarayon ishlayotganligini tekshirish
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "⚠️ Userbot allaqachon fonda ishlamoqda (PID: $PID)"
        exit 0
    else
        rm -f "$PID_FILE"
    fi
fi

PIDS=$(pgrep -f "manage.py run_userbot")
if [ -n "$PIDS" ]; then
    echo "⚠️ Userbot allaqachon fonda ishlamoqda (PID: $PIDS)"
    exit 0
fi

echo "⚡ Userbot fonda ishga tushirilmoqda..."
nohup $PYTHON_BIN manage.py run_userbot > "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo $NEW_PID > "$PID_FILE"

sleep 2
if ps -p "$NEW_PID" > /dev/null 2>&1; then
    echo "✅ Userbot muvaffaqiyatli ishga tushdi! (PID: $NEW_PID)"
    echo "📋 Loglarni ko'rish uchun: tail -f tmp/userbot.log"
else
    echo "❌ Userbot ishga tushishda xatolik yuz berdi. Loglarni ko'ring:"
    cat "$LOG_FILE"
fi
