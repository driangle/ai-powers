"""Distribution summaries. Medians and P90 lead because PR durations are heavily skewed."""

from __future__ import annotations

from typing import Dict, Optional, Sequence


def percentile(values: Sequence[float], fraction: float) -> Optional[float]:
    """Linear interpolation between closest ranks; works for any non-empty sample size."""
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def summarize(values: Sequence[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {"n": 0, "median": None, "p75": None, "p90": None, "mean": None, "max": None}
    return {
        "n": len(values),
        "median": percentile(values, 0.5),
        "p75": percentile(values, 0.75),
        "p90": percentile(values, 0.9),
        "mean": sum(values) / len(values),
        "max": max(values),
    }


def share(part: int, whole: int) -> Optional[float]:
    return part / whole if whole else None
