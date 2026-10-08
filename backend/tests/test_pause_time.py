import unittest

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.meals import Meal
from backend.app.time_taken import actual_times, current_and_next, limit_stopped, minutes_taken, title_line
from backend.tests.test_time_taken import names, task

LUNCH = Meal("Lunch", "12:00", 60)


class PausedTests(unittest.TestCase):
    """While the day is paused nothing is current and no time counts, toward any task or any limit."""

    def test_pausing_ends_the_current_tasks_stretch_and_nothing_is_current_while_paused(self):
        day = [task("Review", "14:00"), task("Read", None)]
        breaks = [("14:10", None)]
        self.assertEqual(names(current_and_next(day, [], "14:09", breaks)), ("Review", "Read"))
        self.assertIsNone(current_and_next(day, [], "14:30", breaks)[0])
        self.assertIsNone(current_and_next(day, [], "21:50", breaks)[0])

    def test_a_status_set_while_paused_keeps_the_time_as_it_was_at_the_pause(self):
        day = [task("Review", "14:00", status="done", at="14:40"), task("Read", None)]
        self.assertEqual(actual_times(day[0], day, [], "14:40", breaks=[("14:10", None)]), ("14:00", "14:10"))
        self.assertEqual(minutes_taken(day[0], day, [], "14:40", breaks=[("14:10", None)]), 10)

    def test_a_task_never_current_given_a_status_while_paused_takes_no_time(self):
        # Read was made at 14:20, so it was never current before the pause either.
        day = [task("Review", "14:00"), task("Read", None, status="done", at="14:40", made="14:20")]
        self.assertEqual(minutes_taken(day[1], day, [], "14:40", breaks=[("14:10", None)]), 0)

    def test_paused_minutes_never_count_toward_a_limit(self):
        # Review's limit is two hours: 10 minutes before the pause and 110 after it reach it at 17:40, not 16:00.
        day = [task("Review", "14:00"), task("Read", None)]
        breaks = [("14:10", "15:50")]
        self.assertEqual(names(current_and_next(day, [], "17:39", breaks))[0], "Review")
        self.assertEqual(names(current_and_next(day, [], "17:40", breaks))[0], "Read")
        self.assertEqual(limit_stopped(day, [], "17:45", breaks), {"review"})


class ResumeTests(unittest.TestCase):
    """On Resume: a timed task whose planned time covers now; else the task current at the pause, if it has no
    status and is under its limit; else the usual rule."""

    def test_resume_inside_a_timed_tasks_planned_time_picks_that_task(self):
        day = [task("Read", None), task("Review", "14:00")]
        self.assertEqual(names(current_and_next(day, [], "14:20", [("11:00", "14:20")]))[0], "Review")

    def test_resume_outside_one_continues_the_task_current_at_the_pause(self):
        day = [task("Review", "14:00"), task("Email Anna", "15:00", 30), task("Read", None)]
        self.assertEqual(names(current_and_next(day, [], "15:40", [("14:10", "15:40")]))[0], "Review")

    def test_a_paused_task_whose_planned_time_ended_during_the_pause_still_continues(self):
        day = [task("Read", None), task("Review", "14:00", 30)]
        self.assertEqual(names(current_and_next(day, [], "16:00", [("14:10", "16:00")]))[0], "Review")

    def test_with_a_status_or_at_its_limit_the_paused_task_gives_way_to_the_usual_rule(self):
        done = [task("Review", "14:00", status="done", at="14:30"), task("Read", None)]
        self.assertEqual(names(current_and_next(done, [], "16:00", [("14:10", "16:00")]))[0], "Read")
        # Review, 30 minutes, reaches its hour-long limit at 14:00, just as the pause begins.
        limited = [task("Review", "13:00", 30), task("Read", None)]
        self.assertEqual(names(current_and_next(limited, [], "15:00", [("14:00", "15:00")]))[0], "Read")

    def test_a_timed_task_wholly_inside_the_pause_gets_no_time_and_is_never_current_or_next(self):
        day = [task("Review", "14:00"), task("Email Anna", "15:00", 30), task("Read", None)]
        breaks = [("14:10", "15:40")]
        self.assertNotEqual(names(current_and_next(day, [], "14:20", breaks))[1], "Email Anna")
        for now in ("15:00", "15:20", "15:40", "17:00"):
            self.assertNotIn("Email Anna", names(current_and_next(day, [], now, breaks)), now)
        self.assertNotIn("email-anna", limit_stopped(day, [], None, breaks))

    def test_a_meal_during_the_pause_changes_nothing(self):
        day = [task("Review", "11:30"), task("Read", None)]
        self.assertEqual(names(current_and_next(day, [LUNCH], "13:30", [("11:40", "13:30")]))[0], "Review")
        self.assertEqual(minutes_taken(day[0], day, [LUNCH], "14:00", breaks=[("11:40", "13:30")]), 40)


class TitleTests(unittest.TestCase):
    def test_while_paused_the_menu_bar_reads_paused_since(self):
        self.assertEqual(title_line(None, None, 0, "en", paused_since="14:10"), "Paused since 14:10")
        self.assertEqual(title_line(None, None, 0, "zh", paused_since="14:10"), "14:10 起已暂停")


if __name__ == "__main__":
    unittest.main()
