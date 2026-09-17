"""Аналитические роуты для ситуационного центра."""
from collections import Counter, defaultdict

from fastapi import APIRouter

from models import AnalyticsSummary, RegionStats, Spike, TimelinePoint
from services.anomaly import get_spikes
from store import all_tickets

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _category_of(t: dict) -> str:
    return t.get("category") or (t.get("_gold") or {}).get("category") or "Другое"


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
def regions():
    tickets = all_tickets()
    by_region: dict[str, list[dict]] = defaultdict(list)
    for t in tickets:
        by_region[t["region"]].append(t)

    # предопределённые тренды для демо-наглядности
    trend_map = {
        "Астана": 12.4,
        "Алматы": -3.1,
        "Шымкент": 8.7,
        "Караганда": 21.5,
        "Павлодар": -5.2,
        "Актобе": 4.0,
    }

    stats: list[RegionStats] = []
    for region, items in by_region.items():
        cats = Counter(_category_of(t) for t in items)
        top_category = cats.most_common(1)[0][0] if cats else "—"
        stats.append(
            RegionStats(
                region=region,
                total=len(items),
                top_category=top_category,
                trend_percent=trend_map.get(region, 0.0),
            )
        )
    stats.sort(key=lambda s: s.total, reverse=True)
    return stats


@router.get("/spikes", response_model=list[Spike])
def spikes():
    return get_spikes()


@router.get("/timeline", response_model=list[TimelinePoint])
def timeline():
    # Демо-данные за 7 дней по трём ключевым категориям.
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    zhkh = [320, 410, 380, 520, 610, 470, 390]
    roads = [140, 160, 210, 180, 240, 200, 170]
    light = [80, 95, 110, 130, 120, 90, 100]
    return [
        TimelinePoint(day=d, ЖКХ=z, Дороги=r, Освещение=l)
        for d, z, r, l in zip(days, zhkh, roads, light)
    ]
