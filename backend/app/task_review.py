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
# The latest reported energy, out of 5, at or below which the Life agent asks for a lighter day.
LOW_ENERGY = 2


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
    """Return what an area agent's own records add beyond its tasks, if anything.

    Learning reports all its sessions so far; Life its latest daily state and its habit reports,
    asking for a lighter day when energy is low; Work the fixed meetings on the day. Project keeps
    no records of its own.

    Args:
        agent: The reviewing agent's key.
        items: The day's tasks.
        evidence: The area records of the days before, by area, with Life's latest check-in only
            when it is recent (see AgentOrchestrator.review_history).
        today: The area's own records on the day itself; a Life check-in made that day is the
            latest one, ahead of any before it.

    Returns:
        At most one finding, for the whole area.
    """
    base = {"agent": agent, "domain": agent}
    if agent == "learning":
        learning = evidence.get("learning") or {}
        if not learning.get("sessions"):
            return []
        return [{**base, "kind": "area-learning", "sessions": learning["sessions"],
                 "minutes": learning["minutes"], "done": learning["done"], "subjects": learning["items"]}]
    if agent == "life":
        life = evidence.get("life") or {}
        checked_in = (today or {}).get("daily")
        latest = life.get("latestDaily")
        if checked_in:
            daily = {"date": checked_in["date"], "energy": checked_in["energyLevel"], "sleep": checked_in["sleepHours"]}
        elif latest:
            daily = {"date": latest["daily_date"], "energy": latest.get("energy_level"), "sleep": latest.get("sleep_hours")}
        else:
            daily = None
        if not daily and not life.get("habitReports"):
            return []
        energy = daily["energy"] if daily else None
        return [{**base, "kind": "area-life", "date": daily["date"] if daily else None,
                 "energy": energy, "sleep": daily["sleep"] if daily else None,
                 "habitDone": life.get("habitDone", 0), "habitReports": life.get("habitReports", 0),
                 "lighter": energy is not None and energy <= LOW_ENERGY}]
    if agent == "work":
        fixed = [item for item in items if item["domain"] == "work" and item["constraint_kind"] == "fixed"
                 and item.get("acceptance", "accepted") == "accepted"]
        if not fixed:
            return []
        return [{**base, "kind": "area-work", "fixed": len(fixed),
                 "minutes": sum(int(item["duration_minutes"]) for item in fixed)}]
    return []
