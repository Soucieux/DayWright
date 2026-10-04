"""How the Orchestrator has the local model choose the two plans offered beside Balanced.

The planner builds every kind of plan the day allows and checks each one; the model only reads the
day and those plans and says which two suit it best, and why, in English and Chinese. Whatever it
answers, the planner keeps only kinds it built, and fills any place the model leaves from its own
ranking.
"""

from __future__ import annotations

import json
import re
from typing import Callable

# How much the model may write: two kinds, each with a sentence in English and one in Chinese.
CHOICE_MAX_TOKENS = 500

CHOICE_ROLE = (
    "You are DayWright's Orchestrator. Beside the Balanced plan, which is always offered, choose the "
    "two plans from the candidates that best fit this person's day. Each area agent has voted for up to "
    "three plans for its own tasks only (agentVotes, best first); weigh their votes, but you decide for "
    "the whole day. Use everything in the day: the "
    "tasks, their details and lengths, fixed times, free time, meals, the area agents' findings, "
    "energy, Summary advice, and the plans the person set most often. Prefer two plans that differ "
    "from each other. Each reason is one short sentence about this day, naming its tasks where that "
    "helps. Answer with JSON only."
)
CHOICE_REQUEST = (
    'Choose the two plans. Reply exactly in this form, using the candidates\' "kind" values: '
    '{"plans": [{"kind": "<kind>", "why": "<one English sentence on why it suits this day>", '
    '"whyZh": "<the same sentence in Simplified Chinese>"}, {"kind": "<kind>", "why": "...", "whyZh": "..."}]}'
)

# The first JSON object in an answer, which may be wrapped in other words or a code block.
_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def parse_choice(answer: str) -> list[dict] | None:
    """Return the picks in the model's answer, or None when it holds no usable JSON.

    Args:
        answer: The model's reply, expected to hold {"plans": [{"kind", "why", "whyZh"}, ...]}.

    Returns:
        Each pick that is an object, in the model's order; the planner checks their contents.
    """
    match = _OBJECT.search(answer)
    if not match:
        return None
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return None
    plans = data.get("plans") if isinstance(data, dict) else None
    return [plan for plan in plans if isinstance(plan, dict)] if isinstance(plans, list) else None


def model_chooser(gateway) -> Callable[[dict], list[dict] | None]:
    """Return a chooser that gives the day and its candidate plans to the local model.

    Args:
        gateway: The local chat model; it answers in "rules" mode when it isn't running.

    Returns:
        A function of the planner's choice context returning the model's picks, or None when the
        model isn't available or its answer can't be read.
    """
    def choose(context: dict) -> list[dict] | None:
        answer, mode = gateway.reply(CHOICE_REQUEST, json.dumps(context, ensure_ascii=False),
                                     system_prompt=CHOICE_ROLE, max_tokens=CHOICE_MAX_TOKENS)
        return None if mode == "rules" else parse_choice(answer)

    return choose
