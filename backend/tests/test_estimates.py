import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.database import Database
from backend.app.estimates import parse_minutes, refine_estimate


def task(title, domain="learning", minutes=None, start=None):
    """A task as the form sends it, with no length unless one is given."""
    return {"date": date.today().isoformat(), "title": title, "detail": "", "domain": domain, "startTime": start,
            "durationMinutes": minutes, "constraintKind": "fixed" if start else "flexible", "repeatKind": "none",
            "goalId": None}


class FakeModel:
    """A local model that gives one answer, or says it isn't running."""

    def __init__(self, answer, mode="local-model"):
        self.answer, self.mode, self.prompts = answer, mode, []

    def reply(self, message, context, system_prompt=None):
        self.prompts.append((message, context, system_prompt))
        return self.answer, self.mode


class EstimateTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "estimates.sqlite3"
        self.store = Database(self.path)

    def stored(self, item_id):
        return next(item for item in self.store.daily_items(date.today().isoformat()) if item["id"] == item_id)

    def facts(self, item):
        return item["duration_minutes"], item["durationSource"], item["estimatedBy"], item["estimateBasis"]

    def move_back(self, items, days=1):
        """Past days are read-only through the store, so earlier tasks are moved back directly."""
        with sqlite3.connect(self.path) as connection:
            for item in items:
                connection.execute("UPDATE daily_items SET item_date = ? WHERE id = ?",
                                   ((date.today() - timedelta(days=days)).isoformat(), item["id"]))

    def test_a_task_without_a_length_gets_its_area_agents_default_estimate(self):
        item = self.store.create_daily_item(task("Read chapter"))
        self.assertEqual(self.facts(item), (30, "estimate", "learning", "default"))

    def test_the_estimate_follows_the_lengths_you_gave_the_same_task_before(self):
        self.move_back([self.store.create_daily_item(task("Read chapter", minutes=minutes)) for minutes in (40, 50, 45)])
        item = self.store.create_daily_item(task("read chapter"))
        self.assertEqual(self.facts(item), (45, "estimate", "learning", "history"))

    def test_the_estimate_remembers_lengths_you_gave_the_task_long_ago(self):
        self.move_back([self.store.create_daily_item(task("Piano", minutes=minutes)) for minutes in (40, 40)], days=400)
        item = self.store.create_daily_item(task("Piano"))
        self.assertEqual(self.facts(item), (40, "estimate", "learning", "history"))

    def test_otherwise_the_estimate_follows_the_areas_usual_length(self):
        self.move_back([self.store.create_daily_item(task("Essay", minutes=35)),
                        self.store.create_daily_item(task("Notes", minutes=35)),
                        self.store.create_daily_item(task("Report", "work", minutes=90))])
        item = self.store.create_daily_item(task("Read chapter"))
        self.assertEqual(self.facts(item), (35, "estimate", "learning", "area"))

    def test_a_length_you_give_is_yours_and_at_least_30_minutes(self):
        item = self.store.create_daily_item(task("Email", "work", 40))
        self.assertEqual(self.facts(item), (40, "user", None, None))
        with self.assertRaisesRegex(ValueError, "at least 30 minutes"):
            self.store.create_daily_item(task("Email", "work", 10))

    def test_editing_keeps_an_estimate_until_you_give_a_length(self):
        item = self.store.create_daily_item(task("Read chapter"))
        kept = self.store.update_daily_item(item["id"], {**task("Read chapter, part 2"), "status": "planned"})
        self.assertEqual(self.facts(kept), (30, "estimate", "learning", "default"))
        mine = self.store.update_daily_item(item["id"], {**task("Read chapter", minutes=30), "status": "planned"})
        self.assertEqual(self.facts(mine), (30, "user", None, None))

    def test_minutes_are_read_from_the_models_answer(self):
        self.assertEqual(parse_minutes("About 50 minutes."), 50)
        self.assertEqual(parse_minutes("1.5 hours"), 90)
        self.assertEqual(parse_minutes("约 40 分钟"), 40)
        self.assertEqual(parse_minutes("47"), 45)
        self.assertEqual(parse_minutes("2000 minutes"), 480)
        self.assertEqual(parse_minutes("2 minutes"), 5)
        self.assertIsNone(parse_minutes("Hard to say."))

    def test_the_area_agent_asks_the_model_and_its_answer_replaces_the_provisional_estimate(self):
        item = self.store.create_daily_item(task("Write the essay outline"))
        model = FakeModel("About 50 minutes.")

        self.assertTrue(refine_estimate(self.store, model, item["id"]))

        self.assertEqual(self.facts(self.stored(item["id"])), (50, "estimate", "learning", "model"))
        message, _, role = model.prompts[0]
        self.assertIn("Write the essay outline", message)
        self.assertIn("Learning agent", role)

    def test_nothing_changes_when_the_model_is_off_or_the_length_is_yours(self):
        estimated = self.store.create_daily_item(task("Read chapter"))
        self.assertFalse(refine_estimate(self.store, FakeModel("The chat model is not available.", "rules"), estimated["id"]))
        mine = self.store.create_daily_item(task("Email", "work", 45))
        self.assertFalse(refine_estimate(self.store, FakeModel("40 minutes"), mine["id"]))
        self.assertEqual(self.facts(self.stored(estimated["id"])), (30, "estimate", "learning", "default"))
        self.assertEqual(self.facts(self.stored(mine["id"])), (45, "user", None, None))

    def test_a_fixed_task_keeps_its_estimate_when_the_models_would_overlap_another_task(self):
        call = self.store.create_daily_item(task("Call", "work", start="09:00"))
        self.store.create_daily_item(task("Stand-up", "work", 30, start="09:30"))
        self.assertFalse(refine_estimate(self.store, FakeModel("60 minutes"), call["id"]))
        self.assertEqual(self.stored(call["id"])["duration_minutes"], 30)


if __name__ == "__main__":
    unittest.main()
