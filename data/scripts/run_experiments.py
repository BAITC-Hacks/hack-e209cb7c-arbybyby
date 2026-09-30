#!/usr/bin/env python3
"""Последовательный перебор энкодеров для SetFit.

Зачем
-----
Главный вопрос к качеству — не число итераций, а выбор базовой модели.
paraphrase-multilingual-MiniLM-L12-v2 обучалась на 50 языках, и казахского
среди них НЕТ, а у нас 38% корпуса на казахском. Поэтому сравниваем с
моделями, которые казахский знают.

Кандидаты
---------
    paraphrase-multilingual-MiniLM-L12-v2  118M  50 языков, без казахского
    intfloat/multilingual-e5-small         118M  100 языков, казахский есть
    sentence-transformers/LaBSE            471M  109 языков, казахский есть

Запуски идут СТРОГО по очереди: два обучения одновременно отнимают ядра друг
у друга и идут втрое медленнее, чем по отдельности (проверено на практике —
30 с/шаг против 6.8 с/шаг).

Каждый прогон кладёт модель и метрики в свою папку, так что результаты можно
сравнить, а не затереть.

Запуск
------
    python data/scripts/run_experiments.py                 # весь список
    python data/scripts/run_experiments.py --only e5-small
    python data/scripts/run_experiments.py --iterations 20 # финальный прогон
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAIN_SCRIPT = PROJECT_ROOT / "data" / "scripts" / "train_setfit.py"
MODELS_DIR = PROJECT_ROOT / "data" / "models"
RESULTS_DIR = PROJECT_ROOT / "data" / "results"

# (короткое имя, идентификатор на HuggingFace, примечание)
EXPERIMENTS = [
    (
        "e5-small",
        "intfloat/multilingual-e5-small",
        "100 языков, казахский есть; размер как у текущей модели",
    ),
    (
        "labse",
        "sentence-transformers/LaBSE",
        "109 языков, казахский есть; 471M — считается дольше",
    ),
]


def _force_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def run_one(name: str, model_id: str, iterations: int, max_seq: int) -> dict | None:
    """Запустить одно обучение и вернуть его метрики."""
    out_model = MODELS_DIR / f"setfit-{name}"
    out_results = RESULTS_DIR / name

    print(f"\n{'=' * 70}")
    print(f"ЭКСПЕРИМЕНТ: {name}")
    print(f"модель: {model_id}")
    print(f"{'=' * 70}", flush=True)

    started = time.time()
    proc = subprocess.run(
        [
            sys.executable, "-u", str(TRAIN_SCRIPT),
            "--model", model_id,
            "--num-iterations", str(iterations),
            "--max-seq-length", str(max_seq),
            "--out-model", str(out_model),
            "--results-dir", str(out_results),
        ],
        cwd=str(PROJECT_ROOT),
    )
    elapsed = time.time() - started

    if proc.returncode != 0:
        print(f"  {name}: упал с кодом {proc.returncode}", flush=True)
        return None

    metrics_path = out_results / "metrics.json"
    if not metrics_path.exists():
        print(f"  {name}: метрики не найдены", flush=True)
        return None

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    print(f"  {name}: готово за {elapsed / 60:.0f} мин", flush=True)
    return metrics


def summarize(results: dict[str, dict]) -> None:
    line = "=" * 78
    print(f"\n{line}\nСРАВНЕНИЕ МОДЕЛЕЙ\n{line}")
    header = f"{'модель':<12} {'accuracy':>9} {'F1 weighted':>12} {'F1 (ru)':>9} {'F1 (kk)':>9} {'время':>8}"
    print(header)
    print("-" * len(header))

    for name, metrics in results.items():
        test = metrics["test"]
        by_lang = test.get("by_language", {})
        ru = by_lang.get("ru", {}).get("f1_weighted", 0)
        kk = by_lang.get("kk", {}).get("f1_weighted", 0)
        mins = metrics.get("train_seconds", 0) / 60
        print(
            f"{name:<12} {test['accuracy']:>9.3f} {test['f1_weighted']:>12.3f} "
            f"{ru:>9.3f} {kk:>9.3f} {mins:>7.0f}м"
        )

    if results:
        best = max(results.items(), key=lambda kv: kv[1]["test"]["f1_weighted"])
        print(f"\nЛучший по F1 weighted: {best[0]} ({best[1]['test']['f1_weighted']:.3f})")
        print("Смотрите также колонку F1 (kk) — казахский половина корпуса.")


def main() -> int:
    _force_utf8_stdout()
    parser = argparse.ArgumentParser(description="Перебор энкодеров для SetFit")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--max-seq-length", type=int, default=96)
    parser.add_argument(
        "--only", nargs="+", default=None,
        help="запустить только указанные эксперименты по короткому имени",
    )
    args = parser.parse_args()

    planned = [
        e for e in EXPERIMENTS
        if args.only is None or e[0] in args.only
    ]
    if not planned:
        print("Нечего запускать: проверьте --only", file=sys.stderr)
        return 1

    print(f"Запланировано экспериментов: {len(planned)}")
    for name, model_id, note in planned:
        print(f"  {name:<12} {model_id}")
        print(f"  {'':<12} {note}")

    results: dict[str, dict] = {}
    for name, model_id, _note in planned:
        metrics = run_one(name, model_id, args.iterations, args.max_seq_length)
        if metrics:
            results[name] = metrics

    # Подтягиваем baseline текущей модели, если он уже посчитан
    baseline_path = RESULTS_DIR / "metrics.json"
    if baseline_path.exists():
        try:
            results["minilm (base)"] = json.loads(
                baseline_path.read_text(encoding="utf-8")
            )
        except Exception:
            pass

    summarize(results)
    (RESULTS_DIR / "comparison.json").write_text(
        json.dumps(
            {name: m["test"] for name, m in results.items()},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nСводка: {RESULTS_DIR / 'comparison.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
