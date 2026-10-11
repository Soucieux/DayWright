import unittest

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.planner import DayRules, PlanItem, build_recorded_variants, day_load, minutes_after_midnight


def untimed(title, domain, minutes, estimated=False):
    return PlanItem(None, title, "", domain, minutes, estimated=estimated)


def fixed(start, title, domain, minutes):
    return PlanItem(start, title, "", domain, minutes, "fixed")


def spans(variant):
    """Each of a plan's tasks by title: its start and end, in minutes after midnight."""
    return {item.title: (minutes_after_midnight(item.start), minutes_after_midnight(item.start) + item.duration_minutes)
            for item in variant["items"]}


def keys(variant):
    return [note["key"] for note in variant["notes"]]


DAY = (untimed("Report", "work", 90), untimed("Read", "learning", 60), untimed("Walk", "life", 30),
       untimed("Sketch", "project", 45), untimed("Email", "work", 30))


class KeepFreeTests(unittest.TestCase):
    """A rule keeping a time free: no plan places a task in it; a task the user fixed there stays."""

    RULES = DayRules(free=(("10:00", "12:00"),))

    def test_no_plan_places_a_task_in_the_time_kept_free(self):
        for variant in build_recorded_variants(DAY, earliest="09:00", rules=self.RULES):
            for title, (start, end) in spans(variant).items():
                self.assertFalse(start < 12 * 60 and 10 * 60 < end, f"{variant['slug']}: {title} {start}-{end}")
            self.assertIn("planRuleFree", keys(variant), variant["slug"])

    def test_the_time_kept_free_is_not_a_task_or_a_meal_of_the_plan(self):
        balanced = build_recorded_variants(DAY, earliest="09:00", rules=self.RULES)[0]
        self.assertEqual(set(spans(balanced)), {item.title for item in DAY})
        self.assertEqual({meal.title for meal in balanced["meals"]}, {"Lunch", "Dinner"})
        note = next(note for note in balanced["notes"] if note["key"] == "planRuleFree")
        self.assertEqual(note["values"], {"start": "10:00", "end": "12:00"})
        self.assertEqual(note["text"], "Keeps 10:00–12:00 free, as your rule says.")

    def test_a_task_the_user_fixed_in_the_time_kept_free_stays_and_the_rest_of_it_stays_free(self):
        day = (fixed("10:30", "Dentist", "life", 30), untimed("Read", "learning", 60), untimed("Report", "work", 60))
        for variant in build_recorded_variants(day, earliest="09:00", rules=self.RULES):
            placed = spans(variant)
            self.assertEqual(placed["Dentist"], (10 * 60 + 30, 11 * 60), variant["slug"])
            for title in ("Read", "Report"):
                start, end = placed[title]
                self.assertFalse(start < 12 * 60 and 10 * 60 < end, f"{variant['slug']}: {title}")

    def test_time_kept_free_counts_in_the_days_load(self):
        load = day_load(DAY, "09:00", rules=self.RULES)
        self.assertEqual(load["freeMinutes"], day_load(DAY, "09:00")["freeMinutes"] - 120)


class FinishByTests(unittest.TestCase):
    """A rule to finish by a time: no plan places a task ending after it; a task the user fixed later stays."""

    RULES = DayRules(finish_by="17:00")

    def test_no_plan_places_a_task_ending_after_the_time(self):
        for variant in build_recorded_variants(DAY, earliest="09:00", rules=self.RULES):
            for title, (start, end) in spans(variant).items():
                self.assertLessEqual(end, 17 * 60, f"{variant['slug']}: {title}")
            self.assertIn("planRuleFinish", keys(variant), variant["slug"])

    def test_the_note_says_the_time(self):
        balanced = build_recorded_variants(DAY, earliest="09:00", rules=self.RULES)[0]
        note = next(note for note in balanced["notes"] if note["key"] == "planRuleFinish")
        self.assertEqual((note["values"], note["text"]), ({"time": "17:00"}, "Done by 17:00, as your rule says."))

    def test_a_task_the_user_fixed_after_the_time_stays(self):
        day = (fixed("19:00", "Class", "learning", 60), untimed("Read", "learning", 60))
        for variant in build_recorded_variants(day, earliest="09:00", rules=self.RULES):
            placed = spans(variant)
            self.assertEqual(placed["Class"], (19 * 60, 20 * 60))
            self.assertLessEqual(placed["Read"][1], 17 * 60)

    def test_tasks_that_cannot_finish_by_the_time_say_so_and_name_the_rule(self):
        with self.assertRaisesRegex(ValueError, "16:00, the time your rule has the day done by"):
            build_recorded_variants((untimed("Long", "work", 240),), earliest="13:00", rules=DayRules(finish_by="16:00"))

    def test_the_earlier_of_two_times_holds(self):
        self.assertEqual(DayRules(finish_by="17:00").end_minutes, 17 * 60)
        self.assertEqual(DayRules(finish_by="23:00").end_minutes, 22 * 60)
        self.assertEqual(DayRules().end_minutes, 22 * 60)


class KeepOffTests(unittest.TestCase):
    """A rule keeping an area or a task off a day: no plan places such a task without a start time; one the user
    fixed stays."""

    def test_no_plan_places_a_task_of_the_area_kept_off(self):
        for variant in build_recorded_variants(DAY, earliest="09:00", rules=DayRules(off_areas=frozenset({"work"}))):
            self.assertEqual(set(spans(variant)), {"Read", "Walk", "Sketch"}, variant["slug"])
            note = next(note for note in variant["notes"] if note["key"] == "planRuleOff")
            self.assertEqual(note["values"], {"tasks": ["Report", "Email"]})

    def test_no_plan_places_the_task_kept_off_named_in_any_case(self):
        for variant in build_recorded_variants(DAY, earliest="09:00", rules=DayRules(off_tasks=frozenset({"walk"}))):
            self.assertNotIn("Walk", spans(variant), variant["slug"])

    def test_a_task_the_user_fixed_stays(self):
        day = (fixed("10:00", "Standup", "work", 30), untimed("Report", "work", 60), untimed("Read", "learning", 60))
        for variant in build_recorded_variants(day, earliest="09:00", rules=DayRules(off_areas=frozenset({"work"}))):
            self.assertEqual(set(spans(variant)), {"Standup", "Read"}, variant["slug"])

    def test_a_day_whose_every_task_is_kept_off_has_no_plans_to_make(self):
        with self.assertRaisesRegex(ValueError, "rules keep every task off"):
            build_recorded_variants((untimed("Report", "work", 60),), rules=DayRules(off_areas=frozenset({"work"})))

    def test_tasks_kept_off_need_no_free_time(self):
        rules = DayRules(off_areas=frozenset({"work"}))
        self.assertEqual(day_load(DAY, "09:00", rules=rules)["taskMinutes"], 60 + 30 + 45)


class NoRulesTests(unittest.TestCase):
    def test_without_rules_plans_are_as_before(self):
        self.assertEqual(build_recorded_variants(DAY, earliest="09:00"),
                         build_recorded_variants(DAY, earliest="09:00", rules=DayRules()))


if __name__ == "__main__":
    unittest.main()
