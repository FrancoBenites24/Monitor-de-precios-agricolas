from __future__ import annotations

import json
from typing import Callable
from urllib import error, parse, request

from .domain import AnalysisResult


class TelegramError(RuntimeError):
    pass


Transport = Callable[[str, bytes, int], dict[str, object]]


class TelegramClient:
    def __init__(
        self,
        bot_token: str,
        chat_id: str = "",
        dry_run: bool = True,
        timeout_seconds: int = 20,
        transport: Transport | None = None,
    ) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.dry_run = dry_run
        self.timeout_seconds = timeout_seconds
        self._transport = transport or self._post_form
        self._sent_analysis_ids: set[str] = set()

    def _call(self, method: str, fields: dict[str, object], timeout: int | None = None):
        if not self.bot_token:
            raise TelegramError("Falta TELEGRAM_BOT_TOKEN")
        url = f"https://api.telegram.org/bot{self.bot_token}/{method}"
        encoded = {
            key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
            for key, value in fields.items()
        }
        response = self._transport(
            url,
            parse.urlencode(encoded).encode("utf-8"),
            timeout or self.timeout_seconds,
        )
        if response.get("ok") is not True:
            raise TelegramError(f"Telegram rechazo la operacion {method}")
        return response.get("result")

    def send_message(self, chat_id: str | int, message: str) -> dict[str, object]:
        result = self._call("sendMessage", {"chat_id": chat_id, "text": message})
        return result if isinstance(result, dict) else {"ok": True}

    def get_updates(self, offset: int | None, poll_timeout: int) -> list[dict[str, object]]:
        fields: dict[str, object] = {
            "timeout": poll_timeout,
            "allowed_updates": ["message"],
        }
        if offset is not None:
            fields["offset"] = offset
        result = self._call("getUpdates", fields, poll_timeout + 10)
        if not isinstance(result, list):
            raise TelegramError("Telegram devolvio actualizaciones invalidas")
        return [item for item in result if isinstance(item, dict)]

    def prepare_long_polling(self) -> None:
        self._call("deleteWebhook", {"drop_pending_updates": False})
        commands = [
            {"command": "precio", "description": "Ultimo precio de un producto"},
            {"command": "variacion", "description": "Cambio entre los dos ultimos precios"},
            {"command": "historial", "description": "Resumen historico de un producto"},
            {"command": "alerta", "description": "Evaluar una variacion atipica"},
            {"command": "productos", "description": "Lista de productos disponibles"},
            {"command": "ayuda", "description": "Mostrar ejemplos de uso"},
        ]
        self._call("setMyCommands", {"commands": commands})

    def send_alert(self, analysis: AnalysisResult, message: str) -> dict[str, object]:
        if not analysis.is_atypical:
            raise TelegramError("No se permite enviar una alerta para una variacion normal")
        if analysis.analysis_id in self._sent_analysis_ids:
            return {"estado": "DUPLICADA_OMITIDA", "analysis_id": analysis.analysis_id}

        if self.dry_run:
            self._sent_analysis_ids.add(analysis.analysis_id)
            return {
                "estado": "SIMULADA",
                "analysis_id": analysis.analysis_id,
                "mensaje": message,
            }

        if not self.bot_token or not self.chat_id:
            raise TelegramError("Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID")

        self.send_message(self.chat_id, message)

        self._sent_analysis_ids.add(analysis.analysis_id)
        return {"estado": "ENVIADA", "analysis_id": analysis.analysis_id}

    @staticmethod
    def _post_form(url: str, data: bytes, timeout: int) -> dict[str, object]:
        http_request = request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
        except (error.HTTPError, error.URLError, TimeoutError) as exc:
            raise TelegramError("No se pudo conectar con Telegram") from exc

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise TelegramError("Telegram devolvio una respuesta invalida") from exc
        if not isinstance(parsed, dict):
            raise TelegramError("Telegram devolvio un formato inesperado")
        return parsed
