import csv
import io
import logging
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/export/csv",
    summary="Экспорт истории распознаваний в CSV",
)
async def export_csv(
    db: AsyncSession = Depends(get_db),
):
    """
    Экспортирует все записи распознавания в CSV формат.
    
    Колонки:
    - id: UUID записи
    - created_at: Дата и время создания
    - product_name: Название товара (или "нет" если отсутствует на ценнике, пусто если не распознан)
    - price: Цена
    - barcode: Штрихкод (или "нет"/пусто)
    - weight: Вес/объем (или "нет"/пусто)
    - store: Магазин (или "нет"/пусто)
    - confidence: Уверенность распознавания цены
    - is_valid: Статус валидации
    - correct_price: Исправленная цена (если есть)
    """
    try:
        items, _ = await crud.get_history(db, limit=10000, offset=0)
        
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_ALL)
        
        writer.writerow([
            'id',
            'created_at',
            'product_name',
            'price',
            'barcode',
            'weight',
            'store',
            'confidence',
            'is_valid',
            'correct_price'
        ])
        
        for item in items:
            created_at = item.created_at.replace(tzinfo=timezone.utc) if item.created_at.tzinfo is None else item.created_at
            
            product_name = format_field(item.product_name)
            price = format_price(item.extracted_price)
            barcode = format_field(item.barcode)
            weight = format_field(item.weight)
            store = format_field(item.store)
            confidence = f"{item.confidence:.3f}" if item.confidence is not None else ""
            is_valid = format_validation_status(item.is_valid)
            correct_price = format_price(item.correct_price)
            
            writer.writerow([
                str(item.id),
                created_at.strftime("%Y-%m-%d %H:%M:%S"),
                product_name,
                price,
                barcode,
                weight,
                store,
                confidence,
                is_valid,
                correct_price
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        # Получаем дату последней записи для имени файла
        last_item_date = items[0].created_at if items else timezone.now()
        filename = f"retailwatch_export_{last_item_date.strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv; charset=utf-8-sig",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
            }
        )
        
    except Exception as e:
        logger.exception("Ошибка при экспорте CSV")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при генерации CSV файла"
        )


def format_field(value: str | None) -> str:
    """
    Форматирует поле согласно ТЗ:
    - Если параметр отсутствует на ценнике -> "нет"
    - Если не распознан -> пусто
    """
    if value is None or value.strip() == "":
        return ""
    return value.strip()


def format_price(value: float | None) -> str:
    """Форматирует цену."""
    if value is None:
        return ""
    return f"{value:.2f}"


def format_validation_status(is_valid: bool | None) -> str:
    """Форматирует статус валидации."""
    if is_valid is None:
        return "pending"
    return "valid" if is_valid else "invalid"
