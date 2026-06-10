import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "123456")
DB_PORT = os.getenv("DB_PORT", "5432")

DSN = f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASS} port={DB_PORT}"


@contextmanager
def _get_connection():
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
            client_encoding='UTF8' 
        )
        yield conn
    except Exception as e:
        print(f"Ошибка БД: {e}")
        raise
    finally:
        if conn:
            conn.close()


def _exec(query: str, params: tuple = (), fetch: bool = False, fetchall: bool = False) -> Any:
    with _get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            
            if fetchall:
                return cur.fetchall()
            if fetch:
                return cur.fetchone()
            
            conn.commit()
            if cur.statusmessage.startswith('INSERT'):
                pass 
            return True


def init_db() -> None:
    _exec("""
        CREATE TABLE IF NOT EXISTS user_entries (
            id           SERIAL PRIMARY KEY,
            user_id      BIGINT NOT NULL,
            entry_date   DATE NOT NULL DEFAULT CURRENT_DATE,
            mood         INTEGER NOT NULL CHECK (mood BETWEEN 1 AND 5),
            work_hours   NUMERIC(4,2) NOT NULL CHECK (work_hours >= 0 AND work_hours <= 24),
            sleep_hours  NUMERIC(4,2) NOT NULL CHECK (sleep_hours >= 0 AND sleep_hours <= 24),
            comment      TEXT,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_user_entry_date UNIQUE (user_id, entry_date)
        );

        CREATE INDEX IF NOT EXISTS idx_user_entries_user_date ON user_entries (user_id, entry_date DESC);
        CREATE INDEX IF NOT EXISTS idx_user_entries_mood ON user_entries (mood);
        CREATE INDEX IF NOT EXISTS idx_user_entries_date_only ON user_entries (entry_date);
        
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id BIGINT PRIMARY KEY,
            reminder_time TEXT DEFAULT '20:00'
        );
    """)


def ensure_user(tid: int, uname: str = "") -> int:
    return tid


def add_entry(tid: int, mood: int, work: float, sleep: float, comment: Optional[str] = None, date: Optional[str] = None) -> int:
    query = """
        INSERT INTO user_entries (user_id, entry_date, mood, work_hours, sleep_hours, comment)
        VALUES (%s, COALESCE(%s::date, CURRENT_DATE), %s, %s, %s, %s)
        ON CONFLICT (user_id, entry_date) 
        DO UPDATE SET 
            mood = EXCLUDED.mood,
            work_hours = EXCLUDED.work_hours,
            sleep_hours = EXCLUDED.sleep_hours,
            comment = EXCLUDED.comment
        RETURNING id;
    """
    result = _exec(query, (tid, date, mood, work, sleep, comment), fetch=True)
    return result['id'] if result else 0


def get_history(tid: int, page: int = 0, per_page: int = 5) -> tuple[List[Dict], int]:
    count_res = _exec("SELECT COUNT(*) as c FROM user_entries WHERE user_id = %s", (tid,), fetch=True)
    total = count_res['c'] if count_res else 0
    
    entries = _exec("""
        SELECT * FROM user_entries 
        WHERE user_id = %s 
        ORDER BY entry_date DESC 
        LIMIT %s OFFSET %s
    """, (tid, per_page, page * per_page), fetchall=True)
    
    return entries, total


def get_aggregated_stats(tid: int, days: int = 7) -> Dict[str, Any]:
    return _exec("""
        SELECT COUNT(*) as cnt, 
            ROUND(AVG(mood)::numeric, 2) as avg_mood, 
            ROUND(AVG(work_hours)::numeric, 2) as avg_work, 
            ROUND(AVG(sleep_hours)::numeric, 2) as avg_sleep,
            MIN(mood) as min_mood, MAX(mood) as max_mood, 
            MIN(work_hours) as min_work, MAX(work_hours) as max_work, 
            MIN(sleep_hours) as min_sleep, MAX(sleep_hours) as max_sleep
        FROM user_entries 
        WHERE user_id = %s AND entry_date >= CURRENT_DATE - INTERVAL '%s days'
    """, (tid, days), fetch=True) or {}


def get_daily_averages(tid: int, days: int = 30) -> List[Dict]:
    return _exec("""
        SELECT entry_date as day, 
            ROUND(AVG(mood)::numeric, 2) as avg_mood, 
            ROUND(AVG(work_hours)::numeric, 2) as avg_work, 
            ROUND(AVG(sleep_hours)::numeric, 2) as avg_sleep
        FROM user_entries 
        WHERE user_id = %s AND entry_date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY entry_date 
        ORDER BY entry_date ASC
    """, (tid, days), fetchall=True)


def get_mood_by_buckets(tid: int, days: int = 30, col: str = "sleep_hours") -> List[Dict]:
    query = f"""
        SELECT 
            CASE 
                WHEN {col} < 6 THEN '< 6ч' 
                WHEN {col} < 7 THEN '6-7ч' 
                WHEN {col} < 8 THEN '7-8ч' 
                WHEN {col} < 9 THEN '8-9ч' 
                ELSE '9+ ч' 
            END as bucket, 
            ROUND(AVG(mood)::numeric, 2) as avg_mood
        FROM user_entries 
        WHERE user_id = %s AND entry_date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY bucket 
        ORDER BY bucket
    """
    return _exec(query, (tid, days), fetchall=True)


def get_best_day(tid: int, days: int = 30) -> Optional[Dict]:
    return _exec("""
        SELECT entry_date as day, ROUND(AVG(mood)::numeric, 2) as avg_mood 
        FROM user_entries 
        WHERE user_id = %s AND entry_date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY entry_date 
        ORDER BY avg_mood DESC 
        LIMIT 1
    """, (tid, days), fetch=True)


def save_settings(tid: int, time: str) -> None:
    _exec("""
        INSERT INTO user_settings (user_id, reminder_time) 
        VALUES (%s, %s) 
        ON CONFLICT (user_id) 
        DO UPDATE SET reminder_time = EXCLUDED.reminder_time
    """, (tid, time))


def get_users_with_reminder(time_str: str) -> List[Dict]:
    return _exec("""
        SELECT s.user_id as telegram_id
        FROM user_settings s
        WHERE s.reminder_time = %s
    """, (time_str,), fetchall=True)


def clear_user_data(tid: int) -> None:
    _exec("DELETE FROM user_entries WHERE user_id = %s", (tid,))
