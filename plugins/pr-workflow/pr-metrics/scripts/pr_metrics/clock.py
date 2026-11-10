"""Measures elapsed time between two instants, in calendar or business hours."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Tuple
from zoneinfo import ZoneInfo

CALENDAR = "calendar"
BUSINESS = "business"


class Clock:
    """Business mode counts only the working hours of working days in one time zone, so a PR
    opened on Friday evening and reviewed on Monday morning has waited minutes, not days."""

    def __init__(self, mode: str, timezone: str, workdays: Tuple[int, ...], start: time, end: time):
        if mode not in (CALENDAR, BUSINESS):
            raise ValueError(f"clock mode must be '{CALENDAR}' or '{BUSINESS}', got '{mode}'")
        if start >= end:
            raise ValueError("clock start must be before clock end")
        self.mode = mode
        self.zone = ZoneInfo(timezone)
        self.workdays = frozenset(workdays)
        self.start = start
        self.end = end

    @property
    def unit_label(self) -> str:
        return "business hours" if self.mode == BUSINESS else "hours"

    def hours_between(self, begin: datetime, finish: datetime) -> float:
        if finish <= begin:
            return 0.0
        if self.mode == CALENDAR:
            return (finish - begin).total_seconds() / 3600
        return self._business_seconds(begin, finish) / 3600

    def is_workday(self, day: date) -> bool:
        return day.weekday() in self.workdays

    def _business_seconds(self, begin: datetime, finish: datetime) -> float:
        total = 0.0
        day = begin.astimezone(self.zone).date()
        last = finish.astimezone(self.zone).date()
        while day <= last:
            if self.is_workday(day):
                open_at = datetime.combine(day, self.start, tzinfo=self.zone)
                close_at = datetime.combine(day, self.end, tzinfo=self.zone)
                overlap = min(close_at, finish) - max(open_at, begin)
                total += max(overlap.total_seconds(), 0.0)
            day += timedelta(days=1)
        return total
