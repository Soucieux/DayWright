"""The service's settings from its environment: where its database is, which workspace is open, and where the
development runner and models folder are (see load_settings)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# The user's own database; the desktop app sets it to the database in DayWright's data folder.
DATABASE_VARIABLE = "DAYWRIGHT_DATABASE"
# The folder where model-server process IDs are recorded; the desktop app sets it in DayWright's data folder.
RUNTIME_VARIABLE = "DAYWRIGHT_RUNTIME_DIR"
# A runner, llama-server, standing in for the one chosen in Settings, for development and tests only: the desktop app
# removes it before reading its settings, as it does MODEL_LIBRARY_VARIABLE.
RUNNER_VARIABLE = "DAYWRIGHT_LLAMA_SERVER"
# A models folder standing in for the one chosen in Settings, for development and tests only: the desktop
# app removes it before reading its settings, so the installed app reads models only from the user's choice.
MODEL_LIBRARY_VARIABLE = "DAYWRIGHT_MODEL_LIBRARY"
# Set, the service opens the demo workspace instead of the user's own (see demo).
DEMO_VARIABLE = "DAYWRIGHT_DEMO"
# The folder in DayWright's data folder that holds the demo workspace: its database, with its vector store, and its
# Library folder.
DEMO_FOLDER = "Demo"


@dataclass(frozen=True)
class Settings:
    """The service's settings as load_settings reads them; a test may make its own."""

    database_path: Path
    # The development runner (see RUNNER_VARIABLE); None unless one is given.
    llama_binary: Path | None = None
    # Whether this is the demo workspace, whose database is then in DEMO_FOLDER: the user's own is never opened.
    demo_mode: bool = False
    model_context: int = 4096
    embedding_context: int = 2048
    # Where model-server process IDs are recorded so a later launch can stop any left behind.
    runtime_directory: Path | None = None
    # The development models folder (see MODEL_LIBRARY_VARIABLE); None unless one is given.
    model_library: Path | None = None
    # DayWright's data folder: the user's own database, the person's settings file (see app_settings) and DEMO_FOLDER.
    data_directory: Path | None = None


def load_settings() -> Settings:
    """The service's settings, from its environment: the user's database (DATABASE_VARIABLE, else the development
    database under backend/data), or the demo's beside it while DEMO_VARIABLE is set; where process IDs are recorded
    (RUNTIME_VARIABLE); and a development runner and models folder (RUNNER_VARIABLE, MODEL_LIBRARY_VARIABLE)."""
    runner = os.environ.get(RUNNER_VARIABLE)
    model_library = os.environ.get(MODEL_LIBRARY_VARIABLE)
    runtime_directory = os.environ.get(RUNTIME_VARIABLE)
    own = Path(os.environ.get(DATABASE_VARIABLE, PROJECT_ROOT / "backend" / "data" / "daywright.sqlite3")).expanduser()
    demo = os.environ.get(DEMO_VARIABLE, "").lower() in {"1", "true", "yes"}
    return Settings(
        database_path=own.parent / DEMO_FOLDER / own.name if demo else own,
        llama_binary=Path(runner).expanduser() if runner else None,
        demo_mode=demo,
        runtime_directory=Path(runtime_directory).expanduser() if runtime_directory else None,
        model_library=Path(model_library).expanduser() if model_library else None,
        data_directory=own.parent,
    )
