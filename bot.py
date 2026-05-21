# bot.py — Главный файл бота

import logging
import threading
import time
from datetime import datetime

import telebot
from telebot.types import Message, CallbackQuery

from config import BOT_TOKEN, States
from db_handler import (
    init_db, upsert_user, get_user,
    add_record, record_exists_today,
    clear_user_data, update_remind_hour,
    get_all_users
)
from analyzer import (
    format_stats_message, format_insights_message,
    format_history_message, generate_chart, MOOD_EMOJI
)
from keyboards import (
    get_main_keyboard, get_mood_keyboard,
    get_work_hours_keyboard, get_sleep_hours_keyboard,
    get_comment_keyboard, get_stats_keyboard,
    get_history_keyboard, get_confirm_clear_keyboard,
    get_settings_keyboard
)

# ─── Логирование ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# ─── Инициализация ────────────────────────────────────────────────────────────
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# Хранилище состояний пользователей в памяти
# { user_id: { "state": States.XXX, "data": {...} } }
user_sessions: dict[int, dict] = {}


def get_session(user_id: int) -> dict:
    """Возвращает или создаёт сессию пользователя."""
    if user_id not in user_sessions:
        user_sessions[user_id] = {"state": States.IDLE, "data": {}}
    return user_sessions[user_id]


def reset_session(user_id: int):
    """Сбрасывает сессию пользователя."""
    user_sessions[user_id] = {"state": States.IDLE, "data": {}}


# ─── Тексты ──────────────────────────────────────────────────────────────────
WELCOME_TEXT = """
👋 Привет, *{name}*! Я — твой личный трекер настроения и продуктивности.

📌 *Что я умею:*
• Ежедневно фиксировать настроение, сон и рабочие часы
• Анализировать статистику за неделю и месяц
• Находить скрытые закономерности в твоей жизни
• Строить наглядные графики

🚀 *Как начать:*
Нажми «➕ Записать день» и ответь на 3–4 простых вопроса.

Записывай каждый день — и через неделю узнаешь о себе кое-что интересное! 📊
"""

HELP_TEXT = """
📖 *Справка по боту*

*Команды:*
/start — Перезапустить бота
/add — Записать сегодняшний день
/stats — Просмотреть статистику
/history — История записей
/settings — Настройки
/clear — Очистить все данные
/help — Эта справка

*Кнопки меню:*
➕ Записать день — начать ввод данных
📊 Статистика — аналитика и инсайты
📋 История — список прошлых записей
⚙️ Настройки — персонализация

*Процесс записи дня:*
1️⃣ Оцени настроение от 1 до 5
2️⃣ Укажи часы работы/учёбы
3️⃣ Укажи часы сна
4️⃣ Добавь комментарий (по желанию)

💡 *Совет:* Заполняй ежедневно в одно и то же время для лучшей аналитики!
"""


# ─── Вспомогательные функции ─────────────────────────────────────────────────

def safe_send(user_id: int, text: str, **kwargs):
    """Безопасная отправка сообщения с обработкой ошибок."""
    try:
        bot.send_message(user_id, text, **kwargs)
    except Exception as e:
        logger.error(f"safe_send error for {user_id}: {e}")


def start_add_flow(user_id: int, chat_id: int):
    """Начинает процесс добавления записи."""
    session = get_session(user_id)

    if record_exists_today(user_id):
        bot.send_message(
            chat_id,
            "📝 Ты уже записал сегодняшний день!\n"
            "Если хочешь обновить данные — продолжи, "
            "и новая запись заменит старую.",
            reply_markup=get_mood_keyboard()
        )
    
    session["state"] = States.WAITING_MOOD
    session["data"] = {}

    bot.send_message(
        chat_id,
        "😊 *Шаг 1 из 4*\n\n"
        "Оцени своё настроение сегодня:\n"
        "1 — ужасно, 5 — отлично",
        reply_markup=get_mood_keyboard()
    )


# ─── Обработчики команд ───────────────────────────────────────────────────────

@bot.message_handler(commands=["start"])
def cmd_start(message: Message):
    user = message.from_user
    upsert_user(user.id, user.username or "", user.first_name or "")
    reset_session(user.id)

    bot.send_message(
        message.chat.id,
        WELCOME_TEXT.format(name=user.first_name or "друг"),
        reply_markup=get_main_keyboard()
    )
    logger.info(f"Пользователь {user.id} ({user.first_name}) запустил бота.")


@bot.message_handler(commands=["help"])
@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
def cmd_help(message: Message):
    bot.send_message(message.chat.id, HELP_TEXT, reply_markup=get_main_keyboard())


@bot.message_handler(commands=["add"])
@bot.message_handler(func=lambda m: m.text == "➕ Записать день")
def cmd_add(message: Message):
    user_id = message.from_user.id
    upsert_user(user_id, message.from_user.username or "",
                message.from_user.first_name or "")
    start_add_flow(user_id, message.chat.id)


@bot.message_handler(commands=["stats"])
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def cmd_stats(message: Message):
    bot.send_message(
        message.chat.id,
        "📊 *Аналитика*\n\nЧто хочешь узнать?",
        reply_markup=get_stats_keyboard()
    )


@bot.message_handler(commands=["history"])
@bot.message_handler(func=lambda m: m.text == "📋 История")
def cmd_history(message: Message):
    bot.send_message(
        message.chat.id,
        "📋 *История записей*\n\nЗа какой период?",
        reply_markup=get_history_keyboard()
    )


@bot.message_handler(commands=["settings"])
@bot.message_handler(func=lambda m: m.text == "⚙️ Настройки")
def cmd_settings(message: Message):
    user = get_user(message.from_user.id)
    remind_hour = user["remind_hour"] if user else 21
    bot.send_message(
        message.chat.id,
        f"⚙️ *Настройки*\n\n"
        f"🔔 Время напоминания: *{remind_hour}:00*\n"
        f"👤 Пользователь: {message.from_user.first_name}",
        reply_markup=get_settings_keyboard()
    )


@bot.message_handler(commands=["clear"])
def cmd_clear(message: Message):
    bot.send_message(
        message.chat.id,
        "🗑 *Очистка данных*\n\n"
        "⚠️ Ты уверен? Все твои записи будут *безвозвратно удалены*.",
        reply_markup=get_confirm_clear_keyboard()
    )


# ─── Обработка текстовых сообщений (состояния диалога) ───────────────────────

@bot.message_handler(func=lambda m: True)
def handle_text(message: Message):
    user_id = message.from_user.id
    session = get_session(user_id)
    state   = session["state"]
    text    = message.text.strip()

    # ── Ввод своего значения для рабочих часов ────────────────────────────────
    if state == States.WAITING_WORK_CUSTOM:
        try:
            hours = float(text.replace(",", "."))
            if hours < 0 or hours > 24:
                raise ValueError
            session["data"]["work_hours"] = hours
            session["state"] = States.WAITING_SLEEP
            bot.send_message(
                message.chat.id,
                f"✅ Записано: *{hours} ч* работы/учёбы.\n\n"
                "😴 *Шаг 3 из 4*\n\nСколько часов ты спал прошлой ночью?",
                reply_markup=get_sleep_hours_keyboard()
            )
        except ValueError:
            bot.send_message(
                message.chat.id,
                "❌ Введи число от 0 до 24 (например: 3.5 или 6)"
            )

    # ── Ввод своего значения для сна ─────────────────────────────────────────
    elif state == States.WAITING_SLEEP_CUSTOM:
        try:
            hours = float(text.replace(",", "."))
            if hours < 0 or hours > 24:
                raise ValueError
            session["data"]["sleep_hours"] = hours
            session["state"] = States.WAITING_COMMENT
            bot.send_message(
                message.chat.id,
                f"✅ Записано: *{hours} ч* сна.\n\n"
                "💬 *Шаг 4 из 4* (необязательно)\n\n"
                "Хочешь добавить комментарий к сегодняшнему дню?\n"
                "Напиши что-нибудь или нажми «Пропустить».",
                reply_markup=get_comment_keyboard()
            )
        except ValueError:
            bot.send_message(
                message.chat.id,
                "❌ Введи число от 0 до 24 (например: 7.5 или 8)"
            )

    # ── Ввод комментария ──────────────────────────────────────────────────────
    elif state == States.WAITING_COMMENT:
        session["data"]["comment"] = text
        _save_record(user_id, message.chat.id)

    # ── Ввод часа напоминания ─────────────────────────────────────────────────
    elif state == States.WAITING_SETTINGS_HOUR:
        try:
            hour = int(text)
            if hour < 0 or hour > 23:
                raise ValueError
            update_remind_hour(user_id, hour)
            reset_session(user_id)
            bot.send_message(
                message.chat.id,
                f"✅ Напоминание установлено на *{hour}:00*",
                reply_markup=get_main_keyboard()
            )
        except ValueError:
            bot.send_message(
                message.chat.id,
                "❌ Введи число от 0 до 23 (например: 9 или 21)"
            )

    else:
        # Неожиданное сообщение
        bot.send_message(
            message.chat.id,
            "🤔 Не понял тебя.\nИспользуй кнопки меню или /help для справки.",
            reply_markup=get_main_keyboard()
        )


def _save_record(user_id: int, chat_id: int):
    """Сохраняет запись в БД и отправляет итоговое сообщение."""
    session = get_session(user_id)
    data    = session["data"]

    success = add_record(
        user_id     = user_id,
        mood        = data["mood"],
        work_hours  = data["work_hours"],
        sleep_hours = data["sleep_hours"],
        comment     = data.get("comment")
    )

    reset_session(user_id)

    if success:
        mood_e = MOOD_EMOJI.get(data["mood"], "")
        comment_line = (
            f"\n💬 Комментарий: _{data.get('comment')}_"
            if data.get("comment") else ""
        )
        bot.send_message(
            chat_id,
            f"✅ *Запись сохранена!*\n\n"
            f"📅 Сегодня:\n"
            f"  Настроение: {data['mood']}/5 {mood_e}\n"
            f"  Работа/учёба: {data['work_hours']} ч\n"
            f"  Сон: {data['sleep_hours']} ч"
            f"{comment_line}\n\n"
            f"Отличная работа! Продолжай в том же духе 💪",
            reply_markup=get_main_keyboard()
        )
        logger.info(f"Запись сохранена для пользователя {user_id}: {data}")
    else:
        bot.send_message(
            chat_id,
            "❌ Произошла ошибка при сохранении. Попробуй ещё раз.",
            reply_markup=get_main_keyboard()
        )


# ─── Обработчики инлайн-кнопок ───────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: call.data.startswith("mood_"))
def cb_mood(call: CallbackQuery):
    user_id = call.from_user.id
    session = get_session(user_id)

    if session["state"] != States.WAITING_MOOD:
        bot.answer_callback_query(call.id, "Сначала начни запись: /add")
        return

    mood = int(call.data.split("_")[1])
    session["data"]["mood"] = mood
    session["state"] = States.WAITING_WORK

    mood_e = MOOD_EMOJI.get(mood, "")
    bot.edit_message_text(
        f"Настроение: *{mood}/5 {mood_e}* ✅",
        chat_id    = call.message.chat.id,
        message_id = call.message.message_id
    )
    bot.send_message(
        call.message.chat.id,
        "💼 *Шаг 2 из 4*\n\n"
        "Сколько часов ты сегодня потратил на полезную работу или учёбу?",
        reply_markup=get_work_hours_keyboard()
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("work_"))
def cb_work(call: CallbackQuery):
    user_id = call.from_user.id
    session = get_session(user_id)

    if session["state"] != States.WAITING_WORK:
        bot.answer_callback_query(call.id, "Сначала начни запись: /add")
        return

    value = call.data.split("_")[1]

    if value == "custom":
        session["state"] = States.WAITING_WORK_CUSTOM
        bot.edit_message_text(
            "✏️ Введи количество рабочих часов (например: 3.5):",
            chat_id    = call.message.chat.id,
            message_id = call.message.message_id
        )
        bot.answer_callback_query(call.id)
        return

    hours = float(value)
    session["data"]["work_hours"] = hours
    session["state"] = States.WAITING_SLEEP

    bot.edit_message_text(
        f"Работа/учёба: *{hours} ч* ✅",
        chat_id    = call.message.chat.id,
        message_id = call.message.message_id
    )
    bot.send_message(
        call.message.chat.id,
        "😴 *Шаг 3 из 4*\n\nСколько часов ты спал прошлой ночью?",
        reply_markup=get_sleep_hours_keyboard()
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("sleep_"))
def cb_sleep(call: CallbackQuery):
    user_id = call.from_user.id
    session = get_session(user_id)

    if session["state"] != States.WAITING_SLEEP:
        bot.answer_callback_query(call.id, "Сначала начни запись: /add")
        return

    value = call.data.split("_")[1]

    if value == "custom":
        session["state"] = States.WAITING_SLEEP_CUSTOM
        bot.edit_message_text(
            "✏️ Введи количество часов сна (например: 7.5):",
            chat_id    = call.message.chat.id,
            message_id = call.message.message_id
        )
        bot.answer_callback_query(call.id)
        return

    hours = float(value)
    session["data"]["sleep_hours"] = hours
    session["state"] = States.WAITING_COMMENT

    bot.edit_message_text(
        f"Сон: *{hours} ч* ✅",
        chat_id    = call.message.chat.id,
        message_id = call.message.message_id
    )
    bot.send_message(
        call.message.chat.id,
        "💬 *Шаг 4 из 4* (необязательно)\n\n"
        "Хочешь добавить комментарий к сегодняшнему дню?\n"
        "Напиши что-нибудь или нажми «Пропустить».",
        reply_markup=get_comment_keyboard()
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "comment_skip")
def cb_comment_skip(call: CallbackQuery):
    user_id = call.from_user.id
    session = get_session(user_id)

    if session["state"] != States.WAITING_COMMENT:
        bot.answer_callback_query(call.id)
        return

    session["data"]["comment"] = None
    bot.edit_message_text(
        "Комментарий: *пропущен* ✅",
        chat_id    = call.message.chat.id,
        message_id = call.message.message_id
    )
    _save_record(user_id, call.message.chat.id)
    bot.answer_callback_query(call.id)


# ── Статистика ────────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: call.data == "stats_week")
def cb_stats_week(call: CallbackQuery):
    user_id = call.from_user.id
    text    = format_stats_message(user_id, days=7)
    bot.edit_message_text(
        text,
        chat_id    = call.message.chat.id,
        message_id = call.message.message_id,
        reply_markup=get_stats_keyboard()
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "stats_month")
def cb_stats_month(call: CallbackQuery):
    user_id = call.from_user.id
    text    = format_stats_message(user_id, days=30)
    bot.edit_message_text(
        text,
        chat_id    = call.message.chat.id,
        message_id = call.message.message_id,
        reply_markup=get_stats_keyboard()
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "stats_insights")
def cb_stats_insights(call: CallbackQuery):
    user_id = call.from_user.id
    text    = format_insights_message(user_id)
    bot.edit_message_text(
        text,
        chat_id    = call.message.chat.id,
        message_id = call.message.message_id,
        reply_markup=get_stats_keyboard()
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "stats_chart")
def cb_stats_chart(call: CallbackQuery):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id, "⏳ Генерирую график...")

    chart = generate_chart(user_id, days=14)
    if chart:
        bot.send_photo(
            call.message.chat.id,
            photo   = chart,
            caption = "📈 *Динамика за последние 14 дней*\n"
                      "Пунктир — среднее значение за период.",
        )
    else:
        bot.send_message(
            call.message.chat.id,
            "📭 Недостаточно данных для графика.\n"
            "Нужно минимум 2 записи!"
        )


# ── История ───────────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: call.data.startswith("history_"))
def cb_history(call: CallbackQuery):
    user_id = call.from_user.id
    days    = int(call.data.split("_")[1])
    text    = format_history_message(user_id, days)

    bot.edit_message_text(
        text,
        chat_id    = call.message.chat.id,
        message_id = call.message.message_id,
        reply_markup=get_history_keyboard()
    )
    bot.answer_callback_query(call.id)


# ── Настройки ─────────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: call.data == "settings_reminder")
def cb_settings_reminder(call: CallbackQuery):
    user_id = call.from_user.id
    session = get_session(user_id)
    session["state"] = States.WAITING_SETTINGS_HOUR

    bot.edit_message_text(
        "🔔 *Изменить время напоминания*\n\n"
        "Введи час в формате 0–23\n"
        "(например: `21` — это 21:00, `9` — это 09:00)",
        chat_id    = call.message.chat.id,
        message_id = call.message.message_id
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "settings_clear")
def cb_settings_clear(call: CallbackQuery):
    bot.edit_message_text(
        "🗑 *Очистка данных*\n\n"
        "⚠️ Ты уверен? Все твои записи будут *безвозвратно удалены*.",
        chat_id    = call.message.chat.id,
        message_id = call.message.message_id,
        reply_markup=get_confirm_clear_keyboard()
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "settings_about")
def cb_settings_about(call: CallbackQuery):
    bot.edit_message_text(
        "ℹ️ *О боте*\n\n"
        "🤖 *Mood & Productivity Tracker*\n"
        "Версия: 1.0.0\n\n"
        "Помогает отслеживать настроение, сон и продуктивность, "
        "находить закономерности и становиться лучше каждый день.\n\n"
        "🛠 Стек: Python, pyTelegramBotAPI, PostgreSQL, Matplotlib",
        chat_id    = call.message.chat.id,
        message_id = call.message.message_id,
        reply_markup=get_settings_keyboard()
    )
    bot.answer_callback_query(call.id)


# ── Очистка данных ────────────────────────────────────────────────────────────

@bot.callback_query_handler(func=lambda call: call.data == "clear_confirm")
def cb_clear_confirm(call: CallbackQuery):
    user_id = call.from_user.id
    success = clear_user_data(user_id)

    if success:
        bot.edit_message_text(
            "🗑 *Данные удалены.*\n\n"
            "Все твои записи были очищены. Начни заново с /add",
            chat_id    = call.message.chat.id,
            message_id = call.message.message_id
        )
        logger.info(f"Данные пользователя {user_id} очищены.")
    else:
        bot.edit_message_text(
            "❌ Ошибка при удалении данных. Попробуй позже.",
            chat_id    = call.message.chat.id,
            message_id = call.message.message_id
        )
    bot.answer_callback_query(call.id)
    reset_session(user_id)


@bot.callback_query_handler(func=lambda call: call.data == "clear_cancel")
def cb_clear_cancel(call: CallbackQuery):
    bot.edit_message_text(
        "✅ Отмена. Данные сохранены.",
        chat_id    = call.message.chat.id,
        message_id = call.message.message_id
    )
    bot.answer_callback_query(call.id, "Данные не удалены.")


# ─── Система напоминаний ──────────────────────────────────────────────────────

def reminder_worker():
    """
    Фоновый поток: каждый час проверяет, кому нужно отправить напоминание.
    """
    logger.info("Поток напоминаний запущен.")
    while True:
        try:
            current_hour = datetime.now().hour
            users = get_all_users()

            for user in users:
                if user["remind_hour"] == current_hour:
                    if not __import__("db_handler").record_exists_today(user["user_id"]):
                        safe_send(
                            user["user_id"],
                            "🔔 *Напоминание!*\n\n"
                            "Ты ещё не записал свой день сегодня.\n"
                            "Это займёт меньше минуты! 👇",
                            reply_markup=get_main_keyboard()
                        )
        except Exception as e:
            logger.error(f"Ошибка в reminder_worker: {e}")

        # Проверяем раз в час
        time.sleep(3600)


# ─── Запуск ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Инициализация базы данных...")
    init_db()

    # Запуск фонового потока напоминаний
    reminder_thread = threading.Thread(target=reminder_worker, daemon=True)
    reminder_thread.start()

    logger.info("Бот запущен. Ожидание сообщений...")
    print("✅ Бот запущен! Нажми Ctrl+C для остановки.")

    bot.infinity_polling(logger_level=logging.WARNING)