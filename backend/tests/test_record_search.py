import threading
import unittest
import zlib
from datetime import date, timedelta

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app import record_search
from backend.app.record_search import (BATCH, ROWS_SHOWN, asks_records, documents, facts, look_up, model_query,
                                       more_line, nothing_line, phrase_query, sync, without_citations)
from backend.app.retrieval import EMBEDDING_DIMENSION, EmbeddingUnavailable, RagService, VectorStore
from backend.tests.test_pattern_records import PatternDay

TODAY = "2026-10-14"  # A Wednesday.
TITLES = ["Review", "Weekly review", "Stretch", "Lesson 4"]
GOALS = ["Spanish to B1", "Restore the old bike"]


def query(message: str, named_day: str | None = None) -> dict | None:
    """The look-up `message`'s phrases make on TODAY, over TITLES and GOALS."""
    return phrase_query(message, TODAY, TITLES, GOALS, named_day)


def asked(start=None, end=None, titles=(), goal=None, area=None, kind=None, energy=None) -> dict:
    """A look-up as phrase_query and model_query give one, every field not named left empty."""
    return {"start": start, "end": end, "titles": list(titles), "goal": goal, "area": area, "kind": kind, "energy": energy}


class MeaningEmbedder:
    """The embedding model as the tests need it: texts that share a meaning lie near each other. Each text is the sum
    of the concepts its words name; one that names none is a direction of its own, near nothing else."""

    CONCEPTS = {"tired": "low energy", "worn out": "low energy", "energy 1.": "low energy", "energy 2.": "low energy",
                "struggle": "unfinished", "partly done": "unfinished", "skipped": "unfinished",
                "spanish": "spanish", "preterite": "spanish", "review": "review"}
    NAMES = sorted(set(CONCEPTS.values()))

    def __init__(self, failing: bool = False) -> None:
        """Embed every text, or fail as an unavailable model does when `failing`."""
        self.failing = failing
        self.document_calls: list[list[str]] = []

    def _vector(self, text: str) -> list[float]:
        """The unit sum of the concepts `text`'s words name, or a direction of its own, from its checksum, when it
        names none."""
        vector = [0.0] * EMBEDDING_DIMENSION
        found = {self.NAMES.index(concept) for word, concept in self.CONCEPTS.items() if word in text.lower()}
        for place in found or {len(self.NAMES) + zlib.crc32(text.encode()) % (EMBEDDING_DIMENSION - len(self.NAMES))}:
            vector[place] = 1.0
        size = sum(value * value for value in vector) ** 0.5
        return [value / size for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Keep the batch asked for and embed each text; fail when `failing`."""
        if self.failing:
            raise EmbeddingUnavailable("The local embedding model is not available")
        self.document_calls.append(list(texts))
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        """Embed a question as a text is embedded; fail when `failing`."""
        if self.failing:
            raise EmbeddingUnavailable("The local embedding model is not available")
        return self._vector(text)


class Answering:
    """The local model, answering every request with the same words."""

    def __init__(self, answer: str) -> None:
        """Answer every request with `answer`."""
        self.answer = answer

    def status(self) -> dict:
        """Always ready."""
        return {"state": "ready"}

    def reply(self, message, context, system_prompt=None, max_tokens=None):
        """Answer with `answer`, as from the local model."""
        return self.answer, "test-model"


def long_day(day: str) -> str:
    """A YYYY-MM-DD day as the English facts write it in full, such as "Tue 6 Oct 2026"."""
    shown = date.fromisoformat(day)
    return f"{shown:%a} {shown.day} {shown:%b} {shown.year}"


def short_day(day: str) -> str:
    """A YYYY-MM-DD day as the English facts write it short, such as "6 Oct"."""
    shown = date.fromisoformat(day)
    return f"{shown.day} {shown:%b}"


def zh_day(day: str) -> str:
    """A YYYY-MM-DD day as the Chinese facts write it, such as "10月6日"."""
    shown = date.fromisoformat(day)
    return f"{shown.month}月{shown.day}日"


class QuestionTests(unittest.TestCase):
    def test_a_question_about_what_the_user_did_is_told_from_a_report_or_a_request(self):
        for message in ("How much time did I spend on Review last week?", "Did I do Stretch yesterday?",
                        "How often did I skip Stretch?", "When did I last do Review?", "What did I do in September?",
                        "When was I tired?", "Which days was I worn out?",
                        "上周我做了什么？", "我上周花了多少时间学西班牙语", "上次复习是什么时候"):
            self.assertTrue(asks_records(message), message)
        for message in ("I skipped Review yesterday", "Move Review to 3pm", "What will I learn today?",
                        "How do repeats work?", "Remember that I study best in the morning",
                        "What did I note about my sleep?", "What did I write about protecting my sleep?",
                        "我的 sleep 笔记写了什么？"):
            self.assertFalse(asks_records(message), message)

    def test_a_question_about_days_of_low_or_high_energy_asks_the_records_and_one_about_free_days_doesnt(self):
        for message in ("What days did I feel exhausted last week?", "Was I worn out this week?", "上周我哪几天很累？",
                        "上周我哪几天很累", "我什么时候精力充沛？", "How many days was I drained in September?"):
            self.assertTrue(asks_records(message), message)
        for message in ("我哪天有空？", "I'm drained", "I'm tired, was I supposed to call Sam?", "What days suit a long run?"):
            self.assertFalse(asks_records(message), message)

    def test_a_habit_or_a_plan_about_tiredness_is_no_question_about_past_days(self):
        for message in ("我什么时候累了就休息", "我哪天累了就早点睡", "如果我累了几天就少安排", "When I'm tired I rest",
                        "If I'm drained, which days should I rest?", "Whenever I feel exhausted, what days do I skip?"):
            self.assertFalse(asks_records(message), message)
        self.assertTrue(asks_records("我哪几天累了就没做任务？"), "asked outright, with its question mark")


class PhraseTests(unittest.TestCase):
    def test_ranges_by_their_words(self):
        for message, start, end in (
                ("What did I do yesterday?", "2026-10-13", "2026-10-13"),
                ("What did I do today?", "2026-10-14", "2026-10-14"),
                ("What did I do last week?", "2026-10-05", "2026-10-11"),
                ("What did I do this week?", "2026-10-12", "2026-10-14"),
                ("What did I do last month?", "2026-09-01", "2026-09-30"),
                ("What did I do this month?", "2026-10-01", "2026-10-14"),
                ("What did I do in September?", "2026-09-01", "2026-09-30"),
                ("What did I do in November?", "2025-11-01", "2025-11-30"),
                ("What did I do in the last 10 days?", "2026-10-05", "2026-10-14"),
                ("What did I do since Monday?", "2026-10-12", "2026-10-14"),
                ("昨天我做了什么", "2026-10-13", "2026-10-13"),
                ("前天我做了什么", "2026-10-12", "2026-10-12"),
                ("上周我做了什么", "2026-10-05", "2026-10-11"),
                ("本周我做了什么", "2026-10-12", "2026-10-14"),
                ("上个月我做了什么", "2026-09-01", "2026-09-30"),
                ("九月我做了什么", "2026-09-01", "2026-09-30"),
                ("9月我做了什么", "2026-09-01", "2026-09-30"),
                ("最近10天我做了什么", "2026-10-05", "2026-10-14")):
            found = query(message)
            self.assertEqual((found["start"], found["end"]), (start, end), message)

    def test_a_day_named_outright_alone_or_since(self):
        self.assertEqual(query("What did I do on 3 Oct?", "2026-10-03"), asked("2026-10-03", "2026-10-03"))
        self.assertEqual(query("What did I do since 3 Oct?", "2026-10-03"), asked("2026-10-03", TODAY))
        self.assertEqual(query("10月3日我做了什么", "2026-10-03"), asked("2026-10-03", "2026-10-03"))

    def test_the_task_goal_or_area_it_names_and_what_it_asks(self):
        self.assertEqual(query("How long did Weekly review take last week?"),
                         asked("2026-10-05", "2026-10-11", titles=["Weekly review"]))
        self.assertEqual(query("When was the last time I did Review?"), asked(titles=["Review"], kind="last"))
        self.assertEqual(query("How often did I skip Stretch?"), asked(titles=["Stretch"], kind="count"))
        self.assertEqual(query("How much Spanish did I do in September?"),
                         asked("2026-09-01", "2026-09-30", goal="Spanish to B1"))
        self.assertEqual(query("What did I do in the work area this week?"), asked("2026-10-12", TODAY, area="work"))
        self.assertEqual(query("上个月工作任务做了几次"), asked("2026-09-01", "2026-09-30", area="work", kind="count"))
        # Studying or working names its area too, in Chinese a workday doesn't.
        self.assertEqual(query("我上周花了多少时间学习？"), asked("2026-10-05", "2026-10-11", area="learning"))
        self.assertEqual(query("上周工作了多久"), asked("2026-10-05", "2026-10-11", area="work"))
        self.assertEqual(query("How much did I study last week?"), asked("2026-10-05", "2026-10-11", area="learning"))
        self.assertEqual(query("上周每个工作日做了什么"), asked("2026-10-05", "2026-10-11"))
        self.assertEqual(query("上次做“Stretch”是什么时候"), asked(titles=["Stretch"], kind="last"))

    def test_days_of_low_or_high_energy_by_their_words_whatever_task_they_name(self):
        self.assertEqual(query("Which days was I tired last week?"), asked("2026-10-05", "2026-10-11", energy="low"))
        self.assertEqual(query("When was I tired after Review?"), asked(energy="low"))
        self.assertEqual(query("上周我哪几天很累？"), asked("2026-10-05", "2026-10-11", energy="low"))
        self.assertEqual(query("我什么时候精力充沛？"), asked(energy="high"))
        self.assertEqual(query("How often was I full of energy in September?"), asked("2026-09-01", "2026-09-30", energy="high"))
        # 累计 and 积累, "in all" and "built up", aren't tiredness.
        self.assertEqual(query("我上周累计做了几次Review？"), asked("2026-10-05", "2026-10-11", titles=["Review"], kind="count"))

    def test_nothing_recognised_gives_no_query(self):
        for message in ("How often?", "Which days did I struggle with?"):
            self.assertIsNone(query(message), message)

    def test_a_title_is_named_beside_chinese_words_and_as_a_whole_word_beside_latin_ones(self):
        titles = ["复习", "Review"]
        self.assertEqual(phrase_query("上周复习了几次", TODAY, titles, GOALS)["titles"], ["复习"])
        self.assertEqual(phrase_query("我上周做了几次Review", TODAY, titles, GOALS)["titles"], ["Review"])
        self.assertEqual(phrase_query("How often did I do Reviewing last week?", TODAY, titles, GOALS)["titles"], [])


class ModelQueryTests(unittest.TestCase):
    def search(self, answer: str) -> dict | None:
        """The model's search for a question about Spanish when the model answers `answer`, or None when rejected."""
        return model_query(Answering(answer), "Which days did I struggle with Spanish?", TODAY, "2026-08-01", TITLES, GOALS)

    def test_the_models_search_is_kept_when_every_field_is_valid(self):
        self.assertEqual(self.search('{"from": "2026-09-01", "to": "2026-09-30", "task": "review", "goal": null, "area": null}'),
                         asked("2026-09-01", "2026-09-30", titles=["Review"]))
        self.assertEqual(self.search('{"from": null, "to": null, "task": null, "goal": "Spanish to B1", "area": "learning"}'),
                         asked(goal="Spanish to B1", area="learning"))

    def test_an_invalid_search_is_rejected_whole(self):
        for answer in ('{"from": "2026-09-30", "to": "2026-09-01", "task": null, "goal": null, "area": null}',
                       '{"from": "2026-10-01", "to": "2026-10-20", "task": null, "goal": null, "area": null}',
                       '{"from": "2026-01-01", "to": "2026-01-31", "task": null, "goal": null, "area": null}',
                       '{"from": "September", "to": null, "task": null, "goal": null, "area": null}',
                       '{"from": null, "to": null, "task": null, "goal": null, "area": "sleep"}',
                       '{"from": null, "to": null, "task": "Gardening", "goal": null, "area": null}',
                       '{"from": null, "to": null, "task": null, "goal": "Unknown", "area": null}',
                       '{"from": null, "to": null, "task": null, "goal": null, "area": null}',
                       "Considered: Which days did I struggle with Spanish?"):
            self.assertIsNone(self.search(answer), answer)


class RecordsDay(PatternDay):
    """A fresh account with past days written straight in, and the records' index on its own embedder."""

    def setUp(self):
        """The records' index over the same database, on the concept embedder."""
        super().setUp()
        self.embedder = MeaningEmbedder()
        self.rag = RagService(VectorStore(self.store.path), self.embedder)

    def back(self, days: int) -> str:
        """The ISO date `days` before today."""
        return (date.fromisoformat(self.today) - timedelta(days=days)).isoformat()

    def done(self, title: str, day: str, minutes: int = 60, status: str = "done", start: str = "10:00") -> dict:
        """An hour's task `title` on `day` reported `status`, taking `minutes` from `start` unless skipped; return
        it."""
        item = self.on_day(title, day, start, 60)
        end = f"{10 + (minutes // 60):02d}:{minutes % 60:02d}" if status != "skipped" else None
        self.took(item, status, start if status != "skipped" else None, end, minutes if status != "skipped" else None,
                  end or "10:05")
        return item

    def energy(self, day: str, level: int) -> None:
        """Record an energy reading of `level` at 08:00 on `day`."""
        self.sql("INSERT INTO energy_log (reading_date, level, reading_time, recorded_at) VALUES (?, ?, '08:00', ?)",
                 day, level, f"{day}T08:00:00+00:00")


class DocumentTests(RecordsDay):
    def test_a_document_for_each_task_on_a_day_and_one_for_each_day(self):
        day = self.back(1)
        goal = self.client.post("/api/goals", json={"title": "Spanish to B1", "domain": "learning"}).json()
        lesson = self.done("Lesson 4", day, 75)
        self.sql("UPDATE daily_items SET goal_id = ? WHERE id = ?", goal["id"], lesson["id"])
        for place, title in enumerate(("Regular verbs", "Irregular verbs")):
            self.sql("""INSERT INTO checklist_items (id, pass_id, position, title, ticked_on, created_at)
                        VALUES (?, 'pass', ?, ?, ?, ?)""", f"item-{place}", place, title, lesson["id"], f"{day}T09:00:00+00:00")
        stretch = self.done("Stretch", day, status="skipped", start="16:00")
        self.energy(day, 2)
        self.sql("INSERT INTO day_pauses (pause_date, paused_at, resumed_at) VALUES (?, '13:10', '15:00')", day)
        found = documents(self.store, self.today)
        self.assertEqual(found[f"task:{lesson['id']}"], (day, f"{long_day(day)} · Learn · goal “Spanish to B1” · “Lesson 4” · "
                                                              "Done · took 1 h 15 min of 1 h planned · studied: Regular verbs; Irregular verbs"))
        self.assertEqual(found[f"task:{stretch['id']}"], (day, f"{long_day(day)} · Learn · “Stretch” · Skipped"))
        self.assertEqual(found[f"day:{day}"], (day, f"{long_day(day)} · energy 2.0 of 5, low energy · 2 tasks: 1 done, "
                                                    "1 skipped · paused 13:10–15:00"))
        self.energy(self.back(2), 4)
        self.energy(self.back(3), 3)
        found = documents(self.store, self.today)
        self.assertEqual(found[f"day:{self.back(2)}"][1], f"{long_day(self.back(2))} · energy 4.0 of 5, high energy")
        self.assertEqual(found[f"day:{self.back(3)}"][1], f"{long_day(self.back(3))} · energy 3.0 of 5")

    def test_a_time_to_check_and_a_time_never_kept_are_worded_as_such(self):
        day = self.back(1)
        long = self.done("Review", day, 150)
        old = self.on_day("Old", day, "09:00", 60)
        self.sql("UPDATE daily_items SET completion_status = 'done', status_at = '10:00' WHERE id = ?", old["id"])
        found = documents(self.store, self.today)
        self.assertTrue(found[f"task:{long['id']}"][1].endswith("· Done · time to check"))
        self.assertTrue(found[f"task:{old['id']}"][1].endswith("· Done · no time kept"))


class IndexTests(RecordsDay):
    def vectors(self) -> set[int]:
        """The ids of the record vectors kept."""
        return self.rag.vector_store.vector_ids("record_vectors")

    def test_every_document_is_embedded_in_batches_then_only_what_changes(self):
        items = [self.done("Review", self.back(days)) for days in range(1, BATCH + 6)]
        first = sync(self.store, self.rag, self.today)
        self.assertEqual(first["embedded"], 2 * len(items))
        self.assertTrue(all(len(call) <= BATCH for call in self.embedder.document_calls))
        self.assertEqual(len(self.vectors()), 2 * len(items))
        self.embedder.document_calls.clear()
        self.took(items[0], "partial", "10:00", "10:30", 30, "10:35")
        again = sync(self.store, self.rag, self.today)
        self.assertEqual((again["changed"], again["embedded"]), (2, 2), "the task, and its day's counts")
        self.assertEqual(self.embedder.document_calls, [[documents(self.store, self.today)[f"task:{items[0]['id']}"][1],
                                                         documents(self.store, self.today)[f"day:{self.back(1)}"][1]]])
        self.sql("DELETE FROM daily_items WHERE id = ?", items[1]["id"])
        gone = sync(self.store, self.rag, self.today)
        self.assertEqual(gone["removed"], 2, "the task, and its day with nothing left on it")
        self.assertEqual(len(self.vectors()), 2 * len(items) - 2)

    def test_without_the_embedding_model_the_documents_wait_for_their_vectors(self):
        self.done("Review", self.back(1))
        waiting = RagService(VectorStore(self.store.path), MeaningEmbedder(failing=True))
        self.assertEqual(sync(self.store, waiting, self.today)["embedded"], 0)
        self.assertEqual(self.vectors(), set())
        self.assertEqual(sync(self.store, self.rag, self.today)["embedded"], 2)

    def test_a_stop_leaves_the_rest_for_the_next_sync_and_one_under_way_is_not_waited_for(self):
        for days in range(1, BATCH + 1):
            self.done("Review", self.back(days))
        stop = threading.Event()

        class Stopping(MeaningEmbedder):
            """The concept embedder, asked to stop as it embeds each batch."""

            def embed_documents(inner, texts):
                """Ask the sync to stop, then embed the batch."""
                stop.set()  # Asked to stop while the first batch is embedded.
                return super().embed_documents(texts)

        cut = sync(self.store, RagService(VectorStore(self.store.path), Stopping()), self.today, stop=stop)
        self.assertEqual((cut["embedded"], cut["left"]), (BATCH, BATCH))
        with record_search._SYNCING:
            self.assertIsNone(sync(self.store, self.rag, self.today, wait=False))
        rest = sync(self.store, self.rag, self.today)
        self.assertEqual((rest["embedded"], rest["left"]), (BATCH, 0))

    def test_a_sync_held_to_a_most_embeds_that_many_and_leaves_the_rest_for_the_next(self):
        for days in range(1, BATCH + 1):
            self.done("Review", self.back(days))
        held = sync(self.store, self.rag, self.today, most=BATCH)
        self.assertEqual((held["added"], held["embedded"], held["left"]), (2 * BATCH, BATCH, BATCH))
        self.assertEqual(len(self.vectors()), BATCH)
        self.assertEqual(sync(self.store, self.rag, self.today)["embedded"], BATCH)


class LookUpTests(RecordsDay):
    def test_exact_rows_and_totals_over_the_whole_matching_history_twenty_shown_and_the_rest_counted(self):
        for days in range(1, 26):
            self.done("Review", self.back(days))
        self.done("Stretch", self.back(1))
        found = look_up(self.store, self.rag, "How often did I do Review?", asked(titles=["Review"], kind="count"), self.today)
        self.assertEqual((len(found["rows"]), found["more"]), (ROWS_SHOWN, 5))
        self.assertEqual([row["date"] for row in found["rows"]][:2], [self.back(1), self.back(2)], "newest first")
        self.assertEqual({key: found["totals"][key] for key in ("count", "done", "minutes")}, {"count": 25, "done": 25, "minutes": 1500})
        self.assertEqual(more_line(found, "en"), f"And 5 more, from {short_day(self.back(25))} to {short_day(self.back(21))}: "
                                                 "name a month, a task or an area to narrow it.")
        self.assertIsNone(more_line(look_up(self.store, self.rag, "Did I stretch?", asked(titles=["Stretch"]), self.today), "en"))

    def test_a_range_and_a_goal_narrow_the_rows(self):
        goal = self.client.post("/api/goals", json={"title": "Spanish to B1", "domain": "learning"}).json()
        for days in (2, 9):
            lesson = self.done("Lesson", self.back(days))
            self.sql("UPDATE daily_items SET goal_id = ? WHERE id = ?", goal["id"], lesson["id"])
        self.done("Review", self.back(2))
        found = look_up(self.store, self.rag, "Spanish this week?", asked(self.back(6), self.today, goal="Spanish to B1"), self.today)
        self.assertEqual([(row["title"], row["date"]) for row in found["rows"]], [("Lesson", self.back(2))])

    def test_a_time_to_check_is_marked_and_left_out_of_the_time_and_a_time_never_kept_is_said_so(self):
        self.done("Review", self.back(2), 150)
        self.done("Review", self.back(1), 60)
        old = self.on_day("Review", self.back(3), "09:00", 60)
        self.sql("UPDATE daily_items SET completion_status = 'done', status_at = '10:00' WHERE id = ?", old["id"])
        found = look_up(self.store, self.rag, "Review?", asked(titles=["Review"]), self.today)
        self.assertEqual({key: found["totals"][key] for key in ("count", "minutes", "toCheck", "noTime")},
                         {"count": 3, "minutes": 60, "toCheck": 1, "noTime": 1})

    def test_a_question_by_meaning_alone_is_answered_from_the_records_nearest_it_with_their_days(self):
        self.done("Review", self.back(3))
        self.done("Review", self.back(2))
        self.energy(self.back(3), 2)
        self.energy(self.back(2), 4)
        sync(self.store, self.rag, self.today)
        found = look_up(self.store, self.rag, "When was I tired?", None, self.today)
        self.assertEqual(found["rows"], [])
        self.assertEqual([match["day"] for match in found["matches"] if match["key"].startswith("day:")], [self.back(3)])

    def test_a_question_naming_days_is_matched_by_meaning_on_those_days_alone(self):
        self.done("Review", self.back(2), 30, status="partial")
        self.done("Review", self.back(20), 30, status="partial")
        sync(self.store, self.rag, self.today)
        found = look_up(self.store, self.rag, "Which days did I struggle this week?", asked(self.back(6), self.today), self.today)
        self.assertTrue(found["matches"] or found["rows"])
        self.assertTrue(all(self.back(6) <= match["day"] <= self.today for match in found["matches"]),
                        [match["day"] for match in found["matches"]])

    def test_a_question_naming_a_task_goal_or_area_is_answered_by_its_rows_alone(self):
        struggled = self.done("Review", self.back(3), 30, status="partial")
        self.done("Review", self.back(2))
        self.done("Stretch", self.back(2), status="skipped", start="16:00")
        sync(self.store, self.rag, self.today)
        for query in (asked(titles=["Review"]), asked(area="learning")):
            found = look_up(self.store, self.rag, "Which Review days did I struggle with?", query, self.today)
            self.assertIn(struggled["id"], {row["itemId"] for row in found["rows"]})
            self.assertEqual(found["matches"], [], "nothing outside what it names, which its rows hold whole")

    def test_rows_and_the_days_near_the_question_each_once(self):
        self.done("Review", self.back(3), 30, status="partial")
        self.energy(self.back(3), 2)
        sync(self.store, self.rag, self.today)
        found = look_up(self.store, self.rag, "Was I worn out this week?", asked(self.back(6), self.today), self.today)
        self.assertEqual([row["date"] for row in found["rows"]], [self.back(3)])
        self.assertEqual([match["key"] for match in found["matches"]], [f"day:{self.back(3)}"], "a task in the rows isn't matched again")

    def test_days_of_low_or_high_energy_are_the_rows_newest_first(self):
        self.done("Review", self.back(3))
        self.energy(self.back(3), 2)
        self.energy(self.back(5), 1)
        self.energy(self.back(5), 2)
        self.energy(self.back(4), 3)
        self.energy(self.back(2), 4)
        found = look_up(self.store, self.rag, "When was I tired?", asked(energy="low"), self.today)
        self.assertEqual([day["date"] for day in found["days"]], [self.back(3), self.back(5)])
        self.assertEqual((found["rows"], found["matches"], found["totals"]["count"]), ([], [], 2))
        found = look_up(self.store, self.rag, "Was I full of energy?", asked(self.back(3), self.today, energy="high"), self.today)
        self.assertEqual([day["date"] for day in found["days"]], [self.back(2)])

    def test_a_reading_from_before_any_task_was_recorded_counts_too(self):
        self.energy(self.back(40), 1)
        self.done("Review", self.back(3))
        self.energy(self.back(3), 2)
        found = look_up(self.store, self.rag, "When was I tired?", asked(energy="low"), self.today)
        self.assertEqual([day["date"] for day in found["days"]], [self.back(3), self.back(40)])

    def test_nothing_matches(self):
        self.done("Review", self.back(1))
        sync(self.store, self.rag, self.today)
        found = look_up(self.store, self.rag, "When did I go sailing?", asked(titles=["Sailing"]), self.today)
        self.assertEqual((found["rows"], found["matches"]), ([], []))
        self.assertEqual(facts(found, "en"), "")
        self.assertEqual(nothing_line("en"), "Nothing in your records matches that.")
        self.assertEqual(nothing_line("zh"), "你的记录中没有与此相符的内容。")


class CitationTests(RecordsDay):
    def test_the_models_own_citations_are_left_out_whatever_their_day(self):
        answer = (f"You did it.\nFrom your records: {short_day(self.back(1))}, Review, Done, 1 h; {short_day(self.back(40))}, Gym\n"
                  "来自你的记录：10月3日，复习，已完成")
        self.assertEqual(without_citations(answer), "You did it.")

    def test_the_facts_total_the_matches_and_cite_each_row_newest_first_then_say_how_many_more(self):
        for days in range(1, 26):
            self.done("Review", self.back(days))
        found = look_up(self.store, self.rag, "How often did I do Review?", asked(titles=["Review"], kind="count"), self.today)
        lines = facts(found, "en").split("\n")
        self.assertEqual(lines[0], f"“Review” from {short_day(self.back(25))} to {short_day(self.back(1))}: 25 times, 25 done; "
                                   "25 h counted.")
        self.assertEqual(lines[1:3], [f"From your records: {short_day(self.back(1))}, Review, Done, 1 h",
                                      f"From your records: {short_day(self.back(2))}, Review, Done, 1 h"])
        self.assertEqual(len([line for line in lines if line.startswith("From your records: ")]), ROWS_SHOWN)
        self.assertEqual(lines[-1], more_line(found, "en"))

    def test_the_facts_for_a_range_a_time_to_check_and_a_time_never_kept(self):
        self.done("Review", self.back(2), 150)
        self.done("Review", self.back(1), 60)
        old = self.on_day("Review", self.back(3), "09:00", 60)
        self.sql("UPDATE daily_items SET completion_status = 'done', status_at = '10:00' WHERE id = ?", old["id"])
        found = look_up(self.store, self.rag, "Review?", asked(self.back(6), self.today), self.today)
        words = facts(found, "en")
        self.assertTrue(words.startswith(f"Your tasks from {short_day(self.back(6))} to {short_day(self.today)}: 3 tasks, 3 done; "
                                         "1 h counted; 1 time to check, left out until confirmed; 1 from before times were kept, "
                                         "with no time."), words)
        self.assertIn(f"From your records: {short_day(self.back(2))}, Review, Done, time to check", words)
        self.assertIn(f"From your records: {short_day(self.back(3))}, Review, Done, no time kept", words)

    def test_the_last_time_is_one_row(self):
        for days in (1, 5):
            self.done("Review", self.back(days), 75)
        found = look_up(self.store, self.rag, "When did I last do Review?", asked(titles=["Review"], kind="last"), self.today)
        self.assertEqual(facts(found, "en"), f"“Review” was last on {short_day(self.back(1))}.\n"
                                             f"From your records: {short_day(self.back(1))}, Review, Done, 1 h 15 min")

    def test_a_question_by_meaning_alone_cites_the_records_nearest_it(self):
        self.done("Review", self.back(3))
        self.energy(self.back(3), 2)
        sync(self.store, self.rag, self.today)
        found = look_up(self.store, self.rag, "When was I tired?", None, self.today)
        lines = facts(found, "en").split("\n")
        self.assertEqual(lines[:2], ["Nearest your question in your records:",
                                     f"From your records: {short_day(self.back(3))}, energy 2.0 of 5; 1 task: 1 done"])

    def test_the_records_near_a_question_are_cited_as_its_rows_are_in_its_language(self):
        self.done("Review", self.back(3), 30, status="partial")
        self.energy(self.back(3), 2)
        self.sql("INSERT INTO day_pauses (pause_date, paused_at, resumed_at) VALUES (?, '13:10', '15:00')", self.back(3))
        self.sql("INSERT INTO day_pauses (pause_date, paused_at, resumed_at) VALUES (?, '17:00', NULL)", self.back(3))
        sync(self.store, self.rag, self.today)
        found = look_up(self.store, self.rag, "When did I struggle and feel tired?", None, self.today)
        shown = date.fromisoformat(self.back(3))
        self.assertEqual(facts(found, "en").split("\n"), [
            "Nearest your question in your records:",
            f"From your records: {short_day(self.back(3))}, energy 2.0 of 5; 1 task: 1 partly done; paused 13:10–15:00, "
            "from 17:00",
            f"From your records: {short_day(self.back(3))}, Review, Partly done, 30 min"])
        self.assertEqual(facts(found, "zh").split("\n"), [
            "你的记录中与问题最接近的：",
            f"来自你的记录：{shown.month}月{shown.day}日，精力 2.0/5；1 项任务：1 项部分完成；暂停 13:10–15:00，17:00 起",
            f"来自你的记录：{shown.month}月{shown.day}日，Review，部分完成，30 分钟"])
        found = look_up(self.store, self.rag, "Was I worn out this week?", asked(self.back(6), self.today), self.today)
        self.assertEqual(facts(found, "en").split("\n")[1:], [
            f"From your records: {short_day(self.back(3))}, Review, Partly done, 30 min", "Also near your question:",
            f"From your records: {short_day(self.back(3))}, energy 2.0 of 5; 1 task: 1 partly done; paused 13:10–15:00, "
            "from 17:00"])

    def test_days_of_low_energy_are_cited_with_what_each_held(self):
        self.done("Review", self.back(3), 30, status="partial")
        self.energy(self.back(3), 2)
        self.energy(self.back(5), 1)
        found = look_up(self.store, self.rag, "When was I tired?", asked(energy="low"), self.today)
        self.assertEqual(facts(found, "en").split("\n"), [
            f"Days of low energy from {short_day(self.back(5))} to {short_day(self.back(3))}: 2 days.",
            f"From your records: {short_day(self.back(3))}, energy 2.0 of 5; 1 task: 1 partly done",
            f"From your records: {short_day(self.back(5))}, energy 1.0 of 5"])
        self.assertEqual(facts(found, "zh").split("\n"), [
            f"精力低的日子（{zh_day(self.back(5))}至{zh_day(self.back(3))}）：共 2 天。",
            f"来自你的记录：{zh_day(self.back(3))}，精力 2.0/5；1 项任务：1 项部分完成",
            f"来自你的记录：{zh_day(self.back(5))}，精力 1.0/5"])
        high = look_up(self.store, self.rag, "Was I full of energy?", asked(self.back(6), self.today, energy="high"), self.today)
        self.assertEqual(facts(high, "en"), "")

    def test_more_days_than_shown_say_how_to_narrow_them(self):
        for days in range(1, 26):
            self.energy(self.back(days), 1)
        found = look_up(self.store, self.rag, "When was I tired?", asked(energy="low"), self.today)
        self.assertEqual((len(found["days"]), found["more"]), (ROWS_SHOWN, 5))
        self.assertEqual(more_line(found, "en"), f"And 5 more days, from {short_day(self.back(25))} to "
                                                 f"{short_day(self.back(21))}: name a month or a week to narrow it.")
        self.assertEqual(more_line(found, "zh"),
                         f"还有 5 天，从{zh_day(self.back(25))}到{zh_day(self.back(21))}：说出月份或哪一周即可缩小范围。")
        self.assertEqual(facts(found, "en").split("\n")[-1], more_line(found, "en"))

    def test_the_facts_in_chinese(self):
        for days in (1, 2):
            self.done("Review", self.back(days), 75)
        found = look_up(self.store, self.rag, "上周复习了几次", asked(self.back(6), self.today, titles=["Review"], kind="count"),
                        self.today)
        self.assertEqual(facts(found, "zh").split("\n")[:2], [
            f"“Review”（{zh_day(self.back(6))}至{zh_day(self.today)}）：共 2 次，2 项已完成；共计 2 小时 30 分。",
            f"来自你的记录：{zh_day(self.back(1))}，Review，已完成，1 小时 15 分"])

    def test_an_area_is_named_by_its_label_in_each_language(self):
        self.done("Review", self.back(1))
        report = self.done("Report", self.back(2))
        self.sql("UPDATE daily_items SET domain = 'work' WHERE id = ?", report["id"])
        for area, english, chinese in (("learning", "Learn tasks", "学习任务"), ("work", "Work tasks", "工作任务")):
            wanted = asked(self.back(6), self.today, area=area, kind="count")
            found = look_up(self.store, self.rag, "How often did I do them?", wanted, self.today)
            self.assertTrue(facts(found, "en").startswith(english), facts(found, "en"))
            self.assertTrue(facts(found, "zh").startswith(chinese), facts(found, "zh"))


if __name__ == "__main__":
    unittest.main()
