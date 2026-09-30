"""Pydantic schemas for AURA — Pulse 109 platform."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

Source = Literal["iKOMEK", "E-SEP", "телефон", "AIKEY"]
Status = Literal["new", "processing", "resolved"]
Priority = Literal["high", "medium", "low"]


class Ticket(BaseModel):
    id: int
    text: str
    source: Source
    region: str
    created_at: datetime
    status: Status = "new"
    priority: Priority = "medium"
    category: Optional[str] = None
    subcategory: Optional[str] = None
    address: Optional[str] = None
    responsible_service: Optional[str] = None
    confidence_score: Optional[int] = None
    reasoning: Optional[str] = None
    needs_review: bool = False
    alternatives: list["CategoryOption"] = []
    # Гражданин идентифицируется только номером — ФИО в систему не попадают.
    citizen_label: Optional[str] = None


class CategoryOption(BaseModel):
    """Вариант категории, предлагаемый оператору при низкой уверенности."""
    category: str
    subcategory: str
    responsible_service: str
    confidence: int


class ClassifyResponse(BaseModel):
    category: str
    subcategory: str
    address: Optional[str] = None
    priority: Priority
    responsible_service: str
    confidence_score: int
    reasoning: str
    # Классификатор не уверен: сработал один маркер либо текст слишком короткий.
    # Оператор выбирает категорию сам из alternatives.
    needs_review: bool = False
    alternatives: list[CategoryOption] = []


class AskRequest(BaseModel):
    """Вопрос к данным на естественном языке."""
    question: str


class CorrectionRequest(BaseModel):
    """Ручная правка категории оператором — сырьё для дообучения модели."""
    original_category: Optional[str] = None
    corrected_category: str


class SimilarTicket(BaseModel):
    id: int
    text: str
    category: str
    similarity_score: int


class RegionStats(BaseModel):
    region: str
    total: int
    top_category: str
    trend_percent: float


class Spike(BaseModel):
    region: str
    description: str
    percent_increase: int
    category: str
    time_window: str


class AnalyticsSummary(BaseModel):
    total_tickets: int
    avg_processing_time: float
    resolved_percent: int
    critical_count: int


# CategoryOption объявлен ниже Ticket, поэтому ссылку в Ticket разрешаем явно.
Ticket.model_rebuild()
