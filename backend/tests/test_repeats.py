import sqlite3
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.agents import AgentOrchestrator
from backend.app.database import Database
from backend.tests.test_meals import MealDay


def days_ago(count):
    return (date.today() - timedelta(days=count)).isoformat()


class SeriesDay(MealDay):
    """A fresh account with helpers that write a repeat's days directly, as history is written."""

    def repeat_day(self, title, day, repeat="daily", series=None, status="done", start="07:00", goal=None,
                   domain="life"):
        """Record one day of a repeating task directly, as history is written; return its id."""
        item_id = f"{title}:{day}:{repeat}"
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """INSERT INTO daily_items (id, item_date, goal_id, title, domain, start_time, duration_minutes,
                       constraint_kind, repeat_kind, repeat_series_id, completion_status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 30, 'fixed', ?, ?, ?, ?)""",
                (item_id, day, goal, title, domain, start, repeat, series, status, day))
        return item_id

    def prepared(self, first, last):
        report = AgentOrchestrator().summary_report("week", "synthetic-week", self.store.summary_facts(first, last))
        return report, AgentOrchestrator().prepare_future_from_summary(self.store, report)


class RepeatSeriesTests(SeriesDay):
    """A repeat's days are linked as one series, copied forward by link, not by name."""

    def test_existing_repeating_records_get_their_series_from_name_and_area(self):
        with sqlite3.connect(self.path) as connection:
            connection.execute("DROP INDEX IF EXISTS daily_items_by_series")
            connection.execute("ALTER TABLE daily_items DROP COLUMN repeat_series_id")
            for item_id, day, title, domain, repeat in (
                    ("a", days_ago(3), "Stretch", "life", "daily"), ("b", days_ago(2), " stretch", "life", "daily"),
                    ("c", days_ago(2), "Stretch", "learning", "weekly"), ("d", days_ago(1), "Stretch", "life", "none")):
                connection.execute(
                    """INSERT INTO daily_items (id, item_date, title, domain, start_time, duration_minutes,
                           constraint_kind, repeat_kind, created_at) VALUES (?, ?, ?, ?, '07:00', 30, 'fixed', ?, ?)""",
                    (item_id, day, title, domain, repeat, day))

        store = Database(self.path)

        with sqlite3.connect(self.path) as connection:
            series = dict(connection.execute("SELECT id, repeat_series_id FROM daily_items"))
        self.assertEqual(series, {"a": "a", "b": "a", "c": "c", "d": None})
        self.assertTrue(store.daily_item("a"))

    def test_a_new_repeating_task_starts_a_series_and_a_one_off_has_none(self):
        daily = self.client.post("/api/daily-items", json={**self.task("Stretch", "07:30", 30), "repeatKind": "daily"}).json()
        once = self.client.post("/api/daily-items", json=self.task("Call", "15:00", 30)).json()

        self.assertEqual((daily["repeatSeriesId"], once["repeatSeriesId"]), (daily["id"], None))

    def test_a_renamed_day_stays_in_its_series_and_the_next_day_copies_it(self):
        first = self.repeat_day("Stretch", days_ago(2), series="series-1")
        self.repeat_day("Morning stretch", days_ago(1), series="series-1")

        report, prepared = self.prepared(days_ago(2), days_ago(1))

        self.assertEqual([(entry["taskTitle"], entry["doneDays"]) for entry in report["completedRecurring"]],
                         [("Morning stretch", 2)])
        self.assertEqual([(item["title"], item["date"], item["repeatSeriesId"]) for item in prepared],
                         [("Morning stretch", self.tomorrow, "series-1")])
        self.assertTrue(first)

    def test_a_day_that_doesnt_repeat_stops_the_series(self):
        self.repeat_day("Stretch", days_ago(3), series="series-1")
        self.repeat_day("Stretch", days_ago(2), series="series-1")
        self.repeat_day("Stretch", days_ago(1), repeat="none", series="series-1")

        _, prepared = self.prepared(days_ago(3), days_ago(1))

        self.assertEqual(prepared, [])

    def test_a_day_that_says_weekly_continues_weekly_on_its_weekday(self):
        self.repeat_day("Swim", days_ago(9), series="series-1")
        self.repeat_day("Swim", days_ago(2), repeat="weekly", series="series-1")

        _, prepared = self.prepared(days_ago(9), days_ago(2))

        self.assertEqual([item["date"] for item in prepared], [days_ago(-5)])

    def test_a_paused_goals_series_is_not_copied_forward(self):
        goal = self.store.create_goal("Mornings", "life")
        self.repeat_day("Stretch", days_ago(2), series="series-1", goal=goal["id"])
        self.repeat_day("Stretch", days_ago(1), series="series-1", goal=goal["id"])
        self.store.update_goal(goal["id"], "Mornings", "paused")

        report, prepared = self.prepared(days_ago(2), days_ago(1))

        self.assertEqual((report["completedRecurring"], prepared), ([], []))


class RepeatFromPastDayTests(SeriesDay):
    """A repeat changed from a past day applies from today on; earlier days stay as they were."""

    def chat(self, day, message):
        return self.client.post("/api/chat", json={"date": day, "message": message}).json()

    def confirm(self, action):
        decided = self.client.post(f"/api/actions/{action['id']}", json={"decision": "confirmed"})
        self.assertEqual(decided.status_code, 200, decided.text)
        return decided.json()

    def rows(self, series):
        with sqlite3.connect(self.path) as connection:
            return {day: (title, repeat) for day, title, repeat in connection.execute(
                "SELECT item_date, title, repeat_kind FROM daily_items WHERE repeat_series_id = ?", (series,))}

    def stretch_days(self):
        """Stretch, daily: done yesterday, still to do today, and prepared for tomorrow."""
        self.repeat_day("Stretch", days_ago(1), series="series-1")
        today = self.repeat_day("Stretch", self.today, series="series-1", status="planned", start="07:30")
        self.repeat_day("Stretch", self.tomorrow, series="series-1", status="planned", start="07:30")
        return today

    def test_starting_a_repeat_from_a_past_day_begins_today_and_leaves_earlier_days(self):
        read = self.repeat_day("Read", days_ago(3), repeat="none", start="16:00")

        action = self.chat(days_ago(3), "Make Read repeat daily")["proposedAction"]

        self.assertEqual((action["actionType"], action["payload"]["mode"], action["payload"]["startsOn"]),
                         ("repeat_item", "start", self.today))
        self.assertIn(f"Propose repeating “Read” daily from {self.today}; earlier days stay as they were.", action["explanation"])
        self.confirm(action)
        with sqlite3.connect(self.path) as connection:
            days = dict(connection.execute("SELECT item_date, repeat_kind FROM daily_items WHERE title = 'Read'"))
            series = connection.execute("SELECT id, repeat_series_id FROM daily_items WHERE item_date = ?", (self.today,)).fetchone()
        self.assertEqual(days, {days_ago(3): "none", self.today: "daily"})
        self.assertEqual(series[0], series[1])
        self.assertTrue(read)

    def test_a_repeat_with_no_time_left_today_starts_tomorrow(self):
        self.repeat_day("Read", days_ago(3), repeat="none", start="06:00")

        action = self.chat(days_ago(3), "Make Read repeat daily")["proposedAction"]

        self.assertEqual(action["payload"]["startsOn"], self.tomorrow)

    def test_a_weekly_repeat_starts_on_the_next_matching_weekday(self):
        self.repeat_day("Read", days_ago(3), repeat="none", start="16:00")

        action = self.chat(days_ago(3), "Make Read repeat weekly")["proposedAction"]

        self.assertEqual(action["payload"]["startsOn"], days_ago(-4))

    def test_stopping_a_repeat_from_a_past_day_deletes_its_unreported_days_from_today(self):
        self.stretch_days()
        self.client.post("/api/plan/generate", json={"date": self.today})
        action = self.chat(days_ago(1), "Stop repeating Stretch")["proposedAction"]

        with patch.object(AgentOrchestrator, "relay_task_change") as relay:
            self.confirm(action)

        self.assertEqual((action["payload"]["mode"], action["payload"]["startsOn"]), ("stop", self.today))
        self.assertEqual(action["payload"]["removes"], [self.today, self.tomorrow])
        self.assertIn(f"Its days still to do on {self.today} and {self.tomorrow} are removed.", action["explanation"])
        self.assertEqual(self.rows("series-1"), {days_ago(1): ("Stretch", "daily")})
        drafts = self.client.get("/api/bootstrap", params={"date": self.today}).json()["variants"]
        self.assertFalse([note for variant in drafts for note in variant["notes"] if "Stretch" in note["text"]])
        told = {day for call in relay.call_args_list for day in call.args[1] if day}
        self.assertLessEqual({self.today, self.tomorrow}, told)

    def test_stopping_when_todays_day_was_reported_keeps_it_and_deletes_later_ones(self):
        today = self.stretch_days()
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE daily_items SET completion_status = 'done' WHERE id = ?", (today,))

        action = self.chat(days_ago(1), "Stop repeating Stretch")["proposedAction"]
        self.confirm(action)

        self.assertEqual(action["payload"]["startsOn"], self.tomorrow)
        self.assertEqual(self.rows("series-1"), {days_ago(1): ("Stretch", "daily"), self.today: ("Stretch", "daily")})
        _, prepared = self.prepared(days_ago(1), self.today)
        self.assertEqual(prepared, [])

    def test_stopping_when_todays_set_plan_scheduled_its_day_keeps_it_and_deletes_later_ones(self):
        self.stretch_days()
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": plan["variants"][0]["id"]})

        action = self.chat(days_ago(1), "Stop repeating Stretch")["proposedAction"]
        self.confirm(action)

        self.assertEqual(action["payload"]["startsOn"], self.tomorrow)
        self.assertEqual(self.rows("series-1"), {days_ago(1): ("Stretch", "daily"), self.today: ("Stretch", "daily")})

    def test_switching_daily_to_weekly_keeps_only_the_weekly_days_unreported_copy(self):
        self.stretch_days()
        self.repeat_day("Stretch", days_ago(-6), series="series-1", status="planned", start="07:30")

        self.confirm(self.chat(days_ago(1), "Repeat Stretch weekly")["proposedAction"])

        self.assertEqual(self.rows("series-1"), {days_ago(1): ("Stretch", "daily"), days_ago(-6): ("Stretch", "weekly")})

    def test_after_switching_to_weekly_the_next_day_is_prepared_on_the_past_tasks_weekday(self):
        for ago in (3, 2, 1):
            self.repeat_day("Stretch", days_ago(ago), series="series-1")

        self.confirm(self.chat(days_ago(3), "Repeat Stretch weekly")["proposedAction"])
        _, prepared = self.prepared(days_ago(3), self.today)

        self.assertEqual([item["date"] for item in prepared], [days_ago(-4)])

    def test_switching_weekly_to_daily_keeps_every_copy(self):
        self.repeat_day("Stretch", days_ago(7), repeat="weekly", series="series-1")
        self.repeat_day("Stretch", self.today, repeat="weekly", series="series-1", status="planned", start="07:30")

        action = self.chat(days_ago(7), "Repeat Stretch daily")["proposedAction"]
        self.confirm(action)

        self.assertEqual(action["payload"]["removes"], [])
        self.assertNotIn("removed", action["explanation"])
        self.assertEqual(self.rows("series-1"), {days_ago(7): ("Stretch", "weekly"), self.today: ("Stretch", "daily")})

    def test_renaming_a_repeating_past_day_asks_whether_the_repeat_changes_too(self):
        self.stretch_days()

        reply = self.chat(days_ago(1), "Rename Stretch to Morning stretch")

        self.assertIsNone(reply["proposedAction"])
        self.assertIn("clarify-repeat-scope", [notice["kind"] for notice in reply["notices"]])

    def test_just_that_day_renames_that_day_alone(self):
        self.stretch_days()
        self.chat(days_ago(1), "Rename Stretch to Morning stretch")

        action = self.chat(days_ago(1), "Just that day")["proposedAction"]

        self.assertEqual((action["payload"]["changes"], action["payload"]["days"]), ({"title": "Morning stretch"}, [days_ago(1)]))
        self.confirm(action)
        self.assertEqual(self.rows("series-1"), {days_ago(1): ("Morning stretch", "daily"), self.today: ("Stretch", "daily"),
                                                 self.tomorrow: ("Stretch", "daily")})

    def test_that_day_and_the_repeat_renames_from_today_on_and_no_other_past_day(self):
        self.repeat_day("Stretch", days_ago(2), series="series-1")
        self.stretch_days()

        action = self.chat(days_ago(1), "Rename Stretch to Morning stretch, and the repeat from today on")["proposedAction"]

        self.assertEqual(action["payload"]["days"], [days_ago(1), self.today, self.tomorrow])
        self.confirm(action)
        self.assertEqual(self.rows("series-1"), {
            days_ago(2): ("Stretch", "daily"), days_ago(1): ("Morning stretch", "daily"),
            self.today: ("Morning stretch", "daily"), self.tomorrow: ("Morning stretch", "daily")})


if __name__ == "__main__":
    unittest.main()
