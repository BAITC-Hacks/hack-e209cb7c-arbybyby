"""In-memory хранилище обращений (MVP — без базы данных).

В проде заменяется на PostgreSQL + pgvector. Здесь — простой список dict,
инициализируемый seed-данными при импорте.
"""
from data.seed import get_seed_data

# Список тикетов как dict (чтобы легко мутировать поля при классификации/подтверждении).
TICKETS: list[dict] = get_seed_data()


def all_tickets() -> list[dict]:
    return TICKETS


def get_ticket(ticket_id: int) -> dict | None:
    return next((t for t in TICKETS if t["id"] == ticket_id), None)
