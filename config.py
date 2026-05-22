import os
import logging
from dotenv import load_dotenv

# Загрузка переменных из .env
load_dotenv()

# ─── Telegram ────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ─── База данных ─────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "mood_tracker"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASS", "")
}

# Флаг для переключения на SQLite (удобно для локальных тестов)
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"
SQLITE_PATH = os.getenv("SQLITE_PATH", "tracker.db")

# ─── Логирование ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8", mode="a")
    ]
)
logger = logging.getLogger(__name__)

# ─── Состояния диалога (для управления вводом данных) ────────────────────────
class States:
    IDLE = "idle"
    WAITING_MOOD = "waiting_mood"
    WAITING_WORK = "waiting_work"
    WAITING_WORK_CUSTOM = "waiting_work_custom"
    WAITING_SLEEP = "waiting_sleep"
    WAITING_SLEEP_CUSTOM = "waiting_sleep_custom"
    WAITING_COMMENT = "waiting_comment"