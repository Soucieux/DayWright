"""The one-time repair, at v5.6's first start in the user's own workspace, of repeats copied forward without their
series: before v5.6 a repeat a day's plan carried onto that day got a copy that belonged to no series. Each such copy
is linked to the one series it unambiguously belongs to, after a backup of the database, in one transaction, once.
A copy that can't be told apart stays as it is, a record of its own; nothing is ever deleted."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from .database import Database

# The repair's name in data_repairs, which records that it ran, so it never runs again.
REPAIR = "repeat-series-5.6"
# The folder, in DayWright's data folder, that keeps the database as it was before the repair.
BACKUPS_FOLDER = "Backups"
# The backup's name, by the day of the first attempt: its start and its end around that date.
_BACKUP_PREFIX = "daywright-before-5.6-"
_BACKUP_SUFFIX = ".sqlite"


class _NoBackup(Exception):
    """The backup couldn't be written, so the repair doesn't start."""


def repair_repeats(store: Database, today: date) -> str | None:
    """Link each repeat copied without its series to the one series it matches, once; see the module.

    A copy matches a series when it has the title, area and repeat kind of the series' own day it follows, on a day
    inside the series' run: from its first day until a recorded stop, with a switched kind matched from the day of
    the switch, and a weekly one on the series' weekday. No match, or more than one, leaves the copy as it is.

    The database is backed up first, inside the same write lock, to BACKUPS_FOLDER beside it; without a backup
    nothing changes. Any error rolls everything back; both leave it to run at the next start.

    Returns:
        The line for the service's log saying what it did, or None when it ran before.
    """
    backup: Path | None = None
    try:
        with store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT 1 FROM data_repairs WHERE name = ?", (REPAIR,)).fetchone():
                return None
            copies = connection.execute(
                """SELECT id, item_date, title, domain, repeat_kind FROM daily_items
                   WHERE repeat_kind != 'none' AND repeat_series_id IS NULL ORDER BY item_date, rowid""").fetchall()
            if copies:
                backup = _back_up(Path(store.path), today)
                linked, ambiguous, outside = _link(connection, copies)
                line = (f"repeat repair: {linked} linked, {ambiguous + outside} left unlinked ({ambiguous} ambiguous, "
                        f"{outside} outside every run), backup {backup}")
            else:
                line = "repeat repair: 0 linked, 0 left unlinked (0 ambiguous, 0 outside every run), no backup needed"
            connection.execute("INSERT INTO data_repairs (name, ran_at, outcome) VALUES (?, ?, ?)",
                               (REPAIR, datetime.now(timezone.utc).isoformat(), line))
            return line
    except _NoBackup as error:
        return f"repeat repair: skipped, the backup couldn't be written ({error}); nothing changed"
    except Exception as error:  # Never in the way of DayWright opening: the data stays as it was, and it runs again.
        return f"repeat repair: failed ({error}); nothing changed, backup {backup}"


def _back_up(database: Path, today: date) -> Path:
    """Copy `database` to BACKUPS_FOLDER beside it, and check the copy: the one backup an earlier attempt made, if
    any, refreshed, as the data may have changed since; else a new one named by `today`. The copy is written beside it
    and moved in once whole, so a backup there is never lost to one that failed.

    Called while the repair holds the database's write lock, which nothing else can then change: the copy is read
    through a connection of its own, as SQLite's backup never finishes from the connection holding that lock, and the
    database's write-ahead log lets it read meanwhile.

    Raises:
        _NoBackup: For a backup that couldn't be written, or doesn't read back whole.
    """
    folder = database.parent / BACKUPS_FOLDER
    making = folder / f"{_BACKUP_PREFIX}making"
    try:
        folder.mkdir(exist_ok=True)
        earlier = sorted(folder.glob(f"{_BACKUP_PREFIX}*{_BACKUP_SUFFIX}"))
        path = earlier[0] if earlier else folder / f"{_BACKUP_PREFIX}{today.isoformat()}{_BACKUP_SUFFIX}"
        making.unlink(missing_ok=True)
        source, target = sqlite3.connect(database), sqlite3.connect(making)
        try:
            source.backup(target)
            checked = target.execute("PRAGMA quick_check").fetchone()[0]
        finally:
            source.close()
            target.close()
        if checked != "ok":
            raise _NoBackup(f"the copy reads back as {checked}")
        making.replace(path)
    except (OSError, sqlite3.Error) as error:
        raise _NoBackup(error) from error
    return path


def _link(connection: sqlite3.Connection, copies: list[sqlite3.Row]) -> tuple[int, int, int]:
    """Link each copy matching exactly one series, as the series stood before any copy was linked.

    Returns:
        How many were linked, matched more than one series, and matched none.
    """
    days: dict[str, list[sqlite3.Row]] = {}
    for row in connection.execute(
            """SELECT repeat_series_id AS series, item_date, title, domain, repeat_kind FROM daily_items
               WHERE repeat_series_id IS NOT NULL ORDER BY item_date, rowid"""):
        days.setdefault(row["series"], []).append(row)
    changes = {row["id"]: row for row in connection.execute("SELECT id, next_kind, next_from FROM repeat_series")}
    linked = ambiguous = outside = 0
    for copy in copies:
        found = [series for series, own in days.items() if _matches(copy, own, changes.get(series))]
        if len(found) == 1:
            connection.execute("UPDATE daily_items SET repeat_series_id = ? WHERE id = ?", (found[0], copy["id"]))
            linked += 1
        elif found:
            ambiguous += 1
        else:
            outside += 1
    return linked, ambiguous, outside


def _matches(copy: sqlite3.Row, own: list[sqlite3.Row], change: sqlite3.Row | None) -> bool:
    """Whether `copy` belongs to the series whose own days are `own`, earliest first, and whose recorded stop or
    switch, if any, is `change`; see repair_repeats."""
    day = copy["item_date"]
    if day < own[0]["item_date"]:
        return False
    follows = [row for row in own if row["item_date"] <= day][-1]
    if change is not None and day >= change["next_from"]:
        kind, weekday_of = change["next_kind"], change["next_from"]
    else:
        kind, weekday_of = follows["repeat_kind"], follows["item_date"]
    if kind == "none" or (copy["title"], copy["domain"], copy["repeat_kind"]) != (follows["title"], follows["domain"], kind):
        return False
    return kind != "weekly" or date.fromisoformat(day).weekday() == date.fromisoformat(weekday_of).weekday()
