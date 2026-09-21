from __future__ import annotations

from .analysis import PriceAnalyzer
from .bot_runner import TelegramBotRunner
from .chatbot import PriceChatbot
from .config import ConfigurationError, load_settings
from .dataset import PriceRepository
from .domain import DataError
from .intent import QuestionInterpreter
from .ollama_client import OllamaClient
from .telegram_client import TelegramClient


def main() -> int:
    try:
        settings = load_settings()
        if not settings.telegram_bot_token:
            raise ConfigurationError("Falta TELEGRAM_BOT_TOKEN en .env")

        repository = PriceRepository(settings.dataset_path)
        ollama = OllamaClient(
            settings.ollama_base_url,
            settings.ollama_model,
            settings.ollama_timeout_seconds,
        )
        telegram = TelegramClient(
            settings.telegram_bot_token,
            timeout_seconds=settings.telegram_timeout_seconds,
            dry_run=False,
        )
        chatbot = PriceChatbot(
            repository=repository,
            analyzer=PriceAnalyzer(),
            interpreter=QuestionInterpreter(repository, ollama),
            ollama=ollama,
            default_threshold=settings.alert_threshold_pct,
        )
        TelegramBotRunner(
            telegram,
            chatbot,
            settings.telegram_poll_timeout_seconds,
        ).run_forever()
    except (ConfigurationError, DataError) as exc:
        print(f"Error de configuracion: {exc}", flush=True)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
