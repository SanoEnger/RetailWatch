from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "pricetag"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # App
    DEBUG: bool = False
    MAX_IMAGE_SIZE_MB: int = 10

    @property
    def MAX_IMAGE_SIZE_BYTES(self) -> int:
        return self.MAX_IMAGE_SIZE_MB * 1024 * 1024

    # ML (заглушки — ML-разработчик заполнит)
    USE_ML: bool = False  # Переключить в True когда ML готов
    YOLO_MODEL_PATH: Optional[str] = None
    OCR_LANG: str = "ru"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
