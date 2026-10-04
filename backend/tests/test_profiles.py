import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.database import Database
from backend.app.profiles import task_profile


def record(day, status, minutes=45, own=None, start=None, yours=True):
    return {"date": day, "start": start, "minutes": minutes, "ownMinutes": own or minutes, "status": status,
            "yours": yours}


def statuses(*names):
    return [record(f"2026-09-{day:02d}", name) for day, name in enumerate(names, 1)]


class TaskProfileTests(unittest.TestCase):
    def test_a_profile_counts_every_report_and_keeps_the_latest_six(self):
        profile = task_profile(statuses("done", "partial", "skipped", "done", "done", "partial", "done", "planned"))
        self.assertEqual((profile["scheduled"], profile["done"], profile["partial"], profile["skipped"],
                          profile["unreported"]), (8, 4, 2, 1, 1))
        self.assertEqual(profile["recent"], ["partial", "skipped", "done", "done", "partial", "done"])
        self.assertEqual((profile["firstDate"], profile["lastDate"]), ("2026-09-01", "2026-09-08"))

    def test_the_trend_says_whether_a_task_is_slipping_improving_or_steady(self):
        self.assertEqual(task_profile(statuses("done", "done", "done", "skipped", "partial", "done"))["trend"], "slipping")
        self.assertEqual(task_profile(statuses("skipped", "partial", "skipped", "done", "done", "done"))["trend"],
                         "improving")
        self.assertEqual(task_profile(statuses("done", "partial", "done", "done", "skipped", "done"))["trend"], "steady")
        self.assertIsNone(task_profile(statuses("done", "skipped", "done"))["trend"])

    def test_a_profile_knows_its_usual_length_and_how_plans_and_you_changed_it(self):
        profile = task_profile([record("2026-09-01", "done", 45), record("2026-09-02", "done", 30, own=45),
                                record("2026-09-03", "partial", 60, own=45), record("2026-09-04", "done", 50)])
        self.assertEqual((profile["usualMinutes"], profile["lastMinutes"]), (48, 50))
        self.assertEqual((profile["lengthened"], profile["shortened"]), (1, 1))
        self.assertEqual(profile["lengthChanges"], 1)

    def test_a_profile_knows_the_lengths_at_which_a_task_was_done_and_left_partly_done(self):
        profile = task_profile([record("2026-09-01", "done", 60), record("2026-09-02", "partial", 30),
                                record("2026-09-03", "done", 75), record("2026-09-04", "partial", 45)])
        self.assertEqual((profile["doneMinutes"], profile["partialMinutes"]), (68, 38))
        self.assertEqual(task_profile(statuses("skipped"))["doneMinutes"], None)

    def test_only_lengths_you_set_count_as_changes_and_each_change_counts(self):
        profile = task_profile([record("2026-09-01", "done", 30), record("2026-09-02", "done", 45),
                                record("2026-09-03", "done", 30), record("2026-09-04", "done", 50, yours=False),
                                record("2026-09-05", "done", 40, yours=False)])
        self.assertEqual(profile["lengthChanges"], 2)

    def test_a_profile_knows_when_and_on_which_weekday_a_task_is_usually_done(self):
        mondays = [date(2026, 9, 7) + timedelta(weeks=week) for week in range(3)]
        records = [record(day.isoformat(), "done", start=start) for day, start in zip(mondays, ("09:00", "09:30", "09:15"))]
        profile = task_profile([*records, record("2026-09-08", "done", start="09:15")])
        self.assertEqual(profile["usualStart"], "09:15")
        self.assertEqual(profile["usualWeekday"], 0)
        scattered = task_profile([record("2026-09-01", "done", start="08:00"), record("2026-09-02", "done", start="15:00")])
        self.assertIsNone(scattered["usualStart"])

    def test_a_profile_counts_how_often_you_asked_for_the_task_to_be_shorter(self):
        self.assertEqual(task_profile([record("2026-09-01", "done")], shorten_requests=3)["shortenRequests"], 3)


def task(title, day, domain="learning", minutes=45, start=None, status="planned"):
    return {"date": day, "title": title, "detail": "", "domain": domain, "startTime": start, "durationMinutes": minutes,
            "constraintKind": "fixed" if start else "flexible", "repeatKind": "none",
            "goalId": None, "status": status}


class StoredProfileTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "profiles.sqlite3"
        self.store = Database(self.path)
        self.today = date.today()

    def past(self, title, days_ago, status, domain="learning"):
        """Past days are read-only through the store, so an earlier task is written there directly."""
        item = self.store.create_daily_item(task(title, self.today.isoformat(), domain))
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE daily_items SET item_date = ?, completion_status = ? WHERE id = ?",
                               ((self.today - timedelta(days=days_ago)).isoformat(), status, item["id"]))

    def test_profiles_cover_every_past_day_and_merge_a_title_however_it_is_written(self):
        for days_ago, status in ((400, "done"), (90, "skipped"), (2, "done")):
            self.past("Read chapter", days_ago, status)
        self.past("read chapter ", 1, "partial")
        self.store.rebuild_task_profiles()
        profile = self.store.task_profiles()[("learning", "read chapter")]
        self.assertEqual((profile["scheduled"], profile["done"], profile["skipped"], profile["partial"]), (4, 2, 1, 1))
        self.assertEqual(profile["firstDate"], (self.today - timedelta(days=400)).isoformat())

    def test_a_task_still_planned_today_is_not_history_yet_but_a_reported_one_is(self):
        self.store.create_daily_item(task("Walk", self.today.isoformat(), "life"))
        reported = self.store.create_daily_item(task("Stretch", self.today.isoformat(), "life"))
        self.store.update_daily_item(reported["id"], task("Stretch", self.today.isoformat(), "life", status="done"))
        self.store.rebuild_task_profiles()
        profiles = self.store.task_profiles()
        self.assertNotIn(("life", "walk"), profiles)
        self.assertEqual(profiles[("life", "stretch")]["done"], 1)

    def test_lengths_an_agent_estimated_are_not_counted_as_your_changes(self):
        for days_ago, minutes in ((3, 30), (2, 60), (1, 30)):
            item = self.store.create_daily_item(task("Essay", self.today.isoformat(), "project", minutes=None))
            with sqlite3.connect(self.path) as connection:
                connection.execute("UPDATE daily_items SET item_date = ?, duration_minutes = ?, completion_status = 'done' "
                                   "WHERE id = ?", ((self.today - timedelta(days=days_ago)).isoformat(), minutes, item["id"]))
        self.store.rebuild_task_profiles()
        self.assertEqual(self.store.task_profiles()[("project", "essay")]["lengthChanges"], 0)

    def test_requests_to_shorten_add_up_however_the_title_is_written(self):
        self.past("Read chapter", 1, "done")
        with sqlite3.connect(self.path) as connection:
            connection.executemany("INSERT INTO feedback_signals VALUES (?, 'message', '2026-10-01', ?, 'learning', "
                                   "'shorten', '2026-10-01')", [("one", "Read chapter"), ("two", "read chapter ")])
        self.store.rebuild_task_profiles()
        self.assertEqual(self.store.task_profiles()[("learning", "read chapter")]["shortenRequests"], 2)

    def test_a_profile_is_kept_in_the_database_between_launches(self):
        self.past("Essay", 3, "done", "project")
        self.store.rebuild_task_profiles()
        self.assertEqual(Database(self.path).task_profiles()[("project", "essay")]["done"], 1)


if __name__ == "__main__":
    unittest.main()
