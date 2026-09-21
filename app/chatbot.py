from __future__ import annotations

from decimal import Decimal

from .agent import message_is_safe, safe_message
from .analysis import PriceAnalyzer
from .dataset import PriceRepository
from .domain import DataError
from .intent import QuestionIntent, QuestionInterpreter
from .ollama_client import OllamaClient, OllamaError


HELP_TEXT = """Soy el bot de precios mayoristas del Mercado Modelo de Piura.

Puedes escribir preguntas como:
- ¿Cuanto cuesta la papaya?
- ¿La papaya subio o bajo?
- Historial de papaya en los ultimos 12 meses

Tambien puedes usar:
/precio Papaya
/variacion Papaya
/historial Papaya 12
/alerta Papaya 5
/productos

Solo respondo con informacion del dataset agricola."""


class PriceChatbot:
    def __init__(
        self,
        repository: PriceRepository,
        analyzer: PriceAnalyzer,
        interpreter: QuestionInterpreter,
        ollama: OllamaClient,
        default_threshold: Decimal,
    ) -> None:
        self.repository = repository
        self.analyzer = analyzer
        self.interpreter = interpreter
        self.ollama = ollama
        self.default_threshold = default_threshold

    def handle_text(self, text: str) -> str:
        intent = self.interpreter.interpret(text)
        try:
            return self._answer(intent)
        except (DataError, ValueError) as exc:
            return f"No pude completar la consulta: {exc}"

    def _answer(self, intent: QuestionIntent) -> str:
        if intent.kind == "AYUDA":
            return HELP_TEXT
        if intent.kind == "PRODUCTOS":
            return "Productos disponibles:\n" + "\n".join(
                f"- {product}" for product in self.repository.products
            )
        if intent.kind == "AMBIGUO":
            options = "\n".join(f"- {product}" for product in intent.candidates)
            return f"Encontre varias opciones. Escribe el nombre completo:\n{options}"
        if intent.kind == "FUERA_DE_ALCANCE":
            return "Solo puedo consultar precios agricolas del dataset de Piura. Usa /ayuda para ver ejemplos."
        if intent.product is None:
            return "Indica el producto. Ejemplo: /precio Papaya"
        if intent.kind == "PRECIO":
            return self._price(intent.product)
        if intent.kind == "VARIACION":
            return self._variation(intent.product)
        if intent.kind == "HISTORIAL":
            return self._history(intent.product, intent.months)
        if intent.kind == "ALERTA":
            threshold = intent.threshold if intent.threshold is not None else self.default_threshold
            return self._alert(intent.product, threshold)
        return "Solo puedo consultar precios agricolas del dataset de Piura. Usa /ayuda para ver ejemplos."

    def _price(self, product: str) -> str:
        record = self.repository.get_latest_price(product)
        return (
            f"Precio mayorista de {record.product}: {record.wholesale_price:.2f} por "
            f"{record.wholesale_unit}, registrado el {record.registered_at:%d/%m/%Y}.\n"
            "Fuente: Gobierno Regional Piura - Mercado Modelo de Piura."
        )

    def _variation(self, product: str) -> str:
        analysis = self.analyzer.evaluate(
            self.repository.get_recent_prices(product), self.default_threshold
        )
        prices = analysis.prices
        direction = {"SUBIO": "subio", "BAJO": "bajo", "SIN_CAMBIO": "no cambio"}[
            analysis.direction
        ]
        return (
            f"{prices.product} {direction} {abs(analysis.variation_pct):.2f}%. "
            f"Paso de {prices.previous.wholesale_price:.2f} el "
            f"{prices.previous.registered_at:%d/%m/%Y} a "
            f"{prices.current.wholesale_price:.2f} por {prices.current.wholesale_unit} el "
            f"{prices.current.registered_at:%d/%m/%Y}.\n"
            "Fuente: Gobierno Regional Piura - Mercado Modelo de Piura."
        )

    def _history(self, product: str, months: int | None) -> str:
        summary = self.analyzer.summarize_history(self.repository.get_history(product, months))
        annual = " | ".join(
            f"{year}: {average:.2f}" for year, average in summary["promedios_anuales"].items()
        )
        period = f"ultimos {months} meses" if months else "todo el periodo disponible"
        return (
            f"Historial mayorista de {summary['producto']} ({period}).\n"
            f"Periodo: {summary['fecha_inicio']} a {summary['fecha_fin']} "
            f"({summary['cantidad_registros']} registros).\n"
            f"Promedio: {summary['precio_promedio']:.2f} por {summary['unidad']}.\n"
            f"Minimo: {summary['precio_minimo']:.2f} el {summary['fecha_minimo']}.\n"
            f"Maximo: {summary['precio_maximo']:.2f} el {summary['fecha_maximo']}.\n"
            f"Variacion del periodo: {summary['variacion_periodo']:+.2f}%.\n"
            f"Promedios anuales: {annual}.\n"
            "Fuente: Gobierno Regional Piura - Mercado Modelo de Piura."
        )

    def _alert(self, product: str, threshold: Decimal) -> str:
        analysis = self.analyzer.evaluate(self.repository.get_recent_prices(product), threshold)
        if not analysis.is_atypical:
            return (
                f"{analysis.prices.product} varia {analysis.variation_pct:+.2f}% y no supera "
                f"el umbral de {analysis.threshold_pct:.2f}%. No se genera alerta."
            )
        try:
            message = self.ollama.generate_alert(analysis)
        except OllamaError:
            return safe_message(analysis)
        return message if message_is_safe(message, analysis) else safe_message(analysis)
