"""Роуты обращений: список, детали, классификация, подтверждение."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from models import ClassifyResponse, Ticket
from services.classifier import classify_ticket
from store import all_tickets, get_ticket

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def _public(t: dict) -> dict:
    """Убрать служебные поля (например _gold) перед отдачей клиенту."""
    return {k: v for k, v in t.items() if not k.startswith("_")}


@router.get("", response_model=list[Ticket])
def list_tickets(
    region: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    items = all_tickets()
    if region:
        items = [t for t in items if t["region"] == region]
    if status:
        items = [t for t in items if t["status"] == status]
    # свежие сверху
    items = sorted(items, key=lambda t: t["created_at"], reverse=True)
    return [_public(t) for t in items]


@router.get("/{ticket_id}", response_model=Ticket)
def get_one(ticket_id: int):
    t = get_ticket(ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Обращение не найдено")
    return _public(t)


@router.post("/{ticket_id}/classify", response_model=ClassifyResponse)
def classify(ticket_id: int):
    t = get_ticket(ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Обращение не найдено")

    result = classify_ticket(t["text"], address_hint=t.get("address"))

    # записываем результат классификации обратно в тикет и переводим в "в работе"
    t["category"] = result.category
    t["subcategory"] = result.subcategory
    t["address"] = result.address or t.get("address")
    t["priority"] = result.priority
    t["responsible_service"] = result.responsible_service
    t["confidence_score"] = result.confidence_score
    t["reasoning"] = result.reasoning
    if t["status"] == "new":
        t["status"] = "processing"

    return result


@router.post("/{ticket_id}/approve", response_model=Ticket)
def approve(ticket_id: int):
    t = get_ticket(ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Обращение не найдено")
    t["status"] = "resolved"
    t["_resolved_at"] = datetime.now(timezone.utc)
    return _public(t)
