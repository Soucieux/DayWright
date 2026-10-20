"""How you work: what the user's records show of how they work, in a few lines Ava reads with every answer and Settings
› Memory shows as From your records. Nothing here is the model's: every line is worded from the figures Patterns draws
(see patterns), the area agents' task profiles (see profiles) and each goal's momentum, all time and over the last
RECENT_DAYS days, and a figure below its graph's threshold is left out. It is made from the records whenever it is read,
so it is never out of date, and it needs no model.
"""

from __future__ import annotations

from datetime import date, timedelta

from . import patterns
from .agents import often_signals
from .domain_records import IDLE_DAYS
from .planner import DAY_END

# The two sets of lines: from every record, and from the last RECENT_DAYS days.
ALL_TIME, LAST_THIRTY = "allTime", "lastThirty"
RECENT_DAYS = 30
# The most lines about single tasks and about goals; with the figures, the summary holds at most MOST_LINES.
MOST_TASK_LINES = 3
MOST_GOALS = 6
MOST_LINES = 16
# A task "usually takes" other than planned once this many of its done times say so, by this many minutes or more.
USUAL_DONE = 3
USUAL_DIFFERENCE = 10
# The figures each set words, in order; when every record lies within the last RECENT_DAYS days the one set words both.
_ALL_TIME_FIGURES = ("bestHours", "plannedActual", "estimates", "energy")
_RECENT_FIGURES = ("plannedActual", "outcome", "reporting")
# The statuses the tally names, in its order; dayPaused counts as without a status, as noReply does.
_TALLY = ("done", "partial", "skipped", "unanswered")

_WORDS = {
    "en": {
        "context": "How the user works, from their records.", ALL_TIME: "All time", LAST_THIRTY: "Last 30 days",
        "tally": "{count} task{plural} recorded: {parts}.", "partsJoin": ", ",
        "done": "{count} done", "partial": "{count} partly done", "skipped": "{count} skipped",
        "unanswered": "{count} without a status",
        "window": "Tasks are most often finished from {start} to {end}{day}.",
        "windows": "Tasks are most often finished around {first} and {second}{day}.",
        "oneHour": "Tasks are all finished between {start} and {end}.", "onDay": ", most of all on {weekday}s",
        "weekdays": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
        "over": "{area} tasks take {percent}% longer than planned.",
        "under": "{area} tasks take {percent}% less time than planned.",
        "close": "Every area's tasks take close to the time planned.",
        "areas": {"learning": "Learn", "life": "Life", "work": "Work", "project": "Project"},
        "down": "The agents' estimates are {now} off the real time, down from {before}.",
        "up": "The agents' estimates are {now} off the real time, up from {before}.",
        "upFromSpot": "The agents' estimates are {now} off the real time; at first they matched it.",
        "same": "The agents' estimates are {now} off the real time, about as before.",
        "spot": "The agents' estimates match the real time.",
        "single": "The agents' estimates are {now} off the real time.",
        "longer": "On days of {group} energy tasks take {percent}% longer than planned.",
        "shorter": "On days of {group} energy tasks take {percent}% less time than planned.",
        "hardly": "Energy hardly changes how long tasks take.",
        "groups": {"low": "low", "middle": "medium", "high": "high"},
        "outcome": "{share}% of the time recorded went to fully done tasks.",
        "outcomeNoReply": "{share}% of the time recorded went to fully done tasks, and {minutes} to tasks left without a status.",
        "reporting": "{share}% of statuses were set right away.",
        "often-skipped": "“{title}” was skipped {count} of {scheduled} times.",
        "often-unanswered": "“{title}” was left without a status {count} of {scheduled} times.",
        "usual": "“{title}” usually takes {taken} when done; it is planned for {planned}.",
        "goal": "“{title}”: {done} tasks done, the last on {day}.",
        "goalRecent": "“{title}”: {done} tasks done, {recent} in the last 30 days, the last on {day}.",
        "goalIdle": "“{title}”: {done} tasks done; nothing for {days} days.",
        "goalNone": "“{title}”: nothing done yet.",
    },
    "zh": {
        "context": "用户的做事方式，来自其记录。", ALL_TIME: "全部", LAST_THIRTY: "最近 30 天",
        "tally": "记录了 {count} 项任务：{parts}。", "partsJoin": "，",
        "done": "{count} 项已完成", "partial": "{count} 项部分完成", "skipped": "{count} 项已跳过",
        "unanswered": "{count} 项没有状态",
        "window": "任务最常在 {start} 到 {end} 完成{day}。",
        "windows": "任务最常在 {first} 和 {second} 前后完成{day}。",
        "oneHour": "任务都在 {start} 到 {end} 之间完成。", "onDay": "，最常在{weekday}",
        "weekdays": ("周一", "周二", "周三", "周四", "周五", "周六", "周日"),
        "over": "{area}任务比计划多用 {percent}%。",
        "under": "{area}任务比计划少用 {percent}%。",
        "close": "每个领域的任务都接近计划用时。",
        "areas": {"learning": "学习", "life": "生活", "work": "工作", "project": "项目"},
        "down": "代理的估时与真实用时相差 {now}，比之前的 {before} 少。",
        "up": "代理的估时与真实用时相差 {now}，比之前的 {before} 多。",
        "upFromSpot": "代理的估时与真实用时相差 {now}；起初两者一致。",
        "same": "代理的估时与真实用时相差 {now}，与之前差不多。",
        "spot": "代理的估时与真实用时一致。",
        "single": "代理的估时与真实用时相差 {now}。",
        "longer": "精力{group}的日子，任务比计划多用 {percent}%。",
        "shorter": "精力{group}的日子，任务比计划少用 {percent}%。",
        "hardly": "精力几乎不影响任务要用多久。",
        "groups": {"low": "低", "middle": "中等", "high": "高"},
        "outcome": "记录的用时有 {share}% 用在了完全完成的任务上。",
        "outcomeNoReply": "记录的用时有 {share}% 用在了完全完成的任务上，{minutes}用在了没有状态的任务上。",
        "reporting": "{share}% 的状态是及时设置的。",
        "often-skipped": "“{title}”在 {scheduled} 次中跳过了 {count} 次。",
        "often-unanswered": "“{title}”在 {scheduled} 次中有 {count} 次没有状态。",
        "usual": "“{title}”完成时通常要 {taken}；计划是 {planned}。",
        "goal": "“{title}”：完成了 {done} 项任务，最近一次在 {day}。",
        "goalRecent": "“{title}”：完成了 {done} 项任务，最近 30 天 {recent} 项，最近一次在 {day}。",
        "goalIdle": "“{title}”：完成了 {done} 项任务；已经 {days} 天没有进展。",
        "goalNone": "“{title}”：还没有完成任何任务。",
    },
}


def minutes_words(minutes: int, language: str) -> str:
    """A length as the interface's formatMinutes words it: "1 h 15 min", "1 小时 15 分"."""
    hours, rest = divmod(minutes, 60)
    if language == "zh":
        return f"{rest} 分钟" if not hours else f"{hours} 小时 {rest} 分" if rest else f"{hours} 小时"
    return f"{rest} min" if not hours else f"{hours} h {rest} min" if rest else f"{hours} h"


def day_words(day: str, language: str) -> str:
    """A day as Ava names it: "13 Oct", "10月13日"."""
    shown = date.fromisoformat(day)
    return f"{shown.month}月{shown.day}日" if language == "zh" else f"{shown.day} {shown.strftime('%b')}"


def _clock(hour: int) -> str:
    return f"{hour:02d}:00"


def _shown(found: dict) -> bool:
    """Whether a graph's figure is worded: from its threshold on, as Patterns draws it."""
    return found["state"] in ("settling", "ready")


def _tally(records: list[dict], words: dict) -> str | None:
    """How many tasks the records hold, by the status each got."""
    if not records:
        return None
    counts = {"done": 0, "partial": 0, "skipped": 0, "unanswered": 0}
    for record in records:
        counts["unanswered" if record["status"] in ("noReply", "dayPaused") else record["status"]] += 1
    parts = words["partsJoin"].join(words[status].format(count=counts[status]) for status in _TALLY if counts[status])
    return words["tally"].format(count=len(records), plural="" if len(records) == 1 else "s", parts=parts)


def _figure(kind: str, records: list[dict], energy_days: list[dict], start: str, end: str, words: dict,
            language: str, day_end: str = DAY_END) -> str | None:
    """One figure's line, worded from what Patterns finds over the records from start to end, or None below its
    threshold or with nothing to say; Reporting habit reads `day_end`, Your day's end."""
    whole = [{"start": start, "end": end, "kind": "all", "current": True}]
    if kind == "bestHours":
        found = patterns.best_hours(records)
        finding = found["finding"]
        if not _shown(found) or not finding:
            return None
        day = words["onDay"].format(weekday=words["weekdays"][finding["day"]]) if finding.get("day") is not None else ""
        if finding["kind"] == "oneHour":
            return words["oneHour"].format(start=_clock(finding["hour"]), end=_clock(finding["hour"] + 1))
        if finding["kind"] == "window":
            return words["window"].format(start=_clock(finding["from"]), end=_clock(finding["to"]), day=day)
        return words["windows"].format(first=_clock(finding["hours"][0]), second=_clock(finding["hours"][1]), day=day)
    if kind == "plannedActual":
        found = patterns.planned_actual(records)
        finding = found["finding"]
        if not _shown(found) or not finding:
            return None
        if finding["kind"] == "close":
            return words["close"]
        return words[finding["kind"]].format(area=words["areas"][finding["key"]], percent=abs(finding["percent"]))
    if kind == "estimates":
        found = patterns.estimates(records, start, end)
        finding = found["finding"]
        if not _shown(found) or not finding:
            return None
        # Estimates that matched at first say so, rather than "up from 0 min".
        kind = "upFromSpot" if finding["kind"] == "up" and not finding["before"] else finding["kind"]
        return words[kind].format(now=minutes_words(finding["now"], language),
                                  before=minutes_words(finding.get("before") or 0, language))
    if kind == "energy":
        found = patterns.energy(records, energy_days)
        finding = found["finding"]
        if not _shown(found) or not finding or finding["kind"] == "never":
            return None
        if finding["kind"] == "hardly":
            return words["hardly"]
        return words[finding["kind"]].format(group=words["groups"][finding["group"]], percent=abs(finding["percent"]))
    if kind == "outcome":
        found = patterns.outcome(records, whole)
        finding = found["finding"]
        if not _shown(found) or not finding:
            return None
        if finding["noReply"]:
            return words["outcomeNoReply"].format(share=finding["share"], minutes=minutes_words(finding["noReply"], language))
        return words["outcome"].format(share=finding["share"])
    found = patterns.reporting(records, whole, day_end)
    if not _shown(found) or not found["finding"]:
        return None
    return words["reporting"].format(share=found["finding"]["now"])


def _task_lines(profiles: list[dict], words: dict, language: str) -> list[str]:
    """Up to MOST_TASK_LINES lines about single tasks: those often skipped or left without a status, then those that
    usually take other than planned, the furthest first."""
    often = [words[kind].format(title=profile["title"], count=count, scheduled=profile["scheduled"])
             for profile in profiles for kind, count in often_signals(profile)]
    differing = sorted((profile for profile in profiles
                        if profile.get("done", 0) >= USUAL_DONE and profile.get("doneMinutes") is not None
                        and profile.get("lastMinutes") and abs(profile["doneMinutes"] - profile["lastMinutes"]) >= USUAL_DIFFERENCE),
                       key=lambda profile: -abs(profile["doneMinutes"] - profile["lastMinutes"]))
    usual = [words["usual"].format(title=profile["title"], taken=minutes_words(profile["doneMinutes"], language),
                                   planned=minutes_words(profile["lastMinutes"], language)) for profile in differing]
    return [*often, *usual][:MOST_TASK_LINES]


def _goal_lines(goals: list[dict], today: str, words: dict, language: str) -> list[str]:
    """Each active goal's momentum, the latest active first, up to MOST_GOALS: how many of its tasks are done, how many
    of them in the last RECENT_DAYS days, and when the last was; or how long nothing was done, from IDLE_DAYS."""
    active = sorted((goal for goal in goals if goal["status"] == "active"), key=lambda goal: goal["lastDone"] or "",
                    reverse=True)
    lines = []
    for goal in active[:MOST_GOALS]:
        if not goal["done"] or goal["lastDone"] is None:
            lines.append(words["goalNone"].format(title=goal["title"]))
            continue
        idle = (date.fromisoformat(today) - date.fromisoformat(goal["lastDone"])).days
        key = "goalIdle" if idle >= IDLE_DAYS else "goalRecent" if goal["recent"] else "goal"
        lines.append(words[key].format(title=goal["title"], done=goal["done"], recent=goal["recent"], days=idle,
                                       day=day_words(goal["lastDone"], language)))
    return lines


def lines(records: list[dict], energy_days: list[dict], profiles: list[dict], goals: list[dict], today: str,
          language: str, day_end: str = DAY_END) -> dict[str, list[str]]:
    """The summary's lines in the interface's language.

    Args:
        records: Every task as Database.pattern_records gives them, from the first recorded day to today.
        energy_days: Each day with energy reported, its "date" and "average" (see Database.energy_days).
        profiles: The area agents' task profiles, each with its "title" (see Database.task_profiles).
        goals: Each goal's momentum, as Database.goal_momentum gives it.
        today: YYYY-MM-DD.
        language: "en" or "zh".
        day_end: Your day's end, after which a status counts as set the next day.

    Returns:
        {ALL_TIME: [...], LAST_THIRTY: [...]}: from every record, its tally, then each figure that reaches its threshold,
        then the tasks and goals worth naming; and from the last RECENT_DAYS days, their tally and figures. When every
        record lies within those days, ALL_TIME words both sets' figures and LAST_THIRTY is empty.
    """
    words = _WORDS[language]
    if not records:
        return {ALL_TIME: [], LAST_THIRTY: []}
    first = min(record["date"] for record in records)
    recent_start = (date.fromisoformat(today) - timedelta(days=RECENT_DAYS - 1)).isoformat()
    longer = first < recent_start
    figures = _ALL_TIME_FIGURES if longer else (*_ALL_TIME_FIGURES, *(kind for kind in _RECENT_FIGURES
                                                                       if kind not in _ALL_TIME_FIGURES))
    all_time = [_tally(records, words), *(_figure(kind, records, energy_days, first, today, words, language, day_end)
                                          for kind in figures)]
    all_time = [line for line in all_time if line] + _task_lines(profiles, words, language) + _goal_lines(goals, today, words, language)
    recent: list[str] = []
    if longer:
        held = [record for record in records if record["date"] >= recent_start]
        recent = [line for line in (_tally(held, words), *(_figure(kind, held, [day for day in energy_days
                                                                                 if day["date"] >= recent_start],
                                                                     recent_start, today, words, language, day_end)
                                                           for kind in _RECENT_FIGURES)) if line]
    return {ALL_TIME: all_time[:MOST_LINES - len(recent)], LAST_THIRTY: recent}


def context(summary: dict[str, list[str]]) -> str:
    """The summary as the model reads it, in English: both sets, each named; nothing when it holds no line."""
    words = _WORDS["en"]
    parts = [f"{words[name]}: " + " ".join(summary[name]) for name in (ALL_TIME, LAST_THIRTY) if summary[name]]
    return f"{words['context']} " + " ".join(parts) if parts else ""


def of_store(store, today: str, language: str) -> dict[str, list[str]]:
    """The summary of a workspace's records, as lines gives it: every record to today, as Patterns reads them."""
    first = store.first_record_date() or today
    return lines(store.pattern_records(first, today)["records"], store.energy_days(first, today),
                 list(store.task_profiles().values()),
                 store.goal_momentum(today, (date.fromisoformat(today) - timedelta(days=RECENT_DAYS - 1)).isoformat()),
                 today, language, store.your_day()["end"])
