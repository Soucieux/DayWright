"""The work schedule set in Settings › Schedule, as it holds on one day.

It is one range of hours on the weekdays the user ticked, either working hours, which plans keep free, or focus
time, which holds the day's Work (see planner.DayRules). It holds on none of the other days, on no statutory holiday
while holidays are on, and nowhere while it is off.
"""

from __future__ import annotations

from datetime import date


def day_schedule(schedule: dict, day: str, holiday: dict | None = None) -> dict | None:
    """Return the work schedule as it holds on `day`: its "mode", "start" and "end"; None when it doesn't.

    Args:
        schedule: The work schedule kept (see app_settings.AppSettings.work_schedule).
        day: The day, as "YYYY-MM-DD".
        holiday: The statutory holiday the day is, when holidays are on.
    """
    if not schedule.get("enabled") or holiday or date.fromisoformat(day).weekday() not in schedule.get("days", ()):
        return None
    return {key: schedule[key] for key in ("mode", "start", "end")}
