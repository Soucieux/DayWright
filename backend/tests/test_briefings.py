import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app import sources
from backend.app.briefings import parse_suggestion, suggest_briefing, wants_suggestion
from backend.app.database import Database
from backend.app.main import create_app
from backend.app.source_store import SourceStore
from backend.app.sources import BRIEFING_WORDS, SourceError
from backend.tests.test_api import FakeEmbeddingGateway, FakeGateway
from backend.tests.test_sources import hashes, tree

SUGGESTION = {"briefing": "How the HTTP client sends requests and handles what comes back.",
              "outline": ["Sending requests", "Reading responses"]}


class AvaGateway(FakeGateway):
    """The local model, answering a briefing request with the suggestion it is given."""

    def __init__(self, answer=json.dumps(SUGGESTION), mode="local-model", state="ready"):
        super().__init__()
        self.answer, self.mode, self.state = answer, mode, state

    def status(self):
        return {**super().status(), "state": self.state, "running": self.state == "ready"}

    def reply(self, message, context, system_prompt=None, max_tokens=None):
        self.calls.append({"message": message, "context": context, "systemPrompt": system_prompt})
        return self.answer, self.mode


class BriefingDay(unittest.TestCase):
    """A fresh account, a throwaway folder whose notes have no paragraph or headings, and no network."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.store = Database(base / "briefings.sqlite3")
        self.shelf = SourceStore(self.store)
        self.folder = tree(base / "Notes", {"bare.md": "- get\n- post\n- interceptors: retry, auth\n",
                                           "full.md": "# Full\n\nA full note that says what it is about in a sentence.\n\n## One\n\nText.\n"})
        network = patch.object(sources, "urlopen", side_effect=AssertionError("no network"))
        network.start()
        self.addCleanup(network.stop)
        folder = self.shelf.connect(str(self.folder), [])
        self.bare, self.full = (next(source for source in folder["sources"] if source["relativePath"] == name)
                                for name in ("bare.md", "full.md"))


class SuggestionTests(BriefingDay):
    def test_ava_suggests_only_where_a_briefing_or_the_headings_are_missing(self):
        self.assertTrue(wants_suggestion(self.bare))
        self.assertFalse(wants_suggestion(self.full))
        with self.assertRaisesRegex(SourceError, "has its own briefing and headings"):
            suggest_briefing(self.shelf, AvaGateway(), self.full["id"])

    def test_a_suggestion_reads_the_files_text_on_this_mac_and_is_kept_only_on_confirm(self):
        before = hashes(self.folder)
        gateway = AvaGateway()

        suggestion = suggest_briefing(self.shelf, gateway, self.bare["id"])

        self.assertEqual(suggestion, {"briefing": SUGGESTION["briefing"], "outline": SUGGESTION["outline"], "by": "ava"})
        self.assertIn("interceptors: retry, auth", gateway.calls[0]["context"])
        unchanged = self.shelf.source(self.bare["id"])
        self.assertEqual((unchanged["briefing"], unchanged["outline"]), (None, []))

        kept = self.shelf.set_briefing(self.bare["id"], suggestion["briefing"], suggestion["outline"], "ava")

        self.assertEqual((kept["briefing"], kept["briefingBy"], kept["outlineBy"]), (SUGGESTION["briefing"], "ava", "ava"))
        self.assertEqual([entry["title"] for entry in kept["outline"][0]["topics"]], SUGGESTION["outline"])
        self.assertEqual(hashes(self.folder), before)

    def test_a_briefing_the_user_edits_is_theirs_and_its_own_headings_are_kept(self):
        kept = self.shelf.set_briefing(self.full["id"], "My words for it.", None, "you")
        self.assertEqual((kept["briefing"], kept["briefingBy"]), ("My words for it.", "you"))
        self.assertEqual(kept["outline"], self.full["outline"])
        self.assertEqual(kept["outlineBy"], "source")
        with self.assertRaises(SourceError):
            self.shelf.set_briefing(self.full["id"], "", None, "you")
        with self.assertRaises(SourceError):
            self.shelf.set_briefing(self.full["id"], "Words.", None, "someone")

    def test_a_note_with_its_own_paragraph_gets_only_headings_and_keeps_its_own_words(self):
        (self.folder / "prose.md").write_text("A plain note that says what it is about but has no headings at all.\n")
        self.shelf.refresh(self.bare["folderId"])
        prose = next(source for source in self.shelf.folder(self.bare["folderId"])["sources"] if source["relativePath"] == "prose.md")

        suggestion = suggest_briefing(self.shelf, AvaGateway(), prose["id"])
        self.assertEqual((suggestion["briefing"], suggestion["outline"]), (None, SUGGESTION["outline"]))
        kept = self.shelf.set_briefing(prose["id"], suggestion["briefing"], suggestion["outline"], "ava")

        self.assertEqual((kept["briefing"], kept["briefingBy"]), (prose["briefing"], "source"))
        self.assertEqual(kept["outlineBy"], "ava")
        with self.assertRaises(SourceError):
            self.shelf.set_briefing(prose["id"], None, None, "ava")

    def test_a_website_that_briefs_itself_wants_nothing_though_it_has_no_headings(self):
        site = self.shelf.add_website("https://atlas.example/", "", "learning")
        with patch("backend.app.source_store.fetch_page", return_value={"title": "Atlas", "briefing": "A map of every signal there is.",
                                                                       "outline": []}):
            site = self.shelf.look_up(site["id"])
        self.assertFalse(wants_suggestion(site))

    def test_a_confirmed_briefing_outlasts_a_refresh_until_the_file_briefs_itself(self):
        self.shelf.set_briefing(self.bare["id"], SUGGESTION["briefing"], SUGGESTION["outline"], "ava")
        self.shelf.set_briefing(self.full["id"], "My words for it.", None, "you")
        (self.folder / "bare.md").write_text("- get\n- post\n- put\n")
        (self.folder / "full.md").write_text("# Full\n\nA changed paragraph that says something else now.\n")

        self.shelf.refresh(self.shelf.source(self.bare["id"])["folderId"])

        bare, full = self.shelf.source(self.bare["id"]), self.shelf.source(self.full["id"])
        self.assertEqual((bare["briefing"], bare["briefingBy"], bare["outlineBy"]), (SUGGESTION["briefing"], "ava", "ava"))
        self.assertEqual((full["briefing"], full["briefingBy"]), ("My words for it.", "you"))

        (self.folder / "bare.md").write_text("# Bare\n\nNow it says what it is about itself.\n\n## Verbs\n")
        self.shelf.refresh(bare["folderId"])
        bare = self.shelf.source(self.bare["id"])
        self.assertEqual((bare["briefingBy"], bare["outlineBy"]), ("source", "source"))
        self.assertEqual(bare["outline"][0]["topics"][0]["title"], "Verbs")

    def test_without_the_local_model_the_user_is_asked_to_type_it(self):
        for gateway in (AvaGateway(state="unavailable"), AvaGateway(answer="Not now.", mode="rules")):
            with self.assertRaisesRegex(SourceError, "type the briefing"):
                suggest_briefing(self.shelf, gateway, self.bare["id"])

    def test_a_website_is_briefed_from_its_title_and_headings_alone_and_too_little_says_so(self):
        site = self.shelf.add_website("https://atlas.example/", "", "learning")
        gateway = AvaGateway()
        with self.assertRaisesRegex(SourceError, "too little"):
            suggest_briefing(self.shelf, gateway, site["id"])
        self.assertEqual(gateway.calls, [])

        page = {"title": "Signals atlas", "briefing": None, "outline": [{"title": "Signals", "topics": [{"title": "Computed"}]}]}
        with patch("backend.app.source_store.fetch_page", return_value=page):
            self.shelf.look_up(site["id"])
        suggestion = suggest_briefing(self.shelf, gateway, site["id"])

        self.assertEqual(suggestion["briefing"], SUGGESTION["briefing"])
        self.assertIsNone(suggestion["outline"], "a website keeps its own headings")
        self.assertIn("Signals atlas", gateway.calls[0]["context"])
        self.assertIn("Computed", gateway.calls[0]["context"])


class ParseTests(unittest.TestCase):
    def test_a_suggestion_is_held_to_forty_words_and_eight_headings(self):
        long = {"briefing": " ".join(["word"] * 60), "outline": [f"Part {n}" for n in range(12)]}
        parsed = parse_suggestion("Sure:\n```json\n" + json.dumps(long) + "\n```")
        self.assertEqual(len(parsed["briefing"].split()), BRIEFING_WORDS)
        self.assertTrue(parsed["briefing"].endswith("…"))
        self.assertEqual(len(parsed["outline"]), 8)

    def test_plain_words_are_taken_as_the_briefing(self):
        self.assertEqual(parse_suggestion("A guide to signals."), {"briefing": "A guide to signals.", "outline": []})
        self.assertEqual(parse_suggestion("  "), {"briefing": None, "outline": []})


class BriefingRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.gateway = AvaGateway()
        self.client = TestClient(create_app(database_path=base / "routes.sqlite3", gateway=self.gateway,
                                            embedding_gateway=FakeEmbeddingGateway()))
        network = patch.object(sources, "urlopen", side_effect=AssertionError("no network"))
        network.start()
        self.addCleanup(network.stop)

    def test_ava_suggests_a_note_briefing_and_confirm_keeps_it(self):
        note = self.client.post("/api/knowledge/sources", json={"title": "Lists", "sourceType": "note", "text": "- one\n- two\n",
                                                                "domain": "learning"})
        self.assertEqual(note.status_code, 200, note.text)
        source_id = next(source["id"] for source in self.client.get("/api/knowledge").json()["sources"] if source["title"] == "Lists")

        suggested = self.client.post(f"/api/sources/{source_id}/suggest-briefing")
        self.assertEqual(suggested.status_code, 200, suggested.text)
        self.assertEqual(suggested.json()["by"], "ava")
        self.assertIn("- one", self.gateway.calls[0]["context"])

        kept = self.client.put(f"/api/sources/{source_id}/briefing", json=suggested.json())
        self.assertEqual(kept.status_code, 200, kept.text)
        listed = next(source for source in self.client.get("/api/knowledge").json()["sources"] if source["id"] == source_id)
        self.assertEqual((listed["briefing"], listed["briefingBy"], listed["outlineBy"]), (SUGGESTION["briefing"], "ava", "ava"))

    def test_the_service_asks_its_own_model_gateway_and_without_a_model_says_to_type_it(self):
        base = Path(self.temp.name)
        folder = tree(base / "Notes", {"bare.md": "- get\n- post\n"})
        nothing = base / "no-models"
        with patch.dict("os.environ", {"DAYWRIGHT_MODEL_LIBRARY": str(nothing), "DAYWRIGHT_LLAMA_SERVER": str(nothing / "llama-server")}):
            client = TestClient(create_app(database_path=base / "own.sqlite3", embedding_gateway=FakeEmbeddingGateway()))
        self.addCleanup(lambda: [thread.join() for thread in client.app.state.indexing])
        connected = client.post("/api/sources/folder", json={"path": str(folder), "unticked": [], "domain": "learning"}).json()

        answer = client.post(f"/api/sources/{connected['sources'][0]['id']}/suggest-briefing")

        self.assertEqual(answer.status_code, 422, answer.text)
        self.assertIn("type the briefing", answer.json()["detail"])

    def test_without_the_model_the_route_says_to_type_it(self):
        self.gateway.state = "unavailable"
        site = self.client.post("/api/sources/website", json={"address": "https://atlas.example/", "briefing": "", "domain": "learning"}).json()
        answer = self.client.post(f"/api/sources/{site['id']}/suggest-briefing")
        self.assertEqual(answer.status_code, 422)
        self.assertEqual(self.client.post("/api/sources/source_none/suggest-briefing").status_code, 404)
