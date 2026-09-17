"""Роут поиска похожих обращений."""
from fastapi import APIRouter, HTTPException

from models import SimilarTicket
from services.embeddings import find_similar
from store import all_tickets, get_ticket

router = APIRouter(prefix="/api/tickets", tags=["similar"])


@router.get("/{ticket_id}/similar", response_model=list[SimilarTicket])
def similar(ticket_id: int):
    t = get_ticket(ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Обращение не найдено")
    return find_similar(t, all_tickets(), top_k=3)
