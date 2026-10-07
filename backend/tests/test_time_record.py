import sqlite3
import unittest
from unittest.mock import patch

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.tests.test_meals import MealDay


class TimeDay(MealDay):
    """A fresh account whose tasks were made before today, so any of them may be current from the day's start."""

    def add(self, title, start=None, minutes=60, day=None):
        made = self.client.post("/api/daily-items", json={**self.task(title, start, minutes), "date": day or self.today})
        self.assertEqual(made.status_code, 200, made.text)
        self.made(made.json()["id"], f"{self.yesterday}T08:00:00+00:00")
        return made.json()

    def made(self, item_id, created):
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE daily_items SET created_at = ? WHERE id = ?", (created, item_id))

    def at(self, clock):
        return patch("backend.app.database._local_time", return_value=clock)

    def report(self, item, status, clock):
        with self.at(clock):
            return self.client.patch(f"/api/daily-items/{item['id']}/status", json={"status": status})

    def timing(self, item):
        saved = self.store.daily_item(item["id"])
        return saved["completion_status"], saved["statusAt"], saved["actualStart"], saved["actualEnd"]


class RecordingTests(TimeDay):
    def test_a_status_records_when_it_was_set_and_the_time_the_task_took(self):
        review, email = self.add("Review", "14:00"), self.add("Email Anna", "15:30", 30)
        self.assertEqual(self.report(review, "done", "14:50").status_code, 200)
        self.assertEqual(self.timing(review), ("done", "14:50", "14:00", "14:50"))
        self.assertEqual(self.timing(email), ("planned", None, None, None))

    def test_a_late_status_ends_at_the_next_tasks_start_and_changes_no_other_task(self):
        review, email = self.add("Review", "14:00"), self.add("Email Anna", "15:30", 30)
        self.report(email, "done", "15:50")
        self.report(review, "done", "16:10")
        self.assertEqual(self.timing(review), ("done", "16:10", "14:00", "15:30"))
        self.assertEqual(self.timing(email), ("done", "15:50", "15:30", "15:50"))

    def test_a_status_changed_again_keeps_its_time_and_planned_clears_it(self):
        review = self.add("Review", "14:00")
        self.report(review, "partial", "14:40")
        self.report(review, "done", "15:10")
        self.assertEqual(self.timing(review), ("done", "14:40", "14:00", "14:40"))
        self.report(review, "planned", "15:20")
        self.assertEqual(self.timing(review), ("planned", None, None, None))

    def test_the_task_form_and_a_set_plans_entry_record_it_too(self):
        review, read = self.add("Review", "14:00"), self.add("Read", None, 45)
        with self.at("14:30"):
            edited = self.client.put(f"/api/daily-items/{review['id']}", json={**self.task("Review", "14:00"), "status": "done"})
        self.assertEqual(edited.status_code, 200, edited.text)
        self.assertEqual(self.timing(review), ("done", "14:30", "14:00", "14:30"))
        plans = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": plans["variants"][0]["id"]})
        entry = next(entry for entry in self.client.get("/api/bootstrap", params={"date": self.today}).json()["entries"]
                     if entry["source_item_id"] == read["id"])
        with self.at("23:00"):
            self.assertEqual(self.client.patch(f"/api/entries/{entry['id']}", json={"status": "skipped"}).status_code, 200)
        status, at, start, end = self.timing(read)
        self.assertEqual((status, at, start), ("skipped", "23:00", entry["start_time"]))
        self.assertTrue(end <= "22:00")

    def test_only_todays_tasks_are_reported_from_the_menu_bar(self):
        later = self.add("Review", "14:00", day=self.tomorrow)
        self.assertEqual(self.report(later, "done", "14:10").status_code, 409)
        self.assertEqual(self.client.patch("/api/daily-items/missing/status", json={"status": "done"}).status_code, 404)
        self.assertEqual(self.client.patch(f"/api/daily-items/{later['id']}/status", json={"status": "maybe"}).status_code, 422)


class NowTests(TimeDay):
    def test_now_names_the_current_and_next_task_with_the_time_taken_and_the_title(self):
        review, email = self.add("Review", "14:00"), self.add("Email Anna", "15:30", 30)
        with self.at("14:32"):
            now = self.client.get("/api/now").json()
        self.assertEqual((now["current"]["id"], now["next"]["id"], now["taken"]), (review["id"], email["id"], 32))
        self.assertEqual((now["current"]["start"], now["current"]["minutes"], now["current"]["durationSource"]), ("14:00", 60, "user"))
        self.assertEqual(now["title"], "Review · 32 / 60 min · next: Email Anna")
        with self.at("14:32"):
            title = self.client.get("/api/now/title")
        self.assertEqual((title.text, title.headers["content-type"].split(";")[0]), (now["title"], "text/plain"))

    def test_an_untimed_current_task_is_stamped_once_when_first_seen_and_starts_there(self):
        read = self.add("Read", None, 45)
        with self.at("09:10"):
            self.assertEqual(self.client.get("/api/now").json()["current"]["id"], read["id"])
        with self.at("09:40"):
            now = self.client.get("/api/now").json()
        self.assertEqual((self.store.daily_item(read["id"])["currentSince"], now["taken"]), ("09:10", 30))
        self.report(read, "done", "09:55")
        self.assertEqual(self.timing(read), ("done", "09:55", "09:10", "09:55"))

    def test_a_task_made_today_is_current_only_from_when_it_was_made(self):
        read = self.add("Read", None, 45)
        self.made(read["id"], f"{self.today}T10:00:00")
        with self.at("09:00"):
            self.assertIsNone(self.client.get("/api/now").json()["current"])

    def test_the_title_speaks_the_interface_language(self):
        self.add("Review", "14:00")
        self.assertEqual(self.client.put("/api/interface-language", json={"language": "zh"}).status_code, 200)
        with self.at("14:05"):
            self.assertEqual(self.client.get("/api/now/title").text, "Review · 5 / 60 分钟")
        self.assertEqual(self.client.put("/api/interface-language", json={"language": "fr"}).status_code, 422)


class NoReplyTests(TimeDay):
    def test_todays_unset_tasks_read_no_reply_from_22_00_and_every_past_days_do(self):
        review = self.add("Review", "14:00")
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE daily_items SET item_date = ? WHERE id = ?", (self.yesterday, review["id"]))
        today = self.add("Read", None, 45)
        for clock, expected in (("21:59", False), ("22:00", True)):
            with self.at(clock):
                self.assertEqual(self.store.daily_item(today["id"])["noReply"], expected, clock)
                self.assertTrue(self.store.daily_item(review["id"])["noReply"])
        self.report(today, "done", "22:30")
        with self.at("22:30"):
            self.assertFalse(self.store.daily_item(today["id"])["noReply"])


if __name__ == "__main__":
    unittest.main()
