"""Checkpointed day-proposal state flow; SQLite domain records remain authoritative."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import date, timedelta
from typing import TypedDict

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from .agents import DOMAIN_SPECS, ORCHESTRATOR, AgentRun
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
    finance_snapshot: dict
    knowledge_task_id: str | None
    next_agent: str
    needs_confirmation: bool
    user_feedback: dict
    source_items: list[dict]
    goal_snapshot: list[dict]
    domain_records: dict[str, dict]
    prior_summary: dict
    memory: list[dict]
    agent_runs: list[dict]
    plan_set_id: str


def run_day_proposal(orchestrator, store, plan_date: str) -> str:
    """Load owned state, route agents, summarize history, and save an unapplied plan."""
    day = store.bootstrap_day(plan_date, create_if_missing=False)

    def dispatch(state: PlatformState) -> dict:
        run = AgentRun(ORCHESTRATOR, "dispatch",
                       f"Loaded current goals/items and {len(state['active_suggestions'])} "
                       "active Summary suggestion(s) from SQLite; delegated bounded domain review.")
        return {"agent_runs": [run.public()], "next_agent": "learning"}

    def domain_node(key: str):
        def assess(state: PlatformState) -> dict:
            snapshot = {"entries": [], "dayItems": state["source_items"]}
            run = orchestrator._domain_agents[key].assess(
                snapshot, "adjust", state["domain_records"].get(key))
            guidance = [item for item in state["active_suggestions"]
                        if item["domain"] in (key, "cross")]
            if guidance:
                run = AgentRun(run.spec, run.phase, run.summary + " Active Summary guidance: "
                               + "; ".join(f"{item['priority']}: {item['content']}"
                                           for item in guidance[:3]))
            return {"agent_runs": [*state["agent_runs"], run.public()],
                    f"{key}_snapshot": {"assessment": run.summary},
                    "next_agent": {"learning": "life", "life": "finance", "finance": "summary"}[key]}
        return assess

    def summarize(state: PlatformState) -> dict:
        prior_day = date.fromisoformat(state["current_date"]) - timedelta(days=1)
        start = prior_day - timedelta(days=29)
        facts = store.summary_facts(start.isoformat(), prior_day.isoformat())
        prior = orchestrator.summary_report("review", f"before-{state['current_date']}", facts)
        memory = store.feedback_memory(state["current_date"])
        domain_runs = [orchestrator._domain_agents[key].assess(
            {"entries": [], "dayItems": state["source_items"]}, "adjust",
            state["domain_records"].get(key))
            for key in DOMAIN_SPECS]
        run = orchestrator._summary.assess(domain_runs)
        run = AgentRun(run.spec, run.phase,
                       f"{run.summary} Prior 30-day evidence: {prior['recordedDays']} recorded days, "
                       f"{len(prior['feedback'])} named preference signals; "
                       f"{len(memory)} cumulative prior task preferences. Protected items remain eligible "
                       "for shorter, not omitted, blocks.")
        return {"prior_summary": prior, "memory": memory,
                "user_feedback": {"signals": memory},
                "agent_runs": [*state["agent_runs"], run.public()],
                "next_agent": "orchestrator"}

    def propose(state: PlatformState) -> dict:
        guidance = [*state["active_suggestions"], *state["prior_summary"]["suggestions"]]
        plan_set_id = store.create_recorded_plan(state["current_date"], state["memory"],
                                                 guidance)
        proposed = store.bootstrap_day(state["current_date"], create_if_missing=False)
        run = AgentRun(ORCHESTRATOR, "synthesis",
                       f"Proposed {len(proposed['variants'])} record-grounded alternative(s) "
                       "after Summary review of dated items and area records. "
                       "No alternative was applied.")
        return {"plan_set_id": plan_set_id, "pending_plans": proposed["variants"],
                "today_plan": {}, "needs_confirmation": True, "next_agent": "user",
                "agent_runs": [*state["agent_runs"], run.public()]}

    builder = StateGraph(PlatformState)
    builder.add_node("dispatch", dispatch)
    for key in DOMAIN_SPECS:
        builder.add_node(key, domain_node(key))
    builder.add_node("summary", summarize)
    builder.add_node("propose", propose)
    builder.add_edge(START, "dispatch")
    builder.add_edge("dispatch", "learning")
    builder.add_edge("learning", "life")
    builder.add_edge("life", "finance")
    builder.add_edge("finance", "summary")
    builder.add_edge("summary", "propose")
    builder.add_edge("propose", END)

    area_records = DomainRecords(store)
    initial: PlatformState = {
        "session_id": store.thread(), "user_input": "Propose from my dated records",
        "messages": [], "current_date": plan_date, "today_plan": {},
        "pending_plans": [], "active_suggestions": store.active_suggestion_pool(),
        "source_items": day["dayItems"],
        "domain_records": {key: area_records.snapshot(key, plan_date)
                           for key in DOMAIN_SPECS},
        "goal_snapshot": day["goals"], "needs_confirmation": False,
        "agent_runs": [], "knowledge_task_id": None,
    }
    checkpoint_path = store.path.with_name(f"{store.path.stem}.checkpoints.sqlite3")
    connection = sqlite3.connect(checkpoint_path, timeout=15, check_same_thread=False)
    try:
        serializer = JsonPlusSerializer(allowed_msgpack_modules=())
        graph = builder.compile(checkpointer=SqliteSaver(connection, serde=serializer))
        thread_id = f"day-proposal:{plan_date}:{uuid.uuid4().hex}"
        state = graph.invoke(initial, {"configurable": {"thread_id": thread_id}})
    finally:
        connection.close()
    store.record_plan_route(state["plan_set_id"], state["agent_runs"])
    return state["plan_set_id"]
