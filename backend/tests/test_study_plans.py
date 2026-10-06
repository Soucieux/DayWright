import unittest

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.planner import PlanItem, StudyTopic, build_recorded_variants

LOW = [{"kind": "area-life", "lighter": True}]
HIGH = [{"kind": "area-life", "focused": True}]


def study(title, effort, goal="g-angular", position=0, count=3, minutes=60):
    """A study task for a topic of a goal."""
    return PlanItem(None, title, "", "learning", minutes, item_id=title,
                    study=StudyTopic(goal=goal, position=position, count=count, goal_title="Angular", effort=effort,
                                     hands_on=effort == "deep", briefing=f"About {title}.", subheadings=("One", "Two")))


MEETING = PlanItem("10:30", "Stand-up", "", "work", 30, "fixed", item_id="meeting")


def balanced(items, findings=(), earliest="09:00", choose=None):
    plans = build_recorded_variants(items, findings=findings, earliest=earliest, choose=choose)
    plan = next(plan for plan in plans if plan["slug"] == "balanced")
    return {item.title: item.start for item in plan["items"] if item.item_id}


class StudyPlacementTests(unittest.TestCase):
    def test_a_deep_topic_takes_the_earlier_hours_and_a_light_one_the_time_left(self):
        starts = balanced([MEETING, study("Signals basics", "light", goal="g-a", minutes=30),
                           study("Change detection", "deep", goal="g-b")])

        self.assertEqual((starts["Change detection"], starts["Signals basics"]), ("09:00", "10:00"))

    def test_at_low_energy_the_light_topic_comes_first(self):
        starts = balanced([MEETING, study("Signals basics", "light", goal="g-a", minutes=30),
                           study("Change detection", "deep", goal="g-b")], findings=LOW)

        self.assertEqual((starts["Signals basics"], starts["Change detection"]), ("09:00", "09:30"))

    def test_at_high_energy_a_deep_topic_goes_first_of_all(self):
        work = PlanItem(None, "Report", "", "work", 60, item_id="report")
        starts = balanced([MEETING, work, study("Change detection", "deep")], findings=HIGH)

        self.assertEqual((starts["Change detection"], starts["Report"]), ("09:00", "11:00"))
        self.assertEqual(balanced([MEETING, work, study("Change detection", "deep")])["Report"], "09:00",
                         "without high energy, work comes first as usual")

    def test_a_goals_topics_keep_their_order_whatever_their_effort(self):
        starts = balanced([MEETING, study("Interceptors", "light", position=1, minutes=30),
                           study("Setup", "light", position=0, minutes=30), study("Errors", "deep", position=2)])

        self.assertLess(starts["Setup"], starts["Interceptors"])
        self.assertLess(starts["Interceptors"], starts["Errors"])


class StudyFactsTests(unittest.TestCase):
    def test_the_model_reads_each_study_tasks_profile_and_its_place_in_its_goal(self):
        seen = {}

        def choose(context):
            seen.update(context)
            return None

        build_recorded_variants([MEETING, study("Change detection", "deep", position=2, count=8),
                                 PlanItem(None, "Report", "", "work", 60, item_id="report"),
                                 PlanItem(None, "Laundry", "", "life", 30, item_id="laundry")], earliest="09:00", choose=choose)

        task = next(task for task in seen["day"]["tasks"] if task["title"] == "Change detection")
        self.assertEqual(task["study"], {"place": "3 of 8 in Angular", "effort": "deep", "handsOn": True,
                                         "briefing": "About Change detection.", "subheadings": ["One", "Two"]})
        self.assertNotIn("study", next(task for task in seen["day"]["tasks"] if task["title"] == "Report"))


if __name__ == "__main__":
    unittest.main()
