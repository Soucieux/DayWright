import unittest

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.agents import (LEARNING, LIFE, PROJECT, WORK, AgentOrchestrator, AgentRun, DomainAgent, SummaryAgent,
                                meal_clashes, named_tasks)
from backend.app.meals import Meal


def fixed_at(title, start, minutes, source="user"):
    """A task fixed at a start, with a length the user gave ("user") or an agent estimated ("estimate")."""
    return {**task(title, start, kind="fixed"), "duration_minutes": minutes, "durationSource": source}


def placed(title, start, minutes):
    """An entry of the set plan placing a task the user gave no start."""
    return {"id": f"entry-{title}", "title": title, "start_time": start, "duration_minutes": minutes,
            "source_item_id": title, "removed": False}


class MealClashTests(unittest.TestCase):
    """What stands in the way of a new meal time, checked before anything changes."""

    LUNCH = Meal("Lunch", "12:30", 60)

    def test_a_task_whose_length_the_user_set_inside_the_new_meal_is_named_and_nothing_proposed(self):
        found = meal_clashes(self.LUNCH, {"2026-10-04": {"dayItems": [fixed_at("Call", "13:00", 30)], "entries": []}})
        self.assertEqual(found["refused"], [{"date": "2026-10-04", "title": "Call", "start": "13:00", "minutes": 30,
                                             "reason": "yours"}])

    def test_an_estimate_the_meal_takes_within_its_first_30_minutes_is_named(self):
        found = meal_clashes(self.LUNCH, {"2026-10-04": {"dayItems": [fixed_at("Read", "12:15", 90, "estimate")],
                                                         "entries": []}})
        self.assertEqual([(clash["title"], clash["reason"]) for clash in found["refused"]], [("Read", "estimate")])
        edge = meal_clashes(self.LUNCH, {"2026-10-04": {"dayItems": [fixed_at("Read", "12:00", 90, "estimate")],
                                                        "entries": []}})
        self.assertEqual((edge["refused"], edge["planChanges"]), ([], True))

    def test_an_estimate_the_meal_takes_only_after_its_first_30_minutes_changes_the_plan(self):
        found = meal_clashes(self.LUNCH, {"2026-10-04": {"dayItems": [fixed_at("Read", "11:45", 90, "estimate")],
                                                         "entries": []}})
        self.assertEqual((found["refused"], found["planChanges"]), ([], True))

    def test_a_paused_goals_fixed_task_inside_the_new_meal_is_named_too(self):
        # Its goal may resume, and the task would then sit inside the meal.
        resting = {**fixed_at("Openings", "13:00", 30), "goalStatus": "paused"}
        found = meal_clashes(self.LUNCH, {"2026-10-04": {"dayItems": [resting], "entries": []}})
        self.assertEqual([(clash["title"], clash["reason"]) for clash in found["refused"]], [("Openings", "yours")])

    def test_a_meal_nothing_stands_in_the_way_of_changes_nothing_else(self):
        found = meal_clashes(self.LUNCH, {"2026-10-04": {"dayItems": [fixed_at("Call", "11:30", 60)], "entries": []}})
        self.assertEqual((found["refused"], found["planChanges"], found["planOverlapMinutes"]), ([], False, 0))

    def test_the_set_plans_placed_tasks_in_the_way_change_the_plan_by_their_overlap(self):
        day = {"dayItems": [task("Draft", None)], "entries": [placed("Draft", "12:15", 45), placed("Notes", "13:15", 30)]}
        found = meal_clashes(self.LUNCH, {"2026-10-04": day})
        self.assertEqual((found["refused"], found["planChanges"], found["planOverlapMinutes"]), ([], True, 30 + 15))

    def test_a_standing_change_names_every_clash_on_every_day_it_checks(self):
        found = meal_clashes(self.LUNCH, {
            "2026-10-04": {"dayItems": [fixed_at("Call", "13:00", 30)], "entries": []},
            "2026-10-05": {"dayItems": [fixed_at("Review", "12:00", 45)], "entries": []},
            "2026-10-06": {"dayItems": [fixed_at("Gym", "17:00", 60)], "entries": []},
        })
        self.assertEqual([(clash["date"], clash["title"]) for clash in found["refused"]],
                         [("2026-10-04", "Call"), ("2026-10-05", "Review")])
        self.assertEqual(found["checked"], ["2026-10-04", "2026-10-05", "2026-10-06"])


def task(title, start, domain="work", kind="flexible"):
    return {"id": title, "title": title, "detail": "", "domain": domain, "start_time": start, "duration_minutes": 45,
            "constraint_kind": kind, "completion_status": "planned", "acceptance": "accepted",
            "durationSource": "user"}


DAY = {"date": "2026-10-02", "entries": [], "dayItems": [task("Client meeting", "10:00", kind="fixed"), task("Draft", None)]}
NO_HISTORY = {"profiles": {}, "memory": [], "areaEvidence": {}}


class FakeGateway:
    def reply(self, message, context, system_prompt=None, max_tokens=None):
        return "A reply.", "rules"


class SummaryTests(unittest.TestCase):
    def test_summary_sums_up_what_the_area_agents_found(self):
        runs = [AgentRun(LEARNING, "assessment", "", ({"kind": "shorten", "taskTitle": "Review", "domain": "learning"},)),
                AgentRun(LIFE, "assessment", "", ({"kind": "keep", "taskTitle": "Walk", "domain": "life"},
                                                  {"kind": "keep", "taskTitle": "Gym", "domain": "life"}))]
        run = SummaryAgent().assess(runs)
        self.assertEqual((run.spec.key, run.phase), ("summary", "summary"))
        self.assertEqual(run.summary, "Summed up Learning and Life: 3 tasks reviewed against all your records, "
                                      "1 to shorten, 2 working at their length.")

    def test_with_nothing_to_review_summary_says_so(self):
        run = SummaryAgent().assess([AgentRun(LEARNING, "assessment", "", ())])
        self.assertEqual(run.summary, "Summed up Learning: no tasks to review for this day.")


class AreaAgentTests(unittest.TestCase):
    def test_in_a_reply_an_area_agent_reviews_its_tasks_and_names_them_without_stock_advice(self):
        run = DomainAgent(WORK).assess(DAY, "ask", None, NO_HISTORY, describe=True)
        self.assertTrue(run.summary.startswith("Reviewed 2 work tasks against all your records"))
        self.assertIn("Client meeting at 10:00 (fixed)", run.summary)
        self.assertIn("Draft (no start time yet)", run.summary)
        self.assertNotIn("Keep fixed meetings where they are", run.summary)
        self.assertEqual(sum("taskTitle" in finding for finding in run.findings), 2)


    def test_without_a_set_plan_a_reply_names_the_users_own_tasks_not_a_draft_plan(self):
        draft = {**task("Client meeting", "11:30"), "duration_minutes": 30}
        pending = {**task("Maybe email", None), "acceptance": "pending"}
        day = {**DAY, "confirmedVariantId": None, "entries": [draft], "dayItems": [*DAY["dayItems"], pending]}
        run = DomainAgent(WORK).assess(day, "ask", None, NO_HISTORY, describe=True)
        self.assertIn("Client meeting at 10:00 (fixed), Draft (no start time yet).", run.summary)
        self.assertNotIn("11:30", run.summary)
        self.assertNotIn("Maybe email", run.summary)

    def test_with_a_set_plan_a_reply_names_the_tasks_where_the_plan_puts_them(self):
        placed = {**task("Draft", "14:00"), "duration_minutes": 45}
        day = {**DAY, "confirmedVariantId": "v1", "entries": [placed]}
        run = DomainAgent(WORK).assess(day, "ask", None, NO_HISTORY, describe=True)
        self.assertIn("Its tasks for the day, 45m: Draft at 14:00.", run.summary)


class OrchestratorTests(unittest.TestCase):
    def test_a_reply_runs_the_orchestrator_once_then_the_area_agents_then_summary(self):
        result = AgentOrchestrator().run("How should I prepare the client meeting?", "ask", DAY, FakeGateway(), "",
                                         history=NO_HISTORY)
        self.assertEqual([run.spec.key for run in result.runs], ["orchestrator", "work", "summary"])
        self.assertEqual(result.runs[0].summary, "Asked Work about this question, and answered as Ava from its review "
                                                 "and Summary's sum-up.")

    def test_only_asking_for_a_lighter_day_in_so_many_words_asks_for_one(self):
        orchestrator = AgentOrchestrator()
        for message, slug in (("Swap plans for the rest of the day", "focused"), ("Something more interesting", "focused"),
                              ("Make it gentler, I'm tired", "gentle")):
            result = orchestrator.run(message, "adjust", DAY, FakeGateway(), "", history=NO_HISTORY)
            self.assertEqual(result.recommended_variant_slug, slug, message)

    def test_without_history_the_area_agents_review_every_task_as_new(self):
        result = AgentOrchestrator().run("How is my work going?", "ask", DAY, FakeGateway(), "")
        self.assertEqual({finding["kind"] for finding in result.runs[1].findings}, {"new", "area-work"})

    def test_for_a_change_the_orchestrator_says_its_proposal_waits_for_confirm(self):
        result = AgentOrchestrator().run("I'm tired, make the day lighter", "adjust", DAY, FakeGateway(), "",
                                         history=NO_HISTORY)
        self.assertTrue(result.runs[0].summary.endswith("; a change it proposes waits for your Confirm."))
        self.assertEqual(result.recommended_variant_slug, "gentle")
        self.assertEqual(result.runs[-1].spec.key, "summary")


EVERY_AGENT = ["orchestrator", "learning", "life", "work", "project", "summary"]


class RouteTests(unittest.TestCase):
    def route(self, message, mode="ask", day=DAY):
        result = AgentOrchestrator().run(message, mode, day, FakeGateway(), "", history=NO_HISTORY)
        return [run.spec.key for run in result.runs]

    def test_a_question_about_nothing_in_your_day_is_answered_by_the_orchestrator_alone(self):
        result = AgentOrchestrator().run("What's the capital of France?", "ask", DAY, FakeGateway(), "",
                                         history=NO_HISTORY)
        self.assertEqual([run.spec.key for run in result.runs], ["orchestrator"])
        self.assertEqual(result.runs[0].summary, "Answered as Ava directly: the question isn't about your tasks, "
                                                 "plans or records, so no area agent was asked.")

    def test_the_suggested_questions_reach_every_area_agent_in_either_language(self):
        for message in ("What should I do next?", "How is my day looking?", "Which plan suits today?",
                        "接下来我该做什么？", "今天的安排怎么样？", "哪个方案最适合今天？"):
            self.assertEqual(self.route(message), EVERY_AGENT, message)

    def test_a_task_the_message_names_brings_in_its_own_area_agent(self):
        day = {**DAY, "dayItems": [*DAY["dayItems"], task("Inbox zero", None, "work"), task("晨跑", None, "life")]}
        self.assertEqual(self.route("Move Inbox zero to 15:00", "adjust", day), ["orchestrator", "work", "summary"])
        self.assertEqual(self.route("把晨跑移到早上7点", "adjust", day), ["orchestrator", "life", "summary"])

    def test_a_change_to_the_whole_day_asks_every_area_agent(self):
        self.assertEqual(self.route("Swap things around please", "adjust"), EVERY_AGENT)

    def test_the_longest_title_a_message_names_is_the_task_it_means(self):
        items = [task("Read", None, "learning"), task("Read chapter 4", None, "learning")]
        self.assertEqual([item["title"] for item in named_tasks("Move read chapter 4 to 10:00", items)],
                         ["Read chapter 4"])
        self.assertEqual(len(named_tasks("Move Walk to 17:00", [task("Walk", "08:00", "life"), task("Walk", None, "life")])),
                         2)

    def test_a_title_counts_only_as_a_whole_word_and_two_different_names_are_both_kept(self):
        items = [task("Read", None, "learning"), task("Review", None, "learning"), task("Run", None, "life")]
        self.assertEqual(named_tasks("Move my bread baking to 3pm", items), [])
        self.assertEqual(named_tasks("Move brunch to 13:00", items), [])
        self.assertEqual([item["title"] for item in named_tasks("Move Read to 15:00 after Review", items)],
                         ["Read", "Review"])

    def test_every_suggested_question_reaches_the_area_agents_in_either_language(self):
        questions = ("How do the plans differ?", "Why these plans?", "How did last week go?", "What's still unfinished?",
                     "Room for more this day?", "Which goal needs focus?", "Next step for my goals?",
                     "How are goals going?", "Notes on today's tasks?", "What should I study next?", "Notes on my goals?",
                     "这些方案有什么不同？", "为什么是这些方案？", "过去一周进展如何？", "还有哪些没完成？",
                     "这一天还能加点什么吗？", "哪个目标需要关注？", "目标的下一步是什么？", "我的目标进展如何？",
                     "关于今天任务的笔记？", "接下来我该学什么？", "关于目标的笔记？")
        for message in questions:
            self.assertNotEqual(self.route(message), ["orchestrator"], message)
        self.assertEqual(self.route("Which goal needs focus?"), EVERY_AGENT)

    def test_the_rest_of_the_day_is_not_a_question_for_life_alone(self):
        self.assertEqual(self.route("What's the plan for the rest of the day?"), EVERY_AGENT)

    def test_chinese_area_words_bring_in_their_area_agent(self):
        self.assertEqual(self.route("我最近的学习怎么样？"), ["orchestrator", "learning", "summary"])
        self.assertEqual(self.route("我的睡眠怎么样？"), ["orchestrator", "life", "summary"])


class DoubtTests(unittest.TestCase):
    READ = {**task("Read", None, "learning"), "duration_minutes": 45}

    def test_moving_a_task_far_from_when_it_is_usually_done_gives_its_agent_a_doubt(self):
        known = {("learning", "read"): {**STEADY, "usualStart": "08:30"}}
        self.assertEqual(AgentOrchestrator().check_change(self.READ, {"start": "21:00"}, known), [
            {"agent": "learning", "kind": "doubt-usual-time",
             "values": {"taskTitle": "Read", "usualStart": "08:30", "requested": "21:00", "done": 4}}])
        self.assertEqual(AgentOrchestrator().check_change(self.READ, {"start": "09:30"}, known), [])

    def test_a_length_at_which_the_task_was_mostly_left_partly_done_gives_a_doubt(self):
        known = {("learning", "read"): {**STEADY, "done": 1, "partial": 3, "partialMinutes": 30, "doneMinutes": 60}}
        self.assertEqual(AgentOrchestrator().check_change(self.READ, {"minutes": 30}, known), [
            {"agent": "learning", "kind": "doubt-too-short",
             "values": {"taskTitle": "Read", "requested": 30, "partial": 3, "partialMinutes": 30, "doneMinutes": 60}}])
        self.assertEqual(AgentOrchestrator().check_change(self.READ, {"minutes": 60}, known), [])

    def test_a_task_mostly_done_raises_no_doubt_about_its_length(self):
        known = {("learning", "read"): {**STEADY, "done": 20, "partial": 2, "partialMinutes": 30, "doneMinutes": 30}}
        self.assertEqual(AgentOrchestrator().check_change(self.READ, {"minutes": 30}, known), [])

    def test_an_agent_doubts_only_from_its_own_area(self):
        known = {("life", "read"): {**STEADY, "usualStart": "08:30"}}
        self.assertEqual(AgentOrchestrator().check_change(self.READ, {"start": "21:00"}, known), [])


ALL_KINDS = ("focused", "rhythm", "early", "quickwins", "easiest", "spacious", "gentle")


def choice(tasks, findings=(), kinds=ALL_KINDS):
    """The planner's choice context: the day's tasks and findings, and the plans the day allows."""
    return {"day": {"tasks": [{"title": title, "area": area, "minutes": minutes, "start": start, "length": "estimated"}
                              for title, area, minutes, start in tasks], "findings": list(findings)},
            "candidates": [{"kind": kind} for kind in kinds]}


class VoteTests(unittest.TestCase):
    def test_an_area_agent_votes_for_up_to_three_plans_for_its_own_tasks(self):
        votes = DomainAgent(LEARNING).vote(choice([("Read", "learning", 60, None), ("Notes", "learning", 45, None),
                                                   ("Walk", "life", 30, None)]), {})
        self.assertEqual(votes[0], {"kind": "focused", "reason": "focus"})
        self.assertLessEqual(len(votes), 3)

    def test_an_agent_with_no_task_to_place_does_not_vote(self):
        self.assertEqual(DomainAgent(WORK).vote(choice([("Stand-up", "work", 30, "10:00"), ("Read", "learning", 45, None)]), {}), [])

    def test_votes_follow_what_the_agent_knows_of_its_tasks(self):
        known = {("learning", "read"): {"usualStart": "08:30", "trend": "slipping", "done": 2, "partial": 2, "skipped": 1}}
        kinds = [vote["kind"] for vote in DomainAgent(LEARNING).vote(choice([("Read", "learning", 45, None)]), known)]
        self.assertIn("rhythm", kinds)
        self.assertIn("easiest", kinds)

    def test_life_votes_a_lighter_day_first_after_a_low_energy_check_in(self):
        low = {"kind": "area-life", "domain": "life", "lighter": True}
        votes = DomainAgent(LIFE).vote(choice([("Walk", "life", 30, None)], [low]), {})
        self.assertEqual(votes[0], {"kind": "gentle", "reason": "low-energy"})

    def test_an_agent_votes_only_for_plans_the_day_allows(self):
        votes = DomainAgent(LEARNING).vote(choice([("Read", "learning", 60, None), ("Notes", "learning", 45, None)],
                                                  kinds=("quickwins", "spacious")), {})
        self.assertTrue({vote["kind"] for vote in votes} <= {"quickwins", "spacious"})


def proposed_day(confirmed=None):
    """A day with untimed learning tasks and a walk, and three proposed plans, one maybe set."""
    items = [{**task("Read", None, "learning"), "duration_minutes": 60}, {**task("Notes", None, "learning")},
             {**task("Walk", None, "life"), "duration_minutes": 30}]
    variants = [{"id": slug, "slug": slug, "name": name} for slug, name in
                (("balanced", "Balanced"), ("focused", "Deep focus"), ("spacious", "Breathing room"))]
    return {"date": "2026-10-03", "dayItems": items, "variants": variants, "confirmedVariantId": confirmed, "planRoute": []}


class AlternativeTests(unittest.TestCase):
    def test_asked_for_another_plan_the_orchestrator_picks_the_one_the_agents_vote_for(self):
        variant, voters = AgentOrchestrator().recommend_variant("Give me a different plan", proposed_day("balanced"), {})
        self.assertEqual((variant["slug"], voters), ("focused", ["learning"]))

    def test_an_area_the_message_names_counts_double(self):
        variant, voters = AgentOrchestrator().recommend_variant("Something easier for my walk and rest",
                                                                proposed_day("balanced"), {})
        self.assertEqual((variant["slug"], voters), ("spacious", ["life"]))

    def test_the_set_plan_is_never_proposed_as_its_own_alternative(self):
        variant, _ = AgentOrchestrator().recommend_variant("Another plan please", proposed_day("focused"), {})
        self.assertEqual(variant["slug"], "spacious")

    def test_with_no_votes_there_is_no_recommendation(self):
        day = {**proposed_day("balanced"), "dayItems": []}
        self.assertEqual(AgentOrchestrator().recommend_variant("Another plan", day, {}), (None, []))


def todays(title, domain, minutes=45, status="planned", start=None):
    """One of today's tasks, flexible unless given a start, with an estimated length."""
    return {**task(title, start, domain, "fixed" if start else "flexible"), "duration_minutes": minutes,
            "completion_status": status, "durationSource": "estimate"}


def day_of(*items, confirmed=None, meals=None):
    """Today with these tasks, a set plan when `confirmed` names one, and its own `meals` when given."""
    return {"date": "2026-10-03", "dayItems": list(items), "confirmedVariantId": confirmed,
            **({"meals": meals} if meals else {})}


class MealTimeIssueTests(unittest.TestCase):
    def test_the_days_own_meal_times_count_against_its_free_time(self):
        items = [todays(f"Task {number}", "learning", 120) for number in range(4)]
        long_meals = [{"title": "Lunch", "start_time": "11:00", "duration_minutes": 180},
                      {"title": "Dinner", "start_time": "17:00", "duration_minutes": 180}]

        self.assertEqual(AgentOrchestrator().day_issues(day_of(*items), {}, {}, "09:00"), [])
        issues = AgentOrchestrator().day_issues(day_of(*items, meals=long_meals), {}, {}, "09:00")
        self.assertEqual([issue["kind"] for issue in issues], ["day-wont-fit"])


# A task done at first that lately is mostly left unfinished: two of its last three reports.
SLIPPING = {"done": 4, "partial": 1, "skipped": 1, "recent": ["done", "done", "done", "partial", "done", "skipped"],
            "trend": "slipping", "usualMinutes": 45, "lengthChanges": 0}
STEADY = {"done": 4, "partial": 0, "skipped": 0, "recent": ["done"] * 4, "trend": "steady", "usualMinutes": 45,
          "lengthChanges": 0}
LOW_ENERGY = {"date": "2026-10-03", "energy": 2}


class IssueTests(unittest.TestCase):
    def test_an_area_agent_reports_a_task_that_keeps_slipping(self):
        issues = DomainAgent(LEARNING).issues(day_of(todays("Read", "learning")), {("learning", "read"): SLIPPING}, None)
        self.assertEqual(issues, [{"issueKey": "slipping:learning:read", "agent": "learning", "kind": "slipping",
                                   "values": {"taskTitle": "Read", "unfinished": 2, "latest": 3}}])

    def test_a_task_mostly_left_partly_done_has_its_length_reported_as_off(self):
        partly = {**STEADY, "done": 1, "partial": 3, "recent": ["partial", "done", "partial", "partial"]}
        issues = DomainAgent(WORK).issues(day_of(todays("Report", "work", 30)), {("work", "report"): partly}, None)
        self.assertEqual(issues, [{"issueKey": "length-off:work:report", "agent": "work", "kind": "length-off",
                                   "values": {"taskTitle": "Report", "minutes": 30, "partial": 3, "reported": 4,
                                              "reason": "unfinished"}}])

    def test_a_task_whose_length_keeps_changing_has_its_length_reported_as_off(self):
        issues = DomainAgent(PROJECT).issues(day_of(todays("Prototype", "project", 60)),
                                             {("project", "prototype"): {**STEADY, "lengthChanges": 2}}, None)
        self.assertEqual([(issue["kind"], issue["values"]) for issue in issues],
                         [("length-off", {"taskTitle": "Prototype", "minutes": 60, "changes": 2, "reason": "changing"})])

    def test_a_slipping_task_is_reported_once_not_also_for_its_length(self):
        both = {**SLIPPING, "done": 2, "partial": 3, "skipped": 0}
        issues = DomainAgent(LEARNING).issues(day_of(todays("Read", "learning")), {("learning", "read"): both}, None)
        self.assertEqual([issue["kind"] for issue in issues], ["slipping"])

    def test_an_agent_reports_only_its_own_tasks_still_to_do(self):
        day = day_of(todays("Read", "learning"), todays("Notes", "learning", status="done"), todays("Walk", "life"))
        known = {("learning", "read"): STEADY, ("learning", "notes"): SLIPPING, ("life", "walk"): SLIPPING}
        self.assertEqual(DomainAgent(LEARNING).issues(day, known, None), [])

    def test_a_task_paused_with_its_goal_raises_no_issue(self):
        resting = {**todays("Read", "learning"), "goalStatus": "paused"}
        self.assertEqual(DomainAgent(LEARNING).issues(day_of(resting), {("learning", "read"): SLIPPING}, None), [])
        blocks = [{**todays(f"Block {number}", "work", 240), "goalStatus": "paused"} for number in range(3)]
        self.assertEqual(AgentOrchestrator().day_issues(day_of(*blocks), {}, {}, "08:00"), [])

    def test_life_tells_the_orchestrator_when_todays_energy_is_low(self):
        issues = DomainAgent(LIFE).issues(day_of(todays("Walk", "life", 30)), {}, LOW_ENERGY)
        self.assertEqual(issues, [{"issueKey": "low-energy", "agent": "life", "kind": "low-energy",
                                   "values": {"energy": 2}}])

    def test_the_orchestrator_passes_on_what_the_area_agents_report(self):
        issues = AgentOrchestrator().day_issues(day_of(todays("Read", "learning")), {("learning", "read"): SLIPPING},
                                                {}, "08:00")
        self.assertEqual([issue["issueKey"] for issue in issues], ["slipping:learning:read"])

    def test_the_orchestrator_reports_a_day_that_wont_fit(self):
        items = [todays(f"Block {number}", "work", 240) for number in range(3)]
        issues = AgentOrchestrator().day_issues(day_of(*items), {}, {}, "08:00")
        self.assertEqual(issues, [{"issueKey": "day-wont-fit", "agent": "orchestrator", "kind": "day-wont-fit",
                                   "values": {"count": 3, "taskMinutes": 720, "freeMinutes": 660}}])

    def test_tasks_already_reported_do_not_count_against_the_free_time(self):
        items = [todays("Block 0", "work", 240), *(todays(f"Block {number}", "work", 240, "done") for number in (1, 2))]
        self.assertEqual(AgentOrchestrator().day_issues(day_of(*items), {}, {}, "08:00"), [])

    def test_a_day_with_a_set_plan_is_not_checked_for_fit(self):
        items = [todays(f"Block {number}", "work", 240) for number in range(3)]
        self.assertEqual(AgentOrchestrator().day_issues(day_of(*items, confirmed="v1"), {}, {}, "08:00"), [])

    def test_low_energy_on_a_full_day_is_reported_with_the_days_load(self):
        items = [todays(f"Block {number}", "work", 120) for number in range(4)]
        issues = AgentOrchestrator().day_issues(day_of(*items), {}, {"life": LOW_ENERGY}, "08:00")
        self.assertEqual(issues, [{"issueKey": "low-energy-full", "agent": "orchestrator", "kind": "low-energy-full",
                                   "values": {"energy": 2, "taskMinutes": 480, "freeMinutes": 660}}])

    def test_once_the_day_is_over_no_fit_is_reported(self):
        items = [todays(f"Block {number}", "work", 240) for number in range(3)]
        self.assertEqual(AgentOrchestrator().day_issues(day_of(*items), {}, {}, "22:30"), [])

    def test_a_fixed_task_alone_never_makes_a_day_that_wont_fit(self):
        late = todays("Night shift", "work", 180, start="21:30")
        self.assertEqual(AgentOrchestrator().day_issues(day_of(late), {}, {}, "08:00"), [])

    def test_low_energy_on_a_full_day_needs_no_message_once_lighter_day_is_set(self):
        items = [todays(f"Block {number}", "work", 120) for number in range(4)]
        day = {**day_of(*items, confirmed="v1"), "variants": [{"id": "v1", "slug": "gentle"}]}
        self.assertEqual(AgentOrchestrator().day_issues(day, {}, {"life": LOW_ENERGY}, "08:00"), [])

    def test_low_energy_on_a_light_day_raises_nothing(self):
        issues = AgentOrchestrator().day_issues(day_of(todays("Walk", "life", 30)), {}, {"life": LOW_ENERGY}, "08:00")
        self.assertEqual(issues, [])


def outcome(title, domain, minutes=45):
    """One task's outcome over a period, as Database.summary_facts lists it."""
    return {"taskTitle": title, "domain": domain, "scheduled": 1, "done": 1, "partial": 0, "skipped": 0, "planned": 0,
            "startTime": None, "durationMinutes": minutes, "constraintKind": "flexible", "detail": "",
            "lastDate": "2026-10-02", "doneStarts": []}


def facts_with(*outcomes):
    """A period's facts, as Database.summary_facts returns them, holding these task outcomes."""
    return {"recordedDays": 1, "goals": [], "feedback": [], "completedRecurring": [], "taskOutcomes": list(outcomes),
            "domains": {area: {"scheduled": 0, "done": 0, "partial": 0, "skipped": 0}
                        for area in ("learning", "life", "work", "project")},
            "areaEvidence": {"repeats": {area: {"scheduled": 0, "done": 0} for area in ("learning", "life", "work", "project")},
                             "energy": None},
            "knowledgeSourceCount": 0}


class SummaryViewTests(unittest.TestCase):
    def test_summary_gathers_how_each_area_agent_sees_the_periods_tasks(self):
        facts = facts_with(outcome("Read", "learning"), outcome("Notes", "learning"), outcome("Walk", "life"),
                           outcome("Essay", "project", 60))
        profiles = {("learning", "read"): SLIPPING, ("learning", "notes"): STEADY, ("life", "walk"): STEADY,
                    ("project", "essay"): {**STEADY, "lengthChanges": 3}, ("work", "report"): SLIPPING}
        report = AgentOrchestrator().summary_report("week", "2026-W40", facts, profiles)
        self.assertEqual(report["agentsView"], [
            {"agent": "learning", "slipping": ["Read"], "lengthOff": [], "going": ["Notes"], "oftenSkipped": [], "oftenUnanswered": []},
            {"agent": "life", "slipping": [], "lengthOff": [], "going": ["Walk"], "oftenSkipped": [], "oftenUnanswered": []},
            {"agent": "project", "slipping": [], "lengthOff": ["Essay"], "going": [], "oftenSkipped": [], "oftenUnanswered": []},
        ])

    def test_without_profiles_summary_has_no_agents_view(self):
        report = AgentOrchestrator().summary_report("week", "2026-W40", facts_with(outcome("Read", "learning")))
        self.assertEqual(report["agentsView"], [])


class DecisionTests(unittest.TestCase):
    TASKS = [("Read", "learning", 60, None), ("Notes", "learning", 45, None), ("Walk", "life", 30, None)]

    def test_without_the_model_the_tally_of_votes_decides_and_names_who_voted(self):
        picks, votes, decided = AgentOrchestrator().decide_plans(choice(self.TASKS), {}, None)
        self.assertEqual(decided, "votes")
        self.assertEqual(picks[0], {"kind": "focused", "agents": ["learning"], "names": "Learning"})
        self.assertEqual(len(picks), 2)
        self.assertEqual(set(votes), {"learning", "life"})

    def test_the_model_decides_with_every_agents_votes_in_front_of_it(self):
        seen = []

        def model(context):
            seen.append(context["agentVotes"])
            return [{"kind": "spacious", "why": "Room.", "whyZh": "余地。"}]

        picks, _, decided = AgentOrchestrator().decide_plans(choice(self.TASKS), {}, model)
        self.assertEqual(decided, "model")
        self.assertEqual(picks[0]["kind"], "spacious")
        self.assertIn("learning", seen[0])
        self.assertEqual(picks[1]["kind"], "focused", "the votes fill any place the model leaves")


class ChangeConcernTests(unittest.TestCase):
    BEFORE = {"title": "Read", "domain": "learning", "date": "2026-10-03", "start_time": None, "duration_minutes": 45,
              "completion_status": "planned", "detail": "", "repeatKind": "none", "goalId": None,
              "constraint_kind": "flexible"}

    def test_an_edit_concerns_only_the_agents_that_read_what_changed(self):
        concerns = AgentOrchestrator().task_change_concerns
        self.assertEqual(concerns(self.BEFORE, dict(self.BEFORE)), (False, False))
        self.assertEqual(concerns(self.BEFORE, {**self.BEFORE, "detail": "Chapter 4"}), (False, True))
        self.assertEqual(concerns(self.BEFORE, {**self.BEFORE, "start_time": "09:00", "constraint_kind": "fixed"}), (True, True))
        self.assertEqual(concerns(None, self.BEFORE), (True, True))


if __name__ == "__main__":
    unittest.main()
