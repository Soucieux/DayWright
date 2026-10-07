import base64
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.database import Database
from backend.app.main import create_app
from backend.app.retrieval import EMBEDDING_DIMENSION, VectorStore
from backend.tests.test_api import FakeEmbeddingGateway, FakeGateway

NOW = "2026-10-07T09:00:00+00:00"


def vector(index=2):
    values = [0.0] * EMBEDDING_DIMENSION
    values[index] = 1.0
    return values


def columns(connection, table):
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


class StudyMoveTests(unittest.TestCase):
    """A Library from v4.8, where every source and folder had an area and a source could have a goal, opened by v4.9."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "v48.sqlite3"
        self.store = Database(self.path)
        self.vectors = VectorStore(self.path)
        with sqlite3.connect(self.path) as connection:
            # v4.8's Library: an area on every source and folder, and a goal on a source; no task links yet.
            connection.execute("ALTER TABLE knowledge_sources ADD COLUMN domain TEXT NOT NULL DEFAULT ''")
            connection.execute("ALTER TABLE knowledge_sources ADD COLUMN goal_id TEXT")
            connection.execute("ALTER TABLE source_folders ADD COLUMN domain TEXT NOT NULL DEFAULT 'learning'")
            connection.execute("DROP TABLE task_sources")
        self.goals = {domain: self.store.create_goal(f"{domain} goal", domain)["id"] for domain in ("learning", "life")}

    def source(self, title, source_type, domain, goal=None, origin=None, folder=None):
        """A v4.8 source with one passage and its vector, in its area and goal."""
        made = self.vectors.replace_source(title, source_type, [f"{title} text."], [vector()], NOW)
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE knowledge_sources SET domain = ?, goal_id = ?, origin = COALESCE(?, origin), folder_id = ? WHERE id = ?",
                               (domain, self.goals.get(goal), origin, folder, made["id"]))
        return made["id"]

    def folder(self, folder_id, domain):
        with sqlite3.connect(self.path) as connection:
            connection.execute("""INSERT INTO source_folders (id, title, path, website, domain, unticked_json, found, created_at)
                                  VALUES (?, ?, ?, '', ?, '[]', 1, ?)""", (folder_id, folder_id, f"/nowhere/{folder_id}", domain, NOW))
        return folder_id

    def website(self, address, domain):
        with sqlite3.connect(self.path) as connection:
            connection.execute("""INSERT INTO knowledge_sources (id, title, source_type, source_url, domain, content_hash, created_at, origin)
                                  VALUES (?, ?, 'document', ?, ?, ?, ?, 'website')""",
                               (f"site_{address}", address, f"https://{address}/", domain, address, NOW))
        return f"site_{address}"

    def test_the_move_deletes_life_work_and_project_sources_and_disconnects_their_folders(self):
        grammar = self.source("Grammar", "note", "learning", "learning")
        lesson = self.source("Lesson 4 · abc", "document", "learning")
        sleep = self.source("Recovery notes", "note", "life", "life")
        brief = self.source("Client brief · def", "document", "work")
        shed = self.source("Shed plans", "note", "project")
        course = self.folder("course", "learning")
        basics = self.source("Basics", "document", "learning", origin="folder", folder=course)
        garden = self.folder("garden", "life")
        roses = self.source("Roses", "document", "life", origin="folder", folder=garden)
        atlas = self.website("atlas.example", "learning")
        vendor = self.website("vendor.example", "work")
        thread = self.store.thread()
        message = self.store.add_message(thread, "assistant", "ask", "From your Library: Recovery notes")
        self.store.record_retrieval(message["id"], self.vectors.search(vector(), 10))

        Database(self.path)

        kept = {grammar, lesson, basics, atlas}
        with sqlite3.connect(self.path) as connection:
            self.assertEqual({row[0] for row in connection.execute("SELECT id FROM knowledge_sources")}, kept)
            self.assertEqual({row[0] for row in connection.execute("SELECT source_id FROM knowledge_chunks")},
                             {grammar, lesson, basics})
            self.assertEqual({row[0] for row in connection.execute("SELECT source_id FROM retrieval_matches")},
                             {grammar, lesson, basics})
            self.assertEqual([row[0] for row in connection.execute("SELECT id FROM source_folders")], [course])
            self.assertFalse({"domain", "goal_id"} & columns(connection, "knowledge_sources"))
            self.assertNotIn("domain", columns(connection, "source_folders"))
            # Ava's reply keeps its words; only her record of the passages it drew on goes.
            self.assertEqual(connection.execute("SELECT content FROM conversation_messages WHERE id = ?",
                                                (message["id"],)).fetchone()[0], "From your Library: Recovery notes")
        with self.vectors._connect() as vectors:
            self.assertEqual(vectors.execute("SELECT COUNT(*) FROM knowledge_chunk_vectors").fetchone()[0], 3)
        for gone in (sleep, brief, shed, roses, vendor):
            self.assertNotIn(gone, {source["id"] for source in self.vectors.sources()})

    def test_a_learning_task_made_from_a_deleted_source_keeps_its_checklist_and_loses_only_the_link(self):
        sleep = self.source("Recovery notes", "note", "life")
        grammar = self.source("Grammar", "note", "learning", "learning")
        for item_id, source, pass_id in (("item_sleep", sleep, "pass_1"), ("item_grammar", grammar, "pass_2")):
            self.store.create_daily_item({"date": date.today().isoformat(), "title": item_id, "detail": "",
                                          "domain": "learning", "startTime": None, "durationMinutes": 30,
                                          "constraintKind": "flexible", "repeatKind": "none", "goalId": None,
                                          "learning": {"sourceId": source, "passId": pass_id,
                                                       "checklist": [{"title": "Wind down", "level": 2}]}})

        Database(self.path)

        with sqlite3.connect(self.path) as connection:
            self.assertEqual(sorted(connection.execute("SELECT pass_id, source_id FROM learning_tasks")),
                             [("pass_1", None), ("pass_2", grammar)])
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM checklist_items").fetchone()[0], 2)

    def test_the_move_runs_once_and_a_new_library_has_no_areas_or_goals(self):
        grammar = self.source("Grammar", "note", "learning")
        Database(self.path)
        self.vectors.replace_source("Recovery notes", "note", ["Recovery notes text."], [vector()], NOW)

        Database(self.path)

        with sqlite3.connect(self.path) as connection:
            self.assertEqual(len(connection.execute("SELECT id FROM knowledge_sources").fetchall()), 2)
            self.assertIn(grammar, {row[0] for row in connection.execute("SELECT id FROM knowledge_sources")})
            self.assertFalse({"domain", "goal_id"} & columns(connection, "knowledge_sources"))
        fresh = Path(self.path).with_name("fresh.sqlite3")
        Database(fresh)
        with sqlite3.connect(fresh) as connection:
            self.assertFalse({"domain", "goal_id"} & columns(connection, "knowledge_sources"))
            self.assertNotIn("domain", columns(connection, "source_folders"))


class StudyLibraryDay(unittest.TestCase):
    """A fresh v4.9 account, its service and its store."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "library.sqlite3"
        self.client = TestClient(create_app(database_path=self.path, gateway=FakeGateway(),
                                            embedding_gateway=FakeEmbeddingGateway()))
        self.today = date.today().isoformat()

    def goal(self, title, domain="learning"):
        return self.client.post("/api/goals", json={"title": title, "domain": domain}).json()["id"]


class SourceShapeTests(StudyLibraryDay):
    def test_a_note_file_or_website_takes_no_area_and_no_goal(self):
        spanish = self.goal("Spanish")
        note = self.client.post("/api/knowledge/sources", json={"title": "Grammar", "sourceType": "note",
                                                                "text": "Verb endings.", "goalId": spanish, "domain": "work"})
        imported = self.client.post("/api/knowledge/import", content=b"# Lesson 4\nVerb endings.", headers={
            "Content-Type": "application/octet-stream", "X-DayWright-Filename": base64.b64encode(b"lesson.md").decode(),
            "X-DayWright-Goal": spanish, "X-DayWright-Area": "work"})
        site = self.client.post("/api/sources/website", json={"address": "https://atlas.example/", "goalId": spanish})

        for made in (note, imported, site):
            self.assertEqual(made.status_code, 200)
            self.assertFalse({"domain", "goalId"} & made.json().keys())
        listed = self.client.get("/api/knowledge").json()["sources"]
        self.assertTrue(all(not {"domain", "goalId", "goalTitle"} & source.keys() for source in listed))
        self.assertEqual(self.client.put(f"/api/knowledge/sources/{note.json()['id']}", json={"goalId": spanish}).status_code, 405)

    def test_search_covers_every_source_and_shows_no_area_or_goal(self):
        for title in ("Office notes", "Study tips"):
            self.client.post("/api/knowledge/sources", json={"title": title, "sourceType": "note", "text": f"{title} plans."})

        found = self.client.post("/api/knowledge/search", json={"query": "plans", "limit": 5}).json()["matches"]

        self.assertEqual({match["sourceTitle"] for match in found}, {"Office notes", "Study tips"})
        self.assertTrue(all(not {"domain", "goalId", "goalTitle"} & match.keys() for match in found))


if __name__ == "__main__":
    unittest.main()
