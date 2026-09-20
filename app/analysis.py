from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import hashlib

from .domain import AnalysisResult, RecentPrices


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
