from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
# A models folder standing in for the one chosen in Settings, for development and tests only: the desktop
# app removes it before reading its settings, so the installed app reads models only from the user's choice.
MODEL_LIBRARY_VARIABLE = "DAYWRIGHT_MODEL_LIBRARY"


@dataclass(frozen=True)
class Settings:
    database_path: Path
    llama_binary: Path
    demo_mode: bool = False
    model_context: int = 4096
    embedding_context: int = 2048
    # Where model-server process IDs are recorded so a later launch can stop any left behind.
    runtime_directory: Path | None = None
    # The development models folder (see MODEL_LIBRARY_VARIABLE); None unless one is given.
    model_library: Path | None = None


def load_settings() -> Settings:
    model_library = os.environ.get(MODEL_LIBRARY_VARIABLE)
    runtime_directory = os.environ.get("DAYWRIGHT_RUNTIME_DIR")
    return Settings(
        database_path=Path(
            os.environ.get(
                "DAYWRIGHT_DATABASE",
                PROJECT_ROOT / "backend" / "data" / "daywright.sqlite3",
            )
        ).expanduser(),
        llama_binary=Path(
            os.environ.get("DAYWRIGHT_LLAMA_SERVER", "/opt/homebrew/bin/llama-server")
        ).expanduser(),
        demo_mode=os.environ.get("DAYWRIGHT_DEMO", "").lower() in {"1", "true", "yes"},
        runtime_directory=Path(runtime_directory).expanduser() if runtime_directory else None,
        model_library=Path(model_library).expanduser() if model_library else None,
    )
