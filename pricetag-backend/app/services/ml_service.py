"""
ML-сервис: заглушка с интерфейсом под реальную модель.

ML-разработчик заменяет _process_real() на настоящую логику.
Переключение: settings.USE_ML = True (в .env: USE_ML=true)
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class MLResult:
    raw_text: Optional[str]
    price: Optional[float]
    confidence: Optional[float]


class OCRProcessor:
    """
    Singleton-обёртка над ML-пайплайном.
    При USE_ML=False возвращает фиктивные данные (заглушка для разработки).
    """

    _instance: Optional["OCRProcessor"] = None

    def __new__(cls) -> "OCRProcessor":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        if settings.USE_ML:
            self._load_models()

    def _load_models(self) -> None:
        """Загрузка моделей — вызывается один раз при старте."""
        try:
            # ML-разработчик подключает реальные модели:
            #
            # from paddleocr import PaddleOCR
            # from ultralytics import YOLO
            #
            # self.ocr = PaddleOCR(use_angle_cls=True, lang=settings.OCR_LANG)
            # if settings.YOLO_MODEL_PATH:
            #     self.yolo = YOLO(settings.YOLO_MODEL_PATH)
            # else:
            #     self.yolo = None
            pass
        except Exception as e:
            logger.error("Ошибка загрузки ML-моделей: %s", e)
            raise

    # ── Public API ─────────────────────────────────────────────────────────────

    async def process(self, image_bytes: bytes) -> MLResult:
        if settings.USE_ML:
            return await self._process_real(image_bytes)
        return self._process_stub(image_bytes)

    # ── Stub (заглушка) ────────────────────────────────────────────────────────

    def _process_stub(self, image_bytes: bytes) -> MLResult:
        """Возвращает фиктивный результат для разработки без модели."""
        logger.debug("ML заглушка: возвращаем фиктивную цену 100.00")
        return MLResult(
            raw_text="Молоко 100.00 руб.",
            price=100.00,
            confidence=0.99,
        )

    # ── Real pipeline (ML-разработчик заполняет) ───────────────────────────────

    async def _process_real(self, image_bytes: bytes) -> MLResult:
        """
        Реальный пайплайн:
          1. Decode bytes → numpy image
          2. Preprocess (CLAHE, denoise)
          3. YOLO crop (опционально)
          4. PaddleOCR → raw_text
          5. extract_price regex
        """
        import numpy as np
        import cv2

        # 1. Decode
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return MLResult(raw_text=None, price=None, confidence=None)

        # 2. Preprocess
        img = self._preprocess(img)

        # 3. YOLO crop (если модель загружена)
        # if hasattr(self, "yolo") and self.yolo:
        #     img = self._yolo_crop(img)

        # 4. OCR
        # results = self.ocr.ocr(img, cls=True)
        # raw_text = " ".join(
        #     word_info[1][0] for line in results for word_info in line
        # )
        raw_text = ""  # заглушка до подключения OCR

        # 5. Extract price
        price = self._extract_price(raw_text)
        confidence = 0.90 if price is not None else 0.0

        return MLResult(raw_text=raw_text, price=price, confidence=confidence)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _preprocess(self, img):
        """CLAHE + denoise для улучшения читаемости."""
        import cv2
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        denoised = cv2.fastNlMeansDenoising(enhanced, h=10)
        return denoised

    @staticmethod
    def _extract_price(text: str) -> Optional[float]:
        """
        Ищет числовой формат цены: 120, 120.50, 120,50
        Возвращает наибольшее найденное число (чаще всего — это и есть цена).
        """
        if not text:
            return None

        pattern = r"\b\d{1,6}([.,]\d{2})?\b"
        matches = re.findall(pattern, text)

        if not matches:
            return None

        # re.findall возвращает список захваченных групп, нам нужны полные совпадения
        full_matches = re.findall(r"\b\d{1,6}(?:[.,]\d{2})?\b", text)
        candidates = [float(m.replace(",", ".")) for m in full_matches]

        return max(candidates) if candidates else None


# Глобальный экземпляр (инициализируется один раз)
ocr_processor = OCRProcessor()
