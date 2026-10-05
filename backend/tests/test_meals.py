import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.agents import AgentOrchestrator
from backend.app.database import Database
from backend.app.main import create_app
from backend.app.meals import Meal, meals_on, one_day, one_day_changes, standing
from backend.tests.test_api import FakeEmbeddingGateway, FakeGateway

USUAL = (Meal("Lunch", "12:00", 60), Meal("Dinner", "18:00", 60))


class MealDay(unittest.TestCase):
    """A fresh account, its service and its store, with plans placing tasks from 09:00."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = Path(self.temp_dir.name) / "meals.sqlite3"
        self.client = TestClient(create_app(database_path=self.path, gateway=FakeGateway(),
                                            embedding_gateway=FakeEmbeddingGateway()))
        self.store = Database(self.path)
        self.today = date.today().isoformat()
        self.yesterday = (date.today() - timedelta(days=1)).isoformat()
        self.tomorrow = (date.today() + timedelta(days=1)).isoformat()
        clock = patch("backend.app.database._local_time", return_value="07:00")
        clock.start()
        self.addCleanup(clock.stop)

    def task(self, title, start, minutes=60):
        return {"date": self.today, "title": title, "detail": "", "domain": "learning", "startTime": start,
                "durationMinutes": minutes, "constraintKind": "fixed" if start else "flexible", "repeatKind": "none",
                "goalId": None}


class DayMealsTests(MealDay):
    """The store keeps the meal times, and every reader takes a day's from it."""

    def test_a_day_has_lunch_and_dinner_at_their_usual_hours_until_one_is_moved(self):
        self.assertEqual(self.store.day_meals(self.today), USUAL)
        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        self.assertEqual(day["meals"], [{"title": "Lunch", "start_time": "12:00", "duration_minutes": 60},
                                        {"title": "Dinner", "start_time": "18:00", "duration_minutes": 60}])

    def test_a_standing_move_holds_from_its_day_on_and_earlier_days_keep_theirs(self):
        self.store.save_meal("lunch", "12:30", 45, from_day=self.today)

        self.assertEqual(self.store.day_meals(self.today)[0], Meal("Lunch", "12:30", 45))
        self.assertEqual(self.store.day_meals(self.tomorrow)[0], Meal("Lunch", "12:30", 45))
        self.assertEqual(self.store.day_meals(self.yesterday), USUAL)

    def test_a_one_day_move_holds_on_its_date_alone(self):
        self.store.save_meal("dinner", "19:00", 60, day=self.tomorrow)

        self.assertEqual(self.store.day_meals(self.tomorrow)[1], Meal("Dinner", "19:00", 60))
        self.assertEqual(self.store.day_meals(self.today), USUAL)

    def test_a_past_day_keeps_the_meals_its_plan_saved(self):
        # A plan set at 14:00, when lunch was over, kept dinner alone.
        self.client.post("/api/daily-items", json=self.task("Seminar", None, 60))
        with patch("backend.app.database._local_time", return_value="14:00"):
            plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": plan["variants"][0]["id"]})
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE daily_items SET item_date = ?", (self.yesterday,))
            connection.execute("UPDATE plan_sets SET plan_date = ?", (self.yesterday,))
            connection.execute("UPDATE daily_confirmations SET plan_date = ?", (self.yesterday,))
        self.store.save_meal("dinner", "19:30", 60, from_day=self.yesterday)

        self.assertEqual(self.store.day_meals(self.yesterday), (Meal("Dinner", "18:00", 60),))

    def test_a_moved_meal_is_kept_free_from_tasks_and_in_every_plan(self):
        self.store.save_meal("lunch", "13:00", 60, from_day=self.today)

        refused = self.client.post("/api/daily-items", json=self.task("Call", "13:15", 30))
        self.assertEqual(refused.status_code, 422)
        self.assertIn("13:00–14:00 is kept for lunch", refused.json()["detail"])
        self.assertEqual(self.client.post("/api/daily-items", json=self.task("Read", "12:00")).status_code, 200)
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        for variant in plan["variants"]:
            self.assertIn({"title": "Lunch", "start_time": "13:00", "duration_minutes": 60}, variant["meals"])


class MealTimesTests(unittest.TestCase):
    def test_lunch_and_dinner_keep_their_hours_when_nothing_is_saved(self):
        self.assertEqual(meals_on("2026-10-05", {}), (Meal("Lunch", "12:00", 60), Meal("Dinner", "18:00", 60)))

    def test_a_standing_change_holds_from_its_day_on_and_not_before(self):
        settings = standing({}, "lunch", "12:30", 45, "2026-10-03")

        self.assertEqual(meals_on("2026-10-03", settings), (Meal("Lunch", "12:30", 45), Meal("Dinner", "18:00", 60)))
        self.assertEqual(meals_on("2026-11-20", settings)[0], Meal("Lunch", "12:30", 45))
        self.assertEqual(meals_on("2026-10-02", settings)[0], Meal("Lunch", "12:00", 60))

    def test_a_later_standing_change_takes_over_from_its_own_day(self):
        settings = standing(standing({}, "dinner", "19:00", 60, "2026-10-03"), "dinner", "18:30", 60, "2026-10-08")

        self.assertEqual(meals_on("2026-10-05", settings)[1], Meal("Dinner", "19:00", 60))
        self.assertEqual(meals_on("2026-10-08", settings)[1], Meal("Dinner", "18:30", 60))

    def test_a_one_day_change_wins_for_its_date_alone(self):
        settings = one_day(standing({}, "lunch", "12:30", 60, "2026-10-03"), "lunch", "13:00", 60, "2026-10-09")

        self.assertEqual(meals_on("2026-10-09", settings)[0], Meal("Lunch", "13:00", 60))
        self.assertEqual(meals_on("2026-10-10", settings)[0], Meal("Lunch", "12:30", 60))

    def test_a_later_standing_change_replaces_one_day_changes_from_its_day_on(self):
        exceptions = one_day(one_day({}, "lunch", "13:00", 60, "2026-10-05"), "lunch", "13:30", 60, "2026-10-09")
        exceptions = one_day(exceptions, "dinner", "19:00", 60, "2026-10-09")

        settings = standing(exceptions, "lunch", "11:30", 60, "2026-10-07")

        self.assertEqual(one_day_changes(exceptions, "lunch", "2026-10-07"), [("2026-10-09", Meal("Lunch", "13:30", 60))])
        self.assertEqual(meals_on("2026-10-05", settings)[0], Meal("Lunch", "13:00", 60))
        self.assertEqual(meals_on("2026-10-09", settings), (Meal("Lunch", "11:30", 60), Meal("Dinner", "19:00", 60)))

    def test_a_change_leaves_the_settings_it_was_given_as_they_were(self):
        settings = {}
        standing(settings, "lunch", "12:30", 60, "2026-10-03")
        self.assertEqual(settings, {})

    def test_a_meal_knows_when_it_ends(self):
        self.assertEqual(Meal("Dinner", "19:00", 75).end, "20:15")


class AvaMealChangeTests(MealDay):
    """A meal moves through Ava: checked first, proposed, and applied with the plan on Confirm."""

    def chat(self, message):
        return self.client.post("/api/chat", json={"date": self.today, "message": message}).json()

    def confirm(self, action):
        decided = self.client.post(f"/api/actions/{action['id']}", json={"decision": "confirmed"})
        self.assertEqual(decided.status_code, 200, decided.text)
        return decided.json()

    def set_plan_placing(self, title, start, minutes=60):
        """Set today's plan with one task the user gave no start, placed by the plan at `start`."""
        self.client.post("/api/daily-items", json=self.task(title, None, minutes))
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": plan["variants"][0]["id"]})
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE plan_entries SET start_time = ? WHERE title = ?", (start, title))

    def entry(self, title):
        """When the set plan places a task, and for how long."""
        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        return next((entry["start_time"], entry["duration_minutes"]) for entry in day["entries"] if entry["title"] == title)

    def test_lunch_from_now_on_is_proposed_for_good_and_saved_only_on_confirm(self):
        action = self.chat("Lunch at 12:30 from now on")["proposedAction"]

        payload = action["payload"]
        self.assertEqual((action["actionType"], payload["meal"], payload["start"], payload["minutes"], payload["scope"]),
                         ("change_meal", "lunch", "12:30", 60, "standing"))
        self.assertEqual(self.store.day_meals(self.today), USUAL)
        self.confirm(action)
        self.assertEqual(self.store.day_meals(self.tomorrow)[0], Meal("Lunch", "12:30", 60))

    def test_dinner_on_friday_is_proposed_for_that_day_alone(self):
        friday = (date.today() + timedelta(days=(4 - date.today().weekday()) % 7)).isoformat()

        payload = self.chat("Dinner 19:00–20:00 on Friday")["proposedAction"]["payload"]

        self.assertEqual((payload["scope"], payload["date"], payload["start"], payload["minutes"]), ("day", friday, "19:00", 60))

    def test_lunch_from_friday_on_is_a_standing_change_from_friday(self):
        friday = date.today() + timedelta(days=(4 - date.today().weekday()) % 7)

        action = self.chat("Lunch 12:30–13:30 from Friday on")["proposedAction"]

        self.assertEqual((action["payload"]["scope"], action["payload"]["date"]), ("standing", friday.isoformat()))
        self.confirm(action)
        self.assertEqual(self.store.day_meals((friday + timedelta(days=7)).isoformat())[0], Meal("Lunch", "12:30", 60))
        self.assertEqual(self.store.day_meals((friday - timedelta(days=1)).isoformat())[0], USUAL[0])

    def test_a_meal_that_would_cross_midnight_is_explained_and_not_proposed(self):
        for message in ("Dinner 23:30–00:30 today", "Dinner 23:30–00:30"):
            reply = self.chat(message)

            self.assertIsNone(reply["proposedAction"], message)
            self.assertIn("23:30–00:30 would run past midnight", reply["assistantMessage"]["content"], message)
            self.assertNotIn("clarify-meal-scope", [notice["kind"] for notice in reply["notices"]], message)

    def test_a_meal_ending_at_midnight_keeps_the_range_asked_for(self):
        self.store.save_meal("dinner", "18:00", 45, from_day=self.today)

        action = self.chat("Dinner 23:00–24:00 today")["proposedAction"]

        self.assertEqual((action["payload"]["start"], action["payload"]["minutes"]), ("23:00", 60))
        self.assertIn("23:00–24:00", action["explanation"])

    def test_a_standing_change_names_the_one_day_changes_it_replaces(self):
        self.store.save_meal("lunch", "13:00", 60, day=self.tomorrow)

        action = self.chat("Lunch 12:30–13:30 from now on")["proposedAction"]

        self.assertEqual(action["payload"]["replaces"], [{"date": self.tomorrow, "start": "13:00", "minutes": 60}])
        self.assertIn(f"It replaces the one-day lunch time on {self.tomorrow} (13:00–14:00).", action["explanation"])
        self.confirm(action)
        self.assertEqual(self.store.day_meals(self.tomorrow)[0], Meal("Lunch", "12:30", 60))

    def test_ava_asks_whether_a_meal_moves_for_good_or_for_one_day(self):
        reply = self.chat("Move lunch to 12:30")

        self.assertIsNone(reply["proposedAction"])
        self.assertIn("clarify-meal-scope", [notice["kind"] for notice in reply["notices"]])

    def test_a_past_day_whose_plan_left_out_lunch_is_refused_rather_than_failing(self):
        # A plan set at 14:00, when lunch was over, kept dinner alone.
        self.client.post("/api/daily-items", json=self.task("Seminar", None, 60))
        with patch("backend.app.database._local_time", return_value="14:00"):
            plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": plan["variants"][0]["id"]})
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE daily_items SET item_date = ?", (self.yesterday,))
            connection.execute("UPDATE plan_sets SET plan_date = ?", (self.yesterday,))
            connection.execute("UPDATE daily_confirmations SET plan_date = ?", (self.yesterday,))

        reply = self.chat(f"Lunch 12:30–13:30 on {self.yesterday}")

        self.assertIsNone(reply["proposedAction"])
        self.assertIn("Past days keep the lunch times they had", reply["assistantMessage"]["content"])

    def test_a_task_in_the_way_is_named_and_nothing_is_saved(self):
        self.client.post("/api/daily-items", json=self.task("Call", "13:30", 30))

        reply = self.chat("Lunch at 13:00 from now on")

        self.assertIsNone(reply["proposedAction"])
        self.assertIn("“Call”", reply["assistantMessage"]["content"])
        self.assertEqual(self.store.day_meals(self.today), USUAL)

    def test_a_small_overlap_adjusts_todays_set_plan_and_says_what_changed(self):
        self.set_plan_placing("Read", "11:45")
        action = self.chat("Lunch 12:30–13:30 from now on")["proposedAction"]
        self.assertTrue(action["payload"]["planChanges"])

        with patch.object(AgentOrchestrator, "relay_task_change") as relayed:
            decided = self.confirm(action)

        self.assertEqual((decided["planUpdate"], decided["changes"]),
                         ("adjusted", [{"title": "Read", "from": "11:45–12:45", "to": "11:30–12:30"}]))
        self.assertEqual(self.entry("Read"), ("11:30", 60))
        self.assertTrue(relayed.called)

    def test_a_large_overlap_puts_todays_set_plan_up_for_review_and_changes_nothing_in_it(self):
        self.set_plan_placing("Read", "12:30")

        decided = self.confirm(self.chat("Lunch 12:30–13:30 from now on")["proposedAction"])

        self.assertEqual(decided["planUpdate"], "review")
        self.assertEqual(self.entry("Read"), ("12:30", 60))
        self.assertTrue(decided["review"]["options"])
        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        drafts = [variant for variant in day["variants"] if variant["id"] != day["confirmedVariantId"]]
        self.assertIn({"title": "Lunch", "start_time": "12:30", "duration_minutes": 60}, drafts[0]["meals"])

    def test_with_a_set_plan_todays_other_drafts_are_proposed_again_around_the_meal(self):
        for title in ("Read", "Walk"):
            self.client.post("/api/daily-items", json=self.task(title, None))
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        self.assertGreater(len(plan["variants"]), 1)
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": plan["variants"][0]["id"]})
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE plan_entries SET start_time = '09:00' WHERE title = 'Read' AND variant_id = ?",
                               (plan["variants"][0]["id"],))
            connection.execute("UPDATE plan_entries SET start_time = '10:00' WHERE title = 'Walk' AND variant_id = ?",
                               (plan["variants"][0]["id"],))

        decided = self.confirm(self.chat("Lunch 12:30–13:30 from now on")["proposedAction"])

        self.assertEqual(decided["planUpdate"], "updated")
        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        drafts = [variant for variant in day["variants"] if variant["id"] != day["confirmedVariantId"]]
        self.assertTrue(drafts)
        for variant in drafts:
            self.assertIn({"title": "Lunch", "start_time": "12:30", "duration_minutes": 60}, variant["meals"])

    def test_a_meal_moved_from_a_later_day_on_leaves_todays_drafts_as_they_were(self):
        self.client.post("/api/daily-items", json=self.task("Read", None))
        made = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        later = (date.today() + timedelta(days=3)).isoformat()

        decided = self.confirm(self.chat(f"Lunch 12:30–13:30 from {later} on")["proposedAction"])

        self.assertEqual(decided["planUpdate"], "none")
        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        self.assertEqual([variant["id"] for variant in day["variants"]], [variant["id"] for variant in made["variants"]])

    def test_a_day_with_no_set_plan_has_its_drafts_proposed_again(self):
        self.client.post("/api/daily-items", json=self.task("Read", None))
        self.client.post("/api/plan/generate", json={"date": self.today})

        decided = self.confirm(self.chat("Lunch at 13:00 from now on")["proposedAction"])

        self.assertEqual(decided["planUpdate"], "repropose")
        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        self.assertIn({"title": "Lunch", "start_time": "13:00", "duration_minutes": 60}, day["variants"][0]["meals"])
