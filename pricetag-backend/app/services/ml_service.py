"""
Robust OCR pipeline for price-tag recognition.

This version is optimized for retail labels:
- detect the tag region first;
- detect the main price block inside the tag;
- OCR a few focused ROI proposals instead of the whole frame repeatedly;
- keep runtime bounded with Tesseract timeouts.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


PRICE_PATTERN = re.compile(r"(?<!\d)(\d{1,6}(?:[.,]\d{1,2})?)(?!\d)")
INTEGER_MONEY_PATTERN = re.compile(r"(?<!\d)(\d{2,6})(?!\d)")
CURRENCY_HINT_PATTERN = re.compile(
    r"(руб|р\b|₽|цена|итог|sale|price|стоим)",
    re.IGNORECASE,
)
OLD_PRICE_HINT_PATTERN = re.compile(
    r"(обычн|старая|без скид|regular|old)",
    re.IGNORECASE,
)
DISCOUNT_HINT_PATTERN = re.compile(r"(%|скид|discount|promo|sale)", re.IGNORECASE)
PRODUCT_UNIT_PATTERN = re.compile(
    r"(?<![а-яa-z])\d{1,5}\s*(г|гр|g|r|кг|kg|мл|ml|л|l|шт|pcs|pc)\b",
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b")

BARCODE_PATTERN = re.compile(r"\b(\d{8,13})\b")
WEIGHT_PATTERN = re.compile(
    r"(\d+\.?\d*)\s*(г|гр|кг|мл|л|g|kg|ml|l|литр|грамм)", 
    re.IGNORECASE
)
STORE_PATTERNS = [
    re.compile(r"(магнит|пятерочка|перекресток|ашан|metro|lenta|globus|верный|fix\s*price)", re.IGNORECASE),
    re.compile(r"(сеть\s+магазинов|торговая\s+сеть|магазин)", re.IGNORECASE),
]
PRODUCT_NAME_INDICATORS = [
    re.compile(r"(наименование|товар|продукт|название)", re.IGNORECASE),
]


@dataclass(slots=True)
class MLResult:
    raw_text: Optional[str]
    price: Optional[float]
    confidence: Optional[float]
    engine: str
    message: Optional[str] = None
    product_name: Optional[str] = None
    barcode: Optional[str] = None
    weight: Optional[str] = None
    store: Optional[str] = None


@dataclass(slots=True)
class OCRToken:
    text: str
    confidence: float
    center_x: float
    center_y: float
    width: float
    height: float
    variant_name: str
    engine_name: str


@dataclass(slots=True)
class PriceCandidate:
    value: float
    score: float
    confidence: float
    source_text: str
    variant_name: str
    engine_name: str


class OCRProcessor:
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
        self.paddle_ocr = None
        self.paddle_available = None
        self.tesseract_available = None

    async def process(self, image_bytes: bytes) -> MLResult:
        if settings.USE_ML:
            return await asyncio.to_thread(self._process_real_sync, image_bytes)
        return self._process_stub()

    def _process_stub(self) -> MLResult:
        return MLResult(
            raw_text="Молоко 100.00 руб. 500г Магнит",
            price=100.00,
            confidence=0.99,
            engine="stub",
            message="ML disabled; stub response is active.",
            product_name="Молоко",
            barcode=None,
            weight="500г",
            store="Магнит",
        )

    def get_status(self) -> dict[str, object]:
        return {
            "use_ml": settings.USE_ML,
            "ocr_engine": settings.OCR_ENGINE,
            "tesseract_available": self._check_tesseract_available(),
            "paddle_initialized": self.paddle_ocr is not None,
            "paddle_available": self.paddle_available,
        }

    def _process_real_sync(self, image_bytes: bytes) -> MLResult:
        import cv2
        import numpy as np

        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            return MLResult(
                raw_text=None,
                price=None,
                confidence=0.0,
                engine="none",
                message="Image decoding failed.",
            )

        image = self._resize_if_needed(image)
        tag_crop = self._detect_price_tag_crop(image)

        all_tokens: list[OCRToken] = []
        used_engines: list[str] = []

        for engine_name in self._engine_order():
            try:
                engine_tokens = self._collect_tokens_for_engine(tag_crop, engine_name)
            except Exception:
                logger.exception("OCR engine '%s' failed", engine_name)
                continue

            if engine_tokens:
                all_tokens.extend(engine_tokens)
                used_engines.append(engine_name)

        tokens = self._dedupe_tokens(all_tokens)
        
        candidate = self._pick_best_price(tokens, tag_crop.shape[1], tag_crop.shape[0])
        
        extracted_info = self._extract_all_parameters(tokens, tag_crop.shape[1], tag_crop.shape[0])

        if self._should_try_sale_roi_paddle(tokens, candidate):
            sale_roi = self._extract_sale_price_roi(tag_crop)
            if sale_roi is not None:
                paddle_sale_tokens = self._run_paddle(sale_roi, "sale-price-roi")
                if paddle_sale_tokens:
                    tokens = self._dedupe_tokens(tokens + paddle_sale_tokens)
                    candidate = self._pick_best_price(
                        tokens,
                        tag_crop.shape[1],
                        tag_crop.shape[0],
                    )
                    
                    updated_info = self._extract_all_parameters(tokens, tag_crop.shape[1], tag_crop.shape[0])
                    extracted_info.update(updated_info)

        raw_text = " ".join(token.text for token in tokens).strip() or None

        if candidate is None:
            return MLResult(
                raw_text=raw_text,
                price=None,
                confidence=0.0,
                engine="+".join(used_engines) if used_engines else "none",
                message="Цена не найдена. Нужен более четкий кадр или более крупный фрагмент ценника.",
                **extracted_info,
            )

        return MLResult(
            raw_text=raw_text,
            price=candidate.value,
            confidence=round(max(0.0, min(candidate.confidence, 0.999)), 3),
            engine=candidate.engine_name,
            message=None,
            **extracted_info,
        )

    def _extract_all_parameters(
        self, 
        tokens: list[OCRToken], 
        tag_width: int, 
        tag_height: int
    ) -> dict:
        """Extract all required parameters from OCR tokens."""
        
        product_name = self._extract_product_name(tokens)
        barcode = self._extract_barcode(tokens)
        weight = self._extract_weight(tokens)
        store = self._extract_store(tokens)
        
        return {
            "product_name": product_name,
            "barcode": barcode,
            "weight": weight,
            "store": store,
        }

    def _extract_product_name(self, tokens: list[OCRToken]) -> Optional[str]:
        """Extract product name from OCR tokens."""
        if not tokens:
            return None
        
        sorted_tokens = sorted(tokens, key=lambda t: (t.center_y, t.center_x))
        
        potential_names = []
        for token in sorted_tokens[:8]:
            text = token.text.strip()
            
            if not text:
                continue
            
            if len(text) < 3 or len(text) > 80:
                continue
            
            if re.match(r'^[\d\s.,%₽]+$|^$', text):
                continue
            
            if any(pattern.search(text) for pattern in [
                PRICE_PATTERN, BARCODE_PATTERN, WEIGHT_PATTERN, DISCOUNT_HINT_PATTERN
            ]):
                continue
            
            potential_names.append(text)
        
        if potential_names:
            name = " ".join(potential_names[:2])
            return name if len(name) >= 3 else None
        
        return None

    def _extract_barcode(self, tokens: list[OCRToken]) -> Optional[str]:
        """Extract barcode from OCR tokens."""
        for token in tokens:
            match = BARCODE_PATTERN.search(token.text)
            if match:
                barcode = match.group(1)
                if 8 <= len(barcode) <= 13:
                    return barcode
        
        combined_text = " ".join(t.text for t in tokens)
        match = BARCODE_PATTERN.search(combined_text)
        if match:
            barcode = match.group(1)
            if 8 <= len(barcode) <= 13:
                return barcode
        
        return None

    def _extract_weight(self, tokens: list[OCRToken]) -> Optional[str]:
        """Extract weight/volume from OCR tokens."""
        for token in tokens:
            match = WEIGHT_PATTERN.search(token.text)
            if match:
                return match.group(0).strip()
        
        combined_text = " ".join(t.text for t in tokens)
        match = WEIGHT_PATTERN.search(combined_text)
        if match:
            return match.group(0).strip()
        
        for token in tokens:
            if PRODUCT_UNIT_PATTERN.search(token.text):
                return token.text.strip()
        
        return None

    def _extract_store(self, tokens: list[OCRToken]) -> Optional[str]:
        """Extract store name from OCR tokens."""
        combined_text = " ".join(t.text for t in tokens)
        
        for pattern in STORE_PATTERNS:
            match = pattern.search(combined_text)
            if match:
                return match.group(0).strip().title()
        
        for token in tokens:
            for pattern in STORE_PATTERNS:
                match = pattern.search(token.text)
                if match:
                    return match.group(0).strip().title()
        
        return None

    def _should_try_sale_roi_paddle(
        self,
        tokens: list[OCRToken],
        candidate: Optional[PriceCandidate],
    ) -> bool:
        if self.paddle_available is False:
            return False

        has_old_price_context = any(
            OLD_PRICE_HINT_PATTERN.search(token.text or "")
            for token in tokens
        )
        has_discount_context = any(
            DISCOUNT_HINT_PATTERN.search(token.text or "")
            for token in tokens
        )

        if candidate is None:
            return True

        if not (has_old_price_context or has_discount_context):
            return False

        if (
            "sale-price-roi" in candidate.variant_name
            and "+" in candidate.variant_name
            and not self._looks_like_product_size(candidate.source_text)
        ):
            return False

        return True

    def _engine_order(self) -> list[Literal["tesseract", "paddle"]]:
        if settings.OCR_ENGINE == "paddle":
            return ["paddle"]
        if settings.OCR_ENGINE == "hybrid":
            return ["tesseract", "paddle"]
        return ["tesseract"]

    def _collect_tokens_for_engine(
        self,
        tag_crop,
        engine_name: Literal["tesseract", "paddle"],
    ) -> list[OCRToken]:
        tokens: list[OCRToken] = []
        variants = self._build_variants(tag_crop)

        for variant_name, variant_image in variants:
            if engine_name == "tesseract":
                tokens.extend(self._run_tesseract(variant_image, variant_name))
            elif engine_name == "paddle":
                tokens.extend(self._run_paddle(variant_image, variant_name))

        return tokens

    def _run_tesseract(self, image, variant_name: str) -> list[OCRToken]:
        import cv2
        import pytesseract

        if not self._check_tesseract_available():
            return []

        if settings.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        tokens: list[OCRToken] = []

        configs = [
            (
                "general",
                f"--oem 3 --psm 6 -l {settings.TESSERACT_LANG}",
                False,
            ),
            (
                "price",
                f"--oem 3 --psm 7 -l {settings.TESSERACT_LANG} "
                "-c tessedit_char_whitelist=0123456789.,",
                True,
            ),
        ]

        for config_name, config, is_price_mode in configs:
            try:
                if is_price_mode:
                    text = pytesseract.image_to_string(gray, config=config, timeout=12)
                    normalized_text = self._normalize_text(text)
                    if normalized_text:
                        height, width = gray.shape[:2]
                        tokens.append(
                            OCRToken(
                                text=normalized_text,
                                confidence=0.78,
                                center_x=width / 2,
                                center_y=height / 2,
                                width=float(width),
                                height=float(height),
                                variant_name=f"{variant_name}:{config_name}",
                                engine_name="tesseract",
                            )
                        )
                    continue

                data = pytesseract.image_to_data(
                    gray,
                    config=config,
                    output_type=pytesseract.Output.DICT,
                    timeout=12,
                )
            except RuntimeError:
                logger.warning("Tesseract timeout on variant '%s' config '%s'", variant_name, config_name)
                continue
            except Exception:
                logger.exception("Tesseract failed on variant '%s' config '%s'", variant_name, config_name)
                continue

            for index, raw_text in enumerate(data.get("text", [])):
                normalized_text = self._normalize_text(str(raw_text).strip())
                if not normalized_text:
                    continue

                confidence_raw = data.get("conf", ["0"])[index]
                try:
                    confidence = max(0.0, min(1.0, float(confidence_raw) / 100))
                except (TypeError, ValueError):
                    confidence = 0.0

                left = float(data.get("left", [0])[index])
                top = float(data.get("top", [0])[index])
                width = float(data.get("width", [0])[index])
                height = float(data.get("height", [0])[index])

                tokens.append(
                    OCRToken(
                        text=normalized_text,
                        confidence=confidence,
                        center_x=left + width / 2,
                        center_y=top + height / 2,
                        width=width,
                        height=height,
                        variant_name=f"{variant_name}:{config_name}",
                        engine_name="tesseract",
                    )
                )

        return tokens

    def _run_paddle(self, image, variant_name: str) -> list[OCRToken]:
        if not self._ensure_paddle_ready():
            return []

        try:
            result = self.paddle_ocr.predict(image) if self.paddle_ocr else []
        except Exception:
            logger.exception("PaddleOCR failed on variant '%s'", variant_name)
            return []

        return self._parse_paddle_result(result, variant_name)

    def _ensure_paddle_ready(self) -> bool:
        if self.paddle_available is False:
            return False

        if self.paddle_ocr is not None:
            return True

        cache_root = Path(__file__).resolve().parents[2] / ".ocr-cache"
        cache_root.mkdir(parents=True, exist_ok=True)
        os.environ["PADDLE_PDX_CACHE_HOME"] = str(cache_root / "paddlex")
        os.environ["PADDLE_HOME"] = str(cache_root / "paddle")
        os.environ["XDG_CACHE_HOME"] = str(cache_root / ".cache")
        os.environ["HOME"] = str(cache_root)
        os.environ["USERPROFILE"] = str(cache_root)
        os.environ["HOMEDRIVE"] = ""
        os.environ["HOMEPATH"] = str(cache_root)
        os.environ["PADDLEOCR_DISABLE_AUTO_LOGGING_CONFIG"] = "1"
        os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"

        try:
            from paddleocr import PaddleOCR
            self.paddle_ocr = PaddleOCR(
                use_textline_orientation=True,
                lang=settings.OCR_LANG,
            )
            self.paddle_available = True
            return True
        except Exception:
            logger.exception("PaddleOCR initialization failed.")
            self.paddle_available = False
            self.paddle_ocr = None
            return False

    def _check_tesseract_available(self) -> bool:
        if self.tesseract_available is not None:
            return self.tesseract_available

        cmd = settings.TESSERACT_CMD or "tesseract"
        self.tesseract_available = shutil.which(cmd) is not None
        if not self.tesseract_available:
            logger.warning("Tesseract binary was not found in PATH.")
        return self.tesseract_available

    def _resize_if_needed(self, image, max_side: int = 1600):
        import cv2

        height, width = image.shape[:2]
        largest_side = max(height, width)
        if largest_side <= max_side:
            return image

        scale = max_side / largest_side
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)

    def _detect_price_tag_crop(self, image):
        import cv2
        import numpy as np

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 175, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 9))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        img_h, img_w = gray.shape
        image_area = img_h * img_w
        best_box = None
        best_score = -math.inf

        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            area = width * height
            if area < image_area * 0.08 or area > image_area * 0.9:
                continue

            ratio = width / max(height, 1)
            score = 0.0
            if 2.0 <= ratio <= 8.5:
                score += 3.0
            if y > img_h * 0.15:
                score += 1.0
            if y + height < img_h * 0.95:
                score += 0.5
            score += min(area / image_area, 0.4) * 4

            if score > best_score:
                best_box = (x, y, width, height)
                best_score = score

        if best_box is None:
            return self._center_crop(image)

        x, y, width, height = best_box
        pad_x = int(width * 0.03)
        pad_y = int(height * 0.06)
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(img_w, x + width + pad_x)
        y2 = min(img_h, y + height + pad_y)
        return image[y1:y2, x1:x2]

    def _center_crop(self, image):
        height, width = image.shape[:2]
        crop_w = int(width * settings.CENTER_CROP_RATIO)
        crop_h = int(height * settings.CENTER_CROP_RATIO)
        start_x = max(0, (width - crop_w) // 2)
        start_y = max(0, (height - crop_h) // 2)
        return image[start_y:start_y + crop_h, start_x:start_x + crop_w]

    def _build_variants(self, tag_crop) -> list[tuple[str, object]]:
        import cv2

        gray = cv2.cvtColor(tag_crop, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        binary = cv2.adaptiveThreshold(
            enhanced,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )

        main_price_crop = self._extract_main_price_region(tag_crop)
        sale_price_roi = self._extract_sale_price_roi(tag_crop)
        upper_right_crop = self._extract_upper_right_region(tag_crop)

        variants: list[tuple[str, object]] = [
            ("tag-general", self._ensure_bgr(enhanced)),
            ("tag-binary", self._ensure_bgr(binary)),
        ]

        if main_price_crop is not None:
            main_gray = cv2.cvtColor(main_price_crop, cv2.COLOR_BGR2GRAY)
            main_upscaled = cv2.resize(
                main_gray,
                None,
                fx=2.0,
                fy=2.0,
                interpolation=cv2.INTER_CUBIC,
            )
            _, main_bin = cv2.threshold(
                main_upscaled,
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU,
            )
            variants.append(("main-price", self._ensure_bgr(main_upscaled)))
            variants.append(("main-price-binary", self._ensure_bgr(main_bin)))

        if sale_price_roi is not None:
            sale_gray = cv2.cvtColor(sale_price_roi, cv2.COLOR_BGR2GRAY)
            sale_upscaled = cv2.resize(
                sale_gray,
                None,
                fx=2.4,
                fy=2.4,
                interpolation=cv2.INTER_CUBIC,
            )
            _, sale_bin = cv2.threshold(
                sale_upscaled,
                0,
                255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU,
            )
            variants.append(("sale-price-roi", self._ensure_bgr(sale_upscaled)))
            variants.append(("sale-price-roi-binary", self._ensure_bgr(sale_bin)))

        if upper_right_crop is not None:
            upper_gray = cv2.cvtColor(upper_right_crop, cv2.COLOR_BGR2GRAY)
            variants.append(("upper-right", self._ensure_bgr(upper_gray)))

        return variants

    def _extract_main_price_region(self, tag_crop):
        import cv2

        height, width = tag_crop.shape[:2]
        roi = tag_crop[int(height * 0.30): int(height * 0.90), int(width * 0.40): width]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 13))
        merged = cv2.morphologyEx(inv, cv2.MORPH_CLOSE, kernel, iterations=2)
        contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidate_boxes: list[tuple[int, int, int, int]] = []
        roi_area = roi.shape[0] * roi.shape[1]

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            if area < roi_area * 0.006:
                continue
            if h < roi.shape[0] * 0.16:
                continue
            if y < roi.shape[0] * 0.08:
                continue
            candidate_boxes.append((x, y, w, h))

        if not candidate_boxes:
            return roi

        x1 = min(box[0] for box in candidate_boxes)
        y1 = min(box[1] for box in candidate_boxes)
        x2 = max(box[0] + box[2] for box in candidate_boxes)
        y2 = max(box[1] + box[3] for box in candidate_boxes)

        x, y, w, h = x1, y1, x2 - x1, y2 - y1
        pad_x = int(w * 0.08)
        pad_y = int(h * 0.12)
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(roi.shape[1], x + w + pad_x)
        y2 = min(roi.shape[0], y + h + pad_y)
        return roi[y1:y2, x1:x2]

    def _extract_upper_right_region(self, tag_crop):
        height, width = tag_crop.shape[:2]
        return tag_crop[0:int(height * 0.35), int(width * 0.72):width]

    def _extract_sale_price_roi(self, tag_crop):
        height, width = tag_crop.shape[:2]
        x1 = int(width * 0.47)
        x2 = int(width * 0.98)
        y1 = int(height * 0.26)
        y2 = int(height * 0.82)
        return tag_crop[y1:y2, x1:x2]

    def _parse_paddle_result(self, result, variant_name: str) -> list[OCRToken]:
        tokens: list[OCRToken] = []
        if not result:
            return tokens

        if isinstance(result, list) and result and isinstance(result[0], dict):
            for page in result:
                texts = page.get("rec_texts") or []
                scores = page.get("rec_scores") or []
                polys = page.get("rec_polys") or page.get("dt_polys") or []

                for index, text in enumerate(texts):
                    normalized_text = self._normalize_text(str(text).strip())
                    if not normalized_text:
                        continue

                    try:
                        confidence = float(scores[index]) if index < len(scores) else 0.0
                    except (TypeError, ValueError):
                        confidence = 0.0

                    bbox = polys[index] if index < len(polys) else None
                    if bbox is None:
                        center_x = center_y = width = height = 0.0
                    else:
                        center_x, center_y, width, height = self._bbox_metrics(bbox)

                    tokens.append(
                        OCRToken(
                            text=normalized_text,
                            confidence=confidence,
                            center_x=center_x,
                            center_y=center_y,
                            width=width,
                            height=height,
                            variant_name=variant_name,
                            engine_name="paddle",
                        )
                    )
        return tokens

    def _dedupe_tokens(self, tokens: list[OCRToken]) -> list[OCRToken]:
        deduped: list[OCRToken] = []
        seen: set[tuple[str, int, int]] = set()

        for token in sorted(tokens, key=lambda item: item.confidence, reverse=True):
            signature = (
                token.text,
                int(token.center_x // 10),
                int(token.center_y // 10),
            )
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(token)

        deduped.sort(key=lambda item: (item.center_y, item.center_x))
        return deduped

    def _bbox_metrics(self, bbox) -> tuple[float, float, float, float]:
        xs = [float(point[0]) for point in bbox]
        ys = [float(point[1]) for point in bbox]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        return (
            (min_x + max_x) / 2,
            (min_y + max_y) / 2,
            max_x - min_x,
            max_y - min_y,
        )

    def _pick_best_price(
        self,
        tokens: list[OCRToken],
        tag_width: int,
        tag_height: int,
    ) -> Optional[PriceCandidate]:
        candidates: list[PriceCandidate] = []

        for index, token in enumerate(tokens):
            context = self._context_window(tokens, index)
            for matched_text in self._number_candidates(token.text, context):
                candidate = self._score_candidate(
                    matched_text=matched_text,
                    token=token,
                    context=context,
                    tag_width=tag_width,
                    tag_height=tag_height,
                )
                if candidate is not None:
                    candidates.append(candidate)

        candidates.extend(
            self._build_composed_candidates(tokens, tag_width, tag_height)
        )

        if not candidates:
            return None

        candidates.sort(key=lambda item: item.score, reverse=True)
        return self._prefer_sale_price_candidate(candidates, tokens) or candidates[0]

    def _prefer_sale_price_candidate(
        self,
        candidates: list[PriceCandidate],
        tokens: list[OCRToken],
    ) -> Optional[PriceCandidate]:
        has_discount_layout = any(
            DISCOUNT_HINT_PATTERN.search(token.text or "")
            or OLD_PRICE_HINT_PATTERN.search(token.text or "")
            for token in tokens
        )
        if not has_discount_layout:
            return None

        sale_candidates = [
            candidate
            for candidate in candidates
            if "sale-price-roi" in candidate.variant_name
            and "+" in candidate.variant_name
            and "." in candidate.source_text
            and 5 <= candidate.value <= 5000
            and not self._looks_like_product_size(candidate.source_text)
        ]
        if not sale_candidates:
            return None

        sale_candidates.sort(key=lambda item: item.score, reverse=True)
        best_sale = sale_candidates[0]
        best_overall = candidates[0]

        if best_sale.score >= best_overall.score - 3.5:
            return best_sale

        return None

    def _build_composed_candidates(
        self,
        tokens: list[OCRToken],
        tag_width: int,
        tag_height: int,
    ) -> list[PriceCandidate]:
        candidates: list[PriceCandidate] = []
        expected_sale_price = self._expected_sale_price_from_discount(tokens)

        numeric_tokens = [
            token
            for token in tokens
            if re.fullmatch(r"\d{1,5}", re.sub(r"\D", "", token.text or ""))
        ]

        for left in numeric_tokens:
            left_digits = re.sub(r"\D", "", left.text)
            if len(left_digits) not in {2, 3}:
                continue

            for right in numeric_tokens:
                if left is right:
                    continue

                right_digits = re.sub(r"\D", "", right.text)
                if len(right_digits) != 2:
                    continue
                if self._looks_like_product_size(left.text) or self._looks_like_product_size(right.text):
                    continue
                if right.center_x <= left.center_x:
                    continue
                if abs(right.center_y - left.center_y) > tag_height * 0.16:
                    continue
                if right.center_x - left.center_x > tag_width * 0.4:
                    continue
                if "sale-price-roi" not in left.variant_name and "main-price" not in left.variant_name:
                    continue

                integer_parts = [(left_digits, False)]
                if (
                    len(left_digits) == 2
                    and "sale-price-roi" in left.variant_name
                    and left.width > left.height * 1.25
                    and left.width > right.width * 1.6
                ):
                    integer_parts.append((f"1{left_digits}", True))

                for integer_part, inferred_leading_digit in integer_parts:
                    raw_value = f"{integer_part}.{right_digits}"
                    value = self._parse_price_value(raw_value)
                    if value is None:
                        continue

                    score = (left.confidence + right.confidence) * 3.2
                    score += 4.5
                    if "sale-price-roi" in left.variant_name:
                        score += 5.5
                    if "sale-price-roi" in right.variant_name:
                        score += 1.2
                    if len(integer_part) >= 3:
                        score += 2.4
                    if inferred_leading_digit:
                        score += 1.4
                    if right.center_y < left.center_y:
                        score += 0.8
                    if 10 <= value <= 5000:
                        score += 1.0

                    if expected_sale_price is not None:
                        relative_delta = abs(value - expected_sale_price) / max(expected_sale_price, 1.0)
                        if relative_delta <= 0.18:
                            score += 5.0 * (1 - relative_delta / 0.18)
                        elif value < expected_sale_price * 0.55:
                            score -= 3.0

                    confidence = min(
                        0.999,
                        max(0.1, 0.45 + (left.confidence + right.confidence) * 0.2),
                    )
                    candidates.append(
                        PriceCandidate(
                            value=round(value, 2),
                            score=score,
                            confidence=confidence,
                            source_text=raw_value,
                            variant_name=f"{left.variant_name}+{right.variant_name}",
                            engine_name=left.engine_name,
                        )
                    )

        return candidates

    def _expected_sale_price_from_discount(self, tokens: list[OCRToken]) -> Optional[float]:
        discount_percent = self._extract_discount_percent(tokens)
        if discount_percent is None:
            return None

        old_prices: list[float] = []
        for index, token in enumerate(tokens):
            if self._looks_like_product_size(token.text):
                continue

            context = self._context_window(tokens, index)
            if DATE_PATTERN.search(context):
                continue

            digits = re.sub(r"\D", "", token.text or "")
            value: Optional[float] = None
            if re.search(r"[.,]\d{1,2}", token.text or ""):
                match = PRICE_PATTERN.search(token.text)
                value = self._parse_price_value(match.group(1)) if match else None
            elif 4 <= len(digits) <= 6:
                value = self._parse_price_value(f"{digits[:-2]}.{digits[-2:]}")

            if value is not None and 20 <= value <= 50000:
                old_prices.append(value)

        if not old_prices:
            return None

        old_price = max(old_prices)
        expected = old_price * (1 - discount_percent / 100)
        return expected if expected > 0 else None

    def _extract_discount_percent(self, tokens: list[OCRToken]) -> Optional[float]:
        for token in tokens:
            match = re.search(r"-?\s*(\d{1,2})\s*%", token.text or "")
            if not match:
                continue

            value = float(match.group(1))
            if 1 <= value <= 95:
                return value

        return None

    def _context_window(self, tokens: list[OCRToken], index: int) -> str:
        start = max(0, index - 1)
        end = min(len(tokens), index + 2)
        return " ".join(token.text for token in tokens[start:end])

    def _number_candidates(self, text: str, context: str) -> list[str]:
        if self._looks_like_product_size(text) or self._looks_like_product_size(context):
            return []

        numbers = [match.group(1) for match in PRICE_PATTERN.finditer(text)]
        if numbers:
            expanded = list(numbers)
            for item in numbers:
                digits_only = re.sub(r"\D", "", item)
                if "." not in item and "," not in item and 4 <= len(digits_only) <= 5:
                    if CURRENCY_HINT_PATTERN.search(context) or len(digits_only) >= 4:
                        expanded.append(f"{digits_only[:-2]}.{digits_only[-2:]}")
            return expanded

        if CURRENCY_HINT_PATTERN.search(text):
            return [match.group(1) for match in INTEGER_MONEY_PATTERN.finditer(text)]

        return []

    def _score_candidate(
        self,
        matched_text: str,
        token: OCRToken,
        context: str,
        tag_width: int,
        tag_height: int,
    ) -> Optional[PriceCandidate]:
        value = self._parse_price_value(matched_text)
        if value is None:
            return None

        score = token.confidence * 5
        normalized_context = self._normalize_text(context)
        has_decimals = bool(re.search(r"[.,]\d{2}$", matched_text))
        digits_only = re.sub(r"\D", "", matched_text)

        if has_decimals:
            score += 3.0
        if CURRENCY_HINT_PATTERN.search(normalized_context):
            score += 1.4
        if OLD_PRICE_HINT_PATTERN.search(normalized_context):
            score -= 2.2
        if token.center_x > tag_width * 0.55:
            score += 1.3
        if token.center_y > tag_height * 0.35:
            score += 1.1
        if token.height > tag_height * 0.18:
            score += 1.8
        if token.width > tag_width * 0.2:
            score += 0.7
        if "main-price" in token.variant_name:
            score += 2.8
        if "sale-price-roi" in token.variant_name:
            score += 4.2
        if "upper-right" in token.variant_name:
            score -= 3.0
        if "tag-general" in token.variant_name and not has_decimals:
            score -= 0.8
        if "sale-price-roi" in token.variant_name and not has_decimals and len(digits_only) <= 2:
            score -= 4.8
        if self._looks_like_product_size(token.text) or self._looks_like_product_size(normalized_context):
            score -= 6.0

        if 5 <= value <= 5000:
            score += 1.5
        if 50 <= value <= 3000:
            score += 0.8
        if value >= 100000:
            score -= 4.0

        if "%" in normalized_context:
            score -= 3.5
        if DATE_PATTERN.search(normalized_context):
            score -= 2.5
        if len(digits_only) >= 7:
            score -= 5.0

        confidence = min(
            0.999,
            max(0.05, 0.32 + token.confidence * 0.5 + min(score / 13, 0.2)),
        )
        return PriceCandidate(
            value=round(value, 2),
            score=score,
            confidence=confidence,
            source_text=matched_text,
            variant_name=token.variant_name,
            engine_name=token.engine_name,
        )

    def _looks_like_product_size(self, text: str) -> bool:
        normalized = self._normalize_text(text or "")
        if not normalized:
            return False

        compact = normalized.replace(" ", "")
        return bool(PRODUCT_UNIT_PATTERN.search(normalized) or PRODUCT_UNIT_PATTERN.search(compact))

    def _parse_price_value(self, raw: str) -> Optional[float]:
        numeric = raw.replace(" ", "").replace(",", ".")
        try:
            value = float(numeric)
        except ValueError:
            return None

        if value <= 0:
            return None

        return value

    def _normalize_text(self, text: str) -> str:
        cleaned = " ".join(text.strip().split())
        if not cleaned:
            return ""

        replacements = {
            "О": "0",
            "o": "0",
            "O": "0",
            "I": "1",
            "l": "1",
            "|": "1",
            "S": "5",
            "Б": "6",
            "B": "8",
        }

        chars: list[str] = []
        for index, char in enumerate(cleaned):
            prev_char = cleaned[index - 1] if index > 0 else ""
            next_char = cleaned[index + 1] if index + 1 < len(cleaned) else ""
            if char in replacements and (prev_char.isdigit() or next_char.isdigit()):
                chars.append(replacements[char])
            else:
                chars.append(char)

        normalized = "".join(chars)
        normalized = normalized.replace(" ,", ",").replace(" .", ".")
        return normalized

    def _ensure_bgr(self, image):
        import cv2

        if len(image.shape) == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        return image


ocr_processor = OCRProcessor()
