from __future__ import annotations

import json
import os
from typing import Callable
from urllib import error, request

from .domain import AnalysisResult
from .prompt import SYSTEM_PROMPT


class OllamaError(RuntimeError):
    pass


Transport = Callable[[str, bytes, dict[str, str], int], dict[str, object]]


class OllamaClient:
    """Cliente de LLM compatible con Ollama local y con APIs OpenAI-compatibles (Groq)."""

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: int = 120,
        transport: Transport | None = None,
        api_key: str | None = None,
        provider: str | None = None,
    ) -> None:
        self.provider = (provider or os.getenv("LLM_PROVIDER", "ollama")).strip().lower()
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.api_key = (api_key or os.getenv("GROQ_API_KEY", "")).strip()
        self._transport = transport or self._post_json

        if self.provider == "groq":
            if not self.api_key:
                raise OllamaError(
                    "LLM_PROVIDER=groq requiere GROQ_API_KEY. "
                    "Obten una clave gratuita en https://console.groq.com"
                )
            self.base_url = "https://api.groq.com/openai/v1"
            if self.model in {"gemma4:e2b-it-qat", "gemma4:e2b", ""}:
                self.model = os.getenv("GROQ_MODEL", "gemma2-9b-it")

    def generate_alert(self, analysis: AnalysisResult) -> str:
        facts = analysis.to_dict()
        user_content = (
            "Redacta la alerta solo con este JSON:\n"
            + json.dumps(facts, ensure_ascii=False, separators=(",", ":"))
        )
        content = self._chat(
            system=SYSTEM_PROMPT,
            user=user_content,
            max_tokens=220,
            json_schema={
                "type": "object",
                "properties": {"mensaje": {"type": "string"}},
                "required": ["mensaje"],
                "additionalProperties": False,
            },
        )
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return content

        generated = parsed.get("mensaje") if isinstance(parsed, dict) else None
        if not isinstance(generated, str) or not generated.strip():
            raise OllamaError("El modelo no genero el campo mensaje")
        return generated.strip()

    def classify_question(self, question: str, products: tuple[str, ...]) -> dict[str, object]:
        allowed_intents = [
            "PRECIO",
            "VARIACION",
            "HISTORIAL",
            "PRODUCTOS",
            "ALERTA",
            "AYUDA",
            "FUERA_DE_ALCANCE",
        ]
        system = (
            "Clasifica preguntas para un bot de precios agricolas. "
            "No respondas la pregunta. Devuelve solamente el JSON solicitado. "
            "El producto debe ser uno de la lista o null. Los temas ajenos son "
            "FUERA_DE_ALCANCE."
        )
        user = json.dumps(
            {"pregunta": question, "productos_permitidos": list(products)},
            ensure_ascii=False,
        )
        content = self._chat(
            system=system,
            user=user,
            max_tokens=120,
            json_schema={
                "type": "object",
                "properties": {
                    "intencion": {"type": "string", "enum": allowed_intents},
                    "producto": {"type": ["string", "null"]},
                    "meses": {"type": ["integer", "null"], "minimum": 1, "maximum": 60},
                    "umbral": {"type": ["number", "null"], "minimum": 0, "maximum": 100},
                },
                "required": ["intencion", "producto", "meses", "umbral"],
                "additionalProperties": False,
            },
        )
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise OllamaError("El modelo devolvio una clasificacion invalida") from exc
        if not isinstance(parsed, dict) or parsed.get("intencion") not in allowed_intents:
            raise OllamaError("El modelo devolvio una intencion no permitida")
        return parsed

    def _chat(
        self,
        system: str,
        user: str,
        max_tokens: int,
        json_schema: dict[str, object],
    ) -> str:
        if self.provider == "groq":
            return self._chat_openai_compatible(system, user, max_tokens, json_schema)
        return self._chat_ollama(system, user, max_tokens, json_schema)

    def _chat_ollama(
        self,
        system: str,
        user: str,
        max_tokens: int,
        json_schema: dict[str, object],
    ) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "think": False,
            "keep_alive": "10m",
            "options": {
                "temperature": 0,
                "num_ctx": 2048,
                "num_predict": max_tokens,
            },
            "format": json_schema,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        response = self._transport(
            f"{self.base_url}/api/chat",
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            {"Content-Type": "application/json"},
            self.timeout_seconds,
        )
        message = response.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise OllamaError("Ollama devolvio una respuesta sin contenido")
        return message["content"].strip()

    def _chat_openai_compatible(
        self,
        system: str,
        user: str,
        max_tokens: int,
        json_schema: dict[str, object],
    ) -> str:
        payload: dict[str, object] = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        response = self._transport(
            f"{self.base_url}/chat/completions",
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers,
            self.timeout_seconds,
        )
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise OllamaError("La API no devolvio choices")
        first = choices[0]
        if not isinstance(first, dict):
            raise OllamaError("Formato de respuesta inesperado")
        message = first.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise OllamaError("La API devolvio una respuesta sin contenido")
        return message["content"].strip()

    @staticmethod
    def _post_json(
        url: str,
        data: bytes,
        headers: dict[str, str],
        timeout: int,
    ) -> dict[str, object]:
        http_request = request.Request(
            url,
            data=data,
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8")[:300]
            except Exception:
                pass
            raise OllamaError(
                f"Error HTTP {exc.code} al llamar al modelo: {detail or exc.reason}"
            ) from exc
        except (error.URLError, TimeoutError) as exc:
            raise OllamaError("No se pudo obtener una respuesta del modelo") from exc

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise OllamaError("El modelo devolvio JSON invalido") from exc
        if not isinstance(parsed, dict):
            raise OllamaError("El modelo devolvio un formato inesperado")
        return parsed