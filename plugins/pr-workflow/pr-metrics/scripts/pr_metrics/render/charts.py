"""Static charts: the stage breakdown as stacked bars and weekly throughput as columns."""

from __future__ import annotations

from html import escape
from typing import Any, Dict, List, Sequence, Tuple

from ..units import format_hours

# (metric id, legend label, colour token), in the order a PR moves through them.
STAGES: Tuple[Tuple[str, str, str], ...] = (
    ("draft_time", "Before review", "--stage-draft"),
    ("time_to_first_review", "Waiting for first review", "--stage-wait"),
    ("review_to_approval", "First review to approval", "--stage-review"),
    ("approval_to_merge", "Approval to merge", "--stage-merge"),
)


def stage_breakdown(metrics: Dict[str, Dict[str, Any]], groups: Sequence[Dict[str, Any]]) -> str:
    """One bar per group; each segment is that stage's median, all bars on one scale. Medians of
    stages do not add up to the median cycle time, so the total is labelled as a sum of medians."""
    stages = [stage for stage in STAGES if stage[0] in metrics]
    if not stages:
        return ""
    rows: List[Tuple[Dict[str, Any], List[float]]] = []
    for group in groups:
        medians = [_median(metrics[stage_id], group["id"]) for stage_id, _, _ in stages]
        rows.append((group, medians))
    scale = max((sum(medians) for _, medians in rows), default=0) or 1
    legend = "".join(
        f'<span style="--swatch: var({token})">{escape(label)}</span>' for _, label, token in stages
    )
    parts = [f'<div class="legend">{legend}</div>']
    dimension = None
    for group, medians in rows:
        if group["dimension"] != dimension:
            dimension = group["dimension"]
            if dimension != "overall":
                parts.append(f'<div class="dimension">By {escape(dimension)}</div>')
        segments = "".join(
            f'<i style="width:{value / scale * 100:.2f}%; background: var({token})" '
            f'title="{escape(label)}: {format_hours(value)}"></i>'
            for value, (_, label, token) in zip(medians, stages)
            if value > 0
        )
        detail = " · ".join(
            f"{escape(label)} {format_hours(value)}" for value, (_, label, _) in zip(medians, stages)
        )
        parts.append(
            f'<div class="stage-row"><div class="label">{_group_label(group)}</div>'
            f'<div><div class="stage-bar" role="img" aria-label="{detail}">{segments}</div>'
            f'<div class="stage-total">{format_hours(sum(medians))} sum of medians · {detail}</div></div></div>'
        )
    return f'<div class="stages">{"".join(parts)}</div>'


def weekly_columns(rows: Sequence[Dict[str, Any]], x_key: str, y_key: str) -> str:
    if not rows:
        return ""
    width, height, left, bottom, top = 640, 180, 34, 26, 10
    peak = max(row[y_key] for row in rows) or 1
    step = _nice_step(peak)
    ceiling = step * -(-peak // step)
    plot_w, plot_h = width - left - 8, height - bottom - top
    slot = plot_w / len(rows)
    bar_w = max(slot * 0.62, 2)
    grid = []
    for tick in range(0, int(ceiling) + 1, int(step)):
        y = top + plot_h - tick / ceiling * plot_h
        grid.append(
            f'<line class="grid" x1="{left}" x2="{width - 8}" y1="{y:.1f}" y2="{y:.1f}"/>'
            f'<text x="{left - 6}" y="{y + 4:.1f}" text-anchor="end">{tick}</text>'
        )
    columns = []
    label_every = max(1, round(len(rows) / 8))
    for index, row in enumerate(rows):
        value = row[y_key]
        h = value / ceiling * plot_h
        x = left + index * slot + (slot - bar_w) / 2
        columns.append(
            f'<rect class="col" x="{x:.1f}" y="{top + plot_h - h:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="2">'
            f"<title>{escape(str(row[x_key]))}: {value}</title></rect>"
        )
        if index % label_every == 0:
            columns.append(
                f'<text x="{x + bar_w / 2:.1f}" y="{height - 8}" text-anchor="middle">{escape(str(row[x_key])[5:])}</text>'
            )
    return (
        f'<div class="chart"><svg viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Merged PRs per week">{"".join(grid)}{"".join(columns)}</svg></div>'
    )


def _nice_step(peak: float) -> int:
    for step in (1, 2, 5, 10, 20, 25, 50, 100):
        if peak / step <= 5:
            return step
    return 200


def _median(metric: Dict[str, Any], group_id: str) -> float:
    value = metric["groups"].get(group_id, {}).get("summary", {}).get("median")
    return value or 0.0


def _group_label(group: Dict[str, Any]) -> str:
    name = "All PRs" if group["dimension"] == "overall" else group["value"]
    return f'<b>{escape(name)}</b> <span class="muted num">{group["prs"]}</span>'
