#!/usr/bin/env python3
"""Черновая разметка обращений под таксономию AURA.

Зачем
-----
В сыром CSV с dialog.egov.kz категории чужие — таксономия портала
(«Строительство, дольщики, жилищные проблемы», «Свободная тема»). Для обучения
нужны наши: ЖКХ / Дороги / Освещение / Транспорт / Благоустройство.

Размечать 300+ обращений руками долго, поэтому метка собирается из двух
независимых источников:

    1. search_query — по какому слову обращение нашлось. Найденное по
       «светофор» почти наверняка про светофоры.
    2. Правила из backend/services/classifier.py — те же, что работают
       в проде сейчас.

Дальше:
    оба согласны        -> метка принимается автоматически (confident)
    согласен один       -> в очередь на проверку (review)
    оба молчат          -> в очередь на проверку (unlabeled)

Человеку остаётся просмотреть только спорное, а не весь корпус.

Выход
-----
    data/processed/train_confident.csv  — готово к обучению
    data/processed/needs_review.csv     — на ручную проверку

Запуск
------
    python data/scripts/build_training_set.py
    python data/scripts/build_training_set.py --input data/raw/other.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw" / "dialog_egov_complaints.csv"
OUT_DIR = PROJECT_ROOT / "data" / "processed"

# Правила берём из бэкенда, чтобы не разъезжались две копии.
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
try:
    from services.classifier import match_rules  # type: ignore
except ImportError as exc:  # pragma: no cover
    print(f"Не удалось импортировать правила из backend: {exc}", file=sys.stderr)
    print("Установите pydantic в текущее окружение.", file=sys.stderr)
    raise SystemExit(1)


# Поисковый запрос -> (категория, подкатегория).
# None означает «запрос слишком общий, метку по нему не выводим».
QUERY_TO_LABEL: dict[str, tuple[str, str] | None] = {
    "ЖКХ": None,                 # слишком широкий: и вода, и тепло, и жильё
    "благоустройство": None,     # пересекается с мусором и площадками
    "водоснабжение": ("ЖКХ", "Водоснабжение"),
    "канализация": ("ЖКХ", "Водоснабжение"),
    "су": ("ЖКХ", "Водоснабжение"),
    "отопление": ("ЖКХ", "Отопление"),
    "жылу": ("ЖКХ", "Отопление"),
    "лифт": ("ЖКХ", "Лифт"),
    "освещение": ("Освещение", "Уличное освещение"),
    "жарық": ("Освещение", "Уличное освещение"),
    "дороги": ("Дороги", "Дорожное покрытие"),
    "жол": ("Дороги", "Дорожное покрытие"),
    "светофор": ("Дороги", "Светофоры"),
    "мусор": ("Благоустройство", "Вывоз мусора"),
    "қоқыс": ("Благоустройство", "Вывоз мусора"),
    "транспорт": ("Транспорт", "Общественный транспорт"),
    "автобус": ("Транспорт", "Общественный транспорт"),
    "көлік": ("Транспорт", "Общественный транспорт"),

    # --- целевые фразы (QUERIES_FOCUSED из скрапера) ---
    # Водоснабжение и канализация
    "прорвало трубу": ("ЖКХ", "Водоснабжение"),
    "нет холодной воды": ("ЖКХ", "Водоснабжение"),
    "нет горячей воды": ("ЖКХ", "Водоснабжение"),
    "затопило подвал": ("ЖКХ", "Водоснабжение"),
    "канализация засор": ("ЖКХ", "Водоснабжение"),
    "течет стояк": ("ЖКХ", "Водоснабжение"),
    "су жоқ": ("ЖКХ", "Водоснабжение"),
    "су құбыры жарылды": ("ЖКХ", "Водоснабжение"),
    # Отопление
    "нет отопления": ("ЖКХ", "Отопление"),
    "холодные батареи": ("ЖКХ", "Отопление"),
    "не топят": ("ЖКХ", "Отопление"),
    "жылу жоқ": ("ЖКХ", "Отопление"),
    "пәтер суық": ("ЖКХ", "Отопление"),
    # Освещение
    "уличное освещение": ("Освещение", "Уличное освещение"),
    "не горят фонари": ("Освещение", "Уличное освещение"),
    "нет освещения во дворе": ("Освещение", "Уличное освещение"),
    "көше жарығы": ("Освещение", "Уличное освещение"),
    # Дороги
    "яма на дороге": ("Дороги", "Дорожное покрытие"),
    "разбитая дорога": ("Дороги", "Дорожное покрытие"),
    "нет асфальта": ("Дороги", "Дорожное покрытие"),
    "тротуар разбит": ("Дороги", "Дорожное покрытие"),
    "жол жөндеу": ("Дороги", "Дорожное покрытие"),
    "жол бұзылған": ("Дороги", "Дорожное покрытие"),
    "не работает светофор": ("Дороги", "Светофоры"),
    # Транспорт
    "автобус не ходит": ("Транспорт", "Общественный транспорт"),
    "нет расписания на остановке": ("Транспорт", "Общественный транспорт"),
    "водитель автобуса": ("Транспорт", "Общественный транспорт"),
    "отменили маршрут": ("Транспорт", "Общественный транспорт"),
    "автобус жүрмейді": ("Транспорт", "Общественный транспорт"),
    "қоғамдық көлік": ("Транспорт", "Общественный транспорт"),
    # Благоустройство
    "не вывозят мусор": ("Благоустройство", "Вывоз мусора"),
    "мусорные контейнеры переполнены": ("Благоустройство", "Вывоз мусора"),
    "стихийная свалка": ("Благоустройство", "Вывоз мусора"),
    "детская площадка сломана": ("Благоустройство", "Детские площадки"),
    "қоқыс шығарылмайды": ("Благоустройство", "Вывоз мусора"),
    # Лифт
    "не работает лифт": ("ЖКХ", "Лифт"),
    "лифт сломан": ("ЖКХ", "Лифт"),
    "лифт жұмыс істемейді": ("ЖКХ", "Лифт"),
}


@dataclass
class Labeled:
    id: str
    text: str
    category: str
    subcategory: str
    source: str          # чем размечено: both / query / rules / none
    query_label: str
    rule_label: str
    search_query: str
    date: str
    portal_category: str


def label_by_rules(text: str) -> tuple[str, str] | None:
    """Прогнать текст через правила прода — ровно ту же функцию, что и API."""
    matched = match_rules(text)
    if matched is None:
        return None
    (category, subcategory, _service), _words = matched
    return category, subcategory


def build(rows: list[dict]) -> list[Labeled]:
    out: list[Labeled] = []
    for r in rows:
        text = r["text"]
        by_query = QUERY_TO_LABEL.get(r["search_query"])
        by_rules = label_by_rules(text)

        if by_query and by_rules and by_query[0] == by_rules[0]:
            # Совпала категория — берём подкатегорию правил, она точнее.
            label, source = (by_query[0], by_rules[1]), "both"
        elif by_query and by_rules:
            label, source = by_rules, "conflict"
        elif by_rules:
            label, source = by_rules, "rules"
        elif by_query:
            label, source = by_query, "query"
        else:
            label, source = ("", ""), "none"

        out.append(
            Labeled(
                id=r["id"],
                text=text,
                category=label[0],
                subcategory=label[1],
                source=source,
                query_label="/".join(by_query) if by_query else "",
                rule_label="/".join(by_rules) if by_rules else "",
                search_query=r["search_query"],
                date=r["date"],
                portal_category=r["category"],
            )
        )
    return out


def save(rows: list[Labeled], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = list(Labeled.__annotations__)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def _force_utf8_stdout() -> None:
    """Консоль Windows по умолчанию в cp1251 и падает на казахских буквах."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    _force_utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, nargs="+", default=[DEFAULT_INPUT],
        help="один или несколько CSV из data/raw (склеиваются с дедупликацией по id)",
    )
    args = parser.parse_args()

    rows: list[dict] = []
    seen: set[str] = set()
    for path in args.input:
        if not path.exists():
            print(f"пропускаю (нет файла): {path}")
            continue
        part = list(csv.DictReader(path.open(encoding="utf-8-sig")))
        fresh = [r for r in part if r["id"] not in seen]
        seen.update(r["id"] for r in fresh)
        rows.extend(fresh)
        print(f"  {path.name}: {len(part)} строк, новых {len(fresh)}")
    print()

    labeled = build(rows)

    confident = [r for r in labeled if r.source == "both"]
    review = [r for r in labeled if r.source != "both"]

    save(confident, OUT_DIR / "train_confident.csv")
    save(review, OUT_DIR / "needs_review.csv")

    line = "=" * 64
    print(f"{line}\nЧЕРНОВАЯ РАЗМЕТКА\n{line}")
    print(f"всего обращений: {len(labeled)}")
    print()
    for name, count in Counter(r.source for r in labeled).most_common():
        explain = {
            "both": "оба источника согласны — берём автоматически",
            "rules": "сработали только правила — проверить",
            "query": "только поисковый запрос — проверить",
            "conflict": "источники расходятся — проверить",
            "none": "не размечено — проверить",
        }[name]
        print(f"  {name:<9} {count:>4}   {explain}")

    print(f"\n{line}\nГОТОВО К ОБУЧЕНИЮ ({len(confident)})\n{line}")
    for (cat, sub), n in Counter(
        (r.category, r.subcategory) for r in confident
    ).most_common():
        print(f"  {n:>4}  {cat} / {sub}")

    print(f"\n{line}\nНА ПРОВЕРКУ ({len(review)})\n{line}")
    for name, n in Counter(r.search_query for r in review).most_common(8):
        print(f"  {n:>4}  запрос «{name}»")

    print(f"\nФайлы: {OUT_DIR / 'train_confident.csv'}")
    print(f"       {OUT_DIR / 'needs_review.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
