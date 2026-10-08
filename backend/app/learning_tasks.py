"""Learning tasks and their checklists.

Studying a file is one task, and a goal is a group of tasks the user chooses. From a source, each file
the user ticks in a connected folder, a website's page or any other Library item becomes one Learning
task, named by its first heading or its file name, all on one day or one a day in their order, alone or
in a Learning goal. Its checklist is its second-level headings, or with none its first-level ones below
the first; any Learning task can have one the user makes, and the user adds, renames, removes and
reorders items in either. Ticking every item never marks the task done, as only the user does that.

A checklist belongs to a pass through the file: a new task from it, and a follow-up of one partly done,
carry on the latest pass with its ticks and items, unless the user starts afresh for a revision pass. A
task's effort, light, steady or deep, and its length come from its whole text, or a website's from its
headings, and the user may change both; a follow-up's length comes from the items still unticked, at the
pace its earlier items went when there is one.

A website's page is looked up again once, quietly, as its task starts: a timed task at its start time,
or the next time DayWright runs after it while the task has no status; an untimed one the first time
its briefing is opened on its day. A changed page brings its briefing, checklist and estimates up to
date, never a length the user set, and a changed file does the same when its folder is refreshed: an
item still there keeps its tick, a new heading joins unticked, marked new, one no longer there stays,
marked so, and the user's own items are left as they are. A site out of reach keeps what was stored.
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import date, datetime, timedelta, timezone
from math import ceil

from .database import LEARNING_ESTIMATE_BASIS, MIN_TASK_MINUTES, Database, add_checklist
from .patterns import source_pace
from .planner import SLOT_MINUTES
from .source_store import SourceStore
from .sources import (SourceError, SourceNotFound, checklist_of, heading_profile, section_text, study_minutes,
                      study_profile)

# How much a task asks of a study session, from a quick read to a long, demanding one; a task with nothing
# to read takes the default.
EFFORTS = ("light", "steady", "deep")
DEFAULT_EFFORT = "steady"
# Tasks made from a source are Learning tasks, and only Learning tasks have a checklist.
LEARNING = "learning"
# How a source's latest reading found a checklist item it gave: as before (""), new in it, or no longer in it.
NEW, GONE = "new", "gone"
# The revision an import appends to a file's name, left out of its task's title.
_REVISION = re.compile(r" · [0-9a-f]{12}$")
_PAST = "A past task's checklist changes only through Ava; ask Ava to tick it"
_TASK_COLUMNS = """l.item_id, l.source_id, l.pass_id, l.profile_json, l.effort_by, l.follows_item_id, l.start_checked_at,
                   l.start_check, s.title AS source_title, s.origin AS source_origin"""


def _new_id(prefix: str) -> str:
    """A new pass's or checklist item's id."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _entries(connection: sqlite3.Connection, pass_id: str) -> list[sqlite3.Row]:
    """A pass's checklist items in order, the ones the user removed included."""
    return connection.execute("SELECT * FROM checklist_items WHERE pass_id = ? ORDER BY position, rowid", (pass_id,)).fetchall()


def _to_study(entries: list[sqlite3.Row]) -> list[sqlite3.Row]:
    """The items still to study: on show, unticked, and still in their source."""
    return [entry for entry in entries if not entry["removed"] and not entry["ticked_at"] and entry["page_state"] != GONE]


def _view(item_id: str, row, entries: list[sqlite3.Row]) -> dict:
    """A Learning task as the routes, Ava and the plans read it: its checklist, items on show in order, with
    who added each, how its source's latest reading found it, and when and on which task it was ticked."""
    checklist = [{"id": entry["id"], "title": entry["title"], "heading": entry["heading"], "addedBy": entry["added_by"],
                  "pageState": entry["page_state"], "tickedAt": entry["ticked_at"], "tickedOn": entry["ticked_on"]}
                 for entry in entries if not entry["removed"]]
    ticked = [entry["title"] for entry in checklist if entry["tickedAt"]]
    profile = json.loads(row["profile_json"]) if row else {}
    return {"itemId": item_id, "sourceId": row and row["source_id"], "sourceTitle": row and row["source_title"],
            "sourceOrigin": row and row["source_origin"], "passId": row and row["pass_id"], "checklist": checklist,
            "sections": [entry["title"] for entry in checklist], "ticked": ticked,
            "progress": {"done": len(ticked), "total": len(checklist)},
            "allTicked": bool(checklist) and len(ticked) == len(checklist), "profile": profile,
            "effort": profile.get("effort", DEFAULT_EFFORT), "effortBy": row["effort_by"] if row else "text",
            "followsItemId": row and row["follows_item_id"], "startCheckedAt": row and row["start_checked_at"],
            "startCheck": row["start_check"] if row else ""}


def _profile_left(entries: list[sqlite3.Row], origin: str | None, text: str, whole: dict) -> tuple[dict, str]:
    """What the items still to study say about studying them, and what that rests on: a website's by their
    headings, a text's by their own sections, else by their share of the whole text's profile; with no
    source, by how many there are. Each item the user added counts as a section with no text of its own."""
    left = _to_study(entries)
    own = [entry for entry in left if entry["added_by"] == "you"]
    given = [entry for entry in left if entry["added_by"] != "you"]
    if origin in (None, "website"):
        return heading_profile(len(left)), "headings"
    parts = "\n\n".join(section_text(text, entry["heading"], entry["level"] or 2) for entry in given) if text else ""
    if parts.strip():
        profile, by = study_profile(parts), "text"
    elif given and "words" in whole:
        share = len(given) / max(sum(1 for entry in entries if entry["added_by"] != "you" and not entry["removed"]), 1)
        profile = {**whole, "words": round(whole["words"] * share), "codeBlocks": round(whole.get("codeBlocks", 0) * share)}
        by = "text"
    else:
        profile, by = heading_profile(len(given)), "headings"
    return ({**profile, "sections": profile.get("sections", 0) + len(own)} if own else profile), by


def _merge(connection: sqlite3.Connection, pass_id: str, headings: list[dict]) -> bool:
    """Bring a pass's checklist up to date with its source's headings: an item still there (by the heading it
    came from, however the user renamed it) keeps its tick and loses any mark; a new heading joins unticked
    after the one before it, marked new; one no longer there stays, marked gone. The user's own items, and
    the source's items the user removed, are left as they are.

    Returns:
        Whether the checklist changed: a heading added, gone, or back.
    """
    entries = _entries(connection, pass_id)
    order = [entry["id"] for entry in entries]
    unmatched = [entry for entry in entries if entry["added_by"] != "you"]
    anchor, changed, states = None, False, {}
    for heading in headings:
        match = next((entry for entry in unmatched if entry["heading"] == heading["title"]), None)
        if match:
            unmatched.remove(match)
            changed = changed or (match["page_state"] == GONE and not match["removed"])
            states[match["id"]] = ""
            anchor = match["id"]
            continue
        new_id = add_checklist(connection, pass_id, [heading], len(order))[0]
        first = next((order.index(entry["id"]) for entry in entries if entry["added_by"] != "you"), len(order))
        order.insert(order.index(anchor) + 1 if anchor else first, new_id)
        states[new_id], anchor, changed = NEW, new_id, True
    for entry in unmatched:
        if not entry["removed"]:
            changed = changed or entry["page_state"] != GONE
            states[entry["id"]] = GONE
    for entry_id, state in states.items():
        connection.execute("UPDATE checklist_items SET page_state = ? WHERE id = ?", (state, entry_id))
    for position, entry_id in enumerate(order):
        connection.execute("UPDATE checklist_items SET position = ? WHERE id = ?", (position, entry_id))
    return changed


class LearningTasks:
    """Learning tasks and their checklists: making them from Library sources, the user's edits and ticks,
    efforts, follow-ups, a goal's next one to study, and their websites' look-up as they start."""

    def __init__(self, store: Database, shelf: SourceStore | None) -> None:
        self.store = store
        self.shelf = shelf

    def entries(self, folder_id: str | None = None, source_id: str | None = None) -> list[dict]:
        """What From a source lists to tick: a folder's files found in it, or one source, each with the
        checklist its task would hold and how far its latest pass has come, if a task was made from it.

        Raises:
            SourceError: For a website not looked up yet, as listing never reaches the network.
        """
        if folder_id:
            sources = [source for source in self.shelf.folder(folder_id)["sources"] if not source["missing"]]
        else:
            sources = [self.shelf.source(source_id)]
            if sources[0]["origin"] == "website" and not sources[0]["lookedUp"]:
                raise SourceError("Look the website up first.")
        progress = self.progress_by_source()
        return [{"key": source["id"], "sourceId": source["id"], "title": _REVISION.sub("", source["title"]),
                 "sections": [heading["title"] for heading in checklist_of(source["outline"])],
                 "relativePath": source["relativePath"], "progress": progress.get(source["id"])} for source in sources]

    def source_of(self, source_id: str | None) -> dict | None:
        """A task's source, or None once it is gone from the Library."""
        try:
            return self.shelf.source(source_id) if source_id and self.shelf else None
        except SourceNotFound:
            return None

    def _text(self, source: dict | None) -> str:
        """A source's text, read now on this Mac; "" for a website, which keeps none, or one out of reach."""
        if source is None or source["origin"] == "website":
            return ""
        try:
            return self.shelf.text(source["id"])
        except SourceError:
            return ""

    def _profile(self, source: dict, text: str, headings: list[dict]) -> tuple[dict, str]:
        """What a source says about studying it and what that rests on: a website's headings ("headings"),
        else its whole text ("text"), or the default effort for one with nothing to read ("default")."""
        if source["origin"] == "website":
            return heading_profile(len(headings)), "headings"
        return (study_profile(text), "text") if text.strip() else ({"effort": DEFAULT_EFFORT}, "default")

    def create_tasks(self, source_ids: list[str], day: str, goal: dict | None = None, one_a_day: bool = False,
                     fresh: bool = False) -> dict:
        """Make a Learning task of each ticked file, page or item, untimed, its length estimated from its source.

        Args:
            source_ids: What was ticked, in the order its tasks take.
            day: The day they go on, or with one_a_day the first of them, YYYY-MM-DD.
            goal: {"goalId"} to put them in an active Learning goal, {"title"} to make one, or None for none.
            one_a_day: One task a day from `day`, in order, rather than all on `day`.
            fresh: Start a new pass through each file, its checklist clean, rather than carry on its latest,
                whose length then counts only the items still to study.

        Returns:
            {"tasks": the tasks as the day lists them, "goal": the goal they joined, or None}.

        Raises:
            SourceError: Nothing ticked, an unknown source, a website not looked up, a goal that isn't an active
                Learning goal, or a new goal's name already in use; nothing is made.
        """
        if not source_ids:
            raise SourceError("Tick a file or page to learn from.")
        sources = [self.shelf.source(source_id) for source_id in source_ids]
        if any(source["origin"] == "website" and not source["lookedUp"] for source in sources):
            raise SourceError("Look the website up first.")
        goals = self.store.goals()
        if goal and goal.get("goalId"):
            chosen = next((entry for entry in goals if entry["id"] == goal["goalId"]), None)
            if not chosen or chosen["domain"] != LEARNING or chosen["status"] != "active":
                raise SourceError("Choose an active Learning goal.")
        elif goal:
            title = (goal.get("title") or "").strip()
            if not title:
                raise SourceError("Name the new goal.")
            if title.casefold() in {entry["title"].casefold() for entry in goals}:
                raise SourceError(f"A goal named “{title}” exists already.")
        texts = {source["id"]: self._text(source) for source in sources}
        first, made = date.fromisoformat(day), []
        with self.store.connect() as connection:
            goal_id = goal and (goal.get("goalId") or Database._create_goal(connection, goal["title"].strip(), LEARNING))
            for offset, source in enumerate(sources):
                headings = checklist_of(source["outline"])
                profile, by = self._profile(source, texts[source["id"]], headings)
                minutes = study_minutes(profile)
                latest = None if fresh else connection.execute(
                    "SELECT pass_id FROM learning_tasks WHERE source_id = ? ORDER BY created_at DESC, rowid DESC LIMIT 1",
                    (source["id"],)).fetchone()
                pass_id = latest["pass_id"] if latest else _new_id("pass")
                if latest:
                    _merge(connection, pass_id, headings)
                    entries = _entries(connection, pass_id)
                    if any(entry["ticked_at"] and not entry["removed"] for entry in entries):
                        minutes = study_minutes(_profile_left(entries, source["origin"], texts[source["id"]], profile)[0])
                item = {"date": (first + timedelta(days=offset if one_a_day else 0)).isoformat(),
                        "title": _REVISION.sub("", source["title"]), "detail": "", "domain": LEARNING, "goalId": goal_id or None,
                        "startTime": None, "durationMinutes": None, "estimateMinutes": minutes,
                        "constraintKind": "flexible", "repeatKind": "none",
                        "learning": {"sourceId": source["id"], "passId": pass_id, "checklist": headings, "profile": profile,
                                     "effortBy": by}}
                made.append(self.store._create_item(connection, item))
        return {"tasks": [self.store.daily_item(item_id) for item_id in made],
                "goal": next((entry for entry in self.store.goals() if entry["id"] == goal_id), None) if goal_id else None}

    def task(self, item_id: str) -> dict:
        """A Learning task's checklist with its pass's ticks and when and where each was made, its progress, its
        source, effort and whose it is, the task it continues, its website's check as it started, the Library
        sources it links as references ("references"), and how long its source's sections take ("pace", see
        patterns.source_pace); a Learning task with no checklist yet has an empty one.

        Raises:
            SourceError: For a task that isn't there, or isn't a Learning task.
        """
        with self.store.connect() as connection:
            item = connection.execute("SELECT domain FROM daily_items WHERE id = ?", (item_id,)).fetchone()
            row = connection.execute(
                f"""SELECT {_TASK_COLUMNS} FROM learning_tasks l LEFT JOIN knowledge_sources s ON s.id = l.source_id
                    WHERE l.item_id = ?""", (item_id,)).fetchone()
            if not item:
                raise SourceNotFound("That task isn't there.")
            if not row and item["domain"] != LEARNING:
                raise SourceError("Only Learning tasks have a checklist.")
            entries = _entries(connection, row["pass_id"]) if row else []
        return {**_view(item_id, row, entries), "references": self.store.task_links(item_id),
                "pace": source_pace(self.store.pace_tasks(), row["source_id"]) if row and row["source_id"] else None}

    def _open(self, connection: sqlite3.Connection, item_id: str, now: datetime, past: bool = False,
              create: bool = False) -> str:
        """The pass whose checklist a task shows, to change it: a Learning task's, today's or a later day's
        unless `past` (Ava's confirmed card), started for one with no checklist yet when `create`.

        Raises:
            SourceError: For a task that isn't a Learning task, or has no checklist and none is started.
            PermissionError: For a past task, unless `past`.
        """
        item = connection.execute("SELECT item_date, domain FROM daily_items WHERE id = ?", (item_id,)).fetchone()
        row = connection.execute("SELECT pass_id FROM learning_tasks WHERE item_id = ?", (item_id,)).fetchone()
        if not item:
            raise SourceNotFound("That task isn't there.")
        if not row and item["domain"] != LEARNING:
            raise SourceError("Only Learning tasks have a checklist.")
        if item["item_date"] < now.date().isoformat() and not past:
            raise PermissionError(_PAST)
        if row:
            return row["pass_id"]
        if not create:
            raise SourceError("That item isn't in the task's checklist.")
        pass_id = _new_id("pass")
        connection.execute("INSERT INTO learning_tasks (item_id, pass_id, created_at) VALUES (?, ?, ?)",
                           (item_id, pass_id, datetime.now(timezone.utc).isoformat()))
        return pass_id

    @staticmethod
    def _entry(connection: sqlite3.Connection, pass_id: str, entry_id: str) -> sqlite3.Row:
        """A checklist item on show in a pass.

        Raises:
            SourceError: For an item the checklist doesn't show.
        """
        entry = connection.execute("SELECT * FROM checklist_items WHERE id = ? AND pass_id = ? AND removed = 0",
                                   (entry_id, pass_id)).fetchone()
        if not entry:
            raise SourceError("That item isn't in the task's checklist.")
        return entry

    def tick(self, item_id: str, entry_id: str, done: bool, now: datetime, confirmed: bool = False) -> dict:
        """Tick a checklist item as finished, with when and on which task, or untick it; an item ticked already
        keeps its first tick. A past task's checklist changes only through Ava, as her confirmed card applies it.

        Returns:
            The task, as task() gives it.

        Raises:
            SourceError: For an item the task's checklist doesn't show.
            PermissionError: For a past task, unless confirmed through Ava.
        """
        with self.store.connect() as connection:
            entry = self._entry(connection, self._open(connection, item_id, now, past=confirmed), entry_id)
            if done and not entry["ticked_at"]:
                connection.execute("UPDATE checklist_items SET ticked_at = ?, ticked_on = ? WHERE id = ?",
                                   (now.isoformat(), item_id, entry_id))
            elif not done:
                connection.execute("UPDATE checklist_items SET ticked_at = NULL, ticked_on = NULL WHERE id = ?", (entry_id,))
        return self.task(item_id)

    def add_to_checklist(self, item_id: str, title: str, now: datetime) -> dict:
        """Add an item of the user's own at the end of a Learning task's checklist, starting one if it has none.

        Raises:
            SourceError: For an empty name, or a task that isn't a Learning task.
            PermissionError: For a past task.
        """
        name = title.strip()
        if not name:
            raise SourceError("Name the item.")
        with self.store.connect() as connection:
            pass_id = self._open(connection, item_id, now, create=True)
            end = connection.execute("SELECT COALESCE(MAX(position) + 1, 0) FROM checklist_items WHERE pass_id = ?",
                                     (pass_id,)).fetchone()[0]
            connection.execute(
                """INSERT INTO checklist_items (id, pass_id, position, title, added_by, created_at)
                   VALUES (?, ?, ?, ?, 'you', ?)""", (_new_id("check"), pass_id, end, name, datetime.now(timezone.utc).isoformat()))
        return self.task(item_id)

    def rename_in_checklist(self, item_id: str, entry_id: str, title: str, now: datetime) -> dict:
        """Rename a checklist item; one from the source still answers to the heading it came from.

        Raises:
            SourceError: For an empty name, or an item the checklist doesn't show.
            PermissionError: For a past task.
        """
        name = title.strip()
        if not name:
            raise SourceError("Name the item.")
        with self.store.connect() as connection:
            self._entry(connection, self._open(connection, item_id, now), entry_id)
            connection.execute("UPDATE checklist_items SET title = ? WHERE id = ?", (name, entry_id))
        return self.task(item_id)

    def remove_from_checklist(self, item_id: str, entry_id: str, now: datetime) -> dict:
        """Remove a checklist item: the user's own goes; one from the source is kept out of sight, so a later
        reading of the source doesn't bring it back.

        Raises:
            SourceError: For an item the checklist doesn't show.
            PermissionError: For a past task.
        """
        with self.store.connect() as connection:
            entry = self._entry(connection, self._open(connection, item_id, now), entry_id)
            if entry["added_by"] == "you":
                connection.execute("DELETE FROM checklist_items WHERE id = ?", (entry_id,))
            else:
                connection.execute("UPDATE checklist_items SET removed = 1, ticked_at = NULL, ticked_on = NULL WHERE id = ?",
                                   (entry_id,))
        return self.task(item_id)

    def move_in_checklist(self, item_id: str, entry_id: str, index: int, now: datetime) -> dict:
        """Move a checklist item to `index` among the items on show, the rest keeping their order.

        Raises:
            SourceError: For an item the checklist doesn't show.
            PermissionError: For a past task.
        """
        with self.store.connect() as connection:
            pass_id = self._open(connection, item_id, now)
            self._entry(connection, pass_id, entry_id)
            entries = _entries(connection, pass_id)
            shown = [entry["id"] for entry in entries if not entry["removed"] and entry["id"] != entry_id]
            shown.insert(max(0, min(index, len(shown))), entry_id)
            placed = iter(shown)
            order = [next(placed) if not entry["removed"] else entry["id"] for entry in entries]
            for position, moved in enumerate(order):
                connection.execute("UPDATE checklist_items SET position = ? WHERE id = ?", (position, moved))
        return self.task(item_id)

    def progress_by_source(self) -> dict[str, dict]:
        """Each file's progress, for every source a task was made from: its latest pass's items ticked of those on
        show, {source id: {"done", "total"}}."""
        with self.store.connect() as connection:
            rows = connection.execute(
                """SELECT l.source_id, COUNT(c.id) AS total, COUNT(c.ticked_at) AS done FROM learning_tasks l
                   LEFT JOIN checklist_items c ON c.pass_id = l.pass_id AND c.removed = 0
                   WHERE l.source_id IS NOT NULL AND l.rowid = (SELECT o.rowid FROM learning_tasks o WHERE o.source_id = l.source_id
                                                                ORDER BY o.created_at DESC, o.rowid DESC LIMIT 1)
                   GROUP BY l.source_id""").fetchall()
        return {row["source_id"]: {"done": row["done"], "total": row["total"]} for row in rows}

    def set_effort(self, item_id: str, effort: str) -> dict:
        """Set a task's effort as the user sees it; reading its source again keeps it.

        Raises:
            SourceError: For an effort that isn't light, steady or deep, or a task with no source or checklist.
        """
        if effort not in EFFORTS:
            raise SourceError("Effort is light, steady or deep.")
        learned = self.task(item_id)
        if not learned["passId"]:
            raise SourceError("That task wasn't made from a source.")
        with self.store.connect() as connection:
            connection.execute("UPDATE learning_tasks SET profile_json = ?, effort_by = 'you' WHERE item_id = ?",
                               (json.dumps({**learned["profile"], "effort": effort}, ensure_ascii=False), item_id))
        return self.task(item_id)

    def follow_up(self, item_id: str, day: str) -> dict:
        """The follow-up Ava proposes for a task partly done, on `day`, to be saved only on Confirm: the same
        source, goal and pass, so the whole checklist with its ticks, and a length for the items still unticked,
        at the pace items went on this task when some were ticked on it, else from what is left of the text.

        Returns:
            The new task as Ava's card carries it, with "left", the items still to study: unticked, and still in
            their source; one no longer there stays on the checklist but isn't counted.

        Raises:
            SourceError: When nothing is left to study, so nothing is left to continue.
        """
        learned, item = self.task(item_id), self.store.daily_item(item_id)
        with self.store.connect() as connection:
            entries = _entries(connection, learned["passId"]) if learned["passId"] else []
        left = [entry["title"] for entry in _to_study(entries)]
        if not left:
            raise SourceError("Every item is ticked, so nothing is left to continue.")
        source = self.source_of(learned["sourceId"])
        text = self._text(source)
        profile, by = _profile_left(entries, source and source["origin"], text, learned["profile"])
        if learned["effortBy"] == "you":
            profile, by = {**profile, "effort": learned["effort"]}, "you"
        done_here = sum(1 for entry in entries if not entry["removed"] and entry["ticked_on"] == item_id)
        if done_here and item["duration_minutes"]:
            minutes = max(MIN_TASK_MINUTES, ceil(item["duration_minutes"] / done_here * len(left) / SLOT_MINUTES) * SLOT_MINUTES)
        else:
            minutes = study_minutes(profile)
        return {"date": day, "title": item["title"], "detail": "", "goalId": item["goalId"], "domain": item["domain"],
                "startTime": None, "durationMinutes": None, "estimateMinutes": minutes, "constraintKind": "flexible",
                "repeatKind": "none", "left": left,
                "learning": {"sourceId": learned["sourceId"], "passId": learned["passId"], "profile": profile,
                             "effortBy": by, "followsItemId": item_id}}

    def study_left(self, item_id: str) -> dict:
        """What is left to study on a task, for "What will I learn today?": the items still unticked, and the
        text of those from a file, read now on this Mac (None for a website's, which keeps no text)."""
        learned = self.task(item_id)
        text = self._text(self.source_of(learned["sourceId"]))
        with self.store.connect() as connection:
            entries = _to_study(_entries(connection, learned["passId"])) if learned["passId"] else []
        parts = "\n\n".join(section_text(text, entry["heading"], entry["level"] or 2)
                            for entry in entries if entry["heading"]) if text else ""
        return {"left": [entry["title"] for entry in entries], "text": parts.strip() or None}

    def next_unstudied(self, goal_id: str) -> dict | None:
        """A goal's next task to study: its first, by day and by when it was made, not yet fully done; None
        once every one is."""
        with self.store.connect() as connection:
            row = connection.execute(
                """SELECT id FROM daily_items WHERE goal_id = ? AND acceptance = 'accepted' AND completion_status != 'done'
                   ORDER BY item_date, start_time IS NULL, start_time, rowid LIMIT 1""", (goal_id,)).fetchone()
        return self.store.daily_item(row["id"]) if row else None

    def check_due(self, now: datetime) -> list[str]:
        """Look up again the websites of timed tasks whose start has come, each once: at its start time, or the
        next time DayWright runs after it, as long as the task has no status yet.

        Returns:
            The tasks checked.
        """
        with self.store.connect() as connection:
            due = [row["item_id"] for row in connection.execute(
                """SELECT l.item_id FROM learning_tasks l JOIN daily_items i ON i.id = l.item_id
                   JOIN knowledge_sources s ON s.id = l.source_id
                   WHERE s.origin = 'website' AND l.start_checked_at IS NULL AND i.completion_status = 'planned'
                     AND i.acceptance = 'accepted' AND i.start_time IS NOT NULL AND i.item_date || ' ' || i.start_time <= ?
                   ORDER BY i.item_date, i.start_time""", (now.strftime("%Y-%m-%d %H:%M"),))]
        found: dict[str, str] = {}
        checked = [item_id for item_id in due if self._claim(item_id, now)]
        for item_id in checked:
            self._check(item_id, now, found)
        return checked

    def briefing_opened(self, item_id: str, now: datetime) -> None:
        """Look an untimed task's website up again the first time its briefing is opened on its day, as that is
        when it starts, as long as it has no status yet; any other task is left as it is."""
        with self.store.connect() as connection:
            due = connection.execute(
                """SELECT 1 FROM learning_tasks l JOIN daily_items i ON i.id = l.item_id
                   JOIN knowledge_sources s ON s.id = l.source_id
                   WHERE l.item_id = ? AND s.origin = 'website' AND l.start_checked_at IS NULL AND i.start_time IS NULL
                     AND i.completion_status = 'planned' AND i.acceptance = 'accepted' AND i.item_date = ?""",
                (item_id, now.date().isoformat())).fetchone()
        if due and self._claim(item_id, now):
            self._check(item_id, now, {})

    def _claim(self, item_id: str, now: datetime) -> bool:
        """Take a task's one start check, so two opens at once, or an open and the minute's round, look its
        website up once between them.

        Returns:
            Whether this caller took it; False when another already had.
        """
        with self.store.connect() as connection:
            return connection.execute("UPDATE learning_tasks SET start_checked_at = ? WHERE item_id = ? AND start_checked_at IS NULL",
                                      (now.isoformat(), item_id)).rowcount == 1

    def _check(self, item_id: str, now: datetime, found: dict[str, str]) -> None:
        """Look a task's website up again, once per source in one round (`found`), and keep when and what came
        of it; a changed page brings its tasks up to date."""
        source_id = self.task(item_id)["sourceId"]
        if source_id not in found:
            found[source_id] = self.shelf.recheck(source_id, now)
            if found[source_id] == "updated":
                self._follow_page(source_id)
        with self.store.connect() as connection:
            connection.execute("UPDATE learning_tasks SET start_checked_at = ?, start_check = ? WHERE item_id = ?",
                               (now.isoformat(), found[source_id], item_id))

    def _follow_page(self, source_id: str) -> None:
        """Bring the tasks still to do from a website up to date with its page: their checklists merged, their
        effort from its headings unless the user set it, and, when the checklist changed, their estimated
        length for the items still to study; a length the user set never changes."""
        self._follow_source(self.shelf.source(source_id), "")

    def _follow_source(self, source: dict, text: str) -> None:
        """Bring the tasks still to do from a source up to date with its latest reading (see _follow_page and
        refresh_profiles): each pass's checklist merged once, each task's profile and effort unless the user
        set it, and an estimated length for what is left when the checklist changed or its text was read."""
        headings = checklist_of(source["outline"])
        whole, by = self._profile(source, text, headings)
        estimates = []
        with self.store.connect() as connection:
            rows = connection.execute(
                """SELECT l.item_id, l.pass_id, l.profile_json, l.effort_by FROM learning_tasks l JOIN daily_items i ON i.id = l.item_id
                   WHERE l.source_id = ? AND i.completion_status = 'planned' AND i.acceptance = 'accepted'""",
                (source["id"],)).fetchall()
            merged: dict[str, bool] = {}
            for row in rows:
                if row["pass_id"] not in merged:
                    merged[row["pass_id"]] = _merge(connection, row["pass_id"], headings)
                kept, kept_by = whole, by
                if row["effort_by"] == "you":
                    kept, kept_by = {**whole, "effort": json.loads(row["profile_json"]).get("effort", DEFAULT_EFFORT)}, "you"
                connection.execute("UPDATE learning_tasks SET profile_json = ?, effort_by = ? WHERE item_id = ?",
                                   (json.dumps(kept, ensure_ascii=False), kept_by, row["item_id"]))
                if merged[row["pass_id"]] or source["origin"] != "website":
                    entries = _entries(connection, row["pass_id"])
                    ticked = any(entry["ticked_at"] and not entry["removed"] for entry in entries)
                    profile = _profile_left(entries, source["origin"], text, whole)[0] if ticked or source["origin"] == "website" else whole
                    estimates.append((row["item_id"], study_minutes(profile)))
        for item_id, minutes in estimates:
            self.store.apply_model_estimate(item_id, minutes, LEARNING_ESTIMATE_BASIS)

    def refresh_profiles(self, source_ids: list[str]) -> None:
        """Read again the tasks still to do from files that changed, as a folder's Refresh does: their checklists
        merged with the file's headings, their effort unless the user set it, and their estimated length."""
        for source_id in source_ids:
            source = self.source_of(source_id)
            if source is not None:
                self._follow_source(source, self._text(source))
