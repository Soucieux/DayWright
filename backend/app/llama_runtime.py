from __future__ import annotations

import atexit
import os
import secrets
import socket
import subprocess
import threading
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


class LlamaRuntime:
    """Own one authenticated loopback llama-server process through readiness."""

    def __init__(self, binary: Path, model: Path, arguments: list[str]) -> None:
        self.binary = binary
        self.model = model
        self.arguments = tuple(arguments)
        self._process: subprocess.Popen | None = None
        self._port: int | None = None
        self._token: str | None = None
        self._ready = False
        self._lock = threading.Lock()
        atexit.register(self.stop)

    @property
    def files_ready(self) -> bool:
        return self.binary.is_file() and self.model.is_file()

    @property
    def running(self) -> bool:
        process = self._process
        return self._ready and process is not None and process.poll() is None

    def connection(self) -> tuple[int, str] | None:
        if not self.running or self._port is None or self._token is None:
            return None
        return self._port, self._token

    @staticmethod
    def _reserve_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
            candidate.bind(("127.0.0.1", 0))
            return int(candidate.getsockname()[1])

    def start(self, timeout: float = 90.0) -> bool:
        failed_process = None
        with self._lock:
            if self.running:
                return True
            if not self.files_ready:
                return False

            self._port = self._reserve_port()
            self._token = secrets.token_urlsafe(32)
            self._ready = False
            environment = os.environ.copy()
            environment["LLAMA_API_KEY"] = self._token
            command = [
                str(self.binary),
                "--model",
                str(self.model),
                *self.arguments,
                "--host",
                "127.0.0.1",
                "--port",
                str(self._port),
                "--device",
                "none",
                "--parallel",
                "1",
                "--no-webui",
                "--offline",
                "--log-disable",
            ]
            try:
                self._process = subprocess.Popen(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                    env=environment,
                )
            except OSError:
                self._process = None
                self._port = None
                self._token = None
                return False

            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if self._process.poll() is not None:
                    break
                try:
                    with urlopen(f"http://127.0.0.1:{self._port}/health", timeout=1):
                        self._ready = True
                        return True
                except (URLError, TimeoutError):
                    time.sleep(0.4)

            failed_process = self._process
            self._process = None
            self._port = None
            self._token = None

        self._terminate(failed_process)
        return False

    def stop(self) -> None:
        with self._lock:
            process = self._process
            self._process = None
            self._port = None
            self._token = None
            self._ready = False
        self._terminate(process)

    @staticmethod
    def _terminate(process: subprocess.Popen | None) -> None:
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
