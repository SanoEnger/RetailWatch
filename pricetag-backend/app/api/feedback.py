import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.database import get_db
from app.models.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter()


@router.post(
    "/feedback/{recognition_id}",
    response_model=FeedbackResponse,
    summary="Отметить результат распознавания как верный/ошибочный",
)
async def submit_feedback(
    recognition_id: uuid.UUID,
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    obj = await crud.update_feedback(
        db=db,
        recognition_id=recognition_id,
        is_valid=body.is_valid,
        correct_price=body.correct_price,
    )

    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Запись {recognition_id} не найдена",
        )

    return FeedbackResponse(
        id=obj.id,
        is_valid=obj.is_valid,
        correct_price=float(obj.correct_price) if obj.correct_price else None,
        message="Спасибо! Обратная связь сохранена.",
    )
