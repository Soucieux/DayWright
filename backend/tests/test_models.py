import hashlib
import os
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.config import load_settings
from backend.app.database import Database
from backend.app.main import create_app
from backend.app.model_gateway import ModelGateway
from backend.app.models import MODELS, ModelFile, ModelLibrary, ModelSpec
from backend.app.retrieval import EmbeddingGateway
from backend.app.speech import SpeechGateway
from backend.tests.test_api import Located

CHAT = b"chat model bytes"
EMBEDDING = b"embedding model bytes"
SPEECH = {"config.json": b"{}", "model.bin": b"speech weights"}


def pin(name, content):
    return ModelFile(name, len(content), hashlib.sha256(content).hexdigest())


# Three small models laid out as the shared library is, each pinned to the bytes written for it.
SPECS = (
    ModelSpec("chat", "gguf/chat.gguf", (pin("", CHAT),)),
    ModelSpec("embedding", "gguf/embedding.gguf", (pin("", EMBEDDING),)),
    ModelSpec("speech", "whisper/speech", tuple(pin(name, content) for name, content in SPEECH.items())),
)


class ModelFolder(unittest.TestCase):
    """A fresh account and a models folder holding the three small models, none chosen yet."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Database(root / "daywright.sqlite3")
        self.folder = root / "AI-Models"
        (self.folder / "gguf").mkdir(parents=True)
        (self.folder / "whisper" / "speech").mkdir(parents=True)
        (self.folder / "gguf" / "chat.gguf").write_bytes(CHAT)
        (self.folder / "gguf" / "embedding.gguf").write_bytes(EMBEDDING)
        for name, content in SPEECH.items():
            (self.folder / "whisper" / "speech" / name).write_bytes(content)
        self.library = ModelLibrary(self.store, specs=SPECS, background=False)

    def tearDown(self):
        self.temp.cleanup()

    def states(self):
        return {model["role"]: model["state"] for model in self.library.states()["models"]}

    def snapshot(self):
        """Every file in the models folder, with its size and when it last changed."""
        return {str(path.relative_to(self.folder)): (path.stat().st_size, path.stat().st_mtime_ns)
                for path in sorted(self.folder.rglob("*"))}


class ModelLibraryTests(ModelFolder):
    def test_with_no_folder_chosen_no_model_is_read_and_none_is_ready(self):
        found = self.library.states()
        self.assertEqual((found["folder"], found["state"]), (None, "none"))
        self.assertEqual(self.states(), {"chat": "noFolder", "embedding": "noFolder", "speech": "noFolder"})
        self.assertEqual([model["location"] for model in found["models"]], [None, None, None])
        self.assertEqual([model["name"] for model in found["models"]], ["chat.gguf", "embedding.gguf", "speech"])
        self.assertIsNone(self.library.path("chat"))

    def test_a_chosen_folder_is_kept_and_its_matching_models_are_ready_where_they_are(self):
        self.library.choose(str(self.folder))
        self.assertEqual(self.store.models_folder(), str(self.folder))
        found = ModelLibrary(self.store, specs=SPECS, background=False).states()
        self.assertEqual((found["folder"], found["state"]), (str(self.folder), "found"))
        self.assertEqual(self.states(), {"chat": "ready", "embedding": "ready", "speech": "ready"})
        self.assertEqual([model["location"] for model in found["models"]],
                         [str(self.folder / "gguf" / "chat.gguf"), str(self.folder / "gguf" / "embedding.gguf"),
                          str(self.folder / "whisper" / "speech")])
        self.assertEqual(self.library.path("chat"), self.folder / "gguf" / "chat.gguf")
        self.assertEqual(self.library.path("speech"), self.folder / "whisper" / "speech")

    def test_only_an_existing_folder_can_be_chosen(self):
        for wrong in (str(self.folder / "nowhere"), str(self.folder / "gguf" / "chat.gguf"), "", "relative/folder"):
            with self.assertRaises(ValueError, msg=wrong):
                self.library.choose(wrong)
        self.assertIsNone(self.store.models_folder())

    def test_a_folder_no_longer_found_says_so_and_names_where_it_looked(self):
        self.library.choose(str(self.folder))
        self.folder.rename(self.folder.with_name("Moved"))
        found = self.library.states()
        self.assertEqual((found["folder"], found["state"]), (str(self.folder), "notFound"))
        self.assertEqual(self.states(), {"chat": "folderNotFound", "embedding": "folderNotFound", "speech": "folderNotFound"})
        self.assertIsNone(self.library.path("chat"))

    def test_a_model_missing_from_the_folder_or_not_matching_its_pin_is_not_ready(self):
        self.library.choose(str(self.folder))
        (self.folder / "gguf" / "chat.gguf").unlink()
        (self.folder / "gguf" / "embedding.gguf").write_bytes(b"x" * len(EMBEDDING))  # The pinned size, other bytes.
        (self.folder / "whisper" / "speech" / "model.bin").unlink()
        self.assertEqual(self.states(), {"chat": "missing", "embedding": "mismatch", "speech": "missing"})
        self.assertEqual([self.library.path(role) for role in ("chat", "embedding", "speech")], [None, None, None])
        (self.folder / "gguf" / "chat.gguf").write_bytes(CHAT + b"!")  # Another size: no checksum needed to tell.
        self.assertEqual(self.states()["chat"], "mismatch")

    def test_any_other_file_in_a_models_place_fails_its_check_and_names_where_it_looked(self):
        self.library.choose(str(self.folder))
        # Another model of the same kind, a valid GGUF the very size of the pinned one; a truncated copy; and one of
        # the speech model's files with other bytes.
        (self.folder / "gguf" / "chat.gguf").write_bytes(b"GGUF" + b"\x03" * (len(CHAT) - 4))
        (self.folder / "gguf" / "embedding.gguf").write_bytes(EMBEDDING[:-3])
        (self.folder / "whisper" / "speech" / "config.json").write_bytes(b"[]")
        found = self.library.states()["models"]
        self.assertEqual([(model["name"], model["state"], model["location"]) for model in found],
                         [("chat.gguf", "mismatch", str(self.folder / "gguf" / "chat.gguf")),
                          ("embedding.gguf", "mismatch", str(self.folder / "gguf" / "embedding.gguf")),
                          ("speech", "mismatch", str(self.folder / "whisper" / "speech"))])
        self.assertEqual([self.library.path(role) for role in ("chat", "embedding", "speech")], [None, None, None])

    def test_a_file_changed_after_its_check_is_checked_again_before_it_is_used(self):
        self.library.choose(str(self.folder))
        self.assertIsNotNone(self.library.path("chat"))
        chat = self.folder / "gguf" / "chat.gguf"
        kept = chat.stat()
        chat.write_bytes(b"x" * len(CHAT))
        os.utime(chat, ns=(kept.st_atime_ns, kept.st_mtime_ns + 1_000_000_000))
        self.assertIsNone(self.library.path("chat"))
        self.assertEqual(self.states()["chat"], "mismatch")

    def test_a_checksum_is_kept_and_taken_again_only_when_the_file_changes(self):
        self.library.choose(str(self.folder))
        hashed = []
        self.library.hash_file = lambda path: hashed.append(path.name) or ModelLibrary.hash_file(path)
        self.library.states()
        self.assertEqual(hashed, [])  # Checked when chosen: kept in DayWright's own preferences.
        self.assertIn(str(self.folder / "gguf" / "chat.gguf"), self.store.model_checks())
        chat = self.folder / "gguf" / "chat.gguf"
        os.utime(chat, ns=(chat.stat().st_atime_ns, chat.stat().st_mtime_ns + 1_000_000_000))
        self.assertEqual(self.states()["chat"], "ready")
        self.assertEqual(hashed, ["chat.gguf"])

    def test_while_a_checksum_is_taken_the_model_reads_checking_and_is_not_ready(self):
        library = ModelLibrary(self.store, specs=SPECS, background=True)
        done = threading.Event()
        library.hash_file = lambda path: done.wait(5) and ModelLibrary.hash_file(path)  # As a long check, until done.
        library.choose(str(self.folder))
        states = lambda: {model["role"]: model["state"] for model in library.states()["models"]}
        self.assertEqual(states(), {"chat": "checking", "embedding": "checking", "speech": "checking"})
        self.assertIsNone(library.path("chat"))
        done.set()
        for _ in range(50):
            if states() == {"chat": "ready", "embedding": "ready", "speech": "ready"}:
                break
            time.sleep(0.05)
        self.assertEqual(states(), {"chat": "ready", "embedding": "ready", "speech": "ready"})

    def test_stop_using_the_folder_forgets_it_and_nothing_in_it_is_ever_written(self):
        before = self.snapshot()
        self.library.choose(str(self.folder))
        self.library.states()
        self.library.forget()
        self.assertIsNone(self.store.models_folder())
        self.assertEqual(self.states(), {"chat": "noFolder", "embedding": "noFolder", "speech": "noFolder"})
        self.assertEqual(self.snapshot(), before)

    def test_a_development_folder_stands_in_for_a_choice_without_being_kept(self):
        library = ModelLibrary(self.store, specs=SPECS, background=False, development_folder=self.folder)
        self.assertEqual(library.states()["folder"], str(self.folder))
        self.assertEqual(library.path("chat"), self.folder / "gguf" / "chat.gguf")
        self.assertIsNone(self.store.models_folder())

    def test_the_runner_is_found_or_not_where_daywright_looks_for_it_whatever_the_folder(self):
        runner = Path(self.temp.name) / "llama-server"
        library = ModelLibrary(self.store, specs=SPECS, background=False, runner=runner)
        self.assertEqual(library.states()["runner"], {"location": str(runner), "state": "notFound"})
        runner.write_bytes(b"program")
        library.choose(str(self.folder))
        self.assertEqual(library.states()["runner"], {"location": str(runner), "state": "found"})

    def test_the_models_are_the_three_daywright_runs_each_pinned_to_its_publishers_files(self):
        self.assertEqual([(spec.role, spec.location) for spec in MODELS],
                         [("chat", "gguf/Qwen3-4B-Q4_K_M.gguf"), ("embedding", "gguf/Qwen3-Embedding-0.6B-Q8_0.gguf"),
                          ("speech", "whisper/faster-whisper-small")])
        self.assertEqual([file.name for file in MODELS[2].files], ["config.json", "model.bin", "tokenizer.json", "vocabulary.txt"])
        self.assertTrue(all(len(file.sha256) == 64 and file.size > 0 for spec in MODELS for file in spec.files))


class GatewayTests(ModelFolder):
    """The model gateways run only a model the library has ready, and read it where it is."""

    def runtime(self, gateway):
        """Start `gateway` with its server faked, returning the command it ran, or None when it ran none."""
        with (patch("backend.app.llama_runtime.subprocess.Popen") as popen,
              patch("backend.app.llama_runtime.urlopen") as health):
            popen.return_value.poll.return_value = None
            health.return_value.__enter__.return_value = object()
            status = gateway.start(timeout=0.1)
        self.addCleanup(gateway.stop)
        return status, popen.call_args.args[0] if popen.called else None

    def settings(self):
        binary = Path(self.temp.name) / "llama-server"
        binary.write_bytes(b"test")
        return replace(load_settings(), llama_binary=binary)

    def test_without_a_folder_chosen_no_gateway_runs_a_model(self):
        for gateway in (ModelGateway(self.settings(), self.library), EmbeddingGateway(self.settings(), self.library)):
            status, command = self.runtime(gateway)
            self.assertEqual((status["state"], status["running"], command), ("unavailable", False, None))
        chat = ModelGateway(self.settings(), self.library).status()
        self.assertEqual((chat["chatModelAvailable"], chat["embeddingModelAvailable"], chat["voiceModelAvailable"]),
                         (False, False, False))
        self.assertEqual(SpeechGateway(self.library).status()["modelAvailable"], False)

    def test_a_ready_model_is_run_from_the_chosen_folder_and_stopped_when_the_folder_is(self):
        self.library.choose(str(self.folder))
        gateway = ModelGateway(self.settings(), self.library)
        status, command = self.runtime(gateway)
        self.assertTrue(status["running"])
        self.assertEqual(command[command.index("--model") + 1], str(self.folder / "gguf" / "chat.gguf"))
        embedder = EmbeddingGateway(self.settings(), self.library)
        _, command = self.runtime(embedder)
        self.assertEqual(command[command.index("--model") + 1], str(self.folder / "gguf" / "embedding.gguf"))
        self.assertEqual(SpeechGateway(self.library).status()["modelAvailable"], True)
        self.library.forget()
        gateway.stop()
        self.assertEqual(gateway.status()["state"], "unavailable")
        self.assertEqual(self.runtime(gateway)[1], None)

    def test_a_model_that_changes_place_is_run_from_its_new_place(self):
        self.library.choose(str(self.folder))
        gateway = ModelGateway(self.settings(), self.library)
        self.runtime(gateway)
        copy = self.folder.with_name("Copy")
        shutil.copytree(self.folder, copy)
        self.library.choose(str(copy))
        status, command = self.runtime(gateway)
        self.assertTrue(status["running"])
        self.assertEqual(command[command.index("--model") + 1], str(copy / "gguf" / "chat.gguf"))


class ModelRouteTests(unittest.TestCase):
    """Settings reads the states, chooses a folder, by its path or the Mac's own window, and stops using it."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / "AI-Models"
        (self.folder / "gguf").mkdir(parents=True)
        self.client = TestClient(create_app(database_path=Path(self.temp.name) / "daywright.sqlite3"))

    def test_no_folder_is_chosen_until_one_is_and_stopping_forgets_it(self):
        found = self.client.get("/api/models").json()
        self.assertEqual((found["folder"], found["state"]), (None, "none"))
        self.assertEqual(self.client.get("/api/health").json()["models"]["state"], "none")
        chosen = self.client.post("/api/models/folder", json={"path": str(self.folder)})
        self.assertEqual(chosen.status_code, 200, chosen.text)
        self.assertEqual((chosen.json()["folder"], chosen.json()["state"]), (str(self.folder), "found"))
        self.assertEqual([model["state"] for model in chosen.json()["models"]], ["missing", "missing", "missing"])
        self.assertEqual(self.client.get("/api/models").json()["folder"], str(self.folder))
        stopped = self.client.delete("/api/models/folder")
        self.assertEqual(stopped.json()["state"], "none")
        self.assertTrue(self.folder.is_dir())

    def test_a_folder_that_doesnt_exist_is_refused(self):
        for wrong in (str(self.folder / "nowhere"), "relative"):
            self.assertEqual(self.client.post("/api/models/folder", json={"path": wrong}).status_code, 422, wrong)
        self.assertEqual(self.client.get("/api/models").json()["state"], "none")

    def test_without_her_model_ava_doesnt_answer_and_nothing_is_kept(self):
        today = date.today().isoformat()
        for message in ("How did last week go?", "Catch up", "Add Read chapter 4 tomorrow at 9"):
            answer = self.client.post("/api/chat", json={"date": today, "message": message})
            self.assertEqual(answer.status_code, 409, message)
            self.assertEqual(answer.json()["detail"], "Ava needs a local model. Choose your models folder in Settings.")
        self.assertEqual(self.client.get("/api/bootstrap", params={"date": today}).json()["messages"], [])

    def test_with_her_model_ready_but_no_runner_ava_doesnt_answer_either(self):
        chat = Path(self.temp.name) / "chat.gguf"
        chat.write_bytes(b"model")
        nowhere = Path(self.temp.name) / "no-runner" / "llama-server"
        client = TestClient(create_app(database_path=Path(self.temp.name) / "own.sqlite3",
                                       gateway=ModelGateway(replace(load_settings(), llama_binary=nowhere), Located(chat=chat))))
        answer = client.post("/api/chat", json={"date": date.today().isoformat(), "message": "Catch up"})
        self.assertEqual(answer.status_code, 409)

    def test_the_macs_own_window_chooses_the_folder(self):
        with patch("backend.app.main.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, stdout=f"{self.folder}/\n")
            picked = self.client.post("/api/models/folder/choose").json()
        self.assertEqual(picked, {"path": f"{self.folder}/"})
        self.assertIn("models folder", " ".join(run.call_args.args[0]))
        with patch("backend.app.main.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 1, stdout="")
            self.assertEqual(self.client.post("/api/models/folder/choose").json(), {"path": None})


if __name__ == "__main__":
    unittest.main()
