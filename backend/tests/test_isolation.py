import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from backend.tests.isolation import PROJECT_DATA
from backend.app.config import DATABASE_VARIABLE, PROJECT_ROOT, load_settings
from backend.app.main import create_app


class DataIsolationTests(unittest.TestCase):
    """The suite runs on a temporary database and never reaches `backend/data/`."""

    def test_settings_point_at_a_temporary_database(self):
        database = load_settings().database_path
        self.assertFalse(database.is_relative_to(PROJECT_DATA))
        self.assertTrue(database.is_relative_to(Path(tempfile.gettempdir())))

    def test_the_service_built_from_the_settings_uses_the_temporary_database(self):
        create_app()
        self.assertTrue(load_settings().database_path.is_file())

    def test_importing_the_service_builds_nothing_so_no_database_is_opened(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "daywright.sqlite3"
            subprocess.run([sys.executable, "-c", "import backend.app.main"], cwd=PROJECT_ROOT, check=True,
                           env={**os.environ, DATABASE_VARIABLE: str(database)})
            self.assertFalse(database.exists())

    def test_creating_or_opening_the_project_data_is_refused(self):
        # Raised as audit events, so this check never touches the folder itself.
        database = PROJECT_DATA / "daywright.sqlite3"
        for event, args in (
            ("open", (database, "r", 0)),
            ("os.mkdir", (PROJECT_DATA, 0o777, -1)),
            ("sqlite3.connect", (database,)),
        ):
            with self.subTest(event=event), self.assertRaises(RuntimeError):
                sys.audit(event, *args)

    def test_paths_outside_the_project_data_are_let_through(self):
        sys.audit("sqlite3.connect", load_settings().database_path)
        sys.audit("os.mkdir", PROJECT_DATA.with_name("data-copy"), 0o777, -1)


if __name__ == "__main__":
    unittest.main()
