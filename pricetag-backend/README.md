# PriceTag Recognition — Backend

FastAPI-бэкенд для сервиса распознавания ценников с извлечением всех параметров.

## Возможности

✅ Распознавание цены
✅ Извлечение названия товара
✅ Поиск штрихкода
✅ Определение веса/объема
✅ Распознавание магазина
✅ Экспорт данных в CSV
✅ История распознаваний
✅ Ручная валидация результатов

## Быстрый старт

### 1. Через Docker (рекомендуется)

```bash
cp .env.example .env
docker-compose up --build
```

API доступно на http://localhost:8000  
Swagger UI: http://localhost:8000/docs

**Важно:** При первом запуске или после обновления примените миграцию БД:
```bash
psql -U postgres -d pricetag -f migration_add_fields.sql
```

---

### 2. Локально (без Docker)

**Требования:** Python 3.11+, PostgreSQL 14+

```bash
# Зависимости
pip install -r requirements.txt

# Переменные окружения
cp .env.example .env
# Отредактируй .env под свою БД

# Создать схему БД (опционально — SQLAlchemy создаёт таблицы автоматически при старте)
psql -U postgres -d pricetag -f schema.sql

# Запуск
uvicorn app.main:app --reload
```

---

## Структура проекта

```
app/
├── main.py              # FastAPI app, middleware, роутеры
├── core/
│   └── config.py        # Настройки (env-переменные через pydantic-settings)
├── api/
│   ├── health.py        # GET /health, GET /health/db
│   ├── recognize.py     # POST /api/v1/recognize
│   ├── history.py       # GET /api/v1/history, GET /api/v1/history/{id}
│   ├── feedback.py      # POST /api/v1/feedback/{id}
│   └── export.py        # GET /api/v1/export/csv
├── db/
│   ├── database.py      # Async SQLAlchemy engine + get_db dependency
│   └── crud.py          # CRUD-операции с таблицей recognitions
├── models/
│   ├── recognition.py   # SQLAlchemy ORM-модель
│   └── schemas.py       # Pydantic-схемы (request/response)
└── services/
    └── ml_service.py    # OCRProcessor (распознавание всех параметров)
```

---

## API

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/health` | Статус сервиса |
| GET | `/health/db` | Проверка связи с БД |
| POST | `/api/v1/recognize` | Распознать ценник (возвращает все параметры) |
| GET | `/api/v1/history` | История (limit, offset, status) |
| GET | `/api/v1/history/{id}` | Карточка с картинкой в base64 |
| POST | `/api/v1/feedback/{id}` | Отметить ошибку / подтвердить |
| GET | `/api/v1/export/csv` | Экспорт всех данных в CSV |

### Пример ответа /recognize

```json
{
  "request_id": "uuid",
  "price": 129.90,
  "product_name": "Молоко Домик в деревне",
  "barcode": "4601234567890",
  "weight": "900г",
  "store": "Магнит",
  "confidence": 0.95,
  "raw_text": "OCR текст...",
  "timestamp": "2026-05-12T10:30:00Z"
}
```

---

## Подключение ML

В `app/services/ml_service.py` реализован класс `OCRProcessor` с полным функционалом распознавания.

**Реализованные методы извлечения:**
- `_extract_product_name()` - название товара
- `_extract_barcode()` - штрихкод (8-13 цифр)
- `_extract_weight()` - вес/объем (г, кг, мл, л)
- `_extract_store()` - магазин (по ключевым словам)

**OCR движки:**
- Tesseract (быстрый, хороший для текста)
- PaddleOCR (точный, хорош для цен)
- Hybrid (оба движка вместе)

**Настройка в `.env`:**
```bash
USE_ML=true              # Включить ML
OCR_ENGINE=hybrid        # tesseract | paddle | hybrid
OCR_LANG=rus+eng         # Язык OCR
```

---

## Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `POSTGRES_HOST` | localhost | Хост БД |
| `POSTGRES_USER` | postgres | Пользователь БД |
| `POSTGRES_PASSWORD` | postgres | Пароль БД |
| `POSTGRES_DB` | pricetag | Имя БД |
| `DEBUG` | false | SQLAlchemy echo |
| `MAX_IMAGE_SIZE_MB` | 10 | Лимит размера файла |
| `USE_ML` | true | Включить ML-пайплайн |
| `OCR_ENGINE` | hybrid | OCR движок: tesseract, paddle, hybrid |
| `OCR_LANG` | rus+eng | Язык OCR |
| `TESSERACT_CMD` | tesseract | Путь к Tesseract |
| `YOLO_MODEL_PATH` | — | Путь к весам YOLOv8 (опционально) |

---

## Миграции БД

При обновлении с предыдущей версии примените миграцию:

```bash
psql -U postgres -d pricetag -f migration_add_fields.sql
```

Это добавит поля: product_name, barcode, weight, store

---

## Тестирование

```bash
# Установка зависимостей
pip install -r ../test_requirements.txt

# Запуск тестов
python ../test_api.py
```

---

## Документация

- [QUICKSTART.md](../QUICKSTART.md) - Быстрый старт
- [UPDATE_INSTRUCTIONS.md](../UPDATE_INSTRUCTIONS.md) - Подробные инструкции по обновлению
- [CHANGELOG.md](../CHANGELOG.md) - История изменений
