"""The metric contract. A new metric is a subclass of `Metric` (or `DurationMetric` for a
"time from A to B" measure) added to the registry in `metrics/__init__.py`."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional, Sequence, Tuple

from ..clock import Clock
from ..config import Config
from ..lifecycle import ReviewerFilter
from ..model import FollowUpCandidate, PullRequest
from ..stats import summarize
from ..units import format_hours

# Units the renderer knows how to format.
HOURS = "hours"
LINES = "lines"
COUNT = "count"
RATIO = "ratio"  # 0..1, shown as a percentage
NUMBER = "number"


@dataclass(frozen=True)
class Field:
    """A named value in a summary or a table row, with the unit the report formats it in."""

    key: str
    label: str
    unit: str


@dataclass(frozen=True)
class Context:
    config: Config
    clock: Clock
    reviewers: ReviewerFilter
    window_start: datetime
    window_end: datetime
    follow_up_candidates: Tuple[FollowUpCandidate, ...] = ()


@dataclass(frozen=True)
class EvidenceItem:
    pr: str  # PullRequest.key
    note: str  # the data that put the PR on the list, so a reader can check it on GitHub


@dataclass(frozen=True)
class Evidence:
    """The PRs behind one number, so the number can be checked PR by PR."""

    label: str
    items: List[EvidenceItem]

    def to_json(self) -> Dict[str, Any]:
        return {"label": self.label, "prs": [vars(item) for item in self.items]}


@dataclass(frozen=True)
class MetricResult:
    summary: Dict[str, Optional[float]]
    rows: List[Dict[str, Any]] = field(default_factory=list)
    per_pr: Dict[str, float] = field(default_factory=dict)
    evidence: Dict[str, Evidence] = field(default_factory=dict)  # keyed by the summary key it explains


class Metric(ABC):
    id: ClassVar[str]
    title: ClassVar[str]
    description: ClassVar[str]
    summary_fields: ClassVar[Tuple[Field, ...]]
    headline: ClassVar[str]  # the summary key that best represents the metric
    lower_is_better: ClassVar[Optional[bool]] = True
    row_fields: ClassVar[Tuple[Field, ...]] = ()
    per_pr_unit: ClassVar[Optional[str]] = None
    needs_follow_ups: ClassVar[bool] = False

    @abstractmethod
    def compute(self, prs: Sequence[PullRequest], ctx: Context) -> MetricResult:
        ...

    def describe(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "headline": self.headline,
            "lower_is_better": self.lower_is_better,
            "summary_fields": [vars(f) for f in self.summary_fields],
            "row_fields": [vars(f) for f in self.row_fields],
            "per_pr_unit": self.per_pr_unit,
        }


DISTRIBUTION_FIELDS = (
    Field("n", "PRs", COUNT),
    Field("median", "Median", HOURS),
    Field("p75", "P75", HOURS),
    Field("p90", "P90", HOURS),
    Field("mean", "Mean", HOURS),
)


class DurationMetric(Metric):
    """Time between two milestones of each PR, measured by the configured clock. PRs that have
    not reached both milestones are left out. The evidence lists the PRs at or above the P90."""

    summary_fields = DISTRIBUTION_FIELDS
    headline = "median"
    per_pr_unit = HOURS

    @abstractmethod
    def span(self, pr: PullRequest, ctx: Context) -> Optional[Tuple[datetime, datetime]]:
        ...

    def compute(self, prs: Sequence[PullRequest], ctx: Context) -> MetricResult:
        per_pr: Dict[str, float] = {}
        for pr in prs:
            span = self.span(pr, ctx)
            if span is not None:
                per_pr[pr.key] = ctx.clock.hours_between(*span)
        summary = summarize(list(per_pr.values()))
        slowest = sorted(per_pr.items(), key=lambda item: item[1], reverse=True)
        items = [EvidenceItem(key, format_hours(hours)) for key, hours in slowest if hours >= (summary["p90"] or 0)]
        evidence = {"p90": Evidence("At or above the P90", items)} if per_pr else {}
        return MetricResult(summary=summary, per_pr=per_pr, evidence=evidence)
