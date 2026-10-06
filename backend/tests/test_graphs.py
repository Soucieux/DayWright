import sqlite3
import unittest
from datetime import date, timedelta

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.periods import period_keys
from backend.tests.test_area_overviews import AreaDay
from backend.tests.test_repeats import days_ago


class GraphDay(AreaDay):
    """A fresh account with a set plan whose entries can be done, skipped, removed or moved on."""

    def set_plan(self, day, entries):
        """Set a plan on `day` with `entries`: (title, domain, minutes, status, removed, moved_to)."""
        with sqlite3.connect(self.path) as connection:
            connection.execute("INSERT INTO plan_sets (id, plan_date, source, created_at) VALUES (?, ?, 'test', ?)",
                               (f"set:{day}", day, day))
            connection.execute("""INSERT INTO plan_variants (id, plan_set_id, name, slug, rationale, created_at)
                                  VALUES (?, ?, 'Balanced', 'balanced', '', ?)""", (f"plan:{day}", f"set:{day}", day))
            connection.execute("INSERT INTO daily_confirmations (plan_date, variant_id, confirmed_at) VALUES (?, ?, ?)",
                               (day, f"plan:{day}", day))
            for position, (title, domain, minutes, status, removed, moved_to) in enumerate(entries):
                connection.execute(
                    """INSERT INTO plan_entries (id, variant_id, position, start_time, title, detail, domain,
                           duration_minutes, constraint_kind, completion_status, removed_at, moved_to)
                       VALUES (?, ?, ?, '09:00', ?, '', ?, ?, 'flexible', ?, ?, ?)""",
                    (f"entry:{day}:{title}", f"plan:{day}", position, title, domain, minutes, status,
                     day if removed else None, moved_to))

    def a_week(self):
        """Two days ago without a plan, yesterday with one, and a task of a paused goal still to do today."""
        self.task_on("Report", days_ago(2), "work", "done", minutes=60)
        self.task_on("Read", days_ago(2), "learning", "done", minutes=45)
        self.task_on("Walk", days_ago(2), "life", "partial", minutes=30)
        self.task_on("Laundry", days_ago(2), "life", "planned", minutes=30)
        # A day with a set plan counts its entries, not its tasks.
        self.task_on("Ignored", days_ago(1), "work", "done", minutes=120)
        self.set_plan(days_ago(1), [("Memo", "work", 90, "done", False, None),
                                    ("Tiles", "project", 30, "skipped", False, None),
                                    ("Notes", "learning", 30, "partial", False, None),
                                    ("Gone", "life", 30, "done", True, None),
                                    ("Email", "work", 30, "planned", True, self.today)])
        paused = self.goal("Website", "project", status="paused")
        self.task_on("Sketch", self.today, "project", "planned", paused)
        self.task_on("Email", self.today, "work", "done", minutes=30)


class ReportGraphsTests(GraphDay):
    def test_each_day_counts_its_tasks_and_the_planned_time_fully_done_by_area(self):
        self.a_week()
        graphs = self.store.report_graphs(days_ago(2), self.today)

        self.assertEqual(graphs["days"], [
            {"date": days_ago(2), "scheduled": 4, "done": 2, "minutes": {"work": 60, "learning": 45}},
            {"date": days_ago(1), "scheduled": 3, "done": 1, "minutes": {"work": 90}},
            {"date": self.today, "scheduled": 1, "done": 1, "minutes": {"work": 30}},
        ])

    def test_days_stop_at_today_and_a_day_with_nothing_counts_none(self):
        graphs = self.store.report_graphs(days_ago(1), (date.today() + timedelta(days=3)).isoformat())

        self.assertEqual(graphs["days"], [{"date": days_ago(1), "scheduled": 0, "done": 0, "minutes": {}},
                                          {"date": self.today, "scheduled": 0, "done": 0, "minutes": {}}])
        self.assertEqual(graphs["followThrough"], [])

    def test_the_counts_are_summarys_own(self):
        self.a_week()
        outcomes = self.store.summary_facts(days_ago(2), self.today)["dayOutcomes"]

        for day in self.store.report_graphs(days_ago(2), self.today)["days"]:
            self.assertEqual((day["scheduled"], day["done"]),
                             (sum(area["scheduled"] for area in outcomes[day["date"]].values()),
                              sum(area["done"] for area in outcomes[day["date"]].values())), day["date"])

    def test_follow_through_takes_each_set_plan_with_its_moved_entries_and_not_its_removed_ones(self):
        self.a_week()

        self.assertEqual(self.store.report_graphs(days_ago(2), self.today)["followThrough"], [
            {"date": days_ago(1), "done": 1, "partial": 1, "moved": 1, "skipped": 1, "unreported": 0}])

    def test_a_set_plan_today_counts_what_is_still_to_do_as_unreported(self):
        self.set_plan(self.today, [("Memo", "work", 60, "done", False, None), ("Read", "learning", 30, "planned", False, None)])

        self.assertEqual(self.store.report_graphs(self.today, self.today)["followThrough"], [
            {"date": self.today, "done": 1, "partial": 0, "moved": 0, "skipped": 0, "unreported": 1}])


class GraphsInReportsTests(GraphDay):
    def summaries(self, day=None):
        return self.client.post(f"/api/summaries?date={day or self.today}").json()["reports"]

    def test_day_week_and_month_reports_carry_their_graphs_and_all_time_none(self):
        self.a_week()
        reports = self.summaries()

        self.assertEqual([day["date"] for day in reports["day"]["graphs"]["days"]], [self.today])
        week_start = date.today() - timedelta(days=date.today().weekday())
        self.assertEqual((reports["week"]["graphs"]["start"], reports["week"]["graphs"]["end"]),
                         (week_start.isoformat(), (week_start + timedelta(days=6)).isoformat()),
                         "the period as asked, so the interface can show the days still to come")
        self.assertEqual(reports["week"]["graphs"]["days"][0]["date"], week_start.isoformat())
        self.assertEqual(reports["week"]["graphs"]["days"][-1]["date"], self.today)
        self.assertEqual(reports["month"]["graphs"]["days"][0]["date"], self.today[:8] + "01")
        self.assertNotIn("graphs", reports["all"])

    def test_a_report_saved_before_graphs_still_gets_them_fresh(self):
        last_week = date.today() - timedelta(days=7)
        key = dict(period_keys(last_week))["week"]
        self.store.save_summary("week", key, {"periodKind": "week", "periodKey": key, "domains": {}, "suggestions": [],
                                              "recordedDays": 0})
        self.task_on("Report", last_week.isoformat(), "work", "done", minutes=60)

        week = self.summaries(last_week.isoformat())["week"]

        self.assertEqual(week["recordedDays"], 0, "the saved report itself stays as saved")
        self.assertIn({"date": last_week.isoformat(), "scheduled": 1, "done": 1, "minutes": {"work": 60}},
                      week["graphs"]["days"])


class FinishingWeekTests(GraphDay):
    def finishing(self, day):
        return self.client.get(f"/api/bootstrap?date={day}").json()["finishingWeek"]

    def test_today_carries_the_seven_days_to_it(self):
        self.a_week()
        week = self.finishing(self.today)

        self.assertEqual([day["date"] for day in week], [days_ago(count) for count in range(6, -1, -1)])
        self.assertEqual(week[-3:], [{"date": days_ago(2), "scheduled": 4, "done": 2},
                                     {"date": days_ago(1), "scheduled": 3, "done": 1},
                                     {"date": self.today, "scheduled": 1, "done": 1}])

    def test_a_later_day_shows_none_after_today(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()

        self.assertEqual(self.finishing(tomorrow)[-1]["date"], self.today)
        self.assertEqual(len(self.finishing(tomorrow)), 6)


if __name__ == "__main__":
    unittest.main()
