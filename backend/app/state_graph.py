"""Checkpointed day-proposal state flow; SQLite domain records remain authoritative."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import date
from typing import TypedDict

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from .agents import DOMAIN_SPECS, ORCHESTRATOR, SUMMARY, AgentRun
from .domain_records import DomainRecords


class PlatformState(TypedDict, total=False):
    session_id: str
    user_input: str
    current_date: str
    messages: list[dict]
    today_plan: dict
    pending_plans: list[dict]
    active_suggestions: list[dict]
    learning_snapshot: dict
    life_snapshot: dict
    work_snapshot: dict
    project_snapshot: dict
    knowledge_task_id: str | None
    next_agent: str
    needs_confirmation: bool
    user_feedback: dict
    source_items: list[dict]
    goal_snapshot: list[dict]
    domain_records: dict[str, dict]
    prior_summary: dict
    memory: list[dict]
    history: dict
    findings: list[dict]
    agent_runs: list[dict]
    plan_set_id: str


def _choice_summary(variants: list[dict], picks: list[dict], asked: bool) -> str:
    """Say which plans were offered beside Balanced, and whether the local model or the votes chose them.

    Args:
        variants: The plans proposed, Balanced among them.
        picks: The Orchestrator's picks: the local model's, then those from the area agents' votes,
            which name the "agents" that voted.
        asked: Whether the local model was asked to choose.
    """
    others = [variant for variant in variants if variant["slug"] != "balanced"]
    if not others:
        return ("Proposed Balanced alone, since no task needs placing in another way. "
                "No plan was applied.")
    names = " and ".join(variant["name"] for variant in others)
    by_model = [variant["name"] for variant in others
                if variant["slug"] in {pick["kind"] for pick in picks if "agents" not in pick}]
    if by_model:
        return (f"After the area agents voted, the local model chose {' and '.join(by_model)} beside Balanced "
                f"from the plans the day allows; offered {names}. No plan was applied.")
    reason = ", as the local model gave no usable choice" if asked else ", as the local model wasn't asked"
    if any(variant["slug"] in {pick["kind"] for pick in picks} for variant in others):
        return f"Chose {names} beside Balanced from the area agents' votes{reason}. No plan was applied."
    return f"Chose {names} beside Balanced by DayWright's own ranking{reason}. No plan was applied."


def run_day_proposal(orchestrator, store, plan_date: str, plan_set_id: str | None = None, choose=None,
                     again: bool = False) -> str:
    """Load owned state, route agents, summarize history, and save an unapplied plan.

    Given the id of plans already proposed for the day, every agent reviews the day again and only
    that route is replaced; no plans are made or changed. With `again`, the day's plans that aren't
    set are proposed again from its tasks as they are now (see Database.repropose_plans). Otherwise
    `choose`, when given, has the local model pick the two plans beside Balanced (see plan_choice),
    and the Orchestrator's last step says whether it did.
    """
    day = store.bootstrap_day(plan_date, create_if_missing=False)

    def dispatch(state: PlatformState) -> dict:
        kept = len(state["active_suggestions"])
        run = AgentRun(ORCHESTRATOR, "dispatch",
                       "Asked Learning, Life, Work and Project to review the day"
                       + (f", with {kept} piece{'s' if kept != 1 else ''} of Summary advice you kept." if kept else "."))
        return {"agent_runs": [run.public()], "next_agent": "learning"}

    def finish(state: PlatformState, outcome: str) -> list[dict]:
        """The route with the Orchestrator's one run, first, also saying what came of it."""
        first, *rest = state["agent_runs"]
        return [{**first, "summary": f"{first['summary']} {outcome}"}, *rest]

    def domain_node(key: str):
        def assess(state: PlatformState) -> dict:
            snapshot = {"entries": [], "dayItems": state["source_items"]}
            run = orchestrator._domain_agents[key].assess(
                snapshot, "adjust", state["domain_records"].get(key), state["history"])
            guidance = [item for item in state["active_suggestions"]
                        if item["domain"] in (key, "cross")]
            if guidance:
                run = AgentRun(run.spec, run.phase, run.summary + " Active Summary guidance: "
                               + "; ".join(f"{item['priority']}: {item['content']}"
                                           for item in guidance[:3]), run.findings)
            return {"agent_runs": [*state["agent_runs"], run.public()],
                    "findings": [*state["findings"], *run.findings],
                    f"{key}_snapshot": {"assessment": run.summary},
                    "next_agent": {"learning": "life", "life": "work", "work": "project",
                                   "project": "summary"}[key]}
        return assess

    def summarize(state: PlatformState) -> dict:
        facts = state["history"]["facts"]
        prior = orchestrator.summary_report("review", f"before-{state['current_date']}", facts)
        memory = state["history"]["memory"]
        reports = [AgentRun(DOMAIN_SPECS[run["agentKey"]], run["phase"], run["summary"], tuple(run["findings"]))
                   for run in state["agent_runs"] if run["agentKey"] in DOMAIN_SPECS]
        run = orchestrator._summary.assess(reports, prior)
        return {"prior_summary": prior, "memory": memory,
                "user_feedback": {"signals": memory},
                "agent_runs": [*state["agent_runs"], run.public()],
                "next_agent": "orchestrator"}

    def propose(state: PlatformState) -> dict:
        if plan_set_id:
            return {"plan_set_id": plan_set_id, "next_agent": "user",
                    "agent_runs": finish(state, "Had every agent review the day again after DayWright was updated; "
                                                "the plans are as they were proposed.")}
        guidance = [*state["active_suggestions"], *state["prior_summary"]["suggestions"]]
        decisions = []

        def decided(context: dict):
            # The area agents vote; the Orchestrator, through the local model or their tally, decides.
            decisions.append(orchestrator.decide_plans(context, state["history"]["profiles"], choose))
            return decisions[-1][0]

        make = store.repropose_plans if again else store.create_recorded_plan
        new_plan_set_id = make(state["current_date"], state["memory"], guidance, state["findings"], decided)
        proposed = store.bootstrap_day(state["current_date"], create_if_missing=False)
        picks, votes, _ = decisions[-1] if decisions else ([], {}, "none")
        summary = _choice_summary(proposed["variants"], picks, choose is not None)
        if again:
            summary = ("Proposed the plans not set again, from the day's tasks as they are now; a set plan stays "
                       f"as set. {summary}")
        runs = [{**run, "votes": votes[run["agentKey"]]} if run["agentKey"] in votes else run
                for run in finish(state, summary)]
        return {"plan_set_id": new_plan_set_id, "pending_plans": proposed["variants"],
                "today_plan": {}, "needs_confirmation": True, "next_agent": "user", "agent_runs": runs}

    builder = StateGraph(PlatformState)
    builder.add_node("dispatch", dispatch)
    for key in DOMAIN_SPECS:
        builder.add_node(key, domain_node(key))
    builder.add_node("summary", summarize)
    builder.add_node("propose", propose)
    builder.add_edge(START, "dispatch")
    builder.add_edge("dispatch", "learning")
    builder.add_edge("learning", "life")
    builder.add_edge("life", "work")
    builder.add_edge("work", "project")
    builder.add_edge("project", "summary")
    builder.add_edge("summary", "propose")
    builder.add_edge("propose", END)

    area_records = DomainRecords(store)
    # The area agents and the Summary agent read the same days before this one.
    history = orchestrator.review_history(store, plan_date)
    initial: PlatformState = {
        "session_id": store.thread(), "user_input": "Propose from my dated records",
        "messages": [], "current_date": plan_date, "today_plan": {},
        "pending_plans": [], "active_suggestions": store.active_suggestion_pool(),
        "source_items": day["dayItems"],
        "domain_records": {key: area_records.snapshot(key, plan_date)
                           for key in DOMAIN_SPECS},
        "goal_snapshot": day["goals"], "needs_confirmation": False,
        "history": history, "findings": [], "agent_runs": [], "knowledge_task_id": None,
    }
    connection = sqlite3.connect(store.checkpoint_path, timeout=15, check_same_thread=False)
    try:
        serializer = JsonPlusSerializer(allowed_msgpack_modules=())
        graph = builder.compile(checkpointer=SqliteSaver(connection, serde=serializer))
        thread_id = f"day-proposal:{plan_date}:{uuid.uuid4().hex}"
        state = graph.invoke(initial, {"configurable": {"thread_id": thread_id}})
    finally:
        connection.close()
    store.record_plan_route(state["plan_set_id"], state["agent_runs"])
    return state["plan_set_id"]


def refresh_earlier_proposals(orchestrator, store) -> str | None:
    """Propose today's plans again when an earlier version proposed them all.

    Those plans could shorten a length the user set, which plans no longer do. The plans not set
    are proposed again by DayWright's own ranking, without waiting for the local model; a set plan
    stays as set.

    Returns:
        A line naming the reason when today's plans could not be proposed again, else None.
    """
    today = date.today().isoformat()
    if not store.earlier_proposals(today):
        return None
    try:
        run_day_proposal(orchestrator, store, today, again=True)
    except Exception as error:  # Today's plans stay as they were; the service still starts.
        return f"{today}: {error}"
    return None


def refresh_earlier_routes(orchestrator, store) -> list[str]:
    """Have every agent review again each day whose saved route came from an earlier version.

    A route saved before the area agents reviewed history names fewer agents, in their earlier
    wording, and its runs carry no findings; one saved before v2.1 also closes with a second
    Orchestrator run. Each such route is replaced by a review from the agents DayWright has now;
    the plans stay as they were proposed.

    Returns:
        A line for each route that could not be replaced, naming its day and the reason.
    """
    agents = {ORCHESTRATOR.key, *DOMAIN_SPECS, SUMMARY.key}
    failures = []
    for plan_set_id, plan_date, route in store.plan_routes():
        current = (agents <= {run.get("agentKey") for run in route} and all("findings" in run for run in route)
                   # Before v2.1 the Orchestrator also closed every route.
                   and not any(run.get("phase") == "synthesis" for run in route))
        if current:
            continue
        try:
            run_day_proposal(orchestrator, store, plan_date, plan_set_id)
        except Exception as error:  # One day's failure must not stop the others or the service.
            failures.append(f"{plan_date}: {error}")
    return failures
