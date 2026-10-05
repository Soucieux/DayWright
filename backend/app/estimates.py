"""How an area agent estimates the length of a task the user gave none.

When the task is saved, its area agent gives a provisional length straight from the user's own
records (see `Database._provisional_estimate`). Then, without holding up the save, the same agent
asks the local model, and the model's answer replaces the provisional length unless the user has
given one meanwhile. Plans use whichever length the task has.
"""

from __future__ import annotations

import re

from .agents import DOMAIN_SPECS

# The length an area agent gives a task when the user's records say nothing about it.
DEFAULT_ESTIMATE_MINUTES = 30
# The bounds and the step of a length the local model suggests.
MODEL_MIN_MINUTES = 5
MODEL_MAX_MINUTES = 480
ESTIMATE_STEP_MINUTES = 5

# A number in the model's answer, in minutes unless hours follow it.
_AMOUNT = re.compile(r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|h\b|小时)?", re.IGNORECASE)


def parse_minutes(answer: str) -> int | None:
    """Return the length the model's answer names, rounded and kept within bounds, or None.

    Args:
        answer: The model's reply, such as "About 50 minutes." or "1.5 hours".
    """
    match = _AMOUNT.search(answer)
    if not match:
        return None
    minutes = float(match[1]) * (60 if match[2] else 1)
    stepped = round(minutes / ESTIMATE_STEP_MINUTES) * ESTIMATE_STEP_MINUTES
    return int(min(MODEL_MAX_MINUTES, max(MODEL_MIN_MINUTES, stepped)))


def refine_estimate(store, gateway, item_id: str) -> bool:
    """Have the task's area agent ask the local model how long the task takes, and keep its answer.

    The store keeps no estimate under its shortest task length, so a shorter answer becomes it.

    Args:
        store: The database holding the task.
        gateway: The local chat model; it answers in "rules" mode when it isn't running.
        item_id: The task whose length the agent estimated.

    Returns:
        True when the model's estimate replaced the provisional one.
    """
    item = store.daily_item(item_id)
    if not item or item["durationSource"] != "estimate":
        return False
    agent = DOMAIN_SPECS[item["domain"]].label
    examples = store.user_lengths(item["domain"])
    context = ("Lengths the user gave similar tasks: "
               + "; ".join(f"{title}: {minutes} minutes" for title, minutes in examples)
               if examples else "The user has given no similar task a length yet.")
    message = (f"How many minutes will this {agent.lower()} task take one person? Title: {item['title']}."
               + (f" Detail: {item['detail']}." if item["detail"] else "")
               + " Answer with one number of minutes.")
    answer, mode = gateway.reply(
        message, context,
        system_prompt=(f"You are the {agent} agent. Estimate realistically how long a task takes, from its "
                       "title, its detail and the user's own past tasks. Reply with a single number of minutes."),
    )
    if mode == "rules":
        return False
    minutes = parse_minutes(answer)
    return minutes is not None and store.apply_model_estimate(item_id, minutes)
