from __future__ import annotations

import json
from typing import Callable
from urllib import error, request

from .domain import AnalysisResult
from .prompt import SYSTEM_PROMPT


class OllamaError(RuntimeError):
    pass


Transport = Callable[[str, bytes, int], dict[str, object]]


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: int = 120,
        transport: Transport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._transport = transport or self._post_json

    def generate_alert(self, analysis: AnalysisResult) -> str:
        facts = analysis.to_dict()
        payload = {
            "model": self.model,
            "stream": False,
            "think": False,
            "keep_alive": "10m",
            "options": {
                "temperature": 0,
                "num_ctx": 2048,
                "num_predict": 220,
            },
            "format": {
                "type": "object",
                "properties": {"mensaje": {"type": "string"}},
                "required": ["mensaje"],
                "additionalProperties": False,
            },
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": "Redacta la alerta solo con este JSON:\n"
                    + json.dumps(facts, ensure_ascii=False, separators=(",", ":")),
                },
            ],
        }

        response = self._transport(
            f"{self.base_url}/api/chat",
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            self.timeout_seconds,
        )
        message = response.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise OllamaError("Ollama devolvio una respuesta sin contenido")

        content = message["content"].strip()
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return content

        generated = parsed.get("mensaje") if isinstance(parsed, dict) else None
        if not isinstance(generated, str) or not generated.strip():
            raise OllamaError("Ollama no genero el campo mensaje")
        return generated.strip()

    @staticmethod
    def _post_json(url: str, data: bytes, timeout: int) -> dict[str, object]:
        http_request = request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
        except (error.HTTPError, error.URLError, TimeoutError) as exc:
            raise OllamaError("No se pudo obtener una respuesta del modelo local") from exc

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama devolvio JSON invalido") from exc
        if not isinstance(parsed, dict):
            raise OllamaError("Ollama devolvio un formato inesperado")
        return parsed
