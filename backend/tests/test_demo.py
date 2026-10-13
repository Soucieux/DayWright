"""The demo workspace: two months of one made-up person's use of DayWright, ending on the day it is made, in a folder
of its own that the user's own data never meets."""

import calendar
import collections
import hashlib
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app import recall, source_store
from backend.app.config import DEMO_FOLDER, DEMO_VARIABLE
from backend.app.database import Database
from backend.app.demo import LIBRARY_FOLDER, MADE_AT, PLANNED_AHEAD_DAYS, build_demo, demo_span
from backend.app.desktop import DATABASE_VARIABLE
from backend.app.main import create_app
from backend.tests.test_api import FakeEmbeddingGateway, FakeGateway, FakeSpeechGateway
from backend.tests.test_ava_memory import stamp

# Every file opened, and every database connected to, while _WATCHING holds True.
_OPENED: list[str] = []
_WATCHING = [False]


def _record(event: str, args: tuple) -> None:
    """Note the path an audit event opens, while a demo session is watched."""
    if _WATCHING[0] and event in ("open", "sqlite3.connect") and args and isinstance(args[0], (str, bytes, os.PathLike)):
        _OPENED.append(os.fsdecode(args[0]))


sys.addaudithook(_record)


def holds_a_whole_month(first: date, last: date) -> bool:
    """Whether the days from `first` to `last` hold one calendar month from its first day to its last."""
    month = first if first.day == 1 else (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    return month.replace(day=calendar.monthrange(month.year, month.month)[1]) <= last


def checksums(folder: Path) -> dict[str, str]:
    """Each file directly in `folder`, the user's own data, with its SHA-256; the demo's folder is left out."""
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(folder.iterdir()) if path.is_file()}


def dump(database: Path) -> dict[str, list[tuple]]:
    """Every row of every table, sorted, with the demo's own folder named alike wherever it was made, so two demos with
    the same records compare equal."""
    folder = str(database.parent)
    same = lambda value: value.replace(folder, "<demo>") if isinstance(value, str) else value  # noqa: E731
    with sqlite3.connect(database) as connection:
        # A vector table's rows are kept in plain tables of its own, compared here; the virtual table needs its module.
        tables = [row[0] for row in connection.execute(
            """SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
               AND sql NOT LIKE 'CREATE VIRTUAL TABLE%' ORDER BY name""")]
        return {table: sorted((tuple(map(same, row)) for row in connection.execute(f'SELECT * FROM "{table}"')), key=repr)
                for table in tables}


class SpanTests(unittest.TestCase):
    def test_the_demo_starts_on_the_same_date_two_months_back_clamped_to_that_months_last_day(self):
        for end, first in ((date(2026, 3, 1), date(2026, 1, 1)), (date(2026, 3, 31), date(2026, 1, 31)),
                           (date(2026, 10, 28), date(2026, 8, 28)), (date(2026, 12, 31), date(2026, 10, 31)),
                           (date(2026, 4, 30), date(2026, 2, 28)), (date(2028, 4, 30), date(2028, 2, 29)),
                           (date(2027, 1, 15), date(2026, 11, 15))):
            self.assertEqual(demo_span(end), (first, end), end)

    def test_whatever_the_reset_day_the_demo_holds_a_whole_month_and_more_than_30_days(self):
        for end in (date(2026, 3, 1), date(2026, 3, 31), date(2026, 10, 28), date(2026, 12, 31)):
            first, last = demo_span(end)
            self.assertTrue(holds_a_whole_month(first, last), end)
            self.assertGreater((last - first).days + 1, 30, end)
        self.assertEqual(PLANNED_AHEAD_DAYS, 14)


class DemoWorkspaceTests(unittest.TestCase):
    """One demo, made as the service makes it the first time the demo opens, beside a workspace of the user's own
    whose files it never opens and whose bytes nothing in the demo changes; then used, and left."""

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.data = Path(cls.temp.name) / "DayWright"
        cls.own = cls.data / "daywright.sqlite3"
        cls.environment = patch.dict(os.environ, {DATABASE_VARIABLE: str(cls.own)})
        cls.environment.start()
        os.environ.pop(DEMO_VARIABLE, None)
        cls.today = date.today()
        # The user's own workspace, with a goal, a task and a language chosen, closed before the demo opens.
        own = TestClient(create_app(gateway=FakeGateway(), embedding_gateway=FakeEmbeddingGateway(), day_jobs=False))
        goal = own.post("/api/goals", json={"title": "Read more", "domain": "learning"}).json()
        own.post("/api/daily-items", json={"date": cls.today.isoformat(), "title": "Library visit", "domain": "learning",
                                           "durationMinutes": 60, "goalId": goal["id"]})
        own.put("/api/interface-language", json={"language": "zh"})
        # A card confirmed three days ago and not yet condensed: Ava's round condenses it once the user's own workspace
        # opens again, and never while the demo is open.
        cls.earlier = cls.today - timedelta(days=3)
        cls.confirm_a_card(Database(cls.own), cls.earlier)
        cls.at_rest = checksums(cls.data)
        cls.switches = []
        _OPENED.clear()
        _WATCHING[0] = True
        try:
            # The demo as the app runs it, with Ava's rounds and the Library's refresh; its website is not looked up.
            with patch.dict(os.environ, {DEMO_VARIABLE: "1"}), patch.object(source_store, "fetch_page", side_effect=OSError):
                # The demo is made as it opens, at a moment between these two.
                cls.made_from = datetime.now()
                app = create_app(gateway=FakeGateway(), embedding_gateway=FakeEmbeddingGateway(),
                                 speech_gateway=FakeSpeechGateway(),
                                 switch=lambda opens_demo, reset: cls.switches.append((opens_demo, reset)))
                cls.made_by = datetime.now()
                with TestClient(app) as cls.client:
                    cls.use_the_demo()
        finally:
            _WATCHING[0] = False
        cls.opened = list(_OPENED)
        cls.after_demo = checksums(cls.data)
        cls.store = Database(cls.data / DEMO_FOLDER / cls.own.name)
        cls.come_back()

    @staticmethod
    def confirm_a_card(store: Database, day: date) -> None:
        """A card confirmed on an earlier day, of a conversation in which nothing was said."""
        action = store.propose_action(store.thread(), "move_item", {"date": day.isoformat()},
                                      "Propose moving “Read” on that day to 10:00. Confirm this edit.")
        with store.connect() as connection:
            connection.execute("UPDATE proposed_actions SET status = 'confirmed', created_at = ? WHERE id = ?",
                               (stamp(day), action["id"]))
            connection.execute("INSERT INTO action_confirmations (id, action_id, decision, decided_at) VALUES (?, ?, 'confirmed', ?)",
                               (f"confirmation_{action['id']}", action["id"], stamp(day, 13)))

    @classmethod
    def come_back(cls):
        """The user's own workspace as the service starts again after the switch back, until Ava's first round has
        condensed the day of the earlier card, or ten seconds have gone."""
        with TestClient(create_app(gateway=FakeGateway(), embedding_gateway=FakeEmbeddingGateway(),
                                   speech_gateway=FakeSpeechGateway())):
            own = Database(cls.own)
            deadline = time.monotonic() + 10
            while not recall.summaries(own) and time.monotonic() < deadline:
                time.sleep(0.05)
            cls.condensed_on_return = sorted(recall.summaries(own))

    @classmethod
    def use_the_demo(cls):
        """Use the demo as the user would: report a task, pause and resume the day, use the Library, ask Ava, and go
        back to their own data."""
        day = cls.client.get("/api/bootstrap", params={"date": cls.today.isoformat()}).json()
        task = next(item for item in day["dayItems"] if item["completion_status"] == "planned")
        cls.reported = task["id"]
        cls.client.patch(f"/api/daily-items/{task['id']}/status", json={"status": "done"})
        cls.client.post("/api/day/pause")
        cls.client.post("/api/day/resume")
        cls.client.get("/api/knowledge")
        cls.client.post("/api/knowledge/sources", json={"title": "Demo note", "sourceType": "note", "text": "Sleep well."})
        cls.client.post("/api/knowledge/search", json={"query": "sleep"})
        cls.client.post("/api/chat", json={"date": cls.today.isoformat(), "message": "How is my week going?"})
        cls.client.post("/api/workspace", json={"workspace": "own"})

    @classmethod
    def tearDownClass(cls):
        cls.environment.stop()
        cls.temp.cleanup()

    def get(self, path: str, **params) -> dict:
        answer = self.client.get(path, params=params)
        self.assertEqual(answer.status_code, 200, answer.text)
        return answer.json()

    def past_items(self) -> list[dict]:
        first, _ = demo_span(self.today)
        return [item for item in self.get("/api/daily-items", start=first.isoformat(), end=self.today.isoformat())["items"]
                if item["date"] < self.today.isoformat()]

    # --- Protection --------------------------------------------------------------------------------------------------

    def test_the_users_own_files_are_byte_identical_and_never_opened_while_the_demo_is(self):
        self.assertEqual(self.after_demo, self.at_rest)
        own = str(self.own)
        self.assertEqual([path for path in self.opened if path.startswith(own) or f"{own.removesuffix('.sqlite3')}." in path], [])
        self.assertEqual(self.switches, [(False, None)])

    def test_back_in_their_own_workspace_avas_round_runs_on_the_users_own_data(self):
        self.assertEqual(self.condensed_on_return, [self.earlier.isoformat()])

    # --- Coverage ----------------------------------------------------------------------------------------------------

    def test_the_demo_spans_two_months_to_today_with_two_weeks_planned_ahead(self):
        first, _ = demo_span(self.today)
        self.assertEqual(self.store.first_record_date(), first.isoformat())
        ahead = self.get("/api/daily-items", start=(self.today + timedelta(days=1)).isoformat(),
                         end=(self.today + timedelta(days=PLANNED_AHEAD_DAYS)).isoformat())["items"]
        self.assertGreaterEqual(len(ahead), 8)
        self.assertGreater(max(item["date"] for item in ahead), (self.today + timedelta(days=PLANNED_AHEAD_DAYS - 5)).isoformat())

    def test_today_has_its_tasks_plans_to_compare_energy_ava_and_yesterdays_catch_up(self):
        day = self.get("/api/bootstrap", date=self.today.isoformat())
        self.assertGreaterEqual(len(day["dayItems"]), 5)
        self.assertEqual((len(day["variants"]), day["confirmedVariantId"]), (3, None))
        self.assertTrue(day["energyReadings"])
        self.assertTrue(day["yesterdayNotice"] and day["yesterdayNotice"]["tasks"])
        self.assertIn("folder-check", {notice["kind"] for notice in day["notices"]})
        self.assertGreaterEqual(len({message["created_at"][:10] for message in day["messages"]}), 5)
        self.assertTrue(day["demoMode"])

    def test_today_reads_as_a_real_persons_up_to_the_moment_the_demo_was_made(self):
        today = [item for item in self.get("/api/bootstrap", date=self.today.isoformat())["dayItems"] if item["id"] != self.reported]
        at = lambda clock, minutes=0: datetime.combine(self.today, datetime.strptime(clock, "%H:%M").time()) + timedelta(minutes=minutes)  # noqa: E731
        timed = [item for item in today if item["start_time"]]
        ended = [item for item in timed if at(item["start_time"], item["duration_minutes"]) <= self.made_from]
        later = [item for item in timed if at(item["start_time"]) >= self.made_by]
        self.assertEqual([item["title"] for item in ended if item["completion_status"] == "planned"], [], "each ended task reported")
        self.assertEqual([item["title"] for item in later if item["completion_status"] != "planned"], [], "nothing reported ahead")
        self.assertEqual([item["title"] for item in today if item["noReply"] or item["limitStopped"]], [],
                         "today's tasks are never left as no reply or stopped at their limit")
        statuses = collections.Counter(item["completion_status"] for item in ended)
        self.assertGreaterEqual(statuses["done"], sum(statuses.values()) / 2)

    def test_odd_states_are_a_handful_each_and_most_tasks_get_a_prompt_status(self):
        items = self.past_items()
        statuses = collections.Counter(item["completion_status"] for item in items)
        self.assertGreaterEqual(statuses["done"] / len(items), 0.65, statuses)
        self.assertTrue(2 <= self.get("/api/patterns", date=self.today.isoformat(), period="all")["toCheck"] <= 6)
        self.assertTrue(1 <= sum(item["noReply"] for item in items) <= 5)
        self.assertTrue(2 <= len(self.get("/api/bootstrap", date=self.today.isoformat())["yesterdayNotice"]["tasks"]) <= 3)
        with self.store.connect() as connection:
            # Today's pause is the one use_the_demo made.
            self.assertEqual(connection.execute("SELECT COUNT(DISTINCT pause_date) FROM day_pauses WHERE pause_date < ?",
                                                (self.today.isoformat(),)).fetchone()[0], 2)

    def test_every_status_a_task_can_have(self):
        items = self.past_items()
        statuses = collections.Counter(item["completion_status"] for item in items)
        self.assertTrue(all(statuses[status] >= 3 for status in ("done", "partial", "skipped")), statuses)
        self.assertTrue(any(item["noReply"] for item in items))
        self.assertTrue(any(item["dayPaused"] for item in items))
        self.assertTrue(any(item["completion_status"] == "skipped" and item["statusAt"] == "24:00" for item in items))
        self.assertGreater(self.get("/api/patterns", date=self.today.isoformat(), period="all")["toCheck"], 0)
        self.assertTrue(any(item["actualMinutes"] and item["actualMinutes"] > item["duration_minutes"] for item in items))
        self.assertTrue(any(item["actualMinutes"] and item["actualMinutes"] < item["duration_minutes"] for item in items))

    def test_every_kind_of_task_and_repeat(self):
        items = self.past_items()
        kinds = {(item["constraint_kind"], item["repeatKind"]) for item in items}
        self.assertLessEqual({("fixed", "weekly"), ("flexible", "daily"), ("flexible", "none"), ("fixed", "none")}, kinds)
        journaling = [item["date"] for item in items if item["title"] == "Evening journaling"]
        self.assertTrue(journaling and max(journaling) < (self.today - timedelta(days=30)).isoformat(), "a repeat stopped")
        self.assertTrue(any(item["title"] == "Call the landlord" for item in items), "a task added through Ava")
        self.assertTrue(any(item["ruleBreaks"] for item in items), "a task placed by hand against a rule")
        self.assertTrue(self.get("/api/areas/work", date=self.today.isoformat())["carryOvers"])

    def test_plans_energy_and_pauses_across_the_days(self):
        month = (self.today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        days = self.get("/api/calendar", month=month)["days"]
        self.assertTrue(all(day["entryCount"] for day in days))
        set_plans = [day["confirmed"] for day in days]
        self.assertTrue(any(set_plans) and not all(set_plans))
        self.assertGreater(sum(day["energy"] is not None for day in days), len(days) // 2)
        with self.store.connect() as connection:
            self.assertGreaterEqual(connection.execute("SELECT COUNT(DISTINCT pause_date) FROM day_pauses").fetchone()[0], 2)

    def test_every_area_page_has_something_on_every_card(self):
        learning = self.get("/api/areas/learning", date=self.today.isoformat())
        self.assertEqual({subject["status"] for subject in learning["subjects"]}, {"active", "paused"})
        self.assertEqual(learning["patterns"]["repeating"]["state"], "ready")
        self.assertEqual(learning["patterns"]["pace"]["state"], "ready")
        self.assertIsNotNone(learning["lastPractised"])
        life = self.get("/api/areas/life", date=self.today.isoformat())
        self.assertTrue(life["habits"] and life["energyWeek"])
        self.assertEqual(life["patterns"]["repeating"]["state"], "ready")
        work = self.get("/api/areas/work", date=self.today.isoformat())
        self.assertTrue(work["plannedMinutes"] and work["meetings"] and work["carryOvers"])
        project = self.get("/api/areas/project", date=self.today.isoformat())
        self.assertEqual({entry["health"] for entry in project["projects"]}, {"on-track", "stalled", "no-steps", "paused"})
        self.assertTrue(project["nextSteps"] and project["recentDone"])

    def test_the_learn_goals_one_paused_one_all_done_one_with_many_sessions(self):
        goals = {goal["title"]: goal for goal in self.get("/api/bootstrap", date=self.today.isoformat())["goals"]}
        self.assertEqual(goals["Statistics refresher"]["status"], "paused")
        systems = goals["Read Thinking in Systems"]
        self.assertEqual(systems["doneCount"], systems["itemCount"])
        self.assertGreaterEqual(goals["Spanish to B1"]["doneCount"], 20)
        self.assertEqual(goals["Restore the old bike"]["status"], "paused")

    def test_patterns_have_figures_on_every_graph(self):
        patterns = self.get("/api/patterns", date=self.today.isoformat(), period="all")
        for graph in ("bestHours", "energy", "plannedActual", "estimates", "outcome", "reporting"):
            self.assertEqual(patterns[graph]["state"], "ready", graph)
        self.assertGreaterEqual(len(patterns["columns"]), 3)

    def test_reports_over_every_period_with_advice_dismissed_and_raised_again(self):
        reports = self.client.post("/api/summaries", params={"date": self.today.isoformat()}).json()["reports"]
        self.assertGreaterEqual(len(reports["all"]["sections"]), 3)
        self.assertTrue(reports["week"]["recordedDays"] and reports["month"]["recordedDays"])
        with self.store.connect() as connection:
            self.assertTrue(connection.execute("SELECT 1 FROM suggestion_pool WHERE status = 'discarded'").fetchone())
            self.assertTrue(connection.execute("SELECT 1 FROM suggestion_notices").fetchone())
            self.assertGreaterEqual(connection.execute("SELECT COUNT(*) FROM summary_reports").fetchone()[0], 8)

    def test_the_library_holds_a_folder_notes_an_import_a_website_and_files_tasks_use(self):
        library = self.get("/api/knowledge")
        sources = {source["title"]: source for source in library["sources"]}
        self.assertEqual([(folder["title"], folder["found"]) for folder in library["folders"]], [("Study notes", True)])
        self.assertNotIn("Receipt", sources)
        self.assertIn("Scanned worksheet", sources)
        self.assertGreaterEqual(sum(source["origin"] == "folder" for source in sources.values()), 13)
        self.assertGreaterEqual(sum(source["origin"] == "note" for source in sources.values()), 2)
        self.assertTrue(any(source["origin"] == "file" and source["originalPath"] for source in sources.values()))
        self.assertTrue(sources["Irregular Spanish verbs"]["lookedUp"])
        self.assertGreaterEqual(sum(bool(source["tasks"]) for source in sources.values()), 5)
        self.assertTrue((self.data / DEMO_FOLDER / LIBRARY_FOLDER / "Spanish" / "Verb tables.pdf").is_file())

    def test_memory_has_notes_in_every_area_rules_of_each_kind_one_past_and_a_dismissed_offer(self):
        memory = self.get("/api/memory")
        self.assertEqual({rule["ruleKind"] for rule in memory["rules"]}, {"keep-free", "keep-off", "finish-by"})
        self.assertEqual({note["area"] for note in memory["notes"]}, {"learning", "life", "work", "project", "general"})
        self.assertTrue(any(note["endsOn"] for note in memory["notes"]))
        self.assertTrue(memory["past"])
        with self.store.connect() as connection:
            self.assertTrue(connection.execute("SELECT 1 FROM memory_dismissed").fetchone())

    def test_a_week_of_conversation_and_a_summary_for_each_earlier_day_talked_on(self):
        window = (self.today - timedelta(days=6)).isoformat()
        with self.store.connect() as connection:
            said = [row[0] for row in connection.execute("SELECT created_at FROM conversation_messages")]
            summaries = [row[0] for row in connection.execute("SELECT day FROM day_summaries")]
        self.assertTrue(said)
        self.assertGreaterEqual(len(summaries), 6)
        self.assertTrue(any(day < window for day in summaries))

    def test_the_menu_bar_title_says_demo_in_the_language_chosen_in_the_users_own_workspace(self):
        self.assertTrue(self.client.get("/api/now/title").text.startswith("演示"))

    def test_what_the_user_does_in_the_demo_is_kept_when_it_opens_again(self):
        with patch.dict(os.environ, {DEMO_VARIABLE: "1"}):
            again = TestClient(create_app(gateway=FakeGateway(), embedding_gateway=FakeEmbeddingGateway(), day_jobs=False))
        titles = {source["title"] for source in again.get("/api/knowledge").json()["sources"]}
        self.assertIn("Demo note", titles)


class DeterminismTests(unittest.TestCase):
    def test_the_same_day_makes_the_same_demo(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {DATABASE_VARIABLE: f"{folder}/own.sqlite3"}):
            made = []
            for name in ("one", "two"):
                database = Path(folder) / name / DEMO_FOLDER / "daywright.sqlite3"
                build_demo(database, date(2026, 10, 28))
                made.append(database)
            self.assertEqual(dump(made[0]), dump(made[1]))
            files = [{str(path.relative_to(database.parent)): path.read_bytes()
                      for path in sorted((database.parent / LIBRARY_FOLDER).rglob("*")) if path.is_file()} for database in made]
            self.assertEqual(files[0], files[1])


class OtherEndDatesTests(unittest.TestCase):
    """Reset makes the demo end on whatever day it is: days that once failed, as the script's days fell on other
    weekdays, still make a whole demo."""

    def test_a_demo_ending_on_other_days_is_made_whole(self):
        for end in (date(2026, 10, 13), date(2026, 12, 31)):
            with self.subTest(end=end), tempfile.TemporaryDirectory() as folder, \
                    patch.dict(os.environ, {DATABASE_VARIABLE: f"{folder}/own.sqlite3"}):
                database = Path(folder) / DEMO_FOLDER / "daywright.sqlite3"
                build_demo(database, end)
                with sqlite3.connect(database) as connection:
                    count = lambda query, *values: connection.execute(query, values).fetchone()[0]  # noqa: E731
                    self.assertGreater(count("SELECT COUNT(*) FROM suggestion_notices"), 0)
                    self.assertEqual(count("SELECT COUNT(DISTINCT pause_date) FROM day_pauses"), 2)
                    self.assertEqual(count("""SELECT COUNT(*) FROM daily_items
                                              WHERE repeat_kind != 'none' AND repeat_series_id IS NULL"""), 0)
                    self.assertGreaterEqual(count("SELECT COUNT(*) FROM daily_items WHERE item_date > ?", end.isoformat()), 8)
                    # Made at MADE_AT, 18:00: today's timed tasks that ended by then are reported, those after it wait.
                    today = connection.execute(
                        """SELECT start_time, duration_minutes, completion_status FROM daily_items
                           WHERE item_date = ? AND start_time IS NOT NULL AND acceptance = 'accepted'""",
                        (end.isoformat(),)).fetchall()
                    at = lambda start, minutes=0: datetime.combine(  # noqa: E731
                        end, datetime.strptime(start, "%H:%M").time()) + timedelta(minutes=minutes)
                    made = datetime.combine(end, MADE_AT)
                    self.assertTrue(today)
                    self.assertTrue(all(status != "planned" for start, minutes, status in today if at(start, minutes) <= made))
                    self.assertTrue(all(status == "planned" for start, _, status in today if at(start) >= made))


if __name__ == "__main__":
    unittest.main()
