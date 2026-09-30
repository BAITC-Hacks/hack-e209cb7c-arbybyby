#!/usr/bin/env python3
"""Сбор обращений из «Виртуальной приёмной» акиматов на gov.kz.

ДВЕ ПОПРАВКИ К ИСХОДНОМУ ЗАМЫСЛУ
--------------------------------

1. Поддоменов вида astana.gov.kz НЕ СУЩЕСТВУЕТ.
   DNS их не резолвит (getaddrinfo failed). Портал давно переехал на единую
   платформу, и акиматы живут по пути:

       https://www.gov.kz/memleket/entities/<код>?lang=ru

   Проверено: astana, almaty, shymkent, karaganda отвечают 200.

2. Раздел называется «Виртуальная приёмная» (Вопрос-Ответ), а данные отдаёт
   не HTML, а API — сайт это React-SPA, страница приходит пустой заглушкой
   на 836 байт. Нужный вызов найден в JS-бандле:

       POST https://www.gov.kz/api/v2/public-data
       {"data": {...}, "project_slug": "<код>", "content_type_slug": "vr_question"}

ОГРАНИЧЕНИЕ: API закрыт антибот-токеном
---------------------------------------
Запрос без токена возвращает:

    HTTP 400 {"error":"browserTicketMissing"}

Это осознанная защита от программного доступа со стороны портала, и обходить
её скрипт не пытается. Если доступ нужен, токен берётся из СВОЕЙ сессии
браузера и передаётся скрипту явно:

    1. Открыть https://www.gov.kz/memleket/entities/astana?lang=ru
    2. DevTools -> Network -> найти запрос к /api/v2/public-data
    3. Скопировать заголовок с тикетом (или cookie целиком)
    4. Запустить:
         python data/scripts/scrape_gov_kz.py --browser-ticket "<значение>"
       либо
         python data/scripts/scrape_gov_kz.py --cookie "<строка cookie>"

Ответственность за соблюдение условий использования портала лежит на том,
кто запускает скрипт.

АЛЬТЕРНАТИВА, КОТОРАЯ УЖЕ РАБОТАЕТ
----------------------------------
Блог-платформа dialog.egov.kz — это и есть официальная площадка обращений
к руководителям госорганов, включая акимов. Именно оттуда собраны 1684
обращения скриптом scrape_dialog_egov.py. То есть цель этого источника
в значительной степени уже закрыта.

Запуск
------
    python data/scripts/scrape_gov_kz.py --browser-ticket "<...>"
    python data/scripts/scrape_gov_kz.py --entities astana almaty --pages 3
"""
from __future__ import annotations

import argparse
import csv
import logging
import random
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "raw" / "gov_kz_complaints.csv"

BASE = "https://www.gov.kz"
API_URL = f"{BASE}/api/v2/public-data"
ENTITY_URL = f"{BASE}/memleket/entities"

# Коды акиматов на единой платформе (проверены: отвечают 200).
ENTITIES: list[str] = [
    "astana", "almaty", "shymkent", "karaganda", "pavlodar",
    "aktobe", "atyrau", "kostanay", "semey", "mangystau",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

CSV_COLUMNS = ["id", "text", "category", "date", "entity", "language", "source"]

log = logging.getLogger("gov_kz")

# Обезличивание переиспользуем из соседнего скрипта — одна реализация на проект.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from scrape_dialog_egov import anonymize
except ImportError:  # pragma: no cover
    def anonymize(text: str) -> str:  # type: ignore[misc]
        return text


class BrowserTicketRequired(RuntimeError):
    """API отказал из-за отсутствия антибот-токена."""


def build_session(ticket: str | None, cookie: str | None) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": BASE,
            "Referer": f"{ENTITY_URL}/astana?lang=ru",
        }
    )
    if ticket:
        # Портал ожидает тикет в заголовке; имя может меняться, поэтому
        # отправляем в нескольких распространённых вариантах.
        session.headers["browser-ticket"] = ticket
        session.headers["X-Browser-Ticket"] = ticket
    if cookie:
        session.headers["Cookie"] = cookie
    return session


def fetch_page(session: requests.Session, entity: str, page: int, size: int) -> list[dict]:
    payload = {
        "data": {"page": page, "size": size},
        "project_slug": entity,
        "content_type_slug": "vr_question",
    }
    resp = session.post(API_URL, json=payload, timeout=40)

    if resp.status_code == 400 and "browserTicket" in resp.text:
        raise BrowserTicketRequired(resp.text.strip())
    if resp.status_code != 200:
        log.warning("  %s стр. %d: HTTP %d", entity, page, resp.status_code)
        return []

    try:
        body = resp.json()
    except ValueError:
        log.warning("  %s стр. %d: ответ не JSON", entity, page)
        return []

    # Структура ответа портала может отличаться по версиям — пробуем варианты.
    for key in ("data", "items", "content", "results"):
        block = body.get(key)
        if isinstance(block, list):
            return block
        if isinstance(block, dict):
            for inner in ("items", "content", "results"):
                if isinstance(block.get(inner), list):
                    return block[inner]
    return []


def parse_item(item: dict, entity: str) -> dict | None:
    text = ""
    for key in ("question", "text", "body", "content", "description"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            text = value
            break
    if not text:
        return None

    category = ""
    for key in ("category", "topic", "vr_category", "theme"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            category = value.strip()
            break
        if isinstance(value, dict):
            category = str(value.get("title") or value.get("name") or "").strip()
            if category:
                break

    date = ""
    for key in ("created_at", "date", "publish_date", "createdAt"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            date = value.strip()[:10]
            break

    return {
        "id": f"gov-{entity}-{item.get('id') or item.get('uuid') or hash(text) & 0xFFFFFF}",
        "text": anonymize(" ".join(text.split())),
        "category": category,
        "date": date,
        "entity": entity,
        "language": "ru",
        "source": "gov_kz",
    }


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Виртуальная приёмная gov.kz")
    parser.add_argument("--entities", nargs="+", default=ENTITIES)
    parser.add_argument("--pages", type=int, default=5, help="страниц на акимат")
    parser.add_argument("--size", type=int, default=20, help="записей на страницу")
    parser.add_argument("--browser-ticket", default=None, help="антибот-токен из своей сессии")
    parser.add_argument("--cookie", default=None, help="строка Cookie из своей сессии")
    parser.add_argument("--delay", type=float, nargs=2, default=[2.0, 3.0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s  %(message)s",
        datefmt="%H:%M:%S", stream=sys.stdout,
    )

    if not args.browser_ticket and not args.cookie:
        log.warning(
            "Ни --browser-ticket, ни --cookie не заданы. API gov.kz отвечает "
            "400 browserTicketMissing на запросы без токена — скорее всего "
            "ничего не соберётся. Как получить токен, описано в шапке файла."
        )

    session = build_session(args.browser_ticket, args.cookie)
    collected: dict[str, dict] = {}

    for i, entity in enumerate(args.entities, start=1):
        log.info("[%d/%d] Акимат «%s»", i, len(args.entities), entity)
        for page in range(args.pages):
            try:
                items = fetch_page(session, entity, page, args.size)
            except BrowserTicketRequired as exc:
                log.error("  API требует антибот-токен: %s", exc)
                log.error("  Сбор остановлен. См. инструкцию в шапке скрипта.")
                items = []
                page = args.pages  # прекращаем по этому акимату
                break

            if not items:
                break

            new = 0
            for raw in items:
                parsed = parse_item(raw, entity)
                if parsed and parsed["id"] not in collected:
                    collected[parsed["id"]] = parsed
                    new += 1
            log.info("  стр. %d — получено %d, новых %d", page, len(items), new)

            if page < args.pages - 1:
                time.sleep(random.uniform(*args.delay))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(collected.values())

    print(f"\nсобрано обращений: {len(collected)}")
    print(f"файл: {args.output}")
    if not collected:
        print(
            "\nПусто — это ожидаемо без антибот-токена. Данные по акимам уже есть "
            "в data/raw/dialog_egov_*.csv: dialog.egov.kz и есть официальная "
            "площадка обращений к руководителям госорганов."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
