from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re

from .dataset import PriceRepository, normalize_text
from .ollama_client import OllamaClient, OllamaError


INTENTS = {
    "PRECIO",
    "VARIACION",
    "HISTORIAL",
    "PRODUCTOS",
    "ALERTA",
    "AYUDA",
    "FUERA_DE_ALCANCE",
    "AMBIGUO",
}


@dataclass(frozen=True)
class QuestionIntent:
    kind: str
    product: str | None = None
    candidates: tuple[str, ...] = ()
    months: int | None = None
    threshold: Decimal | None = None


class QuestionInterpreter:
    def __init__(self, repository: PriceRepository, ollama: OllamaClient) -> None:
        self.repository = repository
        self.ollama = ollama

    def interpret(self, text: str) -> QuestionIntent:
        clean = text.strip()
        if not clean:
            return QuestionIntent("AYUDA")
        if clean.startswith("/"):
            return self._command(clean)

        normalized = normalize_text(clean)
        kind = self._detect_kind(normalized)
        if kind in {"PRODUCTOS", "AYUDA"}:
            return QuestionIntent(kind)

        matches = self._products_mentioned(normalized)
        if not matches:
            matches = self._products_from_keywords(normalized)
        resolved = self._resolve(matches)
        if resolved is not None:
            if resolved.kind == "AMBIGUO":
                return resolved
            return QuestionIntent(
                kind or "PRECIO",
                product=resolved.product,
                months=self._extract_months(normalized),
                threshold=self._extract_threshold(normalized),
            )

        return self._classify_with_ai(clean)

    def _command(self, text: str) -> QuestionIntent:
        command_part, _, arguments = text.partition(" ")
        command = command_part.split("@", 1)[0].lower()
        arguments = arguments.strip()
        if command in {"/start", "/ayuda", "/help"}:
            return QuestionIntent("AYUDA")
        if command == "/productos":
            return QuestionIntent("PRODUCTOS")

        command_intents = {
            "/precio": "PRECIO",
            "/variacion": "VARIACION",
            "/historial": "HISTORIAL",
            "/alerta": "ALERTA",
        }
        kind = command_intents.get(command)
        if kind is None:
            return QuestionIntent("FUERA_DE_ALCANCE")
        if not arguments:
            return QuestionIntent(kind)

        months = None
        threshold = None
        product_query = arguments
        tail_match = re.match(r"^(.*)\s+([0-9]+(?:[.,][0-9]+)?)$", arguments)
        if tail_match:
            possible_product = tail_match.group(1).strip()
            possible_number = tail_match.group(2).replace(",", ".")
            if self.repository.search_products(possible_product):
                product_query = possible_product
                if kind == "HISTORIAL":
                    months = int(Decimal(possible_number))
                elif kind == "ALERTA":
                    threshold = Decimal(possible_number)

        resolved = self._resolve(self.repository.search_products(product_query))
        if resolved is None:
            return QuestionIntent(kind)
        if resolved.kind == "AMBIGUO":
            return resolved
        return QuestionIntent(kind, resolved.product, months=months, threshold=threshold)

    @staticmethod
    def _detect_kind(normalized: str) -> str | None:
        if any(word in normalized for word in ("productos", "lista", "catalogo")):
            return "PRODUCTOS"
        if any(word in normalized for word in ("ayuda", "como usar", "que puedes hacer")):
            return "AYUDA"
        if any(word in normalized for word in ("historial", "historico", "evolucion", "promedio", "minimo", "maximo", "ultimos meses", "ultimo ano", "ultimos anos")):
            return "HISTORIAL"
        if any(word in normalized for word in ("variacion", "cambio", "subio", "bajo")):
            return "VARIACION"
        if any(word in normalized for word in ("alerta", "avisame", "notifica")):
            return "ALERTA"
        if any(word in normalized for word in ("precio", "cuesta", "valor", "cuanto esta")):
            return "PRECIO"
        return None

    def _products_mentioned(self, normalized: str) -> list[str]:
        matches = []
        for product in self.repository.products:
            normalized_product = normalize_text(product)
            if re.search(rf"(?<!\w){re.escape(normalized_product)}(?!\w)", normalized):
                matches.append(product)
        return matches

    def _products_from_keywords(self, normalized: str) -> list[str]:
        ignored = {
            "a", "al", "de", "del", "el", "en", "la", "las", "los", "me", "mi", "por",
            "precio", "cuanto", "cuesta", "esta", "valor", "dame", "muestra", "mostrar",
            "historial", "historico", "evolucion", "variacion", "cambio", "subio", "bajo",
            "alerta", "avisame", "notifica", "ultimo", "ultimos", "mes", "meses", "ano", "anos",
        }
        tokens = [
            token
            for token in re.findall(r"[a-z0-9]+", normalized)
            if token not in ignored and not token.isdigit()
        ]
        if not tokens:
            return []
        matches = []
        for product in self.repository.products:
            product_words = set(re.findall(r"[a-z0-9]+", normalize_text(product)))
            if all(token in product_words for token in tokens):
                matches.append(product)
        return matches

    @staticmethod
    def _resolve(matches: list[str]) -> QuestionIntent | None:
        unique = tuple(dict.fromkeys(matches))
        if not unique:
            return None
        if len(unique) > 1:
            return QuestionIntent("AMBIGUO", candidates=unique)
        return QuestionIntent("PRECIO", product=unique[0])

    @staticmethod
    def _extract_months(normalized: str) -> int | None:
        month_match = re.search(r"(\d+)\s*mes", normalized)
        if month_match:
            return min(max(int(month_match.group(1)), 1), 60)
        year_match = re.search(r"(\d+)\s*ano", normalized)
        if year_match:
            return min(max(int(year_match.group(1)) * 12, 1), 60)
        if "ultimo ano" in normalized:
            return 12
        return None

    @staticmethod
    def _extract_threshold(normalized: str) -> Decimal | None:
        match = re.search(r"(?:umbral\s*)?(\d+(?:[.,]\d+)?)\s*%", normalized)
        if not match:
            return None
        try:
            value = Decimal(match.group(1).replace(",", "."))
        except InvalidOperation:
            return None
        return value if Decimal("0") <= value <= Decimal("100") else None

    def _classify_with_ai(self, text: str) -> QuestionIntent:
        try:
            result = self.ollama.classify_question(text, self.repository.products)
        except OllamaError:
            return QuestionIntent("FUERA_DE_ALCANCE")

        kind = str(result.get("intencion", "FUERA_DE_ALCANCE"))
        if kind not in INTENTS:
            return QuestionIntent("FUERA_DE_ALCANCE")
        if kind in {"PRODUCTOS", "AYUDA", "FUERA_DE_ALCANCE"}:
            return QuestionIntent(kind)

        product_value = result.get("producto")
        if not isinstance(product_value, str):
            return QuestionIntent(kind)
        resolved = self._resolve(self.repository.search_products(product_value))
        if resolved is None or resolved.kind == "AMBIGUO":
            return resolved or QuestionIntent(kind)

        months_value = result.get("meses")
        threshold_value = result.get("umbral")
        months = months_value if isinstance(months_value, int) and 1 <= months_value <= 60 else None
        threshold = None
        if isinstance(threshold_value, (int, float)) and 0 <= threshold_value <= 100:
            threshold = Decimal(str(threshold_value))
        return QuestionIntent(kind, resolved.product, months=months, threshold=threshold)
