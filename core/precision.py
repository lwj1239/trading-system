from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

_Q8 = Decimal("0.00000001")


def to_decimal(value: object) -> Decimal:
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none"}:
        return Decimal("0")
    try:
        return Decimal(text)
    except Exception:
        return Decimal("0")


def q8(value: object) -> Decimal:
    return to_decimal(value).quantize(_Q8, rounding=ROUND_DOWN)


def format_8(value: object) -> str:
    return format(q8(value), ".8f")
