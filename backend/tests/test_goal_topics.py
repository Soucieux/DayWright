import sqlite3
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.domain_records import DomainRecords
from backend.app.goal_topics import GoalTopics
from backend.app.retrieval import VectorStore
from backend.app.sources import SourceError, study_minutes
from backend.tests.test_source_store import ShelfDay

TODAY = date.today().isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()


class TopicDay(ShelfDay):
    """A connected throwaway folder, and goals made from its headings."""

    def setUp(self):
        super().setUp()
        self.topics = GoalTopics(self.store, self.shelf)
        self.folder_record = self.connect()
        self.lesson = next(source for source in self.folder_record["sources"] if source["title"] == "Consuming HTTP Services")

    def goal(self, title):
        return next(goal for goal in self.store.goals() if goal["title"] == title)

    def task_for(self, topic, day=TODAY, status="planned"):
        with sqlite3.connect(self.store.path) as connection:
            connection.execute(
                """INSERT INTO daily_items (id, item_date, goal_id, title, domain, duration_minutes, constraint_kind,
                       completion_status, created_at, topic_id) VALUES (?, ?, ?, ?, 'learning', 45, 'flexible', ?, ?, ?)""",
                (f"study:{topic['id']}:{day}", day, topic["goalId"], topic["title"], status, day, topic["id"]))


class EntryTests(TopicDay):
    def test_a_folder_lists_each_ticked_file_as_one_entry_with_its_second_level_headings(self):
        entries = self.topics.entries(folder_id=self.folder_record["id"])

        self.assertEqual([(entry["title"], entry["topics"]) for entry in entries],
                         [("Basics", []), ("Consuming HTTP Services", ["HttpClient setup", "Interceptors", "Error handling"])])

    def test_a_single_source_lists_its_first_level_headings(self):
        (self.folder / "guide.md").write_text("# Routing\n\n## Guards\n\n# Forms\n\n## Validation\n## Arrays\n", encoding="utf-8")
        self.shelf.refresh(self.folder_record["id"])
        guide = next(item for item in self.shelf.folders()[0]["sources"] if item["relativePath"] == "guide.md")

        entries = self.topics.entries(source_id=guide["id"])

        self.assertEqual([(entry["title"], entry["topics"], entry["index"]) for entry in entries],
                         [("Routing", ["Guards"], 0), ("Forms", ["Validation", "Arrays"], 1)])


class CreateTests(TopicDay):
    def test_each_ticked_entry_becomes_a_learning_goal_with_its_topics_in_order_read_from_their_text(self):
        created = self.topics.create_goals([{"sourceId": self.lesson["id"]}])

        goal = self.goal("Consuming HTTP Services")
        self.assertEqual([goal["id"]], [item["id"] for item in created])
        self.assertEqual(goal["domain"], "learning")
        topics = goal["topics"]
        self.assertEqual([topic["title"] for topic in topics], ["HttpClient setup", "Interceptors", "Error handling"])
        setup, interceptors, errors = (topic["profile"] for topic in topics)
        self.assertEqual((setup["subheadings"], setup["effort"], setup["handsOn"], setup["sourceName"]),
                         (["Providers"], "light", False, "Consuming HTTP Services"))
        self.assertTrue(setup["briefing"].startswith("Provide it once"))
        self.assertTrue(interceptors["handsOn"])
        self.assertTrue(errors["handsOn"], "an exercise makes it hands-on")
        self.assertEqual([topic["minutes"] for topic in topics], [study_minutes(topic["profile"]) for topic in topics],
                         "each topic carries the length a study session for it is estimated at")
        self.assertEqual(self.shelf.source(self.lesson["id"])["goalId"], goal["id"], "the source joins its goal")

    def test_a_websites_headings_make_goals_once_it_is_looked_up(self):
        site = self.shelf.add_website("https://atlas.example/", "", "learning")
        page = {"title": "Atlas", "briefing": None, "outline": [{"title": "Signals", "topics": [{"title": "Computed"}, {"title": "Effects"}]}]}
        with patch("backend.app.source_store.fetch_page", return_value=page) as fetched:
            with self.assertRaises(SourceError):
                self.topics.entries(source_id=site["id"])
            self.assertEqual(fetched.call_count, 0, "never fetched to list entries")
            self.shelf.look_up(site["id"])
            self.topics.create_goals([{"sourceId": site["id"], "index": 0}])
        self.assertEqual(fetched.call_count, 1)

        topics = self.goal("Signals")["topics"]
        self.assertEqual([(topic["title"], topic["profile"]["effort"], topic["effortBy"]) for topic in topics],
                         [("Computed", "steady", "default"), ("Effects", "steady", "default")])

    def test_an_unknown_source_or_heading_is_refused(self):
        with self.assertRaises(SourceError):
            self.topics.create_goals([{"sourceId": "nope"}])
        with self.assertRaises(SourceError):
            self.topics.create_goals([{"sourceId": self.lesson["id"], "index": 9}])


class StudyTests(TopicDay):
    def setUp(self):
        super().setUp()
        self.topics.create_goals([{"sourceId": self.lesson["id"]}])
        self.list = self.goal("Consuming HTTP Services")["topics"]

    def test_the_next_topic_is_the_first_not_studied_and_waits_while_it_is_planned(self):
        goal_id = self.list[0]["goalId"]
        self.assertEqual(self.topics.next_topic(goal_id)["title"], "HttpClient setup")

        self.task_for(self.list[0], TOMORROW)
        self.assertIsNone(self.topics.next_topic(goal_id), "goal order is kept: the first is on its way")

        with sqlite3.connect(self.store.path) as connection:
            connection.execute("UPDATE daily_items SET completion_status = 'done', item_date = ? WHERE topic_id = ?",
                               (TODAY, self.list[0]["id"]))
        self.assertEqual(self.topics.next_topic(goal_id)["title"], "Interceptors")
        studied = self.goal("Consuming HTTP Services")["topics"][0]
        self.assertEqual((studied["studied"], studied["studiedOn"]), (True, TODAY))

    def test_a_partly_done_session_does_not_study_a_topic(self):
        self.task_for(self.list[0], TODAY, "partial")
        self.assertFalse(self.goal("Consuming HTTP Services")["topics"][0]["studied"])

    def test_a_study_task_is_the_topic_in_its_goal_with_its_length_from_its_profile(self):
        topic = self.list[1]
        task = self.topics.study_task(topic["id"], TOMORROW)

        self.assertEqual({key: task[key] for key in ("title", "goalId", "topicId", "domain", "date", "startTime", "constraintKind")},
                         {"title": "Interceptors", "goalId": topic["goalId"], "topicId": topic["id"], "domain": "learning",
                          "date": TOMORROW, "startTime": None, "constraintKind": "flexible"})
        self.assertEqual(task["durationMinutes"], max(30, study_minutes(topic["profile"])))

    def test_a_study_task_saved_carries_its_topic(self):
        task = self.topics.study_task(self.list[0]["id"], TODAY)
        item = self.store.create_daily_item({**task, "detail": "", "repeatKind": "none"})

        with sqlite3.connect(self.store.path) as connection:
            self.assertEqual(connection.execute("SELECT topic_id FROM daily_items WHERE id = ?", (item["id"],)).fetchone()[0],
                             self.list[0]["id"])

    def test_the_learning_overview_names_each_subjects_next_topic_to_study(self):
        subject = next(item for item in DomainRecords(self.store).snapshot("learning", TODAY)["subjects"]
                       if item["title"] == "Consuming HTTP Services")
        first = self.list[0]

        self.assertEqual(subject["topics"], {"studied": 0, "total": 3, "next": {
            "id": first["id"], "title": "HttpClient setup", "number": 1, "minutes": study_minutes(first["profile"]),
            "effort": first["profile"]["effort"]}})
        self.task_for(first, TOMORROW)
        subject = next(item for item in DomainRecords(self.store).snapshot("learning", TODAY)["subjects"]
                       if item["title"] == "Consuming HTTP Services")
        self.assertIsNone(subject["topics"]["next"], "the next topic waits while the first is planned")

    def test_plans_proposed_for_the_day_weigh_each_study_tasks_topic(self):
        self.store.create_daily_item({**self.topics.study_task(self.list[1]["id"], TODAY), "detail": "", "repeatKind": "none"})
        seen = {}

        def choose(context):
            seen.update(context)
            return None

        with patch("backend.app.database._local_time", return_value="07:00"):
            self.store.create_recorded_plan(TODAY, memory=[], guidance=[], choose=choose)

        task = next(task for task in seen["day"]["tasks"] if task["title"] == "Interceptors")
        self.assertEqual((task["study"]["place"], task["study"]["effort"], task["study"]["handsOn"]),
                         ("2 of 3 in Consuming HTTP Services", self.list[1]["profile"]["effort"], True))

    def test_effort_set_by_the_user_stays_when_the_text_is_read_again(self):
        topic = self.topics.set_effort(self.list[0]["id"], "deep")
        self.assertEqual((topic["profile"]["effort"], topic["effortBy"]), ("deep", "you"))
        with self.assertRaises(SourceError):
            self.topics.set_effort(self.list[0]["id"], "heavy")

        (self.folder / "Angular" / "03 Consuming HTTP Services.md").write_text(
            "# Consuming HTTP Services\n\n## HttpClient setup\n\n" + "word " * 500 + "\n\n## Interceptors\n\nShort.\n", encoding="utf-8")
        self.shelf.refresh(self.folder_record["id"])
        self.topics.refresh_profiles([self.lesson["id"]])

        setup, interceptors, _ = (topic["profile"] for topic in self.goal("Consuming HTTP Services")["topics"])
        self.assertEqual((setup["effort"], setup["words"]), ("deep", 500), "the user's effort stays; the rest is read again")
        self.assertEqual(interceptors["effort"], "light")

    def test_removing_the_source_from_the_library_keeps_its_goal_and_topics(self):
        before = self.goal("Consuming HTTP Services")["topics"]
        VectorStore(self.store.path).delete_source(self.lesson["id"])

        after = self.goal("Consuming HTTP Services")["topics"]
        self.assertEqual([(topic["title"], topic["profile"]) for topic in after], [(topic["title"], topic["profile"]) for topic in before])
        self.assertIsNone(self.topics.topic_text(after[0]))
        self.assertEqual(self.topics.next_topic(after[0]["goalId"])["title"], "HttpClient setup")


if __name__ == "__main__":
    unittest.main()
