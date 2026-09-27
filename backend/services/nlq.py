"""Ответы на вопросы к данным на естественном языке.

# Rule-based NL parser. Production: LLM (Claude API) for natural language understanding

Разбор строится на тех же маркерах, что и классификатор обращений: если во
фразе встретился маркер категории — значит вопрос про неё. Регион ищется по
списку с учётом склонений («в Астане», «по Алматы»), период — по словам
«сегодня», «неделя», «месяц».

Осознанные ограничения подхода: он не понимает отрицаний, сравнений («где
больше — в Астане или Алматы») и составных условий. Для этого нужна языковая
модель, отсюда TODO выше.
"""
import re
from datetime import timedelta

from data.history import HISTORY, TODAY
from services.classifier import _RULES

# Регионы и варианты их написания в вопросе (именительный + основа для склонений).
_REGIONS = {
    "Астана": ["астан"],
    "Алматы": ["алмат"],
    "Шымкент": ["шымкент"],
    "Караганда": ["караганд"],
    "Павлодар": ["павлодар"],
    "Актобе": ["актоб"],
}

# Период -> число дней.
_PERIODS = [
    (["сегодня", "бүгін"], 1, "сегодня"),
    (["вчера"], 2, "2 дня"),
    (["недел", "апта"], 7, "7 дней"),
    (["месяц", "ай "], 30, "30 дней"),
    (["квартал", "три месяца"], 90, "90 дней"),
    (["год", "жыл"], 365, "год"),
]

DEFAULT_PERIOD_DAYS = 30
DEFAULT_PERIOD_LABEL = "30 дней"


def _detect_category(question: str) -> str | None:
    """Категория определяется теми же маркерами, что и в классификаторе."""
    for markers, (category, _subcategory, _service) in _RULES:
        pattern = re.compile(r"\b(?:" + "|".join(markers) + r")", re.IGNORECASE)
        if pattern.search(question):
            return category
    # отдельно — прямые упоминания названий категорий
    lowered = question.lower()
    for name in ("жкх", "дорог", "освещен", "транспорт", "благоустройств"):
        if name in lowered:
            return {
                "жкх": "ЖКХ",
                "дорог": "Дороги",
                "освещен": "Освещение",
                "транспорт": "Транспорт",
                "благоустройств": "Благоустройство",
            }[name]
    return None


def _detect_region(question: str) -> str | None:
    lowered = question.lower()
    for region, stems in _REGIONS.items():
        if any(stem in lowered for stem in stems):
            return region
    return None


def _detect_period(question: str) -> tuple[int, str]:
    lowered = question.lower()
    for keywords, days, label in _PERIODS:
        if any(k in lowered for k in keywords):
            return days, label
    return DEFAULT_PERIOD_DAYS, DEFAULT_PERIOD_LABEL


def plural_appeals(n: int) -> str:
    """Склонение слова «обращение» по числу: 1 обращение, 2 обращения, 5 обращений."""
    if 11 <= n % 100 <= 14:
        return "обращений"
    last = n % 10
    if last == 1:
        return "обращение"
    if 2 <= last <= 4:
        return "обращения"
    return "обращений"


def _wants_ranking(question: str) -> bool:
    """Вопрос про лидера («какой район лидирует», «где больше всего»)."""
    lowered = question.lower()
    return any(
        w in lowered
        for w in ("лидир", "больше всего", "топ", "какой район", "какой регион", "чаще всего")
    )


def answer(question: str) -> dict:
    """Разобрать вопрос и посчитать ответ по агрегированной истории."""
    question = (question or "").strip()
    if not question:
        return {
            "answer": "—",
            "filters_applied": {},
            "data": [],
            "clarification": "Введите вопрос.",
        }

    category = _detect_category(question)
    region = _detect_region(question)
    days, period_label = _detect_period(question)
    since = TODAY - timedelta(days=days - 1)

    rows = [
        r for r in HISTORY
        if r["date"] >= since
        and (category is None or r["category"] == category)
        and (region is None or r["region"] == region)
    ]
    total = sum(r["count"] for r in rows)

    filters = {
        "category": category,
        "region": region,
        "period": period_label,
    }

    # Вопрос про лидера — отвечаем регионом, а не числом
    if _wants_ranking(question):
        by_region: dict[str, int] = {}
        for r in rows:
            by_region[r["region"]] = by_region.get(r["region"], 0) + r["count"]
        if by_region:
            leader, leader_count = max(by_region.items(), key=lambda kv: kv[1])
            return {
                "answer": leader,
                "detail": f"{leader_count} {plural_appeals(leader_count)} за {period_label}",
                "filters_applied": filters,
                "data": [
                    {"label": name, "value": value}
                    for name, value in sorted(
                        by_region.items(), key=lambda kv: kv[1], reverse=True
                    )
                ],
                "chart": "bar",
            }

    # Точки для графика — динамика по дням
    by_day: dict[str, int] = {}
    for r in rows:
        key = r["date"].isoformat()
        by_day[key] = by_day.get(key, 0) + r["count"]
    data = [{"label": d, "value": v} for d, v in sorted(by_day.items())]

    result = {
        "answer": f"{total} {plural_appeals(total)}",
        "filters_applied": filters,
        "data": data,
        "chart": "line",
    }

    # Ничего не распозналось — честно просим уточнить, но число всё равно даём
    if category is None and region is None:
        result["clarification"] = (
            "Уточните категорию или регион — сейчас показана общая статистика "
            f"за {period_label}."
        )
    return result
