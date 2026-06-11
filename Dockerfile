# 1-bosqich: Node.js server qurish (bgutil)
FROM node:20-alpine AS node-builder
WORKDIR /app
RUN apk add --no-cache git
# bgutil klonlash
RUN git clone --depth=1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git
WORKDIR /app/bgutil-ytdlp-pot-provider/server
RUN npm ci && npx tsc

# 2-bosqich: Python bot va unga Node js ulanishi
FROM python:3.11-slim

# System paketlari (ffmpeg video birlashtirish uchun, nodejs yt-dlp js challenge uchun)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# bgutil serverni ko'chirish
COPY --from=node-builder /app/bgutil-ytdlp-pot-provider/server /app/bgutil-server

# Python kutubxonalari
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Loyiha fayllari
COPY bot.py .
COPY config.py .
COPY database.py .
COPY downloader.py .
COPY start_prod.sh .

RUN chmod +x start_prod.sh

# Ishga tushirish (start_prod.sh ham botni, ham nodejsni yoqadi)
CMD ["./start_prod.sh"]
