"""Real time taken: which task is current and which is next, and when each task actually ran.

Only the user marks a task done; DayWright records the time each took. Every task has a limit,
LIMIT_FACTOR times its length: the length the user set, or the estimate made when it was made. A
task with no status stops only at its limit, or at DAY_END, when the day ends. A scheduled task
reaching its start, or a meal, interrupts the current task; one interrupted with no status and under
its limit resumes when the interruption ends, and runs on until its limit. Which task is current, in
this order: a scheduled task that has started, with no status and under its limit, the latest started
of several; then the task interrupted most recently, with no status and under its limit; then the
first task without a start time, in the order the tasks were made, with no status and under its
limit. A task with a status, or at its limit, is never current again. Nothing is current during a
meal or after DAY_END.

A task's time adds up every stretch in which it was current before its status was set, each from
when it became current to where it stopped; its limit counts them all together. Its recorded times
are the first stretch's start and the last one's stop. One task's status never ends or changes
another task's time. When a task was never current before its status was set, it took its set length
back from then, starting no earlier than the task or meal before it stopped; a skip then took no
time. A stretch from when the day began, with no earlier stop to start from, counts from when
DayWright first saw the task current, toward its limit too; one DayWright didn't see counts only as
the task's one stretch, as its set length back from where it stopped, and never toward its limit.

The user may pause the day. While it is paused nothing is current and no time counts, toward any task or
any limit; the task current at the pause is interrupted then, as by a meal, and a status set meanwhile
keeps the time it had at the pause. On Resume a scheduled task whose planned time covers now is current,
else the task current at the pause continues if it has no status and is under its limit, else the usual
order applies. A scheduled task whose whole planned time fell inside a pause is never current that day.

Every time here is the Mac's local "HH:MM" on the task's own day. Each task is a dict with:
"id"; "title"; "start", its planned start, or None for a task without a start time; "minutes", its set
length; "status", "planned" until the user reports it; "statusAt", when its status was set that day,
AFTER_DAY for a status set on a later day, or None for a status from before times were kept;
"createdAt", which orders tasks without a start time; "madeAt", when it was made on its own day,
AFTER_DAY for one made later, or None for one made before it; "currentSince", when DayWright first
saw it current, or None; and
"paused", true while its goal is paused. Each of a day's pauses ("breaks") is a (start, end) pair, its
end None while the day is still paused.
"""

from __future__ import annotations

from typing import Iterable

from .meals import Meal
from .planner import DAY_END, clock_time, minutes_after_midnight

# A time after a task's own day ended: when it was reported or made on a later day.
AFTER_DAY = "24:00"
# A task's limit is this many times its length: with no status, it stops there.
LIMIT_FACTOR = 2
# The longest task name the menu bar shows whole; a longer one is cut to this many characters with "…".
NAME_CHARACTERS = 16
# The menu bar title's words, in the interface's two languages.
_TITLE_WORDS = {"en": {"minutes": "min", "next": "next: ", "nextAlone": "Next: ", "paused": "Paused since {time}"},
                "zh": {"minutes": "分钟", "next": "下一项：", "nextAlone": "下一项：", "paused": "{time} 起已暂停"}}

_DAY_END = minutes_after_midnight(DAY_END)


class _Paused:
    """What takes the day while it is paused: no task, and no time toward any."""


_PAUSED = _Paused()


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


def _limit(task: dict) -> float:
    """The minutes a task can be current in all before it stops at its limit; one with no length has none."""
    return LIMIT_FACTOR * task["minutes"] if task.get("minutes") else float("inf")


def _from_day_start(task: dict, began: int) -> bool:
    """Whether a stretch begun at minute `began` is one from when the day began: a task without a start
    time, made before its day, current from the first minute."""
    return began == 0 and not task["start"] and task.get("madeAt") is None


def _same(first: dict | Meal | None, second: dict | Meal | None) -> bool:
    if isinstance(first, dict) and isinstance(second, dict):
        return first["id"] == second["id"]
    return first is second


class _Day:
    """A day run from its first minute: what was current when, each task's minutes toward its limit, the
    tasks that reached it, and when each was last interrupted."""

    def __init__(self, tasks: list[dict], meals: tuple[Meal, ...], breaks: Iterable[tuple[str, str | None]] = ()):
        self.tasks, self.meals = tasks, meals
        # Each pause in minutes, one still under way lasting until the day ends.
        self.breaks = [(_minute(start), _minute(end) if end else _DAY_END) for start, end in breaks]
        self.used = {task["id"]: 0 for task in tasks}
        self.interrupted: dict[str, int] = {}
        self.limited: dict[str, int] = {}
        self.segments: list[tuple[int, int, dict | Meal | _Paused | None]] = []
        self._began: dict[str, int] = {}

    def paused_at(self, minute: int) -> tuple[int, int] | None:
        """The pause under way at `minute`, as (start, end) minutes, or None."""
        return next((pause for pause in self.breaks if pause[0] <= minute < pause[1]), None)

    def available(self, task: dict, minute: int) -> bool:
        """Whether a task can be current at `minute`: still without a status, under its limit, and not a
        scheduled task whose whole planned time fell inside a pause."""
        if task["start"]:
            start = _minute(task["start"])
            if any(begin <= start and start + (task["minutes"] or 0) <= end for begin, end in self.breaks):
                return False
        return _open_at(task, minute) and self.used[task["id"]] < _limit(task)

    def occupant(self, minute: int) -> dict | Meal | _Paused | None:
        """What takes `minute`: the day paused, a meal, the current task, or None when nothing does."""
        if minute >= _DAY_END:
            return None
        if self.paused_at(minute):
            return _PAUSED
        meal = next((meal for meal in self.meals if _minute(meal.start) <= minute < _minute(meal.start) + meal.minutes),
                    None)
        return meal or self._task(minute, None, made=True)

    def following(self, minute: int, current: dict | None) -> dict | None:
        """The task that would be current at `minute` if `current` ended then, a meal under way and when
        tasks were made aside."""
        return self._task(minute, current, made=False)

    def _task(self, minute: int, skip: dict | None, made: bool) -> dict | None:
        def candidate(task: dict) -> bool:
            return not _same(task, skip) and self.available(task, minute)

        started = [task for task in self.tasks if task["start"] and _minute(task["start"]) <= minute and candidate(task)]
        if started:
            return max(started, key=lambda task: task["start"])
        resumed = [task for task in self.tasks if task["id"] in self.interrupted and candidate(task)]
        if resumed:
            return max(resumed, key=lambda task: self.interrupted[task["id"]])
        waiting = [task for task in self.tasks if not task["start"] and candidate(task)
                   and (not made or task.get("madeAt") is None or _minute(task["madeAt"]) <= minute)]
        return min(waiting, key=lambda task: task["createdAt"]) if waiting else None

    def run(self, until: int) -> _Day:
        """Run the day up to minute `until`, or DAY_END if earlier; the occupant then is left to choose."""
        marks = {0, _DAY_END, until}
        for task in self.tasks:
            for field in ("start", "statusAt", "madeAt", "currentSince"):
                if task.get(field):
                    marks.add(_minute(task[field]))
        for meal in self.meals:
            marks.update((_minute(meal.start), _minute(meal.start) + meal.minutes))
        for pause in self.breaks:
            marks.update(pause)
        end = min(until, _DAY_END)
        bounds = sorted(mark for mark in marks if mark <= end)
        minute, previous = 0, None
        while minute < end:
            occupant = self.occupant(minute)
            self._hand_over(previous, occupant, minute)
            following = next(mark for mark in bounds if mark > minute)
            if isinstance(occupant, dict) and self._counts(occupant, minute):
                left = _limit(occupant) - self.used[occupant["id"]]
                following = int(min(following, minute + left))
                self.used[occupant["id"]] += following - minute
                if self.used[occupant["id"]] >= _limit(occupant):
                    self.limited[occupant["id"]] = following
            self._keep(minute, following, occupant)
            previous, minute = occupant, following
        self._hand_over(previous, self.occupant(minute), minute)
        return self

    def _hand_over(self, previous: dict | Meal | None, occupant: dict | Meal | None, minute: int) -> None:
        """Note, as what takes the day changes at `minute`, a task it interrupted and a stretch it began."""
        if _same(previous, occupant):
            return
        if isinstance(previous, dict) and self.available(previous, minute):
            self.interrupted[previous["id"]] = minute
        if isinstance(occupant, dict):
            self._began[occupant["id"]] = minute

    def _counts(self, task: dict, minute: int) -> bool:
        """Whether `minute` counts toward a task's limit: always, but in a stretch from when the day began,
        only once DayWright saw it current."""
        if not _from_day_start(task, self._began[task["id"]]):
            return True
        seen = task.get("currentSince")
        return seen is not None and _minute(seen) <= minute

    def _keep(self, start: int, end: int, occupant: dict | Meal | None) -> None:
        if self.segments and self.segments[-1][1] == start and _same(self.segments[-1][2], occupant):
            self.segments[-1] = (self.segments[-1][0], end, occupant)
        else:
            self.segments.append((start, end, occupant))

    def stretches(self, task: dict) -> list[tuple[int, int]]:
        """Every stretch, as (start, end) minutes in order, in which `task` was current."""
        return [(start, end) for start, end, occupant in self.segments
                if isinstance(occupant, dict) and occupant["id"] == task["id"]]

    def stopped(self, task: dict, until: int) -> int:
        """When the task or meal before `until`, other than `task`, last stopped, or 0."""
        return max((end for _, end, occupant in self.segments
                    if occupant is not None and not _same(occupant, task) and end < until), default=0)


def current_and_next(tasks: list[dict], meals: Iterable[Meal], now: str,
                     breaks: Iterable[tuple[str, str | None]] = ()) -> tuple[dict | None, dict | None]:
    """Return the task current now and the one next, either None; none is current while the day is paused.

    Next is the next scheduled task still to start, else the task that would be current if the current
    one ended now. After DAY_END there is neither.
    """
    meals, minute = tuple(meals), _minute(now)
    if minute >= _DAY_END:
        return None, None
    day = _Day(tasks, meals, breaks).run(minute)
    occupant = day.occupant(minute)
    current = occupant if isinstance(occupant, dict) else None
    upcoming = sorted((task for task in tasks if task["start"] and _minute(task["start"]) > minute
                       and day.available(task, minute)), key=lambda task: task["start"])
    return current, upcoming[0] if upcoming else day.following(minute, current)


def limit_stopped(tasks: list[dict], meals: Iterable[Meal], moment: str | None,
                  breaks: Iterable[tuple[str, str | None]] = ()) -> set[str]:
    """Return the ids of the tasks still without a status that stopped at their limit before `moment`, or
    None (or AFTER_DAY) for the whole day."""
    day = _Day(tasks, tuple(meals), breaks).run(_minute(moment or AFTER_DAY))
    return {task["id"] for task in tasks if task["status"] == "planned" and task["id"] in day.limited}


def _counted(task: dict, tasks: list[dict], meals: Iterable[Meal], moment: str | None,
             status: str, breaks: Iterable[tuple[str, str | None]]) -> list[tuple[int, int]]:
    """Return the stretches, as (start, end) minutes in order, that a task's time adds up, given the status
    set at `moment` (see actual_times): the day run with the task waiting for its status until then."""
    until = _minute(moment or AFTER_DAY)
    held = [{**other, "status": "planned", "statusAt": None} if other["id"] == task["id"] else other for other in tasks]
    day = _Day(held, tuple(meals), breaks).run(until)
    stretches = day.stretches(task)
    if not stretches:
        # A status set while the day is paused counts as set when the pause began.
        pause = day.paused_at(until)
        end = pause[0] if pause else min(until, _DAY_END)
        return [(end if status == "skipped" else max(end - (task["minutes"] or 0), day.stopped(task, until), 0), end)]
    return _kept(task, stretches)


def _kept(task: dict, stretches: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Return the stretches a task's time adds up, of those it was current in (see _counted)."""
    counted = []
    for start, end in stretches:
        if _from_day_start(task, start):
            # Current since the day began: from when DayWright first saw it current. Unseen then, the stretch
            # counts only as the task's one stretch, as its set length back from where it stopped.
            seen = task.get("currentSince")
            if seen and _minute(seen) < end:
                start = _minute(seen)
            elif len(stretches) > 1:
                continue
            else:
                start = max(end - (task["minutes"] or 0), 0)
        counted.append((start, end))
    return counted


def unanswered_minutes(tasks: list[dict], meals: Iterable[Meal], breaks: Iterable[tuple[str, str | None]] = ()) -> dict[str, int]:
    """Return, for each of a day's tasks still without a status once it ended, the minutes it was current:
    every stretch added up as a status would count them (see _counted), the day run once for them all. A
    task never current took none."""
    day = _Day(tasks, tuple(meals), breaks).run(_DAY_END)
    return {task["id"]: sum(end - start for start, end in _kept(task, day.stretches(task)))
            for task in tasks if task["status"] == "planned"}


def actual_times(task: dict, tasks: list[dict], meals: Iterable[Meal], moment: str | None,
                 status: str = "done", breaks: Iterable[tuple[str, str | None]] = ()) -> tuple[str, str]:
    """Return when a task actually started and last stopped, as "HH:MM", given the status set at `moment`:
    its first stretch's start and its last stretch's stop (see minutes_taken for the time it was current).

    Args:
        task: One of `tasks`.
        tasks: Every task of its day, as the module describes them.
        meals: The day's meals.
        moment: When the status is set, or None (or AFTER_DAY) for a status set on a later day.
        status: The status set: a skip of a task never current took no time.
        breaks: The day's pauses.
    """
    counted = _counted(task, tasks, meals, moment, status, breaks)
    return clock_time(counted[0][0]), clock_time(counted[-1][1])


def minutes_taken(task: dict, tasks: list[dict], meals: Iterable[Meal], moment: str | None,
                  status: str = "done", breaks: Iterable[tuple[str, str | None]] = ()) -> int:
    """Return the minutes a task took, given the status set at `moment`: every stretch it was current
    added up. The arguments are actual_times'."""
    return sum(end - start for start, end in _counted(task, tasks, meals, moment, status, breaks))


def taken_so_far(task: dict, tasks: list[dict], meals: Iterable[Meal], now: str,
                 breaks: Iterable[tuple[str, str | None]] = ()) -> int:
    """Return the minutes the current task has run until `now`, every stretch it was current added up."""
    return minutes_taken(task, tasks, meals, now, breaks=breaks)


def _short(title: str) -> str:
    return title if len(title) <= NAME_CHARACTERS else title[:NAME_CHARACTERS - 1].rstrip() + "…"


def title_line(current: dict | None, upcoming: dict | None, taken: int, language: str,
               paused_since: str | None = None) -> str:
    """Return the menu bar's one line: the current task, its time taken and set time, and the next task.

    Args:
        current: The current task, or None.
        upcoming: The next task, or None.
        taken: The minutes the current task has run.
        language: "en" or "zh".
        paused_since: When the day was paused, while it is.

    Returns:
        Such as "Review · 32 / 60 min · next: Email Anna"; "Next: Email Anna" with no current task;
        "Paused since 14:10" while the day is paused; or "" with neither, when the menu bar shows its icon alone.
    """
    words = _TITLE_WORDS[language]
    if paused_since:
        return words["paused"].format(time=paused_since)
    if current is None:
        return f"{words['nextAlone']}{_short(upcoming['title'])}" if upcoming else ""
    line = f"{_short(current['title'])} · {taken} / {current['minutes']} {words['minutes']}"
    return f"{line} · {words['next']}{_short(upcoming['title'])}" if upcoming else line
