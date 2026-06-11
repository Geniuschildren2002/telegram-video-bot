#!/usr/bin/env bash
# ============================================================
# Telegram Video Downloader Bot — Ishga tushirish skripti
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Virtual muhitni faollashtirish
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "❌ venv topilmadi! Avval: python3 -m venv venv && pip install -r requirements.txt"
    exit 1
fi

# bgutil PO Token serveri — YouTube uchun zarur
BGUTIL_DIR="$SCRIPT_DIR/bgutil-server/server"
BGUTIL_PORT=4416

start_bgutil() {
    if curl -s "http://127.0.0.1:$BGUTIL_PORT/ping" > /dev/null 2>&1; then
        echo "✅ bgutil server allaqachon ishlayapti (port $BGUTIL_PORT)"
    else
        echo "🚀 bgutil PO Token serveri ishga tushmoqda..."
        if [ -f "$BGUTIL_DIR/build/main.js" ]; then
            node "$BGUTIL_DIR/build/main.js" > /tmp/bgutil.log 2>&1 &
            BGUTIL_PID=$!
            sleep 2
            if curl -s "http://127.0.0.1:$BGUTIL_PORT/ping" > /dev/null 2>&1; then
                echo "✅ bgutil server ishga tushdi (PID: $BGUTIL_PID)"
            else
                echo "⚠️  bgutil server ishga tushmadi — log: /tmp/bgutil.log"
            fi
        else
            echo "⚠️  bgutil topilmadi. YouTube ba'zi videolar uchun ishlamasligi mumkin."
        fi
    fi
}

# Cleanup fanlksiyasi
cleanup() {
    echo ""
    echo "🛑 Bot to'xtatilmoqda..."
    # bgutil serverini to'xtatish (agar biz ishga tushirgan bo'lsak)
    if [ -n "$BGUTIL_PID" ]; then
        kill "$BGUTIL_PID" 2>/dev/null || true
        echo "✅ bgutil server to'xtatildi"
    fi
    exit 0
}
trap cleanup SIGINT SIGTERM

start_bgutil

echo "🤖 Bot ishga tushmoqda..."
python bot.py
