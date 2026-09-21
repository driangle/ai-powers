#!/usr/bin/env python3
"""Mine a Claude Code session transcript for the signals /reflect cares about.

Usage:
  session_metrics.py                 # the current session
  session_metrics.py <session-id>    # a specific session
  session_metrics.py <path.jsonl>    # a transcript file directly
  session_metrics.py --list          # list transcripts for this project

The current session is resolved via `vibeview self` when vibeview is installed,
and otherwise by finding the most recently modified transcript under
`~/.claude/projects/<slug-of-cwd>/`.

Prints a markdown report: timing, tool errors, retry loops, file churn, the
slowest tool calls, and every user turn (the steering log). It reports numbers
only — the judgement is the agent's job.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

SLOW_TOOL_SECONDS = 20.0
CHURN_THRESHOLD = 3
RETRY_THRESHOLD = 2

PROJECTS_DIR = Path.home() / ".claude" / "projects"


# --- locating the transcript -------------------------------------------------


def project_dir(cwd: Path | None = None) -> Path:
    """Claude Code stores transcripts under a slugified absolute path."""
    cwd = cwd or Path.cwd()
    return PROJECTS_DIR / re.sub(r"[^A-Za-z0-9]", "-", str(cwd))


def local_transcripts() -> list[Path]:
    """Transcripts for this project, newest first. Walks up to the git root."""
    candidates = [Path.cwd(), *Path.cwd().parents]
    for base in candidates:
        directory = project_dir(base)
        if directory.is_dir():
            files = sorted(
                directory.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
            )
            if files:
                return files
    return []


def vibeview_transcript(session_id: str | None) -> str | None:
    try:
        if not session_id:
            out = subprocess.run(
                ["vibeview", "self"], capture_output=True, text=True
            ).stdout
            match = re.search(r"Session:\s+(\S+)", out)
            if not match:
                return None
            session_id = match.group(1)
        info = subprocess.run(
            ["vibeview", "inspect", "--json", session_id],
            capture_output=True,
            text=True,
        )
        if info.returncode != 0:
            return None
        return json.loads(info.stdout).get("file_path")
    except (OSError, json.JSONDecodeError):
        return None


def resolve_transcript(arg: str | None) -> str:
    if arg and arg.endswith(".jsonl"):
        return arg

    path = vibeview_transcript(arg)
    if path and Path(path).exists():
        return path

    if arg:  # a session id, but vibeview could not resolve it — search locally
        for transcript in local_transcripts():
            if transcript.stem == arg or transcript.stem.startswith(arg):
                return str(transcript)
        sys.exit(f"no transcript found for session {arg!r}; pass a .jsonl path")

    transcripts = local_transcripts()
    if not transcripts:
        sys.exit(
            "could not locate a transcript for this project; pass a session id or "
            f"a .jsonl path (looked under {project_dir()})"
        )
    # The current session is the file still being appended to.
    return str(transcripts[0])


def list_transcripts() -> None:
    transcripts = local_transcripts()
    if not transcripts:
        print(f"No transcripts under {project_dir()}")
        return
    print(f"# Transcripts for this project\n\n`{transcripts[0].parent}`\n")
    for transcript in transcripts:
        stat = transcript.stat()
        when = datetime.fromtimestamp(stat.st_mtime)
        print(f"- {when:%Y-%m-%d %H:%M}  {stat.st_size / 1024:8.0f} KB  {transcript.stem}")


# --- parsing -----------------------------------------------------------------


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def blocks(entry: dict) -> list:
    message = entry.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), list):
        return [b for b in message["content"] if isinstance(b, dict)]
    return []


def text_of(block: dict) -> str:
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    return ""


def command_key(name: str, tool_input: dict) -> str:
    """A short, comparable label for a tool call — used to spot retry loops."""
    if name == "Bash":
        return "$ " + " ".join(str(tool_input.get("command", "")).split())[:120]
    for field in ("file_path", "path", "pattern", "url", "query"):
        if field in tool_input:
            return f"{name}({tool_input[field]})"
    return name


def main() -> None:
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg in ("--list", "-l"):
        list_transcripts()
        return
    if arg in ("--help", "-h"):
        print(__doc__)
        return

    path = resolve_transcript(arg)
    entries = []
    with open(path) as handle:
        for line in handle:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    calls: dict[str, dict] = {}
    order: list[str] = []
    user_turns: list[tuple[datetime | None, str]] = []
    stamps: list[datetime] = []

    for entry in entries:
        stamp = parse_ts(entry.get("timestamp"))
        if stamp:
            stamps.append(stamp)
        message = entry.get("message")
        if entry.get("type") == "user" and isinstance(message, dict) and isinstance(
            message.get("content"), str
        ):
            body = message["content"].strip()
            if body and not body.startswith("<"):
                user_turns.append((stamp, body))
        for block in blocks(entry):
            kind = block.get("type")
            if kind == "tool_use":
                call_id = block.get("id", "")
                tool_input = block.get("input") if isinstance(block.get("input"), dict) else {}
                calls[call_id] = {
                    "name": block.get("name", "?"),
                    "input": tool_input,
                    "key": command_key(block.get("name", "?"), tool_input),
                    "start": stamp,
                    "error": False,
                    "result": "",
                    "seconds": None,
                }
                order.append(call_id)
            elif kind == "tool_result":
                call = calls.get(block.get("tool_use_id", ""))
                if not call:
                    continue
                call["error"] = bool(block.get("is_error"))
                call["result"] = text_of(block)
                if stamp and call["start"]:
                    call["seconds"] = (stamp - call["start"]).total_seconds()
            elif kind == "text" and entry.get("type") == "user":
                body = block.get("text", "").strip()
                if body and not body.startswith("<"):
                    user_turns.append((stamp, body))

    out: list[str] = []
    add = out.append

    add(f"# Session metrics\n\n`{path}`\n")

    if stamps:
        stamps.sort()
        span = (stamps[-1] - stamps[0]).total_seconds()
        gaps = [
            (b - a).total_seconds() for a, b in zip(stamps, stamps[1:]) if (b - a).total_seconds() > 120
        ]
        add("## Timing\n")
        add(f"- Wall clock: **{span / 60:.0f} min** ({stamps[0]:%Y-%m-%d %H:%M} → {stamps[-1]:%H:%M})")
        add(f"- Idle gaps > 2 min: {len(gaps)}, totalling {sum(gaps) / 60:.0f} min")
        add(f"- Active time: ~{(span - sum(gaps)) / 60:.0f} min\n")

    tool_counts = Counter(c["name"] for c in calls.values())
    error_counts = Counter(c["name"] for c in calls.values() if c["error"])
    add("## Tool use\n")
    add("| Tool | Calls | Errors |")
    add("| --- | --- | --- |")
    for name, count in tool_counts.most_common():
        add(f"| {name} | {count} | {error_counts.get(name, 0)} |")
    add("")

    failures = [c for c in (calls[i] for i in order) if c["error"]]
    add(f"## Failed tool calls ({len(failures)})\n")
    if not failures:
        add("_None._\n")
    for call in failures:
        first_line = " ".join(call["result"].split())[:200]
        add(f"- `{call['key']}`\n  - {first_line}")
    add("")

    repeats = Counter(c["key"] for c in calls.values())
    loops = [(k, n) for k, n in repeats.most_common() if n > RETRY_THRESHOLD]
    add(f"## Repeated calls (possible retry loops, >{RETRY_THRESHOLD}×)\n")
    if not loops:
        add("_None._\n")
    for key, count in loops:
        add(f"- {count}× `{key}`")
    add("")

    churn: dict[str, int] = defaultdict(int)
    for call in calls.values():
        if call["name"] in ("Edit", "Write", "NotebookEdit"):
            target = call["input"].get("file_path")
            if target:
                churn[target] += 1
    hot = [(f, n) for f, n in sorted(churn.items(), key=lambda kv: -kv[1]) if n >= CHURN_THRESHOLD]
    add(f"## File churn (edited ≥{CHURN_THRESHOLD}×)\n")
    if not hot:
        add("_None._\n")
    for target, count in hot:
        add(f"- {count}× {os.path.relpath(target, os.getcwd()) if target.startswith('/') else target}")
    add("")

    slow = sorted(
        (c for c in calls.values() if c["seconds"] and c["seconds"] >= SLOW_TOOL_SECONDS),
        key=lambda c: -c["seconds"],
    )[:10]
    add(f"## Slowest tool calls (≥{SLOW_TOOL_SECONDS:.0f}s)\n")
    if not slow:
        add("_None._\n")
    for call in slow:
        add(f"- {call['seconds']:.0f}s — `{call['key']}`")
    add("")

    add(f"## User turns ({len(user_turns)}) — the steering log\n")
    for stamp, body in user_turns:
        when = f"{stamp:%H:%M}" if stamp else "--:--"
        add(f"- **{when}** {' '.join(body.split())[:300]}")
    add("")

    print("\n".join(out))


if __name__ == "__main__":
    main()
