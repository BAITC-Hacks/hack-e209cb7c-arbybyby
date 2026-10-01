#!/usr/bin/env python3
"""Выгрузка датасетов, метрик и весов модели в S3-хранилище хакатона.

Зачем
-----
Данные и обученная модель не должны жить только на ноутбуке: S3 — это и бэкап,
и способ переносить артефакты между машиной разработки и сервером, не гоняя
их через git.

Что уезжает
-----------
    datasets/   — собранные CSV из data/raw и data/processed
    results/    — метрики и матрицы ошибок обученных моделей
    models/     — веса SetFit (по запросу, это сотни мегабайт)

Доступы берутся из .env рядом с корнем проекта и НЕ попадают в git.

Запуск
------
    python data/scripts/s3_sync.py --what datasets results
    python data/scripts/s3_sync.py --what models        # долго, ~460 МБ
    python data/scripts/s3_sync.py --list               # что уже лежит
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

# Что откуда и под каким префиксом лежит в бакете.
TARGETS = {
    "datasets": [
        (PROJECT_ROOT / "data" / "raw", "datasets/raw"),
        (PROJECT_ROOT / "data" / "processed", "datasets/processed"),
    ],
    "results": [
        (PROJECT_ROOT / "data" / "results", "results"),
    ],
    "models": [
        (PROJECT_ROOT / "data" / "models", "models"),
    ],
}

SKIP_SUFFIXES = {".pyc", ".bak"}


def _force_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def load_env() -> dict[str, str]:
    """Прочитать .env. Ключи не хардкодим — файл лежит вне git."""
    if not ENV_FILE.exists():
        print(f"Нет файла {ENV_FILE}. Создайте его с ключами S3.", file=sys.stderr)
        raise SystemExit(1)

    env: dict[str, str] = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def make_client(env: dict[str, str]):
    import boto3
    from botocore.config import Config

    # Свежие botocore по умолчанию считают контрольные суммы и шлют тело
    # chunked-кодированием. Этот S3-провайдер такое не принимает и отвечает
    # MissingContentLength, поэтому обе новые фичи отключаем.
    config_kwargs = {"s3": {"addressing_style": "path"}}
    for name in ("request_checksum_calculation", "response_checksum_validation"):
        try:
            Config(**{name: "when_required"})
        except TypeError:
            continue  # старый botocore, параметра нет
        config_kwargs[name] = "when_required"

    return boto3.client(
        "s3",
        endpoint_url=env["S3_ENDPOINT"],
        aws_access_key_id=env["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=env["AWS_SECRET_ACCESS_KEY"],
        region_name=env.get("AWS_DEFAULT_REGION", "us-east-1"),
        config=Config(**config_kwargs),
    )


def iter_files(root: Path):
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix not in SKIP_SUFFIXES:
            yield path


def upload(client, bucket: str, what: list[str]) -> int:
    total_files = 0
    total_bytes = 0

    for group in what:
        for local_root, prefix in TARGETS[group]:
            for path in iter_files(local_root):
                key = f"{prefix}/{path.relative_to(local_root).as_posix()}"
                size = path.stat().st_size
                # put_object с явным ContentLength вместо upload_file:
                # так тело уходит обычным запросом, без chunked-кодирования.
                with path.open("rb") as fh:
                    client.put_object(
                        Bucket=bucket, Key=key, Body=fh, ContentLength=size
                    )
                total_files += 1
                total_bytes += size
                print(f"  ↑ {key}  ({size / 1024:.0f} КБ)")

    print(f"\nзагружено файлов: {total_files}, объём: {total_bytes / 1024 / 1024:.1f} МБ")
    return total_files


def listing(client, bucket: str) -> None:
    paginator = client.get_paginator("list_objects_v2")
    total = 0
    size = 0
    by_prefix: dict[str, list[int]] = {}

    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            total += 1
            size += obj["Size"]
            top = obj["Key"].split("/")[0]
            stats = by_prefix.setdefault(top, [0, 0])
            stats[0] += 1
            stats[1] += obj["Size"]

    if not total:
        print("бакет пуст")
        return

    print(f"{'префикс':<14}{'файлов':>8}{'объём':>12}")
    print("-" * 34)
    for prefix, (count, bytes_) in sorted(by_prefix.items()):
        print(f"{prefix:<14}{count:>8}{bytes_ / 1024 / 1024:>10.1f} МБ")
    print("-" * 34)
    print(f"{'всего':<14}{total:>8}{size / 1024 / 1024:>10.1f} МБ")


def main() -> int:
    _force_utf8_stdout()
    parser = argparse.ArgumentParser(description="Синхронизация артефактов с S3")
    parser.add_argument(
        "--what", nargs="+", choices=list(TARGETS), default=["datasets", "results"],
    )
    parser.add_argument("--list", action="store_true", help="только показать содержимое")
    args = parser.parse_args()

    env = load_env()
    bucket = env["S3_BUCKET"]
    client = make_client(env)

    if args.list:
        listing(client, bucket)
        return 0

    print(f"Бакет: {bucket}\nЗагружаю: {', '.join(args.what)}\n")
    upload(client, bucket, args.what)
    print()
    listing(client, bucket)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
