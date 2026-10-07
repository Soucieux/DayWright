import sqlite3
import unittest

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.main import create_app
from backend.tests.test_api import FakeGateway
from backend.tests.test_library_offline import NearestFirstEmbeddings
from backend.tests.test_meals import MealDay


class LinkDay(MealDay):
    """A fresh account whose Learn tasks link Library sources."""

    def note(self, title, text):
        return self.client.post("/api/knowledge/sources", json={"title": title, "sourceType": "note", "text": text}).json()

    def goal(self, title, domain="learning"):
        return self.client.post("/api/goals", json={"title": title, "domain": domain}).json()["id"]

    def add(self, title, domain="learning", goal=None):
        made = self.client.post("/api/daily-items", json={**self.task(title, None, 45), "domain": domain, "goalId": goal})
        self.settle()
        return made.json()

    def settle(self):
        """Wait for the work DayWright does in the background, such as Ava's link suggestions."""
        for thread in list(self.client.app.state.indexing):
            thread.join()

    def link(self, item, source):
        return self.client.post(f"/api/learning-tasks/{item['id']}/sources", json={"sourceId": source["id"]})

    def unlink(self, item, source):
        return self.client.delete(f"/api/learning-tasks/{item['id']}/sources/{source['id']}")

    def links(self, item):
        return self.client.get(f"/api/learning-tasks/{item['id']}/checklist").json()

    def move(self, item, domain):
        return self.client.put(f"/api/daily-items/{item['id']}", json={**self.task(item["title"], None, 45), "domain": domain,
                                                                      "status": None})

    def chat(self, message, day=None):
        return self.client.post("/api/chat", json={"date": day or self.today, "message": message}).json()

    def decide(self, action, decision="confirmed"):
        return self.client.post(f"/api/actions/{action['id']}", json={"decision": decision})

    def sql(self, statement, *values):
        with sqlite3.connect(self.path) as connection:
            return connection.execute(statement, values).fetchall()

    def offers(self):
        """Ava's link suggestions, each notice with its card."""
        return [notice for notice in self.store.notices() if notice["kind"] == "link-offer"]


class TaskLinkTests(LinkDay):
    def test_a_learn_task_links_several_sources_and_unlinks_one(self):
        grammar, verbs = self.note("Grammar notes", "Verb endings."), self.note("Verb tables", "Every tense.")
        lesson = self.add("Lesson 4")

        self.assertEqual(self.link(lesson, grammar).status_code, 200)
        self.assertEqual(self.link(lesson, verbs).status_code, 200)
        self.assertEqual(self.link(lesson, verbs).status_code, 200)
        self.assertEqual([source["title"] for source in self.links(lesson)["references"]], ["Grammar notes", "Verb tables"])

        self.assertEqual(self.unlink(lesson, grammar).status_code, 200)
        self.assertEqual([source["title"] for source in self.links(lesson)["references"]], ["Verb tables"])
        self.assertEqual(self.link(lesson, {"id": "source_nowhere"}).status_code, 404)

    def test_only_learn_tasks_link_sources_and_a_past_one_only_through_ava(self):
        grammar = self.note("Grammar notes", "Verb endings.")
        gym = self.add("Gym", domain="life")
        lesson = self.add("Lesson 4")
        self.sql("UPDATE daily_items SET item_date = ? WHERE id = ?", self.yesterday, lesson["id"])

        refused = self.link(gym, grammar)
        self.assertEqual(refused.status_code, 422)
        self.assertIn("Only Learn tasks link Library sources", refused.json()["detail"])
        self.assertEqual(self.link(lesson, grammar).status_code, 409)

    def test_the_library_lists_the_tasks_that_link_each_source_with_their_goals(self):
        spanish = self.goal("Spanish")
        grammar, tips = self.note("Grammar notes", "Verb endings."), self.note("Study tips", "# Study tips\nShort sessions.")
        lesson, review = self.add("Lesson 4", goal=spanish), self.add("Review")
        self.link(lesson, grammar)
        self.link(review, grammar)
        self.client.post("/api/learning-tasks", json={"sourceIds": [tips["id"]], "date": self.today, "goal": {"goalId": spanish}})

        listed = {source["title"]: source for source in self.client.get("/api/knowledge").json()["sources"]}

        self.assertEqual([(task["title"], task["goalTitle"], task["role"]) for task in listed["Grammar notes"]["tasks"]],
                         [("Lesson 4", "Spanish", "reference"), ("Review", None, "reference")])
        self.assertEqual([(task["title"], task["goalTitle"], task["role"]) for task in listed["Study tips"]["tasks"]],
                         [("Study tips", "Spanish", "checklist")])
        self.assertNotIn("goalId", listed["Grammar notes"])


class AreaMoveTests(LinkDay):
    def test_a_learn_task_with_a_reference_stays_in_learn_until_it_is_unlinked(self):
        grammar, verbs = self.note("Grammar notes", "Verb endings."), self.note("Verb tables", "Every tense.")
        lesson = self.add("Lesson 4")
        self.link(lesson, grammar)
        self.link(lesson, verbs)

        refused = self.move(lesson, "work")
        self.assertEqual(refused.status_code, 409)
        self.assertIn("It uses Grammar notes and Verb tables from your Library, so it stays in Learn. Unlink them to move it",
                      refused.json()["detail"])

        self.unlink(lesson, grammar)
        self.unlink(lesson, verbs)
        self.assertEqual(self.move(lesson, "work").status_code, 200)
        self.assertEqual(self.store.daily_item(lesson["id"])["domain"], "work")

    def test_a_learning_task_made_from_a_source_stays_in_learn_until_the_source_is_deleted(self):
        tips = self.note("Study tips", "# Study tips\n## Short sessions\nTwenty minutes.")
        made = self.client.post("/api/learning-tasks", json={"sourceIds": [tips["id"]], "date": self.today}).json()["tasks"][0]

        self.assertIn("It uses Study tips from your Library", self.move(made, "life").json()["detail"])

        self.client.delete(f"/api/knowledge/sources/{tips['id']}")
        self.assertEqual(self.move(made, "life").status_code, 200)
        self.assertEqual([entry["title"] for entry in self.links(made)["checklist"]], ["Short sessions"])

    def test_unlinking_a_learning_tasks_own_source_keeps_its_checklist_and_lets_it_move(self):
        tips = self.note("Study tips", "# Study tips\n## Short sessions\nTwenty minutes.\n## Breaks\nFive minutes.")
        made = self.client.post("/api/learning-tasks", json={"sourceIds": [tips["id"]], "date": self.today}).json()["tasks"][0]
        first = self.links(made)["checklist"][0]
        self.client.post(f"/api/learning-tasks/{made['id']}/checklist/{first['id']}/tick", json={"done": True})

        self.assertEqual(self.unlink(made, tips).status_code, 200)

        kept = self.links(made)
        self.assertIsNone(kept["sourceId"])
        self.assertEqual([(entry["title"], bool(entry["tickedAt"])) for entry in kept["checklist"]],
                         [("Short sessions", True), ("Breaks", False)])
        self.assertIn("Study tips", [source["title"] for source in self.client.get("/api/knowledge").json()["sources"]])
        self.assertEqual(self.move(made, "life").status_code, 200)

    def test_a_learn_task_without_sources_moves_freely(self):
        self.assertEqual(self.move(self.add("Lesson 4"), "project").status_code, 200)

    def test_ava_refuses_to_change_a_linked_tasks_area_and_names_its_sources(self):
        grammar = self.note("Grammar notes", "Verb endings.")
        lesson = self.add("Lesson 4")
        self.link(lesson, grammar)
        self.sql("UPDATE daily_items SET item_date = ? WHERE id = ?", self.yesterday, lesson["id"])

        reply = self.chat("Change the area of Lesson 4 to work", self.yesterday)

        self.assertIsNone(reply["proposedAction"])
        self.assertIn("It uses Grammar notes from your Library, so it stays in Learn.", reply["assistantMessage"]["content"])
        self.assertEqual(self.store.daily_item(lesson["id"])["domain"], "learning")

    def test_no_card_or_suggestion_ever_changes_a_linked_tasks_area(self):
        grammar = self.note("Grammar notes", "Verb endings.")
        lesson = self.add("Lesson 4")
        self.link(lesson, grammar)
        self.client.post("/api/plan/generate", json={"date": self.today})

        cards = self.sql("SELECT payload_json FROM proposed_actions")
        self.assertFalse([card for card in cards if '"domain"' in card[0] and lesson["id"] in card[0]])


class RankingTests(LinkDay):
    def setUp(self):
        super().setUp()
        self.client = TestClient(create_app(database_path=self.path.with_name("ranked.sqlite3"), gateway=FakeGateway(),
                                            embedding_gateway=NearestFirstEmbeddings()))

    def ranked(self, message):
        return [match["sourceTitle"] for match in self.chat(message)["retrieval"]["matches"]]

    def test_a_tasks_own_sources_come_first_then_its_goals_other_tasks_then_the_rest(self):
        spanish = self.goal("Spanish")
        self.note("Office notes", "Desk plans for the move.")
        tips, grammar = self.note("Study tips", "Short sessions work best."), self.note("Grammar notes", "Verb endings for the past tense.")
        lesson, practice = self.add("Lesson 4", goal=spanish), self.add("Practice", goal=spanish)
        self.link(lesson, grammar)
        self.link(practice, tips)

        self.assertEqual(self.ranked("Help me get ready for Lesson 4"), ["Grammar notes", "Study tips", "Office notes"])
        self.assertEqual(self.ranked("How should I study for my Spanish goal?"), ["Study tips", "Grammar notes", "Office notes"])


class LinkCardTests(LinkDay):
    def test_asked_ava_proposes_linking_and_unlinking_a_source_applied_on_confirm(self):
        grammar = self.note("Grammar notes", "Verb endings.")
        lesson = self.add("Lesson 4")

        card = self.chat("Link Grammar notes to Lesson 4")["proposedAction"]
        self.assertEqual((card["actionType"], card["payload"]["sourceIds"], card["payload"]["link"]),
                         ("link_sources", [grammar["id"]], True))
        self.assertEqual(self.links(lesson)["references"], [])
        self.decide(card)
        self.assertEqual([source["title"] for source in self.links(lesson)["references"]], ["Grammar notes"])

        self.decide(self.chat("Unlink Grammar notes from Lesson 4")["proposedAction"])
        self.assertEqual(self.links(lesson)["references"], [])

    def test_asked_ava_unlinks_a_learning_tasks_own_source_and_keeps_its_checklist(self):
        tips = self.note("Study tips", "# Study tips\n## Short sessions\nTwenty minutes.")
        made = self.client.post("/api/learning-tasks", json={"sourceIds": [tips["id"]], "date": self.today}).json()["tasks"][0]

        card = self.chat("Unlink Study tips from Study tips")["proposedAction"]
        self.assertEqual((card["payload"]["sourceIds"], card["payload"]["link"]), ([tips["id"]], False))
        self.decide(card)

        self.assertIsNone(self.links(made)["sourceId"])
        self.assertEqual([entry["title"] for entry in self.links(made)["checklist"]], ["Short sessions"])
        self.assertEqual(self.move(made, "work").status_code, 200)

    def test_a_sentence_naming_no_source_is_answered_as_any_other(self):
        self.add("Lesson 4")

        reply = self.chat("Link up with Anna about Lesson 4")

        self.assertIsNone(reply["proposedAction"])
        self.assertNotIn("Library", reply["assistantMessage"]["content"])

    def test_asked_ava_explains_that_only_learn_tasks_link_sources(self):
        self.note("Grammar notes", "Verb endings.")
        self.add("Gym", domain="life")

        reply = self.chat("Link Grammar notes to Gym")

        self.assertIsNone(reply["proposedAction"])
        self.assertIn("Only Learn tasks link Library sources", reply["assistantMessage"]["content"])


class SuggestionTests(LinkDay):
    def test_a_new_learn_task_gets_one_card_of_at_most_three_matching_sources(self):
        for title in ("Sleep diary", "Sleep science", "Sleep hygiene", "Sleep apnoea"):
            self.note(title, f"{title}: notes about sleep.")
        self.note("Budget notes", "Review the grocery budget.")

        lesson = self.add("Sleep course")

        offer, = self.offers()
        card = offer["proposal"]
        self.assertEqual(offer["values"]["itemId"], lesson["id"])
        self.assertEqual(card["actionType"], "link_sources")
        self.assertLessEqual(len(card["payload"]["sourceIds"]), 3)
        self.assertTrue(all("Sleep" in source["title"] for source in card["payload"]["sources"]))
        self.decide(card)
        self.assertEqual(len(self.links(lesson)["references"]), len(card["payload"]["sourceIds"]))

    def test_a_task_matching_nothing_gets_no_card_and_a_dismissed_card_never_returns(self):
        self.note("Sleep diary", "Notes about sleep.")

        self.add("Budget review")
        self.assertEqual(self.offers(), [])

        lesson = self.add("Sleep course")
        self.decide(self.offers()[0]["proposal"], "dismissed")
        self.client.put(f"/api/daily-items/{lesson['id']}", json={**self.task("Sleep course again", None, 45), "status": None})
        self.settle()
        self.assertEqual(len(self.sql("SELECT id FROM proposed_actions WHERE action_type = 'link_sources'")), 1)

    def test_a_task_made_from_a_source_and_a_task_outside_learn_get_no_suggestion(self):
        diary = self.note("Sleep diary", "# Sleep diary\nNotes about sleep.")
        self.client.post("/api/learning-tasks", json={"sourceIds": [diary["id"]], "date": self.today})
        self.add("Sleep earlier", domain="life")
        self.settle()

        self.assertEqual(self.offers(), [])


if __name__ == "__main__":
    unittest.main()
