from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Iterable


DOMAIN_LABELS = {
    "learning": "Learn",
    "life": "Life",
    "finance": "Money",
    "rest": "Rest",
}


@dataclass(frozen=True)
class PlanItem:
    start: str
    title: str
    detail: str
    domain: str
    duration_minutes: int
    constraint: str = "flexible"
    protected: bool = False


BASE_PLAN = (
    PlanItem("08:00", "French listening", "Podcast + notes (Beginner A2)", "learning", 60),
    PlanItem("09:00", "Deep work — Course project", "Build section 2 and write notes", "learning", 90),
    PlanItem("10:30", "Strength session", "Gym · Full body", "life", 60, "fixed"),
    PlanItem("11:30", "Shower & clear inbox", "Tidy up and prep for afternoon", "life", 30),
    PlanItem("12:00", "Lunch", "Good food, short walk", "life", 60),
    PlanItem("13:00", "Budget review", "Check spending, update categories", "finance", 45),
    PlanItem("14:00", "Open buffer", "Use for catch-up or personal task", "life", 90),
    PlanItem("15:30", "Course project", "Continue build + polish", "learning", 90),
    PlanItem("17:00", "Prepare for call", "Review notes and agenda", "life", 30),
    PlanItem("17:30", "Call with Alex", "Project sync", "life", 60, "fixed"),
    PlanItem("18:30", "Evening reset", "Journal, plan tomorrow, wind down", "rest", 30),
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
        {"name": "Balanced", "slug": "balanced", "rationale": "Steady progress across learning, life, and money with a protected buffer.", "items": balanced},
        {"name": "Focused", "slug": "focused", "rationale": "Uses the open buffer for the course milestone while preserving fixed commitments.", "items": focused},
        {"name": "Gentle", "slug": "gentle", "rationale": "Shortens deep work and protects more recovery time for a lower-energy day.", "items": gentle},
    )


def build_recorded_variants(
    items: Iterable[PlanItem], memory: Iterable[dict] = (),
    guidance: Iterable[dict] = (),
) -> tuple[dict, ...]:
    """Build alternatives from owned items and repeated shortening requests."""
    frequent = {(signal["taskTitle"], signal["domain"])
                for signal in memory if signal["shortenRequests"] >= 2}
    original = tuple(sorted(items, key=lambda item: item.start))
    if not original or has_collisions(original):
        raise ValueError("Add non-overlapping timed items before building a day plan")
    balanced = tuple(sorted((
        replace(item, duration_minutes=max(15, item.duration_minutes - 15))
        if item.constraint == "flexible" and item.duration_minutes > 15
        and (item.title, item.domain) in frequent else item
        for item in original
    ), key=lambda item: item.start))

    variants = [{
        "name": "Balanced", "slug": "balanced",
        "rationale": ("Keeps your times and commitments; repeated shortening requests reduce "
                      "flexible blocks by 15 minutes but never remove them."), "items": balanced,
    }]
    focus_item = next((item for domain in ("learning", "finance", "life")
                       for item in balanced if item.domain == domain
                       and item.constraint == "flexible"
                       and (item.title, item.domain) not in frequent), None)
    focused = tuple(replace(item, duration_minutes=item.duration_minutes + 15)
                    if item == focus_item else item for item in balanced)
    if focus_item and not has_collisions(focused):
        variants.append({
            "name": "Focused", "slug": "focused",
            "rationale": (f"Adds 15 minutes to {focus_item.title} where the saved calendar has room; "
                          "fixed times and repeatedly disliked tasks stay unchanged."),
            "items": focused,
        })
    gentler_domains = [item["domain"] for item in guidance
                       if item["content"].startswith("Review the size or timing of ")]
    gentler_domains += [domain for domain in ("learning", "finance", "life", "rest")
                        if domain not in gentler_domains]
    gentle_item = next((item for domain in gentler_domains
                        for item in balanced if item.domain == domain
                        and item.constraint == "flexible" and item.duration_minutes > 15), None)
    gentle = tuple(replace(item, duration_minutes=max(15, item.duration_minutes - 15))
                   if item == gentle_item else item for item in balanced)
    if gentle_item:
        variants.append({
            "name": "Gentle", "slug": "gentle",
            "rationale": (f"Shortens {gentle_item.title} by 15 minutes, never removes it; "
                          "fixed commitments stay unchanged."),
            "items": gentle,
        })
    return tuple(variants)


def minutes_by_domain(items: Iterable[PlanItem]) -> dict[str, int]:
    totals = {domain: 0 for domain in DOMAIN_LABELS}
    for item in items:
        totals[item.domain] += item.duration_minutes
    return totals


def has_collisions(items: Iterable[PlanItem]) -> bool:
    ordered = sorted(items, key=lambda item: item.start)
    day_end = datetime.strptime("00:00", "%H:%M") + timedelta(days=1)
    if any(datetime.strptime(item.start, "%H:%M") + timedelta(
        minutes=item.duration_minutes) > day_end for item in ordered):
        return True
    for current, following in zip(ordered, ordered[1:]):
        current_end = datetime.strptime(current.start, "%H:%M") + timedelta(
            minutes=current.duration_minutes
        )
        if current_end > datetime.strptime(following.start, "%H:%M"):
            return True
    return False
