"""The models DayWright runs on this Mac, read in place from the one folder the user chooses in Settings.

The folder is laid out as the shared model library is, `gguf/` and `whisper/`. Until one is chosen no model is
read, not even from a shared library. Each model is pinned to the exact files its publisher released: a file
whose size or SHA-256 differs is not used. A checksum taken is kept in DayWright's own preferences with the
file's size and modification time, and taken again only when either changes. Nothing in the folder is ever
written, moved or deleted.
"""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from os import stat_result
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # For the annotations only: the store's module reaches the model gateways, which import this one.
    from .database import Database

# How much of a model file is read at once while its checksum is taken.
_CHUNK_BYTES = 1 << 20


@dataclass(frozen=True)
class ModelFile:
    """One file a model needs: its name inside the model's folder ("" for a model that is one file), and the
    size and SHA-256 its publisher released."""
    name: str
    size: int
    sha256: str


@dataclass(frozen=True)
class ModelSpec:
    """A model DayWright runs: its role, where it sits in a models folder, and the files it needs there."""
    role: str
    location: str
    files: tuple[ModelFile, ...]


# Qwen3-4B (Qwen/Qwen3-4B-GGUF at bc640142c66e1fdd12af0bd68f40445458f3869b) for Ava and plans; Qwen3-Embedding-0.6B
# (Qwen/Qwen3-Embedding-0.6B-GGUF at 370f27d7550e0def9b39c1f16d3fbaa13aa67728) for Library search and suggestions;
# Whisper small converted for faster-whisper (Systran/faster-whisper-small at 536b0662742c02347bc0e980a01041f333bce120)
# for voice.
MODELS = (
    ModelSpec("chat", "gguf/Qwen3-4B-Q4_K_M.gguf", (
        ModelFile("", 2497280256, "7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5"),)),
    ModelSpec("embedding", "gguf/Qwen3-Embedding-0.6B-Q8_0.gguf", (
        ModelFile("", 639150592, "06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439"),)),
    ModelSpec("speech", "whisper/faster-whisper-small", (
        ModelFile("config.json", 2370, "b55496ac7940a7ae47d2c01eab40edfd8701feec1229d9cce3b40014383fb828"),
        ModelFile("model.bin", 483546902, "3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671"),
        ModelFile("tokenizer.json", 2203239, "fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab"),
        ModelFile("vocabulary.txt", 459861, "34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913"),
    )),
)

# A file's state, worst first: a model reading several files takes its worst one's.
_FILE_STATES = ("missing", "mismatch", "checking", "ready")


class ModelLibrary:
    """The models folder chosen in Settings and the state of each model in it.

    Args:
        store: Where the choice and the checksums taken are kept.
        specs: The models to look for, MODELS unless a test pins its own.
        background: Whether checksums are taken in the background, the model reading "checking" meanwhile;
            without it, each is taken before its state is given.
        development_folder: A folder standing in for a choice while none is kept, for development and
            tests only: the desktop app never passes one.
        runner: The program that runs the chat and search models, which Settings shows found or not; it
            is not chosen, as a model is.
    """

    def __init__(self, store: Database, specs: tuple[ModelSpec, ...] = MODELS, background: bool = True,
                 development_folder: Path | None = None, runner: Path | None = None) -> None:
        self.store = store
        self.specs = specs
        self.background = background
        self.development_folder = development_folder
        self.runner = runner
        self._checking: set[str] = set()
        self._lock = threading.Lock()

    @staticmethod
    def hash_file(path: Path) -> str:
        """Return a file's SHA-256, read a megabyte at a time."""
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(_CHUNK_BYTES):
                digest.update(chunk)
        return digest.hexdigest()

    def folder(self) -> Path | None:
        """Return the folder models are read from: the one chosen in Settings, else the development folder."""
        chosen = self.store.models_folder()
        return Path(chosen) if chosen else self.development_folder

    def choose(self, folder: str) -> dict:
        """Keep `folder` as the one models are read from, and start checking each model in it.

        Raises:
            ValueError: When it is not the full path of a folder that exists.

        Returns:
            The states (see states).
        """
        path = Path(folder).expanduser()
        if not folder.strip() or not path.is_absolute() or not path.is_dir():
            raise ValueError("Choose a folder that exists, by its full path")
        self.store.set_models_folder(str(path))
        return self.states()

    def forget(self) -> dict:
        """Stop using the chosen folder: no model is read until another is chosen; its files stay as they are.

        Returns:
            The states (see states).
        """
        self.store.set_models_folder(None)
        return self.states()

    def states(self) -> dict:
        """Return the "folder" models are read from, or None; whether it was "found", is "notFound" or is
        "none" chosen; each of the "models" with its "role", its file or folder "name", the "location" looked
        in, or None, and its "state": "noFolder", "folderNotFound", "missing", "mismatch", "checking" or
        "ready"; and the "runner"
        with the "location" looked in and its "state", "found" or "notFound", or None without one."""
        folder = self.folder()
        found = folder is not None and folder.is_dir()
        return {"folder": str(folder) if folder else None, "state": "none" if folder is None else "found" if found else "notFound",
                "models": [{"role": spec.role, "name": Path(spec.location).name,
                            "location": str(folder / spec.location) if folder else None,
                            "state": self._state(spec, folder) if found else "noFolder" if folder is None else "folderNotFound"}
                           for spec in self.specs],
                "runner": self.runner and {"location": str(self.runner), "state": "found" if self.runner.is_file() else "notFound"}}

    def path(self, role: str) -> Path | None:
        """Return where the model for `role` is read from, once it is ready; else None."""
        folder = self.folder()
        spec = next(spec for spec in self.specs if spec.role == role)
        if folder is None or not folder.is_dir() or self._state(spec, folder) != "ready":
            return None
        return folder / spec.location

    def _state(self, spec: ModelSpec, folder: Path) -> str:
        """Return the state of a model in a folder that exists: its worst file's (see _FILE_STATES)."""
        place = folder / spec.location
        states = [self._file_state(place / file.name if file.name else place, file) for file in spec.files]
        return min(states, key=_FILE_STATES.index)

    def _file_state(self, path: Path, pinned: ModelFile) -> str:
        """Return whether one file is "missing", a "mismatch" for its pin, being checked, or "ready"."""
        if not path.is_file():
            return "missing"
        status = path.stat()
        if status.st_size != pinned.size:
            return "mismatch"
        kept = self.store.model_checks().get(str(path))
        if kept and (kept["size"], kept["mtime"]) == (status.st_size, status.st_mtime_ns):
            return "ready" if kept["sha256"] == pinned.sha256 else "mismatch"
        if not self.background:
            return "ready" if self._check(path, status) == pinned.sha256 else "mismatch"
        with self._lock:
            if str(path) not in self._checking:
                self._checking.add(str(path))
                threading.Thread(target=self._check, args=(path, status, True), daemon=True).start()
        return "checking"

    def _check(self, path: Path, status: stat_result, background: bool = False) -> str | None:
        """Take a file's checksum and keep it with the size and modification time it was taken at; None, and
        nothing kept, when the file can't be read."""
        try:
            digest = self.hash_file(path)
            if digest:
                self.store.set_model_check(str(path), {"sha256": digest, "size": status.st_size, "mtime": status.st_mtime_ns})
            return digest
        except OSError:
            return None
        finally:
            if background:
                with self._lock:
                    self._checking.discard(str(path))
