from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import hashlib

from .domain import AnalysisResult, PriceRecord, RecentPrices


TWO_DECIMALS = Decimal("0.01")


class PriceAnalyzer:
    def evaluate(self, prices: RecentPrices, threshold_pct: Decimal) -> AnalysisResult:
        if threshold_pct < 0 or threshold_pct > 100:
            raise ValueError("El umbral debe estar entre 0 y 100")
        if prices.previous.wholesale_price <= 0:
            raise ValueError("El precio anterior debe ser mayor que cero")

        raw_variation = (
            (prices.current.wholesale_price - prices.previous.wholesale_price)
            / prices.previous.wholesale_price
            * Decimal("100")
        )
        rounded_variation = raw_variation.quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP)

        if raw_variation > 0:
            direction = "SUBIO"
        elif raw_variation < 0:
            direction = "BAJO"
        else:
            direction = "SIN_CAMBIO"

        identity = "|".join(
            [
                prices.product,
                prices.previous.registered_at.isoformat(),
                str(prices.previous.wholesale_price),
                prices.current.registered_at.isoformat(),
                str(prices.current.wholesale_price),
                str(threshold_pct),
            ]
        )
        analysis_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]

        return AnalysisResult(
            analysis_id=analysis_id,
            prices=prices,
            variation_pct=rounded_variation,
            direction=direction,
            threshold_pct=threshold_pct.quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP),
            is_atypical=abs(raw_variation) >= threshold_pct,
        )

    def summarize_history(self, records: list[PriceRecord]) -> dict[str, object]:
        if not records:
            raise ValueError("No existen registros para resumir")

        ordered = sorted(records, key=lambda record: record.registered_at)
        units = {record.wholesale_unit for record in ordered}
        if len(units) != 1:
            raise ValueError("El historial contiene unidades incompatibles")

        first = ordered[0]
        last = ordered[-1]
        minimum = min(ordered, key=lambda record: record.wholesale_price)
        maximum = max(ordered, key=lambda record: record.wholesale_price)
        average = (
            sum((record.wholesale_price for record in ordered), Decimal("0"))
            / Decimal(len(ordered))
        ).quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP)
        variation = (
            (last.wholesale_price - first.wholesale_price)
            / first.wholesale_price
            * Decimal("100")
        ).quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP)

        yearly: dict[int, list[Decimal]] = {}
        for record in ordered:
            yearly.setdefault(record.registered_at.year, []).append(record.wholesale_price)
        yearly_averages = {
            str(year): float(
                (sum(values, Decimal("0")) / Decimal(len(values))).quantize(
                    TWO_DECIMALS, rounding=ROUND_HALF_UP
                )
            )
            for year, values in sorted(yearly.items())
        }

        return {
            "producto": last.product,
            "unidad": last.wholesale_unit,
            "cantidad_registros": len(ordered),
            "fecha_inicio": first.registered_at.isoformat(),
            "fecha_fin": last.registered_at.isoformat(),
            "precio_inicial": float(first.wholesale_price),
            "precio_final": float(last.wholesale_price),
            "precio_minimo": float(minimum.wholesale_price),
            "fecha_minimo": minimum.registered_at.isoformat(),
            "precio_maximo": float(maximum.wholesale_price),
            "fecha_maximo": maximum.registered_at.isoformat(),
            "precio_promedio": float(average),
            "variacion_periodo": float(variation),
            "promedios_anuales": yearly_averages,
            "fuente": "Gobierno Regional Piura - Mercado Modelo de Piura",
        }
