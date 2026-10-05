import unittest

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.meals import Meal
from backend.app.planner import (PlanItem, build_recorded_variants, build_variants, day_load, fit_around_meal,
                                 has_collisions, meal_overlap, minutes_by_domain, notes_without)


def placed(start, title, minutes, estimated=False):
    """A task a set plan placed at a start, flexible, with its length given or estimated."""
    return PlanItem(start, title, "", "learning", minutes, "flexible", estimated=estimated)


class FitAroundMealTests(unittest.TestCase):
    """A small move of a meal adjusts the set plan's tasks next to it, and nothing else."""

    DINNER = Meal("Dinner", "18:00", 60)

    def test_a_task_running_into_the_moved_meal_is_shortened_when_its_estimate_allows(self):
        fitted = fit_around_meal((placed("11:45", "Read", 60, estimated=True), placed("14:00", "Walk", 30)),
                                 Meal("Lunch", "12:30", 60), (self.DINNER,))
        self.assertEqual([(item.title, item.start, item.duration_minutes) for item in fitted],
                         [("Read", "11:45", 45), ("Walk", "14:00", 30)])

    def test_a_task_the_moved_meal_starts_inside_is_shifted_earlier_when_the_time_before_is_free(self):
        fitted = fit_around_meal((placed("11:45", "Read", 60),), Meal("Lunch", "12:30", 60), (self.DINNER,))
        self.assertEqual([(item.start, item.duration_minutes) for item in fitted], [("11:30", 60)])

    def test_a_task_inside_the_moved_meal_is_shifted_to_after_it(self):
        fitted = fit_around_meal((placed("13:00", "Read", 30), placed("15:00", "Walk", 30)),
                                 Meal("Lunch", "12:30", 60), (self.DINNER,))
        self.assertEqual([(item.title, item.start) for item in fitted], [("Read", "13:30"), ("Walk", "15:00")])

    def test_an_estimate_is_never_shortened_below_30_minutes(self):
        self.assertIsNone(fit_around_meal((placed("12:10", "Read", 40, estimated=True), placed("11:30", "Call", 40)),
                                          Meal("Lunch", "12:30", 60), (self.DINNER,)))

    def test_a_move_with_no_room_around_the_meal_cannot_be_fitted(self):
        self.assertIsNone(fit_around_meal((placed("13:15", "Read", 45), placed("13:30", "Walk", 60)),
                                          Meal("Lunch", "12:30", 60), (self.DINNER,)))

# A day whose lunch moved to 13:00 for 45 minutes and whose dinner moved to 19:00.
MOVED_MEALS = (Meal("Lunch", "13:00", 45), Meal("Dinner", "19:00", 60))


class MovedMealsTests(unittest.TestCase):
    """Every plan keeps the day's own meal times free, whatever they are."""

    def test_every_plan_keeps_the_days_own_meal_times(self):
        for variant in build_recorded_variants((untimed("Read", "learning", 60),), earliest="12:00", meals=MOVED_MEALS):
            self.assertEqual({meal.title: (meal.start, meal.duration_minutes) for meal in variant["meals"]},
                             {"Lunch": ("13:00", 45), "Dinner": ("19:00", 60)}, variant["slug"])
            self.assertFalse(has_collisions((*variant["items"], *variant["meals"])), variant["slug"])

    def test_a_task_takes_the_hour_a_moved_lunch_leaves_free(self):
        balanced = build_recorded_variants((untimed("Read", "learning", 60),), earliest="12:00", meals=MOVED_MEALS)[0]
        self.assertEqual(starts(balanced), {"Read": "12:00"})

    def test_meal_overlap_names_a_moved_meal(self):
        self.assertEqual(meal_overlap("13:30", 15, MOVED_MEALS).title, "Lunch")
        self.assertIsNone(meal_overlap("12:00", 60, MOVED_MEALS))
        self.assertIsNone(meal_overlap("18:00", 60, MOVED_MEALS))

    def test_the_day_load_counts_the_moved_meals_lengths(self):
        free = day_load((untimed("Read", "learning", 60),), "09:00", MOVED_MEALS)["freeMinutes"]
        self.assertEqual(free, (22 - 9) * 60 - 45 - 60)

    def test_the_local_model_reads_the_moved_meal_times(self):
        seen = []
        build_recorded_variants((untimed("Read", "learning", 60), untimed("Walk", "life", 30)), earliest="08:00",
                                meals=MOVED_MEALS, choose=lambda context: seen.append(context))
        self.assertEqual(seen[0]["day"]["meals"], ["Lunch 13:00–13:45", "Dinner 19:00–20:00"])


def untimed(title, domain, minutes, **flags):
    """A flexible task without a start time, as the user records one."""
    return PlanItem(None, title, "", domain, minutes, **flags)


def fixed(start, title, domain, minutes):
    """A task fixed at a start time."""
    return PlanItem(start, title, "", domain, minutes, "fixed")


def starts(variant):
    """Each task's title and start time in one plan."""
    return {item.title: item.start for item in variant["items"]}


def lengths(variant):
    """Each task's title and length in one plan."""
    return {item.title: item.duration_minutes for item in variant["items"]}


def plan(variants, slug):
    """The plan of one kind among the proposed ones."""
    return next(variant for variant in variants if variant["slug"] == slug)


def slugs(variants):
    return [variant["slug"] for variant in variants]


def meals(variant):
    """Each meal's title and start time in one plan."""
    return {meal.title: meal.start for meal in variant["meals"]}


def minutes(clock_text):
    return int(clock_text[:2]) * 60 + int(clock_text[3:])


def clearly_different(first, second):
    """Whether two plans' tasks come in another order and move an hour in all, or end an hour apart."""
    one, other = first["items"], second["items"]
    times = {item.title: (minutes(item.start), item.duration_minutes) for item in other}
    moved = sum(abs(minutes(item.start) - times[item.title][0]) + abs(item.duration_minutes - times[item.title][1])
                for item in one)
    ends = [max(minutes(item.start) + item.duration_minutes for item in plan_items) for plan_items in (one, other)]
    reordered = [item.title for item in one] != [item.title for item in other]
    return (reordered and moved >= 60) or abs(ends[0] - ends[1]) >= 60


class DemoPlanTests(unittest.TestCase):
    def test_each_variant_has_no_overlapping_items(self):
        for variant in build_variants():
            self.assertFalse(has_collisions(variant["items"]), variant["name"])

    def test_each_variant_represents_all_core_domains(self):
        for variant in build_variants():
            totals = minutes_by_domain(variant["items"])
            for domain in ("learning", "life", "work", "project"):
                self.assertGreater(totals[domain], 0, (variant["name"], domain))

    def test_variants_make_materially_different_tradeoffs(self):
        totals = {variant["slug"]: minutes_by_domain(variant["items"]) for variant in build_variants()}
        self.assertGreater(totals["focused"]["learning"], totals["gentle"]["learning"])
        self.assertGreater(totals["gentle"]["life"], totals["focused"]["life"])


class PlanBasicsTests(unittest.TestCase):
    def test_every_plan_keeps_fixed_times_and_places_every_task_without_overlap(self):
        owned = (fixed("10:00", "Dentist", "life", 60), untimed("Study", "learning", 60),
                 untimed("Weekly report", "work", 30), untimed("Prototype", "project", 45), untimed("Laundry", "life", 30))
        variants = build_recorded_variants(owned, earliest="09:00")
        self.assertEqual(len(variants), 3)
        for variant in variants:
            self.assertTrue(all(item.start for item in variant["items"]), variant["slug"])
            self.assertFalse(has_collisions(variant["items"]), variant["slug"])
            self.assertEqual(starts(variant)["Dentist"], "10:00")
            self.assertTrue(all(item.start >= "09:00" for item in variant["items"]))
        self.assertEqual(len({tuple(sorted(starts(variant).items())) for variant in variants}), 3)

    def test_plans_place_tasks_from_nine_at_the_earliest(self):
        variants = build_recorded_variants((untimed("Study", "learning", 60), untimed("Walk", "life", 30)),
                                           earliest="06:00")
        self.assertEqual(starts(variants[0]), {"Walk": "09:00", "Study": "09:30"})
        self.assertTrue(all(item.start >= "09:00" for variant in variants for item in variant["items"]))

    def test_a_task_the_user_fixed_outside_the_planned_hours_stays_where_it_is(self):
        variants = build_recorded_variants((fixed("07:00", "Run", "life", 45), untimed("Study", "learning", 60)),
                                           earliest="06:00")
        self.assertTrue(all(starts(variant)["Run"] == "07:00" for variant in variants))

    def test_every_plan_keeps_an_hour_for_lunch_and_dinner(self):
        owned = (untimed("Report", "work", 120), untimed("Build", "project", 120), untimed("Read", "learning", 60),
                 untimed("Errands", "life", 90), untimed("Draft", "work", 120))
        for variant in build_recorded_variants(owned, earliest="09:00"):
            self.assertEqual(meals(variant), {"Lunch": "12:00", "Dinner": "18:00"}, variant["slug"])
            self.assertEqual({meal.duration_minutes for meal in variant["meals"]}, {60})
            self.assertFalse(has_collisions((*variant["items"], *variant["meals"])), variant["slug"])

    def test_meals_keep_their_hours_and_one_a_fixed_task_already_takes_is_left_out(self):
        owned = (fixed("11:30", "Client call", "work", 60), untimed("Study", "learning", 60))
        self.assertEqual(meals(build_recorded_variants(owned, earliest="09:00")[0]), {"Dinner": "18:00"})

    def test_a_meal_that_is_over_is_left_out_and_one_under_way_is_kept(self):
        self.assertEqual(meals(build_recorded_variants((untimed("Study", "learning", 60),), earliest="15:00")[0]),
                         {"Dinner": "18:00"})
        during = build_recorded_variants((untimed("Study", "learning", 60),), earliest="12:20")[0]
        self.assertEqual(meals(during), {"Lunch": "12:00", "Dinner": "18:00"})
        self.assertEqual(starts(during)["Study"], "13:00")

    def test_meal_overlap_names_the_meal_a_time_would_take(self):
        self.assertEqual(meal_overlap("11:30", 45).title, "Lunch")
        self.assertEqual(meal_overlap("18:45", 30).title, "Dinner")
        self.assertIsNone(meal_overlap("11:00", 60))
        self.assertIsNone(meal_overlap("13:00", 300))

    def test_nothing_is_placed_before_the_time_given(self):
        variants = build_recorded_variants((untimed("Study", "learning", 60),), earliest="13:10")
        self.assertTrue(all(item.start >= "13:15" for variant in variants for item in variant["items"]))

    def test_tasks_that_cannot_fit_before_the_day_ends_are_refused(self):
        with self.assertRaisesRegex(ValueError, "free time"):
            build_recorded_variants((untimed("Study", "learning", 60),), earliest="21:30")

    def test_overlapping_fixed_tasks_are_refused(self):
        with self.assertRaisesRegex(ValueError, "overlap"):
            build_recorded_variants((fixed("09:00", "Call", "work", 60), fixed("09:30", "Meeting", "work", 30)))

    def test_only_fixed_tasks_leave_one_plan(self):
        self.assertEqual(slugs(build_recorded_variants((fixed("09:00", "Call", "work", 60),))), ["balanced"])

    def test_task_cannot_extend_beyond_midnight(self):
        self.assertTrue(has_collisions([PlanItem("23:50", "Late block", "", "life", 30)]))

    def test_tasks_that_overlap_or_run_past_midnight_are_named(self):
        meeting = fixed("10:00", "Meeting", "work", 60)
        with self.assertRaisesRegex(ValueError, r"^“Meeting” \(10:00–11:00\) and “Call” \(10:30–11:00\) overlap"):
            build_recorded_variants([meeting, fixed("10:30", "Call", "work", 30)], earliest="07:00")
        with self.assertRaisesRegex(ValueError, r"^“Night walk” at 23:30 runs past midnight"):
            build_recorded_variants([meeting, fixed("23:30", "Night walk", "life", 60)], earliest="07:00")

    def test_an_estimated_length_is_shortened_on_request_or_by_a_finding_but_never_below_15(self):
        owned = (untimed("Practice French", "learning", 25, estimated=True),
                 untimed("Guide", "project", 60, estimated=True))
        memory = [{"taskTitle": "Practice French", "domain": "learning", "shortenRequests": 2}]
        findings = [{"kind": "shorten", "taskTitle": "Guide", "domain": "project"}]
        for variant in build_recorded_variants(owned, memory, earliest="09:00", findings=findings):
            self.assertEqual(lengths(variant)["Practice French"], 15, variant["slug"])
            self.assertLessEqual(lengths(variant)["Guide"], 45, variant["slug"])

    def test_no_plan_shortens_a_length_the_user_set(self):
        owned = (untimed("Practice French", "learning", 25), untimed("Guide", "project", 60),
                 untimed("Walk", "life", 45))
        memory = [{"taskTitle": "Practice French", "domain": "learning", "shortenRequests": 2}]
        findings = [{"kind": "shorten", "taskTitle": "Guide", "domain": "project"},
                    {"kind": "area-life", "domain": "life", "lighter": True}]
        for variant in build_recorded_variants(owned, memory, earliest="09:00", findings=findings):
            for title, minutes in (("Practice French", 25), ("Guide", 60), ("Walk", 45)):
                self.assertGreaterEqual(lengths(variant)[title], minutes, (variant["slug"], title))


class DefaultPlansTests(unittest.TestCase):
    def test_a_day_with_few_tasks_gets_balanced_deep_focus_and_lighter_day(self):
        variants = build_recorded_variants([untimed("Guide", "project", 60), untimed("Walk", "life", 30)], earliest="07:00")
        self.assertEqual(slugs(variants), ["balanced", "focused", "gentle"])
        self.assertEqual([variant["name"] for variant in variants], ["Balanced", "Deep focus", "Lighter day"])

    def test_balanced_takes_the_areas_in_turn_by_priority(self):
        owned = (untimed("Read", "learning", 30), untimed("Walk", "life", 30),
                 untimed("Report", "work", 30), untimed("Build", "project", 30))
        balanced = plan(build_recorded_variants(owned, earliest="08:00"), "balanced")
        self.assertEqual(starts(balanced), {"Report": "09:00", "Build": "09:30", "Walk": "10:00", "Read": "10:30"})

    def test_a_low_energy_day_lists_lighter_day_first_and_says_why(self):
        tasks = [untimed("Guide", "project", 60), untimed("Walk", "life", 30)]
        usual = build_recorded_variants(tasks, earliest="07:00")
        lighter = build_recorded_variants(tasks, earliest="07:00",
                                          findings=[{"kind": "area-life", "domain": "life", "lighter": True}])
        self.assertEqual(slugs(lighter), ["gentle", "balanced", "focused"])
        self.assertTrue(lighter[0]["rationale"].startswith("Listed first because the Life agent advised a lighter day. "))
        self.assertEqual(slugs(build_recorded_variants(tasks, earliest="07:00", findings=[
            {"kind": "area-life", "domain": "life", "lighter": False}])), slugs(usual))


class DeepFocusTests(unittest.TestCase):
    def test_focus_tasks_go_back_to_back_in_the_longest_free_stretch(self):
        owned = (fixed("09:00", "Stand-up", "work", 30), fixed("14:00", "Review", "work", 60),
                 untimed("Report", "work", 60), untimed("Build", "project", 60), untimed("Walk", "life", 30))
        focused = plan(build_recorded_variants(owned, earliest="08:00"), "focused")
        # Free stretches: 09:30–12:00, 13:00–14:00, 15:00–18:00 and 19:00–22:00; the first longest wins.
        self.assertEqual(starts(focused), {"Stand-up": "09:00", "Walk": "09:30", "Review": "14:00",
                                           "Report": "15:00", "Build": "16:00"})
        self.assertEqual(lengths(focused)["Report"], 60)
        self.assertIn("“Report” and “Build” back to back", focused["rationale"])
        self.assertIn("15:00–17:00", focused["rationale"])


class LighterDayTests(unittest.TestCase):
    def test_lighter_day_starts_later_with_breaks_life_first_and_trims_the_lowest_priority_estimate(self):
        owned = (untimed("Report", "work", 60, estimated=True), untimed("Build", "project", 60, estimated=True),
                 untimed("Read", "learning", 60, estimated=True), untimed("Walk", "life", 30))
        gentle = plan(build_recorded_variants(owned, earliest="08:00", preferences={"gentle": 5}), "gentle")
        self.assertEqual(lengths(gentle), {"Walk": 30, "Report": 60, "Build": 60, "Read": 45})
        self.assertEqual(starts(gentle)["Walk"], "10:00")
        self.assertEqual(starts(gentle)["Report"], "10:45")
        self.assertIn("“Walk”", gentle["rationale"])
        self.assertIn("“Read” from 60 to 45 minutes", gentle["rationale"])

    def test_summary_advice_about_an_area_makes_lighter_day_trim_that_area_first(self):
        owned = (untimed("Study", "learning", 60, estimated=True), untimed("Home care", "life", 60, estimated=True))
        guidance = [{"domain": "life", "priority": "soft",
                     "content": "Review the size or timing of life work before the next plan."}]
        gentle = plan(build_recorded_variants(owned, guidance=guidance, earliest="09:00"), "gentle")
        self.assertEqual(lengths(gentle), {"Study": 60, "Home care": 45})

    def test_on_a_low_energy_day_lighter_day_trims_every_estimated_length(self):
        owned = (untimed("Report", "work", 60, estimated=True), untimed("Build", "project", 60, estimated=True),
                 untimed("Read", "learning", 20, estimated=True), untimed("Walk", "life", 30),
                 untimed("Plan", "work", 45, estimated=True))
        gentle = build_recorded_variants(owned, earliest="08:00",
                                         findings=[{"kind": "area-life", "domain": "life", "lighter": True}])[0]
        self.assertEqual(gentle["slug"], "gentle")
        self.assertEqual(lengths(gentle), {"Walk": 30, "Report": 45, "Build": 45, "Read": 15, "Plan": 30})


class AdaptivePlansTests(unittest.TestCase):
    def test_finish_early_fills_the_gaps_so_the_day_ends_sooner(self):
        owned = (fixed("11:00", "Workshop", "work", 60), untimed("Errand", "life", 75),
                 untimed("Notes", "learning", 60), untimed("Read", "learning", 60))
        variants = build_recorded_variants(owned, earliest="08:00")
        early = plan(variants, "early")
        self.assertEqual(starts(early), {"Notes": "09:00", "Read": "10:00", "Workshop": "11:00", "Errand": "13:00"})
        self.assertEqual(starts(plan(variants, "balanced"))["Errand"], "09:00")
        self.assertIn("done by 14:15", early["rationale"])
        self.assertIn("45 minutes sooner", early["rationale"])

    def test_finish_early_is_not_offered_when_it_ends_no_sooner(self):
        owned = (untimed("Report", "work", 30), untimed("Walk", "life", 30), untimed("Read", "learning", 30))
        self.assertNotIn("early", slugs(build_recorded_variants(owned, earliest="08:00")))

    def test_quick_wins_first_places_the_shortest_tasks_first(self):
        owned = (untimed("Build", "project", 90), untimed("Study", "learning", 60), untimed("Email", "work", 15),
                 untimed("Water plants", "life", 15), untimed("Call mum", "life", 20))
        quick = plan(build_recorded_variants(owned, earliest="08:00", preferences={"quickwins": 1}), "quickwins")
        # Build doesn't fit before lunch, so it waits until 13:00.
        self.assertEqual(starts(quick), {"Email": "09:00", "Water plants": "09:15", "Call mum": "09:30",
                                         "Study": "10:00", "Build": "13:00"})
        self.assertIn("“Email”, “Water plants”, and “Call mum” first", quick["rationale"])

    def test_easiest_first_starts_with_the_tasks_you_usually_finish(self):
        findings = [
            {"kind": "shorten", "taskTitle": "Guide", "domain": "project", "done": 1, "partial": 2, "skipped": 1, "reported": 4},
            {"kind": "keep", "taskTitle": "Notes", "domain": "learning", "done": 4, "partial": 0, "skipped": 0, "reported": 4},
            {"kind": "mixed", "taskTitle": "Walk", "domain": "life", "done": 2, "partial": 1, "skipped": 0, "reported": 3},
        ]
        owned = (untimed("Guide", "project", 60), untimed("Notes", "learning", 45), untimed("Walk", "life", 30))
        easiest = plan(build_recorded_variants(owned, earliest="08:00", findings=findings,
                                               preferences={"easiest": 1}), "easiest")
        self.assertEqual(starts(easiest), {"Notes": "09:00", "Walk": "09:45", "Guide": "10:15"})
        # Guide's length is the user's own, so the "shorten" finding leaves it as it is.
        self.assertEqual(lengths(easiest)["Guide"], 60)

    def test_your_usual_rhythm_places_tasks_near_their_usual_times_and_only_that_plan_does(self):
        findings = [{"kind": "time", "taskTitle": "Notes", "domain": "learning", "preferredStart": "10:00"}]
        owned = (untimed("Notes", "learning", 45), untimed("Report", "work", 60), untimed("Walk", "life", 30))
        variants = build_recorded_variants(owned, earliest="08:00", findings=findings, preferences={"rhythm": 1})
        rhythm = plan(variants, "rhythm")
        self.assertEqual(starts(rhythm), {"Report": "09:00", "Notes": "10:00", "Walk": "10:45"})
        self.assertNotEqual(starts(plan(variants, "balanced"))["Notes"], "10:00")
        self.assertIn("“Notes” at 10:00", rhythm["rationale"])

    def test_a_usual_time_that_is_taken_or_too_late_falls_back_to_free_time(self):
        owned = [fixed("10:30", "Meeting", "work", 60), untimed("Notes", "learning", 45),
                 untimed("Walk", "life", 30), untimed("Read", "learning", 30)]
        prefer = {"rhythm": 1}
        taken = [{"kind": "time", "taskTitle": "Notes", "domain": "learning", "preferredStart": "10:00"}]
        late = [{"kind": "time", "taskTitle": "Notes", "domain": "learning", "preferredStart": "21:45"}]
        # From 10:00 the next free 45 minutes come after the meeting and lunch, and the plan says so.
        rhythm = plan(build_recorded_variants(owned, earliest="07:00", findings=taken, preferences=prefer), "rhythm")
        self.assertEqual(starts(rhythm)["Notes"], "13:00")
        self.assertIn("“Notes” at 13:00, the first free time after 10:00", rhythm["rationale"])
        # Nothing is free after 21:45, so a plan placing Notes earlier wouldn't follow the usual time.
        self.assertNotIn("rhythm", slugs(build_recorded_variants(owned, earliest="07:00", findings=late,
                                                                  preferences=prefer)))

    def test_breathing_room_spreads_a_light_day_with_equal_gaps(self):
        owned = (untimed("Report", "work", 30), untimed("Walk", "life", 30), untimed("Read", "learning", 30))
        variants = build_recorded_variants(owned, earliest="08:00")
        self.assertEqual(slugs(variants), ["balanced", "focused", "spacious"])
        # An hour after Walk would be 12:00, which lunch keeps, so Read waits until 13:00.
        self.assertEqual(starts(plan(variants, "spacious")), {"Report": "09:00", "Walk": "10:30", "Read": "13:00"})

    def test_the_plans_you_set_most_often_are_offered_first(self):
        owned = (untimed("Report", "work", 30), untimed("Walk", "life", 30), untimed("Read", "learning", 30))
        variants = build_recorded_variants(owned, earliest="08:00", preferences={"spacious": 3, "gentle": 1})
        self.assertEqual(slugs(variants), ["balanced", "spacious", "gentle"])

    def test_plans_offered_together_differ_clearly(self):
        days = [
            (untimed("Email", "work", 15), untimed("Water plants", "life", 15), untimed("Call mum", "life", 15)),
            (untimed("Guide", "project", 60), untimed("Walk", "life", 30)),
            (untimed("Report", "work", 30), untimed("Build", "project", 30), untimed("Walk", "life", 30)),
            (untimed("Build", "project", 90), untimed("Study", "learning", 60), untimed("Email", "work", 15),
             untimed("Water plants", "life", 15), untimed("Call mum", "life", 20)),
        ]
        for owned in days:
            variants = build_recorded_variants(owned, earliest="09:00")
            for index, first in enumerate(variants):
                for second in variants[index + 1:]:
                    self.assertTrue(clearly_different(first, second), (first["slug"], second["slug"]))

    def test_a_plan_that_would_repeat_another_is_left_out_and_a_merely_different_one_fills_in(self):
        # From 13:00 the longest free stretch is the first one, so Deep focus would place the tasks
        # exactly as Balanced does; Lighter day can start no later and only adds a break, so it
        # comes after Breathing room, which differs clearly.
        owned = (untimed("Report", "work", 30), untimed("Build", "project", 30))
        self.assertEqual(slugs(build_recorded_variants(owned, earliest="13:00")), ["balanced", "spacious", "gentle"])

    def test_three_plans_whenever_three_different_ones_can_be_made(self):
        days = [
            (fixed("09:00", "French", "learning", 60), untimed("Housework", "life", 60)),
            (untimed("Guide", "project", 60), untimed("Walk", "life", 30)),
            (untimed("Report", "work", 30), untimed("Walk", "life", 30), untimed("Read", "learning", 30)),
            (fixed("10:00", "Dentist", "life", 60), untimed("Study", "learning", 60), untimed("Laundry", "life", 30)),
        ]
        for owned in days:
            variants = build_recorded_variants(owned, earliest="08:00")
            self.assertEqual(len(variants), 3, [item.title for item in owned])
            self.assertEqual(len({tuple(sorted(starts(variant).items())) for variant in variants}), 3)

    def test_lighter_day_starts_later_still_when_ten_oclock_would_repeat_another_plan(self):
        # Balanced takes 09:00 and Deep focus 13:00; from 10:00 Lighter day would also land at 13:00.
        owned = (fixed("10:00", "Stand-up", "work", 60), untimed("Write tests", "project", 60))
        variants = build_recorded_variants(owned, earliest="08:00")
        self.assertEqual([(variant["slug"], starts(variant)["Write tests"]) for variant in variants],
                         [("balanced", "09:00"), ("focused", "13:00"), ("gentle", "14:00")])
        self.assertIn("Places nothing before 14:00", plan(variants, "gentle")["rationale"])

    def test_lighter_day_and_breathing_room_leave_their_gap_after_fixed_tasks_too(self):
        owned = (fixed("09:00", "French", "learning", 60), untimed("Housework", "life", 60))
        variants = build_recorded_variants(owned, earliest="08:00")
        self.assertEqual(starts(plan(variants, "balanced"))["Housework"], "10:00")
        self.assertEqual(starts(plan(variants, "gentle"))["Housework"], "10:15")
        self.assertEqual(starts(plan(variants, "spacious"))["Housework"], "11:00")

    def test_the_ai_reads_every_plan_it_can_choose_from_with_the_days_facts(self):
        seen = []
        owned = (untimed("Build", "project", 90), untimed("Study", "learning", 60), untimed("Email", "work", 15),
                 untimed("Water plants", "life", 15), untimed("Call mum", "life", 20, estimated=True))
        build_recorded_variants(owned, earliest="08:00", preferences={"spacious": 2},
                                choose=lambda context: seen.append(context))
        context = seen[0]
        kinds = [candidate["kind"] for candidate in context["candidates"]]
        self.assertTrue({"focused", "gentle", "quickwins", "spacious"} <= set(kinds), kinds)
        self.assertNotIn("balanced", kinds)
        quick = next(candidate for candidate in context["candidates"] if candidate["kind"] == "quickwins")
        self.assertEqual((quick["name"], quick["firstTask"], quick["startsAt"]), ("Quick wins first", "Email", "09:00"))
        self.assertIn("“Email”", quick["does"])
        self.assertEqual(context["day"]["start"], "09:00")
        self.assertEqual(context["day"]["meals"], ["Lunch 12:00–13:00", "Dinner 18:00–19:00"])
        self.assertEqual(context["day"]["planPreferences"], {"spacious": 2})
        call = next(task for task in context["day"]["tasks"] if task["title"] == "Call mum")
        self.assertEqual((call["minutes"], call["length"], call["start"]), (20, "estimated", None))

    def test_the_ai_picks_the_two_plans_beside_balanced_and_its_reason_is_shown(self):
        owned = (untimed("Build", "project", 90), untimed("Study", "learning", 60), untimed("Email", "work", 15),
                 untimed("Water plants", "life", 15), untimed("Call mum", "life", 20))
        picks = [{"kind": "spacious", "why": "Your day is light, so spread it out.", "whyZh": "今天任务不多，分散安排。"},
                 {"kind": "quickwins", "why": "Three short tasks get you going.", "whyZh": "三个短任务帮你起步。"}]
        variants = build_recorded_variants(owned, earliest="08:00", choose=lambda context: picks)
        self.assertEqual(slugs(variants), ["balanced", "spacious", "quickwins"])
        spacious = plan(variants, "spacious")
        self.assertEqual(spacious["notes"][0], {"key": "planWhyAgent", "text": "Your day is light, so spread it out.",
                                                "values": {"en": "Your day is light, so spread it out.",
                                                           "zh": "今天任务不多，分散安排。"}})
        self.assertTrue(spacious["rationale"].startswith("Your day is light, so spread it out. Leaves "))

    def test_an_unusable_ai_choice_falls_back_to_the_planners_own_ranking(self):
        owned = (untimed("Report", "work", 30), untimed("Walk", "life", 30), untimed("Read", "learning", 30))
        own = slugs(build_recorded_variants(owned, earliest="08:00"))
        for answer in (None, [], [{"kind": "bogus", "why": "x", "whyZh": "x"}], [{"kind": "rhythm", "why": "x", "whyZh": "x"}]):
            self.assertEqual(slugs(build_recorded_variants(owned, earliest="08:00", choose=lambda context: answer)), own)
        # One usable pick is kept, and the planner's own ranking fills the other place.
        mixed = build_recorded_variants(owned, earliest="08:00", choose=lambda context: [
            {"kind": "gentle", "why": "Ease in.", "whyZh": "轻松开始。"}, {"kind": "bogus", "why": "x", "whyZh": "x"}])
        self.assertEqual(slugs(mixed), ["balanced", "gentle", own[1]])
        self.assertTrue(plan(mixed, own[1])["rationale"].startswith("Suggested because "))

    def test_a_plan_the_area_agents_voted_for_says_who_voted(self):
        owned = (untimed("Report", "work", 30), untimed("Walk", "life", 30), untimed("Read", "learning", 30))
        variants = build_recorded_variants(owned, earliest="08:00", choose=lambda context: [
            {"kind": "spacious", "agents": ["life", "learning"], "names": "Life and Learning"}])
        note = plan(variants, "spacious")["notes"][0]
        self.assertEqual((note["key"], note["values"]["agents"]), ("planWhyVotes", ["life", "learning"]))
        self.assertEqual(note["text"], "The area agents' votes put it here: Life and Learning.")

    def test_on_a_low_energy_day_lighter_day_leads_whatever_the_ai_picks(self):
        owned = (untimed("Report", "work", 30), untimed("Walk", "life", 30), untimed("Read", "learning", 30))
        picks = [{"kind": "focused", "why": "Keep work together.", "whyZh": "集中工作。"},
                 {"kind": "spacious", "why": "Spread out.", "whyZh": "分散。"}]
        variants = build_recorded_variants(owned, earliest="08:00", choose=lambda context: picks,
                                           findings=[{"kind": "area-life", "domain": "life", "lighter": True}])
        self.assertEqual(slugs(variants), ["gentle", "balanced", "focused"])

    def test_every_suggested_plan_says_why_and_what_sets_it_apart(self):
        owned = (untimed("Build", "project", 90), untimed("Study", "learning", 60), untimed("Email", "work", 15),
                 untimed("Water plants", "life", 15), untimed("Call mum", "life", 20))
        variants = build_recorded_variants(owned, earliest="08:00", preferences={"quickwins": 1})
        for variant in variants:
            keys = [note["key"] for note in variant["notes"]]
            self.assertEqual(variant["rationale"], " ".join(note["text"] for note in variant["notes"]))
            self.assertTrue(any(key.startswith("planDoes") for key in keys), variant["slug"])
            if variant["slug"] != "balanced":
                self.assertTrue(keys[0].startswith("planWhy"), variant["slug"])
                self.assertTrue(variant["rationale"].startswith("Suggested because "), variant["rationale"])
        apart = [next(note["text"] for note in variant["notes"] if note["key"].startswith("planDoes"))
                 for variant in variants]
        self.assertEqual(len(set(apart)), len(apart))


def note(key, text="", **values):
    """A plan's sentence as a proposed plan stores it; its text matters only where it stays as it was."""
    return {"key": key, "values": values, "text": text}


class NotesWithoutTests(unittest.TestCase):
    """A proposed plan's sentences, rewritten from the tasks it has left once one of them is deleted."""

    LEFT = ({"title": "Walk", "start_time": "09:00", "duration_minutes": 30, "domain": "life", "constraint_kind": "flexible"},
            {"title": "Draft", "start_time": "13:00", "duration_minutes": 90, "domain": "work", "constraint_kind": "flexible"},
            {"title": "Notes", "start_time": "15:30", "duration_minutes": 30, "domain": "learning", "constraint_kind": "flexible"})
    READ = {"title": "Read", "domain": "learning", "duration_minutes": 60}

    def rewritten(self, *notes, gone=READ):
        rewritten = notes_without(list(notes), gone, self.LEFT)
        self.assertNotIn(gone["title"], " ".join(item["text"] for item in rewritten))
        return [(item["key"], item["values"]) for item in rewritten]

    def test_a_task_list_drops_the_task_and_its_stretch_follows_the_tasks_left(self):
        self.assertEqual(
            self.rewritten(note("planWhyVotes", "The area agents' votes put it here: Learning.", names="Learning",
                                agents=["learning"]),
                           note("planDoesFocus", tasks=["Draft", "Read", "Notes"], start="13:00", end="16:00")),
            [("planWhyVotes", {"names": "Learning", "agents": ["learning"]}),
             ("planDoesFocus", {"tasks": ["Draft", "Notes"], "start": "13:00", "end": "16:00"})])
        self.assertEqual(self.rewritten(note("planDoesFocus", tasks=["Draft", "Read"], start="13:00", end="15:30")),
                         [("planDoesFocusOne", {"tasks": ["Draft"], "start": "13:00"})])

    def test_a_sentence_about_the_task_alone_goes_and_one_about_the_first_task_takes_the_next(self):
        self.assertEqual(self.rewritten(note("planDoesEasiest", usual="Read", often="Draft"),
                                        note("planDoesRhythm", title="Read", time="09:00"),
                                        note("planWhyAgent", en="Read comes first.", zh="先读。"),
                                        note("planDoesGentle", start="09:00", first="Read")),
                         [("planDoesGentle", {"start": "09:00", "first": "Walk"})])

    def test_counts_and_times_follow_the_tasks_left(self):
        self.assertEqual(self.rewritten(note("planWhyFocus", count=3), note("planWhyQuick", count=2),
                                        note("planDoesEarly", end="17:30"), note("planDoesBalanced", start="08:00")),
                         [("planWhyFocus", {"count": 2}), ("planWhyQuick", {"count": 2}),
                          ("planDoesEarly", {"end": "16:00"}), ("planDoesBalanced", {"start": "09:00"})])
        quick = {"title": "Read", "domain": "learning", "duration_minutes": 30}
        self.assertEqual(self.rewritten(note("planWhyQuick", count=2), note("planWhyFocus", count=2), gone=quick), [])


if __name__ == "__main__":
    unittest.main()
