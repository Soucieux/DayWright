import json
import sqlite3
import tempfile
import threading
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.database import Database, move_topics_to_tasks
from backend.app.domain_records import DomainRecords
from backend.app.learning_tasks import LearningTasks
from backend.app.retrieval import VectorStore
from backend.app.sources import SourceError, study_minutes, study_profile
from backend.tests.test_source_store import ShelfDay
from backend.tests.test_sources import LESSON

TODAY = date.today().isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
PAGE = {"title": "Signals atlas", "briefing": "A field guide to signals in Angular.",
        "outline": [{"title": "Signals", "topics": [{"title": "Writable"}, {"title": "Computed"}]},
                    {"title": "Effects", "topics": [{"title": "When effects run"}]}]}
GROWN = {**PAGE, "briefing": "A longer field guide to signals.",
         "outline": PAGE["outline"] + [{"title": "Interop", "topics": [{"title": "toSignal"}, {"title": "toObservable"},
                                                                       {"title": "Zones"}, {"title": "Testing"}]}]}


def at(day: str, clock: str) -> datetime:
    """A local time on a day, as the start check reads the clock."""
    return datetime.fromisoformat(f"{day}T{clock}")


class LearningDay(ShelfDay):
    """A connected throwaway folder, a saved website, and learning tasks made from them."""

    def setUp(self):
        super().setUp()
        self.learning = LearningTasks(self.store, self.shelf)
        self.folder_record = self.connect()
        self.lesson = next(source for source in self.folder_record["sources"] if source["title"] == "Consuming HTTP Services")
        self.basics = next(source for source in self.folder_record["sources"] if source["title"] == "Basics")

    def item(self, item_id):
        return self.store.daily_item(item_id)

    def website(self, page=PAGE):
        site = self.shelf.add_website("https://atlas.example/", "", "learning")
        with patch("backend.app.source_store.fetch_page", return_value=page):
            self.shelf.look_up(site["id"])
        return self.shelf.source(site["id"])

    def goal(self, title):
        return next(goal for goal in self.store.goals() if goal["title"] == title)

    def entry(self, item_id, title):
        """A checklist item's id, by its title."""
        return next(entry["id"] for entry in self.learning.task(item_id)["checklist"] if entry["title"] == title)

    def tick(self, item_id, title, done=True, now=None, **options):
        return self.learning.tick(item_id, self.entry(item_id, title), done, now or at(TODAY, "10:00"), **options)

    def as_form(self, item_id):
        """A task as its form sends it back unchanged."""
        item = self.item(item_id)
        return {"date": item["date"], "title": item["title"], "detail": item["detail"], "goalId": item["goalId"],
                "domain": item["domain"], "startTime": item["start_time"], "durationMinutes": item["duration_minutes"],
                "constraintKind": item["constraint_kind"], "repeatKind": item["repeatKind"], "status": None}


class EntryTests(LearningDay):
    def test_a_folder_lists_each_file_once_with_the_sections_it_covers(self):
        entries = self.learning.entries(folder_id=self.folder_record["id"])

        self.assertEqual([(entry["title"], entry["sections"]) for entry in entries],
                         [("Basics", []), ("Consuming HTTP Services", ["HttpClient setup", "Interceptors", "Error handling"])])

    def test_one_source_is_one_entry_and_a_website_must_be_looked_up_first(self):
        (self.folder / "guide.md").write_text("# Routing\n\n## Guards\n\n# Forms\n\n## Validation\n", encoding="utf-8")
        self.shelf.refresh(self.folder_record["id"])
        guide = next(item for item in self.shelf.folders()[0]["sources"] if item["relativePath"] == "guide.md")

        self.assertEqual([(entry["title"], entry["sections"]) for entry in self.learning.entries(source_id=guide["id"])],
                         [("Routing", ["Guards", "Validation"])], "one task covers the whole file")
        site = self.shelf.add_website("https://atlas.example/", "", "learning")
        with self.assertRaises(SourceError):
            self.learning.entries(source_id=site["id"])

    def test_each_entry_shows_its_latest_pass_so_far(self):
        task_id = self.learning.create_tasks([self.lesson["id"]], TODAY)["tasks"][0]["id"]
        self.tick(task_id, "Interceptors", now=at(TODAY, "09:00"))

        progress = {entry["title"]: entry["progress"] for entry in self.learning.entries(folder_id=self.folder_record["id"])}
        self.assertEqual(progress, {"Basics": None, "Consuming HTTP Services": {"done": 1, "total": 3}})
        self.assertEqual(self.learning.progress_by_source(), {self.lesson["id"]: {"done": 1, "total": 3}})

    def test_without_second_level_headings_the_first_level_ones_below_the_title_are_the_checklist(self):
        (self.folder / "chapters.md").write_text("# Signals\n\nIntro.\n\n# Writable\n\n# Computed\n", encoding="utf-8")
        (self.folder / "plain.md").write_text("Just some words, no headings.\n", encoding="utf-8")
        self.shelf.refresh(self.folder_record["id"])
        found = {item["relativePath"]: item for item in self.shelf.folders()[0]["sources"]}

        self.assertEqual([(entry["title"], entry["sections"]) for entry in self.learning.entries(source_id=found["chapters.md"]["id"])],
                         [("Signals", ["Writable", "Computed"])])
        self.assertEqual([(entry["title"], entry["sections"]) for entry in self.learning.entries(source_id=found["plain.md"]["id"])],
                         [("plain", [])], "no headings, no checklist")
        task_id = self.learning.create_tasks([found["plain.md"]["id"]], TODAY)["tasks"][0]["id"]
        self.assertEqual((self.learning.task(task_id)["checklist"], self.learning.task(task_id)["progress"]),
                         ([], {"done": 0, "total": 0}))


class CreateTests(LearningDay):
    def test_each_ticked_file_becomes_one_untimed_learning_task_estimated_from_its_whole_text(self):
        made = self.learning.create_tasks([self.lesson["id"], self.basics["id"]], TOMORROW)

        self.assertEqual([task["title"] for task in made["tasks"]], ["Consuming HTTP Services", "Basics"])
        self.assertIsNone(made["goal"])
        lesson = self.item(made["tasks"][0]["id"])
        profile = study_profile(LESSON)
        self.assertEqual((lesson["date"], lesson["domain"], lesson["start_time"], lesson["goalId"], lesson["repeatKind"]),
                         (TOMORROW, "learning", None, None, "none"))
        self.assertEqual((lesson["duration_minutes"], lesson["durationSource"]), (study_minutes(profile), "estimate"))
        learned = self.learning.task(lesson["id"])
        self.assertEqual((learned["sourceId"], learned["sections"], learned["effort"], learned["effortBy"]),
                         (self.lesson["id"], ["HttpClient setup", "Interceptors", "Error handling"], profile["effort"], "text"))
        self.assertIsNone(self.shelf.source(self.lesson["id"])["goalId"], "an ungrouped source joins no goal")

    def test_ticked_files_can_join_a_new_goal_or_an_existing_learning_one(self):
        made = self.learning.create_tasks([self.basics["id"], self.lesson["id"]], TODAY, {"title": "Angular"})
        goal = self.goal("Angular")
        self.assertEqual(made["goal"]["id"], goal["id"])
        self.assertEqual([item["title"] for item in goal["linkedItems"]], ["Basics", "Consuming HTTP Services"])
        self.assertEqual(self.shelf.source(self.lesson["id"])["goalId"], goal["id"], "a grouped source joins its goal")

        again = self.learning.create_tasks([self.basics["id"]], TOMORROW, {"goalId": goal["id"]})
        self.assertEqual(self.item(again["tasks"][0]["id"])["goalId"], goal["id"])

        work = self.store.create_goal("Ship it", "work")
        for choice in ({"title": "Angular"}, {"goalId": work["id"]}, {"goalId": "goal_none"}):
            with self.assertRaises(SourceError):
                self.learning.create_tasks([self.basics["id"]], TODAY, choice)
        with self.assertRaises(SourceError):
            self.learning.create_tasks([], TODAY)

    def test_several_files_go_all_on_one_day_or_one_a_day_in_their_order(self):
        together = self.learning.create_tasks([self.basics["id"], self.lesson["id"]], TOMORROW)
        self.assertEqual([self.item(task["id"])["date"] for task in together["tasks"]], [TOMORROW, TOMORROW])

        spread = self.learning.create_tasks([self.lesson["id"], self.basics["id"]], TOMORROW, one_a_day=True)
        after = (date.today() + timedelta(days=2)).isoformat()
        self.assertEqual([(self.item(task["id"])["title"], self.item(task["id"])["date"]) for task in spread["tasks"]],
                         [("Consuming HTTP Services", TOMORROW), ("Basics", after)])

    def test_a_website_task_covers_its_headings_and_is_estimated_from_them(self):
        site = self.website()
        made = self.learning.create_tasks([site["id"]], TODAY)

        task = self.item(made["tasks"][0]["id"])
        learned = self.learning.task(task["id"])
        self.assertEqual((task["title"], learned["sections"], learned["effort"]),
                         ("Signals atlas", ["Writable", "Computed", "When effects run"], "steady"))
        self.assertEqual(task["duration_minutes"], 45, "15 minutes a section, at least 30")
        self.assertEqual({entry["addedBy"] for entry in learned["checklist"]}, {"source"})

    def test_a_website_without_second_level_headings_lists_its_first_level_ones_below_the_title(self):
        site = self.website({**PAGE, "outline": [{"title": "Signals atlas", "topics": []}, {"title": "Effects", "topics": []},
                                                 {"title": "Interop", "topics": []}]})
        task_id = self.learning.create_tasks([site["id"]], TODAY)["tasks"][0]["id"]
        self.assertEqual(self.learning.task(task_id)["sections"], ["Effects", "Interop"])

    def test_the_user_sets_a_tasks_effort(self):
        task_id = self.learning.create_tasks([self.lesson["id"]], TODAY)["tasks"][0]["id"]
        learned = self.learning.set_effort(task_id, "deep")
        self.assertEqual((learned["effort"], learned["effortBy"]), ("deep", "you"))
        with self.assertRaises(SourceError):
            self.learning.set_effort(task_id, "heavy")


class StartCheckTests(LearningDay):
    def setUp(self):
        super().setUp()
        self.site = self.website()
        self.task_id = self.learning.create_tasks([self.site["id"]], TODAY)["tasks"][0]["id"]
        with sqlite3.connect(self.store.path) as connection:
            connection.execute("UPDATE daily_items SET start_time = '10:00', constraint_kind = 'fixed' WHERE id = ?",
                               (self.task_id,))

    def check(self, now, page=PAGE):
        with patch("backend.app.source_store.fetch_page", return_value=page) as fetched:
            checked = self.learning.check_due(now)
        return checked, fetched.call_count

    def test_a_timed_task_is_checked_once_at_its_start_and_not_before(self):
        self.assertEqual(self.check(at(TODAY, "09:59")), ([], 0))
        self.assertEqual(self.check(at(TODAY, "10:00")), ([self.task_id], 1))
        self.assertEqual(self.check(at(TODAY, "11:00")), ([], 0), "at most once")
        learned = self.learning.task(self.task_id)
        self.assertEqual((learned["startCheck"], learned["startCheckedAt"][:16]), ("unchanged", f"{TODAY}T10:00"))

    def test_a_check_missed_while_closed_runs_the_next_time_unless_a_status_was_set(self):
        self.assertEqual(self.check(at(TOMORROW, "08:00")), ([self.task_id], 1), "the next time DayWright runs")

        other = self.learning.create_tasks([self.site["id"]], TODAY)["tasks"][0]["id"]
        with sqlite3.connect(self.store.path) as connection:
            connection.execute("""UPDATE daily_items SET item_date = ?, start_time = '09:00', constraint_kind = 'fixed',
                                  completion_status = 'done' WHERE id = ?""", (YESTERDAY, other))
        self.assertEqual(self.check(at(TOMORROW, "09:00")), ([], 0), "a task with a status isn't checked")

    def test_a_changed_page_updates_the_briefing_and_the_estimates_but_never_the_users_length(self):
        followed = self.learning.create_tasks([self.site["id"]], TODAY)["tasks"][0]["id"]
        self.store.update_daily_item(followed, {**self.as_form(followed), "durationMinutes": 50})

        self.check(at(TODAY, "10:05"), GROWN)

        source = self.shelf.source(self.site["id"])
        self.assertEqual((source["briefing"], len(source["outline"])), (GROWN["briefing"], 3))
        self.assertEqual(source["updatedAt"][:16], f"{TODAY}T10:05")
        learned = self.learning.task(self.task_id)
        self.assertEqual((learned["startCheck"], learned["effort"], len(learned["sections"])), ("updated", "deep", 7))
        self.assertEqual(self.item(self.task_id)["duration_minutes"], 105, "an estimate follows the grown page")
        self.assertEqual(self.item(followed)["duration_minutes"], 50, "a length the user set never changes")
        self.assertEqual(len(self.learning.task(followed)["sections"]), 7)

    def test_a_changed_page_merges_into_the_checklist_without_losing_anything(self):
        self.tick(self.task_id, "Writable", now=at(TODAY, "09:30"))
        self.learning.add_to_checklist(self.task_id, "My notes", at(TODAY, "09:31"))
        self.learning.remove_from_checklist(self.task_id, self.entry(self.task_id, "When effects run"), at(TODAY, "09:32"))
        changed = {**PAGE, "outline": [{"title": "Signals", "topics": [{"title": "Writable"}, {"title": "Linked signals"}]},
                                       {"title": "Effects", "topics": [{"title": "When effects run"}]}]}

        self.check(at(TODAY, "10:00"), changed)

        learned = self.learning.task(self.task_id)
        self.assertEqual([(entry["title"], entry["addedBy"], entry["pageState"], bool(entry["tickedAt"]))
                          for entry in learned["checklist"]],
                         [("Writable", "source", "", True), ("Linked signals", "source", "new", False),
                          ("Computed", "source", "gone", False), ("My notes", "you", "", False)],
                         "ticks kept, the new heading added, the vanished one marked, the user's item and removal kept")
        self.assertEqual(self.learning.follow_up(self.task_id, TOMORROW)["left"], ["Linked signals", "My notes"],
                         "an item no longer on the page stays listed but isn't left to study")

    def test_a_renamed_item_still_matches_its_heading(self):
        self.learning.rename_in_checklist(self.task_id, self.entry(self.task_id, "Computed"), "Computed values", at(TODAY, "09:00"))
        self.check(at(TODAY, "10:00"), {**PAGE, "briefing": "A fresher guide to signals."})
        self.assertEqual(self.learning.task(self.task_id)["startCheck"], "updated")
        learned = self.learning.task(self.task_id)
        self.assertEqual([(entry["title"], entry["pageState"]) for entry in learned["checklist"]],
                         [("Writable", ""), ("Computed values", ""), ("When effects run", "")])

    def test_an_unreachable_site_keeps_what_was_stored_and_says_so(self):
        with patch("backend.app.source_store.fetch_page", side_effect=SourceError("The website could not be reached.")):
            self.assertEqual(self.learning.check_due(at(TODAY, "10:01")), [self.task_id])
        self.assertEqual(self.shelf.source(self.site["id"])["briefing"], PAGE["briefing"])
        self.assertEqual(self.learning.task(self.task_id)["startCheck"], "unreachable")
        self.assertEqual([entry["pageState"] for entry in self.learning.task(self.task_id)["checklist"]], ["", "", ""])

    def test_an_untimed_task_is_checked_when_its_briefing_is_first_opened_on_its_day(self):
        untimed = self.learning.create_tasks([self.site["id"]], TOMORROW)["tasks"][0]["id"]
        with patch("backend.app.source_store.fetch_page", return_value=PAGE) as fetched:
            self.learning.briefing_opened(untimed, at(TODAY, "12:00"))
            self.assertEqual(fetched.call_count, 0, "not before its day")
            self.learning.briefing_opened(untimed, at(TOMORROW, "08:00"))
            self.learning.briefing_opened(untimed, at(TOMORROW, "09:00"))
            self.assertEqual(fetched.call_count, 1, "once, the first time on its day")
            self.assertEqual(self.learning.check_due(at(TOMORROW, "23:00")), [self.task_id],
                             "only the timed task is due; an untimed one waits for its briefing")
        self.assertEqual(fetched.call_count, 2)

    def test_two_opens_at_once_look_the_website_up_once(self):
        untimed = self.learning.create_tasks([self.site["id"]], TODAY)["tasks"][0]["id"]
        with patch("backend.app.source_store.fetch_page", return_value=PAGE) as fetched:
            racing = [threading.Thread(target=self.learning.briefing_opened, args=(untimed, at(TODAY, "08:00"))) for _ in range(4)]
            for thread in racing:
                thread.start()
            for thread in racing:
                thread.join()
        self.assertEqual(fetched.call_count, 1, "the first open claims the check")

    def test_a_folder_task_is_never_looked_up(self):
        lesson = self.learning.create_tasks([self.lesson["id"]], TODAY)["tasks"][0]["id"]
        with sqlite3.connect(self.store.path) as connection:
            connection.execute("UPDATE daily_items SET start_time = '08:00', constraint_kind = 'fixed' WHERE id = ?", (lesson,))
        with patch("backend.app.source_store.fetch_page", side_effect=AssertionError("no lookup")):
            self.learning.briefing_opened(lesson, at(TODAY, "09:00"))
        self.assertIsNone(self.learning.task(lesson)["startCheckedAt"])


class ChecklistTests(LearningDay):
    def setUp(self):
        super().setUp()
        self.task_id = self.learning.create_tasks([self.lesson["id"]], TODAY, {"title": "Angular"})["tasks"][0]["id"]

    def test_the_sections_are_a_checklist_ticked_and_unticked_and_kept_with_their_time(self):
        learned = self.learning.task(self.task_id)
        self.assertEqual((learned["ticked"], learned["progress"]), ([], {"done": 0, "total": 3}))

        learned = self.tick(self.task_id, "Interceptors", now=at(TODAY, "10:30"))
        self.assertEqual((learned["ticked"], learned["progress"]), (["Interceptors"], {"done": 1, "total": 3}))
        ticked = next(entry for entry in learned["checklist"] if entry["title"] == "Interceptors")
        self.assertEqual((ticked["tickedAt"], ticked["tickedOn"]), (at(TODAY, "10:30").isoformat(), self.task_id))

        self.assertEqual(self.tick(self.task_id, "Interceptors", False, at(TODAY, "10:31"))["ticked"], [])
        with self.assertRaises(SourceError):
            self.learning.tick(self.task_id, "check_none", True, at(TODAY, "10:32"))

    def test_ticking_every_section_suggests_done_but_never_marks_it(self):
        for section in ("HttpClient setup", "Interceptors", "Error handling"):
            learned = self.tick(self.task_id, section, now=at(TODAY, "11:00"))
        self.assertTrue(learned["allTicked"])
        self.assertEqual(self.item(self.task_id)["completion_status"], "planned", "only the user marks it done")

    def test_a_past_tasks_checklist_changes_only_through_ava(self):
        with sqlite3.connect(self.store.path) as connection:
            connection.execute("UPDATE daily_items SET item_date = ? WHERE id = ?", (YESTERDAY, self.task_id))
        with self.assertRaises(PermissionError):
            self.tick(self.task_id, "Interceptors", now=at(TODAY, "09:00"))
        learned = self.tick(self.task_id, "Interceptors", now=at(TODAY, "09:00"), confirmed=True)
        self.assertEqual(learned["ticked"], ["Interceptors"], "Ava's confirmed card ticks it")
        entry = self.entry(self.task_id, "Error handling")
        for change in (lambda: self.learning.add_to_checklist(self.task_id, "More", at(TODAY, "09:00")),
                       lambda: self.learning.rename_in_checklist(self.task_id, entry, "Errors", at(TODAY, "09:00")),
                       lambda: self.learning.remove_from_checklist(self.task_id, entry, at(TODAY, "09:00")),
                       lambda: self.learning.move_in_checklist(self.task_id, entry, 0, at(TODAY, "09:00"))):
            with self.assertRaises(PermissionError):
                change()

    def test_a_follow_up_keeps_the_whole_checklist_with_its_ticks_and_counts_only_whats_left(self):
        self.tick(self.task_id, "HttpClient setup", now=at(TODAY, "10:00"))
        self.learning.add_to_checklist(self.task_id, "Write a retry", at(TODAY, "10:05"))

        follow = self.learning.follow_up(self.task_id, TOMORROW)

        self.assertEqual({key: follow[key] for key in ("title", "date", "goalId", "domain", "startTime", "constraintKind")},
                         {"title": "Consuming HTTP Services", "date": TOMORROW, "goalId": self.goal("Angular")["id"],
                          "domain": "learning", "startTime": None, "constraintKind": "flexible"})
        self.assertEqual(follow["learning"]["followsItemId"], self.task_id)
        self.assertEqual(follow["left"], ["Interceptors", "Error handling", "Write a retry"])
        saved = self.store.create_daily_item({**follow, "detail": "", "repeatKind": "none", "durationMinutes": None})
        later = self.learning.task(saved["id"])
        self.assertEqual((later["sections"], later["sourceId"], later["ticked"], later["progress"]),
                         (["HttpClient setup", "Interceptors", "Error handling", "Write a retry"], self.lesson["id"],
                          ["HttpClient setup"], {"done": 1, "total": 4}), "the whole list, the earlier tick still shown")
        self.assertEqual(later["checklist"][0]["tickedAt"], at(TODAY, "10:00").isoformat())
        self.assertEqual(later["checklist"][3]["addedBy"], "you")
        self.assertEqual(self.item(self.task_id)["completion_status"], "planned", "the original is done only when the user says so")

        self.tick(saved["id"], "Interceptors", now=at(TOMORROW, "10:00"))
        original = self.learning.task(self.task_id)
        self.assertEqual((original["ticked"], original["progress"]), (["HttpClient setup", "Interceptors"], {"done": 2, "total": 4}),
                         "ticks on either task count for the file")

    def test_a_new_task_from_the_file_continues_its_ticks_unless_started_fresh(self):
        self.tick(self.task_id, "HttpClient setup", now=at(TODAY, "10:00"))

        again = self.learning.create_tasks([self.lesson["id"]], TOMORROW)["tasks"][0]["id"]
        self.assertEqual(self.learning.task(again)["ticked"], ["HttpClient setup"], "it continues where they left off")

        fresh = self.learning.create_tasks([self.lesson["id"]], TOMORROW, fresh=True)["tasks"][0]["id"]
        self.assertEqual(self.learning.task(fresh)["ticked"], [], "a revision pass starts clean")
        self.tick(fresh, "Error handling", now=at(TOMORROW, "09:00"))
        self.assertEqual(self.learning.task(self.task_id)["ticked"], ["HttpClient setup"], "the earlier pass keeps its own ticks")
        self.assertEqual(self.learning.progress_by_source()[self.lesson["id"]], {"done": 1, "total": 3},
                         "the file shows its latest pass")

    def test_a_follow_up_is_estimated_from_the_pace_of_the_sections_ticked(self):
        self.store.update_daily_item(self.task_id, {**self.as_form(self.task_id), "durationMinutes": 60})
        self.tick(self.task_id, "HttpClient setup", now=at(TODAY, "10:00"))

        follow = self.learning.follow_up(self.task_id, TOMORROW)

        self.assertEqual(follow["estimateMinutes"], 120, "60 minutes for one section: two left take 120")

    def test_without_a_section_ticked_a_follow_up_is_estimated_from_the_text_left(self):
        follow = self.learning.follow_up(self.task_id, TOMORROW)
        self.assertEqual(follow["left"], ["HttpClient setup", "Interceptors", "Error handling"])
        self.assertLessEqual(follow["estimateMinutes"], self.item(self.task_id)["duration_minutes"])

    def test_nothing_is_left_to_continue_once_every_section_is_ticked(self):
        for section in ("HttpClient setup", "Interceptors", "Error handling"):
            self.tick(self.task_id, section, now=at(TODAY, "11:00"))
        with self.assertRaises(SourceError):
            self.learning.follow_up(self.task_id, TOMORROW)


class EditTests(LearningDay):
    def setUp(self):
        super().setUp()
        self.task_id = self.learning.create_tasks([self.lesson["id"]], TODAY)["tasks"][0]["id"]

    def test_items_are_added_renamed_removed_and_reordered(self):
        now = at(TODAY, "09:00")
        learned = self.learning.add_to_checklist(self.task_id, "  Read the RFC  ", now)
        self.assertEqual([(entry["title"], entry["addedBy"]) for entry in learned["checklist"]][-1], ("Read the RFC", "you"))
        with self.assertRaises(SourceError):
            self.learning.add_to_checklist(self.task_id, "   ", now)

        learned = self.learning.rename_in_checklist(self.task_id, self.entry(self.task_id, "Interceptors"), "Auth interceptors", now)
        renamed = next(entry for entry in learned["checklist"] if entry["title"] == "Auth interceptors")
        self.assertEqual((renamed["heading"], renamed["addedBy"]), ("Interceptors", "source"), "it still came from the source")

        learned = self.learning.move_in_checklist(self.task_id, self.entry(self.task_id, "Read the RFC"), 0, now)
        self.assertEqual(learned["sections"], ["Read the RFC", "HttpClient setup", "Auth interceptors", "Error handling"])
        learned = self.learning.move_in_checklist(self.task_id, self.entry(self.task_id, "HttpClient setup"), 3, now)
        self.assertEqual(learned["sections"], ["Read the RFC", "Auth interceptors", "Error handling", "HttpClient setup"])

        self.tick(self.task_id, "Error handling", now=now)
        learned = self.learning.remove_from_checklist(self.task_id, self.entry(self.task_id, "Error handling"), now)
        learned = self.learning.remove_from_checklist(self.task_id, self.entry(self.task_id, "Read the RFC"), now)
        self.assertEqual((learned["sections"], learned["progress"]), (["Auth interceptors", "HttpClient setup"], {"done": 0, "total": 2}))
        with self.assertRaises(SourceError):
            self.learning.rename_in_checklist(self.task_id, "check_none", "x", now)

    def test_a_learning_task_without_a_source_gets_a_checklist_of_its_own(self):
        own = self.store.create_daily_item({"date": TODAY, "title": "Practise scales", "detail": "", "domain": "learning",
                                            "goalId": None, "startTime": None, "durationMinutes": 45,
                                            "constraintKind": "flexible", "repeatKind": "none"})
        blank = self.learning.task(own["id"])
        self.assertEqual((blank["sourceId"], blank["checklist"], blank["progress"]), (None, [], {"done": 0, "total": 0}))

        for title in ("C major", "G major", "D major"):
            self.learning.add_to_checklist(own["id"], title, at(TODAY, "09:00"))
        self.tick(own["id"], "C major", now=at(TODAY, "09:20"))
        learned = self.learning.task(own["id"])
        self.assertEqual((learned["sections"], learned["ticked"], learned["progress"]),
                         (["C major", "G major", "D major"], ["C major"], {"done": 1, "total": 3}))
        self.assertTrue(all(entry["addedBy"] == "you" for entry in learned["checklist"]))
        self.assertEqual(self.learning.follow_up(own["id"], TOMORROW)["estimateMinutes"], 90, "45 minutes a section, two left")

        work = self.store.create_daily_item({"date": TODAY, "title": "Ship it", "detail": "", "domain": "work", "goalId": None,
                                             "startTime": None, "durationMinutes": 30, "constraintKind": "flexible",
                                             "repeatKind": "none"})
        with self.assertRaises(SourceError):
            self.learning.add_to_checklist(work["id"], "A step", at(TODAY, "09:00"))

    def test_a_folder_refresh_merges_a_changed_file_into_its_checklist(self):
        self.tick(self.task_id, "Interceptors", now=at(TODAY, "09:00"))
        path = self.folder / "Angular/03 Consuming HTTP Services.md"
        path.write_text(LESSON.replace("## Error handling", "## Retries\n\nTry again.\n\n## Errors"), encoding="utf-8")
        self.shelf.refresh(self.folder_record["id"])

        self.learning.refresh_profiles([self.lesson["id"]])

        learned = self.learning.task(self.task_id)
        self.assertEqual([(entry["title"], entry["pageState"], bool(entry["tickedAt"])) for entry in learned["checklist"]],
                         [("HttpClient setup", "", False), ("Interceptors", "", True), ("Retries", "new", False),
                          ("Errors", "new", False), ("Error handling", "gone", False)])


class NextTaskTests(LearningDay):
    def test_a_goals_next_unstudied_task_is_its_first_not_fully_done(self):
        made = self.learning.create_tasks([self.basics["id"], self.lesson["id"]], TODAY, {"title": "Angular"})
        goal_id = made["goal"]["id"]
        first, second = (task["id"] for task in made["tasks"])
        self.assertEqual(self.learning.next_unstudied(goal_id)["id"], first)
        with sqlite3.connect(self.store.path) as connection:
            connection.execute("UPDATE daily_items SET completion_status = 'partial' WHERE id = ?", (first,))
        self.assertEqual(self.learning.next_unstudied(goal_id)["id"], first, "partly done is not studied")
        with sqlite3.connect(self.store.path) as connection:
            connection.execute("UPDATE daily_items SET completion_status = 'done' WHERE id = ?", (first,))
        self.assertEqual(self.learning.next_unstudied(goal_id)["id"], second)
        with sqlite3.connect(self.store.path) as connection:
            connection.execute("UPDATE daily_items SET completion_status = 'done' WHERE id = ?", (second,))
        self.assertIsNone(self.learning.next_unstudied(goal_id))


class OverviewTests(LearningDay):
    def test_the_learning_overview_names_each_goals_next_unstudied_task_with_its_checklist(self):
        made = self.learning.create_tasks([self.lesson["id"], self.basics["id"]], TOMORROW, {"title": "Angular"})
        lesson, basics = (task["id"] for task in made["tasks"])
        self.tick(lesson, "Interceptors", now=at(TODAY, "09:00"))

        self.assertEqual(self.subject("Angular")["tasks"], {"done": 0, "total": 2, "next": {
            "id": lesson, "title": "Consuming HTTP Services", "date": TOMORROW, "start_time": None, "minutes": self.item(lesson)["duration_minutes"],
            "number": 1, "checklist": {"done": 1, "total": 3}}})
        with sqlite3.connect(self.store.path) as connection:
            connection.execute("UPDATE daily_items SET completion_status = 'done' WHERE id = ?", (lesson,))
        self.assertEqual((self.subject("Angular")["tasks"]["done"], self.subject("Angular")["tasks"]["next"]["number"],
                          self.subject("Angular")["tasks"]["next"]["checklist"]), (1, 2, None))
        with sqlite3.connect(self.store.path) as connection:
            connection.execute("UPDATE daily_items SET completion_status = 'done' WHERE id = ?", (basics,))
        self.assertIsNone(self.subject("Angular")["tasks"]["next"])

    def subject(self, title):
        return next(item for item in DomainRecords(self.store).snapshot("learning", TODAY)["subjects"] if item["title"] == title)

    def test_plans_proposed_for_the_day_weigh_what_each_task_has_left(self):
        made = self.learning.create_tasks([self.basics["id"], self.lesson["id"]], TODAY, {"title": "Angular"})
        lesson = made["tasks"][1]["id"]
        self.tick(lesson, "HttpClient setup", now=at(TODAY, "07:00"))
        self.store.create_daily_item({"date": TOMORROW, "title": "Practise", "detail": "", "domain": "learning",
                                      "goalId": made["goal"]["id"], "startTime": None, "durationMinutes": 30,
                                      "constraintKind": "flexible", "repeatKind": "none"})
        seen = {}

        def choose(context):
            seen.update(context)
            return None

        with patch("backend.app.database._local_time", return_value="07:00"):
            self.store.create_recorded_plan(TODAY, memory=[], guidance=[], choose=choose)

        task = next(task for task in seen["day"]["tasks"] if task["title"] == "Consuming HTTP Services")
        self.assertEqual((task["study"]["place"], task["study"]["covers"], task["study"]["handsOn"]),
                         ("2 of 3 in Angular", ["Interceptors", "Error handling"], True),
                         "a goal's tasks are counted whether made from a source or not")

    def test_effort_set_by_the_user_stays_when_the_file_is_read_again(self):
        task_id = self.learning.create_tasks([self.lesson["id"]], TODAY)["tasks"][0]["id"]
        self.learning.set_effort(task_id, "light")
        (self.folder / "Angular/03 Consuming HTTP Services.md").write_text(
            "# Consuming HTTP Services\n\n## HttpClient setup\n\n" + "word " * 1500
            + "\n\n## Interceptors\n\nShort.\n\n## Error handling\n\nMore.\n", encoding="utf-8")
        self.shelf.refresh(self.folder_record["id"])

        self.learning.refresh_profiles([self.lesson["id"]])

        learned = self.learning.task(task_id)
        self.assertEqual((learned["effort"], learned["effortBy"]), ("light", "you"), "the user's effort stays")
        self.assertGreaterEqual(learned["profile"]["words"], 1500, "the rest is read again")
        self.assertEqual(self.item(task_id)["duration_minutes"], study_minutes(learned["profile"]))

    def test_removing_the_source_from_the_library_keeps_its_tasks_and_their_checklists(self):
        task_id = self.learning.create_tasks([self.lesson["id"]], TODAY)["tasks"][0]["id"]
        self.tick(task_id, "HttpClient setup", now=at(TODAY, "09:00"))
        VectorStore(self.store.path).delete_source(self.lesson["id"])

        learned = self.learning.task(task_id)
        self.assertEqual((learned["sections"], learned["ticked"]),
                         (["HttpClient setup", "Interceptors", "Error handling"], ["HttpClient setup"]))
        self.assertIsNone(self.learning.study_left(task_id)["text"])
        self.assertEqual(self.learning.follow_up(task_id, TOMORROW)["left"], ["Interceptors", "Error handling"])


class MoveTests(unittest.TestCase):
    """A database v4.5 left: a goal made from a source with its three topics, the first studied."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Database(Path(self.temp.name) / "moved.sqlite3")
        self.goal = self.store.create_goal("Consuming HTTP Services", "learning")
        profile = {"subheadings": ["Providers"], "words": 400, "codeBlocks": 0, "handsOn": False, "effort": "steady",
                   "briefing": "Provide it once.", "sourceName": "Consuming HTTP Services"}
        with sqlite3.connect(self.store.path) as connection:
            connection.execute("ALTER TABLE daily_items ADD COLUMN topic_id TEXT")
            connection.execute("""CREATE TABLE goal_topics (id TEXT PRIMARY KEY, goal_id TEXT NOT NULL, position INTEGER NOT NULL,
                                  title TEXT NOT NULL, source_id TEXT, heading TEXT NOT NULL DEFAULT '',
                                  profile_json TEXT NOT NULL DEFAULT '{}', effort_by TEXT NOT NULL DEFAULT 'text',
                                  created_at TEXT NOT NULL)""")
            for position, (title, by) in enumerate([("HttpClient setup", "you"), ("Interceptors", "text"), ("Error handling", "text")]):
                connection.execute("""INSERT INTO goal_topics VALUES (?, ?, ?, ?, 'source_1', 'Consuming HTTP Services', ?, ?,
                                      '2026-10-05')""",
                                   (f"topic_{position}", self.goal["id"], position, title,
                                    json.dumps({**profile, "effort": "deep" if by == "you" else "steady"}), by))
            connection.execute(
                """INSERT INTO daily_items (id, item_date, goal_id, title, domain, duration_minutes, constraint_kind,
                       completion_status, created_at, topic_id) VALUES ('item_studied', ?, ?, 'HttpClient setup', 'learning', 45,
                       'flexible', 'done', '2026-10-05', 'topic_0')""", (YESTERDAY, self.goal["id"]))

    def test_each_file_goal_gets_one_task_whose_checklist_is_its_topics_and_nothing_is_lost(self):
        with sqlite3.connect(self.store.path) as connection:
            connection.row_factory = sqlite3.Row
            move_topics_to_tasks(connection, TODAY)

        goal = next(goal for goal in self.store.goals() if goal["id"] == self.goal["id"])
        self.assertEqual([(item["title"], item["date"], item["status"]) for item in goal["linkedItems"]],
                         [("HttpClient setup", YESTERDAY, "done"), ("Consuming HTTP Services", TODAY, "planned")],
                         "the study task stays as it was, beside one task for the file")
        learning = LearningTasks(self.store, None)
        self.assertEqual(learning.task("item_studied")["checklist"], [], "the study task stays a plain task")
        file_task = learning.task(goal["linkedItems"][1]["id"])
        self.assertEqual((file_task["sections"], file_task["sourceId"], file_task["ticked"], file_task["progress"]),
                         (["HttpClient setup", "Interceptors", "Error handling"], "source_1", ["HttpClient setup"],
                          {"done": 1, "total": 3}), "the topics, in order, with the studied one ticked")
        planned = self.store.daily_item(goal["linkedItems"][1]["id"])
        self.assertEqual((planned["start_time"], planned["durationSource"], planned["duration_minutes"]),
                         (None, "estimate", study_minutes(file_task["profile"])))
        self.assertEqual(file_task["effort"], "deep", "1,200 words over its topics")
        with sqlite3.connect(self.store.path) as connection:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            columns = {row[1] for row in connection.execute("PRAGMA table_info(daily_items)")}
        self.assertNotIn("goal_topics", tables)
        self.assertNotIn("topic_id", columns)

    def test_a_database_that_never_had_topics_is_left_as_it_is(self):
        fresh = Database(Path(self.temp.name) / "fresh.sqlite3")
        with sqlite3.connect(fresh.path) as connection:
            connection.row_factory = sqlite3.Row
            move_topics_to_tasks(connection, TODAY)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM daily_items").fetchone()[0], 0)
