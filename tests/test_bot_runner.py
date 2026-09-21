import unittest

from app.bot_runner import TelegramBotRunner


class FakeTelegram:
    def __init__(self) -> None:
        self.sent = []

    def send_message(self, chat_id, message):
        self.sent.append((chat_id, message))


class FakeChatbot:
    def handle_text(self, text):
        return f"respuesta: {text}"


class BotRunnerTests(unittest.TestCase):
    def test_update_is_answered_in_the_same_chat(self) -> None:
        telegram = FakeTelegram()
        runner = TelegramBotRunner(telegram, FakeChatbot())
        next_offset = runner.process_update(
            {"update_id": 41, "message": {"chat": {"id": 777}, "text": "/precio Papaya"}}
        )
        self.assertEqual(next_offset, 42)
        self.assertEqual(telegram.sent, [(777, "respuesta: /precio Papaya")])


if __name__ == "__main__":
    unittest.main()
