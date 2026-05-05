import base64
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.database import get_db
from app.models.schemas import HistoryDetailItem, HistoryItem, HistoryResponse

router = APIRouter()

StatusFilter = Literal["all", "ok", "error", "pending"]


@router.get(
    "/history",
    response_model=HistoryResponse,
    summary="История распознаваний",
)
async def get_history(
    limit: int = Query(default=20, ge=1, le=100, description="Кол-во записей"),
    offset: int = Query(default=0, ge=0, description="Смещение"),
    status: StatusFilter = Query(default="all", description="Фильтр по статусу"),
    db: AsyncSession = Depends(get_db),
):
    status_filter = None if status == "all" else status
    items, total = await crud.get_history(db, limit=limit, offset=offset, status=status_filter)

    return HistoryResponse(
        items=[HistoryItem.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/history/{recognition_id}",
    response_model=HistoryDetailItem,
    summary="Детальная карточка распознавания (с изображением в base64)",
)
async def get_recognition_detail(
    recognition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    obj = await crud.get_recognition(db, recognition_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Запись {recognition_id} не найдена",
        )

    item = HistoryDetailItem.model_validate(obj)
    if obj.image_data:
        item.image_base64 = base64.b64encode(obj.image_data).decode("utf-8")

    return item
