"""Formats metric values by unit, for notes, the text digest and the HTML report."""

from __future__ import annotations

from typing import Any


def format_value(value: Any, unit: str) -> str:
    if value is None:
        return "–"
    if unit == "ratio":
        return f"{value * 100:.0f}%"
    if unit == "hours":
        return format_hours(value)
    if unit in ("count", "lines"):
        return f"{value:,.0f}"
    if unit == "number":
        return f"{value:.1f}"
    return str(value)


def format_hours(hours: float) -> str:
    if hours < 1:
        return f"{hours * 60:.0f}m"
    if hours < 100:
        return f"{hours:.1f}h"
    return f"{hours:,.0f}h"
