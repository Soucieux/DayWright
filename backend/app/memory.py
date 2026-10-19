"""Ava's long-term memory of what the user says: notes she weighs, and rules plans obey.

A note is guidance in the user's own words, English or Chinese, at most WORD_LIMIT words (see wording), tagged with
an area or General: Ava, the area agents and Summary weigh it, and nothing enforces it. A rule is firm, and one of
three kinds (RULE_FIELDS): keep a time free on certain days; keep an area or a task off certain days; or finish by a
latest time on certain days. Plans always obey the rules of their day (see day_rules and planner.DayRules); a rule
never blocks the user's own edits, and a task placed against one names it (rule_breaks). Every entry keeps the day
it was said ("saidOn") and may end on a day of its own ("endsOn"), after which it is past and no longer read.

The local model proposes what kind a statement is; the service reads every field of a rule from the statement's own
words (days_in, times_in, until_in and the area words) and keeps it a rule only when they fill every field of its
kind. Anything else is kept as a note, never half a rule, with the fields the rule still needs, which its card lets
the user fill. Nothing is kept twice: the same entry said again is a duplicate, and one that changes an entry is an
update of it (see read_statement).
"""

from __future__ import annotations

import calendar
import json
import re
from datetime import date

from .planner import DayRules, fold_title, minutes_after_midnight
from .wording import WORD_LIMIT, count_words, cut_words

# The areas a note is tagged with: one of the four, or General; a rule keeps one of the four off a day.
MEMORY_AREAS = ("learning", "life", "work", "project", "general")
RULE_AREAS = MEMORY_AREAS[:4]
# The fields each kind of rule needs, in the order its card asks for them; "area" is an area or a task kept off.
RULE_FIELDS = {"keep-free": ("start", "end", "days"), "keep-off": ("area", "days"), "finish-by": ("latest", "days")}
EVERY_DAY = tuple(range(7))
WEEKDAYS = (0, 1, 2, 3, 4)
WEEKEND = (5, 6)
# How an entry reads in English, as Ava says it and the service's own words name it.
_KIND_WORDS = {"keep-free": "Keep free", "keep-off": "Keep off", "finish-by": "Finish by"}
_AREA_WORDS = {"learning": "Learn", "life": "Life", "work": "Work", "project": "Project", "general": "General"}
_DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTH_NAMES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

# What asks Ava outright to remember, in English or Chinese, taken off the words kept.
REMEMBER = re.compile(r"^\s*(?:please\s+)?(?:remember|note)\s+(?:that\s+|this\s*[:：]\s*|[:：]\s*)?|^\s*(?:请)?记住\s*[:：，,]?\s*",
                      re.IGNORECASE)
# What a lasting statement sounds like, for Ava to offer to remember it unasked: a habit, a preference, a priority,
# something every week or from now on, or what plans should never do. Only these reach the model.
LASTING = re.compile(
    r"\b(?:always|never|usually|normally|generally|every|each|from now on|going forward|any more|anymore|prefer|"
    r"i (?:really )?(?:like|love|hate|dislike|need|tend)|i don'?t like|i(?:'m| am) (?:a |an )?(?:morning|night|early|evening)|"
    r"best (?:in|at|after|before)|my (?:priority|focus|goal|exam|deadline)|most important|"
    r"don'?t (?:schedule|put|plan|book)|do not (?:schedule|put|plan|book)|keep\b.*\b(?:free|clear|off)|"
    r"no (?:work|meetings|tasks|study|studying|learning|projects?)\b|(?:done|finish(?:ed)?) by|nothing (?:after|before)|"
    r"weekdays|weekends|mondays|tuesdays|wednesdays|thursdays|fridays|saturdays|sundays)\b"
    r"|总是|从不|从来不|每天|每周|每个|通常|一般|习惯|我喜欢|我讨厌|我不喜欢|以后|不要安排|别安排|留出|空出|最重要|工作日|周末|之前结束|前结束|以后不",
    re.IGNORECASE)

# What the model reads to propose what a statement is (see read_statement, which checks it against the words).
CLASSIFY_ROLE = (
    "You are the memory of Ava, the assistant in DayWright, a day planner. Read one thing the user said and say "
    "whether it is lasting, worth remembering beyond today, and what kind it is. A RULE is firm and is one of three "
    "kinds: keep-free (keep a time range free on certain days), keep-off (keep an area, learning, life, work or "
    "project, or one named task off certain days), or finish-by (have the day done by a time on certain days). A NOTE "
    "is anything else lasting: a preference, a habit, a fact about the user, a priority, guidance. Something about "
    "today or one occasion only is not lasting. A range of times kept clear or set aside is keep-free; nothing after "
    "a time, or done by a time, is finish-by; keep-off names whole days and never a time. When the words say "
    "something a rule would say, answer rule with its kind even if a time or a day is missing; DayWright checks the "
    "words itself. Give a task only for keep-off, as the words name it. A note's area is learning, life, work or "
    "project when it is about one of them, else general. When it changes one of the listed entries, give that "
    "entry's id. Examples: \"Keep 12:30–13:30 free every day\": rule keep-free. \"Wednesday 7-8pm is for piano\": "
    "rule keep-free. \"周日下午2点到4点不要安排\": rule keep-free. \"Keep mornings free\": rule keep-free. \"No project "
    "work on Sundays\": rule keep-off, area project. \"Keep Swimming off Mondays\": rule keep-off, task Swimming. "
    "\"周六不安排学习\": rule keep-off, area learning. \"Be done by 5pm on Fridays\": rule finish-by. \"Nothing after "
    "20:00 on weekdays\": rule finish-by. \"晚上10点以后不安排\": rule finish-by. \"I read best at night\": note, "
    "learning. \"Long calls tire me\": note, work. \"I like a slow start\": note, general. \"我喜欢早上跑步\": note, "
    "life. \"Finishing the website matters most to me\": note, project; a priority is a note, never a rule. \"I'm busy "
    "tonight\": not lasting. Answer with JSON only."
)
CLASSIFY_REQUEST = (
    'Reply exactly in this form: {"lasting": true or false, "kind": "rule" or "note", "rule": "keep-free" or '
    '"keep-off" or "finish-by" or null, "area": "learning" or "life" or "work" or "project" or "general" or null, '
    '"task": "<the task it keeps off, as written>" or null, "updates": "<the id of the entry it changes>" or null}'
)
# How much the model may write: one small object.
CLASSIFY_MAX_TOKENS = 120
# The most entries the model is shown beside a statement, the newest first.
CLASSIFY_ENTRIES = 30
# The first JSON object in an answer, which may be wrapped in other words or a code block.
_OBJECT = re.compile(r"\{.*\}", re.DOTALL)

# Days, in English: a name, singular or plural (an abbreviation only with its capital, so "I sat" names no day), a
# range of names, and the words for weekdays, weekends and every day. "This Monday" or "next weekend" is one day,
# not a lasting one, and names none.
_EN_DAY = (r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)s?"
           r"|(?-i:Mon|Tues?|Wed|Thur?s?|Fri|Sat|Sun)s?")
_EN_DAY_INDEX = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
_ONE_OFF = r"(?<!this\s)(?<!next\s)(?<!last\s)(?<!coming\s)"
_EN_RANGE = re.compile(rf"{_ONE_OFF}\b({_EN_DAY})\s*(?:-|–|—|to|through|thru|until|till)\s*({_EN_DAY})\b", re.IGNORECASE)
_EN_NAME = re.compile(rf"{_ONE_OFF}\b({_EN_DAY})\b", re.IGNORECASE)
_EN_GROUPS = ((re.compile(rf"{_ONE_OFF}\b(?:weekdays|workdays|week\s*days|working\s+days|work\s*days)\b", re.IGNORECASE), WEEKDAYS),
              (re.compile(rf"{_ONE_OFF}\bweekends?\b", re.IGNORECASE), WEEKEND),
              (re.compile(r"\b(?:every\s*day|everyday|daily|each\s+day|all\s+week|every\s+(?:morning|afternoon|evening|night))\b",
                          re.IGNORECASE), EVERY_DAY))
# Days, in Chinese: 周一 to 周日 (or 星期, 礼拜), ranges such as 周一到周五, 工作日, 周末 and 每天. "这周末" or "下周一" is
# one day, not a lasting one.
_ZH_DAYS = "一二三四五六日天"
_ZH_DAY = r"(?:周|星期|礼拜)([一二三四五六日天])"
_ZH_ONE_OFF = r"(?<![这下上本])"
_ZH_RANGE = re.compile(rf"{_ZH_ONE_OFF}{_ZH_DAY}\s*(?:到|至|~|-|—|–)\s*(?:周|星期|礼拜)?([一二三四五六日天])")
_ZH_NAME = re.compile(rf"{_ZH_ONE_OFF}{_ZH_DAY}")
_ZH_GROUPS = ((re.compile(r"工作日"), WEEKDAYS), (re.compile(rf"{_ZH_ONE_OFF}周末"), WEEKEND),
              (re.compile(r"每天|每日|天天"), EVERY_DAY))

# Times, in English: "18:00", "6pm", "6:30 pm", and a range whose first end has no am or pm of its own, as in
# "6-7pm", "between 12 and 1pm" or "11 to 1pm".
_MERIDIEM = r"(am|pm|a\.m\.|p\.m\.)"
_EN_TIME_RANGE = re.compile(rf"\b(\d{{1,2}})(?::([0-5]\d))?\s*(?:-|–|—|~|to|and|until|till)\s*(\d{{1,2}})(?::([0-5]\d))?\s*{_MERIDIEM}",
                            re.IGNORECASE)
_EN_TIME = re.compile(rf"\b(\d{{1,2}})(?::([0-5]\d))?\s*{_MERIDIEM}|\b([01]?\d|2[0-4]):([0-5]\d)\b", re.IGNORECASE)
# Times, in Chinese: "18点", "下午3点半", "晚上8点", with a range's second end taking the first one's part of the day,
# as in "下午3点到5点半" or "中午12点到1点".
_ZH_PART = r"(凌晨|早上|上午|中午|下午|傍晚|晚上)?"
_ZH_CLOCK = r"(\d{1,2})\s*[点點时時](?:\s*(半|(\d{1,2})\s*分?))?"
_ZH_TIME_RANGE = re.compile(rf"{_ZH_PART}\s*{_ZH_CLOCK}\s*(?:到|至|~|-|—|–)\s*{_ZH_PART}\s*{_ZH_CLOCK}")
_ZH_TIME = re.compile(rf"{_ZH_PART}\s*{_ZH_CLOCK}")
# How each part of the day moves an hour.
_AFTERNOON = ("下午", "傍晚", "晚上")

# An end date: "until 31 Dec", "till December 20th", "until the end of January", "until January", "until 2027-02-01",
# "到12月31日为止", "直到11月底".
_MONTHS = ("january|jan", "february|feb", "march|mar", "april|apr", "may", "june|jun", "july|jul", "august|aug",
           "september|sept|sep", "october|oct", "november|nov", "december|dec")
_MONTH = "|".join(_MONTHS)
_UNTIL = r"\b(?:until|till|til|through|thru)\s+(?:the\s+end\s+of\s+)?"
_UNTIL_ISO = re.compile(rf"{_UNTIL}(\d{{4}})-(\d{{1,2}})-(\d{{1,2}})\b|(?:到|至|直到)\s*(\d{{4}})-(\d{{1,2}})-(\d{{1,2}})", re.IGNORECASE)
_UNTIL_DAY = re.compile(rf"{_UNTIL}(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH})\b|{_UNTIL}({_MONTH})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b",
                        re.IGNORECASE)
_UNTIL_MONTH = re.compile(rf"{_UNTIL}({_MONTH})\b", re.IGNORECASE)
_ZH_UNTIL_DAY = re.compile(r"(?:到|至|直到)\s*(\d{1,2})\s*月\s*(\d{1,2})\s*[日号號]")
_ZH_UNTIL_MONTH = re.compile(r"(?:到|至|直到)\s*(\d{1,2})\s*月底")
# Words that say a time is when the day is done by.
_FINISH = re.compile(r"\b(?:after|by|before|no later than|latest)\b|以后|之后|以前|之前|前", re.IGNORECASE)

# The words that name an area a rule keeps off a day; a day's own words ("工作日", "working days") never do.
_AREA_NAMES = (("work", re.compile(r"\b(?:work|working|job)\b|工作", re.IGNORECASE)),
               ("learning", re.compile(r"\b(?:learning|learn|study|studying|studies|lessons?)\b|学习", re.IGNORECASE)),
               ("life", re.compile(r"\b(?:life|personal|chores|errands)\b|生活", re.IGNORECASE)),
               ("project", re.compile(r"\bprojects?\b|项目", re.IGNORECASE)))

# The words that say what an entry is about, to tell a change to it from a new entry beside it (see _topic_words):
# English words of three letters or more and Chinese pairs of characters, without the words any statement might hold,
# nor the days and times of day many entries share.
_EN_WORD = re.compile(r"[a-z]{3,}")
_EN_COMMON = frozenset((
    "the and but for with after before about from into than then when what that this these those its you your are "
    "was were has have had not now too also just very really much more less most some any all every each don can won "
    "isn didn usually always often never sometimes like love hate prefer want need best better remember please keep "
    "free off done finish nothing time times day days week weeks morning mornings afternoon afternoons evening "
    "evenings night nights weekday weekdays weekend weekends monday mondays tuesday tuesdays wednesday wednesdays "
    "thursday thursdays friday fridays saturday saturdays sunday sundays mon tue tues wed thu thur thurs fri sat "
    "sun").split())
_ZH_RUN = re.compile(r"[一-鿿]+")
_ZH_COMMON = re.compile(r"喜欢|通常|一般|总是|习惯|每天|以后|不要|安排|时间|早上|上午|中午|下午|晚上|工作日|周末"
                        r"|(?:周|星期|礼拜)[一二三四五六日天]|[我你的了是在都很最也就还要会不和与把给对]")


def spoken(statement: str) -> str:
    """A statement as it is kept: without the words asking Ava to remember it, its spaces run together."""
    return " ".join(REMEMBER.sub("", statement, count=1).split())


def _en_day(word: str) -> int:
    return _EN_DAY_INDEX[word.lower()[:3]]


def _span(first: int, last: int) -> tuple[int, ...]:
    """The days from `first` to `last`, through the weekend when `last` comes before `first`."""
    return tuple((first + step) % 7 for step in range((last - first) % 7 + 1))


def _day_phrases(text: str) -> tuple[set[int], list[tuple[int, int]]]:
    """The days a text names, and where it names them."""
    found: set[int] = set()
    spans: list[tuple[int, int]] = []

    def take(match: re.Match, days) -> None:
        if any(start < match.end() and match.start() < end for start, end in spans):
            return
        spans.append(match.span())
        found.update(days)

    for match in _EN_RANGE.finditer(text):
        take(match, _span(_en_day(match[1]), _en_day(match[2])))
    for match in _ZH_RANGE.finditer(text):
        take(match, _span(_ZH_DAYS.index(match[1]) % 7 if match[1] != "天" else 6,
                          _ZH_DAYS.index(match[2]) % 7 if match[2] != "天" else 6))
    for pattern, days in (*_EN_GROUPS, *_ZH_GROUPS):
        for match in pattern.finditer(text):
            take(match, days)
    for match in _EN_NAME.finditer(text):
        take(match, (_en_day(match[1]),))
    for match in _ZH_NAME.finditer(text):
        take(match, (6 if match[1] == "天" else _ZH_DAYS.index(match[1]),))
    return found, spans


def days_in(text: str) -> tuple[int, ...] | None:
    """The days of the week a statement names, as lasting ones, 0 (Monday) to 6 (Sunday); None when it names none."""
    found, _ = _day_phrases(text)
    return tuple(sorted(found)) or None


def _clock(hour: int, minute: int) -> str | None:
    return f"{hour:02d}:{minute:02d}" if 0 <= hour <= 24 and 0 <= minute < 60 and (hour, minute) <= (24, 0) else None


def _meridiem(hour: int, mark: str) -> int:
    """An hour on the 12-hour clock as one on the 24-hour clock."""
    return hour % 12 + (12 if mark.lower().startswith("p") else 0)


def _zh_hour(part: str | None, hour: int) -> int:
    """An hour said with a part of the day, as one on the 24-hour clock: 下午3点 is 15:00, 中午1点 13:00."""
    if part in _AFTERNOON and hour < 12:
        return hour + 12
    if part == "中午" and hour <= 3:
        return hour + 12
    return hour


def _zh_minute(half: str | None, minutes: str | None) -> int:
    return 30 if half == "半" else int(minutes or 0)


def times_in(text: str) -> list[str]:
    """The clock times a statement names, "HH:MM", in the order it names them; a range's ends both, its first taking
    the second's am or pm, or its part of the day in Chinese, when it has none of its own."""
    found: list[tuple[int, int, str]] = []

    def take(start: int, end: int, *times: str | None) -> None:
        if any(first < end and start < last for first, last, _ in found) or not all(times):
            return
        found.extend((start, end, time) for time in times)

    for match in _EN_TIME_RANGE.finditer(text):
        later = _meridiem(int(match[3]), match[5])
        # The first end takes the second's am or pm, unless that puts it after the second, as 11 in "11 to 1pm" is.
        sooner = _meridiem(int(match[1]), match[5])
        if (sooner, int(match[2] or 0)) > (later, int(match[4] or 0)):
            sooner = _meridiem(int(match[1]), "am" if match[5].lower().startswith("p") else "pm")
        take(*match.span(), _clock(sooner, int(match[2] or 0)), _clock(later, int(match[4] or 0)))
    for match in _ZH_TIME_RANGE.finditer(text):
        part = match[1]
        take(*match.span(), _clock(_zh_hour(part, int(match[2])), _zh_minute(match[3], match[4])),
             _clock(_zh_hour(match[5] or part, int(match[6])), _zh_minute(match[7], match[8])))
    for match in _EN_TIME.finditer(text):
        if match[1]:
            take(*match.span(), _clock(_meridiem(int(match[1]), match[3]), int(match[2] or 0)))
        else:
            take(*match.span(), _clock(int(match[4]), int(match[5])))
    for match in _ZH_TIME.finditer(text):
        take(*match.span(), _clock(_zh_hour(match[1], int(match[2])), _zh_minute(match[3], match[4])))
    # A range's two times share its place, so the order they were said in is kept.
    return [time for _, _, time in sorted(found, key=lambda entry: entry[0])]


def _month(word: str) -> int:
    return next(index for index, names in enumerate(_MONTHS, 1) if word.lower() in names.split("|"))


def _next(today: date, month: int, day: int | None) -> str | None:
    """The next day with this month and day, from today on; with no day, the month's last day."""
    for year in (today.year, today.year + 1):
        last = calendar.monthrange(year, month)[1]
        try:
            chosen = date(year, month, day if day is not None else last)
        except ValueError:
            return None
        if chosen >= today:
            return chosen.isoformat()
    return None


def until_in(text: str, today: str) -> str | None:
    """The last day a statement says it holds, "YYYY-MM-DD": a date without a year is the next one from today, and a
    month alone its last day; None when it names none."""
    now = date.fromisoformat(today)
    if match := _UNTIL_ISO.search(text):
        parts = [int(value) for value in (match.groups()[:3] if match[1] else match.groups()[3:])]
        try:
            return date(*parts).isoformat()
        except ValueError:
            return None
    if match := _UNTIL_DAY.search(text):
        day, month = (match[1], match[2]) if match[1] else (match[4], match[3])
        return _next(now, _month(month), int(day))
    if match := _UNTIL_MONTH.search(text):
        return _next(now, _month(match[1]), None)
    if match := _ZH_UNTIL_DAY.search(text):
        return _next(now, int(match[1]), int(match[2]))
    if match := _ZH_UNTIL_MONTH.search(text):
        return _next(now, int(match[1]), None)
    return None


def _areas_in(text: str) -> list[str]:
    """The areas a statement names, its days' own words left out."""
    _, spans = _day_phrases(text)
    for start, end in sorted(spans, reverse=True):
        text = text[:start] + " " + text[end:]
    return [area for area, pattern in _AREA_NAMES if pattern.search(text)]


def _rule_fields(kind: str, words: str, proposal: dict) -> tuple[dict, list[str]]:
    """Read a rule of a kind from a statement's own words.

    The days, times and area come from the words alone; a task kept off is the one the model names, and only when
    the words name it too and no area.

    Returns:
        The fields the words fill, and those they leave missing, in RULE_FIELDS order.
    """
    fields: dict = {}
    days = days_in(words)
    if days:
        fields["days"] = list(days)
    times = times_in(words)
    if kind == "keep-free" and len(times) >= 2 and minutes_after_midnight(times[0]) < minutes_after_midnight(times[1]):
        fields["start"], fields["end"] = times[0], times[1]
    if kind == "finish-by" and len(times) == 1:
        fields["latest"] = times[0]
    areas = _areas_in(words)
    task = proposal.get("task")
    if kind == "keep-off":
        if len(areas) == 1:
            fields["area"] = areas[0]
        elif not areas and isinstance(task, str) and len(task.strip()) > 1 and fold_title(task) in fold_title(words):
            fields["task"] = " ".join(task.split())
    have = {"area" if name == "task" else name for name in fields}
    return fields, [name for name in RULE_FIELDS[kind] if name not in have]


def _fits(kind: str, words: str) -> bool:
    """Whether a statement's words have the shape of a kind of rule: a time kept free is a range of times, a time
    the day is done by is one time said with "after", "by" or "before" (以后, 之前, 前), and what is kept off a day
    holds no time at all."""
    times = times_in(words)
    if kind == "keep-off":
        return not times
    if kind == "finish-by":
        return len(times) == 1 and bool(_FINISH.search(words))
    return len(times) >= 2


def _days(entry: dict) -> tuple[int, ...]:
    return tuple(sorted(entry.get("days") or ()))


def _topic_words(wording: str) -> set[str]:
    """What an entry's words are about: its English words of three letters or more and its Chinese character pairs
    (a lone character between common words counts on its own), without the common ones (_EN_COMMON, _ZH_COMMON)."""
    words = set(_EN_WORD.findall(wording.lower())) - _EN_COMMON
    for run in _ZH_RUN.findall(wording):
        for part in filter(None, _ZH_COMMON.split(run)):
            words.update({part} if len(part) == 1 else {part[index:index + 2] for index in range(len(part) - 1)})
    return words


def _same_rule(entry: dict, other: dict) -> bool:
    """Whether two rules hold the same: kind, fields, days and end."""
    return (all(entry.get(name) == other.get(name) for name in ("ruleKind", "start", "end", "latest", "area", "endsOn"))
            and fold_title(entry.get("task") or "") == fold_title(other.get("task") or "") and _days(entry) == _days(other))


def _changes_rule(entry: dict, other: dict) -> bool:
    """Whether a new rule changes an earlier one rather than standing beside it: a task or area kept off again, a
    time kept free that overlaps on a shared day, or a finish on the same days."""
    if entry["ruleKind"] != other["ruleKind"]:
        return False
    if entry["ruleKind"] == "keep-off":
        return (entry.get("area") or None) == (other.get("area") or None) and (
            fold_title(entry.get("task") or "") == fold_title(other.get("task") or ""))
    if entry["ruleKind"] == "finish-by":
        return _days(entry) == _days(other)
    return bool(set(_days(entry)) & set(_days(other))) and (
        minutes_after_midnight(entry["start"]) < minutes_after_midnight(other["end"])
        and minutes_after_midnight(other["start"]) < minutes_after_midnight(entry["end"]))


def active(entry: dict, day: str) -> bool:
    """Whether an entry is read on a day: said by then, and not past its end."""
    return entry["saidOn"] <= day and (not entry.get("endsOn") or day <= entry["endsOn"])


def _against(entry: dict, entries: list[dict], proposal: dict) -> dict:
    """What a new reading of a statement is beside the entries already kept and not past: the same one again (a
    duplicate), a change to one of them (an update), or a new entry (an add)."""
    current = [other for other in entries if not other.get("endsOn") or other["endsOn"] >= entry["saidOn"]]
    if entry["kind"] == "rule":
        rules = [other for other in current if other["kind"] == "rule"]
        if same := next((other for other in rules if _same_rule(entry, other)), None):
            return {"outcome": "duplicate", "entry": entry, "updates": same["id"], "before": same}
        changed = next((other for other in rules if _changes_rule(entry, other)), None)
    else:
        notes = [other for other in current if other["kind"] == "note"]
        same = next((other for other in notes if fold_title(other["wording"]) == fold_title(entry["wording"])
                     and other.get("area") == entry["area"] and other.get("endsOn") == entry.get("endsOn")), None)
        if same:
            return {"outcome": "duplicate", "entry": entry, "updates": same["id"], "before": same}
        changed = None
    # The model may say which entry a statement changes: only one of the same kind, about the same thing (sharing a
    # word, see _topic_words), can be; any other stands beside the new entry, never replaced by it.
    named = proposal.get("updates")
    changed = changed or next((other for other in current if other["id"] == named and other["kind"] == entry["kind"]
                               and other.get("ruleKind") == entry.get("ruleKind")
                               and _topic_words(entry["wording"]) & _topic_words(other["wording"])), None)
    if changed:
        return {"outcome": "update", "entry": entry, "updates": changed["id"], "before": changed}
    return {"outcome": "add", "entry": entry}


def read_statement(statement: str, proposal: dict | None, today: str, entries: list[dict]) -> dict:
    """Read a statement as an entry to keep, from what the model proposes it is and the statement's own words.

    A rule is kept only when the words fill every field of its kind (see _rule_fields); otherwise the statement is
    kept as a note in its own words, cut to WORD_LIMIT words, tagged with the area its words name, or the model's,
    or General. A proposal that can't be read keeps it as a General note.

    Args:
        statement: What the user said, perhaps asking Ava to remember it.
        proposal: The model's reading: its "kind" ("rule" or "note"), "rule" (its kind), "area", "task" and the id of
            an entry it "updates"; None when it couldn't be read.
        today: The day it was said, YYYY-MM-DD.
        entries: Every entry kept, with its id; one past its end is never matched.

    Returns:
        "outcome" ("add", "duplicate" or "update"), the "entry" read, the id of the entry it "updates" and that entry
        "before" it; for a rule kept as a note, the "rule" kind proposed, the fields it still needs ("missing") and
        those its words filled ("ruleFields").
    """
    proposal = proposal if isinstance(proposal, dict) else {}
    words = spoken(statement)
    said = {"saidOn": today, "endsOn": until_in(words, today)}
    kind = proposal.get("rule")
    filled: dict = {}
    missing: list[str] = []
    if proposal.get("kind") == "rule" and kind in RULE_FIELDS:
        filled, missing = _rule_fields(kind, words, proposal)
        if missing or not _fits(kind, words):
            # The words have the shape of another kind, and fill it: that one, when it is the only one.
            fitting = [other for other in RULE_FIELDS if other != kind and _fits(other, words)
                       and not _rule_fields(other, words, proposal)[1]]
            if len(fitting) == 1:
                kind = fitting[0]
                filled, missing = _rule_fields(kind, words, proposal)
        if not missing:
            entry = {"kind": "rule", "ruleKind": kind, "wording": words, **filled, **said}
            return _against(entry, entries, proposal)
    named = proposal.get("area") if proposal.get("area") in MEMORY_AREAS else None
    area = filled.get("area") or named or "general"
    note = _against({"kind": "note", "area": area, "wording": cut_words(words), **said}, entries, proposal)
    return {**note, "rule": kind, "missing": missing, "ruleFields": filled} if missing else note


def _days_text(days) -> str:
    """Days as an entry reads them: "Every day", or runs as "Mon–Fri", the rest listed: "Mon, Wed, Fri"."""
    days = sorted(set(days or ()))
    if tuple(days) == EVERY_DAY:
        return "Every day"
    runs: list[list[int]] = []
    for day in days:
        if runs and day == runs[-1][-1] + 1:
            runs[-1].append(day)
        else:
            runs.append([day])
    return ", ".join(f"{_DAY_NAMES[run[0]]}–{_DAY_NAMES[run[-1]]}" if len(run) > 1 else _DAY_NAMES[run[0]] for run in runs)


def _date_text(day: str, said: str | None) -> str:
    """A date as an entry reads it: "31 Dec", with its year when that isn't the year it was said in."""
    shown = date.fromisoformat(day)
    year = f" {shown.year}" if said and said[:4] != day[:4] else ""
    return f"{shown.day} {_MONTH_NAMES[shown.month - 1]}{year}"


def entry_what(entry: dict) -> str:
    """What a rule holds, as Settings' table and its cards name it: its times, the area or task kept off, or the time
    the day is done by."""
    if entry["ruleKind"] == "keep-free":
        return f"{entry['start']}–{entry['end']}"
    if entry["ruleKind"] == "finish-by":
        return entry["latest"]
    return _AREA_WORDS[entry["area"]] if entry.get("area") else f"“{entry['task']}”"


def entry_line(entry: dict) -> str:
    """An entry in one line, as Ava reads and names it: "Rule · Keep free · 18:00–19:00 · Mon–Fri · until 31 Dec",
    "Note · Learn · I study best in the morning"."""
    until = [f"until {_date_text(entry['endsOn'], entry.get('saidOn'))}"] if entry.get("endsOn") else []
    if entry["kind"] == "note":
        return " · ".join(["Note", _AREA_WORDS[entry["area"]], entry["wording"], *until])
    return " · ".join(["Rule", _KIND_WORDS[entry["ruleKind"]], entry_what(entry), _days_text(entry.get("days")), *until])


def offer_key(entry: dict) -> str:
    """What identifies an entry Ava offered, so one the user dismissed is never offered again: its line, folded."""
    return fold_title(entry_line({**entry, "endsOn": None}))


def _clock_field(value, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d|24:00", value):
        raise ValueError(f"A rule's {name} is a time, HH:MM")
    return value


def checked_entry(entry: dict) -> dict:
    """An entry as it is kept, once every field it needs is there and right, as the user may have filled or changed
    them on a card or in Settings: a note's words (at most WORD_LIMIT) and area; a rule's kind, days (at least one)
    and the fields its kind needs (RULE_FIELDS), and nothing else; each its day said and its end, if any.

    Raises:
        ValueError: Saying what is missing or wrong.
    """
    said = entry.get("saidOn")
    ends = entry.get("endsOn") or None
    for name, value in (("day it was said", said), ("end", ends)):
        if value is not None:
            try:
                date.fromisoformat(value)
            except (TypeError, ValueError):
                raise ValueError(f"An entry's {name} is a date, YYYY-MM-DD") from None
    if not said:
        raise ValueError("An entry needs the day it was said")
    wording = " ".join(str(entry.get("wording") or "").split())
    base = {"wording": wording, "saidOn": said, "endsOn": ends, "area": None, "task": None, "start": None, "end": None,
            "latest": None, "days": [], "ruleKind": None}
    if entry.get("kind") == "note":
        if not wording:
            raise ValueError("A note needs its words")
        if count_words(wording) > WORD_LIMIT:
            raise ValueError(f"A note holds at most {WORD_LIMIT} words")
        if entry.get("area") not in MEMORY_AREAS:
            raise ValueError("A note is tagged Learn, Life, Work, Project or General")
        return {**base, "kind": "note", "area": entry["area"]}
    kind = entry.get("ruleKind")
    if entry.get("kind") != "rule" or kind not in RULE_FIELDS:
        raise ValueError("An entry is a note or a rule: keep free, keep off or finish by")
    days = entry.get("days")
    if not isinstance(days, list) or not days or not all(isinstance(day, int) and 0 <= day <= 6 for day in days):
        raise ValueError("A rule needs at least one day")
    rule = {**base, "kind": "rule", "ruleKind": kind, "days": sorted(set(days))}
    if kind == "keep-free":
        start, end = _clock_field(entry.get("start"), "start"), _clock_field(entry.get("end"), "end")
        if minutes_after_midnight(start) >= minutes_after_midnight(end):
            raise ValueError("A time kept free ends after it starts")
        return {**rule, "start": start, "end": end}
    if kind == "finish-by":
        return {**rule, "latest": _clock_field(entry.get("latest"), "latest time")}
    area, task = entry.get("area"), " ".join(str(entry.get("task") or "").split())
    if bool(area) == bool(task) or (area and area not in RULE_AREAS) or len(task) > 200:
        raise ValueError("A rule keeps off one area, or one task by its title")
    return {**rule, "area": area or None, "task": task or None}


def day_rules(entries: list[dict], day: str, schedule: dict | None = None, holiday: dict | None = None) -> DayRules:
    """What the rules in force on a day ask of its plans: each time they keep free, the earliest time it is done by,
    and the areas and tasks they keep off it. Notes never bind a plan.

    Args:
        entries: Every entry kept.
        day: The day, as "YYYY-MM-DD".
        schedule: The work schedule that holds on the day (see schedule.day_schedule): its "mode", "working" or
            "focus", with its "start" and "end".
        holiday: The statutory holiday the day is, with its "name"; on one the schedule doesn't apply.
    """
    weekday = date.fromisoformat(day).weekday()
    rules = [entry for entry in entries
             if entry["kind"] == "rule" and active(entry, day) and weekday in (entry.get("days") or ())]
    finishes = [entry["latest"] for entry in rules if entry["ruleKind"] == "finish-by"]
    hours = (schedule["start"], schedule["end"]) if schedule and not holiday else None
    return DayRules(
        free=tuple(sorted((entry["start"], entry["end"]) for entry in rules if entry["ruleKind"] == "keep-free")),
        finish_by=min(finishes, key=minutes_after_midnight) if finishes else None,
        off_areas=frozenset(entry["area"] for entry in rules if entry["ruleKind"] == "keep-off" and entry.get("area")),
        off_tasks=frozenset(fold_title(entry["task"]) for entry in rules if entry["ruleKind"] == "keep-off" and entry.get("task")),
        working=hours if hours and schedule["mode"] == "working" else None,
        focus=hours if hours and schedule["mode"] == "focus" else None,
        holiday=holiday["name"] if holiday else None)


def rule_breaks(item: dict, entries: list[dict]) -> list[dict]:
    """The rules a task breaks on its day, in the order they were kept: one keeping its area or title off the day,
    with or without a start time; one keeping a time free that its time overlaps; and one its time ends after. A
    task the user placed so still saves; its sheet names these.

    Args:
        item: The task: its "date", "title", "domain", "start_time" and "duration_minutes".
        entries: Every entry kept.
    """
    weekday = date.fromisoformat(item["date"]).weekday()
    start = item["start_time"] and minutes_after_midnight(item["start_time"])
    end = start + item["duration_minutes"] if item["start_time"] else None
    broken = []
    for entry in entries:
        if entry["kind"] != "rule" or not active(entry, item["date"]) or weekday not in (entry.get("days") or ()):
            continue
        kind = entry["ruleKind"]
        if ((kind == "keep-off" and (entry.get("area") == item["domain"]
                                      or (entry.get("task") and fold_title(entry["task"]) == fold_title(item["title"]))))
                or (kind == "keep-free" and end is not None and start < minutes_after_midnight(entry["end"])
                    and minutes_after_midnight(entry["start"]) < end)
                or (kind == "finish-by" and end is not None and end > minutes_after_midnight(entry["latest"]))):
            broken.append(entry)
    return broken


def parse_object(answer: str) -> dict | None:
    """The first JSON object in a model's answer, or None when it holds none."""
    match = _OBJECT.search(answer)
    if not match:
        return None
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def current(entries: list[dict], today: str) -> list[dict]:
    """The entries not past their end on a day: those Ava reads, and a statement can change."""
    return [entry for entry in entries if not entry.get("endsOn") or entry["endsOn"] >= today]


def classify(gateway, statement: str, entries: list[dict], today: str) -> dict | None:
    """Have the local model propose what a statement is, beside the newest CLASSIFY_ENTRIES entries not past (see
    CLASSIFY_ROLE); read_statement checks what it proposes against the statement's own words.

    Returns:
        The proposal, or None when the model isn't available or its answer can't be read.
    """
    shown = current(entries, today)[-CLASSIFY_ENTRIES:]
    listed = "\n".join(f"[{entry['id']}] {entry_line(entry)}" for entry in shown) or "none"
    answer, mode = gateway.reply(f"Statement: {spoken(statement)}\nEntries kept:\n{listed}\n{CLASSIFY_REQUEST}", "",
                                 system_prompt=CLASSIFY_ROLE, max_tokens=CLASSIFY_MAX_TOKENS)
    return None if mode == "rules" else parse_object(answer)


# Asking Ava to forget what was said about something: what goes is listed on one card, summaries of conversations too.
FORGET = re.compile(r"^\s*(?:please\s+)?forget\b|\bforget\s+(?:what|that|everything|about)\b|忘掉|忘记|别记|不要记", re.IGNORECASE)
# What the forgetting is about, taken in this order: the words after "about" or "关于", else what follows the asking;
# an article or "my" before it is left out.
_FORGET_TOPICS = (re.compile(r"\babout\s+(?:the\s+|a\s+|an\s+|my\s+|our\s+)?(.+?)[.!?。！？]*\s*$", re.IGNORECASE),
                  re.compile(r"关于\s*(.+?)\s*的"),
                  re.compile(r"(?:忘掉|忘记|别记|不要记)\s*(.+?)[。！]*\s*$"),
                  re.compile(r"^\s*(?:please\s+)?forget\s+(?:that\s+|the\s+|my\s+)?(.+?)[.!?]*\s*$", re.IGNORECASE))
# Asking to drop, end or change what Ava keeps, or saying something she keeps no longer holds or has changed.
CHANGE = re.compile(r"\b(?:drop|delete|remove|cancel|scrap|stop|end)\b.*\b(?:rules?|notes?)\b|\bno longer\b|\bnot any\s?more\b"
                    r"|\b(?:moved|changed|switched)\s+to\b|\bis now\b|删掉|删除|取消.*(?:规则|笔记)|不再|改到|改成|推迟到|提前到",
                    re.IGNORECASE)
CHANGE_ROLE = (
    "You keep the memory of Ava, the assistant in DayWright. The user said something that may change, end or delete "
    "entries Ava keeps. From the entries listed, and only those, say which it affects and how: update (what the entry "
    "says has changed, as \"my exam moved to January\" changes a note about the exam), end (it no longer holds, from "
    "today) or delete (the user wants it gone, as \"drop the Friday rule\" does). Give no entry it doesn't affect; "
    "give none when it affects none. Answer with JSON only."
)
CHANGE_REQUEST = 'Reply exactly in this form: {"changes": [{"id": "<entry id>", "op": "update" or "end" or "delete"}]}'
CHANGE_MAX_TOKENS = 160
# What each change does to an entry, in the order the card lists them.
CHANGE_OPS = ("update", "end", "delete")


def forget_topic(statement: str) -> str:
    """What a request to forget is about, in its own words: "Gym" in "Forget what I said about Gym"."""
    match = next((found for pattern in _FORGET_TOPICS if (found := pattern.search(statement))), None)
    return " ".join(match[1].split()) if match else ""


def mentions(text: str, topic: str) -> bool:
    """Whether a text names a topic, whatever its case and spacing."""
    return bool(topic) and fold_title(topic) in fold_title(text)


def proposed_changes(gateway, statement: str, entries: list[dict], today: str) -> list[dict] | None:
    """Have the local model say which kept entries a statement changes, ends or deletes, from the newest
    CLASSIFY_ENTRIES not past, and how (CHANGE_OPS); each is checked here.

    An update takes the new value from the user's own words: a note becomes those words, and a rule keeps its kind
    with every field read from them again (see read_statement); one they don't fill is left out, never half done.
    An end has the entry hold until yesterday; a delete removes it for good.

    Returns:
        Each change: its "op", the entry "before" it and, for an update or an end, the entry "after" it; None when
        the model isn't available or its answer can't be read.
    """
    shown = current(entries, today)[-CLASSIFY_ENTRIES:]
    if not shown:
        return []
    listed = "\n".join(f"[{entry['id']}] {entry_line(entry)}" for entry in shown)
    answer, mode = gateway.reply(f"Statement: {spoken(statement)}\nEntries kept:\n{listed}\n{CHANGE_REQUEST}", "",
                                 system_prompt=CHANGE_ROLE, max_tokens=CHANGE_MAX_TOKENS)
    data = None if mode == "rules" else parse_object(answer)
    if data is None or not isinstance(data.get("changes"), list):
        return None
    by_id = {entry["id"]: entry for entry in shown}
    yesterday = date.fromordinal(date.fromisoformat(today).toordinal() - 1).isoformat()
    changes, seen = [], set()
    for change in data["changes"]:
        entry = by_id.get(change.get("id")) if isinstance(change, dict) else None
        op = change.get("op") if entry else None
        if entry is None or op not in CHANGE_OPS or entry["id"] in seen:
            continue
        seen.add(entry["id"])
        if op == "delete":
            changes.append({"op": op, "before": entry})
        elif op == "end":
            changes.append({"op": op, "before": entry, "after": {**entry, "endsOn": yesterday}})
        elif entry["kind"] == "note":
            changes.append({"op": op, "before": entry, "after": {**entry, "wording": cut_words(spoken(statement)),
                                                                   "saidOn": today}})
        else:
            read = read_statement(statement, {"kind": "rule", "rule": entry["ruleKind"]}, today, [])
            if read["entry"]["kind"] == "rule":
                changes.append({"op": op, "before": entry, "after": {**read["entry"], "id": entry["id"]}})
    return sorted(changes, key=lambda change: CHANGE_OPS.index(change["op"]))
