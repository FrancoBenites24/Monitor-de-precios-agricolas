from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ConfigurationError(ValueError):
    pass


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def _as_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "si", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"Valor booleano invalido: {value}")


@dataclass(frozen=True)
class Settings:
    dataset_path: Path
    alert_threshold_pct: Decimal
    ollama_base_url: str
    ollama_model: str
    ollama_timeout_seconds: int
    telegram_bot_token: str
    telegram_chat_id: str
    telegram_timeout_seconds: int
    dry_run: bool
    demo_product: str


def load_settings(env_file: Path | None = None) -> Settings:
    _load_env_file(env_file or PROJECT_ROOT / ".env")

    raw_dataset = os.getenv("DATASET_PATH", "data/mimercado_dataset.csv")
    dataset_path = Path(raw_dataset)
    if not dataset_path.is_absolute():
        dataset_path = PROJECT_ROOT / dataset_path

    try:
        threshold = Decimal(os.getenv("ALERT_THRESHOLD_PCT", "5.0"))
    except InvalidOperation as exc:
        raise ConfigurationError("ALERT_THRESHOLD_PCT debe ser numerico") from exc
    if threshold < 0 or threshold > 100:
        raise ConfigurationError("ALERT_THRESHOLD_PCT debe estar entre 0 y 100")

    try:
        ollama_timeout = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
        telegram_timeout = int(os.getenv("TELEGRAM_TIMEOUT_SECONDS", "20"))
    except ValueError as exc:
        raise ConfigurationError("Los tiempos de espera deben ser numeros enteros") from exc

    return Settings(
        dataset_path=dataset_path,
        alert_threshold_pct=threshold,
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        ollama_model=os.getenv("OLLAMA_MODEL", "gemma4:e2b-it-qat"),
        ollama_timeout_seconds=ollama_timeout,
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
        telegram_timeout_seconds=telegram_timeout,
        dry_run=_as_bool(os.getenv("DRY_RUN", "true")),
        demo_product=os.getenv("DEMO_PRODUCT", "Papaya").strip() or "Papaya",
    )
