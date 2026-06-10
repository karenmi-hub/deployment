import logging
from datetime import datetime
import db_handler

logger = logging.getLogger(__name__)
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    HAS_SCHEDULER = True
except ImportError:
    HAS_SCHEDULER = False
    logger.warning("APScheduler не установлен. Напоминания отключены.")

def _send_reminders(bot):
    now = datetime.now().strftime("%H:%M")
    reminders = db_handler.get_users_with_reminder(now)  
    for user in reminders:
        user_id = user['telegram_id']
        try:
            bot.send_message(
    user_id,
    "*Напоминание!*\n\nНе забудь записать свой день",
    parse_mode="Markdown"
)
        except Exception as e:
            logger.error(f"Ошибка отправки {user_id}: {e}")

def setup_scheduler(bot):
    if not HAS_SCHEDULER:
        return

    scheduler = BackgroundScheduler(timezone="Europe/Moscow")
    scheduler.add_job(
        _send_reminders,
        CronTrigger(minute="*"),
        args=[bot],
        id="reminders",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Планировщик напоминаний запущен")
    return scheduler
