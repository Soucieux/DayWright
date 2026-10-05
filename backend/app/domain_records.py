"""Each area's overview of a day, built from its tasks, goals and repeats, and Life's from the day's energy."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta

from .database import _GOAL_NOT_PAUSED, Database
from .planner import DAY_END, DAY_START, PlanItem, day_load, minutes_after_midnight

# Days with nothing done after which an active Learning goal is due for review, or a Project goal stalled.
IDLE_DAYS = 3
# How far back Work's carry-overs reach, in days.
CARRY_OVER_DAYS = 7
# The days a list over days covers: the day on show and the six after it, or it and the six before.
SPAN_DAYS = 7
# The reports that show some of a task was done.
_SOME_DONE = "completion_status IN ('done', 'partial')"


def _week_start(day: date) -> date:
    """The Monday of the week a day is in."""
    return day - timedelta(days=day.weekday())


def _days(first: date, count: int = SPAN_DAYS) -> list[str]:
    """The YYYY-MM-DD dates from `first` on, `count` of them."""
    return [(first + timedelta(days=offset)).isoformat() for offset in range(count)]


def _clock(minutes: int) -> str:
    """Minutes after midnight as "HH:MM"."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _merged(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Join stretches of time that overlap or touch, earliest first."""
    joined: list[tuple[int, int]] = []
    for start, end in sorted(span for span in spans if span[1] > span[0]):
        if joined and start <= joined[-1][1]:
            joined[-1] = (joined[-1][0], max(joined[-1][1], end))
        else:
            joined.append((start, end))
    return joined


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


def _idle_days(created_at: str, last_done: str | None, day: date) -> int:
    """Days by `day` since a goal's last task done or partly done, or since it was made when none was yet."""
    made = datetime.fromisoformat(created_at).astimezone().date()
    since = max(made, date.fromisoformat(last_done)) if last_done else made
    return (day - since).days


def _habit_day(when: str, status: str | None, today: str, in_rule: bool) -> str:
    """A habit's state on one day of its week grid.

    Args:
        when: The day, YYYY-MM-DD.
        status: Its copy's status, or None when the day has no copy.
        today: Today's date, before which a day still to do counts as missed.
        in_rule: Whether the repeat's rule has it on that day.

    Returns:
        "done", "partial", "missed" (skipped, or past and not done), "upcoming" (still to come) or
        "off" (the rule skips the day).
    """
    if status in ("done", "partial"):
        return status
    if status == "skipped":
        return "missed"
    if status is None and not in_rule:
        return "off"
    return "missed" if when < today else "upcoming"


class DomainRecords:
    """Read each area's overview from the user's tasks, goals and repeats; it keeps no records of its own."""

    def __init__(self, store: Database) -> None:
        self.store = store

    def snapshot(self, domain: str, selected_date: str, today: str | None = None) -> dict:
        """Return an area's overview of one day, with the figures its screen shows.

        The week is Monday to Sunday and holds `selected_date`; "done" counts tasks done or partly done.

        Learning: each Learning goal still open ("subjects") with its time planned and done this
        week, a practice state per day of the week, when it was last practised and its next session;
        the same time for tasks without a goal ("other"); time planned and done per day
        ("practice"); the last day anything was practised; and the goals due for review. Life: its
        repeats as habits, each with its rule, its first day, the day it stopped when that is this
        week, a state per day of the week, this week's count and its streak; the day's appointments
        (fixed Life tasks outside a repeat), meals, free time, its free windows between DAY_START and
        DAY_END around booked and meal time ("freeWindows"), energy, and the readings of the seven days to
        it ("energyWeek"). Work: the week's time planned and done by day and in all, the fixed Work
        tasks from the day on through the next six ("meetings"), and the carry-overs of the week
        before: tasks still to do or partly done, skipped ones left out, and those a set plan moved
        on. Project: each open Project goal's status, its steps (its tasks) and how many are done,
        its last step done and its next step, the goals that stalled, its tasks still to do from the
        day on through the next six ("nextSteps"), and those done in it and the six days before
        ("recentDone"), newest first.

        Args:
            domain: Learning, Life, Work or Project.
            selected_date: The day on show, YYYY-MM-DD.
            today: Today's date, before which a habit's day still to do counts as missed; the real
                today when not given.

        Raises:
            ValueError: For anything but Learning, Life, Work or Project.
        """
        day = date.fromisoformat(selected_date)
        week = _week_start(day)
        today = today or date.today().isoformat()
        base = {"date": selected_date, "weekStart": week.isoformat(), "weekEnd": (week + timedelta(days=6)).isoformat()}
        with self.store.connect() as connection:
            if domain == "learning":
                return {**base, **self._learning(connection, day, week)}
            if domain == "life":
                return {**base, **self._life(connection, day, week, today)}
            if domain == "work":
                return {**base, **self._work(connection, day, week)}
            if domain == "project":
                return {**base, **self._project(connection, day)}
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
            days = _idle_days(goal["created_at"], goal["last_done"], day)
            if days >= IDLE_DAYS:
                idle.append({"goalId": goal["id"], "title": goal["title"], "days": days, "lastDone": goal["last_done"]})
        return idle

    def _learning(self, connection: sqlite3.Connection, day: date, week: date) -> dict:
        """Learning's overview; see snapshot."""
        days = _days(week)
        rows = connection.execute(
            f"""SELECT goal_id, item_date, COALESCE(duration_minutes, 0) AS minutes, {_SOME_DONE} AS done
                FROM daily_items WHERE domain = 'learning' AND acceptance = 'accepted' AND item_date BETWEEN ? AND ?""",
            (days[0], days[-1])).fetchall()

        def figures(chosen: list[sqlite3.Row]) -> dict:
            return {"plannedMinutes": sum(row["minutes"] for row in chosen),
                    "doneMinutes": sum(row["minutes"] for row in chosen if row["done"])}

        def state(chosen: list[sqlite3.Row], when: str) -> str:
            on_day = [row for row in chosen if row["item_date"] == when]
            return "practised" if any(row["done"] for row in on_day) else "planned" if on_day else "none"

        subjects = []
        for goal in connection.execute(
                "SELECT id, title, status FROM goals WHERE domain = 'learning' AND status != 'completed' ORDER BY created_at, rowid"):
            mine = [row for row in rows if row["goal_id"] == goal["id"]]
            done = figures(mine)
            upcoming = connection.execute(
                """SELECT id, title, item_date AS date, start_time FROM daily_items WHERE goal_id = ? AND acceptance = 'accepted'
                   AND completion_status = 'planned' AND item_date >= ?
                   ORDER BY item_date, start_time IS NULL, start_time, rowid LIMIT 1""", (goal["id"], day.isoformat())).fetchone()
            subjects.append({
                "goalId": goal["id"], "title": goal["title"], "status": goal["status"], "minutes": done["doneMinutes"], **done,
                "days": [state(mine, when) for when in days],
                "lastPractised": connection.execute(
                    f"""SELECT MAX(item_date) FROM daily_items WHERE goal_id = ? AND acceptance = 'accepted' AND {_SOME_DONE}
                        AND item_date <= ?""", (goal["id"], day.isoformat())).fetchone()[0],
                "nextSession": dict(upcoming) if upcoming else None,
            })
        other = figures([row for row in rows if row["goal_id"] is None])
        return {
            "subjects": subjects,
            "otherMinutes": other["doneMinutes"],
            "other": other,
            "practice": [{"date": when, **figures([row for row in rows if row["item_date"] == when])} for when in days],
            "lastPractised": connection.execute(
                f"""SELECT MAX(item_date) FROM daily_items WHERE domain = 'learning' AND acceptance = 'accepted'
                    AND {_SOME_DONE} AND item_date <= ?""", (day.isoformat(),)).fetchone()[0],
            "dueForReview": self._idle(connection, "learning", day),
        }

    @staticmethod
    def _habits(connection: sqlite3.Connection, day: date, week: date, today: str) -> list[dict]:
        """Life's repeats as habits, each with its rule, its week grid, its count and its streak; see snapshot.

        A repeat stops from the day its stop holds, as Ava keeps it, or the day after its last copy
        when that copy no longer repeats, as the task form leaves it; one stopped before this week
        isn't listed.
        """
        on_day, days = day.isoformat(), _days(week)
        habits = []
        # Each series as its latest day up to `day` has it: SQLite takes the bare columns from MAX's row.
        for series in connection.execute(
                """SELECT repeat_series_id AS id, daily_items.id AS item_id, title, domain, repeat_kind, MAX(item_date) AS latest
                   FROM daily_items WHERE repeat_series_id IS NOT NULL AND acceptance = 'accepted' AND item_date <= ?
                   GROUP BY repeat_series_id ORDER BY title""", (on_day,)).fetchall():
            if series["domain"] != "life":
                continue
            rule = connection.execute("SELECT next_kind, next_from FROM repeat_series WHERE id = ?", (series["id"],)).fetchone()
            repeating = connection.execute(
                """SELECT item_date, repeat_kind FROM daily_items WHERE repeat_series_id = ? AND acceptance = 'accepted'
                   AND repeat_kind != 'none' AND item_date <= ? ORDER BY item_date DESC, rowid DESC LIMIT 1""",
                (series["id"], on_day)).fetchone()
            if not repeating:
                continue
            if rule and rule["next_kind"] == "none":
                stopped = rule["next_from"]
            elif series["repeat_kind"] == "none":
                stopped = (date.fromisoformat(series["latest"]) + timedelta(days=1)).isoformat()
            else:
                stopped = None
            if stopped and stopped < days[0]:
                continue
            switched = rule and rule["next_kind"] != "none" and rule["next_from"] <= on_day
            kind = rule["next_kind"] if switched else repeating["repeat_kind"]
            since = rule["next_from"] if switched else connection.execute(
                "SELECT MIN(item_date) FROM daily_items WHERE repeat_series_id = ? AND acceptance = 'accepted'",
                (series["id"],)).fetchone()[0]
            weekday = date.fromisoformat(since if switched else repeating["item_date"]).weekday() if kind == "weekly" else None
            copies = dict(connection.execute(
                """SELECT item_date, completion_status FROM daily_items WHERE repeat_series_id = ? AND acceptance = 'accepted'
                   AND item_date BETWEEN ? AND ?""", (series["id"], days[0], days[-1])).fetchall())
            weekly = kind == "weekly"
            done = {row[0] for row in connection.execute(
                """SELECT item_date FROM daily_items WHERE repeat_series_id = ? AND acceptance = 'accepted'
                   AND completion_status = 'done' AND item_date <= ?""", (series["id"], on_day))}
            reported = any(status != "planned" for when, status in copies.items()
                           if (week.isoformat() if weekly else on_day) <= when <= on_day)
            habits.append({
                "seriesId": series["id"], "title": series["title"], "itemId": series["item_id"], "itemDate": series["latest"],
                "kind": kind, "weekday": weekday, "since": since, "stoppedOn": stopped,
                "days": [_habit_day(when, copies.get(when), today,
                                    since <= when and not (stopped and when >= stopped)
                                    and (weekday is None or date.fromisoformat(when).weekday() == weekday))
                         for when in days],
                "doneThisWeek": sum(when >= days[0] for when in done),
                "streak": _streak(done, day, reported, weekly),
            })
        return habits

    @staticmethod
    def _free_windows(connection: sqlite3.Connection, on_day: str, meals: tuple) -> list[dict]:
        """The day's free windows between DAY_START and DAY_END, around its booked and meal time; see snapshot.

        Booked time is every timed task, in any area, and every entry of the day's set plan; a task
        paused with its goal is on hold and books nothing.
        """
        frame = (minutes_after_midnight(DAY_START), minutes_after_midnight(DAY_END))
        timed = connection.execute(
            f"""SELECT start_time, COALESCE(duration_minutes, 0) FROM daily_items WHERE item_date = ? AND acceptance = 'accepted'
                AND start_time IS NOT NULL AND {_GOAL_NOT_PAUSED}""", (on_day,)).fetchall()
        entries = connection.execute(
            """SELECT e.start_time, e.duration_minutes FROM plan_entries e
               JOIN plan_variants v ON v.id = e.variant_id JOIN plan_sets s ON s.id = v.plan_set_id
               JOIN daily_confirmations c ON c.plan_date = s.plan_date AND c.variant_id = v.id
               WHERE s.plan_date = ? AND e.start_time IS NOT NULL AND e.removed_at IS NULL AND e.moved_to IS NULL
                 AND NOT EXISTS (SELECT 1 FROM daily_items i JOIN goals g ON g.id = i.goal_id
                                 WHERE i.id = e.source_item_id AND g.status = 'paused')""", (on_day,)).fetchall()

        def clipped(start: str, minutes: int) -> tuple[int, int]:
            begin = minutes_after_midnight(start)
            return max(begin, frame[0]), min(begin + minutes, frame[1])

        taken = _merged([clipped(start, minutes) for start, minutes in [*timed, *entries]]
                        + [clipped(meal.start, meal.minutes) for meal in meals])
        windows, cursor = [], frame[0]
        for start, end in [*taken, (frame[1], frame[1])]:
            if start > cursor:
                windows.append({"start": _clock(cursor), "end": _clock(start), "minutes": start - cursor})
            cursor = max(cursor, end)
        return windows

    def _life(self, connection: sqlite3.Connection, day: date, week: date, today: str) -> dict:
        """Life's overview; see snapshot."""
        on_day = day.isoformat()
        tasks = connection.execute(
            f"""SELECT id, title, start_time, duration_minutes, constraint_kind, completion_status, repeat_series_id
                FROM daily_items WHERE domain = 'life' AND item_date = ? AND acceptance = 'accepted'
                AND {_GOAL_NOT_PAUSED} ORDER BY start_time IS NULL, start_time, rowid""", (on_day,)).fetchall()
        meals = self.store.day_meals(on_day)
        everything = connection.execute(
            f"""SELECT start_time, title, detail, domain, duration_minutes, constraint_kind FROM daily_items
                WHERE item_date = ? AND acceptance = 'accepted' AND {_GOAL_NOT_PAUSED}""", (on_day,)).fetchall()
        load = day_load([PlanItem(row["start_time"], row["title"], row["detail"], row["domain"], row["duration_minutes"],
                                  row["constraint_kind"]) for row in everything], meals=meals)
        readings = dict(connection.execute(
            "SELECT reading_date, level FROM energy_readings WHERE reading_date BETWEEN ? AND ?",
            ((day - timedelta(days=SPAN_DAYS - 1)).isoformat(), on_day)).fetchall())
        return {
            "habits": self._habits(connection, day, week, today),
            "appointments": [{"id": row["id"], "title": row["title"], "start_time": row["start_time"],
                              "duration_minutes": row["duration_minutes"], "completion_status": row["completion_status"]}
                             for row in tasks if row["constraint_kind"] == "fixed" and row["repeat_series_id"] is None],
            "meals": [{"title": meal.title, "start_time": meal.start, "duration_minutes": meal.minutes} for meal in meals],
            "freeMinutes": max(0, load["freeMinutes"] - load["taskMinutes"]),
            "freeWindows": self._free_windows(connection, on_day, meals),
            "energy": self.store.energy(on_day),
            "energyWeek": [{"date": when, "level": readings.get(when)}
                           for when in _days(day - timedelta(days=SPAN_DAYS - 1))],
        }

    @staticmethod
    def _work(connection: sqlite3.Connection, day: date, week: date) -> dict:
        """Work's overview; see snapshot."""
        days = _days(week)
        load = {row[0]: (row[1], row[2]) for row in connection.execute(
            f"""SELECT item_date, SUM(COALESCE(duration_minutes, 0)),
                       SUM(CASE WHEN {_SOME_DONE} THEN COALESCE(duration_minutes, 0) ELSE 0 END)
                FROM daily_items WHERE domain = 'work' AND acceptance = 'accepted' AND {_GOAL_NOT_PAUSED}
                AND item_date BETWEEN ? AND ? GROUP BY item_date""", (days[0], days[-1])).fetchall()}
        first, last = (day - timedelta(days=CARRY_OVER_DAYS)).isoformat(), (day - timedelta(days=1)).isoformat()
        moved = [{"id": row["source_item_id"], "title": row["title"], "date": row["plan_date"], "movedTo": row["moved_to"]}
                 for row in connection.execute(
                     """SELECT e.source_item_id, e.title, s.plan_date, e.moved_to FROM plan_entries e
                        JOIN plan_variants v ON v.id = e.variant_id JOIN plan_sets s ON s.id = v.plan_set_id
                        JOIN daily_confirmations c ON c.plan_date = s.plan_date AND c.variant_id = v.id
                        WHERE e.domain = 'work' AND e.moved_to IS NOT NULL AND s.plan_date BETWEEN ? AND ?""",
                     (first, last))]
        undone = [{"id": row["id"], "title": row["title"], "date": row["item_date"], "status": row["completion_status"]}
                  for row in connection.execute(
                      f"""SELECT id, title, item_date, completion_status FROM daily_items WHERE domain = 'work'
                          AND acceptance = 'accepted' AND completion_status IN ('planned', 'partial') AND {_GOAL_NOT_PAUSED}
                          AND item_date BETWEEN ? AND ?""", (first, last))]
        by_day = [{"date": when, "minutes": load.get(when, (0, 0))[0], "doneMinutes": load.get(when, (0, 0))[1]}
                  for when in days]
        ahead = _days(day)
        return {
            "load": by_day,
            "plannedMinutes": sum(entry["minutes"] for entry in by_day),
            "doneMinutes": sum(entry["doneMinutes"] for entry in by_day),
            "meetings": [dict(row) for row in connection.execute(
                f"""SELECT id, title, item_date AS date, start_time, duration_minutes, completion_status FROM daily_items
                    WHERE domain = 'work' AND item_date BETWEEN ? AND ? AND acceptance = 'accepted' AND constraint_kind = 'fixed'
                    AND {_GOAL_NOT_PAUSED} ORDER BY item_date, start_time, rowid""", (ahead[0], ahead[-1]))],
            "carryOvers": sorted([*moved, *undone], key=lambda item: (item["date"], item["title"])),
        }

    def _project(self, connection: sqlite3.Connection, day: date) -> dict:
        """Project's overview; see snapshot."""
        on_day = day.isoformat()
        projects = []
        for goal in connection.execute(
                f"""SELECT g.id, g.title, g.status, g.created_at,
                           (SELECT MAX(item_date) FROM daily_items WHERE goal_id = g.id AND item_date <= ?
                              AND acceptance = 'accepted' AND {_SOME_DONE}) AS last_done
                    FROM goals g WHERE g.domain = 'project' AND g.status != 'completed'
                    ORDER BY g.created_at, g.rowid""", (on_day,)).fetchall():
            steps = [dict(row) for row in connection.execute(
                """SELECT id, title, item_date AS date, completion_status AS status FROM daily_items
                   WHERE goal_id = ? AND acceptance = 'accepted' ORDER BY item_date, start_time IS NULL, start_time, rowid""",
                (goal["id"],))]
            idle = None if goal["status"] == "paused" else _idle_days(goal["created_at"], goal["last_done"], day)
            health = ("paused" if idle is None else "no-steps" if not steps
                      else "stalled" if idle >= IDLE_DAYS else "on-track")
            last = connection.execute(
                f"""SELECT title, item_date AS date FROM daily_items WHERE goal_id = ? AND acceptance = 'accepted'
                    AND {_SOME_DONE} AND item_date <= ?
                    ORDER BY item_date DESC, start_time DESC, rowid DESC LIMIT 1""", (goal["id"], on_day)).fetchone()
            upcoming = connection.execute(
                """SELECT id, title, item_date AS date FROM daily_items WHERE goal_id = ? AND acceptance = 'accepted'
                   AND completion_status IN ('planned', 'partial') AND item_date >= ?
                   ORDER BY item_date, start_time IS NULL, start_time, rowid LIMIT 1""", (goal["id"], on_day)).fetchone()
            projects.append({"goalId": goal["id"], "title": goal["title"], "status": goal["status"], "health": health,
                             "idleDays": idle, "done": sum(step["status"] in ("done", "partial") for step in steps),
                             "total": len(steps), "steps": steps,
                             "lastStep": dict(last) if last else None, "nextStep": dict(upcoming) if upcoming else None})
        steps = """SELECT i.id, i.title, i.item_date AS date, i.start_time, i.duration_minutes, i.completion_status, i.goal_id AS goalId,
                          g.title AS goalTitle
                   FROM daily_items i LEFT JOIN goals g ON g.id = i.goal_id
                   WHERE i.domain = 'project' AND i.acceptance = 'accepted' AND i.item_date BETWEEN ? AND ?"""
        return {
            "projects": projects,
            "stalled": self._idle(connection, "project", day),
            "nextSteps": [dict(row) for row in connection.execute(
                f"""{steps} AND i.completion_status = 'planned' AND (g.status IS NULL OR g.status != 'paused')
                    ORDER BY i.item_date, i.start_time IS NULL, i.start_time, i.rowid""",
                (on_day, (day + timedelta(days=SPAN_DAYS - 1)).isoformat()))],
            "recentDone": [dict(row) for row in connection.execute(
                f"""{steps} AND i.completion_status IN ('done', 'partial')
                    ORDER BY i.item_date DESC, i.start_time DESC, i.rowid DESC""",
                ((day - timedelta(days=SPAN_DAYS - 1)).isoformat(), on_day))],
        }
