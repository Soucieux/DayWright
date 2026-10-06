"""What an area agent finds when it reviews the day's tasks against everything it knows of them.

An agent knows each of its tasks from its profile, built from every record of the task (see
profiles). A finding names its agent, area and task (or the whole area), what the history shows, and
what the plans should do about it. Findings are data rather than prose, so the interface words them
in either language and the planner can act on them.
"""

from __future__ import annotations

from typing import Iterable

from .planner import ADJUST_MINUTES, MIN_TRIMMED_MINUTES

# Partly done or skipped reports that make an agent suggest a shorter block, when they are also at
# least half of the task's reports.
UNFINISHED_TO_SHORTEN = 2
# Done reports, and their share of all reports, that show a task's length works.
DONE_TO_KEEP = 2
KEEP_SHARE = 0.75
# Explicit requests to shorten a task that every plan acts on.
REQUESTS_TO_SHORTEN = 2
# The day's average energy, out of 5, at or below which the Life agent asks for a lighter day, and
# at or above which it sees a day for focused work.
LOW_ENERGY = 2
HIGH_ENERGY = 4


def profile_key(title: str, domain: str) -> tuple[str, str]:
    """The key a task's profile is kept under: its area, and its title in lower case without edge spaces."""
    return domain, title.strip().lower()


def _report_finding(base: dict, item: dict, past: dict) -> dict:
    """Say what a task's reports show: shorten it, keep its length, or neither yet."""
    done, partial, skipped = past["done"], past["partial"], past["skipped"]
    reported = done + partial + skipped
    counts = {"done": done, "partial": partial, "skipped": skipped, "reported": reported}
    if past.get("trend"):
        counts["trend"] = past["trend"]
    unfinished = partial + skipped
    minutes = int(item["duration_minutes"])
    if unfinished >= UNFINISHED_TO_SHORTEN and unfinished * 2 >= reported:
        first_step = item["detail"].strip().rstrip(".")
        if item["constraint_kind"] != "flexible":
            reason = "fixed"
        elif item.get("durationSource") == "user":
            reason = "yours"
        elif minutes <= MIN_TRIMMED_MINUTES:
            reason = "minimum"
        else:
            return {**base, "kind": "shorten", **counts, "fromMinutes": minutes,
                    "toMinutes": max(MIN_TRIMMED_MINUTES, minutes - ADJUST_MINUTES), "firstStep": first_step}
        return {**base, "kind": "hold", **counts, "reason": reason, "firstStep": first_step}
    if done >= DONE_TO_KEEP and done >= reported * KEEP_SHARE:
        return {**base, "kind": "keep", **counts, "minutes": minutes}
    return {**base, "kind": "mixed", **counts}


def review_tasks(agent: str, items: Iterable[dict], profiles: dict[tuple[str, str], dict]) -> list[dict]:
    """Review each of an area's accepted tasks for the day against everything its agent knows of it.

    Args:
        agent: The reviewing agent's key, which is also the area it reviews.
        items: The day's tasks, as stored; tasks of other areas and ones still waiting for the
            user's Accept are skipped.
        profiles: The area's task profiles, keyed by profile_key (see Database.task_profiles).

    Returns:
        One finding per task, followed, for a task without a start time that is usually done at a
        steady time, by a finding naming that time.
    """
    findings = []
    for item in items:
        if item["domain"] != agent or item.get("acceptance", "accepted") != "accepted":
            continue
        base = {"agent": agent, "domain": item["domain"], "taskTitle": item["title"]}
        past = profiles.get(profile_key(item["title"], item["domain"]))
        requests = past["shortenRequests"] if past else 0
        minutes = int(item["duration_minutes"])
        flexible = item["constraint_kind"] == "flexible"
        # Plans shorten only a length an agent estimated; one the user set changes only when they say so.
        estimated = item.get("durationSource") != "user"
        if requests >= REQUESTS_TO_SHORTEN and flexible and estimated and minutes > MIN_TRIMMED_MINUTES:
            findings.append({**base, "kind": "asked-shorter", "requests": requests, "fromMinutes": minutes,
                             "toMinutes": max(MIN_TRIMMED_MINUTES, minutes - ADJUST_MINUTES)})
        elif past is None:
            findings.append({**base, "kind": "new"})
        elif not past["done"] + past["partial"] + past["skipped"]:
            findings.append({**base, "kind": "unreported", "scheduled": past["scheduled"]})
        else:
            findings.append(_report_finding(base, item, past))
        if past and flexible and item["start_time"] is None and past.get("usualStart"):
            findings.append({**base, "kind": "time", "preferredStart": past["usualStart"], "done": past["done"]})
    return findings


def review_area(agent: str, items: Iterable[dict], evidence: dict, today: dict | None = None) -> list[dict]:
    """Return what an area agent reads beyond its tasks, if anything.

    Learning reports when anything was last practised and its goals due for review; Life the
    day's energy, the average of its readings, and how its repeats went, asking for a lighter day
    at LOW_ENERGY or below and seeing a day for focused work at HIGH_ENERGY or above; Work the
    fixed meetings on the day. Project's goals reach the user as notices instead.

    Args:
        agent: The reviewing agent's key.
        items: The day's tasks.
        evidence: The days before, from Database.summary_facts: each area's repeats.
        today: The area's overview of the day itself (see DomainRecords.snapshot), whose energy
            alone counts: a day with none reported asks for nothing, whatever an earlier day said.

    Returns:
        At most one finding, for the whole area.
    """
    base = {"agent": agent, "domain": agent}
    if agent == "learning":
        overview = today or {}
        due = [goal["title"] for goal in overview.get("dueForReview", [])]
        if not due and not overview.get("lastPractised"):
            return []
        return [{**base, "kind": "area-learning", "lastPractised": overview.get("lastPractised"), "due": due}]
    if agent == "life":
        repeats = (evidence.get("repeats") or {}).get("life") or {"scheduled": 0, "done": 0}
        level = (today or {}).get("energy")
        if level is None and not repeats["scheduled"]:
            return []
        return [{**base, "kind": "area-life", "date": today["date"] if level is not None else None, "energy": level,
                 "repeatsDone": repeats["done"], "repeatsScheduled": repeats["scheduled"],
                 "lighter": level is not None and level <= LOW_ENERGY,
                 "focused": level is not None and level >= HIGH_ENERGY}]
    if agent == "work":
        fixed = [item for item in items if item["domain"] == "work" and item["constraint_kind"] == "fixed"
                 and item.get("acceptance", "accepted") == "accepted"]
        if not fixed:
            return []
        return [{**base, "kind": "area-work", "fixed": len(fixed),
                 "minutes": sum(int(item["duration_minutes"]) for item in fixed)}]
    return []
