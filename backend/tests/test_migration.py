import json
import sqlite3
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.database import Database

# The tables that named the Learn, Life, Money and Rest areas, as a database made before
# Work and Project existed holds them, with Money's own records.
OLD_AREAS = "'learning', 'life', 'finance', 'rest'"
OLD_SCHEMA = f"""
CREATE TABLE goals (id TEXT PRIMARY KEY, title TEXT NOT NULL,
    domain TEXT NOT NULL CHECK(domain IN ({OLD_AREAS})),
    status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL);
CREATE TABLE daily_items (id TEXT PRIMARY KEY, item_date TEXT NOT NULL, goal_id TEXT REFERENCES goals(id),
    title TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '',
    domain TEXT NOT NULL CHECK(domain IN ({OLD_AREAS})), start_time TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL, constraint_kind TEXT NOT NULL,
    repeat_kind TEXT NOT NULL DEFAULT 'none', protected INTEGER NOT NULL DEFAULT 0,
    origin_kind TEXT NOT NULL DEFAULT 'user', origin_detail TEXT NOT NULL DEFAULT '',
    origin_source_item_id TEXT REFERENCES daily_items(id),
    completion_status TEXT NOT NULL DEFAULT 'planned',
    acceptance TEXT NOT NULL DEFAULT 'accepted', created_at TEXT NOT NULL);
CREATE TABLE plan_sets (id TEXT PRIMARY KEY, plan_date TEXT NOT NULL UNIQUE, source TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE plan_variants (id TEXT PRIMARY KEY, plan_set_id TEXT NOT NULL REFERENCES plan_sets(id),
    name TEXT NOT NULL, slug TEXT NOT NULL, rationale TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
    supersedes_variant_id TEXT, created_at TEXT NOT NULL);
CREATE TABLE plan_entries (id TEXT PRIMARY KEY, variant_id TEXT NOT NULL REFERENCES plan_variants(id),
    position INTEGER NOT NULL, start_time TEXT NOT NULL, title TEXT NOT NULL, detail TEXT NOT NULL,
    source_item_id TEXT REFERENCES daily_items(id),
    domain TEXT NOT NULL CHECK(domain IN ({OLD_AREAS})), duration_minutes INTEGER NOT NULL,
    constraint_kind TEXT NOT NULL, completion_status TEXT NOT NULL DEFAULT 'planned');
CREATE TABLE suggestion_pool (id TEXT PRIMARY KEY, period_kind TEXT NOT NULL, period_key TEXT NOT NULL,
    domain TEXT NOT NULL CHECK(domain IN ({OLD_AREAS}, 'cross')), content TEXT NOT NULL,
    priority TEXT NOT NULL, source_key TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active',
    discarded_at TEXT, created_at TEXT NOT NULL, UNIQUE(period_kind, period_key, source_key));
CREATE TABLE conversation_threads (id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE conversation_messages (id TEXT PRIMARY KEY, thread_id TEXT NOT NULL, role TEXT NOT NULL,
    mode TEXT NOT NULL, content TEXT NOT NULL, model_mode TEXT, created_at TEXT NOT NULL);
CREATE TABLE agent_runs (id TEXT PRIMARY KEY, message_id TEXT NOT NULL, sequence INTEGER NOT NULL,
    agent_key TEXT NOT NULL CHECK(agent_key IN ('orchestrator', 'learning', 'life', 'finance', 'summary')),
    phase TEXT NOT NULL, summary TEXT NOT NULL, reads_json TEXT NOT NULL, writes_json TEXT NOT NULL,
    created_at TEXT NOT NULL, UNIQUE(message_id, sequence));
CREATE TABLE plan_generation_routes (plan_set_id TEXT PRIMARY KEY, route_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE summary_reports (period_kind TEXT NOT NULL, period_key TEXT NOT NULL, report_json TEXT NOT NULL,
    updated_at TEXT NOT NULL, PRIMARY KEY(period_kind, period_key));
CREATE TABLE life_events (id TEXT PRIMARY KEY, item_id TEXT NOT NULL UNIQUE REFERENCES daily_items(id),
    category TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE finance_account (id INTEGER PRIMARY KEY, opening_balance_cents INTEGER NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE finance_transactions (id TEXT PRIMARY KEY, transaction_date TEXT NOT NULL, type TEXT NOT NULL,
    amount_cents INTEGER NOT NULL, category TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
CREATE TABLE finance_budgets (id TEXT PRIMARY KEY, year_month TEXT NOT NULL, category TEXT NOT NULL,
    budget_cents INTEGER NOT NULL, updated_at TEXT NOT NULL);
"""


class AreaMigrationTests(unittest.TestCase):
    def setUp(self):
        """A throwaway database in OLD_SCHEMA, holding tasks, plans, advice, messages and money records of the retired
        Finance and Rest areas beside Learning's and Life's."""
        self.folder = TemporaryDirectory()
        self.path = Path(self.folder.name) / "daywright.sqlite3"
        self.today = date.today().isoformat()
        self.past = (date.today() - timedelta(days=3)).isoformat()
        now = "2026-01-01T00:00:00+00:00"
        with sqlite3.connect(self.path) as old:
            old.executescript(OLD_SCHEMA)
            old.executemany("INSERT INTO goals VALUES (?, ?, ?, 'active', ?)", [
                ("goal_money", "Save more", "finance", now), ("goal_learn", "Learn French", "learning", now)])
            old.executemany(
                """INSERT INTO daily_items (id, item_date, goal_id, title, domain, start_time,
                   duration_minutes, constraint_kind, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
                    ("item_budget", self.today, "goal_money", "Budget check", "finance", "17:00", 30, "flexible", now),
                    ("item_rest", self.today, None, "Evening reset", "rest", "21:00", 30, "fixed", now),
                    ("item_read", self.today, "goal_learn", "Read", "learning", "09:00", 45, "flexible", now),
                    ("item_gym", self.today, None, "Gym", "life", "18:00", 60, "flexible", now),
                    ("item_old", self.past, None, "Old walk", "life", "08:00", 30, "flexible", now)])
            old.execute("INSERT INTO life_events VALUES ('event_gym', 'item_gym', 'sport', ?)", (now,))
            old.execute("INSERT INTO plan_sets VALUES ('set_past', ?, 'orchestrator-records-v1', ?)", (self.past, now))
            old.execute("INSERT INTO plan_variants (id, plan_set_id, name, slug, rationale, created_at) "
                        "VALUES ('variant_past', 'set_past', 'Balanced', 'balanced', 'Steady', ?)", (now,))
            old.execute("INSERT INTO plan_entries (id, variant_id, position, start_time, title, detail, "
                        "source_item_id, domain, duration_minutes, constraint_kind) VALUES "
                        "('entry_past', 'variant_past', 0, '08:00', 'Old walk', '', 'item_old', 'rest', 30, 'flexible')")
            old.executemany("INSERT INTO suggestion_pool (id, period_kind, period_key, domain, content, priority, "
                            "source_key, created_at) VALUES (?, 'week', '2026-W40', ?, ?, 'soft', ?, ?)", [
                                ("pool_money", "finance", "Check the budget.", "key_money", now),
                                ("pool_rest", "rest", "Sleep earlier.", "key_rest", now)])
            old.execute("INSERT INTO conversation_threads VALUES ('thread_1', 'Today', ?, ?)", (now, now))
            old.execute("INSERT INTO conversation_messages VALUES ('message_1', 'thread_1', 'assistant', 'ask', 'Hi', NULL, ?)", (now,))
            old.executemany("INSERT INTO agent_runs VALUES (?, 'message_1', ?, ?, 'assessment', ?, '[]', '[]', ?)", [
                ("run_learn", 0, "learning", "Learning report", now), ("run_money", 1, "finance", "Balance 12.50", now)])
            old.execute("INSERT INTO plan_generation_routes VALUES ('set_past', ?, ?)", (json.dumps([
                {"agentKey": "learning", "summary": "ok"}, {"agentKey": "finance", "summary": "Balance 12.50"}]), now))
            old.execute("INSERT INTO summary_reports VALUES ('day', ?, '{}', ?)", (self.past, now))
            old.execute("INSERT INTO finance_account VALUES (1, 10000, ?)", (now,))
            old.execute("INSERT INTO finance_transactions VALUES ('tx_1', ?, 'expense', 1250, 'Food', '', ?)", (self.today, now))

    def tearDown(self):
        """Remove the throwaway database's folder."""
        self.folder.cleanup()

    def rows(self, sql, *parameters):
        """The rows `sql` reads with `parameters`, each as a dict."""
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row
            return [dict(row) for row in connection.execute(sql, parameters)]

    def test_retired_areas_move_to_life_and_money_records_are_deleted(self):
        Database(self.path)
        domains = {row["id"]: row["domain"] for row in self.rows("SELECT id, domain FROM daily_items")}
        self.assertEqual(domains, {"item_budget": "life", "item_rest": "life", "item_read": "learning",
                                   "item_gym": "life", "item_old": "life"})
        self.assertEqual({row["id"]: row["domain"] for row in self.rows("SELECT id, domain FROM goals")},
                         {"goal_money": "life", "goal_learn": "learning"})
        self.assertEqual(self.rows("SELECT domain FROM plan_entries"), [{"domain": "life"}])
        tables = {row["name"] for row in self.rows("SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertFalse(tables & {"finance_account", "finance_transactions", "finance_budgets"})
        self.assertEqual([(row["domain"], row["content"]) for row in self.rows("SELECT domain, content FROM suggestion_pool")],
                         [("life", "Sleep earlier.")])
        self.assertEqual([row["agent_key"] for row in self.rows("SELECT agent_key FROM agent_runs")], ["learning"])
        route = json.loads(self.rows("SELECT route_json FROM plan_generation_routes")[0]["route_json"])
        self.assertEqual([run["agentKey"] for run in route], ["learning"])
        self.assertEqual(self.rows("SELECT * FROM summary_reports"), [])

    def test_flexible_tasks_from_today_lose_their_start_time_but_past_days_and_events_keep_theirs(self):
        Database(self.path)
        items = {row["id"]: row for row in self.rows("SELECT id, start_time, constraint_kind FROM daily_items")}
        self.assertIsNone(items["item_read"]["start_time"])
        self.assertIsNone(items["item_budget"]["start_time"])
        self.assertEqual(items["item_rest"]["start_time"], "21:00")
        self.assertEqual(items["item_old"]["start_time"], "08:00")
        self.assertEqual((items["item_gym"]["start_time"], items["item_gym"]["constraint_kind"]), ("18:00", "fixed"))

    def test_the_new_shape_takes_new_areas_and_reopening_changes_nothing(self):
        store = Database(self.path)
        created = store.create_daily_item({
            "date": self.today, "title": "Write tests", "detail": "", "domain": "project",
            "startTime": None, "durationMinutes": 45, "constraintKind": "flexible",
            "repeatKind": "none", "goalId": None})
        self.assertIsNone(created["start_time"])
        before = self.rows("SELECT * FROM daily_items ORDER BY id")
        Database(self.path)
        self.assertEqual(self.rows("SELECT * FROM daily_items ORDER BY id"), before)
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO daily_items (id, item_date, title, domain, start_time, duration_minutes, "
                    "constraint_kind, created_at) VALUES ('item_bad', ?, 'Fixed', 'work', NULL, 30, 'fixed', 'now')",
                    (self.today,))


class RationaleQuoteMigrationTests(unittest.TestCase):
    def test_saved_plans_get_their_task_names_quoted_once(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "quotes.sqlite3"
            Database(path)
            focused = ("Places learning, then project, then work first while attention is fresh, and gives "
                       "Review notes 15 more minutes; fixed times and repeatedly shortened tasks stay as they are.")
            gentle = ("Starts placing from 09:30, life tasks first, and leaves 15 minutes after each task it places; "
                      "shortens Draft the guide by 15 minutes without removing it; fixed times stay as they are.")
            older = ("Adds 15 minutes to this is title where the saved calendar has room; "
                     "fixed times and repeatedly disliked tasks stay unchanged.")
            oldest = "Shortens Walk by 15 minutes, never removes it; fixed commitments stay unchanged."
            with sqlite3.connect(path) as connection:
                connection.execute("INSERT INTO plan_sets VALUES ('set', '2026-10-01', 'recorded', 'now')")
                connection.executemany(
                    "INSERT INTO plan_variants (id, plan_set_id, name, slug, rationale, created_at) VALUES (?, 'set', ?, ?, ?, 'now')",
                    [("focused", "Focused", "focused", focused), ("gentle", "Gentle", "gentle", gentle),
                     ("older", "Focused", "older", older), ("oldest", "Gentle", "oldest", oldest)])

            Database(path)
            Database(path)

            with sqlite3.connect(path) as connection:
                rationales = dict(connection.execute("SELECT id, rationale FROM plan_variants"))
            self.assertIn("and gives “Review notes” 15 more minutes;", rationales["focused"])
            self.assertIn("shortens “Draft the guide” by 15 minutes without removing it;", rationales["gentle"])
            self.assertTrue(rationales["older"].startswith("Adds 15 minutes to “this is title” where the saved calendar"))
            self.assertTrue(rationales["oldest"].startswith("Shortens “Walk” by 15 minutes, never removes it;"))


class EnergyLogMigrationTests(unittest.TestCase):
    def test_each_days_one_reading_moves_into_the_log_once_with_its_local_time_and_the_old_table_goes(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "energy.sqlite3"
            Database(path)
            saved = [("2026-10-01", 2, "2026-10-01T08:15:00+00:00"), ("2026-10-03", 4, "2026-10-03T19:40:00+00:00")]
            with sqlite3.connect(path) as connection:
                connection.execute("DROP TABLE energy_log")
                connection.execute("""CREATE TABLE energy_readings (reading_date TEXT PRIMARY KEY,
                                      level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 5), updated_at TEXT NOT NULL)""")
                connection.executemany("INSERT INTO energy_readings VALUES (?, ?, ?)", saved)

            store = Database(path)
            for day, level, at in saved:
                local = datetime.fromisoformat(at).astimezone().strftime("%H:%M")
                self.assertEqual((store.energy(day), store.energy_readings(day)), (float(level), [{"level": level, "time": local}]))
            Database(path)
            with sqlite3.connect(path) as connection:
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM energy_log").fetchone()[0], 2)
            self.assertNotIn("energy_readings", tables)


class SampleDayMigrationTests(unittest.TestCase):
    def test_the_prototypes_sample_days_go_with_their_suggestions_and_a_day_of_the_users_stays(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "sample.sqlite3"
            Database(path)
            with sqlite3.connect(path) as connection:
                connection.execute("""CREATE TABLE IF NOT EXISTS suggestions (id TEXT PRIMARY KEY, plan_date TEXT NOT NULL,
                                      title TEXT NOT NULL, detail TEXT NOT NULL, decision TEXT, decided_at TEXT)""")
                for plan_set, day, source in (("sample", "2026-09-14", "deterministic-v1"),
                                              ("own", "2026-10-01", "orchestrator-records-v1")):
                    connection.execute("INSERT INTO plan_sets VALUES (?, ?, ?, 'now')", (plan_set, day, source))
                    connection.execute("INSERT INTO plan_variants (id, plan_set_id, name, slug, rationale, created_at) "
                                       "VALUES (?, ?, 'Balanced', 'balanced', 'r', 'now')", (f"{plan_set}-plan", plan_set))
                    connection.execute("""INSERT INTO plan_entries (id, variant_id, position, start_time, title, detail, domain,
                                          duration_minutes, constraint_kind) VALUES (?, ?, 0, '09:00', 'Read', '', 'learning',
                                          60, 'flexible')""", (f"{plan_set}-entry", f"{plan_set}-plan"))
                    connection.execute("INSERT INTO plan_generation_routes VALUES (?, '[]', 'now')", (plan_set,))
                    connection.execute("INSERT INTO daily_confirmations VALUES (?, ?, 'now')", (day, f"{plan_set}-plan"))
                connection.execute("INSERT INTO suggestions VALUES ('walk', '2026-09-14', 'Try a 10-minute walk after lunch.', "
                                   "'A short walk can restore energy.', NULL, NULL)")

            Database(path)
            Database(path)

            with sqlite3.connect(path) as connection:
                kept = {table: [row[0] for row in connection.execute(f"SELECT {column} FROM {table}")]
                        for table, column in (("plan_sets", "id"), ("plan_variants", "id"), ("plan_entries", "id"),
                                              ("plan_generation_routes", "plan_set_id"), ("daily_confirmations", "plan_date"))}
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            self.assertEqual(kept, {"plan_sets": ["own"], "plan_variants": ["own-plan"], "plan_entries": ["own-entry"],
                                    "plan_generation_routes": ["own"], "daily_confirmations": ["2026-10-01"]})
            self.assertNotIn("suggestions", tables)


if __name__ == "__main__":
    unittest.main()
