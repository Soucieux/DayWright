"""The person's own choices, kept once for every workspace in one small file in DayWright's data folder.

They are the models folder and the runner chosen in Settings, with each model file's checksum as last taken (see
models), where the models run, the interface's language, in which the menu bar's title is written, Open with's app for
each file type, Your day, the work schedule (see schedule), and how statutory holidays are used (see holidays). The
demo workspace reads and writes the same file, so a choice made in one workspace holds in the other, while each
workspace's records stay in its own database. Until DayWright 5.5 these choices were rows of the database's
preferences: the first start that finds no file seeds it from those rows, reading the database only, and from then on
the file alone is read and written.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
import threading
from pathlib import Path

from .holiday_places import COUNTRY_CODES
from .planner import minutes_after_midnight

# The file's name, in DayWright's data folder beside the real workspace's database.
SETTINGS_FILE = "settings.json"
# The language the interface starts in until the user chooses one.
DEFAULT_LANGUAGE = "en"
# Where Ava's and search's models run, Settings' Run models on: "automatic", on the Mac's graphics (Metal) when they
# can and on its processor otherwise, until the user chooses "processor" alone. Voice always runs on the processor.
RUN_MODELS_ON = ("automatic", "processor")
AUTOMATIC, PROCESSOR_ONLY = RUN_MODELS_ON
# The file types Open with chooses an app for, and the longest app name it keeps.
OPEN_WITH_TYPES = ("md", "pdf", "docx")
OPEN_WITH_NAME_LENGTH = 80
# Settings › Schedule's two ways to keep a work schedule: working hours kept free of plans, or focus time that holds
# the day's Work.
WORK_MODES = ("working", "focus")
# The work schedule until the user sets one: off, working hours from 09:00 to 17:00, Monday (0) to Friday (4).
DEFAULT_WORK_SCHEDULE = {"enabled": False, "mode": "working", "start": "09:00", "end": "17:00", "days": [0, 1, 2, 3, 4]}
# A time the work schedule and Your day are kept in: HH:MM, from 00:00 to 23:59.
CLOCK = re.compile(r"([01]\d|2[0-3]):[0-5]\d")
# Your day, the hours every day's plans fill and after which it is over, until the user sets it; and the shortest
# day that can be set.
DEFAULT_YOUR_DAY = {"start": "09:00", "end": "22:00"}
MIN_DAY_MINUTES = 6 * 60
# Statutory holidays until the user sets them: off, with no country or region chosen (see holidays).
DEFAULT_HOLIDAYS = {"enabled": False, "country": None, "region": None}
_REGION = re.compile(r"[A-Z]{2}-[A-Z0-9]{1,3}")
# The database preference each choice was kept under up to DayWright 5.5, by its key in the file.
_SEEDED_FROM = {"modelsFolder": "models_folder", "modelChecks": "model_checks", "interfaceLanguage": "interface_language",
                "openWith": "openWith"}


class AppSettings:
    """The person's own choices, read from and written to one file.

    Args:
        path: The file, SETTINGS_FILE in DayWright's data folder.
        seed_from: The real workspace's database, whose preferences seed the file when there is none yet; it is
            opened read-only and never changed. None, as for the demo workspace, seeds nothing.
    """

    def __init__(self, path: Path, seed_from: Path | None = None) -> None:
        self.path = path
        self._lock = threading.Lock()
        if not path.exists() and seed_from is not None and seed_from.is_file():
            self._write(_read_preferences(seed_from))

    def _read(self) -> dict:
        """Return every choice kept, or none when the file isn't there yet."""
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}

    def _write(self, values: dict) -> None:
        """Replace the file with `values` in one step, so a reader never finds it half written."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(prefix=".settings-", dir=self.path.parent)
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(values, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, self.path)

    def _set(self, key: str, value: object) -> None:
        """Keep `value` under `key`, or forget the key, given None."""
        with self._lock:
            values = self._read()
            if value is None:
                values.pop(key, None)
            else:
                values[key] = value
            self._write(values)

    def models_folder(self) -> str | None:
        """Return the models folder chosen in Settings, or None while none is."""
        return self._read().get("modelsFolder")

    def set_models_folder(self, folder: str | None) -> None:
        """Keep the models folder chosen in Settings, or forget it, given None."""
        self._set("modelsFolder", folder)

    def runner(self) -> str | None:
        """Return the runner, llama-server, chosen in Settings, or None while none is."""
        return self._read().get("runner")

    def set_runner(self, path: str | None) -> None:
        """Keep the runner chosen in Settings, or forget it, given None."""
        self._set("runner", path)

    def model_checks(self) -> dict[str, dict]:
        """Return each model file's checksum as last taken, by its full path: its "sha256", and the "size" and
        "mtime" (in nanoseconds) the file had then."""
        return self._read().get("modelChecks", {})

    def set_model_check(self, path: str, check: dict) -> None:
        """Keep one model file's checksum as just taken (see model_checks), beside the others'."""
        with self._lock:
            values = self._read()
            values["modelChecks"] = {**values.get("modelChecks", {}), path: check}
            self._write(values)

    def run_models_on(self) -> str:
        """Return where the models run, AUTOMATIC until PROCESSOR_ONLY is chosen; any other value kept reads AUTOMATIC."""
        chosen = self._read().get("runModelsOn")
        return chosen if chosen in RUN_MODELS_ON else AUTOMATIC

    def set_run_models_on(self, choice: str) -> None:
        """Keep where the models run, one of RUN_MODELS_ON.

        Raises:
            ValueError: For any other choice.
        """
        if choice not in RUN_MODELS_ON:
            raise ValueError(f"Models run on one of: {', '.join(RUN_MODELS_ON)}")
        self._set("runModelsOn", choice)

    def interface_language(self) -> str:
        """Return the interface's language, "en" or "zh", in which the menu bar's title is written."""
        return self._read().get("interfaceLanguage", DEFAULT_LANGUAGE)

    def set_interface_language(self, language: str) -> None:
        """Keep the interface's language, "en" or "zh"."""
        self._set("interfaceLanguage", language)

    def open_with(self) -> dict:
        """Return Open with's app for each file type the user chose; a type not chosen opens in its default."""
        return self._read().get("openWith", {})

    def set_open_with(self, chosen: dict) -> dict:
        """Keep Open with's app for each file type: "default", "obsidian", or an app's name.

        Returns:
            The choices kept: only Open with's file types, each name trimmed and cut to OPEN_WITH_NAME_LENGTH.
        """
        kept = {kind: str(app).strip()[:OPEN_WITH_NAME_LENGTH] for kind, app in chosen.items()
                if kind in OPEN_WITH_TYPES and str(app).strip()}
        self._set("openWith", kept)
        return kept

    def work_schedule(self) -> dict:
        """Return the work schedule: whether it is on ("enabled"), its "mode" (one of WORK_MODES), its "start" and
        "end" as "HH:MM", and the weekdays it holds on ("days", Monday 0 to Sunday 6); DEFAULT_WORK_SCHEDULE until
        one is set."""
        return self._read().get("workSchedule", dict(DEFAULT_WORK_SCHEDULE))

    def set_work_schedule(self, schedule: dict) -> dict:
        """Keep the work schedule, whole, as work_schedule describes it.

        Returns:
            The schedule kept, its days sorted.

        Raises:
            ValueError: When a part is missing or isn't one the schedule allows, or it ends before it starts.
        """
        enabled, mode, start, end, days = (schedule.get(key) for key in ("enabled", "mode", "start", "end", "days"))
        if not isinstance(enabled, bool):
            raise ValueError("The work schedule is either on or off")
        if mode not in WORK_MODES:
            raise ValueError(f"The work schedule is one of: {', '.join(WORK_MODES)}")
        if not all(isinstance(clock, str) and CLOCK.fullmatch(clock) for clock in (start, end)):
            raise ValueError("The work schedule's times are written HH:MM")
        if start >= end:
            raise ValueError("The work schedule ends after it starts")
        if (not isinstance(days, list) or not days
                or not all(isinstance(day, int) and not isinstance(day, bool) and 0 <= day <= 6 for day in days)):
            raise ValueError("The work schedule holds on at least one weekday")
        kept = {"enabled": enabled, "mode": mode, "start": start, "end": end, "days": sorted(set(days))}
        self._set("workSchedule", kept)
        return kept

    def your_day(self) -> dict:
        """Return Your day: its "start" and "end" as "HH:MM", the hours every day's plans fill and after which it is
        over; DEFAULT_YOUR_DAY until set."""
        return self._read().get("yourDay", dict(DEFAULT_YOUR_DAY))

    def set_your_day(self, day: dict) -> dict:
        """Keep Your day, whole, as your_day describes it.

        Returns:
            The day kept.

        Raises:
            ValueError: When a time isn't written HH:MM, or the day ends less than MIN_DAY_MINUTES after it starts.
        """
        start, end = day.get("start"), day.get("end")
        if not all(isinstance(clock, str) and CLOCK.fullmatch(clock) for clock in (start, end)):
            raise ValueError("Your day's times are written HH:MM")
        if minutes_after_midnight(end) - minutes_after_midnight(start) < MIN_DAY_MINUTES:
            raise ValueError(f"Your day ends at least {MIN_DAY_MINUTES // 60} hours after it starts")
        kept = {"start": start, "end": end}
        self._set("yourDay", kept)
        return kept

    def holiday_settings(self) -> dict:
        """Return how statutory holidays are used: whether they are on ("enabled"), the "country" chosen, by its
        ISO 3166-1 code, and the "region", by its ISO 3166-2 code, or None for national holidays alone;
        DEFAULT_HOLIDAYS until set. Turning them off keeps the list imported (see holidays)."""
        return self._read().get("holidays", dict(DEFAULT_HOLIDAYS))

    def set_holiday_settings(self, chosen: dict) -> dict:
        """Keep how statutory holidays are used, whole, as holiday_settings describes it.

        Returns:
            The choice kept.

        Raises:
            ValueError: When it isn't on or off, the country isn't one of holiday_places.COUNTRIES, or the region
                isn't one of the country's.
        """
        enabled, country, region = (chosen.get(key) for key in ("enabled", "country", "region"))
        if not isinstance(enabled, bool):
            raise ValueError("Statutory holidays are either on or off")
        if country is not None and country not in COUNTRY_CODES:
            raise ValueError("Choose a country DayWright can import holidays for")
        if region is not None and not (country and isinstance(region, str) and _REGION.fullmatch(region)
                                       and region.startswith(f"{country}-")):
            raise ValueError("Choose a region of the country chosen")
        kept = {"enabled": enabled, "country": country, "region": region}
        self._set("holidays", kept)
        return kept


def _read_preferences(database: Path) -> dict:
    """Return the choices a database kept as preferences up to DayWright 5.5, by their keys in the file, opening it
    read-only so nothing in it changes; none when it has no preferences to read."""
    connection = sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            f"SELECT key, value_json FROM preferences WHERE key IN ({', '.join('?' * len(_SEEDED_FROM))})",
            tuple(_SEEDED_FROM.values())).fetchall()
    except sqlite3.OperationalError:  # A database from before preferences were kept holds none.
        rows = []
    finally:
        connection.close()
    kept = dict(rows)
    return {key: json.loads(kept[old]) for key, old in _SEEDED_FROM.items() if old in kept}
