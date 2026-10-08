import unittest
from datetime import date, timedelta

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app import patterns


def record(day, status="done", planned=60, minutes=60, end="10:30", domain="work", estimate=None, status_at=None,
           title="Task", series=None):
    """One task as Database.pattern_records gives it: a counted time (minutes), or None for none."""
    return {"date": day, "title": title, "domain": domain, "planned": planned, "estimate": estimate, "status": status,
            "minutes": minutes, "statusAt": status_at if status_at is not None else end, "end": end, "series": series}


def days(first, count):
    """`count` days from `first`, YYYY-MM-DD."""
    start = date.fromisoformat(first)
    return [(start + timedelta(days=offset)).isoformat() for offset in range(count)]


# 2026-09-07 is a Monday; 2026-10-06 a Tuesday.
MONTH = ("2026-09-07", "2026-10-06")


class GaugeTests(unittest.TestCase):
    def test_a_graph_is_empty_then_few_then_settling_until_twice_its_threshold_then_ready(self):
        self.assertEqual([patterns.gauge(count, 10, "tasks")["state"] for count in (0, 3, 10, 19, 20)],
                         ["empty", "few", "settling", "settling", "ready"])
        self.assertEqual(patterns.gauge(4, 3, "days", basis=9), {"state": "settling", "count": 4, "threshold": 3,
                                                                  "unit": "days", "basis": 9})


class ColumnTests(unittest.TestCase):
    def test_week_has_a_column_a_day_month_a_column_a_monday_week_and_all_time_one_a_month(self):
        week = patterns.columns("week", "2026-09-30", "2026-10-06")
        self.assertEqual([(column["start"], column["kind"]) for column in week][:2], [("2026-09-30", "day"), ("2026-10-01", "day")])
        self.assertEqual(len(week), 7)
        month = patterns.columns("month", *MONTH)
        self.assertEqual([(column["start"], column["end"]) for column in month],
                         [("2026-09-07", "2026-09-13"), ("2026-09-14", "2026-09-20"), ("2026-09-21", "2026-09-27"),
                          ("2026-09-28", "2026-10-04"), ("2026-10-05", "2026-10-06")])
        self.assertEqual([column["current"] for column in month], [False] * 4 + [True])
        clipped = patterns.columns("month", "2026-09-09", "2026-10-08")
        self.assertEqual((clipped[0]["start"], clipped[0]["end"]), ("2026-09-09", "2026-09-13"), "the first week starts at the range")
        every = patterns.columns("all", "2026-08-20", "2026-10-06")
        self.assertEqual([(column["start"], column["end"], column["kind"]) for column in every],
                         [("2026-08-20", "2026-08-31", "month"), ("2026-09-01", "2026-09-30", "month"),
                          ("2026-10-01", "2026-10-06", "month")])


class BestHoursTests(unittest.TestCase):
    def finished(self, *cells):
        """Fully done tasks finished at (day, "HH:MM"), a record each."""
        return [record(day, end=end) for day, end in cells]

    def test_only_fully_done_tasks_with_a_counted_time_and_only_the_hours_used(self):
        tasks = self.finished(*[("2026-09-08", "10:20")] * 6, *[("2026-09-09", "11:40")] * 3, ("2026-09-10", "15:05"))
        tasks += [record("2026-09-08", status="partial", end="08:10"), record("2026-09-08", minutes=None, end="07:00")]
        best = patterns.best_hours(tasks)
        self.assertEqual((best["state"], best["count"]), ("settling", 10))
        self.assertEqual(best["hours"], [10, 11, 12, 13, 14, 15], "from the first hour used to the last")
        self.assertEqual(best["cells"][1][0], 6, "Tuesday 10:00–11:00")
        self.assertEqual(best["cells"][2][1], 3)

    def test_four_steps_split_by_the_busiest_cell_with_the_key_in_counts(self):
        # Tuesday 10:00 ×6, Wednesday 11:00 ×3, Thursday 12:00 ×1, Friday 13:00 ×4, Monday 14:00 ×2.
        tasks = self.finished(*[("2026-09-08", "10:20")] * 6, *[("2026-09-09", "11:40")] * 3, ("2026-09-10", "12:05"),
                              *[("2026-09-11", "13:05")] * 4, *[("2026-09-14", "14:05")] * 2)
        best = patterns.best_hours(tasks)
        self.assertEqual(best["steps"][1][0], 4, "6 of 6 is the darkest step")
        self.assertEqual(best["steps"][2][1], 2, "3 of 6")
        self.assertEqual(best["steps"][3][2], 1, "1 of 6")
        self.assertEqual(best["steps"][0][0], 0, "none is no step")
        self.assertEqual(best["key"], [{"step": 1, "from": 1, "to": 1}, {"step": 2, "from": 2, "to": 3},
                                       {"step": 3, "from": 4, "to": 4}, {"step": 4, "from": 5, "to": 6}])

    def test_the_best_two_hours_and_the_busiest_weekday(self):
        tasks = self.finished(*[("2026-09-08", "10:20")] * 5, *[("2026-09-08", "11:10")] * 4, ("2026-09-09", "15:00"),
                              ("2026-09-10", "16:00"))
        best = patterns.best_hours(tasks)
        self.assertEqual(best["finding"], {"kind": "window", "from": 10, "to": 12, "day": 1})
        self.assertEqual(best["best"], [10, 11])

    def test_tied_windows_are_each_named_and_days_evenly_spread_drop_the_day(self):
        tasks = self.finished(*[(day, "10:20") for day in days("2026-09-07", 5)],
                              *[(day, "15:20") for day in days("2026-09-07", 5)])
        best = patterns.best_hours(tasks)
        self.assertEqual(best["finding"], {"kind": "windows", "hours": [10, 15], "day": None})
        self.assertEqual(best["best"], [10, 11, 15], "only the hours on show are marked")

    def test_one_hour_only(self):
        best = patterns.best_hours(self.finished(*[(day, "10:05") for day in days("2026-09-07", 10)]))
        self.assertEqual(best["finding"], {"kind": "oneHour", "hour": 10})
        self.assertEqual(best["hours"], [10])


class PlannedAgainstActualTests(unittest.TestCase):
    def test_per_area_averages_from_fully_done_tasks_only_and_an_area_under_three_needs_more(self):
        tasks = [record("2026-09-08", domain="work", planned=60, minutes=minutes) for minutes in (70, 75, 74)]
        tasks += [record("2026-09-08", domain="learning", planned=50, minutes=55)]
        tasks += [record("2026-09-08", domain="work", status="partial", minutes=200), record("2026-09-08", domain="work", status="skipped", minutes=5)]
        pairs = patterns.planned_actual(tasks)
        self.assertEqual(pairs["rows"], [
            {"key": "learning", "title": None, "domain": "learning", "count": 1, "planned": None, "actual": None, "percent": None},
            {"key": "work", "title": None, "domain": "work", "count": 3, "planned": 60, "actual": 73, "percent": 22}])
        self.assertEqual((pairs["state"], pairs["count"], pairs["basis"]), ("settling", 3, 3))
        self.assertEqual(pairs["finding"], {"kind": "over", "key": "work", "title": None, "percent": 22})

    def test_under_plan_and_close_findings(self):
        under = [record("2026-09-08", domain="life", planned=40, minutes=34) for _ in range(3)]
        self.assertEqual(patterns.planned_actual(under)["finding"], {"kind": "under", "key": "life", "title": None, "percent": -15})
        close = [record("2026-09-08", domain="life", planned=40, minutes=42) for _ in range(3)]
        self.assertEqual(patterns.planned_actual(close)["finding"], {"kind": "close"})

    def test_a_repeating_tasks_list_says_what_it_usually_takes(self):
        tasks = [record("2026-09-08", series="s1", title="Weekly review", planned=60, minutes=75) for _ in range(4)]
        tasks += [record("2026-09-08", series="s2", title="Email triage", planned=30, minutes=28) for _ in range(9)]
        tasks += [record("2026-09-08", series=None, title="Once", planned=30, minutes=90) for _ in range(5)]
        pairs = patterns.planned_actual(tasks, by="series")
        self.assertEqual([row["title"] for row in pairs["rows"]], ["Email triage", "Weekly review"], "only repeating tasks")
        self.assertEqual(pairs["finding"], {"kind": "usual", "key": "s1", "title": "Weekly review", "actual": 75, "planned": 60})


class EstimatesTests(unittest.TestCase):
    def test_only_agents_estimates_count_a_day_without_one_is_a_dash_and_never_zero(self):
        tasks = [record("2026-10-05", estimate=30, minutes=55), record("2026-10-05", estimate=30, minutes=35),
                 record("2026-10-01", estimate=40, minutes=48), record("2026-10-06", estimate=None, minutes=99),
                 record("2026-09-30", estimate=20, minutes=30), record("2026-10-02", status="skipped", estimate=20, minutes=1)]
        estimates = patterns.estimates(tasks, "2026-09-30", "2026-10-06")
        self.assertEqual(estimates["by"], "day")
        self.assertEqual([column["minutes"] for column in estimates["columns"]], [10, 8, None, None, None, 15, None])
        self.assertEqual((estimates["state"], estimates["count"]), ("settling", 3))
        self.assertEqual(estimates["finding"], {"kind": "up", "now": 15, "before": 10, "column": 5, "beforeColumn": 0})

    def test_per_week_once_two_weeks_of_data_and_the_wording_cases(self):
        tasks = [record(day, estimate=30, minutes=30 + gap) for day, gap in
                 (("2026-09-08", 25), ("2026-09-15", 19), ("2026-09-22", 14), ("2026-09-29", 10), ("2026-10-05", 8))]
        estimates = patterns.estimates(tasks, *MONTH)
        self.assertEqual(estimates["by"], "week")
        self.assertEqual([column["minutes"] for column in estimates["columns"]], [25, 19, 14, 10, 8])
        self.assertEqual(estimates["finding"], {"kind": "down", "now": 8, "before": 25, "column": 4, "beforeColumn": 0})
        short = patterns.estimates(tasks[:2], *MONTH)
        self.assertEqual((short["by"], len(short["columns"])), ("day", 30), "8 days of data stay a column a day")
        same = patterns.estimates([record("2026-10-01", estimate=30, minutes=40), record("2026-10-05", estimate=30, minutes=41)],
                                  "2026-09-30", "2026-10-06")
        self.assertEqual(same["finding"]["kind"], "same")
        spot = patterns.estimates([record("2026-10-01", estimate=30, minutes=40), record("2026-10-05", estimate=30, minutes=30)],
                                  "2026-09-30", "2026-10-06")
        self.assertEqual(spot["finding"]["kind"], "spot")
        single = patterns.estimates([record("2026-10-05", estimate=30, minutes=40)], "2026-09-30", "2026-10-06")
        self.assertEqual(single["finding"], {"kind": "single", "now": 10, "column": 5})


class OutcomeTests(unittest.TestCase):
    def test_time_by_status_per_column_scaled_to_the_busiest_with_paused_on_its_own(self):
        tasks = [record("2026-09-08", minutes=600), record("2026-09-08", status="partial", minutes=60),
                 record("2026-09-15", status="skipped", minutes=30), record("2026-09-15", status="noReply", minutes=70),
                 record("2026-10-05", status="dayPaused", minutes=20), record("2026-10-05", minutes=None)]
        outcome = patterns.outcome(tasks, patterns.columns("month", *MONTH))
        self.assertEqual(outcome["columns"][0]["parts"], {"done": 600, "partial": 60, "skipped": 0, "noReply": 0, "dayPaused": 0})
        self.assertEqual((outcome["columns"][0]["total"], outcome["busiest"]), (660, 660))
        self.assertEqual(outcome["totals"], {"done": 600, "partial": 60, "skipped": 30, "noReply": 70, "dayPaused": 20})
        self.assertEqual(outcome["finding"], {"share": 77, "noReply": 70})
        self.assertEqual((outcome["state"], outcome["count"]), ("settling", 3))


class EnergyTests(unittest.TestCase):
    def energy(self, levels):
        return [{"date": day, "average": level} for day, level in levels]

    def test_groups_by_the_days_average_and_the_biggest_change_leads(self):
        low, middle = days("2026-09-07", 3), days("2026-09-14", 4)
        tasks = [record(day, planned=50, minutes=60) for day in low] + [record(day, planned=50, minutes=52) for day in middle]
        tasks += [record("2026-09-21", planned=50, minutes=40)]
        energy = patterns.energy(tasks, self.energy([(day, 2.4) for day in low] + [(day, 3.0) for day in middle]
                                                    + [("2026-09-21", 3.5)]))
        self.assertEqual(energy["groups"], [{"group": "low", "days": 3, "percent": 20}, {"group": "middle", "days": 4, "percent": 4},
                                            {"group": "high", "days": 1, "percent": None}])
        self.assertEqual(energy["finding"], {"kind": "longer", "group": "low", "percent": 20})
        self.assertEqual(energy["focus"], "low")
        self.assertEqual((energy["state"], energy["count"], energy["basis"]), ("settling", 4, 8))

    def test_hardly_any_change_and_energy_never_reported(self):
        tasks = [record(day, planned=50, minutes=51) for day in days("2026-09-07", 3)]
        self.assertEqual(patterns.energy(tasks, self.energy([(day, 4.6) for day in days("2026-09-07", 3)]))["finding"],
                         {"kind": "hardly"})
        self.assertEqual(patterns.energy(tasks, [])["finding"], {"kind": "never"})
        shorter = [record(day, planned=50, minutes=40) for day in days("2026-09-07", 3)]
        self.assertEqual(patterns.energy(shorter, self.energy([(day, 4) for day in days("2026-09-07", 3)]))["finding"],
                         {"kind": "shorter", "group": "high", "percent": -20})


class ReportingTests(unittest.TestCase):
    def test_right_away_within_15_minutes_of_stopping_later_that_day_next_day_and_no_reply(self):
        tasks = [record("2026-10-05", end="10:00", status_at="10:00"), record("2026-10-05", end="10:00", status_at="10:15"),
                 record("2026-10-05", end="10:00", status_at="10:16"), record("2026-10-05", end="10:00", status_at="22:30"),
                 record("2026-10-05", end="10:00", status_at="24:00"), record("2026-10-05", status="noReply", minutes=20),
                 record("2026-10-05", status="dayPaused", minutes=20)]
        habit = patterns.reporting(tasks, patterns.columns("week", "2026-09-30", "2026-10-06"))
        self.assertEqual(habit["totals"], {"rightAway": 2, "laterDay": 1, "nextDay": 2, "noReply": 1})
        self.assertEqual(habit["columns"][5]["shares"], {"rightAway": 33, "laterDay": 17, "nextDay": 33, "noReply": 17})

    def test_the_finding_sets_the_latest_column_against_the_earliest(self):
        tasks = [record(day, end="10:00", status_at=at) for day, at in
                 (("2026-09-08", "10:00"), ("2026-09-08", "12:00"), ("2026-09-15", "10:00"), ("2026-10-05", "10:00"),
                  ("2026-10-05", "10:05"), ("2026-10-05", "10:10"), ("2026-10-05", "13:00"))]
        habit = patterns.reporting(tasks + [record("2026-10-05", status="noReply", minutes=0)], patterns.columns("month", *MONTH))
        self.assertEqual(habit["finding"], {"now": 60, "before": 50, "column": 4, "beforeColumn": 0, "noReply": 1})
        self.assertEqual((habit["state"], habit["count"]), ("settling", 3))


class SectionPaceTests(unittest.TestCase):
    def test_minutes_a_section_by_source_from_two_sections_and_the_fastest_leads(self):
        tasks = [{"sourceId": "a", "sourceTitle": "Consuming HTTP Services", "minutes": 36, "sections": 3},
                 {"sourceId": "a", "sourceTitle": "Consuming HTTP Services", "minutes": 24, "sections": 2},
                 {"sourceId": "b", "sourceTitle": "Directives", "minutes": 24, "sections": 3},
                 {"sourceId": "c", "sourceTitle": "Python Exceptions", "minutes": 15, "sections": 1},
                 {"sourceId": "b", "sourceTitle": "Directives", "minutes": 30, "sections": 0}]
        pace = patterns.section_pace(tasks)
        self.assertEqual(pace["rows"], [{"sourceId": "a", "title": "Consuming HTTP Services", "minutes": 12, "sections": 5},
                                        {"sourceId": "b", "title": "Directives", "minutes": 8, "sections": 3}])
        self.assertEqual(pace["finding"], {"kind": "fastest", "sourceId": "b", "title": "Directives", "minutes": 8})
        self.assertEqual((pace["state"], pace["count"]), ("ready", 5))
        self.assertEqual(patterns.source_pace(tasks, "a"), {"minutes": 12, "sections": 5})
        self.assertIsNone(patterns.source_pace(tasks, "c"), "one section is not enough")
        one = patterns.section_pace(tasks[:2])
        self.assertEqual(one["finding"], {"kind": "one", "sourceId": "a", "title": "Consuming HTTP Services", "minutes": 12})


if __name__ == "__main__":
    unittest.main()
