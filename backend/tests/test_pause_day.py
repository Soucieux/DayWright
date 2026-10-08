import unittest

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
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
