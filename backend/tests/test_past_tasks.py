import sqlite3
import unittest
from datetime import date, timedelta

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.tests.test_meals import MealDay

TWO_DAYS_AGO = (date.today() - timedelta(days=2)).isoformat()


class PastTaskPlacementTests(MealDay):
    """On a past day, Ava corrects what a task is, removes it, or moves it forward, but never rearranges that day."""

    def chat(self, day, message):
        return self.client.post("/api/chat", json={"date": day, "message": message}).json()

    def decide(self, action, decision="confirmed"):
        return self.client.post(f"/api/actions/{action['id']}", json={"decision": decision})

    def sql(self, statement, *values):
        with sqlite3.connect(self.path) as connection:
            return connection.execute(statement, values).fetchall()

    def past(self, title, start="09:00", status="done", minutes=60):
        """Record a task yesterday, reported as `status`."""
        made = self.client.post("/api/daily-items", json=self.task(title, start, minutes)).json()
        self.sql("UPDATE daily_items SET item_date = ?, completion_status = ? WHERE id = ?", self.yesterday, status, made["id"])
        return made

    def planned_yesterday(self, *titles):
        """Set a plan with untimed `titles`, all reported done, then move the day to yesterday."""
        made = [self.client.post("/api/daily-items", json=self.task(title, None, 60)).json() for title in titles]
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": plan["variants"][0]["id"]})
        self.sql("UPDATE daily_items SET item_date = ?, completion_status = 'done'", self.yesterday)
        self.sql("UPDATE plan_entries SET completion_status = 'done'")
        self.sql("UPDATE plan_sets SET plan_date = ?", self.yesterday)
        self.sql("UPDATE daily_confirmations SET plan_date = ?", self.yesterday)
        return made

    def test_a_past_tasks_start_length_and_timing_are_locked(self):
        review = self.past("Review")
        for message in ("Move Review to 11:00", "Review took 45 minutes", f"Move Review to {TWO_DAYS_AGO}"):
            reply = self.chat(self.yesterday, message)

            self.assertIsNone(reply["proposedAction"], message)
            self.assertIn("Nothing was changed.", reply["assistantMessage"]["content"], message)
        self.assertIn("a task keeps its place", self.chat(self.yesterday, "Move Review to 11:00")["assistantMessage"]["content"])
        self.assertIn("can't move onto a past day",
                      self.chat(self.yesterday, f"Move Review to {TWO_DAYS_AGO}")["assistantMessage"]["content"])
        stored = self.store.daily_item(review["id"])
        self.assertEqual((stored["date"], stored["start_time"], stored["duration_minutes"]), (self.yesterday, "09:00", 60))

    def test_a_mixed_request_proposes_only_the_allowed_part_and_names_the_rest(self):
        self.past("Review")

        action = self.chat(self.yesterday, "Review took 45 minutes and was partly done")["proposedAction"]

        self.assertEqual((action["payload"]["changes"], action["payload"]["leftOut"]), ({"status": "partial"}, ["durationMinutes"]))
        self.assertIn("Left out: its length, as a past task keeps its place.", action["explanation"])

    def test_the_service_refuses_placement_changes_on_a_past_task(self):
        review = self.past("Review")
        thread = self.store.thread()
        for changes in ({"startTime": "11:00"}, {"durationMinutes": 45}, {"date": TWO_DAYS_AGO}):
            action = self.store.propose_action(thread, "edit_item", {
                "date": self.yesterday, "itemId": review["id"], "title": "Review", "changes": changes,
                "before": {}, "proposedBy": "orchestrator"}, "test")

            self.assertEqual(self.decide(action).status_code, 409, changes)
        stored = self.store.daily_item(review["id"])
        self.assertEqual((stored["date"], stored["start_time"], stored["duration_minutes"]), (self.yesterday, "09:00", 60))

    def test_moving_a_past_task_forward_marks_its_entry_and_counts_it_on_its_new_day(self):
        review, piano = self.planned_yesterday("Review", "Piano")
        self.client.post("/api/summaries", params={"date": self.yesterday})

        action = self.chat(self.yesterday, "Move Review to today at 15:00")["proposedAction"]

        self.assertEqual(action["payload"]["changes"], {"date": self.today, "startTime": "15:00", "status": "planned"})
        self.assertEqual(self.decide(action).status_code, 200)
        moved = self.store.daily_item(review["id"])
        self.assertEqual((moved["date"], moved["start_time"], moved["constraint_kind"], moved["completion_status"]),
                         (self.today, "15:00", "fixed", "planned"))
        kept = self.client.get("/api/bootstrap", params={"date": self.yesterday}).json()["entries"]
        self.assertEqual(sorted((entry["title"], entry["removed"], entry["moved_to"]) for entry in kept),
                         [("Piano", False, None), ("Review", True, self.today)])
        month = {day["date"]: day for day in self.client.get("/api/calendar", params={"month": self.today[:7]}).json()["days"]}
        self.assertEqual((month[self.yesterday]["entryCount"], month[self.yesterday]["doneCount"]), (1, 1))
        self.assertEqual(month[self.today]["managedCount"], 1)
        reports = self.client.post("/api/summaries", params={"date": self.yesterday}).json()["reports"]
        self.assertEqual(reports["day"]["domains"]["learning"]["scheduled"], 1)
        self.assertNotIn(("learning", "review"), self.store.task_profiles("learning"))
        self.assertTrue(piano)

    def test_a_task_moved_to_today_is_placed_with_the_overlap_and_meal_checks(self):
        self.past("Review")
        self.client.post("/api/daily-items", json=self.task("Call", "15:00", 60))

        clash = self.chat(self.yesterday, "Move Review to today at 15:30")
        meal = self.chat(self.yesterday, "Move Review to today at 12:15")

        self.assertIsNone(clash["proposedAction"])
        self.assertIn("“Call”", clash["assistantMessage"]["content"])
        self.assertIsNone(meal["proposedAction"])
        self.assertIn("lunch", meal["assistantMessage"]["content"])

    def test_a_move_onto_a_day_that_already_has_the_repeats_day_is_refused(self):
        stretch = self.past("Stretch", "07:30", minutes=30)
        self.sql("UPDATE daily_items SET repeat_kind = 'daily', repeat_series_id = 'series-1' WHERE id = ?", stretch["id"])
        today = self.client.post("/api/daily-items", json={**self.task("Stretch", "07:30", 30), "repeatKind": "daily"}).json()
        self.sql("UPDATE daily_items SET repeat_series_id = 'series-1' WHERE id = ?", today["id"])

        reply = self.chat(self.yesterday, "Move Stretch to today")

        self.assertIsNone(reply["proposedAction"])
        self.assertIn("already has its repeat's day", reply["assistantMessage"]["content"])

    def test_a_task_moved_to_today_joins_todays_drafts_when_no_plan_is_set(self):
        self.past("Review", None)
        self.client.post("/api/daily-items", json=self.task("Walk", None, 30))
        self.client.post("/api/plan/generate", json={"date": self.today})

        self.decide(self.chat(self.yesterday, "Move Review to today")["proposedAction"])

        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        drafted = {title for (title,) in self.sql(
            "SELECT e.title FROM plan_entries e JOIN plan_variants v ON v.id = e.variant_id WHERE v.id = ?",
            day["variants"][0]["id"])}
        self.assertEqual(drafted, {"Review", "Walk"})


    def test_a_past_plans_time_by_area_leaves_out_removed_and_moved_entries_still_listed(self):
        review, piano, notes = self.planned_yesterday("Review", "Piano", "Notes")

        self.client.delete(f"/api/daily-items/{piano['id']}")
        removed = self.client.get("/api/bootstrap", params={"date": self.yesterday}).json()
        self.decide(self.chat(self.yesterday, "Move Review to today")["proposedAction"])
        moved = self.client.get("/api/bootstrap", params={"date": self.yesterday}).json()

        self.assertEqual((removed["balance"]["learning"], moved["balance"]["learning"]), (120, 60))
        self.assertEqual(sorted((entry["title"], entry["removed"]) for entry in moved["entries"]),
                         [("Notes", False), ("Piano", True), ("Review", True)])
        self.assertTrue(notes)

    def test_deleting_a_task_today_rewrites_every_draft_without_it(self):
        for title, domain, minutes in (("Read", "learning", 60), ("Notes", "learning", 30), ("Walk", "life", 30),
                                       ("Draft", "work", 90)):
            self.client.post("/api/daily-items", json={**self.task(title, None, minutes), "domain": domain})
        made = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        before = {variant["id"]: dict(self.sql("SELECT title, start_time FROM plan_entries WHERE variant_id = ?", variant["id"]))
                  for variant in made["variants"]}
        read = next(item for item in made["dayItems"] if item["title"] == "Read")

        self.client.delete(f"/api/daily-items/{read['id']}")

        for variant in made["variants"]:
            shown = self.client.get("/api/bootstrap", params={"date": self.today, "variant_id": variant["id"]}).json()
            drafted = next(row for row in shown["variants"] if row["id"] == variant["id"])
            self.assertNotIn("Read", drafted["rationale"], variant["name"])
            self.assertNotIn("Read", str(drafted["notes"]), variant["name"])
            left = dict(self.sql("SELECT title, start_time FROM plan_entries WHERE variant_id = ?", variant["id"]))
            self.assertEqual(left, {title: start for title, start in before[variant["id"]].items() if title != "Read"})
            self.assertEqual(shown["balance"]["learning"], 30, variant["name"])


if __name__ == "__main__":
    unittest.main()
