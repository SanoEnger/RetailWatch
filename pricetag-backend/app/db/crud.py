import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recognition import Recognition


async def create_recognition(
    db: AsyncSession,
    image_data: bytes,
    raw_text: Optional[str],
    extracted_price: Optional[float],
    confidence: Optional[float],
) -> Recognition:
    obj = Recognition(
        image_data=image_data,
        raw_text=raw_text,
        extracted_price=extracted_price,
        confidence=confidence,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_recognition(
    db: AsyncSession, recognition_id: uuid.UUID
) -> Optional[Recognition]:
    result = await db.execute(
        select(Recognition).where(Recognition.id == recognition_id)
    )
    return result.scalar_one_or_none()


async def get_history(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,  # "ok" | "error" | "pending" | None
) -> tuple[list[Recognition], int]:
    query = select(Recognition).order_by(Recognition.created_at.desc())

    if status == "ok":
        query = query.where(Recognition.is_valid == True)
    elif status == "error":
        query = query.where(Recognition.is_valid == False)
    elif status == "pending":
        query = query.where(Recognition.is_valid == None)

    # Считаем total до применения limit/offset
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    result = await db.execute(query.limit(limit).offset(offset))
    items = list(result.scalars().all())

    return items, total


async def update_feedback(
    db: AsyncSession,
    recognition_id: uuid.UUID,
    is_valid: bool,
    correct_price: Optional[float],
) -> Optional[Recognition]:
    obj = await get_recognition(db, recognition_id)
    if not obj:
        return None

    obj.is_valid = is_valid
    obj.correct_price = correct_price
    await db.commit()
    await db.refresh(obj)
    return obj
