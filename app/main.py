from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import json
import sys

from .agent import PriceMonitorAgent
from .analysis import PriceAnalyzer
from .config import ConfigurationError, load_settings
from .dataset import PriceRepository
from .domain import DataError
from .ollama_client import OllamaClient
from .telegram_client import TelegramClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Monitor de precios agricolas de Piura")
    parser.add_argument("--producto", help="Producto exacto o texto de busqueda")
    parser.add_argument("--umbral", help="Umbral porcentual de 0 a 100")
    parser.add_argument(
        "--simular",
        action="store_true",
        help="No envia Telegram aunque existan credenciales",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings()
        threshold = Decimal(args.umbral) if args.umbral is not None else settings.alert_threshold_pct
        repository = PriceRepository(settings.dataset_path)
        agent = PriceMonitorAgent(
            repository=repository,
            analyzer=PriceAnalyzer(),
            ollama=OllamaClient(
                settings.ollama_base_url,
                settings.ollama_model,
                settings.ollama_timeout_seconds,
            ),
            telegram=TelegramClient(
                settings.telegram_bot_token,
                settings.telegram_chat_id,
                dry_run=args.simular or settings.dry_run,
                timeout_seconds=settings.telegram_timeout_seconds,
            ),
        )
        result = agent.run(args.producto or settings.demo_product, threshold)
    except (ConfigurationError, DataError, InvalidOperation, ValueError) as exc:
        result = {"estado": "ERROR_CONFIGURACION", "mensaje": str(exc)}

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("estado") in {"ALERTA_PROCESADA", "SIN_ALERTA"} else 2


if __name__ == "__main__":
    sys.exit(main())
