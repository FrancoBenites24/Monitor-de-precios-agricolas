from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


class DataError(ValueError):
    pass


@dataclass(frozen=True)
class PriceRecord:
    product: str
    category: str
    department: str
    registered_at: date
    wholesale_price: Decimal
    wholesale_unit: str


@dataclass(frozen=True)
class RecentPrices:
    product: str
    category: str
    department: str
    previous: PriceRecord
    current: PriceRecord

    def to_dict(self) -> dict[str, object]:
        return {
            "producto": self.product,
            "categoria": self.category,
            "departamento": self.department,
            "fecha_anterior": self.previous.registered_at.isoformat(),
            "precio_anterior": float(self.previous.wholesale_price),
            "fecha_actual": self.current.registered_at.isoformat(),
            "precio_actual": float(self.current.wholesale_price),
            "unidad": self.current.wholesale_unit,
        }


@dataclass(frozen=True)
class AnalysisResult:
    analysis_id: str
    prices: RecentPrices
    variation_pct: Decimal
    direction: str
    threshold_pct: Decimal
    is_atypical: bool

    def to_dict(self) -> dict[str, object]:
        result = self.prices.to_dict()
        result.update(
            {
                "analysis_id": self.analysis_id,
                "variacion_porcentual": float(self.variation_pct),
                "direccion": self.direction,
                "umbral_porcentual": float(self.threshold_pct),
                "es_atipica": self.is_atypical,
                "fuente": "Gobierno Regional Piura - Mercado Modelo de Piura",
            }
        )
        return result
