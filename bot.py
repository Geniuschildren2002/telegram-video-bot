"""
Telegram Video Downloader Bot
YouTube va Instagram videolarini yuklab beruvchi ko'p foydalanuvchili bot.
"""

import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

import config
import database as db
from downloader import (
    detect_platform,
    download_video,
    cleanup_file,
    DownloadError,
    FileTooLargeError,
)

# Logging sozlamalari
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Rate limiting: {user_id: [timestamp, ...]}
_rate_cache: dict[int, list[datetime]] = defaultdict(list)


# ─────────────────────────── Helpers ────────────────────────────

def check_rate_limit(user_id: int) -> bool:
    """True — so'rov qabul qilindi. False — limit oshdi."""
    now = datetime.utcnow()
    window = timedelta(minutes=1)
    timestamps = [t for t in _rate_cache[user_id] if now - t < window]
    _rate_cache[user_id] = timestamps
    if len(timestamps) >= config.RATE_LIMIT:
        return False
    _rate_cache[user_id].append(now)
    return True


def extract_url(text: str) -> str | None:
    """Matndan birinchi URL ni ajratib olish."""
    pattern = re.compile(r"https?://[^\s]+", re.IGNORECASE)
    match = pattern.search(text)
    return match.group(0) if match else None


def platform_emoji(platform: str) -> str:
    return "🎬" if platform == "YouTube" else "📸"


# ─────────────────────────── Handlers ────────────────────────────

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Botni /start buyrug'i bilan boshlash."""
    user = update.effective_user
    await db.register_user(user.id, user.username, user.first_name)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Yordam", callback_data="help"),
         InlineKeyboardButton("📊 Statistika", callback_data="stats")],
    ])

    await update.message.reply_text(
        f"👋 Assalomu alaykum, <b>{user.first_name}</b>!\n\n"
        "🤖 <b>Video Downloader Bot</b> ga xush kelibsiz!\n\n"
        "📥 <b>Qo'llash:</b>\n"
        "Shunchaki YouTube yoki Instagram linkini yuboring — men videoni yuklab beraman!\n\n"
        "✅ <b>Qo'llab-quvvatlanadigan platformalar:</b>\n"
        "🎬 YouTube (video, shorts, live)\n"
        "📸 Instagram (post, reel, tv)\n\n"
        f"⚡ Limitlar: minutiga <b>{config.RATE_LIMIT} ta</b> so'rov\n"
        f"📦 Maks. hajm: <b>{config.MAX_FILE_SIZE_MB} MB</b>",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Yordam xabari."""
    text = (
        "📖 <b>Yordam</b>\n\n"
        "<b>Qanday ishlatiladi?</b>\n"
        "YouTube yoki Instagram linkini yuboring.\n"
        "Bot avtomatik ravishda videoni yuklab, sizga yuboradi.\n\n"
        "<b>Buyruqlar:</b>\n"
        "/start — Botni qayta ishga tushirish\n"
        "/help — Ushbu yordam xabari\n"
        "/stats — Statistika (faqat admin)\n\n"
        "<b>Misol linklar:</b>\n"
        "• <code>https://youtube.com/watch?v=xxxxx</code>\n"
        "• <code>https://youtu.be/xxxxx</code>\n"
        "• <code>https://youtube.com/shorts/xxxxx</code>\n"
        "• <code>https://instagram.com/p/xxxxx/</code>\n"
        "• <code>https://instagram.com/reel/xxxxx/</code>\n\n"
        "⚠️ <b>Eslatma:</b> Maxfiy (private) postlar yuklab bo'lmaydi."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin uchun statistika."""
    user = update.effective_user
    if config.ADMIN_ID and user.id != config.ADMIN_ID:
        await update.message.reply_text("⛔ Bu buyruq faqat admin uchun.")
        return

    stats = await db.get_stats()
    platforms = "\n".join(
        f"  {platform_emoji(p)} {p}: <b>{cnt}</b> ta"
        for p, cnt in stats["platforms"]
    ) or "  Hali yuklab olinmagan"

    top = "\n".join(
        f"  {i+1}. {name} (@{uname or 'noma'}) — <b>{dl}</b> ta"
        for i, (name, uname, dl) in enumerate(stats["top_users"])
    ) or "  Ma'lumot yo'q"

    text = (
        "📊 <b>Bot Statistikasi</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"📥 Jami yuklashlar: <b>{stats['total_downloads']}</b>\n\n"
        f"🌐 <b>Platformalar bo'yicha:</b>\n{platforms}\n\n"
        f"🏆 <b>Top 5 foydalanuvchi:</b>\n{top}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def url_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xabar ichidagi URL ni ushlab yuklab olish."""
    user = update.effective_user
    message = update.message

    # Rate limit tekshirish
    if not check_rate_limit(user.id):
        await message.reply_text(
            f"⏳ Siz juda tez so'rov yuboryapsiz!\n"
            f"Iltimos, 1 daqiqa kutib turing. (Limit: {config.RATE_LIMIT} ta/daqiqa)"
        )
        return

    # URL ni topish
    url = extract_url(message.text or "")
    if not url:
        await message.reply_text("🔗 Iltimos, to'g'ri video linkini yuboring.")
        return

    # Platformani aniqlash
    platform = detect_platform(url)
    if not platform:
        await message.reply_text(
            "❌ Faqat <b>YouTube</b> va <b>Instagram</b> linklari qabul qilinadi.\n\n"
            "Yordam uchun /help ni yuboring.",
            parse_mode=ParseMode.HTML,
        )
        return

    # Foydalanuvchini ro'yxatdan o'tkazish
    await db.register_user(user.id, user.username, user.first_name)

    # "Yozmoqda..." holati
    await context.bot.send_chat_action(message.chat_id, ChatAction.TYPING)

    # Progress xabari
    status_msg = await message.reply_text(
        f"{platform_emoji(platform)} <b>{platform}</b> dan yuklanmoqda...\n"
        "⏳ Iltimos, kuting...",
        parse_mode=ParseMode.HTML,
    )

    file_path: Path | None = None
    try:
        # Upload animatsiyasi
        await context.bot.send_chat_action(message.chat_id, ChatAction.UPLOAD_VIDEO)

        # Yuklab olish
        file_path = await download_video(url, platform)

        # Status xabarini yangilash
        await status_msg.edit_text(
            f"{platform_emoji(platform)} Video topildi! Telegramga yuborilmoqda... 📤",
            parse_mode=ParseMode.HTML,
        )

        # Videoni yuborish
        with open(file_path, "rb") as video_file:
            await message.reply_video(
                video=video_file,
                caption=(
                    f"{platform_emoji(platform)} <b>{platform}</b> orqali yuklab olindi\n"
                    f"🤖 @{context.bot.username}"
                ),
                parse_mode=ParseMode.HTML,
                supports_streaming=True,
                write_timeout=120,
                read_timeout=60,
            )

        # Statistikani yangilash
        await db.increment_downloads(user.id, url, platform)
        await status_msg.delete()
        logger.info("✅ Yuklandi: user=%s platform=%s", user.id, platform)

    except FileTooLargeError as e:
        await status_msg.edit_text(
            f"⚠️ Video hajmi juda katta ({e.size_mb:.0f} MB).\n"
            f"Maksimal ruxsat etilgan: {config.MAX_FILE_SIZE_MB} MB\n\n"
            "Iltimos, qisqaroq yoki pastroq sifatli videoni sinab ko'ring."
        )
        logger.warning("⚠️ Fayl katta: user=%s size=%.1f MB", user.id, e.size_mb)

    except DownloadError as e:
        await status_msg.edit_text(
            f"❌ <b>Yuklab bo'lmadi</b>\n\n"
            f"{str(e)}\n\n"
            "💡 <i>Sabab:</i> Private post, noto'g'ri link yoki vaqtinchalik xato bo'lishi mumkin.",
            parse_mode=ParseMode.HTML,
        )
        logger.error("❌ DownloadError: user=%s error=%s", user.id, e)

    except telegram.error.NetworkError as e:
        if "Payload Too Large" in str(e) or "File is too large" in str(e):
            await status_msg.edit_text(
                "⚠️ Fayl hajmi 50 MB dan katta!\n"
                "Telegram bepul botlarga 50 MB gacha video yuborishga ruxsat beradi xolos.\n"
                "Iltimos, kichikroq video tanlang."
            )
            logger.warning("⚠️ Telegram 50MB limit oshdi: user=%s", user.id)
        else:
            await status_msg.edit_text("🚫 Tarmoq xatosi (yuklashda). Iltimos, qayta urining.")
            logger.error("❌ Telegram NetworkError: %s", getattr(e, "message", str(e)))

    except telegram.error.BadRequest as e:
        if "File is too large" in str(e):
             await status_msg.edit_text("⚠️ Fayl hajmi 50 MB dan katta (Telegram limiti).")
        else:
             await status_msg.edit_text(f"🚫 Xato: {str(e)}")
        logger.error("❌ BadRequest: %s", str(e))

    except Exception as e:
        await status_msg.edit_text(
            "🚫 Kutilmagan xato yuz berdi. Iltimos, keyinroq qayta urining."
        )
        logger.exception("🚫 Kutilmagan xato: user=%s", user.id)

    finally:
        if file_path:
            cleanup_file(file_path)


async def unknown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Noma'lum matn yoki buyruq."""
    await update.message.reply_text(
        "🔗 YouTube yoki Instagram linkini yuboring.\n"
        "Yordam uchun /help ni bosing."
    )


# ─────────────────────────── Main ────────────────────────────

async def _post_init(app: Application) -> None:
    """Bot ishga tushgandan keyin ma'lumotlar bazasini sozlash."""
    await db.init_db()
    logger.info("✅ Ma'lumotlar bazasi tayyor.")


def main() -> None:
    """Botni ishga tushirish."""
    logger.info("🚀 Bot ishga tushmoqda...")

    # Application yaratish (post_init orqali DB ishga tushadi)
    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(_post_init)
        .build()
    )

    # Handlerlarni qo'shish
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("stats", stats_handler))

    # URL bor xabarlarni ushlab olish
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"https?://"),
            url_handler,
        )
    )

    # Boshqa barcha matnlar
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_handler))

    logger.info("✅ Bot ishlayapti. To'xtatish uchun Ctrl+C bosing.")
    # run_polling o'zi event loop boshqaradi
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
