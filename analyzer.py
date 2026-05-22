import io
import logging
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # Обязательно для серверной среды
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

logger = logging.getLogger(__name__)

# Эмодзи для оценок настроения
MOOD_EMOJI = {1: "😞", 2: "😐", 3: "🙂", 4: "😊", 5: "🤩"}


def _mood_bar(value: float, max_val: float = 5) -> str:
    """Создаёт текстовый прогресс-бар для наглядности."""
    filled = round((value / max_val) * 10)
    return "█" * filled + "░" * (10 - filled)


def format_stats_message(entries: list, days: int) -> str:
    """Формирует текстовое сообщение со статистикой за период."""
    if not entries:
        return f"📭 За последние {days} дней у меня нет твоих данных.\nНачни с команды /add!"

    total = len(entries)
    avg_mood = sum(e["mood"] for e in entries) / total
    avg_work = sum(float(e["work_hours"]) for e in entries) / total
    avg_sleep = sum(float(e["sleep_hours"]) for e in entries) / total
    
    mood_emoji = MOOD_EMOJI.get(round(avg_mood), "🙂")
    
    lines = [
        f"📊 *Статистика за {days} дней* ({total} записей)\n",
        f"😊 *Настроение*",
        f"  Среднее: {avg_mood:.1f}/5 {mood_emoji}",
        f"  {_mood_bar(avg_mood)}",
        "",
        f"💼 *Работа/учёба*",
        f"  Среднее: {avg_work:.1f} ч/день",
        "",
        f"😴 *Сон*",
        f"  Среднее: {avg_sleep:.1f} ч/ночь",
    ]
    
    # Быстрые выводы
    conclusions = []
    if avg_sleep < 6.5:
        conclusions.append("⚠️ Ты мало спишь! Рекомендуется 7–9 часов.")
    elif avg_sleep >= 8:
        conclusions.append("✅ Отличный режим сна!")
    
    if avg_work > 8:
        conclusions.append("⚠️ Высокая нагрузка — не забывай отдыхать.")
    
    if avg_mood >= 4:
        conclusions.append("🌟 Настроение на высоте — так держать!")
    elif avg_mood <= 2:
        conclusions.append("💙 Непростой период. Позаботься о себе.")
    
    if conclusions:
        lines.append("")
        lines.append("💡 *Быстрые выводы:*")
        lines.extend([f"  {c}" for c in conclusions])
    
    return "\n".join(lines)


def format_history_message(entries: list, days: int) -> str:
    """Форматирует историю записей за N дней."""
    if not entries:
        return "📭 Записей за этот период нет."
    
    lines = [f"📋 *История за {days} дней:*\n"]
    for rec in entries[-10:]:  # Показываем последние 10
        mood_e = MOOD_EMOJI.get(rec["mood"], "")
        comment = f"\n     💬 _{rec['comment']}_" if rec.get("comment") else ""
        lines.append(
            f"📅 *{rec['entry_date']}*\n"
            f"   Настроение: {rec['mood']}/5 {mood_e} | "
            f"Сон: {rec['sleep_hours']} ч | "
            f"Работа: {rec['work_hours']} ч{comment}"
        )
    return "\n".join(lines)


def generate_chart(entries: list, days: int = 14) -> io.BytesIO | None:
    """Генерирует график динамики настроения. Возвращает BytesIO с PNG."""
    if len(entries) < 2:
        return None
    
    # Подготовка данных
    dates = [rec["entry_date"] for rec in entries]
    moods = [float(rec["mood"]) for rec in entries]
    
    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")
    
    # Основной график
    ax.plot(dates, moods, color="#e94560", linewidth=2, marker="o", markersize=5)
    ax.fill_between(dates, moods, alpha=0.2, color="#e94560")
    
    # Настройка осей
    ax.set_ylim(1, 5)
    ax.set_ylabel("Настроение (1–5)", color="white")
    ax.tick_params(colors="white")
    ax.spines["bottom"].set_color("#444")
    ax.spines["top"].set_visible(False)
    ax.spines["left"].set_color("#444")
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.2, color="white")
    
    # Среднее значение
    avg = sum(moods) / len(moods)
    ax.axhline(avg, color="yellow", linewidth=0.8, linestyle="--", alpha=0.5)
    
    # Форматирование дат
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    plt.xticks(rotation=45, ha="right", color="white")
    
    # Заголовок
    plt.title(f"📈 Динамика настроения за {days} дней", color="white", pad=15)
    plt.tight_layout()
    
    # Сохранение в память
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    
    return buf  