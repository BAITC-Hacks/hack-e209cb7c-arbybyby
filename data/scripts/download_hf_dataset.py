#!/usr/bin/env python3
"""Загрузка готового датасета обращений с HuggingFace.

Источник: Adilbai/kz-gov-complaints-data-kz-ru (1200 записей, Apache-2.0).

ВАЖНО про природу данных
------------------------
В карточке датасета стоят теги annotations_creators: machine-generated и
language_creators: machine-generated. Это СИНТЕТИЧЕСКИЕ обращения, сгенерированные
моделью, а не собранные у реальных граждан. Отсюда два следствия:

    1. Для обучения они годятся — тексты правдоподобные и размеченные.
    2. Для ЗАМЕРА точности — нет. Модель, обученная и проверенная на синтетике,
       покажет завышенную цифру. Отложенную выборку берите из dialog_egov.

Поэтому в выгрузке проставляется source=huggingface — prepare_dataset.py
использует это, чтобы не пускать синтетику в тестовую выборку.

Структура исходника
-------------------
Каждая запись содержит ПАРАЛЛЕЛЬНЫЕ тексты на двух языках:
    id, text_kz, text_ru, category, urgency, region, status, date_created, ...

Скрипт разворачивает каждую запись в две строки (kk и ru), поэтому на выходе
до 2400 примеров вместо 1200.

Запуск
------
    python data/scripts/download_hf_dataset.py
    python data/scripts/download_hf_dataset.py --output data/raw/hf.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "raw" / "hf_complaints.csv"

DATASET_ID = "Adilbai/kz-gov-complaints-data-kz-ru"

CSV_COLUMNS = [
    "id", "text", "category", "language", "region", "urgency", "date", "source",
]


def _force_utf8_stdout() -> None:
    """Консоль Windows по умолчанию в cp1251 и падает на казахских буквах."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def expand_rows(dataset) -> list[dict]:
    """Развернуть параллельные тексты в отдельные строки по языкам."""
    out: list[dict] = []
    for row in dataset:
        base = {
            "category": (row.get("category") or "").strip(),
            "region": (row.get("region") or "").strip(),
            "urgency": (row.get("urgency") or "").strip(),
            "date": (row.get("date_created") or "") or "",
            "source": "huggingface",
        }
        for field, lang in (("text_ru", "ru"), ("text_kz", "kk")):
            text = (row.get(field) or "").strip()
            if not text:
                continue
            out.append(
                {
                    **base,
                    "id": f"hf-{row.get('id')}-{lang}",
                    "text": " ".join(text.split()),
                    "language": lang,
                }
            )
    return out


def main() -> int:
    _force_utf8_stdout()
    parser = argparse.ArgumentParser(description="Загрузка датасета с HuggingFace")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dataset", default=DATASET_ID)
    args = parser.parse_args()

    try:
        from datasets import load_dataset
    except ImportError:
        print("Нет библиотеки datasets. Установите:", file=sys.stderr)
        print("  pip install -r data/scripts/requirements.txt", file=sys.stderr)
        return 1

    print(f"Загружаю {args.dataset} …")
    ds = load_dataset(args.dataset)
    print(f"сплиты: {', '.join(ds.keys())}")

    rows: list[dict] = []
    for split_name, split in ds.items():
        part = expand_rows(split)
        print(f"  {split_name}: {len(split)} записей -> {len(part)} строк (kk+ru)")
        rows.extend(part)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    line = "=" * 64
    print(f"\n{line}\nИТОГ\n{line}")
    print(f"файл:  {args.output}")
    print(f"строк: {len(rows)}")

    print(f"\nпо языку:")
    for lang, n in Counter(r["language"] for r in rows).most_common():
        print(f"  {lang}  {n}")

    print(f"\nпо категориям:")
    for cat, n in Counter(r["category"] for r in rows).most_common():
        print(f"  {n:>5}  {cat or '(пусто)'}")

    print(
        "\nВНИМАНИЕ: датасет машинно-сгенерированный. Использовать для обучения,"
        "\nно НЕ для замера точности — иначе цифра будет завышенной."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
