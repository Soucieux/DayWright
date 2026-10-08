"""What the times you recorded show: the figures behind Calendar's Patterns tab, the area pages' planned
against actual, the Learn page's section pace and the line in a learning task.

Every figure comes from tasks as Database.pattern_records gives them, each a dict with: "date"; "title";
"domain"; "planned", the length its day gave it (a set plan's, else its own); "estimate", the length an
agent estimated for it, or None for one the user set; "status": "done", "partial", "skipped", "noReply"
(left without one once its day's DAY_END passed) or "dayPaused" (left so on a day that ended paused);
"minutes", the time it took, every stretch it was current added up, or None when that time is left out
(none was kept, it is from before times were kept, or it is one to check until confirmed); "statusAt",
when its status was set, "HH:MM" on its own day or AFTER_DAY on a later one; "end", when it last
stopped; and "series", its repeat's id, or None for a task that doesn't repeat.

Skipped tasks and those left without a status count toward time spent, never toward an estimate or
planned against actual; partly done ones are left out of planned against actual. A graph shows once its
own count reaches its threshold and is "still settling" until twice that (see gauge); the text that says
so, and every finding's words, are the interface's.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from statistics import mean

from .planner import DAY_END, minutes_after_midnight

DOMAINS = ("learning", "life", "work", "project")
# The parts Time by outcome stacks, from fully done at the base.
OUTCOMES = ("done", "partial", "skipped", "noReply", "dayPaused")
# When a status was set, as Reporting habit sorts them.
REPORTS = ("rightAway", "laterDay", "nextDay", "noReply")
# Each graph's threshold: fully done tasks with real times, per area, days with an estimated task fully done,
# days with time, sections ticked in timed tasks, days in one energy group, and days with statuses.
BEST_HOURS_TASKS = 10
PAIR_TASKS = 3
ESTIMATE_DAYS = 3
OUTCOME_DAYS = 2
PACE_SECTIONS = 2
ENERGY_DAYS = 3
REPORTING_DAYS = 3
# A graph is still settling from its threshold until this many times it.
SETTLING_FACTOR = 2
# Best hours: the steps its cells take, the hours a best window spans, and how far the busiest weekday must
# stand above the weekdays' average to be named.
HEAT_STEPS = 4
WINDOW_HOURS = 2
DAY_LEAD = 1.25
# Planned against actual, and energy, within this many percent read as close to plan.
CLOSE_PERCENT = 10
ENERGY_CLOSE_PERCENT = 5
# Estimates within this many minutes of before read as about the same.
SAME_GAP_MINUTES = 2
# Estimates go a column a week once their days span this many.
WEEKLY_AFTER_DAYS = 14
# A status set within this many minutes of its task stopping was set right away.
RIGHT_AWAY_MINUTES = 15
# Energy groups by the day's average: below each bound, the last taking the rest (1–2, 3, 4–5).
ENERGY_GROUPS = (("low", 2.5), ("middle", 3.5), ("high", None))
# The column each period's graphs draw: a day in a week, a week in a month, a month in all time.
COLUMN_KINDS = {"week": "day", "month": "week", "all": "month"}


def _round(value: float) -> int:
    """Round half up, as the figures show."""
    return math.floor(value + 0.5)


def gauge(count: int, threshold: int, unit: str, basis: int | None = None) -> dict:
    """How far a graph has come: "empty" with nothing, "few" below its threshold, "settling" from it until
    SETTLING_FACTOR times it, then "ready"; with its "count", "threshold", the "unit" counted ("tasks",
    "days" or "sections") and the "basis" its still-settling chip names, the count unless given."""
    state = ("empty" if count == 0 else "few" if count < threshold
             else "settling" if count < SETTLING_FACTOR * threshold else "ready")
    return {"state": state, "count": count, "threshold": threshold, "unit": unit, "basis": count if basis is None else basis}


def _column_spans(kind: str, start: str, end: str) -> list[tuple[date, date]]:
    """The spans from start to end, a day, a Monday week or a calendar month each, cut to the range."""
    cursor, last = date.fromisoformat(start), date.fromisoformat(end)
    spans = []
    while cursor <= last:
        if kind == "day":
            stop = cursor
        elif kind == "week":
            stop = cursor + timedelta(days=6 - cursor.weekday())
        else:
            stop = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        stop = min(stop, last)
        spans.append((cursor, stop))
        cursor = stop + timedelta(days=1)
    return spans


def _columns(kind: str, start: str, end: str) -> list[dict]:
    spans = _column_spans(kind, start, end)
    return [{"start": first.isoformat(), "end": stop.isoformat(), "kind": kind, "current": index == len(spans) - 1}
            for index, (first, stop) in enumerate(spans)]


def columns(period: str, start: str, end: str) -> list[dict]:
    """The columns a period's bars take (see COLUMN_KINDS), each its "start", "end", "kind", and whether it
    is the "current" one, the last, holding the day on show."""
    return _columns(COLUMN_KINDS[period], start, end)


def _in(column: dict, day: str) -> bool:
    return column["start"] <= day <= column["end"]


def _fully_done(records: list[dict]) -> list[dict]:
    """The fully done tasks whose time counts."""
    return [record for record in records if record["status"] == "done" and record["minutes"] is not None]


def best_hours(records: list[dict]) -> dict:
    """Best hours: fully done tasks by the weekday and hour they were finished.

    Returns:
        Its gauge (fully done tasks with real times); the "hours" on show, from the first used to the
        last; "cells", Monday first, each hour's tasks; "steps", each cell's of HEAT_STEPS split by the
        busiest cell (0 for none); the "key", each step's counts; the "best" hours, of the best windows
        on show; and the "finding": the WINDOW_HOURS window with the most finishes ("window", or
        "windows" when windows tie), with the busiest weekday unless the days are evenly spread, or
        "oneHour" when every finish was in one hour.
    """
    done = [record for record in _fully_done(records) if record["end"]]
    counts: dict[tuple[int, int], int] = {}
    for record in done:
        cell = (date.fromisoformat(record["date"]).weekday(), min(int(record["end"][:2]), 23))
        counts[cell] = counts.get(cell, 0) + 1
    measured = gauge(len(done), BEST_HOURS_TASKS, "tasks")
    if not done:
        return {**measured, "hours": [], "cells": [], "steps": [], "key": [], "best": [], "finding": None}
    used = [hour for _, hour in counts]
    hours = list(range(min(used), max(used) + 1))
    cells = [[counts.get((weekday, hour), 0) for hour in hours] for weekday in range(7)]
    most = max(max(row) for row in cells)

    def step(count: int) -> int:
        return math.ceil(count * HEAT_STEPS / most) if count else 0

    key = []
    for level in range(1, HEAT_STEPS + 1):
        counted = [count for count in range(1, most + 1) if step(count) == level]
        if counted:
            key.append({"step": level, "from": counted[0], "to": counted[-1]})
    steps = [[step(count) for count in row] for row in cells]
    by_hour = {hour: sum(row[index] for row in cells) for index, hour in enumerate(hours)}
    if len(hours) == 1:
        return {**measured, "hours": hours, "cells": cells, "steps": steps, "key": key, "best": hours,
                "finding": {"kind": "oneHour", "hour": hours[0]}}
    # A window starts at an hour with finishes, so a tie never names an hour nobody finished in.
    windows = {hour: sum(by_hour.get(hour + offset, 0) for offset in range(WINDOW_HOURS)) for hour in hours if by_hour[hour]}
    top = max(windows.values())
    chosen: list[int] = []
    for hour in sorted(windows):
        if windows[hour] == top and all(abs(hour - other) >= WINDOW_HOURS for other in chosen):
            chosen.append(hour)
    weekdays = [sum(row) for row in cells]
    busiest = max(weekdays)
    day = weekdays.index(busiest) if weekdays.count(busiest) == 1 and busiest >= DAY_LEAD * len(done) / 7 else None
    finding = ({"kind": "window", "from": chosen[0], "to": chosen[0] + WINDOW_HOURS, "day": day} if len(chosen) == 1
               else {"kind": "windows", "hours": chosen, "day": day})
    best = sorted({hour + offset for hour in chosen for offset in range(WINDOW_HOURS)} & set(hours))
    return {**measured, "hours": hours, "cells": cells, "steps": steps, "key": key, "best": best, "finding": finding}


def planned_actual(records: list[dict], by: str = "domain") -> dict:
    """Planned against actual: fully done tasks' average planned length beside the time they took, by area,
    or on an area page by repeating task.

    Args:
        by: "domain" for a row per area, in DOMAINS' order; "series" for a row per repeating task, by name.

    Returns:
        Its gauge (the most fully done tasks in a row; its basis, those in the rows drawn); the "rows",
        each its "key", "title" (a repeating task's latest name, else None), "domain", "count", and, from
        PAIR_TASKS on, its average "planned" and "actual" minutes and the "percent" over plan; and the
        "finding": by area, the row furthest "over" plan, else furthest "under", unless every row is within
        CLOSE_PERCENT ("close"); by repeating task, what the row furthest from plan "usual"ly takes.
    """
    done = [record for record in _fully_done(records) if record["planned"] and (by == "domain" or record["series"])]
    groups: dict[str, list[dict]] = {}
    for record in sorted(done, key=lambda record: record["date"]):
        groups.setdefault(record[by], []).append(record)
    order = ([domain for domain in DOMAINS if domain in groups] if by == "domain"
             else sorted(groups, key=lambda key: groups[key][-1]["title"].lower()))
    rows = []
    for key in order:
        group = groups[key]
        ready = len(group) >= PAIR_TASKS
        planned, taken = sum(record["planned"] for record in group), sum(record["minutes"] for record in group)
        rows.append({"key": key, "title": group[-1]["title"] if by == "series" else None, "domain": group[-1]["domain"],
                     "count": len(group), "planned": _round(planned / len(group)) if ready else None,
                     "actual": _round(taken / len(group)) if ready else None,
                     "percent": _round((taken - planned) / planned * 100) if ready else None})
    drawn = [row for row in rows if row["percent"] is not None]
    measured = gauge(max((row["count"] for row in rows), default=0), PAIR_TASKS, "tasks",
                     basis=sum(row["count"] for row in drawn))
    finding = None
    if drawn and by == "series":
        furthest = max(drawn, key=lambda row: abs(row["percent"]))
        finding = ({"kind": "usual", "key": furthest["key"], "title": furthest["title"], "actual": furthest["actual"],
                    "planned": furthest["planned"]} if abs(furthest["percent"]) > CLOSE_PERCENT else {"kind": "close"})
    elif drawn:
        over = [row for row in drawn if row["percent"] > CLOSE_PERCENT]
        under = [row for row in drawn if row["percent"] < -CLOSE_PERCENT]
        row = max(over, key=lambda row: row["percent"]) if over else min(under, key=lambda row: row["percent"]) if under else None
        finding = ({"kind": "over" if over else "under", "key": row["key"], "title": row["title"], "percent": row["percent"]}
                   if row else {"kind": "close"})
    return {**measured, "rows": rows, "finding": finding}


def estimates(records: list[dict], start: str, end: str) -> dict:
    """Estimates improving: how far the agents' estimates were from the real time of the tasks they
    estimated, once fully done; a length the user set never counts.

    Returns:
        Its gauge (days with such a task); "by", "day" until the days with one span WEEKLY_AFTER_DAYS,
        then "week"; the "columns", each its average gap in "minutes", or None with no such task (drawn
        as a dash, never a zero bar), and its "tasks"; and the "finding": the latest column with a gap set
        against the earliest, "spot" on, about the "same" (within SAME_GAP_MINUTES), "down" or "up", or
        "single" with one.
    """
    estimated = [record for record in _fully_done(records) if record["estimate"]]
    dates = sorted({record["date"] for record in estimated})
    spread = (date.fromisoformat(dates[-1]) - date.fromisoformat(dates[0])).days + 1 if dates else 0
    by = "week" if spread >= WEEKLY_AFTER_DAYS else "day"
    shown = _columns(by, start, end)
    for column in shown:
        gaps = [abs(record["minutes"] - record["estimate"]) for record in estimated if _in(column, record["date"])]
        column.update({"minutes": _round(mean(gaps)) if gaps else None, "tasks": len(gaps)})
    filled = [index for index, column in enumerate(shown) if column["minutes"] is not None]
    finding = None
    if len(filled) == 1:
        finding = {"kind": "single", "now": shown[filled[0]]["minutes"], "column": filled[0]}
    elif filled:
        now, before = shown[filled[-1]]["minutes"], shown[filled[0]]["minutes"]
        kind = "spot" if now == 0 else "same" if abs(now - before) <= SAME_GAP_MINUTES else "down" if now < before else "up"
        finding = {"kind": kind, "now": now, "before": before, "column": filled[-1], "beforeColumn": filled[0]}
    return {**gauge(len(dates), ESTIMATE_DAYS, "days"), "by": by, "columns": shown, "finding": finding}


def outcome(records: list[dict], shown: list[dict]) -> dict:
    """Time by outcome: the time tasks took, stacked by the status each got (see OUTCOMES).

    Returns:
        Its gauge (days with time); the "columns", each with its "parts" in minutes and their "total";
        the period's "totals"; the "busiest" column's total, which the columns are scaled to; and the
        "finding": fully done time's "share" of all, and the minutes left without a status ("noReply").
    """
    timed = [record for record in records if record["status"] in OUTCOMES and record["minutes"] is not None]
    drawn = []
    for column in shown:
        parts = {part: sum(record["minutes"] for record in timed if record["status"] == part and _in(column, record["date"]))
                 for part in OUTCOMES}
        drawn.append({**column, "parts": parts, "total": sum(parts.values())})
    totals = {part: sum(column["parts"][part] for column in drawn) for part in OUTCOMES}
    spent = sum(totals.values())
    days = {record["date"] for record in timed if record["minutes"]}
    return {**gauge(len(days), OUTCOME_DAYS, "days"), "columns": drawn, "totals": totals,
            "busiest": max((column["total"] for column in drawn), default=0),
            "finding": {"share": _round(totals["done"] / spent * 100), "noReply": totals["noReply"]} if spent else None}


def _energy_group(average: float) -> str:
    return next(name for name, bound in ENERGY_GROUPS if bound is None or average < bound)


def energy(records: list[dict], energy_days: list[dict]) -> dict:
    """Energy and real time: fully done tasks' real time against planned, by the day's average energy.

    Args:
        energy_days: Each day with energy reported, its "date" and "average" (see Database.energy_days).

    Returns:
        Its gauge (the most days in one group; its basis, the days in all); whether energy was "reported";
        the "groups" (see ENERGY_GROUPS), each its "days" and, from ENERGY_DAYS on, its "percent" over
        plan; the "focus", the group the finding is about; and the "finding": that group's tasks ran
        "longer" or "shorter", or energy "hardly" changes them (every group within ENERGY_CLOSE_PERCENT),
        or it was "never" reported.
    """
    averages = {day["date"]: day["average"] for day in energy_days}
    done = [record for record in _fully_done(records) if record["planned"] and record["date"] in averages]
    groups = []
    for name, _ in ENERGY_GROUPS:
        group = [record for record in done if _energy_group(averages[record["date"]]) == name]
        planned = sum(record["planned"] for record in group)
        days = len({record["date"] for record in group})
        groups.append({"group": name, "days": days,
                       "percent": _round((sum(record["minutes"] for record in group) - planned) / planned * 100)
                       if days >= ENERGY_DAYS else None})
    drawn = [group for group in groups if group["percent"] is not None]
    focus = max(drawn, key=lambda group: abs(group["percent"])) if drawn else None
    if not averages:
        finding = {"kind": "never"}
    elif focus is None:
        finding = None
    elif abs(focus["percent"]) <= ENERGY_CLOSE_PERCENT:
        finding, focus = {"kind": "hardly"}, None
    else:
        finding = {"kind": "longer" if focus["percent"] > 0 else "shorter", "group": focus["group"], "percent": focus["percent"]}
    measured = gauge(max(group["days"] for group in groups), ENERGY_DAYS, "days", basis=sum(group["days"] for group in groups))
    return {**measured, "reported": bool(averages), "groups": groups, "focus": focus and focus["group"], "finding": finding}


def _reported(record: dict) -> str | None:
    """When a task's status was set (see REPORTS), or None for one Reporting habit leaves out: still to
    report, from before times were kept, or left on a day that ended paused, which wasn't unanswered."""
    if record["status"] == "noReply":
        return "noReply"
    if record["status"] not in ("done", "partial", "skipped") or not record["statusAt"] or not record["end"]:
        return None
    if record["statusAt"] >= DAY_END:
        return "nextDay"
    waited = minutes_after_midnight(record["statusAt"]) - minutes_after_midnight(record["end"])
    return "rightAway" if waited <= RIGHT_AWAY_MINUTES else "laterDay"


def reporting(records: list[dict], shown: list[dict]) -> dict:
    """Reporting habit: when statuses were set (see REPORTS): "right away" while the task was current or
    within RIGHT_AWAY_MINUTES of it stopping, "later that day" before DAY_END, on a "next day" (a later day,
    or once the day had ended), or never ("noReply").

    Returns:
        Its gauge (days with statuses); the "columns", each its "counts", their "shares" in percent and
        their "total"; the period's "totals"; and the "finding": the latest column's share set right away
        ("now") against the earliest's ("before", None with one column), and the tasks with "noReply".
    """
    sorted_out = [(record, _reported(record)) for record in records]
    sorted_out = [(record, when) for record, when in sorted_out if when]
    drawn = []
    for column in shown:
        counts = {when: sum(1 for record, kind in sorted_out if kind == when and _in(column, record["date"])) for when in REPORTS}
        total = sum(counts.values())
        drawn.append({**column, "counts": counts, "total": total,
                      "shares": {when: _round(count / total * 100) if total else 0 for when, count in counts.items()}})
    totals = {when: sum(column["counts"][when] for column in drawn) for when in REPORTS}
    filled = [index for index, column in enumerate(drawn) if column["total"]]
    finding = None
    if filled:
        earliest = filled[0] if len(filled) > 1 else None
        finding = {"now": drawn[filled[-1]]["shares"]["rightAway"],
                   "before": drawn[earliest]["shares"]["rightAway"] if earliest is not None else None,
                   "column": filled[-1], "beforeColumn": earliest, "noReply": totals["noReply"]}
    days = {record["date"] for record, _ in sorted_out}
    return {**gauge(len(days), REPORTING_DAYS, "days"), "columns": drawn, "totals": totals, "finding": finding}


def _paces(tasks: list[dict]) -> dict[str, dict]:
    """Each source's minutes and sections, from its learning tasks that ticked any and kept a time."""
    paces: dict[str, dict] = {}
    for task in tasks:
        if task["sections"] and task["minutes"] is not None:
            pace = paces.setdefault(task["sourceId"], {"title": task["sourceTitle"], "minutes": 0, "sections": 0})
            pace["minutes"] += task["minutes"]
            pace["sections"] += task["sections"]
    return paces


def source_pace(tasks: list[dict], source_id: str | None) -> dict | None:
    """How long one source's checklist sections take, as a learning task's line reads it: its "minutes"
    a section and the "sections" that rests on, or None below PACE_SECTIONS."""
    pace = _paces(tasks).get(source_id)
    if not pace or pace["sections"] < PACE_SECTIONS:
        return None
    return {"minutes": _round(pace["minutes"] / pace["sections"]), "sections": pace["sections"]}


def section_pace(tasks: list[dict]) -> dict:
    """Section pace: the time learning tasks took for each checklist section ticked on them, by source.

    Args:
        tasks: Learning tasks with a source and a status, each its "sourceId", "sourceTitle", the
            "minutes" it took (None when left out) and the "sections" ticked on it.

    Returns:
        Its gauge (the most sections ticked in timed tasks of one source); the "rows", by name, each
        source from PACE_SECTIONS on with its "minutes" a section and "sections"; and the "finding":
        the "fastest" source, or the "one" source there is.
    """
    paces = _paces(tasks)
    rows = sorted(({"sourceId": source_id, "title": pace["title"], "minutes": _round(pace["minutes"] / pace["sections"]),
                    "sections": pace["sections"]} for source_id, pace in paces.items() if pace["sections"] >= PACE_SECTIONS),
                  key=lambda row: row["title"].lower())
    finding = None
    if rows:
        fastest = min(rows, key=lambda row: row["minutes"])
        finding = {"kind": "fastest" if len(rows) > 1 else "one", "sourceId": fastest["sourceId"], "title": fastest["title"],
                   "minutes": fastest["minutes"]}
    return {**gauge(max((pace["sections"] for pace in paces.values()), default=0), PACE_SECTIONS, "sections"),
            "rows": rows, "finding": finding}


def tab(records: list[dict], energy_days: list[dict], period: str, start: str, end: str, to_check: int) -> dict:
    """Everything Calendar's Patterns tab shows for a period from start to end: its "columns", the times
    "toCheck" left out of it, and each graph."""
    shown = columns(period, start, end)
    return {"period": period, "start": start, "end": end, "columns": shown, "toCheck": to_check,
            "bestHours": best_hours(records), "energy": energy(records, energy_days),
            "plannedActual": planned_actual(records), "estimates": estimates(records, start, end),
            "outcome": outcome(records, shown), "reporting": reporting(records, shown)}
