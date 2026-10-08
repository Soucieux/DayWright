import base64
from contextlib import nullcontext
import json
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from dataclasses import replace
from io import BytesIO
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from docx import Document
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.main import create_app
from backend.app.agents import AgentOrchestrator
from backend.app.database import Database
from backend.app.config import load_settings
from backend.app.local_import import extract_local_file
from backend.app.model_gateway import ModelGateway
from backend.app.plan_choice import CHOICE_REQUEST
from backend.app.retrieval import EMBEDDING_DIMENSION, EmbeddingGateway
from backend.app.speech import SpeechGateway


class FakeGateway:
    def __init__(self):
        self.calls = []

    def status(self):
        return {
            "state": "ready",
            "running": True,
            "runtimeAvailable": True,
            "chatModelAvailable": True,
            "embeddingModelAvailable": True,
            "voiceModelAvailable": True,
            "label": "Test model",
        }

    def reply(self, message, context, system_prompt=None, max_tokens=None):
        self.calls.append({"message": message, "context": context, "systemPrompt": system_prompt})
        return (f"Considered: {message}", "test-model")

    def stop(self):
        return None


class FakeEmbeddingGateway:
    def __init__(self):
        self.document_calls = []
        self.query_calls = []

    def status(self):
        return {
            "state": "ready",
            "running": True,
            "modelAvailable": True,
            "runtimeAvailable": True,
            "label": "Test embedding model",
            "dimensions": EMBEDDING_DIMENSION,
        }

    def _vector(self, text):
        vector = [0.0] * EMBEDDING_DIMENSION
        lowered = text.lower()
        vector[0 if "sleep" in lowered else 1 if "budget" in lowered else 2] = 1.0
        return vector

    def embed_documents(self, texts):
        self.document_calls.append(texts)
        return [self._vector(text) for text in texts]

    def embed_query(self, text):
        self.query_calls.append(text)
        return self._vector(text)

    def stop(self):
        return None


class FakeSpeechGateway:
    def __init__(self):
        self.clips = []

    def status(self):
        return {"state": "available", "modelAvailable": True,
                "runtimeAvailable": True, "label": "Test local Whisper"}

    def transcribe(self, audio):
        self.clips.append(audio)
        return {"text": "Plan a shorter review", "model": "Test local Whisper"}


class Located:
    """A models library with each role's model ready at the path given, and the others not ready."""

    def __init__(self, **paths):
        self.paths = paths

    def path(self, role):
        return self.paths.get(role)


class SpeechRuntimeTests(unittest.TestCase):
    def test_a_speech_model_not_ready_does_not_enable_the_microphone(self):
        status = SpeechGateway(Located()).status()
        self.assertEqual(status["state"], "unavailable")
        self.assertFalse(status["modelAvailable"])


class LocalModelRuntimeTests(unittest.TestCase):
    def assert_private_runtime_launch(self, gateway_class):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            binary = root / "llama-server"
            chat_model = root / "chat.gguf"
            embedding_model = root / "embedding.gguf"
            for path in (binary, chat_model, embedding_model):
                path.write_bytes(b"test")
            settings = replace(
                load_settings(),
                database_path=root / "daywright.sqlite3",
                llama_binary=binary,
            )
            gateway = gateway_class(settings, Located(chat=chat_model, embedding=embedding_model))
            with (
                patch("backend.app.llama_runtime.secrets.token_urlsafe", return_value="private-token"),
                patch("backend.app.llama_runtime.subprocess.Popen") as popen,
                patch("backend.app.llama_runtime.urlopen") as health,
            ):
                popen.return_value.poll.return_value = None
                health.return_value.__enter__.return_value = object()
                self.assertTrue(gateway.start(timeout=0.1)["running"])

            command = popen.call_args.args[0]
            options = popen.call_args.kwargs
            self.assertNotIn("--api-key", command)
            self.assertNotIn("private-token", command)
            self.assertIn("--log-disable", command)
            self.assertEqual(options["env"]["LLAMA_API_KEY"], "private-token")
            self.assertIs(options["stdout"], subprocess.DEVNULL)
            self.assertIs(options["stderr"], subprocess.DEVNULL)
            gateway.stop()

    def test_chat_runtime_keeps_token_out_of_arguments_and_disables_logs(self):
        self.assert_private_runtime_launch(ModelGateway)

    def test_embedding_runtime_keeps_token_out_of_arguments_and_disables_logs(self):
        self.assert_private_runtime_launch(EmbeddingGateway)

    def test_concurrent_starts_wait_for_one_healthy_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            binary = root / "llama-server"
            model = root / "chat.gguf"
            binary.write_bytes(b"test")
            model.write_bytes(b"test")
            gateway = ModelGateway(replace(load_settings(), llama_binary=binary), Located(chat=model))
            health_started = threading.Event()
            release_health = threading.Event()
            second_started = threading.Event()
            second_finished = threading.Event()
            results = []

            def health(*_args, **_kwargs):
                health_started.set()
                self.assertTrue(release_health.wait(1))
                return nullcontext(object())

            def start(second=False):
                if second:
                    second_started.set()
                results.append(gateway.start(timeout=1)["running"])
                if second:
                    second_finished.set()

            with (
                patch("backend.app.llama_runtime.subprocess.Popen") as popen,
                patch("backend.app.llama_runtime.urlopen", side_effect=health),
            ):
                popen.return_value.poll.return_value = None
                first = threading.Thread(target=start)
                first.start()
                self.assertTrue(health_started.wait(1))
                second = threading.Thread(target=start, kwargs={"second": True})
                second.start()
                self.assertTrue(second_started.wait(1))
                self.assertFalse(second_finished.wait(0.05))
                release_health.set()
                first.join(1)
                second.join(1)

            self.assertEqual(results, [True, True])
            self.assertEqual(popen.call_count, 1)
            gateway.stop()

    def test_spawn_failure_stays_available_without_raising(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            binary = root / "llama-server"
            model = root / "chat.gguf"
            binary.write_bytes(b"test")
            model.write_bytes(b"test")
            gateway = ModelGateway(replace(load_settings(), llama_binary=binary), Located(chat=model))
            with patch(
                "backend.app.llama_runtime.subprocess.Popen",
                side_effect=OSError("cannot execute"),
            ):
                status = gateway.start(timeout=0.1)
            self.assertEqual(status["state"], "available")
            self.assertFalse(status["running"])


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        test_path = Path(self.temp_dir.name) / "test.sqlite3"
        self.gateway = FakeGateway()
        self.embedding_gateway = FakeEmbeddingGateway()
        self.speech_gateway = FakeSpeechGateway()
        app = create_app(
            database_path=test_path,
            gateway=self.gateway,
            embedding_gateway=self.embedding_gateway,
            speech_gateway=self.speech_gateway,
        )
        self.client = TestClient(app)
        self.today = date.today().isoformat()
        self.month = self.today[:7]
        self.yesterday = (date.today() - timedelta(days=1)).isoformat()
        # Explicit isolated prototype fixture for legacy-plan tests, never a runtime default.
        fixture = Database(test_path)
        with fixture.connect() as connection:
            fixture._seed_day(connection, self.today)
        self.day = self.client.get("/api/bootstrap", params={"date": self.today}).json()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_voice_receives_only_bounded_local_wav_and_returns_editable_text(self):
        self.assertEqual(self.day["voice"]["state"], "available")
        refused = self.client.post("/api/voice/transcribe", content=b"private audio",
                                   headers={"content-type": "audio/webm"})
        self.assertEqual(refused.status_code, 415)
        large = self.client.post("/api/voice/transcribe", content=b"A" * 2_000_001,
                                 headers={"content-type": "audio/wav"})
        self.assertEqual(large.status_code, 413)
        clip = self.client.post("/api/voice/transcribe", content=b"short wav clip",
                                headers={"content-type": "audio/wav"})
        self.assertEqual(clip.status_code, 200)
        self.assertEqual(clip.json()["text"], "Plan a shorter review")
        self.assertEqual(self.speech_gateway.clips, [b"short wav clip"])

    def test_local_file_import_supports_markdown_and_word_but_rejects_unsupported_or_scanned(self):
        filename = base64.b64encode("learn.md".encode()).decode()
        source = self.client.post("/api/knowledge/import", content=b"# Learning\nFrench grammar notes",
                                  headers={"Content-Type": "application/octet-stream",
                                           "X-DayWright-Filename": filename, "X-DayWright-Area": "learning"})
        self.assertEqual(source.status_code, 200)
        self.assertEqual(source.json()["sourceType"], "document")
        self.assertTrue(source.json()["title"].startswith("learn.md · "))
        self.assertEqual(self.client.post("/api/knowledge/search", json={
            "query": "French grammar"}).json()["status"], "ready")
        revised = self.client.post("/api/knowledge/import", content=b"# Learning\nFrench review v2",
                                   headers={"Content-Type": "application/octet-stream",
                                            "X-DayWright-Filename": filename, "X-DayWright-Area": "learning"})
        self.assertEqual(revised.status_code, 200)
        self.assertNotEqual(revised.json()["id"], source.json()["id"])

        word = Document()
        word.add_paragraph("Learning reflections")
        word.add_table(rows=1, cols=1).cell(0, 0).text = "Keep review blocks short"
        buffer = BytesIO()
        word.save(buffer)
        title, text = extract_local_file("review.docx", buffer.getvalue())
        self.assertEqual(title, "review.docx")
        self.assertIn("Keep review blocks short", text)

        writer = PdfWriter()
        page = writer.add_blank_page(width=100, height=100)
        content = DecodedStreamObject()
        content.set_data(b"BT /F1 12 Tf 20 70 Td (French lesson) Tj ET")
        page[NameObject("/Contents")] = writer._add_object(content)
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({
                NameObject("/F1"): DictionaryObject({
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type1"),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                }),
            }),
        })
        output = BytesIO()
        writer.write(output)
        self.assertIn("French lesson", extract_local_file("lesson.pdf", output.getvalue())[1])
        blank = PdfWriter()
        blank.add_blank_page(width=100, height=100)
        output = BytesIO()
        blank.write(output)
        with self.assertRaisesRegex(ValueError, "No extractable text"):
            extract_local_file("scanned.pdf", output.getvalue())
        unsupported = self.client.post("/api/knowledge/import", content=b"not a document",
                                       headers={"Content-Type": "application/octet-stream",
                                                "X-DayWright-Filename": base64.b64encode(
                                                    b"old-word.doc").decode(), "X-DayWright-Area": "learning"})
        self.assertEqual(unsupported.status_code, 422)
        self.assertEqual(self.client.post("/api/knowledge/import", content=b"x" * 2_000_001,
                                          headers={"Content-Type": "application/octet-stream",
                                                   "X-DayWright-Filename": filename, "X-DayWright-Area": "learning"}).status_code, 413)
        self.assertEqual(self.client.get("/api/knowledge").json()["rag"]["vectorStore"]["sourceCount"], 2)

    def test_bootstrap_returns_three_persisted_variants(self):
        self.assertEqual(len(self.day["variants"]), 3)
        self.assertGreater(len(self.day["entries"]), 5)
        self.assertIsNone(self.day["confirmedVariantId"])

    def test_bootstrap_discloses_bounded_multi_agent_contract(self):
        agents = {agent["key"]: agent for agent in self.day["agents"]}
        self.assertEqual(set(agents), {"orchestrator", "learning", "life", "work", "project", "summary"})
        self.assertTrue(agents["orchestrator"]["mayProposePlan"])
        self.assertTrue(
            all(not agent["mayProposePlan"] for key, agent in agents.items() if key != "orchestrator")
        )

    def test_confirming_a_variant_is_idempotent_for_the_date(self):
        variant = self.day["variants"][1]
        response = self.client.post(
            "/api/plan/confirm",
            json={"date": self.day["date"], "variantId": variant["id"]},
        )
        self.assertEqual(response.status_code, 200)
        refreshed = self.client.get("/api/bootstrap", params={"date": self.day["date"]}).json()
        self.assertEqual(refreshed["confirmedVariantId"], variant["id"])

    def test_calendar_browses_recorded_days_without_inventing_past_plans(self):
        month = self.client.get("/api/calendar", params={"month": self.month}).json()
        self.assertEqual([day["date"] for day in month["days"]], [self.today])
        empty = self.client.get(
            "/api/bootstrap",
            params={"date": self.yesterday, "create_if_missing": "false"},
        ).json()
        self.assertIsNone(empty["planSetId"])
        self.assertEqual(empty["entries"], [])
        unchanged = self.client.get("/api/calendar", params={"month": self.month}).json()
        self.assertEqual(unchanged["days"], month["days"])

    def test_replacing_a_confirmed_plan_requires_explicit_approval(self):
        balanced, focused = self.day["variants"][:2]
        first = self.client.post(
            "/api/plan/confirm",
            json={"date": self.day["date"], "variantId": balanced["id"]},
        )
        self.assertEqual(first.status_code, 200)
        refused = self.client.post(
            "/api/plan/confirm",
            json={"date": self.day["date"], "variantId": focused["id"]},
        )
        self.assertEqual(refused.status_code, 409)
        current = self.client.get("/api/bootstrap", params={"date": self.day["date"]}).json()
        self.assertEqual(current["confirmedVariantId"], balanced["id"])
        self.assertEqual(current["selectedVariantId"], balanced["id"])
        replaced = self.client.post(
            "/api/plan/confirm",
            json={"date": self.day["date"], "variantId": focused["id"], "replaceExisting": True},
        )
        self.assertEqual(replaced.status_code, 200)
        current = self.client.get("/api/bootstrap", params={"date": self.day["date"]}).json()
        self.assertEqual(current["confirmedVariantId"], focused["id"])
        self.assertEqual(current["selectedVariantId"], focused["id"])
        self.assertEqual(len(current["entries"]), len(self.day["entries"]))

    def test_calendar_summary_and_reporting_follow_current_variant_only(self):
        focused = self.day["variants"][1]
        draft_report = self.client.patch(
            f"/api/entries/{self.day['entries'][0]['id']}", json={"status": "done"},
        )
        self.assertEqual(draft_report.status_code, 409)
        self.client.post(
            "/api/plan/confirm",
            json={"date": self.day["date"], "variantId": focused["id"]},
        )
        focused_day = self.client.get("/api/bootstrap", params={"date": self.day["date"]}).json()
        old_report = self.client.patch(
            f"/api/entries/{self.day['entries'][0]['id']}", json={"status": "done"},
        )
        self.assertEqual(old_report.status_code, 409)
        report = self.client.patch(
            f"/api/entries/{focused_day['entries'][0]['id']}", json={"status": "done"},
        )
        self.assertEqual(report.status_code, 200)
        month = self.client.get("/api/calendar", params={"month": self.month}).json()
        self.assertTrue(month["days"][0]["confirmed"])
        self.assertEqual(month["days"][0]["variantName"], "Focused")
        self.assertEqual(month["days"][0]["doneCount"], 1)

    def test_adjustment_is_a_proposal_until_confirmed(self):
        response = self.client.post(
            "/api/chat",
            json={
                "date": self.day["date"],
                "message": "I am tired; make today gentler",
                "mode": "adjust",
                "selectedVariantId": self.day["selectedVariantId"],
            },
        )
        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["proposedAction"]["payload"]["variantName"], "Gentle")
        self.assertEqual(payload["proposedAction"]["payload"]["proposedBy"], "orchestrator")
        # Being tired is the Life agent's to review; the Orchestrator asks only the agents a request concerns.
        route = [run["agentKey"] for run in payload["agentRoute"]]
        self.assertEqual(route, ["orchestrator", "life", "summary"])
        unchanged = self.client.get("/api/bootstrap", params={"date": self.day["date"]}).json()
        self.assertIsNone(unchanged["confirmedVariantId"])

        decision = self.client.post(
            f"/api/actions/{payload['proposedAction']['id']}",
            json={"decision": "confirmed"},
        )
        self.assertEqual(decision.status_code, 200)
        changed = self.client.get("/api/bootstrap", params={"date": self.day["date"]}).json()
        self.assertEqual(
            changed["confirmedVariantId"], payload["proposedAction"]["payload"]["variantId"]
        )

    def test_chat_plan_replacement_names_current_choice_and_rejects_stale_or_unreviewed_change(self):
        balanced, focused, gentle = self.day["variants"]
        self.client.post("/api/plan/confirm", json={
            "date": self.today, "variantId": balanced["id"]})
        first = self.client.post("/api/chat", json={
            "date": self.today, "message": "I am tired; make today gentler", "mode": "adjust"})
        self.assertEqual(first.status_code, 200)
        proposal = first.json()["proposedAction"]
        self.assertEqual(proposal["payload"]["reviewedFromVariantName"], "Balanced")
        self.assertEqual(proposal["payload"]["reviewedFromVariantId"], balanced["id"])
        self.assertIn("Balanced", proposal["explanation"])
        self.assertIn("Gentle", proposal["explanation"])
        unreviewed = Database(Path(self.temp_dir.name) / "test.sqlite3").propose_action(
            first.json()["threadId"],
            "select_variant", {"date": self.today, "variantId": focused["id"]},
            "Unreviewed plan switch")
        refused = self.client.post(f"/api/actions/{unreviewed['id']}",
                                   json={"decision": "confirmed"})
        self.assertEqual(refused.status_code, 409)
        self.assertEqual(self.client.get("/api/bootstrap", params={"date": self.today}).json()
                         ["confirmedVariantId"], balanced["id"])
        self.client.post("/api/plan/confirm", json={
            "date": self.today, "variantId": focused["id"], "replaceExisting": True})
        stale = self.client.post(f"/api/actions/{proposal['id']}",
                                 json={"decision": "confirmed"})
        self.assertEqual(stale.status_code, 409)
        fresh = self.client.post("/api/chat", json={
            "date": self.today, "message": "I am tired; make today gentler", "mode": "adjust"}).json()
        self.assertEqual(fresh["proposedAction"]["payload"]["reviewedFromVariantName"], "Focused")
        accepted = self.client.post(f"/api/actions/{fresh['proposedAction']['id']}",
                                    json={"decision": "confirmed"})
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(self.client.get("/api/bootstrap", params={"date": self.today}).json()
                         ["confirmedVariantId"], gentle["id"])

    def test_cross_domain_route_is_visible_and_persisted(self):
        response = self.client.post(
            "/api/chat",
            json={
                "date": self.day["date"],
                "message": "Balance French study, sleep, a client meeting, and my project milestone",
                "mode": "ask",
                "selectedVariantId": self.day["selectedVariantId"],
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        route = [run["agentKey"] for run in payload["agentRoute"]]
        self.assertEqual(
            route,
            ["orchestrator", "learning", "life", "work", "project", "summary"],
        )
        self.assertIn("bounded agent reports", self.gateway.calls[-1]["context"].lower())
        self.assertIn("You are Ava, DayWright's planning assistant, speaking for its Orchestrator", self.gateway.calls[-1]["systemPrompt"])

        chinese = self.client.post("/api/chat", json={
            "date": self.day["date"], "message": "请解释今天的计划", "mode": "ask",
            "language": "zh",
        })
        self.assertEqual(chinese.status_code, 200)
        self.assertIn("Respond in Simplified Chinese", self.gateway.calls[-1]["systemPrompt"])

        refreshed = self.client.get(
            "/api/bootstrap", params={"date": self.day["date"]}
        ).json()
        assistant = next(
            message for message in refreshed["messages"] if message["role"] == "assistant"
        )
        self.assertEqual(
            [run["agentKey"] for run in assistant["agentRoute"]], route
        )

    def test_single_domain_request_stays_with_its_agent(self):
        response = self.client.post(
            "/api/chat",
            json={
                "date": self.day["date"],
                "message": "Should I study French longer?",
                "mode": "ask",
                "selectedVariantId": self.day["selectedVariantId"],
            },
        )
        route = [run["agentKey"] for run in response.json()["agentRoute"]]
        self.assertEqual(route, ["orchestrator", "learning", "summary"])

    def test_rag_indexes_retrieves_and_persists_relevant_private_context(self):
        sleep_source = self.client.post(
            "/api/knowledge/sources",
            json={
                "title": "Recovery notes",
                "sourceType": "note",
                "domain": "life",
                "text": "My best sleep routine starts with a screen-free wind-down at 22:30.",
            },
        )
        budget_source = self.client.post(
            "/api/knowledge/sources",
            json={
                "title": "Budget notes",
                "sourceType": "note",
                "domain": "life",
                "text": "Review the grocery budget on Friday before making weekend plans.",
            },
        )
        self.assertEqual(sleep_source.status_code, 200)
        self.assertEqual(budget_source.status_code, 200)

        response = self.client.post(
            "/api/chat",
            json={
                "date": self.day["date"],
                "message": "What did I note about protecting my sleep?",
                "mode": "ask",
                "selectedVariantId": self.day["selectedVariantId"],
            },
        )
        self.assertEqual(response.status_code, 200)
        retrieval = response.json()["retrieval"]
        self.assertEqual(retrieval["status"], "ready")
        self.assertEqual(retrieval["matches"][0]["sourceTitle"], "Recovery notes")
        self.assertIn("screen-free wind-down", self.gateway.calls[-1]["context"])

        knowledge = self.client.get("/api/knowledge").json()
        self.assertEqual(knowledge["rag"]["vectorStore"]["engine"], "sqlite-vec")
        self.assertEqual(knowledge["rag"]["vectorStore"]["sourceCount"], 2)

        refreshed = self.client.get(
            "/api/bootstrap", params={"date": self.day["date"]}
        ).json()
        assistant = next(
            message for message in refreshed["messages"] if message["role"] == "assistant"
        )
        self.assertEqual(
            assistant["retrieval"]["matches"][0]["sourceTitle"], "Recovery notes"
        )

        self.client.post(
            "/api/knowledge/sources",
            json={
                "title": "Recovery notes",
                "sourceType": "note",
                "domain": "life",
                "text": "This revised note replaces the currently indexed source text.",
            },
        )
        history = self.client.get(
            "/api/bootstrap", params={"date": self.day["date"]}
        ).json()
        historical_answer = next(
            message for message in history["messages"] if message["role"] == "assistant"
        )
        self.assertIn(
            "screen-free wind-down",
            historical_answer["retrieval"]["matches"][0]["content"],
        )

    def test_rag_does_not_ground_an_unrelated_question(self):
        self.client.post(
            "/api/knowledge/sources",
            json={
                "title": "Recovery notes",
                "sourceType": "note",
                "domain": "life",
                "text": "My sleep routine starts with a quiet screen-free wind-down.",
            },
        )
        response = self.client.post(
            "/api/knowledge/search",
            json={"query": "What color should I paint a bicycle?", "limit": 4},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "no_match")
        self.assertEqual(response.json()["matches"], [])


class OwnedDayTests(unittest.TestCase):
    """Exercise a genuine empty account, not the opt-in legacy example fixture."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.client = TestClient(create_app(
            database_path=Path(self.temp_dir.name) / "owned.sqlite3",
            gateway=FakeGateway(), embedding_gateway=FakeEmbeddingGateway(),
        ))
        self.today = date.today().isoformat()
        self.yesterday = (date.today() - timedelta(days=1)).isoformat()
        # Plans place untimed tasks only after the current time; start the day early so these
        # tests place them the same way whenever they run.
        clock = patch("backend.app.database._local_time", return_value="07:00")
        clock.start()
        self.addCleanup(clock.stop)

    def tearDown(self):
        self.temp_dir.cleanup()

    def item(self, title, start, domain, goal_id=None, repeat="none"):
        """A task as the form sends it: fixed at `start`, or flexible without one when `start` is None."""
        return {"date": self.today, "title": title, "detail": "User-owned commitment",
                "domain": domain, "startTime": start, "durationMinutes": 60,
                "constraintKind": "fixed" if start else "flexible", "repeatKind": repeat,
                "goalId": goal_id}

    def test_asked_for_another_plan_ava_proposes_the_one_the_area_agents_vote_for(self):
        for title, domain, minutes in (("Read", "learning", 60), ("Notes", "learning", 45), ("Walk", "life", 30)):
            self.client.post("/api/daily-items", json={**self.item(title, None, domain), "durationMinutes": minutes})
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        slugs = {variant["slug"]: variant for variant in plan["variants"]}
        self.assertIn("focused", slugs)
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": slugs["balanced"]["id"]})

        reply = self.client.post("/api/chat", json={"date": self.today, "message": "Switch to a different plan"}).json()

        self.assertEqual(reply["proposedAction"]["payload"]["variantName"], "Deep focus")
        self.assertIn("The area agents' votes favour it: Learning.", reply["assistantMessage"]["content"])

    def test_reporting_a_task_updates_its_area_agents_profile_at_once(self):
        created = self.client.post("/api/daily-items", json=self.item("Stretch", None, "life")).json()
        self.client.put(f"/api/daily-items/{created['id']}", json={**self.item("Stretch", None, "life"), "status": "done"})

        profiles = Database(Path(self.temp_dir.name) / "owned.sqlite3").task_profiles("life")
        self.assertEqual(profiles[("life", "stretch")]["done"], 1)

    def test_a_saved_change_still_succeeds_when_the_profiles_cannot_be_rebuilt(self):
        with patch.object(Database, "rebuild_task_profiles", side_effect=sqlite3.OperationalError("database is locked")):
            saved = self.client.post("/api/daily-items", json=self.item("Stretch", None, "life"))

        self.assertEqual(saved.status_code, 200)
        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        self.assertEqual([item["title"] for item in day["dayItems"]], ["Stretch"])

    def test_profiles_are_built_from_all_earlier_records_when_the_service_starts(self):
        path = Path(self.temp_dir.name) / "owned.sqlite3"
        created = self.client.post("/api/daily-items", json=self.item("Read", None, "learning")).json()
        with sqlite3.connect(path) as connection:
            connection.execute("UPDATE daily_items SET item_date = '2024-01-02', completion_status = 'skipped' WHERE id = ?",
                               (created["id"],))
            connection.execute("DELETE FROM task_profiles")

        TestClient(create_app(database_path=path, gateway=FakeGateway(), embedding_gateway=FakeEmbeddingGateway()))

        self.assertEqual(Database(path).task_profiles()[("learning", "read")]["skipped"], 1)

    def slipping_read(self):
        """Give "Read" a history done at first and lately mostly left unfinished, and put it on today."""
        path = Path(self.temp_dir.name) / "owned.sqlite3"
        statuses = ("done", "done", "done", "partial", "done", "skipped")
        for days_ago, status in zip(range(len(statuses) + 1, 1, -1), statuses):
            created = self.client.post("/api/daily-items", json=self.item("Read", None, "learning")).json()
            with sqlite3.connect(path) as connection:
                connection.execute("UPDATE daily_items SET item_date = ?, completion_status = ? WHERE id = ?",
                                   ((date.today() - timedelta(days=days_ago)).isoformat(), status, created["id"]))
        self.client.post("/api/daily-items", json=self.item("Read", None, "learning"))

    def test_a_goal_runs_from_when_it_was_made_for_as_long_as_its_tasks_take(self):
        goal = self.client.post("/api/goals", json={"title": "Spanish", "domain": "learning"}).json()
        self.assertEqual(goal["startAt"], goal["endAt"])

        self.client.post("/api/daily-items", json={**self.item("Lesson", None, "learning", goal["id"]), "durationMinutes": 45})
        self.client.post("/api/daily-items", json={**self.item("Review", None, "learning", goal["id"]), "durationMinutes": None})

        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        spanish = next(item for item in day["goals"] if item["id"] == goal["id"])
        estimate = next(item for item in day["dayItems"] if item["title"] == "Review")["duration_minutes"]
        self.assertEqual(spanish["startAt"], goal["startAt"])
        self.assertEqual(datetime.fromisoformat(spanish["endAt"]) - datetime.fromisoformat(spanish["startAt"]),
                         timedelta(minutes=45 + estimate))

    def test_a_paused_goals_tasks_are_paused_with_it(self):
        goal = self.client.post("/api/goals", json={"title": "Spanish", "domain": "learning"}).json()
        lesson = self.client.post("/api/daily-items", json=self.item("Lesson", None, "learning", goal["id"])).json()
        self.client.post("/api/daily-items", json=self.item("Walk", None, "life"))
        self.client.put(f"/api/goals/{goal['id']}", json={"title": "Spanish", "status": "paused"})

        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        self.assertEqual(next(item for item in day["dayItems"] if item["title"] == "Lesson")["goalStatus"], "paused")
        reported = self.client.put(f"/api/daily-items/{lesson['id']}", json={
            **self.item("Lesson", None, "learning", goal["id"]), "status": "done"})
        self.assertEqual(reported.status_code, 409)
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        self.assertEqual({entry["title"] for entry in plan["entries"]}, {"Walk"})

    def test_an_edit_that_sends_no_status_keeps_the_reported_one(self):
        read = self.client.post("/api/daily-items", json=self.item("Read", None, "learning")).json()
        self.client.put(f"/api/daily-items/{read['id']}", json={**self.item("Read", None, "learning"), "status": "done"})

        edited = self.client.put(f"/api/daily-items/{read['id']}", json=self.item("Read slowly", None, "learning"))

        self.assertEqual(edited.status_code, 200)
        self.assertEqual((edited.json()["title"], edited.json()["completion_status"]), ("Read slowly", "done"))

    def test_an_edit_to_a_paused_goals_task_keeps_its_reported_status(self):
        goal = self.client.post("/api/goals", json={"title": "Spanish", "domain": "learning"}).json()
        lesson = self.client.post("/api/daily-items", json=self.item("Lesson", None, "learning", goal["id"])).json()
        self.client.put(f"/api/daily-items/{lesson['id']}", json={
            **self.item("Lesson", None, "learning", goal["id"]), "status": "done"})
        self.client.put(f"/api/goals/{goal['id']}", json={"title": "Spanish", "status": "paused"})

        edited = self.client.put(f"/api/daily-items/{lesson['id']}",
                                 json=self.item("Lesson notes", None, "learning", goal["id"]))

        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.json()["completion_status"], "done")

    def test_a_paused_goals_plan_entry_cannot_be_reported(self):
        goal = self.client.post("/api/goals", json={"title": "Spanish", "domain": "learning"}).json()
        self.client.post("/api/daily-items", json=self.item("Lesson", None, "learning", goal["id"]))
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": plan["variants"][0]["id"]})
        entries = self.client.get("/api/bootstrap", params={"date": self.today}).json()["entries"]
        self.client.put(f"/api/goals/{goal['id']}", json={"title": "Spanish", "status": "paused"})

        reported = self.client.patch(f"/api/entries/{entries[0]['id']}", json={"status": "done"})

        self.assertEqual(reported.status_code, 409)
        self.assertIn("paused", reported.json()["detail"])

    def past_read(self, history):
        """Give "Read" earlier days, each (days ago, status, length, start), and put it on today."""
        path = Path(self.temp_dir.name) / "owned.sqlite3"
        for days_ago, status, minutes, start in history:
            created = self.client.post("/api/daily-items", json={**self.item("Read", None, "learning"),
                                                                  "durationMinutes": minutes}).json()
            with sqlite3.connect(path) as connection:
                connection.execute("UPDATE daily_items SET item_date = ?, completion_status = ?, start_time = ? WHERE id = ?",
                                   ((date.today() - timedelta(days=days_ago)).isoformat(), status, start, created["id"]))
        return self.client.post("/api/daily-items", json=self.item("Read", None, "learning")).json()

    def test_moving_a_task_far_from_its_usual_time_brings_its_agents_doubt_with_the_proposal(self):
        self.past_read([(3, "done", 60, "08:30"), (2, "done", 60, "08:45")])

        reply = self.client.post("/api/chat", json={"date": self.today, "message": "Move Read to 21:00"}).json()

        self.assertEqual(reply["proposedAction"]["actionType"], "move_item")
        doubts = [notice for notice in reply["notices"] if notice["kind"] == "doubt-usual-time"]
        self.assertEqual([(notice["agentKey"], notice["values"]["usualStart"], notice["values"]["requested"])
                          for notice in doubts], [("learning", "08:30", "21:00")])
        self.assertGreater(doubts[0]["createdAt"], reply["assistantMessage"]["created_at"])

    def test_a_length_the_task_was_left_partly_done_at_brings_a_doubt(self):
        self.past_read([(4, "partial", 30, None), (3, "partial", 30, None), (2, "done", 60, None)])

        reply = self.client.post("/api/chat", json={"date": self.today, "message": "Set Read to 30 minutes"}).json()

        self.assertEqual(reply["proposedAction"]["actionType"], "set_length")
        self.assertEqual([(notice["kind"], notice["values"]["doneMinutes"]) for notice in reply["notices"]
                          if notice["kind"].startswith("doubt")], [("doubt-too-short", 60)])

    def test_a_change_naming_no_task_asks_which_one_instead_of_switching_plans(self):
        self.client.post("/api/daily-items", json=self.item("Read", None, "learning"))
        self.client.post("/api/plan/generate", json={"date": self.today})

        reply = self.client.post("/api/chat", json={"date": self.today, "message": "Move Gardening to 15:00"}).json()

        self.assertIsNone(reply["proposedAction"])
        self.assertEqual([(notice["kind"], notice["agentKey"], notice["values"]) for notice in reply["notices"]],
                         [("clarify-task", "orchestrator", {"requested": "15:00", "minutes": None})])

    def test_each_message_keeps_the_day_it_was_about(self):
        self.client.post("/api/chat", json={"date": self.yesterday, "message": "How did this day go?"})
        self.client.post("/api/chat", json={"date": self.today, "message": "What should I do next?"})

        messages = self.client.get("/api/bootstrap", params={"date": self.today}).json()["messages"]

        self.assertEqual([(message["role"], message["topicDate"]) for message in messages],
                         [("user", self.yesterday), ("assistant", self.yesterday), ("user", self.today), ("assistant", self.today)])

    def test_a_reply_returns_the_users_own_message_as_saved_so_it_sits_above_the_answer(self):
        reply = self.client.post("/api/chat", json={"date": self.today, "message": "What should I do next?"}).json()

        self.assertEqual(reply["userMessage"]["content"], "What should I do next?")
        self.assertLess(reply["userMessage"]["created_at"], reply["assistantMessage"]["created_at"])

    def test_a_time_that_names_one_of_two_same_named_tasks_picks_it(self):
        self.client.post("/api/daily-items", json=self.item("Walk", "08:00", "life"))
        self.client.post("/api/daily-items", json=self.item("Walk", None, "life"))

        reply = self.client.post("/api/chat", json={"date": self.today, "message": "Move the 08:00 Walk to 17:00"}).json()

        self.assertEqual(reply["proposedAction"]["actionType"], "move_item")
        self.assertEqual(reply["proposedAction"]["payload"]["startTime"], "17:00")
        self.assertIn("from 08:00 to 17:00", reply["proposedAction"]["explanation"])

    def test_a_lighter_day_asked_for_with_a_time_is_still_a_plan_change(self):
        for title in ("Read", "Notes"):
            self.client.post("/api/daily-items", json=self.item(title, None, "learning"))
        self.client.post("/api/plan/generate", json={"date": self.today})

        reply = self.client.post("/api/chat", json={"date": self.today,
                                                    "message": "I'm tired, make the day lighter so I finish by 18:00"}).json()

        self.assertEqual(reply["proposedAction"]["actionType"], "select_variant")
        self.assertFalse(any(notice["kind"] == "clarify-task" for notice in reply["notices"]))

    def test_a_change_to_a_suggestion_waiting_for_accept_asks_to_accept_it_first(self):
        created = self.client.post("/api/daily-items", json=self.item("Read", None, "learning")).json()
        self.client.post("/api/plan/generate", json={"date": self.today})
        with sqlite3.connect(Path(self.temp_dir.name) / "owned.sqlite3") as connection:
            connection.execute("UPDATE daily_items SET acceptance = 'pending' WHERE id = ?", (created["id"],))

        reply = self.client.post("/api/chat", json={"date": self.today, "message": "Move Read to 15:00"}).json()

        self.assertIsNone(reply["proposedAction"])
        self.assertIn("waiting for your Accept", reply["assistantMessage"]["content"])

    def test_a_day_whose_every_task_is_paused_says_why_it_cant_be_planned(self):
        goal = self.client.post("/api/goals", json={"title": "Spanish", "domain": "learning"}).json()
        self.client.post("/api/daily-items", json=self.item("Lesson", None, "learning", goal["id"]))
        self.client.put(f"/api/goals/{goal['id']}", json={"title": "Spanish", "status": "paused"})

        response = self.client.post("/api/plan/generate", json={"date": self.today})

        self.assertEqual(response.status_code, 422)
        self.assertIn("paused", response.json()["detail"])

    def test_a_change_naming_two_tasks_asks_which_one(self):
        self.client.post("/api/daily-items", json=self.item("Walk", "08:00", "life"))
        self.client.post("/api/daily-items", json=self.item("Walk", None, "life"))

        reply = self.client.post("/api/chat", json={"date": self.today, "message": "Move Walk to 17:00"}).json()

        self.assertIsNone(reply["proposedAction"])
        self.assertEqual([(notice["kind"], notice["agentKey"], notice["values"]) for notice in reply["notices"]],
                         [("clarify-which", "life", {"tasks": [{"title": "Walk", "start": "08:00"},
                                                               {"title": "Walk", "start": None}]})])

    def test_a_task_that_keeps_slipping_becomes_one_ava_message_a_day(self):
        self.slipping_read()

        self.client.get("/api/bootstrap", params={"date": self.today})
        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()

        slipping = [notice for notice in day["notices"] if notice["kind"] == "slipping"]
        self.assertEqual(len(slipping), 1)
        self.assertEqual((slipping[0]["agentKey"], slipping[0]["date"], slipping[0]["values"]),
                         ("learning", self.today, {"taskTitle": "Read", "unfinished": 2, "latest": 3}))
        self.assertIsNone(slipping[0]["readAt"])
        self.assertEqual(day["unreadNotices"], len(day["notices"]))

    def test_opening_ava_marks_its_messages_read(self):
        self.slipping_read()
        self.client.get("/api/bootstrap", params={"date": self.today})

        read = self.client.post("/api/notices/read")

        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.json()["unreadNotices"], 0)
        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        self.assertEqual(day["unreadNotices"], 0)
        self.assertTrue(all(notice["readAt"] for notice in day["notices"]))

    def test_messages_already_posted_today_are_not_written_again(self):
        path = Path(self.temp_dir.name) / "owned.sqlite3"
        store = Database(path)
        issue = {"issueKey": "slipping:learning:read", "agent": "learning", "kind": "slipping", "values": {}}
        store.post_notices(self.today, [issue])
        with sqlite3.connect(path) as writer:
            writer.execute("BEGIN IMMEDIATE")
            store.post_notices(self.today, [issue])  # Would wait on the writer's lock if it wrote.
            writer.rollback()
        self.assertEqual(len(store.notices()), 1)

    def test_today_opens_and_tasks_save_even_when_messages_cannot_be_posted(self):
        with patch.object(Database, "post_notices", side_effect=sqlite3.OperationalError("database is locked")):
            self.slipping_read()
            opened = self.client.get("/api/bootstrap", params={"date": self.today})

        self.assertEqual(opened.status_code, 200)
        self.assertEqual(opened.json()["unreadNotices"], 0)
        self.assertEqual([item["title"] for item in opened.json()["dayItems"]], ["Read"])

    def test_opening_another_day_posts_no_message(self):
        self.slipping_read()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        self.client.post("/api/daily-items", json={**self.item("Read", None, "learning"), "date": tomorrow})
        posted = Database(Path(self.temp_dir.name) / "owned.sqlite3").notices()

        day = self.client.get("/api/bootstrap", params={"date": tomorrow}).json()

        self.assertEqual(day["notices"], posted)

    def test_a_change_to_a_task_has_its_agents_look_at_today_again_at_once(self):
        self.slipping_read()

        posted = Database(Path(self.temp_dir.name) / "owned.sqlite3").notices()

        self.assertEqual([(notice["agentKey"], notice["kind"]) for notice in posted], [("learning", "slipping")])

    def test_a_change_reaches_only_the_area_agents_of_its_task(self):
        path = Path(self.temp_dir.name) / "owned.sqlite3"
        self.done_yesterday("Morning chess")
        walk = self.client.post("/api/daily-items", json=self.item("Walk", "17:00", "life")).json()
        with sqlite3.connect(path) as connection:
            # Written directly, so only a rebuild of Life's profiles would see it.
            connection.execute("UPDATE daily_items SET item_date = ?, completion_status = 'done' WHERE id = ?",
                               (self.yesterday, walk["id"]))

        self.client.post("/api/daily-items", json=self.item("Piano", "16:00", "learning"))
        self.assertNotIn(("life", "walk"), Database(path).task_profiles())
        self.client.post("/api/daily-items", json=self.item("Stretch", "20:00", "life"))
        self.assertEqual(Database(path).task_profiles()[("life", "walk")]["done"], 1)

    def test_pausing_a_goal_reaches_its_area_agent_and_renaming_it_only_summary(self):
        path = Path(self.temp_dir.name) / "owned.sqlite3"
        goal = self.client.post("/api/goals", json={"title": "Chess", "domain": "learning"}).json()
        # Written into the past directly, so only a rebuild of Learning's profiles would see it.
        self.done_yesterday("Morning chess")

        self.client.put(f"/api/goals/{goal['id']}", json={"title": "Chess openings", "status": "active"})
        self.assertNotIn(("learning", "morning chess"), Database(path).task_profiles())
        self.client.put(f"/api/goals/{goal['id']}", json={"title": "Chess openings", "status": "paused"})
        self.assertEqual(Database(path).task_profiles()[("learning", "morning chess")]["done"], 1)

    def test_energy_reported_on_an_earlier_day_asks_for_no_lighter_day_and_no_advice(self):
        path = Path(self.temp_dir.name) / "owned.sqlite3"
        gateway = FakeGateway()
        client = TestClient(create_app(database_path=path, gateway=gateway, embedding_gateway=FakeEmbeddingGateway()))
        client.post("/api/daily-items", json=self.item("Walk", None, "life"))
        client.post("/api/daily-items", json=self.item("Read", None, "learning"))
        client.put(f"/api/energy/{self.today}", json={"level": 1})
        with sqlite3.connect(path) as connection:
            connection.execute("UPDATE energy_log SET reading_date = ?", ((date.today() - timedelta(days=2)).isoformat(),))

        plan = client.post("/api/plan/generate", json={"date": self.today}).json()

        findings = [finding for run in plan["planRoute"] for finding in run.get("findings") or []]
        self.assertFalse(any(finding.get("lighter") for finding in findings))
        choice = next(json.loads(call["context"]) for call in gateway.calls if call["message"] == CHOICE_REQUEST)
        self.assertFalse(any("energy" in advice for advice in choice["day"]["advice"]))

    def test_wider_summaries_list_the_next_level_down_with_its_own_outcomes_and_advice(self):
        path = Path(self.temp_dir.name) / "owned.sqlite3"
        recorded = [date.today() - timedelta(days=40), date.today() - timedelta(days=1)]
        for day, status in zip(recorded, ("skipped", "partial")):
            created = self.client.post("/api/daily-items", json=self.item("Read", None, "learning")).json()
            with sqlite3.connect(path) as connection:
                connection.execute("UPDATE daily_items SET item_date = ?, completion_status = ? WHERE id = ?",
                                   (day.isoformat(), status, created["id"]))
        self.client.post("/api/daily-items", json=self.item("Walk", "08:00", "life"))

        reports = self.client.post("/api/summaries", params={"date": self.today}).json()["reports"]

        months = sorted({day.strftime("%Y-%m") for day in (*recorded, date.today())}, reverse=True)
        everything = reports["all"]["sections"]
        self.assertEqual([(section["periodKind"], section["periodKey"]) for section in everything],
                         [("month", month) for month in months])
        oldest = everything[-1]
        self.assertEqual(oldest["domains"]["learning"]["skipped"], 1)
        self.assertTrue(oldest["suggestions"])
        self.assertEqual(reports["week"]["sections"][0]["periodKey"], self.today)
        self.assertTrue(all(section["recordedDays"] for section in reports["month"]["sections"]))
        self.assertNotIn("sections", reports["day"])

    def test_summary_all_time_reaches_back_past_the_month_and_is_never_saved(self):
        path = Path(self.temp_dir.name) / "owned.sqlite3"
        old = self.client.post("/api/daily-items", json=self.item("Read", None, "learning")).json()
        with sqlite3.connect(path) as connection:
            connection.execute("UPDATE daily_items SET item_date = ?, completion_status = 'done' WHERE id = ?",
                               ((date.today() - timedelta(days=400)).isoformat(), old["id"]))

        result = self.client.post("/api/summaries", params={"date": self.today}).json()

        everything = result["reports"]["all"]
        self.assertEqual((everything["periodKind"], everything["domains"]["learning"]["done"]), ("all", 1))
        self.assertEqual(result["reports"]["month"]["domains"]["learning"]["scheduled"], 0)
        self.assertIn("agentsView", everything)
        self.assertNotIn("all", result["pool"])
        with sqlite3.connect(path) as connection:
            kinds = {row[0] for row in connection.execute("SELECT period_kind FROM summary_reports")}
        self.assertNotIn("all", kinds)

    def test_an_unused_record_can_be_removed_but_a_confirmed_one_cannot(self):
        keep = self.client.post("/api/daily-items", json=self.item("Dentist", "09:00", "life"))
        mistake = self.client.post("/api/daily-items", json=self.item("Typo task", "11:00", "life"))
        self.assertEqual(mistake.status_code, 200)

        removed = self.client.delete(f"/api/daily-items/{mistake.json()['id']}")
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(removed.json()["title"], "Typo task")
        remaining = self.client.get("/api/bootstrap", params={"date": self.today}).json()["dayItems"]
        self.assertEqual([item["title"] for item in remaining], ["Dentist"])
        self.assertEqual(
            self.client.delete(f"/api/daily-items/{mistake.json()['id']}").status_code, 404
        )

        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        self.assertEqual(self.client.post("/api/plan/confirm", json={
            "date": self.today, "variantId": plan["variants"][0]["id"]}).status_code, 200)
        blocked = self.client.delete(f"/api/daily-items/{keep.json()['id']}")
        self.assertEqual(blocked.status_code, 409)
        still_recorded = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        self.assertEqual([item["title"] for item in still_recorded["dayItems"]], ["Dentist"])

    def test_setting_a_plan_keeps_what_was_already_reported(self):
        walk = self.client.post("/api/daily-items", json=self.item("Walk", "08:00", "life")).json()
        self.client.post("/api/daily-items", json=self.item("Read", "10:00", "learning"))
        reported = self.client.put(f"/api/daily-items/{walk['id']}", json={
            **self.item("Walk", "08:00", "life"), "status": "done"})
        self.assertEqual(reported.status_code, 200)

        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        self.assertEqual(self.client.post("/api/plan/confirm", json={
            "date": self.today, "variantId": plan["variants"][0]["id"]}).status_code, 200)

        entries = self.client.get("/api/bootstrap", params={"date": self.today}).json()["entries"]
        statuses = {entry["title"]: entry["completion_status"] for entry in entries}
        self.assertEqual(statuses["Walk"], "done")
        self.assertEqual(statuses["Read"], "planned")

    def test_tasks_across_dates_list_in_date_and_time_order(self):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        self.client.post("/api/daily-items", json={**self.item("Dentist", "10:00", "life"), "date": tomorrow})
        self.client.post("/api/daily-items", json=self.item("Read", "09:00", "learning"))

        listed = self.client.get("/api/daily-items", params={"start": self.today, "end": tomorrow})
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([(item["date"], item["title"]) for item in listed.json()["items"]],
                         [(self.today, "Read"), (tomorrow, "Dentist")])
        only_today = self.client.get("/api/daily-items", params={"start": self.today, "end": self.today})
        self.assertEqual([item["title"] for item in only_today.json()["items"]], ["Read"])
        self.assertEqual(self.client.get("/api/daily-items", params={
            "start": tomorrow, "end": self.today}).status_code, 422)
        long_ago = (date.today() - timedelta(days=500)).isoformat()
        self.assertEqual(self.client.get("/api/daily-items", params={
            "start": long_ago, "end": self.today}).status_code, 422)

    def test_life_shows_a_repeating_life_task_as_a_habit_of_its_week(self):
        self.client.post("/api/daily-items", json={**self.item("Stretch", None, "life"), "repeatKind": "daily"})

        life = self.client.get("/api/areas/life", params={"date": self.today}).json()

        monday = date.today() - timedelta(days=date.today().weekday())
        self.assertEqual(life["weekStart"], monday.isoformat())
        self.assertEqual([(habit["title"], habit["kind"], habit["doneThisWeek"], habit["streak"])
                          for habit in life["habits"]], [("Stretch", "daily", 0, 0)])

    def test_a_goal_can_be_removed_only_after_its_linked_records(self):
        goal = self.client.post("/api/goals", json={
            "title": "Learn French", "domain": "learning"}).json()
        linked = self.client.post("/api/daily-items", json=self.item(
            "French practice", "09:00", "learning", goal["id"])).json()

        blocked = self.client.delete(f"/api/goals/{goal['id']}")
        self.assertEqual(blocked.status_code, 409)
        self.assertIn("still link", blocked.json()["detail"])

        self.assertEqual(self.client.delete(f"/api/daily-items/{linked['id']}").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/goals/{goal['id']}").status_code, 200)
        self.assertEqual(
            self.client.get("/api/bootstrap", params={"date": self.today}).json()["goals"], []
        )
        self.assertEqual(self.client.delete(f"/api/goals/{goal['id']}").status_code, 404)

    def test_empty_account_and_past_day_are_not_invented(self):
        fresh = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        self.assertIsNone(fresh["planSetId"])
        self.assertEqual(fresh["dayItems"], [])
        self.assertEqual(fresh["goals"], [])
        legacy_flag = self.client.get("/api/bootstrap", params={
            "date": self.today, "create_if_missing": "true"}).json()
        self.assertIsNone(legacy_flag["planSetId"])
        self.assertEqual(self.client.post("/api/plan/generate", json={
            "date": self.today}).status_code, 422)
        self.assertEqual(self.client.get("/api/calendar", params={"month": self.today[:7]}).json()["days"], [])
        past = self.item("Old appointment", "09:00", "life")
        past["date"] = self.yesterday
        self.assertEqual(self.client.post("/api/daily-items", json=past).status_code, 409)
        self.assertEqual(self.client.post("/api/plan/generate", json={"date": self.today}).status_code, 422)

    def test_past_daily_summary_is_frozen_after_first_saved_report(self):
        self.assertEqual(
            self.client.get("/api/summaries", params={"date": self.yesterday}).status_code,
            405,
        )
        earlier = self.client.post("/api/summaries", params={"date": self.yesterday}).json()
        self.assertEqual(earlier["reports"]["day"]["goals"], [])
        self.client.post("/api/goals", json={"title": "New goal today", "domain": "life"})
        refreshed = self.client.post("/api/summaries", params={"date": self.yesterday}).json()
        self.assertEqual(refreshed["reports"]["day"], earlier["reports"]["day"])

    def done_yesterday(self, title):
        """Record a task, then move it to yesterday as done: past days are written there directly."""
        created = self.client.post("/api/daily-items", json=self.item(title, "09:00", "learning")).json()
        with sqlite3.connect(Path(self.temp_dir.name) / "owned.sqlite3") as connection:
            connection.execute("UPDATE daily_items SET item_date = ?, completion_status = 'done' WHERE id = ?",
                               (self.yesterday, created["id"]))
        return created

    def confirm(self, day, message):
        """Ask Ava for a change about a day, and confirm the change it proposes."""
        action = self.chat(day, message)["proposedAction"]
        decided = self.client.post(f"/api/actions/{action['id']}", json={"decision": "confirmed"})
        self.assertEqual(decided.status_code, 200, decided.text)
        return decided.json()

    def test_a_past_task_changes_only_through_ava_and_the_reports_it_is_in_are_made_again(self):
        chess = self.done_yesterday("Morning chess")
        earlier = self.client.post("/api/summaries", params={"date": self.yesterday}).json()["reports"]
        self.assertIn("Morning chess", json.dumps(earlier["day"]))

        direct = self.client.put(f"/api/daily-items/{chess['id']}", json={
            **self.item("Evening chess", "09:00", "learning"), "date": self.yesterday})
        self.assertEqual((direct.status_code, direct.json()["detail"]),
                         (409, "A past task changes only through Ava; ask Ava to change it"))
        self.confirm(self.yesterday, "Rename Morning chess to “Evening chess”")

        edited = Database(Path(self.temp_dir.name) / "owned.sqlite3").daily_item(chess["id"])
        self.assertEqual((edited["title"], edited["completion_status"]), ("Evening chess", "done"))
        later = self.client.post("/api/summaries", params={"date": self.yesterday}).json()["reports"]
        for kind in ("day", "week", "month"):
            self.assertIn("Evening chess", json.dumps(later[kind]), kind)
            self.assertNotIn("Morning chess", json.dumps(later[kind]), kind)

    def test_moving_a_task_off_a_past_day_makes_that_days_report_again(self):
        self.done_yesterday("Morning chess")
        self.client.post("/api/summaries", params={"date": self.yesterday})

        self.confirm(self.yesterday, f"Move Morning chess to {self.today}")

        later = self.client.post("/api/summaries", params={"date": self.yesterday}).json()["reports"]
        self.assertNotIn("Morning chess", json.dumps(later["day"]))

    def test_no_task_is_changed_directly_on_a_past_day_or_moved_onto_one(self):
        today_task = self.client.post("/api/daily-items", json=self.item("Piano", "16:00", "learning")).json()
        past_task = self.done_yesterday("Morning chess")

        onto_past = self.client.put(f"/api/daily-items/{today_task['id']}", json={
            **self.item("Piano", "16:00", "learning"), "date": self.yesterday})
        reported = self.client.put(f"/api/daily-items/{past_task['id']}", json={
            **self.item("Morning chess", "09:00", "learning"), "date": self.yesterday, "status": "skipped"})

        self.assertEqual((onto_past.status_code, reported.status_code), (409, 409))
        store = Database(Path(self.temp_dir.name) / "owned.sqlite3")
        self.assertEqual(store.daily_item(today_task["id"])["date"], self.today)
        self.assertEqual(store.daily_item(past_task["id"])["completion_status"], "done")

    def saved_report_time(self, day):
        """When the day's own report was saved, or None once it has been dropped."""
        with sqlite3.connect(Path(self.temp_dir.name) / "owned.sqlite3") as connection:
            row = connection.execute("SELECT updated_at FROM summary_reports WHERE period_kind = 'day' AND period_key = ?",
                                     (day,)).fetchone()
        return row[0] if row else None

    def test_saving_a_task_without_a_change_keeps_its_days_saved_report(self):
        chess = self.client.post("/api/daily-items", json=self.item("Morning chess", "09:00", "learning")).json()
        self.client.post("/api/summaries", params={"date": self.today})
        saved = self.saved_report_time(self.today)

        unchanged = self.client.put(f"/api/daily-items/{chess['id']}", json=self.item("Morning chess", "09:00", "learning"))

        self.assertEqual(unchanged.status_code, 200)
        self.assertIsNotNone(saved)
        self.assertEqual(self.saved_report_time(self.today), saved)

    def test_moving_a_task_far_from_its_usual_time_on_its_form_brings_its_agents_doubt(self):
        read = self.past_read([(3, "done", 60, "08:30"), (2, "done", 60, "08:45")])

        moved = self.client.put(f"/api/daily-items/{read['id']}", json=self.item("Read", "21:00", "learning"))

        self.assertEqual(moved.status_code, 200)
        notices = self.client.get("/api/bootstrap", params={"date": self.today}).json()["notices"]
        self.assertEqual([(notice["agentKey"], notice["values"]["usualStart"], notice["values"]["requested"])
                          for notice in notices if notice["kind"] == "doubt-usual-time"], [("learning", "08:30", "21:00")])

    def planned_yesterday(self, title, goal_id=None):
        """Record a task, set today's plan with it, then move the day to yesterday: past days are written there directly.

        Returns:
            The task, and the id of the plan set for yesterday.
        """
        created = self.client.post("/api/daily-items", json=self.item(title, None, "learning", goal_id)).json()
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        variant_id = plan["variants"][0]["id"]
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": variant_id})
        with sqlite3.connect(Path(self.temp_dir.name) / "owned.sqlite3") as connection:
            connection.execute("UPDATE daily_items SET item_date = ? WHERE id = ?", (self.yesterday, created["id"]))
            connection.execute("UPDATE plan_sets SET plan_date = ? WHERE plan_date = ?", (self.yesterday, self.today))
            connection.execute("UPDATE daily_confirmations SET plan_date = ? WHERE plan_date = ?", (self.yesterday, self.today))
        return created, variant_id

    def chat(self, day, message):
        return self.client.post("/api/chat", json={"date": day, "message": message}).json()

    def test_ava_changes_a_past_task_only_once_it_is_confirmed_then_hands_it_on(self):
        path = Path(self.temp_dir.name) / "owned.sqlite3"
        chess = self.done_yesterday("Morning chess")
        earlier = self.client.post("/api/summaries", params={"date": self.yesterday}).json()["reports"]["day"]
        self.assertEqual(earlier["domains"]["learning"]["done"], 1)

        reply = self.chat(self.yesterday, "Morning chess was partly done")

        action = reply["proposedAction"]
        self.assertEqual(action["actionType"], "edit_item")
        self.assertEqual(action["payload"]["changes"], {"status": "partial"})
        self.assertEqual(action["payload"]["before"], {"status": "done"})
        unchanged = Database(path).daily_item(chess["id"])
        self.assertEqual(unchanged["completion_status"], "done")

        decided = self.client.post(f"/api/actions/{action['id']}", json={"decision": "confirmed"})

        self.assertEqual(decided.status_code, 200)
        saved = Database(path).daily_item(chess["id"])
        self.assertEqual((saved["duration_minutes"], saved["completion_status"], saved["date"]), (60, "partial", self.yesterday))
        later = self.client.post("/api/summaries", params={"date": self.yesterday}).json()["reports"]["day"]
        self.assertEqual((later["domains"]["learning"]["done"], later["domains"]["learning"]["partial"]), (0, 1))
        self.assertEqual(Database(path).task_profiles("learning")[("learning", "morning chess")]["partial"], 1)

    def test_a_dismissed_change_to_a_past_task_changes_nothing(self):
        chess = self.done_yesterday("Morning chess")
        action = self.chat(self.yesterday, "Rename Morning chess to “Evening chess”")["proposedAction"]
        self.assertEqual(action["payload"]["changes"], {"title": "Evening chess"})

        self.client.post(f"/api/actions/{action['id']}", json={"decision": "dismissed"})

        self.assertEqual(Database(Path(self.temp_dir.name) / "owned.sqlite3").daily_item(chess["id"])["title"], "Morning chess")

    def test_a_past_task_moved_after_today_goes_back_to_planned(self):
        chess = self.done_yesterday("Morning chess")
        tomorrow = (date.today() + timedelta(days=1)).isoformat()

        action = self.chat(self.yesterday, f"Move Morning chess to {tomorrow}")["proposedAction"]
        self.assertEqual(action["payload"]["changes"], {"date": tomorrow, "status": "planned"})
        self.client.post(f"/api/actions/{action['id']}", json={"decision": "confirmed"})

        moved = Database(Path(self.temp_dir.name) / "owned.sqlite3").daily_item(chess["id"])
        self.assertEqual((moved["date"], moved["completion_status"]), (tomorrow, "planned"))

    def test_ava_proposes_no_move_of_a_past_task_that_would_overlap_another(self):
        self.done_yesterday("Morning chess")
        self.client.post("/api/daily-items", json=self.item("Piano", "11:00", "learning"))

        reply = self.chat(self.yesterday, "Move Morning chess to today at 11:00")

        self.assertIsNone(reply["proposedAction"])
        self.assertIn("“Piano” (11:00–12:00) already takes that time", reply["assistantMessage"]["content"])

    def test_a_confirmed_correction_of_a_past_task_raises_no_doubt(self):
        self.past_read([(3, "done", 60, "08:30"), (2, "done", 60, "08:45")])
        with sqlite3.connect(Path(self.temp_dir.name) / "owned.sqlite3") as connection:
            connection.execute("UPDATE daily_items SET item_date = ?, start_time = '08:30' WHERE item_date = ?",
                               (self.yesterday, self.today))

        action = self.chat(self.yesterday, "Mark Read as skipped")["proposedAction"]
        decided = self.client.post(f"/api/actions/{action['id']}", json={"decision": "confirmed"})

        self.assertEqual(decided.status_code, 200)
        notices = self.client.get("/api/bootstrap", params={"date": self.today}).json()["notices"]
        self.assertEqual([notice for notice in notices if notice["kind"].startswith("doubt-")], [])

    def test_ava_removes_a_past_task_only_once_the_removal_is_confirmed(self):
        path = Path(self.temp_dir.name) / "owned.sqlite3"
        chess = self.done_yesterday("Morning chess")
        self.client.post("/api/summaries", params={"date": self.yesterday})

        action = self.chat(self.yesterday, "Remove Morning chess")["proposedAction"]

        self.assertEqual((action["actionType"], action["payload"]["itemId"]), ("remove_item", chess["id"]))
        self.assertIsNotNone(Database(path).daily_item(chess["id"]))
        decided = self.client.post(f"/api/actions/{action['id']}", json={"decision": "confirmed"})
        self.assertEqual(decided.status_code, 200)
        self.assertIsNone(Database(path).daily_item(chess["id"]))
        later = self.client.post("/api/summaries", params={"date": self.yesterday}).json()["reports"]["day"]
        self.assertNotIn("Morning chess", json.dumps(later))
        self.assertNotIn(("learning", "morning chess"), Database(path).task_profiles("learning"))

    def kept_entries(self, day):
        """The set plan's entries on a day, each its title and the task it still links to."""
        with sqlite3.connect(Path(self.temp_dir.name) / "owned.sqlite3") as connection:
            return connection.execute(
                """SELECT e.title, e.source_item_id FROM plan_entries e
                   JOIN daily_confirmations c ON c.variant_id = e.variant_id WHERE c.plan_date = ?""", (day,)).fetchall()

    def test_ava_removes_a_past_task_its_set_plan_scheduled_and_the_plan_keeps_its_entry(self):
        chess, _ = self.planned_yesterday("Morning chess")

        action = self.chat(self.yesterday, "Remove Morning chess")["proposedAction"]

        self.assertEqual((action["actionType"], action["payload"]["inSetPlan"]), ("remove_item", True))
        self.assertIn("The plan set for that day keeps its entry, as history.", action["explanation"])
        self.client.post(f"/api/actions/{action['id']}", json={"decision": "confirmed"})
        self.assertIsNone(Database(Path(self.temp_dir.name) / "owned.sqlite3").daily_item(chess["id"]))
        self.assertEqual(self.kept_entries(self.yesterday), [("Morning chess", None)])
        entries = self.client.get("/api/bootstrap", params={"date": self.yesterday}).json()["entries"]
        self.assertEqual([(entry["title"], entry["removed"]) for entry in entries], [("Morning chess", True)])

    def test_ava_takes_the_task_the_previous_message_named(self):
        chess = self.done_yesterday("Morning chess")
        self.chat(self.yesterday, "How did Morning chess go?")

        removal = self.chat(self.yesterday, "Remove that task")["proposedAction"]

        self.assertEqual((removal["actionType"], removal["payload"]["itemId"]), ("remove_item", chess["id"]))
        self.chat(self.yesterday, "Morning chess was hard")
        edit = self.chat(self.yesterday, "Change it to partly done")["proposedAction"]
        self.assertEqual((edit["actionType"], edit["payload"]["changes"]), ("edit_item", {"status": "partial"}))
        self.chat(self.yesterday, "Morning chess 怎么样？")
        chinese = self.chat(self.yesterday, "删除那个任务")["proposedAction"]
        self.assertEqual((chinese["actionType"], chinese["payload"]["itemId"]), ("remove_item", chess["id"]))

    def test_ava_asks_which_task_when_the_previous_message_named_several_or_none(self):
        self.done_yesterday("Morning chess")
        self.done_yesterday("Piano")
        self.chat(self.yesterday, "How did Morning chess and Piano go?")

        several = self.chat(self.yesterday, "Remove that task")
        self.chat(self.yesterday, "How did yesterday go?")
        none = self.chat(self.yesterday, "Remove that task")

        self.assertIsNone(several["proposedAction"])
        self.assertIsNone(none["proposedAction"])
        asked = [(notice["kind"], notice["values"]) for notice in none["notices"] if notice["kind"].startswith("clarify")]
        self.assertEqual(sorted(task["title"] for kind, values in asked if kind == "clarify-which" for task in values["tasks"]),
                         ["Morning chess", "Piano"])
        self.assertIn(("clarify-past-task", {"date": self.yesterday}), asked)

    def test_a_past_task_its_set_plan_scheduled_is_deleted_from_its_goal_but_todays_stays(self):
        goal = self.client.post("/api/goals", json={"title": "Chess", "domain": "learning"}).json()
        chess, _ = self.planned_yesterday("Morning chess", goal["id"])

        self.assertEqual(self.client.delete(f"/api/daily-items/{chess['id']}").status_code, 200)
        self.assertEqual(self.kept_entries(self.yesterday), [("Morning chess", None)])
        entries = self.client.get("/api/bootstrap", params={"date": self.yesterday}).json()["entries"]
        self.assertEqual([(entry["title"], entry["removed"], entry["completion_status"]) for entry in entries],
                         [("Morning chess", True, "planned")])

        today_task = self.client.post("/api/daily-items", json=self.item("Endgames", "15:00", "learning", goal["id"])).json()
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": plan["variants"][0]["id"]})
        refused = self.client.delete(f"/api/daily-items/{today_task['id']}")
        self.assertEqual((refused.status_code, refused.json()["detail"]),
                         (409, "A confirmed plan scheduled this record; confirmed days remain read-only"))

    def test_a_past_task_can_be_deleted_from_its_goal_and_its_reports_are_made_again(self):
        path = Path(self.temp_dir.name) / "owned.sqlite3"
        goal = self.client.post("/api/goals", json={"title": "Chess", "domain": "learning"}).json()
        created = self.client.post("/api/daily-items", json=self.item("Morning chess", "09:00", "learning", goal["id"])).json()
        with sqlite3.connect(path) as connection:
            connection.execute("UPDATE daily_items SET item_date = ?, completion_status = 'done' WHERE id = ?",
                               (self.yesterday, created["id"]))
        linked = self.client.get("/api/bootstrap", params={"date": self.today}).json()["goals"][0]["linkedItems"]
        self.assertEqual([item["id"] for item in linked], [created["id"]])
        self.client.post("/api/summaries", params={"date": self.yesterday})

        removed = self.client.delete(f"/api/daily-items/{created['id']}")

        self.assertEqual(removed.status_code, 200)
        later = self.client.post("/api/summaries", params={"date": self.yesterday}).json()["reports"]["day"]
        self.assertNotIn("Morning chess", json.dumps(later))
        self.assertNotIn(("learning", "morning chess"), Database(path).task_profiles("learning"))

    def test_a_past_day_still_takes_no_new_task_and_its_plan_still_cannot_change(self):
        _, variant_id = self.planned_yesterday("Morning chess")
        past = {**self.item("Old appointment", "09:00", "life"), "date": self.yesterday}

        self.assertEqual(self.client.post("/api/daily-items", json=past).status_code, 409)
        self.assertEqual(self.client.post("/api/plan/unset", json={"date": self.yesterday}).status_code, 409)
        self.assertEqual(self.client.post("/api/plan/confirm", json={
            "date": self.yesterday, "variantId": variant_id, "replaceExisting": True}).status_code, 409)
        reply = self.chat(self.yesterday, "Switch to a different plan")
        self.assertIsNone(reply["proposedAction"])
        self.assertIn("A past day's plan is read-only", reply["assistantMessage"]["content"])

    def test_ava_asks_which_task_when_a_change_to_a_past_day_names_none(self):
        self.done_yesterday("Morning chess")

        reply = self.chat(self.yesterday, "Remove that task")

        self.assertIsNone(reply["proposedAction"])
        self.assertEqual([(notice["kind"], notice["values"]) for notice in reply["notices"]
                          if notice["kind"].startswith("clarify")], [("clarify-past-task", {"date": self.yesterday})])

    def test_pausing_a_goal_makes_the_reports_of_its_tasks_days_again(self):
        goal = self.client.post("/api/goals", json={"title": "Chess", "domain": "learning"}).json()
        created = self.client.post("/api/daily-items", json=self.item("Morning chess", "09:00", "learning", goal["id"])).json()
        with sqlite3.connect(Path(self.temp_dir.name) / "owned.sqlite3") as connection:
            connection.execute("UPDATE daily_items SET item_date = ? WHERE id = ?", (self.yesterday, created["id"]))
        earlier = self.client.post("/api/summaries", params={"date": self.yesterday}).json()["reports"]["day"]
        self.assertEqual([entry["status"] for entry in earlier["goals"]], ["active"])

        self.client.put(f"/api/goals/{goal['id']}", json={"title": "Chess", "status": "paused"})

        later = self.client.post("/api/summaries", params={"date": self.yesterday}).json()["reports"]["day"]
        self.assertEqual([entry["status"] for entry in later["goals"]], ["paused"])

    def test_renaming_a_task_on_a_past_planned_day_makes_that_days_report_again(self):
        created = self.client.post("/api/daily-items", json=self.item("Morning chess", None, "learning")).json()
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": plan["variants"][0]["id"]})
        # Past days are read-only through the service, so the planned day is moved back directly.
        with sqlite3.connect(Path(self.temp_dir.name) / "owned.sqlite3") as connection:
            connection.execute("UPDATE daily_items SET item_date = ? WHERE id = ?", (self.yesterday, created["id"]))
            connection.execute("UPDATE plan_sets SET plan_date = ? WHERE plan_date = ?", (self.yesterday, self.today))
            connection.execute("UPDATE daily_confirmations SET plan_date = ? WHERE plan_date = ?", (self.yesterday, self.today))
        earlier = self.client.post("/api/summaries", params={"date": self.yesterday}).json()["reports"]["day"]
        self.assertIn("Morning chess", json.dumps(earlier))

        self.confirm(self.yesterday, "Rename Morning chess to “Evening chess”")

        later = self.client.post("/api/summaries", params={"date": self.yesterday}).json()["reports"]["day"]
        self.assertIn("Evening chess", json.dumps(later))
        self.assertNotIn("Morning chess", json.dumps(later))

    def test_renaming_a_task_renames_it_in_its_plans_so_today_and_summary_follow(self):
        created = self.client.post("/api/daily-items", json=self.item("Morning chess", None, "learning")).json()
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": plan["variants"][0]["id"]})

        self.client.put(f"/api/daily-items/{created['id']}", json=self.item("Evening chess", None, "learning"))

        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        self.assertEqual([entry["title"] for entry in day["entries"]], ["Evening chess"])
        report = self.client.post("/api/summaries", params={"date": self.today}).json()["reports"]["day"]
        self.assertIn("Evening chess", json.dumps(report))

    def test_future_commitment_is_editable_but_future_plan_and_outcome_are_not(self):
        future = self.item("Next week's appointment", "10:00", "life")
        future["date"] = (date.today() + timedelta(days=7)).isoformat()
        created = self.client.post("/api/daily-items", json=future)
        self.assertEqual(created.status_code, 200)
        record = created.json()
        future["detail"] = "Confirmed appointment details"
        update = self.client.put(f"/api/daily-items/{record['id']}", json={**future, "status": "planned"})
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json()["detail"], "Confirmed appointment details")
        premature = self.client.put(f"/api/daily-items/{record['id']}", json={**future, "status": "done"})
        self.assertEqual(premature.status_code, 409)
        self.assertEqual(self.client.post("/api/plan/generate", json={"date": future["date"]}).status_code, 409)
        self.assertEqual(self.client.get("/api/bootstrap", params={"date": future["date"]}).json()["dayItems"][0]["completion_status"], "planned")

    def test_a_learning_goals_reported_time_reaches_its_overview_summary_and_learning_agent(self):
        goal = self.client.post("/api/goals", json={"title": "French pronunciation", "domain": "learning"}).json()
        task = self.client.post("/api/daily-items", json={
            **self.item("Vowel drills", "09:00", "learning", goal["id"]), "durationMinutes": 30}).json()
        self.client.put(f"/api/daily-items/{task['id']}", json={
            **self.item("Vowel drills", "09:00", "learning", goal["id"]), "durationMinutes": 30, "status": "done"})

        area = self.client.get("/api/areas/learning", params={"date": self.today}).json()
        self.assertEqual([(subject["title"], subject["minutes"]) for subject in area["subjects"]],
                         [("French pronunciation", 30)])
        self.assertEqual(area["lastPractised"], self.today)
        summary = self.client.post("/api/summaries", params={"date": self.today}).json()
        self.assertEqual(summary["reports"]["day"]["recordedDays"], 1)
        asked = self.client.post("/api/chat", json={
            "date": self.today, "message": "How is French learning?", "mode": "ask"}).json()
        learning = next(run for run in asked["agentRoute"] if run["agentKey"] == "learning")
        self.assertIn(f"French pronunciation (30m this week). Last practised: {self.today}.", learning["summary"])

    def test_summary_advice_names_the_record_and_a_concrete_next_plan_change(self):
        created = self.client.post("/api/daily-items", json=self.item(
            "Review retrieval notes", "09:30", "learning"))
        self.assertEqual(created.status_code, 200)
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        selected = plan["variants"][0]["id"]
        self.assertEqual(self.client.post("/api/plan/confirm", json={
            "date": self.today, "variantId": selected}).status_code, 200)
        entry = next(item for item in plan["entries"] if item["title"] == "Review retrieval notes")
        self.assertEqual(self.client.patch(f"/api/entries/{entry['id']}", json={
            "status": "skipped"}).status_code, 200)

        report = self.client.post("/api/summaries", params={"date": self.today}).json()
        advice = next(item for item in report["reports"]["day"]["suggestions"]
                      if "Review retrieval notes" in item["content"])
        self.assertIn("45-minute version at 09:30", advice["content"])
        self.assertIn("User-owned commitment", advice["content"])
        self.assertNotIn("Review the size or timing", advice["content"])

    def test_summary_pool_retires_superseded_active_advice_for_the_same_period(self):
        store = Database(Path(self.temp_dir.name) / "pool.sqlite3")
        store.sync_suggestion_pool({"periodKind": "day", "periodKey": self.today,
                                    "suggestions": [{"domain": "life", "priority": "soft",
                                                     "content": "Generic old advice"}]})
        store.sync_suggestion_pool({"periodKind": "day", "periodKey": self.today,
                                    "suggestions": [{"domain": "life", "priority": "soft",
                                                     "content": "Specific current advice"}]})
        items = store.suggestion_pool("day", self.today)["items"]
        self.assertEqual([item["content"] for item in items], ["Specific current advice"])

    def test_todays_low_energy_and_appointment_reach_life_summary_and_the_next_plan(self):
        self.assertEqual(self.client.put(f"/api/energy/{self.today}", json={"level": 2}).status_code, 200)
        appointment = self.client.post("/api/daily-items", json={
            **self.item("Gym appointment", "16:30", "life"), "durationMinutes": 45})
        self.assertEqual(appointment.status_code, 200)
        life = self.client.get("/api/areas/life", params={"date": self.today}).json()
        self.assertEqual(life["energy"], 2)
        self.assertEqual([item["title"] for item in life["appointments"]], ["Gym appointment"])
        report = self.client.post("/api/summaries", params={"date": self.today}).json()
        # One day's reading is too little for advice; the day's report still has its average.
        self.assertNotIn("energy", " ".join(item["content"] for item in report["reports"]["day"]["suggestions"]))
        self.assertEqual(report["reports"]["day"]["energy"]["average"], 2)
        self.client.post("/api/daily-items", json={**self.item("Report", None, "work"), "durationMinutes": 30})
        with patch("backend.app.main._refine_later"):
            care = self.client.post("/api/daily-items", json={
                **self.item("Flexible care", None, "life"), "durationMinutes": None}).json()
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        # Low energy puts Lighter day first; it trims the Life agent's estimate, never Report's own length.
        gentle = plan["variants"][0]
        self.assertEqual(gentle["slug"], "gentle")
        selected = self.client.get("/api/bootstrap", params={
            "date": self.today, "variant_id": gentle["id"]}).json()
        lengths = {entry["title"]: entry["duration_minutes"] for entry in selected["entries"]}
        self.assertEqual((lengths["Flexible care"], lengths["Report"]), (care["duration_minutes"] - 15, 30))

    def test_work_and_project_are_areas_with_their_own_agents_and_money_is_gone(self):
        goal = self.client.post("/api/goals", json={"title": "Ship the guide", "domain": "project"})
        self.assertEqual(goal.status_code, 200)
        self.assertEqual(self.client.post("/api/goals", json={"title": "Budget", "domain": "finance"}).status_code, 422)
        self.assertEqual(self.client.post("/api/daily-items", json=self.item(
            "Client meeting", "10:00", "work")).status_code, 200)
        self.assertEqual(self.client.post("/api/daily-items", json=self.item(
            "Draft chapter", None, "project", goal.json()["id"])).status_code, 200)
        self.assertEqual(self.client.post("/api/daily-items", json=self.item(
            "Evening reset", None, "rest")).status_code, 422)
        work = self.client.get("/api/areas/work", params={"date": self.today}).json()
        self.assertEqual(([meeting["title"] for meeting in work["meetings"]], work["carryOvers"]), (["Client meeting"], []))
        self.assertEqual(self.client.get("/api/areas/finance", params={"date": self.today}).status_code, 422)
        self.assertEqual(self.client.post("/api/money/transactions", json={
            "date": self.today, "type": "expense", "amountCents": 100, "category": "Old"}).status_code, 404)
        asked = self.client.post("/api/chat", json={
            "date": self.today, "message": "How should I prepare the client meeting and the project milestone?",
            "mode": "ask"}).json()
        agents = {run["agentKey"]: run["summary"] for run in asked["agentRoute"]}
        self.assertIn("Client meeting", agents["work"])
        self.assertIn("no start time yet", agents["project"])
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        route = [run["agentKey"] for run in plan["planRoute"]]
        self.assertEqual(route[1:5], ["learning", "life", "work", "project"])
        report = self.client.post("/api/summaries", params={"date": self.today}).json()["reports"]["day"]
        self.assertEqual(set(report["domains"]), {"learning", "life", "work", "project"})
        self.assertNotIn("finance", report["areaEvidence"])

    def test_a_flexible_task_has_no_start_time_and_a_fixed_task_needs_one(self):
        fixed = self.item("Dentist", None, "life")
        fixed["constraintKind"] = "fixed"
        self.assertEqual(self.client.post("/api/daily-items", json=fixed).status_code, 422)
        flexible = {**self.item("Read", None, "learning"), "startTime": "09:00", "constraintKind": "flexible"}
        stored = self.client.post("/api/daily-items", json=flexible).json()
        self.assertIsNone(stored["start_time"])
        short = self.client.post("/api/daily-items", json={**self.item("Stretch", None, "life"), "durationMinutes": 20})
        self.assertEqual(short.status_code, 422)
        self.assertIn("at least 30 minutes", short.json()["detail"])
        stretch = self.client.post("/api/daily-items", json={**self.item("Stretch", None, "life"), "durationMinutes": 30})
        self.assertEqual((stretch.status_code, stretch.json()["duration_minutes"]), (200, 30))

    def test_a_length_under_30_minutes_is_refused_unless_the_task_already_has_it(self):
        store = Database(Path(self.temp_dir.name) / "owned.sqlite3")
        with store.connect() as connection:
            connection.execute(
                """INSERT INTO daily_items (id, item_date, title, domain, start_time,
                   duration_minutes, constraint_kind, created_at)
                   VALUES ('item_short', ?, 'Quick check', 'life', '09:00', 20, 'fixed', ?)""",
                (self.today, self.today))
        report = {**self.item("Quick check", "09:00", "life"), "durationMinutes": 20, "status": "done"}
        self.assertEqual(self.client.put("/api/daily-items/item_short", json=report).status_code, 200)
        shorter = {**report, "durationMinutes": 10, "status": "planned"}
        self.assertEqual(self.client.put("/api/daily-items/item_short", json=shorter).status_code, 422)
        longer = {**report, "durationMinutes": 30, "status": "planned"}
        self.assertEqual(self.client.put("/api/daily-items/item_short", json=longer).json()["duration_minutes"], 30)

    def test_a_task_cannot_be_fixed_over_lunch_or_dinner(self):
        lunch = self.client.post("/api/daily-items", json=self.item("Call", "12:30", "work"))
        self.assertEqual(lunch.status_code, 422)
        self.assertIn("12:00–13:00 is kept for lunch", lunch.json()["detail"])
        dinner = self.client.post("/api/daily-items", json={**self.item("Gym", "17:30", "life"), "durationMinutes": 45})
        self.assertIn("18:00–19:00 is kept for dinner", dinner.json()["detail"])
        self.assertEqual(self.client.post("/api/daily-items", json=self.item("Call", "13:00", "work")).status_code, 200)
        moved = self.client.post("/api/chat", json={"date": self.today, "mode": "adjust",
                                                    "message": "Move Call to 18:00"}).json()["proposedAction"]
        self.assertEqual(moved["payload"]["startTime"], "19:00")

    def test_plans_place_todays_untimed_tasks_and_link_them_to_their_entries(self):
        self.client.post("/api/daily-items", json=self.item("Stand-up", "10:00", "work"))
        task = self.client.post("/api/daily-items", json=self.item("Write tests", None, "project")).json()
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        self.assertEqual(len(plan["variants"]), 3)
        for variant in plan["variants"]:
            day = self.client.get("/api/bootstrap", params={"date": self.today, "variant_id": variant["id"]}).json()
            entry = next(entry for entry in day["entries"] if entry["title"] == "Write tests")
            self.assertTrue(entry["start_time"])
            self.assertEqual(entry["source_item_id"], task["id"])
        set_plan = self.client.post("/api/plan/confirm", json={
            "date": self.today, "variantId": plan["variants"][0]["id"]})
        self.assertEqual(set_plan.status_code, 200)
        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        self.assertIsNone(next(item for item in day["dayItems"] if item["id"] == task["id"])["start_time"])

    def test_each_area_agent_reviews_its_own_tasks_in_the_plans_route(self):
        self.client.post("/api/daily-items", json=self.item("Stand-up", "10:00", "work"))
        self.client.post("/api/daily-items", json=self.item("Write tests", None, "project"))
        self.client.post("/api/plan/generate", json={"date": self.today})

        route = self.client.get("/api/bootstrap", params={"date": self.today}).json()["planRoute"]
        findings = {run["agentKey"]: [(finding["taskTitle"], finding["kind"]) for finding in run["findings"]
                                      if "taskTitle" in finding]
                    for run in route if run["phase"] == "assessment"}
        self.assertEqual(findings, {"learning": [], "life": [], "work": [("Stand-up", "new")],
                                    "project": [("Write tests", "new")]})
        work = next(run for run in route if run["agentKey"] == "work")
        self.assertIn("area-work", [finding["kind"] for finding in work["findings"]])
        self.assertTrue(work["summary"].startswith("Reviewed 1 work task against all your records"))

    def test_agents_learn_from_past_days_and_the_plans_follow_them(self):
        history = [(1, "Guide", "skipped"), (2, "Guide", "partial"), (3, "Guide", "done"),
                   (1, "Notes", "done"), (2, "Notes", "done"), (3, "Notes", "done")]
        domains = {"Guide": "project", "Notes": "learning"}
        created = [self.client.post("/api/daily-items", json=self.item(title, None, domains[title])).json()["id"]
                   for _, title, _ in history]
        # Past days are read-only through the service, so the history is moved back directly.
        with sqlite3.connect(Path(self.temp_dir.name) / "owned.sqlite3") as connection:
            for item_id, (days_ago, title, status) in zip(created, history):
                connection.execute(
                    "UPDATE daily_items SET item_date = ?, start_time = ?, completion_status = ? WHERE id = ?",
                    ((date.today() - timedelta(days=days_ago)).isoformat(), "14:00" if title == "Notes" else None,
                     status, item_id))
        # Guide is saved without a length, so its length is the Project agent's estimate, which
        # plans may shorten; Notes keeps the length the user gave it.
        with patch("backend.app.main._refine_later"):
            self.client.post("/api/daily-items", json={**self.item("Guide", None, "project"), "durationMinutes": None})
        self.client.post("/api/daily-items", json={**self.item("Notes", None, "learning"), "durationMinutes": 45})
        self.client.post("/api/daily-items", json={**self.item("Walk", None, "life"), "durationMinutes": 30})

        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()

        found = {(finding["taskTitle"], finding["kind"]) for run in plan["planRoute"] for finding in run["findings"]
                 if "taskTitle" in finding}
        self.assertTrue({("Guide", "shorten"), ("Notes", "keep"), ("Notes", "time")} <= found, found)
        self.assertEqual({entry["title"]: entry["duration_minutes"] for entry in plan["entries"]}["Guide"], 45)
        # The usual time shapes the plan that follows the user's rhythm.
        rhythm = next(variant for variant in plan["variants"] if variant["slug"] == "rhythm")
        entries = self.client.get("/api/bootstrap", params={"date": self.today, "variant_id": rhythm["id"]}).json()["entries"]
        self.assertEqual({entry["title"]: (entry["start_time"], entry["duration_minutes"]) for entry in entries}["Notes"],
                         ("14:00", 45))

    def test_a_length_the_user_set_is_never_shortened_by_a_plan(self):
        for days_ago, status in ((1, "skipped"), (2, "partial"), (3, "skipped")):
            created = self.client.post("/api/daily-items", json=self.item("Guide", None, "project")).json()["id"]
            with sqlite3.connect(Path(self.temp_dir.name) / "owned.sqlite3") as connection:
                connection.execute("UPDATE daily_items SET item_date = ?, completion_status = ? WHERE id = ?",
                                   ((date.today() - timedelta(days=days_ago)).isoformat(), status, created))
        self.client.post("/api/daily-items", json=self.item("Guide", None, "project"))

        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()

        found = [finding for run in plan["planRoute"] for finding in run["findings"] if finding.get("taskTitle") == "Guide"]
        self.assertEqual([(finding["kind"], finding.get("reason")) for finding in found], [("hold", "yours")])
        for variant in plan["variants"]:
            day = self.client.get("/api/bootstrap", params={"date": self.today, "variant_id": variant["id"]}).json()
            self.assertEqual(next(entry for entry in day["entries"] if entry["title"] == "Guide")["duration_minutes"], 60)

    def test_the_local_model_chooses_the_two_plans_beside_balanced(self):
        class ChoosingGateway(FakeGateway):
            def reply(self, message, context, system_prompt=None, max_tokens=None):
                self.calls.append({"message": message, "context": context, "systemPrompt": system_prompt})
                if "Orchestrator" not in (system_prompt or ""):
                    return f"Considered: {message}", "test-model"
                return json.dumps({"plans": [
                    {"kind": "spacious", "why": "Your three short tasks leave room to breathe.", "whyZh": "三个短任务留有余地。"},
                    {"kind": "gentle", "why": "Ease into the day.", "whyZh": "轻松开始。"}]}), "test-model"

        gateway = ChoosingGateway()
        client = TestClient(create_app(database_path=Path(self.temp_dir.name) / "chosen.sqlite3", gateway=gateway,
                                       embedding_gateway=FakeEmbeddingGateway()))
        for title, domain in (("Report", "work"), ("Walk", "life"), ("Read", "learning")):
            client.post("/api/daily-items", json={**self.item(title, None, domain), "durationMinutes": 30})

        plan = client.post("/api/plan/generate", json={"date": self.today}).json()

        self.assertEqual([variant["slug"] for variant in plan["variants"]], ["balanced", "spacious", "gentle"])
        self.assertEqual(plan["variants"][1]["notes"][0]["values"],
                         {"en": "Your three short tasks leave room to breathe.", "zh": "三个短任务留有余地。"})
        context = json.loads(next(call["context"] for call in gateway.calls if "Orchestrator" in (call["systemPrompt"] or "")))
        self.assertEqual({task["title"] for task in context["day"]["tasks"]}, {"Report", "Walk", "Read"})
        orchestration = plan["planRoute"][0]
        self.assertIn("local model chose Breathing room and Lighter day", orchestration["summary"])

    def test_without_a_usable_answer_the_area_agents_votes_decide(self):
        for title, domain in (("Report", "work"), ("Walk", "life"), ("Read", "learning")):
            self.client.post("/api/daily-items", json={**self.item(title, None, domain), "durationMinutes": 30})

        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()

        self.assertEqual(len(plan["variants"]), 3)
        self.assertIn("from the area agents' votes", plan["planRoute"][0]["summary"])
        life = next(run for run in plan["planRoute"] if run["agentKey"] == "life")
        self.assertEqual(life["votes"][0]["kind"], "spacious")
        voted = [variant for variant in plan["variants"] if variant["notes"] and variant["notes"][0]["key"] == "planWhyVotes"]
        self.assertTrue(voted)

    def test_plans_keep_lunch_and_dinner_and_say_what_sets_each_apart(self):
        self.client.post("/api/daily-items", json=self.item("Write tests", None, "project"))
        self.client.post("/api/daily-items", json={**self.item("Walk", None, "life"), "durationMinutes": 30})

        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()

        for variant in plan["variants"]:
            self.assertEqual(variant["meals"], [{"title": "Lunch", "start_time": "12:00", "duration_minutes": 60},
                                                {"title": "Dinner", "start_time": "18:00", "duration_minutes": 60}])
            keys = [note["key"] for note in variant["notes"]]
            self.assertTrue(any(key.startswith("planDoes") for key in keys), variant["slug"])
            self.assertEqual(variant["rationale"], " ".join(note["text"] for note in variant["notes"]))
        self.assertNotIn("Lunch", [entry["title"] for entry in plan["entries"]])

    def test_a_route_that_closed_with_the_orchestrator_is_reviewed_again_at_start(self):
        self.client.post("/api/daily-items", json=self.item("Write tests", None, "project"))
        self.client.post("/api/plan/generate", json={"date": self.today})
        previous = [{"agentKey": key, "phase": phase, "summary": "Earlier wording", "reads": [], "writes": [], "findings": []}
                    for key, phase in (("orchestrator", "dispatch"), ("learning", "assessment"), ("life", "assessment"),
                                       ("work", "assessment"), ("project", "assessment"), ("summary", "summary"),
                                       ("orchestrator", "synthesis"))]
        path = Path(self.temp_dir.name) / "owned.sqlite3"
        with sqlite3.connect(path) as connection:
            connection.execute("UPDATE plan_generation_routes SET route_json = ?", (json.dumps(previous),))

        restarted = TestClient(create_app(database_path=path, gateway=FakeGateway(),
                                          embedding_gateway=FakeEmbeddingGateway()))

        route = restarted.get("/api/bootstrap", params={"date": self.today}).json()["planRoute"]
        self.assertEqual([run["agentKey"] for run in route], ["orchestrator", "learning", "life", "work", "project", "summary"])
        self.assertNotIn("Earlier wording", route[-1]["summary"])

    def test_a_route_saved_by_an_earlier_version_is_reviewed_again_by_every_agent_at_start(self):
        self.client.post("/api/daily-items", json=self.item("Write tests", None, "project"))
        self.client.post("/api/daily-items", json=self.item("Stand-up", "10:00", "work"))
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": plan["variants"][0]["id"]})
        # A task from an earlier version overlaps another, so the day could not be proposed again.
        sync = self.client.post("/api/daily-items", json=self.item("Sync", "14:00", "work")).json()
        path = Path(self.temp_dir.name) / "owned.sqlite3"
        with sqlite3.connect(path) as connection:
            connection.execute("UPDATE daily_items SET start_time = '10:15' WHERE id = ?", (sync["id"],))
        earlier = [{"agentKey": key, "phase": phase, "summary": "Earlier wording", "reads": [], "writes": []}
                   for key, phase in (("orchestrator", "dispatch"), ("learning", "assessment"),
                                      ("life", "assessment"), ("summary", "summary"), ("orchestrator", "synthesis"))]
        with sqlite3.connect(path) as connection:
            connection.execute("UPDATE plan_generation_routes SET route_json = ?", (json.dumps(earlier),))

        restarted = TestClient(create_app(database_path=path, gateway=FakeGateway(),
                                          embedding_gateway=FakeEmbeddingGateway()))

        day = restarted.get("/api/bootstrap", params={"date": self.today}).json()
        self.assertEqual([run["agentKey"] for run in day["planRoute"]],
                         ["orchestrator", "learning", "life", "work", "project", "summary"])
        self.assertTrue(all("findings" in run for run in day["planRoute"]))
        self.assertIn("review the day again", day["planRoute"][0]["summary"])
        self.assertEqual([variant["id"] for variant in day["variants"]], [variant["id"] for variant in plan["variants"]])
        self.assertEqual(day["confirmedVariantId"], plan["variants"][0]["id"])

    def test_the_kind_of_plan_you_set_most_often_is_offered_first(self):
        path = Path(self.temp_dir.name) / "owned.sqlite3"
        with sqlite3.connect(path) as connection:
            for days_ago in (1, 2, 3):
                past = (date.today() - timedelta(days=days_ago)).isoformat()
                connection.execute("INSERT INTO plan_sets VALUES (?, ?, 'recorded', 'now')", (f"set-{days_ago}", past))
                connection.execute(
                    "INSERT INTO plan_variants (id, plan_set_id, name, slug, rationale, created_at) "
                    "VALUES (?, ?, 'Breathing room', 'spacious', '', 'now')", (f"v-{days_ago}", f"set-{days_ago}"))
                connection.execute("INSERT INTO daily_confirmations VALUES (?, ?, 'now')", (past, f"v-{days_ago}"))
        for title, domain in (("Report", "work"), ("Walk", "life"), ("Read", "learning")):
            self.client.post("/api/daily-items", json={**self.item(title, None, domain), "durationMinutes": 30})

        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()

        self.assertEqual([variant["slug"] for variant in plan["variants"]][:2], ["balanced", "spacious"])

    def test_a_task_saved_without_a_length_gets_an_estimate_the_model_then_refines(self):
        with patch("backend.app.main._refine_later") as later:
            body = self.client.post("/api/daily-items", json={**self.item("Read", None, "learning"),
                                                              "durationMinutes": None}).json()
        self.assertEqual((body["duration_minutes"], body["durationSource"], body["estimatedBy"]), (30, "estimate", "learning"))
        later.assert_called_once()
        self.assertEqual(later.call_args.args[2], body["id"])
        with patch("backend.app.main._refine_later") as later:
            mine = self.client.post("/api/daily-items", json={**self.item("Email", None, "work"), "durationMinutes": 40}).json()
        self.assertEqual((mine["duration_minutes"], mine["durationSource"]), (40, "user"))
        later.assert_not_called()

    def test_a_task_with_a_start_time_cannot_overlap_another_on_its_day(self):
        self.client.post("/api/daily-items", json=self.item("Stand-up", "10:00", "work"))

        overlapping = self.client.post("/api/daily-items", json=self.item("Review", "10:30", "work"))

        self.assertEqual(overlapping.status_code, 422)
        self.assertIn("“Stand-up” (10:00–11:00) already takes that time", overlapping.json()["detail"])
        review = self.client.post("/api/daily-items", json=self.item("Review", "11:00", "work"))
        self.assertEqual(review.status_code, 200)
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        self.assertEqual(self.client.post("/api/daily-items",
                                          json={**self.item("Stand-up", "10:00", "work"), "date": tomorrow}).status_code, 200)
        edit = {**self.item("Review", "10:45", "work"), "status": "planned"}
        self.assertEqual(self.client.put(f"/api/daily-items/{review.json()['id']}", json=edit).status_code, 422)
        renamed = {**self.item("Weekly review", "11:00", "work"), "status": "planned"}
        self.assertEqual(self.client.put(f"/api/daily-items/{review.json()['id']}", json=renamed).status_code, 200)

    def test_talk_moves_a_task_to_the_nearest_free_time_once_confirmed(self):
        self.client.post("/api/daily-items", json=self.item("Stand-up", "10:00", "work"))
        review = self.client.post("/api/daily-items", json=self.item("Review", "13:00", "work")).json()

        reply = self.client.post("/api/chat", json={"date": self.today, "mode": "adjust",
                                                    "message": "Move Review to 10:30"}).json()

        action = reply["proposedAction"]
        self.assertEqual((action["actionType"], action["payload"]["startTime"]), ("move_item", "11:00"))
        self.assertIn("10:30 overlaps “Stand-up”", reply["assistantMessage"]["content"])
        unchanged = self.client.get("/api/bootstrap", params={"date": self.today}).json()["dayItems"]
        self.assertEqual(next(item for item in unchanged if item["id"] == review["id"])["start_time"], "13:00")
        self.assertEqual(self.client.post(f"/api/actions/{action['id']}", json={"decision": "confirmed"}).status_code, 200)
        moved = self.client.get("/api/bootstrap", params={"date": self.today}).json()["dayItems"]
        self.assertEqual(next(item for item in moved if item["id"] == review["id"])["start_time"], "11:00")
        later = self.client.post("/api/chat", json={"date": self.today, "mode": "adjust",
                                                    "message": "move review to 3pm"}).json()["proposedAction"]
        self.assertEqual(later["payload"]["startTime"], "15:00")
        chinese = self.client.post("/api/chat", json={"date": self.today, "mode": "adjust",
                                                      "message": "把 Review 改到下午4点半"}).json()["proposedAction"]
        self.assertEqual(chinese["payload"]["startTime"], "16:30")

    def test_talk_sets_the_length_the_user_names_but_never_below_30_minutes(self):
        review = self.client.post("/api/daily-items", json=self.item("Review", None, "work")).json()

        reply = self.client.post("/api/chat", json={"date": self.today, "mode": "adjust",
                                                    "message": "Make Review 45 minutes"}).json()

        action = reply["proposedAction"]
        self.assertEqual((action["actionType"], action["payload"]["durationMinutes"]), ("set_length", 45))
        self.assertIn("from 60 to 45 minutes", reply["assistantMessage"]["content"])
        self.assertEqual(self.client.post(f"/api/actions/{action['id']}", json={"decision": "confirmed"}).status_code, 200)
        stored = next(item for item in self.client.get("/api/bootstrap", params={"date": self.today}).json()["dayItems"]
                      if item["id"] == review["id"])
        self.assertEqual((stored["duration_minutes"], stored["durationSource"]), (45, "user"))
        hours = self.client.post("/api/chat", json={"date": self.today, "mode": "adjust",
                                                    "message": "make review 1.5 hours"}).json()["proposedAction"]
        self.assertEqual(hours["payload"]["durationMinutes"], 90)
        short = self.client.post("/api/chat", json={"date": self.today, "mode": "adjust",
                                                    "message": "Make Review 10 minutes"}).json()
        self.assertEqual(short["proposedAction"]["payload"]["durationMinutes"], 30)
        self.assertIn("at least 30 minutes, so this proposes 30", short["assistantMessage"]["content"])
        chinese = self.client.post("/api/chat", json={"date": self.today, "mode": "adjust",
                                                      "message": "把 Review 改成 40分钟"}).json()["proposedAction"]
        self.assertEqual(chinese["payload"]["durationMinutes"], 40)
        # Minutes earlier or later move a task; they aren't its length.
        for moved in ("Do review 30 minutes earlier", "push review 1 hour later", "Review 推迟 30分钟"):
            action = self.client.post("/api/chat", json={"date": self.today, "mode": "adjust",
                                                         "message": moved}).json()["proposedAction"]
            self.assertNotEqual((action or {}).get("actionType"), "set_length", moved)

    def test_ava_works_out_what_a_message_wants_without_a_mode(self):
        self.client.post("/api/daily-items", json=self.item("Stand-up", "10:00", "work"))
        self.client.post("/api/daily-items", json=self.item("Review", "13:00", "work"))

        move = self.client.post("/api/chat", json={"date": self.today, "message": "Move Review to 14:00"}).json()
        report = self.client.post("/api/chat", json={"date": self.today, "message": "I finished Review"}).json()
        question = self.client.post("/api/chat", json={"date": self.today, "message": "What should I do next?"}).json()

        self.assertEqual(move["proposedAction"]["actionType"], "move_item")
        self.assertEqual(move["assistantMessage"]["mode"], "adjust")
        self.assertIn("status controls", report["assistantMessage"]["content"])
        self.assertIsNone(question["proposedAction"])
        self.assertEqual(question["assistantMessage"]["mode"], "ask")

    def test_ava_reads_the_days_tasks_plans_goals_and_last_week(self):
        gateway = FakeGateway()
        client = TestClient(create_app(database_path=Path(self.temp_dir.name) / "ava.sqlite3", gateway=gateway,
                                       embedding_gateway=FakeEmbeddingGateway()))
        goal = client.post("/api/goals", json={"title": "Ship the guide", "domain": "project"}).json()
        client.post("/api/daily-items", json={**self.item("Draft", None, "project", goal["id"]), "durationMinutes": 45})

        client.post("/api/chat", json={"date": self.today, "message": "What should I do next?"})

        call = gateway.calls[-1]
        self.assertIn("“Draft” with no start time, project, 45 min (your length), planned", call["context"])
        self.assertIn("“Ship the guide” (project, active, 0 of 1 tasks done)", call["context"])
        today = date.fromisoformat(self.today)
        self.assertIn(f"Last 7 days ({(today - timedelta(days=7)).isoformat()} to {(today - timedelta(days=1)).isoformat()}):",
                      call["context"])
        self.assertIn("You are Ava", call["systemPrompt"])

    def test_talk_refuses_a_length_that_would_overlap_the_next_task(self):
        self.client.post("/api/daily-items", json=self.item("Stand-up", "10:00", "work"))
        self.client.post("/api/daily-items", json=self.item("Review", "09:00", "work"))

        reply = self.client.post("/api/chat", json={"date": self.today, "mode": "adjust",
                                                    "message": "Make Review 90 minutes"}).json()

        self.assertIsNone(reply["proposedAction"])
        self.assertIn("would overlap “Stand-up”", reply["assistantMessage"]["content"])

    def test_deselecting_a_plan_keeps_its_proposals_tasks_and_reports(self):
        self.client.post("/api/daily-items", json=self.item("Walk", "08:00", "life"))
        self.client.post("/api/daily-items", json=self.item("Write tests", None, "project"))
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        first, second = plan["variants"][0]["id"], plan["variants"][1]["id"]
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": first})
        entries = self.client.get("/api/bootstrap", params={"date": self.today}).json()["entries"]
        walk = next(entry for entry in entries if entry["title"] == "Walk")
        self.assertEqual(self.client.patch(f"/api/entries/{walk['id']}", json={"status": "done"}).status_code, 200)

        self.assertEqual(self.client.post("/api/plan/unset", json={"date": self.today}).status_code, 200)

        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        self.assertIsNone(day["confirmedVariantId"])
        self.assertEqual([variant["id"] for variant in day["variants"]], [variant["id"] for variant in plan["variants"]])
        self.assertEqual(next(item for item in day["dayItems"] if item["title"] == "Walk")["completion_status"], "done")
        self.assertEqual(self.client.post("/api/plan/unset", json={"date": self.today}).status_code, 404)
        # With nothing set, another plan is set without a replacement review, and keeps the report.
        self.assertEqual(self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": second}).status_code, 200)
        entries = self.client.get("/api/bootstrap", params={"date": self.today}).json()["entries"]
        self.assertEqual(next(entry for entry in entries if entry["title"] == "Walk")["completion_status"], "done")

    def test_proposing_again_rebuilds_the_plans_not_set_and_keeps_the_set_plan(self):
        self.client.post("/api/daily-items", json={**self.item("Walk", None, "life"), "durationMinutes": 30})
        task = self.client.post("/api/daily-items", json=self.item("Write tests", None, "project")).json()
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        kept = plan["variants"][0]["id"]
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": kept})
        # The task gets a longer length after the plans were proposed.
        self.client.put(f"/api/daily-items/{task['id']}", json={**self.item("Write tests", None, "project"),
                                                                  "durationMinutes": 90, "status": "planned"})

        again = self.client.post("/api/plan/repropose", json={"date": self.today})

        self.assertEqual(again.status_code, 200)
        day = again.json()
        self.assertEqual(day["confirmedVariantId"], kept)
        self.assertEqual(day["variants"][0]["id"], kept)
        self.assertEqual(len(day["variants"]), 3)
        others = [variant for variant in day["variants"] if variant["id"] != kept]
        self.assertFalse({variant["id"] for variant in others} & {variant["id"] for variant in plan["variants"]})
        self.assertNotIn("balanced", [variant["slug"] for variant in others])
        for variant in others:
            entries = self.client.get("/api/bootstrap", params={"date": self.today, "variant_id": variant["id"]}).json()["entries"]
            self.assertEqual(next(entry for entry in entries if entry["title"] == "Write tests")["duration_minutes"], 90)
        self.assertIn("again", day["planRoute"][0]["summary"])
        self.assertEqual(self.client.post("/api/plan/repropose", json={"date": self.yesterday}).status_code, 409)

    def test_proposals_from_an_earlier_version_are_proposed_again_at_start_and_the_set_plan_stays(self):
        path = Path(self.temp_dir.name) / "owned.sqlite3"
        self.client.post("/api/daily-items", json=self.item("Write tests", None, "project"))
        self.client.post("/api/daily-items", json={**self.item("Walk", None, "life"), "durationMinutes": 30})
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        kept = plan["variants"][0]["id"]
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": kept})
        # An earlier version kept no sentences, and its Lighter day shortened a length the user set.
        with sqlite3.connect(path) as connection:
            connection.execute("UPDATE plan_variants SET notes_json = '[]', meals_json = '[]'")
            connection.execute("UPDATE plan_entries SET duration_minutes = 45 WHERE title = 'Write tests' AND variant_id != ?",
                               (kept,))

        restarted = TestClient(create_app(database_path=path, gateway=FakeGateway(), embedding_gateway=FakeEmbeddingGateway()))

        day = restarted.get("/api/bootstrap", params={"date": self.today}).json()
        self.assertEqual((day["confirmedVariantId"], day["variants"][0]["id"]), (kept, kept))
        for variant in day["variants"][1:]:
            self.assertTrue(variant["notes"], variant["slug"])
            entries = restarted.get("/api/bootstrap", params={"date": self.today, "variant_id": variant["id"]}).json()["entries"]
            self.assertEqual(next(entry for entry in entries if entry["title"] == "Write tests")["duration_minutes"], 60)

    def test_only_todays_plan_can_be_deselected(self):
        self.assertEqual(self.client.post("/api/plan/unset", json={"date": self.yesterday}).status_code, 409)
        self.assertEqual(self.client.post("/api/plan/unset", json={"date": "not-a-date"}).status_code, 422)

    def test_owned_records_goals_agent_plan_confirmation_and_summaries(self):
        goal = self.client.post("/api/goals", json={"title": "Learn French", "domain": "learning"})
        self.assertEqual(goal.status_code, 200)
        study = self.client.post("/api/daily-items", json=self.item(
            "French practice", "09:00", "learning", goal.json()["id"]))
        self.assertEqual(study.status_code, 200)
        chore = self.client.post("/api/daily-items", json=self.item("Housework", None, "life"))
        self.assertEqual(chore.status_code, 200)
        before = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        self.assertIsNone(before["planSetId"])
        self.assertEqual(len(before["dayItems"]), 2)
        plan = self.client.post("/api/plan/generate", json={"date": self.today})
        self.assertEqual(plan.status_code, 200)
        planned = plan.json()
        self.assertEqual(planned["planSource"], "orchestrator-records-v1")
        # Only Housework needs placing, after French practice: Lighter day leaves a break before it
        # and Breathing room an hour, so the day still gets three different plans.
        self.assertEqual([variant["name"] for variant in planned["variants"]],
                         ["Balanced", "Breathing room", "Lighter day"])
        self.assertEqual([(entry["title"], entry["start_time"]) for entry in planned["entries"]],
                         [("French practice", "09:00"), ("Housework", "10:00")])
        self.assertEqual(planned["planRoute"][0]["agentKey"], "orchestrator")
        self.assertEqual(planned["planRoute"][-1]["agentKey"], "summary")
        self.assertIsNone(planned["confirmedVariantId"])
        selected = planned["variants"][0]["id"]
        french = next(entry for entry in planned["entries"] if entry["title"] == "French practice")
        self.assertEqual(self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": selected}).status_code, 200)
        self.assertEqual(self.client.patch(f"/api/entries/{french['id']}", json={"status": "done"}).status_code, 200)
        current = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        self.assertEqual(current["confirmedVariantId"], selected)
        self.assertEqual(next(item for item in current["dayItems"] if item["title"] == "French practice")["completion_status"], "done")
        self.assertEqual(next(row for row in current["goals"] if row["id"] == goal.json()["id"])["doneCount"], 1)
        linked = next(row for row in current["goals"] if row["id"] == goal.json()["id"])["linkedItems"]
        self.assertEqual([(item["title"], item["status"]) for item in linked], [("French practice", "done")])
        month = self.client.get("/api/calendar", params={"month": self.today[:7]}).json()
        self.assertEqual(month["days"][0]["doneCount"], 1)
        reports = self.client.post("/api/summaries", params={"date": self.today}).json()["reports"]
        self.assertEqual(set(reports), {"day", "week", "month", "all"})
        self.assertEqual(reports["day"]["domains"]["learning"]["done"], 1)

    def test_adjustment_request_is_explicit_memory_and_does_not_change_plan(self):
        self.client.post("/api/daily-items", json=self.item("French practice", "09:00", "learning"))
        self.client.post("/api/plan/generate", json={"date": self.today})
        message = self.client.post("/api/chat", json={"date": self.today,
            "message": "Please shorten French practice today", "mode": "adjust"})
        self.assertEqual(message.status_code, 200)
        again = self.client.post("/api/chat", json={"date": self.today,
            "message": "Please shorten French practice more", "mode": "adjust"})
        self.assertEqual(again.status_code, 200)
        self.assertIsNone(self.client.get("/api/bootstrap", params={"date": self.today}).json()["confirmedVariantId"])
        report = self.client.post("/api/summaries", params={"date": self.today}).json()["reports"]["day"]
        self.assertEqual(report["feedback"][0]["taskTitle"], "French practice")
        self.assertIn("shorter block", " ".join(s["content"] for s in report["suggestions"]).lower())

    def test_summary_suggestion_pool_persists_discard_and_notices_future_repeat(self):
        self.client.post("/api/daily-items", json=self.item("French practice", "09:00", "learning"))
        for phrase in ("Please shorten French practice", "Please shorten French practice again"):
            self.assertEqual(self.client.post("/api/chat", json={"date": self.today,
                "message": phrase, "mode": "adjust"}).status_code, 200)
        report = self.client.post("/api/summaries", params={"date": self.today}).json()
        day = next(item for item in report["pool"]["day"]["items"]
                   if "French practice" in item["content"])
        self.assertEqual(day["priority"], "soft")
        self.assertEqual(day["status"], "active")
        self.assertGreaterEqual(len(report["pool"]["week"]["items"]), 1)
        planned = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        learning_run = next(run for run in planned["planRoute"] if run["agentKey"] == "learning")
        self.assertIn("Active Summary guidance: soft", learning_run["summary"])
        discarded = self.client.post(f"/api/suggestion-pool/{day['id']}/discard")
        self.assertEqual(discarded.status_code, 200)
        self.assertGreaterEqual(discarded.json()["affectedPeriods"], 3)
        repeated = self.client.post("/api/summaries", params={"date": self.today}).json()
        self.assertEqual(next(item for item in repeated["pool"]["day"]["items"]
                              if item["id"] == day["id"])["status"], "discarded")
        week = repeated["pool"]["week"]["periodKey"]
        refused = self.client.post("/api/suggestion-pool/clear-week", json={
            "week": week, "domain": "learning", "confirmation": "wrong"})
        self.assertEqual(refused.status_code, 422)
        self.assertGreaterEqual(len(repeated["pool"]["week"]["items"]), 1)
        cleared = self.client.post("/api/suggestion-pool/clear-week", json={
            "week": week, "domain": "learning",
            "confirmation": f"CLEAR {week} LEARNING"})
        self.assertEqual(cleared.status_code, 200)
        self.assertGreaterEqual(cleared.json()["deletedAdvice"], 1)
        self.assertFalse(self.client.post("/api/summaries", params={
            "date": self.today}).json()["pool"]["week"]["items"])
        store = Database(Path(self.temp_dir.name) / "owned.sqlite3")
        self.assertFalse(any("French practice" in item["content"]
                             for item in store.active_suggestion_pool()))
        store.sync_suggestion_pool({"periodKind": "day", "periodKey": "later-day",
                                    "suggestions": [{"domain": "learning",
                                                     "content": day["content"],
                                                     "priority": "strong"}]})
        later = store.suggestion_pool("day", "later-day", "learning")
        self.assertEqual(later["items"], [])
        self.assertEqual(len(later["notices"]), 1)
        self.assertEqual(self.client.post(f"/api/suggestion-pool/{day['id']}/discard").status_code, 404)

    def prepare_future_practice(self):
        """Have the Summary agent prepare tomorrow's French practice, and return what it prepared."""
        self.client.post("/api/daily-items", json=self.item(
            "French practice", "09:00", "learning", repeat="daily"))
        for phrase in ("Please shorten French practice", "Please shorten French practice again"):
            response = self.client.post("/api/chat", json={"date": self.today,
                "message": phrase, "mode": "adjust"})
            self.assertEqual(response.status_code, 200)
        first = self.client.post("/api/summaries", params={"date": self.today})
        self.assertEqual(first.status_code, 200)
        prepared = first.json()["futurePrepared"]
        self.assertEqual(len(prepared), 1)
        return prepared[0]

    def test_a_dismissed_agent_suggestion_disappears_and_is_not_suggested_again(self):
        future = self.prepare_future_practice()
        self.assertEqual(future["acceptance"], "pending")
        month = self.client.get("/api/calendar", params={"month": future["date"][:7]}).json()["days"]
        suggested = next(day for day in month if day["date"] == future["date"])
        self.assertEqual((suggested["suggestedCount"], suggested["managedCount"]), (1, 0))

        edit = {**self.item("French practice", "09:00", "learning", repeat="daily"),
                "date": future["date"]}
        self.assertEqual(self.client.put(f"/api/daily-items/{future['id']}", json=edit).status_code, 409)

        self.assertEqual(self.client.post(f"/api/daily-items/{future['id']}/dismiss").status_code, 200)
        hidden = self.client.get("/api/bootstrap", params={"date": future["date"]}).json()
        self.assertEqual(hidden["dayItems"], [])
        self.assertEqual(self.client.post("/api/summaries", params={"date": self.today}).json()["futurePrepared"], [])
        self.assertEqual(self.client.post(f"/api/daily-items/{future['id']}/accept").status_code, 409)

    def test_summary_adds_traceable_future_work_and_agent_can_explain_and_shorten(self):
        future = self.prepare_future_practice()
        self.assertEqual(future["date"], (date.today() + timedelta(days=1)).isoformat())
        self.assertEqual(future["originKind"], "agent-origin")
        self.assertEqual(future["duration_minutes"], 45)
        self.assertIn("Summary", future["originDetail"])
        self.assertEqual(self.client.post("/api/summaries", params={"date": self.today}).json()["futurePrepared"], [])
        why = self.client.post("/api/chat", json={"date": future["date"],
            "message": "Why was French practice added?", "mode": "ask"})
        self.assertEqual(why.status_code, 200)
        self.assertIn("Record provenance", why.json()["assistantMessage"]["content"])
        proposal = self.client.post("/api/chat", json={"date": future["date"],
            "message": "Please shorten French practice", "mode": "adjust"})
        self.assertEqual(proposal.status_code, 200)
        action = proposal.json()["proposedAction"]
        self.assertEqual(action["actionType"], "shorten_future_item")
        self.assertEqual(action["payload"]["durationMinutes"], 30)
        untouched = self.client.get("/api/bootstrap", params={"date": future["date"]}).json()
        self.assertEqual(untouched["dayItems"][0]["duration_minutes"], 45)
        self.assertEqual(self.client.post(f"/api/actions/{action['id']}", json={"decision": "confirmed"}).status_code, 200)
        edited = self.client.get("/api/bootstrap", params={"date": future["date"]}).json()
        self.assertEqual(edited["dayItems"][0]["duration_minutes"], 30)
        self.assertEqual(edited["dayItems"][0]["originKind"], "agent-origin")
        self.assertIsNone(edited["planSetId"])
        accepted = self.client.post(f"/api/daily-items/{future['id']}/accept")
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.json()["acceptance"], "accepted")
        with patch("backend.app.database._writable_day"):
            arrived = self.client.post("/api/plan/generate", json={"date": future["date"]})
        self.assertEqual(arrived.status_code, 200)
        self.assertEqual(arrived.json()["entries"][0]["title"], "French practice")
        self.assertIsNone(arrived.json()["confirmedVariantId"])

    def test_summary_prepares_any_repeatedly_completed_repeating_work_with_shorten_precedence(self):
        store = Database(Path(self.temp_dir.name) / "test.sqlite3")
        today = date.today()
        first = today - timedelta(days=today.weekday())
        if first == today:
            first -= timedelta(days=7)
        second = first + timedelta(days=1)
        with store.connect() as connection:
            for recorded_date in (first, second):
                for title, domain, time, minutes in (
                    ("French practice", "learning", "09:00", 60),
                    ("Morning walk", "life", "10:00", 30),
                ):
                    connection.execute(
                        """INSERT INTO daily_items
                           (id, item_date, title, domain, start_time, duration_minutes,
                            constraint_kind, repeat_kind, repeat_series_id, completion_status, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, 'flexible', 'daily', ?, 'done', ?)""",
                        (f"{title}:{recorded_date}", recorded_date.isoformat(), title,
                         domain, time, minutes, title, recorded_date.isoformat()),
                    )
        facts = store.summary_facts(first.isoformat(), second.isoformat())
        self.assertEqual({entry["taskTitle"] for entry in facts["completedRecurring"]},
                         {"French practice", "Morning walk"})
        orchestrator = AgentOrchestrator()
        report = orchestrator.summary_report("week", "synthetic-week", facts)
        self.assertEqual(len(report["completedRecurring"]), 2)
        report["feedback"].append({"taskTitle": "French practice", "domain": "learning",
                                   "shortenRequests": 2})
        prepared = orchestrator.prepare_future_from_summary(store, report)
        self.assertEqual(len(prepared), 2)
        by_title = {item["title"]: item for item in prepared}
        self.assertEqual(by_title["Morning walk"]["duration_minutes"], 30)
        self.assertIn("completed on 2 recorded days", by_title["Morning walk"]["originDetail"])
        self.assertEqual(by_title["French practice"]["duration_minutes"], 45)
        self.assertIn("requests to shorten", by_title["French practice"]["originDetail"])
        self.assertTrue(all(item["originKind"] == "agent-origin" for item in prepared))
        self.assertEqual(orchestrator.prepare_future_from_summary(store, report), [])

    def repeating_done(self, store, title, days, repeat, goal_id=None):
        """Record a repeating task, fixed at 07:00 for 45 minutes, as done on each of `days`."""
        with store.connect() as connection:
            for recorded_date in days:
                connection.execute(
                    """INSERT INTO daily_items
                       (id, item_date, goal_id, title, domain, start_time, duration_minutes,
                        constraint_kind, repeat_kind, repeat_series_id, completion_status, created_at)
                       VALUES (?, ?, ?, ?, 'life', '07:00', 45, 'fixed', ?, ?, 'done', ?)""",
                    (f"{title}:{recorded_date}", recorded_date.isoformat(), goal_id, title, repeat, title,
                     recorded_date.isoformat()),
                )
        return AgentOrchestrator().summary_report(
            "week", "synthetic-week", store.summary_facts(min(days).isoformat(), max(days).isoformat()))

    def test_a_weekly_repeat_is_prepared_on_its_own_weekday(self):
        store = Database(Path(self.temp_dir.name) / "test.sqlite3")
        latest = date.today() - timedelta(days=2)
        report = self.repeating_done(store, "Swim", (latest - timedelta(days=7), latest), "weekly")

        prepared = AgentOrchestrator().prepare_future_from_summary(store, report)

        self.assertEqual([(item["title"], item["date"]) for item in prepared],
                         [("Swim", (latest + timedelta(days=7)).isoformat())])

    def test_a_paused_goals_repeating_task_is_not_prepared_again(self):
        store = Database(Path(self.temp_dir.name) / "test.sqlite3")
        goal = store.create_goal("Morning routine", "life")
        report = self.repeating_done(store, "Stretch", (date.today() - timedelta(days=2), date.today() - timedelta(days=1)),
                                     "daily", goal["id"])
        store.update_goal(goal["id"], "Morning routine", "paused")

        self.assertEqual(AgentOrchestrator().prepare_future_from_summary(store, report), [])

    def test_summary_gives_no_keep_advice_for_a_paused_goals_repeat(self):
        store = Database(Path(self.temp_dir.name) / "test.sqlite3")
        goal = store.create_goal("Morning routine", "life")
        days = (date.today() - timedelta(days=2), date.today() - timedelta(days=1))
        self.repeating_done(store, "Stretch", days, "daily", goal["id"])
        store.update_goal(goal["id"], "Morning routine", "paused")

        report = AgentOrchestrator().summary_report("week", "synthetic-week",
                                                    store.summary_facts(days[0].isoformat(), days[1].isoformat()))

        self.assertEqual(report["completedRecurring"], [])
        self.assertFalse(any("Stretch" in suggestion["content"] for suggestion in report["suggestions"]))

    def test_a_task_deleted_today_is_dropped_from_todays_drafts(self):
        path = Path(self.temp_dir.name) / "owned.sqlite3"
        read = self.client.post("/api/daily-items", json=self.item("Read", None, "learning")).json()
        self.client.post("/api/daily-items", json=self.item("Walk", None, "life"))
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()

        self.assertEqual(self.client.delete(f"/api/daily-items/{read['id']}").status_code, 200)

        with sqlite3.connect(path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM plan_entries WHERE title = 'Read'").fetchone()[0], 0)
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": plan["variants"][0]["id"]})
        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        self.assertEqual([entry["title"] for entry in day["entries"]], ["Walk"])

    def two_planned_yesterday(self):
        """Set a plan with "Morning chess" and "Piano", both reported done, then move the day to yesterday.

        Returns:
            The "Morning chess" task.
        """
        chess = self.client.post("/api/daily-items", json=self.item("Morning chess", None, "learning")).json()
        self.client.post("/api/daily-items", json=self.item("Piano", None, "learning"))
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": plan["variants"][0]["id"]})
        with sqlite3.connect(Path(self.temp_dir.name) / "owned.sqlite3") as connection:
            connection.execute("UPDATE daily_items SET item_date = ?, completion_status = 'done'", (self.yesterday,))
            connection.execute("UPDATE plan_entries SET completion_status = 'done'")
            connection.execute("UPDATE plan_sets SET plan_date = ?", (self.yesterday,))
            connection.execute("UPDATE daily_confirmations SET plan_date = ?", (self.yesterday,))
        return chess

    def test_a_removed_past_entry_stays_shown_but_leaves_the_calendars_counts(self):
        chess = self.two_planned_yesterday()

        self.client.delete(f"/api/daily-items/{chess['id']}")

        cell = next(day for day in self.client.get("/api/calendar", params={"month": self.yesterday[:7]}).json()["days"]
                    if day["date"] == self.yesterday)
        self.assertEqual((cell["entryCount"], cell["doneCount"]), (1, 1))
        entries = self.client.get("/api/bootstrap", params={"date": self.yesterday}).json()["entries"]
        self.assertEqual(sorted((entry["title"], entry["removed"]) for entry in entries),
                         [("Morning chess", True), ("Piano", False)])

    def test_a_removed_past_entry_leaves_the_reports_and_the_area_profiles(self):
        chess = self.two_planned_yesterday()

        self.client.delete(f"/api/daily-items/{chess['id']}")

        reports = self.client.post("/api/summaries", params={"date": self.yesterday}).json()["reports"]
        for kind in ("day", "week", "month", "all"):
            learning = reports[kind]["domains"]["learning"]
            self.assertEqual((learning["scheduled"], learning["done"]), (1, 1), kind)
        profiles = Database(Path(self.temp_dir.name) / "owned.sqlite3").task_profiles("learning")
        self.assertNotIn(("learning", "morning chess"), profiles)
        self.assertIn(("learning", "piano"), profiles)

    def test_a_paused_goals_task_still_to_do_is_not_scheduled_in_summary(self):
        goal = self.client.post("/api/goals", json={"title": "Chess", "domain": "learning"}).json()
        self.client.post("/api/daily-items", json=self.item("Openings", "16:00", "learning", goal["id"]))
        self.client.post("/api/daily-items", json=self.item("Read", None, "learning"))
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        self.client.post("/api/plan/confirm", json={"date": self.today, "variantId": plan["variants"][0]["id"]})
        self.client.put(f"/api/goals/{goal['id']}", json={"title": "Chess", "status": "paused"})

        for label in ("set plan", "no plan set"):
            day = self.client.post("/api/summaries", params={"date": self.today}).json()["reports"]["day"]
            self.assertEqual(day["domains"]["learning"]["scheduled"], 1, label)
            self.client.post("/api/plan/unset", json={"date": self.today})


if __name__ == "__main__":
    unittest.main()
