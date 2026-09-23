"""Explicit Learning, Life, and Money records beside the shared day-plan ledger."""

from __future__ import annotations

from datetime import date, datetime

from .database import Database, _id, _now, _writable_day, _writable_item_day
from .planner import PlanItem, has_collisions


class DomainRecords:
    """Keep domain reports local and distinct from confirmed plan snapshots."""

    def __init__(self, store: Database) -> None:
        self.store = store

    def snapshot(self, domain: str, selected_date: str) -> dict:
        """Return an area's catalog and selected-date records for one workbench screen."""
        with self.store.connect() as connection:
            if domain == "learning":
                items = [dict(row) for row in connection.execute(
                    "SELECT id, title, difficulty, estimated_minutes AS estimatedMinutes, status "
                    "FROM learning_items ORDER BY created_at, rowid")]
                sessions = [dict(row) for row in connection.execute(
                    """SELECT s.id, s.item_id AS itemId, i.title AS itemTitle,
                              s.session_date AS date, s.minutes, s.result
                       FROM learning_sessions s JOIN learning_items i ON i.id = s.item_id
                       WHERE s.session_date = ? ORDER BY s.created_at, s.rowid""",
                    (selected_date,))]
                return {"date": selected_date, "items": items, "sessions": sessions}
            if domain == "life":
                habits = [dict(row) for row in connection.execute(
                    "SELECT id, title, frequency, active FROM life_habits "
                    "ORDER BY created_at, rowid")]
                logs = [dict(row) for row in connection.execute(
                    """SELECT l.id, l.habit_id AS habitId, h.title AS habitTitle,
                              l.log_date AS date, l.done, l.note
                       FROM life_habit_logs l JOIN life_habits h ON h.id = l.habit_id
                       WHERE l.log_date = ? ORDER BY h.created_at, h.rowid""",
                    (selected_date,))]
                daily = connection.execute(
                    """SELECT daily_date AS date, sleep_hours AS sleepHours,
                              energy_level AS energyLevel, mood, note
                       FROM life_daily WHERE daily_date = ?""", (selected_date,)).fetchone()
                events = [dict(row) for row in connection.execute(
                    """SELECT e.id, e.item_id AS itemId, i.item_date AS date,
                              i.title, i.start_time AS startTime,
                              i.duration_minutes AS durationMinutes,
                              i.constraint_kind AS constraintKind, i.completion_status AS status,
                              e.category
                       FROM life_events e JOIN daily_items i ON i.id = e.item_id
                       WHERE i.item_date = ? ORDER BY i.start_time, e.rowid""",
                    (selected_date,))]
                return {"date": selected_date, "habits": habits, "logs": logs,
                        "daily": dict(daily) if daily else None, "events": events}
            if domain == "finance":
                account = connection.execute(
                    "SELECT opening_balance_cents FROM finance_account WHERE id = 1"
                ).fetchone()
                opening = account["opening_balance_cents"] if account else 0
                flow = connection.execute(
                    """SELECT COALESCE(SUM(CASE WHEN type = 'income' THEN amount_cents
                                               ELSE -amount_cents END), 0) AS net
                       FROM finance_transactions WHERE transaction_date <= ?""",
                    (selected_date,)).fetchone()["net"]
                transactions = [dict(row) for row in connection.execute(
                    """SELECT id, transaction_date AS date, type,
                              amount_cents AS amountCents, category, note
                       FROM finance_transactions WHERE transaction_date = ?
                       ORDER BY created_at, rowid""", (selected_date,))]
                budgets = [dict(row) for row in connection.execute(
                    """SELECT id, year_month AS month, category, budget_cents AS budgetCents
                       FROM finance_budgets WHERE year_month = ? ORDER BY category""",
                    (selected_date[:7],))]
                spent = {row["category"]: row["spent"] for row in connection.execute(
                    """SELECT category, SUM(amount_cents) AS spent
                       FROM finance_transactions WHERE type = 'expense'
                         AND substr(transaction_date, 1, 7) = ?
                       GROUP BY category""", (selected_date[:7],))}
                return {"date": selected_date, "openingBalanceCents": opening,
                        "balanceCents": opening + flow, "transactions": transactions,
                        "budgets": [{**budget, "spentCents": spent.get(budget["category"], 0)}
                                    for budget in budgets]}
        raise ValueError("Choose Learning, Life, or Money")

    def add_learning_item(self, title: str, difficulty: str, estimated_minutes: int) -> dict:
        """Create a learning subject without placing it on the calendar."""
        item_id = _id("learning")
        with self.store.connect() as connection:
            connection.execute(
                """INSERT INTO learning_items
                   (id, title, difficulty, estimated_minutes, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (item_id, title, difficulty, estimated_minutes, _now()),
            )
        return {"id": item_id, "title": title, "difficulty": difficulty,
                "estimatedMinutes": estimated_minutes, "status": "active"}

    def set_learning_status(self, item_id: str, status: str) -> dict:
        """Change a learning item's lifecycle without removing prior sessions."""
        with self.store.connect() as connection:
            updated = connection.execute(
                "UPDATE learning_items SET status = ? WHERE id = ?", (status, item_id)
            )
            if updated.rowcount != 1:
                raise ValueError("Learning item was not found")
        return {"id": item_id, "status": status}

    def record_learning_session(self, selected_date: str, item_id: str,
                                minutes: int, result: str) -> dict:
        """Record an explicit outcome for today's learning; no completion is inferred."""
        _writable_day(selected_date)
        session_id = _id("session")
        with self.store.connect() as connection:
            item = connection.execute(
                "SELECT title, status FROM learning_items WHERE id = ?", (item_id,)
            ).fetchone()
            if not item or item["status"] != "active":
                raise ValueError("Choose an active learning item")
            connection.execute(
                """INSERT INTO learning_sessions
                   (id, item_id, session_date, minutes, result, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (session_id, item_id, selected_date, minutes, result, _now()),
            )
        return {"id": session_id, "itemId": item_id, "itemTitle": item["title"],
                "date": selected_date, "minutes": minutes, "result": result}

    def add_life_habit(self, title: str, frequency: str) -> dict:
        """Create a habit definition; logging is a separate explicit daily action."""
        habit_id = _id("habit")
        with self.store.connect() as connection:
            connection.execute(
                """INSERT INTO life_habits (id, title, frequency, created_at)
                   VALUES (?, ?, ?, ?)""", (habit_id, title, frequency, _now()))
        return {"id": habit_id, "title": title, "frequency": frequency, "active": 1}

    def set_life_habit_active(self, habit_id: str, active: bool) -> dict:
        """Pause or resume a habit while retaining its recorded outcomes."""
        with self.store.connect() as connection:
            updated = connection.execute(
                "UPDATE life_habits SET active = ? WHERE id = ?", (int(active), habit_id)
            )
            if updated.rowcount != 1:
                raise ValueError("Habit was not found")
        return {"id": habit_id, "active": int(active)}

    def record_life_habit(self, selected_date: str, habit_id: str,
                          done: bool, note: str) -> dict:
        """Set today's habit outcome, replacing a same-day report without duplicates."""
        _writable_day(selected_date)
        with self.store.connect() as connection:
            habit = connection.execute(
                "SELECT title, active FROM life_habits WHERE id = ?", (habit_id,)
            ).fetchone()
            if not habit or not habit["active"]:
                raise ValueError("Choose an active habit")
            connection.execute(
                """INSERT INTO life_habit_logs
                   (id, habit_id, log_date, done, note, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(habit_id, log_date) DO UPDATE SET
                     done = excluded.done, note = excluded.note""",
                (_id("habit_log"), habit_id, selected_date, int(done), note, _now()),
            )
            row = connection.execute(
                "SELECT id FROM life_habit_logs WHERE habit_id = ? AND log_date = ?",
                (habit_id, selected_date),
            ).fetchone()
        return {"id": row["id"], "habitId": habit_id, "habitTitle": habit["title"],
                "date": selected_date, "done": int(done), "note": note}

    def set_life_daily(self, selected_date: str, sleep_hours: float | None,
                       energy_level: int | None, mood: int | None, note: str) -> dict:
        """Save today's reported sleep, energy, and mood without guessing them from a plan."""
        _writable_day(selected_date)
        with self.store.connect() as connection:
            connection.execute(
                """INSERT INTO life_daily
                   (daily_date, sleep_hours, energy_level, mood, note, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(daily_date) DO UPDATE SET
                     sleep_hours = excluded.sleep_hours,
                     energy_level = excluded.energy_level,
                     mood = excluded.mood, note = excluded.note,
                     updated_at = excluded.updated_at""",
                (selected_date, sleep_hours, energy_level, mood, note, _now()),
            )
        return {"date": selected_date, "sleepHours": sleep_hours,
                "energyLevel": energy_level, "mood": mood, "note": note}

    def add_life_event(self, selected_date: str, title: str, start: str, end: str,
                       category: str, flexible: bool) -> dict:
        """Create one timed Life event and its Calendar-owned item in the same transaction."""
        _writable_item_day(selected_date)
        beginning = datetime.strptime(start, "%H:%M")
        ending = datetime.strptime(end, "%H:%M")
        minutes = int((ending - beginning).total_seconds() / 60)
        if minutes <= 0:
            raise ValueError("End time must be after start time on the same date")
        item_id, event_id = _id("item"), _id("event")
        with self.store.connect() as connection:
            existing = [PlanItem(row["start_time"], row["title"], row["detail"],
                                 row["domain"], row["duration_minutes"],
                                 row["constraint_kind"])
                        for row in connection.execute(
                            """SELECT start_time, title, detail, domain, duration_minutes,
                                      constraint_kind FROM daily_items
                               WHERE item_date = ? AND acceptance = 'accepted'""",
                            (selected_date,))]
            if has_collisions((*existing, PlanItem(start, title, category, "life", minutes,
                                                  "flexible" if flexible else "fixed"))):
                raise ValueError("This event overlaps another timed record; adjust its time first")
            connection.execute(
                """INSERT INTO daily_items
                   (id, item_date, title, detail, domain, start_time, duration_minutes,
                    constraint_kind, created_at)
                   VALUES (?, ?, ?, ?, 'life', ?, ?, ?, ?)""",
                (item_id, selected_date, title, category, start, minutes,
                 "flexible" if flexible else "fixed", _now()),
            )
            connection.execute(
                "INSERT INTO life_events (id, item_id, category, created_at) VALUES (?, ?, ?, ?)",
                (event_id, item_id, category, _now()),
            )
        return {"id": event_id, "itemId": item_id, "date": selected_date,
                "title": title, "startTime": start, "durationMinutes": minutes,
                "constraintKind": "flexible" if flexible else "fixed", "category": category}

    def set_opening_balance(self, cents: int) -> dict:
        """Set the manual starting amount used with locally entered transactions."""
        with self.store.connect() as connection:
            connection.execute(
                """INSERT INTO finance_account (id, opening_balance_cents, updated_at)
                   VALUES (1, ?, ?) ON CONFLICT(id) DO UPDATE SET
                   opening_balance_cents = excluded.opening_balance_cents,
                   updated_at = excluded.updated_at""", (cents, _now()),
            )
        return {"openingBalanceCents": cents}

    def record_transaction(self, selected_date: str, kind: str, cents: int,
                           category: str, note: str) -> dict:
        """Record today's manual income or expense in integer cents."""
        _writable_day(selected_date)
        transaction_id = _id("transaction")
        with self.store.connect() as connection:
            connection.execute(
                """INSERT INTO finance_transactions
                   (id, transaction_date, type, amount_cents, category, note, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (transaction_id, selected_date, kind, cents, category, note, _now()),
            )
        return {"id": transaction_id, "date": selected_date, "type": kind,
                "amountCents": cents, "category": category, "note": note}

    def set_budget(self, month: str, category: str, cents: int) -> dict:
        """Save one current/future monthly category budget without touching transactions."""
        if month < date.today().isoformat()[:7]:
            raise PermissionError("Past month budgets are read-only")
        with self.store.connect() as connection:
            connection.execute(
                """INSERT INTO finance_budgets
                   (id, year_month, category, budget_cents, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(year_month, category) DO UPDATE SET
                     budget_cents = excluded.budget_cents,
                     updated_at = excluded.updated_at""",
                (_id("budget"), month, category, cents, _now()),
            )
            row = connection.execute(
                "SELECT id FROM finance_budgets WHERE year_month = ? AND category = ?",
                (month, category),
            ).fetchone()
        return {"id": row["id"], "month": month, "category": category,
                "budgetCents": cents}
