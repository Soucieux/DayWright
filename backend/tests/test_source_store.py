import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app import sources
from backend.app.database import Database
from backend.app.retrieval import EmbeddingUnavailable, RagService, VectorStore, _transaction
from backend.app.source_store import SourceStore
from backend.app.sources import SourceError
from backend.tests.test_api import FakeEmbeddingGateway
from backend.tests.test_sources import LESSON, hashes, tree


class ShelfDay(unittest.TestCase):
    """A fresh account and a throwaway folder of notes, never a real one."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.store = Database(base / "shelf.sqlite3")
        self.shelf = SourceStore(self.store)
        self.folder = tree(base / "Notes", {"Angular/03 Consuming HTTP Services.md": LESSON,
                                           "Angular/01 Basics.md": "# Basics\n\nThe very start of it all.\n",
                                           "README.md": "# Notes\n\nAll my notes.\n", "history/old.md": "# Old\n"})
        # Nothing may reach the network while a folder is read.
        network = patch.object(sources, "urlopen", side_effect=AssertionError("no network"))
        network.start()
        self.addCleanup(network.stop)

    def connect(self, unticked=("README.md",), website=""):
        return self.shelf.connect(str(self.folder), list(unticked), website)

    def titles(self, folder):
        return sorted(source["title"] for source in folder["sources"])


class ConnectTests(ShelfDay):
    def test_a_folder_joins_the_library_with_a_source_for_each_ticked_file(self):
        folder = self.connect()

        self.assertEqual((folder["title"], folder["found"]), ("Notes", True))
        self.assertEqual(self.titles(folder), ["Basics", "Consuming HTTP Services"])
        lesson = next(source for source in folder["sources"] if source["title"] == "Consuming HTTP Services")
        self.assertEqual(lesson["origin"], "folder")
        self.assertEqual(lesson["relativePath"], "Angular/03 Consuming HTTP Services.md")
        self.assertTrue(lesson["briefing"].startswith("Angular's HttpClient sends requests"))
        self.assertEqual(lesson["briefingBy"], "source")
        self.assertEqual([topic["title"] for topic in lesson["outline"][0]["topics"]],
                         ["HttpClient setup", "Interceptors", "Error handling"])

    def test_the_preview_lists_the_tree_before_anything_is_kept(self):
        preview = self.shelf.preview(str(self.folder))

        self.assertEqual({item["path"]: item["ticked"] for item in preview["files"]},
                         {"Angular/01 Basics.md": True, "Angular/03 Consuming HTTP Services.md": True,
                          "README.md": True, "history/old.md": False})
        self.assertEqual(self.shelf.folders(), [])
        with self.assertRaises(SourceError):
            self.shelf.preview(str(self.folder / "README.md"))

    def test_nothing_in_the_folder_changes_whatever_the_library_does(self):
        before = hashes(self.folder)
        folder = self.connect()
        self.shelf.refresh(folder["id"])
        self.shelf.open_target(folder["sources"][0]["id"])

        self.assertEqual(hashes(self.folder), before)


class RefreshTests(ShelfDay):
    def test_refresh_picks_up_new_and_changed_files_and_marks_a_missing_one_without_removing_it(self):
        folder = self.connect()
        (self.folder / "Angular" / "02 Signals.md").write_text("# Signals\n\nState that updates itself.\n", encoding="utf-8")
        (self.folder / "Angular" / "01 Basics.md").write_text("# Basics\n\nA new start.\n", encoding="utf-8")
        (self.folder / "Angular" / "03 Consuming HTTP Services.md").unlink()

        result = self.shelf.refresh(folder["id"])
        folder = self.shelf.folders()[0]

        self.assertEqual((result["added"], result["changed"], result["missing"]),
                         (["Angular/02 Signals.md"], ["Angular/01 Basics.md"], ["Angular/03 Consuming HTTP Services.md"]))
        self.assertEqual(self.titles(folder), ["Basics", "Consuming HTTP Services", "Signals"], "the missing one stays")
        missing = next(source for source in folder["sources"] if source["title"] == "Consuming HTTP Services")
        self.assertTrue(missing["missing"])
        self.assertEqual(next(source for source in folder["sources"] if source["title"] == "Basics")["briefing"], "A new start.")

    def test_an_unticked_file_stays_out_and_a_file_that_comes_back_is_found_again(self):
        folder = self.connect()
        moved = self.folder / "Angular" / "01 Basics.md"
        text = moved.read_text(encoding="utf-8")
        moved.unlink()
        self.shelf.refresh(folder["id"])
        moved.write_text(text, encoding="utf-8")
        self.shelf.refresh(folder["id"])

        folder = self.shelf.folders()[0]
        self.assertNotIn("Notes", self.titles(folder), "README.md was unticked")
        self.assertFalse(any(source["missing"] for source in folder["sources"]))

    def test_a_file_renamed_with_the_same_content_is_followed_to_its_new_name(self):
        folder = self.connect()
        (self.folder / "Angular" / "01 Basics.md").rename(self.folder / "Angular" / "01 Start.md")

        result = self.shelf.refresh(folder["id"])

        self.assertEqual((result["moved"], result["added"], result["missing"]), (["Angular/01 Start.md"], [], []))
        self.assertIn("Angular/01 Start.md", [source["relativePath"] for source in self.shelf.folders()[0]["sources"]])

    def test_a_missing_file_is_located_or_removed_only_when_the_user_chooses(self):
        folder = self.connect()
        lesson = self.folder / "Angular" / "03 Consuming HTTP Services.md"
        lesson.rename(self.folder / "Angular" / "03 HTTP.md")
        (self.folder / "Angular" / "03 HTTP.md").write_text(LESSON + "\nMore.\n", encoding="utf-8")
        self.shelf.refresh(folder["id"])
        missing = next(source for source in self.shelf.folders()[0]["sources"] if source["missing"])

        located = self.shelf.locate(missing["id"], "Angular/03 HTTP.md")
        self.assertEqual((located["relativePath"], located["missing"]), ("Angular/03 HTTP.md", False))
        self.assertEqual(self.titles(self.shelf.folders()[0]), ["Basics", "Consuming HTTP Services"],
                         "the copy refresh had added gives way to the source located")
        self.assertEqual(self.shelf.refresh(folder["id"])["added"], [])
        with self.assertRaises(SourceError):
            self.shelf.locate(missing["id"], "../../outside.md")

        self.shelf.forget(located["id"])
        VectorStore(self.store.path).delete_source(located["id"])
        self.assertNotIn("Consuming HTTP Services", self.titles(self.shelf.folders()[0]))
        self.assertEqual(self.shelf.refresh(folder["id"])["added"], [], "a file removed from the Library stays out")
        self.assertIn("Angular/03 HTTP.md", self.shelf.folders()[0]["unticked"])


class MissingFolderTests(ShelfDay):
    def test_a_folder_that_moved_shows_its_notice_and_keeps_every_source_until_its_new_place_is_given(self):
        folder = self.connect()
        moved = Path(self.temp.name) / "Moved notes"
        shutil.move(str(self.folder), str(moved))

        result = self.shelf.refresh(folder["id"])
        kept = self.shelf.folders()[0]
        self.assertEqual((result["found"], kept["found"]), (False, False))
        self.assertEqual(self.titles(kept), ["Basics", "Consuming HTTP Services"])
        self.assertFalse(any(source["missing"] for source in kept["sources"]), "a lost folder marks no file missing")
        with self.assertRaises(SourceError):
            self.shelf.open_target(kept["sources"][0]["id"])

        (moved / "Angular" / "02 Signals.md").write_text("# Signals\n", encoding="utf-8")
        result = self.shelf.relocate(folder["id"], str(moved))
        found = self.shelf.folders()[0]
        self.assertEqual((found["found"], found["path"], result["added"]), (True, str(moved.resolve()), ["Angular/02 Signals.md"]))


class WebsiteTests(ShelfDay):
    PAGE = {"title": "Learning Atlas", "briefing": "A map of what to learn.",
            "outline": [{"title": "Angular", "topics": [{"title": "Signals"}]}]}

    def test_a_website_saved_by_its_address_is_not_looked_up(self):
        site = self.shelf.add_website("https://atlas.example/", "My own words about it.")

        self.assertEqual((site["origin"], site["address"], site["briefing"], site["briefingBy"], site["lookedUp"]),
                         ("website", "https://atlas.example/", "My own words about it.", "you", False))

    def test_a_website_is_looked_up_once_and_keeps_only_its_title_briefing_and_headings(self):
        site = self.shelf.add_website("https://atlas.example/", "")
        with patch("backend.app.source_store.fetch_page", return_value=self.PAGE) as fetched:
            first = self.shelf.look_up(site["id"])
            again = self.shelf.look_up(site["id"])

        self.assertEqual(fetched.call_count, 1)
        self.assertEqual((first["title"], first["briefing"], first["briefingBy"], first["lookedUp"]),
                         ("Learning Atlas", "A map of what to learn.", "source", True))
        self.assertEqual(again["outline"], self.PAGE["outline"])
        with sqlite3.connect(self.store.path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM knowledge_chunks").fetchone()[0], 0,
                             "no text of the page is stored")

    def test_your_briefing_stays_when_the_page_publishes_none(self):
        site = self.shelf.add_website("https://atlas.example/", "Mine.")
        with patch("backend.app.source_store.fetch_page", return_value={**self.PAGE, "briefing": None}):
            looked = self.shelf.look_up(site["id"])

        self.assertEqual((looked["briefing"], looked["briefingBy"]), ("Mine.", "you"))


class OpenTargetTests(ShelfDay):
    def test_a_folder_file_opens_by_its_own_path_and_on_the_folders_website(self):
        folder = self.connect(website="https://observatory.learning-atlas.workers.dev")
        lesson = next(source for source in folder["sources"] if source["title"] == "Consuming HTTP Services")

        self.assertEqual(self.shelf.open_target(lesson["id"]),
                         {"kind": "file", "path": self.folder.resolve() / "Angular" / "03 Consuming HTTP Services.md"})
        self.assertEqual(self.shelf.open_target(lesson["id"], where="website"),
                         {"kind": "website", "address":
                          "https://observatory.learning-atlas.workers.dev/lesson/angular-03-consuming-http-services"})

    def test_a_note_keeps_only_its_text_so_it_has_nothing_to_open(self):
        with sqlite3.connect(self.store.path) as connection:
            connection.execute("""INSERT INTO knowledge_sources (id, title, source_type, content_hash, created_at, origin)
                                  VALUES ('note-1', 'Tips', 'note', 'x', '2026-10-05', 'note')""")
        with self.assertRaises(SourceError):
            self.shelf.open_target("note-1")

    def test_open_with_is_kept_per_file_type(self):
        self.assertEqual(self.shelf.open_with(), {})
        self.assertEqual(self.shelf.set_open_with({"md": "default", "pdf": "Skim", "exe": "x"}), {"md": "default", "pdf": "Skim"})
        self.assertEqual(self.shelf.open_with(), {"md": "default", "pdf": "Skim"})


class IndexTests(ShelfDay):
    def setUp(self):
        super().setUp()
        self.rag = RagService(VectorStore(self.store.path), FakeEmbeddingGateway())
        self.folder_record = self.connect()

    def chunks(self, title):
        with sqlite3.connect(self.store.path) as connection:
            return [row[0] for row in connection.execute(
                """SELECT c.content FROM knowledge_chunks c JOIN knowledge_sources s ON s.id = c.source_id
                   WHERE s.title = ? ORDER BY c.chunk_index""", (title,))]

    def test_a_folders_files_become_passages_ava_finds_and_cites_by_name(self):
        self.assertEqual(self.shelf.index(self.rag, self.folder_record["id"]), 2)

        self.assertTrue(any("provideHttpClient" in chunk for chunk in self.chunks("Consuming HTTP Services")))
        found = self.rag.retrieve("How do interceptors work?", limit=4)
        self.assertIn("Consuming HTTP Services", {match["sourceTitle"] for match in found.public()["matches"]})
        self.assertEqual(self.shelf.index(self.rag, self.folder_record["id"]), 0, "nothing is indexed twice")

    def test_a_changed_file_is_indexed_again(self):
        self.shelf.index(self.rag, self.folder_record["id"])
        (self.folder / "Angular" / "01 Basics.md").write_text("# Basics\n\nNow about signals.\n", encoding="utf-8")
        self.shelf.refresh(self.folder_record["id"])
        basics = next(source for source in self.shelf.folders()[0]["sources"] if source["title"] == "Basics")

        self.assertEqual(self.shelf.index(self.rag, self.folder_record["id"], changed=[basics["id"]]), 1)
        self.assertTrue(any("signals" in chunk for chunk in self.chunks("Basics")))

    def test_without_the_embedding_model_nothing_is_indexed_and_the_next_time_catches_up(self):
        class Unavailable(FakeEmbeddingGateway):
            def embed_documents(self, texts):
                raise EmbeddingUnavailable("The embedding model isn't running.")

        self.assertEqual(self.shelf.index(RagService(VectorStore(self.store.path), Unavailable()), self.folder_record["id"]), 0)
        self.assertEqual(self.chunks("Basics"), [])
        self.assertEqual(self.shelf.index(self.rag, self.folder_record["id"]), 2)

    def test_a_library_write_holds_the_database_from_its_start_so_indexing_and_a_removal_never_collide(self):
        # Folder indexing writes in the background while a Locate or a Remove may write too. A write that
        # read first and took the database only to write would fail at once, as "database is locked",
        # whenever the other committed in between; one that takes it from its start makes the other wait.
        store = VectorStore(self.store.path)
        connection = store._connect()
        try:
            with _transaction(connection):
                connection.execute("SELECT COUNT(*) FROM knowledge_chunks").fetchone()
                with self.assertRaises(sqlite3.OperationalError, msg="the other write waits for this one"):
                    with sqlite3.connect(self.store.path, timeout=0.1) as other:
                        other.execute("""INSERT INTO knowledge_sources (id, title, source_type, content_hash, created_at)
                                         VALUES ('source_meanwhile', 'Meanwhile', 'note', 'x', '2026-10-06T00:00:00+00:00')""")
                connection.execute("DELETE FROM knowledge_chunks WHERE source_id = 'source_none'")
        finally:
            connection.close()


class EarlierLibraryTests(unittest.TestCase):
    def test_notes_and_files_from_before_take_their_origin(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "old.sqlite3"
            Database(path)
            with sqlite3.connect(path) as connection:
                connection.executemany(
                    "INSERT INTO knowledge_sources (id, title, source_type, content_hash, created_at) VALUES (?, ?, ?, 'x', '2026-10-01')",
                    [("n", "A note", "note"), ("f", "A file · 1a2b", "document")])
                connection.execute("UPDATE knowledge_sources SET origin = ''")
            Database(path)
            with sqlite3.connect(path) as connection:
                origins = dict(connection.execute("SELECT id, origin FROM knowledge_sources"))

        self.assertEqual(origins, {"n": "note", "f": "file"})


if __name__ == "__main__":
    unittest.main()
