from decimal import Decimal
from pathlib import Path
import unittest

from app.agent import safe_message
from app.analysis import PriceAnalyzer
from app.chatbot import PriceChatbot
from app.dataset import PriceRepository
from app.intent import QuestionInterpreter


ROOT = Path(__file__).resolve().parent.parent


class FakeOllama:
    def __init__(self) -> None:
        self.classify_calls = 0
        self.alert_calls = 0

    def classify_question(self, question, products):
        self.classify_calls += 1
        return {
            "intencion": "FUERA_DE_ALCANCE",
            "producto": None,
            "meses": None,
            "umbral": None,
        }

    def generate_alert(self, analysis):
        self.alert_calls += 1
        return safe_message(analysis)


class ChatbotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repository = PriceRepository(ROOT / "data" / "mimercado_dataset.csv")

    def build_chatbot(self):
        ollama = FakeOllama()
        chatbot = PriceChatbot(
            repository=self.repository,
            analyzer=PriceAnalyzer(),
            interpreter=QuestionInterpreter(self.repository, ollama),
            ollama=ollama,
            default_threshold=Decimal("5"),
        )
        return chatbot, ollama

    def test_natural_price_question_is_answered_without_ai_classification(self) -> None:
        chatbot, ollama = self.build_chatbot()
        response = chatbot.handle_text("¿Cuanto cuesta la papaya?")
        self.assertIn("Papaya", response)
        self.assertIn("2.40", response)
        self.assertIn("13/03/2026", response)
        self.assertEqual(ollama.classify_calls, 0)

    def test_history_question_returns_dataset_summary(self) -> None:
        chatbot, _ = self.build_chatbot()
        response = chatbot.handle_text("¿Cual fue el precio de la papaya en los ultimos anos?")
        self.assertIn("2024-01-08", response)
        self.assertIn("2026-03-13", response)
        self.assertIn("Promedios anuales", response)

    def test_products_command_fits_in_one_telegram_message(self) -> None:
        chatbot, _ = self.build_chatbot()
        response = chatbot.handle_text("/productos")
        self.assertIn("Papaya", response)
        self.assertLess(len(response), 4096)

    def test_ambiguous_product_lists_real_options(self) -> None:
        chatbot, _ = self.build_chatbot()
        response = chatbot.handle_text("precio de papa")
        self.assertIn("Papa amarilla", response)
        self.assertIn("Papa canchan", response)
        self.assertNotIn("Papaya\n", response)

    def test_out_of_scope_question_never_returns_general_ai_text(self) -> None:
        chatbot, ollama = self.build_chatbot()
        response = chatbot.handle_text("Cuentame un chiste")
        self.assertEqual(
            response,
            "Solo puedo consultar precios agricolas del dataset de Piura. Usa /ayuda para ver ejemplos.",
        )
        self.assertEqual(ollama.classify_calls, 1)

    def test_alert_command_uses_ai_only_for_atypical_result(self) -> None:
        chatbot, ollama = self.build_chatbot()
        response = chatbot.handle_text("/alerta Papaya 5")
        self.assertIn("9.09%", response)
        self.assertEqual(ollama.alert_calls, 1)


if __name__ == "__main__":
    unittest.main()
