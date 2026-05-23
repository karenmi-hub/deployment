import sqlite3
import os
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "wellbeing.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id   INTEGER UNIQUE NOT NULL,
                username      TEXT DEFAULT '',
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS entries (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                mood          INTEGER NOT NULL CHECK(mood BETWEEN 1 AND 5),
                work_hours    REAL    NOT NULL CHECK(work_hours >= 0),
                sleep_hours   REAL    NOT NULL CHECK(sleep_hours >= 0),
                comment       TEXT,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS settings (
                user_id        INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                reminder_time  TEXT DEFAULT '20:00'
            );

            CREATE INDEX IF NOT EXISTS idx_entries_user_id    ON entries(user_id);
            CREATE INDEX IF NOT EXISTS idx_entries_created_at ON entries(created_at);
        """)
    conn.close()


def ensure_user(telegram_id: int, username: str = "") -> int:
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)",
            (telegram_id, username)
        )
        row = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    conn.close()
    return row["id"]


def _get_user_id(telegram_id: int) -> int | None:
    conn = get_connection()
    row = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    conn.close()
    return row["id"] if row else None


def add_entry(telegram_id: int, mood: int, work_hours: float, sleep_hours: float, comment: str | None = None) -> int:
    user_id = _get_user_id(telegram_id)
    if not user_id:
        raise ValueError(f"Пользователь {telegram_id} не найден")
    conn = get_connection()
    with conn:
        cur = conn.execute(
            """INSERT INTO entries (user_id, mood, work_hours, sleep_hours, comment)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, mood, work_hours, sleep_hours, comment)
        )
        entry_id = cur.lastrowid
    conn.close()
    return entry_id


def get_history(telegram_id: int, page: int = 0, per_page: int = 5):
    user_id = _get_user_id(telegram_id)
    if not user_id:
        return [], 0
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM entries WHERE user_id = ?", (user_id,)).fetchone()[0]
    rows = conn.execute(
        """SELECT id, mood, work_hours, sleep_hours, comment, created_at
           FROM entries WHERE user_id = ?
           ORDER BY created_at DESC
           LIMIT ? OFFSET ?""",
        (user_id, per_page, page * per_page)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows], total


def get_entries_for_period(telegram_id: int, days: int) -> list[dict]:
    user_id = _get_user_id(telegram_id)
    if not user_id:
        return []
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, mood, work_hours, sleep_hours, comment, created_at
           FROM entries
           WHERE user_id = ?
             AND created_at >= datetime('now', ?)
           ORDER BY created_at ASC""",
        (user_id, f"-{days} days")
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_aggregated_stats(telegram_id: int, days: int) -> dict:
    user_id = _get_user_id(telegram_id)
    if not user_id:
        return {}
    conn = get_connection()
    row = conn.execute(
        """SELECT
               COUNT(*)           AS cnt,
               ROUND(AVG(mood), 2)        AS avg_mood,
               ROUND(AVG(work_hours), 2)  AS avg_work,
               ROUND(AVG(sleep_hours), 2) AS avg_sleep,
               MIN(mood)          AS min_mood,
               MAX(mood)          AS max_mood,
               MIN(work_hours)    AS min_work,
               MAX(work_hours)    AS max_work,
               MIN(sleep_hours)   AS min_sleep,
               MAX(sleep_hours)   AS max_sleep
           FROM entries
           WHERE user_id = ?
             AND created_at >= datetime('now', ?)""",
        (user_id, f"-{days} days")
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


def get_daily_averages(telegram_id: int, days: int) -> list[dict]:
    user_id = _get_user_id(telegram_id)
    if not user_id:
        return []
    conn = get_connection()
    rows = conn.execute(
        """SELECT
               DATE(created_at)           AS day,
               ROUND(AVG(mood), 2)        AS avg_mood,
               ROUND(AVG(work_hours), 2)  AS avg_work,
               ROUND(AVG(sleep_hours), 2) AS avg_sleep,
               COUNT(*)                   AS cnt
           FROM entries
           WHERE user_id = ?
             AND created_at >= datetime('now', ?)
           GROUP BY DATE(created_at)
           ORDER BY day ASC""",
        (user_id, f"-{days} days")
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_mood_by_sleep_buckets(telegram_id: int, days: int = 30) -> list[dict]:
    user_id = _get_user_id(telegram_id)
    if not user_id:
        return []
    conn = get_connection()
    rows = conn.execute(
        """SELECT
               CASE
                   WHEN sleep_hours < 6  THEN '< 6ч'
                   WHEN sleep_hours < 7  THEN '6–7ч'
                   WHEN sleep_hours < 8  THEN '7–8ч'
                   WHEN sleep_hours < 9  THEN '8–9ч'
                   ELSE '9+ ч'
               END AS sleep_bucket,
               ROUND(AVG(mood), 2) AS avg_mood,
               COUNT(*)            AS cnt
           FROM entries
           WHERE user_id = ?
             AND created_at >= datetime('now', ?)
           GROUP BY sleep_bucket
           ORDER BY sleep_bucket""",
        (user_id, f"-{days} days")
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_mood_by_work_buckets(telegram_id: int, days: int = 30) -> list[dict]:
    user_id = _get_user_id(telegram_id)
    if not user_id:
        return []
    conn = get_connection()
    rows = conn.execute(
        """SELECT
               CASE
                   WHEN work_hours < 2  THEN '< 2ч'
                   WHEN work_hours < 4  THEN '2–4ч'
                   WHEN work_hours < 6  THEN '4–6ч'
                   WHEN work_hours < 8  THEN '6–8ч'
                   ELSE '8+ ч'
               END AS work_bucket,
               ROUND(AVG(mood), 2) AS avg_mood,
               COUNT(*)            AS cnt
           FROM entries
           WHERE user_id = ?
             AND created_at >= datetime('now', ?)
           GROUP BY work_bucket
           ORDER BY work_bucket""",
        (user_id, f"-{days} days")
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_best_day(telegram_id: int, days: int = 30) -> dict | None:
    user_id = _get_user_id(telegram_id)
    if not user_id:
        return None
    conn = get_connection()
    row = conn.execute(
        """SELECT DATE(created_at) AS day, ROUND(AVG(mood),2) AS avg_mood
           FROM entries
           WHERE user_id = ?
             AND created_at >= datetime('now', ?)
           GROUP BY DATE(created_at)
           ORDER BY avg_mood DESC
           LIMIT 1""",
        (user_id, f"-{days} days")
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_settings(telegram_id: int) -> dict | None:
    user_id = _get_user_id(telegram_id)
    if not user_id:
        return None
    conn = get_connection()
    row = conn.execute("SELECT reminder_time FROM settings WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else {"reminder_time": "20:00"}

def save_settings(telegram_id: int, reminder_time: str):
    user_id = _get_user_id(telegram_id)
    if not user_id:
        return
    conn = get_connection()
    with conn:
        conn.execute(
            """INSERT INTO settings (user_id, reminder_time) VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET reminder_time = excluded.reminder_time""",
            (user_id, reminder_time)
        )
    conn.close()

def get_users_with_reminder(time_str: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT u.telegram_id
           FROM users u
           JOIN settings s ON s.user_id = u.id
           WHERE s.reminder_time = ?""",
        (time_str,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def clear_user_data(telegram_id: int):
    user_id = _get_user_id(telegram_id)
    if not user_id:
        return
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM entries WHERE user_id = ?", (user_id,))
    conn.close()