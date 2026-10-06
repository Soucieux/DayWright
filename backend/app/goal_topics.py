"""Learning goals made from a source's headings, and their topics.

A connected folder lists each ticked file as one entry: its first # heading, or its name, with all its
## headings. Any other source lists its first-level headings, each with its second-level ones. Each
entry the user ticks becomes a Learning goal, and its second-level headings that goal's topics, in
order. A topic in a local file is read from its own section of the text into a profile: its briefing,
its subheadings (what will be learnt), its size, whether it is hands-on, and its effort, which the
user may change. A topic is studied once a task for it is fully done; the next topic to study is the
first not yet studied, so a goal's order is kept.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from docx import Document

from .database import Database
from .source_store import SourceStore
from .sources import (SourceError, SourceNotFound, briefing_of, plain, read_file, section_text, study_minutes,
                      topic_profile)

# Effort levels, from a quick read to a long, demanding session; a topic without text to read takes the default.
EFFORTS = ("light", "steady", "deep")
DEFAULT_EFFORT = "steady"
# Goals made from a source are Learning goals.
LEARNING = "learning"
# Word's heading styles, by the level they stand for in a topic's section.
_WORD_HEADINGS = {"Heading 1": 1, "Heading 2": 2, "Heading 3": 3}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _word_section(path: Path, heading: str) -> str:
    """The text under a Word file's Heading 2 of that title, to its next Heading 1 or 2, its Heading 3s as
    ### lines so topic_profile finds them."""
    lines, inside_section = [], False
    for paragraph in Document(str(path)).paragraphs:
        level = _WORD_HEADINGS.get(paragraph.style.name if paragraph.style is not None else "")
        text = plain(paragraph.text)
        if level in (1, 2):
            if inside_section:
                break
            inside_section = level == 2 and text == heading
        elif inside_section and text:
            lines.append(f"### {text}" if level == 3 else text)
    return "\n\n".join(lines)


class GoalTopics:
    """Goals from a source's headings, their topics, and the next topic to study."""

    def __init__(self, store: Database, shelf: SourceStore) -> None:
        self.store = store
        self.shelf = shelf

    def entries(self, folder_id: str | None = None, source_id: str | None = None) -> list[dict]:
        """What "From a source" lists to tick: a folder's files, or a source's first-level headings, each
        with the second-level headings that would become its goal's topics.

        Raises:
            SourceError: For a website not looked up yet, as entries never reach the network.
        """
        if folder_id:
            return [{"key": source["id"], "sourceId": source["id"], "index": None, "title": source["title"],
                     "topics": [topic["title"] for group in source["outline"] for topic in group["topics"]],
                     "sourceTitle": source["title"], "relativePath": source["relativePath"]}
                    for source in self.shelf.folder(folder_id)["sources"] if not source["missing"]]
        source = self.shelf.source(source_id)
        if source["origin"] == "website" and not source["lookedUp"]:
            raise SourceError("Look the website up first.")
        return [{"key": f"{source['id']}#{index}", "sourceId": source["id"], "index": index, "title": group["title"],
                 "topics": [topic["title"] for topic in group["topics"]], "sourceTitle": source["title"]}
                for index, group in enumerate(source["outline"])]

    def _text(self, source: dict) -> tuple[str, Path | None, str | None]:
        """A local file's kind, path and Markdown text, for reading its topics; ("", None, None) for a
        source with no file to read now (a website, a note, a folder not found)."""
        if source["origin"] != "folder":
            return "", None, None
        try:
            path = self.shelf.open_target(source["id"])["path"]
            suffix = path.suffix.lower()
            return suffix, path, read_file(path) if suffix in (".md", ".markdown") else None
        except SourceError:
            return "", None, None

    @staticmethod
    def _section(text: tuple, topic: str) -> str:
        """A topic's own section of a local file (see _text), or "" when there is none to read."""
        suffix, path, markdown = text
        return (section_text(markdown, topic) if markdown is not None
                else _word_section(path, topic) if suffix == ".docx" else "")

    def _profile(self, source: dict, text: tuple, topic: str) -> tuple[dict, str] | None:
        """A topic's profile read from its own section of a local file, with "text" as what set its effort;
        None when there is no section of it to read."""
        section = self._section(text, topic)
        if not section:
            return None
        return {**topic_profile(section), "briefing": briefing_of(section), "sourceName": source["title"]}, "text"

    def create_goals(self, picks: list[dict]) -> list[dict]:
        """Make a Learning goal of each ticked entry, its topics in order, and link its source to it.

        Args:
            picks: [{"sourceId", "index"}], index the first-level heading's place in the source's outline,
                or absent for a folder's whole file.

        Returns:
            The goals made, as goals() gives them, with their topics.

        Raises:
            SourceError: For an unknown source or heading, or a goal name already in use; nothing is made.
        """
        planned = []
        taken = {goal["title"].casefold() for goal in self.store.goals()}
        for pick in picks:
            source = self.shelf.source(pick["sourceId"])
            outline, index = source["outline"], pick.get("index")
            if index is None:
                title, topics = source["title"], [topic["title"] for group in outline for topic in group["topics"]]
            elif isinstance(index, int) and 0 <= index < len(outline):
                title, topics = outline[index]["title"], [topic["title"] for topic in outline[index]["topics"]]
            else:
                raise SourceError("That heading isn't in the source.")
            if title.casefold() in taken:
                raise SourceError(f"A goal named “{title}” exists already.")
            taken.add(title.casefold())
            planned.append((source, title, topics))
        made = []
        for source, title, topics in planned:
            text = self._text(source)
            with self.store.connect() as connection:
                goal_id = Database._create_goal(connection, title, LEARNING)
                for position, topic in enumerate(topics):
                    profile, by = self._profile(source, text, topic) or (
                        {"effort": DEFAULT_EFFORT, "subheadings": [], "handsOn": False, "briefing": None,
                         "sourceName": source["title"]}, "default")
                    connection.execute(
                        """INSERT INTO goal_topics (id, goal_id, position, title, source_id, heading, profile_json, effort_by, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (f"topic_{uuid.uuid4().hex[:16]}", goal_id, position, topic, source["id"], title,
                         json.dumps(profile, ensure_ascii=False), by, _now()))
                if not source["goalId"]:
                    connection.execute("UPDATE knowledge_sources SET goal_id = ?, domain = ? WHERE id = ?",
                                       (goal_id, LEARNING, source["id"]))
            made.append(goal_id)
        return [goal for goal in self.store.goals() if goal["id"] in made]

    def topic_text(self, topic: dict) -> str | None:
        """A topic's own section of its source's text, read now on this Mac; None for a topic with no local
        file to read (a website's, a note's, or one whose folder isn't found)."""
        if not topic["sourceId"]:
            return None
        try:
            source = self.shelf.source(topic["sourceId"])
        except SourceNotFound:
            return None
        return self._section(self._text(source), topic["title"]) or None

    def topic(self, topic_id: str) -> dict:
        """One topic, as Database.topics gives it.

        Raises:
            SourceError: When there is no such topic.
        """
        topics = self.store.topics(topic_id=topic_id)
        if not topics:
            raise SourceNotFound("That topic isn't there any more.")
        return topics[0]

    def next_topic(self, goal_id: str) -> dict | None:
        """The goal's next topic to study: its first not yet studied, or None while that one has a task planned
        from today on, or once every topic is studied."""
        for topic in self.store.topics(goal_id):
            if not topic["studied"]:
                return None if topic["plannedOn"] else topic
        return None

    def study_task(self, topic_id: str, day: str) -> dict:
        """A study task for a topic, in its goal, its length estimated from the topic's profile: what Ava and
        the Learning agent propose, to be saved only on Confirm."""
        topic = self.topic(topic_id)
        goal = next(goal for goal in self.store.goals() if goal["id"] == topic["goalId"])
        return {"date": day, "title": topic["title"], "detail": "", "goalId": goal["id"], "topicId": topic["id"],
                "domain": goal["domain"], "startTime": None, "durationMinutes": study_minutes(topic["profile"]),
                "constraintKind": "flexible", "repeatKind": "none"}

    def set_effort(self, topic_id: str, effort: str) -> dict:
        """Set a topic's effort as the user sees it; reading its text again keeps it.

        Raises:
            SourceError: For an effort that isn't light, steady or deep.
        """
        if effort not in EFFORTS:
            raise SourceError("Effort is light, steady or deep.")
        topic = self.topic(topic_id)
        with self.store.connect() as connection:
            connection.execute("UPDATE goal_topics SET profile_json = ?, effort_by = 'you' WHERE id = ?",
                               (json.dumps({**topic["profile"], "effort": effort}, ensure_ascii=False), topic_id))
        return self.topic(topic_id)

    def refresh_profiles(self, source_ids: list[str]) -> None:
        """Read again the topics of sources whose files changed, as a folder's Refresh does. An effort the user
        set stays, and a topic whose section is gone keeps the profile it had."""
        for source_id in source_ids:
            source = self.shelf.source(source_id)
            text = self._text(source)
            with self.store.connect() as connection:
                rows = connection.execute("SELECT id, title, profile_json, effort_by FROM goal_topics WHERE source_id = ?",
                                          (source_id,)).fetchall()
                for row in rows:
                    read = self._profile(source, text, row["title"])
                    if read is None:
                        continue
                    profile, by = read
                    if row["effort_by"] == "you":
                        profile, by = {**profile, "effort": json.loads(row["profile_json"])["effort"]}, "you"
                    connection.execute("UPDATE goal_topics SET profile_json = ?, effort_by = ? WHERE id = ?",
                                       (json.dumps(profile, ensure_ascii=False), by, row["id"]))
