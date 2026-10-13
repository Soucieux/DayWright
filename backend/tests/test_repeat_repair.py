"""The one-time repair of repeats copied forward without their series before v5.6: each copy linked to the one series
it unambiguously belongs to, after a backup, in one transaction, once, and only in the user's own workspace."""

import os
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.config import DEMO_FOLDER, DEMO_VARIABLE
from backend.app.database import Database
from backend.app.desktop import DATABASE_VARIABLE
from backend.app.main import create_app
from backend.app.repeat_repair import BACKUPS_FOLDER, repair_repeats

TODAY = date(2026, 10, 12)
NOW = "2026-09-01T09:00:00+00:00"


def dump(path: Path) -> dict[str, list[tuple]]:
    """Every row of every plain table, sorted."""
    with sqlite3.connect(path) as connection:
        tables = [row[0] for row in connection.execute(
            """SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
               AND sql NOT LIKE 'CREATE VIRTUAL TABLE%' ORDER BY name""")]
        return {table: sorted(map(tuple, connection.execute(f'SELECT * FROM "{table}"')), key=repr) for table in tables}


class Repair(unittest.TestCase):
    """A user's own database with repeats: each series' own days, and copies made without a series."""

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.data = Path(folder.name)
        self.path = self.data / "daywright.sqlite3"
        self.store = Database(self.path)

    def add(self, item_id: str, day: str, title: str, domain: str, kind: str, series: str | None) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """INSERT INTO daily_items (id, item_date, title, domain, duration_minutes, constraint_kind, repeat_kind,
                                            repeat_series_id, created_at) VALUES (?, ?, ?, ?, 30, 'flexible', ?, ?, ?)""",
                (item_id, day, title, domain, kind, series, NOW))

    def series(self, series_id: str, title: str, domain: str, kind: str, *days: str) -> None:
        """A repeat's own days, the first of them its series' id."""
        for day in days:
            self.add(series_id if day == days[0] else f"{series_id}_{day}", day, title, domain, kind, series_id)

    def change(self, series_id: str, kind: str, starts: str) -> None:
        """A stop (kind "none") or a switch recorded for a series, from `starts` on."""
        with sqlite3.connect(self.path) as connection:
            connection.execute("INSERT INTO repeat_series (id, next_kind, next_from) VALUES (?, ?, ?)", (series_id, kind, starts))

    def series_of(self, item_id: str) -> str | None:
        with sqlite3.connect(self.path) as connection:
            return connection.execute("SELECT repeat_series_id FROM daily_items WHERE id = ?", (item_id,)).fetchone()[0]

    def backup(self) -> Path:
        return self.data / BACKUPS_FOLDER / "daywright-before-5.6-2026-10-12.sqlite"


class MatchTests(Repair):
    def test_a_copy_matching_one_series_exactly_is_linked_to_it(self):
        self.series("gym", "Gym", "life", "weekly", "2026-09-07")
        self.add("copy1", "2026-09-14", "Gym", "life", "weekly", None)
        self.add("copy2", "2026-09-21", "Gym", "life", "weekly", None)
        line = repair_repeats(self.store, TODAY)
        self.assertEqual((self.series_of("copy1"), self.series_of("copy2")), ("gym", "gym"))
        self.assertEqual(line, f"repeat repair: 2 linked, 0 left unlinked (0 ambiguous, 0 outside every run), backup {self.backup()}")

    def test_the_same_title_in_another_area_or_two_series_alike_is_left_unlinked(self):
        self.series("review_learn", "Review", "learning", "weekly", "2026-09-07")
        self.add("project_copy", "2026-09-14", "Review", "project", "weekly", None)
        self.series("standup_a", "Stand-up", "work", "daily", "2026-09-01")
        self.series("standup_b", "Stand-up", "work", "daily", "2026-09-03")
        self.add("standup_copy", "2026-09-10", "Stand-up", "work", "daily", None)
        line = repair_repeats(self.store, TODAY)
        self.assertEqual((self.series_of("project_copy"), self.series_of("standup_copy")), (None, None))
        self.assertIn("0 linked, 2 left unlinked (1 ambiguous, 1 outside every run)", line)

    def test_a_copy_of_a_series_since_renamed_is_left_unlinked(self):
        self.series("reading", "Read a chapter", "learning", "daily", "2026-09-01", "2026-09-02")
        self.add("copy", "2026-09-05", "Read", "learning", "daily", None)
        repair_repeats(self.store, TODAY)
        self.assertIsNone(self.series_of("copy"))

    def test_a_copy_on_a_day_after_its_series_stopped_stays_a_record_of_its_own(self):
        self.series("journal", "Journal", "life", "weekly", "2026-09-07")
        self.change("journal", "none", "2026-09-21")
        self.add("before_stop", "2026-09-14", "Journal", "life", "weekly", None)
        self.add("after_stop", "2026-09-28", "Journal", "life", "weekly", None)
        line = repair_repeats(self.store, TODAY)
        self.assertEqual((self.series_of("before_stop"), self.series_of("after_stop")), ("journal", None))
        self.assertIn("1 linked, 1 left unlinked (0 ambiguous, 1 outside every run)", line)
        with sqlite3.connect(self.path) as connection:
            self.assertTrue(connection.execute("SELECT 1 FROM daily_items WHERE id = 'after_stop'").fetchone(), "never deleted")

    def test_a_switched_repeat_is_matched_by_its_new_kind_from_the_day_it_changed(self):
        self.series("run", "Run", "life", "weekly", "2026-09-07")
        self.change("run", "daily", "2026-09-21")
        self.add("weekly_before", "2026-09-14", "Run", "life", "weekly", None)
        self.add("daily_after", "2026-09-22", "Run", "life", "daily", None)
        self.add("weekly_after", "2026-09-28", "Run", "life", "weekly", None)
        repair_repeats(self.store, TODAY)
        self.assertEqual([self.series_of(item) for item in ("weekly_before", "daily_after", "weekly_after")], ["run", "run", None])

    def test_a_weekly_copy_on_another_weekday_or_before_its_series_began_is_left_unlinked(self):
        self.series("piano", "Piano", "learning", "weekly", "2026-09-08")
        self.add("wednesday", "2026-09-16", "Piano", "learning", "weekly", None)
        self.add("earlier", "2026-09-01", "Piano", "learning", "weekly", None)
        repair_repeats(self.store, TODAY)
        self.assertEqual((self.series_of("wednesday"), self.series_of("earlier")), (None, None))

    def test_a_task_already_in_a_series_is_left_as_it_is(self):
        self.series("gym", "Gym", "life", "weekly", "2026-09-07")
        self.series("gym_again", "Gym", "life", "weekly", "2026-09-14")
        line = repair_repeats(self.store, TODAY)
        self.assertEqual((self.series_of("gym"), self.series_of("gym_again")), ("gym", "gym_again"))
        self.assertIn("0 linked, 0 left unlinked", line)


class SafetyTests(Repair):
    def test_it_runs_once_and_a_second_start_changes_nothing(self):
        self.series("gym", "Gym", "life", "weekly", "2026-09-07")
        self.add("copy", "2026-09-14", "Gym", "life", "weekly", None)
        self.assertIsNotNone(repair_repeats(self.store, TODAY))
        self.add("later_copy", "2026-09-21", "Gym", "life", "weekly", None)
        before = dump(self.path)
        self.assertIsNone(repair_repeats(self.store, TODAY))
        self.assertEqual(dump(self.path), before)
        self.assertIsNone(self.series_of("later_copy"))

    def test_the_backup_is_made_before_any_change_and_holds_the_data_as_it_was(self):
        self.series("gym", "Gym", "life", "weekly", "2026-09-07")
        self.add("copy", "2026-09-14", "Gym", "life", "weekly", None)
        before = dump(self.path)
        repair_repeats(self.store, TODAY)
        self.assertEqual(dump(self.backup()), before)
        self.assertEqual(self.series_of("copy"), "gym")

    def test_an_error_on_the_way_rolls_back_to_exactly_the_data_before_and_it_runs_again_later(self):
        self.series("gym", "Gym", "life", "weekly", "2026-09-07")
        self.add("copy1", "2026-09-14", "Gym", "life", "weekly", None)
        self.add("copy2", "2026-09-21", "Gym", "life", "weekly", None)
        with sqlite3.connect(self.path) as connection:
            connection.execute("""CREATE TRIGGER refuse BEFORE UPDATE OF repeat_series_id ON daily_items WHEN NEW.id = 'copy2'
                                  BEGIN SELECT RAISE(ABORT, 'refused'); END""")
        before = dump(self.path)
        line = repair_repeats(self.store, TODAY)
        self.assertEqual(dump(self.path), before)
        self.assertTrue(line.startswith("repeat repair: failed (refused); nothing changed, backup"), line)
        with sqlite3.connect(self.path) as connection:
            connection.execute("DROP TRIGGER refuse")
        repair_repeats(self.store, TODAY)
        self.assertEqual((self.series_of("copy1"), self.series_of("copy2")), ("gym", "gym"))
        self.assertEqual([path.name for path in (self.data / BACKUPS_FOLDER).iterdir()], [self.backup().name], "one backup")

    def test_a_retry_on_a_later_day_reuses_the_one_backup_holding_the_data_it_starts_from(self):
        self.series("gym", "Gym", "life", "weekly", "2026-09-07")
        self.add("copy", "2026-09-14", "Gym", "life", "weekly", None)
        with sqlite3.connect(self.path) as connection:
            connection.execute("""CREATE TRIGGER refuse BEFORE UPDATE OF repeat_series_id ON daily_items
                                  BEGIN SELECT RAISE(ABORT, 'refused'); END""")
        repair_repeats(self.store, TODAY)
        # Used in between, as DayWright opens anyway: the backup the retry makes holds the data as it now is.
        self.add("used", "2026-10-12", "Call Mum", "life", "none", None)
        with sqlite3.connect(self.path) as connection:
            connection.execute("DROP TRIGGER refuse")
        before = dump(self.path)
        line = repair_repeats(self.store, date(2026, 10, 13))
        self.assertEqual([path.name for path in (self.data / BACKUPS_FOLDER).iterdir()], [self.backup().name])
        self.assertIn(str(self.backup()), line)
        self.assertEqual(dump(self.backup()), before)

    def test_without_a_backup_nothing_is_changed_and_it_tries_again_next_time(self):
        self.series("gym", "Gym", "life", "weekly", "2026-09-07")
        self.add("copy", "2026-09-14", "Gym", "life", "weekly", None)
        (self.data / BACKUPS_FOLDER).write_text("a file where the folder would go")
        before = dump(self.path)
        line = repair_repeats(self.store, TODAY)
        self.assertEqual(dump(self.path), before)
        self.assertTrue(line.startswith("repeat repair: skipped, the backup couldn't be written"), line)
        (self.data / BACKUPS_FOLDER).unlink()
        repair_repeats(self.store, TODAY)
        self.assertEqual(self.series_of("copy"), "gym")

    def test_with_nothing_to_repair_it_only_records_that_it_ran(self):
        line = repair_repeats(self.store, TODAY)
        self.assertEqual(line, "repeat repair: 0 linked, 0 left unlinked (0 ambiguous, 0 outside every run), no backup needed")
        self.assertFalse((self.data / BACKUPS_FOLDER).exists())
        self.assertIsNone(repair_repeats(self.store, TODAY))


class StartTests(Repair):
    def test_the_users_own_workspace_repairs_at_its_first_start_and_the_demo_never_does(self):
        self.series("gym", "Gym", "life", "weekly", "2026-09-07")
        self.add("copy", "2026-09-14", "Gym", "life", "weekly", None)
        demo = Database(self.data / DEMO_FOLDER / self.path.name)
        with sqlite3.connect(demo.path) as connection:
            connection.execute(
                """INSERT INTO daily_items (id, item_date, title, domain, duration_minutes, constraint_kind, repeat_kind,
                                            repeat_series_id, created_at) VALUES
                   ('demo_gym', '2026-09-07', 'Gym', 'life', 30, 'flexible', 'weekly', 'demo_gym', ?),
                   ('demo_copy', '2026-09-14', 'Gym', 'life', 30, 'flexible', 'weekly', NULL, ?)""", (NOW, NOW))
        with patch.dict(os.environ, {DATABASE_VARIABLE: str(self.path), DEMO_VARIABLE: "1"}):
            TestClient(create_app(switch=lambda *_: None))
        with sqlite3.connect(demo.path) as connection:
            self.assertIsNone(connection.execute("SELECT repeat_series_id FROM daily_items WHERE id = 'demo_copy'").fetchone()[0])
            self.assertIsNone(connection.execute("SELECT 1 FROM data_repairs").fetchone())
        self.assertIsNone(self.series_of("copy"), "the user's own data is never opened from the demo")
        self.assertFalse((self.data / BACKUPS_FOLDER).exists())
        with patch.dict(os.environ, {DATABASE_VARIABLE: str(self.path)}):
            os.environ.pop(DEMO_VARIABLE, None)
            TestClient(create_app(switch=lambda *_: None))
        self.assertEqual(self.series_of("copy"), "gym")
        self.assertEqual(len(list((self.data / BACKUPS_FOLDER).iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
