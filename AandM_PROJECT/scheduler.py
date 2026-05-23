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
    reminders = db_handler.get_all_reminders()
    for user_id, reminder_time in reminders:
        if reminder_time == now:
            try:
                from db_handler import already_recorded_today
                if not already_recorded_today(user_id):
                    bot.send_message(
                        user_id,
                        "⏰ <b>Привет!</b> Не забудь записать свой день!\n"
                        "Нажми кнопку + Записать день",
                        parse_mode="HTML",
                    )
            except Exception as e:
                logger.error(f"Ошибка отправки напоминания {user_id}: {e}")

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
    logger.info("Планировщик напоминаний запущен.")
    return scheduler
