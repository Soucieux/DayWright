"""Create a clearly separated, repeatable demonstration workspace."""

from __future__ import annotations

from datetime import date, timedelta

from .database import Database, _now
from .planner import build_variants


def seed_demo_workspace(store: Database) -> None:
    """Seed only an explicitly configured demo database, once."""
    today = date.today()
    existing_goals = store.goals()
    goals = existing_goals or [
        store.create_goal("Finish the local AI course", "learning"),
        store.create_goal("Keep evenings restorative", "life"),
        store.create_goal("Ship the onboarding guide", "project"),
    ]
    goal_ids = {goal["domain"]: goal["id"] for goal in goals}
    today_text = today.isoformat()
    for item in (() if store.daily_items(today_text) else (
        {"date": today_text, "title": "Review retrieval notes", "detail": "Turn three notes into questions.", "domain": "learning", "startTime": None, "durationMinutes": 45, "constraintKind": "flexible", "repeatKind": "none", "goalId": goal_ids["learning"]},
        {"date": today_text, "title": "Team stand-up", "detail": "Share yesterday's progress and today's focus.", "domain": "work", "startTime": "10:00", "durationMinutes": 30, "constraintKind": "fixed", "repeatKind": "daily", "goalId": None},
        {"date": today_text, "title": "Lunch walk", "detail": "A short reset before the afternoon.", "domain": "life", "startTime": "13:00", "durationMinutes": 30, "constraintKind": "fixed", "repeatKind": "daily", "goalId": goal_ids["life"]},
        {"date": today_text, "title": "Draft the onboarding guide", "detail": "Outline the first three sections.", "domain": "project", "startTime": None, "durationMinutes": 60, "constraintKind": "flexible", "repeatKind": "weekly", "goalId": goal_ids["project"]},
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

    if store.energy(today_text) is None:
        store.set_energy(today_text, 4)

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
