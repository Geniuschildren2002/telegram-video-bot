import os
import re
import uuid
import asyncio
from pathlib import Path

import yt_dlp

from config import DOWNLOAD_DIR, MAX_FILE_SIZE_BYTES


# URL naqshlari
YOUTUBE_PATTERN = re.compile(
    r"(https?://)?(www\.)?"
    r"(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/live/)"
    r"[\w\-]+",
    re.IGNORECASE,
)
INSTAGRAM_PATTERN = re.compile(
    r"(https?://)?(www\.)?instagram\.com/(p|reel|tv|stories)/[\w\-]+",
    re.IGNORECASE,
)


def detect_platform(url: str) -> str | None:
    """URL platformasini aniqlash."""
    if YOUTUBE_PATTERN.search(url):
        return "YouTube"
    if INSTAGRAM_PATTERN.search(url):
        return "Instagram"
    return None


class DownloadError(Exception):
    """Yuklab olishda xato."""
    pass


class FileTooLargeError(Exception):
    """Fayl hajmi limitdan oshdi."""
    def __init__(self, size_mb: float):
        self.size_mb = size_mb
        super().__init__(f"Fayl hajmi {size_mb:.1f} MB — limitdan oshdi.")


async def download_video(url: str, platform: str) -> Path:
    """
    URLdan video yuklab olish.
    Muvaffaqiyatli bo'lsa — fayl yo'lini qaytaradi.
    Xato bo'lsa — DownloadError yoki FileTooLargeError.
    """
    output_id = uuid.uuid4().hex
    output_template = os.path.join(DOWNLOAD_DIR, f"{output_id}.%(ext)s")

    # Cookies fayli (ixtiyoriy) — brauzerdan eksport qilingan cookies.txt
    cookies_file = "cookies.txt"

    ydl_opts: dict = {
        "outtmpl": output_template,
        "format": _get_format(platform),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "merge_output_format": "mp4",
        "max_filesize": MAX_FILE_SIZE_BYTES,
    }

    # YouTube uchun maxsus sozlamalar
    if platform == "YouTube":
        # YouTube n-challenge va PO Token uchun:
        # 1. Node.js orqali EJS JS challenge solver ishlatiladi
        # 2. bgutil serveri (port 4416) PO Token beradi
        ydl_opts["js_runtimes"] = {"node": {}}
        ydl_opts["remote_components"] = {"ejs:github": ""}
        # Agar cookies.txt mavjud bo'lsa, qo'shimcha ishonchlillik
        if os.path.isfile(cookies_file):
            ydl_opts["cookiefile"] = cookies_file

    # Instagram uchun maxsus sozlamalar
    elif platform == "Instagram":
        ydl_opts["extractor_args"] = {
            "instagram": {"include_ads": ["0"]},
        }
        if os.path.isfile(cookies_file):
            ydl_opts["cookiefile"] = cookies_file

    try:
        loop = asyncio.get_running_loop()
        file_path = await loop.run_in_executor(None, _run_ydl, ydl_opts, url)
        return file_path
    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        if "File is larger than max-filesize" in msg or "maxfilesize" in msg.lower():
            raise FileTooLargeError(MAX_FILE_SIZE_BYTES / 1024 / 1024)
        raise DownloadError(f"Yuklab bo'lmadi: {_clean_error(msg)}")
    except FileTooLargeError:
        raise
    except Exception as e:
        raise DownloadError(f"Kutilmagan xato: {str(e)}")


def _run_ydl(opts: dict, url: str) -> Path:
    """yt-dlp ni sinxron rejimda ishlatish (executor ichida)."""
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # Yuklangan fayl yo'lini topish
        filename = ydl.prepare_filename(info)
        # .mp4 formatga o'zgartirish (merge bo'lgan holat)
        path = Path(filename).with_suffix(".mp4")
        if not path.exists():
            # Agar merge bo'lmagan bo'lsa, asl kengaytmani sinab ko'rish
            path = Path(filename)
        if not path.exists():
            # Papkada yaratilgan faylni qidirish
            folder = Path(filename).parent
            uid = Path(filename).stem.split(".")[0]
            candidates = list(folder.glob(f"{uid}*"))
            if candidates:
                path = candidates[0]
            else:
                raise DownloadError("Fayl topilmadi.")

        # Hajmini tekshirish
        size = path.stat().st_size
        if size > MAX_FILE_SIZE_BYTES:
            path.unlink(missing_ok=True)
            raise FileTooLargeError(size / 1024 / 1024)

        return path


def _get_format(platform: str) -> str:
    """Platformaga qarab eng yaxshi formatni tanlash."""
    if platform == "YouTube":
        # Eng yaxshi mp4 video+audio, 1080p gacha
        return (
            "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]"
            "/bestvideo[height<=1080]+bestaudio"
            "/best[ext=mp4][height<=1080]"
            "/best[height<=1080]"
            "/best"
        )
    # Instagram
    return "best[ext=mp4]/best"


def _clean_error(msg: str) -> str:
    """Xato xabarini tozalash."""
    # yt-dlp xatolari ko'pincha "ERROR: " bilan boshlanadi
    msg = re.sub(r"^ERROR:\s*", "", msg, flags=re.IGNORECASE)
    # Faqat birinchi satrni olish
    return msg.split("\n")[0][:200]


def cleanup_file(path: Path) -> None:
    """Yuborilgan faylni o'chirish."""
    try:
        if path and path.exists():
            path.unlink()
    except OSError:
        pass
