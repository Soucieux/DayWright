from __future__ import annotations

import base64
import binascii
import hashlib
import re
import sqlite3
import sys
import threading
from contextlib import asynccontextmanager
from datetime import date as CalendarDate, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Literal, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .agents import EARLIEST_RECORD, AgentOrchestrator
from .area_choice import model_area
from .config import load_settings
from .conversation import respond
from .demo import seed_demo_workspace
from .database import Database
from .domain_records import DomainRecords
from .estimates import refine_estimate
from .plan_choice import model_chooser
from .local_import import MAX_FILE_BYTES, extract_local_file
from .model_gateway import ModelGateway
from .periods import period_keys, sections
from .retrieval import EmbeddingGateway, RagService, VectorStore
from .speech import SpeechGateway, SpeechUnavailable
from .state_graph import refresh_earlier_proposals, refresh_earlier_routes

# The longest span one tasks request may cover, so a list stays a bounded read.
MAX_TASK_RANGE_DAYS = 400
# The parts a wider Summary report lists, by its period: a week's days, a month's weeks, all time's months.
SECTION_KINDS = {"week": "day", "month": "week", "all": "month"}


class PlanSelection(BaseModel):
    date: str
    variantId: str
    replaceExisting: bool = False


class ClearSuggestionWeek(BaseModel):
    week: str
    domain: Literal["learning", "life", "work", "project", "cross"]
    confirmation: str


class PlanDate(BaseModel):
    date: str


class EntryUpdate(BaseModel):
    status: Literal["planned", "done", "partial", "skipped"]


class SuggestionDecision(BaseModel):
    decision: Literal["kept", "dismissed"]


class ChatRequest(BaseModel):
    date: str
    message: str = Field(min_length=1, max_length=4000)
    mode: Optional[Literal["ask", "adjust", "report"]] = None
    selectedVariantId: Optional[str] = None
    language: Literal["en", "zh"] = "en"


class ActionDecision(BaseModel):
    decision: Literal["confirmed", "dismissed"]
    # The area chosen on a new task's or goal's card, when the user changed the one suggested.
    domain: Optional[Literal["learning", "life", "work", "project"]] = None


class KnowledgeLinks(BaseModel):
    """A Library note's or file's area, and the goal in that area it belongs to, if any."""

    domain: Literal["learning", "life", "work", "project"]
    goalId: Optional[str] = None


class KnowledgeSourceRequest(KnowledgeLinks):
    title: str = Field(min_length=1, max_length=200)
    sourceType: Literal["note", "document"] = "note"
    text: str = Field(min_length=1, max_length=2_000_000)


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    limit: int = Field(default=4, ge=1, le=10)
    # The area the Library is showing: only its notes and files are searched; without one, all of them are.
    domain: Optional[Literal["learning", "life", "work", "project"]] = None


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    domain: Literal["learning", "life", "work", "project"]


class GoalUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    status: Literal["active", "paused", "completed"]


class DailyItemCreate(BaseModel):
    date: str
    title: str = Field(min_length=1, max_length=200)
    detail: str = Field(default="", max_length=1000)
    domain: Literal["learning", "life", "work", "project"]
    startTime: Optional[str] = None
    # Left out, the task's area agent estimates it; given or estimated, a new length is at least 30 minutes.
    durationMinutes: Optional[int] = Field(default=None, ge=1, le=1440)
    constraintKind: Literal["fixed", "flexible"] = "flexible"
    repeatKind: Literal["none", "daily", "weekly"] = "none"
    goalId: Optional[str] = None


class DailyItemEdit(DailyItemCreate):
    # Left out, the task keeps its reported status: the task form edits everything else.
    status: Optional[Literal["planned", "done", "partial", "skipped"]] = None


class AreaSuggestion(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    detail: str = Field(default="", max_length=1000)
    goalId: Optional[str] = None


class EnergyReading(BaseModel):
    level: int = Field(ge=1, le=5)


def date_from_iso(value: str) -> str:
    parsed = CalendarDate.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Noncanonical date")
    return value


def recorded_item(item: DailyItemCreate) -> dict:
    """Normalize a user's record before it reaches storage.

    A fixed task needs a valid start time. A flexible one has none, whatever was sent: a plan
    chooses its time.
    """
    result = item.model_dump()
    result["date"] = date_from_iso(item.date)
    if item.constraintKind == "flexible":
        result["startTime"] = None
    elif item.startTime is None:
        raise ValueError("A fixed task needs a start time")
    elif datetime.strptime(item.startTime, "%H:%M").strftime("%H:%M") != item.startTime:
        raise ValueError("Use a valid HH:MM time")
    result["title"] = item.title.strip()
    if not result["title"]:
        raise ValueError("Title cannot be blank")
    result["detail"] = item.detail.strip()
    return result


def _refine_later(store: Database, model: ModelGateway, item_id: str, on_refined: Callable[[], None]) -> None:
    """Refine a task's estimated length with the local model, without holding up the save.

    Args:
        store: The database.
        model: The local model.
        item_id: The task.
        on_refined: Called once the length has changed, to hand the change on to the agents.
    """
    def refine() -> None:
        try:
            if refine_estimate(store, model, item_id):
                on_refined()
        except Exception as error:  # A failed refinement leaves the provisional estimate in place.
            print(f"DayWright kept the provisional estimate for {item_id}: {error}", file=sys.stderr)

    threading.Thread(target=refine, daemon=True).start()


def create_app(
    database_path: Optional[Path] = None,
    database: Optional[Database] = None,
    gateway: Optional[ModelGateway] = None,
    embedding_gateway: Optional[EmbeddingGateway] = None,
    speech_gateway: Optional[SpeechGateway] = None,
) -> FastAPI:
    settings = load_settings()
    store = database or Database(database_path or settings.database_path)
    if settings.demo_mode and database is None:
        seed_demo_workspace(store)
    domains = DomainRecords(store)
    model = gateway or ModelGateway(settings)
    embedder = embedding_gateway or EmbeddingGateway(settings)
    rag = RagService(VectorStore(store.path), embedder)
    if settings.demo_mode and not rag.sources():
        # A visible demo source without starting the embedding runtime during app boot.
        rag.vector_store.replace_source(
            "How DayWright uses local RAG", "note",
            ["DayWright chunks private notes, embeds them locally, retrieves relevant passages, and gives those passages to the local chat model. Nothing leaves this Mac."],
            [[1.0] + [0.0] * 1023], datetime.now(timezone.utc).isoformat(), "learning",
        )
    speech = speech_gateway or SpeechGateway(settings)
    orchestrator = AgentOrchestrator()
    # The area agents' profiles reflect every record before they review anything.
    store.rebuild_task_profiles()
    # Plans proposed by an earlier version get their route from the agents DayWright has now.
    for failure in refresh_earlier_routes(orchestrator, store):
        print(f"DayWright kept an earlier agent route for {failure}", file=sys.stderr)
    # Today's plans proposed by an earlier version could shorten a length the user set.
    failure = refresh_earlier_proposals(orchestrator, store)
    if failure:
        print(f"DayWright kept today's earlier plans for {failure}", file=sys.stderr)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        model.stop()
        embedder.stop()

    app = FastAPI(title="DayWright local service", version="4.2.0", lifespan=lifespan)

    def relay(*days: Optional[str], areas: Optional[set[str]] = None) -> None:
        """Tell the Orchestrator a saved change touched tasks on these days, in these areas (None for
        every area, empty for none), to hand on to those area agents and Summary; they then look at
        today again."""
        try:
            orchestrator.relay_task_change(store, days, areas=areas)
        except Exception as error:  # The change is saved; the agents keep their earlier view of it.
            print(f"DayWright couldn't hand a task change on to the agents: {error}", file=sys.stderr)

    def relayed(result: dict, *days: Optional[str], areas: Optional[set[str]] = None) -> dict:
        """Hand a saved change on to the agents of its areas, then answer with what was saved."""
        relay(*days, areas=areas)
        return result

    def reviewed(before: dict, after: dict) -> dict:
        """Have the Orchestrator hand an edit on to the agents its changes concern, then answer with the task.

        Only what changed counts: an edit that changes nothing an agent reads reaches no one, and a
        task moved to another day changes what both days hold.
        """
        try:
            orchestrator.review_task_edit(store, before, after)
        except Exception as error:  # The edit is saved; the agents keep their earlier view of it.
            print(f"DayWright couldn't hand a task edit on to the agents: {error}", file=sys.stderr)
        return after

    @app.get("/api/health")
    def health():
        return {"status": "ok", "model": model.status(), "rag": rag.status(),
                "voice": speech.status(), "demoMode": settings.demo_mode}

    def notices() -> dict:
        """Ava's messages about issues, and how many are still unread."""
        posted = store.notices()
        return {"notices": posted, "unreadNotices": sum(notice["readAt"] is None for notice in posted)}

    @app.post("/api/notices/read")
    def read_notices():
        store.read_notices()
        return notices()

    @app.get("/api/bootstrap")
    def bootstrap(date: str, variant_id: Optional[str] = None, create_if_missing: bool = False):
        try:
            date_value = date_from_iso(date)
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Use a valid YYYY-MM-DD date") from error
        day = store.bootstrap_day(date_value, variant_id, create_if_missing)
        if date_value == CalendarDate.today().isoformat():
            # The Orchestrator asks the area agents about today, and Ava posts each issue once a day.
            try:
                orchestrator.inspect_today(store, day=day)
            except sqlite3.OperationalError as error:  # Today still opens; the next opening posts them.
                print(f"DayWright posted no messages this time: {error}", file=sys.stderr)
        thread_id = store.thread()
        return {
            **day,
            **notices(),
            "threadId": thread_id,
            "messages": store.messages(thread_id),
            "model": model.status(),
            "agents": orchestrator.contract(),
            "rag": rag.status(),
            "voice": speech.status(),
            "demoMode": settings.demo_mode,
        }

    @app.get("/api/agents")
    def agents():
        return {"agents": orchestrator.contract()}

    @app.get("/api/calendar")
    def calendar(month: str):
        try:
            parsed = CalendarDate.fromisoformat(f"{month}-01")
            if parsed.strftime("%Y-%m") != month:
                raise ValueError("Invalid month")
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Use a valid YYYY-MM month") from error
        return {"month": month, "days": store.calendar_month(month)}

    @app.post("/api/summaries")
    def summaries(date: str):
        try:
            selected = date_from_iso(date)
            chosen = datetime.strptime(selected, "%Y-%m-%d").date()
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Use a valid YYYY-MM-DD date") from error
        week_start = chosen - timedelta(days=chosen.weekday())
        week_end = week_start + timedelta(days=6)
        month_start = chosen.replace(day=1)
        next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        month_end = next_month - timedelta(days=1)
        keys = dict(period_keys(chosen))
        periods = (
            ("day", keys["day"], chosen, chosen),
            ("week", keys["week"], week_start, week_end),
            ("month", keys["month"], month_start, month_end),
        )
        profiles = store.task_profiles()
        reports = {}
        for kind, key, start, end in periods:
            frozen = store.saved_summary(kind, key) if end < CalendarDate.today() else None
            if frozen is not None:
                reports[kind] = frozen
            else:
                facts = store.summary_facts(start.isoformat(), end.isoformat())
                reports[kind] = store.save_summary(
                    kind, key, orchestrator.summary_report(kind, key, facts, profiles)
                )
            store.sync_suggestion_pool(reports[kind])
        # Every record to date: made fresh each time, so it is neither saved nor a source of advice.
        reports["all"] = orchestrator.summary_report(
            "all", "all", store.summary_facts(EARLIEST_RECORD, CalendarDate.today().isoformat()), profiles)
        # Calendar can't pick one week or month, so a wider report lists the next level down, made fresh.
        first = store.first_record_date()
        spans = {"week": (week_start, week_end), "month": (month_start, month_end),
                 "all": (CalendarDate.fromisoformat(first), CalendarDate.today()) if first else None}
        for kind, span in spans.items():
            parts = []
            for key, start, end in sections(kind, *span, CalendarDate.today()) if span else ():
                facts = store.summary_facts(start.isoformat(), end.isoformat(), with_goals=False)
                if facts["recordedDays"]:
                    part = orchestrator.summary_report(SECTION_KINDS[kind], key, facts)
                    parts.append({"periodKind": SECTION_KINDS[kind], "periodKey": key, "start": start.isoformat(),
                                  "end": end.isoformat(), "recordedDays": part["recordedDays"],
                                  "domains": part["domains"], "suggestions": part["suggestions"]})
            reports[kind] = {**reports[kind], "sections": parts}
        prepared = (orchestrator.prepare_future_from_summary(store, reports["week"])
                    if selected == CalendarDate.today().isoformat() else [])
        return {"date": selected, "reports": reports,
                "pool": {kind: store.suggestion_pool(kind, key) for kind, key, _, _ in periods},
                "futurePrepared": prepared}

    @app.post("/api/suggestion-pool/{suggestion_id}/discard")
    def discard_pool(suggestion_id: str):
        try:
            return store.discard_pool_suggestion(suggestion_id)
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/api/suggestion-pool/clear-week")
    def clear_week(request: ClearSuggestionWeek):
        if not re.fullmatch(r"\d{4}-W(?:0[1-9]|[1-4]\d|5[0-3])", request.week):
            raise HTTPException(status_code=422, detail="Choose a valid ISO week")
        expected = f"CLEAR {request.week} {request.domain.upper()}"
        if request.confirmation != expected:
            raise HTTPException(status_code=422, detail="Type the exact week and area to clear")
        return store.clear_suggestion_week(request.week, request.domain)

    def goals_changed(result: dict, *days: str, areas: frozenset[str] = frozenset()) -> dict:
        """Hand a change to the goals on to Summary, whose reports list them, and to the area agents
        of `areas`, then answer with what was saved."""
        relay(CalendarDate.today().isoformat(), *days, areas=set(areas))
        return result

    @app.post("/api/goals")
    def create_goal(goal: GoalCreate):
        title = goal.title.strip()
        if not title:
            raise HTTPException(status_code=422, detail="Goal title cannot be blank")
        return goals_changed(store.create_goal(title, goal.domain))

    @app.put("/api/goals/{goal_id}")
    def update_goal(goal_id: str, goal: GoalUpdate):
        title = goal.title.strip()
        if not title:
            raise HTTPException(status_code=422, detail="Goal title cannot be blank")
        try:
            prior = next((entry for entry in store.goals() if entry["id"] == goal_id), None)
            saved = store.update_goal(goal_id, title, goal.status)
            # Pausing, resuming or completing a goal pauses or frees its tasks, which its area agent
            # watches; a rename, like those, changes its tasks' days in Summary's reports.
            moved = prior is not None and prior["status"] != saved["status"]
            return goals_changed(saved, *{item["date"] for item in saved["linkedItems"]},
                                 areas=frozenset({saved["domain"]} if moved else ()))
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.delete("/api/goals/{goal_id}")
    def delete_goal(goal_id: str):
        try:
            return goals_changed(store.delete_goal(goal_id))
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    def estimated(saved: dict) -> dict:
        """Have the task's area agent refine an estimated length with the local model, if it can run."""
        if saved["durationSource"] == "estimate" and model.status()["state"] != "unavailable":
            _refine_later(store, model, saved["id"], lambda: relay(saved["date"], areas={saved["domain"]}))
        return saved

    @app.post("/api/daily-items")
    def create_daily_item(item: DailyItemCreate):
        try:
            saved = store.create_daily_item(recorded_item(item))
            relayed(saved, saved["date"], areas={saved["domain"]})
            # As for a task Ava adds, a day with plans proposed and none set has them proposed again with it.
            drafts_again(saved["date"])
            return estimated(saved)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.put("/api/daily-items/{item_id}")
    def update_daily_item(item_id: str, item: DailyItemEdit):
        try:
            prior = store.daily_item(item_id)
            saved = store.update_daily_item(item_id, recorded_item(item))
            return estimated(reviewed(prior, saved))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.delete("/api/daily-items/{item_id}")
    def delete_daily_item(item_id: str):
        try:
            removed = store.delete_daily_item(item_id)
            return relayed(removed, removed["date"], areas={removed["domain"]})
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/api/daily-items")
    def list_daily_items(start: str, end: str):
        try:
            first, last = date_from_iso(start), date_from_iso(end)
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Use valid YYYY-MM-DD dates") from error
        span = (CalendarDate.fromisoformat(last) - CalendarDate.fromisoformat(first)).days
        if not 0 <= span <= MAX_TASK_RANGE_DAYS:
            raise HTTPException(
                status_code=422,
                detail=f"Choose a start date on or before the end, at most {MAX_TASK_RANGE_DAYS} days apart",
            )
        return {"start": first, "end": last, "items": store.daily_items_between(first, last)}

    @app.post("/api/daily-items/{item_id}/{decision}")
    def decide_daily_item(item_id: str, decision: Literal["accept", "dismiss"]):
        try:
            decided = store.set_item_acceptance(
                item_id, "accepted" if decision == "accept" else "dismissed"
            )
            return relayed(decided, decided.get("date"), areas={decided["domain"]})
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/api/areas/{domain}")
    def area_snapshot(domain: Literal["learning", "life", "work", "project"], date: str):
        try:
            day = date_from_iso(date)
            # The agents' notes are about today as it stands; another day's overview has none.
            notes = orchestrator.area_notes(store, domain) if day == CalendarDate.today().isoformat() else None
            return {**domains.snapshot(domain, day), "notes": notes}
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/api/areas/suggest")
    def suggest_area(request: AreaSuggestion):
        # A goal's tasks are in its area; otherwise the Orchestrator suggests one, asking the local
        # model only while it runs, so the form never waits for it to start.
        goal = next((entry for entry in store.goals() if entry["id"] == request.goalId), None) if request.goalId else None
        if goal:
            return {"domain": goal["domain"], "source": "goal"}
        ask = model_area(model) if model.status()["running"] else None
        return orchestrator.suggest_area(request.title.strip(), request.detail.strip(), ask)

    @app.put("/api/energy/{date}")
    def report_energy(date: str, reading: EnergyReading):
        try:
            saved = store.set_energy(date_from_iso(date), reading.level)
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Use a valid YYYY-MM-DD date") from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        # Life's agent reads it, and a low reading brings a lighter day.
        return relayed(saved, saved["date"], areas={"life"})

    @app.post("/api/plan/generate")
    def generate_plan(selection: PlanDate):
        try:
            plan_date = date_from_iso(selection.date)
            orchestrator.propose_day(store, plan_date, model_chooser(model))
            relay(plan_date, areas=store.day_areas(plan_date))
            return store.bootstrap_day(plan_date, create_if_missing=False)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/api/plan/repropose")
    def repropose_plan(selection: PlanDate):
        """Propose today's plans that aren't set again, from its tasks as they are now."""
        try:
            plan_date = date_from_iso(selection.date)
            orchestrator.propose_day(store, plan_date, model_chooser(model), again=True)
            relay(plan_date, areas=store.day_areas(plan_date))
            return store.bootstrap_day(plan_date, create_if_missing=False)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/api/knowledge")
    def knowledge():
        return {"sources": rag.sources(), "rag": rag.status()}

    def library_links(domain: str, goal_id: Optional[str]) -> None:
        """Refuse a Library item's goal unless it is a goal in the item's area."""
        try:
            store.check_library_link(domain, goal_id)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/api/knowledge/sources")
    def add_knowledge_source(source: KnowledgeSourceRequest):
        library_links(source.domain, source.goalId)
        try:
            return rag.ingest(source.title, source.sourceType, source.text, datetime.now(timezone.utc).isoformat(),
                              source.domain, source.goalId)
        except (ValueError, RuntimeError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.put("/api/knowledge/sources/{source_id}")
    def link_knowledge_source(source_id: str, links: KnowledgeLinks):
        library_links(links.domain, links.goalId)
        try:
            return rag.set_links(source_id, links.domain, links.goalId)
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.delete("/api/knowledge/sources/{source_id}")
    def remove_knowledge_source(source_id: str):
        try:
            return rag.delete_source(source_id)
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/api/knowledge/import")
    async def import_local_file(request: Request):
        if request.headers.get("content-type", "").split(";")[0] != "application/octet-stream":
            raise HTTPException(status_code=415, detail="Choose a local Markdown, PDF, or Word file")
        encoded_name = request.headers.get("x-daywright-filename", "")
        if not encoded_name or len(encoded_name) > 400:
            raise HTTPException(status_code=422, detail="A short file name is required")
        # A file joins an area, and a goal in it if one is chosen, as a note does.
        area, goal_id = request.headers.get("x-daywright-area", ""), request.headers.get("x-daywright-goal") or None
        if area not in ("learning", "life", "work", "project"):
            raise HTTPException(status_code=422, detail="Choose the file's area")
        library_links(area, goal_id)
        try:
            filename = base64.b64decode(encoded_name, validate=True).decode("utf-8")
            # Unsupported formats should be reported before reading or indexing the file.
            if Path(filename).suffix.lower() not in (".md", ".markdown", ".pdf", ".docx"):
                raise ValueError("Supported files are Markdown (.md), PDF (.pdf), and Word (.docx)")
        except (ValueError, UnicodeError, binascii.Error) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > MAX_FILE_BYTES:
                raise HTTPException(status_code=413, detail="Choose a file smaller than 2 MB")
        try:
            title, text = extract_local_file(filename, bytes(data))
            # A changed file with the same basename is a new retained source, not
            # an unapproved overwrite of a previously indexed document.
            revision = hashlib.sha256(data).hexdigest()[:12]
            return rag.ingest(f"{title} · {revision}", "document", text,
                              datetime.now(timezone.utc).isoformat(), area, goal_id)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.post("/api/knowledge/search")
    def search_knowledge(search: KnowledgeSearchRequest):
        return rag.retrieve(search.query, search.limit, area=search.domain).public()

    @app.post("/api/plan/confirm")
    def confirm_plan(selection: PlanSelection):
        try:
            date_value = date_from_iso(selection.date)
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Use a valid YYYY-MM-DD date") from error
        try:
            return relayed(store.confirm_plan(date_value, selection.variantId, selection.replaceExisting), date_value,
                           areas=store.day_areas(date_value))
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/api/plan/unset")
    def unset_plan(selection: PlanDate):
        try:
            date_value = date_from_iso(selection.date)
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Use a valid YYYY-MM-DD date") from error
        try:
            return relayed(store.unset_plan(date_value), date_value, areas=store.day_areas(date_value))
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.patch("/api/entries/{entry_id}")
    def update_entry(entry_id: str, update: EntryUpdate):
        try:
            reported = store.update_entry(entry_id, update.status)
            return relayed(reported, reported["date"], areas={reported["domain"]})
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/api/suggestions/{suggestion_id}")
    def decide_suggestion(suggestion_id: str, decision: SuggestionDecision):
        try:
            return store.decide_suggestion(suggestion_id, decision.decision)
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/api/chat")
    def chat(request: ChatRequest):
        try:
            date_from_iso(request.date)
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Use a valid YYYY-MM-DD date") from error
        reply = respond(
            store,
            model,
            request.date,
            request.message,
            request.mode,
            request.selectedVariantId,
            orchestrator,
            rag,
            request.language,
        )
        # A request to shorten a task counts in its profile and in today's reports, though nothing is
        # changed until confirmed; a reply that recorded none changes nothing an agent reads.
        if reply["feedbackSignals"]:
            relay(CalendarDate.today().isoformat(), areas={signal["domain"] for signal in reply["feedbackSignals"]})
        # With any doubt or question an area agent sent back about this request.
        return {**reply, **notices()}

    @app.post("/api/voice/transcribe")
    async def transcribe_voice(request: Request):
        if request.headers.get("content-type", "").split(";")[0] != "audio/wav":
            raise HTTPException(status_code=415, detail="Send PCM WAV audio")
        audio = bytearray()
        async for chunk in request.stream():
            audio.extend(chunk)
            if len(audio) > 2_000_000:
                raise HTTPException(status_code=413, detail="Voice recording exceeds 2 MB")
        try:
            return await run_in_threadpool(speech.transcribe, bytes(audio))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except SpeechUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    def meal_moved(decided: dict) -> dict:
        """After a confirmed meal move: propose today's plans again when it needs them, and hand it on.

        Whenever the move reaches today, today's plans that aren't set are made again around the new
        time; plans are only proposed for today, so a move from a later day on reaches none yet. A
        set plan up for review keeps its place, with new plans beside it ("review", its "options"
        each a plan's "id", "name" and "slug") for the user to pick from. A plan that changed
        reaches the area agents of the day's tasks; any move reaches Summary, and the agents look at
        today again.
        """
        today = CalendarDate.today().isoformat()
        update = decided["planUpdate"]
        options = []
        if update != "none":
            try:
                orchestrator.propose_day(store, today, model_chooser(model), again=True)
            except ValueError as error:  # The meal moved; plans that can't be made again stay as they were.
                print(f"DayWright couldn't propose today's plans again: {error}", file=sys.stderr)
            day = store.bootstrap_day(today, create_if_missing=False)
            options = [{"id": variant["id"], "name": variant["name"], "slug": variant["slug"]}
                       for variant in day["variants"] if variant["id"] != day["confirmedVariantId"]]
        relay(decided["date"], today, areas=store.day_areas(today) if update in ("adjusted", "review", "repropose") else set())
        return {**decided, **({"review": {"options": options}} if update == "review" else {})}

    def drafts_again(day: str) -> None:
        """Propose a day's plans again, from its tasks as they are now, when it has plans proposed and none set."""
        shown = store.bootstrap_day(day, create_if_missing=False)
        if shown["planSetId"] and not shown["confirmedVariantId"]:
            try:
                orchestrator.propose_day(store, day, model_chooser(model), again=True)
            except (ValueError, PermissionError) as error:  # The task moved; plans that can't be made again stay.
                print(f"DayWright couldn't propose {day}'s plans again: {error}", file=sys.stderr)

    @app.post("/api/actions/{action_id}")
    def decide_action(action_id: str, decision: ActionDecision):
        try:
            decided = store.decide_action(action_id, decision.decision, decision.domain)
            if "created" in decided:
                # New tasks reach their areas' agents, an estimated length is refined, and a day with
                # plans proposed and none set has them proposed again with them.
                relay(*{task["date"] for task in decided["created"]}, areas={task["domain"] for task in decided["created"]})
                for task in decided["created"]:
                    if task["estimated"] and model.status()["state"] != "unavailable":
                        _refine_later(store, model, task["id"], lambda day=task["date"], area=task["domain"]:
                                      relay(day, areas={area}))
                for day in sorted({task["date"] for task in decided["created"]}):
                    drafts_again(day)
                return decided
            if "after" in decided:
                # An edit to a task, as one made on its form, reaches the agents its changes concern; a past
                # task moved forward joins its new day's proposed plans, as a set plan stays as it was.
                reviewed(decided["before"], decided["after"])
                if decided["before"]["date"] < CalendarDate.today().isoformat() <= decided["after"]["date"]:
                    drafts_again(decided["after"]["date"])
                # The repeat's own days a change reached too.
                if decided.get("also"):
                    relay(*{other["date"] for other in decided["also"]}, areas={other["domain"] for other in decided["also"]})
                return decided
            if not decided["applied"]:
                return decided
            if "planUpdate" in decided:
                return meal_moved(decided)
            if "startsOn" in decided:
                # A repeat changed from a past day reaches its area from its first changed day on, and on
                # each day it no longer holds; a repeat starting today joins today's proposed plans.
                gone = decided.get("also", [])
                relay(decided["date"], decided["startsOn"], *{other["date"] for other in gone},
                      areas={decided["before"]["domain"], *(other["domain"] for other in gone)})
                drafts_again(decided["startsOn"])
                return decided
            # A change to one task reaches its area's agent; setting a plan, every area the day holds.
            return relayed(decided, decided["date"], areas=({decided["before"]["domain"]} if "before" in decided
                                                            else store.day_areas(decided["date"])))
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/api/model/start")
    def start_model():
        return model.start()

    @app.post("/api/model/stop")
    def stop_model():
        model.stop()
        return model.status()

    return app


app = create_app()
