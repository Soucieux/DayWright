import unittest

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.meals import Meal
from backend.app.time_taken import (NAME_CHARACTERS, actual_times, current_and_next, stopped_unreported, taken_so_far,
                                    title_line)

LUNCH = Meal("Lunch", "12:00", 60)


def task(name: str, start: str | None, minutes: int = 60, status: str = "planned", at: str | None = None,
         order: int = 0, made: str | None = None, seen: str | None = None, paused: bool = False) -> dict:
    """A task as the time rules read it: its planned start or None, its set length, its status and when it was set."""
    return {"id": name.lower().replace(" ", "-"), "title": name, "start": start, "minutes": minutes, "status": status,
            "statusAt": at, "createdAt": f"2026-10-07T08:{order:02d}:00+00:00", "madeAt": made, "currentSince": seen,
            "paused": paused}


def names(pair: tuple) -> tuple:
    return tuple(item and item["title"] for item in pair)


class CurrentAndNextTests(unittest.TestCase):
    def test_the_task_whose_time_covers_now_is_current_and_the_next_scheduled_one_is_next(self):
        day = [task("Review", "14:00"), task("Email Anna", "15:30", 30), task("Read", None)]
        self.assertEqual(names(current_and_next(day, [], "14:20")), ("Review", "Email Anna"))

    def test_a_task_with_no_status_runs_past_its_length_until_the_next_start(self):
        day = [task("Review", "14:00"), task("Email Anna", "15:30", 30), task("Read", None)]
        self.assertEqual(names(current_and_next(day, [], "15:20")), ("Review", "Email Anna"))
        self.assertEqual(names(current_and_next(day, [], "15:30")), ("Email Anna", "Read"))

    def test_a_task_given_its_status_hands_over_to_the_first_untimed_task(self):
        day = [task("Review", "14:00", status="done", at="14:40"), task("Email Anna", "15:30", 30),
               task("Read", None, order=2), task("Call Bo", None, order=1)]
        self.assertEqual(names(current_and_next(day, [], "14:50")), ("Call Bo", "Email Anna"))

    def test_with_nothing_scheduled_both_come_from_the_untimed_list_in_the_order_made(self):
        day = [task("Read", None, order=3), task("Call Bo", None, order=1), task("Tidy", None, order=2)]
        self.assertEqual(names(current_and_next(day, [], "10:00")), ("Call Bo", "Tidy"))

    def test_a_meal_stops_the_task_before_it_and_nothing_is_current_during_it(self):
        day = [task("Review", "11:00"), task("Read", None)]
        self.assertEqual(names(current_and_next(day, [LUNCH], "12:10")), (None, "Read"))
        self.assertEqual(names(current_and_next(day, [LUNCH], "13:00")), ("Read", None))

    def test_after_22_00_nothing_is_current_or_next(self):
        day = [task("Review", "21:00"), task("Read", None)]
        self.assertEqual(names(current_and_next(day, [], "21:59")), ("Review", "Read"))
        self.assertEqual(names(current_and_next(day, [], "22:00")), (None, None))

    def test_tasks_reported_or_paused_with_their_goal_are_neither(self):
        day = [task("Review", "14:00", status="skipped", at="13:00"), task("Plan", None, paused=True),
               task("Read", None, order=1), task("Email Anna", "15:30", 30, status="done", at="13:30")]
        self.assertEqual(names(current_and_next(day, [], "14:10")), ("Read", None))

    def test_a_task_made_today_is_not_current_before_it_was_made(self):
        day = [task("Read", None, made="13:00")]
        self.assertEqual(names(current_and_next(day, [], "12:00")), (None, "Read"))
        self.assertEqual(names(current_and_next(day, [], "13:00")), ("Read", None))


class ActualTimeTests(unittest.TestCase):
    def test_a_status_set_within_its_time_ends_it_then(self):
        day = [task("Review", "14:00"), task("Email Anna", "15:30", 30)]
        self.assertEqual(actual_times(day[0], day, [], "14:50"), ("14:00", "14:50"))

    def test_with_no_status_a_task_stops_at_the_next_start_and_a_late_one_cannot_overlap_it(self):
        day = [task("Review", "14:00"), task("Email Anna", "15:30", 30)]
        self.assertEqual(actual_times(day[0], day, [], "15:40"), ("14:00", "15:30"))
        self.assertTrue(stopped_unreported(day[0], day, [], "15:40"))
        self.assertFalse(stopped_unreported(day[0], day, [], "15:10"))

    def test_a_late_tick_on_the_earlier_task_sets_only_its_status_and_the_next_keeps_its_planned_start(self):
        late = [task("Review", "14:00", status="done", at="15:40"), task("Email Anna", "15:30", 30)]
        self.assertEqual(actual_times(late[0], late, [], "15:40"), ("14:00", "15:30"))
        self.assertEqual(actual_times(late[1], late, [], "16:10"), ("15:30", "16:10"))
        self.assertEqual(names(current_and_next(late, [], "15:45")), ("Email Anna", None), "Email Anna keeps running")

    def test_no_status_ever_ends_or_changes_another_task(self):
        for at in (None, "14:30", "15:10", "15:40", "17:00"):
            review = task("Review", "14:00", status="planned" if at is None else "done", at=at)
            day = [review, task("Email Anna", "15:30", 30), task("Read", None)]
            self.assertEqual(actual_times(day[1], day, [], "16:10"), ("15:30", "16:10"), at)
            self.assertEqual(names(current_and_next(day, [], "16:05")), ("Email Anna", "Read"), at)

    def test_a_meal_stops_a_task_as_the_next_task_does(self):
        day = [task("Review", "11:00")]
        self.assertEqual(actual_times(day[0], day, [LUNCH], "12:30"), ("11:00", "12:00"))

    def test_the_last_task_stops_at_22_00_and_a_status_set_after_its_day_ends_it_there(self):
        day = [task("Review", "20:00")]
        self.assertEqual(actual_times(day[0], day, [], "23:00"), ("20:00", "22:00"))
        self.assertEqual(actual_times(day[0], day, [], None), ("20:00", "22:00"))

    def test_an_untimed_task_starts_when_it_became_current(self):
        day = [task("Review", "09:00", status="done", at="09:50"), task("Read", None), task("Email Anna", "11:00", 30)]
        self.assertEqual(actual_times(day[1], day, [], "10:30"), ("09:50", "10:30"))
        self.assertEqual(taken_so_far(day[1], day, [], "10:30"), 40)

    def test_an_untimed_task_stops_at_the_next_scheduled_start_and_counts_from_its_return(self):
        day = [task("Review", "09:00", status="done", at="09:50"), task("Read", None),
               task("Email Anna", "11:00", 30, status="done", at="11:20")]
        self.assertEqual(actual_times(day[1], day, [], "10:40"), ("09:50", "10:40"))
        self.assertEqual(actual_times(day[1], day, [], "12:00"), ("11:20", "12:00"))

    def test_an_untimed_task_current_from_the_days_start_starts_when_daywright_first_saw_it(self):
        day = [task("Read", None, seen="08:10")]
        self.assertEqual(actual_times(day[0], day, [], "09:00"), ("08:10", "09:00"))

    def test_a_task_never_seen_current_is_given_its_set_length_back_from_its_status(self):
        unseen = [task("Read", None, minutes=45)]
        self.assertEqual(actual_times(unseen[0], unseen, [], "09:00"), ("08:15", "09:00"))
        # Read was never current, as Call Bo came first; it starts no earlier than Review stopped.
        after = [task("Review", "08:00", status="done", at="08:40"), task("Call Bo", None, order=1),
                 task("Read", None, minutes=45, order=2)]
        self.assertEqual(actual_times(after[2], after, [], "09:00"), ("08:40", "09:00"))

    def test_a_skip_before_a_task_began_takes_no_time_and_a_late_skip_keeps_the_time_that_passed(self):
        day = [task("Review", "14:00"), task("Email Anna", "15:30", 30)]
        self.assertEqual(actual_times(day[1], day, [], "14:10", status="skipped"), ("14:10", "14:10"))
        self.assertEqual(actual_times(day[0], day, [], "15:10", status="skipped"), ("14:00", "15:10"))

    def test_a_task_done_before_its_planned_start_takes_its_set_length_back_from_then(self):
        day = [task("Email Anna", "15:30", 30)]
        self.assertEqual(actual_times(day[0], day, [], "10:00"), ("09:30", "10:00"))


class TitleTests(unittest.TestCase):
    def test_the_title_names_the_current_task_its_time_taken_and_set_time_and_the_next(self):
        self.assertEqual(title_line(task("Review", "14:00"), task("Email Anna", "15:30"), 32, "en"),
                         "Review · 32 / 60 min · next: Email Anna")
        self.assertEqual(title_line(task("Review", "14:00"), task("Email Anna", "15:30"), 32, "zh"),
                         "Review · 32 / 60 分钟 · 下一项：Email Anna")

    def test_names_are_cut_to_a_short_length(self):
        long = "Prepare the quarterly report draft"
        line = title_line(task(long, "14:00"), task(long, None), 5, "en")
        cut = long[:NAME_CHARACTERS - 1].rstrip() + "…"
        self.assertEqual(line, f"{cut} · 5 / 60 min · next: {cut}")
        self.assertEqual(NAME_CHARACTERS, 16)

    def test_without_a_current_task_the_title_names_the_next_and_with_neither_it_is_empty(self):
        self.assertEqual(title_line(None, task("Email Anna", "15:30"), 0, "en"), "Next: Email Anna")
        self.assertEqual(title_line(None, task("Email Anna", "15:30"), 0, "zh"), "下一项：Email Anna")
        self.assertEqual(title_line(task("Review", "14:00"), None, 3, "en"), "Review · 3 / 60 min")
        self.assertEqual(title_line(None, None, 0, "en"), "")


if __name__ == "__main__":
    unittest.main()
