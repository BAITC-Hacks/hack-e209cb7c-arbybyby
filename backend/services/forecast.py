"""Прогноз нагрузки на 1-3 месяца вперёд.

Два пути
--------
1. Facebook Prophet, если он установлен. Даёт тренд, недельную и годовую
   сезонность и честный доверительный интервал.
2. # Fallback: linear trend + weekly seasonality. Production: Facebook Prophet
   Линейная регрессия методом наименьших квадратов по всей истории плюс
   недельная сезонность, снятая с данных (среднее отклонение по дням недели).
   Доверительный интервал строится по остаткам регрессии.

Prophet НЕ стоит в requirements как обязательный: он тянет cmdstanpy с
компиляцией Stan-модели, что на слабой машине занимает минуты и грузит CPU.
Fallback даёт сопоставимый результат на ряде без годовой сезонности, а
переключение автоматическое — достаточно поставить prophet.
"""
import math
import statistics
from datetime import date, timedelta

from data.history import daily_totals

# Сколько дней истории подаём в модель.
HISTORY_LIMIT = 120

# Ширина доверительного интервала в сигмах остатков (~80%).
INTERVAL_SIGMAS = 1.28


def _prophet_available() -> bool:
    try:
        import prophet  # noqa: F401
        return True
    except Exception:
        return False


def _linear_fit(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Наименьшие квадраты: возвращает (наклон, свободный член)."""
    n = len(xs)
    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return 0.0, mean_y
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator
    return slope, mean_y - slope * mean_x


def _weekly_profile(days: list[date], values: list[float], trend: list[float]) -> dict[int, float]:
    """Средний множитель по дню недели после снятия тренда."""
    buckets: dict[int, list[float]] = {}
    for day, actual, expected in zip(days, values, trend):
        if expected > 0:
            buckets.setdefault(day.weekday(), []).append(actual / expected)
    return {wd: statistics.fmean(ratios) for wd, ratios in buckets.items()}


def _forecast_fallback(series: list[tuple[date, int]], horizon: int) -> list[dict]:
    """Линейный тренд + недельная сезонность + интервал по остаткам."""
    days = [d for d, _ in series]
    values = [float(v) for _, v in series]
    xs = [float(i) for i in range(len(values))]

    slope, intercept = _linear_fit(xs, values)
    trend = [slope * x + intercept for x in xs]
    profile = _weekly_profile(days, values, trend)

    # Остатки после снятия тренда и сезонности — основа доверительного интервала
    residuals = []
    for day, actual, expected in zip(days, values, trend):
        seasonal = expected * profile.get(day.weekday(), 1.0)
        residuals.append(actual - seasonal)
    sigma = statistics.pstdev(residuals) if len(residuals) > 1 else 0.0

    last_day = days[-1]
    points: list[dict] = []
    for step in range(1, horizon + 1):
        future_day = last_day + timedelta(days=step)
        x = xs[-1] + step
        base = slope * x + intercept
        predicted = base * profile.get(future_day.weekday(), 1.0)
        # неопределённость растёт с горизонтом — как корень из шага
        spread = INTERVAL_SIGMAS * sigma * math.sqrt(1 + step / 30)
        points.append(
            {
                "date": future_day.isoformat(),
                "predicted": round(max(0.0, predicted), 1),
                "lower": round(max(0.0, predicted - spread), 1),
                "upper": round(predicted + spread, 1),
            }
        )
    return points


def _forecast_prophet(series: list[tuple[date, int]], horizon: int) -> list[dict]:
    """Прогноз через Prophet, если библиотека доступна."""
    import pandas as pd
    from prophet import Prophet

    frame = pd.DataFrame(
        {"ds": [d for d, _ in series], "y": [v for _, v in series]}
    )
    model = Prophet(
        weekly_seasonality=True,
        yearly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.8,
    )
    model.fit(frame)
    future = model.make_future_dataframe(periods=horizon)
    result = model.predict(future).tail(horizon)

    return [
        {
            "date": row.ds.date().isoformat(),
            "predicted": round(float(max(0.0, row.yhat)), 1),
            "lower": round(float(max(0.0, row.yhat_lower)), 1),
            "upper": round(float(row.yhat_upper), 1),
        }
        for row in result.itertuples()
    ]


def build_forecast(months: int = 3) -> dict:
    """История плюс прогноз на months месяцев вперёд."""
    months = max(1, min(3, months))
    horizon = months * 30

    series = daily_totals()[-HISTORY_LIMIT:]
    if len(series) < 14:
        return {
            "method": "insufficient-data",
            "months": months,
            "history": [],
            "forecast": [],
            "note": "Недостаточно истории для прогноза.",
        }

    if _prophet_available():
        try:
            points = _forecast_prophet(series, horizon)
            method = "prophet"
        except Exception:
            # Prophet установлен, но упал (частая история с cmdstanpy) —
            # молча уходим на запасной путь, прогноз всё равно будет.
            points = _forecast_fallback(series, horizon)
            method = "linear+weekly (prophet failed)"
    else:
        points = _forecast_fallback(series, horizon)
        method = "linear+weekly"

    history = [
        {"date": day.isoformat(), "actual": value} for day, value in series
    ]
    total_predicted = sum(p["predicted"] for p in points)
    avg_recent = statistics.fmean([v for _, v in series[-30:]])
    avg_forecast = statistics.fmean([p["predicted"] for p in points])

    return {
        "method": method,
        "months": months,
        "horizon_days": horizon,
        "history": history,
        "forecast": points,
        "summary": {
            "total_predicted": int(round(total_predicted)),
            "avg_per_day_recent": round(avg_recent, 1),
            "avg_per_day_forecast": round(avg_forecast, 1),
            "change_percent": round((avg_forecast - avg_recent) / avg_recent * 100, 1)
            if avg_recent
            else 0.0,
        },
    }
