"""Run DayWright's local service inside its desktop app.

The desktop shell starts this service with a secret for the launch, reads the chosen port from
standard output, and opens its window at `SESSION_PATH` with that secret. The service serves the
built interface and the API from one loopback address, answers only requests that carry the session
cookie that first request sets, and exits when the shell closes its standard input, which also
happens when the shell itself dies.
"""

from __future__ import annotations

import hmac
import os
import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from starlette.requests import HTTPConnection
from starlette.responses import PlainTextResponse, RedirectResponse
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.websockets import WebSocketClose

from .config import MODEL_LIBRARY_VARIABLE, load_settings
from .llama_runtime import stop_orphans

# Tried first so the interface keeps one address, and with it the saved language, across launches.
PREFERRED_PORT = 8425
# The shell reads the port from the line that starts with this, printed once requests are accepted.
PORT_ANNOUNCEMENT = "DAYWRIGHT_PORT="
SESSION_PATH = "/desktop/session"
SESSION_COOKIE = "daywright_session"
# The view the menu bar's panel opens its session on: `PANEL_VIEW` in src-tauri/src/menubar.rs.
PANEL_VIEW = "menubar"
TOKEN_VARIABLE = "DAYWRIGHT_SESSION_TOKEN"
CLIENT_VARIABLE = "DAYWRIGHT_CLIENT_DIR"
DATABASE_VARIABLE = "DAYWRIGHT_DATABASE"
REFUSAL = "DayWright's service answers only its own window."


class SessionGate:
    """Admit only the desktop window.

    The window's first request opens `SESSION_PATH` with the launch secret and gets it back as an
    HttpOnly cookie; every later request must carry that cookie. Any other program on this Mac,
    and any web page, is refused. The cookie is SameSite=Lax rather than Strict because the window
    arrives from its start screen, another site, and a Strict cookie would be withheld from the
    redirect that follows; it lives only in the app's own web view either way.
    """

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self._token = token.encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self.app(scope, receive, send)
            return
        connection = HTTPConnection(scope)
        if scope["type"] == "http" and connection.url.path == SESSION_PATH:
            await self._open_session(connection.query_params.get("token", ""),
                                     connection.query_params.get("view", ""))(scope, receive, send)
        elif self._matches(connection.cookies.get(SESSION_COOKIE, "")):
            await self.app(scope, receive, send)
        elif scope["type"] == "http":
            await PlainTextResponse(REFUSAL, status_code=403)(scope, receive, send)
        else:
            await WebSocketClose()(scope, receive, send)

    def _matches(self, offered: str) -> bool:
        """Compare an offered secret with the launch secret in constant time."""
        return hmac.compare_digest(offered.encode(), self._token)

    def _open_session(self, offered: str, view: str) -> PlainTextResponse | RedirectResponse:
        """Exchange the launch secret for the session cookie and send the window to the interface, or
        the menu bar's panel to its own view (PANEL_VIEW); any other view is not passed on."""
        if not self._matches(offered):
            return PlainTextResponse(REFUSAL, status_code=403)
        response = RedirectResponse(f"/?view={PANEL_VIEW}" if view == PANEL_VIEW else "/", status_code=303)
        response.set_cookie(SESSION_COOKIE, self._token.decode(), httponly=True, samesite="lax")
        return response


def prepare(app: FastAPI, token: str, client_directory: Path) -> None:
    """Serve the built interface in `client_directory` beside `app`'s API routes, all behind the
    session gate for the launch secret `token`. Call it once every API route is registered."""
    app.mount("/", StaticFiles(directory=client_directory, html=True), name="client")
    app.add_middleware(SessionGate, token=token)


def listen(preferred_port: int) -> socket.socket:
    """Bind a loopback socket on `preferred_port`, or on a free port when another program holds it.
    The returned socket is bound but not yet listening; the server listens on it."""
    for port in (preferred_port, 0):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Lets a relaunch reuse the port while the last run's closed connections wait out TIME_WAIT.
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(("127.0.0.1", port))
        except OSError:
            listener.close()
            continue
        return listener
    raise OSError("No loopback port is free for DayWright's service.")


def _announce_when_started(server: uvicorn.Server, port: int) -> None:
    """Tell the shell the port once the service accepts requests."""
    while not server.started:
        if server.should_exit:
            return
        time.sleep(0.05)
    print(f"{PORT_ANNOUNCEMENT}{port}", flush=True)


def _exit_when_shell_closes(server: uvicorn.Server) -> None:
    """Shut down once the shell closes standard input, as it does on quit and when it dies."""
    sys.stdin.buffer.read()
    server.should_exit = True


def main() -> None:
    """Start the service for the desktop shell, which supplies every setting in the environment."""
    token = os.environ.get(TOKEN_VARIABLE, "")
    client = os.environ.get(CLIENT_VARIABLE, "")
    if not (token and client and os.environ.get(DATABASE_VARIABLE)) or not (
        Path(client) / "index.html"
    ).is_file():
        sys.exit(
            f"DayWright's desktop service needs {TOKEN_VARIABLE}, {DATABASE_VARIABLE} and "
            f"{CLIENT_VARIABLE} from its app."
        )
    # The app reads models only from the folder chosen in its Settings, never a development one.
    os.environ.pop(MODEL_LIBRARY_VARIABLE, None)
    settings = load_settings()
    if settings.runtime_directory is not None:
        stop_orphans(settings.runtime_directory, settings.llama_binary)
    # Imported here: importing builds the service from these settings, after leftovers are stopped.
    from .main import app

    prepare(app, token, Path(client))
    listener = listen(PREFERRED_PORT)
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False))
    port = listener.getsockname()[1]
    threading.Thread(target=_announce_when_started, args=(server, port), daemon=True).start()
    threading.Thread(target=_exit_when_shell_closes, args=(server,), daemon=True).start()
    server.run(sockets=[listener])
