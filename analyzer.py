import io, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import db_handler as db

EMOJIS = {1: "😞", 2: "😐", 3: "🙂", 4: "😊", 5: "🤩"}
mood_label = lambda s: f"{s:.1f} {EMOJIS.get(max(1, min(5, round(s))), '')}"

def get_stats(tid, days):
    stats = db.get_aggregated_stats(tid, days)
    if not stats or stats.get("cnt", 0) == 0: 
        return f"За {days} дней записей нет.\n+ Записать день"
    
    best = db.get_best_day(tid, days)
    best_str = f"\n Лучший день: *{datetime.strptime(best['day'], '%Y-%m-%d').strftime('%d.%m')}* ({best['avg_mood']:.1f})" if best else ""
    
    return (f"📊 *Статистика за {days} дней* (записей: {stats['cnt']}){best_str}\n\n"
            f"😊 Настроение: ср. {mood_label(stats['avg_mood'])} (мин: {stats['min_mood']}, макс: {stats['max_mood']})\n"
            f"📚 Работа: ср. *{stats['avg_work']}ч* (мин: {stats['min_work']}, макс: {stats['max_work']})\n"
            f"😴 Сон: ср. *{stats['avg_sleep']}ч* (мин: {stats['min_sleep']}, макс: {stats['max_sleep']})")

def get_insights(tid):
    entries = db.get_history(tid, 0, 100)[0]
    if len(entries) < 3: return "Мало данных. Добавь записи!"
    
    sleep_data = db.get_mood_by_buckets(tid, col="sleep_hours")
    work_data = db.get_mood_by_buckets(tid, col="work_hours")
    
    lines = [" *Интересные факты:*\n"]
    if sleep_data: lines.append(f"настроение при сне *{max(sleep_data, key=lambda x: x['avg_mood'])['bucket']}*")
    if work_data: lines.append(f"настроение на работе *{max(work_data, key=lambda x: x['avg_mood'])['bucket']}*")
    
    if len(entries) >= 4:
        half = len(entries) // 2
        avg_first = sum(e['mood'] for e in entries[:half]) / half
        avg_second = sum(e['mood'] for e in entries[half:]) / (len(entries) - half)
        trend = avg_second - avg_first
        if abs(trend) >= 0.3: lines.append(f"настроения: {'улучшается' if trend > 0 else 'снижается'} (Δ{trend:+.1f})")
           
    return "\n".join(lines)

def get_chart(tid):
    daily = db.get_daily_averages(tid, 30)
    if not daily: return None
    
    dates, moods, works, sleeps = [], [], [], []
    for row in daily:
        dates.append(datetime.strptime(row["day"], "%Y-%m-%d"))
        moods.append(row["avg_mood"]); works.append(row["avg_work"]); sleeps.append(row["avg_sleep"])

    plt.rcParams.update({"figure.facecolor": "#1a1a2e", "axes.facecolor": "#16213e", "text.color": "#e0e0e0", "grid.color": "#0f3460"})
    fig, axes = plt.subplots(3, 1, figsize=(8, 7), sharex=True)
    fig.suptitle("Трекер за месяц", color="#e0e0e0")

    for ax, vals, color, label in zip(axes, [moods, works, sleeps], ["#e94560", "#0f9b8e", "#5c6bc0"], ["Настроение", "Работа (ч)", "Сон (ч)"]):
        ax.plot(dates, vals, color=color, marker="o", markersize=4)
        ax.fill_between(dates, vals, alpha=0.2, color=color)
        ax.set_ylabel(label, fontsize=9); ax.grid(True, linestyle="--")

    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf
    
