"""Analysis options: defaults, an optional JSON file, then command-line overrides.

Unknown keys are rejected so a typo in the config file fails loudly instead of being ignored.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from datetime import date, time, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .clock import Clock

WINDOW_BY = ("merged", "created")
GROUP_DIMENSIONS = ("project", "repo", "author")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ClockConfig:
    mode: str = "business"
    timezone: str = "Europe/Berlin"
    workdays: Tuple[int, ...] = (0, 1, 2, 3, 4)  # Monday = 0
    start: str = "09:00"
    end: str = "18:00"

    def build(self) -> Clock:
        return Clock(self.mode, self.timezone, self.workdays, _parse_time(self.start), _parse_time(self.end))


@dataclass(frozen=True)
class FollowUpConfig:
    window_days: int = 7
    fix_keywords: Tuple[str, ...] = ("fix", "hotfix")
    ignore_files: Tuple[str, ...] = (
        "*package.json",
        "*yarn.lock",
        "*pnpm-lock.yaml",
        "*package-lock.json",
        "*CHANGELOG.md",
    )


@dataclass(frozen=True)
class Config:
    since: date = field(default_factory=lambda: date.today() - timedelta(days=60))
    until: date = field(default_factory=date.today)
    window_by: str = "merged"
    include_open: bool = True
    group_by: Tuple[str, ...] = ("project", "repo")
    authors: Tuple[str, ...] = ()
    ignore_reviewers: Tuple[str, ...] = ()
    ignore_bots: bool = True
    large_pr_lines: int = 400
    size_ignore_files: Tuple[str, ...] = (
        "*.lock",
        "*package-lock.json",
        "*pnpm-lock.yaml",
        "*.snap",
        "*__snapshots__/*",
        "*__generated__/*",
        "*.generated.*",
        "*.min.js",
    )
    test_files: Tuple[str, ...] = (
        "*.test.*",
        "*.spec.*",
        "*/test/*",
        "*/tests/*",
        "*/__tests__/*",
        "*/e2e/*",
    )
    metrics: Tuple[str, ...] = ()
    exclude_metrics: Tuple[str, ...] = ()
    cache_dir: str = "~/.cache/pr-metrics"
    clock: ClockConfig = field(default_factory=ClockConfig)
    follow_up: FollowUpConfig = field(default_factory=FollowUpConfig)

    def __post_init__(self) -> None:
        if self.since > self.until:
            raise ConfigError("since must not be after until")
        if self.window_by not in WINDOW_BY:
            raise ConfigError(f"window_by must be one of {WINDOW_BY}")
        unknown = set(self.group_by) - set(GROUP_DIMENSIONS)
        if unknown:
            raise ConfigError(f"unknown group_by dimensions {sorted(unknown)}; use {GROUP_DIMENSIONS}")

    @property
    def cache_path(self) -> Path:
        return Path(self.cache_dir).expanduser()


def load_config(path: Optional[Path], overrides: Dict[str, Any]) -> Config:
    """Builds the config from defaults, then the file at `path`, then non-None `overrides`."""
    raw: Dict[str, Any] = {}
    if path is not None:
        loaded = json.loads(path.read_text())
        if not isinstance(loaded, dict):
            raise ConfigError(f"{path} must contain a JSON object")
        raw.update(loaded)
    raw.update({key: value for key, value in overrides.items() if value is not None})
    return _build_config(raw)


def _build_config(raw: Dict[str, Any]) -> Config:
    config = Config()
    known = {name for name in Config.__dataclass_fields__}
    unknown = set(raw) - known
    if unknown:
        raise ConfigError(f"unknown config keys {sorted(unknown)}")
    values: Dict[str, Any] = {}
    for key, value in raw.items():
        if key in ("since", "until"):
            values[key] = value if isinstance(value, date) else _parse_date(value, key)
        elif key == "clock":
            values[key] = _build_section(ClockConfig, value, key)
        elif key == "follow_up":
            values[key] = _build_section(FollowUpConfig, value, key)
        else:
            values[key] = _coerce(value, getattr(config, key), key)
    try:
        return replace(config, **values)
    except ValueError as error:
        raise ConfigError(str(error)) from error


def _build_section(section_type: Any, raw: Any, name: str) -> Any:
    if not isinstance(raw, dict):
        raise ConfigError(f"{name} must be an object")
    default = section_type()
    unknown = set(raw) - set(section_type.__dataclass_fields__)
    if unknown:
        raise ConfigError(f"unknown {name} keys {sorted(unknown)}")
    values = {key: _coerce(value, getattr(default, key), f"{name}.{key}") for key, value in raw.items()}
    return replace(default, **values)


def _coerce(value: Any, default: Any, name: str) -> Any:
    """Checks `value` against the type of the field's default; lists become tuples."""
    if isinstance(default, tuple):
        if not isinstance(value, (list, tuple)):
            raise ConfigError(f"{name} must be a list")
        return tuple(value)
    if isinstance(default, bool):
        if not isinstance(value, bool):
            raise ConfigError(f"{name} must be true or false")
        return value
    if isinstance(default, int):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigError(f"{name} must be an integer")
        return value
    if isinstance(default, str):
        if not isinstance(value, str):
            raise ConfigError(f"{name} must be a string")
        return value
    raise ConfigError(f"{name} has an unsupported type")


def _parse_date(value: Any, name: str) -> date:
    if not isinstance(value, str):
        raise ConfigError(f"{name} must be a YYYY-MM-DD string")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ConfigError(f"{name}: {error}") from error


def _parse_time(value: str) -> time:
    try:
        return time.fromisoformat(value)
    except ValueError as error:
        raise ConfigError(f"clock times must be HH:MM, got '{value}'") from error
