import unittest
from datetime import time

from pr_metrics.clock import Clock
from tests.fixtures import at

WEEKDAYS = (0, 1, 2, 3, 4)


def business_clock() -> Clock:
    return Clock("business", "UTC", WEEKDAYS, time(9), time(17))


class BusinessClockTest(unittest.TestCase):
    def test_counts_only_working_hours_within_a_day(self):
        self.assertEqual(business_clock().hours_between(at(5, 8), at(5, 12)), 3)

    def test_skips_the_weekend(self):
        # Friday 16:00 to Monday 10:00 is one hour on Friday and one on Monday.
        self.assertEqual(business_clock().hours_between(at(9, 16), at(12, 10)), 2)

    def test_nothing_counts_outside_working_hours(self):
        self.assertEqual(business_clock().hours_between(at(5, 18), at(6, 8)), 0)

    def test_reversed_span_is_zero(self):
        self.assertEqual(business_clock().hours_between(at(6), at(5)), 0)


class CalendarClockTest(unittest.TestCase):
    def test_counts_every_hour(self):
        clock = Clock("calendar", "UTC", WEEKDAYS, time(9), time(17))
        self.assertEqual(clock.hours_between(at(9, 16), at(12, 10)), 66)


if __name__ == "__main__":
    unittest.main()
