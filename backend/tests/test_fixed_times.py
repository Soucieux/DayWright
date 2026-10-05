import sqlite3
import unittest

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.conversation import _context
from backend.app.planner import PlanItem, day_load
from backend.tests.test_ava_creates import AvaCreates


class FreeTimeTests(unittest.TestCase):
    def test_a_fixed_task_outside_09_00_to_22_00_leaves_the_days_free_time_as_it_was(self):
        def free(*items):
            return day_load(list(items), "07:00")["freeMinutes"]

        self.assertEqual(free(PlanItem("22:30", "Stretch", "", "life", 30)), free())
        self.assertEqual(free(PlanItem("06:30", "Run", "", "life", 30)), free())
        self.assertEqual(free(PlanItem("21:30", "Read", "", "life", 60)), free() - 30)


class FixedTimesOutsideTheDayTests(AvaCreates):
    """A fixed start may be at any hour; only plans keep to 09:00–22:00, for the tasks they place."""

    def form_task(self, title, start=None, minutes=30):
        return {"date": self.today, "title": title, "detail": "", "domain": "life", "startTime": start,
                "durationMinutes": minutes, "constraintKind": "fixed" if start else "flexible", "repeatKind": "none",
                "goalId": None}

    def listed_on_today(self):
        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        return {item["title"]: item["start_time"] for item in day["dayItems"]}

    def test_a_fixed_task_from_the_form_at_06_30_or_22_30_is_saved_and_listed_on_today(self):
        for title, start in (("Run", "06:30"), ("Stretch", "22:30")):
            saved = self.client.post("/api/daily-items", json=self.form_task(title, start))
            self.assertEqual(saved.status_code, 200, saved.text)

        self.assertEqual(self.listed_on_today(), {"Run": "06:30", "Stretch": "22:30"})

    def test_ava_adds_a_fixed_task_at_06_30(self):
        action = self.chat("Add Morning run today at 06:30 for 30 min")["proposedAction"]

        self.assertEqual((action["actionType"], action["payload"]["startTime"]), ("add_item", "06:30"))
        self.confirm(action)
        self.assertEqual(self.listed_on_today(), {"Morning run": "06:30"})

    def test_ava_moves_a_task_to_06_30(self):
        self.client.post("/api/daily-items", json=self.form_task("Gym", "10:00", 60))

        action = self.chat("Move Gym to 06:30")["proposedAction"]

        self.assertEqual((action["actionType"], action["payload"]["startTime"]), ("move_item", "06:30"))
        self.confirm(action)
        self.assertEqual(self.listed_on_today(), {"Gym": "06:30"})

    def test_ava_refuses_a_fixed_time_only_when_it_runs_past_midnight(self):
        reply = self.chat("Add Night shift today at 23:30 for 60 min")

        self.assertIsNone(reply["proposedAction"])
        self.assertIn("past midnight", reply["assistantMessage"]["content"])
        self.assertIn("Nothing was changed.", reply["assistantMessage"]["content"])

    def test_avas_context_says_a_fixed_start_may_be_at_any_hour(self):
        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()

        line = _context(day).splitlines()[0]

        self.assertIn("Plans place tasks without a time between 09:00 and 22:00", line)
        self.assertIn("a fixed start may be at any hour", line)

    def test_plans_place_only_tasks_without_a_time_and_only_between_09_00_and_22_00(self):
        for task in (self.form_task("Run", "06:30"), self.form_task("Stretch", "22:30"),
                     self.form_task("Read", minutes=60), self.form_task("Tidy", minutes=60)):
            self.assertEqual(self.client.post("/api/daily-items", json=task).status_code, 200)

        self.assertEqual(self.client.post("/api/plan/generate", json={"date": self.today}).status_code, 200)

        with sqlite3.connect(self.path) as connection:
            entries = connection.execute(
                """SELECT e.title, e.start_time, e.duration_minutes FROM plan_entries e
                   JOIN plan_variants v ON v.id = e.variant_id JOIN plan_sets s ON s.id = v.plan_set_id
                   WHERE s.plan_date = ?""", (self.today,)).fetchall()
        self.assertTrue(entries)
        for title, start, minutes in entries:
            begin = int(start[:2]) * 60 + int(start[3:])
            if title in ("Run", "Stretch"):
                self.assertEqual(start, {"Run": "06:30", "Stretch": "22:30"}[title])
            else:
                self.assertTrue(9 * 60 <= begin and begin + minutes <= 22 * 60, (title, start))


if __name__ == "__main__":
    unittest.main()
