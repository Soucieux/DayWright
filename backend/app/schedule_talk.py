"""What the user tells Ava about the work schedule and statutory holidays, in English and Chinese: one whole schedule
to set, turn on or turn off (see schedule), or one place to import holidays for (see holidays). Each brings one card,
pencilled until confirmed.
"""

from __future__ import annotations

import re

from .holiday_places import COUNTRIES, COUNTRY_NAMES_ZH, REGION_NAMES
from .memory import days_in, times_in

# The words naming each kind of work schedule.
_WORKING = re.compile(r"\b(?:working|work)\s+hours?\b|工作时间", re.IGNORECASE)
_FOCUS = re.compile(r"\bfocus\s+time\b|专注时间", re.IGNORECASE)
# Turning the schedule off, or on as it is kept.
_OFF = re.compile(r"\b(?:turn|switch)\b.*\boff\b|\bdisable\b|关闭|关掉|停用", re.IGNORECASE)
_ON = re.compile(r"\b(?:turn|switch)\b.*\bon\b|\benable\b|打开|开启|启用", re.IGNORECASE)
# A range of hours said with no am or pm, as in "9 to 6" or "8:30-4:30".
_PLAIN_RANGE = re.compile(r"\b(\d{1,2})(?::([0-5]\d))?\s*(?:-|–|—|to|until|till)\s*(\d{1,2})(?::([0-5]\d))?\b",
                          re.IGNORECASE)
# An hour below this, said with no am or pm at a range's start, is the afternoon's: "1 to 5" is 13:00–17:00.
MORNING_FROM = 7
_CLOCK = re.compile(r"([01]\d|2[0-3]):[0-5]\d")

# Asking to import holidays, and the place named: "import Ontario's holidays", "import the statutory holidays for
# Quebec", "导入安大略省的法定假日".
_IMPORT = re.compile(r"\bimport\b.*\bholidays?\b", re.IGNORECASE)
_PLACE = re.compile(r"\bimport\s+(?:(.*?)\s*(?:'s|’s)?\s+)?holidays?\b(?:\s+(?:for|in|of)\s+(.+?))?\s*[.!?]*$",
                    re.IGNORECASE)
_IMPORT_ZH = re.compile(r"导入(.*?)(?:的)?(?:法定)?(?:节假日|假日|假期)")
# Words around a place's name that name none.
_FILLER = {"the", "my", "our", "statutory", "public", "national"}
# The ending a Chinese region's name may be said with or without.
_ZH_ENDING = re.compile(r"(省|地区|州)$")


def _hours(message: str) -> tuple[str, str] | None:
    """The range of hours a message names, as "HH:MM" start and end, or None.

    A second end said with no am or pm that comes at or before the first is the afternoon's ("9 to 6" ends at 18:00),
    and so is a first end with no am or pm before MORNING_FROM.
    """
    said = times_in(message)
    if len(said) >= 2:
        start, end = said[0], said[1]
        if end <= start and end < "12:00":
            end = f"{int(end[:2]) + 12:02d}{end[2:]}"
        return start, end
    plain = _PLAIN_RANGE.search(message)
    if not plain:
        return None
    first, first_minute, last, last_minute = int(plain[1]), int(plain[2] or 0), int(plain[3]), int(plain[4] or 0)
    if first < MORNING_FROM:
        first += 12
    if (last, last_minute) <= (first, first_minute) and last < 12:
        last += 12
    return f"{first:02d}:{first_minute:02d}", f"{last:02d}:{last_minute:02d}"


def schedule_request(message: str, current: dict) -> dict | None:
    """Read a message setting the work schedule, turning it on or turning it off.

    Args:
        message: What the user said.
        current: The work schedule kept (see app_settings.AppSettings.work_schedule); its days hold when the message
            names none, and all of it when the schedule is turned off or on.

    Returns:
        {"schedule": the whole schedule asked for}, or {"problem": why it can't be} when its hours don't make a range
        in the day; None when the message names working hours or focus time with no range of hours and no on or off.
    """
    mode = "focus" if _FOCUS.search(message) else "working" if _WORKING.search(message) else None
    if mode is None:
        return None
    if _OFF.search(message):
        return {"schedule": {**current, "enabled": False}}
    hours = _hours(message)
    if hours is None:
        return {"schedule": {**current, "enabled": True, "mode": mode}} if _ON.search(message) else None
    start, end = hours
    if not (_CLOCK.fullmatch(start) and _CLOCK.fullmatch(end)) or start >= end:
        return {"problem": f"{'Focus time' if mode == 'focus' else 'Working hours'} need an end after their start, "
                           "within the day"}
    return {"schedule": {"enabled": True, "mode": mode, "start": start, "end": end,
                         "days": list(days_in(message) or current["days"])}}


def place_named(text: str) -> dict | None:
    """The country, and region if one, a place's name means, by its English name, or its Chinese one where DayWright
    has it (see holiday_places); None for a place DayWright doesn't know. A country comes before a region of the same
    name."""
    wanted = text.strip().casefold()
    plain = _ZH_ENDING.sub("", text.strip())
    for code, name in COUNTRIES:
        if wanted == name.casefold() or plain == COUNTRY_NAMES_ZH.get(code):
            return {"country": code, "region": None}
    for code, names in REGION_NAMES.items():
        if wanted == names["en"].casefold() or (names.get("zh") and plain == _ZH_ENDING.sub("", names["zh"])):
            return {"country": code[:2], "region": code}
    return None


def holiday_request(message: str) -> dict | None:
    """Read a message asking to import statutory holidays.

    Returns:
        The place's name as said ("named", None when none is) with the "country" and "region" it means (both None
        for a place DayWright doesn't know); None when the message doesn't ask to import holidays.
    """
    chinese = _IMPORT_ZH.search(message)
    if chinese:
        named = chinese.group(1).strip()
    elif _IMPORT.search(message):
        asked = _PLACE.search(message.strip())
        said = asked and (asked.group(2) or " ".join(word for word in (asked.group(1) or "").split()
                                                      if word.casefold() not in _FILLER))
        named = (said or "").strip()
    else:
        return None
    if not named:
        return {"named": None, "country": None, "region": None}
    return {"named": named, **(place_named(named) or {"country": None, "region": None})}
