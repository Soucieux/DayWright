import sqlite3
import unittest

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.tests.test_meals import MealDay


class CorrectionDay(MealDay):
    """Yesterday's tasks, which Ava alone corrects: what happened to each, and the time it took."""

    def chat(self, message):
        return self.client.post("/api/chat", json={"date": self.yesterday, "message": message}).json()

    def decide(self, action):
        decided = self.client.post(f"/api/actions/{action['id']}", json={"decision": "confirmed"})
        self.assertEqual(decided.status_code, 200, decided.text)
        return decided.json()

    def past(self, title, status="done", taken=None, start="09:00", minutes=60):
        """A task yesterday at `start`, reported as `status`, with the time it took as (start, end)."""
        made = self.client.post("/api/daily-items", json=self.task(title, start, minutes)).json()
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """UPDATE daily_items SET item_date = ?, completion_status = ?, status_at = ?, actual_start = ?,
                       actual_end = ? WHERE id = ?""",
                (self.yesterday, status, taken and "24:00", taken and taken[0], taken and taken[1], made["id"]))
        return made

    def timing(self, item):
        stored = self.store.daily_item(item["id"])
        return (stored["completion_status"], stored["actualStart"], stored["actualEnd"], stored["timeConfirmed"],
                stored["start_time"], stored["duration_minutes"])


class TimeCorrectionTests(CorrectionDay):
    def test_how_long_a_past_task_took_is_a_card_that_changes_the_time_it_took_on_confirm(self):
        review = self.past("Review", taken=("09:00", "10:00"))
        action = self.chat("Review took 2 hours")["proposedAction"]
        self.assertEqual(action["actionType"], "edit_item")
        self.assertEqual(action["payload"]["changes"], {"actualTime": {"start": "09:00", "end": "11:00"}})
        self.assertEqual(action["payload"]["before"], {"actualTime": {"start": "09:00", "end": "10:00"}})
        self.decide(action)
        self.assertEqual(self.timing(review), ("done", "09:00", "11:00", True, "09:00", 60))

    def test_when_it_started_or_ended_changes_that_end_of_the_time_it_took(self):
        self.past("Review", taken=("09:00", "10:00"))
        for message, expected in (("I started Review at 9:30", {"start": "09:30", "end": "10:00"}),
                                  ("Review finished at 10:45", {"start": "09:00", "end": "10:45"}),
                                  ("Review started at 9:15 and finished at 10:15", {"start": "09:15", "end": "10:15"})):
            self.assertEqual(self.chat(message)["proposedAction"]["payload"]["changes"], {"actualTime": expected}, message)

    def test_a_time_you_call_right_is_confirmed_and_then_counts(self):
        write = self.past("Write", taken=("09:00", "12:20"))
        action = self.chat("Write's time is right")["proposedAction"]
        self.assertEqual(action["payload"]["changes"], {"timeConfirmed": True})
        self.decide(action)
        self.assertEqual(self.timing(write), ("done", "09:00", "12:20", True, "09:00", 60))

    def test_a_task_left_without_a_status_is_reported_with_the_time_it_took(self):
        journal = self.past("Journal", status="planned")
        action = self.chat("Journal was done, it took 30 minutes")["proposedAction"]
        self.assertEqual(action["payload"]["changes"], {"status": "done", "actualTime": {"start": "09:00", "end": "09:30"}})
        self.decide(action)
        self.assertEqual(self.timing(journal), ("done", "09:00", "09:30", True, "09:00", 60))

    def test_from_today_a_message_about_yesterday_corrects_yesterdays_task_as_todays_notice_asks(self):
        journal = self.past("Journal", status="planned")
        reply = self.client.post("/api/chat", json={"date": self.today,
                                                     "message": "Yesterday Journal was done, it took 30 minutes"}).json()
        action = reply["proposedAction"]
        self.assertEqual((action["payload"]["date"], action["payload"]["itemId"]), (self.yesterday, journal["id"]))
        self.assertEqual(action["payload"]["changes"], {"status": "done", "actualTime": {"start": "09:00", "end": "09:30"}})

    def test_its_planned_place_still_stays_and_a_time_needs_a_status_and_an_order(self):
        review, journal = self.past("Review", taken=("09:00", "10:00")), self.past("Journal", status="planned", start="11:00")
        for message, said in (("Move Review to 11:00", "keeps its place"),
                              ("Journal took 30 minutes", "Say how “Journal” went too"),
                              ("Review started at 10:30 and finished at 10:00", "ends before it starts")):
            reply = self.chat(message)
            self.assertIsNone(reply["proposedAction"], message)
            self.assertIn(said, reply["assistantMessage"]["content"], message)
        self.assertEqual(self.timing(review), ("done", "09:00", "10:00", False, "09:00", 60))
        self.assertEqual(self.timing(journal)[:3], ("planned", None, None))


class SummedCorrectionTests(CorrectionDay):
    """A past task's time taken added up from stretches, as Ava corrects it."""

    def reading(self):
        # 10:00–11:30 with a break between: 70 minutes current.
        reading = self.past("Reading", taken=("10:00", "11:30"), start="10:00")
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE daily_items SET actual_minutes = 70 WHERE id = ?", (reading["id"],))
        return reading

    def test_a_time_told_sets_the_whole_of_it(self):
        reading = self.reading()
        action = self.chat("Reading took 2 hours")["proposedAction"]
        self.decide(action)
        stored = self.store.daily_item(reading["id"])
        self.assertEqual((stored["actualStart"], stored["actualEnd"], stored["actualMinutes"]), ("10:00", "12:00", 120))

    def test_its_time_confirmed_keeps_the_sum(self):
        reading = self.reading()
        self.decide(self.chat("Reading's time is right")["proposedAction"])
        stored = self.store.daily_item(reading["id"])
        self.assertEqual((stored["actualMinutes"], stored["timeConfirmed"]), (70, True))


if __name__ == "__main__":
    unittest.main()
