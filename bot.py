import telebot
from telebot import types
import os
from dotenv import load_dotenv
import db_handler as db
import analyzer
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
 
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
 
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}

STATE_IDLE = "idle"
STATE_MOOD = "mood"
STATE_WORK = "work"
STATE_WORK_CUSTOM = "work_custom"
STATE_SLEEP = "sleep"
STATE_SLEEP_CUSTOM = "sleep_custom"
STATE_COMMENT = "comment"
STATE_CLEAR_CONFIRM = "clear_confirm"
STATE_SETTINGS_TIME = "settings_time"

def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        types.KeyboardButton("+ Добавить день"),
        types.KeyboardButton("📊 Посмотреть статистику"),
        types.KeyboardButton("📜 Посмотреть историю"),
        types.KeyboardButton("⚙️ Настройки"),
        types.KeyboardButton("? Помощь")
    )
    return kb
 
def mood_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=5)
    moods = [
        ("1 😞", "mood_1"),
        ("2 😐", "mood_2"),
        ("3 🙂", "mood_3"),
        ("4 😊", "mood_4"),
        ("5 🤩", "mood_5"),
    ]
    kb.add(*[types.InlineKeyboardButton(text, callback_data=cd) for text, cd in moods])
    return kb
 
def work_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=4)
    options = [
        ("0.5 ч", "work_0.5"),
        ("1 ч", "work_1"),
        ("2 ч", "work_2"),
        ("4 ч", "work_4"),
        ("6 ч", "work_6"),
        ("8 ч", "work_8"),
        ("Другое", "work_custom"),
    ]
    kb.add(*[types.InlineKeyboardButton(text, callback_data=cd) for text, cd in options])
    return kb
 
def sleep_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=4)
    options = [
        ("5 ч", "sleep_5"),
        ("6 ч", "sleep_6"),
        ("7 ч", "sleep_7"),
        ("8 ч", "sleep_8"),
        ("9 ч", "sleep_9"),
        ("10 ч", "sleep_10"),
        ("✏️ Другое", "sleep_custom"),
    ]
    kb.add(*[types.InlineKeyboardButton(text, callback_data=cd) for text, cd in options])
    return kb
 
def skip_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(">> Пропустить", callback_data="skip_comment"))
    return kb
 
def stats_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("За неделю", callback_data="stats_week"),
        types.InlineKeyboardButton("За месяц", callback_data="stats_month"),
        types.InlineKeyboardButton("Мои интересные факты", callback_data="stats_insights"),
        types.InlineKeyboardButton("График", callback_data="stats_chart"),
    )
    return kb
 
def confirm_clear_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ Удалить", callback_data="clear_confirm"),
        types.InlineKeyboardButton("❌ Отмена", callback_data="clear_cancel"),
    )
    return kb
 
def history_keyboard(page: int, total_pages: int):
    kb = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    if page > 0:
        buttons.append(types.InlineKeyboardButton("< Назад", callback_data=f"history_{page - 1}"))
    buttons.append(types.InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        buttons.append(types.InlineKeyboardButton("Вперёд >", callback_data=f"history_{page + 1}"))
    kb.add(*buttons)
    return kb
 
@bot.message_handler(commands=["start"])
def cmd_start(message):
    db.ensure_user(message.from_user.id, message.from_user.username or "")
    user_states[message.from_user.id] = STATE_IDLE
    text = (
        "👋 *Ассаляму алейкум! Я - бот-трекер самочувствия*\n\n"
        "Я помогаю отслеживать три ключевых показателя каждый день:\n"
        "😊 *Настроение* — от 1 до 5\n"
        "📚 *Часы работы/учёбы*\n"
        "😴 *Часы сна*\n\n"
        "На основе твоих данных показываю твой режим жизни\n"
        "Выбери действие в меню ниже 👇"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=main_keyboard())
 
@bot.message_handler(commands=["help"])
def cmd_help(message):
    text = (
        "📖 *Справка по командам:*\n\n"
        "+ *Записать день* — добавить новую запись\n"
        "📊 *Статистика* — аналитика\n"
        "📜 *История* — все твои записи\n"
        "⚙️ *Настройки* — время напоминания\n"
        "? *Помощь* — эта справка\n\n"
        "*/clear* — очистить данные\n\n"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=main_keyboard())
 
@bot.message_handler(commands=["add"])
@bot.message_handler(func=lambda m: m.text == "+ Записать день")
def cmd_add(message):
    db.ensure_user(message.from_user.id, message.from_user.username or "")
    user_states[message.from_user.id] = STATE_MOOD
    bot.send_message(
        message.chat.id,
        "📝 *Шаг 1 из 4 — Настроение*\n\nОцени своё настроение прямо сейчас:",
        parse_mode="Markdown",
        reply_markup=mood_keyboard()
    )
 
@bot.message_handler(commands=["stats"])
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def cmd_stats(message):
    db.ensure_user(message.from_user.id, message.from_user.username or "")
    bot.send_message(
        message.chat.id,
        "📊 *Статистика*\n\nЧто хочешь узнать?",
        parse_mode="Markdown",
        reply_markup=stats_keyboard()
    )
 
@bot.message_handler(commands=["history"])
@bot.message_handler(func=lambda m: m.text == "📜 История")
def cmd_history(message):
    db.ensure_user(message.from_user.id, message.from_user.username or "")
    send_history_page(message.chat.id, message.from_user.id, 0)
 
@bot.message_handler(commands=["settings"])
@bot.message_handler(func=lambda m: m.text == "⚙️ Настройки")
def cmd_settings(message):
    db.ensure_user(message.from_user.id, message.from_user.username or "")
    settings = db.get_settings(message.from_user.id)
    reminder = settings.get("reminder_time", "16:00") if settings else "20:00"
    text = (
        f"⚙️ *Настройки*\n\n"
        f"🔔 Время напоминания: *{reminder}*\n\n"
        "Чтобы изменить, напиши время в формате *ЧЧ:ММ*\n"
        "Например: `09:00` или `21:30`"
    )
    user_states[message.from_user.id] = STATE_SETTINGS_TIME
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
 
@bot.message_handler(commands=["clear"])
def cmd_clear(message):
    db.ensure_user(message.from_user.id, message.from_user.username or "")
    user_states[message.from_user.id] = STATE_CLEAR_CONFIRM
    bot.send_message(
        message.chat.id,
        "⚠️ *Вы уверены?*\n\nВсе твои записи будут *удалены*.",
        parse_mode="Markdown",
        reply_markup=confirm_clear_keyboard()
    )
 
@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
def btn_help(message):
    cmd_help(message)
 
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message):
    uid = message.from_user.id
    state = user_states.get(uid, STATE_IDLE)
    text = message.text.strip()
 
    if state == STATE_WORK_CUSTOM:
        try:
            hours = float(text.replace(",", "."))
            if not (0 <= hours <= 24):
                raise ValueError
            user_states[uid] = {**user_states[uid], "state": STATE_SLEEP, "work_hours": hours}
            ask_sleep(message.chat.id)
        except ValueError:
            bot.send_message(message.chat.id, "❌ Введи число от 0 до 24, например: `3.5`", parse_mode="Markdown")
    elif state == STATE_SLEEP_CUSTOM:
        try:
            hours = float(text.replace(",", "."))
            if not (0 <= hours <= 24):
                raise ValueError
            user_states[uid] = {**user_states[uid], "state": STATE_COMMENT, "sleep_hours": hours}
            ask_comment(message.chat.id)
        except ValueError:
            bot.send_message(message.chat.id, "❌ Введи число от 0 до 24, например: `7.5`", parse_mode="Markdown")
    elif isinstance(state, dict) and state.get("state") == STATE_WORK_CUSTOM:
        try:
            hours = float(text.replace(",", "."))
            if not (0 <= hours <= 24):
                raise ValueError
            user_states[uid]["work_hours"] = hours
            user_states[uid]["state"] = STATE_SLEEP
            ask_sleep(message.chat.id)
        except ValueError:
            bot.send_message(message.chat.id, "❌ Введи число от 0 до 24, например: `3.5`", parse_mode="Markdown") 
    elif isinstance(state, dict) and state.get("state") == STATE_SLEEP_CUSTOM:
        try:
            hours = float(text.replace(",", "."))
            if not (0 <= hours <= 24):
                raise ValueError
            user_states[uid]["sleep_hours"] = hours
            user_states[uid]["state"] = STATE_COMMENT
            ask_comment(message.chat.id)
        except ValueError:
            bot.send_message(message.chat.id, "❌ Введи число от 0 до 24, например: `7.5`", parse_mode="Markdown")
    elif isinstance(state, dict) and state.get("state") == STATE_COMMENT:
        save_entry(message.chat.id, uid, comment=text)
    elif state == STATE_SETTINGS_TIME:
        import re
        if re.match(r"^\d{2}:\d{2}$", text):
            h, m = map(int, text.split(":"))
            if 0 <= h <= 23 and 0 <= m <= 59:
                db.save_settings(uid, reminder_time=text)
                user_states[uid] = STATE_IDLE
                bot.send_message(
                    message.chat.id,
                    f"✅ Время напоминания установлено: *{text}*",
                    parse_mode="Markdown",
                    reply_markup=main_keyboard()
                )
                return
        bot.send_message(message.chat.id, "❌ Неподходящий формат. Введи время как `ЧЧ:ММ`, например `20:00`", parse_mode="Markdown")
 
    else:
        bot.send_message(
            message.chat.id,
            "Выбери действие в меню 👇",
            reply_markup=main_keyboard()
        )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    uid = call.from_user.id
    data = call.data
    db.ensure_user(uid, call.from_user.username or "")

    if data.startswith("mood_"):
        mood = int(data.split("_")[1])
        user_states[uid] = {"state": STATE_WORK, "mood": mood}
        mood_labels = {1: "😞 Ужасно", 2: "😐 Плохо", 3: "🙂 Нормально", 4: "😊 Хорошо", 5: "🤩 Отлично"}
        bot.edit_message_text(
            f"✅ Настроение: *{mood_labels[mood]}*",
            call.message.chat.id, call.message.message_id,
            parse_mode="Markdown"
        )
        ask_work(call.message.chat.id)
 
    elif data.startswith("work_"):
        val = data.split("_")[1]
        if val == "custom":
            user_states[uid]["state"] = STATE_WORK_CUSTOM
            bot.edit_message_text(
                "✏️ Введи количество часов работы/учёбы (например: `3.5`):",
                call.message.chat.id, call.message.message_id,
                parse_mode="Markdown"
            )
        else:
            hours = float(val)
            user_states[uid]["work_hours"] = hours
            user_states[uid]["state"] = STATE_SLEEP
            bot.edit_message_text(
                f"✅ Часы работы/учёбы: *{hours} ч*",
                call.message.chat.id, call.message.message_id,
                parse_mode="Markdown"
            )
            ask_sleep(call.message.chat.id)
 
    elif data.startswith("sleep_"):
        val = data.split("_")[1]
        if val == "custom":
            user_states[uid]["state"] = STATE_SLEEP_CUSTOM
            bot.edit_message_text(
                "Введи количество часов сна (например: `7.5`):",
                call.message.chat.id, call.message.message_id,
                parse_mode="Markdown"
            )
        else:
            hours = float(val)
            user_states[uid]["sleep_hours"] = hours
            user_states[uid]["state"] = STATE_COMMENT
            bot.edit_message_text(
                f"✅ Часы сна: *{hours} ч*",
                call.message.chat.id, call.message.message_id,
                parse_mode="Markdown"
            )
            ask_comment(call.message.chat.id)
 
    elif data == "skip_comment":
        bot.edit_message_text(
            ">> Комментарий пропущен.",
            call.message.chat.id, call.message.message_id
        )
        save_entry(call.message.chat.id, uid, comment=None)
 
    elif data == "stats_week":
        text = analyzer.get_week_stats(uid)
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    elif data == "stats_month":
        text = analyzer.get_month_stats(uid)
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown") 
    elif data == "stats_insights":
        text = analyzer.get_insights(uid)
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    elif data == "stats_chart":
        bot.answer_callback_query(call.id, "⏳ Строю график...")
        img = analyzer.get_chart(uid)
        if img:
            bot.send_photo(call.message.chat.id, img, caption="Твой график за последние 30 дней")
        else:
            bot.send_message(
                call.message.chat.id,
                "📊 Добавь хотя бы *1 запись*, чтобы увидеть график!",
                parse_mode="Markdown"
            )

    elif data.startswith("history_"):
        page = int(data.split("_")[1])
        send_history_page(call.message.chat.id, uid, page, message_id=call.message.message_id)
 
    elif data == "noop":
        bot.answer_callback_query(call.id)

    elif data == "clear_confirm":
        db.clear_user_data(uid)
        user_states[uid] = STATE_IDLE
        bot.edit_message_text(
            "🗑 Все твои данные удалены.",
            call.message.chat.id, call.message.message_id
        )
        bot.send_message(call.message.chat.id, "Давай заново", reply_markup=main_keyboard())
    elif data == "clear_cancel":
        user_states[uid] = STATE_IDLE
        bot.edit_message_text(
            "✅ Отмена. Данные сохранены.",
            call.message.chat.id, call.message.message_id
        )

    bot.answer_callback_query(call.id)
 
def ask_work(chat_id):
    bot.send_message(
        chat_id,
        "📝 *Шаг 2 из 4 — Работа/учёба*\n\nСколько часов ты потратил на полезную работу/учёбу?",
        parse_mode="Markdown",
        reply_markup=work_keyboard()
    )
 
def ask_sleep(chat_id):
    bot.send_message(
        chat_id,
        "📝 *Шаг 3 из 4 — Сон*\n\nСколько часов ты спал?",
        parse_mode="Markdown",
        reply_markup=sleep_keyboard()
    )
  
def ask_comment(chat_id):
    bot.send_message(
        chat_id,
        "📝 *Шаг 4 из 4 — Комментарий (необязательно)*\n\nХочешь добавить заметку о дне?\nНапиши текст или нажми «Пропустить»",
        parse_mode="Markdown",
        reply_markup=skip_keyboard()
    )
 
def save_entry(chat_id, uid, comment):
    state = user_states.get(uid, {})
    if not isinstance(state, dict):
        bot.send_message(chat_id, "❌ Что-то пошло не так. Начни заново: /add")
        return
 
    mood = state.get("mood")
    work = state.get("work_hours")
    sleep = state.get("sleep_hours")
    if mood is None or work is None or sleep is None:
        bot.send_message(chat_id, "❌ Данные неполны. Начни заново: /add")
        return
    entry_id = db.add_entry(uid, mood, work, sleep, comment)
    user_states[uid] = STATE_IDLE
    mood_labels = {1: "😞", 2: "😐", 3: "🙂", 4: "😊", 5: "🤩"}
    comment_text = f"\n💬 _{comment}_" if comment else ""
 
    text = (
        f"✅ *Запись #{entry_id} сохранена!*\n\n"
        f"😊 Настроение: *{mood}/5* {mood_labels.get(mood, '')}\n"
        f"📚 Работа/учёба: *{work} ч*\n"
        f"😴 Сон: *{sleep} ч*"
        f"{comment_text}\n\n"
        f"_Можешь добавить ещё одну запись в любое время_"
    )
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=main_keyboard())
 
 
def send_history_page(chat_id, uid, page, message_id=None):
    entries, total = db.get_history(uid, page=page, per_page=5)
    if not entries:
        msg = "📜 *История чиста*\n\nДобавь запись через + Записать день!"
        if message_id:
            bot.edit_message_text(msg, chat_id, message_id, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=main_keyboard())
        return
 
    import math
    total_pages = max(1, math.ceil(total / 5))
    mood_labels = {1: "😞", 2: "😐", 3: "🙂", 4: "😊", 5: "🤩"}
 
    lines = [f"📜 *История* (стр. {page + 1}/{total_pages}):\n"]
    for e in entries:
        dt = e["created_at"]
        if hasattr(dt, "strftime"):
            dt_str = dt.strftime("%d.%m.%Y %H:%M")
        else:
            dt_str = str(dt)[:16]
        comment = f"\n   💬 _{e['comment']}_" if e.get("comment") else ""
        lines.append(
            f"*#{e['id']}* | {dt_str}\n"
            f"   {mood_labels.get(e['mood'], '')} {e['mood']}/5 | 📚 {e['work_hours']}ч | 😴 {e['sleep_hours']}ч"
            f"{comment}\n"
        )
 
    text = "\n".join(lines)
    kb = history_keyboard(page, total_pages)
 
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=kb)
    else:
        bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=kb)
 
def send_reminders():
    now = datetime.now().strftime("%H:%M")
    users = db.get_users_with_reminder(now)
    for user in users:
        try:
            bot.send_message(
                user["telegram_id"],
                "🔔 *Напоминание!*\n\nНе забудь записать свой день",
                parse_mode="Markdown",
                reply_markup=main_keyboard()
            )
        except Exception:
            pass
 
if __name__ == "__main__":
    db.init_db()
    print("БД обнаружена")
 
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_reminders, "cron", minute="*")
    scheduler.start()
    print("Планировщик запущен")
 
    print("Бот запущен")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)