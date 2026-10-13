"""A switch of workspace, like quitting, stops the service only once the work under way has finished, so nothing is
left half written: a folder's check and an index pass in the background, Ava condensing a day, and a reply she is
writing while the switch is asked for."""

import tempfile
import threading
import time
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import httpx
import uvicorn
from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.database import Database
from backend.app.desktop import listen
from backend.app.main import create_app
from backend.app.source_store import SourceStore
from backend.tests.test_api import FakeGateway

# How long each stand-in job takes, long enough that a stop not waiting for it would come first.
JOB_SECONDS = 0.5


class SlowGateway(FakeGateway):
    """Ava's model, taking a while over each reply."""

    def reply(self, message, context, system_prompt=None, max_tokens=None):
        self.calls.append(message)
        time.sleep(JOB_SECONDS)
        return super().reply(message, context, system_prompt, max_tokens)


class CleanStopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.done = []

    def job(self, name: str):
        """A stand-in for a job that takes a while: it records itself finished only at its end."""
        def run(*args, **kwargs):
            time.sleep(JOB_SECONDS)
            self.done.append(name)
        return run

    def test_a_stop_waits_for_a_folders_check_and_its_index_pass_running_in_the_background(self):
        folder = self.root / "Notes"
        folder.mkdir()
        (folder / "a.md").write_text("# A\n\nWhat the lesson says.")
        with (patch("backend.app.main.check_folder", self.job("check")), patch.object(SourceStore, "index", self.job("index")),
              TestClient(create_app(database_path=self.root / "daywright.sqlite3")) as client):
            self.assertEqual(client.post("/api/sources/folder", json={"path": str(folder)}).status_code, 200)
        self.assertEqual(sorted(self.done), ["check", "index"])

    def test_a_stop_waits_for_ava_to_finish_condensing_a_day(self):
        with (patch("backend.app.main.recall.keep", self.job("condensed")),
              TestClient(create_app(database_path=self.root / "daywright.sqlite3", day_jobs=True))):
            pass
        self.assertEqual(self.done, ["condensed"])

    def test_a_stop_asked_for_while_ava_replies_waits_for_her_reply_and_keeps_both_messages(self):
        gateway = SlowGateway()
        server: list[uvicorn.Server] = []
        app = create_app(database_path=self.root / "daywright.sqlite3", gateway=gateway,
                         switch=lambda opens_demo, reset: setattr(server[0], "should_exit", True))
        server.append(uvicorn.Server(uvicorn.Config(app, log_level="error")))
        listener = listen(0)
        address = f"http://127.0.0.1:{listener.getsockname()[1]}"
        running = threading.Thread(target=server[0].run, kwargs={"sockets": [listener]})
        running.start()
        for _ in range(100):
            if server[0].started:
                break
            time.sleep(0.05)
        replies = []
        asking = threading.Thread(target=lambda: replies.append(httpx.post(
            f"{address}/api/chat", json={"date": date.today().isoformat(), "message": "How did last week go?"}, timeout=10)))
        asking.start()
        for _ in range(100):
            if gateway.calls:
                break
            time.sleep(0.02)
        self.assertEqual(httpx.post(f"{address}/api/workspace", json={"workspace": "demo"}, timeout=10).status_code, 202)
        running.join(10)
        asking.join(10)
        self.assertFalse(running.is_alive())
        self.assertEqual(replies[0].status_code, 200, replies[0].text)
        store = Database(self.root / "daywright.sqlite3")
        self.assertEqual([message["role"] for message in store.messages(store.thread())], ["user", "assistant"])


if __name__ == "__main__":
    unittest.main()
