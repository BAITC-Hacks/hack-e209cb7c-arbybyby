#!/usr/bin/env python3
"""Сбор обращений граждан с блог-платформы dialog.egov.kz.

ВНИМАНИЕ — robots.txt
---------------------
robots.txt сайта явно закрывает эндпоинт поиска от автоматического обхода:

    # Поиск — раскрывает структуру сайта
    Disallow: /search
    Disallow: /blogs/search/
    Disallow: /blogs/all-questions

Скрипт обращается именно к /search, то есть работает вопреки этому указанию.
Решение об использовании принимает владелец проекта. Crawl-delay: 1 из того же
robots.txt скрипт соблюдает (по умолчанию пауза 1–2 с, см. --delay).

Легальная альтернатива без обхода запрета — открытые датасеты на data.egov.kz.

Что собирается
--------------
Со страницы результатов поиска (10 карточек на страницу):
    id            — номер обращения (иконка fa-pencil)
    text          — текст обращения (в выдаче — усечённый анонс)
    category      — категория обращения (fa-tags)
    date          — дата подачи, ДД.ММ.ГГГГ (fa-calendar)
    views         — количество просмотров (fa-eye)
    search_query  — по какому запросу найдено
    url           — ссылка на обращение (для ручной проверки)

Обезличивание
-------------
ФИО заявителя (<h3>) в выгрузку не попадает вообще — это структурное поле,
оно отбрасывается на этапе парсинга. Текст дополнительно прогоняется через
анонимизатор:

    ФИО, инициалы, «Имя Отчество»  -> [ЗАЯВИТЕЛЬ]
    ИИН / БИН (12 цифр)            -> [ИИН]
    номер телефона                 -> [ТЕЛЕФОН]
    адрес почты                    -> [EMAIL]
    номер счёта или карты          -> [СЧЁТ]

Граждане регулярно указывают ИИН и телефон прямо в теле обращения, поэтому
заменять одни только ФИО недостаточно.

Примеры запуска
---------------
    # быстрая проверка: 2 страницы на запрос
    python data/scripts/scrape_dialog_egov.py --max-pages 2

    # полный сбор (долго: сотни страниц на запрос)
    python data/scripts/scrape_dialog_egov.py --max-pages 0

    # только часть запросов
    python data/scripts/scrape_dialog_egov.py --queries ЖКХ отопление --max-pages 5
"""
from __future__ import annotations

import argparse
import csv
import logging
import random
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass, asdict, fields as dataclass_fields
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://dialog.egov.kz"
SEARCH_URL = f"{BASE_URL}/search"
LANG_URL = f"{BASE_URL}/application/changelang"

# Корень проекта: data/scripts/scrape_dialog_egov.py -> aura-pulse-109/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "raw" / "dialog_egov_complaints.csv"

QUERIES: list[str] = [
    # русский
    "ЖКХ",
    "водоснабжение",
    "отопление",
    "освещение",
    "дороги",
    "мусор",
    "транспорт",
    "канализация",
    "лифт",
    "благоустройство",
    "автобус",
    "светофор",
    # казахский
    "жол",
    "су",
    "жылу",
    "қоқыс",
    "жарық",
    "көлік",
]

# Целевые запросы: фразы вместо отдельных слов. Одиночное «су» находит любое
# обращение, где это сочетание встретилось; «су жоқ» — жалобы на отсутствие воды.
# Выдача по фразам короче в разы (6-67 страниц против 335-2467) и чище.
QUERIES_FOCUSED: list[str] = [
    # Водоснабжение и канализация
    "прорвало трубу", "нет холодной воды", "нет горячей воды",
    "затопило подвал", "канализация засор", "течет стояк",
    "су жоқ", "су құбыры жарылды",
    # Отопление
    "нет отопления", "холодные батареи", "не топят",
    "жылу жоқ", "пәтер суық",
    # Освещение
    "уличное освещение", "не горят фонари", "нет освещения во дворе",
    "көше жарығы", "жарық жоқ",
    # Дороги
    "яма на дороге", "разбитая дорога", "нет асфальта",
    "не работает светофор", "тротуар разбит",
    "жол жөндеу", "жол бұзылған",
    # Транспорт
    "автобус не ходит", "нет расписания на остановке",
    "водитель автобуса", "отменили маршрут",
    "автобус жүрмейді", "қоғамдық көлік",
    # Благоустройство
    "не вывозят мусор", "мусорные контейнеры переполнены",
    "стихийная свалка", "детская площадка сломана",
    "қоқыс шығарылмайды",
    # Лифт
    "не работает лифт", "лифт сломан", "лифт жұмыс істемейді",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

log = logging.getLogger("dialog_egov")


# --------------------------------------------------------------------------
# Модель
# --------------------------------------------------------------------------
@dataclass
class Complaint:
    id: str
    text: str
    category: str
    date: str
    views: str
    search_query: str
    url: str


CSV_COLUMNS = [f.name for f in dataclass_fields(Complaint)]


# --------------------------------------------------------------------------
# Обезличивание
# --------------------------------------------------------------------------

# Слова с заглавной буквы, которые НЕ являются частью ФИО. Без этого стоп-листа
# «Республика Казахстан» или «Астана Су Арнасы» превратились бы в [ЗАЯВИТЕЛЬ].
_NOT_A_NAME = {
    "республика", "казахстан", "астана", "алматы", "шымкент", "караганда",
    "павлодар", "актобе", "атырау", "костанай", "тараз", "семей", "оскемен",
    "петропавловск", "кызылорда", "уральск", "актау", "туркестан", "талдыкорган",
    "кокшетау", "аким", "акимат", "акимата", "акиму", "ministry", "министерство",
    "департамент", "управление", "комитет", "правления", "председатель",
    "директор", "начальник", "тоо", "ао", "гу", "кск", "осi", "осм", "мио",
    "блог", "блоге", "город", "города", "район", "района", "область", "области",
    "улица", "улицы", "проспект", "микрорайон", "мкр", "дом", "квартира",
    "уважаемый", "уважаемая", "здравствуйте", "добрый", "прошу", "просим",
    "согласно", "закон", "закона", "кодекс", "статья", "пункт", "постановление",
    "январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август",
    "сентябрь", "октябрь", "ноябрь", "декабрь", "жкх", "цон", "егов",
}

# «Иванов И.И.» / «Иванов И. И.» / «Иванов И.»
# Второй инициал вместе с пробелом перед ним — в одной опциональной группе,
# иначе при отсутствии второго инициала `\s?` съедал бы пробел после фамилии.
_RE_SURNAME_INITIALS = re.compile(
    r"\b[А-ЯЁӘҒҚҢӨҰҮҺІ][а-яёәғқңөұүhі]+\s+[А-ЯЁӘҒҚҢӨҰҮҺІ]\."
    r"(?:\s?[А-ЯЁӘҒҚҢӨҰҮҺІ]\.)?"
)
# Отдельно стоящие инициалы «А.Б.»
_RE_INITIALS = re.compile(r"\b[А-ЯЁӘҒҚҢӨҰҮҺІ]\.\s?[А-ЯЁӘҒҚҢӨҰҮҺІ]\.")
# Два-три слова подряд с заглавной буквы
_RE_CAPITALIZED_RUN = re.compile(
    r"\b[А-ЯЁӘҒҚҢӨҰҮҺІ][а-яёәғқңөұүhі]{1,}"
    r"(?:\s+[А-ЯЁӘҒҚҢӨҰҮҺІ][а-яёәғқңөұүhі]{1,}){1,2}\b"
)
# ФИО капсом: «СЕРГАЗИН КУАНЫШКАЛИЙ»
_RE_UPPER_RUN = re.compile(
    r"\b[А-ЯЁӘҒҚҢӨҰҮҺІ]{2,}(?:\s+[А-ЯЁӘҒҚҢӨҰҮҺІ]{2,}){1,2}\b"
)

# «Имя Отчество»: отчество узнаётся по суффиксу, это надёжнее общего правила
# «два слова с заглавной» и ловит случаи вида «Уважаемая Ляззат Еркеновна».
_RE_PATRONYMIC = re.compile(
    r"\b[А-ЯЁӘҒҚҢӨҰҮҺІ][а-яёәғқңөұүhі]+\s+"
    r"[А-ЯЁӘҒҚҢӨҰҮҺІ][а-яёәғқңөұүhі]+(?:овна|евна|ична|ович|евич|ұлы|қызы)\b"
)
# Инициал, слитый с фамилией: «Д.Куатбекова»
_RE_INITIAL_SURNAME = re.compile(
    r"\b[А-ЯЁӘҒҚҢӨҰҮҺІ]\.\s?[А-ЯЁӘҒҚҢӨҰҮҺІ][а-яёәғқңөұүhі]+"
)

# Прямые идентификаторы — их нельзя оставлять в обучающем наборе.
_RE_IIN = re.compile(r"\b\d{12}\b")                      # ИИН / БИН
_RE_PHONE = re.compile(
    r"(?:\+7|\b8)[\s\-(]?\d{3}[\s\-)]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b"
)
_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_RE_CARD = re.compile(r"\b\d{16,20}\b")                  # счёт / карта

PLACEHOLDER = "[ЗАЯВИТЕЛЬ]"


def _replace_name_core(match: re.Match[str]) -> str:
    """Заменить в найденной фразе только ту часть, что похожа на ФИО.

    Стоп-слова по краям («Уважаемая Ляззат Еркеновна», «аким Иванов Иван»)
    сохраняем, а ядро заменяем. Прежняя версия отбрасывала фразу целиком,
    если в ней встречалось хоть одно стоп-слово, и пропускала из-за этого
    настоящие ФИО.
    """
    words = match.group(0).split()
    start, end = 0, len(words)
    while start < end and words[start].strip(".,").lower() in _NOT_A_NAME:
        start += 1
    while end > start and words[end - 1].strip(".,").lower() in _NOT_A_NAME:
        end -= 1

    core = words[start:end]
    # Нужно минимум два слова подряд; стоп-слово в середине — значит не ФИО.
    if len(core) < 2 or any(w.strip(".,").lower() in _NOT_A_NAME for w in core):
        return match.group(0)

    return " ".join(words[:start] + [PLACEHOLDER] + words[end:])


def anonymize(text: str) -> str:
    """Убрать из текста персональные данные.

    ФИО и инициалы -> [ЗАЯВИТЕЛЬ], ИИН -> [ИИН], телефон -> [ТЕЛЕФОН],
    почта -> [EMAIL], номер счёта -> [СЧЁТ].
    """
    if not text:
        return text

    # Прямые идентификаторы — до имён: они однозначны и не зависят от регистра.
    text = _RE_EMAIL.sub("[EMAIL]", text)
    text = _RE_CARD.sub("[СЧЁТ]", text)
    text = _RE_IIN.sub("[ИИН]", text)
    text = _RE_PHONE.sub("[ТЕЛЕФОН]", text)

    # Имена: от более специфичных шаблонов к более общим.
    text = _RE_PATRONYMIC.sub(_replace_name_core, text)
    text = _RE_SURNAME_INITIALS.sub(_replace_name_core, text)
    text = _RE_UPPER_RUN.sub(_replace_name_core, text)
    text = _RE_CAPITALIZED_RUN.sub(_replace_name_core, text)
    text = _RE_INITIAL_SURNAME.sub(PLACEHOLDER, text)
    text = _RE_INITIALS.sub(PLACEHOLDER, text)

    # схлопнуть повторы подряд: «[ЗАЯВИТЕЛЬ] [ЗАЯВИТЕЛЬ]»
    text = re.sub(rf"(?:{re.escape(PLACEHOLDER)}[\s,]*){{2,}}", PLACEHOLDER + " ", text)
    return re.sub(r"\s+", " ", text).strip()


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
def build_session() -> requests.Session:
    """Сессия с браузерным UA и русской локалью (язык хранится в cookie)."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,kk;q=0.8",
            "Connection": "keep-alive",
        }
    )
    try:
        session.get(LANG_URL, params={"lang": "ru"}, timeout=30)
    except requests.RequestException as exc:
        log.warning("Не удалось переключить локаль на ru: %s", exc)
    return session


def fetch_page(
    session: requests.Session, query: str, page: int, retries: int = 3
) -> str | None:
    """Забрать одну страницу выдачи. None — если не удалось после retries попыток."""
    params = {
        "page": page,
        "searchType": "",
        "searchText": query,
        "questionNumber": "",
        "orderBy": "",
        "govAgencyBlog": "",
        "categoryBlog": "",
        "statusBlog": "",
        "answered": "",
        "overdue": "",
    }
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(SEARCH_URL, params=params, timeout=40)
            if resp.status_code == 200:
                return resp.text
            log.warning(
                "  «%s» стр. %d: HTTP %d (попытка %d/%d)",
                query, page, resp.status_code, attempt, retries,
            )
        except requests.RequestException as exc:
            log.warning(
                "  «%s» стр. %d: %s (попытка %d/%d)",
                query, page, exc, attempt, retries,
            )
        time.sleep(2 * attempt)  # линейный backoff
    return None


# --------------------------------------------------------------------------
# Парсинг
# --------------------------------------------------------------------------
_RE_TOTAL_PAGES = re.compile(r"totalPages:\s*(\d+)")


def parse_total_pages(html: str) -> int:
    """Число страниц выдачи — сайт кладёт его в конфиг twbsPagination."""
    match = _RE_TOTAL_PAGES.search(html)
    return int(match.group(1)) if match else 1


def _field_by_icon(info_list, icon: str) -> str:
    """Достать значение <li> по классу иконки — не зависит от языка интерфейса."""
    node = info_list.select_one(f"li i.fa.{icon}")
    if node is None:
        return ""
    li = node.find_parent("li")
    return li.get_text(" ", strip=True) if li else ""


def parse_page(html: str, query: str) -> tuple[list[Complaint], int]:
    """Разобрать страницу выдачи.

    Возвращает (обращения граждан, всего карточек на странице).

    В выдаче соседствуют два типа записей:
      * обращение гражданина — есть <h3> с ФИО и номер обращения (fa-pencil);
      * публикация госоргана (/blogs/posts/) — ни номера, ни категории.
    Нужны только первые, вторые считаем отдельно — по ним видно, что страница
    не пустая, просто нерелевантная.
    """
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select("ul.blog-info")
    complaints: list[Complaint] = []

    for info_list in cards:
        card = info_list.find_parent("div", class_="col-xs-12")
        if card is None:
            continue

        # Номер обращения есть только у обращений граждан — это и есть фильтр.
        complaint_id = _field_by_icon(info_list, "fa-pencil")
        if not complaint_id:
            continue

        # Текст обращения — всё между <h3> (ФИО заявителя) и <ul class="blog-info">.
        # <h3> намеренно не читаем: это персональные данные.
        parts: list[str] = []
        heading = card.find("h3")
        node = heading.next_sibling if heading else None
        while node is not None and node is not info_list:
            if getattr(node, "name", None) == "ul":
                break
            text = node.get_text(" ", strip=True) if hasattr(node, "get_text") else str(node).strip()
            if text:
                parts.append(text)
            node = node.next_sibling

        raw_text = re.sub(r"\s+", " ", " ".join(parts)).strip()
        if not raw_text:
            continue

        readmore = card.select_one("a.readmore")
        href = readmore["href"] if readmore and readmore.has_attr("href") else ""
        url = f"{BASE_URL}{href}" if href.startswith("/") else href

        complaints.append(
            Complaint(
                id=complaint_id,
                text=anonymize(raw_text),
                category=_field_by_icon(info_list, "fa-tags"),
                date=_field_by_icon(info_list, "fa-calendar"),
                views=_field_by_icon(info_list, "fa-eye"),
                search_query=query,
                url=url,
            )
        )

    return complaints, len(cards)


# --------------------------------------------------------------------------
# Сбор
# --------------------------------------------------------------------------
def find_first_complaint_page(
    session: requests.Session,
    query: str,
    total_pages: int,
    delay: tuple[float, float],
) -> int:
    """Найти первую страницу выдачи, где начинаются обращения граждан.

    Сайт отдаёт сначала публикации госорганов, и только потом обращения.
    Для коротких казахских слов («жол», «су») публикации занимают первые
    сотни страниц, поэтому обычный обход с первой страницы не находит ничего.

    Граница ищется бинарным поиском: ~log2(N) запросов вместо N.
    Предполагается, что публикации и обращения не перемешаны — на практике
    это так; если разметка сайта изменится, поиск просто вернёт 1 и обход
    пойдёт с начала.
    """
    low, high = 1, total_pages
    boundary: int | None = None

    while low <= high:
        mid = (low + high) // 2
        html = fetch_page(session, query, mid)
        time.sleep(random.uniform(*delay))
        if html is None:
            break

        items, cards = parse_page(html, query)
        if cards == 0:
            high = mid - 1
            continue
        if items:
            boundary = mid
            high = mid - 1
        else:
            low = mid + 1

    return boundary or 1


def scrape(
    queries: list[str],
    max_pages: int,
    delay: tuple[float, float],
    seek: bool = True,
) -> list[Complaint]:
    """Обойти все запросы и страницы, вернуть обращения без дублей по id."""
    session = build_session()
    collected: dict[str, Complaint] = {}

    for q_index, query in enumerate(queries, start=1):
        log.info("[%d/%d] Запрос «%s»", q_index, len(queries), query)

        first = fetch_page(session, query, 1)
        if first is None:
            log.error("  пропускаю «%s» — первая страница недоступна", query)
            continue

        total_pages = parse_total_pages(first)

        # Если на первой странице одни публикации — ищем, где начинаются обращения.
        start_page = 1
        if seek and total_pages > 1:
            first_items, _ = parse_page(first, query)
            if not first_items:
                log.info("  на стр. 1 обращений нет, ищу границу в %d страницах…", total_pages)
                start_page = find_first_complaint_page(session, query, total_pages, delay)
                log.info("  обращения начинаются со стр. %d", start_page)

        last_page = total_pages if max_pages <= 0 else min(total_pages, start_page + max_pages - 1)
        log.info(
            "  страниц в выдаче: %d, обойду %d–%d", total_pages, start_page, last_page
        )

        found_for_query = 0
        new_for_query = 0
        skipped_posts = 0

        for page in range(start_page, last_page + 1):
            html = first if page == 1 else fetch_page(session, query, page)
            if html is None:
                log.warning("  «%s» стр. %d пропущена", query, page)
                continue

            page_items, cards_on_page = parse_page(html, query)
            found_for_query += len(page_items)
            skipped_posts += cards_on_page - len(page_items)

            for item in page_items:
                if item.id not in collected:
                    collected[item.id] = item
                    new_for_query += 1

            log.info(
                "  стр. %d/%d — карточек %d, из них обращений %d, новых %d, в наборе %d",
                page, last_page, cards_on_page, len(page_items),
                new_for_query, len(collected),
            )

            # Страница без обращений — ещё не конец выдачи: там могут быть
            # только публикации госорганов. Останавливаемся, лишь если на
            # странице вообще нет карточек.
            if cards_on_page == 0:
                log.info("  страница без карточек — выдача по «%s» закончилась", query)
                break

            if page < last_page:
                time.sleep(random.uniform(*delay))

        log.info(
            "  итог по «%s»: обращений %d (уникальных +%d), пропущено публикаций %d",
            query, found_for_query, new_for_query, skipped_posts,
        )

    return list(collected.values())


def save_csv(rows: list[Complaint], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig — чтобы Excel на Windows не ломал кириллицу
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


# --------------------------------------------------------------------------
# Отчёт
# --------------------------------------------------------------------------
def _year_of(date: str) -> str:
    match = re.search(r"\b(\d{4})\b", date or "")
    return match.group(1) if match else "не определён"


def report(rows: list[Complaint], path: Path) -> None:
    line = "=" * 70
    print(f"\n{line}\nРЕЗУЛЬТАТ СБОРА\n{line}")
    print(f"Файл: {path}")
    print(f"Всего обращений (уникальных по id): {len(rows)}")

    if not rows:
        print("\nНичего не собрано — проверьте доступность сайта и параметры запуска.")
        return

    print(f"\n{line}\nПЕРВЫЕ 5 СТРОК\n{line}")
    for row in rows[:5]:
        text = row.text if len(row.text) <= 160 else row.text[:157] + "…"
        print(f"\nid={row.id}  дата={row.date}  просмотров={row.views}")
        print(f"  запрос:    {row.search_query}")
        print(f"  категория: {row.category or '—'}")
        print(f"  текст:     {text}")

    print(f"\n{line}\nРАСПРЕДЕЛЕНИЕ ПО КАТЕГОРИЯМ\n{line}")
    categories = Counter(r.category or "без категории" for r in rows)
    width = max(len(c) for c in categories) if categories else 10
    for name, count in categories.most_common():
        share = count / len(rows) * 100
        print(f"  {name:<{width}}  {count:>5}  ({share:5.1f}%)")

    print(f"\n{line}\nРАСПРЕДЕЛЕНИЕ ПО ГОДАМ\n{line}")
    years = Counter(_year_of(r.date) for r in rows)
    for year, count in sorted(years.items()):
        bar = "█" * max(1, round(count / max(years.values()) * 40))
        print(f"  {year}  {count:>5}  {bar}")

    print(f"\n{line}\nРАСПРЕДЕЛЕНИЕ ПО ПОИСКОВЫМ ЗАПРОСАМ\n{line}")
    for name, count in Counter(r.search_query for r in rows).most_common():
        print(f"  {name:<20} {count:>5}")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Сбор обращений граждан с dialog.egov.kz",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--queries", nargs="+", default=None,
        help="явный список запросов (перекрывает --query-set)",
    )
    parser.add_argument(
        "--query-set", choices=["broad", "focused", "all"], default="broad",
        help="broad — 18 одиночных слов; focused — целевые фразы; all — оба списка",
    )
    parser.add_argument(
        "--max-pages", type=int, default=10,
        help="максимум страниц на запрос; 0 — все доступные (по умолчанию 10)",
    )
    parser.add_argument(
        "--delay", type=float, nargs=2, metavar=("MIN", "MAX"), default=[1.0, 2.0],
        help="пауза между запросами в секундах (по умолчанию 1 2)",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT,
        help=f"путь к CSV (по умолчанию {DEFAULT_OUTPUT.relative_to(PROJECT_ROOT)})",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="только предупреждения и ошибки",
    )
    return parser.parse_args(argv)


def _force_utf8_stdout() -> None:
    """Windows-консоль по умолчанию в cp1251 и падает на «қ», «ә», «ң».

    Переключаем поток на UTF-8; errors="replace" — чтобы вывод отчёта никогда
    не ронял скрипт после того, как данные уже собраны и записаны.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdout()
    args = parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s  %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )

    if args.delay[0] < 1.0:
        log.warning(
            "Пауза меньше 1 с нарушает Crawl-delay: 1 из robots.txt сайта."
        )
    log.warning(
        "robots.txt сайта закрывает /search от автоматического обхода. "
        "Скрипт всё равно к нему обращается — убедитесь, что это осознанное решение."
    )

    if args.queries:
        queries = args.queries
    elif args.query_set == "focused":
        queries = QUERIES_FOCUSED
    elif args.query_set == "all":
        # dict.fromkeys сохраняет порядок и убирает повторы между списками
        queries = list(dict.fromkeys(QUERIES + QUERIES_FOCUSED))
    else:
        queries = QUERIES

    started = time.time()
    rows = scrape(queries, args.max_pages, tuple(args.delay))

    # стабильный порядок: свежие сверху
    rows.sort(key=lambda r: (_year_of(r.date), r.date, r.id), reverse=True)

    save_csv(rows, args.output)
    report(rows, args.output)
    log.info("Готово за %.1f с", time.time() - started)
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
