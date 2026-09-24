import signal
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from backend.app.config import load_settings
from backend.app.llama_runtime import stop_orphans
from backend.app.model_gateway import ModelGateway

BINARY = Path("/opt/homebrew/bin/llama-server")


class ModelServerRecordTests(unittest.TestCase):
    def test_records_a_started_server_until_it_stops(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            binary = root / "llama-server"
            model = root / "chat.gguf"
            binary.write_bytes(b"test")
            model.write_bytes(b"test")
            runtime = root / "runtime"
            gateway = ModelGateway(replace(
                load_settings(), llama_binary=binary, model_path=model, runtime_directory=runtime
            ))
            with (
                patch("backend.app.llama_runtime.subprocess.Popen") as popen,
                patch("backend.app.llama_runtime.urlopen") as health,
            ):
                popen.return_value.poll.return_value = None
                popen.return_value.pid = 4242
                health.return_value.__enter__.return_value = object()
                self.assertTrue(gateway.start(timeout=0.1)["running"])
                self.assertTrue((runtime / "4242").is_file())
                gateway.stop()
            self.assertFalse((runtime / "4242").exists())

    def sweep(self, listing: str):
        """Sweep one record for process 4242 while `ps` reports `listing` for it."""
        with tempfile.TemporaryDirectory() as folder:
            runtime = Path(folder)
            (runtime / "4242").touch()
            with (
                patch("backend.app.llama_runtime.subprocess.run") as process_listing,
                patch("backend.app.llama_runtime.os.kill") as kill,
            ):
                process_listing.return_value.stdout = listing
                stop_orphans(runtime, BINARY)
            return kill, list(runtime.iterdir())

    def test_stops_a_recorded_server_whose_service_is_gone(self):
        kill, records = self.sweep(f"    1 {BINARY} --model /models/chat.gguf --port 50000\n")
        kill.assert_called_once_with(4242, signal.SIGTERM)
        self.assertEqual(records, [])

    def test_leaves_a_server_whose_service_is_still_running(self):
        kill, records = self.sweep(f"  812 {BINARY} --model /models/chat.gguf --port 50000\n")
        kill.assert_not_called()
        self.assertEqual(records, [])

    def test_leaves_a_reused_process_id_alone(self):
        kill, records = self.sweep("    1 /usr/libexec/another-program --model elsewhere\n")
        kill.assert_not_called()
        self.assertEqual(records, [])

    def test_forgets_a_record_whose_process_has_exited(self):
        kill, records = self.sweep("")
        kill.assert_not_called()
        self.assertEqual(records, [])


if __name__ == "__main__":
    unittest.main()
