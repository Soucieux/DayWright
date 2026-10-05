import base64
import re
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.database import Database
from backend.app.main import create_app
from backend.app.retrieval import EMBEDDING_DIMENSION, VectorStore
from backend.tests.test_api import FakeEmbeddingGateway, FakeGateway

APP = Path(__file__).resolve().parents[1] / "app"
NOW = "2026-10-01T09:00:00+00:00"


def vector(index=2):
    values = [0.0] * EMBEDDING_DIMENSION
    values[index] = 1.0
    return values


class LibraryDay(unittest.TestCase):
    """A fresh account, its service and its store, with an embedding model that tells sleep, budget and anything else apart."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "library.sqlite3"
        self.gateway = FakeGateway()
        self.client = TestClient(create_app(database_path=self.path, gateway=self.gateway,
                                            embedding_gateway=FakeEmbeddingGateway()))
        self.store = Database(self.path)
        self.today = date.today().isoformat()

    def note(self, title, text, domain, goal=None):
        return self.client.post("/api/knowledge/sources", json={"title": title, "sourceType": "note", "text": text,
                                                               "domain": domain, "goalId": goal})

    def goal(self, title, domain):
        return self.client.post("/api/goals", json={"title": title, "domain": domain}).json()["id"]

    def sources(self):
        return {source["title"]: source for source in self.client.get("/api/knowledge").json()["sources"]}

    def chat(self, message, language="en"):
        return self.client.post("/api/chat", json={"date": self.today, "message": message, "mode": "ask",
                                                   "language": language}).json()


class OfflineTests(LibraryDay):
    def test_the_online_lookup_and_the_network_log_are_gone(self):
        for method, path in (("post", "/api/knowledge/topic"), ("get", "/api/knowledge/import-plans"),
                             ("post", "/api/knowledge/import-plans/plan_1/confirm"), ("get", "/api/network-log")):
            self.assertEqual(getattr(self.client, method)(path).status_code, 404, path)
        self.assertFalse((APP / "knowledge_graph.py").exists())

    def test_day_proposals_keep_their_checkpoints_in_their_own_file(self):
        self.client.post("/api/daily-items", json={
            "date": self.today, "title": "Review", "detail": "", "domain": "learning", "startTime": None,
            "durationMinutes": 45, "constraintKind": "flexible", "repeatKind": "none", "goalId": None})
        with patch("backend.app.database._local_time", return_value="07:00"):
            self.assertEqual(self.client.post("/api/plan/generate", json={"date": self.today}).status_code, 200)

        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("PRAGMA quick_check").fetchone()[0], "ok")
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE name = 'checkpoints'").fetchone()[0], 0)
        with sqlite3.connect(self.store.checkpoint_path) as connection:
            self.assertEqual(connection.execute("PRAGMA quick_check").fetchone()[0], "ok")
            self.assertGreater(connection.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0], 0)

    def test_no_code_path_reaches_beyond_this_mac(self):
        for module in APP.glob("*.py"):
            source = module.read_text()
            for url in re.findall(r"https?://[^\s\"'{}]*", source):
                self.assertTrue(url.startswith("http://127.0.0.1"), f"{module.name}: {url}")
            if "urlopen" in source:
                self.assertIn(module.name, {"llama_runtime.py", "model_gateway.py", "retrieval.py"})


class LibraryMoveTests(unittest.TestCase):
    """A Library from before 3.9, opened by 3.9."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "old.sqlite3"
        self.store = Database(self.path)
        self.vectors = VectorStore(self.path)

    def old_source(self, title, source_type, text, url=""):
        """A note, file or imported page as a Library before 3.9 kept it: no area, no goal, and a page's web address."""
        source = self.vectors.replace_source(title, source_type, [text], [vector()], NOW, "life")
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE knowledge_sources SET domain = '', goal_id = NULL, source_url = ? WHERE id = ?",
                               (url, source["id"]))
        return source["id"]

    def reopen(self):
        Database(self.path)
        return sqlite3.connect(self.path)

    def test_the_move_drops_the_online_tables_and_deletes_imported_pages_with_their_passages_and_vectors(self):
        with sqlite3.connect(self.path) as connection:
            connection.execute("CREATE TABLE network_log (id TEXT PRIMARY KEY, destination TEXT)")
            connection.execute("CREATE TABLE knowledge_acquisitions (id TEXT PRIMARY KEY, title TEXT)")
            connection.execute("CREATE TABLE knowledge_import_plans (id TEXT PRIMARY KEY, acquisition_id TEXT)")
            connection.execute("INSERT INTO network_log VALUES ('net_1', 'en.wikipedia.org')")
        page = self.old_source("Wikipedia · Sleep · Overview", "import", "Sleep is a state of rest.",
                               "https://en.wikipedia.org/wiki/Sleep")
        note = self.old_source("Client report notes", "note", "Send the report to the client on Friday.")
        thread = self.store.thread()
        message = self.store.add_message(thread, "assistant", "ask", "An answer.")
        self.store.record_retrieval(message["id"], self.vectors.search(vector(), 5))
        with sqlite3.connect(self.store.checkpoint_path) as checkpoints:
            checkpoints.execute("CREATE TABLE checkpoints (thread_id TEXT, checkpoint BLOB)")
            checkpoints.execute("INSERT INTO checkpoints VALUES ('topic_1', 'Sleep is a state of rest.')")

        with self.reopen() as connection:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            self.assertFalse(tables & {"network_log", "knowledge_acquisitions", "knowledge_import_plans"})
            self.assertEqual([row[0] for row in connection.execute("SELECT id FROM knowledge_sources")], [note])
            self.assertEqual({row[0] for row in connection.execute("SELECT source_id FROM knowledge_chunks")}, {note})
            self.assertEqual({row[0] for row in connection.execute("SELECT source_id FROM retrieval_matches")}, {note})
        with self.vectors._connect() as vectors:
            self.assertEqual(vectors.execute("SELECT COUNT(*) FROM knowledge_chunk_vectors").fetchone()[0], 1)
        with sqlite3.connect(self.store.checkpoint_path) as checkpoints:
            self.assertEqual(checkpoints.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0], 0)
        self.assertNotIn(page, {source["id"] for source in self.vectors.sources()})

    def test_existing_notes_and_files_get_an_area_by_the_purpose_rule_and_no_goal(self):
        report = self.old_source("Client report notes", "note", "Send it on Friday.")
        piano = self.old_source("Notes", "note", "Practise piano scales every morning.")
        shopping = self.old_source("Shopping list", "document", "Eggs, milk and bread.")

        with self.reopen() as connection:
            areas = dict(connection.execute("SELECT id, domain FROM knowledge_sources WHERE goal_id IS NULL"))
        self.assertEqual(areas, {report: "work", piano: "learning", shopping: "life"})


class LinkTests(LibraryDay):
    def test_an_items_goal_must_be_in_its_area_and_both_can_be_changed_later(self):
        spanish = self.goal("Spanish", "learning")
        office = self.goal("Office move", "work")

        self.assertEqual(self.note("Grammar", "Verb endings.", "learning", office).status_code, 422)
        self.assertEqual(self.client.post("/api/knowledge/sources", json={"title": "Grammar", "sourceType": "note",
                                                                          "text": "Verb endings."}).status_code, 422)
        made = self.note("Grammar", "Verb endings.", "learning", spanish).json()
        self.assertEqual((made["domain"], made["goalId"]), ("learning", spanish))

        moved = self.client.put(f"/api/knowledge/sources/{made['id']}", json={"domain": "work", "goalId": office})
        self.assertEqual(moved.status_code, 200)
        listed = self.sources()["Grammar"]
        self.assertEqual((listed["domain"], listed["goalId"], listed["goalTitle"]), ("work", office, "Office move"))
        self.assertEqual(self.client.put(f"/api/knowledge/sources/{made['id']}",
                                         json={"domain": "life", "goalId": office}).status_code, 422)

    def test_deleting_a_goal_unlinks_its_items_and_keeps_them_and_pausing_keeps_the_link(self):
        shed = self.goal("Garden shed", "project")
        made = self.note("Shed plans", "Timber sizes.", "project", shed).json()

        self.client.put(f"/api/goals/{shed}", json={"title": "Garden shed", "status": "paused"})
        self.assertEqual(self.sources()["Shed plans"]["goalId"], shed)
        self.assertEqual(self.client.delete(f"/api/goals/{shed}").status_code, 200)

        kept = self.sources()["Shed plans"]
        self.assertEqual((kept["id"], kept["domain"], kept["goalId"]), (made["id"], "project", None))

    def test_an_imported_file_takes_the_area_and_goal_chosen_for_it(self):
        spanish = self.goal("Spanish", "learning")
        name = base64.b64encode(b"lesson.md").decode()
        headers = {"Content-Type": "application/octet-stream", "X-DayWright-Filename": name}

        refused = self.client.post("/api/knowledge/import", content=b"# Lesson 4", headers=headers)
        imported = self.client.post("/api/knowledge/import", content=b"# Lesson 4\nVerb endings.",
                                    headers={**headers, "X-DayWright-Area": "learning", "X-DayWright-Goal": spanish})

        self.assertEqual(refused.status_code, 422)
        self.assertEqual((imported.json()["domain"], imported.json()["goalId"]), ("learning", spanish))

    def test_a_search_shows_each_passage_with_its_note_or_file_area_and_goal(self):
        spanish = self.goal("Spanish", "learning")
        self.note("Spanish grammar notes", "Verb endings for the past tense.", "learning", spanish)

        match, = self.client.post("/api/knowledge/search", json={"query": "past tense"}).json()["matches"]

        self.assertEqual((match["sourceTitle"], match["domain"], match["goalId"], match["goalTitle"]),
                         ("Spanish grammar notes", "learning", spanish, "Spanish"))

    def test_a_search_from_one_area_finds_only_its_notes_and_files_and_all_finds_everything(self):
        self.client = TestClient(create_app(database_path=self.path.with_name("ranked.sqlite3"), gateway=self.gateway,
                                            embedding_gateway=NearestFirstEmbeddings()))
        self.note("Office notes", "Desk plans for the move.", "work")
        self.note("Study tips", "Short sessions work best.", "learning")
        self.note("Spanish grammar notes", "Verb endings for the past tense.", "learning")

        def titles(**area):
            found = self.client.post("/api/knowledge/search", json={"query": "plans", "limit": 1, **area}).json()["matches"]
            return [match["sourceTitle"] for match in found]

        self.assertEqual(titles(), ["Office notes"])
        self.assertEqual(titles(domain="learning"), ["Study tips"])
        self.assertEqual(titles(domain="life"), [])


class NearestFirstEmbeddings(FakeEmbeddingGateway):
    """Embeddings that put the office note nearest every question, then the study tips, then the grammar notes."""

    def _vector(self, text):
        values = vector()
        lowered = text.lower()
        for index, (words, offset) in enumerate((("desk", 0.3), ("short sessions", 0.45), ("verb endings", 0.6)), start=3):
            if words in lowered:
                values[index] = offset
        return values


class AvaLibraryTests(LibraryDay):
    def test_the_named_goals_items_come_first_then_its_areas_then_the_rest(self):
        self.client = TestClient(create_app(database_path=self.path.with_name("ranked.sqlite3"), gateway=self.gateway,
                                            embedding_gateway=NearestFirstEmbeddings()))
        spanish = self.goal("Spanish", "learning")
        self.note("Office notes", "Desk plans for the move.", "work")
        self.note("Study tips", "Short sessions work best.", "learning")
        self.note("Spanish grammar notes", "Verb endings for the past tense.", "learning", spanish)
        self.client.post("/api/daily-items", json={
            "date": self.today, "title": "Lesson 4", "detail": "", "domain": "learning", "startTime": None,
            "durationMinutes": 45, "constraintKind": "flexible", "repeatKind": "none", "goalId": spanish})

        for message in ("How should I study for my Spanish goal?", "Help me get ready for Lesson 4"):
            titles = [match["sourceTitle"] for match in self.chat(message)["retrieval"]["matches"]]

            self.assertEqual(titles, ["Spanish grammar notes", "Study tips", "Office notes"], message)

    def test_a_reply_that_used_the_library_ends_with_a_line_naming_exactly_those_items(self):
        self.note("Recovery notes", "My sleep routine starts with a screen-free wind-down.", "life")
        self.note("Budget notes", "Review the grocery budget on Friday.", "life")

        used = self.chat("What did I note about my sleep?")["assistantMessage"]["content"]
        unused = self.chat("What is the capital of France?")["assistantMessage"]["content"]
        chinese = self.chat("我的 sleep 笔记写了什么？", "zh")["assistantMessage"]["content"]

        self.assertTrue(used.endswith("\n\nFrom your Library: Recovery notes"), used)
        self.assertNotIn("Budget notes", used)
        self.assertNotIn("From your Library", unused)
        self.assertTrue(chinese.endswith("\n\n来自你的资料库：Recovery notes"), chinese)

    def test_the_line_names_an_imported_file_as_the_library_lists_it(self):
        name = base64.b64encode("Sleep plan.md".encode()).decode()
        self.client.post("/api/knowledge/import", content="# Sleep plan\nMy sleep routine starts at 22:30.".encode(),
                         headers={"Content-Type": "application/octet-stream", "X-DayWright-Filename": name,
                                  "X-DayWright-Area": "life"})

        used = self.chat("What did I note about my sleep?")["assistantMessage"]["content"]

        self.assertTrue(used.endswith("\n\nFrom your Library: Sleep plan.md"), used)

    def test_the_model_reads_library_passages_after_the_area_context_marked_as_references(self):
        self.note("Recovery notes", "My sleep routine starts with a screen-free wind-down.", "life")

        self.chat("What did I note about my sleep?")

        call = self.gateway.calls[-1]
        context = call["context"]
        self.assertLess(context.index("Bounded agent reports"), context.index("From the user's Library, for reference only"))
        self.assertLess(context.index("From the user's Library, for reference only"), context.index("screen-free wind-down"))
        self.assertIn("advice comes from the area agents' reports and the user's tasks, goals and plans", call["systemPrompt"])


if __name__ == "__main__":
    unittest.main()
