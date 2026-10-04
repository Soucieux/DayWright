import unittest

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.conversation import (_asks_past_change, _asks_removal, _context, _requested_changes, infer_mode,
                                      recent_span)


class PastTaskRequestTests(unittest.TestCase):
    """What Ava reads from a request to change a past task, its name already taken out."""

    task = {"id": "item_1", "title": "Review", "detail": "", "domain": "work", "goalId": "goal_w", "date": "2026-10-01",
            "start_time": "09:00", "duration_minutes": 30, "completion_status": "planned", "durationSource": "user",
            "constraint_kind": "fixed", "repeatKind": "none"}
    goals = [{"id": "goal_w", "title": "Launch", "domain": "work"}, {"id": "goal_l", "title": "Essay", "domain": "learning"}]

    def changes(self, message):
        return _requested_changes(message.replace("Review", " ", 1), self.task, self.goals, "2026-10-03")

    def test_each_field_a_past_task_has_can_be_asked_for_in_the_users_words(self):
        cases = {
            "Move Review to 10:30": {"startTime": "10:30"},
            "Review took 45 minutes": {"durationMinutes": 45},
            "Mark Review as done": {"status": "done"},
            "Review was partly done": {"status": "partial"},
            "I skipped Review": {"status": "skipped"},
            "Rename Review to “Read notes”": {"title": "Read notes"},
            "Change Review's detail to bring the slides": {"detail": "bring the slides"},
            "Link Review to the Essay goal": {"goalId": "goal_l"},
            "Unlink Review from its goal": {"goalId": None},
            "Move Review to 2 Oct": {"date": "2026-10-02"},
            "把 Review 移到10月2日下午3点": {"date": "2026-10-02", "startTime": "15:00"},
            "Move Review to the next day": {"date": "2026-10-02"},
        }
        for message, expected in cases.items():
            self.assertEqual(self.changes(message), expected, message)

    def test_a_new_area_leaves_a_goal_in_the_old_one(self):
        self.assertEqual(self.changes("Move Review to the Life area"), {"domain": "life", "goalId": None})

    def test_a_task_moved_after_today_goes_back_to_planned(self):
        done = {**self.task, "completion_status": "done"}
        self.assertEqual(_requested_changes("Move   to 2026-10-05", done, self.goals, "2026-10-03"),
                         {"date": "2026-10-05", "status": "planned"})

    def test_only_what_would_change_is_asked_for(self):
        self.assertEqual(self.changes("Move Review to 09:00"), {})

    def test_a_removal_is_asked_for_outright_or_politely_but_not_in_a_question(self):
        for message in ("Remove  ", "Can you delete  ?", "删除  ", "能删除  吗？"):
            self.assertTrue(_asks_removal(message), message)
        for message in ("Why did I remove  ?", "Remove   from its goal"):
            self.assertFalse(_asks_removal(message), message)

    def test_renaming_or_relinking_a_past_task_is_a_change(self):
        for message in ("Rename Review to Read", "Unlink Review from its goal", "Remove Review", "删除 Review"):
            self.assertTrue(_asks_past_change(message), message)
        self.assertFalse(_asks_past_change("What is Review's goal?"))



class InferModeTests(unittest.TestCase):
    def test_a_question_is_asked(self):
        for message in ("What should I do next?", "Why is Balanced set?", "How did this week go?", "今天先做什么？"):
            self.assertEqual(infer_mode(message), "ask", message)

    def test_a_change_is_an_adjustment(self):
        for message in ("Move Review to 10:30", "make walk 45 minutes", "Switch to Deep focus", "shorten Review",
                        "Use the lighter day plan", "把 Review 改到下午3点", "换成轻松一天", "Review 推迟 30分钟"):
            self.assertEqual(infer_mode(message), "adjust", message)

    def test_saying_what_happened_is_a_report(self):
        for message in ("I finished Review", "I skipped the walk", "Done with Review", "Review 完成了", "我跳过了散步",
                        "Review was partly done", "Mark Review as done", "Mark Review as not reported", "Review 标记为完成"):
            self.assertEqual(infer_mode(message), "report", message)

    def test_a_question_about_a_change_is_still_a_question(self):
        self.assertEqual(infer_mode("Why did you move Review?"), "ask")
        self.assertEqual(infer_mode("Should I switch to Deep focus?"), "ask")

    def test_a_polite_request_for_a_change_is_an_adjustment(self):
        for message in ("Can you move Review to 3pm?", "Could you shorten Review?", "Can you make Review 45 minutes?",
                        "Please move Review to 4pm", "能把 Review 移到下午3点吗？", "请把散步推迟半小时",
                        "Replace today's plan with a better one", "把今天的计划换成更合适的方案"):
            self.assertEqual(infer_mode(message), "adjust", message)

    def test_scheduling_words_ask_for_a_change(self):
        for message in ("Schedule Review at 3pm", "把 Review 安排到3点", "Review 挪到3点"):
            self.assertEqual(infer_mode(message), "adjust", message)

    def test_a_change_named_with_what_happened_is_still_a_change(self):
        for message in ("I missed Review, move it to 5pm", "把没做完的任务移到明天"):
            self.assertEqual(infer_mode(message), "adjust", message)

    def test_asking_to_be_shown_or_told_is_a_question(self):
        for message in ("Show me what I did yesterday", "Tell me what I finished", "Show me the tasks I set for Friday",
                        "Tell me how to make a plan", "Can you explain why Balanced is set?", "今天的安排怎么样？",
                        "Which other plan would suit today better?"):
            self.assertEqual(infer_mode(message), "ask", message)

    def test_time_spent_and_reports_without_i_are_reports(self):
        for message in ("I spent 30 minutes on Review", "我花了30分钟做 Review", "Finished Review", "Skipped the walk",
                        "I didn't finish Review"):
            self.assertEqual(infer_mode(message), "report", message)


def note(key, text):
    return {"key": key, "values": {}, "text": text}


DAY = {
    "date": "2026-10-02", "selectedVariantId": "v1", "confirmedVariantId": "v1", "balance": {"learning": 30},
    "hardConstraints": ["Stand-up at 10:00 (fixed)"],
    "entries": [{"start_time": "09:00", "title": "Review", "domain": "learning", "completion_status": "done",
                 "duration_minutes": 30}],
    "dayItems": [
        {"start_time": "09:00", "title": "Review", "domain": "learning", "completion_status": "done",
         "duration_minutes": 30, "durationSource": "user", "estimatedBy": None, "originKind": "user",
         "originDetail": "", "acceptance": "accepted"},
        {"start_time": None, "title": "Walk", "domain": "life", "completion_status": "planned",
         "duration_minutes": 45, "durationSource": "estimate", "estimatedBy": "life", "originKind": "user",
         "originDetail": "", "acceptance": "accepted"},
    ],
    "variants": [
        {"id": "v1", "name": "Balanced", "slug": "balanced", "rationale": "Takes the areas in turn.",
         "notes": [note("planDoesBalanced", "Takes the areas in turn by priority from 09:00.")],
         "meals": [{"title": "Lunch", "start_time": "12:00", "duration_minutes": 60}]},
        {"id": "v2", "name": "Deep focus", "slug": "focused", "rationale": "",
         "notes": [note("planWhyAgent", "Two work tasks fit one block."),
                   note("planDoesFocus", "Keeps “Review” back to back from 13:00.")], "meals": []},
    ],
    "planRoute": [{"agentKey": "life", "phase": "assessment", "summary": "",
                   "findings": [{"kind": "area-life", "domain": "life", "energy": 2, "lighter": True},
                                {"kind": "keep", "taskTitle": "Review", "domain": "learning", "done": 3, "reported": 4}]}],
    "goals": [{"title": "Learn French", "domain": "learning", "status": "active", "itemCount": 3, "doneCount": 1}],
}


class RecentSpanTests(unittest.TestCase):
    def test_the_week_ends_the_day_before_a_past_day_or_today(self):
        self.assertEqual(recent_span("2026-09-20", "2026-10-02"), ("2026-09-13", "2026-09-19"))
        self.assertEqual(recent_span("2026-10-02", "2026-10-02"), ("2026-09-25", "2026-10-01"))

    def test_for_a_future_day_the_week_ends_today(self):
        self.assertEqual(recent_span("2026-10-20", "2026-10-02"), ("2026-09-26", "2026-10-02"))


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.context = _context(DAY, {"learning": {"scheduled": 4, "done": 3, "partial": 1, "skipped": 0}},
                                ("2026-09-25", "2026-10-01"))

    def test_a_long_day_is_capped_so_the_prompt_fits_the_model(self):
        long_title = "A very long task title " * 10
        item = {**DAY["dayItems"][0], "title": long_title}
        entry = {**DAY["entries"][0], "title": long_title}
        crowded = {**DAY, "dayItems": [item] * 60, "entries": [entry] * 60,
                   "goals": [{**DAY["goals"][0], "title": long_title}] * 60}
        self.assertLess(len(_context(crowded)), 8000)

    def test_the_context_frames_the_day_and_its_meals(self):
        self.assertIn("between 09:00 and 22:00", self.context)
        self.assertIn("lunch 12:00–13:00 and dinner 18:00–19:00", self.context)

    def test_the_context_states_the_days_own_meal_times(self):
        moved = {**DAY, "meals": [{"title": "Lunch", "start_time": "12:30", "duration_minutes": 45},
                                  {"title": "Dinner", "start_time": "19:00", "duration_minutes": 60}]}
        self.assertIn("lunch 12:30–13:15 and dinner 19:00–20:00 stay free", _context(moved))

    def test_each_task_carries_its_length_and_whose_it_is(self):
        self.assertIn("“Review” at 09:00, learning, 30 min (your length), done", self.context)
        self.assertIn("“Walk” with no start time, life, about 45 min (estimated by the Life agent), planned", self.context)

    def test_the_plans_say_why_and_what_sets_each_apart_and_which_is_set(self):
        self.assertIn("Set plan: Balanced", self.context)
        self.assertIn("Deep focus: Two work tasks fit one block. Keeps “Review” back to back from 13:00.", self.context)

    def test_goals_findings_and_the_last_week_are_included(self):
        self.assertIn("“Learn French” (learning, active, 1 of 3 tasks done)", self.context)
        self.assertIn("life: energy 2/5, a lighter day advised", self.context)
        self.assertIn("“Review”: done 3 of 4 times", self.context)
        self.assertIn("Last 7 days (2026-09-25 to 2026-10-01): learning 3 done, 1 partly done, 0 skipped of 4",
                      self.context)


if __name__ == "__main__":
    unittest.main()
