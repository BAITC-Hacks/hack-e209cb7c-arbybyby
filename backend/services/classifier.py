"""Smart-классификация обращений.

# TODO: Replace with fine-tuned model (QLoRA on Llama/BERT)
# Current: rule-based keyword matching
# Production: model loaded from ./ml_models/classifier_v1/

Placeholder-классификатор на основе поиска ключевых слов. Работает на русском и
казахском. Возвращает категорию, подкатегорию, ответственную службу, приоритет,
адрес (эвристика), confidence_score и человекочитаемый reasoning.
"""
import random
import re

from models import ClassifyResponse

# Правила: (список маркеров) -> (категория, подкатегория, служба)
# Порядок важен: более специфичные правила (светофор) идут раньше общих (дорог).
_RULES = [
    (
        ["светофор"],
        ("Дороги", "Светофоры", "УДС"),
    ),
    (
        ["труб", "вод", "затоп", "течь", "теч", "канализ", "су құбыр", "су жоқ", "су ағ"],
        ("ЖКХ", "Водоснабжение", "Горводоканал"),
    ),
    (
        ["отопл", "тепл", "батаре", "жыл"],
        ("ЖКХ", "Отопление", "Теплосети"),
    ),
    (
        ["свет", "освещ", "фонар", "жарық", "шам"],
        ("Освещение", "Уличное освещение", "Горсвет"),
    ),
    (
        ["дорог", "ям", "асфальт", "жол", "шұңқыр"],
        ("Дороги", "Дорожное покрытие", "УДС"),
    ),
    (
        ["мусор", "қоқыс", "благоустр", "площадк", "свалк", "урн", "лавочк"],
        ("Благоустройство", "Вывоз мусора", "УГХ"),
    ),
    (
        ["автобус", "маршрут", "транспорт", "көлік", "аялдам", "остановк"],
        ("Транспорт", "Общественный транспорт", "Управление транспорта"),
    ),
]

# Маркеры высокого приоритета (аварийность, угроза, срочность).
_HIGH_PRIORITY_MARKERS = [
    "срочно", "авари", "прорв", "жарыл", "хлещ", "фонтан", "кипяток", "затоп",
    "искр", "замыкан", "упаст", "упад", "опасн", "қауіпт", "тез", "минус",
]
_LOW_PRIORITY_MARKERS = ["месяц", "недел", "давно", "постоянно", "не работает уже"]

# Грубая эвристика извлечения адреса (в проде — NER-модель).
_ADDRESS_RE = re.compile(
    r"((?:ул\.|пр\.|мкр\.|проспект|улица|микрорайон)\s?[^,.!?]+?\d+[^,.!?]*)",
    re.IGNORECASE,
)


def _detect_priority(text_lower: str, fallback: str = "medium") -> str:
    if any(m in text_lower for m in _HIGH_PRIORITY_MARKERS):
        return "high"
    if any(m in text_lower for m in _LOW_PRIORITY_MARKERS):
        return "low"
    return fallback


def _extract_address(text: str) -> str | None:
    match = _ADDRESS_RE.search(text)
    if match:
        return match.group(1).strip()
    return None


def classify_ticket(text: str, address_hint: str | None = None) -> ClassifyResponse:
    """Классифицировать текст обращения. Возвращает ClassifyResponse."""
    text_lower = text.lower()

    matched_words: list[str] = []
    category = subcategory = service = None

    for markers, (cat, subcat, svc) in _RULES:
        hits = [m for m in markers if m in text_lower]
        if hits:
            matched_words = hits
            category, subcategory, service = cat, subcat, svc
            break

    if category is None:
        # ничего не совпало — отправляем в общую обработку акимата
        category, subcategory, service = "Другое", "Общие вопросы", "Акимат района"
        reasoning = "Явные маркеры не найдены — обращение направлено на ручную обработку."
        confidence = random.randint(55, 70)
    else:
        readable = ", ".join(f"'{w}'" for w in matched_words[:3])
        reasoning = f"Категория выбрана на основе маркеров: {readable}"
        confidence = random.randint(85, 97)

    priority = _detect_priority(text_lower)
    address = address_hint or _extract_address(text)

    return ClassifyResponse(
        category=category,
        subcategory=subcategory,
        address=address,
        priority=priority,
        responsible_service=service,
        confidence_score=confidence,
        reasoning=reasoning,
    )
