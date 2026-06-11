#!/usr/bin/env bash
# Serverlar/Docker uchun ishga tushirish skripti

set -e

# bgutil PO Token serverini fonga yuborish
echo "🚀 bgutil PO Token serveri ishga tushmoqda..."
node /app/bgutil-server/build/main.js &
BGUTIL_PID=$!

# Botni ishga tushirish
echo "🤖 Telegram Bot ishga tushmoqda..."
python -u bot.py
