"""A switch of workspace, like quitting, stops the service only once the work under way has finished, so nothing is
left half written: a folder's check and an index pass in the background, Ava condensing a day, and a reply she is
writing while the switch is asked for."""

import http.client
import io
import sqlite3
import tempfile
import threading
import time
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import httpx
import uvicorn
from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.database import Database
from backend.app.desktop import listen
from backend.app.main import create_app
from backend.app.retrieval import VectorStore
from backend.app.source_store import SourceStore
from backend.tests.test_api import FakeEmbeddingGateway, FakeGateway

# How long each stand-in job takes, long enough that a stop not waiting for it would come first.
JOB_SECONDS = 0.5


class SlowGateway(FakeGateway):
    """Ava's model, taking a while over each reply."""

    def reply(self, message, context, system_prompt=None, max_tokens=None):
        """Keep the message, take JOB_SECONDS, then answer as the fake gateway does."""
        self.calls.append(message)
        time.sleep(JOB_SECONDS)
        return super().reply(message, context, system_prompt, max_tokens)


class CleanStopTests(unittest.TestCase):
    def setUp(self):
        """A temporary folder, and no stand-in job finished yet."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.done = []

    def job(self, name: str):
        """A stand-in for a job that takes a while: it records itself finished only at its end."""
        def run(*args, **kwargs):
            """Take JOB_SECONDS, then record the job `name` finished."""
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


class CutModel(FakeEmbeddingGateway):
    """The embedding model as a stop leaves it: a request waits until the model is stopped, then fails as a connection
    cut short does."""

    def __init__(self):
        """Neither asked nor stopped yet."""
        super().__init__()
        self.asked = threading.Event()
        self.stopped = threading.Event()

    def embed_documents(self, texts):
        """Say it was asked, wait up to ten seconds for the stop, then fail as a connection cut short."""
        self.asked.set()
        self.stopped.wait(10)
        raise http.client.RemoteDisconnected("Remote end closed connection without response")

    def stop(self):
        """Stop the model, ending any request that waits."""
        self.stopped.set()


class QuietStopTests(unittest.TestCase):
    """Work a stop cuts short, after the wait for it, is noted as left for the next start rather than as a failure,
    and the next start carries it on."""

    def setUp(self):
        """A throwaway database's place, a stop that waits 0.2 seconds, and no folder check or memory keeping."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "daywright.sqlite3"
        for waiting in (patch("backend.app.main.STOP_WAIT_SECONDS", 0.2), patch("backend.app.main.check_folder"),
                        patch("backend.app.main.recall.keep")):
            waiting.start()
            self.addCleanup(waiting.stop)

    def count(self, table: str) -> int:
        """How many rows `table` holds."""
        with sqlite3.connect(self.path) as connection:
            return connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def run_cut(self, embedder: CutModel, work, day_jobs: bool = False) -> list[str]:
        """Start the service, do `work` with it, and stop it while the model is asked; what it logged of itself."""
        app = create_app(database_path=self.path, gateway=FakeGateway(), embedding_gateway=embedder, day_jobs=day_jobs)
        with patch("sys.stderr", new_callable=io.StringIO) as log:
            with TestClient(app) as client:
                work(client)
                self.assertTrue(embedder.asked.wait(5))
            for thread in [app.state.rounds, *app.state.indexing]:
                if thread is not None:
                    thread.join(10)
        return [line for line in log.getvalue().splitlines() if line.startswith("DayWright")]

    def test_a_folders_index_cut_by_a_stop_is_left_for_the_next_start_which_indexes_it(self):
        folder = Path(self.temp.name) / "Notes"
        folder.mkdir()
        (folder / "a.md").write_text("# A\n\nWhat the lesson says.")

        def connect(client: TestClient) -> None:
            """Connect the folder through the service, as the user does."""
            self.assertEqual(client.post("/api/sources/folder", json={"path": str(folder)}).status_code, 200)

        self.assertEqual(self.run_cut(CutModel(), connect),
                         ["DayWright stopped before it could index a folder for search; it's left for the next start."])
        self.assertEqual(self.count("knowledge_chunks"), 0)
        again = create_app(database_path=self.path, gateway=FakeGateway(), embedding_gateway=FakeEmbeddingGateway())
        with TestClient(again):
            pass
        for thread in again.state.indexing:
            thread.join(10)
        self.assertGreater(self.count("knowledge_chunks"), 0)

    def test_the_records_index_cut_by_a_stop_is_left_for_the_next_start_which_carries_it_on(self):
        with TestClient(create_app(database_path=self.path, gateway=FakeGateway(),
                                   embedding_gateway=FakeEmbeddingGateway())) as client:
            made = client.post("/api/daily-items", json={
                "date": date.today().isoformat(), "title": "Review", "detail": "", "domain": "learning", "startTime": "09:00",
                "durationMinutes": 60, "constraintKind": "fixed", "repeatKind": "none", "goalId": None}).json()
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE daily_items SET item_date = ?, completion_status = 'done' WHERE id = ?",
                               ((date.today() - timedelta(days=1)).isoformat(), made["id"]))
        self.assertEqual(self.run_cut(CutModel(), lambda client: None, day_jobs=True),
                         ["DayWright stopped before it could index the records for Ava; it's left for the next start."])
        self.assertEqual((self.count("record_documents"), len(VectorStore(self.path).vector_ids("record_vectors"))), (2, 0))
        with TestClient(create_app(database_path=self.path, gateway=FakeGateway(), embedding_gateway=FakeEmbeddingGateway(),
                                   day_jobs=True)):
            for _ in range(200):
                if VectorStore(self.path).vector_ids("record_vectors"):
                    break
                time.sleep(0.02)
        self.assertEqual(len(VectorStore(self.path).vector_ids("record_vectors")), 2)


if __name__ == "__main__":
    unittest.main()
