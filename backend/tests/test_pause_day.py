import json
import sqlite3
import unittest
from datetime import date, timedelta

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.agents import SummaryAgent
from backend.tests.test_time_record import TimeDay


class PauseDay(TimeDay):
    """A fresh account and a clock the tests set: the day paused and resumed through the service."""

    def pause(self, clock):
        with self.at(clock):
            return self.client.post("/api/day/pause")

    def resume(self, clock):
        with self.at(clock):
            return self.client.post("/api/day/resume")

    def now(self, clock):
        with self.at(clock):
            return self.client.get("/api/now").json()

    def current(self, clock):
        current = self.now(clock)["current"]
        return current and current["title"]

    def ask(self, message, clock, day=None):
        with self.at(clock):
            answer = self.client.post("/api/chat", json={"date": day or self.today, "message": message})
        self.assertEqual(answer.status_code, 200, answer.text)
        return answer.json()

    def add_yesterday(self, title, start=None, minutes=60):
        """Add a task today, then move it to yesterday, as past days are read-only to add to."""
        item = self.add(title, start, minutes)
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE daily_items SET item_date = ? WHERE id = ?", (self.yesterday, item["id"]))
        # Made the day before, as any task can be current from the start of a day it was made before.
        self.made(item["id"], f"{date.fromisoformat(self.yesterday) - timedelta(days=1)}T08:00:00+00:00")
        return item

    def decide(self, action, clock, **choices):
        with self.at(clock):
            return self.client.post(f"/api/actions/{action['id']}", json={"decision": "confirmed", **choices})


class PauseTests(PauseDay):
    def test_pausing_ends_the_current_tasks_stretch_and_nothing_is_current_while_paused(self):
        self.add("Review", "14:00")
        self.assertEqual(self.pause("14:10").status_code, 200)
        now = self.now("14:30")
        self.assertIsNone(now["current"])
        self.assertEqual((now["pausedSince"], now["title"]), ("14:10", "Paused since 14:10"))
        self.assertEqual(self.client.get(f"/api/bootstrap?date={self.today}").json()["pausedSince"], "14:10")

    def test_a_status_set_while_paused_keeps_the_time_the_task_had_at_the_pause(self):
        review = self.add("Review", "14:00")
        self.pause("14:10")
        self.report(review, "done", "14:40")
        self.assertEqual(self.timing(review), ("done", "14:40", "14:00", "14:10"))
        self.assertEqual(self.store.daily_item(review["id"])["actualMinutes"], 10)

    def test_resume_inside_a_timed_tasks_planned_time_picks_that_task(self):
        self.add("Read")
        self.add("Review", "14:00")
        self.pause("11:00")
        self.assertEqual(self.resume("14:20").status_code, 200)
        self.assertEqual(self.current("14:20"), "Review")
        self.assertIsNone(self.now("14:20")["pausedSince"])

    def test_resume_outside_one_continues_the_paused_task_and_a_task_wholly_inside_the_pause_never_runs(self):
        self.add("Review", "14:00")
        email = self.add("Email Anna", "15:00", 30)
        self.add("Read")
        self.pause("14:10")
        self.resume("15:40")
        self.assertEqual(self.current("15:40"), "Review")
        self.assertNotEqual(self.current("15:45"), "Email Anna")
        self.assertEqual(self.store.daily_item(email["id"])["completion_status"], "planned")

    def test_when_the_paused_task_has_a_status_resume_falls_back_to_the_usual_order(self):
        review = self.add("Review", "14:00")
        self.add("Read")
        self.pause("14:10")
        self.report(review, "done", "14:30")
        self.resume("16:00")
        self.assertEqual(self.current("16:00"), "Read")

    def test_pause_and_resume_refuse_what_cant_be_done(self):
        self.assertEqual(self.resume("10:00").status_code, 409)
        self.assertEqual(self.pause("10:00").status_code, 200)
        self.assertEqual(self.pause("10:05").status_code, 409)
        self.resume("10:10")
        self.assertEqual(self.pause("22:00").status_code, 409)

    def test_the_next_day_starts_unpaused(self):
        self.store.pause_day(self.yesterday, "14:10")
        now = self.now("09:00")
        self.assertIsNone(now["pausedSince"])
        self.assertNotIn("Paused", now["title"])


class PausedDayTests(PauseDay):
    """A day still paused at 22:00: its tasks without a status read "Not done · paused", never no reply."""

    def setUp(self):
        super().setUp()
        self.review = self.add_yesterday("Review", "10:00")
        self.read = self.add_yesterday("Read")

    def test_tasks_left_without_a_status_on_a_day_paused_at_its_end_read_not_done_paused(self):
        self.store.pause_day(self.yesterday, "14:10")
        items = {item["title"]: item for item in self.store.daily_items(self.yesterday)}
        self.assertEqual((items["Review"]["dayPaused"], items["Review"]["noReply"]), (True, False))
        self.assertTrue(all(task["dayPaused"] and not task["noReply"] for task in self.store.catch_up_tasks(self.yesterday)))

    def test_a_day_resumed_before_22_00_settles_as_no_reply(self):
        self.store.pause_day(self.yesterday, "14:10")
        self.store.resume_day(self.yesterday, "15:00")
        items = {item["title"]: item for item in self.store.daily_items(self.yesterday)}
        self.assertEqual((items["Review"]["dayPaused"], items["Review"]["noReply"]), (False, True))

    def test_the_next_days_notice_says_when_the_day_was_paused_and_lists_those_tasks(self):
        # Paused at 10:30, before either task reached its limit, which would make it a time to check instead.
        self.store.pause_day(self.yesterday, "10:30")
        notice = self.store.yesterday_notice(self.today)
        self.assertEqual(notice["pausedAt"], "10:30")
        self.assertEqual({task["title"]: task["reason"] for task in notice["tasks"]}, {"Review": "dayPaused", "Read": "dayPaused"})

    def test_kept_out_of_no_reply_in_summaries_and_of_often_left_unanswered(self):
        self.store.pause_day(self.yesterday, "14:10")
        facts = self.store.summary_facts(self.yesterday, self.yesterday)
        work = facts["domains"]["learning"]
        self.assertEqual((work["noReply"], work["dayPaused"]), (0, 2))
        outcome = next(item for item in facts["taskOutcomes"] if item["taskTitle"] == "Review")
        self.assertEqual((outcome["noReply"], outcome["dayPaused"]), (0, 1))
        self.store.rebuild_task_profiles()
        self.assertNotIn(("learning", "review"), self.store.task_profiles())

    def test_summary_names_them_apart_from_no_reply_and_gives_them_no_advice(self):
        self.store.pause_day(self.yesterday, "14:10")
        report = json.dumps(SummaryAgent().period_report("day", self.yesterday,
                                                         self.store.summary_facts(self.yesterday, self.yesterday)))
        self.assertIn("2 not done as the day was paused", report)
        self.assertNotIn("left without a status", report)
        self.assertNotIn("Review was", report)

    def test_corrected_through_ava_like_no_reply(self):
        self.store.pause_day(self.yesterday, "14:10")
        reply = self.ask("Catch up", "09:00", day=self.yesterday)
        card = reply["proposedAction"]
        self.assertTrue(all(task["dayPaused"] for task in card["payload"]["tasks"]))
        self.assertEqual(self.decide(card, "09:01", statuses={self.review["id"]: "done"}).status_code, 200)
        self.assertEqual(self.store.daily_item(self.review["id"])["completion_status"], "done")

    def test_avas_edit_card_says_the_task_was_left_on_a_paused_day(self):
        edit = self.ask("Change Review to partly done", "09:00", day=self.yesterday)["proposedAction"]
        self.assertEqual((edit["actionType"], edit["payload"].get("dayPaused")), ("edit_item", None))
        self.store.pause_day(self.yesterday, "14:10")
        edit = self.ask("Change Review to partly done", "09:00", day=self.yesterday)["proposedAction"]
        self.assertEqual((edit["payload"]["before"], edit["payload"]["dayPaused"]), ({"status": "planned"}, True))


class AvaPauseTests(PauseDay):
    def test_pause_my_day_and_im_done_for_today_bring_a_card_that_pauses_on_confirm(self):
        for words in ("pause my day", "I'm done for today", "暂停今天"):
            with self.subTest(words=words):
                card = self.ask(words, "14:10")["proposedAction"]
                self.assertEqual(card["actionType"], "pause_day")
                self.assertIsNone(self.now("14:11")["pausedSince"], "nothing changes before Confirm")
                self.assertEqual(self.decide(card, "14:12").status_code, 200)
                self.assertEqual(self.now("14:13")["pausedSince"], "14:12")
                self.resume("14:20")

    def test_im_back_brings_a_card_that_resumes_on_confirm_and_says_so_when_not_paused(self):
        self.assertIsNone(self.ask("I'm back", "13:00")["proposedAction"])
        self.pause("13:10")
        for words in ("I'm back", "我回来了"):
            with self.subTest(words=words):
                card = self.ask(words, "14:00")["proposedAction"]
                self.assertEqual(card["actionType"], "resume_day")
                self.assertEqual(self.decide(card, "14:01").status_code, 200)
                self.assertIsNone(self.now("14:02")["pausedSince"])
                self.pause("14:05")

    def test_ava_pauses_and_resumes_only_today(self):
        reply = self.ask("pause my day", "14:10", day=self.yesterday)
        self.assertIsNone(reply["proposedAction"])


if __name__ == "__main__":
    unittest.main()
