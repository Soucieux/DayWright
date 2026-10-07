import sqlite3
import unittest
from datetime import datetime

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.learning_tasks import LearningTasks
from backend.tests.test_time_record import TimeDay


class CatchUpDay(TimeDay):
    """Today's and yesterday's tasks, caught up on several at once: on Today's sheet or through Ava."""

    def catch_up(self, clock, statuses):
        with self.at(clock):
            return self.client.post("/api/catch-up", json={"statuses": statuses})

    def undo(self, clock="16:01"):
        with self.at(clock):
            return self.client.post("/api/catch-up/undo")

    def chat(self, message, day=None, clock="16:00"):
        with self.at(clock):
            return self.client.post("/api/chat", json={"date": day or self.today, "message": message}).json()

    def confirm(self, action, statuses=None, clock="16:05"):
        body = {"decision": "confirmed", **({"statuses": statuses} if statuses is not None else {})}
        with self.at(clock):
            decided = self.client.post(f"/api/actions/{action['id']}", json=body)
        self.assertEqual(decided.status_code, 200, decided.text)
        return decided.json()

    def to_yesterday(self, item, domain=None):
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE daily_items SET item_date = ?, domain = COALESCE(?, domain) WHERE id = ?",
                               (self.yesterday, domain, item["id"]))
        return item

    def studied(self, title, *parts):
        """Today's Learning task without a start time, with a checklist of its own and nothing ticked."""
        made = self.add(title, None, 45)
        learning = LearningTasks(self.store, None)
        for part in parts:
            learning.add_to_checklist(made["id"], part, datetime.now().astimezone())
        return made

    def status(self, item):
        return self.store.daily_item(item["id"])["completion_status"]

    def offers(self):
        return [notice for notice in self.store.notices() if notice["kind"] == "continue-offer"]


class CatchUpSheetTests(CatchUpDay):
    def test_the_sheet_lists_every_task_today_with_its_status_now(self):
        review, email, read = self.add("Review", "14:00"), self.add("Email Anna", "15:30", 30), self.add("Read", None, 45)
        self.add("Later", "09:00", day=self.tomorrow)
        self.report(email, "skipped", "15:40")

        for clock, late in (("16:00", False), ("22:00", True)):
            with self.at(clock):
                listed = self.client.get("/api/catch-up").json()
            self.assertEqual(listed["date"], self.today)
            self.assertEqual([(task["id"], task["start"], task["status"], task["noReply"]) for task in listed["tasks"]],
                             [(review["id"], "14:00", "planned", late), (email["id"], "15:30", "skipped", False),
                              (read["id"], None, "planned", late)], clock)

    def test_one_save_sets_mixed_statuses_each_with_the_time_it_would_have_alone(self):
        review, email, read = self.add("Review", "14:00"), self.add("Email Anna", "15:30", 30), self.add("Read", None, 45)

        saved = self.catch_up("16:00", {review["id"]: "done", email["id"]: "skipped", read["id"]: "partial"})

        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()["updated"], 3)
        # Review was interrupted at Email Anna's start, still running at the save, and keeps that stretch; Email Anna
        # was running and ends at the save; Read was current between lunch and Review.
        self.assertEqual(self.timing(review), ("done", "16:00", "14:00", "15:30"))
        self.assertEqual(self.timing(email), ("skipped", "16:00", "15:30", "16:00"))
        self.assertEqual(self.timing(read), ("partial", "16:00", "13:00", "14:00"))

    def test_a_task_left_as_it_is_and_one_marked_as_it_was_are_not_changed(self):
        review, email = self.add("Review", "14:00"), self.add("Email Anna", "15:30", 30)
        self.report(review, "done", "14:50")

        saved = self.catch_up("16:00", {review["id"]: "done"})

        self.assertEqual(saved.json()["updated"], 0)
        self.assertEqual(self.timing(review), ("done", "14:50", "14:00", "14:50"))
        self.assertEqual(self.timing(email), ("planned", None, None, None))

    def test_re_marking_keeps_the_time_and_undo_restores_statuses_and_times(self):
        review, email = self.add("Review", "14:00"), self.add("Email Anna", "15:30", 30)
        self.report(review, "done", "14:50")

        self.catch_up("16:00", {review["id"]: "partial", email["id"]: "done"})
        self.assertEqual(self.timing(review), ("partial", "14:50", "14:00", "14:50"))
        self.assertEqual(self.timing(email), ("done", "16:00", "15:30", "16:00"))

        undone = self.undo()
        self.assertEqual(undone.status_code, 200, undone.text)
        self.assertEqual(undone.json()["restored"], 2)
        self.assertEqual(self.timing(review), ("done", "14:50", "14:00", "14:50"))
        self.assertEqual(self.timing(email), ("planned", None, None, None))
        self.assertEqual(self.undo().status_code, 409, "only the last save, once")

    def test_undo_leaves_a_task_changed_again_since_the_save(self):
        review, email = self.add("Review", "14:00"), self.add("Email Anna", "15:30", 30)
        self.catch_up("16:00", {review["id"]: "done", email["id"]: "done"})
        self.report(email, "skipped", "16:00")

        self.assertEqual(self.undo().json()["restored"], 1)

        self.assertEqual(self.timing(review), ("planned", None, None, None))
        self.assertEqual(self.timing(email), ("skipped", "16:00", "15:30", "16:00"))

    def test_a_plans_entry_follows_and_undo_restores_it(self):
        read = self.add("Read", None, 45)
        plans = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": plans["variants"][0]["id"]})

        def entry_status():
            return next(entry["completion_status"] for entry in self.client.get("/api/bootstrap", params={"date": self.today}).json()["entries"]
                        if entry["source_item_id"] == read["id"])

        self.catch_up("16:00", {read["id"]: "done"})
        self.assertEqual(entry_status(), "done")
        self.undo()
        self.assertEqual(entry_status(), "planned")

    def test_only_todays_tasks_and_only_done_partly_done_or_skip(self):
        later = self.add("Review", "14:00", day=self.tomorrow)
        today = self.add("Read", None, 45)

        self.assertEqual(self.catch_up("16:00", {today["id"]: "done", later["id"]: "done"}).status_code, 409)
        self.assertEqual(self.catch_up("16:00", {today["id"]: "planned"}).status_code, 422, "as is is left out")
        self.assertEqual(self.catch_up("16:00", {"missing": "done"}).status_code, 404)
        self.assertEqual(self.timing(today), ("planned", None, None, None), "a refused save changes nothing")
        self.assertEqual(self.undo().status_code, 409, "nothing to undo")


class AvaCatchUpTests(CatchUpDay):
    def day_of_five(self):
        tasks = {}
        for order, (title, start) in enumerate((("Gym", "11:00"), ("Review", "09:00"), ("Email", "10:00"),
                                                ("Stretch", None), ("Reading", None))):
            tasks[title] = self.add(title, start, 30)
            self.made(tasks[title]["id"], f"{self.yesterday}T08:0{order}:00+00:00")
        return tasks

    def test_the_sentence_becomes_one_card_of_every_task_applied_on_confirm(self):
        tasks = self.day_of_five()

        reply = self.chat("Did Review and Email, skipped Gym, half of Reading")

        action = reply["proposedAction"]
        self.assertEqual(action["actionType"], "catch_up")
        self.assertEqual([(task["title"], task["status"], task["to"]) for task in action["payload"]["tasks"]],
                         [("Review", "planned", "done"), ("Email", "planned", "done"), ("Gym", "planned", "skipped"),
                          ("Stretch", "planned", None), ("Reading", "planned", "partial")],
                         "every task in time order, untimed last in the order they were made")
        self.assertEqual(self.status(tasks["Review"]), "planned", "nothing changes before Confirm")

        self.confirm(action)

        self.assertEqual({title: self.status(task) for title, task in tasks.items()},
                         {"Review": "done", "Email": "done", "Gym": "skipped", "Reading": "partial", "Stretch": "planned"})
        self.assertEqual(self.timing(tasks["Gym"])[1], "16:05", "today's statuses are set when confirmed")

    def test_the_card_applies_the_choices_changed_on_it(self):
        tasks = self.day_of_five()
        action = self.chat("Did Review and Email, skipped Gym")["proposedAction"]

        self.confirm(action, {tasks["Review"]["id"]: "done", tasks["Stretch"]["id"]: "skipped"})

        self.assertEqual({title: self.status(task) for title, task in tasks.items()},
                         {"Review": "done", "Email": "planned", "Gym": "planned", "Reading": "planned", "Stretch": "skipped"})

    def test_chinese_and_one_task_named_alone_keeps_the_status_controls_answer(self):
        tasks = self.day_of_five()
        action = self.chat("做完了 Review 和 Email，跳过了 Gym，Reading 做了一半")["proposedAction"]
        self.assertEqual({task["title"]: task["to"] for task in action["payload"]["tasks"]},
                         {"Review": "done", "Email": "done", "Gym": "skipped", "Reading": "partial", "Stretch": None})
        alone = self.chat("I finished Review")
        self.assertIsNone(alone["proposedAction"])
        self.assertEqual(self.status(tasks["Review"]), "planned")

    def test_a_change_or_a_question_naming_several_tasks_is_not_a_catch_up(self):
        self.day_of_five()
        for message in ("Did I finish Review and Email?", "Review is done, move Email to 17:00"):
            action = self.chat(message)["proposedAction"]
            self.assertNotEqual(action and action["actionType"], "catch_up", message)

    def test_catch_up_alone_lists_every_task_as_it_is(self):
        review, read = self.add("Review", "09:00"), self.add("Read", None, 45)
        self.report(review, "done", "09:50")

        action = self.chat("Catch up")["proposedAction"]

        self.assertEqual(action["payload"]["date"], self.today)
        self.assertEqual([(task["title"], task["status"], task["to"], task["noReply"]) for task in action["payload"]["tasks"]],
                         [("Review", "done", None, False), ("Read", "planned", None, False)])

    def test_catching_up_on_yesterday_from_today_reads_no_reply_and_is_kept_as_after_the_day(self):
        journal = self.to_yesterday(self.add("Journal", "09:00", 30))
        walk = self.to_yesterday(self.add("Walk", "10:00", 30))

        action = self.chat("Catch up on yesterday")["proposedAction"]

        self.assertEqual(action["payload"]["date"], self.yesterday)
        self.assertEqual([(task["title"], task["noReply"]) for task in action["payload"]["tasks"]],
                         [("Journal", True), ("Walk", True)])
        self.confirm(action, {journal["id"]: "done"})
        self.assertEqual(self.timing(journal)[:2], ("done", "24:00"))
        self.assertEqual(self.timing(walk), ("planned", None, None, None))

    def test_the_next_day_notices_sentences_in_both_languages_catch_up_on_yesterday(self):
        self.to_yesterday(self.add("Journal", "09:00", 30))
        for message in ("Catch up on yesterday", "补记昨天"):
            action = self.chat(message)["proposedAction"]
            self.assertEqual((action["actionType"], action["payload"]["date"]), ("catch_up", self.yesterday), message)

    def test_a_later_day_is_not_caught_up(self):
        self.add("Review", "14:00", day=self.tomorrow)
        reply = self.chat("Catch up", day=self.tomorrow)
        self.assertIsNone(reply["proposedAction"])
        self.assertIn("today and earlier days", reply["assistantMessage"]["content"])

    def test_a_card_with_a_task_changed_since_applies_the_rest_and_a_moved_task_is_left(self):
        review, email = self.add("Review", "09:00"), self.add("Email", "10:00")
        action = self.chat("Did Review and Email")["proposedAction"]
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE daily_items SET item_date = ? WHERE id = ?", (self.tomorrow, email["id"]))
        self.confirm(action)
        self.assertEqual((self.status(review), self.status(email)), ("done", "planned"))


class ContinueOfferTests(CatchUpDay):
    def test_a_partly_done_learning_task_with_items_left_gets_one_continue_card_from_the_sheet(self):
        study = self.studied("Study chapter 4", "Part one", "Part two")
        done = self.studied("Study chapter 5", "Part one")

        self.catch_up("16:00", {study["id"]: "partial", done["id"]: "done"})
        withdrawn = self.offers()[0]["proposal"]["id"]
        self.undo()
        self.assertEqual(self.offers(), [], "Undo withdraws the offer its save posted")
        with sqlite3.connect(self.path) as connection:
            self.assertIsNone(connection.execute("SELECT 1 FROM proposed_actions WHERE id = ?", (withdrawn,)).fetchone())
        self.catch_up("16:10", {study["id"]: "partial"})

        offers = self.offers()
        self.assertEqual(len(offers), 1, "one offer, for the partly done task")
        offer = offers[0]
        self.assertEqual((offer["agentKey"], offer["values"]["taskTitle"]), ("learning", "Study chapter 4"))
        self.assertEqual((offer["proposal"]["actionType"], offer["proposal"]["status"]), ("add_item", "pending"))
        self.assertEqual(offer["proposal"]["payload"]["continues"]["itemId"], study["id"])
        self.assertEqual(offer["proposal"]["payload"]["left"], ["Part one", "Part two"])

    def test_avas_card_brings_the_offer_too_and_none_without_items_left(self):
        study = self.studied("Study chapter 4", "Part one")
        plain = self.add("Read", None, 45)
        action = self.chat("Half of Study chapter 4, half of Read")["proposedAction"]

        self.confirm(action)

        self.assertEqual([offer["values"]["taskTitle"] for offer in self.offers()], ["Study chapter 4"])
        self.assertEqual(self.status(plain), "partial")
        self.assertEqual(self.status(study), "partial")


class CarryForwardTests(CatchUpDay):
    """Not catching up never blocks carrying work forward: yesterday's tasks with no status still move on."""

    def test_continue_next_session_needs_no_status(self):
        study = self.to_yesterday(self.studied("Study chapter 4", "Part one", "Part two"))

        reply = self.chat("Continue “Study chapter 4” next session", day=self.yesterday)

        action = reply["proposedAction"]
        self.assertEqual((action["actionType"], action["payload"]["date"]), ("add_item", self.today))
        created = self.confirm(action)["created"][0]
        self.assertEqual(self.store.daily_item(created["id"])["date"], self.today)
        self.assertEqual(self.status(study), "planned")

    def test_avas_move_to_today_needs_no_status(self):
        email = self.to_yesterday(self.add("Email Anna", "15:00", 30))

        action = self.chat("Move Email Anna to today", day=self.yesterday)["proposedAction"]

        self.assertEqual(action["payload"]["changes"]["date"], self.today)
        self.confirm(action)
        self.assertEqual(self.store.daily_item(email["id"])["date"], self.today)

    def test_works_carry_overs_list_a_task_with_no_status(self):
        email = self.to_yesterday(self.add("Email Anna", "15:00", 30), domain="work")

        carried = self.client.get("/api/areas/work", params={"date": self.today}).json()["carryOvers"]

        self.assertEqual([(item["id"], item["status"]) for item in carried], [(email["id"], "planned")])


if __name__ == "__main__":
    unittest.main()
