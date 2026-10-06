import json
import sqlite3
import unittest
from datetime import date, timedelta

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.tests.test_source_routes import RouteDay

TODAY = date.today().isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


class LearningChatDay(RouteDay):
    """A connected folder whose two files are Learning tasks in a goal, one a day from today, and Ava to talk to."""

    def setUp(self):
        super().setUp()
        folder = self.connect()
        entries = self.client.get(f"/api/sources/entries?folderId={folder['id']}").json()["entries"]
        ordered = sorted(entries, key=lambda entry: entry["title"] != "Consuming HTTP Services")
        made = self.client.post("/api/learning-tasks", json={"sourceIds": [entry["sourceId"] for entry in ordered], "date": TODAY,
                                                             "goal": {"title": "Angular"}, "oneADay": True}).json()
        self.lesson, self.basics = (task["id"] for task in made["tasks"])

    def chat(self, message, day=TODAY):
        return self.client.post("/api/chat", json={"date": day, "message": message}).json()

    def confirm(self, action):
        answer = self.client.post(f"/api/actions/{action['id']}", json={"decision": "confirmed"})
        self.assertEqual(answer.status_code, 200, answer.text)
        return answer.json()

    def checklist(self, item_id):
        return self.client.get(f"/api/learning-tasks/{item_id}/checklist").json()

    def tick(self, item_id, title):
        entry = next(entry for entry in self.checklist(item_id)["checklist"] if entry["title"] == title)
        return self.client.post(f"/api/learning-tasks/{item_id}/checklist/{entry['id']}/tick", json={"done": True}).json()

    def set(self, item_id, **columns):
        with sqlite3.connect(self.database) as connection:
            for column, value in columns.items():
                connection.execute(f"UPDATE daily_items SET {column} = ? WHERE id = ?", (value, item_id))

    def titles_on(self, day):
        return [item["title"] for item in self.client.get(f"/api/bootstrap?date={day}").json()["dayItems"]]

    def stop_model(self):
        running = self.gateway.status()
        self.gateway.status = lambda: {**running, "state": "stopped", "running": False}


class NextTaskTests(LearningChatDay):
    def test_ava_proposes_moving_the_next_task_to_the_day_on_show_saved_only_on_confirm(self):
        self.set(self.lesson, completion_status="done")

        reply = self.chat("What should I study next in “Angular”?")

        action = reply["proposedAction"]
        self.assertEqual((action["actionType"], action["payload"]["itemId"], action["payload"]["changes"]),
                         ("edit_item", self.basics, {"date": TODAY}))
        self.assertIn("next in your goal “Angular”", reply["assistantMessage"]["content"])
        self.assertEqual(self.titles_on(TODAY), ["Consuming HTTP Services"], "nothing moves before Confirm")
        self.confirm(action)
        self.assertEqual(self.titles_on(TODAY), ["Consuming HTTP Services", "Basics"])

        again = self.chat("What should I study next in “Angular”?")
        self.assertIsNone(again["proposedAction"])
        self.assertIn(f"is planned for {TODAY}", again["assistantMessage"]["content"])

    def test_a_task_on_the_day_on_show_is_planned_and_every_task_done_is_said(self):
        reply = self.chat("What should I study next?")
        self.assertIsNone(reply["proposedAction"])
        self.assertIn(f"“Consuming HTTP Services”, next in your goal “Angular”, is planned for {TODAY}",
                      reply["assistantMessage"]["content"])

        self.set(self.lesson, completion_status="done")
        self.set(self.basics, completion_status="done")
        self.assertIn("Every task in “Angular” is done", self.chat("What should I study next?")["assistantMessage"]["content"])

    def test_a_goal_named_in_chinese_quotes_is_the_one_and_an_unknown_one_is_said(self):
        self.set(self.lesson, completion_status="done")
        self.assertEqual(self.chat("“Angular”接下来学什么？")["proposedAction"]["payload"]["itemId"], self.basics)
        none = self.chat("What should I study next in “Spanish”?")
        self.assertIsNone(none["proposedAction"])
        self.assertIn("No active Learning goal is called “Spanish”", none["assistantMessage"]["content"])


class ContinueTests(LearningChatDay):
    def test_ava_proposes_the_follow_up_with_the_whole_checklist_saved_only_on_confirm(self):
        self.tick(self.lesson, "HttpClient setup")

        reply = self.chat("Continue “Consuming HTTP Services” next session")

        action = reply["proposedAction"]
        payload = action["payload"]
        self.assertEqual((action["actionType"], payload["date"], payload["left"], payload["learning"]["followsItemId"]),
                         ("add_item", TOMORROW, ["Interceptors", "Error handling"], self.lesson))
        self.assertIn("earlier ticks kept", reply["assistantMessage"]["content"])
        self.assertEqual(self.titles_on(TOMORROW), ["Basics"], "nothing is saved before Confirm")

        created = self.confirm(action)["created"][0]
        follow = self.checklist(created["id"])
        self.assertEqual((follow["sections"], follow["ticked"]),
                         (["HttpClient setup", "Interceptors", "Error handling"], ["HttpClient setup"]))
        self.assertEqual(self.titles_on(TOMORROW), ["Basics", "Consuming HTTP Services"])
        self.assertEqual(self.client.get(f"/api/bootstrap?date={TODAY}").json()["dayItems"][0]["completion_status"], "planned",
                         "the original is done only when the user marks it")

    def test_continue_in_chinese_and_a_task_with_nothing_left(self):
        self.assertEqual(self.chat("下次继续“Consuming HTTP Services”")["proposedAction"]["actionType"], "add_item")
        for title in ("HttpClient setup", "Interceptors", "Error handling"):
            self.tick(self.lesson, title)
        reply = self.chat("Continue “Consuming HTTP Services” next session")
        self.assertIsNone(reply["proposedAction"])
        self.assertIn("has checklist items left to continue", reply["assistantMessage"]["content"])


class PastTickTests(LearningChatDay):
    def test_a_past_days_checklist_is_corrected_through_avas_card(self):
        self.set(self.lesson, item_date=YESTERDAY)

        reply = self.chat("Tick “Interceptors” in “Consuming HTTP Services”", day=YESTERDAY)

        action = reply["proposedAction"]
        self.assertEqual((action["actionType"], action["payload"]["entryTitle"], action["payload"]["done"]),
                         ("tick_item", "Interceptors", True))
        self.assertEqual(self.checklist(self.lesson)["ticked"], [], "nothing is ticked before Confirm")
        self.confirm(action)
        entry = next(entry for entry in self.checklist(self.lesson)["checklist"] if entry["title"] == "Interceptors")
        self.assertEqual((bool(entry["tickedAt"]), entry["tickedOn"]), (True, self.lesson))

        self.assertIsNone(self.chat("Tick “Interceptors” in “Consuming HTTP Services”", day=YESTERDAY)["proposedAction"],
                          "ticked already")
        untick = self.chat("取消勾选“Consuming HTTP Services”中的“Interceptors”", day=YESTERDAY)["proposedAction"]
        self.assertEqual(untick["payload"]["done"], False)
        self.confirm(untick)
        self.assertEqual(self.checklist(self.lesson)["ticked"], [])


class LearnTodayTests(LearningChatDay):
    def test_the_model_answers_from_the_days_tasks_and_the_text_of_what_is_left(self):
        self.tick(self.lesson, "Interceptors")

        reply = self.chat("What will I learn today?")

        self.assertIsNone(reply["proposedAction"])
        self.assertEqual(reply["assistantMessage"]["mode"], "ask")
        task = json.loads(self.gateway.calls[-1]["context"])["tasks"][0]
        self.assertEqual((task["title"], task["goal"], task["left"]),
                         ("Consuming HTTP Services", "Angular", ["HttpClient setup", "Error handling"]))
        self.assertIn("provideHttpClient", task["text"], "a local file's items left give the model their text, read on this Mac")
        self.assertNotIn("HttpInterceptorFn", task["text"], "a ticked item's text is left out")

    def test_without_the_model_the_answer_lists_each_task_with_what_is_left(self):
        self.tick(self.lesson, "Interceptors")
        self.stop_model()
        content = self.chat("What will I learn today?")["assistantMessage"]["content"]

        self.assertIn("“Consuming HTTP Services” (in Angular)", content)
        self.assertIn("Still to do, 1 of 3 ticked: HttpClient setup, Error handling.", content)

    def test_a_day_with_no_learning_task_says_so(self):
        self.stop_model()
        content = self.chat("What will I learn today?", day=(date.today() + timedelta(days=5)).isoformat())["assistantMessage"]["content"]
        self.assertIn("No Learning task is planned for", content)


if __name__ == "__main__":
    unittest.main()
