from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.database import Database

# Learning's and Life's own records, as every database made before v3.5 holds them.
OLD_RECORDS = """
CREATE TABLE learning_items (id TEXT PRIMARY KEY, title TEXT NOT NULL, difficulty TEXT NOT NULL,
    estimated_minutes INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL);
CREATE TABLE learning_sessions (id TEXT PRIMARY KEY, item_id TEXT NOT NULL REFERENCES learning_items(id),
    session_date TEXT NOT NULL, minutes INTEGER NOT NULL, result TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE life_habits (id TEXT PRIMARY KEY, title TEXT NOT NULL, frequency TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
CREATE TABLE life_habit_logs (id TEXT PRIMARY KEY, habit_id TEXT NOT NULL REFERENCES life_habits(id),
    log_date TEXT NOT NULL, done INTEGER NOT NULL, note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
    UNIQUE(habit_id, log_date));
CREATE TABLE life_daily (daily_date TEXT PRIMARY KEY, sleep_hours REAL, energy_level INTEGER, mood INTEGER,
    note TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL);
CREATE TABLE life_events (id TEXT PRIMARY KEY, item_id TEXT NOT NULL UNIQUE REFERENCES daily_items(id),
    category TEXT NOT NULL, created_at TEXT NOT NULL);
"""
OLD_TABLES = {"learning_items", "learning_sessions", "life_habits", "life_habit_logs", "life_daily", "life_events"}
NOW = "2026-09-01T08:00:00+00:00"


def tables(path):
    with sqlite3.connect(path) as connection:
        return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


class AreaRecordsMoveTests(unittest.TestCase):
    """On first start of v3.5, Learning's and Life's own records fold into tasks and goals, once."""

    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "daywright.sqlite3"
        self.today = date.today()
        yesterday = (self.today - timedelta(days=1)).isoformat()
        # A database as v3.4 left it: its current tables, and the area records beside them.
        Database(self.path)
        with sqlite3.connect(self.path) as old:
            old.executescript(OLD_RECORDS)
            old.executemany("INSERT INTO life_habits VALUES (?, ?, ?, ?, ?)", [
                ("habit_walk", "Evening walk", "daily", 1, NOW), ("habit_call", "Call home", "weekly", 1, NOW),
                ("habit_old", "Cold shower", "daily", 0, NOW)])
            old.execute("INSERT INTO life_habit_logs VALUES ('log_1', 'habit_walk', ?, 1, 'Nice.', ?)", (yesterday, NOW))
            old.executemany("INSERT INTO learning_items VALUES (?, ?, ?, ?, ?, ?)", [
                ("subject_rag", "RAG foundations", "hard", 240, "active", NOW),
                ("subject_french", "French verbs", "easy", 30, "done", NOW),
                ("subject_chess", "Chess openings", "medium", 60, "archived", NOW)])
            old.execute("INSERT INTO learning_sessions VALUES ('session_1', 'subject_rag', ?, 35, 'done', ?)",
                        (yesterday, NOW))
            old.execute("INSERT INTO life_daily VALUES (?, 6.5, 2, 3, 'Tired.', ?)", (yesterday, NOW))
            old.execute("""INSERT INTO daily_items (id, item_date, title, detail, domain, start_time, duration_minutes,
                               constraint_kind, created_at) VALUES ('item_gym', ?, 'Gym', 'sport', 'life', '18:30', 60,
                               'fixed', ?)""", (yesterday, NOW))
            old.execute("""INSERT INTO daily_items (id, item_date, title, detail, domain, start_time, duration_minutes,
                               constraint_kind, created_at) VALUES ('item_club', ?, 'Book club', 'social, at Anna''s',
                               'life', '20:00', 60, 'fixed', ?)""", (yesterday, NOW))
            old.executemany("INSERT INTO life_events VALUES (?, ?, ?, ?)", [
                ("event_gym", "item_gym", "sport", NOW), ("event_club", "item_club", "social", NOW)])
            old.execute("""INSERT INTO summary_reports (period_kind, period_key, report_json, updated_at)
                           VALUES ('week', '2026-W40', '{}', ?)""", (NOW,))
        self.store = Database(self.path)

    def life_tasks(self):
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row
            return {row["title"]: dict(row) for row in connection.execute(
                "SELECT * FROM daily_items WHERE domain = 'life' AND item_date = ?", (self.today.isoformat(),))}

    def test_active_habits_become_repeating_flexible_life_tasks_from_today(self):
        tasks = self.life_tasks()

        self.assertEqual(set(tasks), {"Evening walk", "Call home"})
        for title, kind in (("Evening walk", "daily"), ("Call home", "weekly")):
            task = tasks[title]
            self.assertEqual((task["repeat_kind"], task["constraint_kind"], task["start_time"]), (kind, "flexible", None))
            self.assertEqual((task["duration_source"], task["estimated_by"]), ("estimate", "life"))
            self.assertEqual(task["repeat_series_id"], task["id"])
            self.assertEqual(task["completion_status"], "planned")

    def test_learning_subjects_become_learning_goals_with_finished_ones_completed(self):
        goals = {goal["title"]: goal for goal in self.store.goals()}

        self.assertEqual({title: (goal["domain"], goal["status"]) for title, goal in goals.items()}, {
            "RAG foundations": ("learning", "active"), "French verbs": ("learning", "completed"),
            "Chess openings": ("learning", "completed")})
        self.assertNotIn("difficulty", goals["RAG foundations"])

    def test_events_stay_fixed_tasks_and_a_detail_that_was_only_their_category_is_cleared(self):
        gym, club = self.store.daily_item("item_gym"), self.store.daily_item("item_club")

        self.assertEqual((gym["constraint_kind"], gym["start_time"], gym["detail"]), ("fixed", "18:30", ""))
        self.assertEqual(club["detail"], "social, at Anna's")

    def test_the_old_records_and_tables_are_gone(self):
        self.assertFalse(tables(self.path) & OLD_TABLES)
        self.assertIsNone(self.store.energy((self.today - timedelta(days=1)).isoformat()))
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM summary_reports").fetchone()[0], 0)

    def test_it_runs_once_and_a_reopened_database_changes_nothing(self):
        before = (self.life_tasks(), self.store.goals())

        Database(self.path)

        self.assertEqual((self.life_tasks(), self.store.goals()), before)

    def test_a_new_database_never_has_the_old_tables(self):
        fresh = Path(self.folder.name) / "fresh.sqlite3"

        Database(fresh)

        self.assertFalse(tables(fresh) & OLD_TABLES)
        self.assertIn("energy_readings", tables(fresh))


class AreaRecordsMoveDuplicateTests(unittest.TestCase):
    """A habit or subject the user already keeps as a task or goal of the same name isn't made twice."""

    def test_a_habit_already_on_today_as_a_life_task_and_a_subject_already_a_learning_goal_are_skipped(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "daywright.sqlite3"
            store = Database(path)
            goal = store.create_goal("RAG foundations", "learning")
            store.create_daily_item({"date": date.today().isoformat(), "title": "Evening walk", "detail": "",
                                     "domain": "life", "startTime": None, "durationMinutes": 45,
                                     "constraintKind": "flexible", "repeatKind": "daily", "goalId": None})
            with sqlite3.connect(path) as old:
                old.executescript(OLD_RECORDS)
                old.execute("INSERT INTO life_habits VALUES ('habit_walk', ' evening  Walk', 'daily', 1, ?)", (NOW,))
                old.execute("INSERT INTO learning_items VALUES ('subject_rag', 'rag foundations', 'hard', 240, 'done', ?)",
                            (NOW,))

            store = Database(path)

            self.assertEqual([item["title"] for item in store.daily_items(date.today().isoformat())], ["Evening walk"])
            self.assertEqual([(entry["id"], entry["status"]) for entry in store.goals()], [(goal["id"], "active")])


if __name__ == "__main__":
    unittest.main()
