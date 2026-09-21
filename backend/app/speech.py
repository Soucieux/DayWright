"""Ephemeral, loopback-only transcription with a local CTranslate2 Whisper model."""

from __future__ import annotations

import importlib.util
import tempfile
import threading
from pathlib import Path

from .config import Settings


class SpeechUnavailable(RuntimeError):
    """The short local audio clip cannot be transcribed by the configured runtime."""


class SpeechGateway:
    """Transcribe a short WAV locally and remove its temporary recording afterward."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model = None
        self._lock = threading.Lock()

    def status(self) -> dict:
        """Report whether both converted model files and the Python runtime are present."""
        files = ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt")
        model_ready = (all((self.settings.whisper_path / name).is_file() for name in files)
                       and (self.settings.whisper_path / "model.bin").stat().st_size > 450_000_000)
        runtime_ready = importlib.util.find_spec("faster_whisper") is not None
        ready = model_ready and runtime_ready
        return {"state": "available" if ready else "unavailable",
                "modelAvailable": model_ready, "runtimeAvailable": runtime_ready,
                "label": "Whisper small · local push-to-talk" if ready
                         else "Local speech runtime needs setup"}

    def transcribe(self, audio: bytes) -> dict:
        """Validate a bounded mono PCM WAV, recognize it locally, and discard the WAV."""
        if self.status()["state"] != "available":
            raise SpeechUnavailable("The local Whisper runtime is not ready")
        if not 44 <= len(audio) <= 2_000_000 or audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
            raise ValueError("Send a short PCM WAV recording (up to 2 MB)")
        if (int.from_bytes(audio[20:22], "little") != 1
                or int.from_bytes(audio[22:24], "little") != 1
                or int.from_bytes(audio[34:36], "little") != 16):
            raise ValueError("Voice input must be mono 16-bit PCM WAV")
        with tempfile.TemporaryDirectory(prefix="daywright-voice-") as folder:
            input_path = Path(folder) / "push-to-talk.wav"
            input_path.write_bytes(audio)
            try:
                with self._lock:
                    if self._model is None:
                        from faster_whisper import WhisperModel

                        self._model = WhisperModel(str(self.settings.whisper_path),
                                                   device="cpu", compute_type="int8",
                                                   cpu_threads=4, local_files_only=True)
                    segments, _ = self._model.transcribe(str(input_path), beam_size=3,
                                                         vad_filter=False)
                    transcript = " ".join(part.text.strip() for part in segments
                                          if part.text.strip())
            except Exception as error:
                raise SpeechUnavailable("Local speech recognition failed") from error
            if not transcript:
                raise SpeechUnavailable("No speech was recognized; try a short, clear recording")
            return {"text": transcript[:4000], "model": self.status()["label"]}
