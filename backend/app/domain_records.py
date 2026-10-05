"""Each area's overview of a day, built from its tasks, goals and repeats, and Life's from the day's energy."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta

from .database import _GOAL_NOT_PAUSED, Database
from .planner import PlanItem, day_load

# Days with nothing done after which an active Learning goal is due for review, or a Project goal stalled.
IDLE_DAYS = 3
# How far back Work's carry-overs reach, in days.
CARRY_OVER_DAYS = 7
# The reports that show some of a task was done.
_SOME_DONE = "completion_status IN ('done', 'partial')"


def _week_start(day: date) -> date:
    """The Monday of the week a day is in."""
    return day - timedelta(days=day.weekday())


def _streak(done: set[str], day: date, reported: bool, weekly: bool) -> int:
    """Count the repeat's days, or weeks for a weekly one, done in a row up to `day`.

    The day's own copy, or the week's, counts once done; still to do, it doesn't break the streak,
    which then runs from the day or week before.

    Args:
        done: The dates the repeat was done, as YYYY-MM-DD.
        day: The day the streak runs up to.
        reported: Whether the copy on `day`, or in its week, was reported other than done.
        weekly: Count weeks rather than days.
    """
    step = timedelta(days=7 if weekly else 1)
    marks = {_week_start(date.fromisoformat(when)) for when in done} if weekly else {date.fromisoformat(when) for when in done}
    cursor = _week_start(day) if weekly else day
    if cursor not in marks:
        if reported:
            return 0
        cursor -= step
    count = 0
    while cursor in marks:
        count, cursor = count + 1, cursor - step
    return count


class DomainRecords:
    """Read each area's overview from the user's tasks, goals and repeats; it keeps no records of its own."""

    def __init__(self, store: Database) -> None:
        self.store = store

    def snapshot(self, domain: str, selected_date: str) -> dict:
        """Return an area's overview of one day.

        Learning: each Learning goal still open with its time reported this week ("subjects"), the
        time reported without a goal ("otherMinutes"), the last day anything was practised, and
        the goals due for review. Life: its repeats as habits, the day's appointments (fixed Life
        tasks outside a repeat), meals, free time and energy. Work: the week's load by day, the
        day's meetings (fixed Work tasks) and the carry-overs of the week before: tasks still to do
        or partly done, skipped ones left out, and those a set plan moved on. Project: each
        open Project goal's progress, last step done and next step, and the goals that stalled.

        Raises:
            ValueError: For anything but Learning, Life, Work or Project.
        """
        day = date.fromisoformat(selected_date)
        week = _week_start(day)
        with self.store.connect() as connection:
            if domain == "learning":
                return {"date": selected_date, "weekStart": week.isoformat(), **self._learning(connection, day, week)}
            if domain == "life":
                return {"date": selected_date, "weekStart": week.isoformat(), **self._life(connection, day, week)}
            if domain == "work":
                return {"date": selected_date, "weekStart": week.isoformat(), **self._work(connection, day, week)}
            if domain == "project":
                return {"date": selected_date, "weekStart": week.isoformat(), **self._project(connection, day)}
        raise ValueError("Choose Learning, Life, Work, or Project")

    @staticmethod
    def _idle(connection: sqlite3.Connection, domain: str, day: date) -> list[dict]:
        """Return the area's active goals with nothing done for IDLE_DAYS or more by `day`.

        Days count from the last day any of the goal's tasks was done or partly done, or from the
        day the goal was made when none was yet. A paused or completed goal never counts.
        """
        idle = []
        for goal in connection.execute(
                f"""SELECT g.id, g.title, g.created_at,
                           (SELECT MAX(item_date) FROM daily_items WHERE goal_id = g.id AND item_date <= ?
                              AND acceptance = 'accepted' AND {_SOME_DONE}) AS last_done
                    FROM goals g WHERE g.domain = ? AND g.status = 'active' ORDER BY g.created_at, g.rowid""",
                (day.isoformat(), domain)).fetchall():
            made = datetime.fromisoformat(goal["created_at"]).astimezone().date()
            since = max(made, date.fromisoformat(goal["last_done"])) if goal["last_done"] else made
            if (day - since).days >= IDLE_DAYS:
                idle.append({"goalId": goal["id"], "title": goal["title"], "days": (day - since).days,
                             "lastDone": goal["last_done"]})
        return idle

    def _learning(self, connection: sqlite3.Connection, day: date, week: date) -> dict:
        """Learning's overview; see snapshot."""
        reported = (f"""SELECT COALESCE(SUM(duration_minutes), 0) FROM daily_items WHERE domain = 'learning'
                        AND acceptance = 'accepted' AND {_SOME_DONE} AND item_date BETWEEN ? AND ?""")
        span = (week.isoformat(), day.isoformat())
        subjects = [{"goalId": goal["id"], "title": goal["title"], "status": goal["status"],
                     "minutes": connection.execute(f"{reported} AND goal_id = ?", (*span, goal["id"])).fetchone()[0]}
                    for goal in connection.execute(
                        """SELECT id, title, status FROM goals WHERE domain = 'learning' AND status != 'completed'
                           ORDER BY created_at, rowid""")]
        return {
            "subjects": subjects,
            "otherMinutes": connection.execute(f"{reported} AND goal_id IS NULL", span).fetchone()[0],
            "lastPractised": connection.execute(
                f"""SELECT MAX(item_date) FROM daily_items WHERE domain = 'learning' AND acceptance = 'accepted'
                    AND {_SOME_DONE} AND item_date <= ?""", (day.isoformat(),)).fetchone()[0],
            "dueForReview": self._idle(connection, "learning", day),
        }

    def _life(self, connection: sqlite3.Connection, day: date, week: date) -> dict:
        """Life's overview; see snapshot."""
        today = day.isoformat()
        habits = []
        # Each series as its latest day up to `day` has it: SQLite takes the bare columns from MAX's row.
        for series in connection.execute(
                """SELECT repeat_series_id AS id, title, domain, repeat_kind, MAX(item_date) AS latest
                   FROM daily_items WHERE repeat_series_id IS NOT NULL AND acceptance = 'accepted' AND item_date <= ?
                   GROUP BY repeat_series_id ORDER BY title""", (today,)).fetchall():
            if series["domain"] != "life" or series["repeat_kind"] == "none":
                continue
            weekly = series["repeat_kind"] == "weekly"
            copies = connection.execute(
                """SELECT item_date, completion_status FROM daily_items WHERE repeat_series_id = ?
                   AND acceptance = 'accepted' AND item_date BETWEEN ? AND ?""",
                (series["id"], (week if weekly else day).isoformat(), today)).fetchall()
            done = {row[0] for row in connection.execute(
                """SELECT item_date FROM daily_items WHERE repeat_series_id = ? AND acceptance = 'accepted'
                   AND completion_status = 'done' AND item_date <= ?""", (series["id"], today))}
            habits.append({"seriesId": series["id"], "title": series["title"], "kind": series["repeat_kind"],
                           "doneThisWeek": sum(when >= week.isoformat() for when in done),
                           "streak": _streak(done, day, any(row[1] != "planned" for row in copies), weekly)})
        tasks = connection.execute(
            f"""SELECT id, title, start_time, duration_minutes, constraint_kind, completion_status, repeat_series_id
                FROM daily_items WHERE domain = 'life' AND item_date = ? AND acceptance = 'accepted'
                AND {_GOAL_NOT_PAUSED} ORDER BY start_time IS NULL, start_time, rowid""", (today,)).fetchall()
        meals = self.store.day_meals(today)
        everything = connection.execute(
            f"""SELECT start_time, title, detail, domain, duration_minutes, constraint_kind FROM daily_items
                WHERE item_date = ? AND acceptance = 'accepted' AND {_GOAL_NOT_PAUSED}""", (today,)).fetchall()
        load = day_load([PlanItem(row["start_time"], row["title"], row["detail"], row["domain"], row["duration_minutes"],
                                  row["constraint_kind"]) for row in everything], meals=meals)
        return {
            "habits": habits,
            "appointments": [{"id": row["id"], "title": row["title"], "start_time": row["start_time"],
                              "duration_minutes": row["duration_minutes"], "completion_status": row["completion_status"]}
                             for row in tasks if row["constraint_kind"] == "fixed" and row["repeat_series_id"] is None],
            "meals": [{"title": meal.title, "start_time": meal.start, "duration_minutes": meal.minutes} for meal in meals],
            "freeMinutes": max(0, load["freeMinutes"] - load["taskMinutes"]),
            "energy": self.store.energy(today),
        }

    @staticmethod
    def _work(connection: sqlite3.Connection, day: date, week: date) -> dict:
        """Work's overview; see snapshot."""
        load = dict(connection.execute(
            f"""SELECT item_date, SUM(duration_minutes) FROM daily_items WHERE domain = 'work'
                AND acceptance = 'accepted' AND {_GOAL_NOT_PAUSED} AND item_date BETWEEN ? AND ? GROUP BY item_date""",
            (week.isoformat(), (week + timedelta(days=6)).isoformat())).fetchall())
        first, last = (day - timedelta(days=CARRY_OVER_DAYS)).isoformat(), (day - timedelta(days=1)).isoformat()
        moved = [{"title": row["title"], "date": row["plan_date"], "movedTo": row["moved_to"]}
                 for row in connection.execute(
                     """SELECT e.title, s.plan_date, e.moved_to FROM plan_entries e
                        JOIN plan_variants v ON v.id = e.variant_id JOIN plan_sets s ON s.id = v.plan_set_id
                        JOIN daily_confirmations c ON c.plan_date = s.plan_date AND c.variant_id = v.id
                        WHERE e.domain = 'work' AND e.moved_to IS NOT NULL AND s.plan_date BETWEEN ? AND ?""",
                     (first, last))]
        undone = [{"id": row["id"], "title": row["title"], "date": row["item_date"], "status": row["completion_status"]}
                  for row in connection.execute(
                      f"""SELECT id, title, item_date, completion_status FROM daily_items WHERE domain = 'work'
                          AND acceptance = 'accepted' AND completion_status IN ('planned', 'partial') AND {_GOAL_NOT_PAUSED}
                          AND item_date BETWEEN ? AND ?""", (first, last))]
        return {
            "load": [{"date": when, "minutes": load.get(when, 0)}
                     for when in ((week + timedelta(days=offset)).isoformat() for offset in range(7))],
            "meetings": [dict(row) for row in connection.execute(
                """SELECT id, title, start_time, duration_minutes, completion_status FROM daily_items
                   WHERE domain = 'work' AND item_date = ? AND acceptance = 'accepted' AND constraint_kind = 'fixed'
                   ORDER BY start_time, rowid""", (day.isoformat(),))],
            "carryOvers": sorted([*moved, *undone], key=lambda item: (item["date"], item["title"])),
        }

    def _project(self, connection: sqlite3.Connection, day: date) -> dict:
        """Project's overview; see snapshot."""
        today = day.isoformat()
        projects = []
        for goal in connection.execute(
                """SELECT g.id, g.title, g.status, COUNT(i.id) AS total,
                          SUM(CASE WHEN i.completion_status = 'done' THEN 1 ELSE 0 END) AS done
                   FROM goals g LEFT JOIN daily_items i ON i.goal_id = g.id AND i.acceptance = 'accepted'
                   WHERE g.domain = 'project' AND g.status != 'completed'
                   GROUP BY g.id ORDER BY g.created_at, g.rowid""").fetchall():
            last = connection.execute(
                """SELECT title, item_date AS date FROM daily_items WHERE goal_id = ? AND acceptance = 'accepted'
                   AND completion_status = 'done' AND item_date <= ?
                   ORDER BY item_date DESC, start_time DESC, rowid DESC LIMIT 1""", (goal["id"], today)).fetchone()
            upcoming = connection.execute(
                """SELECT id, title, item_date AS date FROM daily_items WHERE goal_id = ? AND acceptance = 'accepted'
                   AND completion_status IN ('planned', 'partial') AND item_date >= ?
                   ORDER BY item_date, start_time IS NULL, start_time, rowid LIMIT 1""", (goal["id"], today)).fetchone()
            projects.append({"goalId": goal["id"], "title": goal["title"], "status": goal["status"],
                             "done": goal["done"] or 0, "total": goal["total"],
                             "lastStep": dict(last) if last else None, "nextStep": dict(upcoming) if upcoming else None})
        return {"projects": projects, "stalled": self._idle(connection, "project", day)}
