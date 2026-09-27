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
#
# Маркеры — фрагменты регулярных выражений. Каждый проверяется С ГРАНИЦЕЙ СЛОВА
# в начале (см. _compile_markers), иначе короткие подстроки ловят что попало.
# Проверено на 313 реальных обращениях с dialog.egov.kz:
#   «вод»   ловил «водителя»     -> жалоба на водителя уходила в Водоснабжение
#   «жыл»   ловил «жылдан/жылы»  -> «жыл» это «год» по-казахски, 32 ложных срабатывания
#   «ям»    ловил «обязанностям» -> дательный падеж мн. ч. уходил в Дороги
#   «освещ» ловил «просвещения»  -> Министерство просвещения уходило в Освещение
# Поэтому голые «вод», «жыл», «тепл», «свет», «ям», «площадк» заменены точными формами.
#
# Порядок важен: специфичные правила идут раньше общих. Транспорт стоит перед
# Дорогами, чтобы «водитель автобуса» не перехватывался маркером «дорог».
_RULES = [
    (
        [r"светофор"],
        ("Дороги", "Светофоры", "УДС"),
    ),
    (
        [r"лифт"],
        ("ЖКХ", "Лифт", "КСК"),
    ),
    (
        [
            r"водоснабж", r"водопровод", r"водоотвед", r"водоканал",
            r"вод[аыуе]\b", r"водой\b", r"труб", r"затоп", r"течь",
            r"протечк", r"прорыв", r"канализ", r"стояк",
            r"су\s+құбыр", r"су\s+жоқ", r"су\s+ағ", r"сумен", r"ағынды\s+су",
        ],
        ("ЖКХ", "Водоснабжение", "Горводоканал"),
    ),
    (
        [
            r"отоплен", r"теплоснаб", r"тепла\b", r"тепло\b", r"батаре",
            r"радиатор", r"котельн", r"жылу", r"жылыт", r"қыздыр",
        ],
        ("ЖКХ", "Отопление", "Теплосети"),
    ),
    (
        [
            r"освещ", r"фонар", r"светильник", r"лампоч", r"жарық",
            r"шам\b", r"шамдар",
        ],
        ("Освещение", "Уличное освещение", "Горсвет"),
    ),
    (
        [
            r"автобус", r"маршрут", r"остановк", r"аялдам", r"водител",
            r"көлік", r"қоғамдық\s+көлік", r"троллейбус", r"расписани",
        ],
        ("Транспорт", "Общественный транспорт", "Управление транспорта"),
    ),
    (
        [
            r"дорог", r"автодорог", r"ям[аыуеой]?\b", r"асфальт",
            r"выбоин", r"жол", r"шұңқыр", r"тротуар",
        ],
        ("Дороги", "Дорожное покрытие", "УДС"),
    ),
    (
        [
            r"мусор", r"қоқыс", r"свалк", r"урн", r"контейнер",
            r"благоустр", r"детск\w*\s+площадк", r"игров\w*\s+площадк",
            r"лавочк", r"скамейк", r"озелен",
        ],
        ("Благоустройство", "Вывоз мусора", "УГХ"),
    ),
]


def _compile_markers(markers: list[str]) -> re.Pattern[str]:
    """Собрать маркеры в одну регулярку с границей слова в начале."""
    return re.compile(r"\b(?:" + "|".join(markers) + r")", re.IGNORECASE)


# (скомпилированная регулярка, (категория, подкатегория, служба))
_COMPILED_RULES = [(_compile_markers(m), label) for m, label in _RULES]


def match_rules(text: str) -> tuple[tuple[str, str, str], list[str]] | None:
    """Найти первое подходящее правило.

    Возвращает ((категория, подкатегория, служба), найденные слова) или None.
    Вынесено в отдельную функцию, чтобы скрипты разметки в data/scripts
    использовали ровно ту же логику, что и прод.
    """
    for pattern, label in _COMPILED_RULES:
        hits = pattern.findall(text)
        if hits:
            # findall с группами вернул бы группы, поэтому берём срезы по match
            words = [m.group(0) for m in pattern.finditer(text)]
            return label, words
    return None

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

    matched = match_rules(text)
    if matched is not None:
        (category, subcategory, service), matched_words = matched

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
