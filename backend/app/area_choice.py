"""How the Orchestrator suggests the area of a task added without a goal.

The area goes by the task's purpose, taken in order: someone else expects it (Work); it is a step
toward something the user is building that has an end (Project); its point is getting better at
something (Learning); anything else is Life. Keywords for each purpose decide whenever one matches;
the local model applies the rule only when none does and it is running, and Life stands when it
isn't or its answer can't be read. The user may change the area either way, and a task linked to a
goal always takes the goal's area.
"""

from __future__ import annotations

import re
from typing import Callable

# The areas in the order the rule takes them; Life is everything else.
RULE_ORDER = ("work", "project", "learning")

AREA_ROLE = (
    "You are DayWright's Orchestrator. Choose the area a task belongs to by its purpose, taking this rule "
    "in order: 1. someone else expects it: work; 2. it is a step toward something the person is building "
    "that has an end: project; 3. its point is getting better at something: learning; 4. everything else: "
    "life. Worked examples: \"Kitchen renovation\": project; \"Call the plumber\": life; \"Read chapter 4\": "
    "learning; \"Reply to the client\": work; \"Buy groceries\": life; \"Build the app prototype\": project. "
    "Answer with the one word."
)
# The one word the model answers with, and a little room around it.
AREA_MAX_TOKENS = 8

# Words that show each purpose, matched whole in English and anywhere in Chinese.
PURPOSE_WORDS = {
    "work": ("client", "clients", "customer", "customers", "boss", "manager", "colleague", "colleagues", "team",
             "meeting", "meetings", "stand-up", "standup", "email", "emails", "reply", "invoice", "invoices",
             "deadline", "report", "submit", "office", "work", "job", "shift"),
    "project": ("project", "build", "prototype", "launch", "ship", "release", "milestone", "app", "website",
                "landing page", "renovate", "renovation"),
    "learning": ("learn", "learning", "study", "studying", "practise", "practice", "course", "lesson", "lessons",
                 "homework", "revise", "revision", "flashcards", "tutorial", "read", "reading"),
}
PURPOSE_WORDS_ZH = {
    "work": ("客户", "老板", "经理", "同事", "会议", "邮件", "汇报", "报告", "截止", "提交", "工作", "上班"),
    "project": ("项目", "原型", "上线", "发布", "里程碑", "搭建", "开发", "装修"),
    "learning": ("学习", "课程", "练习", "复习", "阅读", "背单词", "作业"),
}
# How the model may name each area: in English, or in Chinese.
_AREA_NAMES = {"work": "work", "project": "project", "learning": "learning", "life": "life",
               "工作": "work", "项目": "project", "学习": "learning", "生活": "life"}
_ANSWER = re.compile("|".join(re.escape(name) for name in _AREA_NAMES), re.IGNORECASE)


def matched_area(title: str, detail: str) -> str | None:
    """Return the first area in RULE_ORDER whose purpose words a task has, or None when it has none.

    Args:
        title: The task's title.
        detail: Its detail, which may be empty.
    """
    text = f"{title} {detail}".lower()
    for area in RULE_ORDER:
        if (any(re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", text) for word in PURPOSE_WORDS[area])
                or any(word in text for word in PURPOSE_WORDS_ZH[area])):
            return area
    return None


def keyword_area(title: str, detail: str) -> str:
    """Return the area the purpose rule gives a task from its words alone: the one they match, else "life"."""
    return matched_area(title, detail) or "life"


def parse_area(answer: str) -> str | None:
    """Return the area the model's answer names first, or None when it names none."""
    match = _ANSWER.search(answer)
    return _AREA_NAMES[match.group().lower()] if match else None


def model_area(gateway) -> Callable[[str, str], str | None]:
    """Return a function that has the local model apply the purpose rule to a task.

    Args:
        gateway: The local chat model, which must be running; asking would start it otherwise.

    Returns:
        A function of the task's title and detail returning its area, or None when the model's
        answer can't be read.
    """
    def ask(title: str, detail: str) -> str | None:
        message = f"Task: {title}." + (f" Detail: {detail}." if detail else "") + " Which area?"
        answer, mode = gateway.reply(message, "", system_prompt=AREA_ROLE, max_tokens=AREA_MAX_TOKENS)
        return None if mode == "rules" else parse_area(answer)

    return ask
