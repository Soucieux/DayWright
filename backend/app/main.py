from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import threading
from contextlib import asynccontextmanager
from datetime import date as CalendarDate, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .agents import AgentOrchestrator
from .config import load_settings
from .conversation import respond
from .demo import seed_demo_workspace
from .database import Database
from .domain_records import DomainRecords
from .knowledge_graph import PublicSourceUnavailable, WikipediaFetcher, acquire_topic
from .local_import import MAX_FILE_BYTES, extract_local_file
from .model_gateway import ModelGateway
from .retrieval import EmbeddingGateway, RagService, VectorStore
from .speech import SpeechGateway, SpeechUnavailable


class PlanSelection(BaseModel):
    date: str
    variantId: str
    replaceExisting: bool = False


class ClearSuggestionWeek(BaseModel):
    week: str
    domain: Literal["learning", "life", "finance", "rest", "cross"]
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
    mode: Literal["ask", "adjust", "report"] = "ask"
    selectedVariantId: Optional[str] = None
    language: Literal["en", "zh"] = "en"


class ActionDecision(BaseModel):
    decision: Literal["confirmed", "dismissed"]


class KnowledgeSourceRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    sourceType: Literal["note", "document", "import"] = "note"
    text: str = Field(min_length=1, max_length=2_000_000)


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    limit: int = Field(default=4, ge=1, le=10)


class KnowledgeTopicRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    explicitWeb: bool = False


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    domain: Literal["learning", "life", "finance", "rest"]


class GoalUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    status: Literal["active", "paused", "completed"]


class DailyItemCreate(BaseModel):
    date: str
    title: str = Field(min_length=1, max_length=200)
    detail: str = Field(default="", max_length=1000)
    domain: Literal["learning", "life", "finance", "rest"]
    startTime: str
    durationMinutes: int = Field(ge=1, le=1440)
    constraintKind: Literal["fixed", "flexible"] = "flexible"
    repeatKind: Literal["none", "daily", "weekly"] = "none"
    protected: bool = False
    goalId: Optional[str] = None


class DailyItemEdit(DailyItemCreate):
    status: Literal["planned", "done", "partial", "skipped"] = "planned"


class LearningItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    estimatedMinutes: int = Field(ge=1, le=1440)


class LearningSessionCreate(BaseModel):
    date: str
    itemId: str
    minutes: int = Field(ge=1, le=1440)
    result: Literal["done", "partial", "skipped"]


class LearningStatusUpdate(BaseModel):
    status: Literal["active", "done", "archived"]


class LifeHabitCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    frequency: Literal["daily", "weekly"] = "daily"


class LifeHabitLog(BaseModel):
    done: bool
    note: str = Field(default="", max_length=1000)


class LifeHabitStatusUpdate(BaseModel):
    active: bool


class LifeDailyUpdate(BaseModel):
    sleepHours: Optional[float] = Field(default=None, ge=0, le=24)
    energyLevel: Optional[int] = Field(default=None, ge=1, le=5)
    mood: Optional[int] = Field(default=None, ge=1, le=5)
    note: str = Field(default="", max_length=1000)


class LifeEventCreate(BaseModel):
    date: str
    title: str = Field(min_length=1, max_length=200)
    startTime: str
    endTime: str
    category: Literal["sport", "social", "chore", "health", "other"] = "other"
    flexible: bool = True


class OpeningBalanceUpdate(BaseModel):
    cents: int = Field(ge=-1_000_000_000_000, le=1_000_000_000_000)


class MoneyTransactionCreate(BaseModel):
    date: str
    type: Literal["income", "expense"]
    amountCents: int = Field(ge=1, le=1_000_000_000_000)
    category: str = Field(min_length=1, max_length=100)
    note: str = Field(default="", max_length=1000)


class MoneyBudgetUpdate(BaseModel):
    month: str
    category: str = Field(min_length=1, max_length=100)
    budgetCents: int = Field(ge=0, le=1_000_000_000_000)


def date_from_iso(value: str) -> str:
    parsed = CalendarDate.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Noncanonical date")
    return value


def nonblank_label(value: str, label: str) -> str:
    """Trim a user-entered record label and reject whitespace-only values."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{label} cannot be blank")
    return cleaned


def recorded_item(item: DailyItemCreate) -> dict:
    """Normalize a user's timed record before it reaches storage."""
    result = item.model_dump()
    result["date"] = date_from_iso(item.date)
    parsed = datetime.strptime(item.startTime, "%H:%M")
    if parsed.strftime("%H:%M") != item.startTime:
        raise ValueError("Use a valid HH:MM time")
    result["title"] = item.title.strip()
    if not result["title"]:
        raise ValueError("Title cannot be blank")
    result["detail"] = item.detail.strip()
    return result


def create_app(
    database_path: Optional[Path] = None,
    database: Optional[Database] = None,
    gateway: Optional[ModelGateway] = None,
    embedding_gateway: Optional[EmbeddingGateway] = None,
    public_fetcher: Optional[WikipediaFetcher] = None,
    speech_gateway: Optional[SpeechGateway] = None,
) -> FastAPI:
    settings = load_settings()
    store = database or Database(database_path or settings.database_path)
    if settings.demo_mode and database is None:
        seed_demo_workspace(store)
    domains = DomainRecords(store)
    import_lock = threading.Lock()
    model = gateway or ModelGateway(settings)
    embedder = embedding_gateway or EmbeddingGateway(settings)
    rag = RagService(VectorStore(store.path), embedder)
    if settings.demo_mode and not rag.sources():
        # A visible demo source without starting the embedding runtime during app boot.
        rag.vector_store.replace_source(
            "How DayWright uses local RAG", "note",
            ["DayWright chunks private notes, embeds them locally, retrieves relevant passages, and gives those passages to the local chat model. Calendar records are never sent to a public search service."],
            [[1.0] + [0.0] * 1023], datetime.now(timezone.utc).isoformat(),
        )
    speech = speech_gateway or SpeechGateway(settings)
    orchestrator = AgentOrchestrator()
    fetcher = public_fetcher or WikipediaFetcher()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        model.stop()
        embedder.stop()

    app = FastAPI(title="DayWright local service", version="0.1.0", lifespan=lifespan)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "model": model.status(), "rag": rag.status(),
                "voice": speech.status(), "demoMode": settings.demo_mode}

    @app.get("/api/bootstrap")
    def bootstrap(date: str, variant_id: Optional[str] = None, create_if_missing: bool = False):
        try:
            date_value = date_from_iso(date)
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Use a valid YYYY-MM-DD date") from error
        day = store.bootstrap_day(date_value, variant_id, create_if_missing)
        thread_id = store.thread()
        return {
            **day,
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
        year, week, _ = chosen.isocalendar()
        periods = (
            ("day", selected, chosen, chosen),
            ("week", f"{year}-W{week:02d}", week_start, week_end),
            ("month", chosen.strftime("%Y-%m"), month_start, month_end),
        )
        reports = {}
        for kind, key, start, end in periods:
            frozen = store.saved_summary(kind, key) if end < CalendarDate.today() else None
            if frozen is not None:
                reports[kind] = frozen
            else:
                facts = store.summary_facts(start.isoformat(), end.isoformat())
                reports[kind] = store.save_summary(
                    kind, key, orchestrator.summary_report(kind, key, facts)
                )
            store.sync_suggestion_pool(reports[kind])
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

    @app.post("/api/goals")
    def create_goal(goal: GoalCreate):
        title = goal.title.strip()
        if not title:
            raise HTTPException(status_code=422, detail="Goal title cannot be blank")
        return store.create_goal(title, goal.domain)

    @app.put("/api/goals/{goal_id}")
    def update_goal(goal_id: str, goal: GoalUpdate):
        title = goal.title.strip()
        if not title:
            raise HTTPException(status_code=422, detail="Goal title cannot be blank")
        try:
            return store.update_goal(goal_id, title, goal.status)
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/api/daily-items")
    def create_daily_item(item: DailyItemCreate):
        try:
            return store.create_daily_item(recorded_item(item))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.put("/api/daily-items/{item_id}")
    def update_daily_item(item_id: str, item: DailyItemEdit):
        try:
            return store.update_daily_item(item_id, recorded_item(item))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/api/areas/{domain}")
    def area_snapshot(domain: Literal["learning", "life", "finance"], date: str):
        try:
            return domains.snapshot(domain, date_from_iso(date))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/api/learning/items")
    def create_learning_item(item: LearningItemCreate):
        try:
            return domains.add_learning_item(
                nonblank_label(item.title, "Learning item"), item.difficulty,
                item.estimatedMinutes)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.patch("/api/learning/items/{item_id}")
    def update_learning_status(item_id: str, update: LearningStatusUpdate):
        try:
            return domains.set_learning_status(item_id, update.status)
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/api/learning/sessions")
    def add_learning_session(session: LearningSessionCreate):
        try:
            return domains.record_learning_session(
                date_from_iso(session.date), session.itemId, session.minutes,
                session.result)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/api/life/habits")
    def create_life_habit(habit: LifeHabitCreate):
        try:
            return domains.add_life_habit(
                nonblank_label(habit.title, "Habit"), habit.frequency)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.patch("/api/life/habits/{habit_id}")
    def update_life_habit(habit_id: str, update: LifeHabitStatusUpdate):
        try:
            return domains.set_life_habit_active(habit_id, update.active)
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.put("/api/life/habits/{habit_id}/logs/{date}")
    def record_life_habit(habit_id: str, date: str, log: LifeHabitLog):
        try:
            return domains.record_life_habit(
                date_from_iso(date), habit_id, log.done, log.note.strip())
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.put("/api/life/daily/{date}")
    def update_life_daily(date: str, daily: LifeDailyUpdate):
        try:
            return domains.set_life_daily(
                date_from_iso(date), daily.sleepHours, daily.energyLevel,
                daily.mood, daily.note.strip())
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/api/life/events")
    def create_life_event(event: LifeEventCreate):
        try:
            start = datetime.strptime(event.startTime, "%H:%M").strftime("%H:%M")
            end = datetime.strptime(event.endTime, "%H:%M").strftime("%H:%M")
            if start != event.startTime or end != event.endTime:
                raise ValueError("Use valid HH:MM event times")
            return domains.add_life_event(
                date_from_iso(event.date), nonblank_label(event.title, "Event"),
                start, end, event.category, event.flexible)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.put("/api/money/opening-balance")
    def update_opening_balance(balance: OpeningBalanceUpdate):
        return domains.set_opening_balance(balance.cents)

    @app.post("/api/money/transactions")
    def create_transaction(transaction: MoneyTransactionCreate):
        try:
            return domains.record_transaction(
                date_from_iso(transaction.date), transaction.type,
                transaction.amountCents,
                nonblank_label(transaction.category, "Category"),
                transaction.note.strip())
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.put("/api/money/budgets")
    def update_budget(budget: MoneyBudgetUpdate):
        try:
            first = CalendarDate.fromisoformat(f"{budget.month}-01")
            if first.strftime("%Y-%m") != budget.month:
                raise ValueError("Use a valid YYYY-MM month")
            return domains.set_budget(
                budget.month, nonblank_label(budget.category, "Category"),
                budget.budgetCents)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/api/plan/generate")
    def generate_plan(selection: PlanDate):
        try:
            plan_date = date_from_iso(selection.date)
            orchestrator.propose_day(store, plan_date)
            return store.bootstrap_day(plan_date, create_if_missing=False)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/api/knowledge")
    def knowledge():
        return {"sources": rag.sources(), "rag": rag.status()}

    @app.get("/api/knowledge/import-plans")
    def pending_import_plans():
        return {"pending": store.pending_knowledge_imports()}

    @app.post("/api/knowledge/sources")
    def add_knowledge_source(source: KnowledgeSourceRequest):
        try:
            return rag.ingest(
                source.title,
                source.sourceType,
                source.text,
                datetime.now(timezone.utc).isoformat(),
            )
        except (ValueError, RuntimeError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.post("/api/knowledge/import")
    async def import_local_file(request: Request):
        if request.headers.get("content-type", "").split(";")[0] != "application/octet-stream":
            raise HTTPException(status_code=415, detail="Choose a local Markdown, PDF, or Word file")
        encoded_name = request.headers.get("x-daywright-filename", "")
        if not encoded_name or len(encoded_name) > 400:
            raise HTTPException(status_code=422, detail="A short file name is required")
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
                              datetime.now(timezone.utc).isoformat())
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.post("/api/knowledge/search")
    def search_knowledge(search: KnowledgeSearchRequest):
        return rag.retrieve(search.query, search.limit).public()

    @app.post("/api/knowledge/topic")
    def acquire_knowledge_topic(request: KnowledgeTopicRequest):
        topic = request.topic.strip()
        if not topic:
            raise HTTPException(status_code=422, detail="Topic cannot be blank")
        try:
            return acquire_topic(rag, store, topic, request.explicitWeb, fetcher)
        except PublicSourceUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.post("/api/knowledge/import-plans/{plan_id}/confirm")
    def confirm_import_plan(plan_id: str):
        with import_lock:
            choice = store.knowledge_import_plan(plan_id)
            if not choice:
                raise HTTPException(status_code=404, detail="Import choice was not found")
            if choice["confirmed_plan_id"] and choice["confirmed_plan_id"] != plan_id:
                raise HTTPException(status_code=409, detail="Another import choice was confirmed")
            if choice["imported_source_id"]:
                source = next((item for item in rag.sources()
                               if item["id"] == choice["imported_source_id"]), None)
                return {"planId": plan_id, "source": source, "alreadyImported": True}
            try:
                source = rag.ingest(
                    f"{choice['title']} · {choice['name']}", "import", choice["content"],
                    datetime.now(timezone.utc).isoformat(), choice["source_url"],
                    choice["source_license"],
                )
                store.record_knowledge_import(plan_id, source["id"])
                return {"planId": plan_id, "source": source, "alreadyImported": False,
                        "organizationLabels": json.loads(choice["labels_json"])}
            except RuntimeError as error:
                raise HTTPException(status_code=503, detail=str(error)) from error
            except PermissionError as error:
                raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/api/plan/confirm")
    def confirm_plan(selection: PlanSelection):
        try:
            date_value = date_from_iso(selection.date)
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Use a valid YYYY-MM-DD date") from error
        try:
            return store.confirm_plan(date_value, selection.variantId, selection.replaceExisting)
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.patch("/api/entries/{entry_id}")
    def update_entry(entry_id: str, update: EntryUpdate):
        try:
            return store.update_entry(entry_id, update.status)
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
        return respond(
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

    @app.post("/api/actions/{action_id}")
    def decide_action(action_id: str, decision: ActionDecision):
        try:
            return store.decide_action(action_id, decision.decision)
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
