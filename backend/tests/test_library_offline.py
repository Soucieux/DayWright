import base64
import re
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import sqlite_vec
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

    def note(self, title, text):
        return self.client.post("/api/knowledge/sources", json={"title": title, "sourceType": "note", "text": text})

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

    def test_only_the_one_website_lookup_reaches_beyond_this_mac(self):
        for module in APP.glob("*.py"):
            source = module.read_text()
            for url in re.findall(r"https?://[^\s\"'{}]*", source):
                # The lookup's own words name the schemes it takes; no address beyond this Mac is written in.
                self.assertTrue(url.startswith("http://127.0.0.1") or url.rstrip(".,") in ("http://", "https://"),
                                f"{module.name}: {url}")
            if "urlopen" in source:
                self.assertIn(module.name, {"llama_runtime.py", "model_gateway.py", "retrieval.py", "sources.py"})


class LibraryMoveTests(unittest.TestCase):
    """A Library from before 3.9, which kept no area and no goal, opened by today's DayWright."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "old.sqlite3"
        self.store = Database(self.path)
        self.vectors = VectorStore(self.path)
        with sqlite3.connect(self.path) as connection:
            # A Library from before 3.9 kept no area or goal, and v4.9's task links came long after.
            connection.execute("DROP TABLE task_sources")

    def old_source(self, title, source_type, text, url=""):
        """A note, file or imported page as a Library before 3.9 kept it, with one passage and its vector."""
        source_id = f"source_old_{title}"
        connection = self.vectors._connect()
        try:
            connection.execute("""INSERT INTO knowledge_sources (id, title, source_type, source_url, content_hash, created_at, origin)
                                  VALUES (?, ?, ?, ?, 'x', ?, '')""", (source_id, title, source_type, url, NOW))
            chunk = connection.execute("""INSERT INTO knowledge_chunks (source_id, chunk_index, content, created_at)
                                          VALUES (?, 0, ?, ?)""", (source_id, text, NOW)).lastrowid
            connection.execute("INSERT INTO knowledge_chunk_vectors(rowid, embedding) VALUES (?, ?)",
                               (chunk, sqlite_vec.serialize_float32(vector())))
        finally:
            connection.close()
        return source_id

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
        note = self.old_source("Notes", "note", "Practise piano scales every morning.")
        thread = self.store.thread()
        message = self.store.add_message(thread, "assistant", "ask", "An answer.")
        with sqlite3.connect(self.path) as connection:
            for rank, (source, chunk) in enumerate(connection.execute("SELECT source_id, id FROM knowledge_chunks"), start=1):
                connection.execute("""INSERT INTO retrieval_matches (id, message_id, chunk_id, source_id, source_title, source_type,
                                                                     chunk_index, content, rank, distance, created_at)
                                      VALUES (?, ?, ?, ?, 'title', 'note', 0, 'text', ?, 0.1, ?)""",
                                   (f"match_{rank}", message["id"], chunk, source, rank, NOW))
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

    def test_earlier_notes_and_files_take_an_area_by_the_purpose_rule_and_only_learnings_stay(self):
        self.old_source("Client report notes", "note", "Send it on Friday.")
        piano = self.old_source("Notes", "note", "Practise piano scales every morning.")
        self.old_source("Shopping list", "document", "Eggs, milk and bread.")

        with self.reopen() as connection:
            kept = [row[0] for row in connection.execute("SELECT id FROM knowledge_sources")]
            columns = {row[1] for row in connection.execute("PRAGMA table_info(knowledge_sources)")}
        self.assertEqual(kept, [piano])
        self.assertFalse({"domain", "goal_id"} & columns)


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
    def test_the_named_goals_tasks_sources_come_first_then_the_rest_by_nearness(self):
        self.client = TestClient(create_app(database_path=self.path.with_name("ranked.sqlite3"), gateway=self.gateway,
                                            embedding_gateway=NearestFirstEmbeddings()))
        spanish = self.goal("Spanish", "learning")
        self.note("Office notes", "Desk plans for the move.")
        self.note("Study tips", "Short sessions work best.")
        grammar = self.note("Spanish grammar notes", "Verb endings for the past tense.").json()
        lesson = self.client.post("/api/daily-items", json={
            "date": self.today, "title": "Lesson 4", "detail": "", "domain": "learning", "startTime": None,
            "durationMinutes": 45, "constraintKind": "flexible", "repeatKind": "none", "goalId": spanish}).json()
        self.client.post(f"/api/learning-tasks/{lesson['id']}/sources", json={"sourceId": grammar["id"]})

        for message in ("How should I study for my Spanish goal?", "Help me get ready for Lesson 4"):
            titles = [match["sourceTitle"] for match in self.chat(message)["retrieval"]["matches"]]

            self.assertEqual(titles, ["Spanish grammar notes", "Office notes", "Study tips"], message)

    def test_a_reply_that_used_the_library_ends_with_a_line_naming_exactly_those_items(self):
        self.note("Recovery notes", "My sleep routine starts with a screen-free wind-down.")
        self.note("Budget notes", "Review the grocery budget on Friday.")

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
                         headers={"Content-Type": "application/octet-stream", "X-DayWright-Filename": name})

        used = self.chat("What did I note about my sleep?")["assistantMessage"]["content"]

        self.assertTrue(used.endswith("\n\nFrom your Library: Sleep plan.md"), used)

    def test_the_model_reads_library_passages_after_the_area_context_marked_as_references(self):
        self.note("Recovery notes", "My sleep routine starts with a screen-free wind-down.")

        self.chat("What did I note about my sleep?")

        call = self.gateway.calls[-1]
        context = call["context"]
        self.assertLess(context.index("Bounded agent reports"), context.index("From the user's Library, for reference only"))
        self.assertLess(context.index("From the user's Library, for reference only"), context.index("screen-free wind-down"))
        self.assertIn("advice comes from the area agents' reports and the user's tasks, goals and plans", call["systemPrompt"])


if __name__ == "__main__":
    unittest.main()
