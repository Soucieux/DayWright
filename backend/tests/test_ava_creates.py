import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.database import Database
from backend.app.main import create_app
from backend.tests.test_api import FakeEmbeddingGateway
from backend.tests.test_area_suggestion import ModelAnswering

TODAY = date.today()
TOMORROW = (TODAY + timedelta(days=1)).isoformat()
# The next Saturday, today when it is one.
SATURDAY = (TODAY + timedelta(days=(5 - TODAY.weekday()) % 7)).isoformat()


class AvaCreates(unittest.TestCase):
    """A fresh account whose local model isn't running, so areas are suggested by keywords."""

    answer, running = "Noted.", False

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "ava.sqlite3"
        self.client = TestClient(create_app(database_path=self.path, gateway=ModelAnswering(self.answer, self.running),
                                            embedding_gateway=FakeEmbeddingGateway()))
        self.store = Database(self.path)
        self.today = TODAY.isoformat()
        clock = patch("backend.app.database._local_time", return_value="07:00")
        clock.start()
        self.addCleanup(clock.stop)

    def chat(self, message, day=None):
        return self.client.post("/api/chat", json={"date": day or self.today, "message": message}).json()

    def confirm(self, action, **choice):
        decided = self.client.post(f"/api/actions/{action['id']}", json={"decision": "confirmed", **choice})
        self.assertEqual(decided.status_code, 200, decided.text)
        return decided.json()

    def counts(self):
        with sqlite3.connect(self.path) as connection:
            return tuple(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("daily_items", "goals"))

    def goal(self, title, domain, status="active"):
        made = self.client.post("/api/goals", json={"title": title, "domain": domain}).json()
        if status != "active":
            self.client.put(f"/api/goals/{made['id']}", json={"title": title, "status": status})
        return made["id"]


class AvaCreatesTaskTests(AvaCreates):
    def test_a_task_joins_its_goal_with_its_day_time_length_and_repeat_on_confirm(self):
        spanish = self.goal("Spanish", "learning")
        before = self.counts()

        action = self.chat("Add Read chapter 4 tomorrow at 9 for 45 min to my Spanish goal, every day")["proposedAction"]

        self.assertEqual(action["actionType"], "add_item")
        payload = action["payload"]
        self.assertEqual({key: payload[key] for key in ("date", "title", "startTime", "durationMinutes", "constraintKind",
                                                        "repeatKind", "goalId", "goalTitle", "domain", "domainSource")},
                         {"date": TOMORROW, "title": "Read chapter 4", "startTime": "09:00", "durationMinutes": 45,
                          "constraintKind": "fixed", "repeatKind": "daily", "goalId": spanish, "goalTitle": "Spanish",
                          "domain": "learning", "domainSource": "goal"})
        self.assertEqual(self.counts(), before)
        self.confirm(action, domain="work")
        task, = self.store.daily_items(TOMORROW)
        self.assertEqual((task["title"], task["start_time"], task["duration_minutes"], task["repeatKind"], task["goalId"],
                          task["domain"]), ("Read chapter 4", "09:00", 45, "daily", spanish, "learning"))
        self.assertEqual(task["repeatSeriesId"], task["id"])

    def test_a_task_without_a_time_or_length_is_flexible_with_an_estimate_never_under_30(self):
        with sqlite3.connect(self.path) as connection:
            connection.execute("""INSERT INTO daily_items (id, item_date, title, domain, duration_minutes, constraint_kind,
                                      completion_status, created_at) VALUES ('short', ?, 'Tea', 'life', 15, 'flexible',
                                      'done', ?)""", ((TODAY - timedelta(days=2)).isoformat(), self.today))

        action = self.chat("Add Water the plants")["proposedAction"]

        payload = action["payload"]
        self.assertEqual((payload["date"], payload["startTime"], payload["durationMinutes"], payload["constraintKind"],
                          payload["repeatKind"], payload["goalId"], payload["domain"], payload["domainSource"]),
                         (self.today, None, None, "flexible", "none", None, "life", "keywords"))
        self.confirm(action)
        task, = self.store.daily_items(self.today)
        self.assertEqual((task["title"], task["duration_minutes"], task["durationSource"]), ("Water the plants", 30, "estimate"))

    def test_the_suggested_area_can_be_changed_on_the_card(self):
        action = self.chat("Add Water the plants tomorrow")["proposedAction"]

        self.confirm(action, domain="work")

        self.assertEqual(self.store.daily_items(TOMORROW)[0]["domain"], "work")

    def test_a_task_the_day_has_no_room_for_is_explained_instead_of_proposed(self):
        self.client.post("/api/daily-items", json={"date": self.today, "title": "Stand-up", "detail": "", "domain": "work",
                                                   "startTime": "09:00", "durationMinutes": 60, "constraintKind": "fixed",
                                                   "repeatKind": "none", "goalId": None})

        reply = self.chat("Add Call Anna today at 9:30 for 30 min")

        self.assertIsNone(reply["proposedAction"])
        self.assertIn("“Stand-up”", reply["assistantMessage"]["content"])
        self.assertIn("Nothing was changed.", reply["assistantMessage"]["content"])

    def test_a_past_day_is_refused(self):
        before = self.counts()

        reply = self.chat("Add Read chapter 4 yesterday")

        self.assertIsNone(reply["proposedAction"])
        self.assertIn("has passed", reply["assistantMessage"]["content"])
        self.assertEqual(self.counts(), before)

    def test_a_paused_goal_is_explained_instead_of_proposed(self):
        self.goal("Spanish", "learning", status="paused")

        reply = self.chat("Add Read chapter 4 to my Spanish goal")

        self.assertIsNone(reply["proposedAction"])
        self.assertIn("“Spanish” is paused", reply["assistantMessage"]["content"])

    def test_adding_minutes_to_a_task_is_not_a_new_task(self):
        self.client.post("/api/daily-items", json={"date": self.today, "title": "Review", "detail": "", "domain": "work",
                                                   "startTime": "10:00", "durationMinutes": 60, "constraintKind": "fixed",
                                                   "repeatKind": "none", "goalId": None})

        action = self.chat("Add 15 minutes to Review")["proposedAction"]

        self.assertNotEqual((action or {}).get("actionType"), "add_item")

    def test_a_task_in_chinese(self):
        action = self.chat("添加 读第4章 明天上午9点 45分钟")["proposedAction"]

        payload = action["payload"]
        self.assertEqual((payload["title"], payload["date"], payload["startTime"], payload["durationMinutes"]),
                         ("读第4章", TOMORROW, "09:00", 45))


class AvaCreatesTaskWithModelTests(AvaCreates):
    answer, running = "Project", True

    def test_a_running_model_suggests_the_area(self):
        payload = self.chat("Add Paint the fence tomorrow")["proposedAction"]["payload"]

        self.assertEqual((payload["domain"], payload["domainSource"]), ("project", "model"))


class AvaCreatesGoalTests(AvaCreates):
    def test_a_goal_on_its_own(self):
        before = self.counts()

        action = self.chat("Start a goal: Kitchen renovation")["proposedAction"]

        self.assertEqual(action["actionType"], "add_goal")
        self.assertEqual({key: action["payload"][key] for key in ("title", "domain", "domainSource", "tasks")},
                         {"title": "Kitchen renovation", "domain": "project", "domainSource": "keywords", "tasks": []})
        self.assertEqual(self.counts(), before)
        self.confirm(action)
        self.assertEqual([(goal["title"], goal["domain"], goal["status"]) for goal in self.store.goals()],
                         [("Kitchen renovation", "project", "active")])

    def test_a_goal_with_its_first_tasks_is_one_card_created_together(self):
        before = self.counts()

        action = self.chat("Start a goal: Kitchen renovation and add pick tiles on Saturday")["proposedAction"]

        self.assertEqual(action["payload"]["title"], "Kitchen renovation")
        self.assertEqual([(task["title"], task["date"]) for task in action["payload"]["tasks"]], [("pick tiles", SATURDAY)])
        self.assertEqual(self.counts(), before)
        self.confirm(action, domain="life")
        goal, = self.store.goals()
        task, = self.store.daily_items(SATURDAY)
        self.assertEqual((goal["domain"], task["title"], task["goalId"], task["domain"]),
                         ("life", "pick tiles", goal["id"], "life"))

    def test_a_goal_in_chinese(self):
        payload = self.chat("新建目标：厨房装修")["proposedAction"]["payload"]

        self.assertEqual((payload["title"], payload["domain"]), ("厨房装修", "project"))


class NewTasksReachTheDaysPlansTests(AvaCreates):
    """A task added to a day with plans proposed and none set is placed in them, from the form or through Ava."""

    def form_task(self, title, minutes):
        return {"date": self.today, "title": title, "detail": "", "domain": "life", "startTime": None,
                "durationMinutes": minutes, "constraintKind": "flexible", "repeatKind": "none", "goalId": None}

    def drafted(self):
        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        with sqlite3.connect(self.path) as connection:
            return {title for (title,) in connection.execute(
                "SELECT title FROM plan_entries WHERE variant_id = ?", (day["variants"][0]["id"],))}

    def setUp(self):
        super().setUp()
        self.client.post("/api/daily-items", json=self.form_task("Review", 60))
        self.client.post("/api/plan/generate", json={"date": self.today})

    def test_a_task_added_in_the_form_joins_the_days_proposed_plans(self):
        self.assertEqual(self.client.post("/api/daily-items", json=self.form_task("Walk", 30)).status_code, 200)

        self.assertEqual(self.drafted(), {"Review", "Walk"})

    def test_a_task_ava_adds_joins_the_days_proposed_plans(self):
        self.confirm(self.chat("Add Walk today for 30 min")["proposedAction"])

        self.assertEqual(self.drafted(), {"Review", "Walk"})


if __name__ == "__main__":
    unittest.main()
