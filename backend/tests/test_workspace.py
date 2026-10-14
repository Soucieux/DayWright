"""Switching between the user's own workspace and the demo: the demo's own folder, the switch asked for through the
service, which starts the same program again in place on the same port, the demo's title, and nothing anywhere
recording the choice, so a new launch opens the user's own workspace."""

import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app import desktop, workspace
from backend.app.config import DEMO_FOLDER, DEMO_VARIABLE, load_settings
from backend.app.database import Database
from backend.app.desktop import CLIENT_VARIABLE, DATABASE_VARIABLE, PORT_VARIABLE, TOKEN_VARIABLE
from backend.app.main import create_app
from backend.app.time_taken import demo_title

TODAY = date.today().isoformat()


class Workspaces(unittest.TestCase):
    """A data folder of its own, holding the user's own database and, beside it, the demo's folder."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / "DayWright"
        self.own = self.data / "daywright.sqlite3"
        environment = patch.dict(os.environ, {DATABASE_VARIABLE: str(self.own)})
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop(DEMO_VARIABLE, None)
        self.switches = []

    def client(self, demo: bool = False) -> TestClient:
        """The service over the user's own workspace, or the demo's, already made; its switches are recorded."""
        if demo:
            Database(self.data / DEMO_FOLDER / self.own.name)
        with patch.dict(os.environ, {DEMO_VARIABLE: "1"} if demo else {}):
            return TestClient(create_app(switch=lambda opens_demo, reset: self.switches.append((opens_demo, reset))))

    def snapshot(self) -> dict:
        """Every file in the data folder with its bytes."""
        return {str(path.relative_to(self.data)): path.read_bytes() for path in sorted(self.data.rglob("*")) if path.is_file()}


class DemoPathTests(Workspaces):
    def test_the_demo_has_a_folder_of_its_own_beside_the_users_database(self):
        own = load_settings()
        self.assertEqual((own.database_path, own.data_directory, own.demo_mode), (self.own, self.data, False))
        with patch.dict(os.environ, {DEMO_VARIABLE: "1"}):
            demo = load_settings()
        self.assertEqual((demo.database_path, demo.data_directory, demo.demo_mode),
                         (self.data / DEMO_FOLDER / "daywright.sqlite3", self.data, True))


class SwitchRouteTests(Workspaces):
    def test_open_the_demo_asks_to_start_again_in_it_and_reset_deletes_it_first(self):
        client = self.client()
        answer = client.post("/api/workspace", json={"workspace": "demo"})
        self.assertEqual((answer.status_code, answer.json()), (202, {"workspace": "demo", "reset": False}))
        self.assertEqual(client.post("/api/workspace", json={"workspace": "demo", "reset": True}).status_code, 202)
        self.assertEqual(self.switches, [(True, None), (True, self.data / DEMO_FOLDER)])

    def test_back_to_my_data_asks_to_start_again_in_the_users_own_and_the_demo_can_be_reset_from_itself(self):
        client = self.client(demo=True)
        self.assertEqual(client.post("/api/workspace", json={"workspace": "own"}).status_code, 202)
        self.assertEqual(client.post("/api/workspace", json={"workspace": "demo", "reset": True}).status_code, 202)
        self.assertEqual(self.switches, [(False, None), (True, self.data / DEMO_FOLDER)])

    def test_the_workspace_already_open_is_not_opened_again_and_only_the_demo_resets(self):
        self.assertEqual(self.client().post("/api/workspace", json={"workspace": "own"}).status_code, 409)
        self.assertEqual(self.client(demo=True).post("/api/workspace", json={"workspace": "demo"}).status_code, 409)
        self.assertEqual(self.client().post("/api/workspace", json={"workspace": "own", "reset": True}).status_code, 422)
        self.assertEqual(self.switches, [])

    def test_the_service_says_which_workspace_is_open(self):
        for demo in (False, True):
            client = self.client(demo)
            self.assertEqual(client.get("/api/health").json()["demoMode"], demo)
            self.assertEqual(client.get("/api/bootstrap", params={"date": "2026-10-12"}).json()["demoMode"], demo)

    def test_the_service_says_whether_the_demo_is_made_so_the_window_says_it_is_being_made(self):
        self.assertFalse(self.client().get("/api/health").json()["demoMade"])
        self.assertTrue(self.client(demo=True).get("/api/health").json()["demoMade"])
        self.assertTrue(self.client().get("/api/health").json()["demoMade"])

    def test_a_demo_that_cant_be_made_leaves_the_users_own_workspace_open_and_says_so(self):
        self.client().post("/api/daily-items", json={"date": TODAY, "title": "Library visit", "domain": "learning",
                                                      "durationMinutes": 60})
        with patch("backend.app.main.build_demo", side_effect=OSError("disk full")), patch.dict(os.environ, {DEMO_VARIABLE: "1"}):
            client = TestClient(create_app(switch=lambda opens_demo, reset: self.switches.append((opens_demo, reset))))
            self.assertNotIn(DEMO_VARIABLE, os.environ, "a later start, and a switch, begin from the user's own workspace")
        health = client.get("/api/health").json()
        self.assertEqual((health["demoMode"], health["demoFailed"]), (False, True))
        titles = [item["title"] for item in client.get("/api/bootstrap", params={"date": TODAY}).json()["dayItems"]]
        self.assertEqual(titles, ["Library visit"])
        self.assertFalse(self.client().get("/api/health").json()["demoFailed"])

    def test_each_start_of_the_service_has_its_own_mark_so_the_window_knows_the_switch_is_done(self):
        client = self.client()
        first = client.get("/api/health").json()["started"]
        self.assertEqual(client.get("/api/health").json()["started"], first)
        self.assertNotEqual(self.client().get("/api/health").json()["started"], first)

    def test_nothing_records_the_choice_so_quitting_in_the_demo_reopens_the_users_own_workspace(self):
        client = self.client()
        before = self.snapshot()
        client.post("/api/workspace", json={"workspace": "demo"})
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(load_settings().demo_mode)
        self.assertFalse(self.client().get("/api/health").json()["demoMode"])


class TitleTests(Workspaces):
    def test_the_menu_bar_title_starts_demo_in_the_demo_and_in_its_language(self):
        self.assertEqual(self.client(demo=True).get("/api/now/menu").json()["title"], "Demo")
        self.assertEqual(self.client().get("/api/now/menu").json()["title"], "")
        self.assertEqual(demo_title("Review · 5 / 60 min", "en"), "Demo · Review · 5 / 60 min")
        self.assertEqual((demo_title("", "zh"), demo_title("复习 · 5 / 60 分钟", "zh")), ("演示", "演示 · 复习 · 5 / 60 分钟"))


class RestartTests(Workspaces):
    """The service starts again as the same program, once stopped, with the demo switch set or cleared."""

    def switch(self, opens_demo: bool, reset: Path | None = None, frozen: bool = False):
        """Ask for a switch, run what happens once the service has stopped, and return the program started again."""
        stopped = []
        with (patch.object(workspace, "_stop", lambda: stopped.append(True)),
              patch("backend.app.workspace.atexit.register") as register):
            workspace.switch(opens_demo, reset)
        self.assertEqual(stopped, [True])
        once_stopped, *arguments = register.call_args.args
        with patch("backend.app.workspace.os.execv") as execv, patch.object(sys, "frozen", frozen, create=True):
            once_stopped(*arguments)
        return execv.call_args.args

    def test_open_the_demo_starts_the_same_program_again_with_the_demo_switch_set(self):
        self.assertEqual(self.switch(True), (sys.executable, [sys.executable, *sys.argv]))
        self.assertEqual(os.environ[DEMO_VARIABLE], "1")

    def test_back_to_my_data_clears_the_switch_and_the_desktop_service_starts_its_own_program_again(self):
        os.environ[DEMO_VARIABLE] = "1"
        self.assertEqual(self.switch(False, frozen=True), (sys.executable, sys.argv))
        self.assertNotIn(DEMO_VARIABLE, os.environ)

    def test_reset_deletes_the_demos_folder_once_stopped_so_it_is_made_anew(self):
        folder = self.data / DEMO_FOLDER
        Database(folder / self.own.name)
        (folder / "Library").mkdir()
        self.switch(True, folder)
        self.assertFalse(folder.exists())
        self.assertTrue(self.data.is_dir())

    def test_the_desktop_service_starts_again_on_the_port_it_had_and_stops_its_own_server_to_switch(self):
        with tempfile.TemporaryDirectory() as folder:
            client = Path(folder)
            (client / "index.html").write_text("")
            environment = {TOKEN_VARIABLE: "secret", CLIENT_VARIABLE: str(client), PORT_VARIABLE: "8433"}
            with (patch.dict("os.environ", environment), patch("backend.app.desktop.prepare"),
                  patch("backend.app.desktop.listen") as listening, patch("backend.app.desktop.uvicorn.Server") as server,
                  patch("backend.app.desktop._announce_when_started"), patch("backend.app.desktop._exit_when_shell_closes"),
                  patch.object(workspace, "_stop", workspace._stop)):
                listening.return_value.getsockname.return_value = ("127.0.0.1", 8433)
                desktop.main()
                self.assertEqual(listening.call_args.args, (8433,))
                self.assertEqual(os.environ[PORT_VARIABLE], "8433")
                workspace._stop()
                self.assertIs(server.return_value.should_exit, True)


if __name__ == "__main__":
    unittest.main()
