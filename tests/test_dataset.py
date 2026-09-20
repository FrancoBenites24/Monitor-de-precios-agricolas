from decimal import Decimal
from pathlib import Path
import unittest

from app.analysis import PriceAnalyzer
from app.dataset import PriceRepository


ROOT = Path(__file__).resolve().parent.parent


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repository = PriceRepository(ROOT / "data" / "mimercado_dataset.csv")

    def test_real_dataset_shape(self) -> None:
        self.assertEqual(self.repository.row_count, 7464)
        self.assertEqual(self.repository.product_count, 51)

    def test_search_ignores_case_and_accents(self) -> None:
        self.assertEqual(self.repository.search_products("  AJI   ESCABECHE "), ["Aji escabeche"])

    def test_partial_search_can_be_ambiguous(self) -> None:
        self.assertEqual(
            self.repository.search_products("papa"),
            ["Papa amarilla", "Papa canchan", "Papaya"],
        )

    def test_papaya_uses_two_latest_valid_prices(self) -> None:
        prices = self.repository.get_recent_prices("Papaya")
        self.assertEqual(prices.previous.registered_at.isoformat(), "2026-03-11")
        self.assertEqual(prices.previous.wholesale_price, Decimal("2.2"))
        self.assertEqual(prices.current.registered_at.isoformat(), "2026-03-13")
        self.assertEqual(prices.current.wholesale_price, Decimal("2.4"))
        self.assertEqual(prices.current.wholesale_unit, "KILOGRAMO")

    def test_papaya_variation_is_9_09_percent(self) -> None:
        prices = self.repository.get_recent_prices("Papaya")
        result = PriceAnalyzer().evaluate(prices, Decimal("5"))
        self.assertEqual(result.variation_pct, Decimal("9.09"))
        self.assertTrue(result.is_atypical)
        self.assertEqual(result.direction, "SUBIO")


if __name__ == "__main__":
    unittest.main()
