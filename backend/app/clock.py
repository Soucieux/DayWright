"""Clock times as DayWright writes them, "HH:MM", and the minutes after midnight they stand for, which the meals,
the planner and every module that places or reads a time share."""


def minutes_after_midnight(clock: str) -> int:
    """Return minutes after midnight for an "HH:MM" time."""
    hours, minutes = clock.split(":")
    return int(hours) * 60 + int(minutes)


def clock_time(minutes: int) -> str:
    """Return the "HH:MM" time `minutes` after midnight."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"
