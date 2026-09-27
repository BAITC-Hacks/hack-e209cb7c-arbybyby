"""In-memory хранилище обращений (MVP — без базы данных).

В проде заменяется на PostgreSQL + pgvector. Здесь — простой список dict,
инициализируемый seed-данными при импорте.
"""
from data.seed import get_seed_data

# Список тикетов как dict (чтобы легко мутировать поля при классификации/подтверждении).
TICKETS: list[dict] = get_seed_data()


# TODO: corrections dataset used for model retraining (feedback loop)
# Каждая правка оператора — размеченный пример «модель ошиблась вот так».
# В проде уезжает в отдельную таблицу и периодически вливается в обучающую выборку.
CORRECTIONS: list[dict] = []


def add_correction(entry: dict) -> None:
    CORRECTIONS.append(entry)


def all_corrections() -> list[dict]:
    return CORRECTIONS


def all_tickets() -> list[dict]:
    return TICKETS


def get_ticket(ticket_id: int) -> dict | None:
    return next((t for t in TICKETS if t["id"] == ticket_id), None)
