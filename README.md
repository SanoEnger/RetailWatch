# RetailWatch - Система распознавания ценников

## Быстрый старт

### Требования

- Docker и Docker Compose
- Node.js 18+
- PostgreSQL (через Docker)

---

## Установка и запуск

### Шаг 1: Клонирование репозитория

```bash
git clone <repository-url>
cd RetailWatch
```

### Шаг 2: Запуск backend

```bash
cd pricetag-backend

# Копирование конфигурации
cp .env.example .env

# Запуск через Docker
docker-compose up -d

# Проверка
curl http://localhost:8000/health
```

Backend доступен по адресу: http://localhost:8000  
Swagger UI: http://localhost:8000/docs

### Шаг 3: Запуск frontend

```bash
cd ../pricetag-frontend

# Установка зависимостей
npm install

# Запуск в режиме разработки
npm run dev
```

Frontend доступен по адресу: http://localhost:5173

---

## Использование

### 1. Загрузка изображения

1. Откройте http://localhost:5173
2. Нажмите "Выбрать файл" или перетащите изображение ценника
3. Нажмите "Распознать"
4. Результат отобразится автоматически

### 2. Просмотр истории

- Все распознавания сохраняются в базе данных
- Откройте вкладку "История"
- Можно фильтровать по дате и цене

### 3. Экспорт в CSV

- Нажмите кнопку "Экспорт CSV" в истории
- Файл скачается в формате, совместимом с Excel

---

## Применение миграции БД

Если у вас уже есть база данных, примените миграцию:

```bash
cd pricetag-backend

# Копирование файла миграции в контейнер
docker cp migration_add_fields.sql pricetag-backend-db-1:/tmp/migration_add_fields.sql

# Выполнение миграции
docker-compose exec db psql -U postgres -d pricetag -f /tmp/migration_add_fields.sql

# Перезапуск backend
docker-compose restart backend
```

---

## API Endpoints

### Основные

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/health` | Проверка здоровья |
| POST | `/recognize` | Распознавание ценника |
| GET | `/history` | Получение истории |
| GET | `/export/csv` | Экспорт в CSV |
| POST | `/feedback` | Отправка обратной связи |

### Пример использования API

```bash
# Распознавание
curl -X POST http://localhost:8000/recognize \
  -F "file=@pricetag.jpg"

# Получение истории
curl http://localhost:8000/history?limit=10

# Экспорт в CSV
curl -o export.csv http://localhost:8000/export/csv
```

---

## Структура проекта

```
RetailWatch/
├── pricetag-backend/      # Backend (FastAPI + PostgreSQL)
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── services/     # ML/OCR services
│   │   ├── models/       # Database models
│   │   └── db/           # Database operations
│   ├── docker-compose.yml
│   └── requirements.txt
│
├── pricetag-frontend/     # Frontend (React + TypeScript)
│   ├── src/
│   │   ├── components/   # UI components
│   │   ├── lib/          # API client
│   │   └── types/        # TypeScript types
│   └── package.json
│
└── ml_model/              # ML model training
    ├── Данные/           # Labeled dataset
    ├── yolo_dataset/     # YOLO format dataset
    ── colab_training.zip # Archive for Colab
```

---

## Распознаваемые параметры

Система извлекает из ценников:

- **Название товара** (product_name)
- **Цена** (price)
- **Штрихкод** (barcode, 8-13 цифр)
- **Вес/Объем** (weight, например: 500г, 1л)
- **Магазин** (store, например: Магнит, Пятерочка)

---

## Технологии

### Backend
- **FastAPI** - Web framework
- **SQLAlchemy** - ORM
- **PostgreSQL** - Database
- **Tesseract OCR / PaddleOCR** - Распознавание текста
- **OpenCV** - Обработка изображений
- **Docker** - Контейнеризация

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool

### ML
- **YOLOv8** - Детекция ценников (опционально)
- **PyTorch** - ML framework

---

## Настройка

### Backend (.env)

```env
DATABASE_URL=postgresql://postgres:postgres@db:5432/pricetag
OCR_ENGINE=tesseract  # или paddle
SECRET_KEY=your-secret-key
```

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000
```

---

## Тестирование

```bash
# Backend тесты
cd pricetag-backend
pytest tests/

# API тесты
python test_api.py
```

---

## Обучение ML модели

См. инструкцию: [ml_model/README.md](ml_model/README.md)

Кратко:
1. Загрузите `ml_model/colab_training.zip` в Google Drive
2. Откройте Google Colab
3. Выполните ячейки из инструкции
4. Скачайте обученную модель
5. Поместите в `ml_model/models/`

---

## Устранение проблем

### Backend не запускается

```bash
# Проверка логов
docker-compose logs backend

# Перезапуск
docker-compose restart backend

# Полное пересоздание
docker-compose down
docker-compose up -d --build
```

### Frontend не подключается к API

1. Проверьте, что backend работает: http://localhost:8000/health
2. Проверьте CORS настройки в backend
3. Обновите `VITE_API_URL` в frontend .env

### Ошибки OCR

- Убедитесь, что Tesseract установлен
- Проверьте качество изображения
- Попробуйте другой OCR engine (paddle вместо tesseract)

---

## Производительность

- **Время распознавания**: ~1-3 секунды на изображение
- **Поддерживаемые форматы**: JPG, PNG, BMP
- **Рекомендуемое разрешение**: 800x600 и выше

---

## Лицензия

MIT

---

## Контакты

По вопросам и предложениям: [your-email@example.com]
