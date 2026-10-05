import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app import guide
from backend.app.main import create_app
from backend.tests.test_api import FakeEmbeddingGateway
from backend.tests.test_area_suggestion import ModelAnswering

YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


def card(card_id):
    return next(item for section in guide.GUIDE["sections"] for item in section["cards"] if item["id"] == card_id)


class GuideQuestionTests(unittest.TestCase):
    """Which questions ask how something works, and which of the Guide's cards answer them."""

    def titles(self, message):
        return [item["title"] for item in guide.asked_cards(message)]

    def test_asking_how_something_works_names_its_cards_in_guide_order(self):
        cases = {
            "How does energy work?": ["Energy"],
            "How do plans work?": ["Plans"],
            "Ava, how do repeats and meals work?": ["Meals", "Repeats"],
            "How do past days work?": ["Past days"],
            "How do past tasks work?": ["Past days"],
            "What is the Library for?": ["Library"],
            "What does the Orchestrator do?": ["Agents"],
            "Explain how the Calendar works.": ["Calendar"],
            "How do you work?": ["Ava"],
            "How do I use goals?": ["Goals"],
            "how does the day strip work": ["Today"],
        }
        self.assertEqual({message: self.titles(message) for message in cases}, cases)

    def test_other_questions_and_requests_are_not_guide_questions(self):
        for message in ("How long did Review take?", "What is planned today?", "How did this week go?",
                        "What are the plans for today?", "Move lunch to 13:00", "Why was Review added?",
                        "How do I work less?", "How does it work?", "How did the plan work out?", "Add a task"):
            self.assertEqual(guide.asked_cards(message), [], message)

    def test_the_answer_is_each_cards_lines_then_one_see_guide_line_naming_them(self):
        meals, repeats = card("meals"), card("repeats")
        self.assertEqual(guide.answer([meals, repeats]),
                         f"**Meals**\nFor: {meals['for']}\nDo: {meals['do']}\nRule: {meals['rule']}\n\n"
                         f"**Repeats**\nFor: {repeats['for']}\nDo: {repeats['do']}\nRule: {repeats['rule']}\n\n"
                         "See Guide: Meals, Repeats")


class AvaAnswersFromTheGuideTests(unittest.TestCase):
    """Through the service: a question about how something works, with the local model running."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "guide.sqlite3"
        self.gateway = ModelAnswering("The model's own words.")
        self.client = TestClient(create_app(database_path=self.path, gateway=self.gateway,
                                            embedding_gateway=FakeEmbeddingGateway()))

    def chat(self, message, day=None):
        return self.client.post("/api/chat", json={"date": day or date.today().isoformat(), "message": message}).json()

    def test_a_how_question_is_answered_from_its_card_by_the_rules_and_ends_with_its_see_guide_line(self):
        reply = self.chat("How does energy work?")
        message = reply["assistantMessage"]
        energy = card("energy")
        for line in (energy["for"], energy["do"], energy["rule"]):
            self.assertIn(line, message["content"])
        self.assertTrue(message["content"].endswith("\n\nSee Guide: Energy"), message["content"])
        self.assertEqual((message["mode"], message["model_mode"]), ("ask", "guide"))
        self.assertEqual(self.gateway.calls, [], "the model isn't asked")
        self.assertEqual((reply["proposedAction"], reply["agentRoute"], reply["feedbackSignals"]), (None, [], []))

    def test_asking_about_meals_or_repeats_changes_nothing_even_on_a_past_day(self):
        before = self.client.get("/api/bootstrap", params={"date": date.today().isoformat()}).json()["notices"]
        for message, day, named in (("How do meals work?", None, "Meals"), ("How do repeats work?", YESTERDAY, "Repeats"),
                                    ("How do past tasks work?", YESTERDAY, "Past days")):
            reply = self.chat(message, day)
            self.assertIsNone(reply["proposedAction"], message)
            self.assertTrue(reply["assistantMessage"]["content"].endswith(f"See Guide: {named}"), message)
            self.assertEqual(reply["notices"], before, "no agent posts a message about it")
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM proposed_actions").fetchone()[0], 0)

    def test_the_answer_stays_in_the_conversation(self):
        self.chat("What is the Library for?")
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute("SELECT role, content, model_mode FROM conversation_messages ORDER BY rowid").fetchall()
        self.assertEqual([(role, mode) for role, _, mode in rows], [("user", None), ("assistant", "guide")])
        self.assertTrue(rows[1][1].endswith("See Guide: Library"))

    def test_any_other_question_still_goes_to_the_model(self):
        reply = self.chat("What should I do next?")
        self.assertTrue(self.gateway.calls)
        self.assertNotEqual(reply["assistantMessage"]["model_mode"], "guide")
        self.assertNotIn("See Guide", reply["assistantMessage"]["content"])


if __name__ == "__main__":
    unittest.main()
