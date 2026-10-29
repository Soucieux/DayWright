"""The person's own choices, kept once for both workspaces in one file in DayWright's data folder: the models
folder with each model file's checksum, the interface's language, and Open with's app for each file type."""

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.app_settings import SETTINGS_FILE, AppSettings
from backend.app.database import Database

CHECK = {"sha256": "a" * 64, "size": 3, "mtime": 1}


def checksum(path: Path) -> str:
    """The SHA-256 of the file at `path`, to show a file was left as it was."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AppSettingsTests(unittest.TestCase):
    def setUp(self):
        """A temporary folder, and the shared settings file's place in it, not yet written."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.file = self.root / SETTINGS_FILE

    def keep_in_database(self, store: Database, values: dict) -> None:
        """Write preference rows as DayWright up to 5.5 kept them in its database."""
        with sqlite3.connect(store.path) as connection:
            connection.executemany("INSERT INTO preferences (key, value_json, updated_at) VALUES (?, ?, '2026-10-01T09:00:00+00:00')",
                                   [(key, json.dumps(value)) for key, value in values.items()])

    def test_a_new_file_holds_no_choice_and_english_and_is_written_only_when_something_is_chosen(self):
        shared = AppSettings(self.file)
        self.assertEqual((shared.models_folder(), shared.model_checks(), shared.interface_language(), shared.open_with()),
                         (None, {}, "en", {}))
        self.assertFalse(self.file.exists())

    def test_each_choice_is_kept_in_the_file_for_the_next_start(self):
        shared = AppSettings(self.file)
        shared.set_models_folder("/Models")
        shared.set_model_check("/Models/gguf/chat.gguf", CHECK)
        shared.set_interface_language("zh")
        self.assertEqual(shared.set_open_with({"md": "default", "pdf": " Skim ", "exe": "x", "docx": " "}),
                         {"md": "default", "pdf": "Skim"})
        again = AppSettings(self.file)
        self.assertEqual((again.models_folder(), again.model_checks(), again.interface_language(), again.open_with()),
                         ("/Models", {"/Models/gguf/chat.gguf": CHECK}, "zh", {"md": "default", "pdf": "Skim"}))
        again.set_models_folder(None)
        self.assertIsNone(AppSettings(self.file).models_folder())
        self.assertEqual(sorted(path.name for path in self.root.iterdir()), [SETTINGS_FILE])

    def test_the_file_is_seeded_from_the_databases_preferences_by_reading_it_only(self):
        store = Database(self.root / "daywright.sqlite3")
        self.keep_in_database(store, {"models_folder": "/Models", "model_checks": {"/Models/gguf/chat.gguf": CHECK},
                                      "interface_language": "zh", "openWith": {"pdf": "Skim"}, "meals": {"lunch": "12:00"}})
        before = (checksum(store.path), sorted(path.name for path in self.root.iterdir()))
        shared = AppSettings(self.file, seed_from=store.path)
        self.assertEqual((shared.models_folder(), shared.model_checks(), shared.interface_language(), shared.open_with()),
                         ("/Models", {"/Models/gguf/chat.gguf": CHECK}, "zh", {"pdf": "Skim"}))
        self.assertEqual((checksum(store.path), sorted(path.name for path in self.root.iterdir() if path != self.file)), before)
        self.assertEqual(set(json.loads(self.file.read_text())), {"modelsFolder", "modelChecks", "interfaceLanguage", "openWith"})

    def test_once_the_file_exists_it_alone_is_read_and_written(self):
        store = Database(self.root / "daywright.sqlite3")
        self.keep_in_database(store, {"models_folder": "/Models", "interface_language": "zh"})
        AppSettings(self.file, seed_from=store.path)
        with sqlite3.connect(store.path) as connection:
            connection.execute("UPDATE preferences SET value_json = ? WHERE key = 'models_folder'", (json.dumps("/Elsewhere"),))
        before = checksum(store.path)
        shared = AppSettings(self.file, seed_from=store.path)
        self.assertEqual(shared.models_folder(), "/Models")
        shared.set_models_folder(None)
        shared.set_model_check("/Models/gguf/chat.gguf", CHECK)
        shared.set_interface_language("en")
        self.assertEqual(checksum(store.path), before)
        self.assertEqual((AppSettings(self.file).models_folder(), AppSettings(self.file).interface_language()), (None, "en"))

    def test_a_database_with_no_preferences_seeds_an_empty_file_and_a_missing_one_seeds_nothing(self):
        missing = self.root / "missing.sqlite3"
        shared = AppSettings(self.file, seed_from=missing)
        self.assertEqual((shared.models_folder(), shared.interface_language()), (None, "en"))
        self.assertFalse(missing.exists())
        self.assertFalse(self.file.exists())
        store = Database(self.root / "daywright.sqlite3")
        AppSettings(self.file, seed_from=store.path)
        self.assertEqual(json.loads(self.file.read_text()), {})


if __name__ == "__main__":
    unittest.main()
