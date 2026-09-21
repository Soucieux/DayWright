from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    database_path: Path
    model_path: Path
    embedding_path: Path
    whisper_path: Path
    llama_binary: Path
    demo_mode: bool = False
    model_context: int = 4096
    embedding_context: int = 2048


def load_settings() -> Settings:
    model_library = Path(
        os.environ.get("DAYWRIGHT_MODEL_LIBRARY", Path.home() / "Documents" / "AI-Models")
    ).expanduser()
    return Settings(
        database_path=Path(
            os.environ.get(
                "DAYWRIGHT_DATABASE",
                PROJECT_ROOT / "backend" / "data" / "daywright.sqlite3",
            )
        ).expanduser(),
        model_path=model_library / "gguf" / "Qwen3-4B-Q4_K_M.gguf",
        embedding_path=model_library / "gguf" / "Qwen3-Embedding-0.6B-Q8_0.gguf",
        whisper_path=model_library / "whisper" / "faster-whisper-small",
        llama_binary=Path(
            os.environ.get("DAYWRIGHT_LLAMA_SERVER", "/opt/homebrew/bin/llama-server")
        ).expanduser(),
        demo_mode=os.environ.get("DAYWRIGHT_DEMO", "").lower() in {"1", "true", "yes"},
    )
