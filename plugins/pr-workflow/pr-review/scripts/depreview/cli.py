"""Command line: `fetch-pr`, `lockdiff` and `pkgdiff`. Each prints Markdown, or JSON with --json."""

import argparse
import json
import sys
from pathlib import Path

from . import lockfiles, prfiles, render
from .classify import Limits, compare


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.run(args)
    except (lockfiles.UnsupportedLockfile, prfiles.FetchError) as error:
        print(f"depdiff: {error}", file=sys.stderr)
        return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="depdiff", description=__doc__)
    commands = parser.add_subparsers(required=True)

    fetch = commands.add_parser("fetch-pr", help="download a PR's lockfiles and manifests at its merge base and head")
    fetch.add_argument("pr", help="PR URL, or a number with --repo")
    fetch.add_argument("--repo", help="owner/name when the PR is given as a number")
    fetch.add_argument("--out", type=Path, required=True, help="empty or new directory")
    fetch.set_defaults(run=_fetch_pr)

    lock = commands.add_parser("lockdiff", help="compare two lockfiles and sort the changes into review tiers")
    lock.add_argument("base", type=Path)
    lock.add_argument("head", type=Path)
    lock.add_argument("--format", choices=sorted(lockfiles.LOADERS), help="default: from the file name")
    lock.add_argument("--target", action="append", default=[], help="package the PR is for; repeatable")
    lock.add_argument("--max-depth", type=int, default=Limits.max_depth)
    lock.add_argument("--max-deep", type=int, default=Limits.max_deep)
    lock.add_argument("--base-manifest", type=Path, action="append", default=[], help="package.json/pyproject.toml")
    lock.add_argument("--head-manifest", type=Path, action="append", default=[], help="package.json/pyproject.toml")
    lock.add_argument("--json", action="store_true")
    lock.set_defaults(run=_lockdiff)

    pkg = commands.add_parser("pkgdiff", help="download two releases of a package and diff what was published")
    pkg.add_argument("ecosystem", choices=["npm", "pypi", "crates", "go", "rubygems", "maven"])
    pkg.add_argument("name", help="package name; maven takes group:artifact")
    pkg.add_argument("old")
    pkg.add_argument("new")
    pkg.add_argument("--out", type=Path, required=True, help="empty or new directory")
    pkg.add_argument("--registry", default="https://registry.npmjs.org", help="npm registry base URL")
    pkg.add_argument("--json", action="store_true")
    pkg.set_defaults(run=_pkgdiff)
    return parser


def _fetch_pr(args) -> int:
    fetched = prfiles.fetch(args.pr, args.repo, args.out)
    print(json.dumps(fetched, indent=2))
    return 0


def _lockdiff(args) -> int:
    fmt = args.format or lockfiles.detect_format(args.head)
    base = lockfiles.load(args.base, fmt, [p.read_text(encoding="utf-8") for p in args.base_manifest])
    head = lockfiles.load(args.head, fmt, [p.read_text(encoding="utf-8") for p in args.head_manifest])
    report = compare(base, head, args.target, Limits(max_depth=args.max_depth, max_deep=args.max_deep))
    print(json.dumps(render.to_json(report), indent=2) if args.json else render.to_markdown(report))
    return 0


def _pkgdiff(args) -> int:
    from . import pkgdiff  # network and archive handling are only needed here

    summary = pkgdiff.run(args.ecosystem, args.name, args.old, args.new, args.out, args.registry)
    print(json.dumps(summary, indent=2) if args.json else pkgdiff.to_markdown(summary))
    return 0
