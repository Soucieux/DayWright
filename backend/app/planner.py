from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from itertools import zip_longest
from typing import Callable, Iterable

from .meals import DEFAULT_MEALS, KEPT_ESTIMATE_MINUTES, Meal


DOMAIN_LABELS = {
    "learning": "Learn",
    "life": "Life",
    "work": "Work",
    "project": "Project",
}

# Plans never shorten a length the user set; a length an area agent estimated may lose
# ADJUST_MINUTES at a time, but never drops below this.
MIN_TRIMMED_MINUTES = 15
ADJUST_MINUTES = 15
# The part of the day plans place tasks in. A task the user fixed outside it stays where it is.
DAY_START = "09:00"
DAY_END = "22:00"
# Placed tasks start on this grid of minutes.
SLOT_MINUTES = 15
# Every plan keeps lunch and dinner free at the day's own times (see meals.py); no task may be fixed over
# them. A meal that is over, or that a task fixed earlier already takes, is left out of the plan.
# Lunch and dinner at their default times, for a caller that names no day's own.
USUAL_MEALS = tuple(DEFAULT_MEALS.values())
# The constraint a plan's meal carries, which tells it from the user's tasks.
MEAL = "meal"
# The areas' importance, highest first, which orders tasks whenever nothing else decides.
AREA_PRIORITY = ("work", "project", "life", "learning")
# The areas whose tasks Deep focus keeps together, in priority order.
FOCUS_AREAS = ("work", "project", "learning")
# Lighter day starts placing later, eases in with life tasks, and leaves a breather after each.
GENTLE_START = "10:00"
GENTLE_BREAK_MINUTES = 15
GENTLE_ORDER = ("life", "work", "project", "learning")
# Where a study task's effort places it, by the day's energy (see _study_ranked).
_STUDY_RANKS = {"normal": {"light": 1}, "high": {"deep": -1, "light": 1}, "low": {"light": -1, "deep": 1}}

# Every kind of plan, by the slug it is stored under, with its name.
PLAN_KINDS = {
    "balanced": "Balanced", "focused": "Deep focus", "gentle": "Lighter day", "early": "Finish early",
    "quickwins": "Quick wins first", "easiest": "Easiest first", "rhythm": "Your usual rhythm",
    "spacious": "Breathing room",
}
# The order the kinds beside Balanced are offered in when the user's choices don't rank them.
DEFAULT_RANK = ("focused", "rhythm", "early", "quickwins", "easiest", "spacious", "gentle")
# The everyday plans beside Balanced: offered on any day, and first on a day with few tasks.
EVERYDAY = ("focused", "gentle")
# With fewer tasks than this to place, a day offers the everyday plans first.
FEW_TASKS = 3
# Tasks without a start time that need at least this percentage of the day's free time make a full day.
FULL_DAY_PERCENT = 70
# Finish early is offered only when it ends at least this much sooner than Balanced.
EARLIER_BY_MINUTES = 30
# A task this short or shorter counts as a quick win.
QUICK_TASK_MINUTES = 30
# Breathing room leaves at least, and at most, this long between tasks.
SPACIOUS_MIN_GAP = 30
SPACIOUS_MAX_GAP = 60
# Easiest first is offered when the finish rates of the day's tasks differ by at least this much.
EASIEST_SPREAD = 0.25
# Two plans differ clearly when their tasks come in another order and move at least this many
# minutes in all, or when one is done at least this much sooner than the other.
DISTINCT_MINUTES = 60

# What a plan's rationale says, by the key the interface words it under in each language. A plan
# beside Balanced first says why it was suggested ("planWhy…"), then what sets it apart
# ("planDoes…"). A value named `tasks` is a list of task titles.
NOTES = {
    "planWhyLighterAdvised": "Listed first because the Life agent advised a lighter day.",
    "planWhyHighEnergy": "Listed first because your energy today averages 4 or above.",
    "planWhyFull": "Suggested because your tasks fill most of your free time.",
    "planWhyEveryday": "Suggested because it is one of the everyday plans.",
    "planWhyFocus": "Suggested because you have {count} work, project, and learning tasks to keep together.",
    "planWhyEarly": "Suggested because filling the gaps finishes {minutes} minutes sooner than Balanced.",
    "planWhyQuick": "Suggested because {count} of your tasks take 30 minutes or less.",
    "planWhyEasiest": "Suggested because your reports show which tasks you usually finish.",
    "planWhyRhythm": "Suggested because your reports show you do some tasks at a steady time of day.",
    "planWhySpacious": "Suggested because your tasks fill less than half of your free time.",
    "planWhyAlternative": "Suggested as another way to arrange the same tasks.",
    # The Orchestrator's own reason, written by the local model in English (`en`) and Chinese (`zh`).
    "planWhyAgent": "{en}",
    # Chosen from the area agents' votes: the agents' keys (`agents`) and their names in English (`names`).
    "planWhyVotes": "The area agents' votes put it here: {names}.",
    "planDoesBalanced": ("Takes the areas in turn by priority, work, project, life, then learning, from {start}, "
                         "with no gaps between tasks."),
    "planDoesFocus": ("Keeps {tasks} back to back in the longest free stretch of the day, {start}–{end}, with "
                      "nothing in between; life tasks fit around them."),
    "planDoesFocusOne": ("Gives {tasks} the longest free stretch of the day, from {start}, so nothing interrupts "
                         "it; life tasks fit around it."),
    "planDoesGentle": ("Places nothing before {start}, eases in with “{first}”, and leaves 15 minutes after "
                       "every task."),
    "planDoesGentleTrim": "Trims the estimated length of “{title}” from {from} to {to} minutes.",
    "planDoesGentleTrimAll": "Trims each of the {count} estimated lengths by 15 minutes, never below 15.",
    "planDoesEarly": "Fills the gaps between your fixed times as fully as possible, so the day is done by {end}.",
    "planDoesQuick": "Does {tasks} first, shortest first, then the longer tasks.",
    "planDoesEasiest": ("Starts with “{usual}”, which you usually finish, and leaves “{often}”, which you often "
                        "don't, for last."),
    "planDoesRhythm": ("Places “{title}” at {time}, when you usually do it; the rest follow your priorities "
                       "around it."),
    "planDoesRhythmAfter": ("Places “{title}” at {time}, the first free time after {usual}, when you usually do "
                            "it; the rest follow your priorities around it."),
    "planDoesRhythmMany": ("Places {tasks} near the times you usually do them; the rest follow your "
                           "priorities around them."),
    "planDoesSpacious": "Leaves {gap} minutes between tasks so the day has room to breathe; done by {end}.",
}


@dataclass(frozen=True)
class StudyTask:
    """A Learning task made from a Library source, as plans weigh it: what its text says about studying
    it, the sections it covers, its place in its goal when it is in one, and, for the day being planned,
    where its effort puts it (see _study_order)."""

    effort: str
    goal: str | None = None
    position: int = 0
    count: int = 0
    goal_title: str | None = None
    hands_on: bool = False
    briefing: str | None = None
    sections: tuple[str, ...] = ()
    # -1 placed before every other task, 1 after them all, 0 where the kind of plan puts it.
    rank: int = 0


@dataclass(frozen=True)
class PlanItem:
    start: str | None
    title: str
    detail: str
    domain: str
    duration_minutes: int
    constraint: str = "flexible"
    item_id: str | None = None
    # Whether an area agent estimated the length; only an estimated length may be shortened.
    estimated: bool = False
    # What it studies, for a Learning task made from a source.
    study: StudyTask | None = None


BASE_PLAN = (
    PlanItem("08:00", "French listening", "Podcast + notes (Beginner A2)", "learning", 60),
    PlanItem("09:00", "Deep work — Course project", "Build section 2 and write notes", "learning", 90),
    PlanItem("10:30", "Strength session", "Gym · Full body", "life", 60, "fixed"),
    PlanItem("11:30", "Shower & clear inbox", "Tidy up and prep for afternoon", "life", 30),
    PlanItem("12:00", "Lunch", "Good food, short walk", "life", 60),
    PlanItem("13:00", "Weekly report", "Summarize progress for the team", "work", 45),
    PlanItem("14:00", "Open buffer", "Use for catch-up or personal task", "life", 90),
    PlanItem("15:30", "Course project", "Continue build + polish", "project", 90),
    PlanItem("17:00", "Prepare for call", "Review notes and agenda", "work", 30),
    PlanItem("17:30", "Call with Alex", "Project sync", "work", 60, "fixed"),
    PlanItem("18:30", "Evening reset", "Journal, plan tomorrow, wind down", "life", 30),
)


def _move(items: Iterable[PlanItem], target_title: str, **changes: object) -> tuple[PlanItem, ...]:
    return tuple(replace(item, **changes) if item.title == target_title else item for item in items)


def build_variants() -> tuple[dict, ...]:
    balanced = BASE_PLAN

    focused = _move(BASE_PLAN, "Open buffer", domain="learning", title="Focused build block", detail="Finish the hardest course milestone")
    focused = _move(focused, "Course project", duration_minutes=75)

    gentle = _move(BASE_PLAN, "Deep work — Course project", duration_minutes=60, detail="One clear milestone, then stop")
    gentle = _move(gentle, "Open buffer", title="Recovery buffer", detail="Walk, errands, or unplanned needs", duration_minutes=120)
    gentle = _move(
        gentle,
        "Course project",
        start="16:00",
        title="Light course review",
        detail="Review notes; no new build work",
        duration_minutes=60,
    )

    return (
        {"name": "Balanced", "slug": "balanced", "rationale": "Steady progress across learning, life, work, and project with a protected buffer.", "items": balanced},
        {"name": "Focused", "slug": "focused", "rationale": "Uses the open buffer for the course milestone while preserving fixed commitments.", "items": focused},
        {"name": "Gentle", "slug": "gentle", "rationale": "Shortens deep work and protects more recovery time for a lower-energy day.", "items": gentle},
    )


def minutes_after_midnight(clock: str) -> int:
    """Return minutes after midnight for an "HH:MM" time."""
    hours, minutes = clock.split(":")
    return int(hours) * 60 + int(minutes)


def clock_time(minutes: int) -> str:
    """Return the "HH:MM" time `minutes` after midnight."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _next_slot(minutes: int) -> int:
    """Round minutes after midnight up to the next start on the placement grid."""
    return -(-minutes // SLOT_MINUTES) * SLOT_MINUTES


def _shorter(item: PlanItem) -> PlanItem:
    """Return the task with ADJUST_MINUTES fewer minutes, never fewer than MIN_TRIMMED_MINUTES."""
    return replace(item, duration_minutes=max(MIN_TRIMMED_MINUTES, item.duration_minutes - ADJUST_MINUTES))


def _priority(item: PlanItem) -> int:
    """Return the rank of the task's area, the most important first."""
    return AREA_PRIORITY.index(item.domain)


def _slots(minutes: int) -> int:
    """Return how many grid slots a task of `minutes` takes."""
    return -(-minutes // SLOT_MINUTES)


def _alternating(untimed: list[PlanItem]) -> list[PlanItem]:
    """Order tasks one area at a time in turn, by area priority, each area's tasks in their own order."""
    queues = [[item for item in untimed if item.domain == domain] for domain in AREA_PRIORITY]
    return [item for turn in zip_longest(*queues) for item in turn if item is not None]


def _by_area(order: tuple[str, ...]) -> Callable[[list[PlanItem]], list[PlanItem]]:
    """Return an ordering that places one area's tasks before the next."""
    return lambda untimed: sorted(untimed, key=lambda item: order.index(item.domain))


def _first_free(minutes: int, earliest: int, busy: list[tuple[int, int]]) -> int | None:
    """Return the earliest start on the grid from `earliest` with `minutes` free before DAY_END."""
    candidate = _next_slot(earliest)
    while candidate + minutes <= minutes_after_midnight(DAY_END):
        clash = next((block for block in busy if block[0] < candidate + minutes and candidate < block[1]), None)
        if clash is None:
            return candidate
        candidate = _next_slot(clash[1])
    return None


def _place(items: Iterable[PlanItem], order: Callable[[list[PlanItem]], list[PlanItem]],
           start: int, gap: int = 0, preferred: dict[tuple[str, str], int] | None = None,
           ) -> tuple[PlanItem, ...] | None:
    """Give every task without a start time the earliest free slot from `start`.

    A task with a preferred time is placed before the others, at the first free slot from that
    time; when none is left after it, it falls back to the earliest free slot like the rest.

    Args:
        items: The day's tasks. Those with a start time stay where they are.
        order: Puts the tasks without a start time in the order they are placed.
        start: Minutes after midnight before which nothing is placed.
        gap: Minutes kept free after each task, fixed or placed, but not after a meal.
        preferred: Minutes after midnight a task is usually done at, by title and area.

    Returns:
        Every task sorted by start time, or None when tasks with a start time overlap or the free
        time before DAY_END cannot hold every task without one.
    """
    preferred = preferred or {}
    owned = tuple(items)
    timed = [item for item in owned if item.start is not None]
    if has_collisions(timed):
        return None
    untimed = sorted(order([item for item in owned if item.start is None]),
                     key=lambda item: (item.title, item.domain) not in preferred)
    placed = _fill(untimed, _busy(timed, gap), start, gap, preferred)
    return None if placed is None else _in_order((*timed, *placed))


def _busy(items: Iterable[PlanItem], gap: int = 0) -> list[tuple[int, int]]:
    """Return the minutes taken by each task with a start time, as (start, end) pairs.

    Args:
        items: The tasks; those without a start time are skipped.
        gap: Minutes kept free after each task, but not after a meal.
    """
    return [(minutes_after_midnight(item.start), minutes_after_midnight(item.start) + item.duration_minutes + (0 if item.constraint == MEAL else gap))
            for item in items if item.start is not None]


def _in_order(items: Iterable[PlanItem]) -> tuple[PlanItem, ...]:
    """Return the tasks sorted by start time."""
    return tuple(sorted(items, key=lambda item: item.start))


def _study_ranked(item: PlanItem, energy: str) -> PlanItem:
    """A study task with its rank for the day: a light one after every other task, so it takes the time
    left between them; at high energy a deep one before every other; at low energy a light one before
    every other and a deep one after them all."""
    if item.study is None:
        return item
    return replace(item, study=replace(item.study, rank=_STUDY_RANKS[energy].get(item.study.effort, 0)))


def _study_facts(study: StudyTask) -> dict:
    """What the plan chooser reads of a study task: its place in its goal, when it is in one, and its profile."""
    return {"place": f"{study.position + 1} of {study.count} in {study.goal_title}" if study.goal else None,
            "effort": study.effort, "handsOn": study.hands_on, "briefing": study.briefing, "covers": list(study.sections)}


def _study_order(tasks: list[PlanItem]) -> list[PlanItem]:
    """Tasks in the order a plan gives them, study tasks moved by their rank, and a goal's study tasks
    kept in their goal's order whatever their effort."""
    ranked = sorted(tasks, key=lambda item: item.study.rank if item.study else 0)
    slots: dict[str, list[int]] = {}
    for index, item in enumerate(ranked):
        if item.study and item.study.goal:
            slots.setdefault(item.study.goal, []).append(index)
    for indexes in slots.values():
        for index, item in zip(indexes, sorted((ranked[index] for index in indexes), key=lambda item: item.study.position)):
            ranked[index] = item
    return ranked


def _fill(tasks: Iterable[PlanItem], busy: list[tuple[int, int]], earliest: int, gap: int = 0,
          preferred: dict[tuple[str, str], int] | None = None) -> list[PlanItem] | None:
    """Place tasks in the order given, each at the first free slot from `earliest`.

    A task with a preferred time goes to the first free slot from that time, or from `earliest`
    when none is left after it. Each placed task is added to `busy`, with `gap` minutes after it.

    Returns:
        The placed tasks, or None when one doesn't fit before DAY_END.
    """
    preferred = preferred or {}
    placed = []
    for item in _study_order(list(tasks)):
        wanted = preferred.get((item.title, item.domain))
        candidate = _first_free(item.duration_minutes, max(earliest, wanted), busy) if wanted is not None else None
        if candidate is None:
            candidate = _first_free(item.duration_minutes, earliest, busy)
        if candidate is None:
            return None
        placed.append(replace(item, start=clock_time(candidate)))
        busy.append((candidate, candidate + item.duration_minutes + gap))
    return placed


def _free_windows(timed: Iterable[PlanItem], start: int) -> list[tuple[int, int]]:
    """Return the free stretches between `start` and DAY_END around the tasks with a start time.

    A fixed task may be at any hour; one after DAY_END never stretches a window past it.
    """
    windows = []
    cursor, day_end = start, minutes_after_midnight(DAY_END)
    for begin, end in sorted(_busy(timed)):
        if min(begin, day_end) > cursor:
            windows.append((cursor, min(begin, day_end)))
        cursor = max(cursor, _next_slot(end))
    if cursor < day_end:
        windows.append((cursor, day_end))
    return windows


def _ends(items: Iterable[PlanItem]) -> int:
    """Return when the last task ends, in minutes after midnight; meals don't count."""
    return max(minutes_after_midnight(item.start) + item.duration_minutes for item in items if item.constraint != MEAL)


def _tasks(items: Iterable[PlanItem]) -> tuple[PlanItem, ...]:
    """Return a plan's tasks without its meals."""
    return tuple(item for item in items if item.constraint != MEAL)


def _key(item: PlanItem) -> object:
    """Return what identifies a task across plans: its id, or its title and area."""
    return item.item_id or (item.title, item.domain)


def meal_overlap(start: str, minutes: int, meals: Iterable[Meal] = USUAL_MEALS) -> Meal | None:
    """Return the meal a task starting at `start` for `minutes` would overlap, if any.

    Args:
        start: The task's "HH:MM" start.
        minutes: How long the task lasts.
        meals: The day's meals.
    """
    begin = minutes_after_midnight(start)
    return next((meal for meal in meals
                 if minutes_after_midnight(meal.start) < begin + minutes and begin < minutes_after_midnight(meal.start) + meal.minutes), None)


def _meals(timed: Iterable[PlanItem], start: int, meals: Iterable[Meal]) -> tuple[PlanItem, ...]:
    """Return lunch and dinner at the day's times, as a plan keeps them free.

    Args:
        timed: The tasks with a start time. A meal one of them already takes is left out.
        start: Minutes after midnight before which nothing is placed; a meal over by then is left out.
        meals: The day's meals.
    """
    busy = _busy(timed)
    return tuple(PlanItem(meal.start, meal.title, "", "life", meal.minutes, MEAL) for meal in meals
                 if minutes_after_midnight(meal.start) + meal.minutes > start
                 and not any(begin < minutes_after_midnight(meal.start) + meal.minutes and minutes_after_midnight(meal.start) < end
                             for begin, end in busy))


def fit_around_meal(items: Iterable[PlanItem], meal: Meal, others: Iterable[Meal] = ()) -> tuple[PlanItem, ...] | None:
    """Fit a set plan's tasks around a meal moved by a little, changing only the tasks it takes.

    A task that runs into the meal is shortened to end as it starts when its length is an estimate
    that keeps KEPT_ESTIMATE_MINUTES; else a flexible one moves earlier by as much, when that time
    is free. A flexible task the meal takes the start of moves to when the meal ends, when that
    time is free, or, as an estimate, moves there shortened to the time free, if that keeps
    KEPT_ESTIMATE_MINUTES. Free time keeps clear of every other task and meal, within DAY_START and
    DAY_END.

    Args:
        items: The set plan's tasks, each with its start.
        meal: The meal at its new time.
        others: The day's other meals.

    Returns:
        The tasks in the order given, those next to the meal changed; None when one can't be fitted
        so, and the plan needs a review instead.
    """
    begin = minutes_after_midnight(meal.start)
    end = begin + meal.minutes
    fitted = list(items)
    meals = [(begin, end), *((minutes_after_midnight(other.start), minutes_after_midnight(other.start) + other.minutes)
                             for other in others)]

    def free(index: int, start: int, finish: int) -> bool:
        taken = [*meals, *((minutes_after_midnight(other.start), minutes_after_midnight(other.start) + other.duration_minutes)
                           for place, other in enumerate(fitted) if place != index)]
        return (minutes_after_midnight(DAY_START) <= start and finish <= minutes_after_midnight(DAY_END)
                and not any(first < finish and start < last for first, last in taken))

    for index, item in enumerate(fitted):
        start = minutes_after_midnight(item.start)
        finish = start + item.duration_minutes
        if finish <= begin or start >= end:
            continue
        flexible = item.constraint == "flexible"
        if start < begin and item.estimated and begin - start >= KEPT_ESTIMATE_MINUTES:
            fitted[index] = replace(item, duration_minutes=begin - start)
        elif start < begin and flexible and free(index, start - (finish - begin), begin):
            fitted[index] = replace(item, start=clock_time(start - (finish - begin)))
        elif start >= begin and flexible and free(index, end, end + item.duration_minutes):
            fitted[index] = replace(item, start=clock_time(end))
        elif start >= begin and flexible and item.estimated:
            starts = [minutes_after_midnight(task.start) for place, task in enumerate(fitted) if place != index]
            room = min([moment for moment in (*starts, *(first for first, _ in meals)) if moment >= end]
                       + [minutes_after_midnight(DAY_END)]) - end
            if room < KEPT_ESTIMATE_MINUTES:
                return None
            fitted[index] = replace(item, start=clock_time(end), duration_minutes=min(item.duration_minutes, room))
        else:
            return None
    return tuple(fitted)


def _best_fill(tasks: list[PlanItem], free_slots: int) -> list[PlanItem]:
    """Return the tasks, in their given order, that together fill the most of `free_slots` slots."""
    best: dict[int, tuple[int, ...]] = {0: ()}
    for index, item in enumerate(tasks):
        for used, chosen in list(best.items()):
            total = used + _slots(item.duration_minutes)
            if total <= free_slots and total not in best:
                best[total] = (*chosen, index)
    return [tasks[index] for index in best[max(best)]]


def _distinct(first: Iterable[PlanItem], second: Iterable[PlanItem]) -> bool:
    """Return whether two plans differ clearly, as DISTINCT_MINUTES defines; meals don't count."""
    one, other = _tasks(first), _tasks(second)
    times = {_key(item): (minutes_after_midnight(item.start), item.duration_minutes) for item in other}
    moved = sum(abs(minutes_after_midnight(item.start) - times[_key(item)][0]) + abs(item.duration_minutes - times[_key(item)][1])
                for item in one)
    reordered = [_key(item) for item in one] != [_key(item) for item in other]
    return (reordered and moved >= DISTINCT_MINUTES) or abs(_ends(one) - _ends(other)) >= DISTINCT_MINUTES


def _quoted(titles: list[str]) -> str:
    """Return task titles in quotation marks, joined as an English list."""
    quoted = [f"“{title}”" for title in titles]
    if len(quoted) == 1:
        return quoted[0]
    return f"{', '.join(quoted[:-1])}{',' if len(quoted) > 2 else ''} and {quoted[-1]}"


def _note(key: str, **values: object) -> dict:
    """Return one sentence of a plan's rationale: its key in NOTES, its values, and its English text."""
    worded = {name: _quoted(value) if isinstance(value, list) else value for name, value in values.items()}
    return {"key": key, "values": values, "text": NOTES[key].format(**worded)}


def notes_without(notes: list[dict], gone: dict, entries: Iterable[dict]) -> list[dict]:
    """Rewrite a proposed plan's sentences once one of its tasks is deleted, from the tasks it has left.

    A list of tasks loses it, and a stretch of tasks follows the ones left; a sentence about it
    alone, or one the local model wrote that names it, goes; a gentle start eases in with the
    first flexible task left. Counts of focus and quick tasks follow it, the reason going once
    fewer than two are left, and when the day starts and ends follows the tasks left. The other
    sentences stay word for word.

    Args:
        notes: The plan's sentences, each its "key", "values" and "text".
        gone: The task deleted: its "title", "domain", "duration_minutes" and "start_time".
        entries: The plan's entries left, each its "title", "start_time", "duration_minutes" and
            "constraint_kind"; they keep their times.

    Returns:
        The sentences, rewritten where the task touched them, in their order.
    """
    left = sorted(entries, key=lambda entry: entry["start_time"])
    title = gone["title"]
    ends = {entry["title"]: minutes_after_midnight(entry["start_time"]) + entry["duration_minutes"] for entry in left}
    counted = {"planWhyFocus": gone["domain"] in FOCUS_AREAS,
               "planWhyQuick": gone["duration_minutes"] <= QUICK_TASK_MINUTES}
    rewritten = []
    for item in notes:
        key, values = item["key"], dict(item["values"])
        if (any(values.get(name) == title for name in ("title", "usual", "often"))
                or key == "planWhyAgent" and any(title in str(values.get(name, "")) for name in ("en", "zh"))):
            continue
        if title in values.get("tasks", ()):
            values["tasks"] = [task for task in values["tasks"] if task != title]
            if not values["tasks"]:
                continue
            if key in ("planDoesFocus", "planDoesFocusOne"):
                start = next((entry["start_time"] for entry in left if entry["title"] in values["tasks"]), None)
                if start is None:
                    continue
                key, values = (("planDoesFocusOne", {"tasks": values["tasks"], "start": start}) if len(values["tasks"]) == 1
                               else ("planDoesFocus", {"tasks": values["tasks"], "start": start,
                                                       "end": clock_time(max(ends[task] for task in values["tasks"]))}))
        if values.get("first") == title:
            values["first"] = next((entry["title"] for entry in left if entry["constraint_kind"] == "flexible"), None)
            if values["first"] is None:
                continue
        if counted.get(key) and gone.get("start_time") is None:
            values["count"] -= 1
            if values["count"] < 2:
                continue
        if key in ("planDoesEarly", "planDoesSpacious") and ends:
            values["end"] = clock_time(max(ends.values()))
        if key == "planDoesBalanced" and left:
            values["start"] = left[0]["start_time"]
        rewritten.append(item if (key, values) == (item["key"], item["values"]) else _note(key, **values))
    return rewritten


def _variant(slug: str, items: Iterable[PlanItem], notes: list[dict]) -> dict:
    """Return a plan as proposed: its name, its rationale in sentences and as text, its tasks and meals."""
    owned = tuple(items)
    return {"name": PLAN_KINDS[slug], "slug": slug, "rationale": " ".join(note["text"] for note in notes),
            "notes": notes, "items": _tasks(owned), "meals": tuple(item for item in owned if item.constraint == MEAL)}


def _deep_focus(base: tuple[PlanItem, ...], start: int) -> tuple | None:
    """Keep work, project and learning tasks back to back in the longest free stretch of the day.

    Life tasks are placed around the block, from `start`.

    Returns:
        The plan's tasks and what sets it apart, or None when no free stretch holds the block.
    """
    timed = [item for item in base if item.start is not None]
    untimed = [item for item in base if item.start is None]
    focus = sorted((item for item in untimed if item.domain in FOCUS_AREAS),
                   key=lambda item: FOCUS_AREAS.index(item.domain))
    windows = _free_windows(timed, start)
    if not focus or not windows:
        return None
    begin, end = max(windows, key=lambda window: window[1] - window[0])
    if sum(_slots(item.duration_minutes) for item in focus) * SLOT_MINUTES > end - begin:
        return None
    busy = _busy(timed)
    placed = _fill(focus, busy, begin)
    others = _fill([item for item in untimed if item.domain not in FOCUS_AREAS], busy, start)
    if placed is None or others is None:
        return None
    titles = [item.title for item in focus]
    note = (_note("planDoesFocus", tasks=titles, start=clock_time(begin), end=clock_time(_ends(placed)))
            if len(focus) > 1 else _note("planDoesFocusOne", tasks=titles, start=clock_time(begin)))
    return _in_order((*timed, *placed, *others)), [note]


def _lighter_day(base: tuple[PlanItem, ...], start: int, guidance_domains: list[str], lighter: bool,
                 not_before: str = GENTLE_START) -> tuple | None:
    """Start later with life tasks, leave a breather after each task, and trim estimated lengths.

    Nothing is placed before `not_before`, or before `start` when that is later; when the tasks
    don't fit from then, they are placed from `start` instead.

    On a low-energy day every estimated length loses ADJUST_MINUTES;
    otherwise only one does, in the areas Summary advice names first and then the least important
    area first. A length the user set is never trimmed, and none drops below MIN_TRIMMED_MINUTES.

    Returns:
        The plan's tasks and what sets it apart, or None.
    """
    untimed = [item for item in base if item.start is None]
    if not untimed:
        return None
    order = [*guidance_domains, *(domain for domain in reversed(AREA_PRIORITY) if domain not in guidance_domains)]
    trimmable = sorted((item for item in untimed
                        if item.estimated and item.duration_minutes > MIN_TRIMMED_MINUTES),
                       key=lambda item: (order.index(item.domain), -item.duration_minutes))
    trimmed = trimmable if lighter else trimmable[:1]
    items = tuple(_shorter(item) if any(item is chosen for chosen in trimmed) else item for item in base)
    gentle_start = max(start, minutes_after_midnight(not_before))
    placed = _place(items, _by_area(GENTLE_ORDER), gentle_start, GENTLE_BREAK_MINUTES)
    if placed is None:
        gentle_start = start
        placed = _place(items, _by_area(GENTLE_ORDER), gentle_start, GENTLE_BREAK_MINUTES)
    if placed is None:
        return None
    timed = {_key(item) for item in base if item.start is not None}
    first = next(item for item in placed if _key(item) not in timed)
    notes = [_note("planDoesGentle", start=clock_time(gentle_start), first=first.title)]
    if len(trimmed) > 1:
        notes.append(_note("planDoesGentleTrimAll", count=len(trimmed)))
    elif trimmed:
        notes.append(_note("planDoesGentleTrim", title=trimmed[0].title,
                           **{"from": trimmed[0].duration_minutes, "to": _shorter(trimmed[0]).duration_minutes}))
    return placed, notes


def _finish_early(base: tuple[PlanItem, ...], start: int) -> tuple[PlanItem, ...] | None:
    """Fill each gap between fixed times as fully as possible, so the day ends as soon as it can.

    Returns:
        The plan's tasks, or None when they don't fit before DAY_END.
    """
    timed = [item for item in base if item.start is not None]
    remaining = sorted((item for item in base if item.start is None), key=_priority)
    windows = _free_windows(timed, start)
    busy = _busy(timed)
    placed = []
    for index, (begin, end) in enumerate(windows):
        if not remaining:
            break
        chosen = remaining if index == len(windows) - 1 else _best_fill(remaining, (end - begin) // SLOT_MINUTES)
        filled = _fill(chosen, busy, begin)
        if filled is None:
            return None
        placed += filled
        remaining = [item for item in remaining if not any(item is taken for taken in chosen)]
    return None if remaining else _in_order((*timed, *placed))


def _finish_rates(findings: Iterable[dict]) -> dict[tuple[str, str], float]:
    """Return the share of reports that were Done, for each task an area agent reviewed."""
    return {(finding["taskTitle"], finding["domain"]): finding["done"] / finding["reported"]
            for finding in findings if finding.get("reported")}


def _same(first: Iterable[PlanItem], second: Iterable[PlanItem]) -> bool:
    """Return whether two plans give every task the same start and length; meals don't count."""
    return ({(_key(item), item.start, item.duration_minutes) for item in _tasks(first)}
            == {(_key(item), item.start, item.duration_minutes) for item in _tasks(second)})


# The parts of an agent's finding the local model reads when it chooses plans.
_FINDING_FIELDS = ("kind", "taskTitle", "domain", "done", "partial", "skipped", "reported", "preferredStart",
                   "energy", "sleep", "lighter", "focused")


def _choice(choose: Callable[[dict], object] | None, context: dict, kinds: Iterable[str]) -> list[dict]:
    """Return the usable plans the local model chose, at most two, each with its kind and reasons.

    A pick naming a kind that isn't on offer, or repeating one, is dropped. Its reasons are kept
    only when both the English and the Chinese one are given.
    """
    answer = choose(context) if choose else None
    picks = []
    for pick in answer if isinstance(answer, list) else []:
        kind = pick.get("kind") if isinstance(pick, dict) else None
        if kind in kinds and kind not in (chosen["kind"] for chosen in picks):
            reasons = all(isinstance(pick.get(name), str) and pick[name].strip() for name in ("why", "whyZh"))
            voted = isinstance(pick.get("agents"), list) and isinstance(pick.get("names"), str)
            picks.append({"kind": kind, **({"why": pick["why"].strip(), "whyZh": pick["whyZh"].strip()}
                                           if reasons else {}),
                          **({"agents": [str(agent) for agent in pick["agents"]], "names": pick["names"]}
                             if voted and not reasons else {})})
    return picks[:2]


def build_recorded_variants(
    items: Iterable[PlanItem], memory: Iterable[dict] = (),
    guidance: Iterable[dict] = (), earliest: str = DAY_START, findings: Iterable[dict] = (),
    preferences: dict[str, int] | None = None, choose: Callable[[dict], object] | None = None,
    meals: Iterable[Meal] = USUAL_MEALS,
) -> tuple[dict, ...]:
    """Build Balanced and the two other plans that suit the day best, from the day's own tasks.

    Every plan places tasks between DAY_START (or `earliest`, if later) and DAY_END, keeps the
    tasks with a start time where they are, and keeps lunch and dinner free. Balanced is always
    first: the areas take turns by priority. The planner then builds every other kind of plan the
    day allows that doesn't repeat Balanced:

    - Deep focus keeps work, project and learning tasks back to back in the longest free stretch;
      Lighter day starts later, life first, with a break after each task, and trims an estimated
      length. These are the everyday pair, first in the planner's own ranking on a day with fewer
      than FEW_TASKS tasks to place.
    - Finish early fills the gaps between fixed times (when that ends EARLIER_BY_MINUTES sooner),
      Quick wins first does the short tasks first, Easiest first starts with the tasks the user
      usually finishes, Your usual rhythm places tasks at the times they are usually done, and
      Breathing room leaves an even gap after every task.

    The local model, through `choose`, reads the day and those plans and picks two; the planner's
    own ranking (kinds the user set most often, then the ones that suit the day) fills any place
    it leaves. Plans that differ clearly (see DISTINCT_MINUTES) are preferred, and one that merely
    differs fills the third place when no clearly different one is left, so a day gets three plans
    whenever three different ones can be made. When the day's average energy is LOW_ENERGY or less,
    Lighter day is one of them and listed first; at HIGH_ENERGY or more, Deep focus is. No plan removes a task or shortens a length the user set; a length an area agent
    estimated is shorter in every plan when the user repeatedly asked to shorten the task or an
    agent found it often unfinished, but never below MIN_TRIMMED_MINUTES.

    Args:
        items: The day's tasks, each with the length plans use.
        memory: Earlier explicit shortening requests, counted per task.
        guidance: Active Summary advice; Lighter day trims a task in its areas first.
        earliest: The earliest "HH:MM" a task without a start time may be placed at.
        findings: The area agents' findings; see task_review.
        preferences: How many times the user set each kind of plan lately, by slug.
        choose: Asks the local model to choose. It receives the day ("day") and the plans on offer
            ("candidates"), and returns up to two picks, each a dict with the plan's "kind" and its
            reasons in English ("why") and Chinese ("whyZh"), or None.
        meals: The day's lunch and dinner, which every plan keeps free.

    Returns:
        The plans, each with a name, slug, rationale, its sentences as `notes`, its tasks sorted
        by start time as `items`, and its `meals`.

    Raises:
        ValueError: When there are no tasks, tasks with a start time overlap, or the free time
            left today cannot hold every task without a start time.
    """
    findings = tuple(findings)
    guidance = tuple(guidance)
    preferences = preferences or {}
    shortened = {(signal["taskTitle"], signal["domain"])
                 for signal in memory if signal["shortenRequests"] >= 2}
    shortened |= {(finding["taskTitle"], finding["domain"]) for finding in findings if finding["kind"] == "shorten"}
    preferred = {(finding["taskTitle"], finding["domain"]): minutes_after_midnight(finding["preferredStart"])
                 for finding in findings if finding["kind"] == "time"}
    owned = tuple(items)
    if not owned:
        raise ValueError("Add today's tasks before building a day plan")
    clash = collision([item for item in owned if item.start is not None])

    def span(item: PlanItem) -> str:
        return f"“{item.title}” ({item.start}–{clock_time(minutes_after_midnight(item.start) + item.duration_minutes)})"

    if len(clash) == 2:
        raise ValueError(f"{span(clash[0])} and {span(clash[1])} overlap; change one of their start "
                         "times or lengths before proposing plans")
    if clash:
        raise ValueError(f"“{clash[0].title}” at {clash[0].start} runs past midnight; shorten it or move "
                         "it earlier before proposing plans")
    start = max(_next_slot(minutes_after_midnight(earliest)), minutes_after_midnight(DAY_START))
    tasks = tuple(_shorter(item) if item.estimated and item.constraint == "flexible"
                  and (item.title, item.domain) in shortened else item for item in owned)
    lighter = any(finding["kind"] == "area-life" and finding.get("lighter") for finding in findings)
    high = any(finding["kind"] == "area-life" and finding.get("focused") for finding in findings)
    # A study task's effort places it for the day's energy (see _study_ranked).
    tasks = tuple(_study_ranked(item, "low" if lighter else "high" if high else "normal") for item in tasks)
    untimed = [item for item in tasks if item.start is None]
    kept = _meals([item for item in tasks if item.start is not None], start, meals)
    base = (*tasks, *kept)
    balanced = _place(base, _alternating, start)
    if balanced is None:
        raise ValueError(f"The free time left before {DAY_END} can't hold every task without a "
                         "start time; shorten one or move it to another day")
    variants = [_variant("balanced", balanced, [_note("planDoesBalanced", start=clock_time(start))])]
    if not untimed:
        return tuple(variants)

    busy = [item for item in base if item.start is not None]
    load = sum(item.duration_minutes for item in untimed)
    free = sum(end - begin for begin, end in _free_windows(busy, start))
    guidance_domains = [item["domain"] for item in guidance if item.get("domain") in AREA_PRIORITY]
    focus_count = sum(item.domain in FOCUS_AREAS for item in untimed)
    quick = sorted((item for item in untimed if item.duration_minutes <= QUICK_TASK_MINUTES),
                   key=lambda item: (item.duration_minutes, _priority(item)))
    placeable = {(item.title, item.domain) for item in untimed}
    rates = {key: rate for key, rate in _finish_rates(findings).items() if key in placeable}
    usual = sorted((minutes, key) for key, minutes in preferred.items() if key in placeable)
    spacious_gap = min(SPACIOUS_MAX_GAP, (free - load) // (len(untimed) + 1) // SLOT_MINUTES * SLOT_MINUTES)

    # Each builder returns the plan, what sets it apart, and the planner's own reason to suggest it
    # (None when the day doesn't particularly suit it), or None when the day doesn't allow the kind.
    def focused() -> tuple | None:
        built = _deep_focus(base, start)
        why = (_note("planWhyHighEnergy") if high
               else _note("planWhyFocus", count=focus_count) if focus_count >= 2 else None)
        return built and (*built, why)

    def gentle() -> tuple | None:
        built = _lighter_day(base, start, guidance_domains, lighter)
        why = (_note("planWhyLighterAdvised") if lighter
               else _note("planWhyFull") if load * 100 >= free * FULL_DAY_PERCENT else None)
        return built and (*built, why)

    def early() -> tuple | None:
        plan = _finish_early(base, start)
        if plan is None or _ends(plan) > _ends(balanced) - EARLIER_BY_MINUTES:
            return None
        return (plan, [_note("planDoesEarly", end=clock_time(_ends(plan)))],
                _note("planWhyEarly", minutes=_ends(balanced) - _ends(plan)))

    def quickwins() -> tuple | None:
        if not quick or len(untimed) < 2:
            return None
        plan = _place(base, lambda chosen: sorted(chosen, key=lambda item: (item.duration_minutes, _priority(item))),
                      start)
        return plan and (plan, [_note("planDoesQuick", tasks=[item.title for item in quick])],
                         _note("planWhyQuick", count=len(quick)) if 2 <= len(quick) < len(untimed) else None)

    def easiest() -> tuple | None:
        if len(rates) < 2 or max(rates.values()) - min(rates.values()) < EASIEST_SPREAD:
            return None
        plan = _place(base, lambda chosen: sorted(chosen, key=lambda item: (
            -rates.get((item.title, item.domain), 0.5), _priority(item))), start)
        known = sorted(rates, key=lambda key: -rates[key])
        return plan and (plan, [_note("planDoesEasiest", usual=known[0][0], often=known[-1][0])],
                         _note("planWhyEasiest"))

    def rhythm() -> tuple | None:
        if not usual:
            return None
        plan = _place(base, _alternating, start, preferred=preferred)
        if plan is None:
            return None
        minutes, (title, domain) = usual[0]
        placed = minutes_after_midnight(next(item.start for item in plan if (item.title, item.domain) == (title, domain)))
        # Placed before its usual time, the task only fell back to free time: that isn't its rhythm.
        if placed < minutes:
            return None
        does = (_note("planDoesRhythmMany", tasks=[key[0] for _, key in usual]) if len(usual) > 1
                else _note("planDoesRhythm", title=title, time=clock_time(placed)) if placed == minutes
                else _note("planDoesRhythmAfter", title=title, time=clock_time(placed), usual=clock_time(minutes)))
        return plan, [does], _note("planWhyRhythm")

    def spacious() -> tuple | None:
        if spacious_gap < SPACIOUS_MIN_GAP:
            return None
        plan = _place(base, _alternating, start, spacious_gap)
        return plan and (plan, [_note("planDoesSpacious", gap=spacious_gap, end=clock_time(_ends(plan)))],
                         _note("planWhySpacious") if load * 2 <= free else None)

    builders = {"focused": focused, "gentle": gentle, "early": early, "quickwins": quickwins,
                "easiest": easiest, "rhythm": rhythm, "spacious": spacious}
    candidates = {}
    for kind in DEFAULT_RANK:
        built = builders[kind]()
        if built and not _same(built[0], balanced):
            candidates[kind] = built
    # The planner's own ranking: kinds the user sets more often first, then the everyday pair on a
    # day with few tasks or the kinds that suit the day otherwise, then the default order.
    few = len(untimed) < FEW_TASKS
    ranked = sorted(candidates, key=lambda kind: (-preferences.get(kind, 0),
                                                  not (kind in EVERYDAY if few else candidates[kind][2]),
                                                  DEFAULT_RANK.index(kind)))

    def facts(plan: tuple[PlanItem, ...]) -> dict:
        first = _tasks(plan)[0]
        resized = sum(item.duration_minutes != next(task.duration_minutes for task in tasks if _key(task) == _key(item))
                      for item in _tasks(plan))
        return {"firstTask": first.title, "startsAt": first.start, "doneBy": clock_time(_ends(plan)),
                "lengthsChanged": resized}

    context = {
        "day": {
            "start": clock_time(start), "end": DAY_END,
            "meals": [f"{meal.title} {meal.start}–{clock_time(minutes_after_midnight(meal.start) + meal.duration_minutes)}"
                      for meal in kept],
            "tasks": [{"title": item.title, "detail": item.detail, "area": item.domain, "minutes": item.duration_minutes,
                       "length": "estimated" if item.estimated else "yours", "start": item.start,
                       **({"study": _study_facts(item.study)} if item.study else {})} for item in tasks],
            "freeMinutes": free, "taskMinutes": load, "lighterDayAdvised": lighter,
            "advice": [item["content"] for item in guidance if item.get("content")],
            "findings": [{name: finding[name] for name in _FINDING_FIELDS if name in finding} for finding in findings],
            "planPreferences": preferences,
        },
        "candidates": [{"kind": kind, "name": PLAN_KINDS[kind],
                        "does": " ".join(note["text"] for note in candidates[kind][1]),
                        "plannerReason": candidates[kind][2]["text"] if candidates[kind][2] else "",
                        **facts(candidates[kind][0])} for kind in ranked],
    }
    picks = _choice(choose, context, candidates)
    order = [*(pick["kind"] for pick in picks), *(kind for kind in ranked if kind not in {pick["kind"] for pick in picks})]
    # The day's average energy makes Lighter day, at LOW_ENERGY or below, or Deep focus, at HIGH_ENERGY
    # or above, one of the plans, whatever else is chosen.
    first = "gentle" if lighter else "focused" if high else None
    if first in candidates:
        order = [first, *(kind for kind in order if kind != first)]
    chosen: list[str] = []
    for clearly in (True, False):
        for kind in order:
            plans = [balanced, *(candidates[other][0] for other in chosen)]
            if len(chosen) < 2 and kind not in chosen and all(
                    _distinct(candidates[kind][0], other) if clearly else not _same(candidates[kind][0], other)
                    for other in plans):
                chosen.append(kind)
    # When Lighter day from GENTLE_START would repeat a plan already offered, it starts later still,
    # an hour at a time, so the day keeps three different plans.
    if len(chosen) < 2 and "gentle" not in chosen:
        plans = [balanced, *(candidates[other][0] for other in chosen)]
        for later in range(minutes_after_midnight(GENTLE_START) + 60, minutes_after_midnight(DAY_END), 60):
            built = _lighter_day(base, start, guidance_domains, lighter, clock_time(later))
            if built and not any(_same(built[0], other) for other in plans):
                candidates["gentle"] = (*built, candidates.get("gentle", (None, None, None))[2])
                chosen.append("gentle")
                break
    reasons = {pick["kind"]: _note("planWhyAgent", en=pick["why"], zh=pick["whyZh"]) for pick in picks if "why" in pick}
    reasons |= {pick["kind"]: _note("planWhyVotes", names=pick["names"], agents=pick["agents"])
                for pick in picks if "agents" in pick}
    for kind in chosen:
        plan, does, why = candidates[kind]
        # The plan the day's energy puts first says so, whatever chose it.
        why = ((why if kind == first else None) or reasons.get(kind) or why
               or _note("planWhyEveryday" if kind in EVERYDAY else "planWhyAlternative"))
        variants.append(_variant(kind, plan, [why, *does]))
    # That plan is listed first, where it is shown and compared first.
    if first:
        variants.sort(key=lambda variant: variant["slug"] != first)
    return tuple(variants)


def day_load(items: Iterable[PlanItem], earliest: str = DAY_START, meals: Iterable[Meal] = USUAL_MEALS) -> dict:
    """Weigh the day's tasks without a start time against its free time, as every plan sees it.

    Args:
        items: The day's tasks; those with a start time, and lunch and dinner, take their time.
        earliest: The earliest "HH:MM" a task without a start time may be placed at.
        meals: The day's meals.

    Returns:
        The "taskMinutes" the tasks without a start time need, the "freeMinutes" left for them
        between `earliest` (or DAY_START, if later) and DAY_END, whether Balanced can place every
        one ("fits"), and whether they make a full day ("full", see FULL_DAY_PERCENT).
    """
    owned = tuple(items)
    start = max(_next_slot(minutes_after_midnight(earliest)), minutes_after_midnight(DAY_START))
    timed = [item for item in owned if item.start is not None]
    kept = _meals(timed, start, meals)
    load = sum(item.duration_minutes for item in owned if item.start is None)
    free = sum(end - begin for begin, end in _free_windows([*timed, *kept], start))
    return {"taskMinutes": load, "freeMinutes": free, "fits": _place((*owned, *kept), _alternating, start) is not None,
            "full": load * 100 >= free * FULL_DAY_PERCENT}


def minutes_by_domain(items: Iterable[PlanItem]) -> dict[str, int]:
    totals = {domain: 0 for domain in DOMAIN_LABELS}
    for item in items:
        totals[item.domain] += item.duration_minutes
    return totals


def collision(items: Iterable[PlanItem]) -> tuple[PlanItem, ...]:
    """Return the first task that runs past midnight, else the first two whose times overlap.

    Args:
        items: Tasks with a start time.

    Returns:
        One task, two tasks, or an empty tuple when the times fit in the day without overlapping.
    """
    ordered = sorted(items, key=lambda item: item.start)
    day_end = datetime.strptime("00:00", "%H:%M") + timedelta(days=1)
    late = next((item for item in ordered if datetime.strptime(item.start, "%H:%M") + timedelta(
        minutes=item.duration_minutes) > day_end), None)
    if late:
        return (late,)
    for current, following in zip(ordered, ordered[1:]):
        current_end = datetime.strptime(current.start, "%H:%M") + timedelta(
            minutes=current.duration_minutes
        )
        if current_end > datetime.strptime(following.start, "%H:%M"):
            return (current, following)
    return ()


def has_collisions(items: Iterable[PlanItem]) -> bool:
    return bool(collision(items))
