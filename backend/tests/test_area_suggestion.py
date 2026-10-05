from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.area_choice import AREA_ROLE, keyword_area, parse_area
from backend.app.main import create_app
from backend.tests.test_api import FakeEmbeddingGateway, FakeGateway


class ModelAnswering(FakeGateway):
    """A local model that is running, or not, and answers with `answer`."""

    def __init__(self, answer, running=True):
        super().__init__()
        self.answer, self.running = answer, running

    def status(self):
        return {**super().status(), "state": "ready" if self.running else "available", "running": self.running}

    def reply(self, message, context, system_prompt=None, max_tokens=None):
        self.calls.append({"message": message, "context": context, "systemPrompt": system_prompt})
        return self.answer, "local-model"


class KeywordAreaTests(unittest.TestCase):
    """Without the model, keywords follow the purpose rule: someone else expects it, then a step toward
    something with an end, then getting better at something, then everything else."""

    def test_each_area_by_its_purpose(self):
        cases = {"Send the quarterly report to the client": "work", "Build the landing page for the launch": "project",
                 "Practise piano scales": "learning", "Water the plants": "life", "回复客户的邮件": "work",
                 "搭建项目原型": "project", "复习英语单词": "learning", "去超市买菜": "life"}
        self.assertEqual({title: keyword_area(title, "") for title in cases}, cases)

    def test_the_rule_is_taken_in_order(self):
        self.assertEqual(keyword_area("Practise the talk my manager asked for", ""), "work")
        self.assertEqual(keyword_area("Study the docs", "for the app launch"), "project")

    def test_a_word_counts_only_whole(self):
        self.assertEqual(keyword_area("Bread and jam", ""), "life")

    def test_the_models_answer_is_read_as_one_area_or_none(self):
        self.assertEqual([parse_area(answer) for answer in ("Project.", "learning", " 工作", "Maybe health?")],
                         ["project", "learning", "work", None])


class AreaSuggestionApiTests(unittest.TestCase):
    def client(self, gateway):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        return TestClient(create_app(database_path=Path(folder.name) / "areas.sqlite3", gateway=gateway,
                                     embedding_gateway=FakeEmbeddingGateway()))

    def test_without_a_running_model_the_keywords_suggest(self):
        gateway = ModelAnswering("project", running=False)

        suggested = self.client(gateway).post("/api/areas/suggest", json={"title": "Reply to the client"}).json()

        self.assertEqual(suggested, {"domain": "work", "source": "keywords"})
        self.assertEqual(gateway.calls, [])

    def test_a_running_model_suggests_by_the_purpose_rule(self):
        gateway = ModelAnswering("Project")

        suggested = self.client(gateway).post("/api/areas/suggest", json={"title": "Paint the fence", "detail": ""}).json()

        self.assertEqual(suggested, {"domain": "project", "source": "model"})
        self.assertEqual(gateway.calls[0]["systemPrompt"], AREA_ROLE)
        self.assertIn("Paint the fence", gateway.calls[0]["message"])

    def test_an_unusable_answer_falls_back_to_the_keywords(self):
        suggested = self.client(ModelAnswering("Hard to say")).post("/api/areas/suggest", json={"title": "Study French"})

        self.assertEqual(suggested.json(), {"domain": "learning", "source": "keywords"})

    def test_a_goals_area_wins(self):
        client = self.client(ModelAnswering("learning"))
        goal = client.post("/api/goals", json={"title": "Quarterly close", "domain": "work"}).json()

        suggested = client.post("/api/areas/suggest", json={"title": "Study the ledger", "goalId": goal["id"]}).json()

        self.assertEqual(suggested, {"domain": "work", "source": "goal"})


if __name__ == "__main__":
    unittest.main()
