"""How DayWright counts words: the one way, everywhere a text is held to a number of them. A Guide card's For,
Do and Rule together, and a source's briefing, its own, the user's or Ava's, each hold at most WORD_LIMIT words.
src/wording.json holds the limit and the examples this counter and the interface's (src/wording.js) both answer
to; the desktop service carries a copy at the same place in its bundle.

A word is a run of text between spaces that holds a letter or a digit, and each Chinese character is a word of
its own, as Chinese is written without spaces.
"""

from __future__ import annotations

import json
import re

from .config import PROJECT_ROOT

WORDING = json.loads((PROJECT_ROOT / "src" / "wording.json").read_text(encoding="utf-8"))
# The most words a Guide card's For, Do and Rule hold together, and a source's briefing.
WORD_LIMIT: int = WORDING["wordLimit"]
# The fewest words a briefing needs before Ava stops offering one.
BRIEFING_MIN_WORDS: int = WORDING["briefingMinWords"]
# A Chinese character, a word of its own; split out of a run with the runs around it.
_HAN = re.compile(r"([㐀-鿿])")


def _pieces(token: str) -> list[str]:
    """A run of text between spaces in its parts: each Chinese character, and the runs between them."""
    return [piece for piece in _HAN.split(token) if piece]


def _is_word(piece: str) -> bool:
    """Whether a part counts as a word: a Chinese character, or a run holding a letter or a digit."""
    return bool(_HAN.fullmatch(piece)) or any(char.isalnum() for char in piece)


def count_words(text: str) -> int:
    """How many words a text holds."""
    return sum(1 for token in text.split() for piece in _pieces(token) if _is_word(piece))


def cut_words(text: str, limit: int = WORD_LIMIT) -> str:
    """A text held to `limit` words: as it is, its spaces run together, when it fits; else cut at the last word
    boundary within the limit, never inside a word, with … where it was cut. "" for a text with nothing in it."""
    kept: list[str] = []
    count = 0
    for token in text.split():
        pieces = _pieces(token)
        words = sum(1 for piece in pieces if _is_word(piece))
        if count + words <= limit:
            kept.append(token)
            count += words
            continue
        # A run of Chinese crosses the limit: keep its characters up to it.
        part: list[str] = []
        for piece in pieces:
            if _is_word(piece):
                if count == limit:
                    break
                count += 1
            part.append(piece)
        while part and not _is_word(part[-1]):
            part.pop()
        if part:
            kept.append("".join(part))
        return " ".join(kept) + "…"
    return " ".join(kept)
