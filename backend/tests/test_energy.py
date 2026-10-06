import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.agents import AgentOrchestrator, WORK_HEAVY_MINUTES
from backend.app.database import Database
from backend.app.main import create_app
from backend.app.periods import period_keys
from backend.tests.test_api import FakeEmbeddingGateway
from backend.tests.test_area_suggestion import ModelAnswering
from backend.tests.test_meals import MealDay


def logged(path, day, *readings):
    """Write a day's readings straight into the log, each a (level, "HH:MM") tap."""
    with sqlite3.connect(path) as connection:
        connection.executemany(
            "INSERT INTO energy_log (reading_date, level, reading_time, recorded_at) VALUES (?, ?, ?, ?)",
            [(day, level, time, f"{day}T{time}:00+00:00") for level, time in readings])


class EnergyDay(MealDay):
    def report(self, level):
        return self.client.put(f"/api/energy/{self.today}", json={"level": level})

    def add(self, title, area, minutes=60, start=None, day=None, **extra):
        made = self.client.post("/api/daily-items", json={**self.task(title, start, minutes), "domain": area,
                                                          "date": day or self.today, **extra})
        self.assertEqual(made.status_code, 200, made.text)
        return made.json()

    def bootstrap(self):
        return self.client.get("/api/bootstrap", params={"date": self.today}).json()


class EnergyLogTests(EnergyDay):
    """Each change is kept with its time; the day's average is what counts."""

    def test_each_change_is_kept_with_its_time_and_the_day_takes_their_average(self):
        self.report(2)
        with patch("backend.app.database._local_time", return_value="14:30"):
            saved = self.report(4).json()

        readings = [{"level": 2, "time": "07:00"}, {"level": 4, "time": "14:30"}]
        self.assertEqual(saved, {"date": self.today, "level": 4, "average": 3.0, "readings": readings})
        day = self.bootstrap()
        self.assertEqual((day["energy"], day["energyReadings"]), (3.0, readings))
        self.assertEqual(self.store.energy(self.today), 3.0)

    def test_an_unreported_day_stays_empty(self):
        day = self.bootstrap()
        self.assertEqual((day["energy"], day["energyReadings"]), (None, []))

    def test_another_days_energy_cant_change(self):
        for day in (self.yesterday, self.tomorrow):
            self.assertEqual(self.client.put(f"/api/energy/{day}", json={"level": 4}).status_code, 409)
            self.assertIsNone(self.store.energy(day))

    def test_a_level_outside_one_to_five_is_refused(self):
        for level in (0, 6):
            self.assertEqual(self.report(level).status_code, 422)
        self.assertIsNone(self.store.energy(self.today))

    def test_each_change_reaches_every_agent_and_summary_rebuilds_the_days_reports(self):
        self.client.post("/api/summaries", params={"date": self.today})
        keys = period_keys(date.today())
        self.assertTrue(all(self.store.saved_summary(kind, key) for kind, key in keys))
        with patch.object(AgentOrchestrator, "inspect_today", autospec=True,
                          side_effect=AgentOrchestrator.inspect_today) as looked:
            self.report(3)

        self.assertEqual([call.kwargs.get("agents") for call in looked.call_args_list], [None])
        self.assertEqual([self.store.saved_summary(kind, key) for kind, key in keys], [None, None, None])


class EnergyPlanOrderTests(EnergyDay):
    """Plans proposed after a change take the day's average: Lighter day first at 2 or below,
    Deep focus first at 4 or above, the agents' order between."""

    def setUp(self):
        super().setUp()
        self.add("Statistics chapter", "learning", 90)
        self.add("Quarterly report", "work", 90)
        self.add("Kitchen plans", "project", 60)
        self.add("Laundry", "life", 30)

    def plans(self):
        return self.client.post("/api/plan/generate", json={"date": self.today}).json()["variants"]

    def test_an_average_of_two_or_below_puts_lighter_day_first(self):
        self.report(1)
        self.report(3)
        plans = self.plans()
        self.assertEqual(plans[0]["slug"], "gentle")
        self.assertEqual(plans[0]["notes"][0]["key"], "planWhyLighterAdvised")

    def test_an_average_between_keeps_the_agents_order(self):
        self.report(2)
        self.report(3)
        self.assertEqual(self.store.energy(self.today), 2.5)
        self.assertEqual(self.plans()[0]["slug"], "balanced")

    def test_an_average_of_four_or_above_puts_focused_first(self):
        self.report(5)
        self.report(4)
        plans = self.plans()
        self.assertEqual(plans[0]["slug"], "focused")
        self.assertEqual(plans[0]["notes"][0]["key"], "planWhyHighEnergy")

    def test_an_earlier_days_reading_no_longer_stands_in_for_today(self):
        logged(self.path, (date.today() - timedelta(days=2)).isoformat(), (1, "09:00"))
        plans = self.plans()
        self.assertEqual(plans[0]["slug"], "balanced")
        self.assertFalse(any(finding.get("lighter") for run in self.bootstrap()["planRoute"]
                             for finding in run.get("findings") or []))

    def test_a_change_leaves_the_proposed_plans_and_the_set_plan_as_they_are(self):
        before = self.plans()
        self.report(5)
        self.assertEqual(self.bootstrap()["variants"], before)
        chosen = before[1]["id"]
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": chosen, "replaceExisting": False})
        self.report(1)
        day = self.bootstrap()
        self.assertEqual((day["confirmedVariantId"], [plan["id"] for plan in day["variants"]]),
                         (chosen, [plan["id"] for plan in before]))


class EnergyNotesTests(EnergyDay):
    """Each area agent's note on the day's average, only where it applies, and none in the middle."""

    def notes(self, area):
        return {note["kind"]: note["values"] for note in
                self.client.get(f"/api/areas/{area}", params={"date": self.today}).json()["notes"]
                if "energy" in note["kind"]}

    def everything(self):
        self.add("Spanish lesson", "learning", 45)
        self.add("Quarterly report", "work", 120)
        self.add("Inbox", "work", 90)
        goal = self.client.post("/api/goals", json={"title": "Kitchen renovation", "domain": "project"}).json()
        self.add("Pick tiles", "project", 60, day=self.tomorrow, goalId=goal["id"])
        self.add("Walk", "life", 30)

    def test_at_two_or_below_a_short_review_a_heavy_load_a_small_step_and_rest(self):
        self.everything()
        self.report(2)
        self.assertEqual(self.notes("learning"), {"energy-short-review": {"energy": 2.0, "taskTitle": "Spanish lesson"}})
        self.assertEqual(self.notes("work"), {"energy-heavy-load": {"energy": 2.0, "minutes": 210}})
        self.assertEqual(self.notes("project"), {"energy-small-step": {"energy": 2.0, "taskTitle": "Pick tiles"}})
        self.assertEqual(list(self.notes("life")), ["low-energy"])

    def test_at_four_or_above_a_harder_session_the_biggest_work_task_and_the_next_big_step(self):
        self.everything()
        self.report(4)
        self.assertEqual(self.notes("learning"), {"energy-harder-session": {"energy": 4.0, "taskTitle": "Spanish lesson"}})
        self.assertEqual(self.notes("work"), {"energy-biggest-work": {"energy": 4.0, "taskTitle": "Quarterly report",
                                                                      "minutes": 120}})
        self.assertEqual(self.notes("project"), {"energy-next-big-step": {"energy": 4.0, "taskTitle": "Pick tiles"}})
        self.assertEqual(self.notes("life"), {})

    def test_in_the_middle_no_area_says_anything_about_energy(self):
        self.everything()
        self.report(3)
        self.assertEqual([self.notes(area) for area in ("learning", "life", "work", "project")], [{}, {}, {}, {}])

    def test_each_note_needs_what_it_speaks_of(self):
        self.add("Inbox", "work", 90)
        self.assertLess(90, WORK_HEAVY_MINUTES)
        self.report(1)
        self.assertEqual([self.notes(area) for area in ("learning", "work", "project")], [{}, {}, {}])

    def test_the_notes_stay_on_the_area_pages_and_never_reach_ava(self):
        self.everything()
        self.report(2)
        self.assertFalse([notice for notice in self.bootstrap()["notices"] if notice["kind"].startswith("energy-")])


class AvaEnergyTests(unittest.TestCase):
    """Telling Ava how your energy is brings a small card; nothing is saved until Confirm, and only today."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "energy.sqlite3"
        self.gateway = ModelAnswering("The model's own words.")
        self.client = TestClient(create_app(database_path=self.path, gateway=self.gateway,
                                            embedding_gateway=FakeEmbeddingGateway()))
        self.store = Database(self.path)
        self.today = date.today().isoformat()
        clock = patch("backend.app.database._local_time", return_value="10:00")
        clock.start()
        self.addCleanup(clock.stop)

    def chat(self, message, day=None):
        return self.client.post("/api/chat", json={"date": day or self.today, "message": message}).json()

    def test_energy_four_brings_a_card_saved_only_on_confirm(self):
        reply = self.chat("energy 4")
        action = reply["proposedAction"]
        self.assertEqual((reply["assistantMessage"]["mode"], action["actionType"]), ("adjust", "set_energy"))
        self.assertEqual({key: action["payload"][key] for key in ("date", "level")}, {"date": self.today, "level": 4})
        self.assertTrue(reply["assistantMessage"]["content"].startswith("Add a reading of 4 to today's energy? Today's average becomes 4."),
                        "a reading, not 4 points")
        self.assertIsNone(self.store.energy(self.today))

        with patch.object(AgentOrchestrator, "inspect_today", autospec=True,
                          side_effect=AgentOrchestrator.inspect_today) as looked:
            decided = self.client.post(f"/api/actions/{action['id']}", json={"decision": "confirmed"})
        self.assertEqual(decided.status_code, 200, decided.text)
        self.assertEqual(self.store.energy(self.today), 4.0)
        self.assertEqual([call.kwargs.get("agents") for call in looked.call_args_list], [None])

    def test_the_words_say_the_level(self):
        cases = {"I'm drained": 1, "I'm so tired today": 2, "Energy: 3/5": 3, "my energy is 5": 5, "精力 4": 4}
        found = {message: (self.chat(message)["proposedAction"] or {}).get("payload", {}).get("level") for message in cases}
        self.assertEqual(found, cases)

    def test_a_dismissed_card_saves_nothing(self):
        action = self.chat("energy 2")["proposedAction"]
        self.client.post(f"/api/actions/{action['id']}", json={"decision": "dismissed"})
        self.assertIsNone(self.store.energy(self.today))

    def test_on_another_day_ava_refuses_in_words_with_no_card(self):
        for day in ((date.today() - timedelta(days=1)).isoformat(), (date.today() + timedelta(days=1)).isoformat()):
            reply = self.chat("energy 4", day)
            self.assertIsNone(reply["proposedAction"], day)
            self.assertIn("today only", reply["assistantMessage"]["content"])
            self.assertIsNone(self.store.energy(day))

    def test_a_card_made_for_another_day_is_refused_on_confirm(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        action = self.store.propose_action(self.store.thread(), "set_energy", {"date": yesterday, "level": 4},
                                           "Record energy 4.")
        self.assertEqual(self.client.post(f"/api/actions/{action['id']}", json={"decision": "confirmed"}).status_code, 409)
        self.assertIsNone(self.store.energy(yesterday))

    def test_other_messages_bring_no_energy_card(self):
        for message in ("What was my energy yesterday?", "I'm tired of this plan", "How is my energy?", "energy",
                        "Move Review to 4pm"):
            action = self.chat(message)["proposedAction"]
            self.assertFalse(action and action["actionType"] == "set_energy", message)
        self.assertEqual(self.chat("How does energy work?")["assistantMessage"]["model_mode"], "guide")

    def context(self):
        self.chat("What should I do next?")
        return next(call["context"] for call in reversed(self.gateway.calls) if call["message"] == "What should I do next?")

    def test_her_context_holds_todays_average_and_leans_short_and_easy_on_a_low_day(self):
        self.client.put(f"/api/energy/{self.today}", json={"level": 2})
        context = self.context()
        self.assertIn("Energy today: 2 out of 5, the average of 1 reading", context)
        self.assertIn("lean to short or easy tasks", context)

    def test_on_a_high_day_she_leans_to_the_hardest_or_most_important_task(self):
        self.client.put(f"/api/energy/{self.today}", json={"level": 5})
        self.client.put(f"/api/energy/{self.today}", json={"level": 4})
        context = self.context()
        self.assertIn("Energy today: 4.5 out of 5, the average of 2 readings", context)
        self.assertIn("lean to the hardest or most important task", context)

    def test_in_the_middle_or_unreported_she_leans_neither_way(self):
        self.assertIn("Energy today: not reported", self.context())
        self.client.put(f"/api/energy/{self.today}", json={"level": 3})
        context = self.context()
        self.assertIn("Energy today: 3 out of 5", context)
        self.assertNotIn("lean to", context)


class EnergySummaryTests(EnergyDay):
    """Summary's view of energy, from reported readings only, and its advice only with enough of them."""

    def setUp(self):
        super().setUp()
        monday = date.today() - timedelta(days=date.today().weekday() + 21)
        self.week = [(monday + timedelta(days=offset)).isoformat() for offset in range(7)]

    def day_of(self, offset, readings, outcomes):
        """Readings on a day of the week three weeks ago, and its tasks with their outcomes."""
        day = self.week[offset]
        logged(self.path, day, *readings)
        with sqlite3.connect(self.path) as connection:
            connection.executemany(
                """INSERT INTO daily_items (id, item_date, title, domain, duration_minutes, constraint_kind,
                       completion_status, created_at) VALUES (?, ?, ?, ?, 30, 'flexible', ?, ?)""",
                [(f"{day}-{index}", day, f"Task {index}", area, status, day)
                 for index, (area, status) in enumerate(outcomes)])
        return day

    def reports(self, offset=2):
        return self.client.post("/api/summaries", params={"date": self.week[offset]}).json()["reports"]

    def five_days(self):
        self.day_of(0, [(2, "09:00")], [("learning", "done"), ("learning", "skipped")])
        self.day_of(1, [(1, "09:00"), (3, "15:00")], [("learning", "partial"), ("work", "skipped")])
        self.day_of(2, [(4, "10:00")], [("learning", "done"), ("work", "done")])
        self.day_of(3, [(3, "08:00"), (5, "13:00")], [("learning", "done")])
        self.day_of(4, [(3, "11:00")], [("work", "partial")])
        logged(self.path, (date.fromisoformat(self.week[0]) - timedelta(days=3)).isoformat(), (4, "09:00"))

    def test_the_week_has_its_average_its_days_its_lowest_and_highest_and_its_trend(self):
        self.five_days()
        energy = self.reports()["week"]["energy"]
        self.assertEqual({key: energy[key] for key in ("start", "end", "average", "daysReported", "lowest", "highest")}, {
            "start": self.week[0], "end": self.week[6], "average": 3.0, "daysReported": 5,
            "lowest": {"date": self.week[0], "average": 2.0}, "highest": {"date": self.week[2], "average": 4.0}})
        self.assertEqual(energy["days"][1], {"date": self.week[1], "average": 2.0, "low": 1, "high": 3,
                                             "readings": [{"level": 1, "time": "09:00"}, {"level": 3, "time": "15:00"}]})
        self.assertEqual(energy["trend"], {"before": 4.0, "change": -1.0})

    def test_with_enough_days_the_fully_done_rate_on_low_days_is_set_against_other_days_and_advised_on(self):
        self.five_days()
        week = self.reports()["week"]
        comparison = week["energy"]["comparison"]
        self.assertEqual(comparison["low"], {"days": 2, "done": 1, "scheduled": 4, "rate": 25})
        self.assertEqual(comparison["other"], {"days": 3, "done": 3, "scheduled": 4, "rate": 75})
        self.assertEqual(comparison["areas"]["learning"], {"low": {"done": 1, "scheduled": 3, "rate": 33},
                                                           "other": {"done": 2, "scheduled": 2, "rate": 100}})
        advice = [item["content"] for item in week["suggestions"] if "energy" in item["content"]]
        self.assertEqual(len(advice), 1)
        self.assertIn("25%", advice[0])
        self.assertIn("75%", advice[0])

    def test_without_enough_days_there_is_no_comparison_and_no_advice(self):
        self.day_of(0, [(2, "09:00")], [("learning", "skipped")])
        self.day_of(1, [(1, "09:00")], [("learning", "skipped")])
        self.day_of(2, [(4, "10:00")], [("learning", "done")])
        self.day_of(3, [(4, "10:00")], [("learning", "done")])
        reports = self.reports()
        self.assertIsNone(reports["week"]["energy"]["comparison"])
        self.assertEqual(reports["week"]["energy"]["daysReported"], 4)
        for kind in ("day", "week", "month"):
            self.assertFalse([item for item in reports[kind]["suggestions"] if "energy" in item["content"].lower()], kind)

    def test_a_day_compares_with_the_day_before_and_all_time_with_nothing(self):
        self.five_days()
        reports = self.reports()
        self.assertEqual(reports["day"]["energy"]["trend"], {"before": 2.0, "change": 2.0})
        self.assertIsNone(reports["all"]["energy"]["trend"])

    def test_a_period_with_no_readings_has_no_figures(self):
        self.day_of(0, [], [("learning", "done")])
        energy = self.reports(0)["day"]["energy"]
        self.assertEqual((energy["daysReported"], energy["average"], energy["lowest"], energy["comparison"]),
                         (0, None, None, None))


class EnergyEverywhereTests(EnergyDay):
    """The day's average in the Calendar and on Life's page, with the day's readings and the week's range."""

    def test_a_day_with_only_energy_shows_in_the_calendar_with_its_average(self):
        self.report(2)
        self.report(3)
        days = self.client.get("/api/calendar", params={"month": self.today[:7]}).json()["days"]
        self.assertEqual(next(day for day in days if day["date"] == self.today)["energy"], 2.5)

    def test_lifes_page_has_the_days_readings_and_each_days_average_and_range_this_week(self):
        self.report(2)
        with patch("backend.app.database._local_time", return_value="15:00"):
            self.report(5)
        life = self.client.get("/api/areas/life", params={"date": self.today}).json()
        self.assertEqual((life["energy"], life["energyReadings"]),
                         (3.5, [{"level": 2, "time": "07:00"}, {"level": 5, "time": "15:00"}]))
        self.assertEqual(life["energyWeek"][-1], {"date": self.today, "average": 3.5, "low": 2, "high": 5})
        self.assertEqual(life["energyWeek"][0]["average"], None)


class RemovedAreaRecordRoutesTests(MealDay):
    def test_the_old_learning_and_life_record_routes_are_gone(self):
        for method, path in (("post", "/api/learning/items"), ("patch", "/api/learning/items/x"),
                             ("post", "/api/learning/sessions"), ("post", "/api/life/habits"),
                             ("patch", "/api/life/habits/x"), ("put", f"/api/life/habits/x/logs/{self.today}"),
                             ("put", f"/api/life/daily/{self.today}"), ("post", "/api/life/events")):
            self.assertEqual(getattr(self.client, method)(path, json={}).status_code, 404, path)


if __name__ == "__main__":
    unittest.main()
