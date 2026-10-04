import unittest
from datetime import date

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.periods import period_keys, sections


def spans(found):
    """Each section as its key and its first and last day."""
    return [(key, start.isoformat(), end.isoformat()) for key, start, end in found]


class SectionTests(unittest.TestCase):
    def test_a_week_is_made_of_its_days_newest_first_and_none_after_today(self):
        found = sections("week", date(2026, 9, 28), date(2026, 10, 4), date(2026, 10, 1))
        self.assertEqual([key for key, _, _ in found], ["2026-10-01", "2026-09-30", "2026-09-29", "2026-09-28"])

    def test_a_month_is_made_of_its_weeks_each_kept_inside_the_month(self):
        found = sections("month", date(2026, 9, 1), date(2026, 9, 30), date(2026, 10, 3))
        self.assertEqual(spans(found)[0], ("2026-W40", "2026-09-28", "2026-09-30"))
        self.assertEqual(spans(found)[-1], ("2026-W36", "2026-09-01", "2026-09-06"))
        self.assertEqual(len(found), 5)

    def test_all_time_is_made_of_its_months_from_the_first_record(self):
        found = sections("all", date(2025, 12, 20), date(2026, 2, 10), date(2026, 2, 10))
        self.assertEqual(spans(found), [("2026-02", "2026-02-01", "2026-02-10"), ("2026-01", "2026-01-01", "2026-01-31"),
                                        ("2025-12", "2025-12-20", "2025-12-31")])

    def test_a_month_still_to_come_has_no_part_that_ends_before_it_starts(self):
        self.assertEqual(sections("month", date(2026, 11, 1), date(2026, 11, 30), date(2026, 10, 30)), [])

    def test_a_day_has_no_smaller_parts(self):
        self.assertEqual(sections("day", date(2026, 10, 1), date(2026, 10, 1), date(2026, 10, 1)), [])


class PeriodKeyTests(unittest.TestCase):
    def test_a_day_falls_in_its_own_report_its_iso_weeks_and_its_months(self):
        self.assertEqual(period_keys(date(2026, 10, 3)), (("day", "2026-10-03"), ("week", "2026-W40"), ("month", "2026-10")))
        self.assertEqual(dict(period_keys(date(2027, 1, 1)))["week"], "2026-W53")


if __name__ == "__main__":
    unittest.main()
