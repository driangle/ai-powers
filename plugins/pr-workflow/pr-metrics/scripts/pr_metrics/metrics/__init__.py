"""The metric registry. Order here is the order of the report."""

from __future__ import annotations

from typing import Dict, List, Sequence

from .base import Context, Evidence, EvidenceItem, Metric, MetricResult
from .ci import CiFailures
from .follow_ups import FollowUpFixes, Reverts
from .review_quality import ReviewDepth, ReviewRounds
from .review_stages import ApprovalToMerge, DraftTime, ReviewCycleTime, ReviewToApproval, TimeToFirstReview
from .reviewers import ReviewerLoad, ReviewPairs
from .size import PrSize
from .stacks import StackWait
from .throughput import Throughput
from .wip import WorkInProgress

ALL_METRICS: List[Metric] = [
    ReviewCycleTime(),
    DraftTime(),
    TimeToFirstReview(),
    ReviewToApproval(),
    ApprovalToMerge(),
    PrSize(),
    Throughput(),
    WorkInProgress(),
    StackWait(),
    ReviewRounds(),
    ReviewDepth(),
    FollowUpFixes(),
    Reverts(),
    CiFailures(),
    ReviewerLoad(),
    ReviewPairs(),
]

BY_ID: Dict[str, Metric] = {metric.id: metric for metric in ALL_METRICS}


def select_metrics(include: Sequence[str], exclude: Sequence[str]) -> List[Metric]:
    """All metrics, or only `include`, minus `exclude`. Unknown ids are an error."""
    unknown = (set(include) | set(exclude)) - set(BY_ID)
    if unknown:
        raise ValueError(f"unknown metrics {sorted(unknown)}; known: {sorted(BY_ID)}")
    chosen = [BY_ID[metric_id] for metric_id in include] if include else ALL_METRICS
    return [metric for metric in chosen if metric.id not in exclude]


__all__ = ["ALL_METRICS", "Context", "Evidence", "EvidenceItem", "Metric", "MetricResult", "select_metrics"]
