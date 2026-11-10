"""Renders the results document (and optional insights) as one self-contained HTML page, ready to
publish as an Artifact. Everything is static, so the page reads fully without running scripts."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .charts import stage_breakdown, weekly_columns
from ..units import format_hours, format_value

FONTS = (
    "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700"
    "&family=IBM+Plex+Mono:wght@400;600&family=Public+Sans:wght@400;600&display=swap"
)
TONES = {"good": "Good", "watch": "Watch", "problem": "Problem"}
SLOWEST_COUNT = 12
ROW_LIMIT = 25
STAGES_INTRO = (
    "Median time in each stage of a PR's life, for all PRs and per group. A wide amber segment "
    "means PRs wait for a first look; a wide blue one means many review rounds; a wide green one "
    "means CI, merge conflicts or stacked PRs hold merges up."
)

# KPI tiles: (metric id, summary key, label, note template). Tiles for metrics not run are skipped.
KPIS = (
    ("review_cycle_time", "median", "Review cycle, median", "P90 {p90}"),
    ("time_to_first_review", "median", "Time to first review", "P90 {p90}"),
    ("pr_size", "median", "PR size, median lines", "{median_code_lines} outside tests"),
    ("follow_up_fixes", "share", "Followed by a fix", "within the follow-up window"),
    ("ci_failures", "share", "Had a failing CI run", "of PRs with checks"),
)


def render_report(results: Dict[str, Any], insights: Optional[Dict[str, Any]], title: str) -> str:
    metrics = {metric["id"]: metric for metric in results["metrics"]}
    groups = results["groups"]
    prs = {pr["key"]: pr for pr in results["prs"]}
    css = (Path(__file__).parent / "style.css").read_text()
    body = [
        _header(results, insights, title),
        _kpis(metrics),
        _section("Where the time goes", STAGES_INTRO, stage_breakdown(metrics, groups)),
        _insights(insights, metrics, prs),
        *(_metric(metric, groups, prs) for metric in results["metrics"]),
        _slowest(results, metrics),
        _about(results),
    ]
    return (
        f"<title>{escape(title)}</title>\n"
        f'<link rel="stylesheet" href="{FONTS}">\n<style>\n{css}</style>\n'
        f'<main class="page">{"".join(part for part in body if part)}</main>\n'
    )


def _header(results: Dict[str, Any], insights: Optional[Dict[str, Any]], title: str) -> str:
    window, clock, dataset = results["window"], results["clock"], results["dataset"]
    headline = (insights or {}).get("headline")
    business = f" ({clock['hours']} {clock['timezone']})" if clock["mode"] == "business" else ""
    meta = [
        f"{window['since']} to {window['until']}, by {window['by']} date",
        f"{dataset['analysed']} PRs analysed of {dataset['listed']} linked",
        f"Times in {clock['unit']}{business}",
    ]
    return (
        '<header class="top"><div class="eyebrow">Pull request health</div>'
        f"<h1>{escape(title)}</h1>"
        f'<div class="meta">{"".join(f"<span>{escape(item)}</span>" for item in meta)}</div>'
        + (f'<p class="lede">{escape(headline)}</p>' if headline else "")
        + "</header>"
    )


def _kpis(metrics: Dict[str, Dict[str, Any]]) -> str:
    tiles = []
    for metric_id, key, label, note in KPIS:
        metric = metrics.get(metric_id)
        if metric is None:
            continue
        summary = metric["groups"]["overall:all"]["summary"]
        units = {field["key"]: field["unit"] for field in metric["summary_fields"]}
        formatted = {k: format_value(v, units.get(k, "number")) for k, v in summary.items()}
        tiles.append(
            f'<div class="kpi"><div class="eyebrow">{escape(label)}</div>'
            f'<div class="value">{escape(formatted.get(key, "–"))}</div>'
            f'<div class="note">{escape(note.format(**formatted))}</div></div>'
        )
    return f'<div class="kpis">{"".join(tiles)}</div>' if tiles else ""


def _insights(
    insights: Optional[Dict[str, Any]], metrics: Dict[str, Dict[str, Any]], prs: Dict[str, Dict[str, Any]]
) -> str:
    if not insights:
        return ""
    parts = []
    findings = insights.get("findings") or []
    if findings:
        items = "".join(
            f'<li class="finding"><span class="chip {_tone(f)}">{TONES[_tone(f)]}</span>'
            f"<strong>{escape(f['title'])}</strong>"
            f'<span class="detail">{escape(f.get("detail", ""))}</span>'
            f"{_finding_evidence(f, metrics, prs)}</li>"
            for f in findings
        )
        parts.append(_section("Findings", "", f'<ul class="findings">{items}</ul>'))
    recommendations = insights.get("recommendations") or []
    if recommendations:
        items = "".join(
            f"<li><strong>{escape(r['title'])}</strong>"
            f'<span class="detail">{escape(r.get("detail", ""))}</span></li>'
            for r in recommendations
        )
        parts.append(_section("What to try", "", f'<ol class="recs">{items}</ol>'))
    return "".join(parts)


def _finding_evidence(
    finding: Dict[str, Any], metrics: Dict[str, Dict[str, Any]], prs: Dict[str, Dict[str, Any]]
) -> str:
    """A finding may name the PR list behind it: {"metric": id, "key": summary key, "group": id}."""
    ref = finding.get("evidence")
    if not isinstance(ref, dict) or ref.get("metric") not in metrics:
        return ""
    group = metrics[ref["metric"]]["groups"].get(ref.get("group", "overall:all"), {})
    evidence = group.get("evidence", {}).get(ref.get("key"))
    return f'<div class="detail">{_evidence_list(evidence, prs)}</div>' if evidence else ""


def _evidence_list(evidence: Dict[str, Any], prs: Dict[str, Dict[str, Any]]) -> str:
    items = evidence["prs"]
    if not items:
        return ""
    rows = "".join(
        "<tr>"
        f'<td class="text">{_pr_link(prs.get(item["pr"]), item["pr"])}</td>'
        f'<td class="text">{escape(prs.get(item["pr"], {}).get("author", ""))}</td>'
        f'<td class="text">{escape(item["note"])}</td>'
        "</tr>"
        for item in items
    )
    return (
        f'<details class="evidence"><summary>{escape(evidence["label"])} · {_count(items)}</summary>'
        '<div class="table-wrap"><table><thead><tr><th>PR</th><th>Author</th><th>Why it is listed</th></tr></thead>'
        f"<tbody>{rows}</tbody></table></div></details>"
    )


def _count(items: List[Dict[str, str]]) -> str:
    unique = len({item["pr"] for item in items})
    prs = f"{unique} PR" + ("" if unique == 1 else "s")
    return prs if unique == len(items) else f"{len(items)} matches across {prs}"


def _pr_link(pr: Optional[Dict[str, Any]], key: str) -> str:
    if pr is None:
        return escape(key)
    return f'<a href="{escape(pr["url"])}">{escape(_short_pr(pr["url"]))}</a> {escape(pr["title"])}'


def _tone(finding: Dict[str, Any]) -> str:
    tone = finding.get("tone", "watch")
    return tone if tone in TONES else "watch"


def _metric(metric: Dict[str, Any], groups: Sequence[Dict[str, Any]], prs: Dict[str, Dict[str, Any]]) -> str:
    fields = metric["summary_fields"]
    headline = metric["headline"]
    values = [metric["groups"][g["id"]]["summary"].get(headline) for g in groups]
    peak = max((v for v in values if v is not None), default=0) or 1
    head = "".join(
        f'<th class="num{" headline" if f["key"] == headline else ""}">{escape(f["label"])}</th>' for f in fields
    )
    rows = []
    dimension = None
    for group in groups:
        summary = metric["groups"][group["id"]]["summary"]
        starts = group["dimension"] != dimension
        dimension = group["dimension"]
        cells = "".join(_summary_cell(summary.get(f["key"]), f, f["key"] == headline, peak) for f in fields)
        row_class = ' class="dim-start"' if starts else ""
        rows.append(f'<tr{row_class}><td class="group text">{_group_name(group)}</td>{cells}</tr>')
    table = (
        f'<div class="table-wrap"><table><thead><tr><th>Group</th>{head}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )
    return (
        f'<section class="metric" id="{escape(metric["id"])}"><div class="section-head">'
        f'<h3>{escape(metric["title"])}</h3><p class="muted">{escape(metric["description"])}</p></div>'
        f"{table}{_metric_rows(metric)}{_metric_evidence(metric, prs)}</section>"
    )


def _metric_evidence(metric: Dict[str, Any], prs: Dict[str, Dict[str, Any]]) -> str:
    evidence = metric["groups"]["overall:all"].get("evidence", {})
    return "".join(_evidence_list(evidence[key], prs) for key in evidence)


def _summary_cell(value: Any, field: Dict[str, str], is_headline: bool, peak: float) -> str:
    text = escape(format_value(value, field["unit"]))
    if not is_headline:
        return f'<td class="num">{text}</td>'
    width = 0 if value is None else max(value / peak * 56, 1)
    return f'<td class="num headline"><span class="cell-bar"><i style="width:{width:.0f}px"></i>{text}</span></td>'


def _metric_rows(metric: Dict[str, Any]) -> str:
    rows: List[Dict[str, Any]] = metric["groups"]["overall:all"]["rows"]
    fields = metric["row_fields"]
    if not rows or not fields:
        return ""
    if metric["id"] == "throughput":
        return weekly_columns(rows, fields[0]["key"], fields[1]["key"])
    shown = rows[:ROW_LIMIT]
    head = "".join(f'<th class="{_cell_class(f)}">{escape(f["label"])}</th>' for f in fields)
    body = "".join("<tr>" + "".join(_row_cell(row.get(f["key"]), f) for f in fields) + "</tr>" for row in shown)
    more = (
        f'<p class="muted">Showing {len(shown)} of {len(rows)}; every row is in the results JSON.</p>'
        if len(rows) > len(shown)
        else ""
    )
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>{more}'


def _cell_class(field: Dict[str, str]) -> str:
    return "text" if field["unit"] in ("text", "link") else "num"


def _row_cell(value: Any, field: Dict[str, str]) -> str:
    if field["unit"] == "link":
        if not value:
            return '<td class="text">–</td>'
        url = str(value)
        return f'<td class="text"><a href="{escape(url)}">{escape(_short_pr(url))}</a></td>'
    if field["unit"] == "text":
        return f'<td class="text">{escape(str(value))}</td>'
    return f'<td class="num">{escape(format_value(value, field["unit"]))}</td>'


def _short_pr(url: str) -> str:
    """https://github.com/org/repo/pull/12 -> repo#12"""
    parts = url.rstrip("/").split("/")
    return f"{parts[-3]}#{parts[-1]}" if len(parts) >= 4 else url


def _slowest(results: Dict[str, Any], metrics: Dict[str, Dict[str, Any]]) -> str:
    if "review_cycle_time" not in metrics:
        return ""
    timed = [pr for pr in results["prs"] if "review_cycle_time" in pr["metrics"]]
    timed.sort(key=lambda pr: pr["metrics"]["review_cycle_time"], reverse=True)
    rows = "".join(
        "<tr>"
        f'<td class="text"><a href="{escape(pr["url"])}">{escape(_short_pr(pr["url"]))}</a> {escape(pr["title"])}</td>'
        f'<td class="text">{escape(pr["author"])}</td>'
        f'<td class="text">{escape(", ".join(pr["tickets"]))}</td>'
        f'<td class="num">{format_hours(pr["metrics"]["review_cycle_time"])}</td>'
        f'<td class="num">{_hours_or_dash(pr["metrics"].get("time_to_first_review"))}</td>'
        f'<td class="num">{format_value(pr["metrics"].get("pr_size"), "lines")}</td>'
        "</tr>"
        for pr in timed[:SLOWEST_COUNT]
    )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>PR</th><th>Author</th><th>Tickets</th>'
        '<th class="num">Review cycle</th><th class="num">First review</th><th class="num">Lines</th>'
        f"</tr></thead><tbody>{rows}</tbody></table></div>"
    )
    return _section("Slowest to merge", "The PRs with the longest review cycle, to read case by case.", table)


def _about(results: Dict[str, Any]) -> str:
    dataset = results["dataset"]
    lists = []
    for key, label in (("missing", "Could not be read"), ("excluded", "Left out of the analysis")):
        entries = dataset[key]
        if entries:
            items = "".join(
                f'<li><a href="{escape(e["url"])}">{escape(_short_pr(e["url"]))}</a>: {escape(e["reason"])}</li>'
                for e in entries
            )
            lists.append(f"<details><summary>{label} ({len(entries)})</summary><ul>{items}</ul></details>")
    intro = (
        f"Durations use {results['clock']['unit']}. Medians and P90 lead because a few long-running "
        f"PRs skew averages. Generated {results['generated_at']}."
    )
    return _section("About this data", intro, "".join(lists) or "<p>Every linked PR was analysed.</p>")


def _section(title: str, intro: str, content: str) -> str:
    if not content:
        return ""
    lead = f'<p class="muted">{escape(intro)}</p>' if intro else ""
    return f'<section><div class="section-head"><h2>{escape(title)}</h2>{lead}</div>{content}</section>'


def _group_name(group: Dict[str, Any]) -> str:
    count = f'<span class="num">{group["prs"]}</span>'
    if group["dimension"] == "overall":
        return f"<b>All PRs</b> {count}"
    return f'{escape(group["dimension"])} · <b>{escape(group["value"])}</b> {count}'


def _hours_or_dash(value: Optional[float]) -> str:
    return "–" if value is None else format_hours(value)
