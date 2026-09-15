"""Utilidades compartidas: dinero con Decimal, ids, reloj."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

ZERO = Decimal(0)
CENT = Decimal("0.01")
MILLI = Decimal("0.0001")


def D(value: Any) -> Decimal:
    """Decimal a partir de lo que sea (float, str, int, Decimal, None)."""
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def q2(value: Any) -> Decimal:
    return D(value).quantize(CENT, rounding=ROUND_HALF_UP)


def q4(value: Any) -> Decimal:
    return D(value).quantize(MILLI, rounding=ROUND_HALF_UP)


def money(value: Any) -> float:
    """Para JSON: dinero a 2 decimales como float."""
    return float(q2(value))


def fmt_money(value: Any) -> str:
    """Dinero para texto que lee una persona: "$7,989.04", "-$14.25".

    Un solo formato para todas las frases (explicaciones, asistente): antes unas
    decían "$7989.04" y otras "$7,989.04" para la misma cifra.
    """
    d = q2(value)
    return f"{'-' if d < 0 else ''}${abs(d):,.2f}"


def qty(value: Any) -> float:
    """Para JSON: cantidades/costos unitarios a 4 decimales."""
    return float(q4(value))


def safe_div(numerator: Any, denominator: Any) -> Decimal | None:
    den = D(denominator)
    if den == 0:
        return None
    return D(numerator) / den


def new_id() -> str:
    return uuid.uuid4().hex


def now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def now_iso() -> str:
    return now().replace(microsecond=0).isoformat()


def today() -> date:
    return now().date()


def today_iso() -> str:
    return today().isoformat()


def iso_date(value: Any) -> str:
    """Normaliza 'YYYY-MM-DD', 'YYYY-MM-DDTHH:MM:SS' o date/datetime a 'YYYY-MM-DD'."""
    if value is None:
        return today_iso()
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(str(value)[:10])


def period_bounds(period: str, anchor: date | None = None) -> tuple[date, date]:
    """Rangos usados por analítica y asistente. Todos inclusivos.

    today, yesterday, week (esta semana, lunes a hoy), last_week, month,
    last_month, 7d, 30d, 90d, year, all.
    """
    anchor = anchor or today()
    if period == "today":
        return anchor, anchor
    if period == "yesterday":
        y = anchor - timedelta(days=1)
        return y, y
    if period == "week":
        start = anchor - timedelta(days=anchor.weekday())
        return start, anchor
    if period == "last_week":
        this_monday = anchor - timedelta(days=anchor.weekday())
        return this_monday - timedelta(days=7), this_monday - timedelta(days=1)
    if period == "month":
        return anchor.replace(day=1), anchor
    if period == "last_month":
        first_this = anchor.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        return last_prev.replace(day=1), last_prev
    if period == "7d":
        return anchor - timedelta(days=6), anchor
    if period == "30d":
        return anchor - timedelta(days=29), anchor
    if period == "90d":
        return anchor - timedelta(days=89), anchor
    if period == "year":
        return anchor.replace(month=1, day=1), anchor
    return date(2000, 1, 1), anchor


def previous_period(start: date, end: date) -> tuple[date, date]:
    """El periodo inmediatamente anterior, del mismo largo."""
    length = (end - start).days + 1
    return start - timedelta(days=length), start - timedelta(days=1)
