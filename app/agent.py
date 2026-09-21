from __future__ import annotations

from decimal import Decimal
import re

from .analysis import PriceAnalyzer
from .dataset import PriceRepository, normalize_text
from .domain import AnalysisResult, DataError
from .ollama_client import OllamaClient, OllamaError
from .telegram_client import TelegramClient, TelegramError


FORBIDDEN_CAUSAL_PHRASES = {
    "debido a",
    "causado por",
    "probablemente",
    "escasez",
    "inflacion",
    "clima",
    "demanda",
    "oferta",
    "recomendamos",
    "deberia comprar",
    "deberia vender",
}


def _format_price(value: Decimal) -> str:
    return f"{value:.2f}"


def _format_date(value) -> str:
    return value.strftime("%d/%m/%Y")


def safe_message(analysis: AnalysisResult) -> str:
    prices = analysis.prices
    action = {
        "SUBIO": "subio",
        "BAJO": "bajo",
        "SIN_CAMBIO": "no cambio",
    }[analysis.direction]
    return (
        "Alerta de precio agricola - Piura. "
        f"{prices.product} {action} {abs(analysis.variation_pct):.2f}%, "
        f"de {_format_price(prices.previous.wholesale_price)} a "
        f"{_format_price(prices.current.wholesale_price)} por {prices.current.wholesale_unit}, "
        f"entre el {_format_date(prices.previous.registered_at)} y el "
        f"{_format_date(prices.current.registered_at)}. "
        f"El cambio supera el umbral de {analysis.threshold_pct:.2f}%. "
        "Fuente: Gobierno Regional Piura - Mercado Modelo de Piura."
    )


def message_is_safe(message: str, analysis: AnalysisResult) -> bool:
    if not message or len(message) > 600:
        return False
    normalized = normalize_text(message)
    if not normalized.startswith("alerta de precio agricola - piura"):
        return False
    if any(phrase in normalized for phrase in FORBIDDEN_CAUSAL_PHRASES):
        return False

    prices = analysis.prices
    required = [
        normalize_text(prices.product),
        _format_price(prices.previous.wholesale_price),
        _format_price(prices.current.wholesale_price),
        _format_date(prices.previous.registered_at),
        _format_date(prices.current.registered_at),
        f"{abs(analysis.variation_pct):.2f}",
        f"{analysis.threshold_pct:.2f}",
        normalize_text(prices.current.wholesale_unit),
        "gobierno regional piura",
    ]
    if not all(item in normalized for item in required):
        return False

    # Una respuesta general suele contener varias oraciones extras. El limite
    # mantiene la salida como una unica alerta verificable.
    sentence_marks = re.findall(r"(?<!\d)[.!?](?!\d)", message)
    return len(sentence_marks) <= 6


class PriceMonitorAgent:
    def __init__(
        self,
        repository: PriceRepository,
        analyzer: PriceAnalyzer,
        ollama: OllamaClient,
        telegram: TelegramClient,
    ) -> None:
        self.repository = repository
        self.analyzer = analyzer
        self.ollama = ollama
        self.telegram = telegram

    # Estas funciones corresponden al flujo de alerta descrito por los
    # esquemas JSON de app/tool_schemas.py.
    def buscar_productos(self, consulta: str) -> list[str]:
        return self.repository.search_products(consulta)

    def obtener_precios_recientes(self, producto: str):
        return self.repository.get_recent_prices(producto)

    def evaluar_variacion(self, producto: str, umbral_porcentual: Decimal) -> AnalysisResult:
        prices = self.obtener_precios_recientes(producto)
        return self.analyzer.evaluate(prices, umbral_porcentual)

    def enviar_alerta_telegram(
        self, analysis: AnalysisResult, mensaje: str
    ) -> dict[str, object]:
        return self.telegram.send_alert(analysis, mensaje)

    def run(self, product_query: str, threshold_pct: Decimal) -> dict[str, object]:
        tools_used = ["buscar_productos"]
        matches = self.buscar_productos(product_query)
        if not matches:
            return {
                "estado": "PRODUCTO_NO_ENCONTRADO",
                "consulta": product_query,
                "mensaje": "El producto no existe en el dataset de Piura.",
                "herramientas_usadas": tools_used,
            }
        if len(matches) > 1:
            return {
                "estado": "PRODUCTO_AMBIGUO",
                "consulta": product_query,
                "opciones": matches,
                "mensaje": "La consulta coincide con varios productos del dataset.",
                "herramientas_usadas": tools_used,
            }

        product = matches[0]
        tools_used.append("obtener_precios_recientes")
        try:
            prices = self.obtener_precios_recientes(product)
        except DataError as exc:
            return {
                "estado": "DATOS_INSUFICIENTES",
                "producto": product,
                "mensaje": str(exc),
                "herramientas_usadas": tools_used,
            }

        tools_used.append("evaluar_variacion")
        analysis = self.evaluar_variacion(product, threshold_pct)
        if not analysis.is_atypical:
            return {
                "estado": "SIN_ALERTA",
                "analisis": analysis.to_dict(),
                "mensaje": "La variacion no supera el umbral configurado.",
                "herramientas_usadas": tools_used,
            }

        origin = "ollama"
        ai_error = None
        try:
            draft = self.ollama.generate_alert(analysis)
            if not message_is_safe(draft, analysis):
                origin = "plantilla_segura_por_respuesta_no_valida"
                draft = safe_message(analysis)
        except OllamaError:
            origin = "plantilla_segura_por_error_ia"
            ai_error = "El modelo local no estuvo disponible o devolvio un formato invalido."
            draft = safe_message(analysis)

        tools_used.append("enviar_alerta_telegram")
        try:
            notification = self.enviar_alerta_telegram(analysis, draft)
            status = "ALERTA_PROCESADA"
        except TelegramError as exc:
            notification = {"estado": "ERROR", "detalle": str(exc)}
            status = "ERROR_TELEGRAM"

        result: dict[str, object] = {
            "estado": status,
            "analisis": analysis.to_dict(),
            "mensaje": draft,
            "origen_mensaje": origin,
            "notificacion": notification,
            "herramientas_usadas": tools_used,
        }
        if ai_error:
            result["advertencia_ia"] = ai_error
        return result
