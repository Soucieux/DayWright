import json
import math
import tempfile
import unittest
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app import recall
from backend.app.agents import LEARNING, MEMORY_ORDER, SUMMARY, AgentRun, SummaryAgent
from backend.app.conversation import MEMORY_WORDS, _memory_context, _within_budget
from backend.app.database import Database
from backend.app.main import create_app
from backend.app.memory import CHANGE_ROLE, CLASSIFY_ROLE
from backend.app.recall import CONDENSE_ROLE, REPLACE_ROLE
from backend.app.retrieval import EMBEDDING_DIMENSION, RagService, VectorStore
from backend.app.wording import count_words
from backend.tests.test_api import FakeEmbeddingGateway, FakeGateway, FakeSpeechGateway

TODAY = date.today()


def stamp(day: date, hour: int = 12) -> str:
    """A UTC time on a local day, as the database keeps one."""
    return datetime.combine(day, time(hour)).astimezone().astimezone(timezone.utc).isoformat()


class MemoryGateway(FakeGateway):
    """The local model, answering each of memory's own prompts with what a test sets (a value, or a function of the
    message), and any other with `answer`."""

    def __init__(self):
        """Ready, with no answer scripted for any of memory's prompts and none for the rest."""
        super().__init__()
        self.scripted = {CLASSIFY_ROLE: None, CHANGE_ROLE: None, CONDENSE_ROLE: None, REPLACE_ROLE: None}
        self.answer = None
        self.state = "ready"

    def status(self):
        """The fake gateway's status in `state`, running only when ready."""
        return {**super().status(), "state": self.state, "running": self.state == "ready"}

    def reply(self, message, context, system_prompt=None, max_tokens=None):
        """Keep the request; answer one of memory's prompts with its scripted value as JSON ("I'm not sure." when
        none is set), and any other with `answer` or a line naming the message."""
        self.calls.append({"message": message, "context": context, "systemPrompt": system_prompt})
        if system_prompt in self.scripted:
            value = self.scripted[system_prompt]
            value = value(message) if callable(value) else value
            return (json.dumps(value) if value is not None else "I'm not sure.", "test-model")
        return (self.answer or f"Considered: {message}", "test-model")

    def asked(self, role):
        """The requests sent with the system prompt `role`."""
        return [call for call in self.calls if call["systemPrompt"] == role]


class TopicEmbeddings(FakeEmbeddingGateway):
    """Vectors by the topics a text names, so the nearest by meaning are those sharing a topic."""

    TOPICS = ("spanish", "gym", "exam", "piano", "garden", "running", "evening")

    def _vector(self, text):
        """A unit vector spread evenly over the topics `text` names, or on a place of its own when it names none."""
        vector = [0.0] * EMBEDDING_DIMENSION
        hits = [place for place, topic in enumerate(self.TOPICS) if topic in text.lower()] or [len(self.TOPICS)]
        for place in hits:
            vector[place] = 1 / math.sqrt(len(hits))
        return vector


class MemoryApp(unittest.TestCase):
    """DayWright on a throwaway database, early in the day, with the scripted model and topic embeddings."""

    def setUp(self):
        """A client of the service on a throwaway database, the clock at 07:00, with the scripted model, topic
        embeddings and a search service over the same vectors."""
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Database(Path(self.folder.name) / "daywright.sqlite3")
        self.today = TODAY.isoformat()
        clock = patch("backend.app.database.local_time", return_value="07:00")
        clock.start()
        self.addCleanup(clock.stop)
        self.model = MemoryGateway()
        self.embeddings = TopicEmbeddings()
        self.client = TestClient(create_app(database=self.store, gateway=self.model, embedding_gateway=self.embeddings,
                                            speech_gateway=FakeSpeechGateway()))
        self.rag = RagService(VectorStore(self.store.path), self.embeddings)

    def chat(self, message, language="en"):
        """Ava's reply to `message`, sent from today in `language`."""
        reply = self.client.post("/api/chat", json={"date": self.today, "message": message, "language": language})
        self.assertEqual(reply.status_code, 200, reply.text)
        return reply.json()

    def decide(self, action, decision="confirmed", **extra):
        """Answer Ava's proposed `action` with `decision` and any `extra` fields; return the answer."""
        decided = self.client.post(f"/api/actions/{action['id']}", json={"decision": decision, **extra})
        self.assertEqual(decided.status_code, 200, decided.text)
        return decided.json()

    def keep(self, **entry):
        """Keep a memory entry said today, with `entry`'s fields over the defaults; return what was kept."""
        return self.store.save_memory({"saidOn": self.today, "wording": "said", **entry})

    def said(self, day: date, role: str, content: str, hour: int = 12) -> str:
        """A message of an earlier day, as the conversation kept it."""
        message_id = f"message_{day.isoformat()}_{hour}_{role}_{len(content)}"
        with self.store.connect() as connection:
            connection.execute("""INSERT INTO conversation_messages (id, thread_id, role, mode, content, created_at, topic_date)
                                  VALUES (?, ?, ?, 'ask', ?, ?, ?)""",
                               (message_id, self.store.thread(), role, content, stamp(day, hour), day.isoformat()))
        return message_id

    def confirmed_card(self, day: date, explanation: str):
        """A card confirmed on an earlier day."""
        action = self.store.propose_action(self.store.thread(), "move_item", {"date": day.isoformat()}, explanation)
        with self.store.connect() as connection:
            connection.execute("UPDATE proposed_actions SET status = 'confirmed', created_at = ? WHERE id = ?",
                               (stamp(day), action["id"]))
            connection.execute("INSERT INTO action_confirmations (id, action_id, decision, decided_at) VALUES (?, ?, 'confirmed', ?)",
                               (f"confirmation_{action['id']}", action["id"], stamp(day, 13)))
        return action

    def context(self):
        """What the model read for Ava's last answer."""
        return next(call for call in reversed(self.model.calls) if call["systemPrompt"] not in self.model.scripted)


class RememberTests(MemoryApp):
    """"Remember that…" brings one card naming Ava; a lasting statement brings her offer; nothing is kept until Confirm."""

    def test_remember_gives_one_card_and_keeps_its_entry_on_confirm(self):
        self.model.scripted[CLASSIFY_ROLE] = {"lasting": True, "kind": "note", "area": "learning"}
        reply = self.chat("Remember that I study best in the evening")
        card = reply["proposedAction"]
        self.assertEqual((card["actionType"], card["payload"]["entry"]["kind"], card["payload"]["offered"]),
                         ("remember", "note", False))
        self.assertEqual(self.store.memory_entries(), [])
        self.decide(card)
        self.assertEqual([entry["wording"] for entry in self.store.memory_entries()], ["I study best in the evening"])

    def test_remember_is_read_before_energy(self):
        self.model.scripted[CLASSIFY_ROLE] = {"lasting": True, "kind": "note", "area": "life"}
        self.assertEqual(self.chat("Remember that I'm tired after 6pm")["proposedAction"]["actionType"], "remember")
        self.assertEqual(self.chat("记住：我晚上很累")["proposedAction"]["actionType"], "remember")

    def test_a_rule_its_words_dont_fill_is_a_note_the_card_can_make_a_rule(self):
        self.model.scripted[CLASSIFY_ROLE] = {"lasting": True, "kind": "rule", "rule": "keep-free"}
        card = self.chat("Keep evenings free")["proposedAction"]
        self.assertEqual((card["payload"]["entry"]["kind"], card["payload"]["missing"]), ("note", ["start", "end", "days"]))
        filled = {**card["payload"]["entry"], "kind": "rule", "ruleKind": "keep-free", "start": "18:00", "end": "21:00",
                  "days": [0, 1, 2, 3, 4]}
        self.decide(card, memory=filled)
        kept = self.store.memory_entries()[0]
        self.assertEqual((kept["kind"], kept["start"], kept["days"]), ("rule", "18:00", [0, 1, 2, 3, 4]))

    def test_a_card_completed_wrongly_is_refused_and_stays(self):
        self.model.scripted[CLASSIFY_ROLE] = {"lasting": True, "kind": "rule", "rule": "keep-free"}
        card = self.chat("Keep evenings free")["proposedAction"]
        refused = self.client.post(f"/api/actions/{card['id']}", json={"decision": "confirmed", "memory": {
            **card["payload"]["entry"], "kind": "rule", "ruleKind": "keep-free", "start": "21:00", "end": "18:00", "days": [0]}})
        self.assertEqual(refused.status_code, 409)
        self.assertEqual(self.store.memory_entries(), [])

    def test_one_already_kept_is_said_in_words_with_no_card(self):
        self.keep(kind="note", area="learning", wording="I study best in the evening")
        self.model.scripted[CLASSIFY_ROLE] = {"lasting": True, "kind": "note", "area": "learning"}
        reply = self.chat("Remember that I study best in the evening")
        self.assertIsNone(reply["proposedAction"])
        self.assertIn("I already remember that", reply["assistantMessage"]["content"])

    def test_a_statement_that_changes_an_entry_updates_it_in_place(self):
        kept = self.keep(kind="rule", ruleKind="keep-off", area="work", days=[5, 6], wording="No work on weekends")
        self.model.scripted[CLASSIFY_ROLE] = {"lasting": True, "kind": "rule", "rule": "keep-off", "area": "work"}
        card = self.chat("Remember: no work on Sundays")["proposedAction"]
        self.assertEqual((card["payload"]["outcome"], card["payload"]["updates"]), ("update", kept["id"]))
        self.decide(card)
        self.assertEqual([(entry["id"], entry["days"]) for entry in self.store.memory_entries()], [(kept["id"], [6])])

    def test_a_lasting_statement_brings_one_offer_and_no_other_card(self):
        self.model.scripted[CLASSIFY_ROLE] = {"lasting": True, "kind": "rule", "rule": "keep-off", "area": "work"}
        reply = self.chat("No work on weekends")
        self.assertEqual((reply["proposedAction"]["actionType"], reply["proposedAction"]["payload"]["offered"]),
                         ("remember", True))
        self.assertEqual(reply["notices"], [])

    def test_a_dismissed_offer_is_never_offered_again(self):
        self.model.scripted[CLASSIFY_ROLE] = {"lasting": True, "kind": "note", "area": "learning"}
        self.decide(self.chat("I always study best in the evening")["proposedAction"], "dismissed")
        self.assertIsNone(self.chat("I always study best in the evening")["proposedAction"])
        # Asked outright, Ava still offers it.
        self.assertEqual(self.chat("Remember that I always study best in the evening")["proposedAction"]["actionType"],
                         "remember")

    def test_a_statement_that_isnt_lasting_is_answered_as_any_other(self):
        self.model.scripted[CLASSIFY_ROLE] = {"lasting": False, "kind": "note"}
        reply = self.chat("I usually skip breakfast")
        self.assertIsNone(reply["proposedAction"])
        self.assertIn("Considered", reply["assistantMessage"]["content"])

    def test_a_rule_kept_through_ava_has_todays_proposed_plans_made_again(self):
        self.store.create_daily_item({"date": self.today, "title": "Read", "detail": "", "domain": "learning",
                                      "startTime": None, "durationMinutes": 60, "constraintKind": "flexible",
                                      "repeatKind": "none"})
        self.client.post("/api/plan/generate", json={"date": self.today})
        self.model.scripted[CLASSIFY_ROLE] = {"lasting": True, "kind": "rule", "rule": "keep-free"}
        self.decide(self.chat("Remember to keep 21:00 to 22:00 free every day")["proposedAction"])
        variants = self.store.bootstrap_day(self.today)["variants"]
        self.assertTrue(variants)
        self.assertTrue(all("planRuleFree" in [note["key"] for note in variant["notes"]] for variant in variants))


class ChangeTests(MemoryApp):
    """Talking can change, end or delete what Ava keeps, on one card; "Forget…" lists exactly what goes."""

    def test_dropping_a_rule_deletes_it_for_good_on_confirm(self):
        rule = self.keep(kind="rule", ruleKind="finish-by", latest="17:00", days=[4], wording="Done by 5pm on Fridays")
        self.model.scripted[CHANGE_ROLE] = {"changes": [{"id": rule["id"], "op": "delete"}]}
        card = self.chat("Drop the Friday rule")["proposedAction"]
        self.assertEqual((card["actionType"], [change["op"] for change in card["payload"]["changes"]]),
                         ("change_memory", ["delete"]))
        self.decide(card)
        self.assertEqual(self.store.memory_entries(), [])

    def test_a_note_that_changed_takes_the_new_words(self):
        note = self.keep(kind="note", area="learning", wording="My exam is on 12 December")
        self.model.scripted[CHANGE_ROLE] = {"changes": [{"id": note["id"], "op": "update"}, {"id": "made-up", "op": "delete"}]}
        card = self.chat("My exam moved to 15 January")["proposedAction"]
        self.assertEqual(len(card["payload"]["changes"]), 1)
        self.decide(card)
        self.assertEqual([entry["wording"] for entry in self.store.memory_entries()], ["My exam moved to 15 January"])

    def test_ending_an_entry_moves_it_to_past(self):
        rule = self.keep(kind="rule", ruleKind="keep-off", area="work", days=[5, 6], wording="No work on weekends")
        self.model.scripted[CHANGE_ROLE] = {"changes": [{"id": rule["id"], "op": "end"}]}
        self.decide(self.chat("The weekend rule no longer holds")["proposedAction"])
        view = self.store.memory_view(self.today)
        self.assertEqual(([entry["id"] for entry in view["past"]], view["rules"]), ([rule["id"]], []))

    def test_a_statement_changing_nothing_kept_is_answered_as_any_other(self):
        self.model.scripted[CHANGE_ROLE] = {"changes": []}
        reply = self.chat("Review moved to 3pm and that is fine")
        self.assertNotEqual((reply["proposedAction"] or {}).get("actionType"), "change_memory")

    def test_forget_lists_exactly_what_goes_and_deletes_it_for_good(self):
        note = self.keep(kind="note", area="life", wording="I go to the gym on Mondays")
        self.keep(kind="note", area="life", wording="I like walks")
        recall._save(self.store, (TODAY - timedelta(days=20)).isoformat(),
                     [("mentioned", "The gym membership renews in March"), ("asked", "What to cook")], [])
        card = self.chat("Forget what I said about the gym")["proposedAction"]
        self.assertEqual(card["actionType"], "forget_memory")
        self.assertEqual(([entry["id"] for entry in card["payload"]["entries"]], [line["text"] for line in card["payload"]["lines"]]),
                         ([note["id"]], ["The gym membership renews in March"]))
        self.decide(card)
        self.assertEqual([entry["wording"] for entry in self.store.memory_entries()], ["I like walks"])
        self.assertEqual([line["text"] for day in recall.summaries(self.store).values() for lines in day.values() for line in lines],
                         ["What to cook"])

    def test_forgetting_what_isnt_kept_says_so(self):
        reply = self.chat("Forget what I said about piano")
        self.assertIsNone(reply["proposedAction"])
        self.assertIn("I keep nothing about “piano”", reply["assistantMessage"]["content"])


class ReadingTests(MemoryApp):
    """Ava reads every rule, the notes (twelve at most, the nearest the question), the last days' chat, and for a
    question about past conversations the summaries that best match it, trusting them in that order."""

    def test_rules_and_notes_reach_ava_in_order_with_their_precedence(self):
        self.keep(kind="rule", ruleKind="keep-free", start="18:00", end="19:00", days=[0, 1, 2, 3, 4], wording="r")
        self.keep(kind="note", area="learning", wording="I study best in the evening")
        self.chat("Any advice for this week?")
        call = self.context()
        self.assertIn(MEMORY_ORDER, call["systemPrompt"])
        self.assertLess(call["context"].index("The user's rules, which plans always obey"),
                        call["context"].index("The user's notes, guidance to weigh"))
        self.assertIn("Rule · Keep free · 18:00–19:00 · Mon–Fri", call["context"])

    def test_twelve_notes_at_most_the_nearest_the_question(self):
        for number in range(14):
            self.keep(kind="note", area="general", wording=f"Plain note {number}")
        self.keep(kind="note", area="learning", wording="Spanish comes first this month")
        self.chat("How should I fit Spanish in?")
        context = self.context()["context"]
        self.assertIn("Spanish comes first this month", context)
        self.assertEqual(context.count("Note · "), 12)

    def test_twelve_or_fewer_notes_are_all_read(self):
        for number in range(12):
            self.keep(kind="note", area="general", wording=f"Plain note {number}")
        self.chat("Anything to keep in mind?")
        self.assertEqual(self.context()["context"].count("Note · "), 12)

    def test_memory_is_held_to_its_budget_summaries_going_first_then_the_earliest_chat_never_a_rule(self):
        rules = [{"kind": "rule", "ruleKind": "keep-off", "area": "work", "days": [5, 6]}]
        notes = [{"kind": "note", "area": "general", "wording": f"Note {number} " + "word " * 30, "saidOn": self.today}
                 for number in range(12)]
        chat = [{"day": self.today, "role": "user", "content": f"Message {number} " + "word " * 35} for number in range(12)]
        talked = [{"day": self.today, "lines": {"mentioned": [{"text": "word " * 20}]}} for _ in range(5)]
        notes_read, chat_read, talked_read = _within_budget(rules, notes, chat, talked)
        self.assertLessEqual(count_words(_memory_context(rules, notes_read, chat_read, talked_read)), MEMORY_WORDS)
        self.assertEqual(talked_read, [])
        self.assertEqual(chat_read, chat[-len(chat_read):], "the earliest messages go, the latest stay")
        self.assertLess(len(chat_read), len(chat))
        self.assertEqual(notes_read, notes, "notes go only once the chat has")
        self.assertIn("Rule · Keep off · Work", _memory_context(rules, [], [], []))

    def test_past_notes_are_not_read(self):
        self.keep(kind="note", area="general", wording="Old news", endsOn=(TODAY - timedelta(days=1)).isoformat(),
                  saidOn=(TODAY - timedelta(days=9)).isoformat())
        self.chat("Anything to keep in mind?")
        self.assertNotIn("Old news", self.context()["context"])

    def test_the_last_days_chat_the_latest_six_and_the_earlier_ones_that_match(self):
        self.said(TODAY - timedelta(days=9), "user", "My piano lesson is long gone")
        for hour in range(8, 12):
            self.said(TODAY - timedelta(days=2), "user", f"Ordinary talk {hour}", hour)
        self.said(TODAY - timedelta(days=2), "user", "My piano teacher moved the lesson", 13)
        for hour in range(14, 20):
            self.said(TODAY - timedelta(days=1), "user", f"Recent talk {hour}", hour)
        self.chat("When is my piano lesson?")
        context = self.context()["context"]
        self.assertIn("My piano teacher moved the lesson", context)
        self.assertNotIn("long gone", context)
        self.assertNotIn("Ordinary talk", context)
        self.assertEqual(context.count("Recent talk"), 6)

    def test_a_note_cited_is_kept_and_one_never_given_is_left_out(self):
        self.keep(kind="note", area="learning", wording="I study best in the evening")
        self.model.answer = ("Study after dinner.\nFrom your notes: I study best in the evening\n"
                             "From your notes: I hate Mondays")
        content = self.chat("When should I study?")["assistantMessage"]["content"]
        self.assertIn("From your notes: I study best in the evening", content)
        self.assertNotIn("I hate Mondays", content)

    def test_the_agents_and_summary_read_the_notes(self):
        self.keep(kind="note", area="learning", wording="Spanish comes first this month")
        self.keep(kind="note", area="general", wording="Fewer meetings please")
        self.store.create_daily_item({"date": self.today, "title": "Read", "detail": "", "domain": "learning",
                                      "startTime": None, "durationMinutes": 60, "constraintKind": "flexible",
                                      "repeatKind": "none"})
        self.chat("How does my learning look today?")
        context = self.context()["context"]
        self.assertIn("notes it weighs for Learning: “Spanish comes first this month”", context)
        self.assertIn("notes it weighs for Summary: “Fewer meetings please”", context)

    def test_summary_reads_only_general_notes(self):
        learning = AgentRun(LEARNING, "assessment", "Reviewed")
        run = SummaryAgent().assess([learning], notes=[{"area": "general", "wording": "Rest on Sundays"},
                                                       {"area": "work", "wording": "Fewer calls"}])
        self.assertIn("Rest on Sundays", run.summary)
        self.assertNotIn("Fewer calls", run.summary)
        self.assertEqual(run.spec, SUMMARY)


class SummaryTests(MemoryApp):
    """Each day over is condensed into a short summary; the full text goes after seven days, the summary stays."""

    CONDENSED = {"asked": ["What to study first"], "mentioned": ["Piano lesson moved to Thursday"], "open": ["Gift for Anna"],
                 "remember": []}

    def test_a_day_is_condensed_from_its_words_and_its_confirmed_cards(self):
        day = TODAY - timedelta(days=1)
        self.said(day, "user", "hi", 9)
        self.said(day, "user", "My piano lesson moved to Thursday", 10)
        self.said(day, "assistant", "Noted the lesson.\n\nFrom your Library: Piano notes", 11)
        self.confirmed_card(day, "Propose moving “Review” on 2026-10-02 from 09:00 to 10:00, as a fixed task. Confirm this edit.")
        self.model.scripted[CONDENSE_ROLE] = self.CONDENSED
        kept = recall.keep(self.store, self.model, self.rag, self.today)
        self.assertEqual(kept["condensed"], [day.isoformat()])
        read = self.model.asked(CONDENSE_ROLE)[0]["message"]
        self.assertNotIn("You: hi", read)
        self.assertNotIn("Piano notes", read)
        held = recall.summaries(self.store)[day.isoformat()]
        self.assertEqual([line["text"] for line in held["decided"]],
                         ["Confirmed: moving “Review” on 2026-10-02 from 09:00 to 10:00, as a fixed task"])
        self.assertEqual(set(held), {"asked", "mentioned", "open", "decided"})

    def test_a_summary_holds_at_most_80_words(self):
        day = TODAY - timedelta(days=1)
        self.said(day, "user", "A long day of talk")
        self.model.scripted[CONDENSE_ROLE] = {"asked": ["word " * 30] * 3, "mentioned": ["word " * 30] * 3,
                                              "open": ["word " * 30], "remember": []}
        recall.keep(self.store, self.model, self.rag, self.today)
        held = recall.summaries(self.store)[day.isoformat()]
        self.assertLessEqual(sum(count_words(line["text"]) for lines in held.values() for line in lines), 80)

    def test_the_full_text_goes_after_seven_days_and_the_summary_stays(self):
        old, recent_day = TODAY - timedelta(days=8), TODAY - timedelta(days=2)
        message = self.said(old, "user", "My piano lesson moved to Thursday")
        self.said(recent_day, "user", "Hello there, plan my garden")
        with self.store.connect() as connection:
            connection.execute("""INSERT INTO feedback_signals (id, message_id, request_date, task_title, domain, request_kind,
                                  created_at) VALUES ('feedback_1', ?, ?, 'Read', 'learning', 'shorten', ?)""",
                               (message, old.isoformat(), stamp(old)))
        self.model.scripted[CONDENSE_ROLE] = self.CONDENSED
        kept = recall.keep(self.store, self.model, self.rag, self.today)
        self.assertEqual(kept["cleared"], [old.isoformat()])
        self.assertEqual([message["content"] for message in self.store.messages(self.store.thread())],
                         ["Hello there, plan my garden"])
        self.assertIn(old.isoformat(), recall.summaries(self.store))
        self.assertEqual(len(self.store.feedback_memory(self.today)), 1)

    def test_without_the_model_nothing_is_condensed_or_cleared(self):
        old = TODAY - timedelta(days=9)
        self.said(old, "user", "My piano lesson moved to Thursday")
        self.model.state = "unavailable"
        kept = recall.keep(self.store, self.model, self.rag, self.today)
        self.assertEqual((kept["condensed"], kept["cleared"]), ([], []))
        self.assertEqual(len(self.store.messages(self.store.thread())), 1)
        # Back with the model, the day is condensed and then cleared.
        self.model.state = "ready"
        self.model.scripted[CONDENSE_ROLE] = self.CONDENSED
        self.assertEqual(recall.keep(self.store, self.model, self.rag, self.today)["cleared"], [old.isoformat()])

    def test_a_day_of_confirmed_cards_alone_needs_no_model(self):
        day = TODAY - timedelta(days=3)
        self.confirmed_card(day, "Propose moving “Read” to 10:00. Confirm this edit.")
        self.model.state = "unavailable"
        self.assertEqual(recall.keep(self.store, self.model, self.rag, self.today)["condensed"], [day.isoformat()])

    def test_the_first_pass_condenses_every_day_offers_one_card_then_clears(self):
        first, second = TODAY - timedelta(days=20), TODAY - timedelta(days=12)
        self.said(first, "user", "I always study best in the evening")
        self.said(second, "user", "No work on weekends, ever")
        self.model.scripted[CONDENSE_ROLE] = lambda message: {
            "asked": [], "mentioned": ["Study habits"], "open": [],
            "remember": ["I always study best in the evening"] if "evening" in message else ["No work on weekends"]}
        self.model.scripted[CLASSIFY_ROLE] = lambda message: (
            {"lasting": True, "kind": "note", "area": "learning"} if "evening" in message
            else {"lasting": True, "kind": "rule", "rule": "keep-off", "area": "work"})
        kept = recall.keep(self.store, self.model, self.rag, self.today)
        self.assertEqual(kept["condensed"], [first.isoformat(), second.isoformat()])
        card = kept["offer"]
        self.assertEqual((card["actionType"], len(card["payload"]["entries"])), ("review_memory", 2))
        self.assertEqual(sorted(offer["entry"]["saidOn"] for offer in card["payload"]["entries"]),
                         [first.isoformat(), second.isoformat()])
        self.assertEqual([notice["kind"] for notice in self.store.notices()], ["memory-review"])
        self.assertEqual(kept["cleared"], [first.isoformat(), second.isoformat()])
        # Kept ticked, the first is kept; the second, unticked, is never offered again.
        self.decide(card, kept=[0])
        self.assertEqual([entry["wording"] for entry in self.store.memory_entries()], ["I always study best in the evening"])
        self.assertIsNone(recall.keep(self.store, self.model, self.rag, self.today)["offer"])

    def test_a_question_about_past_conversations_reads_the_best_matching_summaries_and_cites_them(self):
        piano, garden = TODAY - timedelta(days=20), TODAY - timedelta(days=30)
        recall._save(self.store, piano.isoformat(), [("mentioned", "Piano lesson moved to Thursday")], [])
        recall._save(self.store, garden.isoformat(), [("mentioned", "Garden needs watering")], [])
        recall.index(self.store, self.rag, self.today)
        shown = f"{piano.day} {piano.strftime('%b')}"
        self.model.answer = (f"On Thursday.\nFrom our conversation on {shown}: the lesson moved\n"
                             "From our conversation on 1 Jan: something else")
        content = self.chat("What did I say about the piano lesson?")["assistantMessage"]["content"]
        context = self.context()["context"]
        self.assertIn("Piano lesson moved to Thursday", context)
        self.assertNotIn("Garden needs watering", context)
        self.assertIn(f"From our conversation on {shown}: the lesson moved", content)
        self.assertNotIn("1 Jan", content)

    def test_a_newer_statement_replaces_the_lines_it_makes_out_of_date(self):
        day = TODAY - timedelta(days=15)
        recall._save(self.store, day.isoformat(), [("mentioned", "My exam is in December")], [])
        recall.index(self.store, self.rag, self.today)
        line = recall.summaries(self.store)[day.isoformat()]["mentioned"][0]
        self.model.scripted[CHANGE_ROLE] = {"changes": []}
        self.model.scripted[CLASSIFY_ROLE] = {"lasting": False}
        self.model.scripted[REPLACE_ROLE] = {"replaces": [line["id"]]}
        content = self.chat("My exam moved to January")["assistantMessage"]["content"]
        self.assertIn("This replaces what you said on", content)
        self.assertNotIn(day.isoformat(), recall.summaries(self.store))
        self.assertEqual(recall.summary_context(self.store, self.rag, "exam"), [])

    def test_the_panel_holds_the_last_seven_days(self):
        self.said(TODAY - timedelta(days=8), "user", "Too old to show")
        self.said(TODAY - timedelta(days=6), "user", "Still in the window")
        shown = [message["content"] for message in self.client.get("/api/bootstrap", params={"date": self.today}).json()["messages"]]
        self.assertEqual(shown, ["Still in the window"])


class ChangeCitationTests(MemoryApp):
    """A change cites only the notes and Library passages that bear on it: a note naming a task it concerns, and passages
    from the sources that task uses; none else."""

    def task(self, title, domain, start="14:00"):
        """Make an hour-long flexible task `title` in `domain` today at `start`; return it."""
        made = self.client.post("/api/daily-items", json={"date": self.today, "title": title, "detail": "", "domain": domain,
                                                          "startTime": start, "durationMinutes": 60, "constraintKind": "flexible",
                                                          "repeatKind": "none"})
        self.assertEqual(made.status_code, 200, made.text)
        return made.json()

    def source(self, title, text):
        """Add a Library note `title` holding `text`; return it."""
        return self.client.post("/api/knowledge/sources", json={"title": title, "sourceType": "note", "text": text}).json()

    def test_a_change_keeps_a_note_naming_its_task_and_leaves_out_one_that_doesnt(self):
        self.task("Gym", "life")
        self.keep(kind="note", area="life", wording="Gym is easier before lunch")
        self.keep(kind="note", area="work", wording="Sam prefers written updates on Fridays")
        self.model.answer = ("Moving it.\nFrom your notes: Gym is easier before lunch\n"
                             "From your notes: Sam prefers written updates on Fridays")
        reply = self.chat("Move Gym to 16:00")
        self.assertIsNotNone(reply["proposedAction"])
        content = reply["assistantMessage"]["content"]
        self.assertIn("From your notes: Gym is easier before lunch", content)
        self.assertNotIn("Sam prefers", content)

    def test_a_change_names_no_library_passage_its_task_doesnt_use(self):
        self.task("Gym", "life")
        self.source("Gym routines", "Gym: warm up for ten minutes, then the circuit.")
        reply = self.chat("Move Gym to 16:00")
        self.assertIsNotNone(reply["proposedAction"])
        self.assertNotIn("From your Library", reply["assistantMessage"]["content"])
        self.assertEqual(reply["retrieval"]["matches"], [])
        asked = self.chat("What do my gym routines say?")["assistantMessage"]["content"]
        self.assertTrue(asked.endswith("From your Library: Gym routines"), "a question still names what it drew on")

    def test_a_change_names_the_library_passages_its_task_uses(self):
        lesson = self.task("Spanish lesson", "learning")
        grammar = self.source("Spanish grammar", "Spanish: the preterite for finished actions.")
        self.source("Spanish films", "Spanish films to watch with subtitles.")
        self.client.post(f"/api/learning-tasks/{lesson['id']}/sources", json={"sourceId": grammar["id"]})
        reply = self.chat("Move Spanish lesson to 16:00")
        self.assertIsNotNone(reply["proposedAction"])
        self.assertTrue(reply["assistantMessage"]["content"].endswith("From your Library: Spanish grammar"),
                        reply["assistantMessage"]["content"])


if __name__ == "__main__":
    unittest.main()
