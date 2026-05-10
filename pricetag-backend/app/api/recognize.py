import logging
from datetime import timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import crud
from app.db.database import get_db
from app.models.schemas import RecognizeErrorResponse, RecognizeResponse
from app.services.ml_service import ocr_processor

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post(
    "/recognize",
    response_model=RecognizeResponse,
    responses={400: {"model": RecognizeErrorResponse}},
    summary="Распознать цену на изображении",
)
async def recognize_price(
    file: UploadFile = File(..., description="Изображение ценника (JPEG/PNG/WEBP)"),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Неподдерживаемый тип файла: {file.content_type}. "
                f"Разрешены: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
            ),
        )

    contents = await file.read()

    if len(contents) > settings.MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Файл слишком большой. Максимум: {settings.MAX_IMAGE_SIZE_MB} МБ",
        )

    try:
        ml_result = await ocr_processor.process(contents)
    except Exception:
        logger.exception("Ошибка OCR-пайплайна")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка обработки изображения",
        )

    recognition = await crud.create_recognition(
        db=db,
        image_data=contents,
        raw_text=ml_result.raw_text,
        extracted_price=ml_result.price,
        confidence=ml_result.confidence,
    )

    return RecognizeResponse(
        request_id=recognition.id,
        price=float(recognition.extracted_price)
        if recognition.extracted_price is not None
        else None,
        raw_text=recognition.raw_text,
        confidence=float(recognition.confidence)
        if recognition.confidence is not None
        else None,
        timestamp=recognition.created_at.replace(tzinfo=timezone.utc)
        if recognition.created_at.tzinfo is None
        else recognition.created_at,
        detected=ml_result.price is not None,
        engine=ml_result.engine,
        message=ml_result.message,
    )
