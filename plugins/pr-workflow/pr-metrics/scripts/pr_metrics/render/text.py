"""A plain-text digest of the results: every metric's summary, one line per group."""

from __future__ import annotations

from typing import Any, Dict

from ..units import format_value


def render_text(results: Dict[str, Any]) -> str:
    dataset = results["dataset"]
    window = results["window"]
    lines = [
        f"Window {window['since']} to {window['until']} (by {window['by']}), times in {results['clock']['unit']}",
        f"PRs: {dataset['listed']} listed, {dataset['fetched']} fetched, {dataset['analysed']} analysed, "
        f"{len(dataset['missing'])} missing, {len(dataset['excluded'])} excluded",
    ]
    group_width = max(len(group["id"]) for group in results["groups"]) + 2
    for metric in results["metrics"]:
        fields = metric["summary_fields"]
        lines += ["", f"== {metric['title']} ({metric['id']})"]
        lines.append(" " * group_width + "".join(f"{field['label'][:16]:>18}" for field in fields))
        for group in results["groups"]:
            summary = metric["groups"][group["id"]]["summary"]
            cells = "".join(f"{format_value(summary.get(f['key']), f['unit']):>18}" for f in fields)
            lines.append(f"{group['id']:<{group_width}}{cells}")
    return "\n".join(lines)


