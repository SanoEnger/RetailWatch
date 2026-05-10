import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RecognizeResponse(BaseModel):
    request_id: uuid.UUID
    price: Optional[float]
    raw_text: Optional[str]
    confidence: Optional[float]
    timestamp: datetime
    detected: bool = True
    engine: Optional[str] = None
    message: Optional[str] = None

    model_config = {"from_attributes": True}


class RecognizeErrorResponse(BaseModel):
    error: str


class RecognitionStatus(str):
    OK = "ok"
    ERROR = "error"
    PENDING = "pending"


class HistoryItem(BaseModel):
    id: uuid.UUID
    extracted_price: Optional[float]
    raw_text: Optional[str]
    confidence: Optional[float]
    is_valid: Optional[bool]
    created_at: datetime

    @property
    def status(self) -> str:
        if self.is_valid is None:
            return "pending"
        return "ok" if self.is_valid else "error"

    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    items: list[HistoryItem]
    total: int
    limit: int
    offset: int


class HistoryDetailItem(HistoryItem):
    image_base64: Optional[str] = None


class FeedbackRequest(BaseModel):
    is_valid: bool = Field(
        ...,
        description="True — распознано верно, False — ошибка",
    )
    correct_price: Optional[float] = Field(
        None,
        description="Верная цена, если is_valid=False",
    )


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    is_valid: bool
    correct_price: Optional[float]
    message: str
