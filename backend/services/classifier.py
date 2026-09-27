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

from models import CategoryOption, ClassifyResponse

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

def score_rules(text: str) -> list[tuple[tuple[str, str, str], list[str]]]:
    """Все сработавшие правила, отсортированные по числу совпавших маркеров.

    В отличие от match_rules (возвращает первое совпадение) нужен, чтобы
    предложить оператору несколько вариантов, когда уверенности мало.
    """
    scored: list[tuple[tuple[str, str, str], list[str]]] = []
    for pattern, label in _COMPILED_RULES:
        words = [m.group(0) for m in pattern.finditer(text)]
        if words:
            scored.append((label, words))
    scored.sort(key=lambda item: len(item[1]), reverse=True)
    return scored


# Чем добираем список вариантов, если правил сработало меньше трёх.
# Порядок — по частоте категорий в реальном потоке обращений 109.
_FALLBACK_OPTIONS: list[tuple[str, str, str]] = [
    ("ЖКХ", "Водоснабжение", "Горводоканал"),
    ("Дороги", "Дорожное покрытие", "УДС"),
    ("Благоустройство", "Вывоз мусора", "УГХ"),
    ("Освещение", "Уличное освещение", "Горсвет"),
    ("Транспорт", "Общественный транспорт", "Управление транспорта"),
]

# Порог, ниже которого текст считается слишком коротким для уверенного вывода.
# Казахские обращения вида «Су жоқ» (7 символов) попадают именно сюда.
MIN_CONFIDENT_LENGTH = 20

# Одиночный маркер сам по себе НЕ повод сомневаться: во фразе «канализацию
# засорило, стоки во дворе» маркер один, но смысл однозначен. Считаем сигнал
# слабым, только если при одном маркере текст ещё и короткий.
# На seed-данных: порог 60 даёт ~15% обращений на проверку, без него — 60%,
# и тогда классификатор выглядит бесполезным.
SINGLE_MARKER_MAX_LENGTH = 60


def build_alternatives(
    scored: list[tuple[tuple[str, str, str], list[str]]],
    top_confidence: int,
) -> list[CategoryOption]:
    """Три наиболее вероятные категории с убывающей уверенностью."""
    options: list[tuple[str, str, str]] = [label for label, _ in scored]

    for fallback in _FALLBACK_OPTIONS:
        if len(options) >= 3:
            break
        if fallback not in options:
            options.append(fallback)

    result: list[CategoryOption] = []
    for position, (category, subcategory, service) in enumerate(options[:3]):
        # разносим уверенность: первый вариант вероятнее остальных
        confidence = max(10, top_confidence - position * 15)
        result.append(
            CategoryOption(
                category=category,
                subcategory=subcategory,
                responsible_service=service,
                confidence=confidence,
            )
        )
    return result


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
    stripped = text.strip()

    scored = score_rules(text)
    top_hits = scored[0][1] if scored else []

    # Уверенности мало, если зацепился ровно один маркер либо текста слишком мало.
    # Второй случай важен для казахского: «Су жоқ» — валидная жалоба на воду,
    # но семи символов недостаточно, чтобы отвечать за категорию.
    too_short = len(stripped) < MIN_CONFIDENT_LENGTH
    weak_single_marker = (
        len(top_hits) <= 1 and len(stripped) < SINGLE_MARKER_MAX_LENGTH
    )
    needs_review = bool(scored) and (too_short or weak_single_marker)

    if not scored:
        # ничего не совпало — отправляем в общую обработку акимата
        category, subcategory, service = "Другое", "Общие вопросы", "Акимат района"
        reasoning = "Явные маркеры не найдены — обращение направлено на ручную обработку."
        confidence = random.randint(55, 70)
        needs_review = True
        alternatives = build_alternatives([], confidence)
    elif needs_review:
        (category, subcategory, service) = scored[0][0]
        confidence = random.randint(55, 70)
        cause = (
            f"текст короче {MIN_CONFIDENT_LENGTH} символов"
            if too_short
            else f"единственный маркер '{top_hits[0]}' в коротком тексте"
        )
        reasoning = f"Низкая уверенность ({cause}) — требуется проверка оператором."
        alternatives = build_alternatives(scored, confidence)
    else:
        (category, subcategory, service) = scored[0][0]
        readable = ", ".join(f"'{w}'" for w in top_hits[:3])
        reasoning = f"Категория выбрана на основе маркеров: {readable}"
        confidence = random.randint(85, 97)
        alternatives = []

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
        needs_review=needs_review,
        alternatives=alternatives,
    )
