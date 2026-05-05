# PriceTag Recognition — Backend

FastAPI-бэкенд для MVP-сервиса распознавания цен на ценниках.

## Быстрый старт

### 1. Через Docker (рекомендуется)

```bash
cp .env.example .env
docker-compose up --build
```

API доступно на http://localhost:8000  
Swagger UI: http://localhost:8000/docs

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
│   └── feedback.py      # POST /api/v1/feedback/{id}
├── db/
│   ├── database.py      # Async SQLAlchemy engine + get_db dependency
│   └── crud.py          # CRUD-операции с таблицей recognitions
├── models/
│   ├── recognition.py   # SQLAlchemy ORM-модель
│   └── schemas.py       # Pydantic-схемы (request/response)
└── services/
    └── ml_service.py    # OCRProcessor (заглушка + скелет для ML)
```

---

## API

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/health` | Статус сервиса |
| GET | `/health/db` | Проверка связи с БД |
| POST | `/api/v1/recognize` | Распознать цену на фото |
| GET | `/api/v1/history` | История (limit, offset, status) |
| GET | `/api/v1/history/{id}` | Карточка с картинкой в base64 |
| POST | `/api/v1/feedback/{id}` | Отметить ошибку / подтвердить |

---

## Подключение ML

В `app/services/ml_service.py` описан класс `OCRProcessor`.  
Сейчас он работает в режиме заглушки (возвращает фиктивную цену 100.00).

Чтобы включить реальную модель:

1. Раскомментировать ML-зависимости в `requirements.txt`
2. Заполнить `_load_models()` и `_process_real()` в `ml_service.py`
3. Установить `USE_ML=true` в `.env`

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
| `USE_ML` | false | Включить реальный ML-пайплайн |
| `YOLO_MODEL_PATH` | — | Путь к весам YOLOv8 |
