from __future__ import annotations

import json
import hashlib
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from .planner import DOMAIN_LABELS, PlanItem, build_recorded_variants, build_variants, minutes_by_domain


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _writable_day(plan_date: str) -> None:
    if plan_date != date.today().isoformat():
        raise PermissionError("Only today's plan and outcomes can be changed; past plans are read-only")


def _writable_item_day(item_date: str) -> None:
    if item_date < date.today().isoformat():
        raise PermissionError("Past daily records are read-only")


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
                    version INTEGER NOT NULL DEFAULT 1,
                    supersedes_variant_id TEXT REFERENCES plan_variants(id),
                    created_at TEXT NOT NULL,
                    UNIQUE(plan_set_id, slug, version)
                );

                CREATE TABLE IF NOT EXISTS plan_entries (
                    id TEXT PRIMARY KEY,
                    variant_id TEXT NOT NULL REFERENCES plan_variants(id) ON DELETE CASCADE,
                    position INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    title TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    source_item_id TEXT REFERENCES daily_items(id),
                    domain TEXT NOT NULL CHECK(domain IN ('learning', 'life', 'finance', 'rest')),
                    duration_minutes INTEGER NOT NULL CHECK(duration_minutes > 0),
                    constraint_kind TEXT NOT NULL CHECK(constraint_kind IN ('fixed', 'flexible')),
                    completion_status TEXT NOT NULL DEFAULT 'planned' CHECK(completion_status IN ('planned', 'done', 'partial', 'skipped')),
                    UNIQUE(variant_id, position)
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
                    created_at TEXT NOT NULL
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

                CREATE TABLE IF NOT EXISTS suggestion_pool (
                    id TEXT PRIMARY KEY,
                    period_kind TEXT NOT NULL CHECK(period_kind IN ('day', 'week', 'month')),
                    period_key TEXT NOT NULL,
                    domain TEXT NOT NULL CHECK(domain IN ('learning', 'life', 'finance', 'rest', 'cross')),
                    content TEXT NOT NULL,
                    priority TEXT NOT NULL CHECK(priority IN ('soft', 'strong')),
                    source_key TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'discarded')),
                    discarded_at TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(period_kind, period_key, source_key)
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

                CREATE TABLE IF NOT EXISTS finance_entries (
                    id TEXT PRIMARY KEY,
                    amount_minor INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    category TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS goals (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    domain TEXT NOT NULL CHECK(domain IN ('learning', 'life', 'finance', 'rest')),
                    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'paused', 'completed')),
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS daily_items (
                    id TEXT PRIMARY KEY,
                    item_date TEXT NOT NULL,
                    goal_id TEXT REFERENCES goals(id),
                    title TEXT NOT NULL,
                    detail TEXT NOT NULL DEFAULT '',
                    domain TEXT NOT NULL CHECK(domain IN ('learning', 'life', 'finance', 'rest')),
                    start_time TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL CHECK(duration_minutes > 0),
                    constraint_kind TEXT NOT NULL CHECK(constraint_kind IN ('fixed', 'flexible')),
                    repeat_kind TEXT NOT NULL DEFAULT 'none' CHECK(repeat_kind IN ('none', 'daily', 'weekly')),
                    protected INTEGER NOT NULL DEFAULT 0 CHECK(protected IN (0, 1)),
                    origin_kind TEXT NOT NULL DEFAULT 'user' CHECK(origin_kind IN ('user', 'agent-origin')),
                    origin_detail TEXT NOT NULL DEFAULT '',
                    origin_source_item_id TEXT REFERENCES daily_items(id),
                    completion_status TEXT NOT NULL DEFAULT 'planned' CHECK(completion_status IN ('planned', 'done', 'partial', 'skipped')),
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS daily_items_by_date ON daily_items(item_date);

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

                CREATE TABLE IF NOT EXISTS plan_generation_routes (
                    plan_set_id TEXT PRIMARY KEY REFERENCES plan_sets(id) ON DELETE CASCADE,
                    route_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS agent_runs (
                    id TEXT PRIMARY KEY,
                    message_id TEXT NOT NULL REFERENCES conversation_messages(id) ON DELETE CASCADE,
                    sequence INTEGER NOT NULL,
                    agent_key TEXT NOT NULL CHECK(agent_key IN ('orchestrator', 'learning', 'life', 'finance', 'summary')),
                    phase TEXT NOT NULL CHECK(phase IN ('dispatch', 'assessment', 'summary', 'synthesis')),
                    summary TEXT NOT NULL,
                    reads_json TEXT NOT NULL,
                    writes_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(message_id, sequence)
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

                CREATE TABLE IF NOT EXISTS knowledge_acquisitions (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    source_license TEXT NOT NULL,
                    source_updated_at TEXT,
                    filter_json TEXT NOT NULL,
                    confirmed_plan_id TEXT,
                    imported_source_id TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS knowledge_import_plans (
                    id TEXT PRIMARY KEY,
                    acquisition_id TEXT NOT NULL REFERENCES knowledge_acquisitions(id),
                    name TEXT NOT NULL,
                    labels_json TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    UNIQUE(acquisition_id, position)
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

                CREATE TABLE IF NOT EXISTS learning_items (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    difficulty TEXT NOT NULL CHECK(difficulty IN ('easy', 'medium', 'hard')),
                    estimated_minutes INTEGER NOT NULL CHECK(estimated_minutes > 0),
                    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'done', 'archived')),
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS learning_sessions (
                    id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL REFERENCES learning_items(id),
                    session_date TEXT NOT NULL,
                    minutes INTEGER NOT NULL CHECK(minutes > 0),
                    result TEXT NOT NULL CHECK(result IN ('done', 'partial', 'skipped')),
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS life_habits (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    frequency TEXT NOT NULL CHECK(frequency IN ('daily', 'weekly')),
                    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1)),
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS life_habit_logs (
                    id TEXT PRIMARY KEY,
                    habit_id TEXT NOT NULL REFERENCES life_habits(id),
                    log_date TEXT NOT NULL,
                    done INTEGER NOT NULL CHECK(done IN (0, 1)),
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    UNIQUE(habit_id, log_date)
                );

                CREATE TABLE IF NOT EXISTS life_daily (
                    daily_date TEXT PRIMARY KEY,
                    sleep_hours REAL CHECK(sleep_hours IS NULL OR (sleep_hours >= 0 AND sleep_hours <= 24)),
                    energy_level INTEGER CHECK(energy_level IS NULL OR (energy_level BETWEEN 1 AND 5)),
                    mood INTEGER CHECK(mood IS NULL OR (mood BETWEEN 1 AND 5)),
                    note TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS life_events (
                    id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL UNIQUE REFERENCES daily_items(id),
                    category TEXT NOT NULL CHECK(category IN ('sport', 'social', 'chore', 'health', 'other')),
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS finance_account (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    opening_balance_cents INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS finance_transactions (
                    id TEXT PRIMARY KEY,
                    transaction_date TEXT NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                    amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
                    category TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS finance_budgets (
                    id TEXT PRIMARY KEY,
                    year_month TEXT NOT NULL,
                    category TEXT NOT NULL,
                    budget_cents INTEGER NOT NULL CHECK(budget_cents >= 0),
                    updated_at TEXT NOT NULL,
                    UNIQUE(year_month, category)
                );
                """
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
            connection.execute(
                """CREATE UNIQUE INDEX IF NOT EXISTS future_origin_once
                   ON daily_items(item_date, origin_source_item_id)
                   WHERE origin_source_item_id IS NOT NULL"""
            )
            entry_columns = {row["name"] for row in connection.execute("PRAGMA table_info(plan_entries)")}
            if "source_item_id" not in entry_columns:
                connection.execute("ALTER TABLE plan_entries ADD COLUMN source_item_id TEXT REFERENCES daily_items(id)")
            source_columns = {row["name"] for row in connection.execute("PRAGMA table_info(knowledge_sources)")}
            if "source_url" not in source_columns:
                connection.execute("ALTER TABLE knowledge_sources ADD COLUMN source_url TEXT NOT NULL DEFAULT ''")
            if "source_license" not in source_columns:
                connection.execute("ALTER TABLE knowledge_sources ADD COLUMN source_license TEXT NOT NULL DEFAULT ''")
            match_columns = {row["name"] for row in connection.execute("PRAGMA table_info(retrieval_matches)")}
            if "source_url" not in match_columns:
                connection.execute("ALTER TABLE retrieval_matches ADD COLUMN source_url TEXT NOT NULL DEFAULT ''")
            if "source_license" not in match_columns:
                connection.execute("ALTER TABLE retrieval_matches ADD COLUMN source_license TEXT NOT NULL DEFAULT ''")

    def goals(self) -> list[dict]:
        """Return the user's goal ledger in creation order."""
        with self.connect() as connection:
            goals = [dict(row) for row in connection.execute(
                """SELECT g.id, g.title, g.domain, g.status,
                          COUNT(i.id) AS itemCount,
                          SUM(CASE WHEN i.completion_status = 'done' THEN 1 ELSE 0 END) AS doneCount
                   FROM goals g LEFT JOIN daily_items i ON i.goal_id = g.id
                   GROUP BY g.id ORDER BY g.created_at, g.rowid"""
            )]
            linked = connection.execute(
                """SELECT id, goal_id AS goalId, item_date AS date, title, detail, domain,
                          start_time AS startTime, duration_minutes AS durationMinutes,
                          completion_status AS status
                   FROM daily_items WHERE goal_id IS NOT NULL
                   ORDER BY item_date, start_time, rowid"""
            ).fetchall()
        by_goal: dict[str, list[dict]] = {goal["id"]: [] for goal in goals}
        for row in linked:
            by_goal.setdefault(row["goalId"], []).append(dict(row))
        for goal in goals:
            goal["linkedItems"] = by_goal.get(goal["id"], [])
        return goals

    def create_goal(self, title: str, domain: str) -> dict:
        """Add a user-authored goal without generating a schedule."""
        goal_id = _id("goal")
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO goals (id, title, domain, created_at) VALUES (?, ?, ?, ?)",
                (goal_id, title, domain, _now()),
            )
        return next(goal for goal in self.goals() if goal["id"] == goal_id)

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
        """Return dated user records independently of any proposed plan snapshot."""
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(
                """SELECT id, item_date AS date, goal_id AS goalId, title, detail, domain,
                          start_time, duration_minutes, constraint_kind,
                          repeat_kind AS repeatKind, protected, origin_kind AS originKind,
                          origin_detail AS originDetail, origin_source_item_id AS originSourceItemId,
                          completion_status
                   FROM daily_items WHERE item_date = ? ORDER BY start_time, rowid""",
                (plan_date,),
            )]

    def _check_goal(self, connection: sqlite3.Connection, goal_id: str | None, domain: str) -> None:
        if goal_id is None:
            return
        row = connection.execute("SELECT domain FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if not row or row["domain"] != domain:
            raise ValueError("Choose a goal in the same area")

    def create_daily_item(self, item: dict) -> dict:
        """Store a dated task or commitment supplied by the user."""
        _writable_item_day(item["date"])
        item_id = _id("item")
        with self.connect() as connection:
            self._check_goal(connection, item.get("goalId"), item["domain"])
            connection.execute(
                """INSERT INTO daily_items
                   (id, item_date, goal_id, title, detail, domain, start_time,
                    duration_minutes, constraint_kind, repeat_kind, protected, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (item_id, item["date"], item.get("goalId"), item["title"], item["detail"],
                 item["domain"], item["startTime"], item["durationMinutes"],
                 item["constraintKind"], item["repeatKind"], int(item["protected"]), _now()),
            )
        return next(record for record in self.daily_items(item["date"]) if record["id"] == item_id)

    def update_daily_item(self, item_id: str, item: dict) -> dict:
        """Update an owned daily record; existing plan snapshots remain unchanged."""
        _writable_item_day(item["date"])
        if item["date"] > date.today().isoformat() and item["status"] != "planned":
            raise PermissionError("Future outcomes cannot be reported before the day arrives")
        with self.connect() as connection:
            prior = connection.execute(
                "SELECT item_date FROM daily_items WHERE id = ?", (item_id,)
            ).fetchone()
            if not prior:
                raise ValueError("Daily item not found")
            _writable_item_day(prior["item_date"])
            if item["domain"] != "life" and connection.execute(
                "SELECT 1 FROM life_events WHERE item_id = ?", (item_id,)
            ).fetchone():
                raise ValueError("A categorized Life event must remain in the Life area")
            self._check_goal(connection, item.get("goalId"), item["domain"])
            updated = connection.execute(
                """UPDATE daily_items SET item_date = ?, goal_id = ?, title = ?, detail = ?,
                   domain = ?, start_time = ?, duration_minutes = ?, constraint_kind = ?,
                   repeat_kind = ?, protected = ?, completion_status = ? WHERE id = ?""",
                (item["date"], item.get("goalId"), item["title"], item["detail"],
                 item["domain"], item["startTime"], item["durationMinutes"],
                 item["constraintKind"], item["repeatKind"], int(item["protected"]),
                 item["status"], item_id),
            )
            if not updated.rowcount:
                raise ValueError("Daily item not found")
            connection.execute(
                "UPDATE plan_entries SET completion_status = ? WHERE source_item_id = ?",
                (item["status"], item_id),
            )
        return next(record for record in self.daily_items(item["date"]) if record["id"] == item_id)

    def delete_daily_item(self, item_id: str) -> dict:
        """Remove an owned record for today or later that no confirmed plan used.

        Past records and anything a confirmed day scheduled stay as history. Unconfirmed plan
        proposals keep their own copy of the entry and simply lose the link.
        """
        with self.connect() as connection:
            row = connection.execute(
                "SELECT item_date, title FROM daily_items WHERE id = ?", (item_id,)
            ).fetchone()
            if not row:
                raise ValueError("Daily item not found")
            _writable_item_day(row["item_date"])
            if connection.execute(
                """SELECT 1 FROM plan_entries entry
                   JOIN daily_confirmations confirmation ON confirmation.variant_id = entry.variant_id
                   WHERE entry.source_item_id = ?""",
                (item_id,),
            ).fetchone():
                raise PermissionError(
                    "A confirmed plan scheduled this record; confirmed days remain read-only"
                )
            connection.execute(
                "UPDATE plan_entries SET source_item_id = NULL WHERE source_item_id = ?", (item_id,)
            )
            connection.execute(
                "UPDATE daily_items SET origin_source_item_id = NULL WHERE origin_source_item_id = ?",
                (item_id,),
            )
            connection.execute("DELETE FROM life_events WHERE item_id = ?", (item_id,))
            connection.execute("DELETE FROM daily_items WHERE id = ?", (item_id,))
        return {"id": item_id, "title": row["title"], "date": row["item_date"]}

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

    def summary_facts(self, start: str, end: str) -> dict:
        """Collect confirmed-plan outcomes or owned records without double counting."""
        end = min(end, date.today().isoformat())
        with self.connect() as connection:
            plan_rows = connection.execute(
                """SELECT s.plan_date AS record_date, e.title, e.detail, e.domain,
                          e.start_time, e.duration_minutes, e.constraint_kind,
                          e.completion_status, COALESCE(i.protected, 0) AS protected
                   FROM plan_entries e
                   JOIN plan_variants v ON v.id = e.variant_id
                   JOIN plan_sets s ON s.id = v.plan_set_id
                   JOIN daily_confirmations c ON c.plan_date = s.plan_date
                                              AND c.variant_id = v.id
                   LEFT JOIN daily_items i ON i.id = e.source_item_id
                   WHERE s.plan_date BETWEEN ? AND ?""", (start, end)
            ).fetchall()
            managed_rows = connection.execute(
                """SELECT i.item_date AS record_date, i.title, i.detail, i.domain,
                          i.start_time, i.duration_minutes, i.constraint_kind,
                          i.completion_status, i.protected
                   FROM daily_items i
                   WHERE i.item_date BETWEEN ? AND ? AND NOT EXISTS (
                     SELECT 1 FROM daily_confirmations c WHERE c.plan_date = i.item_date
                   )""", (start, end)
            ).fetchall()
            feedback_rows = connection.execute(
                """SELECT f.task_title, f.domain, COUNT(DISTINCT f.id) AS requests,
                          MAX(COALESCE(i.protected, 0)) AS protected
                   FROM feedback_signals f
                   LEFT JOIN daily_items i ON i.title = f.task_title AND i.domain = f.domain
                   WHERE f.request_date BETWEEN ? AND ?
                   GROUP BY f.task_title, f.domain ORDER BY requests DESC, f.task_title""",
                (start, end),
            ).fetchall()
            recurring_success_rows = connection.execute(
                """SELECT title, domain, COUNT(DISTINCT item_date) AS done_days
                   FROM daily_items WHERE item_date BETWEEN ? AND ?
                     AND completion_status = 'done' AND protected = 1
                     AND repeat_kind != 'none'
                   GROUP BY title, domain HAVING done_days >= 2
                   ORDER BY done_days DESC, title""",
                (start, end),
            ).fetchall()
            recorded_days = connection.execute(
                """SELECT COUNT(*) FROM (
                     SELECT plan_date AS day FROM plan_sets WHERE plan_date BETWEEN ? AND ?
                     UNION SELECT item_date AS day FROM daily_items WHERE item_date BETWEEN ? AND ?
                     UNION SELECT session_date AS day FROM learning_sessions
                       WHERE session_date BETWEEN ? AND ?
                     UNION SELECT log_date AS day FROM life_habit_logs
                       WHERE log_date BETWEEN ? AND ?
                     UNION SELECT daily_date AS day FROM life_daily
                       WHERE daily_date BETWEEN ? AND ?
                     UNION SELECT transaction_date AS day FROM finance_transactions
                       WHERE transaction_date BETWEEN ? AND ?
                   )""", (start, end) * 6
            ).fetchone()[0]
            learning_rows = connection.execute(
                """SELECT s.session_date, s.minutes, s.result, i.title, i.difficulty
                   FROM learning_sessions s JOIN learning_items i ON i.id = s.item_id
                   WHERE s.session_date BETWEEN ? AND ? ORDER BY s.session_date""",
                (start, end),
            ).fetchall()
            habit_rows = connection.execute(
                """SELECT l.log_date, l.done, h.title FROM life_habit_logs l
                   JOIN life_habits h ON h.id = l.habit_id
                   WHERE l.log_date BETWEEN ? AND ? ORDER BY l.log_date""",
                (start, end),
            ).fetchall()
            life_rows = connection.execute(
                """SELECT daily_date, sleep_hours, energy_level, mood, note
                   FROM life_daily WHERE daily_date BETWEEN ? AND ? ORDER BY daily_date""",
                (start, end),
            ).fetchall()
            money_rows = connection.execute(
                """SELECT transaction_date, type, amount_cents, category, note
                   FROM finance_transactions WHERE transaction_date BETWEEN ? AND ?
                   ORDER BY transaction_date""", (start, end)
            ).fetchall()
            budget_rows = connection.execute(
                """SELECT year_month, category, budget_cents FROM finance_budgets
                   WHERE year_month BETWEEN ? AND ? ORDER BY year_month, category""",
                (start[:7], end[:7]),
            ).fetchall()
            month_spending = connection.execute(
                """SELECT substr(transaction_date, 1, 7) AS month, category,
                          SUM(amount_cents) AS spent
                   FROM finance_transactions WHERE type = 'expense'
                     AND substr(transaction_date, 1, 7) BETWEEN ? AND ?
                     AND transaction_date <= ? GROUP BY month, category""",
                (start[:7], end[:7], end),
            ).fetchall()
            knowledge_count = connection.execute(
                "SELECT COUNT(*) FROM knowledge_sources"
            ).fetchone()[0]
        domains = {domain: {"scheduled": 0, "done": 0, "partial": 0, "skipped": 0}
                   for domain in DOMAIN_LABELS}
        for row in (*plan_rows, *managed_rows):
            domain = domains[row["domain"]]
            domain["scheduled"] += 1
            if row["completion_status"] != "planned":
                domain[row["completion_status"]] += 1
        task_outcomes = {}
        for row in (*plan_rows, *managed_rows):
            identity = (row["title"], row["domain"])
            outcome = task_outcomes.setdefault(identity, {
                "taskTitle": row["title"], "domain": row["domain"],
                "scheduled": 0, "done": 0, "partial": 0, "skipped": 0,
                "planned": 0, "startTime": row["start_time"],
                "durationMinutes": row["duration_minutes"],
                "constraintKind": row["constraint_kind"], "detail": row["detail"],
                "protected": bool(row["protected"]), "lastDate": row["record_date"],
            })
            outcome["scheduled"] += 1
            outcome[row["completion_status"]] += 1
            outcome["protected"] = outcome["protected"] or bool(row["protected"])
            if row["record_date"] >= outcome["lastDate"]:
                outcome.update({
                    "startTime": row["start_time"],
                    "durationMinutes": row["duration_minutes"],
                    "constraintKind": row["constraint_kind"],
                    "detail": row["detail"], "lastDate": row["record_date"],
                })
        return {
            "recordedDays": recorded_days, "domains": domains,
            "goals": self.goals(), "knowledgeSourceCount": knowledge_count,
            "taskOutcomes": sorted(task_outcomes.values(), key=lambda item: (
                item["domain"], item["taskTitle"]
            )),
            "feedback": [{"taskTitle": row["task_title"], "domain": row["domain"],
                          "shortenRequests": row["requests"], "protected": bool(row["protected"])}
                         for row in feedback_rows],
            "completedRecurring": [{"taskTitle": row["title"], "domain": row["domain"],
                                    "doneDays": row["done_days"]}
                                   for row in recurring_success_rows],
            "areaEvidence": {
                "learning": {"sessions": len(learning_rows),
                             "minutes": sum(row["minutes"] for row in learning_rows),
                             "done": sum(row["result"] == "done" for row in learning_rows),
                             "items": sorted({row["title"] for row in learning_rows})},
                "life": {"habitReports": len(habit_rows),
                         "habitDone": sum(bool(row["done"]) for row in habit_rows),
                         "latestDaily": dict(life_rows[-1]) if life_rows else None,
                         "notes": [row["note"] for row in life_rows if row["note"]][-10:]},
                "finance": {"transactions": len(money_rows),
                            "incomeCents": sum(row["amount_cents"] for row in money_rows
                                               if row["type"] == "income"),
                            "expenseCents": sum(row["amount_cents"] for row in money_rows
                                                if row["type"] == "expense"),
                            "categories": sorted({row["category"] for row in money_rows}),
                            "budgetStatus": [{"month": row["year_month"],
                                              "category": row["category"],
                                              "budgetCents": row["budget_cents"],
                                              "spentCents": next((spent["spent"] for spent in month_spending
                                                                  if spent["month"] == row["year_month"]
                                                                  and spent["category"] == row["category"]), 0)}
                                             for row in budget_rows]},
            },
        }

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

    def prepare_future_commitments(self, report: dict) -> list[dict]:
        """Add Summary-informed future records with durable agent provenance, no plan approval."""
        if report["periodKind"] not in ("week", "month"):
            return []
        now = date.today()
        added = []
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            shortening = {(signal["taskTitle"], signal["domain"]): signal
                          for signal in report["feedback"]
                          if signal["shortenRequests"] >= 2 and signal["protected"]}
            successes = {(signal["taskTitle"], signal["domain"]): signal
                         for signal in report.get("completedRecurring", ())
                         if signal["doneDays"] >= 2}
            for title, domain in sorted(shortening.keys() | successes.keys()):
                row = connection.execute(
                    """SELECT id, goal_id, title, detail, domain, start_time, duration_minutes,
                              constraint_kind, repeat_kind, protected, origin_source_item_id
                       FROM daily_items WHERE title = ? AND domain = ? AND protected = 1
                         AND repeat_kind != 'none' AND item_date <= ?
                       ORDER BY item_date DESC, rowid DESC LIMIT 1""",
                    (title, domain, now.isoformat()),
                ).fetchone()
                if not row:
                    continue
                source_id = row["origin_source_item_id"] or row["id"]
                future_date = (now + timedelta(days=7 if row["repeat_kind"] == "weekly" else 1)).isoformat()
                existing = connection.execute(
                    """SELECT id FROM daily_items WHERE item_date = ? AND
                       (origin_source_item_id = ? OR (title = ? AND domain = ? AND start_time = ?))""",
                    (future_date, source_id, row["title"], row["domain"], row["start_time"]),
                ).fetchone()
                if existing:
                    continue
                preference = shortening.get((title, domain))
                completed = successes.get((title, domain))
                evidence = (f"Summary {report['periodKey']}: {preference['shortenRequests']} explicit "
                            f"requests to shorten {row['title']}; marked important to keep. "
                            "A shorter future block preserves its benefit without omitting it.") if preference else (
                            f"Summary {report['periodKey']}: {row['title']} was marked important "
                            f"and completed on {completed['doneDays']} recorded days. "
                            "Prepared its next recurring date at the existing size; you can change it.")
                item_id = _id("item")
                connection.execute(
                    """INSERT INTO daily_items
                       (id, item_date, goal_id, title, detail, domain, start_time,
                        duration_minutes, constraint_kind, repeat_kind, protected,
                        origin_kind, origin_detail, origin_source_item_id, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'agent-origin', ?, ?, ?)""",
                    (item_id, future_date, row["goal_id"], row["title"], row["detail"],
                    row["domain"], row["start_time"],
                    max(15, row["duration_minutes"] - 15) if preference else row["duration_minutes"],
                     row["constraint_kind"], row["repeat_kind"], row["protected"],
                     evidence, source_id, _now()),
                )
                added.append((future_date, item_id))
        return [next(item for item in self.daily_items(future_date) if item["id"] == item_id)
                for future_date, item_id in added]

    def record_plan_route(self, plan_set_id: str, runs: Iterable[dict]) -> list[dict]:
        """Retain the bounded agent route that proposed a plan, separate from approval."""
        route = list(runs)
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO plan_generation_routes (plan_set_id, route_json, created_at) VALUES (?, ?, ?)",
                (plan_set_id, json.dumps(route), _now()),
            )
        return route

    def plan_route(self, plan_set_id: str) -> list[dict]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT route_json FROM plan_generation_routes WHERE plan_set_id = ?",
                (plan_set_id,),
            ).fetchone()
        return json.loads(row["route_json"]) if row else []

    def create_recorded_plan(self, plan_date: str, memory: Iterable[dict] | None = None,
                             guidance: Iterable[dict] | None = None) -> str:
        """Build alternatives from owned and recurring items, then retain a snapshot."""
        _writable_day(plan_date)
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM plan_sets WHERE plan_date = ?", (plan_date,)
            ).fetchone()
            if existing:
                raise PermissionError("A saved plan already exists for this date")
            today_rows = list(connection.execute(
                """SELECT goal_id, start_time, title, detail, domain, duration_minutes,
                          constraint_kind, repeat_kind, protected
                   FROM daily_items WHERE item_date = ? ORDER BY start_time, rowid""",
                (plan_date,),
            ))
            recurring = connection.execute(
                """SELECT i.goal_id, i.item_date, i.start_time, i.title, i.detail,
                          i.domain, i.duration_minutes, i.constraint_kind,
                          i.repeat_kind, i.protected, i.origin_kind, i.origin_detail,
                          i.origin_source_item_id
                   FROM daily_items i LEFT JOIN goals g ON g.id = i.goal_id
                   WHERE i.item_date < ? AND i.repeat_kind != 'none'
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
            rows = sorted((*today_rows, *carried), key=lambda row: row["start_time"])
            items = [PlanItem(row["start_time"], row["title"], row["detail"], row["domain"],
                              row["duration_minutes"], row["constraint_kind"],
                              bool(row["protected"])) for row in rows]
            variants = build_recorded_variants(
                items, self.feedback_memory(plan_date) if memory is None else memory,
                self.active_suggestion_pool() if guidance is None else guidance,
            )
            for row in carried:
                connection.execute(
                    """INSERT INTO daily_items
                       (id, item_date, goal_id, title, detail, domain, start_time,
                        duration_minutes, constraint_kind, repeat_kind, protected,
                        origin_kind, origin_detail, origin_source_item_id, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (_id("item"), plan_date, row["goal_id"], row["title"], row["detail"],
                     row["domain"], row["start_time"], row["duration_minutes"],
                     row["constraint_kind"], row["repeat_kind"], row["protected"],
                     row["origin_kind"], row["origin_detail"], row["origin_source_item_id"], _now()),
                )
            return self._seed_day(connection, plan_date, "orchestrator-records-v1", variants)

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
        source_refs = {}
        if source != "deterministic-v1":
            source_refs = {(row["title"], row["domain"], row["start_time"]): row["id"]
                           for row in connection.execute(
                               "SELECT id, title, domain, start_time FROM daily_items WHERE item_date = ?",
                               (plan_date,),
                           )}
        for variant in (variants if variants is not None else build_variants()):
            variant_id = _id("variant")
            connection.execute(
                """INSERT INTO plan_variants
                   (id, plan_set_id, name, slug, rationale, version, created_at)
                   VALUES (?, ?, ?, ?, ?, 1, ?)""",
                (
                    variant_id,
                    plan_set_id,
                    variant["name"],
                    variant["slug"],
                    variant["rationale"],
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
                        source_refs.get((item.title, item.domain, item.start)),
                        item.domain,
                        item.duration_minutes,
                        item.constraint,
                    ),
                )
        if source == "deterministic-v1":
            connection.execute(
                """INSERT INTO suggestions (id, plan_date, title, detail)
                   VALUES (?, ?, ?, ?)""",
                (_id("suggestion"), plan_date, "Try a 10-minute walk after lunch.",
                 "A short walk can restore energy and focus for the afternoon."),
            )
        return plan_set_id

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
                }
            plan_set_id = str(existing["id"])
            source = str(existing["source"])
            variants = connection.execute(
                """SELECT id, name, slug, rationale, version
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
                          constraint_kind, completion_status
                   FROM plan_entries WHERE variant_id = ? ORDER BY position""",
                (selected,),
            ).fetchall()
            suggestion = connection.execute(
                """SELECT id, title, detail, decision
                   FROM suggestions WHERE plan_date = ? ORDER BY rowid LIMIT 1""",
                (plan_date,),
            ).fetchone()

        entry_payload = [dict(row) for row in entries]
        owned_items = self.daily_items(plan_date)
        memory = self.feedback_memory(plan_date) if source != "deterministic-v1" else []
        totals = {domain: 0 for domain in DOMAIN_LABELS}
        for entry in entry_payload:
            totals[entry["domain"]] += int(entry["duration_minutes"])
        return {
            "date": plan_date,
            "planSetId": plan_set_id,
            "planRoute": self.plan_route(plan_set_id),
            "planSource": source,
            "selectedVariantId": selected,
            "confirmedVariantId": str(confirmed["variant_id"]) if confirmed else None,
            "confirmedAt": str(confirmed["confirmed_at"]) if confirmed else None,
            "variants": [dict(row) for row in variants],
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
                    f"Repeated shortening requests for {signal['taskTitle']} informed this plan; "
                    "keep a shorter block rather than removing an important-to-keep task."
                    if any(item["title"] == signal["taskTitle"] and item["protected"]
                           for item in owned_items) else
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
                   LEFT JOIN plan_entries e ON e.variant_id = v.id
                   WHERE substr(s.plan_date, 1, 7) = ?
                   GROUP BY s.plan_date, s.source, c.variant_id, v.name
                   ORDER BY s.plan_date""",
                (month,),
            ).fetchall()
            managed = connection.execute(
                """SELECT item_date, COUNT(*) AS item_count,
                          SUM(CASE WHEN completion_status = 'done' THEN 1 ELSE 0 END) AS done_count
                   FROM daily_items WHERE substr(item_date, 1, 7) = ?
                   GROUP BY item_date ORDER BY item_date""", (month,)
            ).fetchall()
        records = {row["plan_date"]: {
            "date": row["plan_date"], "confirmed": row["confirmed_variant_id"] is not None,
            "variantName": row["display_variant_name"], "planSource": row["source"],
            "entryCount": row["entry_count"], "doneCount": row["done_count"],
            "managedCount": 0, "managedDoneCount": 0,
        } for row in rows}
        for row in managed:
            record = records.setdefault(row["item_date"], {
                "date": row["item_date"], "confirmed": False, "variantName": None,
                "planSource": None, "entryCount": row["item_count"],
                "doneCount": row["done_count"], "managedCount": 0, "managedDoneCount": 0,
            })
            record["managedCount"] = row["item_count"]
            record["managedDoneCount"] = row["done_count"]
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

    def update_entry(self, entry_id: str, status: str) -> dict:
        with self.connect() as connection:
            entry = connection.execute(
                """SELECT e.id, e.variant_id, e.source_item_id, s.plan_date,
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
            cursor = connection.execute(
                "UPDATE plan_entries SET completion_status = ? WHERE id = ?",
                (status, entry_id),
            )
            if entry["source_item_id"]:
                connection.execute(
                    "UPDATE plan_entries SET completion_status = ? WHERE source_item_id = ?",
                    (status, entry["source_item_id"]),
                )
                connection.execute(
                    "UPDATE daily_items SET completion_status = ? WHERE id = ?",
                    (status, entry["source_item_id"]),
                )
            if cursor.rowcount != 1:
                raise ValueError("Plan entry was not found")
            row = connection.execute(
                "SELECT id, completion_status FROM plan_entries WHERE id = ?", (entry_id,)
            ).fetchone()
        return dict(row)

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
                source_key = hashlib.sha256(
                    f"{domain}\0{' '.join(content.lower().split())}".encode("utf-8")
                ).hexdigest()[:24]
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

    def stage_knowledge_acquisition(self, topic: str, source: dict,
                                    filtering: dict, choices: list[dict]) -> dict:
        acquisition_id = _id("acquisition")
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO knowledge_acquisitions
                   (id, topic, title, content, source_url, source_license,
                    source_updated_at, filter_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (acquisition_id, topic, source["title"], source["text"],
                 source["sourceUrl"], source["sourceLicense"],
                 source.get("sourceUpdatedAt"), json.dumps(filtering), _now()),
            )
            plans = []
            for position, choice in enumerate(choices):
                plan_id = _id("import_plan")
                connection.execute(
                    """INSERT INTO knowledge_import_plans
                       (id, acquisition_id, name, labels_json, position)
                       VALUES (?, ?, ?, ?, ?)""",
                    (plan_id, acquisition_id, choice["name"],
                     json.dumps(choice["labels"]), position),
                )
                plans.append({"id": plan_id, "name": choice["name"],
                              "labels": choice["labels"]})
        return {"acquisitionId": acquisition_id, "topic": topic,
                "sourceTitle": source["title"], "sourceUrl": source["sourceUrl"],
                "sourceLicense": source["sourceLicense"], "filter": filtering,
                "plans": plans}

    def pending_knowledge_imports(self) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT id, topic, title, source_url, source_license, filter_json,
                          confirmed_plan_id, created_at
                   FROM knowledge_acquisitions WHERE imported_source_id IS NULL
                   ORDER BY created_at DESC LIMIT 10"""
            ).fetchall()
            return [{"acquisitionId": row["id"], "topic": row["topic"],
                     "sourceTitle": row["title"], "sourceUrl": row["source_url"],
                     "sourceLicense": row["source_license"],
                     "filter": json.loads(row["filter_json"]),
                     "selectedPlanId": row["confirmed_plan_id"],
                     "plans": [{"id": plan["id"], "name": plan["name"],
                                "labels": json.loads(plan["labels_json"])}
                               for plan in connection.execute(
                                   """SELECT id, name, labels_json FROM knowledge_import_plans
                                      WHERE acquisition_id = ? ORDER BY position""",
                                   (row["id"],))]} for row in rows]

    def knowledge_import_plan(self, plan_id: str) -> dict | None:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT p.id, p.name, p.labels_json, a.id AS acquisition_id,
                          a.topic, a.title, a.content, a.source_url, a.source_license,
                          a.confirmed_plan_id, a.imported_source_id
                   FROM knowledge_import_plans p JOIN knowledge_acquisitions a
                     ON a.id = p.acquisition_id WHERE p.id = ?""", (plan_id,)
            ).fetchone()
        return dict(row) if row else None

    def record_knowledge_import(self, plan_id: str, source_id: str) -> None:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT a.id, a.confirmed_plan_id FROM knowledge_import_plans p
                   JOIN knowledge_acquisitions a ON a.id = p.acquisition_id
                   WHERE p.id = ?""", (plan_id,),
            ).fetchone()
            if not row or (row["confirmed_plan_id"] and row["confirmed_plan_id"] != plan_id):
                raise PermissionError("Another import choice is already confirmed")
            connection.execute(
                """UPDATE knowledge_acquisitions
                   SET confirmed_plan_id = ?, imported_source_id = ? WHERE id = ?""",
                (plan_id, source_id, row["id"]),
            )

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
                """SELECT id, role, mode, content, model_mode, created_at
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
        self, thread_id: str, role: str, mode: str, content: str, model_mode: str | None = None
    ) -> dict:
        message_id = _id("message")
        created_at = _now()
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO conversation_messages
                   (id, thread_id, role, mode, content, model_mode, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (message_id, thread_id, role, mode, content, model_mode, created_at),
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

    def decide_action(self, action_id: str, decision: str) -> dict:
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
        return {"id": action_id, "decision": decision, "applied": decision == "confirmed"}

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
