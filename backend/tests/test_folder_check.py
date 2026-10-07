import io
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app import folder_check, main, sources
from backend.app.database import Database
from backend.app.folder_check import check_folder, study_material
from backend.app.main import create_app
from backend.tests.test_api import FakeEmbeddingGateway, FakeGateway
from backend.tests.test_sources import hashes, tree

NOW = "2026-10-07T09:00:00+00:00"


class StudyJudge(FakeGateway):
    """A local model that takes every file for study material except an invoice."""

    def reply(self, message, context, system_prompt=None, max_tokens=None):
        self.calls.append({"message": message, "context": context, "systemPrompt": system_prompt})
        return ("No." if "invoice" in message.lower() else "Yes, these are lesson notes.", "test-model")


class NoModel(FakeGateway):
    """No local model: replies come from DayWright's rules."""

    def reply(self, message, context, system_prompt=None, max_tokens=None):
        return ("I can still help with the plan using DayWright’s local rules.", "rules")


def blank_pdf(path):
    """A PDF of one page with no text on it, as a scanned page is."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with path.open("wb") as handle:
        writer.write(handle)


class FolderCheckDay(unittest.TestCase):
    """The service on a fresh account and a throwaway folder: a lesson, an invoice, a scan and a broken PDF."""

    gateway = StudyJudge

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.database = base / "check.sqlite3"
        self.folder = tree(base / "Course", {"Angular/01 Basics.md": "# Basics\n\nComponents and templates.\n",
                                            "Invoices/March invoice.md": "# March invoice\n\nTotal due: 40 EUR.\n"})
        blank_pdf(self.folder / "scan.pdf")
        (self.folder / "broken.pdf").write_bytes(b"%PDF-1.4 not really a PDF")
        self.client = self.service()
        network = patch.object(sources, "urlopen", side_effect=AssertionError("no network"))
        network.start()
        self.addCleanup(network.stop)

    def service(self):
        client = TestClient(create_app(database_path=self.database, gateway=self.gateway(),
                                       embedding_gateway=FakeEmbeddingGateway()))
        self.addCleanup(lambda: [thread.join() for thread in client.app.state.indexing])
        return client

    def settle(self):
        """Wait for the work DayWright does in the background, and the work that work starts: refreshing, indexing
        and checking the folder."""
        while alive := [thread for thread in self.client.app.state.indexing if thread.is_alive()]:
            for thread in alive:
                thread.join()

    def connect(self):
        folder = self.client.post("/api/sources/folder", json={"path": str(self.folder), "unticked": []}).json()
        self.settle()
        return folder

    def cards(self):
        """Ava's folder notices, each with its card, oldest first."""
        return [notice for notice in Database(self.database).notices() if notice["kind"] == "folder-check"]

    def decide(self, card, decision="confirmed", ticked=None):
        return self.client.post(f"/api/actions/{card['id']}", json={"decision": decision, "ticked": ticked})

    def kept(self):
        return sorted(source["relativePath"] for source in self.client.get("/api/knowledge").json()["sources"]
                      if source["origin"] == "folder")


class CheckTests(FolderCheckDay):
    def test_each_kept_file_is_checked_and_ava_reports_ready_unreadable_and_not_study_material(self):
        self.connect()

        notice, = self.cards()
        card = notice["proposal"]
        files = {file["path"]: (file["verdict"], file["ticked"]) for file in card["payload"]["files"]}
        self.assertEqual(files, {"Angular/01 Basics.md": ("ready", True), "Invoices/March invoice.md": ("not-study", False),
                                 "scan.pdf": ("unreadable", False), "broken.pdf": ("unreadable", False)})
        reasons = {file["path"]: file["reason"] for file in card["payload"]["files"]}
        self.assertEqual(reasons["scan.pdf"], "No text to read: it may be scanned pages.")
        self.assertEqual(reasons["broken.pdf"], "This PDF could not be read.")
        self.assertEqual((notice["agentKey"], notice["values"]["ready"], notice["values"]["unreadable"], notice["values"]["notStudy"]),
                         ("learning", 1, 2, 1))
        self.assertIn("Ready to study: 1 · Can't read: 2 · Doesn't look like study material: 1", card["explanation"])
        self.assertEqual(len(self.kept()), 4, "nothing changes before Confirm")

    def test_confirm_removes_the_files_left_unticked_and_keeps_one_ticked_back(self):
        self.connect()
        card = self.cards()[0]["proposal"]

        self.decide(card, ticked=["Angular/01 Basics.md", "Invoices/March invoice.md"])

        self.assertEqual(self.kept(), ["Angular/01 Basics.md", "Invoices/March invoice.md"])
        folder, = self.client.get("/api/knowledge").json()["folders"]
        self.assertEqual(sorted(folder["unticked"]), ["broken.pdf", "scan.pdf"])
        self.client.post(f"/api/sources/folder/{folder['id']}/refresh")
        self.settle()
        self.assertEqual(self.kept(), ["Angular/01 Basics.md", "Invoices/March invoice.md"])
        self.assertEqual(len(self.cards()), 1, "a refresh with nothing new reports nothing")

    def test_dismissing_the_card_leaves_the_folder_as_connected(self):
        self.connect()

        self.decide(self.cards()[0]["proposal"], "dismissed")

        self.assertEqual(len(self.kept()), 4)

    def test_a_refresh_checks_and_reports_only_new_or_changed_files(self):
        folder = self.connect()
        self.decide(self.cards()[0]["proposal"], ticked=["Angular/01 Basics.md"])
        tree(self.folder, {"Angular/02 Signals.md": "# Signals\n\nState that updates the view.\n",
                           "Angular/01 Basics.md": "# Basics\n\nComponents, templates and bindings.\n"})

        self.client.post(f"/api/sources/folder/{folder['id']}/refresh")
        self.settle()

        latest = self.cards()[-1]["proposal"]
        self.assertEqual([file["path"] for file in latest["payload"]["files"]], ["Angular/01 Basics.md", "Angular/02 Signals.md"])

    def test_the_folder_shows_it_is_being_checked_from_connect_until_the_check_ends(self):
        release = threading.Event()

        def held(*args):
            release.wait(10)
            return check_folder(*args)

        with patch.object(main, "check_folder", held):
            self.client.post("/api/sources/folder", json={"path": str(self.folder), "unticked": []})
            folder, = self.client.get("/api/knowledge").json()["folders"]
            release.set()
            self.settle()

        self.assertEqual(folder["checking"], {"done": 0, "total": None}, "marked before the files are counted")
        self.assertIsNone(self.client.get("/api/knowledge").json()["folders"][0]["checking"])
        self.assertEqual(len(self.cards()), 1)

    def test_a_refresh_during_a_check_waits_its_turn_and_every_file_is_reported_once(self):
        release = threading.Event()

        def held(*args):
            release.wait(10)
            return study_material(*args)

        with patch.object(folder_check, "study_material", held), patch("sys.stderr", new_callable=io.StringIO) as errors:
            folder = self.client.post("/api/sources/folder", json={"path": str(self.folder), "unticked": []}).json()
            tree(self.folder, {"Angular/02 Signals.md": "# Signals\n\nState that updates the view.\n"})
            self.client.post(f"/api/sources/folder/{folder['id']}/refresh")
            release.set()
            self.settle()

        self.assertNotIn("couldn't check", errors.getvalue())
        files = [file["path"] for notice in self.cards() for file in notice["proposal"]["payload"]["files"]]
        self.assertEqual(sorted(files), ["Angular/01 Basics.md", "Angular/02 Signals.md", "Invoices/March invoice.md",
                                         "broken.pdf", "scan.pdf"])
        self.assertIsNone(self.client.get("/api/knowledge").json()["folders"][0]["checking"])

    def test_a_check_that_fails_leaves_the_folder_unmarked(self):
        with patch.object(Database, "folder_checks", side_effect=sqlite3.OperationalError("disk I/O error")):
            self.connect()

        self.assertIsNone(self.client.get("/api/knowledge").json()["folders"][0]["checking"])

    def test_the_folder_itself_is_never_written(self):
        before = hashes(self.folder)
        times = {path: path.stat().st_mtime_ns for path in self.folder.rglob("*")}

        self.connect()
        self.decide(self.cards()[0]["proposal"], ticked=[])

        self.assertEqual(hashes(self.folder), before)
        self.assertEqual({path: path.stat().st_mtime_ns for path in self.folder.rglob("*")}, times)


class NoModelTests(FolderCheckDay):
    gateway = NoModel

    def test_without_the_model_only_readability_is_checked_and_the_card_says_so(self):
        self.connect()

        card = self.cards()[0]["proposal"]

        self.assertFalse(card["payload"]["modelChecked"])
        self.assertEqual({file["path"]: file["verdict"] for file in card["payload"]["files"]}["Invoices/March invoice.md"], "ready")
        self.assertIn("The study check couldn't run", card["explanation"])


class MoveCheckTests(FolderCheckDay):
    def test_a_learn_folder_kept_by_the_move_is_checked_on_the_first_launch_after_it(self):
        with sqlite3.connect(self.database) as connection:
            connection.execute("ALTER TABLE knowledge_sources ADD COLUMN domain TEXT NOT NULL DEFAULT ''")
            connection.execute("ALTER TABLE knowledge_sources ADD COLUMN goal_id TEXT")
            connection.execute("ALTER TABLE source_folders ADD COLUMN domain TEXT NOT NULL DEFAULT 'learning'")
            connection.execute("DROP TABLE task_sources")
            connection.execute("DROP TABLE folder_checks")
            connection.execute("""INSERT INTO source_folders (id, title, path, website, domain, unticked_json, found, created_at)
                                  VALUES ('folder_course', 'Course', ?, '', 'learning', '[]', 1, ?)""", (str(self.folder), NOW))
            connection.execute("""INSERT INTO knowledge_sources (id, title, source_type, content_hash, created_at, origin,
                                                                 folder_id, relative_path, domain)
                                  VALUES ('source_basics', 'Basics', 'document', 'old', ?, 'folder', 'folder_course',
                                          'Angular/01 Basics.md', 'learning')""", (NOW,))

        with self.service() as client:
            self.client = client
            self.settle()

        notice, = self.cards()
        self.assertEqual(notice["values"]["folderId"], "folder_course")
        self.assertIn("Angular/01 Basics.md", [file["path"] for file in notice["proposal"]["payload"]["files"]])


if __name__ == "__main__":
    unittest.main()
