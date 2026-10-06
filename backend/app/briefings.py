"""Ava's briefing for a source that doesn't brief itself.

A source's own first paragraph (or a website's own description) and its own headings brief it. Where
either is missing or says too little, Ava asks the local model, on this Mac only, for a briefing of at
most WORD_LIMIT words (see wording) and, for a file or a note without headings, a short outline. A suggestion is
only shown for editing; the source keeps it only when the user confirms it (see SourceStore.set_briefing).
"""

from __future__ import annotations

import json
import re

from .model_gateway import ModelGateway
from .source_store import SourceStore
from .sources import SourceError, plain
from .wording import BRIEFING_MIN_WORDS, WORD_LIMIT, count_words, cut_words

# How much of a source's text the model reads, and how much it may answer with.
SUGGEST_TEXT_CHARACTERS = 6000
SUGGEST_MAX_TOKENS = 260
# The most headings a suggested outline has, and the longest each may be.
SUGGEST_OUTLINE_HEADINGS = 8
SUGGEST_HEADING_CHARACTERS = 80

BRIEFING_ROLE = (
    f"You brief one source in DayWright's Library. Say what it is about in at most {WORD_LIMIT} plain words, in the "
    "source's own language, without praising it. When the source has no headings, also give up to eight short "
    "headings for its parts, in order. Use only what you are given. Answer only with JSON: "
    '{"briefing": "…", "outline": ["…"]}.'
)
BRIEFING_REQUEST = "Write this source's briefing."


def wants_suggestion(source: dict) -> bool:
    """Whether a source lacks a briefing or headings of its own, or its briefing says too little. A website
    keeps only its own headings, so only its briefing can want one."""
    briefing = source.get("briefing") or ""
    return count_words(briefing) < BRIEFING_MIN_WORDS or (not source.get("outline") and source.get("origin") != "website")


def parse_suggestion(content: str) -> dict:
    """The model's answer as a briefing cut to WORD_LIMIT words, at a word boundary, and an outline of at most
    SUGGEST_OUTLINE_HEADINGS headings; an answer that isn't JSON is taken as the briefing.

    Returns:
        {"briefing": str or None, "outline": [str]}.
    """
    start, end = content.find("{"), content.rfind("}")
    try:
        answer = json.loads(content[start:end + 1]) if 0 <= start < end else None
    except json.JSONDecodeError:
        answer = None
    if not isinstance(answer, dict):
        answer = {"briefing": re.sub(r"```\w*", "", content), "outline": []}
    headings = answer.get("outline") if isinstance(answer.get("outline"), list) else []
    outline = [plain(str(heading)).strip()[:SUGGEST_HEADING_CHARACTERS] for heading in headings]
    return {"briefing": cut_words(plain(str(answer.get("briefing") or ""))) or None,
            "outline": [heading for heading in outline if heading][:SUGGEST_OUTLINE_HEADINGS]}


def suggest_briefing(shelf: SourceStore, gateway: ModelGateway, source_id: str) -> dict:
    """Ask the local model to brief a source where its own briefing or headings fall short. A file's or a
    note's text is read on this Mac; a website gives only its title and headings, as kept when it was looked
    up, and is never fetched for this. Nothing is kept until the user confirms.

    Returns:
        {"briefing": the suggestion, or None where the source's own stands; "outline": suggested headings,
        or None where the source has its own or is a website; "by": "ava"}.

    Raises:
        SourceError: When the source briefs itself, gives too little to go on, or the model is unavailable.
    """
    source = shelf.source(source_id)
    if not wants_suggestion(source):
        raise SourceError("This source has its own briefing and headings.")
    headings = [entry["title"] for entry in source["outline"]] + [
        topic["title"] for entry in source["outline"] for topic in entry["topics"]]
    if source["origin"] == "website":
        if not headings:
            raise SourceError("The site gives too little to go on; type the briefing.")
        context = {"title": source["title"], "address": source["address"], "headings": headings}
    else:
        text = shelf.text(source_id).strip()
        if not text:
            raise SourceError("The source gives too little to go on; type the briefing.")
        context = {"title": source["title"], "headings": headings, "text": text[:SUGGEST_TEXT_CHARACTERS]}
    if gateway.status()["state"] == "unavailable":
        raise SourceError("Ava needs the local model to suggest one; type the briefing.")
    answer, mode = gateway.reply(BRIEFING_REQUEST, json.dumps(context, ensure_ascii=False),
                                 system_prompt=BRIEFING_ROLE, max_tokens=SUGGEST_MAX_TOKENS)
    if mode == "rules":
        raise SourceError("Ava needs the local model to suggest one; type the briefing.")
    suggestion = parse_suggestion(answer)
    own_briefing = count_words(source["briefing"] or "") >= BRIEFING_MIN_WORDS
    briefing = None if own_briefing else suggestion["briefing"]
    outline = None if source["outline"] or source["origin"] == "website" else suggestion["outline"] or None
    if briefing is None and outline is None:
        raise SourceError("Ava found too little to say; type the briefing.")
    return {"briefing": briefing, "outline": outline, "by": "ava"}
