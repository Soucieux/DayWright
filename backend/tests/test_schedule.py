import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.app_settings import DEFAULT_WORK_SCHEDULE, SETTINGS_FILE, AppSettings
from backend.app.memory import day_rules
from backend.app.planner import DayRules, build_recorded_variants, day_load
from backend.app.schedule import day_schedule
from backend.tests.test_repeats import SeriesDay, days_ago
from backend.tests.test_rules import fixed, keys, spans, untimed

WORKING = {"mode": "working", "start": "09:00", "end": "17:00"}
FOCUS = {"mode": "focus", "start": "09:00", "end": "12:00"}


def _minutes(clock):
    return int(clock[:2]) * 60 + int(clock[3:])


def inside(span, start, end):
    """Whether a task's (start, end) in minutes lies wholly within `start`–`end`, given as "HH:MM"."""
    return _minutes(start) <= span[0] and span[1] <= _minutes(end)


def overlaps(span, start, end):
    """Whether a task's (start, end) in minutes overlaps `start`–`end`, given as "HH:MM"."""
    return span[0] < _minutes(end) and _minutes(start) < span[1]


class WorkingHoursPlanTests(unittest.TestCase):
    """Working hours: the range is kept free, and nothing, Work included, is planned inside it."""

    RULES = DayRules(working=("09:00", "17:00"))
    DAY = (untimed("Report", "work", 60), untimed("Read", "learning", 45), untimed("Walk", "life", 30))

    def test_nothing_is_planned_inside_working_hours_work_included(self):
        for variant in build_recorded_variants(self.DAY, earliest="07:00", rules=self.RULES):
            for title, span in spans(variant).items():
                self.assertFalse(overlaps(span, "09:00", "17:00"), f"{variant['slug']}: {title} {span}")
            self.assertIn("planScheduleWorking", keys(variant), variant["slug"])

    def test_the_plans_say_they_kept_your_working_hours_free(self):
        balanced = build_recorded_variants(self.DAY, earliest="07:00", rules=self.RULES)[0]
        note = next(note for note in balanced["notes"] if note["key"] == "planScheduleWorking")
        self.assertEqual(note["values"], {"start": "09:00", "end": "17:00"})
        self.assertEqual(note["text"], "Keeps your working hours, 09:00–17:00, free.")

    def test_a_task_fixed_inside_working_hours_stays_where_it_is(self):
        day = (fixed("10:00", "Dentist", "life", 30), *self.DAY)
        for variant in build_recorded_variants(day, earliest="07:00", rules=self.RULES):
            self.assertEqual(spans(variant)["Dentist"], (600, 630), variant["slug"])

    def test_working_hours_are_not_free_time_in_the_days_load(self):
        self.assertEqual(day_load(self.DAY, "09:00", rules=self.RULES)["freeMinutes"], 240)
        self.assertEqual(day_load(self.DAY, "09:00")["freeMinutes"], 660)

    def test_tasks_that_cant_fit_around_working_hours_say_so(self):
        with self.assertRaises(ValueError):
            build_recorded_variants((untimed("Thesis", "learning", 300),), earliest="07:00", rules=self.RULES)


class FocusTimePlanTests(unittest.TestCase):
    """Focus time: Work is planned inside the range and not outside it; the other areas may fill its gaps."""

    RULES = DayRules(focus=("09:00", "12:00"))
    DAY = (untimed("Report", "work", 60), untimed("Email", "work", 30), untimed("Read", "learning", 45),
           untimed("Walk", "life", 30))

    def test_work_is_planned_inside_focus_time_and_not_outside_it_in_every_plan(self):
        for variant in build_recorded_variants(self.DAY, earliest="07:00", rules=self.RULES):
            placed = spans(variant)
            for title in ("Report", "Email"):
                self.assertTrue(inside(placed[title], "09:00", "12:00"), f"{variant['slug']}: {title} {placed[title]}")
            self.assertIn("planScheduleFocus", keys(variant), variant["slug"])

    def test_the_other_areas_may_fill_the_gaps_left_inside_it(self):
        day = (untimed("Report", "work", 30), untimed("Read", "learning", 45))
        balanced = build_recorded_variants(day, earliest="07:00", rules=self.RULES)[0]
        self.assertTrue(inside(spans(balanced)["Read"], "09:00", "12:00"), spans(balanced))

    def test_work_that_doesnt_fit_in_focus_time_says_so(self):
        day = (untimed("Report", "work", 120), untimed("Review", "work", 90), untimed("Walk", "life", 30))
        with self.assertRaisesRegex(ValueError, "focus time"):
            build_recorded_variants(day, earliest="07:00", rules=self.RULES)
        self.assertFalse(day_load(day, "09:00", rules=self.RULES)["fits"])
        self.assertTrue(day_load(day, "09:00")["fits"])

    def test_a_work_task_fixed_outside_focus_time_stays_where_it_is(self):
        day = (fixed("15:00", "Client call", "work", 60), *self.DAY)
        for variant in build_recorded_variants(day, earliest="07:00", rules=self.RULES):
            self.assertEqual(spans(variant)["Client call"], (900, 960), variant["slug"])

    def test_the_plans_say_work_is_placed_in_focus_time(self):
        balanced = build_recorded_variants(self.DAY, earliest="07:00", rules=self.RULES)[0]
        note = next(note for note in balanced["notes"] if note["key"] == "planScheduleFocus")
        self.assertEqual(note["values"], {"start": "09:00", "end": "12:00"})
        self.assertEqual(note["text"], "Places Work in your focus time, 09:00–12:00.")


class DayRulesFromScheduleTests(unittest.TestCase):
    """A day's rules carry its work schedule and its holiday."""

    DAY = "2026-10-14"

    def test_working_hours_and_focus_time_reach_the_days_rules(self):
        self.assertEqual(day_rules([], self.DAY, WORKING).working, ("09:00", "17:00"))
        self.assertIsNone(day_rules([], self.DAY, WORKING).focus)
        self.assertEqual(day_rules([], self.DAY, FOCUS).focus, ("09:00", "12:00"))
        self.assertIsNone(day_rules([], self.DAY, FOCUS).working)
        self.assertEqual(day_rules([], self.DAY), DayRules())

    def test_a_holiday_reaches_the_days_rules_and_every_plan_names_it(self):
        rules = day_rules([], self.DAY, None, {"name": "Thanksgiving"})
        self.assertEqual(rules.holiday, "Thanksgiving")
        for variant in build_recorded_variants(WorkingHoursPlanTests.DAY, earliest="07:00", rules=rules):
            note = next(note for note in variant["notes"] if note["key"] == "planHoliday")
            self.assertEqual(note["values"], {"name": "Thanksgiving"})
            self.assertEqual(note["text"], "Thanksgiving is a statutory holiday: your work schedule doesn't apply, "
                                           "and Work repeats aren't carried.")


class ScheduleSettingTests(unittest.TestCase):
    """The work schedule is kept once for both workspaces, off until turned on."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / SETTINGS_FILE

    def test_off_with_weekdays_until_set_then_kept_in_the_shared_file(self):
        settings = AppSettings(self.path)
        self.assertEqual(settings.work_schedule(), DEFAULT_WORK_SCHEDULE)
        self.assertEqual(DEFAULT_WORK_SCHEDULE, {"enabled": False, "mode": "working", "start": "09:00", "end": "17:00",
                                                 "days": [0, 1, 2, 3, 4]})
        chosen = {"enabled": True, "mode": "focus", "start": "09:00", "end": "12:00", "days": [0, 2, 4]}
        self.assertEqual(settings.set_work_schedule(chosen), chosen)
        self.assertEqual(json.loads(self.path.read_text())["workSchedule"], chosen)
        self.assertEqual(AppSettings(self.path).work_schedule(), chosen, "the other workspace reads the same file")

    def test_only_a_whole_schedule_is_kept(self):
        settings = AppSettings(self.path)
        good = dict(DEFAULT_WORK_SCHEDULE, enabled=True)
        for broken in ({"mode": "overtime"}, {"start": "25:00"}, {"start": "17:00", "end": "09:00"},
                       {"start": "09:00", "end": "09:00"}, {"days": []}, {"days": [7]}, {"start": "9am"},
                       {"enabled": "yes"}):
            with self.subTest(broken=broken), self.assertRaises(ValueError):
                settings.set_work_schedule({**good, **broken})
        self.assertEqual(settings.work_schedule(), DEFAULT_WORK_SCHEDULE)


class DayScheduleTests(unittest.TestCase):
    """The schedule holds on its ticked days only, never on a holiday, and not at all while off."""

    ON = {"enabled": True, "mode": "working", "start": "09:00", "end": "17:00", "days": [0, 1, 2, 3, 4]}
    WEDNESDAY, SATURDAY = "2026-10-14", "2026-10-17"

    def test_on_a_ticked_day_it_holds(self):
        self.assertEqual(day_schedule(self.ON, self.WEDNESDAY), WORKING)

    def test_not_on_a_day_left_unticked(self):
        self.assertIsNone(day_schedule(self.ON, self.SATURDAY))

    def test_not_while_switched_off(self):
        self.assertIsNone(day_schedule({**self.ON, "enabled": False}, self.WEDNESDAY))

    def test_not_on_a_holiday(self):
        self.assertIsNone(day_schedule(self.ON, self.WEDNESDAY, {"name": "Thanksgiving"}))


class StoreScheduleTests(SeriesDay):
    """The store plans with the schedule it is given, notes a task placed inside working hours, and keeps Work
    repeats off a holiday."""

    def titles_on(self, day):
        with sqlite3.connect(self.path) as connection:
            return {row[0] for row in connection.execute("SELECT title FROM daily_items WHERE item_date = ?", (day,))}

    def test_the_days_plans_keep_working_hours_free(self):
        self.store.schedule_for = lambda day: WORKING
        self.store.create_daily_item({**self.task("Report", None, 60), "domain": "work"})
        self.store.create_daily_item(self.task("Read", None, 45))
        self.store.create_recorded_plan(self.today)
        day = self.store.bootstrap_day(self.today)
        for variant in day["variants"]:
            self.assertIn("planScheduleWorking", [note["key"] for note in variant["notes"]], variant["slug"])
            for entry in self.store.bootstrap_day(self.today, variant["id"])["entries"]:
                start = _minutes(entry["start_time"])
                self.assertFalse(overlaps((start, start + entry["duration_minutes"]), "09:00", "17:00"), entry["title"])
        self.assertEqual(self.store.day_rules(self.today).working, ("09:00", "17:00"))

    def test_a_task_placed_inside_working_hours_by_hand_saves_with_a_note(self):
        self.store.schedule_for = lambda day: WORKING if day == self.today else None
        self.store.create_daily_item(self.task("Dentist", "10:00", 30))
        self.store.create_daily_item(self.task("Run", "20:00", 30))
        found = {item["title"]: item["workingHours"] for item in self.store.daily_items(self.today)}
        self.assertEqual(found, {"Dentist": {"start": "09:00", "end": "17:00"}, "Run": None})

    def test_work_repeats_are_not_carried_onto_a_holiday(self):
        self.repeat_day("Standup", days_ago(1), domain="work")
        self.repeat_day("Stretch", days_ago(1), domain="life", start="06:30")
        self.store.holiday_for = lambda day: {"name": "Thanksgiving"} if day == self.today else None
        self.store.create_recorded_plan(self.today)
        self.assertEqual(self.titles_on(self.today), {"Stretch"})

    def test_on_any_other_day_work_repeats_are_carried_as_before(self):
        self.repeat_day("Standup", days_ago(1), domain="work")
        self.store.holiday_for = lambda day: {"name": "Thanksgiving"} if day == self.tomorrow else None
        self.store.create_recorded_plan(self.today)
        self.assertEqual(self.titles_on(self.today), {"Standup"})


class ScheduleRouteTests(SeriesDay):
    """Settings › Schedule reads and keeps the work schedule, and today's proposed plans follow a change at once."""

    EVERY_DAY = {"enabled": True, "mode": "working", "start": "09:00", "end": "17:00", "days": [0, 1, 2, 3, 4, 5, 6]}

    def test_the_schedule_is_off_until_set_and_kept_once_set(self):
        self.assertEqual(self.client.get("/api/schedule").json()["schedule"], DEFAULT_WORK_SCHEDULE)
        kept = self.client.put("/api/schedule", json=self.EVERY_DAY)
        self.assertEqual(kept.status_code, 200)
        self.assertEqual(kept.json()["schedule"], self.EVERY_DAY)
        self.assertEqual(self.client.get("/api/schedule").json()["schedule"], self.EVERY_DAY)

    def test_a_schedule_that_isnt_whole_is_refused_and_nothing_changes(self):
        refused = self.client.put("/api/schedule", json={**self.EVERY_DAY, "end": "08:00"})
        self.assertEqual(refused.status_code, 422)
        self.assertEqual(self.client.get("/api/schedule").json()["schedule"], DEFAULT_WORK_SCHEDULE)

    def test_todays_proposed_plans_are_made_again_under_the_new_schedule(self):
        for title in ("Read", "Sketch"):
            self.client.post("/api/daily-items", json=self.task(title, None, 45))
        self.client.post("/api/plan/generate", json={"date": self.today})
        self.client.put("/api/schedule", json=self.EVERY_DAY)
        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        for variant in day["variants"]:
            self.assertIn("planScheduleWorking", [note["key"] for note in variant["notes"]], variant["slug"])


if __name__ == "__main__":
    unittest.main()
