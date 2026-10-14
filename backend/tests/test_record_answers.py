import threading
import time
from datetime import date, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app import record_search
from backend.app.main import create_app
from backend.app.record_search import SEARCH_ROLE
from backend.app.retrieval import VectorStore
from backend.tests.test_api import FakeEmbeddingGateway, FakeSpeechGateway
from backend.tests.test_ava_memory import MemoryGateway
from backend.tests.test_record_search import MeaningEmbedder, RecordsDay

AVA = "You are Ava"


class Meanings(MeaningEmbedder, FakeEmbeddingGateway):
    """The concept embedder of the records' tests, with the status and stop the service asks of one."""


class AnswerDay(RecordsDay):
    """A fresh account with past days written straight in, answered by a model that records what it was given."""

    def setUp(self):
        super().setUp()
        self.model = MemoryGateway()
        self.model.scripted[SEARCH_ROLE] = None
        self.embedder = Meanings()
        self.client = TestClient(create_app(database_path=self.path, gateway=self.model, embedding_gateway=self.embedder,
                                            speech_gateway=FakeSpeechGateway()))

    def chat(self, message, language="en", day=None):
        reply = self.client.post("/api/chat", json={"date": day or self.today, "message": message, "language": language})
        self.assertEqual(reply.status_code, 200, reply.text)
        return reply.json()

    def avas(self):
        """What Ava's own prompts were given, in order."""
        return [call for call in self.model.calls if (call["systemPrompt"] or "").startswith(AVA)]

    def roles(self):
        """Every other prompt the model was asked."""
        return [call["systemPrompt"] for call in self.model.calls if not (call["systemPrompt"] or "").startswith(AVA)]

    def last_week(self, place: int) -> str:
        """A day of last week, Monday being 0."""
        monday = date.fromisoformat(self.today) - timedelta(days=date.fromisoformat(self.today).weekday() + 7)
        return (monday + timedelta(days=place)).isoformat()

    def short(self, day: str) -> str:
        shown = date.fromisoformat(day)
        return f"{shown.day} {shown:%b}"


class RecordQuestionTests(AnswerDay):
    def test_a_question_about_what_the_user_did_is_answered_by_the_service_from_the_records_alone(self):
        for place in (0, 2, 4):
            self.done("Review", self.last_week(place), 75)
        self.done("Stretch", self.last_week(1), status="skipped")
        self.model.answer = "Last week you spent 25 h on Review."
        reply = self.chat("How much time did I spend on Review last week?")
        message = reply["assistantMessage"]
        self.assertEqual((message["mode"], message["model_mode"], reply["proposedAction"], reply["agentRoute"]),
                         ("ask", "records", None, []))
        monday, sunday = self.short(self.last_week(0)), self.short(self.last_week(6))
        self.assertEqual(message["content"].split("\n"), [
            f"“Review” from {monday} to {sunday}: 3 tasks, 3 done; 3 h 45 min counted.",
            *(f"From your records: {self.short(self.last_week(place))}, Review, Done, 1 h 15 min" for place in (4, 2, 0))])
        # Even one naming an area: neither Ava's model nor any other prompt reads it, and nothing is offered or changed.
        self.chat("How often did I skip life tasks last week?")
        self.assertEqual((self.avas(), self.roles()), ([], []))

    def test_a_question_about_what_was_said_or_discussed_is_the_models_as_before(self):
        self.done("Review", self.yesterday, 75)
        self.chat("What did I say about Review?")
        self.assertIn("Tasks:", self.avas()[-1]["context"])
        self.assertIn("Library", self.avas()[-1]["context"])
        self.model.answer = "We talked about Review twice."
        reply = self.chat("How often did we discuss Review?")
        self.assertEqual(reply["assistantMessage"]["content"], "We talked about Review twice.")
        self.assertNotEqual(reply["assistantMessage"]["model_mode"], "records")

    def test_asked_when_they_were_tired_the_days_of_low_energy_answer_and_no_energy_card_comes(self):
        self.done("Review", self.back(3), 75)
        self.energy(self.back(3), 2)
        reply = self.chat("When was I tired?")
        self.assertEqual(reply["assistantMessage"]["content"].split("\n"), [
            f"Days of low energy on {self.short(self.back(3))}: 1 day.",
            f"From your records: {self.short(self.back(3))}, energy 2.0 of 5; 1 task: 1 done"])
        reply = self.chat("我哪几天很累", language="zh")
        self.assertTrue(reply["assistantMessage"]["content"].startswith("精力低的日子（"), reply["assistantMessage"]["content"])
        self.assertIsNone(reply["proposedAction"])
        self.assertEqual(self.avas(), [])
        self.assertEqual(self.chat("I'm drained")["proposedAction"]["actionType"], "set_energy", "a feeling said is as before")

    def test_a_question_in_chinese_about_a_past_day_stays_a_question(self):
        self.done("Review", self.yesterday, 75)
        reply = self.chat("我昨天花了多少时间做Review", language="zh")
        self.assertEqual((reply["assistantMessage"]["mode"], reply["proposedAction"]), ("ask", None))
        day = date.fromisoformat(self.yesterday)
        self.assertIn(f"来自你的记录：{day.month}月{day.day}日，Review，已完成，1 小时 15 分", reply["assistantMessage"]["content"])
        self.assertEqual((self.avas(), self.roles()), ([], []))

    def test_the_model_reads_how_they_work_then_rules_notes_and_the_conversation_and_never_the_records(self):
        self.done("Review", self.yesterday, 75)
        self.store.save_memory({"saidOn": self.today, "kind": "rule", "ruleKind": "keep-off", "area": "work",
                                "days": [5, 6], "wording": "No work on weekends"})
        self.store.save_memory({"saidOn": self.today, "kind": "note", "area": "learning",
                                "wording": "I study best in the evening"})
        self.chat("Hello")
        self.chat("What did we talk about yesterday?")
        context = self.avas()[-1]["context"]
        places = [context.index(heading) for heading in ("How the user works", "The user's rules", "The user's notes",
                                                         "Earlier in this conversation")]
        self.assertEqual(places, sorted(places))
        self.assertNotIn("From the user's records", context)
        self.assertNotIn("records an answer rests on", self.avas()[-1]["systemPrompt"])

    def test_the_models_own_citations_of_the_records_are_left_out(self):
        self.done("Review", self.yesterday, 75)
        self.model.answer = f"Focus on Review.\nFrom your records: {self.short(self.yesterday)}, Review, Done, 2 h"
        self.assertEqual(self.chat("What should I focus on this afternoon?")["assistantMessage"]["content"],
                         "Focus on Review.")

    def test_more_rows_than_shown_end_with_how_to_narrow_them(self):
        for days in range(1, 24):
            self.done("Review", self.back(days), 60)
        answer = self.chat("How often did I do Review?")["assistantMessage"]["content"]
        self.assertTrue(answer.startswith(f"“Review” from {self.short(self.back(23))} to {self.short(self.back(1))}: "
                                          "23 times, 23 done; 23 h counted."), answer)
        self.assertTrue(answer.endswith(f"And 3 more, from {self.short(self.back(23))} to {self.short(self.back(21))}: "
                                        "name a month, a task or an area to narrow it."), answer)

    def test_nothing_in_the_records_is_said_plainly(self):
        self.model.answer = "You did a lot last week, about 5 hours of Spanish."
        self.assertEqual(self.chat("What did I do last week?")["assistantMessage"]["content"],
                         "Nothing in your records matches that.")
        self.assertEqual(self.chat("上周我做了什么？", language="zh")["assistantMessage"]["content"],
                         "你的记录中没有与此相符的内容。")

    def test_the_models_search_is_used_when_no_phrase_names_the_records_and_rejected_when_invalid(self):
        goal = self.client.post("/api/goals", json={"title": "Spanish to B1", "domain": "learning"}).json()
        lesson = self.done("Lesson 4", self.back(3), 50, status="partial")
        self.sql("UPDATE daily_items SET goal_id = ? WHERE id = ?", goal["id"], lesson["id"])
        self.model.scripted[SEARCH_ROLE] = {"from": None, "to": None, "task": None, "goal": "Spanish to B1", "area": None}
        answer = self.chat("Which days did I struggle?")["assistantMessage"]["content"]
        self.assertIn(SEARCH_ROLE, self.roles())
        self.assertTrue(answer.startswith(f"Goal “Spanish to B1” on {self.short(self.back(3))}: 1 task, 1 partly done; "
                                          "50 min counted."), answer)
        self.model.scripted[SEARCH_ROLE] = {"from": "2001-01-01", "to": None, "task": None, "goal": None, "area": None}
        answer = self.chat("Which days did I struggle?")["assistantMessage"]["content"]
        self.assertTrue(answer.startswith("Nearest your question in your records:"), answer)
        self.assertEqual(self.avas(), [])

    def test_how_they_work_is_read_with_every_answer_the_model_gives(self):
        self.done("Review", self.yesterday, 75)
        self.chat("What should I focus on this afternoon?")
        context = self.avas()[-1]["context"]
        self.assertIn("How the user works, from their records. All time: 1 task recorded: 1 done.", context)
        self.assertNotIn("From the user's records", context)

    def test_the_records_are_indexed_as_they_are_asked_about_and_an_answer_never_waits_for_an_index_under_way(self):
        self.done("Review", self.yesterday, 75)
        self.chat("When did I last do Review?")
        with self.store.connect() as connection:
            held = connection.execute("SELECT COUNT(*) FROM record_documents").fetchone()[0]
        self.assertEqual(held, len(record_search.documents(self.store, self.today)))
        self.done("Stretch", self.yesterday, 30)
        with record_search._SYNCING:
            reply = []
            asking = threading.Thread(target=lambda: reply.append(self.chat("When did I last do Stretch?")))
            asking.start()
            asking.join(10)
            self.assertFalse(asking.is_alive(), "The answer waited for the index under way.")
        self.assertIn("Stretch, Done, 30 min", reply[0]["assistantMessage"]["content"])

    def test_a_question_embeds_one_batch_of_the_records_at_most_and_leaves_the_rest_to_avas_rounds(self):
        for days in range(1, record_search.BATCH + 1):
            self.done("Review", self.back(days), 30)
        self.chat("When did I last do Review?")
        self.assertEqual(len(VectorStore(self.store.path).vector_ids("record_vectors")), record_search.BATCH)

    def test_without_the_model_the_records_still_answer(self):
        self.done("Review", self.yesterday, 75)
        self.model.state = "off"
        self.model.reply = lambda message, context, system_prompt=None, max_tokens=None: ("The model is off.", "rules")
        answer = self.chat("When did I last do Review?")["assistantMessage"]["content"]
        self.assertEqual(answer, f"“Review” was last on {self.short(self.yesterday)}.\n"
                                 f"From your records: {self.short(self.yesterday)}, Review, Done, 1 h 15 min")


class ServiceTests(AnswerDay):
    def held(self) -> int:
        with self.store.connect() as connection:
            return connection.execute("SELECT COUNT(*) FROM record_documents").fetchone()[0]

    def test_avas_rounds_index_the_records_from_the_start(self):
        self.done("Review", self.yesterday, 75)
        with (patch("backend.app.main.recall.keep"),
              TestClient(create_app(database_path=self.path, gateway=self.model, embedding_gateway=self.embedder,
                                    speech_gateway=FakeSpeechGateway(), day_jobs=True))):
            for _ in range(200):
                if self.held():
                    break
                time.sleep(0.02)
        self.assertEqual(self.held(), 2)
        self.assertEqual(len(VectorStore(self.store.path).vector_ids("record_vectors")), 2)

    def test_settings_memory_shows_how_they_work_in_the_interface_language(self):
        self.done("Review", self.yesterday, 75)
        self.assertEqual(self.client.get("/api/memory").json()["records"],
                         {"allTime": ["1 task recorded: 1 done."], "lastThirty": []})
        self.client.put("/api/interface-language", json={"language": "zh"})
        self.assertEqual(self.client.get("/api/memory").json()["records"],
                         {"allTime": ["记录了 1 项任务：1 项已完成。"], "lastThirty": []})


class RemarkTests(AnswerDay):
    def remarks(self, answer: str) -> list[str]:
        return [line for line in answer.split("\n") if line.startswith("From your records: ")]

    def test_a_length_far_from_the_usual_brings_one_remark_citing_its_records(self):
        for days in (2, 4, 6):
            self.done("Review", self.back(days), 90)
        self.add("Review", "14:00", 60)
        self.model.answer = "Shorter it is.\nFrom your records: Review usually runs long."
        answer = self.chat("Change Review to 45 minutes")["assistantMessage"]["content"]
        self.assertEqual(self.remarks(answer), [
            f"From your records: “Review” took 1 h 30 min on average the last 3 times it was done: "
            f"{self.short(self.back(2))}, 1 h 30 min; {self.short(self.back(4))}, 1 h 30 min; "
            f"{self.short(self.back(6))}, 1 h 30 min."])

    def test_a_length_close_to_the_usual_brings_none(self):
        for days in (2, 4, 6):
            self.done("Review", self.back(days), 50)
        self.add("Review", "14:00", 60)
        self.assertEqual(self.remarks(self.chat("Change Review to 45 minutes")["assistantMessage"]["content"]), [])

    def test_moving_a_task_that_keeps_slipping_says_so_in_chinese(self):
        for days in (1, 2, 3):
            self.done("Stretch", self.back(days), status="skipped", start="10:00")
        self.done("Stretch", self.back(4), 30, start="10:00")
        self.add("Stretch", "10:00", 30)
        answer = self.chat("把 Stretch 移到 10:30", language="zh")["assistantMessage"]["content"]
        days = "；".join(f"{date.fromisoformat(self.back(n)).month}月{date.fromisoformat(self.back(n)).day}日，已跳过"
                        for n in (1, 2, 3))
        self.assertEqual(self.remarks(answer), [])
        self.assertIn(f"来自你的记录：“Stretch”最近 4 次中有 3 次没有完成：{days}。", answer)

    def test_adding_a_task_done_before_names_its_last_time(self):
        self.done("Stretch", self.back(5), 30)
        answer = self.chat("Add Stretch tomorrow at 9am for 30 minutes")["assistantMessage"]["content"]
        self.assertEqual(self.remarks(answer), [f"From your records: “Stretch” was last on {self.short(self.back(5))}: "
                                                "Done, 30 min."])

    def test_a_doubt_from_the_tasks_agent_leaves_the_remark_out(self):
        for days in (2, 3, 4):
            self.done("Review", self.back(days), 90, start="09:00")
        self.store.rebuild_task_profiles()
        self.add("Review", "09:00", 60)
        reply = self.chat("Move Review to 16:00")
        self.assertIsNotNone(reply["proposedAction"])
        self.assertEqual(self.remarks(reply["assistantMessage"]["content"]), [])

    def test_a_question_brings_no_remark(self):
        for days in (2, 4, 6):
            self.done("Review", self.back(days), 90)
        self.add("Review", "14:00", 60)
        self.model.answer = "Review is at 14:00."
        self.assertEqual(self.chat("What is Review about today?")["assistantMessage"]["content"], "Review is at 14:00.")
