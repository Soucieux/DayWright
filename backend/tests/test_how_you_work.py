import unittest
from datetime import date, timedelta

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.how_you_work import (ALL_TIME, LAST_THIRTY, MOST_GOALS, MOST_LINES, MOST_TASK_LINES, context, day_words,
                                      lines, of_store)
from backend.tests.test_pattern_records import PatternDay

TODAY = "2026-10-14"


def day(back: int) -> str:
    return (date.fromisoformat(TODAY) - timedelta(days=back)).isoformat()


def record(when: str, title: str = "Review", domain: str = "work", planned: int = 60, status: str = "done",
           minutes: int | None = 60, end: str | None = "10:30", at: str | None = None, estimate: int | None = None) -> dict:
    """A task as Database.pattern_records gives it."""
    return {"date": when, "title": title, "domain": domain, "planned": planned, "estimate": estimate, "status": status,
            "minutes": minutes, "statusAt": at or end, "end": end, "series": None}


def profile(title: str, scheduled: int, done: int = 0, skipped: int = 0, unreported: int = 0,
            done_minutes: int | None = None, last_minutes: int = 60, domain: str = "work") -> dict:
    """A task profile as Database.task_profiles gives one."""
    return {"title": title, "domain": domain, "scheduled": scheduled, "done": done, "partial": 0, "skipped": skipped,
            "unreported": unreported, "doneMinutes": done_minutes, "lastMinutes": last_minutes}


def made(records: list[dict], energy: list[dict] = (), profiles: list[dict] = (), goals: list[dict] = (),
         language: str = "en") -> dict:
    return lines(records, list(energy), list(profiles), list(goals), TODAY, language)


class TallyAndThresholdTests(unittest.TestCase):
    def test_a_few_records_give_only_their_tally_as_every_figure_is_below_its_threshold(self):
        summary = made([record(day(2)), record(day(1), status="skipped", minutes=None, end=None)])
        self.assertEqual(summary, {ALL_TIME: ["2 tasks recorded: 1 done, 1 skipped."], LAST_THIRTY: []})

    def test_the_tally_counts_each_status_once_and_names_those_left_without_one(self):
        summary = made([record(day(3)), record(day(3), status="partial", minutes=30), record(day(2), status="noReply"),
                        record(day(1), status="dayPaused", minutes=None)])
        self.assertEqual(summary[ALL_TIME][0], "4 tasks recorded: 1 done, 1 partly done, 2 without a status.")

    def test_nothing_recorded_gives_no_lines(self):
        self.assertEqual(made([]), {ALL_TIME: [], LAST_THIRTY: []})


class FigureTests(unittest.TestCase):
    def test_an_area_over_its_plan_once_it_has_enough_fully_done_tasks(self):
        summary = made([record(day(back), minutes=75) for back in (3, 2, 1)])
        self.assertIn("Work tasks take 25% longer than planned.", summary[ALL_TIME])
        self.assertNotIn("Work tasks take 25% longer than planned.", made([record(day(back), minutes=75) for back in (2, 1)])[ALL_TIME])

    def test_best_hours_once_ten_fully_done_tasks_have_real_times(self):
        finished = [record(day(back), end="09:40" if back <= 6 else "10:20") for back in range(1, 11)]
        self.assertIn("Tasks are most often finished from 09:00 to 11:00.", made(finished)[ALL_TIME])
        self.assertIn("Tasks are all finished between 10:00 and 11:00.",
                      made([record(day(back), end="10:20") for back in range(1, 11)])[ALL_TIME])

    def test_energy_on_days_of_low_energy(self):
        tired = [{"date": day(back), "average": 2.0} for back in (3, 2, 1)]
        summary = made([record(day(back), minutes=72, domain="life") for back in (3, 2, 1)], energy=tired)
        self.assertIn("On days of low energy tasks take 20% longer than planned.", summary[ALL_TIME])

    def test_the_agents_estimates_from_the_earliest_day_to_the_latest(self):
        estimated = [record(day(3), minutes=80, estimate=60), record(day(2), minutes=70, estimate=60),
                     record(day(1), minutes=64, estimate=60)]
        self.assertIn("The agents' estimates are 4 min off the real time, down from 20 min.", made(estimated)[ALL_TIME])

    def test_estimates_that_matched_at_first_say_so_rather_than_up_from_none(self):
        estimated = [record(day(3), minutes=60, estimate=60), record(day(2), minutes=66, estimate=60),
                     record(day(1), minutes=72, estimate=60)]
        self.assertIn("The agents' estimates are 12 min off the real time; at first they matched it.", made(estimated)[ALL_TIME])
        self.assertIn("代理的估时与真实用时相差 12 分钟；起初两者一致。", made(estimated, language="zh")[ALL_TIME])
        self.assertFalse(any("0 min" in line for line in made(estimated)[ALL_TIME]))

    def test_time_by_outcome_and_the_reporting_habit(self):
        summary = made([record(day(3), minutes=90), record(day(2), status="noReply", minutes=30, at=None, end="11:00"),
                        record(day(1), minutes=60, at="21:00")])
        self.assertIn("83% of the time recorded went to fully done tasks, and 30 min to tasks left without a status.",
                      summary[ALL_TIME])
        self.assertIn("33% of statuses were set right away.", summary[ALL_TIME])


class SetTests(unittest.TestCase):
    def test_a_longer_history_gives_all_time_and_the_last_30_days_each_its_own_lines(self):
        older = [record(day(back), minutes=90) for back in (60, 59, 58)]
        recent = [record(day(back), minutes=60) for back in (3, 2, 1)]
        summary = made([*older, *recent])
        self.assertEqual(summary[ALL_TIME][0], "6 tasks recorded: 6 done.")
        self.assertEqual(summary[LAST_THIRTY][0], "3 tasks recorded: 3 done.")
        self.assertIn("Work tasks take 25% longer than planned.", summary[ALL_TIME])
        self.assertIn("Every area's tasks take close to the time planned.", summary[LAST_THIRTY])

    def test_tasks_goals_and_every_line_are_held_to_their_limits(self):
        profiles = [profile(f"Task {number}", scheduled=6, skipped=4) for number in range(6)]
        goals = [{"title": f"Goal {number}", "status": "active", "done": 4, "recent": 2, "lastDone": day(1)}
                 for number in range(8)]
        summary = made([record(day(back), minutes=60, end="10:20") for back in range(1, 41)], profiles=profiles, goals=goals)
        task_lines = [line for line in summary[ALL_TIME] if line.startswith("“Task")]
        goal_lines = [line for line in summary[ALL_TIME] if line.startswith("“Goal")]
        self.assertEqual((len(task_lines), len(goal_lines)), (MOST_TASK_LINES, MOST_GOALS))
        self.assertLessEqual(len(summary[ALL_TIME]) + len(summary[LAST_THIRTY]), MOST_LINES)


class TaskAndGoalTests(unittest.TestCase):
    def test_tasks_often_skipped_or_left_without_a_status_and_those_that_take_other_than_planned(self):
        summary = made([record(day(1))], profiles=[
            profile("Stretch", scheduled=6, skipped=4, done=2), profile("Journal", scheduled=5, unreported=3, done=2),
            profile("Weekly review", scheduled=5, done=5, done_minutes=75, last_minutes=60),
            profile("Read", scheduled=5, done=5, done_minutes=65, last_minutes=60)])
        self.assertIn("“Stretch” was skipped 4 of 6 times.", summary[ALL_TIME])
        self.assertIn("“Journal” was left without a status 3 of 5 times.", summary[ALL_TIME])
        self.assertIn("“Weekly review” usually takes 1 h 15 min when done; it is planned for 1 h.", summary[ALL_TIME])
        self.assertFalse(any(line.startswith("“Read”") for line in summary[ALL_TIME]), "within 10 minutes of its plan")

    def test_each_active_goals_momentum_the_latest_first_and_a_paused_one_left_out(self):
        summary = made([record(day(1))], goals=[
            {"title": "Shed", "status": "active", "done": 3, "recent": 0, "lastDone": day(9)},
            {"title": "Spanish to B1", "status": "active", "done": 24, "recent": 9, "lastDone": day(1)},
            {"title": "Bike", "status": "paused", "done": 2, "recent": 0, "lastDone": day(40)},
            {"title": "Website", "status": "active", "done": 0, "recent": 0, "lastDone": None}])
        goal_lines = [line for line in summary[ALL_TIME] if line.startswith("“")]
        self.assertEqual(goal_lines, ["“Spanish to B1”: 24 tasks done, 9 in the last 30 days, the last on 13 Oct.",
                                      "“Shed”: 3 tasks done; nothing for 9 days.",
                                      "“Website”: nothing done yet."])


class LanguageAndContextTests(unittest.TestCase):
    def test_chinese(self):
        summary = made([record(day(back), minutes=75) for back in (3, 2, 1)], language="zh")
        self.assertEqual(summary[ALL_TIME][0], "记录了 3 项任务：3 项已完成。")
        self.assertIn("工作任务比计划多用 25%。", summary[ALL_TIME])

    def test_what_the_model_reads_names_both_sets(self):
        summary = {ALL_TIME: ["6 tasks recorded: 6 done.", "Work tasks take 25% longer than planned."],
                   LAST_THIRTY: ["3 tasks recorded: 3 done."]}
        self.assertEqual(context(summary), "How the user works, from their records. All time: 6 tasks recorded: 6 done. "
                                           "Work tasks take 25% longer than planned. Last 30 days: 3 tasks recorded: 3 done.")
        self.assertEqual(context({ALL_TIME: [], LAST_THIRTY: []}), "")


class StoreTests(PatternDay):
    def test_the_summary_is_made_from_the_stores_records_its_profiles_and_each_goal(self):
        goal = self.client.post("/api/goals", json={"title": "Spanish to B1", "domain": "learning"}).json()
        days = [(date.fromisoformat(self.today) - timedelta(days=back)).isoformat() for back in (3, 2, 1)]
        for number, when in enumerate(days):
            lesson = self.on_day(f"Lesson {number}", when, "10:00", 60)
            self.sql("UPDATE daily_items SET goal_id = ? WHERE id = ?", goal["id"], lesson["id"])
            self.took(lesson, "done", "10:00", "11:15", 75, "11:20")
        summary = of_store(self.store, self.today, "en")
        self.assertEqual(summary[ALL_TIME][0], "3 tasks recorded: 3 done.")
        self.assertIn("Learn tasks take 25% longer than planned.", summary[ALL_TIME])
        self.assertIn(f"“Spanish to B1”: 3 tasks done, 3 in the last 30 days, the last on {day_words(days[-1], 'en')}.",
                      summary[ALL_TIME])

    def test_a_goals_momentum_counts_its_done_tasks_those_since_a_day_and_the_last(self):
        goal = self.client.post("/api/goals", json={"title": "Shed", "domain": "project"}).json()
        old, recent = ((date.fromisoformat(self.today) - timedelta(days=back)).isoformat() for back in (40, 5))
        for when in (old, recent):
            step = self.on_day("Step", when, "10:00", 60)
            self.sql("UPDATE daily_items SET goal_id = ? WHERE id = ?", goal["id"], step["id"])
            self.took(step, "done", "10:00", "11:00", 60, "11:05")
        since = (date.fromisoformat(self.today) - timedelta(days=29)).isoformat()
        momentum = {item["title"]: item for item in self.store.goal_momentum(self.today, since)}
        self.assertEqual(momentum["Shed"], {"title": "Shed", "status": "active", "done": 2, "recent": 1, "lastDone": recent})


if __name__ == "__main__":
    unittest.main()
