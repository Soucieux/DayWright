"""The smaller periods a Summary report breaks down into: all time into months, a month into weeks,
and a week into days. Calendar can't pick one particular week or month, so a wider report lists the
next level down instead.
"""

from __future__ import annotations

from datetime import date, timedelta


def period_keys(day: date) -> tuple[tuple[str, str], ...]:
    """Return the saved Summary reports a day falls in, as (kind, key) pairs.

    Args:
        day: The day.

    Returns:
        Its own report's key ("2026-10-02"), its ISO week's ("2026-W40") and its month's ("2026-10").
    """
    year, week, _ = day.isocalendar()
    return ("day", day.isoformat()), ("week", f"{year}-W{week:02d}"), ("month", day.strftime("%Y-%m"))


def _next_month(day: date) -> date:
    """Return the first day of the month after the one `day` falls in."""
    return (day.replace(day=28) + timedelta(days=4)).replace(day=1)


def sections(kind: str, start: date, end: date, today: date) -> list[tuple[str, date, date]]:
    """List the periods one level down that make up a period, newest first, and none after today.

    Args:
        kind: The period: "week" (into days), "month" (into ISO weeks) or "all" (into months); a
            day has no smaller parts.
        start: Its first day; for "all", the first day anything was recorded.
        end: Its last day.
        today: Today; nothing after it is listed, and a part reaching past it ends there.

    Returns:
        Each part's key ("2026-10-03", "2026-W40" or "2026-10") with its first and last day, each
        kept inside the period.
    """
    end = min(end, today)
    found: list[tuple[str, date, date]] = []
    if kind == "week":
        found = [((start + timedelta(days=offset)).isoformat(), start + timedelta(days=offset),
                  start + timedelta(days=offset)) for offset in range((end - start).days + 1)]
    elif kind == "month":
        cursor = start - timedelta(days=start.weekday())
        while cursor <= end:
            year, week, _ = cursor.isocalendar()
            found.append((f"{year}-W{week:02d}", max(cursor, start), min(cursor + timedelta(days=6), end)))
            cursor += timedelta(days=7)
    elif kind == "all":
        cursor = start.replace(day=1)
        while cursor <= end:
            found.append((cursor.strftime("%Y-%m"), max(cursor, start), min(_next_month(cursor) - timedelta(days=1), end)))
            cursor = _next_month(cursor)
    # A part of a period still to come can start after today; it has nothing to show.
    return [part for part in found[::-1] if part[1] <= part[2]]
