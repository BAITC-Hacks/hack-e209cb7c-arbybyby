#!/usr/bin/env python3
"""Сборка обучающего набора из всех источников в data/raw/.

Что делает
----------
    1. Склеивает все CSV из data/raw/ (источник определяется по имени файла
       либо по колонке source).
    2. Дедуплицирует ПО ТЕКСТУ, а не по id: у разных источников свои id,
       и одно обращение может прийти дважды.
    3. Приводит категории источников к единой таксономии проекта.
    4. Определяет язык (kk / ru) по наличию специфичных букв.
    5. Делит на train/val/test 70/15/15 со стратификацией по метке.

Таксономия проекта
------------------
    ЖКХ / Водоснабжение, Отопление, Лифт
    Дороги / Дорожное покрытие, Светофоры
    Освещение / Уличное освещение
    Транспорт / Общественный транспорт
    Благоустройство / Вывоз мусора, Детские площадки
    Другое / Общие вопросы

Источники и как с ними обходимся
--------------------------------
    dialog_egov   — реальные обращения граждан. Метка выводится из поискового
                    запроса и правил прода (см. build_training_set.py).
    huggingface   — СИНТЕТИКА (машинная генерация). Годится для обучения,
                    но не для замера точности: см. --real-eval.
    kazsandra     — отзывы о товарах с метками тональности, категорий нет.
                    По умолчанию ИСКЛЮЧАЕТСЯ (--include-kazsandra чтобы вернуть).
    gov_kz        — API портала закрыт антибот-токеном, обычно файл пуст.

Запуск
------
    python data/scripts/prepare_dataset.py
    python data/scripts/prepare_dataset.py --real-eval      # val/test только из реальных
    python data/scripts/prepare_dataset.py --include-kazsandra
"""
from __future__ import annotations

import argparse
import csv
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUT_DIR = PROJECT_ROOT / "data" / "processed"

# Правила и маппинг запросов берём из уже существующих модулей проекта,
# чтобы логика разметки жила в одном месте.
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from services.classifier import match_rules  # noqa: E402
from build_training_set import QUERY_TO_LABEL  # noqa: E402

CSV_COLUMNS = [
    "id", "text", "label", "category", "subcategory",
    "language", "source", "date", "label_origin",
]

# Категории HuggingFace-датасета -> наша таксономия.
HF_CATEGORY_MAP: dict[str, tuple[str, str]] = {
    "жкх": ("ЖКХ", "Общие вопросы"),
    "дороги": ("Дороги", "Дорожное покрытие"),
    "общественный транспорт": ("Транспорт", "Общественный транспорт"),
    "экология": ("Благоустройство", "Вывоз мусора"),
    # Вне периметра продукта — отправляем в «Другое», они нужны как
    # отрицательные примеры, чтобы модель не тянула всё в городские категории.
    "медицина": ("Другое", "Общие вопросы"),
    "образование": ("Другое", "Общие вопросы"),
    "полиция": ("Другое", "Общие вопросы"),
    "интернет": ("Другое", "Общие вопросы"),
    "соцподдержка": ("Другое", "Общие вопросы"),
    "коррупция": ("Другое", "Общие вопросы"),
}

_KK_LETTERS = re.compile(r"[әғқңөұүhіӘҒҚҢӨҰҮҺІ]")
_WS = re.compile(r"\s+")


def _force_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def detect_language(text: str) -> str:
    """Казахский определяем по специфичным буквам — их нет в русском."""
    return "kk" if len(_KK_LETTERS.findall(text)) > 3 else "ru"


def normalize_for_dedup(text: str) -> str:
    """Ключ дедупликации: без регистра, пунктуации и лишних пробелов."""
    lowered = re.sub(r"[^\w\s]", " ", text.lower())
    return _WS.sub(" ", lowered).strip()


def source_of(path: Path, row: dict) -> str:
    if row.get("source"):
        return row["source"]
    name = path.name.lower()
    if "dialog_egov" in name:
        return "dialog_egov"
    if "hf_" in name or "huggingface" in name:
        return "huggingface"
    if "kazsandra" in name:
        return "kazsandra"
    if "gov_kz" in name:
        return "gov_kz"
    return "unknown"


def label_row(row: dict, source: str) -> tuple[tuple[str, str], str] | None:
    """Вернуть ((категория, подкатегория), чем размечено) либо None."""
    text = row.get("text") or ""

    if source == "dialog_egov":
        by_query = QUERY_TO_LABEL.get(row.get("search_query", ""))
        matched = match_rules(text)
        by_rules = (matched[0][0], matched[0][1]) if matched else None

        if by_query and by_rules and by_query[0] == by_rules[0]:
            return (by_query[0], by_rules[1]), "query+rules"
        if by_query:
            return by_query, "query"
        if by_rules:
            return by_rules, "rules"
        return None

    if source == "huggingface":
        raw = (row.get("category") or "").strip().lower()
        mapped = HF_CATEGORY_MAP.get(raw)
        return (mapped, "hf_category") if mapped else None

    # kazsandra / gov_kz / unknown — своей категории нет
    matched = match_rules(text)
    if matched:
        return (matched[0][0], matched[0][1]), "rules"
    return None


def load_all(raw_dir: Path, include_kazsandra: bool) -> list[dict]:
    rows: list[dict] = []
    seen: dict[str, str] = {}
    stats_files: list[tuple[str, int, int, int]] = []

    for path in sorted(raw_dir.glob("*.csv")):
        with path.open(encoding="utf-8-sig") as fh:
            raw_rows = list(csv.DictReader(fh))
        if not raw_rows:
            stats_files.append((path.name, 0, 0, 0))
            continue

        source = source_of(path, raw_rows[0])
        if source == "kazsandra" and not include_kazsandra:
            print(f"  {path.name}: пропущен ({len(raw_rows)} строк) — "
                  f"отзывы о товарах без категорий, см. --include-kazsandra")
            continue

        kept = dupes = unlabeled = 0
        for row in raw_rows:
            text = _WS.sub(" ", (row.get("text") or "")).strip()
            if len(text) < 25:          # обрывки и мусорные строки
                continue

            key = normalize_for_dedup(text)
            if key in seen:
                dupes += 1
                continue

            labeled = label_row(row, source)
            if labeled is None:
                unlabeled += 1
                continue

            (category, subcategory), origin = labeled
            seen[key] = source
            kept += 1
            rows.append(
                {
                    "id": row.get("id") or f"{source}-{kept}",
                    "text": text,
                    "label": f"{category}/{subcategory}",
                    "category": category,
                    "subcategory": subcategory,
                    "language": row.get("language") or detect_language(text),
                    "source": source,
                    "date": row.get("date") or "",
                    "label_origin": origin,
                }
            )
        stats_files.append((path.name, len(raw_rows), kept, dupes))
        print(f"  {path.name}: {len(raw_rows)} строк -> взято {kept}, "
              f"дублей {dupes}, без метки {unlabeled}")

    return rows


def stratified_split(
    rows: list[dict], seed: int, real_eval: bool
) -> dict[str, list[dict]]:
    """Разбить 70/15/15 со стратификацией по метке.

    real_eval=True: синтетика (huggingface) целиком уходит в train, а val и
    test набираются только из реальных источников — иначе точность окажется
    завышенной, ведь модель будет проверяться на данных того же генератора.
    """
    rng = random.Random(seed)
    splits: dict[str, list[dict]] = {"train": [], "val": [], "test": []}

    by_label: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_label[row["label"]].append(row)

    for label, group in sorted(by_label.items()):
        if real_eval:
            synthetic = [r for r in group if r["source"] == "huggingface"]
            real = [r for r in group if r["source"] != "huggingface"]
            splits["train"].extend(synthetic)
            group = real

        rng.shuffle(group)
        n = len(group)
        n_test = max(1, round(n * 0.15)) if n >= 3 else 0
        n_val = max(1, round(n * 0.15)) if n >= 3 else 0
        splits["test"].extend(group[:n_test])
        splits["val"].extend(group[n_test:n_test + n_val])
        splits["train"].extend(group[n_test + n_val:])

    for part in splits.values():
        rng.shuffle(part)
    return splits


def save(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def report(rows: list[dict], splits: dict[str, list[dict]], real_eval: bool) -> None:
    line = "=" * 70
    print(f"\n{line}\nИТОГОВЫЙ НАБОР\n{line}")
    print(f"всего примеров: {len(rows)}")

    print(f"\n{line}\nПО КЛАССАМ\n{line}")
    counts = Counter(r["label"] for r in rows)
    width = max(len(k) for k in counts)
    for label, n in counts.most_common():
        share = n / len(rows) * 100
        print(f"  {label:<{width}}  {n:>5}  ({share:4.1f}%)")

    print(f"\n{line}\nПО ИСТОЧНИКАМ\n{line}")
    for src, n in Counter(r["source"] for r in rows).most_common():
        print(f"  {src:<14} {n:>5}  ({n / len(rows) * 100:4.1f}%)")

    print(f"\n{line}\nПО ЯЗЫКУ\n{line}")
    for lang, n in Counter(r["language"] for r in rows).most_common():
        print(f"  {lang:<14} {n:>5}  ({n / len(rows) * 100:4.1f}%)")

    print(f"\n{line}\nПО СПОСОБУ РАЗМЕТКИ\n{line}")
    for origin, n in Counter(r["label_origin"] for r in rows).most_common():
        print(f"  {origin:<14} {n:>5}")

    print(f"\n{line}\nРАЗБИЕНИЕ\n{line}")
    for name in ("train", "val", "test"):
        part = splits[name]
        share = len(part) / len(rows) * 100 if rows else 0
        synth = sum(1 for r in part if r["source"] == "huggingface")
        note = f", синтетики {synth}" if synth else ""
        print(f"  {name:<6} {len(part):>5}  ({share:4.1f}%){note}")

    # Предупреждения
    warnings: list[str] = []
    for label, n in counts.items():
        if n < 30:
            warnings.append(f"класс «{label}» — всего {n} примеров (для SetFit желательно 30+)")
    test_synth = sum(1 for r in splits["test"] if r["source"] == "huggingface")
    if test_synth:
        warnings.append(
            f"в тестовой выборке {test_synth} синтетических примеров — "
            f"замеренная точность будет завышена, запустите с --real-eval"
        )
    for name in ("val", "test"):
        thin = [lab for lab, n in Counter(r["label"] for r in splits[name]).items() if n < 5]
        if thin:
            warnings.append(f"в {name} меньше 5 примеров у классов: {', '.join(thin)}")

    if warnings:
        print(f"\n{line}\nПРЕДУПРЕЖДЕНИЯ\n{line}")
        for w in warnings:
            print(f"  ! {w}")
    else:
        print(f"\n{line}\nПредупреждений нет.\n{line}")

    if real_eval:
        print("\nРежим --real-eval: синтетика целиком в train, "
              "val и test только из реальных обращений.")


def main() -> int:
    _force_utf8_stdout()
    parser = argparse.ArgumentParser(description="Сборка обучающего набора")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--real-eval", action="store_true",
        help="синтетику только в train; val/test из реальных источников",
    )
    parser.add_argument(
        "--include-kazsandra", action="store_true",
        help="включить отзывы KazSAnDRA (по умолчанию исключены)",
    )
    args = parser.parse_args()

    print("Читаю data/raw/ …")
    rows = load_all(args.raw_dir, args.include_kazsandra)
    if not rows:
        print("Ничего не собрано.", file=sys.stderr)
        return 1

    splits = stratified_split(rows, args.seed, args.real_eval)

    save(rows, args.out_dir / "dataset_all.csv")
    for name, part in splits.items():
        save(part, args.out_dir / f"{name}.csv")

    report(rows, splits, args.real_eval)
    print(f"\nФайлы в {args.out_dir}:")
    print("  dataset_all.csv, train.csv, val.csv, test.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
