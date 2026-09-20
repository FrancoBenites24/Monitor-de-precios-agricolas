from decimal import Decimal
from pathlib import Path
import unittest

from app.agent import PriceMonitorAgent, safe_message
from app.analysis import PriceAnalyzer
from app.dataset import PriceRepository
from app.telegram_client import TelegramClient


ROOT = Path(__file__).resolve().parent.parent


class FakeOllama:
    def __init__(self, mode: str = "valid") -> None:
        self.mode = mode
        self.calls = 0

    def generate_alert(self, analysis):
        self.calls += 1
        if self.mode == "unsafe":
            return "Alerta de precio agricola - Piura. Subio debido al clima y la escasez."
        return safe_message(analysis)


class AgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repository = PriceRepository(ROOT / "data" / "mimercado_dataset.csv")

    def build_agent(self, ollama: FakeOllama) -> PriceMonitorAgent:
        return PriceMonitorAgent(
            repository=self.repository,
            analyzer=PriceAnalyzer(),
            ollama=ollama,
            telegram=TelegramClient("", "", dry_run=True),
        )

    def test_unknown_product_never_calls_ai(self) -> None:
        ollama = FakeOllama()
        result = self.build_agent(ollama).run("cuentame un chiste", Decimal("5"))
        self.assertEqual(result["estado"], "PRODUCTO_NO_ENCONTRADO")
        self.assertEqual(ollama.calls, 0)

    def test_normal_variation_never_calls_ai_or_telegram(self) -> None:
        ollama = FakeOllama()
        result = self.build_agent(ollama).run("Aji escabeche", Decimal("5"))
        self.assertEqual(result["estado"], "SIN_ALERTA")
        self.assertEqual(ollama.calls, 0)
        self.assertEqual(result["herramientas_usadas"][-1], "evaluar_variacion")

    def test_papaya_generates_simulated_alert(self) -> None:
        ollama = FakeOllama()
        result = self.build_agent(ollama).run("Papaya", Decimal("5"))
        self.assertEqual(result["estado"], "ALERTA_PROCESADA")
        self.assertEqual(result["origen_mensaje"], "ollama")
        self.assertEqual(result["notificacion"]["estado"], "SIMULADA")
        self.assertEqual(ollama.calls, 1)
        self.assertEqual(
            result["herramientas_usadas"],
            [
                "buscar_productos",
                "obtener_precios_recientes",
                "evaluar_variacion",
                "enviar_alerta_telegram",
            ],
        )

    def test_unsafe_ai_message_is_replaced(self) -> None:
        result = self.build_agent(FakeOllama("unsafe")).run("Papaya", Decimal("5"))
        self.assertEqual(result["origen_mensaje"], "plantilla_segura_por_respuesta_no_valida")
        self.assertNotIn("clima", result["mensaje"].lower())
        self.assertIn("9.09%", result["mensaje"])


if __name__ == "__main__":
    unittest.main()
