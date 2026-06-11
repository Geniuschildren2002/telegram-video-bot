# 🎬 Telegram Video Downloader Bot

YouTube va Instagram videolarini yuklab beruvchi **ko'p foydalanuvchili** Telegram bot.

## ✨ Xususiyatlar

- 🎬 **YouTube** — video, shorts, live
- 📸 **Instagram** — post, reel, tv
- 👥 **Ko'p foydalanuvchi** — cheksiz
- ⚡ **Rate limiting** — minutiga 5 ta so'rov
- 📊 **Admin statistikasi** — `/stats`
- 🗃️ **SQLite** — foydalanuvchilar va yuklashlar tarixi
- 🔄 **Progress xabarlari** — real-time holat
- 🧹 **Avtomatik tozalash** — fayllar yuborilgach o'chiriladi

---

## 🚀 O'rnatish va ishga tushirish

### 1. Loyihani klonlash

```bash
cd telegram-video-bot
```

### 2. Virtual muhit yaratish (tavsiya etiladi)

```bash
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
# yoki
venv\Scripts\activate      # Windows
```

### 3. Kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt
```

> `yt-dlp` uchun `ffmpeg` ham o'rnatilgan bo'lishi kerak:
> ```bash
> # macOS
> brew install ffmpeg
> # Ubuntu/Debian
> sudo apt install ffmpeg
> ```

### 4. Bot tokenini olish

1. Telegram'da [@BotFather](https://t.me/BotFather) ga o'ting
2. `/newbot` buyrug'ini yuboring
3. Bot nomini va username ni kiriting
4. Olingan tokenni nusxalab oling

### 5. `.env` faylini sozlash

```bash
cp .env.example .env
```

`.env` faylini muharrir bilan oching va to'ldiring:

```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_ID=123456789       # Sizning Telegram IDingiz (@userinfobot dan bilib oling)
MAX_FILE_SIZE_MB=50
DOWNLOAD_DIR=downloads
RATE_LIMIT=5
```

> Telegram ID ni bilish uchun: [@userinfobot](https://t.me/userinfobot) ga `/start` yuboring.

### 6. Botni ishga tushirish

```bash
python bot.py
```

---

## 📁 Loyiha tuzilmasi

```
telegram-video-bot/
├── bot.py           # Asosiy bot (handlerlar, logika)
├── downloader.py    # yt-dlp yordamida video yuklash
├── database.py      # SQLite ma'lumotlar bazasi
├── config.py        # Sozlamalar (.env o'qish)
├── requirements.txt # Python kutubxonalari
├── .env.example     # Token shablon fayli
├── .env             # Sizning tokeningiz (git ga qo'shmang!)
├── downloads/       # Vaqtinchalik fayllar papkasi (avto-yaratilaadi)
└── bot.db           # SQLite bazasi (avto-yaratilaadi)
```

---

## 💬 Bot buyruqlari

| Buyruq | Tavsif |
|--------|--------|
| `/start` | Botni boshlash |
| `/help` | Yordam xabari |
| `/stats` | Statistika (faqat admin) |
| `<URL>` | Video yuklab olish |

---

## ☁️ Server (VPS) da ishlatish (ixtiyoriy)

Agar botni doimiy ishlatmoqchi bo'lsangiz, `systemd` service yarating:

```ini
# /etc/systemd/system/videobot.service
[Unit]
Description=Telegram Video Downloader Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/telegram-video-bot
ExecStart=/path/to/venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable videobot
sudo systemctl start videobot
sudo systemctl status videobot
```

---

## ⚠️ Eslatmalar

- **Private** Instagram postlari yuklab bo'lmaydi
- Telegram bepul botlarda fayl hajmi **50 MB** ga cheklangan
- Instagram vaqti-vaqti bilan bot so'rovlarini bloklashi mumkin
- YouTube **age-restricted** videolar uchun cookies kerak bo'lishi mumkin

---

## 📄 Litsenziya

MIT License
