import telebot
import re 
from telebot import types
from telebot import apihelper
import os
import logging
from dotenv import load_dotenv
import db_handler as db
import analyzer

telebot.logger.setLevel(logging.DEBUG)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("ОШИБКА: Токен бота не найден")

# apihelper.proxy = {'https': 'http://127.0.0.1:7890'}  

bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}

def create_kb(buttons, row_width=2, inline=False):
    kb = types.InlineKeyboardMarkup(row_width=row_width) if inline else types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=row_width)
    kb.add(*[types.InlineKeyboardButton(t, callback_data=c) if inline else types.KeyboardButton(t) for t, c in buttons])
    return kb

MAIN_KB = create_kb([("Добавить день", "add"), ("Статистика", "stats"), ("История", "history"), ("Настройки", "settings")])
MOOD_KB = create_kb([(f"{i} {['😞','😐','🙂','😊','🤩'][i-1]}", f"mood_{i}") for i in range(1,6)], 5, True)
WORK_KB = create_kb([(f"{h} ч", f"work_{h}") for h in [0.5,1,2,4,6,8]] + [("Другое", "work_custom")], 4, True)
SLEEP_KB = create_kb([(f"{h} ч", f"sleep_{h}") for h in range(5,11)] + [("Другое", "sleep_custom")], 4, True)

def next_step(uid, state, **kwargs):
    user_states[uid] = {**(user_states.get(uid, {})), "state": state, **kwargs}

@bot.message_handler(commands=["start"])
def start(m):
    db.ensure_user(m.from_user.id, m.from_user.username or "")
    user_states[m.from_user.id] = "idle"
    bot.send_message(m.chat.id, " Привет! Я трекер самочувствия.", reply_markup=MAIN_KB)

@bot.message_handler(func=lambda m: m.text == "Добавить день")
def add_entry(m):
    next_step(m.from_user.id, "mood")
    bot.send_message(m.chat.id, "Шаг 1/4: Настроение?", reply_markup=MOOD_KB)

@bot.callback_query_handler(func=lambda c: c.data.startswith(("mood_", "work_", "sleep_", "skip_", "stats_", "history_", "clear_")))
def handle_callbacks(c):
    uid, data = c.from_user.id, c.data
    db.ensure_user(uid, c.from_user.username or "")
    
    if data.startswith("mood_"):
        next_step(uid, "work", mood=int(data.split("_")[1]))
        bot.edit_message_text(f" Настроение принято", c.message.chat.id, c.message.message_id)
        bot.send_message(c.message.chat.id, "Шаг 2/4: Часы работы?", reply_markup=WORK_KB)

    elif data.startswith("work_"):
        val = data.split("_")[1]
        if val == "custom":
            next_step(uid, "work_custom")
            bot.edit_message_text("Введи число часов:", c.message.chat.id, c.message.message_id)
        else:
            next_step(uid, "sleep", work_hours=float(val))
            bot.edit_message_text(f"Работа: {val}ч", c.message.chat.id, c.message.message_id)
            bot.send_message(c.message.chat.id, "Шаг 3/4: Часы сна?", reply_markup=SLEEP_KB)

    elif data.startswith("sleep_"):
        val = data.split("_")[1]
        if val == "custom":
            next_step(uid, "sleep_custom")
            bot.edit_message_text("Введи число часов сна:", c.message.chat.id, c.message.message_id)
        else:
            next_step(uid, "comment", sleep_hours=float(val))
            bot.edit_message_text(f" Сон: {val}ч", c.message.chat.id, c.message.message_id)
            bot.send_message(c.message.chat.id, "Шаг 4/4: Коммент (или /skip)", reply_markup=create_kb([("Пропустить", "skip_comment")], 1, True))

    elif data == "skip_comment":
        save_and_finish(c.message.chat.id, uid, None)
        bot.edit_message_text("Запись сохранена!", c.message.chat.id, c.message.message_id)

    elif data.startswith("stats_"):
        if data == "stats_week":
            text = analyzer.get_stats(uid, 7)
            bot.edit_message_text(text, c.message.chat.id, c.message.message_id, parse_mode="Markdown")
        elif data == "stats_month":
            text = analyzer.get_stats(uid, 30)
            bot.edit_message_text(text, c.message.chat.id, c.message.message_id, parse_mode="Markdown")
        elif data == "stats_insights":
            text = analyzer.get_insights(uid)
            bot.edit_message_text(text, c.message.chat.id, c.message.message_id, parse_mode="Markdown")
        elif data == "stats_chart":
            img = analyzer.get_chart(uid)
            if img: 
                bot.send_photo(c.message.chat.id, img)
            else: 
                bot.send_message(c.message.chat.id, "Мало данных для графика")

    elif data.startswith("history_"):
        page = int(data.split("_")[1])
        entries, total = db.get_history(uid, page=page)
        text = "\n".join([f"#{e['id']} | {e['created_at'][:10]} | {e['mood']}" for e in entries]) if entries else "Пусто"
        kb = create_kb([("<", f"history_{page-1}"), (">", f"history_{page+1}")], 2, True) if len(entries)==5 else None
        bot.edit_message_text(text, c.message.chat.id, c.message.message_id, reply_markup=kb)

    bot.answer_callback_query(c.id)

@bot.message_handler(content_types=["text"])
def handle_text(m):
    uid, text = m.from_user.id, m.text.strip()
    state = user_states.get(uid, {})
    
    if isinstance(state, dict):
        s = state.get("state")
        if s == "work_custom":
            try: 
                next_step(uid, "sleep", work_hours=float(text.replace(",",".")))
                bot.send_message(m.chat.id, "Шаг 3/4: Часы сна?", reply_markup=SLEEP_KB)
            except: 
                bot.send_message(m.chat.id, "Ошибка ввода")
        elif s == "sleep_custom":
            try: 
                next_step(uid, "comment", sleep_hours=float(text.replace(",",".")))
                bot.send_message(m.chat.id, "Шаг 4/4: Комментарий?")
            except: 
                bot.send_message(m.chat.id, "Ошибка ввода")
        elif s == "comment":
            save_and_finish(m.chat.id, uid, text)
        elif s == "settings_time" and re.match(r"^\d{2}:\d{2}$", text):
            db.save_settings(uid, text)
            bot.send_message(m.chat.id, f"Время установлено: {text}", reply_markup=MAIN_KB)
            user_states[uid] = "idle"
    elif text == "Статистика":
        bot.send_message(m.chat.id, "Выбери период:", reply_markup=create_kb([("Неделя", "stats_week"), ("Месяц", "stats_month"), ("Факты", "stats_insights"), ("График", "stats_chart")], 2, True))
    elif text == "История":
        entries, total = db.get_history(uid, page=0)
        text = "\n".join([f"#{e['id']} | {e['created_at'][:10]} | {e['mood']}" for e in entries]) if entries else "Пусто"
        kb = create_kb([("<", "history_0"), (">", "history_1")], 2, True) if len(entries)==5 else None
        bot.send_message(m.chat.id, text, reply_markup=kb)
    elif text == "Настройки":
        user_states[uid] = {"state": "settings_time"}
        bot.send_message(m.chat.id, "Введи время (ЧЧ:ММ):")
    else:
        bot.send_message(m.chat.id, "Жми кнопки меню", reply_markup=MAIN_KB)

def save_and_finish(chat_id, uid, comment):
    s = user_states.get(uid, {})
    if all(k in s for k in ["mood", "work_hours", "sleep_hours"]):
        db.add_entry(uid, s["mood"], s["work_hours"], s["sleep_hours"], comment)
        bot.send_message(chat_id, "Готово!", reply_markup=MAIN_KB)
    user_states[uid] = "idle"

if __name__ == "__main__":
    db.init_db()
    print("Бот запущен и слушает сообщения...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
