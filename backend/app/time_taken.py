"""Real time taken: which task is current and which is next, and when each task actually ran.

Only the user marks a task done; DayWright records the time each took. The scheduled task whose time
covers now is current, and it runs past its set length until it gets a status, stopping at the next
scheduled task's or meal's start, and at DAY_END for the last. With no scheduled task running, the
first task without a start time is current, in the order the tasks were made. Nothing is current
during a meal or after DAY_END.

A task's time is one stretch: the last time it was current before its status was set. A scheduled
task's stretch starts at its planned start; one without a start time starts when it became current,
as the task before it got its status or a meal ended. One task's status never ends or changes another
task's time. When a task was never current before its status was set, it took its set length back
from then, starting no earlier than the task or meal before it stopped; a skip then took no time. A
task current since the day began, with no earlier stop to start from, starts when DayWright first saw
it current.

Every time here is the Mac's local "HH:MM" on the task's own day. Each task is a dict with:
"id"; "title"; "start", its planned start, or None for a task without a start time; "minutes", its set
length; "status", "planned" until the user reports it; "statusAt", when its status was set that day,
AFTER_DAY for a status set on a later day, or None for a status from before times were kept;
"createdAt", which orders tasks without a start time; "madeAt", when it was made on its own day,
AFTER_DAY for one made later, or None for one made before it; "currentSince", when DayWright first
saw it current, or None; and
"paused", true while its goal is paused.
"""

from __future__ import annotations

from typing import Iterable

from .meals import Meal
from .planner import DAY_END, clock_time, minutes_after_midnight

# A time after a task's own day ended: when it was reported or made on a later day.
AFTER_DAY = "24:00"
# The longest task name the menu bar shows whole; a longer one is cut to this many characters with "…".
NAME_CHARACTERS = 16
# The menu bar title's words, in the interface's two languages.
_TITLE_WORDS = {"en": {"minutes": "min", "next": "next: ", "nextAlone": "Next: "},
                "zh": {"minutes": "分钟", "next": "下一项：", "nextAlone": "下一项："}}

_DAY_END = minutes_after_midnight(DAY_END)


def _minute(clock: str) -> int:
    return minutes_after_midnight(clock)


def _open_at(task: dict, minute: int) -> bool:
    """Whether a task was still waiting for its status at `minute`. A status from before times were kept
    closes the task all day, as when it came isn't known; a paused task is never open."""
    if task.get("paused"):
        return False
    if task["status"] == "planned":
        return True
    return task["statusAt"] is not None and _minute(task["statusAt"]) > minute


def _cap(start: int, tasks: list[dict], meals: Iterable[Meal], own_id: str) -> int:
    """The first scheduled start or meal after `start`, else DAY_END: where a task begun then stops."""
    later = [_minute(other["start"]) for other in tasks
             if other["start"] and other["id"] != own_id and not other.get("paused") and _minute(other["start"]) > start]
    later += [_minute(meal.start) for meal in meals if _minute(meal.start) > start]
    return min([*later, _DAY_END])


def _occupant(tasks: list[dict], meals: tuple[Meal, ...], minute: int) -> dict | Meal | None:
    """What takes `minute`: the current task, a meal, or None when nothing does."""
    if minute >= _DAY_END:
        return None
    meal = next((meal for meal in meals if _minute(meal.start) <= minute < _minute(meal.start) + meal.minutes), None)
    if meal:
        return meal
    running = [task for task in tasks if task["start"] and _open_at(task, minute)
               and _minute(task["start"]) <= minute < _cap(_minute(task["start"]), tasks, meals, task["id"])]
    if running:
        return max(running, key=lambda task: task["start"])
    waiting = [task for task in tasks if not task["start"] and _open_at(task, minute)
               and (task.get("madeAt") is None or _minute(task["madeAt"]) <= minute)]
    return min(waiting, key=lambda task: task["createdAt"]) if waiting else None


def _current(tasks: list[dict], meals: tuple[Meal, ...], minute: int) -> dict | None:
    occupant = _occupant(tasks, meals, minute)
    return occupant if isinstance(occupant, dict) else None


def current_and_next(tasks: list[dict], meals: Iterable[Meal], now: str) -> tuple[dict | None, dict | None]:
    """Return the task current now and the one next, either None.

    Next is the next scheduled task still waiting, else the first other task without a start time.
    After DAY_END there is neither.
    """
    meals, minute = tuple(meals), _minute(now)
    if minute >= _DAY_END:
        return None, None
    current = _current(tasks, meals, minute)
    upcoming = sorted((task for task in tasks if task["start"] and _open_at(task, minute) and _minute(task["start"]) > minute),
                      key=lambda task: task["start"])
    if upcoming:
        return current, upcoming[0]
    waiting = sorted((task for task in tasks if not task["start"] and _open_at(task, minute) and task is not current),
                     key=lambda task: task["createdAt"])
    return current, waiting[0] if waiting else None


def _segments(task: dict, tasks: list[dict], meals: tuple[Meal, ...], until: int):
    """Yield each stretch of the day before `until` as (start, end, occupant), with `task` waiting for its
    status throughout. What takes the day changes only at these boundaries."""
    held = [{**other, "status": "planned", "statusAt": None} if other["id"] == task["id"] else other for other in tasks]
    marks = {0, _DAY_END, until}
    for other in held:
        for field in ("start", "statusAt", "madeAt"):
            if other.get(field):
                marks.add(_minute(other[field]))
    for meal in meals:
        marks.update((_minute(meal.start), _minute(meal.start) + meal.minutes))
    bounds = sorted(mark for mark in marks if mark <= until)
    for start, end in zip(bounds, bounds[1:]):
        yield start, end, _occupant(held, meals, start)


def _stretch(task: dict, tasks: list[dict], meals: tuple[Meal, ...], until: int) -> tuple[tuple[int, int] | None, int]:
    """Return the last stretch, as (start, end) minutes, in which `task` was current before `until`, or
    None; and when the task or meal before `until` last stopped, or 0."""
    last, stopped = None, 0
    for start, end, occupant in _segments(task, tasks, meals, until):
        if isinstance(occupant, dict) and occupant["id"] == task["id"]:
            last = (last[0], end) if last and last[1] == start else (start, end)
        elif occupant is not None and end < until:
            stopped = end
    return last, stopped


def actual_times(task: dict, tasks: list[dict], meals: Iterable[Meal], moment: str | None,
                 status: str = "done") -> tuple[str, str]:
    """Return when a task actually started and stopped, as "HH:MM", given the status set at `moment`.

    Args:
        task: One of `tasks`.
        tasks: Every task of its day, as the module describes them.
        meals: The day's meals.
        moment: When the status is set, or None (or AFTER_DAY) for a status set on a later day.
        status: The status set: a skip of a task never current took no time.
    """
    meals = tuple(meals)
    until = _minute(moment or AFTER_DAY)
    stretch, stopped = _stretch(task, tasks, meals, until)
    if stretch is None:
        end = min(until, _DAY_END)
        start = end if status == "skipped" else max(end - task["minutes"], stopped, 0)
        return clock_time(start), clock_time(end)
    start, end = stretch
    if start == 0 and not task["start"]:
        # Current since the day began: it started when DayWright first saw it, else it took its set length.
        seen = task.get("currentSince")
        start = _minute(seen) if seen and _minute(seen) < end else max(end - task["minutes"], 0)
    return clock_time(start), clock_time(end)


def stopped_unreported(task: dict, tasks: list[dict], meals: Iterable[Meal], moment: str | None) -> bool:
    """Whether a task stopped at the next task's or meal's start still waiting for its status, its status
    then set at `moment`, or None for none that day. A task stopped by DAY_END is "no reply" instead."""
    meals = tuple(meals)
    until = _minute(moment or AFTER_DAY)
    stretch, _ = _stretch(task, tasks, meals, until)
    return stretch is not None and stretch[1] < min(until, _DAY_END)


def taken_so_far(task: dict, tasks: list[dict], meals: Iterable[Meal], now: str) -> int:
    """Return the minutes the current task has run until `now`."""
    start, end = actual_times(task, tasks, meals, now)
    return _minute(end) - _minute(start)


def _short(title: str) -> str:
    return title if len(title) <= NAME_CHARACTERS else title[:NAME_CHARACTERS - 1].rstrip() + "…"


def title_line(current: dict | None, upcoming: dict | None, taken: int, language: str) -> str:
    """Return the menu bar's one line: the current task, its time taken and set time, and the next task.

    Args:
        current: The current task, or None.
        upcoming: The next task, or None.
        taken: The minutes the current task has run.
        language: "en" or "zh".

    Returns:
        Such as "Review · 32 / 60 min · next: Email Anna"; "Next: Email Anna" with no current task; or
        "" with neither, when the menu bar shows its icon alone.
    """
    words = _TITLE_WORDS[language]
    if current is None:
        return f"{words['nextAlone']}{_short(upcoming['title'])}" if upcoming else ""
    line = f"{_short(current['title'])} · {taken} / {current['minutes']} {words['minutes']}"
    return f"{line} · {words['next']}{_short(upcoming['title'])}" if upcoming else line
