import sqlite3
import unittest
from datetime import date, timedelta

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.estimates import refine_estimate
from backend.app.planner import clock_time, minutes_after_midnight
from backend.tests.test_time_record import TimeDay


def ago(days):
    return (date.today() - timedelta(days=days)).isoformat()


class Past(TimeDay):
    """Days already lived: each record with its status, its length that day and the time it took."""

    def past(self, title, days, status, minutes=60, taken=None, domain="learning", start="10:00", at=None):
        item_id = f"past:{title}:{days}:{start}"
        end = None if taken is None else clock_time(minutes_after_midnight(start) + taken)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """INSERT INTO daily_items (id, item_date, title, detail, domain, start_time, duration_minutes,
                       constraint_kind, completion_status, created_at, duration_source, status_at, actual_start,
                       actual_end)
                   VALUES (?, ?, ?, '', ?, ?, ?, 'fixed', ?, ?, 'user', ?, ?, ?)""",
                (item_id, ago(days), title, domain, start, minutes, status, f"{ago(days + 1)}T08:00:00+00:00",
                 at or end, None if taken is None else start, end))
        return item_id

    def estimate(self, title):
        made = self.store.create_daily_item({**self.task(title, None), "durationMinutes": None, "date": self.tomorrow})
        return made["duration_minutes"], made["estimateBasis"]

    def set_entry(self, title, day, start, status):
        with sqlite3.connect(self.path) as connection:
            if not connection.execute("SELECT 1 FROM plan_sets WHERE id = ?", (f"set:{day}",)).fetchone():
                connection.execute("INSERT INTO plan_sets (id, plan_date, source, created_at) VALUES (?, ?, 'test', ?)",
                                   (f"set:{day}", day, day))
                connection.execute("""INSERT INTO plan_variants (id, plan_set_id, name, slug, rationale, created_at)
                                      VALUES (?, ?, 'Balanced', 'balanced', '', ?)""", (f"plan:{day}", f"set:{day}", day))
                connection.execute("INSERT INTO daily_confirmations (plan_date, variant_id, confirmed_at) VALUES (?, ?, ?)",
                                   (day, f"plan:{day}", day))
            position = connection.execute("SELECT COUNT(*) FROM plan_entries WHERE variant_id = ?", (f"plan:{day}",)).fetchone()[0]
            connection.execute(
                """INSERT INTO plan_entries (id, variant_id, position, start_time, title, detail, domain, duration_minutes,
                       constraint_kind, completion_status) VALUES (?, ?, ?, ?, ?, '', 'learning', 60, 'flexible', ?)""",
                (f"entry:{title}:{day}", f"plan:{day}", position, start, title, status))


class EstimateTests(Past):
    def test_a_new_tasks_estimate_takes_the_time_its_done_days_took(self):
        self.past("Review", 3, "done", taken=80)
        self.past("Review", 2, "done", taken=70)
        self.assertEqual(self.estimate("Review"), (75, "taken"))

    def test_a_partly_done_day_only_raises_it(self):
        self.past("Review", 3, "done", taken=60)
        self.past("Review", 2, "partial", taken=90)
        self.assertEqual(self.estimate("Review"), (90, "taken"))
        self.past("Read", 3, "done", minutes=45, taken=45)
        self.past("Read", 2, "partial", minutes=45, taken=20)
        self.assertEqual(self.estimate("Read"), (45, "taken"))

    def test_skipped_and_unanswered_days_never_change_it(self):
        self.past("Plan", 4, "done", minutes=45, taken=45)
        self.past("Plan", 3, "skipped", minutes=45, taken=120)
        self.past("Plan", 2, "planned", minutes=45)
        self.assertEqual(self.estimate("Plan"), (45, "taken"))

    def test_the_local_model_never_replaces_an_estimate_from_the_time_a_task_took(self):
        self.past("Review", 2, "done", taken=80)
        made = self.store.create_daily_item({**self.task("Review", None), "durationMinutes": None, "date": self.tomorrow})

        class Answering:
            def reply(self, *args, **kwargs):
                return "20 minutes", "model"

        self.assertFalse(refine_estimate(self.store, Answering(), made["id"]))
        self.assertEqual(self.store.daily_item(made["id"])["duration_minutes"], 80)

    def test_a_time_over_twice_its_length_counts_only_once_you_confirm_it(self):
        flagged = self.past("Write", 3, "done", taken=200)
        self.assertEqual(self.estimate("Write"), (60, "history"))
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE daily_items SET time_confirmed = 1 WHERE id = ?", (flagged,))
        self.assertEqual(self.estimate("Write"), (200, "taken"))


class ProfileTests(Past):
    def test_profiles_take_the_time_done_and_partly_done_days_took_and_leave_out_times_to_check(self):
        self.past("Review", 4, "done", taken=200)
        self.past("Review", 3, "done", taken=80)
        self.past("Review", 2, "done", taken=90)
        self.past("Review", 1, "partial", taken=40)
        self.store.rebuild_task_profiles()
        profile = self.store.task_profiles()[("learning", "review")]
        self.assertEqual((profile["doneMinutes"], profile["partialMinutes"]), (85, 40))

    def test_tasks_often_skipped_or_left_unanswered_are_notes_on_their_area_and_in_summary(self):
        for days, status in ((3, "skipped"), (2, "skipped"), (1, "done")):
            self.past("Stretch", days, status)
        for days, status in ((3, "planned"), (2, "planned"), (1, "done")):
            self.past("Journal", days, status, start="16:00")
        self.add("Stretch", "14:00")
        self.add("Journal", "16:00")
        self.store.rebuild_task_profiles()
        notes = self.client.get("/api/areas/learning", params={"date": self.today}).json()["notes"]
        found = {(note["kind"], note["values"]["taskTitle"]) for note in notes}
        self.assertLessEqual({("often-skipped", "Stretch"), ("often-unanswered", "Journal")}, found)
        facts = self.store.summary_facts(ago(3), ago(1))
        self.assertEqual(facts["domains"]["learning"]["noReply"], 2)
        journal = next(outcome for outcome in facts["taskOutcomes"] if outcome["taskTitle"] == "Journal")
        self.assertEqual(journal["noReply"], 2)


class GraphTests(Past):
    def test_the_fully_done_graph_counts_the_time_tasks_took_and_leaves_out_times_to_check(self):
        self.past("Review", 1, "done", taken=80)
        self.past("Write", 1, "done", start="14:00", taken=200)
        self.past("Old", 1, "done", start="19:00")
        day, = self.store.report_graphs(ago(1), ago(1))["days"]
        self.assertEqual(day["minutes"], {"learning": 140})

    def test_follow_through_counts_unanswered_entries_apart_from_skipped_and_today_waits_for_22_00(self):
        self.set_entry("Review", ago(1), "10:00", "skipped")
        self.set_entry("Write", ago(1), "11:00", "planned")
        self.set_entry("Read", self.today, "10:00", "planned")
        for clock, waiting, unanswered in (("21:59", 1, 0), ("22:00", 0, 1)):
            with self.at(clock):
                yesterday, today = self.store.report_graphs(ago(1), self.today)["followThrough"]
            self.assertEqual((yesterday["skipped"], yesterday["noReply"], yesterday["unreported"]), (1, 1, 0))
            self.assertEqual((today["unreported"], today["noReply"]), (waiting, unanswered), clock)


class UsualLengthTests(Past):
    def test_done_times_that_keep_differing_from_the_length_you_set_offer_to_change_it_on_confirm(self):
        for days, taken in ((3, 75), (2, 80), (1, 75)):
            self.past("Review", days, "done", start="14:00", taken=taken)
        today, later = self.add("Review", "14:00"), self.add("Review", "14:00", day=self.tomorrow)
        self.report(today, "done", "15:15")
        notice, = [notice for notice in self.store.notices() if notice["kind"] == "usual-length"]
        self.assertEqual({key: notice["values"][key] for key in ("taskTitle", "usualMinutes", "setMinutes")},
                         {"taskTitle": "Review", "usualMinutes": 75, "setMinutes": 60})
        self.assertEqual((notice["agentKey"], notice["proposal"]["status"], notice["proposal"]["payload"]["itemIds"]),
                         ("learning", "pending", [later["id"]]))
        decided = self.client.post(f"/api/actions/{notice['proposal']['id']}", json={"decision": "confirmed"})
        self.assertEqual(decided.status_code, 200, decided.text)
        changed = self.store.daily_item(later["id"])
        self.assertEqual((changed["duration_minutes"], changed["durationSource"]), (75, "user"))
        self.assertEqual(self.store.daily_item(today["id"])["duration_minutes"], 60)
        self.assertEqual(next(n for n in self.store.notices() if n["kind"] == "usual-length")["proposal"]["status"], "confirmed")

    def test_no_offer_while_fewer_than_three_of_the_last_four_differ(self):
        for days, taken in ((3, 75), (2, 60), (1, 60)):
            self.past("Review", days, "done", start="14:00", taken=taken)
        today = self.add("Review", "14:00")
        self.add("Review", "14:00", day=self.tomorrow)
        self.report(today, "done", "15:15")
        self.assertFalse([notice for notice in self.store.notices() if notice["kind"] == "usual-length"])


class YesterdayNoticeTests(Past):
    def notice(self):
        return self.client.get("/api/bootstrap", params={"date": self.today}).json()["yesterdayNotice"]

    def test_today_lists_yesterdays_tasks_stopped_at_their_limit_left_unanswered_or_with_a_time_to_check(self):
        # Journal, an hour from 09:00, is interrupted by Review at 10:00 and resumes after lunch until its limit.
        self.past("Journal", 1, "planned", start="09:00")
        self.past("Review", 1, "done", start="10:00", taken=90, at="12:00")
        self.past("Call Bo", 1, "done", start="11:30", minutes=30, taken=30)
        self.past("Write", 1, "done", start="14:00", taken=200)
        self.past("Tea", 1, "planned", start="21:30", minutes=30)
        notice = self.notice()
        self.assertEqual(notice["date"], ago(1))
        # Review has its status and a time under twice its length, so it isn't listed.
        self.assertEqual([(task["title"], task["reason"]) for task in notice["tasks"]],
                         [("Journal", "limit"), ("Write", "checkTime"), ("Tea", "noReply")])
        self.assertEqual(self.client.post("/api/yesterday-notice/dismiss", json={"date": ago(1)}).status_code, 200)
        self.assertIsNone(self.notice())

    def test_a_day_with_nothing_to_fix_has_no_notice(self):
        self.past("Call Bo", 1, "done", minutes=30, taken=30)
        self.assertIsNone(self.notice())


if __name__ == "__main__":
    unittest.main()
