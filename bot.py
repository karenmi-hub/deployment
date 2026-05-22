import telebot
from telebot.types import Message, CallbackQuery
from datetime import date
import logging

import config
import db_handler 
import analyzer 
import keyboards

# Инициализация логгера
logger = logging.getLogger(__name__)

# Инициализация бота
bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="Markdown")
bot.infinity_polling(timeout=30, long_polling_timeout=30)

print("✅ Бот инициализирован с токеном:", config.BOT_TOKEN[:20] + "...")
print("🎧 Ожидание сообщений...")

# Хранилище состояний: {user_id: {"state": ..., "data": {...}}}
user_sessions: dict[int, dict] = {}


def get_session(user_id: int) -> dict:
    """Возвращает или создаёт сессию пользователя."""
    if user_id not in user_sessions:
        user_sessions[user_id] = {"state": config.States.IDLE, "data": {}}
    return user_sessions[user_id]


def reset_session(user_id: int):
    """Сбрасывает сессию пользователя."""
    user_sessions[user_id] = {"state": config.States.IDLE, "data": {}}


# ─── Команды ─────────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start"])
def cmd_start(message: Message):
    """Приветствие и инструкция."""
    name = message.from_user.first_name or "друг"
    text = (
        f"👋 Привет, *{name}*!\n\n"
        "Я — трекер настроения и продуктивности.\n\n"
        "📌 *Что умею:*\n"
        "• Фиксировать настроение, сон и рабочие часы\n"
        "• Показывать статистику за неделю/месяц\n"
        "• Строить графики и находить закономерности\n\n"
        "🚀 *Как начать:*\n"
        "Нажми «➕ Записать день» или введи /add"
    )
    bot.send_message(message.chat.id, text, reply_markup=keyboards.get_main_keyboard())
    logger.info(f"Пользователь {message.from_user.id} запустил бота")


@bot.message_handler(commands=["help"])
def cmd_help(message: Message):
    """Справка по командам."""
    text = (
        "📖 *Справка*\n\n"
        "/start — Перезапустить бота\n"
        "/add — Записать сегодняшний день\n"
        "/stats — Просмотреть статистику\n"
        "/history — История записей\n"
        "/settings — Настройки (заглушка)\n"
        "/clear — Очистить все данные (с подтверждением)\n"
        "/help — Эта справка\n\n"
        "💡 *Совет:*\n"
        "Заполняй данные ежедневно в одно время — так аналитика будет точнее!"
    )
    bot.send_message(message.chat.id, text, reply_markup=keyboards.get_main_keyboard())


@bot.message_handler(commands=["add"])
@bot.message_handler(func=lambda m: m.text == "➕ Записать день")
def cmd_add(message: Message):
    """Начинает процесс ввода данных за сегодня."""
    user_id = message.from_user.id
    
    # Проверка: если уже есть запись за сегодня
    if db_handler.record_exists_today(user_id):
        bot.send_message(
            message.chat.id,
            "📝 Ты уже записал сегодняшний день!\n"
            "Если хочешь обновить — продолжи, старая запись заменится.",
            reply_markup=keyboards.get_mood_keyboard()
        )
    else:
        bot.send_message(
            message.chat.id,
            "😊 *Шаг 1 из 4*\n\nОцени своё настроение сегодня:\n1 — ужасно, 5 — отлично",
            reply_markup=keyboards.get_mood_keyboard()
        )
    
    # Установка состояния
    session = get_session(user_id)
    session["state"] = config.States.WAITING_MOOD
    session["data"] = {}


@bot.message_handler(commands=["stats"])
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def cmd_stats(message: Message):
    """Показывает меню выбора периода для статистики."""
    bot.send_message(
        message.chat.id,
        "📊 *Аналитика*\n\nЧто хочешь узнать?",
        reply_markup=keyboards.get_stats_keyboard()
    )


@bot.message_handler(commands=["history"])
@bot.message_handler(func=lambda m: m.text == "📜 История")
def cmd_history(message: Message):
    """Показывает меню выбора периода для истории."""
    bot.send_message(
        message.chat.id,
        "📋 *История*\n\nЗа какой период?",
        reply_markup=keyboards.get_history_keyboard()
    )


@bot.message_handler(commands=["clear"])
def cmd_clear(message: Message):
    """Запрашивает подтверждение перед удалением данных."""
    bot.send_message(
        message.chat.id,
        "🗑 *Очистка данных*\n\n⚠️ Ты уверен? Все записи будут удалены безвозвратно.",
        reply_markup=keyboards.get_confirm_keyboard()
    )


@bot.message_handler(commands=["settings"])
@bot.message_handler(func=lambda m: m.text == "⚙️ Настройки")
def cmd_settings(message: Message):
    """Заглушка для настроек (по требованиям)."""
    bot.send_message(
        message.chat.id,
        "⚙️ *Настройки*\n\n"
        "Функция в разработке.\n"
        "Здесь можно будет настроить время напоминаний.",
        reply_markup=keyboards.get_main_keyboard()
    )


# ─── Обработка инлайн-кнопок (ввод данных) ────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data.startswith("mood_"))
def cb_mood(call: CallbackQuery):
    """Обработка выбора настроения."""
    user_id = call.from_user.id
    session = get_session(user_id)
    
    if session["state"] != config.States.WAITING_MOOD:
        bot.answer_callback_query(call.id, "Сначала начни запись: /add")
        return
    
    mood = int(call.data.split("_")[1])
    session["data"]["mood"] = mood
    session["state"] = config.States.WAITING_WORK
    
    # Обновляем сообщение с выбором
    bot.edit_message_text(
        f"Настроение: *{mood}/5 {analyzer.MOOD_EMOJI.get(mood, '')}* ✅",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )
    
    # Следующий шаг
    bot.send_message(
        call.message.chat.id,
        "💼 *Шаг 2 из 4*\n\nСколько часов потратил на работу/учёбу?",
        reply_markup=keyboards.get_work_keyboard()
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("work_"))
def cb_work(call: CallbackQuery):
    """Обработка выбора часов работы."""
    user_id = call.from_user.id
    session = get_session(user_id)
    
    if session["state"] != config.States.WAITING_WORK:
        bot.answer_callback_query(call.id, "Сначала начни запись: /add")
        return
    
    value = call.data.split("_")[1]
    
    if value == "custom":
        # Запрос ручного ввода
        session["state"] = config.States.WAITING_WORK_CUSTOM
        bot.edit_message_text(
            "✏️ Введи количество часов (например: 3.5):",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        bot.answer_callback_query(call.id)
    else:
        hours = float(value)
        session["data"]["work_hours"] = hours
        session["state"] = config.States.WAITING_SLEEP
        
        bot.edit_message_text(
            f"Работа: *{hours} ч* ✅",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        bot.send_message(
            call.message.chat.id,
            "😴 *Шаг 3 из 4*\n\nСколько часов спал?",
            reply_markup=keyboards.get_sleep_keyboard()
        )
        bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("sleep_"))
def cb_sleep(call: CallbackQuery):
    """Обработка выбора часов сна."""
    user_id = call.from_user.id
    session = get_session(user_id)
    
    if session["state"] != config.States.WAITING_SLEEP:
        bot.answer_callback_query(call.id, "Сначала начни запись: /add")
        return
    
    value = call.data.split("_")[1]
    
    if value == "custom":
        session["state"] = config.States.WAITING_SLEEP_CUSTOM
        bot.edit_message_text(
            "✏️ Введи количество часов сна (например: 7.5):",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        bot.answer_callback_query(call.id)
    else:
        hours = float(value)
        session["data"]["sleep_hours"] = hours
        session["state"] = config.States.WAITING_COMMENT
        
        bot.edit_message_text(
            f"Сон: *{hours} ч* ✅",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        bot.send_message(
            call.message.chat.id,
            "💬 *Шаг 4 из 4* (необязательно)\n\nДобавить комментарий? Или нажми «Пропустить».",
            reply_markup=keyboards.get_comment_keyboard()
        )
        bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "comment_skip")
def cb_comment_skip(call: CallbackQuery):
    """Пропуск комментария и сохранение записи."""
    user_id = call.from_user.id
    session = get_session(user_id)
    
    if session["state"] != config.States.WAITING_COMMENT:
        bot.answer_callback_query(call.id)
        return
    
    session["data"]["comment"] = None
    bot.edit_message_text("Комментарий: *пропущен* ✅", 
                         chat_id=call.message.chat.id, 
                         message_id=call.message.message_id)
    _save_and_finish(user_id, call.message.chat.id)
    bot.answer_callback_query(call.id)


# ─── Обработка текстового ввода (ручные значения, комментарий) ───────────────

@bot.message_handler(func=lambda m: True)
def handle_text(message: Message):
    """Обрабатывает ручной ввод чисел и комментариев."""
    user_id = message.from_user.id
    session = get_session(user_id)
    state = session["state"]
    text = message.text.strip()
    
    try:
        # ── Ручной ввод часов работы ──────────────────────────────────────
        if state == config.States.WAITING_WORK_CUSTOM:
            hours = float(text.replace(",", "."))
            if not 0 <= hours <= 24:
                raise ValueError
            session["data"]["work_hours"] = hours
            session["state"] = config.States.WAITING_SLEEP
            
            bot.send_message(
                message.chat.id,
                f"✅ Записано: *{hours} ч* работы.\n\n"
                "😴 *Шаг 3 из 4*\n\nСколько часов спал?",
                reply_markup=keyboards.get_sleep_keyboard()
            )
        
        # ── Ручной ввод часов сна ─────────────────────────────────────────
        elif state == config.States.WAITING_SLEEP_CUSTOM:
            hours = float(text.replace(",", "."))
            if not 0 <= hours <= 24:
                raise ValueError
            session["data"]["sleep_hours"] = hours
            session["state"] = config.States.WAITING_COMMENT
            
            bot.send_message(
                message.chat.id,
                f"✅ Записано: *{hours} ч* сна.\n\n"
                "💬 *Шаг 4 из 4*\n\nДобавить комментарий? Или «Пропустить».",
                reply_markup=keyboards.get_comment_keyboard()
            )
        
        # ── Ввод комментария ──────────────────────────────────────────────
        elif state == config.States.WAITING_COMMENT:
            session["data"]["comment"] = text
            _save_and_finish(user_id, message.chat.id)
        
        # ── Неожиданное сообщение ─────────────────────────────────────────
        else:
            bot.send_message(
                message.chat.id,
                "🤔 Не понял. Используй кнопки меню или /help для справки.",
                reply_markup=keyboards.get_main_keyboard()
            )
    
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введи корректное число (например: 3.5 или 7)")


def _save_and_finish(user_id: int, chat_id: int):
    """Сохраняет запись в БД и отправляет подтверждение."""
    session = get_session(user_id)
    data = session["data"]
    
    success = db_handler.add_entry(
        user_id=user_id,
        entry_date=date.today(),
        mood=data["mood"],
        work_hours=data["work_hours"],
        sleep_hours=data["sleep_hours"],
        comment=data.get("comment")
    )
    
    reset_session(user_id)
    
    if success:
        mood_e = analyzer.MOOD_EMOJI.get(data["mood"], "")
        comment_line = f"\n💬 Комментарий: _{data.get('comment')}_" if data.get("comment") else ""
        
        bot.send_message(
            chat_id,
            f"✅ *Запись сохранена!*\n\n"
            f"📅 Сегодня:\n"
            f"  Настроение: {data['mood']}/5 {mood_e}\n"
            f"  Работа: {data['work_hours']} ч\n"
            f"  Сон: {data['sleep_hours']} ч"
            f"{comment_line}\n\n"
            f"Отлично! Продолжай в том же духе 💪",
            reply_markup=keyboards.get_main_keyboard()
        )
        logger.info(f"Запись сохранена: user={user_id}, mood={data['mood']}")
    else:
        bot.send_message(
            chat_id,
            "❌ Ошибка при сохранении. Попробуй ещё раз.",
            reply_markup=keyboards.get_main_keyboard()
        )


# ─── Статистика и история (инлайн-кнопки) ────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data in ["stats_7", "stats_30"])
def cb_stats_period(call: CallbackQuery):
    """Показывает статистику за выбранный период."""
    user_id = call.from_user.id
    days = 7 if call.data == "stats_7" else 30
    
    entries = db_handler.get_entries(user_id, days)
    text = analyzer.format_stats_message(entries, days)
    
    bot.edit_message_text(
        text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.get_stats_keyboard()
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "stats_chart")
def cb_stats_chart(call: CallbackQuery):
    """Генерирует и отправляет график."""
    user_id = call.from_user.id
    bot.answer_callback_query(call.id, "⏳ Генерирую график...")
    
    entries = db_handler.get_entries(user_id, 14)
    chart = analyzer.generate_chart(entries, 14)
    
    if chart:
        bot.send_photo(
            call.message.chat.id,
            photo=chart,
            caption="📈 *Динамика настроения за 14 дней*\nПунктир — среднее значение."
        )
    else:
        bot.send_message(
            call.message.chat.id,
            "📭 Недостаточно данных для графика.\nНужно минимум 2 записи!"
        )


@bot.callback_query_handler(func=lambda c: c.data in ["hist_7", "hist_30"])
def cb_history_period(call: CallbackQuery):
    """Показывает историю за выбранный период."""
    user_id = call.from_user.id
    days = 7 if call.data == "hist_7" else 30
    
    entries = db_handler.get_entries(user_id, days)
    text = analyzer.format_history_message(entries, days)
    
    bot.edit_message_text(
        text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.get_history_keyboard()
    )
    bot.answer_callback_query(call.id)


# ─── Очистка данных (с подтверждением) ───────────────────────────────────────

@bot.callback_query_handler(func=lambda c: c.data in ["confirm_yes", "confirm_no"])
def cb_clear_confirm(call: CallbackQuery):
    """Обрабатывает подтверждение очистки."""
    user_id = call.from_user.id
    
    if call.data == "confirm_yes":
        success = db_handler.clear_user_data(user_id)
        text = "🗑 *Данные удалены.*\nНачни заново с /add" if success else "❌ Ошибка при удалении."
    else:
        text = "✅ Отмена. Данные сохранены."
    
    bot.edit_message_text(
        text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.get_main_keyboard()
    )
    bot.answer_callback_query(call.id)
    reset_session(user_id)


# ─── Запуск ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("🚀 Инициализация базы данных...")
    db_handler.init_db()
    
    logger.info("✅ Бот запущен. Ожидание сообщений...")
    print("🤖 Бот работает! Нажми Ctrl+C для остановки.")
    

