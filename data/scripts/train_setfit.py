#!/usr/bin/env python3
"""Обучение SetFit-классификатора обращений граждан.

Что делает
----------
    1. Читает data/processed/{train,val,test}.csv (готовятся prepare_dataset.py
       с флагом --real-eval, чтобы val/test были только из реальных обращений).
    2. Сводит подкатегории к 10 целевым классам.
    3. Ограничивает класс «Другое» в train, чтобы он не доминировал.
    4. Дообучает SetFit на CPU.
    5. Считает метрики на val и test, включая разбивку ПО ЯЗЫКАМ.
    6. Сохраняет модель, маппинг меток, metrics.json и confusion_matrix.png.

Про API
-------
В setfit 1.x класс SetFitTrainer объявлен устаревшим: параметры обучения
переехали в TrainingArguments, а тренер называется Trainer. Скрипт написан
под актуальный API, набор параметров тот же (num_iterations, batch_size,
num_epochs, loss).

Про модель и казахский язык
---------------------------
По умолчанию берётся paraphrase-multilingual-MiniLM-L12-v2, как самая лёгкая.
Она обучалась на 50 языках, и КАЗАХСКОГО СРЕДИ НИХ НЕТ — токенизатор XLM-R
кириллицу переварит, но качество на казахском ожидаемо ниже русского.
Поэтому метрики считаются отдельно по ru и kk. Если разрыв большой, пробуйте:

    --model sentence-transformers/LaBSE

LaBSE покрывает 109 языков, включая казахский, но весит ~1.8 ГБ против ~470 МБ.

Запуск
------
    python data/scripts/train_setfit.py
    python data/scripts/train_setfit.py --model sentence-transformers/LaBSE
    python data/scripts/train_setfit.py --num-iterations 5   # быстрая проверка
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "data" / "models"
RESULTS_DIR = PROJECT_ROOT / "data" / "results"

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Подкатегории из prepare_dataset.py -> 10 целевых классов.
# «Детские площадки» вливаются в «Благоустройство»: примеров мало (39),
# а семантически это тот же городской двор.
LABEL_MAP: dict[str, str] = {
    "ЖКХ/Водоснабжение": "ЖКХ — Водоснабжение",
    "ЖКХ/Отопление": "ЖКХ — Отопление",
    "ЖКХ/Общие вопросы": "ЖКХ — Общие вопросы",
    "ЖКХ/Лифт": "Лифт",
    "Освещение/Уличное освещение": "Освещение",
    "Дороги/Дорожное покрытие": "Дороги",
    "Дороги/Светофоры": "Дороги — Светофоры",
    "Транспорт/Общественный транспорт": "Транспорт",
    "Благоустройство/Вывоз мусора": "Благоустройство",
    "Благоустройство/Детские площадки": "Благоустройство",
    "Другое/Общие вопросы": "Другое",
}

OTHER_LABEL = "Другое"


def _force_utf8_stdout() -> None:
    """UTF-8 в консоль Windows + отключение буферизации.

    Без line_buffering вывод копится в буфере и при запуске в фоне
    (перенаправление в файл) прогресс не виден до самого конца.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def load_split(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def remap(rows: list[dict]) -> list[dict]:
    """Привести метки к целевым классам, отбросив неизвестные."""
    out = []
    for row in rows:
        target = LABEL_MAP.get(row["label"])
        if target is None:
            continue
        out.append({**row, "target": target})
    return out


def cap_class(rows: list[dict], label: str, limit: int, seed: int) -> list[dict]:
    """Ограничить один класс случайной подвыборкой — остальные не трогаем."""
    chosen = [r for r in rows if r["target"] == label]
    rest = [r for r in rows if r["target"] != label]
    if len(chosen) <= limit:
        return rows
    rng = random.Random(seed)
    rng.shuffle(chosen)
    return rest + chosen[:limit]


def print_distribution(title: str, rows: list[dict]) -> None:
    print(f"\n{title} ({len(rows)})")
    counts = Counter(r["target"] for r in rows)
    width = max((len(k) for k in counts), default=10)
    for label, n in counts.most_common():
        print(f"    {label:<{width}}  {n:>5}")


def evaluate(model, rows: list[dict], label_names: list[str]) -> dict:
    """Метрики на одном сплите: общие, по классам и по языкам."""
    from sklearn.metrics import (
        accuracy_score, f1_score, classification_report, confusion_matrix,
    )

    texts = [r["text"] for r in rows]
    y_true = [r["target"] for r in rows]
    y_pred = [str(p) for p in model.predict(texts)]

    result = {
        "n": len(rows),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "f1_weighted": round(float(f1_score(y_true, y_pred, average="weighted", zero_division=0)), 4),
        "f1_macro": round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "per_class": classification_report(
            y_true, y_pred, labels=label_names, output_dict=True, zero_division=0
        ),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=label_names).tolist(),
        "labels": label_names,
    }

    # Разбивка по языкам: казахский — половина корпуса, и модель может
    # работать на нём заметно хуже. Без этой разбивки провал не виден.
    by_lang = {}
    for lang in sorted({r.get("language", "?") for r in rows}):
        idx = [i for i, r in enumerate(rows) if r.get("language") == lang]
        if not idx:
            continue
        lt = [y_true[i] for i in idx]
        lp = [y_pred[i] for i in idx]
        by_lang[lang] = {
            "n": len(idx),
            "accuracy": round(float(accuracy_score(lt, lp)), 4),
            "f1_weighted": round(float(f1_score(lt, lp, average="weighted", zero_division=0)), 4),
        }
    result["by_language"] = by_lang
    return result


def save_confusion_matrix(matrix, labels: list[str], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")           # без GUI — скрипт может идти в фоне
    import matplotlib.pyplot as plt
    import seaborn as sns

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, 9))
    sns.heatmap(
        matrix, annot=True, fmt="d", cmap="Blues", cbar=False,
        xticklabels=labels, yticklabels=labels, ax=ax,
        linewidths=0.5, linecolor="#E5E7EB",
    )
    ax.set_xlabel("Предсказано", fontsize=11)
    ax.set_ylabel("Истинный класс", fontsize=11)
    ax.set_title("Матрица ошибок — test", fontsize=13, pad=14)
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.yticks(rotation=0, fontsize=9)
    plt.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> int:
    _force_utf8_stdout()
    parser = argparse.ArgumentParser(description="Обучение SetFit-классификатора")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--num-iterations", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--num-epochs", type=int, default=1)
    parser.add_argument("--other-cap", type=int, default=200,
                        help="максимум примеров класса «Другое» в train")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--max-seq-length", type=int, default=96,
        help="обрезка входа в токенах; тексты ~280 символов это ~70 токенов, "
             "дефолтные 128 тратятся на padding",
    )
    parser.add_argument("--out-model", type=Path,
                        default=MODELS_DIR / "setfit-classifier-v1")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()

    from datasets import Dataset
    from sentence_transformers.losses import CosineSimilarityLoss
    from setfit import SetFitModel, Trainer, TrainingArguments
    import torch

    # Число потоков torch НЕ трогаем: дефолт (по числу физических ядер)
    # разумен для гибридных процессоров Intel, где логических потоков вдвое
    # больше физических ядер (здесь i7-13620H: 6P + 4E, 16 потоков).
    # Скорость шага сильно зависит от посторонней нагрузки на машине —
    # наблюдались 6.9 с/шаг на свободной системе против 29 с/шаг при
    # активной работе в IDE и браузере.
    random.seed(args.seed)

    line = "=" * 70
    print(f"{line}\nПОДГОТОВКА ДАННЫХ\n{line}")

    train = remap(load_split(PROCESSED_DIR / "train.csv"))
    val = remap(load_split(PROCESSED_DIR / "val.csv"))
    test = remap(load_split(PROCESSED_DIR / "test.csv"))

    before = sum(1 for r in train if r["target"] == OTHER_LABEL)
    train = cap_class(train, OTHER_LABEL, args.other_cap, args.seed)
    after = sum(1 for r in train if r["target"] == OTHER_LABEL)
    print(f"  класс «{OTHER_LABEL}» в train: {before} -> {after}")

    label_names = sorted({r["target"] for r in train})
    print(f"  классов: {len(label_names)}")
    print_distribution("  train", train)
    print_distribution("  val", val)
    print_distribution("  test", test)

    # SetFit ожидает числовые метки, поэтому держим маппинг явно.
    label2id = {label: i for i, label in enumerate(label_names)}
    id2label = {str(i): label for label, i in label2id.items()}

    train_ds = Dataset.from_dict({
        "text": [r["text"] for r in train],
        "label": [label2id[r["target"]] for r in train],
    })
    val_ds = Dataset.from_dict({
        "text": [r["text"] for r in val],
        "label": [label2id[r["target"]] for r in val],
    })

    print(f"\n{line}\nОБУЧЕНИЕ\n{line}")
    print(f"  модель:         {args.model}")
    print(f"  num_iterations: {args.num_iterations}")
    print(f"  batch_size:     {args.batch_size}")
    print(f"  num_epochs:     {args.num_epochs}")
    print(f"  max_seq_length: {args.max_seq_length}")
    print(f"  устройство:     CPU ({torch.get_num_threads()} потоков)")
    print("  loss:           CosineSimilarityLoss")
    print("\n  Загружаю модель (при первом запуске качается с HuggingFace)…")

    model = SetFitModel.from_pretrained(args.model, labels=label_names)
    # Половина вычислений на дефолтных 128 токенах уходит в padding: наши
    # обращения — около 280 символов, то есть ~70 токенов.
    if getattr(model, "model_body", None) is not None:
        model.model_body.max_seq_length = args.max_seq_length

    train_args = TrainingArguments(
        num_iterations=args.num_iterations,
        batch_size=args.batch_size,
        num_epochs=args.num_epochs,
        loss=CosineSimilarityLoss,
        seed=args.seed,
        report_to="none",
    )
    trainer = Trainer(
        model=model,
        args=train_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
    )

    started = time.time()
    trainer.train()
    train_seconds = time.time() - started
    print(f"\n  обучение заняло: {train_seconds / 60:.1f} мин ({train_seconds:.0f} с)")

    print(f"\n{line}\nОЦЕНКА\n{line}")
    val_metrics = evaluate(model, val, label_names)
    test_metrics = evaluate(model, test, label_names)

    print(f"\n  VAL   accuracy {val_metrics['accuracy']:.3f} | "
          f"F1 weighted {val_metrics['f1_weighted']:.3f}")
    print(f"  TEST  accuracy {test_metrics['accuracy']:.3f} | "
          f"F1 weighted {test_metrics['f1_weighted']:.3f} | "
          f"F1 macro {test_metrics['f1_macro']:.3f}")

    print("\n  По языкам (test):")
    for lang, m in test_metrics["by_language"].items():
        print(f"    {lang}  n={m['n']:<5} accuracy {m['accuracy']:.3f} | "
              f"F1 {m['f1_weighted']:.3f}")

    print("\n  По классам (test):")
    print(f"    {'класс':<24} {'precision':>9} {'recall':>8} {'f1':>7} {'n':>5}")
    for label in label_names:
        row = test_metrics["per_class"].get(label, {})
        print(f"    {label:<24} {row.get('precision', 0):>9.3f} "
              f"{row.get('recall', 0):>8.3f} {row.get('f1-score', 0):>7.3f} "
              f"{int(row.get('support', 0)):>5}")

    # ---- сохранение ----
    args.out_model.parent.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(args.out_model))

    mapping_path = MODELS_DIR / "label_mapping.json"
    mapping_path.write_text(
        json.dumps(
            {"id2label": id2label, "label2id": label2id, "labels": label_names},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )

    args.results_dir.mkdir(parents=True, exist_ok=True)
    save_confusion_matrix(
        test_metrics["confusion_matrix"], label_names,
        args.results_dir / "confusion_matrix.png",
    )

    metrics = {
        "model": args.model,
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "train_seconds": round(train_seconds, 1),
        "hyperparameters": {
            "num_iterations": args.num_iterations,
            "batch_size": args.batch_size,
            "num_epochs": args.num_epochs,
            "loss": "CosineSimilarityLoss",
            "seed": args.seed,
            "other_cap": args.other_cap,
            "max_seq_length": args.max_seq_length,
        },
        "dataset": {
            "train": len(train), "val": len(val), "test": len(test),
            "labels": label_names,
            "train_distribution": dict(Counter(r["target"] for r in train)),
        },
        "val": val_metrics,
        "test": test_metrics,
    }
    (args.results_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n{line}\nСОХРАНЕНО\n{line}")
    print(f"  модель:   {args.out_model}")
    print(f"  маппинг:  {mapping_path}")
    print(f"  метрики:  {args.results_dir / 'metrics.json'}")
    print(f"  матрица:  {args.results_dir / 'confusion_matrix.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
