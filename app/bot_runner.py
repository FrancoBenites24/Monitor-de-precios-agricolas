from __future__ import annotations

import time

from .chatbot import PriceChatbot
from .telegram_client import TelegramClient, TelegramError


class TelegramBotRunner:
    def __init__(
        self,
        telegram: TelegramClient,
        chatbot: PriceChatbot,
        poll_timeout_seconds: int = 25,
    ) -> None:
        self.telegram = telegram
        self.chatbot = chatbot
        self.poll_timeout_seconds = poll_timeout_seconds

    def process_update(self, update: dict[str, object]) -> int | None:
        update_id = update.get("update_id")
        message = update.get("message")
        if not isinstance(update_id, int) or not isinstance(message, dict):
            return update_id + 1 if isinstance(update_id, int) else None

        chat = message.get("chat")
        text = message.get("text")
        if not isinstance(chat, dict) or not isinstance(chat.get("id"), (str, int)):
            return update_id + 1
        if not isinstance(text, str):
            self.telegram.send_message(chat["id"], "Solo puedo leer mensajes de texto. Usa /ayuda.")
            return update_id + 1

        response = self.chatbot.handle_text(text)
        self.telegram.send_message(chat["id"], response[:4096])
        return update_id + 1

    def run_forever(self) -> None:
        self.telegram.prepare_long_polling()
        print("Bot de Telegram listo para recibir consultas.", flush=True)
        offset = None
        while True:
            try:
                updates = self.telegram.get_updates(offset, self.poll_timeout_seconds)
                for update in updates:
                    next_offset = self.process_update(update)
                    if next_offset is not None:
                        offset = next_offset
            except TelegramError as exc:
                print(f"Telegram temporalmente no disponible: {exc}", flush=True)
                time.sleep(3)
            except Exception:
                print("No se pudo procesar un mensaje. El bot continuara activo.", flush=True)
                time.sleep(1)
