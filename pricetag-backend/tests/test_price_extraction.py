import unittest

from app.services.ml_service import OCRProcessor, OCRToken


class PriceExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.processor = OCRProcessor()

    def test_extract_decimal_price_with_currency_hint(self) -> None:
        token = OCRToken(
            text="Цена 129.90 ₽",
            confidence=0.98,
            center_x=100,
            center_y=120,
            width=180,
            height=24,
            variant_name="test",
            engine_name="tesseract",
        )
        candidate = self.processor._score_candidate("129.90", token, token.text, 500, 250)
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.value, 129.90)

    def test_extract_integer_price_with_ruble_hint(self) -> None:
        token = OCRToken(
            text="349 руб",
            confidence=0.91,
            center_x=100,
            center_y=120,
            width=120,
            height=22,
            variant_name="test",
            engine_name="tesseract",
        )
        candidate = self.processor._score_candidate("349", token, token.text, 500, 250)
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.value, 349.0)

    def test_normalization_fixes_common_ocr_confusions(self) -> None:
        normalized = self.processor._normalize_text("1O9,9O ₽")
        self.assertEqual(normalized, "109,90 ₽")

    def test_discount_layout_prefers_composed_sale_price(self) -> None:
        tokens = [
            OCRToken(
                text="обычная цена",
                confidence=0.92,
                center_x=420,
                center_y=40,
                width=140,
                height=24,
                variant_name="tag-general:general",
                engine_name="tesseract",
            ),
            OCRToken(
                text="39900",
                confidence=0.86,
                center_x=460,
                center_y=70,
                width=180,
                height=52,
                variant_name="tag-general:general",
                engine_name="tesseract",
            ),
            OCRToken(
                text="-56%",
                confidence=0.9,
                center_x=120,
                center_y=180,
                width=170,
                height=90,
                variant_name="tag-general:general",
                engine_name="tesseract",
            ),
            OCRToken(
                text="72",
                confidence=0.98,
                center_x=280,
                center_y=180,
                width=150,
                height=80,
                variant_name="sale-price-roi",
                engine_name="paddle",
            ),
            OCRToken(
                text="90",
                confidence=0.98,
                center_x=410,
                center_y=155,
                width=70,
                height=38,
                variant_name="sale-price-roi",
                engine_name="paddle",
            ),
            OCRToken(
                text="150г",
                confidence=0.9,
                center_x=330,
                center_y=60,
                width=85,
                height=22,
                variant_name="tag-general:general",
                engine_name="tesseract",
            ),
        ]

        candidate = self.processor._pick_best_price(tokens, 600, 320)

        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.value, 172.90)


if __name__ == "__main__":
    unittest.main()
