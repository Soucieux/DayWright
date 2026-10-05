"""Lunch and dinner: the times every plan keeps free, standing from a day on, or for one day alone.

The times are saved as settings under PREFERENCE_KEY:

- "standing": changes that hold from their day on, each {"from", "meal", "start", "minutes"}; for a
  meal, the latest one from on or before a day is in force that day, so earlier days keep the
  times they had;
- "days": changes for one date alone, {date: {meal: {"start", "minutes"}}}, which win over the
  standing times on their date, until a later standing change from that date or before replaces them.

A meal ends by midnight, at 24:00 at the latest.

A meal nothing has changed keeps its default time (DEFAULT_MEALS).
"""

from __future__ import annotations

from dataclasses import dataclass

# The preference that holds the saved meal times.
PREFERENCE_KEY = "meals"
# A moved meal may not take the first minutes of an estimated task, and a plan never shortens one
# below them to make room for a meal.
KEPT_ESTIMATE_MINUTES = 30
# A moved meal that overlaps what today's set plan places by this many minutes or fewer, in all, is
# fitted into the plan in place; one that overlaps more puts the plan up for review.
SMALL_MEAL_OVERLAP_MINUTES = 30


@dataclass(frozen=True)
class Meal:
    """A meal a plan keeps free: its title, its "HH:MM" start, and how long it lasts."""

    title: str
    start: str
    minutes: int

    @property
    def end(self) -> str:
        """When the meal ends, "HH:MM"."""
        hours, minutes = map(int, self.start.split(":"))
        return f"{(hours * 60 + minutes + self.minutes) // 60:02d}:{(minutes + self.minutes) % 60:02d}"


# The meals by key, at the times they keep until changed: lunch 12:00–13:00 and dinner 18:00–19:00.
DEFAULT_MEALS = {"lunch": Meal("Lunch", "12:00", 60), "dinner": Meal("Dinner", "18:00", 60)}


def meals_on(day: str, settings: dict) -> tuple[Meal, ...]:
    """Return lunch and dinner as they are on a day.

    Args:
        day: The YYYY-MM-DD date.
        settings: The saved meal times, as this module's description lays out; empty for none.

    Returns:
        Lunch, then dinner: each the day's own time, else the standing time in force that day, else
        its default.
    """
    return tuple(_meal_on(day, key, default, settings) for key, default in DEFAULT_MEALS.items())


def listed_meals(day: dict) -> tuple[Meal, ...]:
    """Return the meals a day lists as the service gives it ("meals"), or the usual ones when it lists none.

    Args:
        day: The day as the service shows it; each meal has "title", "start_time" and "duration_minutes".
    """
    listed = day.get("meals")
    if listed is None:
        return tuple(DEFAULT_MEALS.values())
    return tuple(Meal(meal["title"], meal["start_time"], meal["duration_minutes"]) for meal in listed)


def _meal_on(day: str, key: str, default: Meal, settings: dict) -> Meal:
    """One meal as it is on a day; see meals_on."""
    own = settings.get("days", {}).get(day, {}).get(key)
    if own:
        return Meal(default.title, own["start"], own["minutes"])
    in_force = [change for change in settings.get("standing", []) if change["meal"] == key and change["from"] <= day]
    if in_force:
        latest = max(in_force, key=lambda change: change["from"])
        return Meal(default.title, latest["start"], latest["minutes"])
    return default


def standing(settings: dict, key: str, start: str, minutes: int, from_day: str) -> dict:
    """Return the settings with a meal moved from a day on; the settings given stay as they were.

    A standing change from the same day replaces one made before it, and so does it the meal's
    one-day changes from that day on (see one_day_changes); those before it stay.
    """
    kept = [change for change in settings.get("standing", []) if not (change["meal"] == key and change["from"] == from_day)]
    days = {day: {meal: times for meal, times in meals.items() if not (meal == key and day >= from_day)}
            for day, meals in settings.get("days", {}).items()}
    return {**settings, "standing": [*kept, {"from": from_day, "meal": key, "start": start, "minutes": minutes}],
            "days": {day: meals for day, meals in days.items() if meals}}


def one_day_changes(settings: dict, key: str, from_day: str) -> list[tuple[str, Meal]]:
    """Return a meal's one-day changes from a day on, which a standing change from that day replaces.

    Args:
        settings: The saved meal times, as this module's description lays out.
        key: "lunch" or "dinner".
        from_day: The YYYY-MM-DD date the standing change holds from.

    Returns:
        Each change's date and the meal as it was set for that day, by date.
    """
    return sorted((day, Meal(DEFAULT_MEALS[key].title, meals[key]["start"], meals[key]["minutes"]))
                  for day, meals in settings.get("days", {}).items() if key in meals and day >= from_day)


def one_day(settings: dict, key: str, start: str, minutes: int, day: str) -> dict:
    """Return the settings with a meal moved on one day alone; the settings given stay as they were."""
    days = settings.get("days", {})
    return {**settings, "days": {**days, day: {**days.get(day, {}), key: {"start": start, "minutes": minutes}}}}
