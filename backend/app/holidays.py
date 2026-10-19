"""Statutory holidays, from Nager.Date (date.nager.at), which DayWright reaches only when the user imports them in
Settings › Schedule or confirms Ava's card to.

Import fetches this year's and next year's public holidays for the country chosen, national and regional alike, and
keeps them in HOLIDAYS_FILE beside the settings; the region chosen then picks among them without another fetch. An
Import that fails changes nothing. Plans, Today, the Calendar, the agents and Ava read the list kept, never the
network.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import urlopen  # Looked up at each fetch, so tests can stand in for the network.

# Where the holidays come from, and the address of one country's holidays for one year.
SOURCE_HOST = "date.nager.at"
SOURCE = "https://date.nager.at/api/v3/PublicHolidays/{year}/{country}"
# The file the holidays imported are kept in, in DayWright's data folder beside the settings.
HOLIDAYS_FILE = "holidays.json"
# How long one year's fetch may take before the Import says it failed.
FETCH_SECONDS = 15
# The month and day from which Today reminds the user to import next year's holidays while they are missing.
REMINDER_FROM = (12, 1)
# Nager.Date's kind of holiday DayWright keeps: a day off by law. Bank, school, optional and observed days are not.
KEPT_TYPE = "Public"


class ImportFailed(Exception):
    """Nager.Date couldn't be reached, or didn't answer with a list of holidays."""


def parse(payload: object) -> list[dict]:
    """Return the statutory holidays in Nager.Date's answer for one year, in its order.

    Each has its "date" ("YYYY-MM-DD"), its English "name", its "localName", and the "regions" it holds in, by
    ISO 3166-2 code, or None when it holds in the whole country.

    Raises:
        ImportFailed: When the answer isn't a list of holidays.
    """
    if not isinstance(payload, list):
        raise ImportFailed(f"{SOURCE_HOST} didn't answer with a list of holidays")
    kept = []
    for entry in payload:
        try:
            day = date.fromisoformat(entry["date"]).isoformat()
            name = str(entry["name"]).strip()
            local = str(entry.get("localName") or "").strip() or name
            types = entry.get("types") or []
            counties = entry.get("counties")
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            raise ImportFailed(f"{SOURCE_HOST} answered with a holiday DayWright can't read") from error
        if KEPT_TYPE in types and name:
            kept.append({"date": day, "name": name, "localName": local,
                         "regions": sorted(str(county) for county in counties) if counties else None})
    return kept


def fetch_year(country: str, year: int) -> list[dict]:
    """Fetch one year's statutory holidays for a country from Nager.Date (see parse).

    Raises:
        ImportFailed: When it can't be reached or answers with something else, saying which year.
    """
    try:
        with urlopen(SOURCE.format(year=year, country=country), timeout=FETCH_SECONDS) as response:
            payload = json.load(response)
    except (OSError, ValueError) as error:  # Offline, refused and timed out are OSErrors; a garbled answer a ValueError.
        raise ImportFailed(f"DayWright couldn't get {year}'s holidays from {SOURCE_HOST} ({error})") from error
    return parse(payload)


class Holidays:
    """The holidays imported, kept in one file: the "country", when they were imported ("importedAt", in UTC), the
    "years" imported, and the "holidays" themselves, by date (see parse).

    Args:
        path: The file, HOLIDAYS_FILE beside the settings.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def kept(self) -> dict | None:
        """Return the holidays kept, or None before the first Import or after they were removed."""
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None

    def import_years(self, country: str, years: tuple[int, ...]) -> dict:
        """Fetch each year's holidays for the country and keep them in place of any kept before.

        Every year is fetched before anything is written, so an Import that fails keeps what was there.

        Returns:
            The holidays kept now (see Holidays).

        Raises:
            ImportFailed: When one year's fetch fails.
        """
        found = [holiday for year in years for holiday in fetch_year(country, year)]
        kept = {"country": country, "importedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "years": sorted(years), "holidays": sorted(found, key=lambda holiday: holiday["date"])}
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handle, temporary = tempfile.mkstemp(prefix=".holidays-", dir=self.path.parent)
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(kept, stream, ensure_ascii=False, indent=2)
            os.replace(temporary, self.path)
        return kept

    def remove(self) -> None:
        """Forget every holiday imported."""
        with self._lock:
            self.path.unlink(missing_ok=True)


def _holds(holiday: dict, region: str | None) -> bool:
    """Whether a holiday holds in the region chosen: a national one everywhere, a regional one in its regions."""
    return holiday["regions"] is None or region in holiday["regions"]


def _shown(holiday: dict) -> dict:
    """A holiday as the interface, the agents and Ava read it: whether it is "regional" in place of its regions."""
    return {"date": holiday["date"], "name": holiday["name"], "localName": holiday["localName"],
            "regional": holiday["regions"] is not None}


def listed(kept: dict | None, country: str | None, region: str | None) -> list[dict]:
    """Return the holidays kept that hold in the country and region chosen, by date; none when the list kept is for
    another country."""
    if not kept or kept["country"] != country:
        return []
    return [_shown(holiday) for holiday in kept["holidays"] if _holds(holiday, region)]


def on(kept: dict | None, day: str, country: str | None, region: str | None) -> dict | None:
    """Return the holiday `day` is in the country and region chosen (see listed), or None."""
    return next((holiday for holiday in listed(kept, country, region) if holiday["date"] == day), None)


def regions(kept: dict | None, country: str | None) -> list[str]:
    """Return the regions with a holiday of their own in the list kept for the country, by code."""
    if not kept or kept["country"] != country:
        return []
    return sorted({region for holiday in kept["holidays"] for region in holiday["regions"] or ()})


def reminder(kept: dict | None, country: str | None, today: date) -> int | None:
    """Return next year when Today should remind the user to import its holidays: from REMINDER_FROM on, while the
    list kept for the country chosen doesn't have it; else None."""
    if not country or (today.month, today.day) < REMINDER_FROM:
        return None
    following = today.year + 1
    return None if kept and kept["country"] == country and following in kept["years"] else following
