"""Switching between the user's own workspace and the demo (see demo).

The service stops as it does on quit, its background work finished first, then starts again in place: the same
program in the same process, with the same session, port and pipes to the desktop app, and with the demo switch
(config.DEMO_VARIABLE) set or cleared. Nothing anywhere records the choice, so a new launch opens the user's own
workspace, as does quitting in the demo.
"""

from __future__ import annotations

import atexit
import os
import shutil
import signal
import sys
from pathlib import Path
from typing import Callable

from .config import DEMO_VARIABLE


def _interrupt() -> None:
    """Stop the service as an interrupt from the command line does: its server shuts down, then the program ends."""
    os.kill(os.getpid(), signal.SIGINT)


# How a switch stops the service; the desktop service stops its own server instead (see desktop.main).
_stop: Callable[[], None] = _interrupt


def set_stop(stop: Callable[[], None]) -> None:
    """Have a switch stop the service with `stop`, as the desktop service does with its own server."""
    global _stop
    _stop = stop


def switch(opens_demo: bool, reset: Path | None = None) -> None:
    """Stop the service, to start it again in the demo workspace or in the user's own.

    Args:
        opens_demo: Whether the service starts again in the demo workspace.
        reset: The demo's folder, deleted once the service has stopped so the demo is made anew; None keeps it.
    """
    if opens_demo:
        os.environ[DEMO_VARIABLE] = "1"
    else:
        os.environ.pop(DEMO_VARIABLE, None)
    atexit.register(_start_again, reset)
    _stop()


def _start_again(reset: Path | None) -> None:
    """As the stopped service's program ends: delete the demo's folder when asked, then start the same program
    again in this process, with the environment as the switch left it."""
    if reset is not None:
        shutil.rmtree(reset, ignore_errors=True)
    sys.stdout.flush()
    sys.stderr.flush()
    # The desktop app's service is a frozen program, started as itself; otherwise Python runs the server's script.
    os.execv(sys.executable, sys.argv if getattr(sys, "frozen", False) else [sys.executable, *sys.argv])
