from __future__ import annotations

import atexit
import os
import re
import secrets
import signal
import socket
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, TypeVar
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from .app_settings import AUTOMATIC, PROCESSOR_ONLY

# How long the runner may take to list the Mac's devices before it is taken to list none.
LIST_DEVICES_SECONDS = 10
# More layers than any model DayWright runs has, so on the graphics every layer is offloaded to it.
ALL_LAYERS = "999"
# A Metal device in the runner's list, as "  MTL0: Apple M1 Pro (12124 MiB, 12123 MiB free)".
_METAL_LINE = re.compile(r"^\s*(MTL\d+):\s", re.MULTILINE)
# Why a model runs on the processor although Automatic is chosen, as LlamaRuntime.device names it: the runner lists
# no graphics device, its server on the graphics didn't start, or it stopped while in use.
NO_DEVICE, DIDNT_START, STOPPED = "noDevice", "didntStart", "stopped"
# What a request meets when its server has died or hangs, unlike one answered with an error.
_LOST_SERVER = (URLError, TimeoutError, ConnectionError)

# The Metal device each runner listed, asked once a launch (see graphics_device).
_devices: dict[Path, str | None] = {}
_devices_lock = threading.Lock()

T = TypeVar("T")


def metal_device(listing: str) -> str | None:
    """Return the first Metal device in what llama-server's --list-devices printed, such as "MTL0"; None for a list
    without one, or for anything that isn't such a list."""
    match = _METAL_LINE.search(listing)
    return match[1] if match else None


def list_devices(binary: Path) -> str:
    """Return what `binary --list-devices` prints, on either of its outputs; "" when the runner isn't a program this
    Mac can run, fails to start, or takes longer than LIST_DEVICES_SECONDS."""
    if not os.access(binary, os.X_OK):
        return ""
    try:
        listed = subprocess.run([str(binary), "--list-devices"], capture_output=True, text=True, errors="replace",
                                timeout=LIST_DEVICES_SECONDS, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return f"{listed.stdout}\n{listed.stderr}"


def graphics_device(binary: Path) -> str | None:
    """Return the Mac's Metal device as `binary` lists it, or None; asked once a launch and kept until it ends."""
    with _devices_lock:
        if binary not in _devices:
            _devices[binary] = metal_device(list_devices(binary))
        return _devices[binary]


def device_arguments(device: str | None) -> list[str]:
    """Return the runner's arguments for where a model runs: every layer on `device`, or, given None, on the
    processor alone, with no device, as DayWright always ran them before."""
    return ["--device", device, "--n-gpu-layers", ALL_LAYERS] if device else ["--device", "none"]


class LlamaRuntime:
    """Own one authenticated loopback llama-server process through readiness, on the Mac's graphics or its processor.

    With Automatic chosen in Settings a model runs on the graphics (Metal) when the runner lists a device for it; any
    trouble there moves it to the processor for the rest of the launch, and the next launch tries the graphics again.
    With Processor only chosen it never uses the graphics.

    Args:
        binary: The runner, llama-server.
        model: The model file, or None until one is ready.
        arguments: The runner's arguments for the model's own use, such as its context size.
        pid_directory: Where a started server's process ID is recorded (see stop_orphans), or None.
        run_on: Return the Run models on choice: AUTOMATIC or PROCESSOR_ONLY.
        find_device: Return the runner's Metal device, or None; graphics_device unless given.
    """

    def __init__(
        self, binary: Path, model: Path | None, arguments: list[str], pid_directory: Path | None = None,
        run_on: Callable[[], str] = lambda: AUTOMATIC, find_device: Callable[[Path], str | None] | None = None,
    ) -> None:
        self.binary = binary
        self.model = model
        self.arguments = tuple(arguments)
        self.pid_directory = pid_directory
        self.run_on = run_on
        self._find_device = find_device
        self._process: subprocess.Popen | None = None
        self._port: int | None = None
        self._token: str | None = None
        self._ready = False
        # The device the running server uses, None on the processor; why it runs there although Automatic is
        # chosen; and the trouble with the graphics this launch, which holds until it ends.
        self._device: str | None = None
        self._reason: str | None = None
        self._fallback: str | None = None
        self._lock = threading.Lock()
        atexit.register(self.stop)

    @property
    def files_ready(self) -> bool:
        return self.binary.is_file() and self.model is not None and self.model.is_file()

    @property
    def running(self) -> bool:
        process = self._process
        return self._ready and process is not None and process.poll() is None

    def connection(self) -> tuple[int, str] | None:
        if not self.running or self._port is None or self._token is None:
            return None
        return self._port, self._token

    def device(self) -> dict:
        """Return where the model runs, as Settings shows it: "graphics" or "processor" while its server runs, with
        the "reason" it runs on the processor although Automatic is chosen (NO_DEVICE, DIDNT_START or STOPPED, else
        None); "standby" before its first use or once stopped, unless trouble with the graphics this launch already
        holds it to the processor."""
        if self.running:
            return {"state": "graphics" if self._device else "processor", "reason": None if self._device else self._reason}
        if self._fallback and self.run_on() != PROCESSOR_ONLY:
            return {"state": "processor", "reason": self._fallback}
        return {"state": "standby", "reason": None}

    @staticmethod
    def _reserve_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
            candidate.bind(("127.0.0.1", 0))
            return int(candidate.getsockname()[1])

    def start(self, timeout: float = 90.0) -> bool:
        """Start the server where the choice and this launch allow (see _place), unless it runs, and wait for its
        health check. A server on the graphics that exits, or doesn't answer within `timeout`, is stopped and the
        model starts on the processor instead, where it stays until the launch ends."""
        with self._lock:
            if self.running:
                return True
            if not self.files_ready:
                return False
            device, self._reason = self._place()
            started = self._launch(device, timeout)
            if started is False and device is not None:
                self._fallback = self._reason = DIDNT_START
                started = self._launch(None, timeout)
            return bool(started)

    def _place(self) -> tuple[str | None, str | None]:
        """Return the device the server starts on, None for the processor, and why it starts there although Automatic
        is chosen: the processor alone with Processor only chosen, or after trouble with the graphics this launch;
        else the runner's Metal device, or the processor when it lists none."""
        if self.run_on() == PROCESSOR_ONLY:
            return None, None
        if self._fallback:
            return None, self._fallback
        device = (self._find_device or graphics_device)(self.binary)
        return (device, None) if device else (None, NO_DEVICE)

    def _launch(self, device: str | None, timeout: float) -> bool | None:
        """Start the server on `device`, None for the processor, and wait up to `timeout` for its health check.

        Returns:
            True once it answers; False when it exited or didn't answer in time, and was stopped; None when it
            couldn't be started at all, which no other device would change.
        """
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
            *device_arguments(device),
            "--parallel",
            "1",
            "--no-webui",
            "--offline",
            "--log-disable",
        ]
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=environment,
            )
        except OSError:
            self._port = None
            self._token = None
            return None
        self._process = process
        self._record(process)

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break
            try:
                with urlopen(f"http://127.0.0.1:{self._port}/health", timeout=1):
                    self._ready = True
                    self._device = device
                    return True
            except (URLError, TimeoutError):
                time.sleep(0.4)

        self._process = None
        self._port = None
        self._token = None
        self._terminate(process)
        self._forget(process)
        return False

    def retrying(self, send: Callable[[int, str], T]) -> T:
        """Send a request to the running server with `send(port, token)`. When the server is on the graphics and the
        request fails as a dead or stuck server's does, the model moves to the processor for the rest of this launch
        and the request is sent once more there; whatever else `send` raises is raised.

        Raises:
            ConnectionError: When the server isn't running, or doesn't start again on the processor.
        """
        connection = self.connection()
        if connection is None:
            raise ConnectionError("The model server isn't running")
        on_graphics = self._device is not None
        try:
            return send(*connection)
        except HTTPError:
            raise  # The server answered, with an error: the graphics are not at fault.
        except _LOST_SERVER:
            if not on_graphics:
                raise
        with self._lock:
            self._fallback = STOPPED
        self.stop()
        if not self.start():
            raise ConnectionError("The model server didn't start again on the processor")
        return send(*self.connection())

    def use(self, model: Path | None) -> None:
        """Run `model` from the next start, None for no model: a server running another one is stopped."""
        if model != self.model:
            self.stop()
            self.model = model

    def stop(self) -> None:
        with self._lock:
            process = self._process
            self._process = None
            self._port = None
            self._token = None
            self._ready = False
            self._device = None
        self._terminate(process)
        self._forget(process)

    def _record(self, process: subprocess.Popen) -> None:
        """Note a started server's process ID so a later launch can stop it if this service dies first."""
        if self.pid_directory is not None:
            self.pid_directory.mkdir(parents=True, exist_ok=True)
            (self.pid_directory / str(process.pid)).touch()

    def _forget(self, process: subprocess.Popen | None) -> None:
        """Remove the process-ID record of a server this runtime has stopped."""
        if self.pid_directory is not None and process is not None:
            (self.pid_directory / str(process.pid)).unlink(missing_ok=True)

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


def stop_orphans(pid_directory: Path, binary: Path) -> None:
    """Stop model servers left running by a service that ended without shutting them down.

    Each record in `pid_directory` names a server a runtime started. A recorded process is signalled
    only when launchd has adopted it, because its service is gone, and its command still starts with
    `binary --model`, so a process ID the system has since reused is left alone. Every record is
    removed afterwards.
    """
    if not pid_directory.is_dir():
        return
    for record in pid_directory.iterdir():
        if record.name.isdigit() and _is_orphaned_server(int(record.name), binary):
            try:
                os.kill(int(record.name), signal.SIGTERM)
            except ProcessLookupError:
                pass  # It exited between the check and the signal, which is the outcome wanted.
        record.unlink(missing_ok=True)


def _is_orphaned_server(pid: int, binary: Path) -> bool:
    """Whether `pid` is a model server started from `binary` whose parent service has exited."""
    listing = subprocess.run(
        ["/bin/ps", "-o", "ppid=,args=", "-p", str(pid)], capture_output=True, text=True, check=False
    )
    fields = listing.stdout.split(maxsplit=1)
    return len(fields) == 2 and fields[0] == "1" and fields[1].startswith(f"{binary} --model ")
