import sqlite3
import subprocess
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app import opener, sources
from backend.app.main import create_app
from backend.tests.test_api import FakeEmbeddingGateway, FakeGateway
from backend.tests.test_sources import LESSON, hashes, tree


TODAY = date.today().isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


class RouteDay(unittest.TestCase):
    """The service on a fresh account, a throwaway folder of notes, and a count of every network call."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.gateway = FakeGateway()
        self.database = base / "routes.sqlite3"
        self.client = TestClient(create_app(database_path=self.database, gateway=self.gateway,
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
            entries = self.client.get(f"/api/sources/entries?sourceId={site['id']}").json()["entries"]
            self.client.post("/api/learning-tasks", json={"sourceIds": [site["id"]], "date": TODAY})
        self.assertEqual((looked.json()["title"], fetched.call_count), ("Atlas", 1))
        self.assertEqual([(entry["title"], entry["sections"]) for entry in entries], [("Atlas", ["Computed"])])

    def test_a_site_that_cant_be_reached_says_so(self):
        site = self.client.post("/api/sources/website", json={"address": "https://atlas.example/", "briefing": "", "domain": "learning"}).json()
        answer = self.client.post(f"/api/sources/{site['id']}/look-up")
        self.assertEqual((answer.status_code, answer.json()["detail"]), (422, "The website could not be reached."))
        self.assertEqual(self.client.post("/api/sources/website", json={"address": "ftp://x", "briefing": "", "domain": "learning"}).status_code, 422)


class OriginalFileRouteTests(RouteDay):
    def choose(self, stdout, code=0, multiple=True):
        with patch("backend.app.main.subprocess.run", return_value=subprocess.CompletedProcess([], code, stdout=stdout)) as run:
            answer = self.client.post("/api/sources/files/choose", json={"multiple": multiple}).json()
        self.assertEqual(run.call_args.args[0][0], "osascript", "the Mac's own window")
        return answer

    def imported(self):
        original = self.folder / "Angular" / "03 Consuming HTTP Services.md"
        unread = self.folder / "notes.txt"
        unread.write_text("Not a kind DayWright reads.", encoding="utf-8")
        chosen = self.choose(f"{original}\n{unread}\n")
        self.assertEqual(chosen, {"paths": [str(original), str(unread)]})
        answer = self.client.post("/api/sources/files/import", json={"paths": chosen["paths"], "domain": "learning"}).json()
        self.assertEqual([(failed["name"], failed["reason"]) for failed in answer["failed"]],
                         [("notes.txt", "Supported files are Markdown (.md), PDF (.pdf), and Word (.docx)")])
        return original, answer["saved"][0]

    def listed(self, source_id):
        return next(source for source in self.client.get("/api/knowledge").json()["sources"] if source["id"] == source_id)

    def open(self, source_id):
        with patch.object(opener.subprocess, "run") as run, patch("backend.app.main.obsidian_installed", return_value=False):
            answer = self.client.post(f"/api/sources/{source_id}/open", json={"where": "app"})
        return answer, run

    def test_a_file_chosen_on_the_mac_remembers_where_it_is_and_opens_there(self):
        original, saved = self.imported()
        self.assertTrue(saved["title"].startswith("03 Consuming HTTP Services.md · "), "named as an upload is")
        listed = self.listed(saved["id"])
        self.assertEqual((listed["originalPath"], listed["originalFound"]), (str(original.resolve()), True))

        answer, run = self.open(saved["id"])
        self.assertEqual(answer.status_code, 200, answer.text)
        self.assertEqual(run.call_args.args[0], ["open", str(original.resolve())])
        self.assertEqual(self.choose("", code=1), {"paths": []}, "a cancelled pick chooses nothing")

    def test_a_moved_original_is_not_found_until_it_is_located(self):
        original, saved = self.imported()
        moved = self.folder / "Moved.md"
        original.rename(moved)

        self.assertFalse(self.listed(saved["id"])["originalFound"])
        answer, run = self.open(saved["id"])
        self.assertEqual((answer.status_code, answer.json()["detail"]), (422, "Original not found."))
        run.assert_not_called()

        missing = str(self.folder / "none.md")
        self.assertEqual(self.client.post(f"/api/sources/{saved['id']}/original", json={"path": missing}).status_code, 422)
        located = self.client.post(f"/api/sources/{saved['id']}/original", json={"path": str(moved)}).json()
        self.assertEqual((located["originalPath"], self.listed(saved["id"])["originalFound"]), (str(moved.resolve()), True))
        self.assertEqual(self.open(saved["id"])[1].call_args.args[0], ["open", str(moved.resolve())])

    def test_a_file_uploaded_from_the_browser_keeps_only_its_text(self):
        uploaded = self.client.post("/api/knowledge/import", content=b"# Uploaded\n\nSome text.\n", headers={
            "content-type": "application/octet-stream", "x-daywright-filename": "VXBsb2FkZWQubWQ=", "x-daywright-area": "learning"})
        self.assertEqual(uploaded.status_code, 200, uploaded.text)
        self.assertIsNone(self.listed(uploaded.json()["id"])["originalPath"])
        self.assertEqual(self.open(uploaded.json()["id"])[0].status_code, 422)


class LearningTaskRouteTests(RouteDay):
    def made(self, folder, **choices):
        entries = self.client.get(f"/api/sources/entries?folderId={folder['id']}").json()["entries"]
        lesson = next(entry for entry in entries if entry["title"] == "Consuming HTTP Services")
        self.assertEqual(lesson["sections"], ["HttpClient setup", "Interceptors", "Error handling"])
        made = self.client.post("/api/learning-tasks", json={"sourceIds": [lesson["sourceId"]], "date": TODAY, **choices})
        self.assertEqual(made.status_code, 200, made.text)
        return made.json()

    def test_ticked_files_become_tasks_in_a_goal_and_their_checklists_are_edited_and_ticked(self):
        made = self.made(self.connect(), goal={"title": "Angular"})
        task_id = made["tasks"][0]["id"]
        self.assertEqual((made["goal"]["title"], made["tasks"][0]["goalId"]), ("Angular", made["goal"]["id"]))
        checklist = self.client.get(f"/api/learning-tasks/{task_id}/checklist").json()
        self.assertEqual(checklist["sections"], ["HttpClient setup", "Interceptors", "Error handling"])

        first = checklist["checklist"][0]["id"]
        ticked = self.client.post(f"/api/learning-tasks/{task_id}/checklist/{first}/tick", json={"done": True}).json()
        self.assertEqual(ticked["progress"], {"done": 1, "total": 3})
        added = self.client.post(f"/api/learning-tasks/{task_id}/checklist", json={"title": "Read the RFC"}).json()
        mine = added["checklist"][-1]
        self.assertEqual((mine["title"], mine["addedBy"]), ("Read the RFC", "you"))
        renamed = self.client.put(f"/api/learning-tasks/{task_id}/checklist/{mine['id']}", json={"title": "Skim the RFC"}).json()
        self.assertEqual(renamed["sections"][-1], "Skim the RFC")
        moved = self.client.post(f"/api/learning-tasks/{task_id}/checklist/{mine['id']}/move", json={"index": 0}).json()
        self.assertEqual(moved["sections"][0], "Skim the RFC")
        removed = self.client.delete(f"/api/learning-tasks/{task_id}/checklist/{mine['id']}").json()
        self.assertEqual(removed["sections"], ["HttpClient setup", "Interceptors", "Error handling"])

        listed = next(source for source in self.client.get("/api/knowledge").json()["sources"] if source["id"] == checklist["sourceId"])
        self.assertEqual(listed["progress"], {"done": 1, "total": 3}, "the Library shows the file's latest pass")
        self.assertEqual(self.client.put(f"/api/learning-tasks/{task_id}/effort", json={"effort": "deep"}).json()["effortBy"], "you")
        self.assertEqual(self.client.put(f"/api/learning-tasks/{task_id}/effort", json={"effort": "huge"}).status_code, 422)
        self.assertEqual(self.client.post(f"/api/learning-tasks/{task_id}/checklist", json={"title": "  "}).status_code, 422)
        self.assertEqual(self.client.get("/api/learning-tasks/item_none/checklist").status_code, 404)
        self.assertEqual(self.client.post("/api/learning-tasks", json={"sourceIds": [made["tasks"][0]["id"]], "date": TODAY}).status_code,
                         404, "an unknown source")

    def test_a_past_tasks_checklist_is_read_only_on_screen(self):
        task_id = self.made(self.connect())["tasks"][0]["id"]
        first = self.client.get(f"/api/learning-tasks/{task_id}/checklist").json()["checklist"][0]["id"]
        with sqlite3.connect(self.database) as connection:
            connection.execute("UPDATE daily_items SET item_date = ? WHERE id = ?", (YESTERDAY, task_id))
        answer = self.client.post(f"/api/learning-tasks/{task_id}/checklist/{first}/tick", json={"done": True})
        self.assertEqual(answer.status_code, 409)
        self.assertIn("through Ava", answer.json()["detail"])
        self.assertEqual(self.client.post(f"/api/learning-tasks/{task_id}/checklist", json={"title": "More"}).status_code, 409)

    def test_files_go_one_a_day_and_a_task_without_a_source_gets_its_own_checklist(self):
        folder = self.connect()
        entries = self.client.get(f"/api/sources/entries?folderId={folder['id']}").json()["entries"]
        spread = self.client.post("/api/learning-tasks", json={"sourceIds": [entry["sourceId"] for entry in entries],
                                                               "date": TODAY, "oneADay": True}).json()
        self.assertEqual([task["date"] for task in spread["tasks"]], [TODAY, TOMORROW])

        own = self.client.post("/api/daily-items", json={"date": TODAY, "title": "Scales", "detail": "", "domain": "learning",
                                                       "goalId": None, "startTime": None, "durationMinutes": 30,
                                                       "constraintKind": "flexible", "repeatKind": "none"}).json()
        self.assertEqual(self.client.get(f"/api/learning-tasks/{own['id']}/checklist").json()["checklist"], [])
        listed = self.client.post(f"/api/learning-tasks/{own['id']}/checklist", json={"title": "C major"}).json()
        self.assertEqual(listed["sections"], ["C major"])

    def test_opening_an_untimed_website_tasks_briefing_on_its_day_looks_it_up_once(self):
        site = self.client.post("/api/sources/website", json={"address": "https://atlas.example/", "briefing": "", "domain": "learning"}).json()
        with patch("backend.app.source_store.fetch_page", return_value=WebsiteRouteTests.PAGE):
            self.client.post(f"/api/sources/{site['id']}/look-up")
        task_id = self.client.post("/api/learning-tasks", json={"sourceIds": [site["id"]], "date": TODAY}).json()["tasks"][0]["id"]
        grown = {**WebsiteRouteTests.PAGE, "outline": [{"title": "Signals", "topics": [{"title": "Computed"}, {"title": "Effects"}]}]}
        with patch("backend.app.source_store.fetch_page", return_value=grown) as fetched:
            opened = self.client.post(f"/api/learning-tasks/{task_id}/briefing-opened").json()
            self.client.post(f"/api/learning-tasks/{task_id}/briefing-opened")
        self.assertEqual(fetched.call_count, 1)
        self.assertEqual((opened["startCheck"], [entry["pageState"] for entry in opened["checklist"]]), ("updated", ["", "new"]))


if __name__ == "__main__":
    unittest.main()
