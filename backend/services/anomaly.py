"""Детектор всплесков обращений.

# Statistical anomaly detection (Z-score). Production: rolling window on PostgreSQL

Логика
------
Для каждой пары «категория + регион» берётся ряд по дням. По скользящему окну
в 30 дней (без текущего дня, иначе всплеск сам себя размоет) считаются среднее
и стандартное отклонение. Если сегодняшнее значение выше mean + 2*std —
это всплеск.

Когда истории мало (меньше MIN_WINDOW дней) статистика недостоверна, и
используется простой порог по абсолютному числу обращений за день.
"""
import statistics
from datetime import date, timedelta

from data.history import HISTORY, TODAY
from models import Spike

# Сколько дней берём в скользящее окно.
WINDOW_DAYS = 30

# Минимум наблюдений, ниже которого среднее и сигма считать бессмысленно.
MIN_WINDOW = 7

# Порог в сигмах.
Z_THRESHOLD = 2.0

# Запасной порог: столько обращений одной категории из одного региона за день
# уже считается всплеском, даже без статистики.
SIMPLE_THRESHOLD = 5

# На малых числах сигма неустойчива: 2 обращения против нормы 1.1 дают z=3.3,
# хотя никакого события за этим нет. Поэтому всплеском считаем только то, что
# заметно и в абсолютных величинах.
MIN_ABSOLUTE_COUNT = 4

# Человекочитаемые пояснения по категориям — что всплеск означает на практике.
_EXPLANATION = {
    "ЖКХ": "вероятна авария на сетях",
    "Дороги": "возможно повреждение покрытия после осадков",
    "Освещение": "вероятен сбой на линии уличного освещения",
    "Транспорт": "возможен сбой в расписании или отмена маршрутов",
    "Благоустройство": "вероятен срыв графика вывоза мусора",
    "Другое": "требуется уточнение у профильной службы",
}


def _grouped_series() -> dict[tuple[str, str], dict[date, int]]:
    """{(категория, регион): {день: количество}}."""
    grouped: dict[tuple[str, str], dict[date, int]] = {}
    for row in HISTORY:
        key = (row["category"], row["region"])
        grouped.setdefault(key, {})[row["date"]] = row["count"]
    return grouped


def _window_values(series: dict[date, int], current_day: date) -> list[int]:
    """Значения за WINDOW_DAYS до текущего дня, сам текущий день исключён."""
    values: list[int] = []
    for offset in range(1, WINDOW_DAYS + 1):
        day = current_day - timedelta(days=offset)
        if day in series:
            values.append(series[day])
    return values


def detect_spikes(current_day: date | None = None) -> list[dict]:
    """Найти всплески на текущий день. Возвращает сырые словари."""
    day = current_day or TODAY
    found: list[dict] = []

    for (category, region), series in _grouped_series().items():
        current = series.get(day, 0)
        if current < MIN_ABSOLUTE_COUNT:
            continue

        window = _window_values(series, day)

        if len(window) >= MIN_WINDOW:
            mean = statistics.fmean(window)
            # pstdev, а не stdev: окно — это вся рассматриваемая популяция
            std = statistics.pstdev(window)
            if std == 0:
                continue
            z = (current - mean) / std
            if z < Z_THRESHOLD:
                continue
            method = "z-score"
        else:
            # Истории мало — статистике верить нельзя, работаем по порогу
            if current <= SIMPLE_THRESHOLD:
                continue
            mean = statistics.fmean(window) if window else float(current)
            std = 0.0
            z = 0.0
            method = "threshold"

        percent = int(round((current - mean) / mean * 100)) if mean else 100
        found.append(
            {
                "region": region,
                "category": category,
                "current": current,
                "mean": round(mean, 1),
                "std": round(std, 2),
                "z_score": round(z, 2),
                "percent_increase": max(percent, 1),
                "method": method,
                "day": day,
            }
        )

    # самые выраженные — первыми
    found.sort(key=lambda item: (item["z_score"], item["percent_increase"]), reverse=True)
    return found


def get_spikes(limit: int = 3) -> list[Spike]:
    """Всплески в формате API."""
    result: list[Spike] = []
    for item in detect_spikes()[:limit]:
        explanation = _EXPLANATION.get(item["category"], "требуется проверка")
        if item["method"] == "z-score":
            window_text = (
                f"сегодня {item['current']} при норме {item['mean']} "
                f"(отклонение {item['z_score']}σ)"
            )
        else:
            window_text = f"сегодня {item['current']} — порог {SIMPLE_THRESHOLD}"

        result.append(
            Spike(
                region=item["region"],
                description=(
                    f"Рост обращений по категории «{item['category']}» — {explanation}"
                ),
                percent_increase=item["percent_increase"],
                category=item["category"],
                time_window=window_text,
            )
        )
    return result
