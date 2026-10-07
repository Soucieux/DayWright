from __future__ import annotations

import json
import hashlib
import re
import sqlite3
import uuid
from contextlib import closing, contextmanager
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Callable, Iterable

import sqlite_vec

from .area_choice import keyword_area
from .estimates import DEFAULT_ESTIMATE_MINUTES, ESTIMATE_STEP_MINUTES, TAKEN_BASIS
from .periods import period_keys
from .profiles import task_profile
from .sources import combined_profile, library_name, study_minutes
from .meals import PREFERENCE_KEY as MEALS_KEY, SMALL_MEAL_OVERLAP_MINUTES, Meal, meals_on, one_day, one_day_changes, standing
from .planner import (DAY_END, DOMAIN_LABELS, MIN_TRIMMED_MINUTES, SLOT_MINUTES, PlanItem, StudyTask,
                      build_recorded_variants, build_variants, clock_time, day_load, fit_around_meal, meal_overlap,
                      minutes_after_midnight, notes_without)
from .time_taken import (AFTER_DAY, actual_times, current_and_next, limit_stopped, minutes_taken, taken_so_far,
                         title_line)

# A day's length, which no task may run past.
MINUTES_PER_DAY = 24 * 60
# How far back the plans the user set count toward which kinds of plan come first.
PREFERENCE_DAYS = 30
# The shortest length a task may have, given in the form or through Ava, or estimated.
MIN_TASK_MINUTES = 30
# How many plans a day is offered: Balanced and two others.
PLAN_COUNT = 3
# How many days, to the day on show, Today's finishing graph covers.
FINISHING_DAYS = 7
# What a Learning task's length rests on when its source gave it (see learning_tasks).
LEARNING_ESTIMATE_BASIS = "source"
# The preference that keeps the interface's language, for the menu bar's title.
INTERFACE_LANGUAGE_KEY = "interface_language"
# The preference that keeps the last day whose notice on Today the user dismissed.
NOTICE_DISMISSED_KEY = "yesterday_notice_dismissed"
# The preference that keeps what the last catch-up save changed, until it is undone or replaced.
CATCH_UP_UNDO_KEY = "catch_up_undo"
# A time a task took of this many times its length or more, as one stopped at its limit took (see
# time_taken.LIMIT_FACTOR), is one to check: it stays out of estimates, profiles and graphs until the
# user confirms it.
CHECK_TIME_FACTOR = 2
# When at least USUAL_DIFFERS of a task's last USUAL_LOOKBACK done times differ by USUAL_DIFFERENCE
# minutes or more from the length the user set, its area agent offers to change it.
USUAL_LOOKBACK = 4
USUAL_DIFFERS = 3
USUAL_DIFFERENCE = 10
# The tables of the online lookup and its network log, which DayWright no longer has.
_ONLINE_TABLES = ("knowledge_import_plans", "knowledge_acquisitions", "network_log")
# How much of a note's or file's opening text, with its title, suggests its area.
OPENING_CHARACTERS = 500

# A task named without quotation marks in a plan's rationale, as every earlier version wrote them:
# Focused gives one more time, Gentle shortens one, and the oldest plans added or shortened one.
_UNQUOTED_RATIONALE_TASK = re.compile(
    r"(, and gives |; shortens |^Adds 15 minutes to |^Shortens )(?!“)(.+?)"
    r"( 15 more minutes;| by 15 minutes without removing it;| where the saved calendar has room;"
    r"| by 15 minutes, never removes it;)")


# A task whose goal is paused is paused with it: plans skip it, and it can't be reported.
_GOAL_NOT_PAUSED = "NOT EXISTS (SELECT 1 FROM goals WHERE goals.id = daily_items.goal_id AND goals.status = 'paused')"
_PAUSED_MESSAGE = "This task's goal is paused; resume the goal to report it"
# A task a set plan scheduled stays on its day, today's or a past one: only replacing the plan changes it.
_IN_SET_PLAN = """EXISTS (SELECT 1 FROM plan_entries entry
    JOIN daily_confirmations confirmation ON confirmation.variant_id = entry.variant_id
    WHERE entry.source_item_id = daily_items.id)"""
_SET_PLAN_KEEPS_MESSAGE = "A confirmed plan scheduled this record; confirmed days remain read-only"
_PAST_TASK_MESSAGE = "A past task changes only through Ava; ask Ava to change it"
# A task's fields as the service shows it.
_ITEM_FIELDS = """id, item_date AS date, goal_id AS goalId, title, detail, domain,
    start_time, duration_minutes, constraint_kind,
    repeat_kind AS repeatKind, repeat_series_id AS repeatSeriesId, origin_kind AS originKind,
    origin_detail AS originDetail, origin_source_item_id AS originSourceItemId,
    completion_status, acceptance, duration_source AS durationSource,
    estimated_by AS estimatedBy, estimate_basis AS estimateBasis, created_at AS createdAt,
    status_at AS statusAt, actual_start AS actualStart, actual_end AS actualEnd, actual_minutes AS actualMinutes,
    current_since AS currentSince, time_confirmed AS timeConfirmed,
    (SELECT status FROM goals WHERE goals.id = daily_items.goal_id) AS goalStatus"""

# The areas a goal, task or plan entry belongs to, as an SQL list for CHECK constraints.
_AREA_LIST = ", ".join(f"'{domain}'" for domain in DOMAIN_LABELS)

# When a task's status was set and the time it actually took, "HH:MM" on its day (see time_taken): its
# first stretch's start, its last stretch's stop, and the minutes it was current between them, every
# stretch added up (none for a time kept before they were, which took from its start to its stop);
# when DayWright first saw it current, and whether the user confirmed a time flagged to check.
_TIME_COLUMN_LIST = ("status_at TEXT", "actual_start TEXT", "actual_end TEXT", "actual_minutes INTEGER",
                     "current_since TEXT", "time_confirmed INTEGER NOT NULL DEFAULT 0")
_TIME_COLUMNS = ",\n            ".join(_TIME_COLUMN_LIST)

# Tables whose CHECK constraints name the areas. Each is written with a `{table}` placeholder so a
# migration can build the current shape beside an older table and copy rows across.
_AREA_TABLES = {
    "plan_entries": f"""
        CREATE TABLE IF NOT EXISTS {{table}} (
            id TEXT PRIMARY KEY,
            variant_id TEXT NOT NULL REFERENCES plan_variants(id) ON DELETE CASCADE,
            position INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            title TEXT NOT NULL,
            detail TEXT NOT NULL,
            source_item_id TEXT REFERENCES daily_items(id),
            domain TEXT NOT NULL CHECK(domain IN ({_AREA_LIST})),
            duration_minutes INTEGER NOT NULL CHECK(duration_minutes > 0),
            constraint_kind TEXT NOT NULL CHECK(constraint_kind IN ('fixed', 'flexible')),
            completion_status TEXT NOT NULL DEFAULT 'planned' CHECK(completion_status IN ('planned', 'done', 'partial', 'skipped')),
            removed_at TEXT,
            moved_to TEXT,
            UNIQUE(variant_id, position)
        );""",
    "suggestion_pool": f"""
        CREATE TABLE IF NOT EXISTS {{table}} (
            id TEXT PRIMARY KEY,
            period_kind TEXT NOT NULL CHECK(period_kind IN ('day', 'week', 'month')),
            period_key TEXT NOT NULL,
            domain TEXT NOT NULL CHECK(domain IN ({_AREA_LIST}, 'cross')),
            content TEXT NOT NULL,
            priority TEXT NOT NULL CHECK(priority IN ('soft', 'strong')),
            source_key TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'discarded')),
            discarded_at TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(period_kind, period_key, source_key)
        );""",
    "goals": f"""
        CREATE TABLE IF NOT EXISTS {{table}} (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            domain TEXT NOT NULL CHECK(domain IN ({_AREA_LIST})),
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'paused', 'completed')),
            created_at TEXT NOT NULL
        );""",
    # A flexible task has no start time until a plan places it; a fixed one always has one.
    "daily_items": f"""
        CREATE TABLE IF NOT EXISTS {{table}} (
            id TEXT PRIMARY KEY,
            item_date TEXT NOT NULL,
            goal_id TEXT REFERENCES goals(id),
            title TEXT NOT NULL,
            detail TEXT NOT NULL DEFAULT '',
            domain TEXT NOT NULL CHECK(domain IN ({_AREA_LIST})),
            start_time TEXT,
            duration_minutes INTEGER NOT NULL CHECK(duration_minutes > 0),
            constraint_kind TEXT NOT NULL CHECK(constraint_kind IN ('fixed', 'flexible')),
            repeat_kind TEXT NOT NULL DEFAULT 'none' CHECK(repeat_kind IN ('none', 'daily', 'weekly')),
            repeat_series_id TEXT,
            protected INTEGER NOT NULL DEFAULT 0 CHECK(protected IN (0, 1)),
            origin_kind TEXT NOT NULL DEFAULT 'user' CHECK(origin_kind IN ('user', 'agent-origin')),
            origin_detail TEXT NOT NULL DEFAULT '',
            origin_source_item_id TEXT REFERENCES daily_items(id),
            completion_status TEXT NOT NULL DEFAULT 'planned' CHECK(completion_status IN ('planned', 'done', 'partial', 'skipped')),
            acceptance TEXT NOT NULL DEFAULT 'accepted' CHECK(acceptance IN ('accepted', 'pending', 'dismissed')),
            created_at TEXT NOT NULL,
            duration_source TEXT NOT NULL DEFAULT 'user' CHECK(duration_source IN ('user', 'estimate')),
            estimated_by TEXT,
            estimate_basis TEXT,
            {_TIME_COLUMNS},
            CHECK(start_time IS NOT NULL OR constraint_kind = 'flexible')
        );""",
    "agent_runs": """
        CREATE TABLE IF NOT EXISTS {table} (
            id TEXT PRIMARY KEY,
            message_id TEXT NOT NULL REFERENCES conversation_messages(id) ON DELETE CASCADE,
            sequence INTEGER NOT NULL,
            agent_key TEXT NOT NULL CHECK(agent_key IN ('orchestrator', 'learning', 'life', 'work', 'project', 'summary')),
            phase TEXT NOT NULL CHECK(phase IN ('dispatch', 'assessment', 'summary', 'synthesis')),
            summary TEXT NOT NULL,
            reads_json TEXT NOT NULL,
            writes_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(message_id, sequence)
        );""",
}

# Indexes on `daily_items`, rebuilt whenever the table is.
_DAILY_ITEM_INDEXES = """
    CREATE INDEX IF NOT EXISTS daily_items_by_date ON daily_items(item_date);
    CREATE INDEX IF NOT EXISTS daily_items_by_series ON daily_items(repeat_series_id);
    CREATE UNIQUE INDEX IF NOT EXISTS future_origin_once
        ON daily_items(item_date, origin_source_item_id)
        WHERE origin_source_item_id IS NOT NULL;
"""

# The areas DayWright no longer has. Their tasks, goals and plan entries now belong to Life.
_RETIRED_AREAS = ("finance", "rest")

# Money's own records, deleted with the area.
_MONEY_TABLES = ("finance_entries", "finance_account", "finance_transactions", "finance_budgets")

# Learning's and Life's own records before v3.5, folded into tasks and goals and then dropped.
_AREA_RECORD_TABLES = ("learning_sessions", "learning_items", "life_habit_logs", "life_habits", "life_daily",
                       "life_events")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _local_time() -> str:
    """Return the Mac's local time now as "HH:MM", before which a plan places nothing today."""
    return datetime.now().strftime("%H:%M")


def _taken(start: str | None, end: str | None, taken: int | None) -> int | None:
    """Return the minutes a task took: every stretch it was current added up, or for a time kept before
    those were, from its start to its stop; None when no time was kept."""
    if not (start and end):
        return None
    return taken if taken is not None else minutes_after_midnight(end) - minutes_after_midnight(start)


def _time_to_check(start: str | None, end: str | None, minutes: int, confirmed: bool, taken: int | None) -> bool:
    """Whether the time a task took (see _taken) is one to check: CHECK_TIME_FACTOR times the `minutes`
    it had that day or more, as a task stopped at its limit took, and not yet confirmed by the user."""
    took = _taken(start, end, taken)
    return took is not None and not confirmed and took >= CHECK_TIME_FACTOR * minutes


def _counted_time(start: str | None, end: str | None, minutes: int, confirmed: bool, taken: int | None) -> int | None:
    """Return the minutes a task took (see _taken) as estimates, profiles and graphs count them, or None
    when no time was kept or the time is one to check (see _time_to_check)."""
    if _time_to_check(start, end, minutes, confirmed, taken):
        return None
    return _taken(start, end, taken)


def _stepped(minutes: float) -> int:
    """Round a length to the nearest ESTIMATE_STEP_MINUTES."""
    return int(round(minutes / ESTIMATE_STEP_MINUTES) * ESTIMATE_STEP_MINUTES)


def _advice_key(domain: str, content: str) -> str:
    """Return the key that recognizes the same advice in one area, however it is cased or spaced."""
    return hashlib.sha256(
        f"{domain}\0{' '.join(content.lower().split())}".encode("utf-8")
    ).hexdigest()[:24]


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _add_learning(connection: sqlite3.Connection, item_id: str, learning: dict) -> None:
    """Record a new task as a Learning task with a checklist: a new pass's, which `learning` lists, or one it
    carries on, which keeps its own.

    Args:
        learning: {"sourceId" (or None), "passId", "checklist" ([{"title", "level"}] for a new pass's
            headings), "profile", "effortBy", "followsItemId" (optional)}.
    """
    connection.execute(
        """INSERT INTO learning_tasks (item_id, source_id, pass_id, profile_json, effort_by, follows_item_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (item_id, learning.get("sourceId"), learning["passId"], json.dumps(learning.get("profile", {}), ensure_ascii=False),
         learning.get("effortBy", "text"), learning.get("followsItemId"), _now()))
    if not connection.execute("SELECT 1 FROM checklist_items WHERE pass_id = ?", (learning["passId"],)).fetchone():
        add_checklist(connection, learning["passId"], learning.get("checklist", []))


def add_checklist(connection: sqlite3.Connection, pass_id: str, headings: list[dict], start: int = 0) -> list[str]:
    """Add a source's headings to a pass's checklist, from position `start`, each named as its heading.

    Args:
        headings: [{"title", "level"}], as sources.checklist_of gives them.

    Returns:
        The new items' ids, in order.
    """
    ids = []
    for offset, heading in enumerate(headings):
        ids.append(_id("check"))
        connection.execute(
            """INSERT INTO checklist_items (id, pass_id, position, title, heading, level, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (ids[-1], pass_id, start + offset, heading["title"], heading["title"], heading.get("level", 2), _now()))
    return ids


def move_topics_to_tasks(connection: sqlite3.Connection, day: str) -> None:
    """Move v4.5's goals made from a file, once, to how studying a file now works: one Learning task for
    the file, its sections a checklist inside it. Each such goal keeps its name and its tasks, and gains
    one untimed task for the file on `day`, titled as the file is, whose checklist is the goal's topics
    in order; a topic studied (a task for it fully done) is ticked, and its task stays as it is. The
    task's effort and length come from its topics' profiles together. Then the topics and the tasks'
    link to them go. A database that never had topics is left as it is.

    Args:
        connection: An open connection, its rows readable by name.
        day: The day each file's task is put on, YYYY-MM-DD.
    """
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'goal_topics'").fetchone():
        return
    linked = "topic_id" in {row["name"] for row in connection.execute("PRAGMA table_info(daily_items)")}
    topics: dict[str, list[sqlite3.Row]] = {}
    for topic in connection.execute("SELECT * FROM goal_topics ORDER BY goal_id, position").fetchall():
        topics.setdefault(topic["goal_id"], []).append(topic)
    for goal_id, listed in topics.items():
        profiles = [json.loads(topic["profile_json"]) for topic in listed]
        profile = combined_profile(profiles)
        source_id = next((topic["source_id"] for topic in listed if topic["source_id"]), None)
        item_id = _id("item")
        connection.execute(
            """INSERT INTO daily_items (id, item_date, goal_id, title, detail, domain, start_time, duration_minutes,
                   constraint_kind, created_at, duration_source, estimated_by, estimate_basis)
               VALUES (?, ?, ?, ?, '', 'learning', NULL, ?, 'flexible', ?, 'estimate', 'learning', ?)""",
            (item_id, day, goal_id, listed[0]["heading"] or listed[0]["title"], max(study_minutes(profile), MIN_TASK_MINUTES),
             _now(), LEARNING_ESTIMATE_BASIS))
        pass_id = _id("pass")
        _add_learning(connection, item_id, {"sourceId": source_id, "passId": pass_id, "profile": profile, "effortBy": "text",
                                            "checklist": [{"title": topic["title"], "level": 2} for topic in listed]})
        entries = connection.execute("SELECT id FROM checklist_items WHERE pass_id = ? ORDER BY position", (pass_id,)).fetchall()
        for topic, entry in zip(listed, entries):
            studied = linked and connection.execute(
                """SELECT id, item_date FROM daily_items WHERE topic_id = ? AND completion_status = 'done'
                   ORDER BY item_date LIMIT 1""", (topic["id"],)).fetchone()
            if studied:
                connection.execute("UPDATE checklist_items SET ticked_at = ?, ticked_on = ? WHERE id = ?",
                                   (f"{studied['item_date']}T00:00:00", studied["id"], entry["id"]))
    connection.execute("DROP TABLE goal_topics")
    if linked:
        connection.execute("ALTER TABLE daily_items DROP COLUMN topic_id")


def _delete_sources(connection: sqlite3.Connection, source_ids: list[str]) -> None:
    """Delete Library sources for good, with their passages, their passages' vectors, the records of Ava having
    drawn on them, and every task's link to them. A learning task made from one keeps its checklist and ticks.

    Args:
        connection: An open connection, its rows readable by name.
        source_ids: The sources to delete; none changes nothing.
    """
    if not source_ids:
        return
    marks = ",".join("?" for _ in source_ids)
    chunks = [row[0] for row in connection.execute(f"SELECT id FROM knowledge_chunks WHERE source_id IN ({marks})", source_ids)]
    if chunks and connection.execute("SELECT 1 FROM sqlite_master WHERE name = 'knowledge_chunk_vectors'").fetchone():
        # The vectors live in a virtual table that only the vector extension can change.
        connection.enable_load_extension(True)
        connection.load_extension(sqlite_vec.loadable_path())
        connection.enable_load_extension(False)
        connection.executemany("DELETE FROM knowledge_chunk_vectors WHERE rowid = ?", [(chunk,) for chunk in chunks])
    connection.execute(f"DELETE FROM retrieval_matches WHERE source_id IN ({marks})", source_ids)
    connection.execute(f"DELETE FROM task_sources WHERE source_id IN ({marks})", source_ids)
    connection.execute(f"UPDATE learning_tasks SET source_id = NULL WHERE source_id IN ({marks})", source_ids)
    connection.execute(f"DELETE FROM knowledge_sources WHERE id IN ({marks})", source_ids)


def _writable_day(plan_date: str) -> None:
    if plan_date != date.today().isoformat():
        raise PermissionError("Only today's plan and outcomes can be changed; past plans are read-only")


def _day_order(task: dict) -> tuple:
    """Order a day's tasks as time_taken reads them: scheduled ones by start, then those without a start time
    in the order they were made."""
    return task["start"] is None, task["start"] or "", task["createdAt"]


def _writable_item_day(item_date: str) -> None:
    if item_date < date.today().isoformat():
        raise PermissionError("Past daily records are read-only")


def edited_task(task: dict, changes: dict) -> dict:
    """Return a task as an edit leaves it, in the shape update_daily_item takes: its fields as they
    are, with the edit's changes over them.

    A task given a new start becomes fixed at it. One moved after today goes back to planned, as a
    day is reported only once it comes. A length the edit leaves alone stays the user's, or stays
    the area agent's estimate.

    Args:
        task: The task as the service shows it.
        changes: The new values by field: "title", "detail", "domain", "goalId", "date",
            "startTime", "durationMinutes" or "status".
    """
    day = changes.get("date", task["date"])
    moved = "startTime" in changes and changes["startTime"] is not None
    return {
        "date": day,
        "title": changes.get("title", task["title"]),
        "detail": changes.get("detail", task["detail"]),
        "domain": changes.get("domain", task["domain"]),
        "goalId": changes.get("goalId", task["goalId"]),
        "startTime": changes.get("startTime", task["start_time"]),
        "durationMinutes": changes.get("durationMinutes",
                                       None if task["durationSource"] == "estimate" else task["duration_minutes"]),
        "constraintKind": "fixed" if moved else task["constraint_kind"],
        "repeatKind": task["repeatKind"],
        "status": "planned" if day > date.today().isoformat() else changes.get("status", task["completion_status"]),
    }


def _span(start: str, minutes: int) -> str:
    """Name a stretch of a day by its times, as "11:45–12:45"."""
    return f"{start}–{clock_time(minutes_after_midnight(start) + minutes)}"


def _clash_message(clash: dict) -> str:
    """Say which task or meal already takes a start time, and when."""
    end = minutes_after_midnight(clash["start_time"]) + clash["duration_minutes"]
    span = f"{clash['start_time']}–{clock_time(end)}"
    if clash.get("meal"):
        return f"{span} is kept for {clash['title'].lower()}; choose a start time that doesn't overlap it"
    return f"“{clash['title']}” ({span}) already takes that time; choose a start time that doesn't overlap it"


def _refuse_paused_day(connection: sqlite3.Connection, plan_date: str, items: list) -> None:
    """Say plainly why a day can't be planned when every task on it is paused with its goal.

    Raises:
        ValueError: When nothing is left to plan but the day has tasks whose goal is paused.
    """
    if not items and connection.execute(
            f"SELECT 1 FROM daily_items WHERE item_date = ? AND acceptance = 'accepted' AND NOT {_GOAL_NOT_PAUSED}",
            (plan_date,)).fetchone():
        raise ValueError("Every task on this day belongs to a paused goal; resume a goal to plan its tasks")


def _plan_item(row: sqlite3.Row) -> PlanItem:
    """Return a stored task as the planner reads it."""
    return PlanItem(row["start_time"], row["title"], row["detail"], row["domain"], row["duration_minutes"],
                    row["constraint_kind"], row["id"], row["duration_source"] == "estimate")


def _check_length(minutes: int | None, kept: int | None = None) -> None:
    """Refuse a length the user gives below MIN_TASK_MINUTES, unless the task already has it.

    Args:
        minutes: The length given, or None to have the area agent estimate one.
        kept: The task's stored length, which it may keep when it was set shorter earlier.
    """
    if minutes is not None and minutes < MIN_TASK_MINUTES and minutes != kept:
        raise ValueError(f"A length you give is at least {MIN_TASK_MINUTES} minutes; "
                         "leave it blank and the area agent estimates it")


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _migrate(self) -> None:
        with self.connect() as connection:
            # The tables there were before this start: a Library from v4.9 on has its task links.
            before = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;

                CREATE TABLE IF NOT EXISTS plan_sets (
                    id TEXT PRIMARY KEY,
                    plan_date TEXT NOT NULL UNIQUE,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS plan_variants (
                    id TEXT PRIMARY KEY,
                    plan_set_id TEXT NOT NULL REFERENCES plan_sets(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    notes_json TEXT NOT NULL DEFAULT '[]',
                    meals_json TEXT NOT NULL DEFAULT '[]',
                    version INTEGER NOT NULL DEFAULT 1,
                    supersedes_variant_id TEXT REFERENCES plan_variants(id),
                    created_at TEXT NOT NULL,
                    UNIQUE(plan_set_id, slug, version)
                );

                CREATE TABLE IF NOT EXISTS daily_confirmations (
                    plan_date TEXT PRIMARY KEY,
                    variant_id TEXT NOT NULL REFERENCES plan_variants(id),
                    confirmed_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS conversation_threads (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL REFERENCES conversation_threads(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    mode TEXT NOT NULL CHECK(mode IN ('ask', 'adjust', 'report')),
                    content TEXT NOT NULL,
                    model_mode TEXT,
                    created_at TEXT NOT NULL,
                    topic_date TEXT
                );

                CREATE TABLE IF NOT EXISTS proposed_actions (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL REFERENCES conversation_threads(id) ON DELETE CASCADE,
                    action_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'confirmed', 'dismissed')),
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS action_confirmations (
                    id TEXT PRIMARY KEY,
                    action_id TEXT NOT NULL UNIQUE REFERENCES proposed_actions(id) ON DELETE CASCADE,
                    decision TEXT NOT NULL CHECK(decision IN ('confirmed', 'dismissed')),
                    decided_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    provenance_message_id TEXT REFERENCES conversation_messages(id),
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS suggestions (
                    id TEXT PRIMARY KEY,
                    plan_date TEXT NOT NULL,
                    title TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    decision TEXT CHECK(decision IN ('kept', 'dismissed')),
                    decided_at TEXT
                );

                CREATE TABLE IF NOT EXISTS suggestion_notices (
                    period_kind TEXT NOT NULL,
                    period_key TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    source_key TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(period_kind, period_key, source_key)
                );

                CREATE TABLE IF NOT EXISTS cleared_suggestion_periods (
                    period_kind TEXT NOT NULL,
                    period_key TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    cleared_at TEXT NOT NULL,
                    PRIMARY KEY(period_kind, period_key, domain)
                );

                CREATE TABLE IF NOT EXISTS feedback_signals (
                    id TEXT PRIMARY KEY,
                    message_id TEXT NOT NULL REFERENCES conversation_messages(id) ON DELETE CASCADE,
                    request_date TEXT NOT NULL,
                    task_title TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    request_kind TEXT NOT NULL CHECK(request_kind IN ('shorten')),
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS summary_reports (
                    period_kind TEXT NOT NULL CHECK(period_kind IN ('day', 'week', 'month')),
                    period_key TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(period_kind, period_key)
                );

                CREATE TABLE IF NOT EXISTS task_profiles (
                    domain TEXT NOT NULL,
                    task_key TEXT NOT NULL,
                    title TEXT NOT NULL,
                    profile_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(domain, task_key)
                );

                CREATE TABLE IF NOT EXISTS ava_notices (
                    id TEXT PRIMARY KEY,
                    notice_date TEXT NOT NULL,
                    issue_key TEXT NOT NULL,
                    agent_key TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    values_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    read_at TEXT,
                    UNIQUE(notice_date, issue_key)
                );

                CREATE TABLE IF NOT EXISTS plan_generation_routes (
                    plan_set_id TEXT PRIMARY KEY REFERENCES plan_sets(id) ON DELETE CASCADE,
                    route_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS knowledge_sources (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source_type TEXT NOT NULL CHECK(source_type IN ('note', 'document', 'import')),
                    source_url TEXT NOT NULL DEFAULT '',
                    source_license TEXT NOT NULL DEFAULT '',
                    content_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL REFERENCES knowledge_sources(id) ON DELETE CASCADE,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(source_id, chunk_index)
                );

                CREATE TABLE IF NOT EXISTS retrieval_matches (
                    id TEXT PRIMARY KEY,
                    message_id TEXT NOT NULL REFERENCES conversation_messages(id) ON DELETE CASCADE,
                    chunk_id INTEGER NOT NULL,
                    source_id TEXT NOT NULL,
                    source_title TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_url TEXT NOT NULL DEFAULT '',
                    source_license TEXT NOT NULL DEFAULT '',
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    rank INTEGER NOT NULL,
                    distance REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(message_id, rank)
                );

                -- The energy the user reported, out of 5: every reading kept with its local time,
                -- each made only on its own day; the day's energy is their average.
                CREATE TABLE IF NOT EXISTS energy_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reading_date TEXT NOT NULL,
                    level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 5),
                    reading_time TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS energy_log_by_date ON energy_log(reading_date);

                -- A repeat's change that today's own day couldn't take, as it was reported or its
                -- set plan scheduled it: from next_from on, the series repeats as next_kind says.
                CREATE TABLE IF NOT EXISTS repeat_series (
                    id TEXT PRIMARY KEY,
                    next_kind TEXT NOT NULL CHECK(next_kind IN ('none', 'daily', 'weekly')),
                    next_from TEXT NOT NULL
                );

                -- A folder the user connected, read and never written: its files the user unticked,
                -- the website its files also open on, and whether it was found at its path when
                -- last refreshed. Its files are Library sources with origin 'folder'.
                CREATE TABLE IF NOT EXISTS source_folders (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    path TEXT NOT NULL,
                    website TEXT NOT NULL DEFAULT '',
                    unticked_json TEXT NOT NULL DEFAULT '[]',
                    found INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    refreshed_at TEXT
                );

                -- A Learning task with a checklist, made from a Library source or not: the source, the
                -- pass the task belongs to (whose checklist it shows), what the source's text says about
                -- studying it and whose its effort is, the task it continues, and when its website was
                -- looked up again as it started, with what came of it. See learning_tasks.
                CREATE TABLE IF NOT EXISTS learning_tasks (
                    item_id TEXT PRIMARY KEY REFERENCES daily_items(id) ON DELETE CASCADE,
                    source_id TEXT,
                    pass_id TEXT NOT NULL,
                    profile_json TEXT NOT NULL DEFAULT '{}',
                    effort_by TEXT NOT NULL DEFAULT 'text',
                    follows_item_id TEXT,
                    start_checked_at TEXT,
                    start_check TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );

                -- An item of a pass's checklist, in its order: its name, the source heading (and level)
                -- it came from or none for one the user added, how the source's latest reading found it
                -- ('' as before, 'new', or 'gone' when no longer there), whether the user removed it (a
                -- source item stays, unseen, so a later reading doesn't bring it back), and when and on
                -- which task it was ticked, which gives the pass's progress and the pace it goes at.
                CREATE TABLE IF NOT EXISTS checklist_items (
                    id TEXT PRIMARY KEY,
                    pass_id TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    heading TEXT,
                    level INTEGER,
                    added_by TEXT NOT NULL DEFAULT 'source',
                    page_state TEXT NOT NULL DEFAULT '',
                    removed INTEGER NOT NULL DEFAULT 0,
                    ticked_at TEXT,
                    ticked_on TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS checklist_items_pass ON checklist_items(pass_id, position);

                -- A Library source a Learn task links as a reference, beside the source a learning task
                -- was made from (learning_tasks). A goal holds the sources its tasks link.
                CREATE TABLE IF NOT EXISTS task_sources (
                    item_id TEXT NOT NULL REFERENCES daily_items(id) ON DELETE CASCADE,
                    source_id TEXT NOT NULL,
                    linked_at TEXT NOT NULL,
                    PRIMARY KEY (item_id, source_id)
                );

                -- What the study check found for a connected folder's file at its content hash: why it can't be
                -- read, or None, and whether the local model took it for study material ('yes', 'no', or
                -- 'unchecked' when the model couldn't run), and whether Ava has reported it.
                CREATE TABLE IF NOT EXISTS folder_checks (
                    folder_id TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    reason TEXT,
                    study TEXT NOT NULL CHECK(study IN ('yes', 'no', 'unchecked')),
                    checked_at TEXT NOT NULL,
                    reported INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (folder_id, relative_path)
                );
                """
            )
            connection.executescript(
                "".join(sql.format(table=name) for name, sql in _AREA_TABLES.items())
            )
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(daily_items)")}
            if "repeat_kind" not in columns:
                connection.execute("ALTER TABLE daily_items ADD COLUMN repeat_kind TEXT NOT NULL DEFAULT 'none'")
            if "protected" not in columns:
                connection.execute("ALTER TABLE daily_items ADD COLUMN protected INTEGER NOT NULL DEFAULT 0")
            if "origin_kind" not in columns:
                connection.execute("ALTER TABLE daily_items ADD COLUMN origin_kind TEXT NOT NULL DEFAULT 'user'")
            if "origin_detail" not in columns:
                connection.execute("ALTER TABLE daily_items ADD COLUMN origin_detail TEXT NOT NULL DEFAULT ''")
            if "origin_source_item_id" not in columns:
                connection.execute("ALTER TABLE daily_items ADD COLUMN origin_source_item_id TEXT REFERENCES daily_items(id)")
            if "acceptance" not in columns:
                # Agent-prepared work placed before the Accept step existed stays as it was: accepted.
                connection.execute("ALTER TABLE daily_items ADD COLUMN acceptance TEXT NOT NULL DEFAULT 'accepted'")
            if "duration_source" not in columns:
                # Every length recorded before agents estimated lengths was the user's own.
                connection.execute("ALTER TABLE daily_items ADD COLUMN duration_source TEXT NOT NULL DEFAULT 'user'")
                connection.execute("ALTER TABLE daily_items ADD COLUMN estimated_by TEXT")
                connection.execute("ALTER TABLE daily_items ADD COLUMN estimate_basis TEXT")
            if "repeat_series_id" not in columns:
                # Repeats recorded before they were linked join a series by their name and area: the
                # earliest repeating day's. A day that doesn't repeat stays out of it.
                connection.execute("ALTER TABLE daily_items ADD COLUMN repeat_series_id TEXT")
                first: dict[tuple[str, str], str] = {}
                for row in connection.execute("""SELECT id, domain, title FROM daily_items WHERE repeat_kind != 'none'
                                                 ORDER BY item_date, rowid""").fetchall():
                    series = first.setdefault((row["domain"], " ".join(row["title"].lower().split())), row["id"])
                    connection.execute("UPDATE daily_items SET repeat_series_id = ? WHERE id = ?", (series, row["id"]))
            # Tasks reported before times were kept have none: screens show them as planned.
            for column in _TIME_COLUMN_LIST:
                if column.split()[0] not in columns:
                    connection.execute(f"ALTER TABLE daily_items ADD COLUMN {column}")
            connection.executescript(_DAILY_ITEM_INDEXES)
            entry_columns = {row["name"] for row in connection.execute("PRAGMA table_info(plan_entries)")}
            if "source_item_id" not in entry_columns:
                connection.execute("ALTER TABLE plan_entries ADD COLUMN source_item_id TEXT REFERENCES daily_items(id)")
            if "removed_at" not in entry_columns:
                # When the task a past set plan scheduled was removed; the plan keeps the entry as history.
                connection.execute("ALTER TABLE plan_entries ADD COLUMN removed_at TEXT")
            if "moved_to" not in entry_columns:
                # The day a past set plan's task moved to, its entry marked removed from that plan's day.
                connection.execute("ALTER TABLE plan_entries ADD COLUMN moved_to TEXT")
            variant_columns = {row["name"] for row in connection.execute("PRAGMA table_info(plan_variants)")}
            if "notes_json" not in variant_columns:
                # Plans proposed earlier keep their rationale as text alone, and kept no meals free.
                connection.execute("ALTER TABLE plan_variants ADD COLUMN notes_json TEXT NOT NULL DEFAULT '[]'")
                connection.execute("ALTER TABLE plan_variants ADD COLUMN meals_json TEXT NOT NULL DEFAULT '[]'")
            source_columns = {row["name"] for row in connection.execute("PRAGMA table_info(knowledge_sources)")}
            if "source_url" not in source_columns:
                connection.execute("ALTER TABLE knowledge_sources ADD COLUMN source_url TEXT NOT NULL DEFAULT ''")
            if "source_license" not in source_columns:
                connection.execute("ALTER TABLE knowledge_sources ADD COLUMN source_license TEXT NOT NULL DEFAULT ''")
            if "goal_id" not in source_columns and "knowledge_sources" in before and "task_sources" not in before:
                # A Library from before 3.9 kept neither an area nor a goal: _offline_library gives each
                # note and file an area, and _study_library then keeps only Learning's.
                connection.execute("ALTER TABLE knowledge_sources ADD COLUMN domain TEXT NOT NULL DEFAULT ''")
                connection.execute("ALTER TABLE knowledge_sources ADD COLUMN goal_id TEXT")
            if "origin" not in source_columns:
                # Where a source came from (a note, an imported file, a connected folder's file, a website),
                # with what DayWright keeps of it to brief and outline it; see source_store.
                for column in ("origin TEXT NOT NULL DEFAULT ''", "folder_id TEXT", "relative_path TEXT",
                               "briefing TEXT", "briefing_by TEXT NOT NULL DEFAULT ''",
                               "outline_json TEXT NOT NULL DEFAULT '[]'", "outline_by TEXT NOT NULL DEFAULT ''",
                               "missing INTEGER NOT NULL DEFAULT 0", "looked_up_at TEXT"):
                    connection.execute(f"ALTER TABLE knowledge_sources ADD COLUMN {column}")
            # When a website was last looked up again and last found changed, and where an imported file
            # came from on this Mac; a file imported before origins were kept has none.
            source_columns = {row["name"] for row in connection.execute("PRAGMA table_info(knowledge_sources)")}
            for column in ("checked_at TEXT", "updated_at TEXT", "original_path TEXT"):
                if column.split()[0] not in source_columns:
                    connection.execute(f"ALTER TABLE knowledge_sources ADD COLUMN {column}")
            # Notes and imported files from before origins were kept take theirs from their type.
            connection.execute("""UPDATE knowledge_sources SET origin = CASE source_type WHEN 'note' THEN 'note' ELSE 'file' END
                                  WHERE origin = ''""")
            move_topics_to_tasks(connection, date.today().isoformat())
            message_columns = {row["name"] for row in connection.execute("PRAGMA table_info(conversation_messages)")}
            if "topic_date" not in message_columns:
                # Earlier messages kept no day of their own, so Ava marks no change of day before them.
                connection.execute("ALTER TABLE conversation_messages ADD COLUMN topic_date TEXT")
            match_columns = {row["name"] for row in connection.execute("PRAGMA table_info(retrieval_matches)")}
            if "source_url" not in match_columns:
                connection.execute("ALTER TABLE retrieval_matches ADD COLUMN source_url TEXT NOT NULL DEFAULT ''")
            if "source_license" not in match_columns:
                connection.execute("ALTER TABLE retrieval_matches ADD COLUMN source_license TEXT NOT NULL DEFAULT ''")
            # Plans proposed before task names were quoted in their rationale get the quotes too.
            for row in connection.execute("SELECT id, rationale FROM plan_variants").fetchall():
                quoted = _UNQUOTED_RATIONALE_TASK.sub(lambda match: f"{match[1]}“{match[2]}”{match[3]}", row["rationale"])
                if quoted != row["rationale"]:
                    connection.execute("UPDATE plan_variants SET rationale = ? WHERE id = ?", (quoted, row["id"]))
            if connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'energy_readings'").fetchone():
                # Before every change was kept, a day held one reading: it becomes the day's one entry in
                # the log, at the local time it was last changed.
                connection.executemany(
                    "INSERT INTO energy_log (reading_date, level, reading_time, recorded_at) VALUES (?, ?, ?, ?)",
                    [(row["reading_date"], row["level"], datetime.fromisoformat(row["updated_at"]).astimezone().strftime("%H:%M"),
                      row["updated_at"])
                     for row in connection.execute("SELECT reading_date, level, updated_at FROM energy_readings").fetchall()])
                connection.execute("DROP TABLE energy_readings")
        self._retire_areas()
        self._fold_area_records()
        self._offline_library()
        self._study_library()

    def _offline_library(self) -> None:
        """Take the Library offline, and give every note and file of a Library from before 3.9 an area.

        Whenever any is left: the network log and the online lookup's tables are dropped, and every
        page the lookup imported (source type "import") is deleted with its passages, their vectors,
        and the records of Ava having drawn on it; the plan checkpoints, which held copies of fetched
        text, are cleared with them. Then, while sources still have areas, a note or file without one
        gets the one the purpose rule gives its title and opening text, by keywords, and no goal. It
        does nothing once all that is done, so it runs safely at every start.
        """
        with self.connect() as connection:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            dropped = tables & set(_ONLINE_TABLES)
            pages = [row[0] for row in connection.execute("SELECT id FROM knowledge_sources WHERE source_type = 'import'")]
            _delete_sources(connection, pages)
            for table in _ONLINE_TABLES:
                connection.execute(f"DROP TABLE IF EXISTS {table}")
            if "domain" in {row["name"] for row in connection.execute("PRAGMA table_info(knowledge_sources)")}:
                for row in connection.execute(
                        """SELECT s.id, s.title, (SELECT content FROM knowledge_chunks WHERE source_id = s.id
                                                   ORDER BY chunk_index LIMIT 1) AS opening
                           FROM knowledge_sources s WHERE s.domain = ''""").fetchall():
                    connection.execute("UPDATE knowledge_sources SET domain = ?, goal_id = NULL WHERE id = ?",
                                       (keyword_area(row["title"], (row["opening"] or "")[:OPENING_CHARACTERS]), row["id"]))
        if dropped or pages:
            self._clear_checkpoints()

    def _study_library(self) -> None:
        """Make the Library for studying alone, once, while its sources still have areas (before v4.9).

        Every Life, Work and Project note, imported file and website is deleted for good, with its passages,
        their vectors and the records of Ava having drawn on it, and every Life, Work and Project folder is
        disconnected the same way, its files on the Mac untouched. A learning task made from one keeps its
        checklist and loses only its link. Learning's sources and folders stay. Sources then lose their links
        to goals, as only tasks link them, and sources and folders lose their areas. Learning's folders are
        checked as any folder whose files weren't (see folder_check).
        """
        with self.connect() as connection:
            if "domain" not in {row["name"] for row in connection.execute("PRAGMA table_info(knowledge_sources)")}:
                return
            # Folders came in v4.5 with their areas; a Library older than them has none to disconnect.
            areas = "domain" in {row["name"] for row in connection.execute("PRAGMA table_info(source_folders)")}
            folders = [row[0] for row in connection.execute(
                "SELECT id FROM source_folders WHERE domain IN ('life', 'work', 'project')")] if areas else []
            marks = ",".join("?" for _ in folders)
            _delete_sources(connection, [row[0] for row in connection.execute(
                f"""SELECT id FROM knowledge_sources
                    WHERE (domain IN ('life', 'work', 'project') AND origin IN ('note', 'file', 'website'))
                       OR folder_id IN ({marks})""", folders)])
            connection.execute(f"DELETE FROM source_folders WHERE id IN ({marks})", folders)
            connection.execute("ALTER TABLE knowledge_sources DROP COLUMN goal_id")
            connection.execute("ALTER TABLE knowledge_sources DROP COLUMN domain")
            if areas:
                connection.execute("ALTER TABLE source_folders DROP COLUMN domain")

    @property
    def checkpoint_path(self) -> Path:
        """The separate file where day proposals keep their LangGraph checkpoints."""
        return self.path.with_name(f"{self.path.stem}.checkpoints.sqlite3")

    def _retire_areas(self) -> None:
        """Move a database from the Learn, Life, Money and Rest areas to Learn, Life, Work and Project.

        Runs once, while `daily_items` still names the old areas. Rest and Money goals, tasks and
        plan entries move to Life. Money's own records are deleted, with its advice, its agent's
        reports, saved Summary reports (rebuilt on request) and the plan checkpoints that held
        money figures. A flexible task for today or later loses its start time, which a plan now
        chooses, except a timed Life event, which becomes fixed. Past days keep their times. One
        transaction does it all, so a failure leaves the database as it was.
        """
        connection = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            current = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'daily_items'"
            ).fetchone()
            if "'finance'" not in current["sql"]:
                return
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute("BEGIN IMMEDIATE")
            retired = ", ".join(f"'{area}'" for area in _RETIRED_AREAS)
            area = f"CASE WHEN domain IN ({retired}) THEN 'life' ELSE domain END"
            event = "id IN (SELECT item_id FROM life_events)"
            today = date.today().isoformat()
            for name, sql in _AREA_TABLES.items():
                connection.execute(sql.format(table=f"{name}_current"))
            connection.execute(
                f"""INSERT INTO goals_current (id, title, domain, status, created_at)
                    SELECT id, title, {area}, status, created_at FROM goals"""
            )
            connection.execute(
                f"""INSERT INTO daily_items_current
                    (id, item_date, goal_id, title, detail, domain, start_time, duration_minutes,
                     constraint_kind, repeat_kind, protected, origin_kind, origin_detail,
                     origin_source_item_id, completion_status, acceptance, created_at)
                    SELECT id, item_date, goal_id, title, detail, {area},
                           CASE WHEN constraint_kind = 'flexible' AND item_date >= ? AND NOT {event}
                                THEN NULL ELSE start_time END,
                           duration_minutes,
                           CASE WHEN constraint_kind = 'flexible' AND item_date >= ? AND {event}
                                THEN 'fixed' ELSE constraint_kind END,
                           repeat_kind, protected, origin_kind, origin_detail, origin_source_item_id,
                           completion_status, acceptance, created_at
                    FROM daily_items""",
                (today, today),
            )
            connection.execute(
                f"""INSERT INTO plan_entries_current
                    (id, variant_id, position, start_time, title, detail, source_item_id, domain,
                     duration_minutes, constraint_kind, completion_status)
                    SELECT id, variant_id, position, start_time, title, detail, source_item_id, {area},
                           duration_minutes, constraint_kind, completion_status
                    FROM plan_entries"""
            )
            for row in connection.execute("SELECT * FROM suggestion_pool WHERE domain != 'finance'").fetchall():
                moved = row["domain"] in _RETIRED_AREAS
                domain = "life" if moved else row["domain"]
                connection.execute(
                    """INSERT OR IGNORE INTO suggestion_pool_current
                       (id, period_kind, period_key, domain, content, priority, source_key, status,
                        discarded_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (row["id"], row["period_kind"], row["period_key"], domain, row["content"],
                     row["priority"], _advice_key(domain, row["content"]) if moved else row["source_key"],
                     row["status"], row["discarded_at"], row["created_at"]),
                )
            connection.execute(
                """INSERT INTO agent_runs_current
                   (id, message_id, sequence, agent_key, phase, summary, reads_json, writes_json, created_at)
                   SELECT id, message_id, sequence, agent_key, phase, summary, reads_json, writes_json, created_at
                   FROM agent_runs WHERE agent_key != 'finance'"""
            )
            for name in _AREA_TABLES:
                connection.execute(f"DROP TABLE {name}")
                connection.execute(f"ALTER TABLE {name}_current RENAME TO {name}")
            for statement in filter(str.strip, _DAILY_ITEM_INDEXES.split(";")):
                connection.execute(statement)
            for row in connection.execute("SELECT plan_set_id, route_json FROM plan_generation_routes").fetchall():
                route = [run for run in json.loads(row["route_json"]) if run.get("agentKey") != "finance"]
                connection.execute(
                    "UPDATE plan_generation_routes SET route_json = ? WHERE plan_set_id = ?",
                    (json.dumps(route), row["plan_set_id"]),
                )
            connection.execute(f"UPDATE feedback_signals SET domain = 'life' WHERE domain IN ({retired})")
            connection.execute(f"DELETE FROM suggestion_notices WHERE domain IN ({retired})")
            connection.execute("UPDATE OR IGNORE cleared_suggestion_periods SET domain = 'life' WHERE domain = 'rest'")
            connection.execute(f"DELETE FROM cleared_suggestion_periods WHERE domain IN ({retired})")
            connection.execute("DELETE FROM summary_reports")
            for table in _MONEY_TABLES:
                connection.execute(f"DROP TABLE IF EXISTS {table}")
            if connection.execute("PRAGMA foreign_key_check").fetchone():
                raise RuntimeError("Moving to the new areas would break a link between records")
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
        self._clear_checkpoints()

    def _clear_checkpoints(self) -> None:
        """Delete the day proposals' saved checkpoints, which hold copies of records a move drops."""
        if self.checkpoint_path.exists():
            with closing(sqlite3.connect(self.checkpoint_path, timeout=15)) as checkpoints:
                tables = {row[0] for row in checkpoints.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
                for table in tables & {"checkpoints", "writes"}:
                    checkpoints.execute(f"DELETE FROM {table}")
                checkpoints.commit()

    def _fold_area_records(self) -> None:
        """Fold Learning's and Life's own records into tasks and goals, and drop them.

        Runs once, while any of _AREA_RECORD_TABLES is left. Each active habit becomes a flexible
        Life task on today that repeats as the habit did (a weekly one on today's weekday), with its
        area agent's estimated length; each learning subject becomes a Learning goal, active while
        the subject was, completed otherwise. A habit already on today as a Life task, or a subject
        already a Learning goal, by the same name in any case or spacing, isn't made twice. A Life
        event is already a fixed task and stays one; its Detail is cleared when it is exactly the
        event's category, which goes, and kept otherwise. Everything else those records held is deleted
        with them, as are saved Summary reports (rebuilt on request) and the plan checkpoints that
        copied them. One transaction does it all, so a failure leaves the database as it was.
        """
        connection = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            present = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            left = [table for table in _AREA_RECORD_TABLES if table in present]
            if not left:
                return
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute("BEGIN IMMEDIATE")
            today, now = date.today().isoformat(), _now()

            def same(title: str) -> str:
                """A name as the move compares it: in lower case, its spaces single."""
                return " ".join(title.lower().split())

            if "life_habits" in present:
                kept = {same(row["title"]) for row in connection.execute(
                    "SELECT title FROM daily_items WHERE domain = 'life' AND item_date = ?", (today,))}
                for habit in connection.execute(
                        "SELECT title, frequency FROM life_habits WHERE active = 1 ORDER BY created_at, rowid").fetchall():
                    if same(habit["title"]) in kept:
                        continue
                    kept.add(same(habit["title"]))
                    item_id = _id("item")
                    minutes, basis = self._provisional_estimate(connection, habit["title"], "life")
                    connection.execute(
                        """INSERT INTO daily_items
                           (id, item_date, title, domain, duration_minutes, constraint_kind, repeat_kind,
                            repeat_series_id, created_at, duration_source, estimated_by, estimate_basis)
                           VALUES (?, ?, ?, 'life', ?, 'flexible', ?, ?, ?, 'estimate', 'life', ?)""",
                        (item_id, today, habit["title"].strip(), minutes, habit["frequency"], item_id, now, basis))
            if "learning_items" in present:
                kept = {same(row["title"]) for row in connection.execute(
                    "SELECT title FROM goals WHERE domain = 'learning'")}
                for subject in connection.execute(
                        "SELECT title, status, created_at FROM learning_items ORDER BY created_at, rowid").fetchall():
                    if same(subject["title"]) in kept:
                        continue
                    kept.add(same(subject["title"]))
                    connection.execute(
                        "INSERT INTO goals (id, title, domain, status, created_at) VALUES (?, ?, 'learning', ?, ?)",
                        (_id("goal"), subject["title"].strip(),
                         "active" if subject["status"] == "active" else "completed", subject["created_at"]))
            if "life_events" in present:
                # An event's Detail that is only its category goes with the category; any other text stays.
                connection.execute(
                    """UPDATE daily_items SET detail = '' WHERE EXISTS (
                         SELECT 1 FROM life_events e WHERE e.item_id = daily_items.id AND e.category = daily_items.detail)""")
            for table in left:
                connection.execute(f"DROP TABLE {table}")
            connection.execute("DELETE FROM summary_reports")
            if connection.execute("PRAGMA foreign_key_check").fetchone():
                raise RuntimeError("Folding the area records into tasks and goals would break a link between records")
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()
        self._clear_checkpoints()

    def goals(self) -> list[dict]:
        """Return the user's goal ledger in creation order.

        Each goal has its linked tasks, how many are done, and the time it spans: from when it was
        made ("startAt") to that plus the length of every linked task ("endAt"), so adding a task
        extends it by the task's length, given or estimated.
        """
        with self.connect() as connection:
            goals = [dict(row) for row in connection.execute(
                """SELECT g.id, g.title, g.domain, g.status, g.created_at AS startAt,
                          COUNT(i.id) AS itemCount,
                          SUM(CASE WHEN i.completion_status = 'done' THEN 1 ELSE 0 END) AS doneCount,
                          COALESCE(SUM(i.duration_minutes), 0) AS taskMinutes
                   FROM goals g LEFT JOIN daily_items i ON i.goal_id = g.id AND i.acceptance = 'accepted'
                   GROUP BY g.id ORDER BY g.created_at, g.rowid"""
            )]
            linked = connection.execute(
                """SELECT id, goal_id AS goalId, item_date AS date, title, detail, domain,
                          start_time AS startTime, duration_minutes AS durationMinutes,
                          completion_status AS status
                   FROM daily_items WHERE goal_id IS NOT NULL AND acceptance = 'accepted'
                   ORDER BY item_date, start_time IS NULL, start_time, rowid"""
            ).fetchall()
        by_goal: dict[str, list[dict]] = {goal["id"]: [] for goal in goals}
        for row in linked:
            by_goal.setdefault(row["goalId"], []).append(dict(row))
        for goal in goals:
            goal["linkedItems"] = by_goal.get(goal["id"], [])
            # A goal runs from when it was made for as long as its tasks take, estimated or given.
            goal["endAt"] = (datetime.fromisoformat(goal["startAt"]) + timedelta(minutes=goal["taskMinutes"])).isoformat()
        return goals

    def create_goal(self, title: str, domain: str) -> dict:
        """Add a user-authored goal without generating a schedule."""
        with self.connect() as connection:
            goal_id = self._create_goal(connection, title, domain)
        return next(goal for goal in self.goals() if goal["id"] == goal_id)

    @staticmethod
    def _create_goal(connection: sqlite3.Connection, title: str, domain: str) -> str:
        """Add a goal within an open transaction, as create_goal does; return its id."""
        goal_id = _id("goal")
        connection.execute("INSERT INTO goals (id, title, domain, created_at) VALUES (?, ?, ?, ?)",
                           (goal_id, title, domain, _now()))
        return goal_id

    def update_goal(self, goal_id: str, title: str, status: str) -> dict:
        """Edit a goal's name or lifecycle without erasing linked daily records."""
        with self.connect() as connection:
            updated = connection.execute(
                "UPDATE goals SET title = ?, status = ? WHERE id = ?", (title, status, goal_id)
            )
            if not updated.rowcount:
                raise ValueError("Goal not found")
        return next(goal for goal in self.goals() if goal["id"] == goal_id)

    def delete_goal(self, goal_id: str) -> dict:
        """Remove a goal that no dated record links to.

        Linked records are removed first, one at a time, so no dated work disappears with a goal.
        """
        with self.connect() as connection:
            row = connection.execute(
                "SELECT title FROM goals WHERE id = ?", (goal_id,)
            ).fetchone()
            if not row:
                raise ValueError("Goal not found")
            linked = connection.execute(
                "SELECT COUNT(*) FROM daily_items WHERE goal_id = ?", (goal_id,)
            ).fetchone()[0]
            if linked:
                raise PermissionError(
                    f"{linked} dated record(s) still link to this goal; remove those first"
                )
            connection.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
        return {"id": goal_id, "title": row["title"]}

    def daily_items(self, plan_date: str) -> list[dict]:
        """Return dated user records independently of any proposed plan snapshot.

        Agent-prepared records waiting for the user's Accept are included and marked `pending`;
        dismissed ones are left out.
        """
        return self.daily_items_between(plan_date, plan_date)

    def daily_items_between(self, start: str, end: str) -> list[dict]:
        """Return the user's dated records from `start` to `end` inclusive, in date and time order.

        Within a day, records without a start time follow the timed ones. Agent-prepared records
        waiting for the user's Accept are included and marked `pending`; dismissed ones are left out.
        Each says whether it is "no reply" (`noReply`): one of the user's tasks still without a status
        once its day's DAY_END has passed, as DayWright marks it, unless its goal is paused.
        """
        today, clock = date.today().isoformat(), _local_time()
        with self.connect() as connection:
            rows = connection.execute(
                f"""SELECT {_ITEM_FIELDS}
                   FROM daily_items WHERE item_date BETWEEN ? AND ? AND acceptance != 'dismissed'
                   ORDER BY item_date, start_time IS NULL, start_time, rowid""",
                (start, end),
            ).fetchall()
        return [{**dict(row), "timeConfirmed": bool(row["timeConfirmed"]),
                 "noReply": (row["completion_status"] == "planned" and row["acceptance"] == "accepted"
                             and row["goalStatus"] != "paused"
                             and (row["date"] < today or (row["date"] == today and clock >= DAY_END)))}
                for row in rows]

    def _check_goal(self, connection: sqlite3.Connection, goal_id: str | None, domain: str) -> None:
        if goal_id is None:
            return
        row = connection.execute("SELECT domain FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if not row or row["domain"] != domain:
            raise ValueError("Choose a goal in the same area")

    def _clashing_task(self, connection: sqlite3.Connection, item_date: str, start: str, minutes: int,
                       exclude_id: str | None = None) -> dict | None:
        """Return the first other accepted task that day whose time overlaps `start` for `minutes`,
        else the meal it would overlap, marked `meal`, since no task is fixed over lunch or dinner."""
        begin = minutes_after_midnight(start)
        for row in connection.execute(
            """SELECT id, title, start_time, duration_minutes FROM daily_items
               WHERE item_date = ? AND start_time IS NOT NULL AND acceptance = 'accepted' AND id != ?
               ORDER BY start_time""",
            (item_date, exclude_id or ""),
        ):
            other = minutes_after_midnight(row["start_time"])
            if other < begin + minutes and begin < other + row["duration_minutes"]:
                return dict(row)
        meal = meal_overlap(start, minutes, self._day_meals(connection, item_date))
        return meal and {"id": None, "title": meal.title, "start_time": meal.start,
                         "duration_minutes": meal.minutes, "meal": True}

    def day_meals(self, plan_date: str) -> tuple[Meal, ...]:
        """Return a day's lunch and dinner; see _day_meals."""
        with self.connect() as connection:
            return self._day_meals(connection, plan_date)

    def _day_meals(self, connection: sqlite3.Connection, plan_date: str) -> tuple[Meal, ...]:
        """Return a day's lunch and dinner, which plans keep free and no task may be fixed over.

        A past day with a set plan keeps the meals that plan saved, which leaves out one that was
        over, or taken by a fixed task, when it was set. Any other day has its own times, else the
        standing times in force that day, else the usual ones; see meals.py.
        """
        if plan_date < date.today().isoformat():
            saved = connection.execute(
                """SELECT v.meals_json FROM daily_confirmations c JOIN plan_variants v ON v.id = c.variant_id
                   WHERE c.plan_date = ?""", (plan_date,)).fetchone()
            if saved:
                return tuple(Meal(meal["title"], meal["start_time"], meal["duration_minutes"])
                             for meal in json.loads(saved["meals_json"]))
        return meals_on(plan_date, self._meal_settings(connection))

    def _meal_settings(self, connection: sqlite3.Connection) -> dict:
        """Return the saved meal times, as meals.py lays them out; empty when none was ever moved."""
        row = connection.execute("SELECT value_json FROM preferences WHERE key = ?", (MEALS_KEY,)).fetchone()
        return json.loads(row["value_json"]) if row else {}

    def save_meal(self, key: str, start: str, minutes: int, day: str | None = None, from_day: str | None = None) -> None:
        """Move lunch or dinner on one day, or from a day on.

        Args:
            key: "lunch" or "dinner".
            start: The new "HH:MM" start.
            minutes: How long it now lasts.
            day: The one YYYY-MM-DD date it moves on.
            from_day: The YYYY-MM-DD date it moves from, for that day and every later one.
        """
        with self.connect() as connection:
            self._save_meal(connection, key, start, minutes, day, from_day)

    def _save_meal(self, connection: sqlite3.Connection, key: str, start: str, minutes: int,
                   day: str | None, from_day: str | None) -> None:
        """Save a moved meal within an open transaction; see save_meal."""
        settings = self._meal_settings(connection)
        changed = (one_day(settings, key, start, minutes, day) if day
                   else standing(settings, key, start, minutes, from_day))
        connection.execute(
            """INSERT INTO preferences (key, value_json, updated_at) VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at""",
            (MEALS_KEY, json.dumps(changed), _now()))

    def replaced_meal_days(self, key: str, from_day: str) -> list[tuple[str, Meal]]:
        """Return the one-day changes to a meal that a standing change from `from_day` replaces; see
        meals.one_day_changes."""
        with self.connect() as connection:
            return one_day_changes(self._meal_settings(connection), key, from_day)

    def meal_check_days(self, day: str, standing: bool) -> dict[str, dict]:
        """Return the days a meal change is checked on; see _meal_days."""
        with self.connect() as connection:
            return self._meal_days(connection, day, standing)

    def _meal_days(self, connection: sqlite3.Connection, day: str, standing: bool) -> dict[str, dict]:
        """Return the days a meal change is checked on, each with its tasks and its set plan's entries.

        Args:
            day: The day the change is for, or the first day of a standing one.
            standing: Whether it holds from `day` on, which checks `day` and every later day with a task.

        Returns:
            Each day by date, in order, with its accepted tasks ("dayItems", as the service shows them)
            and its set plan's entries ("entries", empty when no plan is set); see agents.meal_clashes.
        """
        dates = [day]
        if standing:
            dates += [row["item_date"] for row in connection.execute(
                """SELECT DISTINCT item_date FROM daily_items WHERE item_date > ? AND acceptance = 'accepted'
                   ORDER BY item_date""", (day,))]
        return {checked: {
            "dayItems": [dict(row) for row in connection.execute(
                f"SELECT {_ITEM_FIELDS} FROM daily_items WHERE item_date = ? AND acceptance = 'accepted'", (checked,))],
            "entries": [{**dict(row), "removed": bool(row["removed"])} for row in connection.execute(
                """SELECT e.id, e.title, e.start_time, e.duration_minutes, e.source_item_id,
                          e.removed_at IS NOT NULL AS removed
                   FROM plan_entries e JOIN daily_confirmations c ON c.variant_id = e.variant_id
                   WHERE c.plan_date = ? ORDER BY e.position""", (checked,))],
        } for checked in dates}

    def _change_meal(self, connection: sqlite3.Connection, payload: dict) -> dict:
        """Move a meal as a confirmed proposal asks, within an open transaction, and update today's plan.

        The tasks in the way are checked again first, so one added since refuses the move. Today's
        set plan, when the move reaches today, is fitted around the meal in place when the meal
        overlaps what it places by SMALL_MEAL_OVERLAP_MINUTES or less (see planner.fit_around_meal);
        else, or when it can't be fitted so, it is left as it is, up for review with new plans, as
        today's plans are with no plan set.

        Returns:
            How the plan updates ("planUpdate": "adjusted", "updated", "review", "repropose" or
            "none"), and each task an adjustment moved or shortened ("changes"), its "title" and its
            times "from" and "to".
        """
        from .agents import meal_clashes

        standing = payload["scope"] == "standing"
        meal = Meal(payload["title"], payload["start"], payload["minutes"])
        days = self._meal_days(connection, payload["date"], standing)
        found = meal_clashes(meal, days)
        if found["refused"]:
            raise PermissionError(f"“{found['refused'][0]['title']}” now stands in the way of "
                                  f"{payload['title'].lower()} at {meal.start}–{meal.end}; nothing was changed")
        self._save_meal(connection, payload["meal"], meal.start, meal.minutes,
                        None if standing else payload["date"], payload["date"] if standing else None)
        today = date.today().isoformat()
        if today not in days:
            return {"planUpdate": "none", "changes": []}
        confirmed = connection.execute(
            "SELECT variant_id FROM daily_confirmations WHERE plan_date = ?", (today,)).fetchone()
        if not confirmed:
            drafted = connection.execute("SELECT 1 FROM plan_sets WHERE plan_date = ?", (today,)).fetchone()
            return {"planUpdate": "repropose" if drafted else "none", "changes": []}
        overlap = meal_clashes(meal, {today: days[today]})["planOverlapMinutes"]
        if overlap > SMALL_MEAL_OVERLAP_MINUTES:
            return {"planUpdate": "review", "changes": []}
        tasks = {item["id"]: item for item in days[today]["dayItems"]}
        entries = [entry for entry in days[today]["entries"] if not entry["removed"]]
        items = tuple(PlanItem(entry["start_time"], entry["title"], "", "life", entry["duration_minutes"],
                               "fixed" if tasks.get(entry["source_item_id"], {}).get("start_time") else "flexible",
                               entry["id"],
                               tasks.get(entry["source_item_id"], {}).get("durationSource") == "estimate")
                      for entry in entries)
        others = tuple(other for other in self._day_meals(connection, today) if other.title != meal.title)
        fitted = fit_around_meal(items, meal, others)
        if fitted is None:
            return {"planUpdate": "review", "changes": []}
        changes = []
        for before, after in zip(items, fitted):
            if (before.start, before.duration_minutes) != (after.start, after.duration_minutes):
                connection.execute("UPDATE plan_entries SET start_time = ?, duration_minutes = ? WHERE id = ?",
                                   (after.start, after.duration_minutes, after.item_id))
                changes.append({"title": before.title, "from": _span(before.start, before.duration_minutes),
                                "to": _span(after.start, after.duration_minutes)})
        saved = json.loads(connection.execute("SELECT meals_json FROM plan_variants WHERE id = ?",
                                              (confirmed["variant_id"],)).fetchone()["meals_json"])
        connection.execute("UPDATE plan_variants SET meals_json = ? WHERE id = ?", (json.dumps(
            [{**kept, "start_time": meal.start, "duration_minutes": meal.minutes} if kept["title"] == meal.title else kept
             for kept in saved], ensure_ascii=False), confirmed["variant_id"]))
        return {"planUpdate": "adjusted" if changes else "updated", "changes": changes}

    def _meal_payload(self, plan_date: str) -> list[dict]:
        """A day's meals as the interface reads them, in the shape a plan saves its own."""
        return [{"title": meal.title, "start_time": meal.start, "duration_minutes": meal.minutes}
                for meal in self.day_meals(plan_date)]

    def clashing_task(self, item_date: str, start: str, minutes: int, exclude_id: str | None = None) -> dict | None:
        """Return the first other task that day whose time overlaps `start` for `minutes`, if any.

        Args:
            item_date: The YYYY-MM-DD day.
            start: The proposed "HH:MM" start.
            minutes: How long the task lasts.
            exclude_id: The task being moved, which never clashes with itself.

        Returns:
            The clashing task's id, title, start_time and duration_minutes, or None.
        """
        with self.connect() as connection:
            return self._clashing_task(connection, item_date, start, minutes, exclude_id)

    def next_free_start(self, item_date: str, minutes: int, earliest: str,
                        exclude_id: str | None = None) -> str | None:
        """Return the first quarter-hour start from `earliest` with `minutes` free before midnight."""
        start = -(-minutes_after_midnight(earliest) // SLOT_MINUTES) * SLOT_MINUTES
        with self.connect() as connection:
            while start + minutes <= MINUTES_PER_DAY:
                clock = clock_time(start)
                if not self._clashing_task(connection, item_date, clock, minutes, exclude_id):
                    return clock
                start += SLOT_MINUTES
        return None

    def _length(self, connection: sqlite3.Connection, item: dict,
                exclude_id: str | None = None) -> tuple[int, str, str | None, str | None]:
        """Return a task's length, whose it is, the agent that estimated it, and on what basis.

        A length the user gives is theirs. Without one, a task made from a Library source takes the
        estimate its source gives ("estimateMinutes"; see learning_tasks), and any other its area
        agent's from the user's own lengths, which plans use until the user gives one.
        """
        if item["durationMinutes"] is not None:
            return item["durationMinutes"], "user", None, None
        if item.get("estimateMinutes"):
            return max(item["estimateMinutes"], MIN_TASK_MINUTES), "estimate", item["domain"], LEARNING_ESTIMATE_BASIS
        minutes, basis = self._provisional_estimate(connection, item["title"], item["domain"], exclude_id)
        return minutes, "estimate", item["domain"], basis

    def _provisional_estimate(self, connection: sqlite3.Connection, title: str, domain: str,
                              exclude_id: str | None = None) -> tuple[int, str]:
        """Return an area agent's first estimate of a task's length, and what it rests on.

        The median time the same task took on the days it was done ("taken"), else the median
        length the user ever gave it ("history"), else the median of the lengths they gave the
        area's tasks ("area"), else DEFAULT_ESTIMATE_MINUTES ("default"). A day it was partly done
        only raises the estimate: when the median time those days took is longer, it becomes the
        estimate ("taken"). Skipped and unanswered days, and times to check, never count; a time
        taken is rounded to ESTIMATE_STEP_MINUTES. The estimate is never under MIN_TASK_MINUTES, as
        older records may hold shorter lengths. Only lengths the user gave or times tasks took
        count, so estimates never feed on estimates.
        """
        rows = connection.execute(
            """SELECT title, duration_minutes FROM daily_items
               WHERE domain = ? AND duration_source = 'user' AND acceptance = 'accepted' AND id != ?""",
            (domain, exclude_id or ""),
        ).fetchall()
        named = title.strip().lower()
        times: dict[str, list[int]] = {"done": [], "partial": []}
        for row in connection.execute(
                """SELECT title, completion_status, duration_minutes, actual_start, actual_end, actual_minutes, time_confirmed
                   FROM daily_items WHERE domain = ? AND acceptance = 'accepted' AND id != ?
                     AND completion_status IN ('done', 'partial') AND actual_start IS NOT NULL""",
                (domain, exclude_id or "")):
            taken = _counted_time(row["actual_start"], row["actual_end"], row["duration_minutes"], row["time_confirmed"],
                                  row["actual_minutes"])
            if row["title"].strip().lower() == named and taken is not None:
                times[row["completion_status"]].append(taken)
        same = [row["duration_minutes"] for row in rows if row["title"].strip().lower() == named]
        if times["done"]:
            minutes, basis = _stepped(median(times["done"])), TAKEN_BASIS
        elif same:
            minutes, basis = round(median(same)), "history"
        elif rows:
            minutes, basis = round(median(row["duration_minutes"] for row in rows)), "area"
        else:
            minutes, basis = DEFAULT_ESTIMATE_MINUTES, "default"
        if times["partial"] and _stepped(median(times["partial"])) > minutes:
            minutes, basis = _stepped(median(times["partial"])), TAKEN_BASIS
        return max(minutes, MIN_TASK_MINUTES), basis

    def daily_item(self, item_id: str) -> dict | None:
        """Return one dated record, as `daily_items` lists it, or None when there is none."""
        with self.connect() as connection:
            row = connection.execute("SELECT item_date FROM daily_items WHERE id = ?", (item_id,)).fetchone()
        return next((item for item in self.daily_items(row["item_date"]) if item["id"] == item_id), None) if row else None

    def day_areas(self, plan_date: str) -> set[str]:
        """Return the areas of a day's accepted tasks, whose agents a change to the day's plan concerns."""
        with self.connect() as connection:
            return {row["domain"] for row in connection.execute(
                "SELECT DISTINCT domain FROM daily_items WHERE item_date = ? AND acceptance = 'accepted'", (plan_date,))}

    def user_lengths(self, domain: str, limit: int = 8) -> list[tuple[str, int]]:
        """Return the titles and lengths the user most recently gave the area's tasks."""
        with self.connect() as connection:
            return [(row["title"], row["duration_minutes"]) for row in connection.execute(
                """SELECT title, duration_minutes FROM daily_items
                   WHERE domain = ? AND duration_source = 'user' AND acceptance = 'accepted'
                   ORDER BY item_date DESC, rowid DESC LIMIT ?""",
                (domain, limit),
            )]

    def apply_model_estimate(self, item_id: str, minutes: int, basis: str = "model") -> bool:
        """Replace a task's estimated length with the local model's, or with its source's when that
        changed, never under MIN_TASK_MINUTES.

        Nothing changes when the user has given the task a length meanwhile, or when a fixed task
        would then overlap another.

        Args:
            basis: What the new estimate rests on: "model", or LEARNING_ESTIMATE_BASIS for a source.

        Returns:
            True when the length changed.
        """
        minutes = max(minutes, MIN_TASK_MINUTES)
        with self.connect() as connection:
            row = connection.execute(
                "SELECT item_date, start_time, duration_source FROM daily_items WHERE id = ?", (item_id,)
            ).fetchone()
            if not row or row["duration_source"] != "estimate":
                return False
            if row["start_time"] and self._clashing_task(connection, row["item_date"], row["start_time"], minutes, item_id):
                return False
            connection.execute(
                """UPDATE daily_items SET duration_minutes = ?, estimate_basis = ?
                   WHERE id = ? AND duration_source = 'estimate'""",
                (minutes, basis, item_id),
            )
        return True

    def create_daily_item(self, item: dict) -> dict:
        """Store a dated task or commitment supplied by the user.

        A task with a start time may not overlap another one on that day. A task without a length
        gets its area agent's provisional estimate, which plans use until the user gives one.
        """
        with self.connect() as connection:
            item_id = self._create_item(connection, item)
        return next(record for record in self.daily_items(item["date"]) if record["id"] == item_id)

    def check_new_item(self, item: dict) -> None:
        """Check that a new task would be saved, without saving it, so Ava proposes only what applies.

        Raises:
            ValueError, PermissionError: Why create_daily_item would refuse it.
        """
        with self.connect() as connection:
            self._create_item(connection, item)
            connection.rollback()

    def _create_item(self, connection: sqlite3.Connection, item: dict) -> str:
        """Store a new task within an open transaction, as create_daily_item describes.

        Returns:
            The task's id.
        """
        _writable_item_day(item["date"])
        _check_length(item["durationMinutes"])
        item_id = _id("item")
        self._check_goal(connection, item.get("goalId"), item["domain"])
        minutes, source, estimated_by, basis = self._length(connection, item)
        # A fixed start may be at any hour; only another task, a meal or midnight stands in its way.
        if item["startTime"] and minutes_after_midnight(item["startTime"]) + minutes > MINUTES_PER_DAY:
            raise ValueError(f"starting at {item['startTime']} for {minutes} minutes, it would run past midnight")
        clash = item["startTime"] and self._clashing_task(connection, item["date"], item["startTime"], minutes)
        if clash:
            raise ValueError(_clash_message(clash))
        # A repeating task starts its own series, which every copy of it carries.
        connection.execute(
            """INSERT INTO daily_items
               (id, item_date, goal_id, title, detail, domain, start_time,
                duration_minutes, constraint_kind, repeat_kind, repeat_series_id, created_at,
                duration_source, estimated_by, estimate_basis)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (item_id, item["date"], item.get("goalId"), item["title"], item["detail"],
             item["domain"], item["startTime"], minutes,
             item["constraintKind"], item["repeatKind"], item_id if item["repeatKind"] != "none" else None, _now(),
             source, estimated_by, basis),
        )
        if item.get("learning"):
            _add_learning(connection, item_id, item["learning"])
        return item_id

    def update_daily_item(self, item_id: str, item: dict) -> dict:
        """Update an owned daily record on today or a later day.

        A past task changes only through Ava, whose confirmed proposals apply through decide_action,
        so this refuses a task on a past day, and a move onto one.

        A new day, start time or length may not make the task overlap another one on that day. A
        task left without a length keeps its estimate, or gets a new one when its area changes. A
        task sent without a status keeps the one it has. Its plans keep the times and lengths they
        scheduled, which only a replacement changes, but take its new title, detail and area.
        """
        with self.connect() as connection:
            stored = connection.execute("SELECT item_date FROM daily_items WHERE id = ?", (item_id,)).fetchone()
            if stored and min(stored["item_date"], item["date"]) < date.today().isoformat():
                raise PermissionError(_PAST_TASK_MESSAGE)
            self._update_item(connection, item_id, item)
        return next(record for record in self.daily_items(item["date"]) if record["id"] == item_id)

    def check_item_edit(self, item_id: str, item: dict) -> None:
        """Check that an edit would be saved, without saving it, so Ava proposes only what applies.

        Raises:
            ValueError, PermissionError: Why update_daily_item would refuse it.
        """
        with self.connect() as connection:
            self._update_item(connection, item_id, item)
            connection.rollback()

    def _update_item(self, connection: sqlite3.Connection, item_id: str, item: dict) -> None:
        """Update a task within an open transaction, as update_daily_item describes."""
        prior = connection.execute(
            f"""SELECT id, item_date, title, start_time, acceptance, duration_minutes, domain, duration_source,
                      estimated_by, estimate_basis, completion_status, NOT {_GOAL_NOT_PAUSED} AS paused
               FROM daily_items WHERE id = ?""", (item_id,)
        ).fetchone()
        if not prior:
            raise ValueError("Daily item not found")
        if item["date"] != prior["item_date"]:
            # Moved off its day, today or later: that day's proposed plans let it go.
            self._drop_from_drafts(connection, dict(prior), prior["item_date"])
        if prior["acceptance"] != "accepted":
            raise PermissionError("Accept this suggestion before changing it")
        status = item["status"] or prior["completion_status"]
        if item["date"] > date.today().isoformat() and status != "planned":
            raise PermissionError("Future outcomes cannot be reported before the day arrives")
        if prior["paused"] and status != prior["completion_status"]:
            raise PermissionError(_PAUSED_MESSAGE)
        _check_length(item["durationMinutes"], prior["duration_minutes"])
        self._check_goal(connection, item.get("goalId"), item["domain"])
        self._check_area_move(connection, item_id, prior["domain"], item["domain"])
        kept = (item["durationMinutes"] is None and prior["duration_source"] == "estimate"
                and prior["domain"] == item["domain"])
        minutes, source, estimated_by, basis = (
            (prior["duration_minutes"], "estimate", prior["estimated_by"], prior["estimate_basis"]) if kept
            else self._length(connection, item, item_id))
        timing = (item["date"], item["startTime"], minutes)
        if item["startTime"] and timing != (prior["item_date"], prior["start_time"], prior["duration_minutes"]):
            clash = self._clashing_task(connection, item["date"], item["startTime"], minutes, item_id)
            if clash:
                raise ValueError(_clash_message(clash))
        # A task made to repeat starts a series; one in a series keeps it, whatever it now says.
        updated = connection.execute(
            """UPDATE daily_items SET item_date = ?, goal_id = ?, title = ?, detail = ?,
               domain = ?, start_time = ?, duration_minutes = ?, constraint_kind = ?,
               repeat_kind = ?, repeat_series_id = COALESCE(repeat_series_id, CASE WHEN ? != 'none' THEN id END),
               completion_status = ?, duration_source = ?,
               estimated_by = ?, estimate_basis = ? WHERE id = ?""",
            (item["date"], item.get("goalId"), item["title"], item["detail"],
             item["domain"], item["startTime"], minutes,
             item["constraintKind"], item["repeatKind"], item["repeatKind"],
             status, source, estimated_by, basis, item_id),
        )
        if not updated.rowcount:
            raise ValueError("Daily item not found")
        connection.execute(
            "UPDATE plan_entries SET completion_status = ?, title = ?, detail = ?, domain = ? WHERE source_item_id = ?",
            (status, item["title"], item["detail"], item["domain"], item_id),
        )
        self._record_time(connection, item_id, status, prior["completion_status"], item["date"])

    @staticmethod
    def _check_area_move(connection: sqlite3.Connection, item_id: str, domain: str, new_domain: str) -> None:
        """Keep a Learn task that uses Library sources in Learn: a Library source is only ever a learning task's.

        Raises:
            PermissionError: When the task would leave Learn while it uses a source, as the learning task made
                from it or through a link, naming the sources, each of which it can unlink first.
        """
        if domain != "learning" or new_domain == "learning":
            return
        names = [library_name(row[0]) for row in connection.execute(
            """SELECT s.title FROM (SELECT source_id, 0 AS kind, '' AS at FROM learning_tasks WHERE item_id = ?
                                    UNION ALL SELECT source_id, 1, linked_at FROM task_sources WHERE item_id = ?) u
               JOIN knowledge_sources s ON s.id = u.source_id ORDER BY u.kind, u.at""", (item_id, item_id))]
        if names:
            listed = names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"
            raise PermissionError(f"It uses {listed} from your Library, so it stays in Learn. "
                                  f"Unlink {'it' if len(names) == 1 else 'them'} to move it")

    def task_links(self, item_id: str) -> list[dict]:
        """The Library sources a task links as references, in the order they were linked: each one's id, name as
        the Library shows it, and origin."""
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT s.id, s.title, s.origin FROM task_sources t JOIN knowledge_sources s ON s.id = t.source_id
                   WHERE t.item_id = ? ORDER BY t.linked_at, t.rowid""", (item_id,)).fetchall()
        return [{"id": row["id"], "title": library_name(row["title"]), "origin": row["origin"]} for row in rows]

    def link_sources(self, item_id: str, source_ids: list[str], link: bool = True, past: bool = False) -> None:
        """Link Library sources to a Learn task as references, or unlink them; a source linked already stays once.
        Unlinking the source a learning task was made from leaves the task its checklist and ticks, and the
        source in the Library.

        Args:
            past: Allow a past day's task, as Ava's confirmed card does; otherwise it changes only through her.

        Raises:
            LookupError: For a task, or a source to link, that isn't there.
            ValueError: For a task outside Learn: only Learn tasks link Library sources.
            PermissionError: For a past day's task, unless `past`.
        """
        with self.connect() as connection:
            self._link_sources(connection, item_id, source_ids, link, past)

    @staticmethod
    def _link_sources(connection: sqlite3.Connection, item_id: str, source_ids: list[str], link: bool, past: bool) -> None:
        """Link or unlink a task's sources within an open transaction, as link_sources describes."""
        task = connection.execute("SELECT item_date, domain FROM daily_items WHERE id = ?", (item_id,)).fetchone()
        if not task:
            raise LookupError("That task isn't there.")
        if task["domain"] != "learning":
            raise ValueError("Only Learn tasks link Library sources.")
        if not past and task["item_date"] < date.today().isoformat():
            raise PermissionError(_PAST_TASK_MESSAGE)
        for source_id in source_ids:
            if not link:
                connection.execute("DELETE FROM task_sources WHERE item_id = ? AND source_id = ?", (item_id, source_id))
                connection.execute("UPDATE learning_tasks SET source_id = NULL WHERE item_id = ? AND source_id = ?",
                                   (item_id, source_id))
            elif not connection.execute("SELECT 1 FROM knowledge_sources WHERE id = ?", (source_id,)).fetchone():
                raise LookupError("That source isn't in the Library.")
            else:
                connection.execute("INSERT OR IGNORE INTO task_sources (item_id, source_id, linked_at) VALUES (?, ?, ?)",
                                   (item_id, source_id, _now()))

    def source_tasks(self) -> dict[str, list[dict]]:
        """For each Library source, the tasks that use it: a learning task made from it ("checklist") and each task
        linking it ("reference"), with their id, title, date and goal, those of a goal first by its title, those
        without one last, each by date."""
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT u.source_id, u.role, i.id, i.title, i.item_date, i.goal_id, g.title AS goal_title
                   FROM (SELECT source_id, item_id, 'checklist' AS role FROM learning_tasks WHERE source_id IS NOT NULL
                         UNION ALL SELECT source_id, item_id, 'reference' FROM task_sources) u
                   JOIN daily_items i ON i.id = u.item_id LEFT JOIN goals g ON g.id = i.goal_id
                   WHERE i.acceptance != 'dismissed'
                   ORDER BY g.title IS NULL, g.title, i.item_date, i.rowid""").fetchall()
        tasks: dict[str, list[dict]] = {}
        for row in rows:
            tasks.setdefault(row["source_id"], []).append(
                {"itemId": row["id"], "title": row["title"], "date": row["item_date"], "goalId": row["goal_id"],
                 "goalTitle": row["goal_title"], "role": row["role"]})
        return tasks

    def linked_sources(self, item_ids: Iterable[str]) -> list[str]:
        """The Library sources some tasks use, as the source a learning task was made from or as a reference."""
        ids = list(item_ids)
        marks = ",".join("?" for _ in ids)
        with self.connect() as connection:
            return [row[0] for row in connection.execute(
                f"""SELECT source_id FROM learning_tasks WHERE source_id IS NOT NULL AND item_id IN ({marks})
                    UNION SELECT source_id FROM task_sources WHERE item_id IN ({marks})""", ids + ids)]

    def links_offered(self, item_id: str, series_id: str | None) -> bool:
        """Whether Ava has suggested Library sources for a task, or for any day of its repeat, already: once
        offered, pending, confirmed or dismissed, a task is never offered sources again."""
        with self.connect() as connection:
            return bool(connection.execute(
                """SELECT 1 FROM proposed_actions WHERE action_type = 'link_sources'
                   AND json_extract(payload_json, '$.proposedBy') = 'learning'
                   AND (json_extract(payload_json, '$.itemId') = ?
                        OR (? IS NOT NULL AND json_extract(payload_json, '$.seriesId') = ?))""",
                (item_id, series_id, series_id)).fetchone())

    def folder_checks(self, folder_id: str) -> dict[str, str]:
        """The content hash each of a folder's files was last checked at, by its path in the folder; see folder_check."""
        with self.connect() as connection:
            return dict(connection.execute("SELECT relative_path, content_hash FROM folder_checks WHERE folder_id = ?",
                                           (folder_id,)).fetchall())

    def record_check(self, folder_id: str, path: str, content_hash: str, reason: str | None, study: str) -> None:
        """Keep what checking a folder's file at its content found, to be reported once: why it can't be read, or
        None, and whether it is study material ("yes", "no", or "unchecked" without the local model)."""
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO folder_checks (folder_id, relative_path, content_hash, reason, study, checked_at, reported)
                   VALUES (?, ?, ?, ?, ?, ?, 0)
                   ON CONFLICT(folder_id, relative_path) DO UPDATE SET content_hash = excluded.content_hash,
                     reason = excluded.reason, study = excluded.study, checked_at = excluded.checked_at, reported = 0""",
                (folder_id, path, content_hash, reason, study, _now()))

    def unreported_checks(self, folder_id: str) -> list[dict]:
        """A folder's checked files Ava hasn't reported yet, in path order: each one's "path", "reason" and "study"."""
        with self.connect() as connection:
            return [{"path": row["relative_path"], "reason": row["reason"], "study": row["study"]} for row in connection.execute(
                """SELECT relative_path, reason, study FROM folder_checks WHERE folder_id = ? AND reported = 0
                   ORDER BY relative_path""", (folder_id,))]

    def mark_reported(self, folder_id: str, paths: list[str]) -> None:
        """Mark a folder's checked files reported, so Ava names each one once."""
        with self.connect() as connection:
            connection.executemany("UPDATE folder_checks SET reported = 1 WHERE folder_id = ? AND relative_path = ?",
                                   [(folder_id, path) for path in paths])

    def report_item(self, item_id: str, status: str) -> dict:
        """Report one of today's tasks, as the menu bar's panel does, with its entries in the day's plans,
        recording the time it took (see _record_time).

        Returns:
            The task's id, status, date and area.

        Raises:
            ValueError: When there is no such task.
            PermissionError: For a task on another day, an agent's suggestion not yet accepted, or a
                task whose goal is paused.
        """
        with self.connect() as connection:
            row = connection.execute(
                f"""SELECT item_date, domain, completion_status, acceptance, NOT {_GOAL_NOT_PAUSED} AS paused
                    FROM daily_items WHERE id = ?""", (item_id,)).fetchone()
            if not row:
                raise ValueError("Daily item not found")
            _writable_day(row["item_date"])
            if row["acceptance"] != "accepted":
                raise PermissionError("Accept this suggestion before reporting it")
            if row["paused"] and status != row["completion_status"]:
                raise PermissionError(_PAUSED_MESSAGE)
            connection.execute("UPDATE daily_items SET completion_status = ? WHERE id = ?", (status, item_id))
            connection.execute("UPDATE plan_entries SET completion_status = ? WHERE source_item_id = ?", (status, item_id))
            self._record_time(connection, item_id, status, row["completion_status"], row["item_date"])
        return {"id": item_id, "status": status, "date": row["item_date"], "domain": row["domain"]}

    def catch_up_tasks(self, day: str) -> list[dict]:
        """Return a day's tasks to catch up on, as Today's catch-up sheet and Ava's card list them: the
        user's accepted tasks whose goal isn't paused, scheduled ones in time order, then those without a
        start time in the order they were made.

        Returns:
            Each task's "id", "title", "start" (a set plan's, else its own, or None), "minutes", "domain",
            "status", and whether it is "noReply" (see daily_items_between).
        """
        late = day < date.today().isoformat() or (day == date.today().isoformat() and _local_time() >= DAY_END)
        with self.connect() as connection:
            tasks = self._time_tasks(connection, day)
        return [{"id": task["id"], "title": task["title"], "start": task["start"], "minutes": task["minutes"],
                 "domain": task["domain"], "status": task["status"], "noReply": late and task["status"] == "planned"}
                for task in sorted(tasks, key=_day_order) if not task["paused"]]

    def catch_up(self, statuses: dict[str, str]) -> dict:
        """Set several of today's tasks' statuses in one save, as Today's catch-up sheet does, keeping what
        they had so undo_catch_up can restore it. A task left out stays as it is, and one given the status
        it has is unchanged. Each status records its time as report_item's does (see _record_time).

        Args:
            statuses: The status set for each task, by id: "done", "partial" or "skipped".

        Returns:
            The "date", how many tasks were "updated", and each one changed in "items" (its "id", "status"
            and "domain").

        Raises:
            ValueError: When a task isn't there.
            PermissionError: For a task on another day, a suggestion not yet accepted, or a task whose goal
                is paused; nothing is saved.
        """
        today = date.today().isoformat()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            changed = self._apply_statuses(connection, today, statuses, strict=True)
            if changed:
                connection.execute(
                    """INSERT INTO preferences (key, value_json, updated_at) VALUES (?, ?, ?)
                       ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at""",
                    (CATCH_UP_UNDO_KEY, json.dumps({"date": today, "items": changed}), _now()))
        return {"date": today, "updated": len(changed),
                "items": [{key: item[key] for key in ("id", "status", "domain")} for item in changed]}

    def keep_catch_up_offers(self, action_ids: list[str]) -> None:
        """Keep, with today's last catch-up save, the cards it offered through Ava (a task's usual length, a
        Learning task's next session), so undo_catch_up withdraws them."""
        if not action_ids:
            return
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT value_json FROM preferences WHERE key = ?", (CATCH_UP_UNDO_KEY,)).fetchone()
            if not row:
                return
            saved = json.loads(row["value_json"])
            saved["offers"] = [*saved.get("offers", []), *action_ids]
            connection.execute("UPDATE preferences SET value_json = ?, updated_at = ? WHERE key = ?",
                               (json.dumps(saved), _now(), CATCH_UP_UNDO_KEY))

    def undo_catch_up(self) -> dict:
        """Undo the last catch-up save, once, while it is still today's: each task it changed that hasn't
        changed since gets back its status, when it was set and the time it took, with its entries in the
        day's plans; and the cards it offered through Ava, still pending, are withdrawn, so the same offers
        may come again.

        Returns:
            The "date", how many tasks were "restored", and each one's "id" and "domain" in "items", and
            how many offers were "withdrawn".

        Raises:
            PermissionError: When there is no save of today's to undo.
        """
        today = date.today().isoformat()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT value_json FROM preferences WHERE key = ?", (CATCH_UP_UNDO_KEY,)).fetchone()
            saved = json.loads(row["value_json"]) if row else None
            if not saved or saved["date"] != today:
                raise PermissionError("There is no catch-up of today's to undo")
            connection.execute("DELETE FROM preferences WHERE key = ?", (CATCH_UP_UNDO_KEY,))
            restored = []
            for item in saved["items"]:
                prior = item["prior"]
                undone = connection.execute(
                    """UPDATE daily_items SET completion_status = ?, status_at = ?, actual_start = ?, actual_end = ?,
                              actual_minutes = ?, time_confirmed = ? WHERE id = ? AND completion_status = ?""",
                    (prior["status"], prior["statusAt"], prior["actualStart"], prior["actualEnd"], prior.get("actualMinutes"),
                     prior["timeConfirmed"], item["id"], item["status"]))
                if undone.rowcount:
                    connection.execute("UPDATE plan_entries SET completion_status = ? WHERE source_item_id = ?",
                                       (prior["status"], item["id"]))
                    restored.append({"id": item["id"], "domain": item["domain"]})
            withdrawn = self._withdraw_offers(connection, saved.get("offers", []))
        return {"date": today, "restored": len(restored), "items": restored, "withdrawn": withdrawn}

    @staticmethod
    def _withdraw_offers(connection: sqlite3.Connection, action_ids: list[str]) -> int:
        """Withdraw, within an open transaction, the cards offered through Ava that are still pending: each
        card and the message that offered it are removed.

        Returns:
            How many were withdrawn.
        """
        pending = {row["id"] for row in connection.execute(
            f"""SELECT id FROM proposed_actions WHERE status = 'pending'
                AND id IN ({','.join('?' * len(action_ids))})""", tuple(action_ids))} if action_ids else set()
        if not pending:
            return 0
        offering = [row["id"] for row in connection.execute("SELECT id, values_json FROM ava_notices")
                    if json.loads(row["values_json"]).get("actionId") in pending]
        connection.executemany("DELETE FROM ava_notices WHERE id = ?", [(notice_id,) for notice_id in offering])
        connection.executemany("DELETE FROM proposed_actions WHERE id = ?", [(action_id,) for action_id in pending])
        return len(pending)

    def _apply_statuses(self, connection: sqlite3.Connection, day: str, statuses: dict[str, str],
                        strict: bool) -> list[dict]:
        """Set, within an open transaction, several of a day's tasks' statuses at once, with their entries in
        the day's plans and the time each took (see _record_time). The day's tasks are read once, as they
        stood before any changed, so no task's status changes another's time.

        Args:
            day: The tasks' day, YYYY-MM-DD.
            statuses: The status set for each task, by id.
            strict: Refuse the whole save for a task that can't take its status, as the sheet does; else
                leave that task as it is, as Ava's card does for a task changed since it was made.

        Returns:
            Each task changed: its "id", "status" and "domain", and what it had before ("prior": its
            "status", "statusAt", "actualStart", "actualEnd", "actualMinutes" and "timeConfirmed").

        Raises:
            ValueError: When strict, for a task that isn't there.
            PermissionError: When strict, for a task on another day, a suggestion not yet accepted, or a
                task whose goal is paused.
        """
        if not statuses:
            return []
        rows = {row["id"]: row for row in connection.execute(
            f"""SELECT id, item_date, domain, completion_status, acceptance, status_at, actual_start, actual_end,
                       actual_minutes, time_confirmed, NOT {_GOAL_NOT_PAUSED} AS paused
                FROM daily_items WHERE id IN ({','.join('?' * len(statuses))})""", tuple(statuses)).fetchall()}
        changing = []
        for item_id, status in statuses.items():
            row = rows.get(item_id)
            refusal = (ValueError("Daily item not found") if not row
                       else PermissionError("Only the day's own tasks can be caught up on") if row["item_date"] != day
                       else PermissionError("Accept this suggestion before reporting it") if row["acceptance"] != "accepted"
                       else PermissionError(_PAUSED_MESSAGE) if row["paused"] and status != row["completion_status"]
                       else None)
            if refusal and strict:
                raise refusal
            if not refusal and status != row["completion_status"]:
                changing.append((row, status))
        tasks = self._time_tasks(connection, day) if changing else []
        changed = []
        for row, status in changing:
            connection.execute("UPDATE daily_items SET completion_status = ? WHERE id = ?", (status, row["id"]))
            connection.execute("UPDATE plan_entries SET completion_status = ? WHERE source_item_id = ?", (status, row["id"]))
            self._record_time(connection, row["id"], status, row["completion_status"], day, tasks)
            changed.append({"id": row["id"], "status": status, "domain": row["domain"],
                            "prior": {"status": row["completion_status"], "statusAt": row["status_at"],
                                      "actualStart": row["actual_start"], "actualEnd": row["actual_end"],
                                      "actualMinutes": row["actual_minutes"], "timeConfirmed": row["time_confirmed"]}})
        return changed

    def _record_time(self, connection: sqlite3.Connection, item_id: str, status: str, prior: str, day: str,
                     tasks: list[dict] | None = None) -> None:
        """Record, within an open transaction, when a task's status was set and the time it took.

        Its first status records the moment, the first stretch's start and the last one's stop, and the
        minutes of every stretch it was current added up (see time_taken): today's at the local time
        now, an earlier day's as after that day ended. A status changed later keeps that time, as the
        task had already stopped; set back to planned, the task has no time again. No other task's
        time changes.

        Args:
            status: The status now set.
            prior: The status it had.
            day: The task's day, YYYY-MM-DD.
            tasks: The day's tasks as _time_tasks reads them, when a save setting several statuses read
                them once, before any changed; else they are read now.
        """
        if status == prior:
            return
        if status == "planned":
            connection.execute("""UPDATE daily_items SET status_at = NULL, actual_start = NULL, actual_end = NULL,
                                  actual_minutes = NULL, time_confirmed = 0 WHERE id = ?""", (item_id,))
            return
        if prior != "planned":
            return
        moment = _local_time() if day == date.today().isoformat() else AFTER_DAY
        tasks = self._time_tasks(connection, day) if tasks is None else tasks
        task = next((task for task in tasks if task["id"] == item_id), None)
        if task is None:
            return
        meals = self._day_meals(connection, day)
        start, end = actual_times(task, tasks, meals, moment, status)
        connection.execute(
            "UPDATE daily_items SET status_at = ?, actual_start = ?, actual_end = ?, actual_minutes = ? WHERE id = ?",
            (moment, start, end, minutes_taken(task, tasks, meals, moment, status), item_id))

    def _time_tasks(self, connection: sqlite3.Connection, day: str) -> list[dict]:
        """Return a day's tasks as time_taken reads them: the user's accepted tasks, each at the time and
        length a set plan gave it, else its own."""
        placed = {row["source_item_id"]: row for row in connection.execute(
            """SELECT e.source_item_id, e.start_time, e.duration_minutes FROM plan_entries e
               JOIN daily_confirmations c ON c.variant_id = e.variant_id
               WHERE c.plan_date = ? AND e.source_item_id IS NOT NULL AND e.removed_at IS NULL""", (day,))}
        tasks = []
        for row in connection.execute(
                f"SELECT {_ITEM_FIELDS} FROM daily_items WHERE item_date = ? AND acceptance = 'accepted'", (day,)):
            entry = placed.get(row["id"])
            made = datetime.fromisoformat(row["createdAt"]).astimezone()
            tasks.append({
                "id": row["id"], "title": row["title"], "domain": row["domain"], "durationSource": row["durationSource"],
                "start": entry["start_time"] if entry else row["start_time"],
                "minutes": entry["duration_minutes"] if entry else row["duration_minutes"],
                "status": row["completion_status"], "statusAt": row["statusAt"], "createdAt": row["createdAt"],
                "madeAt": (None if made.date().isoformat() < day
                           else made.strftime("%H:%M") if made.date().isoformat() == day else AFTER_DAY),
                "currentSince": row["currentSince"], "paused": row["goalStatus"] == "paused",
            })
        return tasks

    def now(self) -> dict:
        """Return what the menu bar shows now: today's current and next task (see time_taken), the
        minutes the current one has taken, and the title in the interface's language. A task without
        a start time is marked when first seen current, as it may have been current since the day began.

        Returns:
            The "date" and "time", the "current" and "next" task (each its id, title, start or None,
            minutes, durationSource, area and status) or None, "taken", and the "title" line.
        """
        day, clock = date.today().isoformat(), _local_time()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            tasks, meals = self._time_tasks(connection, day), self._day_meals(connection, day)
            current, upcoming = current_and_next(tasks, meals, clock)
            if current and not current["start"] and not current["currentSince"]:
                connection.execute("UPDATE daily_items SET current_since = ? WHERE id = ? AND current_since IS NULL",
                                   (clock, current["id"]))
                current["currentSince"] = clock
            taken = taken_so_far(current, tasks, meals, clock) if current else 0
            row = connection.execute("SELECT value_json FROM preferences WHERE key = ?", (INTERFACE_LANGUAGE_KEY,)).fetchone()

        def view(task: dict | None) -> dict | None:
            return task and {key: task[key] for key in ("id", "title", "start", "minutes", "durationSource", "domain",
                                                        "status")}

        return {"date": day, "time": clock, "current": view(current), "next": view(upcoming), "taken": taken,
                "title": title_line(current, upcoming, taken, json.loads(row["value_json"]) if row else "en")}

    def set_interface_language(self, language: str) -> None:
        """Keep the interface's language, "en" or "zh", in which the menu bar's title is written."""
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO preferences (key, value_json, updated_at) VALUES (?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at""",
                (INTERFACE_LANGUAGE_KEY, json.dumps(language), _now()))

    def set_item_acceptance(self, item_id: str, decision: str) -> dict:
        """Accept or dismiss an agent-prepared record that is waiting for the user.

        Accepting makes it the user's own, so plans may schedule it. Dismissing hides it and keeps
        it on file, so the same work is not prepared again for that date.
        """
        if decision not in ("accepted", "dismissed"):
            raise ValueError("Choose to accept or dismiss")
        with self.connect() as connection:
            row = connection.execute(
                "SELECT item_date, acceptance, domain FROM daily_items WHERE id = ?", (item_id,)
            ).fetchone()
            if not row:
                raise ValueError("Daily item not found")
            _writable_item_day(row["item_date"])
            if row["acceptance"] != "pending":
                raise PermissionError("This suggestion has already been decided")
            connection.execute(
                "UPDATE daily_items SET acceptance = ? WHERE id = ?", (decision, item_id)
            )
        return {"id": item_id, "date": row["item_date"], "domain": row["domain"], "acceptance": decision}

    def delete_daily_item(self, item_id: str) -> dict:
        """Remove an owned record, on any day, past ones included.

        A task today's or a later day's set plan scheduled stays: only replacing the plan changes
        it. A past day's plan never changes, so a past task it scheduled is removed and the plan
        keeps its entry, marked removed, on show but left out of its counts and reports. Plans
        proposed for today or later and not set drop the task, so setting one can't schedule it;
        a past day's proposals keep their own copy, which simply loses the link.
        """
        with self.connect() as connection:
            return self._delete_item(connection, item_id)

    def series_day(self, series_id: str, day: str, exclude_id: str | None = None) -> bool:
        """Whether a repeat already has its own day on `day`, other than the task `exclude_id`."""
        with self.connect() as connection:
            return self._series_day(connection, series_id, day, exclude_id)

    @staticmethod
    def _series_day(connection: sqlite3.Connection, series_id: str, day: str, exclude_id: str | None) -> bool:
        """See series_day; within an open transaction."""
        return connection.execute(
            """SELECT 1 FROM daily_items WHERE repeat_series_id = ? AND item_date = ? AND id IS NOT ?
                 AND acceptance != 'dismissed'""", (series_id, day, exclude_id)).fetchone() is not None

    def series_days_from(self, series_id: str, day: str) -> list[str]:
        """The dates of a repeat's own days from `day` on, earliest first, its dismissed ones left out."""
        with self.connect() as connection:
            return [row["item_date"] for row in connection.execute(
                """SELECT item_date FROM daily_items WHERE repeat_series_id = ? AND item_date >= ?
                     AND acceptance != 'dismissed' ORDER BY item_date""", (series_id, day))]

    def series_kind(self, series_id: str) -> str:
        """How a repeat repeats now: as a change waiting for its day says, else as its latest day says."""
        with self.connect() as connection:
            waiting = connection.execute("SELECT next_kind FROM repeat_series WHERE id = ?", (series_id,)).fetchone()
            latest = connection.execute(
                """SELECT repeat_kind FROM daily_items WHERE repeat_series_id = ? AND acceptance != 'dismissed'
                   ORDER BY item_date DESC, rowid DESC LIMIT 1""", (series_id,)).fetchone()
        return waiting["next_kind"] if waiting else latest["repeat_kind"] if latest else "none"

    def repeat_start(self, task: dict, kind: str) -> str:
        """The first day of a repeat started from a past task: today while there is still time for it, else
        the next day it falls on; a weekly one falls on the past task's weekday.

        There is still time for a task with a start that hasn't passed, or for one without a start
        that today's plan can still place among today's other tasks.
        """
        today = date.today()
        first = (today + timedelta(days=(date.fromisoformat(task["date"]).weekday() - today.weekday()) % 7)
                 if kind == "weekly" else today)
        if first == today:
            now = _local_time()
            to_do = [PlanItem(item["start_time"], item["title"], "", item["domain"], item["duration_minutes"])
                     for item in self.daily_items(today.isoformat()) if item["acceptance"] == "accepted"
                     and item["completion_status"] == "planned" and item.get("goalStatus") != "paused"]
            in_time = (task["start_time"] > now if task["start_time"] else
                       day_load([*to_do, PlanItem(None, task["title"], "", task["domain"], task["duration_minutes"])],
                                now, self.day_meals(today.isoformat()))["fits"])
            if not in_time:
                first += timedelta(days=7 if kind == "weekly" else 1)
        return first.isoformat()

    def repeat_change_start(self, series_id: str) -> str:
        """The first day a repeat stopped or switched from a past day changes on: today, unless today's own
        day was reported or today's set plan scheduled it, which keeps it as it was, so tomorrow."""
        today = date.today().isoformat()
        with self.connect() as connection:
            held = connection.execute(
                f"""SELECT 1 FROM daily_items WHERE repeat_series_id = ? AND item_date = ? AND acceptance != 'dismissed'
                      AND (completion_status != 'planned' OR {_IN_SET_PLAN})""", (series_id, today)).fetchone()
        return (date.today() + timedelta(days=1)).isoformat() if held else today

    def repeat_leaves(self, series_id: str, starts_on: str, kind: str, past_day: str) -> list[str]:
        """The days a repeat stopped or switched from a past day removes, earliest first; see _repeat_leaves."""
        with self.connect() as connection:
            return [copy["item_date"] for copy in self._repeat_leaves(connection, series_id, starts_on, kind, past_day)]

    @staticmethod
    def _repeat_leaves(connection: sqlite3.Connection, series_id: str, starts_on: str, kind: str,
                       past_day: str) -> list[sqlite3.Row]:
        """A repeat's own days from `starts_on` on, still to do, that a stop or a switch to `kind` leaves out.

        A stop leaves out every one; a switch to weekly those not on `past_day`'s weekday, the day the
        change is made from; a switch to daily none. A reported day is never among them.

        Returns:
            Each day's "id" and "item_date", earliest first.
        """
        weekday = date.fromisoformat(past_day).weekday()
        return [copy for copy in connection.execute(
            """SELECT id, item_date FROM daily_items WHERE repeat_series_id = ? AND item_date >= ?
                 AND completion_status = 'planned' AND acceptance != 'dismissed' ORDER BY item_date, rowid""",
            (series_id, starts_on)).fetchall()
            if kind == "none" or (kind == "weekly" and date.fromisoformat(copy["item_date"]).weekday() != weekday)]

    def _repeat_change(self, connection: sqlite3.Connection, task: dict, payload: dict) -> list[dict]:
        """Apply a repeat started, stopped or switched from a past day, within an open transaction.

        Started, the past task is the template of a new repeat's first day, on `startsOn`; the past
        task itself and the days between stay as they were. Stopped or switched, the repeat's own
        days from `startsOn` on that are still to do are deleted when the new repeat leaves them
        out (every one for a stop; for weekly, those not on the past task's weekday), as a delete
        would, so they leave proposed plans; the rest take the new repeat. Reported days are never
        touched, and `startsOn` is tomorrow when today's own day was reported or its set plan
        scheduled it. The change is kept for the series too, so the days copied forward follow it,
        a weekly one on the past task's weekday.

        Returns:
            Each deleted day's id, title, date and area, for its agents to be told.
        """
        if payload["mode"] == "start":
            start = task["start_time"]
            clash = start and self._clashing_task(connection, payload["startsOn"], start, task["duration_minutes"])
            if clash:
                raise ValueError(_clash_message(clash))
            item_id = _id("item")
            connection.execute(
                """INSERT INTO daily_items
                   (id, item_date, goal_id, title, detail, domain, start_time, duration_minutes, constraint_kind,
                    repeat_kind, repeat_series_id, created_at, duration_source, estimated_by, estimate_basis)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (item_id, payload["startsOn"], task["goalId"], task["title"], task["detail"], task["domain"], start,
                 task["duration_minutes"], task["constraint_kind"], payload["repeatKind"], item_id, _now(),
                 task["durationSource"], task["estimatedBy"], task["estimateBasis"]))
            return []
        kind, weekday = payload["repeatKind"], date.fromisoformat(task["date"]).weekday()
        removed = [self._delete_item(connection, copy["id"])
                   for copy in self._repeat_leaves(connection, payload["seriesId"], payload["startsOn"], kind, task["date"])]
        connection.execute(
            """UPDATE daily_items SET repeat_kind = ? WHERE repeat_series_id = ? AND item_date >= ?
                 AND completion_status = 'planned'""",
            (kind, payload["seriesId"], payload["startsOn"]))
        # A weekly repeat holds from its first day on the past task's weekday, whose weekday copies follow.
        start = date.fromisoformat(payload["startsOn"])
        holds_from = start + timedelta(days=(weekday - start.weekday()) % 7) if kind == "weekly" else start
        connection.execute(
            """INSERT INTO repeat_series (id, next_kind, next_from) VALUES (?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET next_kind = excluded.next_kind, next_from = excluded.next_from""",
            (payload["seriesId"], kind, holds_from.isoformat()))
        return removed

    def _past_task_edit(self, connection: sqlite3.Connection, task: dict, changes: dict) -> None:
        """Check an edit to a past task, and when it moves the task forward, mark its past day's entry.

        On its past day a task keeps its place: its start, length and timing don't change (the time it
        actually took may), and it moves only to today or a later day, never onto another past day, nor onto a day that already
        has its repeat's own day. Moved, its past day's set plan keeps the entry, marked removed and
        with the day it moved to, so it counts on its new day alone; that day's plans lose the link.

        Raises:
            PermissionError: Why the edit can't apply.
        """
        today = date.today().isoformat()
        moved_to = changes.get("date", task["date"])
        if moved_to < today:
            if moved_to != task["date"]:
                raise PermissionError("A task can't move onto a past day; move it to today or a later day")
            if any(field in changes for field in ("startTime", "durationMinutes", "constraintKind")):
                raise PermissionError("On a past day a task keeps its place: its start, length and timing can't change")
            return
        if task["repeatSeriesId"] and self._series_day(connection, task["repeatSeriesId"], moved_to, task["id"]):
            raise PermissionError(f"“{task['title']}” already has its repeat's day on {moved_to}")
        connection.execute(
            """UPDATE plan_entries SET removed_at = ?, moved_to = ? WHERE source_item_id = ?
               AND variant_id IN (SELECT variant_id FROM daily_confirmations WHERE plan_date = ?)""",
            (_now(), moved_to, task["id"], task["date"]))
        connection.execute(
            """UPDATE plan_entries SET source_item_id = NULL WHERE source_item_id = ? AND variant_id IN (
                 SELECT v.id FROM plan_variants v JOIN plan_sets s ON s.id = v.plan_set_id WHERE s.plan_date = ?)""",
            (task["id"], task["date"]))

    def set_plan_keeps(self, item_id: str) -> bool:
        """Whether a set plan scheduled a task, so the plan keeps an entry for it."""
        with self.connect() as connection:
            return bool(connection.execute(
                f"SELECT {_IN_SET_PLAN} FROM daily_items WHERE id = ?", (item_id,)).fetchone()[0])

    @staticmethod
    def _drop_from_drafts(connection: sqlite3.Connection, task: dict, day: str) -> None:
        """Take a task off the plans proposed for its day, today or later, and not set, as it leaves the day.

        Each such plan loses its entry, and its sentences and description are rewritten from the
        entries it has left (see planner.notes_without), which keep their times, so setting it can't
        schedule the task and nothing in it names the task. A past day's plans stay as they were.

        Args:
            task: The task: its "id", "title", "domain", "start_time" and "duration_minutes".
            day: The day it leaves.
        """
        if day < date.today().isoformat():
            return
        drafts = connection.execute(
            """SELECT v.id, v.notes_json FROM plan_variants v JOIN plan_sets s ON s.id = v.plan_set_id
               WHERE s.plan_date = ? AND v.id NOT IN (SELECT variant_id FROM daily_confirmations)
                 AND EXISTS (SELECT 1 FROM plan_entries e WHERE e.variant_id = v.id AND e.source_item_id = ?)""",
            (day, task["id"])).fetchall()
        for draft in drafts:
            connection.execute("DELETE FROM plan_entries WHERE variant_id = ? AND source_item_id = ?", (draft["id"], task["id"]))
            # A plan proposed by an earlier version kept no sentences, only its description, which stays.
            if not json.loads(draft["notes_json"]):
                continue
            left = [dict(entry) for entry in connection.execute(
                "SELECT title, start_time, duration_minutes, constraint_kind FROM plan_entries WHERE variant_id = ?",
                (draft["id"],))]
            notes = notes_without(json.loads(draft["notes_json"]), task, left)
            connection.execute("UPDATE plan_variants SET notes_json = ?, rationale = ? WHERE id = ?",
                               (json.dumps(notes), " ".join(note["text"] for note in notes), draft["id"]))

    def _delete_item(self, connection: sqlite3.Connection, item_id: str) -> dict:
        """Remove a task within an open transaction, as delete_daily_item describes.

        Returns:
            The removed task's id, title, date and area.
        """
        row = connection.execute(
            f"""SELECT id, item_date, title, domain, start_time, duration_minutes, {_IN_SET_PLAN} AS in_set_plan
                FROM daily_items WHERE id = ?""",
            (item_id,)).fetchone()
        if not row:
            raise ValueError("Daily item not found")
        if row["in_set_plan"] and row["item_date"] >= date.today().isoformat():
            raise PermissionError(_SET_PLAN_KEEPS_MESSAGE)
        # The past day's set plan keeps the entry, marked removed; nothing else in it changes.
        connection.execute(
            """UPDATE plan_entries SET removed_at = ? WHERE source_item_id = ?
               AND variant_id IN (SELECT variant_id FROM daily_confirmations)""", (_now(), item_id))
        self._drop_from_drafts(connection, dict(row), row["item_date"])
        connection.execute(
            "UPDATE plan_entries SET source_item_id = NULL WHERE source_item_id = ?", (item_id,)
        )
        connection.execute(
            "UPDATE daily_items SET origin_source_item_id = NULL WHERE origin_source_item_id = ?",
            (item_id,),
        )
        connection.execute("DELETE FROM daily_items WHERE id = ?", (item_id,))
        # A checklist no task shows any more goes with its last task.
        connection.execute("DELETE FROM checklist_items WHERE pass_id NOT IN (SELECT pass_id FROM learning_tasks)")
        return {"id": item_id, "title": row["title"], "date": row["item_date"], "domain": row["domain"]}

    def record_shorten_request(self, message_id: str, request_date: str, message: str, day: dict) -> list[dict]:
        """Retain explicit task-specific shortening requests with message provenance."""
        if request_date != date.today().isoformat() or not re.search(
            r"\b(shorten|shorter|reduce|less time)\b", message.lower()
        ):
            return []
        lowered = message.lower()
        candidates = day["dayItems"] or day["entries"]
        matched = {(item["title"], item["domain"]) for item in candidates
                   if item["title"].lower() in lowered}
        with self.connect() as connection:
            for title, domain in matched:
                connection.execute(
                    """INSERT INTO feedback_signals
                       (id, message_id, request_date, task_title, domain, request_kind, created_at)
                       VALUES (?, ?, ?, ?, ?, 'shorten', ?)""",
                    (_id("feedback"), message_id, request_date, title, domain, _now()),
                )
        return [{"taskTitle": title, "domain": domain, "requestKind": "shorten"}
                for title, domain in sorted(matched)]

    def feedback_memory(self, before_date: str) -> list[dict]:
        """Aggregate prior explicit requests, not casual chat, for later planning."""
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT task_title, domain, COUNT(*) AS requests
                   FROM feedback_signals WHERE request_date < ?
                   GROUP BY task_title, domain ORDER BY requests DESC, task_title""",
                (before_date,),
            ).fetchall()
        return [{"taskTitle": row["task_title"], "domain": row["domain"],
                 "shortenRequests": row["requests"]} for row in rows]

    @staticmethod
    def _counted_rows(connection: sqlite3.Connection, start: str, end: str) -> tuple[list, list]:
        """The tasks a period's figures count: a day with a set plan counts that plan's entries, and
        any other day its own tasks. Left out: an entry a past plan keeps for a task removed or moved
        on, and a task whose goal is paused while it is still to do.

        Returns:
            The set plans' entries and the other days' tasks, each with its "record_date" and the
            time its task took ("actual_start", "actual_end", "actual_minutes" and "time_confirmed").
        """
        plan_rows = connection.execute(
            """SELECT s.plan_date AS record_date, e.title, e.detail, e.domain,
                      e.start_time, e.duration_minutes, e.constraint_kind,
                      e.completion_status, source.actual_start, source.actual_end, source.actual_minutes,
                      COALESCE(source.time_confirmed, 0) AS time_confirmed
               FROM plan_entries e
               JOIN plan_variants v ON v.id = e.variant_id
               JOIN plan_sets s ON s.id = v.plan_set_id
               JOIN daily_confirmations c ON c.plan_date = s.plan_date
                                          AND c.variant_id = v.id
               LEFT JOIN daily_items source ON source.id = e.source_item_id
               WHERE s.plan_date BETWEEN ? AND ? AND e.removed_at IS NULL
                 AND NOT (e.completion_status = 'planned' AND EXISTS (
                   SELECT 1 FROM daily_items i JOIN goals g ON g.id = i.goal_id
                   WHERE i.id = e.source_item_id AND g.status = 'paused'))""", (start, end)
        ).fetchall()
        managed_rows = connection.execute(
            """SELECT i.item_date AS record_date, i.title, i.detail, i.domain,
                      i.start_time, i.duration_minutes, i.constraint_kind,
                      i.completion_status, i.actual_start, i.actual_end, i.actual_minutes, i.time_confirmed
               FROM daily_items i
               WHERE i.item_date BETWEEN ? AND ? AND i.acceptance = 'accepted' AND NOT EXISTS (
                 SELECT 1 FROM daily_confirmations c WHERE c.plan_date = i.item_date
               ) AND NOT (i.completion_status = 'planned' AND EXISTS (
                 SELECT 1 FROM goals g WHERE g.id = i.goal_id AND g.status = 'paused'))""", (start, end)
        ).fetchall()
        return plan_rows, managed_rows

    def report_graphs(self, start: str, end: str) -> dict:
        """What a report's graphs show, from the tasks its figures count (see _counted_rows).

        Args:
            start: The first day, as YYYY-MM-DD.
            end: The last day; no day after today is listed.

        Returns:
            The period's "start" and "end" as asked; "days": every day from start to end, each with
            its tasks scheduled and fully done, and by area the minutes those done took: the time
            each took, or its planned length when no time was kept, a time to check (see
            _time_to_check) counting nothing until confirmed. "followThrough": each day with a set
            plan, with its entries done, partly done, moved on to another day, skipped, left without
            a status once the day's DAY_END passed ("noReply"), and not yet reported (today before
            DAY_END); an entry for a removed task is left out.
        """
        period = {"start": start, "end": end}
        today, clock = date.today().isoformat(), _local_time()
        end = min(end, today)
        with self.connect() as connection:
            plan_rows, managed_rows = self._counted_rows(connection, start, end)
            set_days = [row[0] for row in connection.execute(
                "SELECT plan_date FROM daily_confirmations WHERE plan_date BETWEEN ? AND ? ORDER BY plan_date",
                (start, end))]
            moved = dict(connection.execute(
                """SELECT s.plan_date, COUNT(*) FROM plan_entries e
                   JOIN plan_variants v ON v.id = e.variant_id
                   JOIN plan_sets s ON s.id = v.plan_set_id
                   JOIN daily_confirmations c ON c.plan_date = s.plan_date AND c.variant_id = v.id
                   WHERE s.plan_date BETWEEN ? AND ? AND e.moved_to IS NOT NULL GROUP BY s.plan_date""",
                (start, end)).fetchall())
        counts: dict[str, dict] = {}
        for row in (*plan_rows, *managed_rows):
            day = counts.setdefault(row["record_date"], {"scheduled": 0, "done": 0, "minutes": {}})
            day["scheduled"] += 1
            if row["completion_status"] == "done":
                day["done"] += 1
                taken = _counted_time(row["actual_start"], row["actual_end"], row["duration_minutes"], row["time_confirmed"],
                                      row["actual_minutes"])
                spent = row["duration_minutes"] if row["actual_start"] is None else taken or 0
                day["minutes"][row["domain"]] = day["minutes"].get(row["domain"], 0) + spent
        days = []
        current, last = date.fromisoformat(start), date.fromisoformat(end)
        while current <= last:
            days.append({"date": current.isoformat(),
                         **counts.get(current.isoformat(), {"scheduled": 0, "done": 0, "minutes": {}})})
            current += timedelta(days=1)
        follow = {day: {"date": day, "done": 0, "partial": 0, "moved": moved.get(day, 0), "skipped": 0, "noReply": 0,
                        "unreported": 0} for day in set_days}
        for row in plan_rows:
            unanswered = row["record_date"] < today or clock >= DAY_END
            follow[row["record_date"]][row["completion_status"] if row["completion_status"] != "planned"
                                       else "noReply" if unanswered else "unreported"] += 1
        return {**period, "days": days, "followThrough": list(follow.values())}

    def finishing_week(self, day: str) -> list[dict]:
        """The FINISHING_DAYS days to `day`, for Today's finishing graph: each with its tasks
        scheduled and fully done, as report_graphs counts them; no day after today is listed."""
        first = (date.fromisoformat(day) - timedelta(days=FINISHING_DAYS - 1)).isoformat()
        return [{"date": item["date"], "scheduled": item["scheduled"], "done": item["done"]}
                for item in self.report_graphs(first, day)["days"]]

    def summary_facts(self, start: str, end: str, with_goals: bool = True,
                      before: tuple[str, str] | None = None) -> dict:
        """Collect confirmed-plan outcomes or owned records without double counting.

        Left out: an entry a past plan keeps for a removed task, a task whose goal is paused while it
        is still to do, and, from the repeating work done, a task whose goal is paused.

        Args:
            start: The first day, as YYYY-MM-DD.
            end: The last day; no day after today counts.
            with_goals: Include the goal ledger; a part of a wider report leaves it out, as it
                reads only outcomes and advice.
            before: The first and last day of the period before, whose average energy the
                period's is set against; None when there is none to compare with.

        Returns:
            Besides the outcomes, each area's and each task's count of tasks left without a status
            once their day's DAY_END passed ("noReply"), the period's "start" and "end" as asked for, each day with energy
            reported ("energyDays", see energy_days), each day's outcomes by area ("dayOutcomes"),
            and the period before's average energy ("energyBefore", the mean of its days' averages).
        """
        period = {"start": start, "end": end}
        today = date.today().isoformat()
        end = min(end, today)
        with self.connect() as connection:
            plan_rows, managed_rows = self._counted_rows(connection, start, end)
            feedback_rows = connection.execute(
                """SELECT f.task_title, f.domain, COUNT(DISTINCT f.id) AS requests
                   FROM feedback_signals f
                   WHERE f.request_date BETWEEN ? AND ?
                   GROUP BY f.task_title, f.domain ORDER BY requests DESC, f.task_title""",
                (start, end),
            ).fetchall()
            # By series, so a day renamed or moved to another area is still the same habit; it goes by
            # the name and area of its latest day (SQLite takes them from the row MAX picks).
            recurring_success_rows = connection.execute(
                f"""SELECT repeat_series_id AS series, title, domain, MAX(item_date) AS latest,
                          COUNT(DISTINCT item_date) AS done_days
                   FROM daily_items WHERE item_date BETWEEN ? AND ? AND acceptance = 'accepted'
                     AND completion_status = 'done' AND repeat_series_id IS NOT NULL AND {_GOAL_NOT_PAUSED}
                   GROUP BY repeat_series_id HAVING done_days >= 2
                   ORDER BY done_days DESC, title""",
                (start, end),
            ).fetchall()
            recorded_days = connection.execute(
                """SELECT COUNT(*) FROM (
                     SELECT plan_date AS day FROM plan_sets WHERE plan_date BETWEEN ? AND ?
                     UNION SELECT item_date AS day FROM daily_items WHERE item_date BETWEEN ? AND ?
                       AND acceptance = 'accepted'
                     UNION SELECT reading_date AS day FROM energy_log
                       WHERE reading_date BETWEEN ? AND ?
                   )""", (start, end) * 3
            ).fetchone()[0]
            repeat_rows = connection.execute(
                f"""SELECT domain, COUNT(*) AS scheduled,
                          SUM(CASE WHEN completion_status = 'done' THEN 1 ELSE 0 END) AS done
                   FROM daily_items WHERE item_date BETWEEN ? AND ? AND acceptance = 'accepted'
                     AND repeat_series_id IS NOT NULL AND {_GOAL_NOT_PAUSED} GROUP BY domain""",
                (start, end),
            ).fetchall()
            knowledge_count = connection.execute(
                "SELECT COUNT(*) FROM knowledge_sources"
            ).fetchone()[0]
        domains = {domain: {"scheduled": 0, "done": 0, "partial": 0, "skipped": 0, "noReply": 0}
                   for domain in DOMAIN_LABELS}
        clock = _local_time()

        def unanswered(row: sqlite3.Row) -> bool:
            """Whether a task was left without a status once its day's DAY_END passed."""
            return row["completion_status"] == "planned" and (row["record_date"] < today or clock >= DAY_END)

        day_outcomes: dict[str, dict[str, dict[str, int]]] = {}
        for row in (*plan_rows, *managed_rows):
            domain = domains[row["domain"]]
            domain["scheduled"] += 1
            if row["completion_status"] != "planned":
                domain[row["completion_status"]] += 1
            domain["noReply"] += unanswered(row)
            on_day = day_outcomes.setdefault(row["record_date"], {}).setdefault(row["domain"], {"scheduled": 0, "done": 0})
            on_day["scheduled"] += 1
            on_day["done"] += row["completion_status"] == "done"
        energy_days = self.energy_days(start, end)
        earlier = self.energy_days(*before) if before else []
        task_outcomes = {}
        for row in (*plan_rows, *managed_rows):
            identity = (row["title"], row["domain"])
            outcome = task_outcomes.setdefault(identity, {
                "taskTitle": row["title"], "domain": row["domain"],
                "scheduled": 0, "done": 0, "partial": 0, "skipped": 0,
                "planned": 0, "noReply": 0, "startTime": row["start_time"],
                "durationMinutes": row["duration_minutes"],
                "constraintKind": row["constraint_kind"], "detail": row["detail"],
                "lastDate": row["record_date"], "doneStarts": [],
            })
            outcome["scheduled"] += 1
            outcome[row["completion_status"]] += 1
            outcome["noReply"] += unanswered(row)
            if row["completion_status"] == "done" and row["start_time"]:
                outcome["doneStarts"].append(row["start_time"])
            if row["record_date"] >= outcome["lastDate"]:
                outcome.update({
                    "startTime": row["start_time"],
                    "durationMinutes": row["duration_minutes"],
                    "constraintKind": row["constraint_kind"],
                    "detail": row["detail"], "lastDate": row["record_date"],
                })
        return {
            "recordedDays": recorded_days, "domains": domains,
            "goals": self.goals() if with_goals else [], "knowledgeSourceCount": knowledge_count,
            "taskOutcomes": sorted(task_outcomes.values(), key=lambda item: (
                item["domain"], item["taskTitle"]
            )),
            "feedback": [{"taskTitle": row["task_title"], "domain": row["domain"],
                          "shortenRequests": row["requests"]}
                         for row in feedback_rows],
            "completedRecurring": [{"taskTitle": row["title"], "domain": row["domain"],
                                    "doneDays": row["done_days"], "seriesId": row["series"]}
                                   for row in recurring_success_rows],
            "areaEvidence": {
                "repeats": {domain: {"scheduled": 0, "done": 0} for domain in DOMAIN_LABELS}
                           | {row["domain"]: {"scheduled": row["scheduled"], "done": row["done"]} for row in repeat_rows},
                # The latest day with energy reported, by its average.
                "energy": ({"date": energy_days[-1]["date"], "level": energy_days[-1]["average"]}
                           if energy_days else None),
            },
            **period,
            "energyDays": energy_days,
            "dayOutcomes": day_outcomes,
            "energyBefore": (round(sum(day["average"] for day in earlier) / len(earlier), 1) if earlier else None),
        }

    def first_record_date(self) -> str | None:
        """Return the first day anything was recorded, as summary_facts counts a recorded day, or None."""
        with self.connect() as connection:
            return connection.execute(
                """SELECT MIN(day) FROM (
                     SELECT MIN(plan_date) AS day FROM plan_sets
                     UNION ALL SELECT MIN(item_date) FROM daily_items WHERE acceptance = 'accepted'
                     UNION ALL SELECT MIN(reading_date) FROM energy_log)""").fetchone()[0]

    def rebuild_task_profiles(self, areas: Iterable[str] | None = None) -> int:
        """Rebuild area agents' task profiles from all the user's records, in one pass.

        A record is a task on a day with a set plan, as that plan placed it, or else the user's own
        accepted task. It counts once its day has passed or once it is reported, so a task still
        planned today is not history yet. An entry a past plan keeps for a removed task, marked
        "Removed", counts no more. Titles that differ only in case or spaces are one task.

        Args:
            areas: Rebuild only these areas' profiles, as a change reaches only its tasks' area
                agents; None for every area.

        Returns:
            How many task profiles were built.
        """
        wanted = None if areas is None else set(areas)
        today = date.today().isoformat()
        with self.connect() as connection:
            # Read and rewrite as one write transaction, so a rebuild running alongside can't
            # replace newer profiles with ones built from older records.
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """SELECT s.plan_date AS record_date, e.title, e.domain, e.start_time, e.duration_minutes,
                          COALESCE(i.duration_minutes, e.duration_minutes) AS own_minutes,
                          COALESCE(i.duration_source = 'user', 0) AS yours, e.completion_status,
                          i.actual_start, i.actual_end, i.actual_minutes, COALESCE(i.time_confirmed, 0) AS time_confirmed
                   FROM plan_entries e
                   JOIN plan_variants v ON v.id = e.variant_id
                   JOIN plan_sets s ON s.id = v.plan_set_id
                   JOIN daily_confirmations c ON c.plan_date = s.plan_date AND c.variant_id = v.id
                   LEFT JOIN daily_items i ON i.id = e.source_item_id
                   WHERE e.removed_at IS NULL
                   UNION ALL
                   SELECT i.item_date, i.title, i.domain, i.start_time, i.duration_minutes, i.duration_minutes,
                          i.duration_source = 'user', i.completion_status, i.actual_start, i.actual_end,
                          i.actual_minutes, i.time_confirmed
                   FROM daily_items i
                   WHERE i.acceptance = 'accepted' AND NOT EXISTS (
                     SELECT 1 FROM daily_confirmations c WHERE c.plan_date = i.item_date)"""
            ).fetchall()
            requests: dict[tuple[str, str], int] = {}
            for row in connection.execute(
                    """SELECT domain, task_title, COUNT(DISTINCT id) AS requests FROM feedback_signals
                       GROUP BY domain, task_title"""):
                key = (row["domain"], row["task_title"].strip().lower())
                requests[key] = requests.get(key, 0) + row["requests"]
            grouped: dict[tuple[str, str], list[dict]] = {}
            titles: dict[tuple[str, str], str] = {}
            for row in rows:
                if ((row["record_date"] >= today and row["completion_status"] == "planned")
                        or (wanted is not None and row["domain"] not in wanted)):
                    continue
                key = (row["domain"], row["title"].strip().lower())
                grouped.setdefault(key, []).append({
                    "date": row["record_date"], "start": row["start_time"], "minutes": row["duration_minutes"],
                    "ownMinutes": row["own_minutes"], "yours": bool(row["yours"]), "status": row["completion_status"],
                    "taken": _counted_time(row["actual_start"], row["actual_end"], row["duration_minutes"],
                                           row["time_confirmed"], row["actual_minutes"]),
                    "toCheck": _time_to_check(row["actual_start"], row["actual_end"], row["duration_minutes"],
                                              row["time_confirmed"], row["actual_minutes"])})
                titles[key] = row["title"].strip()
            now = _now()
            if wanted is None:
                connection.execute("DELETE FROM task_profiles")
            else:
                connection.executemany("DELETE FROM task_profiles WHERE domain = ?", [(area,) for area in wanted])
            connection.executemany(
                """INSERT INTO task_profiles (domain, task_key, title, profile_json, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                [(domain, task_key, titles[(domain, task_key)],
                  json.dumps(task_profile(records, requests.get((domain, task_key), 0))), now)
                 for (domain, task_key), records in grouped.items()])
        return len(grouped)

    def task_profiles(self, domain: str | None = None) -> dict[tuple[str, str], dict]:
        """Return the area agents' task profiles, by area and lower-case title, with each task's "title".

        Args:
            domain: Only this area's profiles, as an area agent reads only its own.
        """
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT domain, task_key, title, profile_json FROM task_profiles WHERE ? IS NULL OR domain = ?",
                (domain, domain)).fetchall()
        return {(row["domain"], row["task_key"]): {**json.loads(row["profile_json"]), "title": row["title"]}
                for row in rows}

    def post_notices(self, notice_date: str, issues: Iterable[dict]) -> None:
        """Keep what the agents sent through Ava as its messages, each once on a day.

        Args:
            notice_date: The day they were sent on.
            issues: Each with its "issueKey", "agent", "kind" and "values": an issue found in the
                day (see AgentOrchestrator.day_issues), or a doubt or a which-task question about a
                request, keyed by its reply. One already posted that day is left as it is, without
                writing, so opening today doesn't wait on another write.
        """
        now = _now()
        with self.connect() as connection:
            posted = {row["issue_key"] for row in connection.execute(
                "SELECT issue_key FROM ava_notices WHERE notice_date = ?", (notice_date,))}
            fresh = [issue for issue in issues if issue["issueKey"] not in posted]
            if not fresh:
                return
            connection.executemany(
                """INSERT OR IGNORE INTO ava_notices
                   (id, notice_date, issue_key, agent_key, kind, values_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [(_id("notice"), notice_date, issue["issueKey"], issue["agent"], issue["kind"],
                  json.dumps(issue["values"]), now) for issue in fresh])

    def notices(self) -> list[dict]:
        """Return Ava's messages about issues, oldest first, each with when it was read or None; one that
        offers a change carries its card ("proposal", as propose_action gives it, with its status now)."""
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT id, notice_date, agent_key, kind, values_json, created_at, read_at
                   FROM ava_notices ORDER BY created_at, rowid""").fetchall()
            offered = [json.loads(row["values_json"]).get("actionId") for row in rows]
            offered = [action_id for action_id in offered if action_id]
            actions = {row["id"]: {"id": row["id"], "actionType": row["action_type"], "payload": json.loads(row["payload_json"]),
                                   "explanation": row["explanation"], "status": row["status"]}
                       for row in connection.execute(
                           f"""SELECT id, action_type, payload_json, explanation, status FROM proposed_actions
                               WHERE id IN ({','.join('?' * len(offered))})""", offered)} if offered else {}
        notices = []
        for row in rows:
            values = json.loads(row["values_json"])
            notice = {"id": row["id"], "date": row["notice_date"], "agentKey": row["agent_key"], "kind": row["kind"],
                      "values": values, "createdAt": row["created_at"], "readAt": row["read_at"]}
            if values.get("actionId") in actions:
                notice["proposal"] = actions[values["actionId"]]
            notices.append(notice)
        return notices

    def offer_usual_length(self, item_id: str) -> dict | None:
        """Have a done task's area agent offer, through Ava, to change the length the user set for it when
        its done times keep differing from it: at least USUAL_DIFFERS of its last USUAL_LOOKBACK done
        times, times to check left out, differ by USUAL_DIFFERENCE minutes or more. The usual length,
        their median, is offered as a card for the task's days still to come at the length set, saved
        only on Confirm; it is offered once for each usual length.

        Returns:
            The notice posted, or None when there is nothing to offer.
        """
        today = date.today().isoformat()
        with self.connect() as connection:
            task = connection.execute(
                "SELECT title, domain, duration_minutes, duration_source FROM daily_items WHERE id = ?", (item_id,)).fetchone()
            if not task or task["duration_source"] != "user":
                return None
            named, set_minutes = task["title"].strip().lower(), task["duration_minutes"]
            times = [taken for row in connection.execute(
                         """SELECT title, duration_minutes, actual_start, actual_end, actual_minutes, time_confirmed
                            FROM daily_items WHERE domain = ? AND acceptance = 'accepted' AND completion_status = 'done'
                              AND actual_start IS NOT NULL ORDER BY item_date DESC, status_at DESC""", (task["domain"],))
                     if row["title"].strip().lower() == named
                     and (taken := _counted_time(row["actual_start"], row["actual_end"], row["duration_minutes"],
                                                 row["time_confirmed"], row["actual_minutes"])) is not None][:USUAL_LOOKBACK]
            if sum(abs(taken - set_minutes) >= USUAL_DIFFERENCE for taken in times) < USUAL_DIFFERS:
                return None
            usual = _stepped(median(times))
            later = [row for row in connection.execute(
                         """SELECT id, item_date, title FROM daily_items
                            WHERE domain = ? AND item_date >= ? AND acceptance = 'accepted' AND completion_status = 'planned'
                              AND duration_source = 'user' AND duration_minutes = ? AND id != ? ORDER BY item_date""",
                         (task["domain"], today, set_minutes, item_id))
                     if row["title"].strip().lower() == named]
            offered = any(json.loads(row["payload_json"])["title"].strip().lower() == named
                          and json.loads(row["payload_json"])["durationMinutes"] == usual
                          for row in connection.execute(
                              "SELECT payload_json FROM proposed_actions WHERE action_type = 'usual_length'"))
        if abs(usual - set_minutes) < USUAL_DIFFERENCE or not later or offered:
            return None
        proposal = self.propose_action(
            self.thread(), "usual_length",
            {"date": later[0]["item_date"], "itemIds": [row["id"] for row in later], "durationMinutes": usual,
             "title": task["title"], "fromMinutes": set_minutes},
            f"“{task['title']}” usually takes {usual} minutes; you set {set_minutes}. Change it on its days to come?")
        notice = {"issueKey": f"usual-length:{named}:{usual}", "agent": task["domain"], "kind": "usual-length",
                  "values": {"taskTitle": task["title"], "usualMinutes": usual, "setMinutes": set_minutes,
                             "actionId": proposal["id"]}}
        self.post_notices(today, [notice])
        return notice

    def yesterday_notice(self, today: str) -> dict | None:
        """Return what Today's notice lists of yesterday, until the user dismisses it: the tasks still
        without a status, stopped at their limit ("limit"; see time_taken.limit_stopped) or left without
        one ("noReply"), and those with a status whose time is one to check ("checkTime"; see
        _time_to_check), each to fix through Ava. A task with a status and its time counted isn't listed.

        Returns:
            Yesterday's "date" and its "tasks", each its "id", "title" and "reason", timed ones first
            in time order; or None when there is nothing to fix or the notice was dismissed.
        """
        day = (date.fromisoformat(today) - timedelta(days=1)).isoformat()
        with self.connect() as connection:
            dismissed = connection.execute("SELECT value_json FROM preferences WHERE key = ?", (NOTICE_DISMISSED_KEY,)).fetchone()
            if dismissed and json.loads(dismissed["value_json"]) == day:
                return None
            tasks, meals = self._time_tasks(connection, day), self._day_meals(connection, day)
            rows = {row["id"]: row for row in connection.execute(
                "SELECT id, actual_start, actual_end, actual_minutes, time_confirmed FROM daily_items WHERE item_date = ?",
                (day,))}
        listed, limited = [], limit_stopped(tasks, meals, AFTER_DAY)
        for task in sorted(tasks, key=_day_order):
            row = rows[task["id"]]
            reason = (("limit" if task["id"] in limited else "noReply") if task["status"] == "planned"
                      else "checkTime" if _time_to_check(row["actual_start"], row["actual_end"], task["minutes"],
                                                         row["time_confirmed"], row["actual_minutes"])
                      else None)
            if reason and not task["paused"]:
                listed.append({"id": task["id"], "title": task["title"], "reason": reason})
        return {"date": day, "tasks": listed} if listed else None

    def dismiss_yesterday_notice(self, day: str) -> None:
        """Hide Today's notice about `day`, YYYY-MM-DD, as the user asked; a later day's shows."""
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO preferences (key, value_json, updated_at) VALUES (?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at""",
                (NOTICE_DISMISSED_KEY, json.dumps(day), _now()))

    def energy(self, day: str) -> float | None:
        """Return a day's energy: the average of its readings so far, out of 5 to one decimal, or None
        for a day with none. It is the one value plans, Ava, the agents, Summary and Calendar use."""
        with self.connect() as connection:
            average = connection.execute("SELECT AVG(level) FROM energy_log WHERE reading_date = ?", (day,)).fetchone()[0]
        return None if average is None else round(average, 1)

    def energy_readings(self, day: str) -> list[dict]:
        """Return a day's energy readings in the order they were made, each its "level" and local "time" ("HH:MM")."""
        with self.connect() as connection:
            rows = connection.execute("""SELECT level, reading_time FROM energy_log WHERE reading_date = ?
                                         ORDER BY recorded_at, id""", (day,)).fetchall()
        return [{"level": row["level"], "time": row["reading_time"]} for row in rows]

    def energy_days(self, start: str, end: str) -> list[dict]:
        """Return each day from start to end with energy reported, oldest first.

        Returns:
            Each day's "date", its "average" to one decimal, its lowest ("low") and highest ("high")
            reading, and its "readings", as energy_readings gives them.
        """
        with self.connect() as connection:
            rows = connection.execute("""SELECT reading_date, level, reading_time FROM energy_log
                                         WHERE reading_date BETWEEN ? AND ? ORDER BY reading_date, recorded_at, id""",
                                      (start, end)).fetchall()
        days: dict[str, list[dict]] = {}
        for row in rows:
            days.setdefault(row["reading_date"], []).append({"level": row["level"], "time": row["reading_time"]})
        return [{"date": day, "average": round(sum(reading["level"] for reading in readings) / len(readings), 1),
                 "low": min(reading["level"] for reading in readings), "high": max(reading["level"] for reading in readings),
                 "readings": readings} for day, readings in days.items()]

    def add_energy(self, day: str, level: int) -> dict:
        """Add a reading, out of 5, to today's energy log at the local time now; the day's average takes it in.

        Returns:
            The reading's date and level, the day's "average" with it, and all the day's "readings".

        Raises:
            PermissionError: For any day but today, whose readings stay as they were.
        """
        with self.connect() as connection:
            self._log_energy(connection, day, level)
        return {"date": day, "level": level, "average": self.energy(day), "readings": self.energy_readings(day)}

    @staticmethod
    def _log_energy(connection: sqlite3.Connection, day: str, level: int) -> None:
        """Write a reading into the energy log at the local time now, as add_energy and a confirmed
        energy card do.

        Raises:
            PermissionError: For any day but today.
        """
        if day != date.today().isoformat():
            raise PermissionError("Energy is reported for today only")
        connection.execute("INSERT INTO energy_log (reading_date, level, reading_time, recorded_at) VALUES (?, ?, ?, ?)",
                           (day, level, _local_time(), _now()))

    def read_notices(self) -> None:
        """Mark every unread message about an issue read, as opening Ava does."""
        with self.connect() as connection:
            connection.execute("UPDATE ava_notices SET read_at = ? WHERE read_at IS NULL", (_now(),))

    def save_summary(self, kind: str, key: str, report: dict) -> dict:
        """Persist a reproducible Summary-agent report for a day, week, or month."""
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO summary_reports (period_kind, period_key, report_json, updated_at)
                   VALUES (?, ?, ?, ?) ON CONFLICT(period_kind, period_key) DO UPDATE SET
                   report_json = excluded.report_json, updated_at = excluded.updated_at""",
                (kind, key, json.dumps(report), _now()),
            )
        return report

    def saved_summary(self, kind: str, key: str) -> dict | None:
        """Return a frozen historical report rather than rewriting its past context."""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT report_json FROM summary_reports WHERE period_kind = ? AND period_key = ?",
                (kind, key),
            ).fetchone()
        return json.loads(row["report_json"]) if row else None

    def forget_summaries(self, days: Iterable[str]) -> None:
        """Drop the saved reports for the day, week and month each date falls in.

        Summary then makes them again, with their advice, from the records as they are now, the next
        time they are asked for. A report for a period no change touched stays as it was saved.

        Args:
            days: The dates a change touched, as YYYY-MM-DD.
        """
        keys = {key for day in days for key in period_keys(date.fromisoformat(day))}
        if not keys:
            return
        with self.connect() as connection:
            connection.executemany("DELETE FROM summary_reports WHERE period_kind = ? AND period_key = ?", keys)

    def prepare_future_commitments(self, report: dict) -> list[dict]:
        """Prepare Summary-informed future records with durable agent provenance.

        A repeat is a series of linked days, whatever each is called. One finished on two recorded
        days, or asked twice to be shorter, gets its next date prepared from its most recent day up
        to today, shorter in the second case: tomorrow when that day repeats daily, and the next day
        on its weekday when it repeats weekly; a day that doesn't repeat ends the series, and a
        change today's own day couldn't take (see repeat_series) holds from its day on. Each waits,
        pending, until the user accepts it; plans leave it out until then. A dismissed one is kept
        out of sight so the same work is not prepared again for that date. A series whose latest
        day's goal is paused is on hold, so it isn't prepared.
        """
        if report["periodKind"] not in ("week", "month"):
            return []
        now = date.today()
        added = []
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            # A request to shorten names a task; it counts for the series of its latest repeating day.
            shortening: dict[str, dict] = {}
            for signal in report["feedback"]:
                found = signal["shortenRequests"] >= 2 and connection.execute(
                    """SELECT repeat_series_id FROM daily_items WHERE title = ? AND domain = ? AND item_date <= ?
                         AND repeat_series_id IS NOT NULL AND acceptance = 'accepted'
                       ORDER BY item_date DESC, rowid DESC LIMIT 1""",
                    (signal["taskTitle"], signal["domain"], now.isoformat())).fetchone()
                if found:
                    shortening[found["repeat_series_id"]] = signal
            successes = {signal["seriesId"]: signal for signal in report.get("completedRecurring", ())
                         if signal["doneDays"] >= 2 and signal.get("seriesId")}
            for series in sorted(shortening.keys() | successes.keys()):
                row = connection.execute(
                    f"""SELECT id, item_date, goal_id, title, detail, domain, start_time, duration_minutes,
                              constraint_kind, repeat_kind, origin_source_item_id, NOT {_GOAL_NOT_PAUSED} AS paused
                       FROM daily_items WHERE repeat_series_id = ? AND item_date <= ? AND acceptance = 'accepted'
                       ORDER BY item_date DESC, rowid DESC LIMIT 1""",
                    (series, now.isoformat()),
                ).fetchone()
                if not row or row["paused"]:
                    continue
                waiting = connection.execute("SELECT next_kind, next_from FROM repeat_series WHERE id = ?",
                                             (series,)).fetchone()
                pending = waiting and row["item_date"] < waiting["next_from"]
                kind = waiting["next_kind"] if pending else row["repeat_kind"]
                if kind == "none":
                    continue
                source_id = row["origin_source_item_id"] or row["id"]
                # A weekly task keeps its weekday, or a change waiting for its day the weekday it holds from:
                # the next one after today, a week on when that is today's.
                weekday = date.fromisoformat(waiting["next_from"] if pending else row["item_date"]).weekday()
                ahead = (weekday - now.weekday()) % 7 or 7 if kind == "weekly" else 1
                future_date = (now + timedelta(days=ahead)).isoformat()
                # A flexible task's next date leaves its start time for that day's plan to choose.
                start_time = row["start_time"] if row["constraint_kind"] == "fixed" else None
                existing = connection.execute(
                    """SELECT id FROM daily_items WHERE item_date = ? AND (repeat_series_id = ?
                       OR origin_source_item_id = ? OR (title = ? AND domain = ? AND start_time IS ?))""",
                    (future_date, series, source_id, row["title"], row["domain"], start_time),
                ).fetchone()
                if existing:
                    continue
                preference = shortening.get(series)
                completed = successes.get(series)
                evidence = (f"Summary {report['periodKey']}: {preference['shortenRequests']} explicit "
                            f"requests to shorten {row['title']}. "
                            "A shorter future block keeps it in your days without the length you asked to cut.") if preference else (
                            f"Summary {report['periodKey']}: {row['title']} was completed on "
                            f"{completed['doneDays']} recorded days. "
                            "Prepared its next recurring date at the existing size; you can change it.")
                item_id = _id("item")
                connection.execute(
                    """INSERT INTO daily_items
                       (id, item_date, goal_id, title, detail, domain, start_time,
                        duration_minutes, constraint_kind, repeat_kind, repeat_series_id,
                        origin_kind, origin_detail, origin_source_item_id, acceptance, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'agent-origin', ?, ?, 'pending', ?)""",
                    (item_id, future_date, row["goal_id"], row["title"], row["detail"],
                    row["domain"], start_time,
                    max(MIN_TRIMMED_MINUTES, row["duration_minutes"] - 15) if preference else row["duration_minutes"],
                     row["constraint_kind"], kind, series,
                     evidence, source_id, _now()),
                )
                added.append((future_date, item_id))
        return [next(item for item in self.daily_items(future_date) if item["id"] == item_id)
                for future_date, item_id in added]

    def record_plan_route(self, plan_set_id: str, runs: Iterable[dict]) -> list[dict]:
        """Retain the bounded agent route that proposed a plan, separate from approval.

        A plan's route is replaced when its agents review the day again.
        """
        route = list(runs)
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO plan_generation_routes (plan_set_id, route_json, created_at) VALUES (?, ?, ?)
                   ON CONFLICT(plan_set_id) DO UPDATE SET route_json = excluded.route_json,
                                                          created_at = excluded.created_at""",
                (plan_set_id, json.dumps(route), _now()),
            )
        return route

    def plan_routes(self) -> list[tuple[str, str, list[dict]]]:
        """Return every saved plan route with its plan set's id and date, oldest day first."""
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT r.plan_set_id, s.plan_date, r.route_json
                   FROM plan_generation_routes r JOIN plan_sets s ON s.id = r.plan_set_id
                   ORDER BY s.plan_date"""
            ).fetchall()
        return [(row["plan_set_id"], row["plan_date"], json.loads(row["route_json"])) for row in rows]

    def plan_route(self, plan_set_id: str) -> list[dict]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT route_json FROM plan_generation_routes WHERE plan_set_id = ?",
                (plan_set_id,),
            ).fetchone()
        return json.loads(row["route_json"]) if row else []

    def create_recorded_plan(self, plan_date: str, memory: Iterable[dict] | None = None,
                             guidance: Iterable[dict] | None = None, findings: Iterable[dict] = (),
                             choose: Callable[[dict], object] | None = None) -> str:
        """Build alternatives from owned and recurring items, then retain a snapshot.

        `findings` are the area agents' reviews of the day's tasks, which shorten an often
        unfinished task and place one near the time it is usually done. `choose` has the local
        model pick the two plans beside Balanced; see planner.build_recorded_variants.
        """
        _writable_day(plan_date)
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM plan_sets WHERE plan_date = ?", (plan_date,)
            ).fetchone()
            if existing:
                raise PermissionError("A saved plan already exists for this date")
            today_rows = list(connection.execute(
                f"""SELECT id, goal_id, start_time, title, detail, domain, duration_minutes,
                          constraint_kind, repeat_kind, duration_source
                   FROM daily_items WHERE item_date = ? AND acceptance = 'accepted' AND {_GOAL_NOT_PAUSED}
                   ORDER BY start_time IS NULL, start_time, rowid""",
                (plan_date,),
            ))
            recurring = connection.execute(
                """SELECT i.goal_id, i.item_date, i.start_time, i.title, i.detail,
                          i.domain, i.duration_minutes, i.constraint_kind,
                          i.repeat_kind, i.origin_kind, i.origin_detail,
                          i.origin_source_item_id, i.duration_source, i.estimated_by, i.estimate_basis
                   FROM daily_items i LEFT JOIN goals g ON g.id = i.goal_id
                   WHERE i.item_date < ? AND i.repeat_kind != 'none' AND i.acceptance = 'accepted'
                     AND (i.goal_id IS NULL OR g.status = 'active')
                   ORDER BY i.item_date DESC, i.rowid DESC""", (plan_date,)
            ).fetchall()
            seen = {(row["title"].lower(), row["domain"]) for row in today_rows}
            carried = []
            target_weekday = date.fromisoformat(plan_date).weekday()
            for row in recurring:
                key = (row["title"].lower(), row["domain"])
                if key in seen or (row["repeat_kind"] == "weekly" and
                                   date.fromisoformat(row["item_date"]).weekday() != target_weekday):
                    continue
                seen.add(key)
                carried.append(row)
            items = [_plan_item(row) for row in today_rows]
            for row in carried:
                # A carried flexible task leaves its start time for today's plan to choose.
                start_time = row["start_time"] if row["constraint_kind"] == "fixed" else None
                item_id = _id("item")
                # A carried task keeps where its length came from, so an estimate stays one.
                connection.execute(
                    """INSERT INTO daily_items
                       (id, item_date, goal_id, title, detail, domain, start_time,
                        duration_minutes, constraint_kind, repeat_kind,
                        origin_kind, origin_detail, origin_source_item_id, duration_source,
                        estimated_by, estimate_basis, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (item_id, plan_date, row["goal_id"], row["title"], row["detail"],
                     row["domain"], start_time, row["duration_minutes"],
                     row["constraint_kind"], row["repeat_kind"],
                     row["origin_kind"], row["origin_detail"], row["origin_source_item_id"],
                     row["duration_source"], row["estimated_by"], row["estimate_basis"], _now()),
                )
                items.append(PlanItem(start_time, row["title"], row["detail"], row["domain"],
                                      row["duration_minutes"], row["constraint_kind"],
                                      item_id, row["duration_source"] == "estimate"))
            _refuse_paused_day(connection, plan_date, items)
            variants = self._variants_for(connection, plan_date, items, memory, guidance, findings, choose)
            return self._seed_day(connection, plan_date, "orchestrator-records-v1", variants)

    @staticmethod
    def _with_study(connection: sqlite3.Connection, items: list[PlanItem]) -> list[PlanItem]:
        """The day's tasks, each Learning task made from a source with what plans weigh of it: its effort
        and profile, its source's briefing, the checklist items still unticked it covers, and, in a goal, its
        place among the goal's tasks by day and by when each was made (see planner.StudyTask)."""
        ids = [item.item_id for item in items if item.item_id]
        if not ids:
            return items
        goal_tasks = "FROM daily_items oi WHERE oi.goal_id = i.goal_id AND oi.acceptance = 'accepted'"
        rows = connection.execute(
            f"""SELECT i.id, i.goal_id, l.pass_id, l.profile_json, g.title AS goal_title, s.briefing,
                       (SELECT COUNT(*) {goal_tasks} AND (oi.item_date < i.item_date
                          OR (oi.item_date = i.item_date AND oi.rowid < i.rowid))) AS position,
                       (SELECT COUNT(*) {goal_tasks}) AS task_count
                FROM learning_tasks l JOIN daily_items i ON i.id = l.item_id
                LEFT JOIN goals g ON g.id = i.goal_id LEFT JOIN knowledge_sources s ON s.id = l.source_id
                WHERE l.source_id IS NOT NULL AND i.id IN ({','.join('?' for _ in ids)})""", ids).fetchall()
        studies = {}
        for row in rows:
            profile = json.loads(row["profile_json"])
            left = connection.execute(
                """SELECT title FROM checklist_items WHERE pass_id = ? AND removed = 0 AND ticked_at IS NULL
                   ORDER BY position""", (row["pass_id"],)).fetchall()
            studies[row["id"]] = StudyTask(
                effort=profile.get("effort", "steady"), goal=row["goal_id"], position=row["position"], count=row["task_count"],
                goal_title=row["goal_title"], hands_on=bool(profile.get("handsOn")), briefing=row["briefing"],
                sections=tuple(entry["title"] for entry in left))
        return [replace(item, study=studies[item.item_id]) if item.item_id in studies else item for item in items]

    def _variants_for(self, connection: sqlite3.Connection, plan_date: str, items: list[PlanItem],
                      memory: Iterable[dict] | None, guidance: Iterable[dict] | None, findings: Iterable[dict],
                      choose: Callable[[dict], object] | None) -> tuple[dict, ...]:
        """Build the day's plans from its tasks, each Learning task with what it studies, with the kinds of plan
        the user set lately first."""
        items = self._with_study(connection, items)
        since = (date.fromisoformat(plan_date) - timedelta(days=PREFERENCE_DAYS)).isoformat()
        preferences = dict(connection.execute(
            """SELECT v.slug, COUNT(*) FROM daily_confirmations c JOIN plan_variants v ON v.id = c.variant_id
               WHERE c.plan_date >= ? AND c.plan_date < ? GROUP BY v.slug""",
            (since, plan_date),
        ).fetchall())
        return build_recorded_variants(
            items, self.feedback_memory(plan_date) if memory is None else memory,
            self.active_suggestion_pool() if guidance is None else guidance,
            _local_time(), findings, preferences, choose, self._day_meals(connection, plan_date),
        )

    def repropose_plans(self, plan_date: str, memory: Iterable[dict] | None = None,
                        guidance: Iterable[dict] | None = None, findings: Iterable[dict] = (),
                        choose: Callable[[dict], object] | None = None) -> str:
        """Propose again today's plans that aren't set, from its tasks as they are now.

        A set plan stays exactly as set, and the new plans take the other places, so the day still
        has three. Plans proposed earlier for the day and not set are removed.

        Returns:
            The id of the day's plans.

        Raises:
            PermissionError: When the day isn't today.
            ValueError: When no plans have been proposed for the day yet, or the tasks can't be planned.
        """
        _writable_day(plan_date)
        with self.connect() as connection:
            plan_set = connection.execute("SELECT id FROM plan_sets WHERE plan_date = ?", (plan_date,)).fetchone()
            if not plan_set:
                raise ValueError("No plans have been proposed for this day yet")
            kept = connection.execute(
                """SELECT v.id, v.slug FROM daily_confirmations c JOIN plan_variants v ON v.id = c.variant_id
                   WHERE c.plan_date = ?""", (plan_date,)).fetchone()
            rows = connection.execute(
                f"""SELECT id, start_time, title, detail, domain, duration_minutes, constraint_kind,
                          duration_source FROM daily_items WHERE item_date = ? AND acceptance = 'accepted'
                   AND {_GOAL_NOT_PAUSED} ORDER BY start_time IS NULL, start_time, rowid""", (plan_date,)).fetchall()
            _refuse_paused_day(connection, plan_date, rows)
            variants = self._variants_for(connection, plan_date, [_plan_item(row) for row in rows],
                                          memory, guidance, findings, choose)
            connection.execute("UPDATE plan_variants SET supersedes_variant_id = NULL WHERE plan_set_id = ?",
                               (plan_set["id"],))
            connection.execute("DELETE FROM plan_variants WHERE plan_set_id = ? AND id != ?",
                               (plan_set["id"], kept["id"] if kept else ""))
            fresh = [variant for variant in variants if not kept or variant["slug"] != kept["slug"]]
            self._insert_variants(connection, plan_set["id"], plan_date, fresh[:PLAN_COUNT - 1] if kept else fresh)
            return str(plan_set["id"])

    def earlier_proposals(self, plan_date: str) -> bool:
        """Return whether the day's plans were all proposed by a DayWright that kept no plan sentences.

        Those plans could shorten a length the user set; see repropose_plans.
        """
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT v.notes_json FROM plan_variants v JOIN plan_sets s ON s.id = v.plan_set_id
                   WHERE s.plan_date = ? AND s.source = 'orchestrator-records-v1'""", (plan_date,)).fetchall()
        return bool(rows) and all(row["notes_json"] == "[]" for row in rows)

    def _seed_day(
        self, connection: sqlite3.Connection, plan_date: str,
        source: str = "deterministic-v1", variants: Iterable[dict] | None = None,
    ) -> str:
        existing = connection.execute(
            "SELECT id FROM plan_sets WHERE plan_date = ?", (plan_date,)
        ).fetchone()
        if existing:
            return str(existing["id"])

        plan_set_id = _id("set")
        connection.execute(
            "INSERT INTO plan_sets (id, plan_date, source, created_at) VALUES (?, ?, ?, ?)",
            (plan_set_id, plan_date, source, _now()),
        )
        self._insert_variants(connection, plan_set_id, plan_date,
                              variants if variants is not None else build_variants(), source != "deterministic-v1")
        if source == "deterministic-v1":
            connection.execute(
                """INSERT INTO suggestions (id, plan_date, title, detail)
                   VALUES (?, ?, ?, ?)""",
                (_id("suggestion"), plan_date, "Try a 10-minute walk after lunch.",
                 "A short walk can restore energy and focus for the afternoon."),
            )
        return plan_set_id

    def _insert_variants(self, connection: sqlite3.Connection, plan_set_id: str, plan_date: str,
                         variants: Iterable[dict], recorded: bool = True) -> None:
        """Store plans, each with its sentences, meals and entries, in the day's set of plans.

        An entry of plans made from the user's records names the task it places; the demo
        workspace's sample plans name none.
        """
        source_refs = {}
        if recorded:
            source_refs = {(row["title"], row["domain"], row["start_time"]): row["id"]
                           for row in connection.execute(
                               "SELECT id, title, domain, start_time FROM daily_items "
                               "WHERE item_date = ? AND acceptance = 'accepted'",
                               (plan_date,),
                           )}
        for variant in variants:
            variant_id = _id("variant")
            connection.execute(
                """INSERT INTO plan_variants
                   (id, plan_set_id, name, slug, rationale, notes_json, meals_json, version, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                (
                    variant_id,
                    plan_set_id,
                    variant["name"],
                    variant["slug"],
                    variant["rationale"],
                    json.dumps(variant.get("notes", []), ensure_ascii=False),
                    json.dumps([{"title": meal.title, "start_time": meal.start, "duration_minutes": meal.duration_minutes}
                                for meal in variant.get("meals", ())], ensure_ascii=False),
                    _now(),
                ),
            )
            for position, item in enumerate(variant["items"]):
                connection.execute(
                    """INSERT INTO plan_entries
                       (id, variant_id, position, start_time, title, detail, source_item_id,
                        domain, duration_minutes, constraint_kind)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        _id("entry"),
                        variant_id,
                        position,
                        item.start,
                        item.title,
                        item.detail,
                        item.item_id or source_refs.get((item.title, item.domain, item.start)),
                        item.domain,
                        item.duration_minutes,
                        item.constraint,
                    ),
                )

    def bootstrap_day(
        self,
        plan_date: str,
        selected_variant_id: str | None = None,
        create_if_missing: bool = False,
    ) -> dict:
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT id, source FROM plan_sets WHERE plan_date = ?", (plan_date,)
            ).fetchone()
            # The legacy flag remains accepted by the API, but a new account must
            # never acquire an example plan just by opening a day.
            if not existing:
                return {
                    "date": plan_date,
                    "planSetId": None,
                    "planSource": None,
                    "selectedVariantId": None,
                    "confirmedVariantId": None,
                    "confirmedAt": None,
                    "variants": [],
                    "entries": [],
                    "balance": {domain: 0 for domain in DOMAIN_LABELS},
                    "suggestion": None,
                    "hardConstraints": [],
                    "plannerNotes": [],
                    "planRoute": [],
                    "dayItems": self.daily_items(plan_date),
                    "goals": self.goals(),
                    "meals": self._meal_payload(plan_date),
                    "energy": self.energy(plan_date),
                    "energyReadings": self.energy_readings(plan_date),
                    "finishingWeek": self.finishing_week(plan_date),
                }
            plan_set_id = str(existing["id"])
            source = str(existing["source"])
            variants = connection.execute(
                """SELECT id, name, slug, rationale, notes_json, meals_json, version
                   FROM plan_variants WHERE plan_set_id = ? ORDER BY rowid""",
                (plan_set_id,),
            ).fetchall()
            confirmed = connection.execute(
                "SELECT variant_id, confirmed_at FROM daily_confirmations WHERE plan_date = ?",
                (plan_date,),
            ).fetchone()
            valid_ids = {str(row["id"]) for row in variants}
            selected = (
                selected_variant_id
                if selected_variant_id in valid_ids
                else str(confirmed["variant_id"])
                if confirmed
                else str(variants[0]["id"])
            )
            entries = connection.execute(
                """SELECT id, start_time, title, detail, source_item_id, domain, duration_minutes,
                          constraint_kind, completion_status, removed_at IS NOT NULL AS removed, moved_to
                   FROM plan_entries WHERE variant_id = ? ORDER BY position""",
                (selected,),
            ).fetchall()
            suggestion = connection.execute(
                """SELECT id, title, detail, decision
                   FROM suggestions WHERE plan_date = ? ORDER BY rowid LIMIT 1""",
                (plan_date,),
            ).fetchone()

        entry_payload = [{**dict(row), "removed": bool(row["removed"])} for row in entries]
        owned_items = self.daily_items(plan_date)
        memory = self.feedback_memory(plan_date) if source != "deterministic-v1" else []
        # Time by area leaves out a past plan's entries for tasks removed or moved away, still listed.
        totals = {domain: 0 for domain in DOMAIN_LABELS}
        for entry in entry_payload:
            if not entry["removed"]:
                totals[entry["domain"]] += int(entry["duration_minutes"])
        return {
            "date": plan_date,
            "planSetId": plan_set_id,
            "planRoute": self.plan_route(plan_set_id),
            "planSource": source,
            "selectedVariantId": selected,
            "confirmedVariantId": str(confirmed["variant_id"]) if confirmed else None,
            "confirmedAt": str(confirmed["confirmed_at"]) if confirmed else None,
            "meals": self._meal_payload(plan_date),
            "energy": self.energy(plan_date),
            "energyReadings": self.energy_readings(plan_date),
            "finishingWeek": self.finishing_week(plan_date),
            "variants": [{"id": row["id"], "name": row["name"], "slug": row["slug"], "rationale": row["rationale"],
                          "notes": json.loads(row["notes_json"]), "meals": json.loads(row["meals_json"]),
                          "version": row["version"]} for row in variants],
            "entries": entry_payload,
            "balance": totals,
            "suggestion": dict(suggestion) if suggestion else None,
            "hardConstraints": [
                "Call with Alex at 17:30 (fixed)", "Gym closes at 12:00",
                "Keep at least 30 minutes for evening reset", "Personal spending review today",
            ] if source == "deterministic-v1" else [
                f"{entry['title']} at {entry['start_time']} (fixed)"
                for entry in entry_payload if entry["constraint_kind"] == "fixed"
            ],
            "plannerNotes": [
                "Energy is 3/5, so deep work ends by 16:00.",
                "7h 20m sleep supports a moderate training block.",
            ] if source == "deterministic-v1" else [
                "This plan is a snapshot of your dated records; later edits do not silently rewrite it.",
                *[
                    f"Repeated shortening requests for {signal['taskTitle']} informed a shorter block."
                    for signal in memory
                    if signal["shortenRequests"] >= 2 and
                    any(entry["title"] == signal["taskTitle"] for entry in entry_payload)
                ],
            ],
            "dayItems": owned_items,
            "goals": self.goals(),
        }

    def calendar_month(self, month: str) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT s.plan_date, s.source, c.variant_id AS confirmed_variant_id,
                          v.name AS display_variant_name,
                          COUNT(e.id) AS entry_count,
                          SUM(CASE WHEN e.completion_status = 'done' THEN 1 ELSE 0 END) AS done_count
                   FROM plan_sets s
                   LEFT JOIN daily_confirmations c ON c.plan_date = s.plan_date
                   JOIN plan_variants v ON v.id = COALESCE(
                     c.variant_id,
                     (SELECT first.id FROM plan_variants first
                      WHERE first.plan_set_id = s.id ORDER BY first.rowid LIMIT 1)
                   )
                   LEFT JOIN plan_entries e ON e.variant_id = v.id AND e.removed_at IS NULL
                   WHERE substr(s.plan_date, 1, 7) = ?
                   GROUP BY s.plan_date, s.source, c.variant_id, v.name
                   ORDER BY s.plan_date""",
                (month,),
            ).fetchall()
            managed = connection.execute(
                """SELECT item_date,
                          SUM(CASE WHEN acceptance = 'accepted' THEN 1 ELSE 0 END) AS item_count,
                          SUM(CASE WHEN acceptance = 'accepted' AND completion_status = 'done'
                                   THEN 1 ELSE 0 END) AS done_count,
                          SUM(CASE WHEN acceptance = 'pending' THEN 1 ELSE 0 END) AS suggested_count
                   FROM daily_items WHERE substr(item_date, 1, 7) = ? AND acceptance != 'dismissed'
                   GROUP BY item_date ORDER BY item_date""", (month,)
            ).fetchall()
        records = {row["plan_date"]: {
            "date": row["plan_date"], "confirmed": row["confirmed_variant_id"] is not None,
            "variantName": row["display_variant_name"], "planSource": row["source"],
            "entryCount": row["entry_count"], "doneCount": row["done_count"],
            "managedCount": 0, "managedDoneCount": 0, "suggestedCount": 0,
        } for row in rows}
        for row in managed:
            record = records.setdefault(row["item_date"], {
                "date": row["item_date"], "confirmed": False, "variantName": None,
                "planSource": None, "entryCount": row["item_count"],
                "doneCount": row["done_count"], "managedCount": 0, "managedDoneCount": 0,
                "suggestedCount": 0,
            })
            record["managedCount"] = row["item_count"]
            record["managedDoneCount"] = row["done_count"]
            record["suggestedCount"] = row["suggested_count"]
        # Each day's energy average, on a day with nothing else recorded too.
        averages = {day["date"]: day["average"] for day in self.energy_days(f"{month}-01", f"{month}-31")}
        for day, average in averages.items():
            records.setdefault(day, {"date": day, "confirmed": False, "variantName": None, "planSource": None,
                                     "entryCount": 0, "doneCount": 0, "managedCount": 0, "managedDoneCount": 0,
                                     "suggestedCount": 0})
        for record in records.values():
            record["energy"] = averages.get(record["date"])
        return [records[key] for key in sorted(records)]

    def confirm_plan(self, plan_date: str, variant_id: str, replace_existing: bool = False) -> dict:
        _writable_day(plan_date)
        with self.connect() as connection:
            found = connection.execute(
                """SELECT v.id FROM plan_variants v
                   JOIN plan_sets s ON s.id = v.plan_set_id
                   WHERE v.id = ? AND s.plan_date = ?""",
                (variant_id, plan_date),
            ).fetchone()
            if not found:
                raise ValueError("Plan variant does not belong to this date")
            current = connection.execute(
                "SELECT variant_id, confirmed_at FROM daily_confirmations WHERE plan_date = ?",
                (plan_date,),
            ).fetchone()
            if current and current["variant_id"] == variant_id:
                return {"variantId": variant_id, "confirmedAt": current["confirmed_at"]}
            if current and not replace_existing:
                raise PermissionError("This date already has a confirmed plan. Review and approve a replacement.")
            confirmed_at = _now()
            self._confirm_with_connection(connection, plan_date, variant_id, confirmed_at)
        return {"variantId": variant_id, "confirmedAt": confirmed_at}

    def unset_plan(self, plan_date: str) -> dict:
        """Stop following today's set plan. Its proposals stay, to compare and set one again.

        The day's tasks keep what was reported for them, because reporting a plan entry also
        reports its task, and setting a plan again carries those reports back into it.
        """
        _writable_day(plan_date)
        with self.connect() as connection:
            removed = connection.execute(
                "DELETE FROM daily_confirmations WHERE plan_date = ?", (plan_date,)
            )
            if removed.rowcount != 1:
                raise ValueError("This date has no set plan")
        return {"date": plan_date, "confirmedVariantId": None}

    def update_entry(self, entry_id: str, status: str) -> dict:
        """Report a set plan's entry, and the task it schedules with it, recording the time the task took
        (see _record_time).

        Returns:
            The entry's id and status, the date of its plan and its area, and the task it schedules
            ("itemId"), or None.
        """
        with self.connect() as connection:
            entry = connection.execute(
                """SELECT e.id, e.variant_id, e.source_item_id, e.domain, s.plan_date,
                          c.variant_id AS confirmed_variant_id
                   FROM plan_entries e
                   JOIN plan_variants v ON v.id = e.variant_id
                   JOIN plan_sets s ON s.id = v.plan_set_id
                   LEFT JOIN daily_confirmations c ON c.plan_date = s.plan_date
                   WHERE e.id = ?""",
                (entry_id,),
            ).fetchone()
            if not entry:
                raise ValueError("Plan entry was not found")
            _writable_day(entry["plan_date"])
            if entry["variant_id"] != entry["confirmed_variant_id"]:
                raise PermissionError("Confirm this date's plan before reporting its entries.")
            if entry["source_item_id"] and connection.execute(
                    f"SELECT 1 FROM daily_items WHERE id = ? AND NOT {_GOAL_NOT_PAUSED}", (entry["source_item_id"],)).fetchone():
                raise PermissionError(_PAUSED_MESSAGE)
            cursor = connection.execute(
                "UPDATE plan_entries SET completion_status = ? WHERE id = ?",
                (status, entry_id),
            )
            if entry["source_item_id"]:
                prior = connection.execute("SELECT completion_status FROM daily_items WHERE id = ?",
                                           (entry["source_item_id"],)).fetchone()
                connection.execute(
                    "UPDATE plan_entries SET completion_status = ? WHERE source_item_id = ?",
                    (status, entry["source_item_id"]),
                )
                connection.execute(
                    "UPDATE daily_items SET completion_status = ? WHERE id = ?",
                    (status, entry["source_item_id"]),
                )
                if prior:
                    self._record_time(connection, entry["source_item_id"], status, prior["completion_status"],
                                      entry["plan_date"])
            if cursor.rowcount != 1:
                raise ValueError("Plan entry was not found")
            row = connection.execute(
                "SELECT id, completion_status FROM plan_entries WHERE id = ?", (entry_id,)
            ).fetchone()
        return {**dict(row), "date": entry["plan_date"], "domain": entry["domain"], "itemId": entry["source_item_id"]}

    def decide_suggestion(self, suggestion_id: str, decision: str) -> dict:
        with self.connect() as connection:
            cursor = connection.execute(
                """UPDATE suggestions SET decision = ?, decided_at = ? WHERE id = ?""",
                (decision, _now(), suggestion_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Suggestion was not found")
        return {"id": suggestion_id, "decision": decision}

    def sync_suggestion_pool(self, report: dict) -> None:
        """Retain Summary advice, and notify instead of reactivating discarded repeats."""
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            prepared = []
            for item in report["suggestions"]:
                domain = item["domain"]
                content = item["content"].strip()
                source_key = _advice_key(domain, content)
                prepared.append((item, domain, content, source_key))
            kind, period = report["periodKind"], report["periodKey"]
            current_keys = {source_key for _, _, _, source_key in prepared}
            stale_rows = connection.execute(
                """SELECT id, source_key FROM suggestion_pool
                   WHERE period_kind = ? AND period_key = ? AND status = 'active'""",
                (kind, period),
            ).fetchall()
            for row in stale_rows:
                if row["source_key"] not in current_keys:
                    connection.execute("DELETE FROM suggestion_pool WHERE id = ?", (row["id"],))
            for item, domain, content, source_key in prepared:
                kind, period = report["periodKind"], report["periodKey"]
                cleared = connection.execute(
                    """SELECT 1 FROM cleared_suggestion_periods
                       WHERE period_kind = ? AND period_key = ? AND domain = ?""",
                    (kind, period, domain),
                ).fetchone()
                if cleared:
                    continue
                present = connection.execute(
                    """SELECT 1 FROM suggestion_pool
                       WHERE period_kind = ? AND period_key = ? AND source_key = ?""",
                    (kind, period, source_key),
                ).fetchone()
                notice = connection.execute(
                    """SELECT 1 FROM suggestion_notices
                       WHERE period_kind = ? AND period_key = ? AND source_key = ?""",
                    (kind, period, source_key),
                ).fetchone()
                if present or notice:
                    continue
                discarded_before = connection.execute(
                    "SELECT 1 FROM suggestion_pool WHERE source_key = ? AND status = 'discarded' LIMIT 1",
                    (source_key,),
                ).fetchone()
                if discarded_before:
                    connection.execute(
                        """INSERT INTO suggestion_notices
                           (period_kind, period_key, domain, source_key, content, created_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (kind, period, domain, source_key, content, _now()),
                    )
                else:
                    connection.execute(
                        """INSERT INTO suggestion_pool
                           (id, period_kind, period_key, domain, content, priority,
                            source_key, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (_id("pool"), kind, period, domain, content,
                         item.get("priority", "soft"), source_key, _now()),
                    )

    def suggestion_pool(self, kind: str, period: str, domain: str | None = None) -> dict:
        suffix = " AND domain = ?" if domain else ""
        parameters = (kind, period, domain) if domain else (kind, period)
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT id, domain, content, priority, status, discarded_at, created_at
                   FROM suggestion_pool WHERE period_kind = ? AND period_key = ?"""
                + suffix + " ORDER BY CASE priority WHEN 'strong' THEN 0 ELSE 1 END, created_at",
                parameters,
            ).fetchall()
            notices = connection.execute(
                """SELECT domain, content, created_at FROM suggestion_notices
                   WHERE period_kind = ? AND period_key = ?""" + suffix + " ORDER BY created_at",
                parameters,
            ).fetchall()
        return {"periodKind": kind, "periodKey": period,
                "items": [dict(row) for row in rows],
                "notices": [dict(row) for row in notices]}

    def active_suggestion_pool(self) -> list[dict]:
        """Only active guidance can reach agents, independently of its age."""
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT domain, content, priority, period_kind, period_key
                   FROM suggestion_pool WHERE status = 'active'
                   ORDER BY CASE priority WHEN 'strong' THEN 0 ELSE 1 END,
                            created_at DESC LIMIT 30"""
            ).fetchall()
        return [dict(row) for row in rows]

    def discard_pool_suggestion(self, suggestion_id: str) -> dict:
        with self.connect() as connection:
            source = connection.execute(
                "SELECT source_key FROM suggestion_pool WHERE id = ? AND status = 'active'",
                (suggestion_id,),
            ).fetchone()
            if not source:
                raise ValueError("This active suggestion does not exist")
            changed = connection.execute(
                """UPDATE suggestion_pool SET status = 'discarded', discarded_at = ?
                   WHERE source_key = ? AND status = 'active'""", (_now(), source["source_key"])
            ).rowcount
        return {"id": suggestion_id, "status": "discarded", "affectedPeriods": changed}

    def clear_suggestion_week(self, week: str, domain: str) -> dict:
        """Irreversibly clear the exact weekly area selected and confirmed by the user."""
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """INSERT INTO cleared_suggestion_periods
                   (period_kind, period_key, domain, cleared_at) VALUES ('week', ?, ?, ?)
                   ON CONFLICT(period_kind, period_key, domain)
                   DO UPDATE SET cleared_at = excluded.cleared_at""",
                (week, domain, _now()),
            )
            removed = connection.execute(
                """DELETE FROM suggestion_pool WHERE period_kind = 'week'
                   AND period_key = ? AND domain = ?""", (week, domain)
            ).rowcount
            notices = connection.execute(
                """DELETE FROM suggestion_notices WHERE period_kind = 'week'
                   AND period_key = ? AND domain = ?""", (week, domain)
            ).rowcount
        return {"week": week, "domain": domain, "deletedAdvice": removed,
                "deletedNotices": notices}

    def thread(self) -> str:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id FROM conversation_threads ORDER BY updated_at DESC LIMIT 1"
            ).fetchone()
            if row:
                return str(row["id"])
            thread_id = _id("thread")
            now = _now()
            connection.execute(
                """INSERT INTO conversation_threads (id, title, created_at, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (thread_id, "Today’s plan", now, now),
            )
            return thread_id

    def messages(self, thread_id: str) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT id, role, mode, content, model_mode, created_at, topic_date AS topicDate
                   FROM conversation_messages WHERE thread_id = ? ORDER BY created_at""",
                (thread_id,),
            ).fetchall()
            message_ids = [str(row["id"]) for row in rows]
            route_rows = []
            retrieval_rows = []
            if message_ids:
                placeholders = ",".join("?" for _ in message_ids)
                route_rows = connection.execute(
                    f"""SELECT message_id, agent_key, phase, summary, reads_json, writes_json
                        FROM agent_runs WHERE message_id IN ({placeholders})
                        ORDER BY message_id, sequence""",
                    message_ids,
                ).fetchall()
                retrieval_rows = connection.execute(
                    f"""SELECT r.message_id, r.rank, r.distance, r.chunk_id,
                               r.content, r.chunk_index, r.source_id,
                               r.source_title, r.source_type, r.source_url, r.source_license
                        FROM retrieval_matches r
                        WHERE r.message_id IN ({placeholders})
                        ORDER BY r.message_id, r.rank""",
                    message_ids,
                ).fetchall()
        routes: dict[str, list[dict]] = {message_id: [] for message_id in message_ids}
        for row in route_rows:
            routes[str(row["message_id"])].append(
                {
                    "agentKey": row["agent_key"],
                    "label": str(row["agent_key"]).title(),
                    "phase": row["phase"],
                    "summary": row["summary"],
                    "reads": json.loads(row["reads_json"]),
                    "writes": json.loads(row["writes_json"]),
                }
            )
        retrievals: dict[str, list[dict]] = {message_id: [] for message_id in message_ids}
        for row in retrieval_rows:
            retrievals[str(row["message_id"])].append(
                {
                    "rank": row["rank"],
                    "chunkId": row["chunk_id"],
                    "content": row["content"],
                    "chunkIndex": row["chunk_index"],
                    "sourceId": row["source_id"],
                    "sourceTitle": row["source_title"],
                    "sourceType": row["source_type"],
                    "sourceUrl": row["source_url"],
                    "sourceLicense": row["source_license"],
                    "distance": row["distance"],
                }
            )
        payload = []
        for row in rows:
            message = dict(row)
            if routes.get(str(row["id"])):
                message["agentRoute"] = routes[str(row["id"])]
            if retrievals.get(str(row["id"])):
                message["retrieval"] = {
                    "status": "ready",
                    "matches": retrievals[str(row["id"])],
                }
            payload.append(message)
        return payload

    def add_message(
        self, thread_id: str, role: str, mode: str, content: str, model_mode: str | None = None,
        topic_date: str | None = None,
    ) -> dict:
        """Keep one turn of Ava's conversation.

        Args:
            thread_id: The conversation.
            role: "user" or "assistant".
            mode: Whether the turn asks, changes or reports.
            content: Its words.
            model_mode: How the reply was made, for Ava's own turns.
            topic_date: The day the turn is about, as YYYY-MM-DD, so Ava can show where the day changed.
        """
        message_id = _id("message")
        created_at = _now()
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO conversation_messages
                   (id, thread_id, role, mode, content, model_mode, created_at, topic_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (message_id, thread_id, role, mode, content, model_mode, created_at, topic_date),
            )
            connection.execute(
                "UPDATE conversation_threads SET updated_at = ? WHERE id = ?",
                (created_at, thread_id),
            )
        return {
            "id": message_id,
            "role": role,
            "mode": mode,
            "content": content,
            "model_mode": model_mode,
            "created_at": created_at,
            "topicDate": topic_date,
        }

    def record_agent_runs(
        self, message_id: str, runs: Iterable[AgentRun]
    ) -> list[dict]:
        public_runs = [run.public() for run in runs]
        with self.connect() as connection:
            for sequence, run in enumerate(public_runs):
                connection.execute(
                    """INSERT INTO agent_runs
                       (id, message_id, sequence, agent_key, phase, summary, reads_json,
                        writes_json, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        _id("run"),
                        message_id,
                        sequence,
                        run["agentKey"],
                        run["phase"],
                        run["summary"],
                        json.dumps(run["reads"]),
                        json.dumps(run["writes"]),
                        _now(),
                    ),
                )
        return public_runs

    def record_retrieval(self, message_id: str, matches: list[dict]) -> None:
        with self.connect() as connection:
            for match in matches:
                connection.execute(
                    """INSERT INTO retrieval_matches
                       (id, message_id, chunk_id, source_id, source_title, source_type,
                        source_url, source_license, chunk_index, content, rank, distance, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        _id("retrieval"),
                        message_id,
                        match["chunkId"],
                        match["sourceId"],
                        match["sourceTitle"],
                        match["sourceType"],
                        match.get("sourceUrl", ""),
                        match.get("sourceLicense", ""),
                        match["chunkIndex"],
                        match["content"],
                        match["rank"],
                        match["distance"],
                        _now(),
                    ),
                )

    def propose_action(self, thread_id: str, action_type: str, payload: dict, explanation: str) -> dict:
        action_id = _id("action")
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO proposed_actions
                   (id, thread_id, action_type, payload_json, explanation, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (action_id, thread_id, action_type, json.dumps(payload), explanation, _now()),
            )
        return {
            "id": action_id,
            "actionType": action_type,
            "payload": payload,
            "explanation": explanation,
            "status": "pending",
        }

    def decide_action(self, action_id: str, decision: str, domain: str | None = None,
                      statuses: dict[str, str] | None = None, ticked: list[str] | None = None) -> dict:
        """Confirm or dismiss a change the agents proposed; only a confirmation applies it.

        Confirming an edit to a task ("edit_item") applies the fields it changes to the task as it
        is now, through the checks its form has; confirming a removal ("remove_item") removes the
        task as delete_daily_item does. Confirming a new task ("add_item") or a new goal with its
        first tasks ("add_goal") creates them through the same checks, in the area chosen on the
        card unless the task joins a goal, whose area it takes; a length left to the area agent is
        at least MIN_TASK_MINUTES. Confirming an energy card ("set_energy") adds its reading to the
        day's log, which only today's can take. Confirming a usual length ("usual_length"; see
        offer_usual_length) makes it the user's on the task's days still to come and still to do.
        Confirming a catch-up ("catch_up") sets the status chosen for each task on the card, on today
        or an earlier day, as Today's catch-up sheet does (see _apply_statuses); a task changed or
        moved since the card was made is left as it is. Confirming a link card ("link_sources") links or
        unlinks a Learn task's Library sources (see link_sources). A change that can no longer apply is refused,
        and the proposal stays pending.

        Args:
            domain: The area the user chose on a new task's or goal's card, if they changed it.
            statuses: The statuses chosen on a catch-up card, by task id, when the user changed the
                ones it proposed; a task left out stays as it is.
            ticked: The files left ticked on a folder check card, by their paths in the folder, when the user
                changed the ones it proposed; confirming it names the rest, as "folderCheck", for the service
                to take out of the Library, as only it reaches the folder (see folder_check).

        Returns:
            The decision, whether it was applied, and the date it concerns; for an applied change to
            a task, the task "before" it too, and for an applied edit the task "after" it; for new
            tasks, each one "created" (its id, date, area and length source), and a new "goalId"; for
            an energy reading, the day's "energy" ("average" and "readings"); for a catch-up, each
            task changed in "caughtUp" (its "id", "status" and "domain").
        """
        caught = None
        folder_check = None
        before = None
        meal_update = None
        created: list[dict] = []
        new_goal = None
        with self.connect() as connection:
            row = connection.execute(
                "SELECT action_type, payload_json, status FROM proposed_actions WHERE id = ?",
                (action_id,),
            ).fetchone()
            if not row:
                raise ValueError("Proposed action was not found")
            if row["status"] != "pending":
                raise ValueError("Proposed action was already decided")
            payload = json.loads(row["payload_json"])
            connection.execute(
                "UPDATE proposed_actions SET status = ? WHERE id = ?",
                (decision, action_id),
            )
            connection.execute(
                """INSERT INTO action_confirmations (id, action_id, decision, decided_at)
                   VALUES (?, ?, ?, ?)""",
                (_id("confirmation"), action_id, decision, _now()),
            )
            if decision == "confirmed" and "itemId" in payload:
                # The task as it is before the change, for the Orchestrator to hand on.
                task = connection.execute(f"SELECT {_ITEM_FIELDS} FROM daily_items WHERE id = ?",
                                          (payload["itemId"],)).fetchone()
                before = dict(task) if task else None
            if decision == "confirmed" and row["action_type"] == "select_variant":
                _writable_day(payload["date"])
                found = connection.execute(
                    """SELECT v.id FROM plan_variants v JOIN plan_sets s ON s.id = v.plan_set_id
                       WHERE v.id = ? AND s.plan_date = ?""",
                    (payload["variantId"], payload["date"]),
                ).fetchone()
                if not found:
                    raise ValueError("Plan variant does not belong to this date")
                current = connection.execute(
                    "SELECT variant_id FROM daily_confirmations WHERE plan_date = ?",
                    (payload["date"],),
                ).fetchone()
                if current and current["variant_id"] != payload["variantId"]:
                    if payload.get("reviewedFromVariantId") != current["variant_id"]:
                        raise PermissionError(
                            "The confirmed plan changed. Review its named replacement again."
                        )
                if not current or current["variant_id"] != payload["variantId"]:
                    self._confirm_with_connection(
                        connection, payload["date"], payload["variantId"]
                    )
            if decision == "confirmed" and row["action_type"] == "shorten_future_item":
                _writable_item_day(payload["date"])
                if payload["date"] <= date.today().isoformat():
                    raise PermissionError("This proposal is no longer for a future date")
                edited = connection.execute(
                    """UPDATE daily_items SET duration_minutes = ?
                       WHERE id = ? AND item_date = ?""",
                    (payload["durationMinutes"], payload["itemId"], payload["date"]),
                )
                if edited.rowcount != 1:
                    raise ValueError("Future commitment was not found")
            if decision == "confirmed" and row["action_type"] == "move_item":
                _writable_item_day(payload["date"])
                task = connection.execute(
                    """SELECT duration_minutes FROM daily_items
                       WHERE id = ? AND item_date = ? AND acceptance = 'accepted'""",
                    (payload["itemId"], payload["date"]),
                ).fetchone()
                if not task:
                    raise ValueError("The task to move was not found")
                # Another task may have taken the time since the move was proposed.
                clash = self._clashing_task(connection, payload["date"], payload["startTime"],
                                            task["duration_minutes"], payload["itemId"])
                if clash:
                    raise ValueError(_clash_message(clash))
                connection.execute(
                    "UPDATE daily_items SET start_time = ?, constraint_kind = 'fixed' WHERE id = ?",
                    (payload["startTime"], payload["itemId"]),
                )
            if decision == "confirmed" and row["action_type"] == "set_length":
                _writable_item_day(payload["date"])
                task = connection.execute(
                    """SELECT start_time FROM daily_items
                       WHERE id = ? AND item_date = ? AND acceptance = 'accepted'""",
                    (payload["itemId"], payload["date"]),
                ).fetchone()
                if not task:
                    raise ValueError("The task to change was not found")
                # Another task may have taken the time the longer task needs since this was proposed.
                clash = task["start_time"] and self._clashing_task(
                    connection, payload["date"], task["start_time"], payload["durationMinutes"], payload["itemId"])
                if clash:
                    raise ValueError(_clash_message(clash))
                # The length the user named to Ava is theirs, however short, so plans never shorten it.
                connection.execute(
                    """UPDATE daily_items SET duration_minutes = ?, duration_source = 'user',
                              estimated_by = NULL, estimate_basis = NULL WHERE id = ?""",
                    (payload["durationMinutes"], payload["itemId"]),
                )
            if decision == "confirmed" and row["action_type"] == "usual_length":
                # The length becomes the user's on the task's days still to come at the length they set.
                for item_id in payload["itemIds"]:
                    task = connection.execute(
                        """SELECT item_date, start_time FROM daily_items WHERE id = ? AND acceptance = 'accepted'
                           AND completion_status = 'planned' AND item_date >= ?""",
                        (item_id, date.today().isoformat())).fetchone()
                    if not task:
                        continue
                    clash = task["start_time"] and self._clashing_task(
                        connection, task["item_date"], task["start_time"], payload["durationMinutes"], item_id)
                    if clash:
                        raise ValueError(_clash_message(clash))
                    connection.execute(
                        """UPDATE daily_items SET duration_minutes = ?, duration_source = 'user',
                                  estimated_by = NULL, estimate_basis = NULL WHERE id = ?""",
                        (payload["durationMinutes"], item_id))
            if decision == "confirmed" and row["action_type"] == "catch_up":
                if payload["date"] > date.today().isoformat():
                    raise PermissionError("Only today's and earlier days' tasks can be caught up on")
                listed = {task["id"] for task in payload["tasks"]}
                chosen = statuses if statuses is not None else {task["id"]: task["to"] for task in payload["tasks"] if task["to"]}
                caught = [{key: item[key] for key in ("id", "status", "domain")}
                          for item in self._apply_statuses(connection, payload["date"], {
                              item_id: status for item_id, status in chosen.items() if item_id in listed}, strict=False)]
            if decision == "confirmed" and row["action_type"] == "change_meal":
                meal_update = self._change_meal(connection, payload)
            if decision == "confirmed" and row["action_type"] == "set_energy":
                # A card made on an earlier day is refused: a reading belongs to its own day alone.
                self._log_energy(connection, payload["date"], payload["level"])
            if decision == "confirmed" and row["action_type"] == "tick_item":
                # Ava's card is how a past day's checklist is corrected; the tick is kept as made now, on that task.
                entry = connection.execute(
                    """SELECT c.id FROM checklist_items c JOIN learning_tasks l ON l.pass_id = c.pass_id
                       WHERE l.item_id = ? AND c.id = ? AND c.removed = 0""", (payload["itemId"], payload["entryId"])).fetchone()
                if not entry:
                    raise ValueError("That checklist item is no longer there")
                connection.execute(
                    """UPDATE checklist_items SET ticked_at = CASE WHEN ? THEN COALESCE(ticked_at, ?) END,
                              ticked_on = CASE WHEN ? THEN COALESCE(ticked_on, ?) END WHERE id = ?""",
                    (payload["done"], datetime.now().isoformat(), payload["done"], payload["itemId"], payload["entryId"]))
            if decision == "confirmed" and row["action_type"] == "folder_check":
                chosen = set(ticked) if ticked is not None else {file["path"] for file in payload["files"] if file["ticked"]}
                folder_check = {"folderId": payload["folderId"],
                                "remove": [file["sourceId"] for file in payload["files"] if file["path"] not in chosen]}
            if decision == "confirmed" and row["action_type"] == "link_sources":
                # Ava's card links or unlinks a Learn task's sources on any day, as past days change through her.
                try:
                    self._link_sources(connection, payload["itemId"], payload["sourceIds"], payload["link"], past=True)
                except LookupError as error:
                    raise ValueError(str(error)) from error
            if decision == "confirmed" and row["action_type"] in ("add_item", "add_goal"):
                tasks = [payload] if row["action_type"] == "add_item" else payload["tasks"]
                area = domain or payload["domain"]
                if row["action_type"] == "add_goal":
                    new_goal = self._create_goal(connection, payload["title"], area)
                for task in tasks:
                    goal_id = new_goal or task.get("goalId")
                    if goal_id:
                        goal = connection.execute("SELECT domain, status FROM goals WHERE id = ?", (goal_id,)).fetchone()
                        if not goal or goal["status"] != "active":
                            raise ValueError("Its goal is no longer active; resume it, then ask again")
                    item = {"date": task["date"], "title": task["title"], "detail": "",
                            "domain": goal["domain"] if goal_id else area, "goalId": goal_id,
                            "startTime": task["startTime"], "durationMinutes": task["durationMinutes"],
                            "constraintKind": task["constraintKind"], "repeatKind": task["repeatKind"],
                            "estimateMinutes": task.get("estimateMinutes"), "learning": task.get("learning")}
                    # A length its source estimated stays the source's; any other estimate the model may refine.
                    created.append({"id": self._create_item(connection, item), "date": item["date"], "domain": item["domain"],
                                    "estimated": item["durationMinutes"] is None and not item["estimateMinutes"]})
            also = []
            if decision == "confirmed" and row["action_type"] in ("edit_item", "remove_item", "repeat_item"):
                if before is None:
                    raise ValueError("The task to change was not found")
                if row["action_type"] == "edit_item":
                    if before["date"] < date.today().isoformat():
                        self._past_task_edit(connection, before, payload["changes"])
                    self._update_item(connection, payload["itemId"], edited_task(before, payload["changes"]))
                    # The time a reported task took, as the user told it, or confirmed: it counts from now on. A
                    # time told is the whole of it, from its start to its stop, however many stretches it had.
                    timing = payload["changes"].get("actualTime")
                    if timing or payload["changes"].get("timeConfirmed"):
                        connection.execute(
                            """UPDATE daily_items SET actual_start = COALESCE(?, actual_start),
                                      actual_end = COALESCE(?, actual_end), actual_minutes = COALESCE(?, actual_minutes),
                                      time_confirmed = 1
                               WHERE id = ? AND completion_status != 'planned'""",
                            (timing and timing["start"], timing and timing["end"],
                             timing and minutes_after_midnight(timing["end"]) - minutes_after_midnight(timing["start"]),
                             payload["itemId"]))
                    # A repeating task's change reaches the repeat's own days from today on, when asked to.
                    alike = {field: value for field, value in payload["changes"].items()
                             if field in ("title", "detail", "goalId", "domain")}
                    later = [day for day in payload.get("days", []) if day >= date.today().isoformat()]
                    for other in connection.execute(
                            f"""SELECT {_ITEM_FIELDS} FROM daily_items WHERE repeat_series_id = ? AND id != ?
                                AND item_date IN ({','.join('?' * len(later))}) AND acceptance != 'dismissed'""",
                            (before["repeatSeriesId"], before["id"], *later)).fetchall() if later and alike else ():
                        if other["acceptance"] == "accepted":
                            self._update_item(connection, other["id"], edited_task(dict(other), alike))
                        else:
                            # A day prepared and still waiting for Accept is in no plan: its fields alone change.
                            changed = edited_task(dict(other), alike)
                            self._check_goal(connection, changed["goalId"], changed["domain"])
                            self._check_area_move(connection, other["id"], other["domain"], changed["domain"])
                            connection.execute(
                                "UPDATE daily_items SET title = ?, detail = ?, goal_id = ?, domain = ? WHERE id = ?",
                                (changed["title"], changed["detail"], changed["goalId"], changed["domain"], other["id"]))
                        also.append({"date": other["date"], "domain": other["domain"]})
                elif row["action_type"] == "repeat_item":
                    also = [{"date": gone["date"], "domain": gone["domain"]}
                            for gone in self._repeat_change(connection, before, payload)]
                else:
                    self._delete_item(connection, payload["itemId"])
        decided = {"id": action_id, "decision": decision, "applied": decision == "confirmed", "date": payload.get("date"),
                   **(meal_update or {}), **({"created": created} if created else {}),
                   **({"goalId": new_goal} if new_goal else {}), **({"caughtUp": caught} if caught is not None else {}),
                   **({"folderCheck": folder_check} if folder_check else {})}
        if decision == "confirmed" and row["action_type"] == "set_energy":
            decided["energy"] = {"average": self.energy(payload["date"]), "readings": self.energy_readings(payload["date"])}
        if before is None:
            return decided
        after = self.daily_item(before["id"]) if row["action_type"] == "edit_item" else None
        repeat = {"startsOn": payload["startsOn"]} if row["action_type"] == "repeat_item" else {}
        return {**decided, "before": before, **({"after": after} if after else {}), **({"also": also} if also else {}),
                **repeat}

    def _confirm_with_connection(
        self,
        connection: sqlite3.Connection,
        plan_date: str,
        variant_id: str,
        confirmed_at: str | None = None,
    ) -> None:
        connection.execute(
            """INSERT INTO daily_confirmations (plan_date, variant_id, confirmed_at)
               VALUES (?, ?, ?)
               ON CONFLICT(plan_date) DO UPDATE SET
                 variant_id = excluded.variant_id,
                 confirmed_at = excluded.confirmed_at""",
            (plan_date, variant_id, confirmed_at or _now()),
        )
        # A task reported before the plan was set keeps its status in the plan that schedules it.
        connection.execute(
            """UPDATE plan_entries
               SET completion_status = (
                 SELECT item.completion_status FROM daily_items item
                 WHERE item.id = plan_entries.source_item_id)
               WHERE variant_id = ? AND EXISTS (
                 SELECT 1 FROM daily_items item
                 WHERE item.id = plan_entries.source_item_id AND item.completion_status != 'planned')""",
            (variant_id,),
        )
