# RetailWatch Frontend

Фронтенд для MVP-сервиса распознавания ценников.

## Что внутри

- `React + TypeScript + Vite`
- ручная загрузка изображения на `/recognize`
- история распознаваний через `/history`
- карточка детали с base64-изображением через `/history/{id}`
- обратная связь через `/feedback/{id}`

## Запуск

```bash
cp .env.example .env
npm install
npm run dev
```

По умолчанию фронтенд ожидает backend на `http://localhost:8000/api/v1`.
