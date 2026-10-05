import unittest

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.task_review import review_area, review_tasks


def task(title, domain="project", minutes=60, start=None, kind=None, detail="", source="estimate"):
    """A task on the day under review, as the service stores it; its length is an agent's estimate."""
    return {"title": title, "domain": domain, "detail": detail, "start_time": start,
            "duration_minutes": minutes, "constraint_kind": kind or ("fixed" if start else "flexible"),
            "acceptance": "accepted", "durationSource": source}


def profile(title, domain="project", done=0, partial=0, skipped=0, planned=0, requests=0, usual_start=None, trend=None):
    """What a task's area agent knows of it from every record, keyed as the database keeps it."""
    return {(domain, title.lower()): {
        "title": title, "done": done, "partial": partial, "skipped": skipped, "unreported": planned,
        "scheduled": done + partial + skipped + planned, "shortenRequests": requests, "usualStart": usual_start,
        "trend": trend}}


def profiles(*entries):
    return {key: value for entry in entries for key, value in entry.items()}


def kinds(findings):
    """Each finding's task and kind."""
    return [(finding["taskTitle"], finding["kind"]) for finding in findings]


class TaskReviewTests(unittest.TestCase):
    def test_an_often_unfinished_task_is_shortened_with_its_first_step(self):
        findings = review_tasks("project", [task("Guide", detail="Outline three sections.")],
                                profile("Guide", done=1, partial=1, skipped=2))
        self.assertEqual(findings, [{
            "agent": "project", "domain": "project", "taskTitle": "Guide", "kind": "shorten",
            "done": 1, "partial": 1, "skipped": 2, "reported": 4,
            "fromMinutes": 60, "toMinutes": 45, "firstStep": "Outline three sections"}])

    def test_a_task_that_cannot_be_shortened_keeps_its_length_and_says_why(self):
        unfinished = profiles(profile("Guide", partial=1, skipped=1), profile("Stand-up", "work", skipped=2),
                              profile("Short", partial=2))
        findings = review_tasks("project", [task("Guide", source="user")], unfinished)
        findings += review_tasks("work", [task("Stand-up", "work", 30, "10:00")], unfinished)
        findings += review_tasks("project", [task("Short", minutes=15)], unfinished)
        self.assertEqual([(finding["kind"], finding["reason"]) for finding in findings],
                         [("hold", "yours"), ("hold", "fixed"), ("hold", "minimum")])

    def test_a_length_the_user_set_is_never_shortened_by_findings_or_requests(self):
        findings = review_tasks("project", [task("Guide", source="user")], profile("Guide", partial=1, skipped=2))
        self.assertEqual([(finding["kind"], finding["reason"]) for finding in findings], [("hold", "yours")])
        asked = review_tasks("project", [task("Guide", source="user")], profile("Guide", done=4, requests=2))
        self.assertEqual(kinds(asked), [("Guide", "keep")])

    def test_a_task_usually_done_keeps_its_length(self):
        findings = review_tasks("learning", [task("Notes", "learning", 45)],
                                profile("Notes", "learning", done=3, partial=1))
        self.assertEqual(kinds(findings), [("Notes", "keep")])
        self.assertEqual(findings[0]["minutes"], 45)

    def test_new_unreported_and_mixed_tasks_are_named_for_what_they_are(self):
        history = profiles(profile("Listed", planned=3), profile("Mixed", done=1, skipped=1))
        findings = review_tasks("project", [task("Fresh"), task("Listed"), task("Mixed")], history)
        self.assertEqual(kinds(findings), [("Fresh", "new"), ("Listed", "unreported"), ("Mixed", "mixed")])
        self.assertEqual(findings[1]["scheduled"], 3)

    def test_repeated_requests_to_shorten_come_before_the_reports(self):
        findings = review_tasks("project", [task("Guide")], profile("Guide", done=4, requests=2))
        self.assertEqual(kinds(findings), [("Guide", "asked-shorter")])
        self.assertEqual((findings[0]["requests"], findings[0]["toMinutes"]), (2, 45))

    def test_an_untimed_task_done_at_a_steady_time_gets_a_preferred_start(self):
        history = profiles(profile("Notes", "learning", done=3, usual_start="08:30"), profile("Drifts", "learning", done=2))
        findings = review_tasks("learning", [task("Notes", "learning"), task("Drifts", "learning")], history)
        times = [finding for finding in findings if finding["kind"] == "time"]
        self.assertEqual([(finding["taskTitle"], finding["preferredStart"], finding["done"]) for finding in times],
                         [("Notes", "08:30", 3)])

    def test_only_its_own_areas_accepted_tasks_are_reviewed(self):
        pending = {**task("Waiting"), "acceptance": "pending"}
        findings = review_tasks("project", [task("Walk", "life"), pending, task("Mine")], {})
        self.assertEqual(kinds(findings), [("Mine", "new")])

    def test_a_task_is_known_however_its_title_is_written_and_its_trend_is_kept(self):
        findings = review_tasks("project", [task("  guide ")], profile("Guide", done=3, skipped=1, trend="slipping"))
        self.assertEqual(kinds(findings), [("  guide ", "keep")])
        self.assertEqual(findings[0]["trend"], "slipping")

    def test_area_findings_carry_what_each_agent_reads(self):
        evidence = {"repeats": {"life": {"scheduled": 4, "done": 3}}, "energy": {"date": "2026-10-01", "level": 2}}
        learning = {"date": "2026-10-02", "lastPractised": "2026-09-28",
                    "dueForReview": [{"goalId": "goal_1", "title": "RAG", "days": 4, "lastDone": "2026-09-28"}]}
        work_day = [task("Stand-up", "work", 30, "10:00"), task("Review", "work", 60, "14:00"), task("Report", "work")]
        self.assertEqual(review_area("learning", [], evidence, learning),
                         [{"agent": "learning", "domain": "learning", "kind": "area-learning",
                           "lastPractised": "2026-09-28", "due": ["RAG"]}])
        self.assertEqual(review_area("life", [], evidence),
                         [{"agent": "life", "domain": "life", "kind": "area-life", "date": "2026-10-01",
                           "energy": 2, "repeatsDone": 3, "repeatsScheduled": 4, "lighter": True}])
        self.assertEqual(review_area("work", work_day, evidence),
                         [{"agent": "work", "domain": "work", "kind": "area-work", "fixed": 2, "minutes": 90}])
        self.assertEqual(review_area("project", [], evidence), [])
        self.assertEqual(review_area("learning", [], evidence, {"lastPractised": None, "dueForReview": []}), [])

    def test_energy_reported_on_the_day_comes_before_earlier_readings(self):
        evidence = {"energy": {"date": "2026-10-01", "level": 4}}
        self.assertEqual(review_area("life", [], evidence, {"date": "2026-10-02", "energy": 2}),
                         [{"agent": "life", "domain": "life", "kind": "area-life", "date": "2026-10-02",
                           "energy": 2, "repeatsDone": 0, "repeatsScheduled": 0, "lighter": True}])
        self.assertEqual(review_area("life", [], evidence, {"date": "2026-10-02", "energy": None})[0]["date"], "2026-10-01")


if __name__ == "__main__":
    unittest.main()
