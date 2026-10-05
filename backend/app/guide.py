"""The Guide's cards, which the interface shows and Ava answers from. One file holds their text for
both, src/guide/guide.json; the desktop service carries a copy at the same place in its bundle."""

from __future__ import annotations

import json
import re

from .config import PROJECT_ROOT

GUIDE = json.loads((PROJECT_ROOT / "src" / "guide" / "guide.json").read_text(encoding="utf-8"))
_CARDS = [card for section in GUIDE["sections"] for card in section["cards"]]
# Every word that names a card, longest first, so "past tasks" is read before "tasks".
_WORDS = sorted(((word, card["id"]) for card in _CARDS for word in card["words"]), key=lambda pair: -len(pair[0]))
# A question that asks how something works, what it is for or does, or how to use it, and the words
# naming it: "How do meals work?", "What is the Library for?", "What does the Orchestrator do?",
# "How do I use goals?". The Guide is in English, and so are the questions it answers.
_ASKS_HOW = re.compile(r"\bhow\s+(?:(?:does|do)\s+)?(.+?)\s+works?\W*$"
                       r"|\bwhat\s+(?:is|are)\s+(.+?)\s+for\W*$"
                       r"|\bwhat\s+(?:does|do)\s+(.+?)\s+do\W*$"
                       r"|\bhow\s+(?:do|can|should)\s+i\s+use\s+(.+?)\W*$", re.IGNORECASE)


def asked_cards(message: str) -> list[dict]:
    """The Guide's cards a question about how something works asks for, by the words naming them.

    Each word is taken once, so "How do past tasks work?" asks for Past days and not Tasks as well.

    Returns:
        The cards in Guide order, or an empty list for any other message, or one naming no card.
    """
    asked = _ASKS_HOW.search(message)
    if not asked:
        return []
    subject = next(group for group in asked.groups() if group).lower()
    named = set()
    for word, card_id in _WORDS:
        pattern = rf"\b{re.escape(word)}\b"
        if re.search(pattern, subject):
            named.add(card_id)
            subject = re.sub(pattern, " ", subject)
    return [card for card in _CARDS if card["id"] in named]


def answer(cards: list[dict]) -> str:
    """Ava's answer from the cards: each card's title and its three labelled lines, then one line
    naming the cards, which the interface turns into links that open each in the Guide."""
    labels = GUIDE["labels"]
    lines = "\n\n".join(f"**{card['title']}**\n{labels['for']}: {card['for']}\n{labels['do']}: {card['do']}\n"
                        f"{labels['rule']}: {card['rule']}" for card in cards)
    return f"{lines}\n\n{labels['seeGuide']}: {', '.join(card['title'] for card in cards)}"
