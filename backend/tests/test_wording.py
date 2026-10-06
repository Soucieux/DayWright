import json
import sqlite3
import unittest
from pathlib import Path

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app import guide
from backend.app.briefings import BRIEFING_MIN_WORDS, parse_suggestion, wants_suggestion
from backend.app.retrieval import VectorStore
from backend.app.sources import briefing_of, parse_page
from backend.app.wording import WORD_LIMIT, count_words, cut_words
from backend.tests.test_source_store import ShelfDay

WORDING = json.loads((Path(__file__).resolve().parents[2] / "src" / "wording.json").read_text(encoding="utf-8"))
LONG = " ".join(f"word{index}" for index in range(WORD_LIMIT + 15))


def whole_words(cut: str, original: str) -> bool:
    """Whether a cut text is made of the original's words, each whole, as a cut at a word boundary leaves them."""
    return set(cut.rstrip("…").split()) <= set(original.split())


class CounterTests(unittest.TestCase):
    def test_the_one_limit_and_counter_are_the_shared_files(self):
        self.assertEqual((WORD_LIMIT, BRIEFING_MIN_WORDS), (WORDING["wordLimit"], WORDING["briefingMinWords"]))
        self.assertEqual(WORD_LIMIT, 40)

    def test_words_are_counted_as_the_interface_counts_them(self):
        for text, count in WORDING["counts"]:
            self.assertEqual(count_words(text), count, text)

    def test_text_is_cut_at_a_word_boundary_as_the_interface_cuts_it(self):
        for text, limit, cut in WORDING["cuts"]:
            self.assertEqual(cut_words(text, limit), cut, text)
        self.assertTrue(whole_words(cut_words(LONG), LONG))
        self.assertEqual(count_words(cut_words(LONG)), WORD_LIMIT)


class PlaceTests(ShelfDay):
    def test_every_guide_card_is_within_the_limit(self):
        for card in (card for section in guide.GUIDE["sections"] for card in section["cards"]):
            self.assertLessEqual(count_words(" ".join((card["for"], card["do"], card["rule"]))), WORD_LIMIT, card["title"])

    def test_a_files_own_briefing_is_cut_to_the_limit(self):
        briefing = briefing_of(f"# T\n\n{LONG}\n")
        self.assertEqual((count_words(briefing), briefing.endswith("…")), (WORD_LIMIT, True))

    def test_a_websites_own_description_is_cut_to_the_limit(self):
        page = parse_page(f'<html><head><title>T</title><meta name="description" content="{LONG}"></head></html>')
        self.assertEqual(count_words(page["briefing"]), WORD_LIMIT)
        self.assertTrue(whole_words(page["briefing"], LONG))

    def test_avas_suggestion_is_cut_at_a_word_boundary(self):
        suggested = parse_suggestion(json.dumps({"briefing": LONG + " endingmidword", "outline": []}))["briefing"]
        self.assertEqual(count_words(suggested), WORD_LIMIT)
        self.assertTrue(whole_words(suggested, LONG))

    def test_a_briefing_the_user_writes_or_types_with_a_website_is_held_to_the_limit(self):
        folder = self.connect()
        lesson = next(source for source in folder["sources"] if source["title"] == "Consuming HTTP Services")
        kept = self.shelf.set_briefing(lesson["id"], LONG, None, "you")
        self.assertEqual(count_words(kept["briefing"]), WORD_LIMIT)
        site = self.shelf.add_website("https://atlas.example/", LONG, "learning")
        self.assertEqual(count_words(self.shelf.source(site["id"])["briefing"]), WORD_LIMIT)

    def test_a_longer_briefing_kept_before_reads_within_the_limit(self):
        site = self.shelf.add_website("https://atlas.example/", "", "learning")
        with sqlite3.connect(self.store.path) as connection:
            connection.execute("UPDATE knowledge_sources SET briefing = ? WHERE id = ?", (LONG, site["id"]))
        self.assertEqual(count_words(self.shelf.source(site["id"])["briefing"]), WORD_LIMIT)
        listed = next(item for item in VectorStore(self.store.path).sources() if item["id"] == site["id"])
        self.assertEqual(count_words(listed["briefing"]), WORD_LIMIT)

    def test_a_briefing_too_short_to_go_on_is_counted_the_same_way(self):
        self.assertTrue(wants_suggestion({"briefing": "A map.", "outline": [{"title": "x", "topics": []}], "origin": "folder"}))
        self.assertFalse(wants_suggestion({"briefing": "资料库中的笔记", "outline": [{"title": "x", "topics": []}], "origin": "folder"}),
                         "Chinese is counted a character a word, as everywhere")


if __name__ == "__main__":
    unittest.main()
