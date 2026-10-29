import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.database import Database
from backend.app.main import create_app
from backend.app.memory import day_rules, days_in, entry_line, read_statement, rule_breaks, times_in, until_in
from backend.app.planner import DayRules
from backend.tests.test_api import FakeEmbeddingGateway, FakeGateway, FakeSpeechGateway

# The labelled statements, with what a model proposes for each and what must be kept (see its "about").
LABELLED = json.loads((Path(__file__).parent / "memory_statements.json").read_text(encoding="utf-8"))
# The fields an entry is compared by: the ones a statement fills, and none of its bookkeeping.
FIELDS = ("kind", "ruleKind", "start", "end", "latest", "days", "area", "task", "endsOn", "wording")


def existing(*names):
    """Entries kept before, from the labelled set, each with its name as its id."""
    return [{"id": name, **{field: None for field in FIELDS}, **LABELLED["existing"][name]} for name in names]


def compared(entry):
    """An entry's fields as the labels give them: those it has, a rule's own wording left out."""
    shown = {field: entry.get(field) for field in FIELDS if entry.get(field) not in (None, [])}
    if shown.get("kind") == "rule":
        shown.pop("wording", None)
    return shown


class ParsingTests(unittest.TestCase):
    """A rule's times, days and end date come from the user's own words, in English or Chinese."""

    def test_days(self):
        for text, days in (("on weekdays", (0, 1, 2, 3, 4)), ("at weekends", (5, 6)), ("every day", tuple(range(7))),
                           ("daily", tuple(range(7))), ("on Mondays and Wednesdays", (0, 2)), ("Mon–Fri", (0, 1, 2, 3, 4)),
                           ("from Tuesday to Thursday", (1, 2, 3)), ("Sat", (5,)), ("工作日", (0, 1, 2, 3, 4)),
                           ("周末", (5, 6)), ("每天", tuple(range(7))), ("周一到周三", (0, 1, 2)), ("星期天", (6,)),
                           ("礼拜五", (4,)), ("周二和周四", (1, 3))):
            self.assertEqual(days_in(text), days, text)

    def test_no_days(self):
        for text in ("Keep evenings free", "today", "this weekend's plans are big"):
            self.assertIsNone(days_in(text), text)

    def test_times(self):
        for text, times in (("18:00–19:00", ["18:00", "19:00"]), ("6-7pm", ["18:00", "19:00"]),
                            ("between 12 and 1pm", ["12:00", "13:00"]), ("from 9am to 12pm", ["09:00", "12:00"]),
                            ("11 to 1pm", ["11:00", "13:00"]), ("by 6pm", ["18:00"]), ("18点到19点", ["18:00", "19:00"]),
                            ("中午12点到1点", ["12:00", "13:00"]), ("下午3点到5点半", ["15:00", "17:30"]),
                            ("晚上8点前", ["20:00"]), ("上午9点到12点", ["09:00", "12:00"]), ("21点以后", ["21:00"])):
            self.assertEqual(times_in(text), times, text)

    def test_until(self):
        today = LABELLED["today"]
        for text, ends in (("until 31 Dec", "2026-12-31"), ("till December 20th", "2026-12-20"),
                           ("until the end of January", "2027-01-31"), ("until January", "2027-01-31"),
                           ("到12月31日为止", "2026-12-31"), ("直到11月底", "2026-11-30"), ("until 2027-02-01", "2027-02-01")):
            self.assertEqual(until_in(text, today), ends, text)
        self.assertIsNone(until_in("Keep Monday evenings free", today))


class ValidatorTests(unittest.TestCase):
    """The model proposes what kind a statement is; the service keeps a rule only when its own words fill every field
    of that kind, else a note, never half a rule; and it never keeps the same entry twice."""

    def test_every_labelled_statement_is_kept_as_labelled(self):
        for case in LABELLED["statements"]:
            with self.subTest(case["statement"]):
                read = read_statement(case["statement"], case["proposal"], LABELLED["today"],
                                      existing(*case.get("existing", ())))
                expect = case["expect"]
                self.assertEqual(read["outcome"], expect["outcome"])
                self.assertEqual(read.get("updates"), expect.get("updates"))
                if "entry" in expect:
                    self.assertEqual(compared(read["entry"]), expect["entry"])
                self.assertEqual(read.get("rule"), expect.get("rule"))
                self.assertEqual(read.get("missing", []), expect.get("missing", []))

    def test_a_rule_is_never_kept_as_a_note_nor_a_note_as_a_rule(self):
        for case in LABELLED["statements"]:
            if "entry" not in case["expect"]:
                continue
            read = read_statement(case["statement"], case["proposal"], LABELLED["today"], existing(*case.get("existing", ())))
            self.assertEqual(read["entry"]["kind"], case["expect"]["entry"]["kind"], case["statement"])

    def test_a_field_the_model_gives_that_the_words_dont_hold_is_missing(self):
        proposal = {"kind": "rule", "rule": "keep-free", "start": "18:00", "end": "22:00", "days": [0, 1, 2, 3, 4]}
        read = read_statement("Keep evenings free", proposal, LABELLED["today"], [])
        self.assertEqual((read["entry"]["kind"], read["missing"]), ("note", ["start", "end", "days"]))

    def test_a_task_kept_off_must_be_named_in_the_words(self):
        read = read_statement("Keep Sundays quiet", {"kind": "rule", "rule": "keep-off", "task": "Gym"}, LABELLED["today"], [])
        self.assertEqual((read["entry"]["kind"], read["missing"]), ("note", ["area"]))

    def test_an_unreadable_answer_keeps_a_remember_as_a_general_note(self):
        read = read_statement("Remember that the boiler is serviced in March", None, LABELLED["today"], [])
        self.assertEqual(compared(read["entry"]), {"kind": "note", "area": "general",
                                                   "wording": "the boiler is serviced in March"})

    def test_a_note_holds_at_most_40_words(self):
        long = "I " + " ".join(["really"] * 50) + " like quiet mornings"
        read = read_statement(long, {"kind": "note", "area": "life"}, LABELLED["today"], [])
        self.assertEqual(len(read["entry"]["wording"].split()), 40)
        self.assertTrue(read["entry"]["wording"].endswith("…"))

    def test_an_end_date_without_a_year_is_the_next_one(self):
        read = read_statement("No work on weekends until 1 Oct", {"kind": "rule", "rule": "keep-off"}, LABELLED["today"], [])
        self.assertEqual(read["entry"]["endsOn"], "2027-10-01")

    def test_said_on_is_today(self):
        read = read_statement("No work on weekends", {"kind": "rule", "rule": "keep-off"}, LABELLED["today"], [])
        self.assertEqual(read["entry"]["saidOn"], LABELLED["today"])


class WordingTests(unittest.TestCase):
    """An entry reads the same way everywhere Ava names it: kind, what, days and its end."""

    def test_lines(self):
        self.assertEqual(entry_line({"kind": "rule", "ruleKind": "keep-free", "start": "18:00", "end": "19:00",
                                     "days": [0, 1, 2, 3, 4], "endsOn": "2026-12-31"}),
                         "Rule · Keep free · 18:00–19:00 · Mon–Fri · until 31 Dec")
        self.assertEqual(entry_line({"kind": "rule", "ruleKind": "keep-off", "area": "work", "days": [5, 6]}),
                         "Rule · Keep off · Work · Sat–Sun")
        self.assertEqual(entry_line({"kind": "rule", "ruleKind": "keep-off", "task": "Gym", "days": [0, 2, 4]}),
                         "Rule · Keep off · “Gym” · Mon, Wed, Fri")
        self.assertEqual(entry_line({"kind": "rule", "ruleKind": "finish-by", "latest": "18:00", "days": list(range(7))}),
                         "Rule · Finish by · 18:00 · Every day")
        self.assertEqual(entry_line({"kind": "note", "area": "learning", "wording": "I study best in the morning"}),
                         "Note · Learn · I study best in the morning")
        self.assertEqual(entry_line({"kind": "note", "area": "general", "wording": "Spanish first"}),
                         "Note · General · Spanish first")


RULES = [
    {"id": "free", "kind": "rule", "ruleKind": "keep-free", "start": "18:00", "end": "19:00", "days": [0, 1, 2, 3, 4],
     "saidOn": "2026-10-01", "endsOn": None},
    {"id": "off", "kind": "rule", "ruleKind": "keep-off", "area": "work", "task": None, "days": [5, 6],
     "saidOn": "2026-10-01", "endsOn": None},
    {"id": "gym", "kind": "rule", "ruleKind": "keep-off", "area": None, "task": "Gym", "days": [6],
     "saidOn": "2026-10-01", "endsOn": None},
    {"id": "finish", "kind": "rule", "ruleKind": "finish-by", "latest": "17:00", "days": [4],
     "saidOn": "2026-10-01", "endsOn": "2026-10-31"},
    {"id": "note", "kind": "note", "area": "learning", "wording": "I study best in the morning",
     "saidOn": "2026-10-01", "endsOn": None},
]


class DayRulesTests(unittest.TestCase):
    """Rules apply on their days, from the day they were said until their end date; notes never bind a plan."""

    def test_a_weekday(self):
        self.assertEqual(day_rules(RULES, "2026-10-07"), DayRules(free=(("18:00", "19:00"),)))

    def test_a_friday_within_its_end(self):
        self.assertEqual(day_rules(RULES, "2026-10-09"), DayRules(free=(("18:00", "19:00"),), finish_by="17:00"))

    def test_a_friday_after_its_end(self):
        self.assertEqual(day_rules(RULES, "2026-11-06"), DayRules(free=(("18:00", "19:00"),)))

    def test_a_sunday(self):
        self.assertEqual(day_rules(RULES, "2026-10-11"), DayRules(off_areas=frozenset({"work"}), off_tasks=frozenset({"gym"})))

    def test_before_it_was_said(self):
        self.assertEqual(day_rules(RULES, "2026-09-30"), DayRules())

    def test_the_earliest_finish_holds(self):
        later = {**RULES[3], "id": "later", "latest": "19:00"}
        self.assertEqual(day_rules([RULES[3], later], "2026-10-09").finish_by, "17:00")


class RuleBreakTests(unittest.TestCase):
    """A task the user placed against a rule saves; it names each rule it breaks."""

    def task(self, **fields):
        """An untimed hour of Learning, Read, on 2026-10-07, with `fields` over it."""
        return {"date": "2026-10-07", "title": "Read", "domain": "learning", "start_time": None, "duration_minutes": 60,
                **fields}

    def test_a_fixed_task_in_a_time_kept_free(self):
        self.assertEqual([rule["id"] for rule in rule_breaks(self.task(start_time="18:30"), RULES)], ["free"])

    def test_a_task_beside_the_time_kept_free(self):
        self.assertEqual(rule_breaks(self.task(start_time="17:00"), RULES), [])

    def test_a_task_ending_after_the_finish(self):
        broken = rule_breaks(self.task(date="2026-10-09", start_time="16:30"), RULES)
        self.assertEqual([rule["id"] for rule in broken], ["finish"])

    def test_a_task_kept_off_by_its_area_or_title_with_or_without_a_time(self):
        self.assertEqual([rule["id"] for rule in rule_breaks(self.task(date="2026-10-11", domain="work"), RULES)], ["off"])
        self.assertEqual([rule["id"] for rule in rule_breaks(self.task(date="2026-10-11", title=" gym ", start_time="08:00"),
                                                             RULES)], ["gym"])

    def test_an_untimed_task_breaks_no_time_rule(self):
        self.assertEqual(rule_breaks(self.task(date="2026-10-09"), RULES), [])


class StoredMemory(unittest.TestCase):
    """A throwaway database for each test."""

    def setUp(self):
        """A throwaway database and today, the clock at 07:00."""
        self.folder = tempfile.TemporaryDirectory()
        self.store = Database(Path(self.folder.name) / "daywright.sqlite3")
        self.today = date.today().isoformat()
        # Early in the day, so today's plans have the whole day to place tasks in, whenever the tests run.
        clock = patch("backend.app.database.local_time", return_value="07:00")
        clock.start()
        self.addCleanup(clock.stop)

    def tearDown(self):
        """Remove the throwaway database's folder."""
        self.folder.cleanup()

    def keep(self, statement, proposal):
        """Keep what a statement reads as today, the way confirming its card does."""
        return self.store.save_memory(read_statement(statement, proposal, self.today, self.store.memory_entries())["entry"])


class StorageTests(StoredMemory):
    """Entries are kept exactly as read, change in place, and go for good when deleted."""

    def test_every_labelled_add_is_kept_exactly(self):
        for case in LABELLED["statements"]:
            if case["expect"]["outcome"] != "add":
                continue
            with self.subTest(case["statement"]):
                kept = self.keep(case["statement"], case["proposal"])
                stored = next(entry for entry in self.store.memory_entries() if entry["id"] == kept["id"])
                expected = case["expect"]["entry"]
                if "endsOn" in expected:  # The labels' end dates count from their own today, not this one.
                    expected = {**expected, "endsOn": until_in(case["statement"], self.today)}
                self.assertEqual(compared(stored), expected)

    def test_an_update_changes_the_entry_in_place(self):
        kept = self.keep("No work on weekends", {"kind": "rule", "rule": "keep-off"})
        read = read_statement("No work on Sundays", {"kind": "rule", "rule": "keep-off"}, self.today, self.store.memory_entries())
        self.assertEqual((read["outcome"], read["updates"]), ("update", kept["id"]))
        self.store.save_memory(read["entry"], read["updates"])
        self.assertEqual([(entry["id"], entry["days"]) for entry in self.store.memory_entries()], [(kept["id"], [6])])

    def test_a_duplicate_keeps_one_entry(self):
        self.keep("I study best in the morning", {"kind": "note", "area": "learning"})
        read = read_statement("I study best in the morning", {"kind": "note", "area": "learning"}, self.today,
                              self.store.memory_entries())
        self.assertEqual(read["outcome"], "duplicate")
        self.assertEqual(len(self.store.memory_entries()), 1)

    def test_a_delete_is_for_good(self):
        kept = self.keep("No work on weekends", {"kind": "rule", "rule": "keep-off"})
        self.assertEqual(self.store.delete_memory([kept["id"]]), 1)
        self.assertEqual(self.store.memory_entries(), [])
        with self.assertRaises(ValueError):
            self.store.save_memory({**kept, "days": [5]}, kept["id"])

    def test_an_entry_past_its_end_moves_to_past_and_is_not_read(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        kept = self.store.save_memory({"kind": "rule", "ruleKind": "keep-off", "area": "work", "days": list(range(7)),
                                       "wording": "No work", "saidOn": "2026-01-01", "endsOn": yesterday})
        view = self.store.memory_view(self.today)
        self.assertEqual(([entry["id"] for entry in view["past"]], view["rules"]), ([kept["id"]], []))
        self.assertEqual(self.store.day_rules(self.today), DayRules())

    def test_settings_lists_rules_notes_and_past(self):
        self.keep("Keep 18:00–19:00 free on weekdays", {"kind": "rule", "rule": "keep-free"})
        self.keep("I study best in the morning", {"kind": "note", "area": "learning"})
        view = self.store.memory_view(self.today)
        self.assertEqual((len(view["rules"]), len(view["notes"]), view["past"]), (1, 1, []))

    def test_an_incomplete_entry_is_refused_with_why(self):
        for entry, why in (({"kind": "rule", "ruleKind": "keep-free", "start": "19:00", "end": "18:00", "days": [0]},
                            "ends after it starts"),
                           ({"kind": "rule", "ruleKind": "finish-by", "latest": "18:00", "days": []}, "at least one day"),
                           ({"kind": "rule", "ruleKind": "keep-off", "area": "work", "task": "Gym", "days": [0]}, "one area"),
                           ({"kind": "note", "area": "elsewhere", "wording": "Hi"}, "tagged"),
                           ({"kind": "note", "area": "life", "wording": "word " * 41}, "at most 40 words")):
            with self.subTest(why), self.assertRaisesRegex(ValueError, why):
                self.store.save_memory({"saidOn": self.today, **entry})


class PlansObeyRulesTests(StoredMemory):
    """Plans made from the day's tasks obey the rules kept, and a task placed against one names it."""

    def add(self, title, domain, start=None, minutes=60, day=None, repeat="none"):
        """Make a task `title` in `domain` of `minutes` on `day` (today when not given), fixed at `start` when given,
        repeating as `repeat`; return it."""
        return self.store.create_daily_item({"date": day or self.today, "title": title, "detail": "", "domain": domain,
                                             "startTime": start, "durationMinutes": minutes,
                                             "constraintKind": "fixed" if start else "flexible", "repeatKind": repeat})

    def rule(self, **fields):
        """Keep a rule said today for every day of the week, with `fields` over it; return what was kept."""
        return self.store.save_memory({"kind": "rule", "wording": "a rule", "saidOn": self.today,
                                       "days": list(range(7)), **fields})

    def test_every_plan_keeps_the_time_free_and_says_so(self):
        self.rule(ruleKind="keep-free", start="09:00", end="12:00")
        self.add("Report", "work")
        self.add("Read", "learning")
        self.store.create_recorded_plan(self.today)
        for variant in self.store.bootstrap_day(self.today)["variants"]:
            self.assertIn("planRuleFree", [note["key"] for note in variant["notes"]], variant["slug"])

    def test_a_task_the_user_fixed_in_the_time_names_the_rule_it_breaks(self):
        kept = self.rule(ruleKind="keep-free", start="09:00", end="12:00")
        self.add("Dentist", "life", start="10:00", minutes=30)
        self.add("Read", "learning", start="13:30", minutes=30)
        items = {item["title"]: item for item in self.store.daily_items(self.today)}
        self.assertEqual([rule["id"] for rule in items["Dentist"]["ruleBreaks"]], [kept["id"]])
        self.assertEqual(items["Read"]["ruleBreaks"], [])

    def test_a_repeat_kept_off_the_day_is_not_carried_onto_it(self):
        gym = self.add("Gym", "life", minutes=45, repeat="daily")
        with self.store.connect() as connection:
            connection.execute("UPDATE daily_items SET item_date = ? WHERE id = ?",
                               ((date.today() - timedelta(days=1)).isoformat(), gym["id"]))
        self.add("Read", "learning")
        self.rule(ruleKind="keep-off", task="Gym", days=[date.today().weekday()])
        self.store.create_recorded_plan(self.today)
        self.assertEqual([item["title"] for item in self.store.daily_items(self.today)], ["Read"])

    def test_without_the_rule_the_repeat_is_carried(self):
        gym = self.add("Gym", "life", minutes=45, repeat="daily")
        with self.store.connect() as connection:
            connection.execute("UPDATE daily_items SET item_date = ? WHERE id = ?",
                               ((date.today() - timedelta(days=1)).isoformat(), gym["id"]))
        self.add("Read", "learning")
        self.store.create_recorded_plan(self.today)
        self.assertEqual(sorted(item["title"] for item in self.store.daily_items(self.today)), ["Gym", "Read"])


class RouteTests(StoredMemory):
    """Settings › Memory reads, edits and deletes entries; a changed rule has today's proposed plans made again."""

    def setUp(self):
        """A client of the service on the same database."""
        super().setUp()
        self.client = TestClient(create_app(database=self.store, gateway=FakeGateway(),
                                            embedding_gateway=FakeEmbeddingGateway(), speech_gateway=FakeSpeechGateway()))

    def test_settings_reads_the_entries(self):
        self.keep("No work on weekends", {"kind": "rule", "rule": "keep-off"})
        view = self.client.get("/api/memory").json()
        self.assertEqual(([entry["area"] for entry in view["rules"]], view["notes"], view["past"]), (["work"], [], []))

    def test_an_edit_is_checked_and_kept(self):
        kept = self.keep("I study best in the morning", {"kind": "note", "area": "learning"})
        changed = self.client.put(f"/api/memory/{kept['id']}", json={**kept, "wording": "I study best at night"})
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.json()["notes"][0]["wording"], "I study best at night")
        refused = self.client.put(f"/api/memory/{kept['id']}", json={**kept, "area": "elsewhere"})
        self.assertEqual(refused.status_code, 422)

    def test_a_delete_is_for_good(self):
        kept = self.keep("No work on weekends", {"kind": "rule", "rule": "keep-off"})
        self.assertEqual(self.client.delete(f"/api/memory/{kept['id']}").json()["rules"], [])
        self.assertEqual(self.client.delete(f"/api/memory/{kept['id']}").status_code, 404)

    def test_a_changed_rule_has_todays_proposed_plans_made_again(self):
        self.store.create_daily_item({"date": self.today, "title": "Read", "detail": "", "domain": "learning",
                                      "startTime": None, "durationMinutes": 60, "constraintKind": "flexible",
                                      "repeatKind": "none"})
        self.client.post("/api/plan/generate", json={"date": self.today})
        kept = self.store.save_memory({"kind": "rule", "ruleKind": "keep-free", "start": "21:00", "end": "22:00",
                                       "days": list(range(7)), "wording": "a rule", "saidOn": self.today})
        self.client.put(f"/api/memory/{kept['id']}", json={**kept, "start": "20:00"})
        notes = [note for variant in self.store.bootstrap_day(self.today)["variants"] for note in variant["notes"]
                 if note["key"] == "planRuleFree"]
        self.assertTrue(notes)
        self.assertTrue(all(note["values"] == {"start": "20:00", "end": "22:00"} for note in notes))


if __name__ == "__main__":
    unittest.main()
