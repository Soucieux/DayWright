"""What an area agent knows about one of its tasks from every record of it, not a recent window.

A profile is built from each time the task was on a day the user recorded: its length that day, the
task's own length, its start, and what the user reported. The agents keep their profiles in the
database (see Database.rebuild_task_profiles), review from them, vote from them and report from
them what needs the user's attention.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from statistics import median
from typing import Iterable

from .planner import SLOT_MINUTES, clock_time, minutes_after_midnight

# The reports a profile keeps in order, newest last, to show how a task has gone lately.
RECENT_REPORTS = 6
# The latest reports a trend compares with the ones before them, and how many reports it needs.
TREND_WINDOW = 3
TREND_MIN_REPORTS = 4
# Done reports that show when a task is usually done, and how far apart their starts may lie.
DONE_TO_LEARN_TIME = 2
TIME_SPREAD_MINUTES = 120
# Done reports on one weekday that make it the task's usual day.
DONE_TO_LEARN_WEEKDAY = 2

_REPORTED = ("done", "partial", "skipped")


def _trend(reported: list[str]) -> str | None:
    """Say whether the latest TREND_WINDOW reports are worse, better or no different from the rest.

    Returns:
        "slipping" when most of the latest reports are unfinished after a mostly done start,
        "improving" when they are all done after a mostly unfinished start, "steady" otherwise,
        or None with fewer than TREND_MIN_REPORTS reports.
    """
    if len(reported) < TREND_MIN_REPORTS:
        return None
    latest, earlier = reported[-TREND_WINDOW:], reported[:-TREND_WINDOW]
    earlier_rate = earlier.count("done") / len(earlier)
    unfinished = sum(status != "done" for status in latest)
    if unfinished * 2 > len(latest) and earlier_rate >= 0.5:
        return "slipping"
    if not unfinished and earlier_rate < 0.5:
        return "improving"
    return "steady"


def _usual_start(starts: list[str]) -> str | None:
    """Return when a task is usually done, if its done reports started close together."""
    minutes = sorted(minutes_after_midnight(start) for start in starts)
    if len(minutes) < DONE_TO_LEARN_TIME or minutes[-1] - minutes[0] > TIME_SPREAD_MINUTES:
        return None
    return clock_time(round(median(minutes) / SLOT_MINUTES) * SLOT_MINUTES)


def _usual_weekday(days: list[str]) -> int | None:
    """Return the weekday, Monday 0, on which most of a task's done reports fall, if one stands out."""
    counts = Counter(date.fromisoformat(day).weekday() for day in days)
    if not counts:
        return None
    weekday, count = counts.most_common(1)[0]
    return weekday if count >= DONE_TO_LEARN_WEEKDAY and count * 2 >= len(days) else None


def _median_minutes(records: list[dict], status: str) -> int | None:
    """Return the median time a task took on the days it was reported with `status`, or None: each
    day's time taken, or its length that day when no time was kept. A time to check is left out."""
    lengths = [item["minutes"] if item.get("taken") is None else item["taken"]
               for item in records if item["status"] == status and not item.get("toCheck")]
    return round(median(lengths)) if lengths else None


def task_profile(records: Iterable[dict], shorten_requests: int = 0) -> dict:
    """Build what an area agent knows about a task from every record of it.

    Args:
        records: Each time the task was on a recorded day: its "date", its "start" or None, the
            "minutes" it had that day, the task's own length that day ("ownMinutes"), which differs
            when a set plan lengthened or shortened it, whether the user gave that length ("yours")
            rather than an agent estimating it, the "status" reported, the minutes it took
            ("taken", None when no time was kept or it is one to check) and whether its time is
            one to check ("toCheck").
        shorten_requests: How many times the user asked Ava to make it shorter.

    Returns:
        Its counts by status ("unreported" for a past record never reported: "Not done · no reply"),
        its latest reports ("recent"), its "trend" (see _trend), its usual and last length, the usual
        time it took on the days it was done ("doneMinutes") and partly done ("partialMinutes"; see
        _median_minutes), how often a plan
        "lengthened" or "shortened" it, how often you changed the length you gave it from one
        record to the next ("lengthChanges"), its "usualStart" and "usualWeekday" (Monday 0) when
        they stand out, its first and last date, and "shortenRequests".
    """
    records = sorted(records, key=lambda item: item["date"])
    reported = [item["status"] for item in records if item["status"] in _REPORTED]
    done = [item for item in records if item["status"] == "done"]
    yours = [item["ownMinutes"] for item in records if item["yours"]]
    return {
        "scheduled": len(records),
        **{status: reported.count(status) for status in _REPORTED},
        "unreported": len(records) - len(reported),
        "recent": reported[-RECENT_REPORTS:],
        "trend": _trend(reported),
        "usualMinutes": round(median(item["minutes"] for item in records)) if records else None,
        "doneMinutes": _median_minutes(records, "done"),
        "partialMinutes": _median_minutes(records, "partial"),
        "lastMinutes": records[-1]["minutes"] if records else None,
        "lengthened": sum(item["minutes"] > item["ownMinutes"] for item in records),
        "shortened": sum(item["minutes"] < item["ownMinutes"] for item in records),
        "lengthChanges": sum(before != after for before, after in zip(yours, yours[1:])),
        "usualStart": _usual_start([item["start"] for item in done if item["start"]]),
        "usualWeekday": _usual_weekday([item["date"] for item in done]),
        "firstDate": records[0]["date"] if records else None,
        "lastDate": records[-1]["date"] if records else None,
        "shortenRequests": shorten_requests,
    }
