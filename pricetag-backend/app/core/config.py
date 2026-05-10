from typing import Any, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "pricetag"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    DEBUG: bool = False
    MAX_IMAGE_SIZE_MB: int = 10
    CENTER_CROP_RATIO: float = 0.72

    USE_ML: bool = False
    YOLO_MODEL_PATH: Optional[str] = None
    OCR_LANG: str = "ru"
    OCR_ENGINE: str = "tesseract"
    TESSERACT_LANG: str = "rus+eng"
    TESSERACT_CMD: Optional[str] = None

    @field_validator("DEBUG", "USE_ML", mode="before")
    @classmethod
    def parse_bool_loose(cls, value: Any) -> Any:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off", "release"}:
                return False
        return value

    @field_validator("OCR_ENGINE", mode="before")
    @classmethod
    def normalize_ocr_engine(cls, value: Any) -> str:
        normalized = str(value or "tesseract").strip().lower()
        allowed = {"tesseract", "paddle", "hybrid"}
        return normalized if normalized in allowed else "tesseract"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def MAX_IMAGE_SIZE_BYTES(self) -> int:
        return self.MAX_IMAGE_SIZE_MB * 1024 * 1024

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
