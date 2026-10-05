import sqlite3
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.agents import AgentOrchestrator
from backend.app.domain_records import DomainRecords
from backend.tests.test_area_overviews import AreaDay
from backend.tests.test_repeats import days_ago

# A Wednesday three weeks back, taken as today for the week figures, so the week has past days, today and days to come.
WED = date.today() - timedelta(days=(date.today().weekday() - 2) % 7 + 21)
MON, TUE, THU, FRI, SAT, SUN = (WED + timedelta(days=offset) for offset in (-2, -1, 1, 2, 3, 4))


def iso(day):
    return day.isoformat()


def later(count):
    return (date.today() + timedelta(days=count)).isoformat()


class AreaWeek(AreaDay):
    """A fresh account, read as it stood on WED."""

    def week(self, domain, day=WED):
        return DomainRecords(self.store).snapshot(domain, iso(day), today=iso(WED))

    def stop_series(self, series, from_day):
        with sqlite3.connect(self.path) as connection:
            connection.execute("INSERT INTO repeat_series (id, next_kind, next_from) VALUES (?, 'none', ?)",
                               (series, from_day))

    def energy_on(self, day, level):
        with sqlite3.connect(self.path) as connection:
            connection.execute("INSERT INTO energy_readings (reading_date, level, updated_at) VALUES (?, ?, ?)",
                               (day, level, day))

    def set_plan_entry(self, title, day, start, minutes, removed=False):
        """An entry of the plan set for `day`, set up the first time it is called for that day."""
        with sqlite3.connect(self.path) as connection:
            if not connection.execute("SELECT 1 FROM plan_sets WHERE id = ?", (f"set:{day}",)).fetchone():
                connection.execute("INSERT INTO plan_sets (id, plan_date, source, created_at) VALUES (?, ?, 'test', ?)",
                                   (f"set:{day}", day, day))
                connection.execute("""INSERT INTO plan_variants (id, plan_set_id, name, slug, rationale, created_at)
                                      VALUES (?, ?, 'Balanced', 'balanced', '', ?)""", (f"plan:{day}", f"set:{day}", day))
                connection.execute("INSERT INTO daily_confirmations (plan_date, variant_id, confirmed_at) VALUES (?, ?, ?)",
                                   (day, f"plan:{day}", day))
            position = connection.execute("SELECT COUNT(*) FROM plan_entries WHERE variant_id = ?", (f"plan:{day}",)).fetchone()[0]
            connection.execute(
                """INSERT INTO plan_entries (id, variant_id, position, start_time, title, detail, domain,
                       duration_minutes, constraint_kind, removed_at)
                   VALUES (?, ?, ?, ?, ?, '', 'work', ?, 'flexible', ?)""",
                (f"entry:{title}", f"plan:{day}", position, start, title, minutes, day if removed else None))


class LearningWeekTests(AreaWeek):
    def test_each_subject_shows_its_weeks_time_fully_done_against_planned_and_a_practice_row(self):
        rag = self.goal("RAG", "learning", age=40)
        self.task_on("Paper", iso(MON), "learning", "done", rag, minutes=45)
        self.task_on("Notes", iso(TUE), "learning", "planned", rag, minutes=30)
        self.task_on("Recap", iso(WED), "learning", "partial", rag, minutes=30)
        self.task_on("Course", iso(FRI), "learning", "planned", rag, minutes=60)
        self.task_on("Old", iso(MON - timedelta(days=1)), "learning", "done", rag, minutes=99)

        subject, = self.week("learning")["subjects"]

        self.assertEqual((subject["plannedMinutes"], subject["doneMinutes"], subject["minutes"]), (165, 45, 45))
        self.assertEqual(subject["days"], ["practised", "planned", "planned", "none", "planned", "none", "none"])

    def test_a_subject_shows_when_it_was_last_fully_practised_and_its_next_session(self):
        rag = self.goal("RAG", "learning", age=40)
        self.goal("Chess", "learning", age=40)
        self.task_on("Paper", iso(MON), "learning", "done", rag)
        self.task_on("Recap", iso(WED), "learning", "partial", rag)
        self.task_on("Missed", iso(TUE), "learning", "planned", rag)
        course = self.task_on("Course", iso(FRI), "learning", "planned", rag, start="10:00")

        rag_view, chess_view = self.week("learning")["subjects"]

        self.assertEqual(rag_view["lastPractised"], iso(MON))
        self.assertEqual(rag_view["nextSession"], {"id": course, "title": "Course", "date": iso(FRI), "start_time": "10:00"})
        self.assertEqual((chess_view["lastPractised"], chess_view["nextSession"]), (None, None))

    def test_learning_without_a_goal_and_the_weeks_practice_by_day(self):
        rag = self.goal("RAG", "learning", age=40)
        self.task_on("Paper", iso(MON), "learning", "done", rag, minutes=45)
        self.task_on("Podcast", iso(MON), "learning", "done", minutes=20)
        self.task_on("Article", iso(THU), "learning", "planned", minutes=40)
        self.task_on("Quiz", iso(THU), "learning", "partial", minutes=15)

        view = self.week("learning")

        self.assertEqual(view["other"], {"plannedMinutes": 75, "doneMinutes": 20})
        self.assertEqual([(day["date"], day["plannedMinutes"], day["doneMinutes"]) for day in view["practice"]],
                         [(iso(MON), 65, 65), (iso(TUE), 0, 0), (iso(WED), 0, 0), (iso(THU), 55, 0),
                          (iso(FRI), 0, 0), (iso(SAT), 0, 0), (iso(SUN), 0, 0)])


class LifeWeekTests(AreaWeek):
    def test_a_daily_habit_shows_its_rule_its_start_and_a_state_for_each_day_of_the_week(self):
        for day, status in ((MON - timedelta(days=3), "done"), (MON, "done"), (TUE, "skipped"), (WED, "partial")):
            self.repeat_day("Walk", iso(day), "daily", series="Walk", status=status)
        self.repeat_day("Stretch", iso(WED), "daily", series="Stretch", status="planned")

        habits = {habit["title"]: habit for habit in self.week("life")["habits"]}

        walk, stretch = habits["Walk"], habits["Stretch"]
        self.assertEqual((walk["kind"], walk["since"], walk["stoppedOn"]), ("daily", iso(MON - timedelta(days=3)), None))
        self.assertEqual((walk["itemId"], walk["itemDate"]), (f"Walk:{iso(WED)}:daily", iso(WED)))
        self.assertEqual(walk["days"], ["done", "missed", "partial", "upcoming", "upcoming", "upcoming", "upcoming"])
        self.assertEqual(stretch["days"], ["off", "off", "upcoming", "upcoming", "upcoming", "upcoming", "upcoming"])

    def test_a_past_day_with_no_copy_or_left_unreported_is_missed(self):
        self.repeat_day("Read", iso(MON - timedelta(days=1)), "daily", series="Read")
        self.repeat_day("Read", iso(TUE), "daily", series="Read", status="planned")

        read, = self.week("life")["habits"]

        self.assertEqual(read["days"][:3], ["missed", "missed", "upcoming"])

    def test_a_weekly_habit_shows_its_weekday_and_leaves_the_other_days_empty(self):
        self.repeat_day("Call", iso(FRI - timedelta(days=7)), "weekly", series="Call")

        call, = self.week("life")["habits"]

        self.assertEqual((call["kind"], call["weekday"]), ("weekly", 4))
        self.assertEqual(call["days"], ["off", "off", "off", "off", "upcoming", "off", "off"])

    def test_a_repeat_stopped_this_week_stays_listed_until_the_week_ends(self):
        for day in (MON - timedelta(days=2), MON, TUE):
            self.repeat_day("Yoga", iso(day), "daily", series="Yoga")
        self.stop_series("Yoga", iso(THU))
        self.repeat_day("Old", iso(MON - timedelta(days=9)), "daily", series="Old")
        self.stop_series("Old", iso(MON - timedelta(days=4)))
        self.repeat_day("Tea", iso(MON - timedelta(days=1)), "daily", series="Tea")
        self.repeat_day("Tea", iso(MON), "none", series="Tea")

        habits = {habit["title"]: habit for habit in self.week("life")["habits"]}

        self.assertEqual(sorted(habits), ["Tea", "Yoga"])
        self.assertEqual(habits["Yoga"]["stoppedOn"], iso(THU))
        self.assertEqual(habits["Yoga"]["days"], ["done", "done", "upcoming", "off", "off", "off", "off"])
        self.assertEqual(habits["Tea"]["stoppedOn"], iso(TUE))
        self.assertEqual(habits["Tea"]["days"], ["done", "off", "off", "off", "off", "off", "off"])

    def test_todays_shape_lists_the_free_windows_around_booked_and_meal_time(self):
        self.task_on("Stand-up", self.today, "work", start="10:00", minutes=60)
        self.task_on("Dentist", self.today, "life", start="14:00", minutes=60)
        self.task_on("Laundry", self.today, "life", minutes=30)
        self.task_on("On hold", self.today, "work", goal=self.goal("Rest", "work", status="paused"), start="20:00")
        self.set_plan_entry("Stand-up", self.today, "10:00", 60)
        self.set_plan_entry("Report", self.today, "16:00", 30)
        self.set_plan_entry("Dropped", self.today, "21:00", 30, removed=True)

        windows = self.overview("life")["freeWindows"]

        self.assertEqual([(window["start"], window["end"], window["minutes"]) for window in windows],
                         [("09:00", "10:00", 60), ("11:00", "12:00", 60), ("13:00", "14:00", 60),
                          ("15:00", "16:00", 60), ("16:30", "18:00", 90), ("19:00", "22:00", 180)])

    def test_energy_shows_the_last_seven_days_readings(self):
        self.energy_on(days_ago(6), 3)
        self.energy_on(days_ago(2), 2)
        self.energy_on(days_ago(7), 5)
        self.store.set_energy(self.today, 4)

        week = self.overview("life")["energyWeek"]

        self.assertEqual([(day["date"], day["level"]) for day in week],
                         [(days_ago(6), 3), (days_ago(5), None), (days_ago(4), None), (days_ago(3), None),
                          (days_ago(2), 2), (days_ago(1), None), (self.today, 4)])


class WorkWeekTests(AreaWeek):
    def test_work_load_shows_each_days_planned_and_done_time_and_the_weeks_totals(self):
        self.task_on("Report", iso(MON), "work", "done", minutes=60)
        self.task_on("Email", iso(MON), "work", minutes=30)
        self.task_on("Review", iso(TUE), "work", "partial", minutes=45)
        self.task_on("Pitch", iso(WED), "work", "skipped", minutes=30)
        self.task_on("Plan", iso(FRI), "work", minutes=90)
        self.task_on("Old", iso(MON - timedelta(days=1)), "work", "done", minutes=99)
        self.task_on("Held", iso(THU), "work", goal=self.goal("Rest", "work", status="paused"), minutes=50)

        view = self.week("work")

        self.assertEqual([(day["date"], day["minutes"], day["doneMinutes"]) for day in view["load"]],
                         [(iso(MON), 90, 60), (iso(TUE), 45, 0), (iso(WED), 30, 0), (iso(THU), 0, 0),
                          (iso(FRI), 90, 0), (iso(SAT), 0, 0), (iso(SUN), 0, 0)])
        self.assertEqual((view["plannedMinutes"], view["doneMinutes"]), (255, 60))

    def test_meetings_cover_the_day_on_show_and_the_next_six_days(self):
        self.task_on("Stand-up", iso(WED), "work", start="10:00")
        self.task_on("Client", iso(THU), "work", start="09:00")
        self.task_on("Review", iso(WED + timedelta(days=6)), "work", start="11:00")
        self.task_on("Too far", iso(WED + timedelta(days=7)), "work", start="11:00")
        self.task_on("Yesterday", iso(TUE), "work", start="11:00")
        self.task_on("Memo", iso(THU), "work")
        self.task_on("Dentist", iso(THU), "life", start="15:00")

        meetings = self.week("work")["meetings"]

        self.assertEqual([(item["title"], item["date"], item["start_time"]) for item in meetings],
                         [("Stand-up", iso(WED), "10:00"), ("Client", iso(THU), "09:00"),
                          ("Review", iso(WED + timedelta(days=6)), "11:00")])


    def test_each_carry_over_names_its_task_and_where_it_stands(self):
        email = self.task_on("Email", days_ago(2), "work", "partial")
        memo = self.task_on("Memo", days_ago(3), "work")
        slides = self.task_on("Slides", self.today, "work")
        self.moved_entry("Slides", days_ago(4), self.today)
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE plan_entries SET source_item_id = ? WHERE title = 'Slides'", (slides,))

        carried = self.overview("work")["carryOvers"]

        self.assertEqual([(item["id"], item["date"], item.get("status"), item.get("movedTo")) for item in carried],
                         [(slides, days_ago(4), None, self.today), (memo, days_ago(3), "planned", None),
                          (email, days_ago(2), "partial", None)])


class ProjectStatusTests(AreaWeek):
    def test_a_project_is_on_track_stalled_paused_or_without_steps(self):
        self.task_on("Step", days_ago(2), "project", "done", self.goal("Two idle", "project"))
        self.task_on("Step", days_ago(3), "project", "done", self.goal("Three idle", "project"))
        self.task_on("Step", days_ago(1), "project", "done", self.goal("Resting", "project", status="paused"))
        self.goal("Empty", "project", age=1)

        projects = {project["title"]: project for project in self.overview("project")["projects"]}

        self.assertEqual({title: (project["health"], project["idleDays"]) for title, project in projects.items()},
                         {"Two idle": ("on-track", 2), "Three idle": ("stalled", 3), "Resting": ("paused", None),
                          "Empty": ("no-steps", 1)})

    def test_a_partly_done_step_isnt_done_and_steps_are_listed_in_order(self):
        site = self.goal("Site", "project")
        draft = self.task_on("Draft", days_ago(2), "project", "partial", site)
        build = self.task_on("Build", later(2), "project", "planned", site)
        polish = self.task_on("Polish", days_ago(1), "project", "skipped", site)

        project, = self.overview("project")["projects"]

        self.assertEqual((project["done"], project["total"], project["lastStep"]), (0, 3, None))
        self.assertEqual([(step["id"], step["status"]) for step in project["steps"]],
                         [(draft, "partial"), (polish, "skipped"), (build, "planned")])

    def test_next_steps_cover_the_next_seven_days_and_recently_done_the_past_seven(self):
        site = self.goal("Site", "project")
        self.task_on("Plan", self.today, "project", "planned", site)
        self.task_on("Order", later(6), "project", "planned")
        self.task_on("Too far", later(7), "project", "planned", site)
        self.task_on("Ship", self.today, "project", "done", site)
        self.task_on("Sketch", days_ago(6), "project", "done", site)
        self.task_on("Too old", days_ago(7), "project", "done", site)
        self.task_on("Draft", days_ago(1), "project", "partial")
        self.task_on("Skipped", days_ago(2), "project", "skipped", site)

        view = self.overview("project")

        self.assertEqual([(step["title"], step["date"], step["goalTitle"]) for step in view["nextSteps"]],
                         [("Plan", self.today, "Site"), ("Order", later(6), None)])
        self.assertEqual([(step["title"], step["date"], step["goalTitle"]) for step in view["recentDone"]],
                         [("Ship", self.today, "Site"), ("Sketch", days_ago(6), "Site")])

    def test_idle_days_count_from_the_last_task_fully_done(self):
        shed = self.goal("Shed", "project", age=10)
        self.task_on("Frame", days_ago(1), "project", "partial", shed)
        french = self.goal("French", "learning", age=5)
        self.task_on("Verbs", days_ago(1), "learning", "partial", french)

        project, = self.overview("project")["projects"]

        self.assertEqual((project["health"], project["idleDays"]), ("stalled", 10))
        self.assertEqual([(goal["title"], goal["days"]) for goal in self.overview("learning")["dueForReview"]], [("French", 5)])


class AreaNotesTests(AreaWeek):
    def test_an_areas_notes_for_today_bring_its_agents_flags_and_its_doubts(self):
        french = self.goal("French", "learning", age=5)
        doubt = {"taskTitle": "Read", "usualStart": "09:00", "requested": "21:00", "done": 4}
        self.store.post_notices(self.today, [
            {"issueKey": "doubt:read", "agent": "learning", "kind": "doubt-usual-time", "values": doubt},
            {"issueKey": "doubt:walk", "agent": "life", "kind": "doubt-usual-time", "values": doubt}])

        notes = AgentOrchestrator().area_notes(self.store, "learning")

        self.assertEqual([(note["agent"], note["kind"], note["values"]) for note in notes],
                         [("learning", "due-for-review", {"goalId": french, "goalTitle": "French", "days": 5}),
                          ("learning", "doubt-usual-time", doubt)])

    def test_life_notes_show_low_energy_and_an_area_with_nothing_to_flag_has_no_notes(self):
        self.store.set_energy(self.today, 2)

        self.assertEqual([note["kind"] for note in AgentOrchestrator().area_notes(self.store, "life")], ["low-energy"])
        self.assertEqual(AgentOrchestrator().area_notes(self.store, "work"), [])

    def test_a_day_that_wont_fit_is_the_orchestrators_notice_alone_not_an_area_note(self):
        for title in ("Report", "Slides", "Budget"):
            self.task_on(title, self.today, "work", minutes=300)
        clock = patch("backend.app.database._local_time", return_value="07:00")
        clock.start()
        self.addCleanup(clock.stop)

        notes = AgentOrchestrator().area_notes(self.store, "work")
        day = self.store.bootstrap_day(self.today, None, create_if_missing=False)
        issues = AgentOrchestrator().day_issues(day, self.store.task_profiles(), {}, "07:00")

        self.assertNotIn("day-wont-fit", [note["kind"] for note in notes])
        self.assertIn("day-wont-fit", [issue["kind"] for issue in issues])

    def test_the_area_route_gives_its_notes_for_today_only(self):
        self.goal("Shed", "project", age=5)

        today = self.client.get("/api/areas/project", params={"date": self.today}).json()
        yesterday = self.client.get("/api/areas/project", params={"date": self.yesterday}).json()

        self.assertEqual([note["kind"] for note in today["notes"]], ["stalled"])
        self.assertIsNone(yesterday["notes"])


class AvaMovesACarryOverTests(AreaWeek):
    def chat(self, message):
        return self.client.post("/api/chat", json={"date": self.today, "message": message}).json()

    def test_ava_moves_a_task_from_the_day_the_request_names_to_today(self):
        made = self.client.post("/api/daily-items", json={**self.task("Email", None, 30), "domain": "work"}).json()
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE daily_items SET item_date = ? WHERE id = ?", (days_ago(2), made["id"]))
        then = date.today() - timedelta(days=2)
        english = f"Move “Email” from {then.strftime('%a')} {then.day} {then.strftime('%b')} to today"
        chinese = f"把“Email”从{then.month}月{then.day}日周{'一二三四五六日'[then.weekday()]}移到今天"

        for message in (english, chinese):
            action = self.chat(message)["proposedAction"]

            self.assertIsNotNone(action, message)
            self.assertEqual((action["actionType"], action["payload"]["date"], action["payload"]["changes"]["date"]),
                             ("edit_item", days_ago(2), self.today), message)


if __name__ == "__main__":
    unittest.main()
