from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db.database import engine, Base
from app.api import recognize, history, feedback, health, export


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создаём таблицы при старте
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="PriceTag Recognition API",
    description="MVP-сервис распознавания цен с ценников",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В проде заменить на конкретный адрес фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(recognize.router, prefix="/api/v1", tags=["recognize"])
app.include_router(history.router, prefix="/api/v1", tags=["history"])
app.include_router(feedback.router, prefix="/api/v1", tags=["feedback"])
app.include_router(export.router, prefix="/api/v1", tags=["export"])
