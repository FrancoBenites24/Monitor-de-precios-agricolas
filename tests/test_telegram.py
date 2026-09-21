from decimal import Decimal
from pathlib import Path
import unittest

from app.agent import safe_message
from app.analysis import PriceAnalyzer
from app.dataset import PriceRepository
from app.telegram_client import TelegramClient, TelegramError


ROOT = Path(__file__).resolve().parent.parent


class TelegramTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        repository = PriceRepository(ROOT / "data" / "mimercado_dataset.csv")
        cls.atypical = PriceAnalyzer().evaluate(repository.get_recent_prices("Papaya"), Decimal("5"))
        cls.normal = PriceAnalyzer().evaluate(
            repository.get_recent_prices("Aji escabeche"), Decimal("5")
        )

    def test_real_mode_uses_configured_chat_without_exposing_it_to_ai(self) -> None:
        requests = []

        def fake_transport(url, data, timeout):
            requests.append((url, data.decode("utf-8"), timeout))
            return {"ok": True}

        client = TelegramClient(
            "secret-token",
            "12345",
            dry_run=False,
            transport=fake_transport,
        )
        result = client.send_alert(self.atypical, safe_message(self.atypical))
        self.assertEqual(result["estado"], "ENVIADA")
        self.assertEqual(len(requests), 1)
        self.assertIn("chat_id=12345", requests[0][1])

    def test_normal_analysis_cannot_be_sent(self) -> None:
        client = TelegramClient("token", "chat", dry_run=False, transport=lambda *_: {"ok": True})
        with self.assertRaises(TelegramError):
            client.send_alert(self.normal, "mensaje")

    def test_duplicate_analysis_is_omitted(self) -> None:
        client = TelegramClient("", "", dry_run=True)
        first = client.send_alert(self.atypical, safe_message(self.atypical))
        second = client.send_alert(self.atypical, safe_message(self.atypical))
        self.assertEqual(first["estado"], "SIMULADA")
        self.assertEqual(second["estado"], "DUPLICADA_OMITIDA")

    def test_long_polling_uses_offset_and_message_updates_only(self) -> None:
        requests = []

        def fake_transport(url, data, timeout):
            requests.append((url, data.decode("utf-8"), timeout))
            return {"ok": True, "result": [{"update_id": 9, "message": {}}]}

        client = TelegramClient("secret-token", transport=fake_transport)
        updates = client.get_updates(8, 25)
        self.assertEqual(updates[0]["update_id"], 9)
        self.assertIn("offset=8", requests[0][1])
        self.assertIn("allowed_updates", requests[0][1])
        self.assertEqual(requests[0][2], 35)

    def test_startup_removes_webhook_and_registers_commands(self) -> None:
        methods = []

        def fake_transport(url, data, timeout):
            methods.append(url.rsplit("/", 1)[-1])
            return {"ok": True, "result": True}

        TelegramClient("secret-token", transport=fake_transport).prepare_long_polling()
        self.assertEqual(methods, ["deleteWebhook", "setMyCommands"])


if __name__ == "__main__":
    unittest.main()
