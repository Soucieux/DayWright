import json
import subprocess
import tempfile
import unittest
from contextlib import contextmanager, nullcontext
from dataclasses import replace
from itertools import count
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.app_settings import SETTINGS_FILE, AppSettings
from backend.app.config import load_settings
from backend.app.llama_runtime import LlamaRuntime, device_arguments, graphics_device, list_devices, metal_device
from backend.app.main import create_app
from backend.app.model_gateway import ModelGateway
from backend.app.retrieval import EMBEDDING_DIMENSION, EmbeddingGateway
from backend.tests.test_api import Located

# What llama-server's --list-devices prints on an Apple silicon Mac.
LISTING = ("Available devices:\n  BLAS: Accelerate (0 MiB, 0 MiB free)\n"
           "  MTL0: Apple M1 Pro (12124 MiB, 12123 MiB free)\n")
_pids = count(41000)


class DeviceListTests(unittest.TestCase):
    """The Mac's graphics device is read once a launch from the runner's own list."""

    def test_the_metal_device_is_read_from_the_runners_list(self):
        self.assertEqual(metal_device(LISTING), "MTL0")
        self.assertEqual(metal_device("Available devices:\n  MTL1: Apple M4 (24000 MiB, 23000 MiB free)\n"), "MTL1")

    def test_a_list_without_metal_or_that_isnt_a_list_has_none(self):
        for listing in ("Available devices:\n  BLAS: Accelerate (0 MiB, 0 MiB free)\n", "", "error: unknown argument\n",
                        "MTL0", "  MTLX: Apple (12 MiB)\n", "\x00\x01garbage: MTL0", "  CPU: MTL0: Apple\n"):
            self.assertIsNone(metal_device(listing), repr(listing))

    def runner(self) -> Path:
        """A runner this Mac would run, in a folder of its own, so each test asks its own once a launch."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        runner = Path(folder.name) / "llama-server"
        runner.write_bytes(b"test")
        runner.chmod(0o755)
        return runner

    def test_a_runner_this_mac_cant_run_lists_nothing_and_isnt_run(self):
        with patch("backend.app.llama_runtime.subprocess.run") as run:
            self.assertEqual(list_devices(Path("/nowhere/llama-server")), "")
        run.assert_not_called()

    def test_the_list_is_asked_of_the_runner_and_any_trouble_reads_as_no_list(self):
        runner = self.runner()
        with patch("backend.app.llama_runtime.subprocess.run",
                   return_value=subprocess.CompletedProcess([], 0, "", LISTING)) as run:
            self.assertIn("MTL0: Apple M1 Pro", list_devices(runner))
        self.assertEqual(run.call_args.args[0], [str(runner), "--list-devices"])
        for trouble in (OSError("Exec format error"), subprocess.TimeoutExpired(str(runner), 10)):
            with patch("backend.app.llama_runtime.subprocess.run", side_effect=trouble):
                self.assertEqual(list_devices(runner), "", type(trouble).__name__)

    def test_the_runner_is_asked_once_a_launch(self):
        runner = self.runner()
        with patch("backend.app.llama_runtime.subprocess.run",
                   return_value=subprocess.CompletedProcess([], 0, LISTING, "")) as run:
            self.assertEqual([graphics_device(runner) for _ in range(3)], ["MTL0"] * 3)
        self.assertEqual(run.call_count, 1)


class ArgumentTests(unittest.TestCase):
    """On the graphics every layer goes to its device; on the processor the runner uses none, exactly as before."""

    def test_on_the_graphics_every_layer_goes_to_its_device(self):
        self.assertEqual(device_arguments("MTL0"), ["--device", "MTL0", "--n-gpu-layers", "999"])

    def test_on_the_processor_the_runner_uses_no_device(self):
        self.assertEqual(device_arguments(None), ["--device", "none"])


class RuntimeCase(unittest.TestCase):
    """A model server faked: every start's command and process, and a graphics server that `graphics_fails` makes
    exit at once ("exits") or never answer its health check ("unhealthy")."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.binary = root / "llama-server"
        self.model = root / "chat.gguf"
        for path in (self.binary, self.model):
            path.write_bytes(b"test")
        self.records = root / "runtime"
        self.commands = []
        self.processes = []
        self.graphics_fails = None

    def popen(self, command, **_options):
        process = MagicMock(pid=next(_pids))
        process.poll.return_value = 1 if self.graphics_fails == "exits" and "MTL0" in command else None
        self.commands.append(command)
        self.processes.append(process)
        return process

    def health(self, *_args, **_kwargs):
        if self.graphics_fails == "unhealthy" and "MTL0" in self.commands[-1]:
            raise URLError("not ready")
        return nullcontext(object())

    @contextmanager
    def faked(self):
        with (patch("backend.app.llama_runtime.subprocess.Popen", side_effect=self.popen),
              patch("backend.app.llama_runtime.urlopen", side_effect=self.health)):
            yield

    def runtime(self, run_on="automatic", device="MTL0"):
        runtime = LlamaRuntime(self.binary, self.model, ["--ctx-size", "4096"], self.records,
                               run_on=lambda: run_on, find_device=lambda _binary: device)
        self.addCleanup(runtime.stop)
        return runtime

    def started(self, runtime, timeout=1.0):
        with self.faked():
            return runtime.start(timeout)


class PlacementTests(RuntimeCase):
    """Where a model runs: Automatic on the graphics when the runner lists one, Processor only never."""

    def test_before_first_use_a_model_is_on_standby(self):
        self.assertEqual(self.runtime().device(), {"state": "standby", "reason": None})
        self.assertEqual(self.runtime(run_on="processor").device(), {"state": "standby", "reason": None})

    def test_automatic_with_a_metal_device_runs_on_the_graphics(self):
        runtime = self.runtime()
        self.assertTrue(self.started(runtime))
        command = self.commands[-1]
        self.assertEqual(command[command.index("--device"):command.index("--device") + 4], device_arguments("MTL0"))
        self.assertEqual(command[:3], [str(self.binary), "--model", str(self.model)], "stop_orphans still knows it")
        self.assertEqual(runtime.device(), {"state": "graphics", "reason": None})

    def test_processor_only_never_passes_a_metal_device(self):
        def never(_binary):
            raise AssertionError("Processor only doesn't look for the graphics")
        runtime = LlamaRuntime(self.binary, self.model, [], run_on=lambda: "processor", find_device=never)
        self.addCleanup(runtime.stop)
        self.assertTrue(self.started(runtime))
        command = self.commands[-1]
        self.assertNotIn("MTL0", command)
        self.assertNotIn("--n-gpu-layers", command)
        self.assertEqual(command[command.index("--device") + 1], "none")
        self.assertEqual(runtime.device(), {"state": "processor", "reason": None})

    def test_with_no_device_listed_it_runs_on_the_processor_saying_so(self):
        runtime = self.runtime(device=None)
        self.assertTrue(self.started(runtime))
        self.assertEqual(self.commands[-1][self.commands[-1].index("--device") + 1], "none")
        self.assertEqual(runtime.device(), {"state": "processor", "reason": "noDevice"})


class FallbackTests(RuntimeCase):
    """On any trouble with the graphics a model moves to the processor for the rest of the launch, and the request
    that met the trouble is sent once more there."""

    def assert_started_again_on_the_processor(self, runtime, reason):
        self.assertEqual(len(self.commands), 2)
        self.assertIn("MTL0", self.commands[0])
        self.assertEqual(self.commands[1][self.commands[1].index("--device") + 1], "none")
        self.assertEqual(runtime.device(), {"state": "processor", "reason": reason})
        self.assertEqual([record.name for record in self.records.iterdir()], [str(self.processes[1].pid)],
                         "the failed server's record is gone")

    def test_a_graphics_server_that_exits_at_start_gives_way_to_the_processor(self):
        self.graphics_fails = "exits"
        runtime = self.runtime()
        self.assertTrue(self.started(runtime))
        self.assert_started_again_on_the_processor(runtime, "didntStart")

    def test_a_graphics_server_not_healthy_in_time_is_stopped_and_the_processor_takes_over(self):
        self.graphics_fails = "unhealthy"
        runtime = self.runtime()
        self.assertTrue(self.started(runtime, timeout=0.3))
        self.processes[0].terminate.assert_called_once()
        self.assert_started_again_on_the_processor(runtime, "didntStart")

    def test_a_failed_start_holds_for_the_rest_of_the_launch(self):
        self.graphics_fails = "exits"
        runtime = self.runtime()
        self.started(runtime)
        runtime.stop()
        self.graphics_fails = None
        self.assertTrue(self.started(runtime))
        self.assertNotIn("MTL0", self.commands[-1])
        self.assertEqual(runtime.device(), {"state": "processor", "reason": "didntStart"})

    def test_a_request_the_graphics_fails_is_sent_once_more_on_the_processor(self):
        for failure in (URLError("connection refused"), TimeoutError("timed out"), ConnectionResetError("reset")):
            with self.subTest(failure=type(failure).__name__):
                self.commands.clear()
                self.processes.clear()
                runtime = self.runtime()
                sent = []

                def send(port, token):
                    sent.append(self.commands[-1])
                    if len(sent) == 1:
                        raise failure
                    return "answer"

                with self.faked():
                    self.assertTrue(runtime.start(1.0))
                    self.assertEqual(runtime.retrying(send), "answer")
                self.assertEqual(len(sent), 2)
                self.assertIn("MTL0", sent[0])
                self.assertNotIn("MTL0", sent[1])
                self.assertEqual(runtime.device(), {"state": "processor", "reason": "stopped"})
                self.processes[0].terminate.assert_called_once()

    def test_a_server_that_answers_with_an_error_hasnt_lost_the_graphics(self):
        runtime = self.runtime()
        calls = []

        def send(port, token):
            calls.append(port)
            raise HTTPError("http://127.0.0.1", 500, "Server error", {}, None)

        with self.faked():
            runtime.start(1.0)
            with self.assertRaises(HTTPError):
                runtime.retrying(send)
        self.assertEqual((len(calls), runtime.device()["state"]), (1, "graphics"))

    def test_on_the_processor_a_failed_request_is_not_sent_again(self):
        for run_on, device in (("processor", "MTL0"), ("automatic", None)):
            with self.subTest(run_on=run_on, device=device):
                runtime = self.runtime(run_on=run_on, device=device)
                calls = []

                def send(port, token):
                    calls.append(port)
                    raise TimeoutError("timed out")

                with self.faked():
                    runtime.start(1.0)
                    with self.assertRaises(TimeoutError):
                        runtime.retrying(send)
                self.assertEqual(len(calls), 1)

    def test_chat_and_search_fall_back_each_on_its_own(self):
        chat, search = self.runtime(), self.runtime()

        def failing(port, token):
            raise URLError("connection refused")

        with self.faked():
            chat.start(1.0)
            search.start(1.0)
            with self.assertRaises(URLError):
                chat.retrying(failing)
        self.assertEqual(chat.device(), {"state": "processor", "reason": "stopped"})
        self.assertEqual(search.device(), {"state": "graphics", "reason": None})

    def test_the_next_launch_tries_the_graphics_again(self):
        self.graphics_fails = "exits"
        self.started(self.runtime())
        self.graphics_fails = None
        later = self.runtime()  # A new launch builds its runtimes anew, and nothing of the last one is kept.
        self.assertTrue(self.started(later))
        self.assertIn("MTL0", self.commands[-1])
        self.assertEqual(later.device(), {"state": "graphics", "reason": None})


class GatewayTests(RuntimeCase):
    """Ava's replies and the Library's search keep the request that met trouble on the graphics."""

    def gateway(self, kind):
        settings = replace(load_settings(), llama_binary=self.binary)
        library = Located(chat=self.model, embedding=self.model)
        gateway = kind(settings, library, run_on=lambda: "automatic")
        self.addCleanup(gateway.stop)
        return gateway

    def test_avas_reply_that_met_trouble_on_the_graphics_comes_from_the_processor(self):
        gateway = self.gateway(ModelGateway)
        answer = {"choices": [{"message": {"content": "Moved to 45 min."}}]}
        replies = [URLError("connection refused"), nullcontext(MagicMock(read=lambda: json.dumps(answer).encode()))]
        with (self.faked(), patch("backend.app.llama_runtime.graphics_device", return_value="MTL0"),
              patch("backend.app.model_gateway.urlopen", side_effect=replies)):
            self.assertEqual(gateway.reply("Change Answer email to 45 min", "context"), ("Moved to 45 min.", "local-model"))
        self.assertEqual(gateway.status()["device"], {"state": "processor", "reason": "stopped"})

    def test_a_search_that_met_trouble_on_the_graphics_is_answered_on_the_processor(self):
        gateway = self.gateway(EmbeddingGateway)
        vectors = {"data": [{"index": 0, "embedding": [0.0] * EMBEDDING_DIMENSION}]}
        replies = [TimeoutError("timed out"), nullcontext(MagicMock(read=lambda: json.dumps(vectors).encode()))]
        with (self.faked(), patch("backend.app.llama_runtime.graphics_device", return_value="MTL0"),
              patch("backend.app.retrieval.urlopen", side_effect=replies)):
            self.assertEqual(len(gateway.embed_query("past tense")), EMBEDDING_DIMENSION)
        self.assertEqual(gateway.status()["device"], {"state": "processor", "reason": "stopped"})

    def test_each_gateway_says_where_its_model_runs(self):
        for kind in (ModelGateway, EmbeddingGateway):
            gateway = self.gateway(kind)
            self.assertEqual(gateway.status()["device"], {"state": "standby", "reason": None})
            with self.faked(), patch("backend.app.llama_runtime.graphics_device", return_value="MTL0"):
                gateway.start(timeout=1.0)
            self.assertEqual(gateway.status()["device"], {"state": "graphics", "reason": None})


class RunModelsOnTests(unittest.TestCase):
    """Settings › Models: Run models on Automatic or Processor only, kept once for both workspaces."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / SETTINGS_FILE

    def test_automatic_until_chosen_then_kept_in_the_shared_settings_file(self):
        settings = AppSettings(self.path)
        self.assertEqual(settings.run_models_on(), "automatic")
        settings.set_run_models_on("processor")
        self.assertEqual(json.loads(self.path.read_text())["runModelsOn"], "processor")
        self.assertEqual(AppSettings(self.path).run_models_on(), "processor", "the other workspace reads the same file")

    def test_only_its_two_choices_are_kept_and_any_other_reads_as_automatic(self):
        settings = AppSettings(self.path)
        with self.assertRaises(ValueError):
            settings.set_run_models_on("graphics")
        self.path.write_text(json.dumps({"runModelsOn": "fast"}))
        self.assertEqual(settings.run_models_on(), "automatic")


class RunModelsOnRouteTests(unittest.TestCase):
    """The models' states say where each runs, and choosing where stops the model servers for the next use."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "daywright.sqlite3"
        self.client = TestClient(create_app(database_path=self.database))

    def test_the_states_say_the_choice_and_where_each_model_runs(self):
        states = self.client.get("/api/models").json()
        self.assertEqual(states["runOn"], "automatic")
        self.assertEqual(states["devices"], {"chat": {"state": "standby", "reason": None},
                                             "embedding": {"state": "standby", "reason": None},
                                             "speech": {"state": "processor", "reason": None}})

    def test_choosing_processor_only_keeps_it_and_stops_both_model_servers(self):
        with (patch.object(ModelGateway, "stop") as chat_stopped, patch.object(EmbeddingGateway, "stop") as search_stopped):
            answer = self.client.put("/api/models/run-on", json={"runOn": "processor"})
        self.assertEqual(answer.status_code, 200, answer.text)
        self.assertEqual((answer.json()["runOn"], answer.json()["state"]), ("processor", "none"))
        chat_stopped.assert_called_once()
        search_stopped.assert_called_once()
        self.assertEqual(json.loads((self.database.parent / SETTINGS_FILE).read_text())["runModelsOn"], "processor")
        self.assertEqual(self.client.get("/api/models").json()["runOn"], "processor")

    def test_any_other_choice_is_refused(self):
        self.assertEqual(self.client.put("/api/models/run-on", json={"runOn": "graphics"}).status_code, 422)
        self.assertEqual(self.client.get("/api/models").json()["runOn"], "automatic")

    def test_a_folder_change_answers_with_the_same_states(self):
        folder = Path(self.temp.name) / "AI-Models"
        folder.mkdir()
        for answer in (self.client.post("/api/models/folder", json={"path": str(folder)}).json(),
                       self.client.delete("/api/models/folder").json()):
            self.assertEqual((answer["runOn"], sorted(answer["devices"])), ("automatic", ["chat", "embedding", "speech"]))


if __name__ == "__main__":
    unittest.main()
