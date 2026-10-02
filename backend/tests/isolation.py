"""Keep the backend tests away from DayWright's own data.

`load_settings()` defaults to the database in `backend/data/`, and importing `backend.app.main`
builds the service from those settings, which opens and migrates that database. Importing this
module first points the database setting at a folder that lasts for this test process, so the
service, every `load_settings()` call, and the checkpoint files kept beside the database stay
there. It also refuses any test that still reaches `backend/data/`, so a new path to it fails the
suite instead of touching real data.

Every test module imports it before anything from `backend.app`.
"""

from __future__ import annotations

import atexit
import os
import sys
import tempfile
from pathlib import Path

from backend.app.config import PROJECT_ROOT
from backend.app.desktop import DATABASE_VARIABLE

PROJECT_DATA = PROJECT_ROOT / "backend" / "data"
# The audit events through which a test could create or open something in PROJECT_DATA.
_GUARDED_EVENTS = frozenset({"open", "os.mkdir", "sqlite3.connect"})

_folder = tempfile.TemporaryDirectory(prefix="daywright-tests-")
atexit.register(_folder.cleanup)
os.environ[DATABASE_VARIABLE] = str(Path(_folder.name) / "daywright.sqlite3")


def _refuse_project_data(event: str, args: tuple) -> None:
    """Raise when audit `event` would create or open a path inside `PROJECT_DATA`.

    The path is the first argument of every guarded event; an `open` of a file descriptor carries
    an integer there instead and is let through. RuntimeError, not an OSError, so that
    `Path.mkdir(exist_ok=True)` cannot swallow the refusal.
    """
    if event not in _GUARDED_EVENTS or not args:
        return
    if not isinstance(args[0], (str, bytes, os.PathLike)):
        return
    target = Path(os.path.abspath(os.fsdecode(args[0])))
    if target.is_relative_to(PROJECT_DATA):
        raise RuntimeError(f"A test reached DayWright's own data: {target}")


sys.addaudithook(_refuse_project_data)
