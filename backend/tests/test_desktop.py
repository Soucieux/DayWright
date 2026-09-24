import signal
import socket
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.config import load_settings
from backend.app.desktop import SESSION_COOKIE, SESSION_PATH, listen, prepare
from backend.app.llama_runtime import stop_orphans
from backend.app.model_gateway import ModelGateway

SECRET = "f" * 64
BINARY = Path("/opt/homebrew/bin/llama-server")


def desktop_client(folder: Path) -> TestClient:
    """A service with one API route and a built interface, prepared the way the desktop app runs it."""
    (folder / "index.html").write_text("<!doctype html><title>DayWright interface</title>")
    app = FastAPI()

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    prepare(app, SECRET, folder)
    return TestClient(app, base_url="http://127.0.0.1:8425")


class SessionGateTests(unittest.TestCase):
    def test_refuses_the_interface_and_api_without_the_session(self):
        with tempfile.TemporaryDirectory() as folder:
            client = desktop_client(Path(folder))
            self.assertEqual(client.get("/api/health").status_code, 403)
            self.assertEqual(client.get("/").status_code, 403)
            client.cookies.set(SESSION_COOKIE, "not-the-secret")
            self.assertEqual(client.get("/api/health").status_code, 403)

    def test_refuses_a_wrong_launch_secret_without_a_cookie(self):
        with tempfile.TemporaryDirectory() as folder:
            response = desktop_client(Path(folder)).get(
                f"{SESSION_PATH}?token=not-the-secret", follow_redirects=False
            )
            self.assertEqual(response.status_code, 403)
            self.assertNotIn("set-cookie", response.headers)

    def test_launch_secret_opens_a_private_session_for_the_interface_and_api(self):
        with tempfile.TemporaryDirectory() as folder:
            client = desktop_client(Path(folder))
            response = client.get(f"{SESSION_PATH}?token={SECRET}", follow_redirects=False)
            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.headers["location"], "/")
            cookie = response.headers["set-cookie"]
            self.assertIn(f"{SESSION_COOKIE}={SECRET}", cookie)
            self.assertIn("HttpOnly", cookie)
            self.assertIn("SameSite=lax", cookie)
            self.assertIn("DayWright interface", client.get("/").text)
            self.assertEqual(client.get("/api/health").json(), {"status": "ok"})


class ListenTests(unittest.TestCase):
    def test_uses_the_preferred_port_when_it_is_free(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            free_port = probe.getsockname()[1]
        with listen(free_port) as listener:
            self.assertEqual(listener.getsockname(), ("127.0.0.1", free_port))

    def test_moves_to_another_loopback_port_when_the_preferred_one_is_taken(self):
        with socket.socket() as holder:
            holder.bind(("127.0.0.1", 0))
            holder.listen()
            taken_port = holder.getsockname()[1]
            with listen(taken_port) as listener:
                address, port = listener.getsockname()
                self.assertEqual(address, "127.0.0.1")
                self.assertNotEqual(port, taken_port)


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
