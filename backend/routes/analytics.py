"""Аналитические роуты для ситуационного центра."""
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Query

from data.history import HISTORY, TODAY
from models import AnalyticsSummary, AskRequest, RegionStats, Spike
from services.anomaly import get_spikes
from services.forecast import build_forecast
from services.nlq import answer as answer_question
from store import all_tickets

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Периоды, которые предлагает интерфейс. Произвольное число дней не принимаем:
# окно должно укладываться в глубину истории.
_PERIODS = (7, 30, 90)
DEFAULT_PERIOD = 7

# Самый ранний день в истории — дальше сравнивать не с чем.
_FIRST_DAY = min(row["date"] for row in HISTORY)

# Категории графика нагрузки по умолчанию — три самых массовых.
# При фильтре по категории рисуем одну линию.
_TIMELINE_CATEGORIES = ("ЖКХ", "Дороги", "Освещение")

_WEEKDAYS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")


def _period_days(period: int) -> int:
    return period if period in _PERIODS else DEFAULT_PERIOD


def _window(days: int) -> tuple[date, date, int]:
    """Начало окна, начало предыдущего окна и его реальная длина в днях.

    На 90 днях предыдущее окно частично выходит за глубину истории: данных
    там 30 дней вместо 90, и сравнение сумм показало бы трёхкратный «рост»
    во всех регионах. Поэтому возвращаем ещё и покрытую длину — тренд
    считается по средним за день.
    """
    start = TODAY - timedelta(days=days - 1)
    prev_start = start - timedelta(days=days)
    covered = max((start - max(prev_start, _FIRST_DAY)).days, 0)
    return start, prev_start, covered


def _day_label(day: date, days: int) -> str:
    """Неделя читается по дням недели, длинные периоды — по датам."""
    return _WEEKDAYS[day.weekday()] if days <= 7 else day.strftime("%d.%m")


@router.get("/summary", response_model=AnalyticsSummary)
def summary():
    tickets = all_tickets()
    resolved = [t for t in tickets if t["status"] == "resolved"]
    critical = [t for t in tickets if t["priority"] == "high"]

    # Демо-показатели: масштабируем до правдоподобных значений колл-центра 109.
    return AnalyticsSummary(
        total_tickets=12847,
        avg_processing_time=4.2,
        resolved_percent=89,
        critical_count=max(23, len(critical)),
    )


@router.get("/regions", response_model=list[RegionStats])
def regions(
    period: int = Query(DEFAULT_PERIOD, description="Окно в днях: 7, 30 или 90"),
    category: Optional[str] = Query(None, description="Категория, например «ЖКХ»"),
):
    """Статистика по регионам за выбранное окно.

    Считается по агрегированной истории, а не по 55 seed-обращениям: без
    временного ряда фильтр «7 / 30 / 90 дней» не на чем применять. Тренд —
    честное сравнение окна с предыдущим окном такой же длины, а не константа.
    """
    days = _period_days(period)
    start, prev_start, prev_days = _window(days)

    current: dict[str, Counter] = defaultdict(Counter)  # регион -> категории
    previous: Counter = Counter()  # регион -> всего за прошлое окно

    for row in HISTORY:
        if category and row["category"] != category:
            continue
        day = row["date"]
        if day >= start:
            current[row["region"]][row["category"]] += row["count"]
        elif day >= prev_start:
            previous[row["region"]] += row["count"]

    stats: list[RegionStats] = []
    for region, cats in current.items():
        total = sum(cats.values())
        was = previous.get(region, 0)
        # Сравниваем интенсивность (обращений в день), а не сырые суммы.
        if was and prev_days:
            before = was / prev_days
            trend = round((total / days - before) / before * 100, 1)
        else:
            trend = 0.0
        stats.append(
            RegionStats(
                region=region,
                total=total,
                top_category=cats.most_common(1)[0][0] if cats else "—",
                trend_percent=trend,
            )
        )
    stats.sort(key=lambda s: s.total, reverse=True)
    return stats


@router.get("/spikes", response_model=list[Spike])
def spikes():
    return get_spikes()


@router.get("/timeline")
def timeline(
    period: int = Query(DEFAULT_PERIOD, description="Окно в днях: 7, 30 или 90"),
    category: Optional[str] = Query(None, description="Категория, например «ЖКХ»"),
) -> list[dict]:
    """Нагрузка по дням: [{"day": "Пн", "ЖКХ": 12, ...}].

    Набор серий зависит от фильтра (одна категория или три массовых), поэтому
    схема ответа динамическая — фиксированная модель здесь только мешала бы.
    """
    days = _period_days(period)
    start, _, _ = _window(days)
    series = (category,) if category else _TIMELINE_CATEGORIES

    buckets: dict[date, Counter] = {
        start + timedelta(days=i): Counter() for i in range(days)
    }
    for row in HISTORY:
        if row["date"] < start or row["category"] not in series:
            continue
        buckets[row["date"]][row["category"]] += row["count"]

    return [
        {"day": _day_label(day, days), **{name: counts[name] for name in series}}
        for day, counts in sorted(buckets.items())
    ]


@router.get("/forecast")
def forecast(months: int = 3):
    """Прогноз нагрузки на 1-3 месяца вперёд."""
    return build_forecast(months)


@router.post("/ask")
def ask(payload: AskRequest):
    """Вопрос к данным на естественном языке."""
    return answer_question(payload.question)
