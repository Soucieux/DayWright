"""What the user did, as the service answers a question about it in its own words (see facts): the exact records the
question names, the records nearest it by meaning, or its days of low or high energy.

Every task on a past day, and every day, is kept as a short document (see documents) in record_documents, embedded with
the Library's embedding model into record_vectors. sync keeps them in step with the records, embedding only what is new
or changed, BATCH at a time, so the first pass over a long history can stop and carry on at the next.

A question about what the user did (asks_records) is looked up (look_up) by the rows its words name, by the phrases
recognised (phrase_query) or, failing them, by the local model's search checked against the records (model_query), with
their totals over the whole matching history. One naming no task, goal or area also gets the records nearest it by
meaning, any already among the rows left out; one asking for days of low or high energy gets those days. The rows carry
every figure, read as Patterns reads them: a time to check is marked and left out of the time, and a task from before
times were kept says that it has none.
"""

from __future__ import annotations

import re
import threading
from datetime import date, timedelta
from typing import Iterable

from .agents import OFTEN_COUNT
from .calendar_words import AREA_NAMES, CHINESE_WEEKDAYS, WEEKDAYS
from .database import Database
from .how_you_work import USUAL_DIFFERENCE, day_words, minutes_words
from .memory import parse_object
from .model_gateway import ModelGateway
from .planner import DOMAIN_LABELS, DOMAIN_LABELS_ZH
from .retrieval import EmbeddingUnavailable, RagService
from .task_review import HIGH_ENERGY, LOW_ENERGY

# How many rows an answer lists, the rest counted; how many records by meaning it adds; how many documents are
# embedded at once.
ROWS_SHOWN = 20
MEANING_MATCHES = 8
BATCH = 32
# How many times more of the nearest records a question naming its days looks through, keeping those on its days.
DATED_WIDENING = 4
_TABLE = "record_vectors"

STATUS_WORDS = {"done": "Done", "partial": "Partly done", "skipped": "Skipped", "noReply": "Not done · no reply",
                "dayPaused": "Not done · paused"}
# The statuses a tally counts, with their words; noReply and dayPaused are both without a status.
_TALLIED = (("done", "done"), ("partial", "partly done"), ("skipped", "skipped"), ("unanswered", "without a status"))

# A question about what the user did, rather than a report of it or a request.
_ASKS = re.compile(
    r"\bhow\s+(?:often|many\s+times|much\s+time|long\s+did)\b|\b(?:did|have)\s+i\b"
    r"|\bwhen\s+(?:did\s+i|was\s+i|was\s+the\s+last)\b|\bwhat\s+did\s+i\b"
    r"|\bwhich\s+(?:\w+\s+)?(?:days?|tasks?)\s+(?:did|was|were)\s+i\b|\b(?:the\s+)?last\s+time\s+i\b|\bhow\s+much\b.*\bdid\s+i\b"
    r"|多少次|几次|多少时间|多长时间|花了多少|用了多少|做了什么|做了哪些|完成了哪些|完成了什么|上次|最近一次|有没有(?:做|完成|学)",
    re.IGNORECASE)
# A question about what the user said, wrote or noted rather than did.
_SAID_OR_NOTED = re.compile(r"\b(?:did|have)\s+i\s+(?:ever\s+)?(?:say|said|tell|told|mention(?:ed)?|talk(?:ed)?|note[sd]?|write|"
                            r"wrote|written|jot(?:ted)?|save[sd]?|read)\b|笔记|说过|提过|提到|告诉过|聊过", re.IGNORECASE)
# Days of low or high energy, as a question names them ("tired", "很累"; "full of energy", "精力充沛"), and the words that
# ask for past days by them: in English with a word of the past ("Which days was I tired?", "Was I worn out this
# week?"), never a condition ("If I'm drained, which days…"); in Chinese ("上周我哪几天很累") unless it states a habit or a
# plan ("我什么时候累了就休息"), as asking outright with a question mark doesn't.
_ENERGY_LOW = re.compile(r"\b(?:tired(?!\s+of)|exhausted|drained|worn\s+out|fatigued|sleepy|low\s+(?:on\s+)?energy)\b"
                         r"|(?<![积连])累(?![计积])|疲惫|疲劳|没精神|精力(?:不足|低|差)", re.IGNORECASE)
_ENERGY_HIGH = re.compile(r"\b(?:energetic|energi[sz]ed|full\s+of\s+energy|high\s+energy)\b|精力(?:充沛|好|高|足)|精神(?:好|足)",
                          re.IGNORECASE)
_ENERGY_ASKS_EN = re.compile(r"\b(?:which|what)\s+days?\b|\bwhen\s+(?:was|were|did)\s+i\b|\bhow\s+(?:often|many\s+days)\b"
                             r"|\b(?:was|were)\s+i\s+(?:\w+\s+)?(?:tired|exhausted|drained|worn|fatigued|sleepy|low|energetic|"
                             r"energi[sz]ed|full|high)\b", re.IGNORECASE)
_PAST_EN = re.compile(r"\b(?:was|were|did|had|felt|got|yesterday|ago|last|this\s+(?:week|month))\b", re.IGNORECASE)
_CONDITION_EN = re.compile(r"\b(?:if|whenever)\b", re.IGNORECASE)
_ENERGY_ASKS_ZH = re.compile(r"哪(?:一|几|些)?天|什么时候|几天|多少天")
_HABIT_ZH = re.compile(r"就|便|的话|每当|只要|如果|一旦")
_ASKED_OUTRIGHT = re.compile(r"[?？]\s*$")
_SINCE = re.compile(r"\bsince\b|以来|自从|从", re.IGNORECASE)
_SINCE_WEEKDAY = re.compile(rf"\bsince\s+({'|'.join(WEEKDAYS)})\b|(?:自从?|从)?(?:周|星期)([一二三四五六日天])(?:以来|开始)",
                            re.IGNORECASE)
_MONTH_WORDS = ("jan(?:uary)?", "feb(?:ruary)?", "mar(?:ch)?", "apr(?:il)?", "may", "june?", "july?", "aug(?:ust)?",
                "sep(?:t(?:ember)?)?", "oct(?:ober)?", "nov(?:ember)?", "dec(?:ember)?")
_IN_MONTH = re.compile(rf"\b(?:in|during)\s+(?:{'|'.join(f'({word})' for word in _MONTH_WORDS)})\b", re.IGNORECASE)
_CHINESE_NUMBERS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11,
                    "十二": 12}
_CHINESE_MONTH = re.compile(r"(?<![\d一二三四五六七八九十])(十[一二]?|[一二三四五六七八九]|1[0-2]|[1-9])月(?!\s*[\d一二三四五六七八九十]+\s*[日号號])")
_LAST_DAYS = re.compile(r"\b(?:in\s+)?(?:the\s+)?(?:last|past)\s+(\d{1,3})\s+days\b|(?:最近|过去)\s*(\d{1,3})\s*天", re.IGNORECASE)
# The ranges named in words, each from today: the phrase, then the first and last day.
_RANGES = (
    (re.compile(r"\bday\s+before\s+yesterday\b|前天", re.IGNORECASE), lambda today: (today - timedelta(days=2),) * 2),
    (re.compile(r"\byesterday\b|昨天", re.IGNORECASE), lambda today: (today - timedelta(days=1),) * 2),
    (re.compile(r"\blast\s+week\b|上周|上个星期|上星期", re.IGNORECASE),
     lambda today: (today - timedelta(days=today.weekday() + 7), today - timedelta(days=today.weekday() + 1))),
    (re.compile(r"\bthis\s+week\b|本周|这周|这个星期", re.IGNORECASE), lambda today: (today - timedelta(days=today.weekday()), today)),
    (re.compile(r"\blast\s+month\b|上个月|上月", re.IGNORECASE),
     lambda today: ((today.replace(day=1) - timedelta(days=1)).replace(day=1), today.replace(day=1) - timedelta(days=1))),
    (re.compile(r"\bthis\s+month\b|本月|这个月", re.IGNORECASE), lambda today: (today.replace(day=1), today)),
    (re.compile(r"\btoday\b|今天", re.IGNORECASE), lambda today: (today, today)),
)
_LAST = re.compile(r"\b(?:the\s+)?last\s+time\b|\bwhen\s+did\s+i\s+last\b|上次|最近一次", re.IGNORECASE)
_COUNT = re.compile(r"\bhow\s+(?:often|many\s+times)\b|几次|多少次", re.IGNORECASE)
# An area named outright, or by studying or working: "Learn tasks", "学习领域", "studied", "学习" (a 工作日 is a workday).
_AREA = re.compile(r"\b(learn(?:ing)?|life|work|project)\s+(?:area|tasks?)\b|(学习|生活|工作|项目)(?:领域|任务)"
                   r"|\b(stud(?:y|ied|ying))\b|(学习|工作)(?!日|领域|任务)", re.IGNORECASE)
_AREA_NAMES = {**AREA_NAMES, "learn": "learning", "study": "learning", "studied": "learning", "studying": "learning"}
_QUOTED = re.compile(r"[“\"「]([^”\"」]+)[”\"」]")
# A title is named as a word where it meets Latin letters or digits; beside Chinese, which has no spaces, anywhere.
_LATIN = "[A-Za-z0-9]"
# A goal is named by a word of its title this long, which no other goal's title has.
_GOAL_WORD = 5
# Where a citation of the records the model writes begins, anywhere in a line.
_CITE = re.compile(r"(?:From your records|From the user's records|(?:来自|从|根据)[你您]的记录)\s*[:：,，]", re.IGNORECASE)
# How an answer's facts are worded (see facts), in English and Chinese.
_FACTS = {
    "en": {"language": "en", "cite": "From your records: {row}", "part": ", ", "join": ", ", "end": ".",
           "toCheckRow": "time to check", "noTimeRow": "no time kept",
           "total": "{subject}{period}: {count} {noun}, {tally}; {minutes} counted", "tasks": ("task", "tasks"),
           "times": ("time", "times"), "toCheck": "; {count} time{plural} to check, left out until confirmed",
           "noTime": "; {count} from before times were kept, with no time",
           "tally": (("done", "{} done"), ("partial", "{} partly done"), ("skipped", "{} skipped"),
                     ("unanswered", "{} without a status")),
           "period": " from {first} to {last}", "on": " on {day}", "title": "“{title}”", "goal": "Goal “{goal}”",
           "area": "{area} tasks", "areas": DOMAIN_LABELS, "every": "Your tasks", "last": "{subject} was last on {day}.",
           "near": "Nearest your question in your records:", "also": "Also near your question:",
           "groups": "; ", "energy": "energy {level:.1f} of 5", "plan": "plan: {plan}", "dayTasks": "{count} {noun}: {tally}",
           "paused": "paused {spans}", "span": "{start}–{end}", "from": "from {start}",
           "energyTotal": "Days of {level} energy{period}: {count} {noun}.", "levels": {"low": "low", "high": "high"},
           "days": ("day", "days")},
    "zh": {"language": "zh", "cite": "来自你的记录：{row}", "part": "，", "join": "，", "end": "。",
           "toCheckRow": "用时待核对", "noTimeRow": "没有记录用时",
           "total": "{subject}{period}：共 {count} {noun}，{tally}；共计 {minutes}", "tasks": ("项任务", "项任务"),
           "times": ("次", "次"), "toCheck": "；{count} 项用时待核对，确认前不计入",
           "noTime": "；{count} 项来自开始记录用时之前，没有用时",
           "tally": (("done", "{} 项已完成"), ("partial", "{} 项部分完成"), ("skipped", "{} 项已跳过"),
                     ("unanswered", "{} 项没有状态")),
           "period": "（{first}至{last}）", "on": "（{day}）", "title": "“{title}”", "goal": "目标“{goal}”",
           "area": "{area}任务", "areas": DOMAIN_LABELS_ZH, "every": "你的任务", "last": "{subject}上一次在{day}。",
           "near": "你的记录中与问题最接近的：", "also": "与问题相近的还有：",
           "groups": "；", "energy": "精力 {level:.1f}/5", "plan": "计划：{plan}", "dayTasks": "{count} {noun}：{tally}",
           "paused": "暂停 {spans}", "span": "{start}–{end}", "from": "{start} 起",
           "energyTotal": "精力{level}的日子{period}：共 {count} {noun}。", "levels": {"low": "低", "high": "高"},
           "days": ("天", "天")},
}

SEARCH_ROLE = ("You turn a user's question about what they did into a search of their own records of tasks. Use only "
               "the tasks, goals and areas listed, and dates between the first day of the records and today. Leave "
               "out what the question doesn't name. Answer with JSON only.")
SEARCH_REQUEST = ('Reply exactly in this form: {"from": "YYYY-MM-DD" or null, "to": "YYYY-MM-DD" or null, '
                  '"task": a task listed or null, "goal": a goal listed or null, '
                  '"area": "learning", "life", "work", "project" or null}')
SEARCH_MAX_TOKENS = 80
# The most task titles the model is shown.
SEARCH_TITLES = 120

_SYNCING = threading.Lock()

# A remark Ava makes unasked about a task rests on its latest REMARK_LATEST records: a length when REMARK_TIMES or more
# of them were done in a time USUAL_DIFFERENCE minutes or more from the one asked, on average; that it keeps slipping
# when OFTEN_COUNT or more, and half of them, weren't done.
REMARK_LATEST = 5
REMARK_TIMES = 2
STATUS_WORDS_ZH = {"done": "已完成", "partial": "部分完成", "skipped": "已跳过", "noReply": "未完成 · 未回复",
                   "dayPaused": "未完成 · 已暂停"}
_NOT_DONE = ("skipped", "noReply", "dayPaused")
_REMARKS = {
    "en": {"length": "From your records: “{title}” took {average} on average the last {count} times it was done: {rows}.",
           "slipping": "From your records: “{title}” wasn't done {missed} of the last {count} times: {rows}.",
           "last": "From your records: “{title}” was last on {day}: {row}.", "join": "; ", "part": ", "},
    "zh": {"length": "来自你的记录：“{title}”最近 {count} 次完成平均用了 {average}：{rows}。",
           "slipping": "来自你的记录：“{title}”最近 {count} 次中有 {missed} 次没有完成：{rows}。",
           "last": "来自你的记录：“{title}”上一次在{day}：{row}。", "join": "；", "part": "，"},
}


def asks_records(message: str) -> bool:
    """Whether a message asks about what the user did, or on which days their energy was low or high, rather than
    reporting it, asking for a change, or asking what they said, wrote or noted, which past conversations and the
    Library answer."""
    return bool(_ASKS.search(message) or _asks_energy(message)) and not _SAID_OR_NOTED.search(message)


def _asks_energy(message: str) -> bool:
    """Whether a message asks for past days of low or high energy (see _ENERGY_ASKS_EN and _ENERGY_ASKS_ZH)."""
    if not _energy(message):
        return False
    if _ENERGY_ASKS_EN.search(message) and _PAST_EN.search(message) and not _CONDITION_EN.search(message):
        return True
    return bool(_ENERGY_ASKS_ZH.search(message)) and (not _HABIT_ZH.search(message) or bool(_ASKED_OUTRIGHT.search(message)))


def _energy(message: str) -> str | None:
    """The energy a message names days by: "low" or "high", or None."""
    return "low" if _ENERGY_LOW.search(message) else "high" if _ENERGY_HIGH.search(message) else None


def _query(start: str | None = None, end: str | None = None, titles: Iterable[str] = (), goal: str | None = None,
           area: str | None = None, kind: str | None = None, energy: str | None = None) -> dict:
    """A look-up in the shape phrase_query and model_query give one: its days, the tasks or goal or area it names, its
    kind and the energy it asks about, each None or empty when the message names none."""
    return {"start": start, "end": end, "titles": list(titles), "goal": goal, "area": area, "kind": kind, "energy": energy}


def _latin(letter: str) -> bool:
    """Whether a character is an ASCII letter or digit, so a title's English words aren't matched inside others."""
    return bool(letter) and letter.isascii() and letter.isalnum()


def _titles_named(message: str, titles: list[str]) -> list[str]:
    """The task titles a message names, quoted or in its words; one inside a longer one named is left out."""
    lowered = message.lower()
    quoted = {text.strip().lower() for text in _QUOTED.findall(message)}
    spans = []
    for title in titles:
        named = title.lower()
        if named in quoted:
            spans.append((0, len(message), title))
            continue
        pattern = ((rf"(?<!{_LATIN})" if _latin(named[:1]) else "") + re.escape(named)
                   + (rf"(?!{_LATIN})" if _latin(named[-1:]) else ""))
        if match := re.search(pattern, lowered):
            spans.append((match.start(), match.end(), title))
    return [title for start, end, title in spans
            if not any(other != title and other_start <= start and end <= other_end and (other_end - other_start) > (end - start)
                       for other_start, other_end, other in spans)]


def _goal_named(message: str, goals: list[str]) -> str | None:
    """The goal a message names: by its whole title, or by a word of it at least _GOAL_WORD letters long that no other
    goal's title has."""
    lowered = message.lower()
    whole = [goal for goal in goals if goal.lower() in lowered]
    if whole:
        return max(whole, key=len)
    words = {goal: {word for word in re.findall(r"[a-z]+", goal.lower()) if len(word) >= _GOAL_WORD} for goal in goals}
    named = [goal for goal, own in words.items()
             if any(re.search(rf"\b{word}\b", lowered) and not any(word in words[other] for other in goals if other != goal)
                    for word in own)]
    return named[0] if len(named) == 1 else None


def _range(message: str, today: date, named_day: str | None) -> tuple[date, date] | None:
    """The days a message names, first and last: a day named outright, alone or "since" it; a range in words; a month;
    the last N days; or since a weekday."""
    if named_day:
        day = date.fromisoformat(named_day)
        return (day, today) if _SINCE.search(message) else (day, day)
    if match := _SINCE_WEEKDAY.search(message):
        weekday = (WEEKDAYS.index(match[1].lower()) if match[1]
                   else CHINESE_WEEKDAYS.index("日" if match[2] == "天" else match[2]))
        return today - timedelta(days=(today.weekday() - weekday) % 7), today
    for pattern, span in _RANGES:
        if pattern.search(message):
            return span(today)
    if match := _LAST_DAYS.search(message):
        return today - timedelta(days=int(match[1] or match[2]) - 1), today
    month = None
    if match := _IN_MONTH.search(message):
        month = next(place for place, word in enumerate(match.groups(), start=1) if word)
    elif match := _CHINESE_MONTH.search(message):
        month = _CHINESE_NUMBERS.get(match[1]) or int(match[1])
    if month:
        year = today.year if month <= today.month else today.year - 1
        first = date(year, month, 1)
        return first, (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return None


def phrase_query(message: str, today: str, titles: list[str], goals: list[str], named_day: str | None = None) -> dict | None:
    """The look-up a question's recognised phrases make.

    Args:
        message: The question.
        today: YYYY-MM-DD.
        titles: Every task title in the records.
        goals: Every goal's title.
        named_day: The day the question names outright, as the conversation reads one ("3 Oct", "10月3日"), or None.

    Returns:
        The "start" and "end" days (None for the whole history), the task "titles", "goal" and "area" it names, and
        what it asks ("kind": "last" for the last time, "count" for how often, else None); or, for one asking for days
        of low or high energy, those days' "energy" ("low" or "high") whatever task it names. None when it names no
        days, task, goal, area or energy.
    """
    span = _range(message, date.fromisoformat(today), named_day)
    if energy := _energy(message):
        return _query(*(day.isoformat() for day in span) if span else (None, None), energy=energy)
    area = _AREA.search(message)
    found = _query(*(day.isoformat() for day in span) if span else (None, None), _titles_named(message, titles),
                   _goal_named(message, goals), _AREA_NAMES[next(name for name in area.groups() if name).lower()] if area else None,
                   "last" if _LAST.search(message) else "count" if _COUNT.search(message) else None)
    return found if span or found["titles"] or found["goal"] or found["area"] else None


def model_query(gateway: ModelGateway, message: str, today: str, first: str, titles: list[str],
                goals: list[str]) -> dict | None:
    """The local model's search for a question no phrase was recognised in, kept only when every field is valid: dates
    from the first recorded day to today, the first not after the last, an area DayWright has, and a task or goal the
    records hold. Anything else, or nothing named, rejects it whole.

    Returns:
        The look-up, as phrase_query gives one; None when the model isn't there or its search is rejected.
    """
    listed = (f"Today: {today}. The records begin on {first}.\nTasks: {'; '.join(titles[:SEARCH_TITLES])}\n"
              f"Goals: {'; '.join(goals)}\nQuestion: {message}\n{SEARCH_REQUEST}")
    answer, mode = gateway.reply(listed, "", system_prompt=SEARCH_ROLE, max_tokens=SEARCH_MAX_TOKENS)
    data = None if mode == "rules" else parse_object(answer)
    if not isinstance(data, dict):
        return None
    days = []
    for key in ("from", "to"):
        value = data.get(key)
        if value is None:
            days.append(None)
            continue
        try:
            day = date.fromisoformat(str(value)).isoformat()
        except ValueError:
            return None
        if not first <= day <= today:
            return None
        days.append(day)
    if days[0] and days[1] and days[0] > days[1]:
        return None
    by_name = {title.lower(): title for title in titles}
    goal_names = {goal.lower(): goal for goal in goals}
    task, goal, area = data.get("task"), data.get("goal"), data.get("area")
    if ((task is not None and str(task).lower() not in by_name) or (goal is not None and str(goal).lower() not in goal_names)
            or (area is not None and area not in DOMAIN_LABELS)):
        return None
    if not (any(days) or task or goal or area):
        return None
    return _query(days[0], days[1], [by_name[str(task).lower()]] if task else [],
                  goal_names[str(goal).lower()] if goal else None, area)


def _long_day(day: str) -> str:
    """A YYYY-MM-DD day in full, as a record's text for search gives it, such as "Tue 6 Oct 2026"."""
    shown = date.fromisoformat(day)
    return f"{shown:%a} {shown.day} {shown:%b} {shown.year}"


def _rows(store: Database, today: str) -> tuple[list[dict], str]:
    """Every task on a day to today, as Patterns reads them, each with whether its time is one "toCheck" and whether it
    has "noTime", from before times were kept; and the first recorded day."""
    first = store.first_record_date() or today
    found = store.pattern_records(first, today, unanswered=False)
    checking = {check["itemId"] for check in found["checks"] if not check["needsStatus"]}
    rows = []
    for record in found["records"]:
        to_check = record["itemId"] in checking
        rows.append({**record, "toCheck": to_check,
                     "noTime": record["status"] in ("done", "partial") and record["minutes"] is None and not to_check})
    return rows, first


def _tally(counts: dict[str, int]) -> str:
    """Tasks by their status, as "2 done, 1 skipped"."""
    return ", ".join(f"{counts[status]} {name}" for status, name in _TALLIED if counts.get(status))


def _counts(rows: list[dict]) -> dict[str, int]:
    """How many of these tasks were done, partly done, skipped, and left without a status."""
    return {"done": sum(row["status"] == "done" for row in rows), "partial": sum(row["status"] == "partial" for row in rows),
            "skipped": sum(row["status"] == "skipped" for row in rows),
            "unanswered": sum(row["status"] in ("noReply", "dayPaused") for row in rows)}


def _days(store: Database, rows: list[dict], first: str, today: str) -> dict[str, dict]:
    """Every day from the first recorded to today with a task or an energy reading, oldest first: its "date", its
    average "energy" (None without a reading), the "plan" set (None without one), its tasks ("rows") and its "pauses",
    each (paused at, resumed at, or None when it wasn't resumed)."""
    with store.connect() as connection:
        plans = dict(connection.execute("""SELECT c.plan_date, v.name FROM daily_confirmations c
                                           JOIN plan_variants v ON v.id = c.variant_id""").fetchall())
        pauses: dict[str, list[tuple[str, str | None]]] = {}
        for row in connection.execute("SELECT pause_date, paused_at, resumed_at FROM day_pauses ORDER BY pause_date, paused_at"):
            pauses.setdefault(row["pause_date"], []).append((row["paused_at"], row["resumed_at"]))
    by_day: dict[str, list[dict]] = {}
    for row in rows:
        by_day.setdefault(row["date"], []).append(row)
    energy = {day["date"]: day["average"] for day in store.energy_days(first, today)}
    return {day: {"date": day, "energy": energy.get(day), "plan": plans.get(day), "rows": by_day.get(day, []),
                  "pauses": pauses.get(day, [])} for day in sorted(set(by_day) | set(energy))}


def documents(store: Database, today: str) -> dict[str, tuple[str, str]]:
    """The documents the records are searched by meaning in, by key: "task:<id>" for each task on a past day or
    reported today (its day, area, goal, title, status, the time it took of its plan or why it has none, the sections
    studied on it and its detail), and "day:<day>" for each day with a task or an energy reading (its energy, the plan
    set, its tasks by status and its pauses); each as (day, words)."""
    rows, first = _rows(store, today)
    with store.connect() as connection:
        sections: dict[str, list[str]] = {}
        for row in connection.execute("""SELECT ticked_on, title FROM checklist_items WHERE ticked_on IS NOT NULL
                                         AND removed = 0 ORDER BY ticked_on, position"""):
            sections.setdefault(row["ticked_on"], []).append(row["title"])
    found: dict[str, tuple[str, str]] = {}
    for row in rows:
        words = [_long_day(row["date"]), DOMAIN_LABELS[row["domain"]]]
        if row["goal"]:
            words.append(f"goal “{row['goal']}”")
        words += [f"“{row['title']}”", STATUS_WORDS[row["status"]]]
        if row["toCheck"]:
            words.append("time to check")
        elif row["noTime"]:
            words.append("no time kept")
        elif row["minutes"] is not None and row["status"] in ("done", "partial"):
            words.append(f"took {minutes_words(row['minutes'], 'en')} of {minutes_words(row['planned'], 'en')} planned")
        if sections.get(row["itemId"]):
            words.append("studied: " + "; ".join(sections[row["itemId"]]))
        if row["detail"]:
            words.append(f"note: {row['detail']}")
        found[f"task:{row['itemId']}"] = (row["date"], " · ".join(words))
    for day, held in _days(store, rows, first, today).items():
        words = [_long_day(day)]
        if (level := held["energy"]) is not None:
            words.append(f"energy {level:.1f} of 5" + (", low energy" if level <= LOW_ENERGY
                                                       else ", high energy" if level >= HIGH_ENERGY else ""))
        if held["plan"] is not None:
            words.append(f"plan set: {held['plan']}")
        if held["rows"]:
            count = len(held["rows"])
            words.append(f"{count} task{'' if count == 1 else 's'}: {_tally(_counts(held['rows']))}")
        if held["pauses"]:
            words.append("paused " + ", ".join(f"{start}–{end or 'the day’s end'}" for start, end in held["pauses"]))
        found[f"day:{day}"] = (day, " · ".join(words))
    return found


def names(store: Database, today: str) -> tuple[list[str], list[str]]:
    """Every task title the records hold to today, and every goal's title, as a question's words are read against."""
    with store.connect() as connection:
        titles = [row[0] for row in connection.execute(
            """SELECT DISTINCT title FROM daily_items WHERE item_date <= ? AND acceptance = 'accepted'
               ORDER BY title""", (today,))]
        goals = [row[0] for row in connection.execute("SELECT title FROM goals ORDER BY created_at")]
    return titles, goals


def query_for(store: Database, gateway: ModelGateway, message: str, today: str, named_day: str | None) -> dict | None:
    """The look-up a question about what the user did makes: by its phrases (phrase_query), or failing them by the
    local model's search (model_query); None for one by meaning alone."""
    titles, goals = names(store, today)
    return (phrase_query(message, today, titles, goals, named_day)
            or model_query(gateway, message, today, store.first_record_date() or today, titles, goals))


def sync(store: Database, rag: RagService, today: str, wait: bool = True,
         stop: threading.Event | None = None, most: int | None = None) -> dict[str, int] | None:
    """Bring the documents and their vectors in step with the records: add the new, rewrite the changed, delete the
    gone, then embed every document without a vector, BATCH at a time, each batch kept as it is done. Without the
    embedding model, once `stop` is set, or past `most`, the rest wait for their vectors until the next sync.

    Args:
        wait: Whether to wait for a sync under way; without waiting, none is made while one is.
        most: The most documents embedded this time, as for a question, which mustn't wait for a whole history to
            be embedded; None for every one.

    Returns:
        How many documents were "added", "changed" and "removed", how many were "embedded", and how many were "left"
        without a vector; None when a sync was under way and `wait` is False.
    """
    if not _SYNCING.acquire(blocking=wait):
        return None
    try:
        found = documents(store, today)
        with store.connect() as connection:
            held = {row["key"]: (row["id"], row["text"]) for row in connection.execute("SELECT id, key, text FROM record_documents")}
            gone = [held[key][0] for key in held if key not in found]
            changed = [key for key in found if key in held and held[key][1] != found[key][1]]
            added = [key for key in found if key not in held]
            if gone:
                connection.execute(f"DELETE FROM record_documents WHERE id IN ({','.join('?' * len(gone))})", gone)
            connection.executemany("UPDATE record_documents SET day = ?, text = ? WHERE key = ?",
                                   [(*found[key], key) for key in changed])
            connection.executemany("INSERT INTO record_documents (key, day, text) VALUES (?, ?, ?)",
                                   [(key, *found[key]) for key in added])
            current = {row["id"]: row["text"] for row in connection.execute("SELECT id, text FROM record_documents ORDER BY id")}
        have = rag.vector_store.vector_ids(_TABLE)
        rag.vector_store.drop_vectors(_TABLE, (have - set(current)) | {held[key][0] for key in changed})
        have = rag.vector_store.vector_ids(_TABLE)
        missing = [(row_id, text) for row_id, text in current.items() if row_id not in have]
        now = missing if most is None else missing[:most]
        embedded = 0
        for start in range(0, len(now), BATCH):
            if stop is not None and stop.is_set():
                break
            try:
                rag.index_memory(_TABLE, now[start:start + BATCH])
            except EmbeddingUnavailable:
                break
            embedded += len(now[start:start + BATCH])
        return {"added": len(added), "changed": len(changed), "removed": len(gone), "embedded": embedded,
                "left": len(missing) - embedded}
    finally:
        _SYNCING.release()


def look_up(store: Database, rag: RagService, message: str, query: dict | None, today: str) -> dict:
    """The records a question about what the user did rests on.

    Args:
        query: The look-up its words make (phrase_query or model_query), or None for one by meaning alone.

    Returns:
        For a question asking for days of low or high energy, those days, as _energy_days gives them. Otherwise
        the "query"; its "rows", newest first, up to ROWS_SHOWN, each a record with "toCheck" and "noTime", and no
        "days"; how many more match ("more"), with the first and last day of those ("moreFrom", "moreTo"); the
        "totals" over every row matching (its "count", each status's, the "minutes" counted, those "toCheck" and
        with "noTime", and the "first" and "last" day), None without a query; and the "matches" by meaning,
        nearest first, up to MEANING_MATCHES, none of them a task among the rows and none for a question naming a
        task, a goal or an area, whose rows hold all it names; each its "key" and "day", with a task's record
        ("row") or a day's ("facts", see _days).
    """
    every, first = _rows(store, today)
    if query is not None and query["energy"]:
        return _energy_days(store, query, every, first, today)
    rows: list[dict] = []
    totals = None
    if query is not None:
        start, end = query["start"] or first, query["end"] or today
        titles = {title.lower() for title in query["titles"]}
        rows = sorted((row for row in every if start <= row["date"] <= end
                       and (not titles or row["title"].lower() in titles)
                       and (not query["goal"] or row["goal"] == query["goal"])
                       and (not query["area"] or row["domain"] == query["area"])),
                      key=lambda row: row["date"], reverse=True)
        totals = {"count": len(rows), **_counts(rows),
                  "minutes": sum(row["minutes"] for row in rows if row["minutes"] is not None),
                  "toCheck": sum(row["toCheck"] for row in rows), "noTime": sum(row["noTime"] for row in rows),
                  "first": rows[-1]["date"] if rows else None, "last": rows[0]["date"] if rows else None}
    keys = {f"task:{row['itemId']}" for row in rows}
    # A question naming a task, a goal or an area is answered by its rows alone; one naming only its days is matched by
    # meaning on those days alone, from more of the nearest.
    scoped = query is not None and bool(query["titles"] or query["goal"] or query["area"])
    dated = query is not None and bool(query["start"] or query["end"])
    near = ([] if scoped else
            rag.nearest_memory(_TABLE, message, (MEANING_MATCHES + len(keys)) * (DATED_WIDENING if dated else 1)) or [])
    matches: list[dict] = []
    if near:
        with store.connect() as connection:
            held = {row["id"]: (row["key"], row["day"]) for row in connection.execute(
                f"SELECT id, key, day FROM record_documents WHERE id IN ({','.join('?' * len(near))})",
                [row_id for row_id, _ in near])}
        by_item = {row["itemId"]: row for row in every}
        days = _days(store, every, first, today)
        for row_id, _ in near:
            key, day = held.get(row_id, (None, None))
            if key is None or key in keys or (dated and not start <= day <= end):
                continue
            if key.startswith("task:") and (row := by_item.get(key.removeprefix("task:"))):
                matches.append({"key": key, "day": day, "row": row})
            elif key.startswith("day:") and day in days:
                matches.append({"key": key, "day": day, "facts": days[day]})
            if len(matches) == MEANING_MATCHES:
                break
    rest = rows[ROWS_SHOWN:]
    return {"query": query, "rows": rows[:ROWS_SHOWN], "days": [], "more": len(rest),
            "moreFrom": rest[-1]["date"] if rest else None, "moreTo": rest[0]["date"] if rest else None, "totals": totals,
            "matches": matches}


def _energy_days(store: Database, query: dict, every: list[dict], first: str, today: str) -> dict:
    """The days of low energy (LOW_ENERGY or below on average) or high (HIGH_ENERGY or above) a question asks for, on
    its days or every day recorded, as look_up gives a question's records: the "days", newest first, up to ROWS_SHOWN,
    each as _days gives it; how many "more", from "moreFrom" to "moreTo"; and the "totals", their "count" with the
    "first" and "last" day."""
    start, end = query["start"] or first, query["end"] or today
    low = query["energy"] == "low"
    chosen = [day for day in reversed(_days(store, every, first, today).values())
              if start <= day["date"] <= end and day["energy"] is not None
              and (day["energy"] <= LOW_ENERGY if low else day["energy"] >= HIGH_ENERGY)]
    rest = chosen[ROWS_SHOWN:]
    return {"query": query, "rows": [], "days": chosen[:ROWS_SHOWN], "more": len(rest),
            "moreFrom": rest[-1]["date"] if rest else None, "moreTo": rest[0]["date"] if rest else None,
            "totals": {"count": len(chosen), "first": chosen[-1]["date"] if chosen else None,
                       "last": chosen[0]["date"] if chosen else None}, "matches": []}


def _row_words(row: dict, language: str = "en") -> str:
    """A row as an answer cites it: "13 Oct, Review, Done, 1 h", "10月13日，Review，已完成，1 小时"."""
    words = _FACTS[language]
    time = (words["toCheckRow"] if row["toCheck"] else words["noTimeRow"] if row["noTime"]
            else minutes_words(row["minutes"], language) if row["minutes"] is not None and row["status"] in ("done", "partial")
            else None)
    status = (STATUS_WORDS_ZH if language == "zh" else STATUS_WORDS)[row["status"]]
    return words["part"].join(part for part in (day_words(row["date"], language), row["title"], status, time) if part)


def _day_line(day: dict, language: str = "en") -> str:
    """A day as an answer cites it, from _days: "2 Oct, energy 2.0 of 5; plan: Lighter day; 6 tasks: 5 done, 1 skipped;
    paused 13:10–15:00, from 17:00", "10月2日，精力 2.0/5；……"."""
    words = _FACTS[language]
    parts = []
    if day["energy"] is not None:
        parts.append(words["energy"].format(level=day["energy"]))
    if day["plan"] is not None:
        parts.append(words["plan"].format(plan=day["plan"]))
    if day["rows"]:
        counts, count = _counts(day["rows"]), len(day["rows"])
        tally = words["join"].join(word.format(counts[status]) for status, word in words["tally"] if counts.get(status))
        parts.append(words["dayTasks"].format(count=count, noun=words["tasks"][count != 1], tally=tally))
    if day["pauses"]:
        parts.append(words["paused"].format(spans=words["join"].join(
            words["span"].format(start=start, end=end) if end else words["from"].format(start=start)
            for start, end in day["pauses"])))
    return words["part"].join((day_words(day["date"], language), words["groups"].join(parts)))


def _period(first: str, last: str, words: dict) -> str:
    """The days an answer covers, in its language: "on" one day, or the "period" from the first to the last."""
    return (words["on"].format(day=day_words(first, words["language"])) if first == last
            else words["period"].format(first=day_words(first, words["language"]), last=day_words(last, words["language"])))


def _subject(query: dict, words: dict) -> str:
    """What a look-up names, as an answer's totals begin: “Review”, Goal “Spanish to B1”, Learn tasks, Your tasks."""
    if query["titles"]:
        return words["part"].join(words["title"].format(title=title) for title in query["titles"])
    if query["goal"]:
        return words["goal"].format(goal=query["goal"])
    if query["area"]:
        return words["area"].format(area=words["areas"][query["area"]])
    return words["every"]


def facts(found: dict, language: str) -> str:
    """What an answer about what the user did says of the records, written by the service, never the model: the exact
    look-up's totals in one sentence, then each row cited, newest first, the records nearest the question by meaning
    after them while fewer than ROWS_SHOWN are cited, and how many more rows match; for the last time, that day's row
    alone; for a question by meaning alone, the records nearest it; for days of low or high energy, their count in one
    sentence, then each day cited. Empty when nothing matches."""
    words = _FACTS[language]
    query, totals, rows = found["query"], found["totals"], found["rows"]
    if query is not None and query["energy"]:
        if not found["days"]:
            return ""
        count = totals["count"]
        lines = [words["energyTotal"].format(level=words["levels"][query["energy"]], count=count,
                                             noun=words["days"][count != 1],
                                             period=_period(query["start"] or totals["first"], query["end"] or totals["last"],
                                                            words)),
                 *(words["cite"].format(row=_day_line(day, language)) for day in found["days"])]
        return "\n".join([*lines, *filter(None, [more_line(found, language)])])
    cite = [words["cite"].format(row=_row_words(row, language)) for row in rows]
    if query is not None and rows and query["kind"] == "last":
        return "\n".join([words["last"].format(subject=_subject(query, words), day=day_words(rows[0]["date"], language)), cite[0]])
    lines = []
    if query is not None and rows:
        count = totals["count"]
        noun = words["times" if query["kind"] == "count" else "tasks"][count != 1]
        tally = words["join"].join(word.format(totals[status]) for status, word in words["tally"] if totals.get(status))
        sentence = words["total"].format(subject=_subject(query, words), count=count, noun=noun, tally=tally,
                                         minutes=minutes_words(totals["minutes"], language),
                                         period=_period(query["start"] or totals["first"], query["end"] or totals["last"], words))
        if totals["toCheck"]:
            sentence += words["toCheck"].format(count=totals["toCheck"], plural="" if totals["toCheck"] == 1 else "s")
        if totals["noTime"]:
            sentence += words["noTime"].format(count=totals["noTime"])
        lines += [sentence + words["end"], *cite]
    room = ROWS_SHOWN - len(cite)
    if found["matches"] and room > 0:
        lines.append(words["also" if lines else "near"])
        lines += [words["cite"].format(row=_row_words(match["row"], language) if "row" in match
                                       else _day_line(match["facts"], language)) for match in found["matches"][:room]]
    if more := more_line(found, language):
        lines.append(more)
    return "\n".join(lines)


def more_line(found: dict, language: str) -> str | None:
    """The line an answer ends with when more rows match than it lists, saying how to narrow it; None otherwise."""
    if not found["more"]:
        return None
    first, last, more = day_words(found["moreFrom"], language), day_words(found["moreTo"], language), found["more"]
    if found["query"] is not None and found["query"]["energy"]:
        if language == "zh":
            return f"还有 {more} 天，从{first}到{last}：说出月份或哪一周即可缩小范围。"
        return f"And {more} more day{'' if more == 1 else 's'}, from {first} to {last}: name a month or a week to narrow it."
    if language == "zh":
        return f"还有 {more} 项，从{first}到{last}：说出月份、任务或领域即可缩小范围。"
    return f"And {more} more, from {first} to {last}: name a month, a task or an area to narrow it."


def nothing_line(language: str) -> str:
    """The answer to a question about what the user did that nothing in the records matches."""
    return "你的记录中没有与此相符的内容。" if language == "zh" else "Nothing in your records matches that."


def without_citations(answer: str) -> str:
    """An answer with every citation of the records the model wrote left out, from "From your records:" ("来自你的记录：")
    to the end of its line, as the service cites them itself (see facts)."""
    kept = []
    for line in answer.split("\n"):
        cut = _CITE.search(line)
        if cut is None:
            kept.append(line)
        elif line[:cut.start()].strip():
            kept.append(line[:cut.start()].rstrip())
    return "\n".join(kept).strip()


def _remark_row(row: dict, language: str, dated: bool = True) -> str:
    """A record as a remark cites it: "13 Oct, Done, 1 h 15 min", or without its day "Done, 1 h 15 min"."""
    words = STATUS_WORDS_ZH if language == "zh" else STATUS_WORDS
    time = (minutes_words(row["minutes"], language) if row["minutes"] is not None and not row["toCheck"]
            and row["status"] in ("done", "partial") else None)
    return _REMARKS[language]["part"].join(part for part in (dated and day_words(row["date"], language),
                                                             words[row["status"]], time) if part)


def remark(store: Database, today: str, asked: list[tuple], language: str) -> str | None:
    """The one remark Ava makes unasked beside a change, from the records before today of the tasks it concerns.

    Args:
        asked: What the change concerns, in order: ("length", title, minutes) for a length set or a task added with
            one, ("slipping", title) for a task moved or a plan chosen, ("last", title) for a task added. The first
            with something to say gives the remark.
        language: "en" or "zh".

    Returns:
        A line beginning "From your records: " ("来自你的记录：") citing the records it rests on: the time a task took
        when done, over its latest REMARK_LATEST, when REMARK_TIMES or more of them differ on average from the length
        asked by USUAL_DIFFERENCE minutes or more; that it wasn't done OFTEN_COUNT or more, and half, of its latest
        times; or its last record. A time to check is never counted. None when none of them has anything to say.
    """
    rows, _ = _rows(store, today)
    words = _REMARKS[language]
    for kind, title, *more in asked:
        own = sorted((row for row in rows if row["title"].lower() == title.lower() and row["date"] < today),
                     key=lambda row: row["date"], reverse=True)
        if kind == "length":
            timed = [row for row in own if row["status"] == "done" and row["minutes"] is not None
                     and not row["toCheck"]][:REMARK_LATEST]
            average = round(sum(row["minutes"] for row in timed) / len(timed)) if timed else None
            if len(timed) >= REMARK_TIMES and abs(average - more[0]) >= USUAL_DIFFERENCE:
                cited = words["join"].join(words["part"].join((day_words(row["date"], language),
                                                               minutes_words(row["minutes"], language)))
                                           for row in timed)
                return words["length"].format(title=title, average=minutes_words(average, language), count=len(timed),
                                              rows=cited)
        elif kind == "slipping":
            latest = own[:REMARK_LATEST]
            missed = [row for row in latest if row["status"] in _NOT_DONE]
            if len(missed) >= OFTEN_COUNT and len(missed) * 2 >= len(latest):
                return words["slipping"].format(title=title, missed=len(missed), count=len(latest),
                                                rows=words["join"].join(_remark_row(row, language) for row in missed))
        elif own:
            return words["last"].format(title=title, day=day_words(own[0]["date"], language),
                                        row=_remark_row(own[0], language, dated=False))
    return None
