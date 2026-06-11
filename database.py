import aiosqlite
from datetime import datetime

DB_PATH = "bot.db"


async def init_db() -> None:
    """Ma'lumotlar bazasini ishga tushirish va jadvallarni yaratish."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                downloads   INTEGER DEFAULT 0,
                joined_at   TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS downloads_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                url         TEXT NOT NULL,
                platform    TEXT NOT NULL,
                downloaded_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)
        await db.commit()


async def register_user(user_id: int, username: str | None, first_name: str) -> None:
    """Yangi foydalanuvchini ro'yxatdan o'tkazish (agar mavjud bo'lmasa)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name, downloads, joined_at)
            VALUES (?, ?, ?, 0, ?)
        """, (user_id, username, first_name, datetime.utcnow().isoformat()))
        # Ism yoki username o'zgargan bo'lsa yangilash
        await db.execute("""
            UPDATE users SET username = ?, first_name = ?
            WHERE user_id = ?
        """, (username, first_name, user_id))
        await db.commit()


async def increment_downloads(user_id: int, url: str, platform: str) -> None:
    """Yuklab olishlar sonini oshirish va logga yozish."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users SET downloads = downloads + 1 WHERE user_id = ?
        """, (user_id,))
        await db.execute("""
            INSERT INTO downloads_log (user_id, url, platform, downloaded_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, url, platform, datetime.utcnow().isoformat()))
        await db.commit()


async def get_stats() -> dict:
    """Admin uchun umumiy statistika."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            total_users = (await cur.fetchone())[0]

        async with db.execute("SELECT SUM(downloads) FROM users") as cur:
            total_downloads = (await cur.fetchone())[0] or 0

        async with db.execute("""
            SELECT platform, COUNT(*) as cnt
            FROM downloads_log
            GROUP BY platform
            ORDER BY cnt DESC
        """) as cur:
            platforms = await cur.fetchall()

        async with db.execute("""
            SELECT u.first_name, u.username, u.downloads
            FROM users u
            ORDER BY u.downloads DESC
            LIMIT 5
        """) as cur:
            top_users = await cur.fetchall()

    return {
        "total_users": total_users,
        "total_downloads": total_downloads,
        "platforms": platforms,
        "top_users": top_users,
    }
