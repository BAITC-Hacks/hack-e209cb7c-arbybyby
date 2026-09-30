"""Роуты обращений: список, детали, классификация, подтверждение."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from models import ClassifyResponse, CorrectionRequest, Ticket
from services.classifier import classify_ticket
from store import add_correction, all_corrections, all_tickets, get_ticket

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

# Значения по умолчанию при ручной смене категории. Без них правка «ЖКХ ->
# Освещение» оставляла подкатегорию «Водоснабжение» и службу «Горводоканал» —
# бессмысленное сочетание, которое видно оператору.
_CATEGORY_DEFAULTS: dict[str, tuple[str, str]] = {
    "ЖКХ": ("Общие вопросы", "КСК"),
    "Дороги": ("Дорожное покрытие", "УДС"),
    "Освещение": ("Уличное освещение", "Горсвет"),
    "Транспорт": ("Общественный транспорт", "Управление транспорта"),
    "Благоустройство": ("Вывоз мусора", "УГХ"),
    "Другое": ("Общие вопросы", "Акимат района"),
}


def _public(t: dict) -> dict:
    """Убрать служебные поля (например _gold) перед отдачей клиенту."""
    return {k: v for k, v in t.items() if not k.startswith("_")}


def _effective_category(t: dict) -> Optional[str]:
    """Категория обращения для фильтрации.

    У необработанных обращений поле category пустое — оно заполняется только
    после классификации. Если фильтровать строго по нему, выбор «ЖКХ» покажет
    лишь те обращения, которые оператор уже открывал, а очередь входящих
    окажется пустой. Поэтому подставляем эталонную категорию (_gold) —
    в проде её роль играет предварительная классификация на приёме.
    """
    return t.get("category") or (t.get("_gold") or {}).get("category")


@router.get("", response_model=list[Ticket])
def list_tickets(
    region: Optional[str] = Query(None, description="Регион, например «Астана»"),
    status: Optional[str] = Query(None, description="new | processing | resolved"),
    category: Optional[str] = Query(None, description="Категория, например «ЖКХ»"),
    priority: Optional[str] = Query(None, description="high | medium | low"),
    q: Optional[str] = Query(None, description="Поиск по тексту обращения"),
):
    items = all_tickets()
    if region:
        items = [t for t in items if t["region"] == region]
    if status:
        items = [t for t in items if t["status"] == status]
    if category:
        items = [t for t in items if _effective_category(t) == category]
    if priority:
        items = [t for t in items if t["priority"] == priority]
    if q:
        needle = q.strip().casefold()
        if needle:
            # Поиск по тексту обращения и по адресу — оператор ищет и «труба», и «Кенесары».
            items = [
                t
                for t in items
                if needle in t["text"].casefold()
                or needle in (t.get("address") or "").casefold()
            ]
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
    t["needs_review"] = result.needs_review
    t["alternatives"] = [a.model_dump() for a in result.alternatives]
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


@router.post("/{ticket_id}/correct", response_model=Ticket)
def correct(ticket_id: int, payload: CorrectionRequest):
    """Оператор вручную исправил категорию.

    Правка применяется к обращению и складывается в список коррекций.
    # TODO: corrections dataset used for model retraining (feedback loop)
    """
    t = get_ticket(ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Обращение не найдено")

    original = payload.original_category or t.get("category")
    t["category"] = payload.corrected_category

    # Категория сменилась — подкатегория и служба от прежней больше не подходят
    if payload.corrected_category != original:
        default = _CATEGORY_DEFAULTS.get(payload.corrected_category)
        if default:
            t["subcategory"], t["responsible_service"] = default
    # Правка оператора — источник истины, поэтому уверенность больше не показываем
    # как машинную: обращение классифицировано человеком.
    t["confidence_score"] = 100
    t["needs_review"] = False
    t["alternatives"] = []
    t["reasoning"] = f"Категория установлена оператором (было: {original or '—'})."

    add_correction(
        {
            "ticket_id": ticket_id,
            "original_category": original,
            "corrected_category": payload.corrected_category,
            "corrected_at": datetime.now(timezone.utc).isoformat(),
            "text": t["text"],
        }
    )
    return _public(t)


@router.get("/corrections/all")
def corrections():
    """Накопленные правки операторов — витрина будущей обучающей выборки."""
    return {"total": len(all_corrections()), "items": all_corrections()}
