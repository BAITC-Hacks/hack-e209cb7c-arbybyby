"""Агрегированная история обращений для аналитики.

Зачем отдельный модуль
----------------------
В seed.py лежат 55 детальных обращений за 3 дня — этого хватает оператору,
но не статистике: скользящее окно Z-score требует недель наблюдений, а
прогноз на месяцы — хотя бы пары месяцев истории. На трёх точках и то и
другое математически бессмысленно.

Поэтому детальные обращения (для рабочего места оператора) и агрегированная
история (для ситуационного центра) разведены. Здесь — только счётчики
«день + категория + регион», без текстов и персональных данных.

Данные ДЕМОНСТРАЦИОННЫЕ, но генерируются детерминированно и с правдоподобной
структурой: базовый уровень по категориям, недельная сезонность (в будни
обращений больше), плавный тренд и несколько заложенных аномалий. Алгоритмы
поверх них работают по-настоящему — Z-score действительно считает отклонения,
прогноз действительно экстраполирует ряд.

В проде заменяется запросом к PostgreSQL:
    SELECT date_trunc('day', created_at), category, region, count(*)
    FROM tickets GROUP BY 1, 2, 3
"""
import math
import random
from datetime import date, datetime, timedelta

# Сколько дней истории генерируем.
HISTORY_DAYS = 120

# Базовое число обращений в день по категориям (до сезонности и шума).
_CATEGORY_BASE = {
    "ЖКХ": 14.0,
    "Дороги": 8.0,
    "Благоустройство": 6.0,
    "Освещение": 5.0,
    "Транспорт": 4.5,
    "Другое": 3.0,
}

# Доля региона в общем потоке — примерно пропорционально населению.
_REGION_SHARE = {
    "Астана": 0.24,
    "Алматы": 0.26,
    "Шымкент": 0.16,
    "Караганда": 0.13,
    "Павлодар": 0.11,
    "Актобе": 0.10,
}

# Заложенные аномалии: (смещение в днях назад, регион, категория, множитель).
# Нужны, чтобы детектор всплесков было на чём продемонстрировать, —
# сам детектор о них не знает и находит их статистикой.
_INJECTED_SPIKES = [
    (0, "Астана", "ЖКХ", 3.4),
    (0, "Караганда", "ЖКХ", 2.9),
    (0, "Алматы", "Дороги", 3.1),
    (2, "Шымкент", "Благоустройство", 2.4),
    (14, "Павлодар", "Освещение", 2.7),
    (33, "Астана", "Транспорт", 2.5),
]

# Фиксированная «сегодняшняя» дата: seed тоже привязан к 17.09.2026,
# иначе демо разъезжается при смене системной даты.
TODAY = date(2026, 9, 17)


def _weekly_factor(day: date) -> float:
    """Недельная сезонность: будни выше, выходные ниже."""
    # Синус с периодом 7 дней, сдвинутый так, чтобы минимум приходился на воскресенье.
    phase = (day.weekday() - 2) / 7.0 * 2 * math.pi
    return 1.0 + 0.22 * math.cos(phase)


def _trend_factor(days_ago: int) -> float:
    """Плавный рост потока обращений со временем (около +18% за 120 дней)."""
    return 1.0 + 0.0015 * (HISTORY_DAYS - days_ago)


def build_history() -> list[dict]:
    """Агрегаты вида {date, region, category, count}, свежие в конце."""
    rng = random.Random(20260917)  # детерминированно: цифры не пляшут между запусками
    spikes = {(d, r, c): m for d, r, c, m in _INJECTED_SPIKES}

    rows: list[dict] = []
    for days_ago in range(HISTORY_DAYS, -1, -1):
        day = TODAY - timedelta(days=days_ago)
        week = _weekly_factor(day)
        trend = _trend_factor(days_ago)

        for category, base in _CATEGORY_BASE.items():
            for region, share in _REGION_SHARE.items():
                expected = base * share * week * trend
                # пуассоновский по духу разброс, но без numpy
                noise = rng.gauss(1.0, 0.28)
                value = expected * max(0.25, noise)
                value *= spikes.get((days_ago, region, category), 1.0)

                count = max(0, int(round(value)))
                if count:
                    rows.append(
                        {
                            "date": day,
                            "region": region,
                            "category": category,
                            "count": count,
                        }
                    )
    return rows


# Считаем один раз при импорте — генерация лёгкая, но повторять её незачем.
HISTORY: list[dict] = build_history()


def daily_totals() -> list[tuple[date, int]]:
    """Суммарное число обращений по дням — временной ряд для прогноза."""
    totals: dict[date, int] = {}
    for row in HISTORY:
        totals[row["date"]] = totals.get(row["date"], 0) + row["count"]
    return sorted(totals.items())


def series_for(category: str | None = None, region: str | None = None) -> list[tuple[date, int]]:
    """Ряд по дням с фильтрами по категории и региону."""
    totals: dict[date, int] = {}
    for row in HISTORY:
        if category and row["category"] != category:
            continue
        if region and row["region"] != region:
            continue
        totals[row["date"]] = totals.get(row["date"], 0) + row["count"]
    return sorted(totals.items())


def as_datetime(day: date) -> datetime:
    return datetime(day.year, day.month, day.day)
