"""Create a clearly separated, repeatable demonstration workspace."""

from __future__ import annotations

from datetime import date, timedelta

from .database import Database, _now
from .domain_records import DomainRecords
from .planner import build_variants


def seed_demo_workspace(store: Database) -> None:
    """Seed only an explicitly configured demo database, once."""
    today = date.today()
    existing_goals = store.goals()
    goals = existing_goals or [
        store.create_goal("Finish the local AI course", "learning"),
        store.create_goal("Keep evenings restorative", "life"),
        store.create_goal("Build a three-month buffer", "finance"),
    ]
    goal_ids = {goal["domain"]: goal["id"] for goal in goals}
    today_text = today.isoformat()
    for item in (() if store.daily_items(today_text) else (
        {"date": today_text, "title": "Review retrieval notes", "detail": "Turn three notes into questions.", "domain": "learning", "startTime": "09:30", "durationMinutes": 45, "constraintKind": "flexible", "repeatKind": "none", "protected": True, "goalId": goal_ids["learning"]},
        {"date": today_text, "title": "Lunch walk", "detail": "A short reset before the afternoon.", "domain": "life", "startTime": "12:30", "durationMinutes": 30, "constraintKind": "fixed", "repeatKind": "daily", "protected": True, "goalId": goal_ids["life"]},
        {"date": today_text, "title": "Weekly spending check", "detail": "Review groceries and subscriptions.", "domain": "finance", "startTime": "17:15", "durationMinutes": 25, "constraintKind": "flexible", "repeatKind": "weekly", "protected": False, "goalId": goal_ids["finance"]},
    )):
        store.create_daily_item(item)
    # The demo opens immediately before plan generation: goals and dated work are
    # populated, while the presenter still gets to demonstrate agent alternatives.
    with store.connect() as connection:
        current = connection.execute(
            "SELECT id FROM plan_sets WHERE plan_date = ?", (today_text,)
        ).fetchone()
        if current:
            connection.execute("DELETE FROM daily_confirmations WHERE plan_date = ?", (today_text,))
            connection.execute("DELETE FROM plan_sets WHERE id = ?", (current["id"],))

    domains = DomainRecords(store)
    learning = domains.snapshot("learning", today_text)
    if not learning["items"]:
        domains.add_learning_item("Local RAG foundations", "medium", 240)
        learning = domains.snapshot("learning", today_text)
    if not learning["sessions"]:
        domains.record_learning_session(today_text, learning["items"][0]["id"], 35, "done")
    life = domains.snapshot("life", today_text)
    if not life["habits"]:
        habit = domains.add_life_habit("Evening wind-down", "daily")
        domains.record_life_habit(today_text, habit["id"], True, "Screens off by 10:30.")
        domains.set_life_daily(today_text, 7.5, 4, 4,
                               "Good energy; keep the evening light.")
    finance = domains.snapshot("finance", today_text)
    if not finance["budgets"] and not finance["transactions"]:
        domains.set_opening_balance(275000)
        domains.record_transaction(today_text, "expense", 2850, "Learning",
                                   "Reference book")
        domains.set_budget(today_text[:7], "Learning", 12000)

    # Past plans are snapshots. Insert them directly so normal read-only rules remain intact.
    for offset in (1, 2, 4, 7):
        plan_date = (today - timedelta(days=offset)).isoformat()
        with store.connect() as connection:
            plan_set_id = store._seed_day(connection, plan_date, "demo-v1", build_variants())
            variant = connection.execute(
                "SELECT id FROM plan_variants WHERE plan_set_id = ? ORDER BY created_at LIMIT 1",
                (plan_set_id,),
            ).fetchone()
            connection.execute(
                "INSERT OR IGNORE INTO daily_confirmations (plan_date, variant_id, confirmed_at) VALUES (?, ?, ?)",
                (plan_date, variant["id"], _now()),
            )
            entries = connection.execute(
                "SELECT id FROM plan_entries WHERE variant_id = ? ORDER BY position", (variant["id"],)
            ).fetchall()
            for index, entry in enumerate(entries):
                status = "done" if index < max(1, len(entries) - 1) else ("partial" if offset == 2 else "skipped")
                connection.execute(
                    "UPDATE plan_entries SET completion_status = ? WHERE id = ?", (status, entry["id"])
                )
