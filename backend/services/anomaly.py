"""Детектор всплесков (spike detection).

# TODO: Replace with statistical anomaly detection (Z-score / IQR on rolling window)
# Current: hardcoded demo alerts
# Production: скользящее окно по регионам/категориям, отклонение > N сигм -> алерт
"""
from models import Spike


def get_spikes() -> list[Spike]:
    """Вернуть текущие всплески обращений (демо-данные)."""
    return [
        Spike(
            region="Астана",
            description="Резкий рост обращений по водоснабжению — вероятна крупная авария на сети",
            percent_increase=240,
            category="ЖКХ — Водоснабжение",
            time_window="за последние 2 часа",
        ),
        Spike(
            region="Караганда",
            description="Всплеск жалоб на отопление — возможен сбой на теплоцентрали",
            percent_increase=170,
            category="ЖКХ — Отопление",
            time_window="за последние 4 часа",
        ),
        Spike(
            region="Алматы",
            description="Учащённые обращения по неработающим светофорам в центре города",
            percent_increase=95,
            category="Дороги — Светофоры",
            time_window="за последние 6 часов",
        ),
    ]
