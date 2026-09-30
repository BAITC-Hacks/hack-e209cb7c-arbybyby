#!/usr/bin/env python3
"""Загрузка и фильтрация KazSAnDRA (IS2AI).

Источник: github.com/IS2AI/KazSAnDRA — Kazakh Sentiment Analysis Dataset of
Reviews and Attitudes, ~180k отзывов.

ВЫВОД ПО ПРИГОДНОСТИ: источник для нашей задачи НЕ подходит
-----------------------------------------------------------
Проверено на валидационном сплите (16 796 строк):

    совпало по инфраструктурным ключевым словам: 152 (0.9%)
    из них по существу релевантных: единицы

Причины:
    1. Это отзывы о приложениях и товарах (домены appstore, market,
       bookstore, mapping), а не обращения граждан в органы власти.
    2. Метка — тональность (0/1 или 1-5 звёзд), а не категория проблемы.
       Для классификатора по категориям она бесполезна.
    3. Совпадения по ключевым словам — почти сплошь омонимы:
         «жол»     -> «жолдасыма» (супругу), «ең тиімді жол» (лучший способ)
         «мусор»   -> оценка игры («гавно игра»)
         «жарық»   -> отзыв о книге
         «жолдың»  -> «вдоль дороги» в отзыве о заведении

Скрипт оставлен, чтобы вывод можно было перепроверить, и на случай, если
понадобится доменный текст на казахском для других задач (например, для
дообучения эмбеддингов на разговорной лексике). В обучающую выборку
классификатора результат по умолчанию НЕ включается — см. prepare_dataset.py.

Запуск
------
    python data/scripts/download_kazsandra.py
    python data/scripts/download_kazsandra.py --splits 04_pc_valid  # быстрая проверка
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "raw" / "kazsandra_filtered.csv"

RAW_BASE = "https://raw.githubusercontent.com/IS2AI/KazSAnDRA/main/dataset"

# pc — polarity classification, sc — score classification.
# Наборы пересекаются по текстам, поэтому дедуплицируем по custom_id.
ALL_SPLITS = [
    "01_pc_train_ib", "02_pc_train_ros", "03_pc_train_rus",
    "04_pc_valid", "05_pc_test",
    "06_sc_train_ib", "07_sc_train_ros", "08_sc_train_rus",
    "09_sc_valid", "10_sc_test",
]

# Те же маркеры, что в маппинге категорий проекта.
KEYWORDS = [
    "труб", "вод", "дорог", "свет", "мусор", "лифт", "автобус",
    "отопл", "жылу", "жол", "қоқыс", "жарық",
]
KEYWORD_RE = re.compile(r"\b(?:" + "|".join(KEYWORDS) + r")", re.IGNORECASE)

CSV_COLUMNS = ["id", "text", "category", "language", "domain", "sentiment", "source"]


def _force_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def fetch_split(name: str) -> list[dict]:
    """Скачать один zip и распарсить лежащий внутри CSV."""
    url = f"{RAW_BASE}/{name}.zip"
    resp = requests.get(url, timeout=180)
    resp.raise_for_status()
    archive = zipfile.ZipFile(io.BytesIO(resp.content))
    member = archive.namelist()[0]
    text = archive.read(member).decode("utf-8", errors="replace")
    return list(csv.DictReader(io.StringIO(text)))


def main() -> int:
    _force_utf8_stdout()
    parser = argparse.ArgumentParser(description="Фильтрация KazSAnDRA")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--splits", nargs="+", default=ALL_SPLITS)
    args = parser.parse_args()

    seen_ids: set[str] = set()
    total_seen = 0
    matched: list[dict] = []

    for name in args.splits:
        try:
            rows = fetch_split(name)
        except Exception as exc:
            print(f"  {name}: не скачан ({exc})")
            continue

        fresh = [r for r in rows if r.get("custom_id") not in seen_ids]
        seen_ids.update(r.get("custom_id") for r in fresh)
        total_seen += len(fresh)

        hits = [r for r in fresh if KEYWORD_RE.search(r.get("text") or "")]
        for r in hits:
            matched.append(
                {
                    "id": f"kas-{r.get('custom_id')}",
                    "text": " ".join((r.get("text") or "").split()),
                    "category": "",          # категории в источнике нет
                    "language": "kk",
                    "domain": r.get("domain") or "",
                    "sentiment": r.get("label") or "",
                    "source": "kazsandra",
                }
            )
        print(f"  {name}: {len(rows)} строк, новых {len(fresh)}, совпало {len(hits)}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(matched)

    line = "=" * 64
    print(f"\n{line}\nИТОГ\n{line}")
    print(f"просмотрено уникальных отзывов: {total_seen}")
    share = len(matched) / total_seen * 100 if total_seen else 0
    print(f"прошло фильтр: {len(matched)} ({share:.1f}%)")
    print(f"файл: {args.output}")

    if matched:
        print("\nпо доменам:")
        for dom, n in Counter(r["domain"] for r in matched).most_common(6):
            print(f"  {n:>5}  {dom or '(пусто)'}")
        print("\nпримеры совпадений:")
        for r in matched[:5]:
            print(f"  [{r['domain']}] {r['text'][:90]}")

    print(
        "\nНАПОМИНАНИЕ: это отзывы о приложениях и товарах с метками тональности."
        "\nКатегорий проблем в источнике нет, совпадения по ключевым словам —"
        "\nпреимущественно омонимы. В обучение классификатора не включать."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
