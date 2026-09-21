from __future__ import annotations

import calendar
import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import unicodedata

from .domain import DataError, PriceRecord, RecentPrices


REQUIRED_COLUMNS = {
    "DEPARTAMENTO",
    "FECHA_REGISTRO",
    "PRODUCTO",
    "PRECIO_MAYORISTA",
    "CATEGORIA",
    "UNIDAD_MEDIDA_MAY",
}


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_accents.casefold()).strip()


class PriceRepository:
    def __init__(self, csv_path: Path, department: str = "PIURA") -> None:
        self.csv_path = csv_path
        self.department = department
        self._records = self._load_records()
        self._products = sorted(
            {
                record.product
                for record in self._records
                if normalize_text(record.department) == normalize_text(self.department)
            },
            key=normalize_text,
        )

    def _load_records(self) -> list[PriceRecord]:
        if not self.csv_path.exists():
            raise DataError(f"No se encontro el dataset: {self.csv_path}")

        records: list[PriceRecord] = []
        with self.csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            columns = set(reader.fieldnames or [])
            missing = sorted(REQUIRED_COLUMNS - columns)
            if missing:
                raise DataError(f"Faltan columnas obligatorias: {', '.join(missing)}")

            for line_number, row in enumerate(reader, start=2):
                try:
                    registered_at = datetime.strptime(row["FECHA_REGISTRO"].strip(), "%Y%m%d").date()
                    wholesale_price = Decimal(row["PRECIO_MAYORISTA"].strip())
                except (ValueError, InvalidOperation, AttributeError) as exc:
                    raise DataError(f"Fila {line_number} con fecha o precio invalido") from exc

                product = row["PRODUCTO"].strip()
                category = row["CATEGORIA"].strip()
                department = row["DEPARTAMENTO"].strip()
                unit = row["UNIDAD_MEDIDA_MAY"].strip()
                if not all((product, category, department, unit)):
                    raise DataError(f"Fila {line_number} con un campo obligatorio vacio")

                records.append(
                    PriceRecord(
                        product=product,
                        category=category,
                        department=department,
                        registered_at=registered_at,
                        wholesale_price=wholesale_price,
                        wholesale_unit=unit,
                    )
                )

        if not records:
            raise DataError("El dataset no contiene registros")
        return records

    @property
    def row_count(self) -> int:
        return len(self._records)

    @property
    def product_count(self) -> int:
        return len(self._products)

    @property
    def products(self) -> tuple[str, ...]:
        return tuple(self._products)

    def search_products(self, query: str, limit: int = 10) -> list[str]:
        normalized_query = normalize_text(query)
        if not normalized_query:
            return []

        exact = [product for product in self._products if normalize_text(product) == normalized_query]
        if exact:
            return exact

        pattern = re.compile(rf"(?<!\w){re.escape(normalized_query)}(?!\w)")
        return [product for product in self._products if pattern.search(normalize_text(product))][:limit]

    def _valid_records(self, product: str) -> list[PriceRecord]:
        normalized_product = normalize_text(product)
        valid = [
            record
            for record in self._records
            if normalize_text(record.department) == normalize_text(self.department)
            and normalize_text(record.product) == normalized_product
            and record.wholesale_price > 0
        ]
        valid.sort(key=lambda record: record.registered_at)
        return valid

    def get_latest_price(self, product: str) -> PriceRecord:
        valid = self._valid_records(product)
        if not valid:
            raise DataError(f"{product} no tiene precios mayoristas validos")
        return valid[-1]

    def get_history(self, product: str, months: int | None = None) -> list[PriceRecord]:
        valid = self._valid_records(product)
        if not valid:
            raise DataError(f"{product} no tiene precios mayoristas validos")
        if months is None:
            return valid
        if months < 1 or months > 60:
            raise DataError("La consulta historica admite entre 1 y 60 meses")

        latest = valid[-1].registered_at
        month_index = latest.year * 12 + latest.month - 1 - months
        cutoff_year, cutoff_month_index = divmod(month_index, 12)
        cutoff_month = cutoff_month_index + 1
        cutoff_day = min(latest.day, calendar.monthrange(cutoff_year, cutoff_month)[1])
        cutoff = date(cutoff_year, cutoff_month, cutoff_day)
        return [record for record in valid if record.registered_at >= cutoff]

    def get_recent_prices(self, product: str) -> RecentPrices:
        valid = self._valid_records(product)

        if len(valid) < 2:
            raise DataError(f"{product} no tiene dos precios mayoristas validos")

        previous, current = valid[-2], valid[-1]
        if normalize_text(previous.wholesale_unit) != normalize_text(current.wholesale_unit):
            raise DataError(f"{product} tiene unidades incompatibles en sus dos registros recientes")

        return RecentPrices(
            product=current.product,
            category=current.category,
            department=current.department,
            previous=previous,
            current=current,
        )
