"""Value normalisation, transformations and cell-level comparison rules."""

from __future__ import annotations

import math
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Sequence

import pandas as pd

TRANSFORMS: dict[str, Callable[[str], str]] = {
    "none": lambda value: value,
    "upper": str.upper,
    "lower": str.lower,
    "trim": str.strip,
}


def is_null(value: Any) -> bool:
    """True for None, NaN, NaT and pandas NA values."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str):
        return False
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def normalize_key(value: Any) -> str | None:
    """Business key as a comparable string: 1001, 1001.0 and ' 1001 ' all become '1001'."""
    if is_null(value):
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    return text or None


def typed_value(value: Any, compare: str) -> Decimal | date | str | None:
    """Convert a raw value to the type used for comparison. Unparseable values stay as text."""
    if is_null(value):
        return None
    if compare == "numeric":
        try:
            number = Decimal(str(value).strip().replace(",", ""))
        except InvalidOperation:
            return str(value)
        return number if number.is_finite() else str(value)
    if compare == "date":
        parsed = pd.to_datetime(value, errors="coerce")
        return str(value) if pd.isna(parsed) else parsed.date()
    return str(value)


def display_value(value: Any, compare: str) -> str:
    """How a value is written in the mismatch report (NULL for missing values)."""
    typed = typed_value(value, compare)
    if typed is None:
        return "NULL"
    if isinstance(typed, Decimal):
        two_dp = typed.quantize(Decimal("0.01"))
        return f"{two_dp:f}" if two_dp == typed else f"{typed:f}"
    if isinstance(typed, date):
        return typed.isoformat()
    return str(typed)


def apply_transforms(names: Sequence[str], value: Any) -> Any:
    """Apply named transformations in order. Only text values are transformed."""
    for name in names:
        if isinstance(value, str):
            value = TRANSFORMS[name](value)
    return value


def has_padding(value: Any) -> bool:
    """True for text with leading or trailing whitespace (common in fixed-width CHAR extracts)."""
    return isinstance(value, str) and value != value.strip()


def values_match(
    source_value: Any,
    target_value: Any,
    *,
    transforms: Sequence[str] | str = (),
    compare: str = "text",
    tolerance: float = 0.0,
) -> bool:
    """Does the target hold the source value after the expected transformations?

    The transformations are applied to the source side only, so a target that is
    not in the expected form (for example mixed-case email) is reported as a mismatch.
    NULL matches NULL and nothing else.
    """
    if isinstance(transforms, str):
        transforms = (transforms,)
    expected = apply_transforms(transforms, typed_value(source_value, compare))
    actual = typed_value(target_value, compare)
    if expected is None or actual is None:
        return expected is None and actual is None
    if isinstance(expected, Decimal) and isinstance(actual, Decimal):
        return abs(expected - actual) <= Decimal(str(tolerance))
    return expected == actual
