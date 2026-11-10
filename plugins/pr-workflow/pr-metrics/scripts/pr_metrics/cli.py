"""Command line: build the PR list, analyse it, render the report.

    run.py prlist  linear-tickets.json -o prs.csv
    run.py analyze prs.csv [--config config.json] [--since D] [--until D] -o results.json
    run.py render  results.json [--insights insights.json] [--title T] -o report.html
    run.py metrics
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path
from typing import List, Optional

from .analysis import analyse, select_in_window, window_bounds
from .config import ConfigError, load_config
from .github.client import GitHubClient, GitHubError
from .github.fetch import PrCache, fetch_follow_up_candidates, fetch_pull_requests
from .lifecycle import ReviewerFilter
from .metrics import ALL_METRICS, Context, select_metrics
from .prlist import read_pr_list, refs_from_linear, write_pr_list
from .render.html import render_report
from .render.text import render_text


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.handler(args)
    except (ConfigError, GitHubError, ValueError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


def _prlist(args: argparse.Namespace) -> int:
    refs = refs_from_linear(Path(args.tickets))
    write_pr_list(refs, Path(args.output))
    print(f"wrote {len(refs)} PRs to {args.output}", file=sys.stderr)
    return 0


def _analyze(args: argparse.Namespace) -> int:
    config = load_config(
        Path(args.config) if args.config else None,
        {
            "since": args.since,
            "until": args.until,
            "metrics": _csv(args.metrics),
            "exclude_metrics": _csv(args.exclude_metrics),
        },
    )
    metrics = select_metrics(config.metrics, config.exclude_metrics)
    clock = config.clock.build()
    client = GitHubClient()

    refs = read_pr_list(Path(args.pr_list))
    prs, missing = fetch_pull_requests(refs, client, PrCache(config.cache_path))
    start, end = window_bounds(config, clock.zone)
    kept, skipped = select_in_window(prs, config, start, end)

    candidates = ()
    if any(metric.needs_follow_ups for metric in metrics) and kept:
        candidates = tuple(
            fetch_follow_up_candidates(
                {pr.repo for pr in kept},
                config.since,
                config.until + timedelta(days=config.follow_up.window_days),
                (*config.follow_up.fix_keywords, "revert"),
                client,
            )
        )

    ctx = Context(
        config=config,
        clock=clock,
        reviewers=ReviewerFilter(frozenset(config.ignore_reviewers), config.ignore_bots),
        window_start=start,
        window_end=end,
        follow_up_candidates=candidates,
    )
    dataset = {
        "pr_list": str(args.pr_list),
        "listed": len(refs),
        "fetched": len(prs),
        "analysed": len(kept),
        "missing": [{"url": ref.url, "reason": reason} for ref, reason in missing],
        "excluded": [{"url": pr.url, "reason": reason} for pr, reason in skipped],
    }
    results = analyse(kept, metrics, ctx, {"dataset": dataset})
    Path(args.output).write_text(json.dumps(results, indent=1, default=str))
    print(render_text(results))
    print(f"\nwrote {args.output}", file=sys.stderr)
    return 0


def _render(args: argparse.Namespace) -> int:
    results = json.loads(Path(args.results).read_text())
    insights = json.loads(Path(args.insights).read_text()) if args.insights else None
    Path(args.output).write_text(render_report(results, insights, args.title))
    print(f"wrote {args.output}", file=sys.stderr)
    return 0


def _list_metrics(args: argparse.Namespace) -> int:
    for metric in ALL_METRICS:
        print(f"{metric.id:<22} {metric.title}: {metric.description}")
    return 0


def _csv(value: Optional[str]) -> Optional[List[str]]:
    return [part.strip() for part in value.split(",") if part.strip()] if value else None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pr-metrics", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    commands = parser.add_subparsers(required=True)

    prlist = commands.add_parser("prlist", help="build the PR list CSV from Linear tickets JSON")
    prlist.add_argument("tickets")
    prlist.add_argument("-o", "--output", required=True)
    prlist.set_defaults(handler=_prlist)

    analyze = commands.add_parser("analyze", help="fetch the PRs from GitHub and compute the metrics")
    analyze.add_argument("pr_list")
    analyze.add_argument("-c", "--config")
    analyze.add_argument("--since", help="YYYY-MM-DD, default 60 days ago")
    analyze.add_argument("--until", help="YYYY-MM-DD, default today")
    analyze.add_argument("--metrics", help="comma-separated metric ids to run (default: all)")
    analyze.add_argument("--exclude-metrics", help="comma-separated metric ids to skip")
    analyze.add_argument("-o", "--output", required=True)
    analyze.set_defaults(handler=_analyze)

    render = commands.add_parser("render", help="render the results JSON as an HTML report")
    render.add_argument("results")
    render.add_argument("--insights", help="JSON with the headline, findings and recommendations")
    render.add_argument("--title", default="PR Health")
    render.add_argument("-o", "--output", required=True)
    render.set_defaults(handler=_render)

    metrics = commands.add_parser("metrics", help="list the available metrics")
    metrics.set_defaults(handler=_list_metrics)
    return parser
