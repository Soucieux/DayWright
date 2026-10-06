import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app import opener, sources
from backend.app.main import create_app
from backend.tests.test_api import FakeEmbeddingGateway, FakeGateway
from backend.tests.test_sources import LESSON, hashes, tree


class RouteDay(unittest.TestCase):
    """The service on a fresh account, a throwaway folder of notes, and a count of every network call."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.gateway = FakeGateway()
        self.client = TestClient(create_app(database_path=base / "routes.sqlite3", gateway=self.gateway,
                                            embedding_gateway=FakeEmbeddingGateway()))
        # Folder indexing runs in the background; it finishes before the throwaway folder goes.
        self.addCleanup(lambda: [thread.join() for thread in self.client.app.state.indexing])
        self.folder = tree(base / "Notes", {"Angular/03 Consuming HTTP Services.md": LESSON,
                                           "Angular/01 Basics.md": "# Basics\n\nThe very start.\n"})
        self.calls = []

        def offline(*args, **kwargs):
            self.calls.append(args)
            raise OSError("offline")

        network = patch.object(sources, "urlopen", side_effect=offline)
        network.start()
        self.addCleanup(network.stop)

    def connect(self, website=""):
        answer = self.client.post("/api/sources/folder", json={"path": str(self.folder), "unticked": [], "website": website,
                                                               "domain": "learning"})
        self.assertEqual(answer.status_code, 200, answer.text)
        return answer.json()

    def lesson(self, folder):
        return next(source for source in folder["sources"] if source["title"] == "Consuming HTTP Services")


class FolderRouteTests(RouteDay):
    def test_a_folder_is_previewed_connected_and_listed_with_the_library(self):
        preview = self.client.post("/api/sources/folder/preview", json={"path": str(self.folder)})
        self.assertEqual([item["path"] for item in preview.json()["files"]],
                         ["Angular/01 Basics.md", "Angular/03 Consuming HTTP Services.md"])
        folder = self.connect()

        library = self.client.get("/api/knowledge").json()
        self.assertEqual([item["id"] for item in library["folders"]], [folder["id"]])
        self.assertEqual({source["origin"] for source in library["sources"]}, {"folder"})
        self.assertIn("openWith", library)
        self.assertIn("obsidian", library)
        self.assertEqual(self.client.post("/api/sources/folder/preview", json={"path": str(self.folder / "nope")}).status_code, 422)

    def test_refresh_relocate_and_locate_go_through_the_service_and_the_folder_never_changes(self):
        before = hashes(self.folder)
        folder = self.connect()
        self.assertEqual(self.client.post(f"/api/sources/folder/{folder['id']}/refresh").json()["found"], True)
        self.assertEqual(hashes(self.folder), before)

        moved = Path(self.temp.name) / "Moved"
        self.folder.rename(moved)
        self.assertEqual(self.client.post(f"/api/sources/folder/{folder['id']}/refresh").json()["found"], False)
        self.assertEqual(len(self.client.get("/api/knowledge").json()["sources"]), 2, "nothing is removed")
        relocated = self.client.post(f"/api/sources/folder/{folder['id']}/relocate", json={"path": str(moved)})
        self.assertEqual(relocated.json()["found"], True)

        (moved / "Angular" / "01 Basics.md").rename(moved / "Angular" / "01 Start.md")
        (moved / "Angular" / "01 Start.md").write_text("# Basics\n\nChanged.\n", encoding="utf-8")
        self.client.post(f"/api/sources/folder/{folder['id']}/refresh")
        missing = next(source for source in self.client.get("/api/knowledge").json()["sources"] if source["missing"])
        located = self.client.post(f"/api/sources/{missing['id']}/locate", json={"relativePath": "Angular/01 Start.md"})
        self.assertEqual((located.status_code, located.json()["missing"]), (200, False))

        self.assertEqual(self.client.delete(f"/api/knowledge/sources/{missing['id']}").status_code, 200)
        self.client.post(f"/api/sources/folder/{folder['id']}/refresh")
        self.assertEqual([source["title"] for source in self.client.get("/api/knowledge").json()["sources"]],
                         ["Consuming HTTP Services"], "a file removed from the Library stays out after Refresh")
        self.assertTrue((moved / "Angular" / "01 Start.md").is_file(), "removing never touches the file")

    def test_the_mac_picks_the_folder_and_a_cancelled_pick_gives_none(self):
        with patch("backend.app.main.subprocess.run", return_value=subprocess.CompletedProcess([], 0, stdout=f"{self.folder}/\n")) as run:
            self.assertEqual(self.client.post("/api/sources/folder/choose").json(), {"path": f"{self.folder}/"})
        self.assertEqual(run.call_args.args[0][0], "osascript")
        with patch("backend.app.main.subprocess.run", return_value=subprocess.CompletedProcess([], 1, stdout="", stderr="User canceled.")):
            self.assertEqual(self.client.post("/api/sources/folder/choose").json(), {"path": None})


class OpenRouteTests(RouteDay):
    def test_a_source_opens_by_its_stored_path_only_and_open_with_is_kept(self):
        folder = self.connect(website="https://observatory.learning-atlas.workers.dev")
        lesson = self.lesson(folder)
        with patch.object(opener.subprocess, "run") as run, patch("backend.app.main.obsidian_installed", return_value=False):
            answer = self.client.post(f"/api/sources/{lesson['id']}/open", json={"where": "app", "path": "/etc/passwd"})
            self.assertEqual(answer.status_code, 200, answer.text)
            self.assertEqual(run.call_args.args[0], ["open", str(self.folder.resolve() / "Angular" / "03 Consuming HTTP Services.md")])
            self.client.post(f"/api/sources/{lesson['id']}/open", json={"where": "website"})
            self.assertEqual(run.call_args.args[0][-1],
                             "https://observatory.learning-atlas.workers.dev/lesson/angular-03-consuming-http-services")

        self.assertEqual(self.client.put("/api/sources/open-with", json={"pdf": "Skim"}).json(), {"pdf": "Skim"})
        self.assertEqual(self.client.get("/api/knowledge").json()["openWith"], {"pdf": "Skim"})
        self.assertEqual(self.client.post("/api/sources/source_none/open", json={"where": "app"}).status_code, 404)


class WebsiteRouteTests(RouteDay):
    PAGE = {"title": "Atlas", "briefing": "A map.", "outline": [{"title": "Signals", "topics": [{"title": "Computed"}]}]}

    def test_the_network_is_reached_once_when_a_website_is_looked_up_and_never_elsewhere(self):
        folder = self.connect()
        site = self.client.post("/api/sources/website", json={"address": "https://atlas.example/", "briefing": "", "domain": "learning"}).json()
        self.client.post(f"/api/sources/folder/{folder['id']}/refresh")
        self.client.get("/api/knowledge")
        self.client.get(f"/api/sources/entries?folderId={folder['id']}")
        self.assertEqual(self.calls, [], "no network until the lookup")

        with patch("backend.app.source_store.fetch_page", return_value=self.PAGE) as fetched:
            looked = self.client.post(f"/api/sources/{site['id']}/look-up")
            self.client.post(f"/api/sources/{site['id']}/look-up")
            entries = self.client.get(f"/api/sources/entries?sourceId={site['id']}").json()
            self.client.post("/api/goals/from-source", json={"picks": [{"sourceId": site["id"], "index": 0}]})
        self.assertEqual((looked.json()["title"], fetched.call_count), ("Atlas", 1))
        self.assertEqual([entry["title"] for entry in entries], ["Signals"])

    def test_a_site_that_cant_be_reached_says_so(self):
        site = self.client.post("/api/sources/website", json={"address": "https://atlas.example/", "briefing": "", "domain": "learning"}).json()
        answer = self.client.post(f"/api/sources/{site['id']}/look-up")
        self.assertEqual((answer.status_code, answer.json()["detail"]), (422, "The website could not be reached."))
        self.assertEqual(self.client.post("/api/sources/website", json={"address": "ftp://x", "briefing": "", "domain": "learning"}).status_code, 422)


class GoalRouteTests(RouteDay):
    def test_goals_are_made_from_ticked_entries_and_a_topics_effort_is_set(self):
        folder = self.connect()
        entries = self.client.get(f"/api/sources/entries?folderId={folder['id']}").json()
        lesson = next(entry for entry in entries if entry["title"] == "Consuming HTTP Services")

        made = self.client.post("/api/goals/from-source", json={"picks": [{"sourceId": lesson["sourceId"]}]})
        self.assertEqual(made.status_code, 200, made.text)
        goal = made.json()["goals"][0]
        self.assertEqual([topic["title"] for topic in goal["topics"]], ["HttpClient setup", "Interceptors", "Error handling"])

        topic = goal["topics"][0]
        changed = self.client.put(f"/api/topics/{topic['id']}/effort", json={"effort": "deep"}).json()
        self.assertEqual((changed["profile"]["effort"], changed["effortBy"]), ("deep", "you"))
        self.assertEqual(self.client.put(f"/api/topics/{topic['id']}/effort", json={"effort": "huge"}).status_code, 422)
        self.assertEqual(self.client.post("/api/goals/from-source", json={"picks": [{"sourceId": lesson["sourceId"]}]}).status_code, 422,
                         "a goal name already in use")


if __name__ == "__main__":
    unittest.main()
