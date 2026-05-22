import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date
import config
import logging

logger = logging.getLogger(__name__)


def get_connection():
    """Возвращает соединение с БД (PostgreSQL или SQLite)."""
    if config.USE_SQLITE:
        import sqlite3
        return sqlite3.connect(config.SQLITE_PATH)
    return psycopg2.connect(**config.DB_CONFIG)


def init_db():
    """Создаёт таблицы, если не существуют."""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        if config.USE_SQLITE:
            # Создаём таблицу для SQLite
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS user_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id BIGINT NOT NULL,
                    entry_date DATE NOT NULL,
                    mood INTEGER CHECK (mood BETWEEN 1 AND 5),
                    work_hours REAL CHECK (work_hours >= 0),
                    sleep_hours REAL CHECK (sleep_hours >= 0),
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, entry_date)
                );
                
                CREATE INDEX IF NOT EXISTS idx_user_entries_date 
                ON user_entries(user_id, entry_date DESC);
            """)
        else:
            # Создаём таблицу для PostgreSQL
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_entries (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    entry_date DATE NOT NULL,
                    mood INTEGER CHECK (mood BETWEEN 1 AND 5),
                    work_hours NUMERIC(4,2) CHECK (work_hours >= 0),
                    sleep_hours NUMERIC(4,2) CHECK (sleep_hours >= 0),
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, entry_date)
                );
                
                CREATE INDEX IF NOT EXISTS idx_user_entries_date 
                ON user_entries(user_id, entry_date DESC);
            """)
        
        conn.commit()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        raise
    finally:
        if conn:
            conn.close()

# def init_db():
#     """Создаёт таблицу из schema.sql, если не существует."""
#     try:
#         with open("schema.sql", "r", encoding="utf-8") as f:
#             sql_script = f.read()
        
#         conn = get_connection()
#         cur = conn.cursor()
#         cur.execute(sql_script)
#         conn.commit()
#         logger.info("✅ База данных инициализирована")
#     except Exception as e:
#         logger.error(f"❌ Ошибка инициализации БД: {e}")
#         raise
#     finally:
#         if conn:
#             conn.close()


def add_entry(user_id: int, entry_date: date, mood: int, 
              work_hours: float, sleep_hours: float, comment: str = None) -> bool:
    """Добавляет или обновляет запись за указанный день."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        if config.USE_SQLITE:
            # SQLite синтаксис
            cur.execute("""
                INSERT OR REPLACE INTO user_entries 
                (user_id, entry_date, mood, work_hours, sleep_hours, comment)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, entry_date, mood, work_hours, sleep_hours, comment))
        else:
            # PostgreSQL синтаксис с ON CONFLICT
            cur.execute("""
                INSERT INTO user_entries 
                (user_id, entry_date, mood, work_hours, sleep_hours, comment)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, entry_date) DO UPDATE SET
                    mood = EXCLUDED.mood,
                    work_hours = EXCLUDED.work_hours,
                    sleep_hours = EXCLUDED.sleep_hours,
                    comment = EXCLUDED.comment,
                    created_at = CURRENT_TIMESTAMP
            """, (user_id, entry_date, mood, work_hours, sleep_hours, comment))
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"add_entry error: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def get_entries(user_id: int, days: int = 7) -> list:
    """Возвращает записи пользователя за последние N дней."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor if not config.USE_SQLITE else None)
        
        if config.USE_SQLITE:
            cur.execute("""
                SELECT * FROM user_entries 
                WHERE user_id = ? AND entry_date >= date('now', ?)
                ORDER BY entry_date ASC
            """, (user_id, f"-{days} days"))
        else:
            cur.execute("""
                SELECT * FROM user_entries 
                WHERE user_id = %s AND entry_date >= CURRENT_DATE - %s * INTERVAL '1 day'
                ORDER BY entry_date ASC
            """, (user_id, days))
        
        return cur.fetchall()
    except Exception as e:
        logger.error(f"get_entries error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def clear_user_data(user_id: int) -> bool:
    """Удаляет все записи пользователя."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM user_entries WHERE user_id = %s", (user_id,))
        conn.commit()
        logger.info(f"Очищены данные пользователя {user_id}")
        return True
    except Exception as e:
        logger.error(f"clear_user_data error: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


def record_exists_today(user_id: int) -> bool:
    """Проверяет, есть ли запись за сегодня."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        if config.USE_SQLITE:
            cur.execute("""
                SELECT 1 FROM user_entries 
                WHERE user_id = ? AND entry_date = date('now')
            """, (user_id,))
        else:
            cur.execute("""
                SELECT 1 FROM user_entries 
                WHERE user_id = %s AND entry_date = CURRENT_DATE
            """, (user_id,))
        
        return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"record_exists_today error: {e}")
        return False
    finally:
        if conn:
            conn.close()