import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app import patterns
from backend.app.app_settings import DEFAULT_YOUR_DAY, MIN_DAY_MINUTES, SETTINGS_FILE, AppSettings
from backend.app.memory import day_rules
from backend.app.planner import DayRules, build_recorded_variants, day_load
from backend.app.time_taken import current_and_next, limit_stopped
from backend.tests.test_graphs import GraphDay
from backend.tests.test_planner import fixed, untimed
from backend.tests.test_repeats import SeriesDay
from backend.tests.test_rules import spans
from backend.tests.test_schedule import overlaps
from backend.tests.test_schedule_cards import CardDay
from backend.tests.test_time_taken import names, task

EARLY = {"start": "07:00", "end": "22:00"}
SHORT = {"start": "09:00", "end": "20:00"}


class YourDaySettingTests(unittest.TestCase):
    """Your day is 09:00 to 22:00 until set, kept once for both workspaces, and at least six hours long."""

    def setUp(self):
        """The shared settings file's place in a temporary folder, not yet written."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / SETTINGS_FILE

    def test_09_to_22_until_set_then_kept_in_the_shared_file(self):
        settings = AppSettings(self.path)
        self.assertEqual(settings.your_day(), DEFAULT_YOUR_DAY)
        self.assertEqual(DEFAULT_YOUR_DAY, {"start": "09:00", "end": "22:00"})
        self.assertEqual(MIN_DAY_MINUTES, 6 * 60)
        self.assertEqual(settings.set_your_day(EARLY), EARLY)
        self.assertEqual(json.loads(self.path.read_text())["yourDay"], EARLY)
        self.assertEqual(AppSettings(self.path).your_day(), EARLY, "the other workspace reads the same file")

    def test_only_a_day_of_six_hours_or_more_is_kept(self):
        settings = AppSettings(self.path)
        for broken in ({"start": "22:00", "end": "09:00"}, {"start": "09:00", "end": "14:59"}, {"start": "7am", "end": "22:00"},
                       {"start": "07:00", "end": "24:00"}, {"start": "07:00"}):
            with self.subTest(broken=broken), self.assertRaises(ValueError):
                settings.set_your_day(broken)
        self.assertEqual(settings.your_day(), DEFAULT_YOUR_DAY)
        self.assertEqual(settings.set_your_day({"start": "09:00", "end": "15:00"}), {"start": "09:00", "end": "15:00"})


class DayRulesYourDayTests(unittest.TestCase):
    """A day's rules carry Your day, and the work schedule is clipped to it."""

    DAY = "2026-10-14"

    def test_the_days_bounds_reach_its_rules_09_to_22_by_default(self):
        default = day_rules([], self.DAY)
        self.assertEqual((default.day_start, default.day_end), ("09:00", "22:00"))
        early = day_rules([], self.DAY, your_day=EARLY)
        self.assertEqual((early.day_start, early.day_end), ("07:00", "22:00"))

    def test_working_hours_and_focus_time_are_clipped_to_your_day(self):
        later = {"start": "10:00", "end": "22:00"}
        self.assertEqual(day_rules([], self.DAY, {"mode": "working", "start": "08:00", "end": "17:00"}, your_day=later).working,
                         ("10:00", "17:00"))
        self.assertEqual(day_rules([], self.DAY, {"mode": "focus", "start": "20:00", "end": "23:00"}, your_day=later).focus,
                         ("20:00", "22:00"))
        self.assertIsNone(day_rules([], self.DAY, {"mode": "working", "start": "06:00", "end": "08:00"}).working,
                          "a range wholly outside Your day holds nothing")


class PlannerYourDayTests(unittest.TestCase):
    """Plans place tasks within Your day: from its start, and done by its end."""

    DAY = (untimed("Read", "learning", 60), untimed("Walk", "life", 30))

    def test_by_default_plans_are_as_before(self):
        default = build_recorded_variants(self.DAY, earliest="06:00")
        explicit = build_recorded_variants(self.DAY, earliest="06:00", rules=DayRules(day_start="09:00", day_end="22:00"))
        self.assertEqual([spans(variant) for variant in explicit], [spans(variant) for variant in default])
        self.assertEqual(min(start for start, _ in spans(default[0]).values()), 9 * 60)

    def test_an_early_start_lets_tasks_go_before_working_hours(self):
        late = build_recorded_variants(self.DAY, earliest="06:00", rules=DayRules(working=("09:00", "17:00")))
        self.assertEqual(min(start for start, _ in spans(late[0]).values()), 17 * 60)
        early = build_recorded_variants(self.DAY, earliest="06:00",
                                        rules=DayRules(working=("09:00", "17:00"), day_start="07:00"))
        self.assertEqual(min(start for start, _ in spans(early[0]).values()), 7 * 60)
        for variant in early:
            for title, span in spans(variant).items():
                self.assertFalse(overlaps(span, "09:00", "17:00"), f"{variant['slug']}: {title} {span}")

    def test_a_day_ending_earlier_places_nothing_after_it_and_says_so_when_tasks_dont_fit(self):
        rules = DayRules(day_end="20:00")
        for variant in build_recorded_variants(self.DAY, earliest="06:00", rules=rules):
            self.assertTrue(all(end <= 20 * 60 for _, end in spans(variant).values()), variant["slug"])
        self.assertEqual(day_load(self.DAY, "09:00", rules=rules)["freeMinutes"], 540)
        self.assertEqual(day_load(self.DAY, "09:00")["freeMinutes"], 660)
        with self.assertRaisesRegex(ValueError, "20:00"):
            build_recorded_variants((untimed("Thesis", "learning", 600),), earliest="06:00", rules=rules)

    def test_a_day_ending_later_has_room_after_22(self):
        day = (fixed("13:00", "Workshop", "life", 480), untimed("Essay", "learning", 120))
        with self.assertRaises(ValueError):
            build_recorded_variants(day, earliest="13:00")
        plans = build_recorded_variants(day, earliest="13:00", rules=DayRules(day_end="23:30"))
        self.assertEqual(spans(plans[0])["Essay"], (21 * 60, 23 * 60))


class TimeTakenYourDayTests(unittest.TestCase):
    """Your day's end stops what is current, and a task left running stops there rather than at its limit."""

    def test_nothing_is_current_once_your_day_ends(self):
        day = [task("Review", "19:00")]
        self.assertEqual(names(current_and_next(day, [], "20:30")), ("Review", None))
        self.assertEqual(names(current_and_next(day, [], "20:30", day_end="20:00")), (None, None))

    def test_a_task_left_running_stops_at_your_days_end_before_its_limit(self):
        day = [task("Report", "18:00", 30)]
        self.assertEqual(limit_stopped(day, [], None), {"report"})
        self.assertEqual(limit_stopped(day, [], None, day_end="18:45"), set())


class PatternsYourDayTests(unittest.TestCase):
    """A status set after Your day ended counts as set the next day in Reporting habit."""

    def test_a_status_after_your_days_end_was_set_the_next_day(self):
        record = {"status": "done", "statusAt": "20:30", "end": "19:00", "ownEnd": "19:00"}
        self.assertEqual(patterns._reported(record), "laterDay")
        self.assertEqual(patterns._reported(record, "20:00"), "nextDay")

    def test_a_fixed_task_after_your_days_end_reported_in_its_own_time_was_reported_right_away(self):
        record = {"status": "done", "statusAt": "21:50", "end": "21:50", "ownEnd": "22:00"}
        self.assertEqual(patterns._reported(record, "20:00"), "rightAway")
        self.assertEqual(patterns._reported({**record, "statusAt": "22:30"}, "20:00"), "nextDay")


class StoreYourDayTests(SeriesDay):
    """The store reads Your day for the day's rules, its plans, and when a task is left without a status."""

    def test_the_days_rules_and_the_day_carry_your_day(self):
        self.assertEqual(self.store.bootstrap_day(self.today)["yourDay"], DEFAULT_YOUR_DAY)
        self.store.your_day = lambda: EARLY
        self.assertEqual(self.store.day_rules(self.today).day_start, "07:00")
        self.assertEqual(self.store.bootstrap_day(self.today)["yourDay"], EARLY)

    def test_a_task_is_left_without_a_status_once_your_day_ends(self):
        self.store.create_daily_item(self.task("Read", "10:00", 30))
        with patch("backend.app.database.local_time", return_value="21:00"):
            self.assertFalse(self.store.daily_items(self.today)[0]["noReply"])
            self.store.your_day = lambda: SHORT
            self.assertTrue(self.store.daily_items(self.today)[0]["noReply"])

    def test_todays_plans_start_at_your_day(self):
        self.store.your_day = lambda: {"start": "06:00", "end": "22:00"}
        self.store.create_daily_item(self.task("Read", None, 45))
        with patch("backend.app.database.local_time", return_value="06:00"):
            self.store.create_recorded_plan(self.today)
        day = self.store.bootstrap_day(self.today)
        self.assertEqual(min(entry["start_time"] for entry in day["entries"]), "06:00")


class FixedAfterYourDayTests(GraphDay):
    """A fixed task whose own time runs past Your day's end stays open until that time has passed, rather than
    reading no reply at the day's end, before it has even started; a task within the day still does at its end."""

    def setUp(self):
        """Your day ending at 20:00, and three fixed tasks today: one within it, one running past its end and one
        after."""
        super().setUp()
        self.store.your_day = lambda: SHORT
        for title, start, minutes in (("Read", "10:00", 30), ("Call", "19:30", 60), ("Gym", "21:00", 60)):
            self.store.create_daily_item(self.task(title, start, minutes))

    def at(self, clock, read):
        """What `read` gives with the service's local time at `clock`."""
        with patch("backend.app.database.local_time", return_value=clock):
            return read()

    def test_today_reads_no_reply_only_once_its_own_time_has_passed(self):
        def no_reply() -> dict[str, bool]:
            """Whether each of today's tasks reads no reply, by its title."""
            return {item["title"]: item["noReply"] for item in self.store.daily_items(self.today)}

        self.assertEqual(self.at("20:15", no_reply), {"Read": True, "Call": False, "Gym": False})
        self.assertEqual(self.at("20:30", no_reply), {"Read": True, "Call": True, "Gym": False})
        self.assertEqual(self.at("22:00", no_reply), {"Read": True, "Call": True, "Gym": True})

    def test_catch_up_reads_the_same(self):
        def no_reply() -> dict[str, bool]:
            """Whether each task to catch up on reads no reply, by its title."""
            return {task["title"]: task["noReply"] for task in self.store.catch_up_tasks(self.today)}

        self.assertEqual(self.at("20:15", no_reply), {"Read": True, "Call": False, "Gym": False})

    def test_patterns_and_summary_count_it_only_once_its_time_has_passed(self):
        def records(field: str) -> dict[str, str]:
            """One field of each of today's pattern records, by its title."""
            return {record["title"]: record[field] for record in self.store.pattern_records(self.today, self.today)["records"]}

        def unanswered() -> int:
            """How many of today's Learning tasks Summary counts as no reply."""
            return self.store.summary_facts(self.today, self.today)["domains"]["learning"]["noReply"]

        self.assertEqual(self.at("20:15", lambda: records("status")), {"Read": "noReply"})
        self.assertEqual(self.at("22:00", lambda: records("status")), {"Read": "noReply", "Call": "noReply", "Gym": "noReply"})
        self.assertEqual(self.at("22:00", lambda: records("ownEnd")), {"Read": "10:30", "Call": "20:30", "Gym": "22:00"})
        self.assertEqual(self.at("20:15", unanswered), 1)
        self.assertEqual(self.at("22:00", unanswered), 3)

    def test_a_set_plans_entry_after_the_days_end_is_still_to_report(self):
        self.set_plan(self.today, [("Memo", "work", 30, "planned", False, None), ("Gym", "life", 60, "planned", False, None)])
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE plan_entries SET start_time = '21:00' WHERE title = 'Gym'")

        def follow() -> dict:
            """Today's set plan, as its follow-through graph counts it."""
            return self.store.report_graphs(self.today, self.today)["followThrough"][0]

        self.assertEqual({part: self.at("20:15", follow)[part] for part in ("noReply", "unreported")},
                         {"noReply": 1, "unreported": 1})
        self.assertEqual(self.at("22:00", follow)["noReply"], 2)


class YourDayRouteTests(SeriesDay):
    """Settings › Schedule reads and keeps Your day, and today's proposed plans follow a change at once."""

    def test_your_day_is_09_to_22_until_set_and_kept_once_set(self):
        self.assertEqual(self.client.get("/api/schedule").json()["day"], DEFAULT_YOUR_DAY)
        kept = self.client.put("/api/your-day", json=EARLY)
        self.assertEqual(kept.status_code, 200, kept.text)
        self.assertEqual(kept.json()["day"], EARLY)
        self.assertEqual(self.client.get("/api/bootstrap", params={"date": self.today}).json()["yourDay"], EARLY)

    def test_a_day_shorter_than_six_hours_is_refused_and_nothing_changes(self):
        refused = self.client.put("/api/your-day", json={"start": "09:00", "end": "13:00"})
        self.assertEqual(refused.status_code, 422)
        self.assertEqual(self.client.get("/api/schedule").json()["day"], DEFAULT_YOUR_DAY)

    def test_todays_proposed_plans_follow_a_new_day_at_once(self):
        self.client.post("/api/daily-items", json=self.task("Read", None, 45))
        self.client.post("/api/plan/generate", json={"date": self.today})

        def first() -> str:
            """When today's first plan entry starts."""
            return min(entry["start_time"] for entry in self.client.get("/api/bootstrap", params={"date": self.today}).json()["entries"])

        self.assertEqual(first(), "09:00")
        self.client.put("/api/your-day", json=EARLY)
        self.assertEqual(first(), "07:00")


class YourDayCardTests(CardDay):
    """"My day starts at 7" pencils one card with the whole day; nothing changes until it is confirmed."""

    def test_each_phrase_pencils_the_whole_day_in_english_and_chinese(self):
        for message, language, expected in (
                ("my day starts at 7", "en", {"start": "07:00", "end": "22:00"}),
                ("I finish my day at 21:00", "en", {"start": "09:00", "end": "21:00"}),
                ("My day runs from 6:30am to 9pm", "en", {"start": "06:30", "end": "21:00"}),
                ("我的一天从7点开始", "zh", {"start": "07:00", "end": "22:00"}),
                ("我晚上9点结束一天", "zh", {"start": "09:00", "end": "21:00"})):
            with self.subTest(message=message):
                reply = self.say(message, language)
                card = reply["proposedAction"]
                self.assertEqual(card["actionType"], "set_your_day")
                self.assertEqual(card["payload"], {"day": expected})
                self.assertIn("Nothing changes until you confirm", reply["assistantMessage"]["content"])
                self.assertEqual(self.schedule()["day"], DEFAULT_YOUR_DAY, "nothing changes until confirmed")

    def test_a_day_shorter_than_six_hours_is_answered_in_words(self):
        reply = self.say("my day ends at 12:00")
        self.assertIsNone(reply["proposedAction"])
        self.assertIn("Nothing was changed", reply["assistantMessage"]["content"])

    def test_confirming_keeps_your_day(self):
        card = self.say("my day starts at 7")["proposedAction"]
        decided = self.decide(card)
        self.assertEqual(decided.status_code, 200, decided.text)
        self.assertEqual(self.schedule()["day"], EARLY)
        self.assertEqual(decided.json()["settings"]["day"], EARLY)


if __name__ == "__main__":
    unittest.main()
