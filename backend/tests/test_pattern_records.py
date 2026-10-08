import sqlite3
import unittest
from datetime import date, timedelta

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app import patterns
from backend.tests.test_learning_tasks import TODAY, LearningDay, at
from backend.tests.test_pause_day import PauseDay


class PatternDay(PauseDay):
    """A fresh account whose past days' tasks and times are written straight in, as recorded since v4.7."""

    def on_day(self, title, day, start=None, minutes=60, made_before=True):
        """A task on `day`, made the day before it unless `made_before` is False, then made after it."""
        item = self.add(title, start, minutes)
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE daily_items SET item_date = ? WHERE id = ?", (day, item["id"]))
        before = date.fromisoformat(day) - timedelta(days=1)
        self.made(item["id"], f"{before}T08:00:00+00:00" if made_before else f"{self.today}T12:00:00+00:00")
        return item

    def took(self, item, status, start, end, minutes, at, confirmed=0):
        """Its status and the time it took, as the store records them."""
        with sqlite3.connect(self.path) as connection:
            connection.execute("""UPDATE daily_items SET completion_status = ?, status_at = ?, actual_start = ?, actual_end = ?,
                                  actual_minutes = ?, time_confirmed = ? WHERE id = ?""",
                               (status, at, start, end, minutes, confirmed, item["id"]))

    def sql(self, statement, *values):
        with sqlite3.connect(self.path) as connection:
            connection.execute(statement, values)

    def records(self, start=None, end=None):
        found = self.store.pattern_records(start or self.yesterday, end or self.yesterday)
        return {record["title"]: record for record in found["records"]}, found["toCheck"]


class RecordTests(PatternDay):
    def test_a_task_with_a_status_gives_its_time_its_status_and_when_that_was_set(self):
        review = self.on_day("Review", self.yesterday, "10:00", 60)
        self.took(review, "done", "10:00", "11:05", 65, "11:10")
        records, to_check = self.records()
        self.assertEqual(records["Review"], {"date": self.yesterday, "title": "Review", "domain": "learning", "planned": 60,
                                             "estimate": None, "status": "done", "minutes": 65, "statusAt": "11:10",
                                             "end": "11:05", "series": None})
        self.assertEqual(to_check, 0)

    def test_a_time_to_check_stays_out_until_confirmed_and_is_counted_apart(self):
        review = self.on_day("Review", self.yesterday, "09:00", 60)
        self.took(review, "done", "09:00", "11:00", 120, "24:00")
        records, to_check = self.records()
        self.assertEqual((records["Review"]["minutes"], to_check), (None, 1))
        self.sql("UPDATE daily_items SET time_confirmed = 1 WHERE id = ?", review["id"])
        records, to_check = self.records()
        self.assertEqual((records["Review"]["minutes"], to_check), (120, 0))

    def test_nothing_from_before_times_were_kept(self):
        old = self.on_day("Old", self.yesterday, "09:00", 60)
        self.sql("UPDATE daily_items SET completion_status = 'done' WHERE id = ?", old["id"])
        records, to_check = self.records()
        self.assertEqual((records["Old"]["minutes"], records["Old"]["statusAt"], records["Old"]["end"], to_check),
                         (None, None, None, 0))
        habit = patterns.reporting(list(records.values()), patterns.columns("week", self.yesterday, self.yesterday))
        self.assertEqual(habit["totals"], {"rightAway": 0, "laterDay": 0, "nextDay": 0, "noReply": 0})

    def test_a_task_left_without_a_status_counts_the_time_it_was_current_and_one_never_current_none(self):
        self.on_day("Read", self.yesterday, "09:00", 90)
        self.on_day("Later", self.yesterday, None, 30, made_before=False)
        self.store.pause_day(self.yesterday, "10:00")
        self.store.resume_day(self.yesterday, "21:30")
        records, to_check = self.records()
        self.assertEqual((records["Read"]["status"], records["Read"]["minutes"]), ("noReply", 60 + 30))
        self.assertEqual((records["Later"]["status"], records["Later"]["minutes"]), ("noReply", 0))
        self.assertEqual(to_check, 0)

    def test_one_left_at_its_limit_is_left_out_and_counted_as_needing_a_status_first(self):
        read = self.on_day("Read", self.yesterday, "09:00", 60)
        found = self.store.pattern_records(self.yesterday, self.yesterday)
        records = {record["title"]: record for record in found["records"]}
        self.assertEqual((records["Read"]["status"], records["Read"]["minutes"], found["toCheck"]), ("noReply", None, 1))
        self.assertEqual(found["checks"], [{"itemId": read["id"], "date": self.yesterday, "title": "Read", "start": None,
                                            "end": None, "minutes": None, "setMinutes": 60, "needsStatus": True}])

    def test_a_day_that_ended_paused_reads_day_paused_and_its_paused_time_counts_nowhere(self):
        self.on_day("Read", self.yesterday, "09:00", 90)
        self.store.pause_day(self.yesterday, "10:00")
        records, _ = self.records()
        self.assertEqual((records["Read"]["status"], records["Read"]["minutes"]), ("dayPaused", 60))

    def test_tasks_still_to_do_and_agents_suggestions_are_left_out(self):
        self.add("Today", "09:00")
        suggestion = self.on_day("Suggested", self.yesterday, "11:00")
        self.sql("UPDATE daily_items SET acceptance = 'pending' WHERE id = ?", suggestion["id"])
        with self.at("10:00"):
            records, _ = self.records(self.yesterday, self.today)
        self.assertEqual(set(records), set())

    def test_an_agents_estimate_and_a_repeat_are_named(self):
        review = self.on_day("Review", self.yesterday, "09:00", 45)
        self.took(review, "done", "09:00", "09:50", 50, "09:50")
        self.sql("UPDATE daily_items SET duration_source = 'estimate', repeat_kind = 'weekly', repeat_series_id = 's1' WHERE id = ?",
                 review["id"])
        records, _ = self.records()
        self.assertEqual((records["Review"]["estimate"], records["Review"]["series"]), (45, "s1"))


class PatternRouteTests(PatternDay):
    def test_the_patterns_tab_reads_seven_or_thirty_days_to_the_day_on_show_or_everything(self):
        review = self.on_day("Review", self.yesterday, "10:00", 60)
        self.took(review, "done", "10:00", "11:00", 60, "11:00")
        month = self.client.get("/api/patterns", params={"date": self.today, "period": "month"}).json()
        self.assertEqual((month["start"], month["end"], month["period"]),
                         ((date.today() - timedelta(days=29)).isoformat(), self.today, "month"))
        self.assertEqual(month["bestHours"]["count"], 1)
        week = self.client.get("/api/patterns", params={"date": self.yesterday, "period": "week"}).json()
        self.assertEqual((week["start"], week["end"], len(week["columns"])),
                         ((date.today() - timedelta(days=7)).isoformat(), self.yesterday, 7))
        ahead = self.client.get("/api/patterns", params={"date": self.tomorrow, "period": "week"}).json()
        self.assertEqual(ahead["end"], self.today, "a day ahead reads to today")
        every = self.client.get("/api/patterns", params={"date": self.today, "period": "all"}).json()
        self.assertEqual(every["start"], self.yesterday, "from the first recorded day")
        self.assertEqual(self.client.get("/api/patterns", params={"date": self.today, "period": "year"}).status_code, 422)

    def test_area_pages_list_their_repeating_tasks_and_life_its_energy_line(self):
        for offset in (1, 2, 3):
            day = (date.today() - timedelta(days=offset)).isoformat()
            review = self.on_day("Weekly review", day, "10:00", 60)
            self.took(review, "done", "10:00", "11:15", 75, "11:15")
            self.sql("UPDATE daily_items SET repeat_kind = 'weekly', repeat_series_id = 's1' WHERE id = ?", review["id"])
        learning = self.client.get("/api/areas/learning", params={"date": self.today}).json()
        self.assertEqual(learning["patterns"]["repeating"]["finding"],
                         {"kind": "usual", "key": "s1", "title": "Weekly review", "actual": 75, "planned": 60})
        self.assertIn("pace", learning["patterns"])
        life = self.client.get("/api/areas/life", params={"date": self.today}).json()
        self.assertEqual(life["patterns"]["energy"], {"kind": "never"})

    def test_ava_checks_every_time_to_check_on_one_card_each_with_its_day(self):
        earlier = (date.today() - timedelta(days=3)).isoformat()
        for title, day in (("Inbox", self.yesterday), ("Plan week", earlier)):
            task = self.on_day(title, day, "09:00", 30)
            self.took(task, "done", "09:00", "10:00", 60, "24:00")
        card = self.ask("Check my times", "09:00")["proposedAction"]
        self.assertEqual(card["actionType"], "check_times")
        self.assertEqual([(task["title"], task["date"]) for task in card["payload"]["tasks"]],
                         [("Plan week", earlier), ("Inbox", self.yesterday)])
        self.assertIsNone(card["payload"]["date"])
        self.assertEqual(self.ask("核对我的用时", "09:01")["proposedAction"]["actionType"], "check_times")
        ids = {task["title"]: task["itemId"] for task in card["payload"]["tasks"]}
        decided = self.decide(card, "09:02", times={ids["Inbox"]: "right", ids["Plan week"]: 45})
        self.assertEqual(decided.status_code, 200, decided.text)
        inbox, plan = self.store.daily_item(ids["Inbox"]), self.store.daily_item(ids["Plan week"])
        self.assertEqual((inbox["timeConfirmed"], plan["actualMinutes"], plan["actualEnd"], plan["timeConfirmed"]),
                         (True, 45, "09:45", True))
        self.assertEqual(self.store.pattern_records(earlier, self.yesterday)["toCheck"], 0)

    def test_the_note_counts_every_time_left_out_and_ava_lists_the_same_set_for_the_range_shown(self):
        inbox = self.on_day("Inbox", self.yesterday, "09:00", 30)
        self.took(inbox, "done", "09:00", "10:00", 60, "24:00")
        old = self.on_day("Plan week", (date.today() - timedelta(days=10)).isoformat(), "09:00", 30)
        self.took(old, "done", "09:00", "10:00", 60, "24:00")
        # Without a status, Read runs to its limit: its time is left out until it has one and is checked.
        read = self.on_day("Read", self.yesterday, "13:00", 60)
        month = self.client.get("/api/patterns", params={"date": self.today, "period": "month"}).json()
        self.assertEqual((month["toCheck"], month["needsStatus"]), (3, 1))
        week = self.client.get("/api/patterns", params={"date": self.today, "period": "week"}).json()
        self.assertEqual((week["toCheck"], week["needsStatus"]), (2, 1), "Plan week is older than these 7 days")
        reply = self.ask("Check my times for these 7 days", "09:00")
        card = reply["proposedAction"]
        self.assertIn("1 task needs a status first", reply["assistantMessage"]["content"])
        self.assertEqual(card["payload"]["period"], "week")
        listed = {task["itemId"]: task["needsStatus"] for task in card["payload"]["tasks"]}
        self.assertEqual(listed, {check["itemId"]: check["needsStatus"] for check in week["checks"]})
        self.assertEqual(listed, {inbox["id"]: False, read["id"]: True})
        # Patterns asks in these words, as its period shows (see checkPrompt in patternText.js).
        for prompt, count in (("Check my times for these 30 days", 3), ("Check all my times", 3), ("核对这 7 天的用时", 2),
                              ("核对这 30 天的用时", 3), ("核对我所有的用时", 3)):
            self.assertEqual(len(self.ask(prompt, "09:01")["proposedAction"]["payload"]["tasks"]), count, prompt)
        decided = self.decide(card, "09:02", times={inbox["id"]: "right"})
        self.assertEqual(decided.status_code, 200, decided.text)
        self.assertEqual(self.store.daily_item(read["id"])["completion_status"], "planned", "a task needing a status keeps none")
        # With only a task needing a status left, the card has nothing to confirm, and Ava doesn't ask for it.
        left = self.ask("Check my times for these 7 days", "09:03")
        self.assertEqual([task["needsStatus"] for task in left["proposedAction"]["payload"]["tasks"]], [True])
        self.assertNotIn("until you confirm", left["assistantMessage"]["content"])
        # Its Catch up asks Ava from its own day.
        caught = self.ask("Catch up", "09:03", day=self.yesterday)["proposedAction"]
        self.assertEqual((caught["actionType"], caught["payload"]["date"]), ("catch_up", self.yesterday))
        self.assertIn(read["id"], [task["id"] for task in caught["payload"]["tasks"]])


class SectionPaceRecordTests(LearningDay):
    def test_a_sources_pace_comes_from_its_timed_tasks_sections_ticked_on_them(self):
        task = self.learning.create_tasks([self.lesson["id"]], TODAY)["tasks"][0]["id"]
        self.tick(task, "HttpClient setup", now=at(TODAY, "10:00"))
        self.tick(task, "Interceptors", now=at(TODAY, "10:10"))
        with self.store.connect() as connection:
            connection.execute("""UPDATE daily_items SET completion_status = 'done', status_at = '10:30', actual_start = '10:00',
                                  actual_end = '10:24', actual_minutes = 24, duration_minutes = 30 WHERE id = ?""", (task,))
        self.assertEqual(self.store.pace_tasks(), [{"sourceId": self.lesson["id"], "sourceTitle": "Consuming HTTP Services",
                                                    "minutes": 24, "sections": 2}])
        self.assertEqual(self.learning.task(task)["pace"], {"minutes": 12, "sections": 2})


if __name__ == "__main__":
    unittest.main()
