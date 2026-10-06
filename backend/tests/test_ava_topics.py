import json
import unittest
from datetime import date

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.sources import study_minutes
from backend.tests.test_source_routes import RouteDay

TODAY = date.today().isoformat()


class TopicChatDay(RouteDay):
    """A connected folder with a goal made from its lesson, and Ava to talk to."""

    def setUp(self):
        super().setUp()
        folder = self.connect()
        lesson = self.lesson(folder)
        self.goal = self.client.post("/api/goals/from-source", json={"picks": [{"sourceId": lesson["id"]}]}).json()["goals"][0]

    def chat(self, message):
        return self.client.post("/api/chat", json={"date": TODAY, "message": message}).json()

    def plan_first_topic(self):
        action = self.chat("What should I study next?")["proposedAction"]
        self.client.post(f"/api/actions/{action['id']}", json={"decision": "confirmed"})

    def stop_model(self):
        running = self.gateway.status()
        self.gateway.status = lambda: {**running, "state": "stopped", "running": False}


class NextTopicTests(TopicChatDay):
    def test_ava_proposes_the_next_topic_as_a_study_task_saved_only_on_confirm(self):
        reply = self.chat("What should I study next?")
        action = reply["proposedAction"]
        first = self.goal["topics"][0]

        self.assertEqual(action["actionType"], "add_item")
        self.assertEqual({key: action["payload"][key] for key in ("title", "goalId", "topicId", "durationMinutes", "topicNumber", "topicCount")},
                         {"title": "HttpClient setup", "goalId": self.goal["id"], "topicId": first["id"],
                          "durationMinutes": study_minutes(first["profile"]), "topicNumber": 1, "topicCount": 3})
        self.assertIn("topic 1 of 3", reply["assistantMessage"]["content"])
        self.assertEqual(self.client.get(f"/api/bootstrap?date={TODAY}").json()["dayItems"], [], "nothing saved yet")

        self.client.post(f"/api/actions/{action['id']}", json={"decision": "confirmed"})
        items = self.client.get(f"/api/bootstrap?date={TODAY}").json()["dayItems"]
        self.assertEqual([item["title"] for item in items], ["HttpClient setup"])

        again = self.chat("What should I study next?")
        self.assertIsNone(again["proposedAction"], "goal order is kept: the first topic is planned")
        self.assertIn("HttpClient setup", again["assistantMessage"]["content"])

    def test_a_goal_named_is_the_one_studied_next_and_none_is_proposed_for_a_goal_without_topics(self):
        reply = self.chat("Plan my next topic in Consuming HTTP Services")
        self.assertEqual(reply["proposedAction"]["payload"]["goalTitle"], "Consuming HTTP Services")

        none = self.chat("Plan my next topic in Spanish")
        self.assertIsNone(none["proposedAction"])

    def test_a_goal_named_in_quotes_in_chinese_is_the_one_studied_next(self):
        (self.folder / "Angular" / "04 Routing.md").write_text("# Routing\n\n## Guards\n\nText.\n", encoding="utf-8")
        folder = self.client.get("/api/knowledge").json()["folders"][0]
        self.client.post(f"/api/sources/folder/{folder['id']}/refresh")
        routing = next(source for source in self.client.get("/api/knowledge").json()["sources"] if source["title"] == "Routing")
        self.client.post("/api/goals/from-source", json={"picks": [{"sourceId": routing["id"]}]})

        reply = self.chat("“Routing”接下来学什么？")
        self.assertEqual(reply["proposedAction"]["payload"]["goalTitle"], "Routing")
        self.assertIsNone(self.chat("“西班牙语”接下来学什么？")["proposedAction"])


class LearnTodayTests(TopicChatDay):
    def test_the_model_answers_what_will_i_learn_today_from_the_days_topics_and_their_text(self):
        self.plan_first_topic()
        reply = self.chat("What will I learn today?")

        self.assertIsNone(reply["proposedAction"])
        self.assertEqual(reply["assistantMessage"]["mode"], "ask")
        context = json.loads(self.gateway.calls[-1]["context"])
        topic = context["topics"][0]
        self.assertEqual((topic["title"], topic["place"], topic["covers"]), ("HttpClient setup", "1 of 3 in Consuming HTTP Services",
                                                                             ["Providers"]))
        self.assertIn("provideHttpClient", topic["text"], "a local folder's topic gives the model its text, read on this Mac")

    def test_without_the_model_the_answer_lists_each_topic_with_its_briefing_and_what_it_covers(self):
        self.plan_first_topic()
        self.stop_model()
        content = self.chat("What will I learn today?")["assistantMessage"]["content"]

        self.assertIn("“HttpClient setup” (1 of 3 in Consuming HTTP Services)", content)
        self.assertIn("Provide it once with provideHttpClient().", content)
        self.assertIn("It covers: Providers.", content)

    def test_a_day_with_no_study_topic_says_so(self):
        self.stop_model()
        content = self.chat("What will I learn today?")["assistantMessage"]["content"]
        self.assertIn("No study topic is planned for", content)


if __name__ == "__main__":
    unittest.main()
