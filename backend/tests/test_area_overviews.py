import sqlite3
import unittest
from datetime import date, timedelta

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.agents import AgentOrchestrator
from backend.app.domain_records import DomainRecords
from backend.app.planner import day_load
from backend.tests.test_repeats import SeriesDay, days_ago

TOMORROW = (date.today() + timedelta(days=1)).isoformat()


class AreaDay(SeriesDay):
    """A fresh account with helpers that write goals and tasks on any day, as history is written."""

    def goal(self, title, domain, age=10, status="active"):
        """Make a goal `age` days old, in `status`; return its id."""
        goal_id = self.store.create_goal(title, domain)["id"]
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE goals SET created_at = ?, status = ? WHERE id = ?",
                               (f"{days_ago(age)}T12:00:00+00:00", status, goal_id))
        return goal_id

    def task_on(self, title, day, domain, status="planned", goal=None, start=None, minutes=30):
        """Record one task on `day` directly, as history is written; return its id."""
        item_id = f"{title}:{day}"
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """INSERT INTO daily_items (id, item_date, goal_id, title, domain, start_time, duration_minutes,
                       constraint_kind, completion_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (item_id, day, goal, title, domain, start, minutes, "fixed" if start else "flexible", status, day))
        return item_id

    def moved_entry(self, title, day, moved_to, domain="work"):
        """A set plan on `day` whose entry for `title` was moved on to `moved_to`."""
        with sqlite3.connect(self.path) as connection:
            connection.execute("INSERT INTO plan_sets (id, plan_date, source, created_at) VALUES (?, ?, 'test', ?)",
                               (f"set:{day}", day, day))
            connection.execute("""INSERT INTO plan_variants (id, plan_set_id, name, slug, rationale, created_at)
                                  VALUES (?, ?, 'Balanced', 'balanced', '', ?)""", (f"plan:{day}", f"set:{day}", day))
            connection.execute("INSERT INTO daily_confirmations (plan_date, variant_id, confirmed_at) VALUES (?, ?, ?)",
                               (day, f"plan:{day}", day))
            connection.execute(
                """INSERT INTO plan_entries (id, variant_id, position, start_time, title, detail, domain,
                       duration_minutes, constraint_kind, removed_at, moved_to)
                   VALUES (?, ?, 0, '09:00', ?, '', ?, 30, 'flexible', ?, ?)""",
                (f"entry:{title}", f"plan:{day}", title, domain, day, moved_to))

    def overview(self, domain, day=None):
        return DomainRecords(self.store).snapshot(domain, day or self.today)


class LearningOverviewTests(AreaDay):
    def test_learning_shows_this_weeks_time_per_subject_and_when_the_user_last_practised(self):
        rag = self.goal("RAG", "learning")
        french = self.goal("French", "learning")
        self.goal("Chess", "learning", status="completed")
        self.task_on("Read paper", self.today, "learning", "done", rag, minutes=45)
        self.task_on("Notes", self.today, "learning", "partial", rag, minutes=30)
        self.task_on("Later", self.today, "learning", "planned", rag, minutes=90)
        self.task_on("Flashcards", days_ago(7), "learning", "done", french, minutes=60)
        self.task_on("Podcast", self.today, "learning", "done", minutes=20)

        view = self.overview("learning")

        self.assertEqual([(subject["title"], subject["minutes"]) for subject in view["subjects"]],
                         [("RAG", 75), ("French", 0)])
        self.assertEqual(view["otherMinutes"], 20)
        self.assertEqual(view["lastPractised"], self.today)

    def test_an_active_learning_goal_is_due_for_review_after_three_days_with_nothing_done(self):
        for title, last in (("Three", 3), ("Two", 2)):
            self.task_on(f"{title} task", days_ago(last), "learning", "done", self.goal(title, "learning"))
        self.goal("Paused", "learning", status="paused")
        self.goal("New", "learning", age=2)
        self.goal("Idle", "learning", age=3)
        skipped = self.goal("Skipped", "learning")
        self.task_on("Done once", days_ago(4), "learning", "done", skipped)
        self.task_on("Skipped since", days_ago(1), "learning", "skipped", skipped)

        view = self.overview("learning")

        self.assertEqual([(goal["title"], goal["days"]) for goal in view["dueForReview"]],
                         [("Three", 3), ("Skipped", 4), ("Idle", 3)])


class LifeOverviewTests(AreaDay):
    def walk(self, days, kind="daily", domain="life", title="Walk"):
        for day, status in days:
            self.repeat_day(title, day, kind, series=title, status=status, domain=domain)

    def test_a_daily_repeat_shows_as_a_habit_with_this_weeks_count_and_its_streak(self):
        days = [(self.today, "done"), (days_ago(1), "done"), (days_ago(2), "done"), (days_ago(3), "skipped"),
                (days_ago(4), "done")]
        self.walk(days)
        week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()

        habit, = self.overview("life")["habits"]

        self.assertEqual((habit["title"], habit["kind"], habit["streak"]), ("Walk", "daily", 3))
        self.assertEqual(habit["doneThisWeek"], sum(day >= week_start and status == "done" for day, status in days))

    def test_todays_copy_still_to_do_doesnt_break_a_daily_streak(self):
        self.walk([(self.today, "planned"), (days_ago(1), "done"), (days_ago(2), "done"), (days_ago(3), "partial")])

        self.assertEqual(self.overview("life")["habits"][0]["streak"], 2)

    def test_a_weekly_repeat_counts_its_streak_in_weeks(self):
        self.walk([(self.today, "done"), (days_ago(7), "done"), (days_ago(14), "done"), (days_ago(21), "skipped")],
                  kind="weekly")
        self.walk([(self.today, "planned"), (days_ago(7), "done"), (days_ago(14), "done")], kind="weekly",
                  title="Call")

        habits = {habit["title"]: habit for habit in self.overview("life")["habits"]}

        self.assertEqual((habits["Walk"]["kind"], habits["Walk"]["streak"]), ("weekly", 3))
        self.assertEqual(habits["Call"]["streak"], 2)

    def test_only_lifes_repeats_still_repeating_are_habits(self):
        self.walk([(days_ago(1), "done")], domain="learning", title="Read")
        self.walk([(days_ago(2), "done")], title="Stretch")
        self.walk([(days_ago(1), "done")], kind="none", title="Stretch")

        self.assertEqual(self.overview("life")["habits"], [])

    def test_life_shows_the_days_appointments_meals_free_time_and_energy(self):
        self.task_on("Dentist", self.today, "life", start="09:00", minutes=60)
        self.task_on("Laundry", self.today, "life", minutes=30)
        self.repeat_day("Stretch", self.today, "daily", series="Stretch", start="15:00")
        self.task_on("Old dentist", days_ago(1), "life", start="09:00")
        self.store.set_energy(self.today, 4)
        empty = day_load([], meals=self.store.day_meals(self.today))["freeMinutes"]

        view = self.overview("life")

        self.assertEqual([item["title"] for item in view["appointments"]], ["Dentist"])
        self.assertEqual([(meal["title"], meal["start_time"]) for meal in view["meals"]],
                         [("Lunch", "12:00"), ("Dinner", "18:00")])
        self.assertEqual(view["freeMinutes"], empty - 60 - 30 - 30)
        self.assertEqual(view["energy"], 4)


class WorkOverviewTests(AreaDay):
    def test_work_shows_the_weeks_load_by_day_the_days_meetings_and_carry_overs(self):
        self.task_on("Stand-up", self.today, "work", start="10:00", minutes=30)
        self.task_on("Report", self.today, "work", minutes=60)
        self.task_on("Email", days_ago(2), "work", "partial")
        self.task_on("Invoices", days_ago(3), "work", "done")
        self.task_on("Old pitch", days_ago(1), "work", "skipped")
        self.task_on("Old memo", days_ago(8), "work")
        self.moved_entry("Slides", days_ago(4), self.today)
        self.moved_entry("Ancient", days_ago(9), days_ago(8))

        view = self.overview("work")

        load = {day["date"]: day["minutes"] for day in view["load"]}
        self.assertEqual(len(load), 7)
        self.assertEqual(load[self.today], 90)
        self.assertEqual([meeting["title"] for meeting in view["meetings"]], ["Stand-up"])
        self.assertEqual([(item["title"], item["date"], item.get("movedTo"), item.get("status"))
                          for item in view["carryOvers"]],
                         [("Slides", days_ago(4), self.today, None), ("Email", days_ago(2), None, "partial")])


class ProjectOverviewTests(AreaDay):
    def test_project_shows_progress_the_last_step_done_and_the_next_one(self):
        site = self.goal("Launch site", "project")
        self.task_on("Old step", days_ago(5), "project", "done", site)
        self.task_on("Draft copy", days_ago(2), "project", "done", site)
        self.task_on("Polish", days_ago(1), "project", "skipped", site)
        build = self.task_on("Build page", TOMORROW, "project", "planned", site)
        self.goal("Garden shed", "project", age=1)

        site_view, shed_view = self.overview("project")["projects"]

        self.assertEqual((site_view["title"], site_view["done"], site_view["total"]), ("Launch site", 2, 4))
        self.assertEqual(site_view["lastStep"], {"title": "Draft copy", "date": days_ago(2)})
        self.assertEqual(site_view["nextStep"], {"id": build, "title": "Build page", "date": TOMORROW})
        self.assertEqual((shed_view["lastStep"], shed_view["nextStep"]), (None, None))

    def test_an_active_project_stalls_after_three_days_with_nothing_done_and_a_paused_one_never(self):
        self.task_on("A step", days_ago(3), "project", "done", self.goal("A", "project"))
        self.task_on("B step", days_ago(2), "project", "done", self.goal("B", "project"))
        self.goal("Paused", "project", status="paused")
        self.goal("Idle", "project", age=4)
        self.goal("Done", "project", status="completed")

        self.assertEqual([(goal["title"], goal["days"]) for goal in self.overview("project")["stalled"]],
                         [("A", 3), ("Idle", 4)])


class AreaFlagNoticeTests(AreaDay):
    def test_due_for_review_and_stalled_reach_ava_from_their_area_agent_once_a_day_per_goal(self):
        french = self.goal("French", "learning", age=5)
        shed = self.goal("Shed", "project", age=5)
        self.goal("Resting", "project", age=9, status="paused")

        AgentOrchestrator().inspect_today(self.store)
        AgentOrchestrator().inspect_today(self.store)

        flags = [(notice["agentKey"], notice["kind"], notice["values"]) for notice in self.store.notices()
                 if notice["kind"] in ("due-for-review", "stalled")]
        self.assertEqual(flags, [("learning", "due-for-review", {"goalId": french, "goalTitle": "French", "days": 5}),
                                 ("project", "stalled", {"goalId": shed, "goalTitle": "Shed", "days": 5})])


class SummaryWithoutAreaRecordsTests(AreaDay):
    def test_summary_reads_repeats_and_energy_in_place_of_habits_sessions_and_check_ins(self):
        for day, status in ((days_ago(1), "done"), (days_ago(2), "skipped")):
            self.repeat_day("Read", day, "daily", series="Read", status=status, domain="learning")
        self.store.set_energy(self.today, 2)

        facts = self.store.summary_facts(days_ago(6), self.today)
        report = AgentOrchestrator().summary_report("week", "this-week", facts)

        self.assertEqual(facts["areaEvidence"]["energy"], {"date": self.today, "level": 2})
        self.assertEqual(facts["areaEvidence"]["repeats"]["learning"], {"scheduled": 2, "done": 1})
        self.assertEqual(facts["areaEvidence"]["repeats"]["life"], {"scheduled": 0, "done": 0})
        life = [advice for advice in report["suggestions"] if advice["domain"] == "life"]
        self.assertEqual([(advice["priority"], "energy was 2/5" in advice["content"]) for advice in life],
                         [("strong", True)])
        self.assertIn("Repeats: 1/2 done.", report["text"])
        self.assertIn("Latest reported energy: 2/5.", report["text"])
        self.assertEqual(self.store.first_record_date(), days_ago(2))


if __name__ == "__main__":
    unittest.main()
