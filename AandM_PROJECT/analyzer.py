import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import db_handler as db

MOOD_EMOJI = {1: "😞", 2: "😐", 3: "🙂", 4: "😊", 5: "🤩"}

def _mood_label(score: float) -> str:
    rounded = max(1, min(5, round(score)))
    return f"{score:.1f} {MOOD_EMOJI.get(rounded, '')}"

def get_week_stats(telegram_id: int) -> str:
    stats = db.get_aggregated_stats(telegram_id, days=7)
    entries = db.get_entries_for_period(telegram_id, days=7)

    if not stats or stats.get("cnt", 0) == 0:
        return (
            "📅 *Статистика за неделю*\n\n"
            "Записей пока нет.\nДобавь первую через ➕ Записать день!"
        )

    cnt = stats["cnt"]
    best = db.get_best_day(telegram_id, days=7)
    best_day_str = ""
    if best:
        try:
            d = datetime.strptime(best["day"], "%Y-%m-%d")
            best_day_str = f"\n🏆 Лучший день: *{d.strftime('%d.%m')}* (настроение {best['avg_mood']:.1f})"
        except Exception:
            pass

    return (
        f"📅 *Статистика за 7 дней*\n\n"
        f"📊 Всего записей: *{cnt}*\n\n"
        f"😊 *Настроение:*\n"
        f"   Среднее: {_mood_label(stats['avg_mood'])}\n"
        f"   Мин: {stats['min_mood']}  |  Макс: {stats['max_mood']}\n\n"
        f"📚 *Работа/учёба:*\n"
        f"   Среднее: *{stats['avg_work']} ч*\n"
        f"   Мин: {stats['min_work']}ч  |  Макс: {stats['max_work']}ч\n\n"
        f"😴 *Сон:*\n"
        f"   Среднее: *{stats['avg_sleep']} ч*\n"
        f"   Мин: {stats['min_sleep']}ч  |  Макс: {stats['max_sleep']}ч"
        f"{best_day_str}"
    )

def get_month_stats(telegram_id: int) -> str:
    stats = db.get_aggregated_stats(telegram_id, days=30)

    if not stats or stats.get("cnt", 0) == 0:
        return (
            "🗓 *Статистика за месяц*\n\n"
            "Записей пока нет.\nДобавь первую через ➕ Записать день!"
        )

    cnt = stats["cnt"]
    best = db.get_best_day(telegram_id, days=30)
    best_day_str = ""
    if best:
        try:
            d = datetime.strptime(best["day"], "%Y-%m-%d")
            best_day_str = f"\n🏆 Лучший день: *{d.strftime('%d.%m')}* (настроение {best['avg_mood']:.1f})"
        except Exception:
            pass

    return (
        f"🗓 *Статистика за 30 дней*\n\n"
        f"📊 Всего записей: *{cnt}*\n\n"
        f"😊 *Настроение:*\n"
        f"   Среднее: {_mood_label(stats['avg_mood'])}\n"
        f"   Мин: {stats['min_mood']}  |  Макс: {stats['max_mood']}\n\n"
        f"📚 *Работа/учёба:*\n"
        f"   Среднее: *{stats['avg_work']} ч*\n"
        f"   Мин: {stats['min_work']}ч  |  Макс: {stats['max_work']}ч\n\n"
        f"😴 *Сон:*\n"
        f"   Среднее: *{stats['avg_sleep']} ч*\n"
        f"   Мин: {stats['min_sleep']}ч  |  Макс: {stats['max_sleep']}ч"
        f"{best_day_str}"
    )

def get_insights(telegram_id: int) -> str:
    sleep_data = db.get_mood_by_sleep_buckets(telegram_id, days=30)
    work_data = db.get_mood_by_work_buckets(telegram_id, days=30)
    entries = db.get_entries_for_period(telegram_id, days=30)
    stats = db.get_aggregated_stats(telegram_id, days=30)

    if not entries:
        return (
            "🔍 *Мои инсайты*\n\n"
            "Недостаточно данных для анализа.\n"
            "Добавь хотя бы несколько записей!"
        )
    lines = ["🔍 *Мои инсайты за 30 дней*\n"]

    if sleep_data and len(sleep_data) >= 2:
        best_sleep = max(sleep_data, key=lambda x: x["avg_mood"])
        worst_sleep = min(sleep_data, key=lambda x: x["avg_mood"])
        lines.append(
            f"😴 *Сон и настроение:*\n"
            f"   Лучшее настроение при сне *{best_sleep['sleep_bucket']}* "
            f"— avg {best_sleep['avg_mood']:.1f}\n"
            f"   Худшее настроение при сне *{worst_sleep['sleep_bucket']}* "
            f"— avg {worst_sleep['avg_mood']:.1f}\n"
        )
    elif sleep_data:
        lines.append(
            f"😴 *Сон и настроение:*\n"
            f"   При сне {sleep_data[0]['sleep_bucket']} "
            f"среднее настроение: {sleep_data[0]['avg_mood']:.1f}\n"
        )

    if work_data and len(work_data) >= 2:
        best_work = max(work_data, key=lambda x: x["avg_mood"])
        worst_work = min(work_data, key=lambda x: x["avg_mood"])
        lines.append(
            f"📚 *Работа и настроение:*\n"
            f"   Лучшее настроение при *{best_work['work_bucket']}* работы "
            f"— avg {best_work['avg_mood']:.1f}\n"
            f"   Худшее настроение при *{worst_work['work_bucket']}* работы "
            f"— avg {worst_work['avg_mood']:.1f}\n"
        )
    elif work_data:
        lines.append(
            f"📚 *Работа и настроение:*\n"
            f"   При {work_data[0]['work_bucket']} работы "
            f"среднее настроение: {work_data[0]['avg_mood']:.1f}\n"
        )

    if len(entries) >= 3:
        avg_sleep = stats.get("avg_sleep", 0)
        high_sleep = [e for e in entries if e["sleep_hours"] >= avg_sleep]
        low_sleep = [e for e in entries if e["sleep_hours"] < avg_sleep]

        if high_sleep and low_sleep:
            avg_work_high = sum(e["work_hours"] for e in high_sleep) / len(high_sleep)
            avg_work_low = sum(e["work_hours"] for e in low_sleep) / len(low_sleep)
            diff = avg_work_high - avg_work_low
            emoji = "⬆️" if diff > 0 else "⬇️"
            lines.append(
                f"💡 *Сон → Продуктивность:*\n"
                f"   Когда ты спишь ≥ {avg_sleep:.1f}ч, работаешь в среднем "
                f"*{avg_work_high:.1f}ч* {emoji}\n"
                f"   Когда меньше — *{avg_work_low:.1f}ч*\n"
            )

    if len(entries) >= 4:
        half = len(entries) // 2
        first_half = entries[:half]
        second_half = entries[half:]
        avg_first = sum(e["mood"] for e in first_half) / len(first_half)
        avg_second = sum(e["mood"] for e in second_half) / len(second_half)
        trend = avg_second - avg_first
        if abs(trend) >= 0.3:
            direction = "улучшается 📈" if trend > 0 else "снижается 📉"
            lines.append(f"📊 *Тренд настроения:* {direction} (Δ{trend:+.1f})\n")
    if len(lines) == 1:
        lines.append("Добавь больше записей для детального анализа!")
    return "\n".join(lines)

def get_chart(telegram_id: int) -> io.BytesIO | None:
    daily = db.get_daily_averages(telegram_id, days=30)
    if not daily:
        return None
    dates = []
    moods = []
    works = []
    sleeps = []
    for row in daily:
        try:
            d = datetime.strptime(row["day"], "%Y-%m-%d")
        except Exception:
            continue
        dates.append(d)
        moods.append(row["avg_mood"])
        works.append(row["avg_work"])
        sleeps.append(row["avg_sleep"])

    if not dates:
        return None

    plt.rcParams.update({
        "figure.facecolor": "#1a1a2e",
        "axes.facecolor": "#16213e",
        "axes.edgecolor": "#0f3460",
        "axes.labelcolor": "#e0e0e0",
        "xtick.color": "#a0a0b0",
        "ytick.color": "#a0a0b0",
        "text.color": "#e0e0e0",
        "grid.color": "#0f3460",
        "grid.alpha": 0.5,
        "font.family": "DejaVu Sans",
    })

    fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
    fig.suptitle("📊 Твой трекер за последние 30 дней", fontsize=14,
                 color="#e0e0e0", fontweight="bold", y=0.98)

    configs = [
        (axes[0], moods, "#e94560", "Настроение (1–5)", 1, 5),
        (axes[1], works, "#0f9b8e", "Часы работы/учёбы", 0, None),
        (axes[2], sleeps, "#5c6bc0", "Часы сна", 0, None),
    ]

    for ax, values, color, label, ymin, ymax in configs:
        if len(dates) == 1:
            ax.scatter(dates, values, color=color, s=80, zorder=5)
        else:
            ax.plot(dates, values, color=color, linewidth=2, marker="o",
                    markersize=5, markerfacecolor="white", markeredgecolor=color)
            ax.fill_between(dates, values, alpha=0.15, color=color)

        ax.set_ylabel(label, fontsize=9)
        ax.set_ylim(bottom=ymin, top=ymax)
        ax.grid(True, linestyle="--", linewidth=0.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        for x, y in zip(dates, values):
            ax.annotate(f"{y:.1f}", (x, y),
                        textcoords="offset points", xytext=(0, 6),
                        ha="center", fontsize=7, color=color)

    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    axes[2].xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
    plt.setp(axes[2].xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=8)

    plt.tight_layout(rect=[0, 0, 1, 0.97])

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)

    return buf