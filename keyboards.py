import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура (всегда видна внизу)."""
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        KeyboardButton("➕ Записать день"),
        KeyboardButton("📊 Статистика")
    )
    kb.add(
        KeyboardButton("📜 История"),
        KeyboardButton("⚙️ Настройки")
    )
    kb.add(KeyboardButton("ℹ️ Помощь"))
    return kb


def get_mood_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-кнопки для выбора настроения 1–5."""
    kb = InlineKeyboardMarkup(row_width=5)
    buttons = [
        InlineKeyboardButton(f"{i} {emo}", callback_data=f"mood_{i}")
        for i, emo in [(1,"😞"), (2,"😐"), (3,"🙂"), (4,"😊"), (5,"🤩")]
    ]
    kb.add(*buttons)
    return kb


def get_work_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-кнопки для выбора часов работы."""
    kb = InlineKeyboardMarkup(row_width=5)
    options = [
        ("0.5 ч", "work_0.5"), ("1 ч", "work_1"), ("2 ч", "work_2"),
        ("4 ч", "work_4"), ("Другое", "work_custom")
    ]
    kb.add(*[InlineKeyboardButton(t, d) for t, d in options])
    return kb


def get_sleep_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-кнопки для выбора часов сна."""
    kb = InlineKeyboardMarkup(row_width=5)
    options = [
        ("6 ч", "sleep_6"), ("7 ч", "sleep_7"), ("8 ч", "sleep_8"),
        ("9 ч", "sleep_9"), ("Другое", "sleep_custom")
    ]
    kb.add(*[InlineKeyboardButton(t, d) for t, d in options])
    return kb


def get_comment_keyboard() -> InlineKeyboardMarkup:
    """Кнопка «Пропустить» для комментария."""
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⏭ Пропустить", callback_data="comment_skip"))
    return kb


def get_stats_keyboard() -> InlineKeyboardMarkup:
    """Меню статистики."""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📅 За неделю", callback_data="stats_7"),
        InlineKeyboardButton("🗓 За месяц", callback_data="stats_30")
    )
    kb.add(InlineKeyboardButton("📉 График", callback_data="stats_chart"))
    return kb


def get_history_keyboard() -> InlineKeyboardMarkup:
    """Меню истории."""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📅 7 дней", callback_data="hist_7"),
        InlineKeyboardButton("🗓 30 дней", callback_data="hist_30")
    )
    return kb


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение опасного действия."""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Да", callback_data="confirm_yes"),
        InlineKeyboardButton("❌ Нет", callback_data="confirm_no")
    )
    return kb