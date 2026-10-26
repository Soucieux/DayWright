from __future__ import annotations

import base64
import binascii
import hashlib
import os
import re
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import asynccontextmanager
from datetime import date as CalendarDate, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Literal, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from . import holidays, how_you_work, recall, record_search, workspace
from .agents import EARLIEST_RECORD, AgentOrchestrator
from .app_settings import AUTOMATIC, SETTINGS_FILE, AppSettings
from .area_choice import model_area
from .briefings import suggest_briefing
from .config import DEMO_FOLDER, DEMO_VARIABLE, load_settings
from .conversation import offer_continue, respond, suggest_links
from .database import Database
from .demo import build_demo
from .folder_check import ask as ask_check, check_folder, progress as check_progress
from .domain_records import DomainRecords
from .holiday_places import COUNTRIES, REGION_NAMES
from .holidays import HOLIDAYS_FILE, SOURCE_HOST, Holidays, ImportFailed
from .estimates import refine_estimate
from .learning_tasks import LearningTasks
from .opener import OpenError, obsidian_installed, open_source
from .plan_choice import model_chooser
from .repeat_repair import repair_repeats
from .source_store import SourceStore
from .sources import SourceError, SourceNotFound
from .local_import import MAX_FILE_BYTES, extract_local_file
from .model_gateway import ModelGateway
from .menubar import menu_model
from .models import ModelLibrary
from .periods import period_keys, sections
from .retrieval import EmbeddingGateway, RagService, VectorStore
from .schedule import day_schedule
from .speech import SpeechGateway, SpeechUnavailable
from .state_graph import refresh_earlier_proposals, refresh_earlier_routes

# The longest span one tasks request may cover, so a list stays a bounded read.
MAX_TASK_RANGE_DAYS = 400
# The parts a wider Summary report lists, by its period: a week's days, a month's weeks, all time's months.
SECTION_KINDS = {"week": "day", "month": "week", "all": "month"}
# How long the Mac's own folder picker waits for the user to choose a folder.
FOLDER_PICK_SECONDS = 600
# The Mac's folder picker, which answers with the chosen folder's path.
FOLDER_PICK_SCRIPT = 'POSIX path of (choose folder with prompt "Choose a folder for the Library")'
# The same picker, for the models folder Settings reads every model from.
MODELS_PICK_SCRIPT = 'POSIX path of (choose folder with prompt "Choose your models folder")'
# What Ava says instead of answering while her model or its runner isn't ready.
AVA_NEEDS_MODEL = "Ava needs a local model. Choose your models folder in Settings."
# Ava's cards that change Settings › Schedule: the work schedule, Your day, and the statutory holidays to import.
SETTINGS_CARDS = ("set_schedule", "set_your_day", "import_holidays")
# The Mac's file picker, which answers with each chosen file's path on a line of its own; one file, or several.
FILES_PICK_SCRIPT = ['set chosen to choose file with prompt "Choose files for the Library"{multiple}',
                     'if class of chosen is not list then set chosen to {chosen}',
                     'set paths to ""',
                     'repeat with picked in chosen',
                     'set paths to paths & POSIX path of picked & linefeed',
                     'end repeat',
                     'return paths']
# How often, while DayWright runs, it looks for timed Learning tasks whose start has come (see LearningTasks.check_due).
START_CHECK_SECONDS = 60
# How long a stop, on quit or a switch of workspace, waits for the work under way in the background to finish, within
# the time the desktop app gives its service to stop (STOP_GRACE in src-tauri/src/service.rs). Each step of that work
# is saved whole, so what isn't done by then is done again at the next start.
STOP_WAIT_SECONDS = 10
# The menu bar's title and menu, as one answer: `MENU_PATH` in src-tauri/src/menubar.rs.
MENU_PATH = "/api/now/menu"


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


class InterfaceLanguage(BaseModel):
    language: Literal["en", "zh"]


class WorkspaceChoice(BaseModel):
    """The workspace to open: the demo, or the user's own; and, for the demo, whether to make it anew."""
    workspace: Literal["demo", "own"]
    reset: bool = False


# The statuses a catch-up sets, by task id; a task left as it is is left out.
CaughtStatuses = dict[str, Literal["done", "partial", "skipped"]]


class CatchUp(BaseModel):
    statuses: CaughtStatuses


class ReminderIds(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=100)


class SuggestionDecision(BaseModel):
    decision: Literal["kept", "dismissed"]


class ChatRequest(BaseModel):
    date: str
    message: str = Field(min_length=1, max_length=4000)
    mode: Optional[Literal["ask", "adjust", "report"]] = None
    selectedVariantId: Optional[str] = None
    language: Literal["en", "zh"] = "en"


class MemoryEntry(BaseModel):
    """An entry Ava remembers, as Settings › Memory edits it or a card completes it; memory.checked_entry checks it."""
    kind: Literal["note", "rule"]
    ruleKind: Optional[Literal["keep-free", "keep-off", "finish-by"]] = None
    wording: str = Field(default="", max_length=2000)
    area: Optional[str] = Field(default=None, max_length=20)
    task: Optional[str] = Field(default=None, max_length=200)
    start: Optional[str] = Field(default=None, max_length=5)
    end: Optional[str] = Field(default=None, max_length=5)
    latest: Optional[str] = Field(default=None, max_length=5)
    days: list[int] = Field(default_factory=list, max_length=7)
    saidOn: str = Field(max_length=10)
    endsOn: Optional[str] = Field(default=None, max_length=10)


class ActionDecision(BaseModel):
    decision: Literal["confirmed", "dismissed"]
    # The area chosen on a new task's or goal's card, when the user changed the one suggested.
    domain: Optional[Literal["learning", "life", "work", "project"]] = None
    # The statuses chosen on a catch-up card, when the user changed the ones it proposed.
    statuses: Optional[CaughtStatuses] = None
    # The files left ticked on a folder check card, by their paths in the folder, when the user changed them.
    ticked: Optional[list[str]] = Field(default=None, max_length=20000)
    # On a check-times card, by task id, "right" or the minutes the task took, for the times the user checked.
    times: Optional[dict[str, Literal["right"] | int]] = None
    # On a card to remember, the entry as the user completed it, as when they filled what a rule still needed.
    memory: Optional[MemoryEntry] = None
    # On a card of things to remember, the places of those left ticked.
    kept: Optional[list[int]] = Field(default=None, max_length=200)


class KnowledgeSourceRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    sourceType: Literal["note", "document"] = "note"
    text: str = Field(min_length=1, max_length=2_000_000)


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    limit: int = Field(default=4, ge=1, le=10)


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


class FolderPath(BaseModel):
    """A folder the user picked or typed, anywhere on this Mac."""

    path: str = Field(min_length=1, max_length=4096)


class RunModelsOn(BaseModel):
    """Settings' Run models on: "automatic" or "processor" (see app_settings.RUN_MODELS_ON)."""

    runOn: str = Field(min_length=1, max_length=20)


class WorkSchedule(BaseModel):
    """Settings › Schedule's work schedule (see app_settings.AppSettings.work_schedule)."""

    enabled: bool
    mode: str = Field(min_length=1, max_length=20)
    start: str = Field(min_length=1, max_length=5)
    end: str = Field(min_length=1, max_length=5)
    days: list[int] = Field(max_length=7)


class YourDay(BaseModel):
    """Settings › Schedule's Your day (see app_settings.AppSettings.your_day)."""

    start: str = Field(min_length=1, max_length=5)
    end: str = Field(min_length=1, max_length=5)


class HolidayChoice(BaseModel):
    """Settings › Schedule's statutory holidays (see app_settings.AppSettings.holiday_settings)."""

    enabled: bool
    country: Optional[str] = Field(default=None, max_length=2)
    region: Optional[str] = Field(default=None, max_length=6)


class FolderConnect(FolderPath):
    # The tree's files the user unticked, and an address the folder's files also open on.
    unticked: list[str] = Field(default_factory=list, max_length=20000)
    website: str = Field(default="", max_length=2000)


class FolderTicks(BaseModel):
    # Every file of a connected folder's tree the user leaves unticked, as Change files… sends them.
    unticked: list[str] = Field(default_factory=list, max_length=20000)


class FileLocation(BaseModel):
    relativePath: str = Field(min_length=1, max_length=4096)


class WebsiteSource(BaseModel):
    address: str = Field(min_length=1, max_length=2000)
    briefing: str = Field(default="", max_length=600)


class BriefingChoice(BaseModel):
    briefing: Optional[str] = Field(default=None, max_length=600)
    outline: Optional[list[str]] = Field(default=None, max_length=8)
    by: Literal["ava", "you"] = "you"


class OpenRequest(BaseModel):
    # A source opens by its own stored path or address alone; nothing else in the request is used.
    where: Literal["app", "website"] = "app"


class OpenWithChoice(BaseModel):
    md: Optional[str] = Field(default=None, max_length=80)
    pdf: Optional[str] = Field(default=None, max_length=80)
    docx: Optional[str] = Field(default=None, max_length=80)


class FilesPick(BaseModel):
    multiple: bool = True


class FilesImport(BaseModel):
    paths: list[str] = Field(min_length=1, max_length=50)


class SourceLink(BaseModel):
    """A Library source a Learn task links as a reference."""

    sourceId: str = Field(min_length=1, max_length=100)


class OriginalPath(BaseModel):
    path: str = Field(min_length=1, max_length=4096)


class GoalChoice(BaseModel):
    # An active Learning goal to join, or the name of a new one; neither leaves the tasks ungrouped.
    goalId: Optional[str] = Field(default=None, max_length=100)
    title: Optional[str] = Field(default=None, max_length=200)


class TasksFromSource(BaseModel):
    sourceIds: list[str] = Field(min_length=1, max_length=100)
    date: str
    goal: Optional[GoalChoice] = None
    # One task a day from `date`, in the order ticked, rather than all on `date`.
    oneADay: bool = False
    # A new pass through each file, its checklist clean, rather than carrying on its latest.
    fresh: bool = False


class TaskEffort(BaseModel):
    effort: str = Field(min_length=1, max_length=20)


class ChecklistName(BaseModel):
    title: str = Field(max_length=200)


class ChecklistPlace(BaseModel):
    index: int = Field(ge=0, le=500)


class ChecklistTick(BaseModel):
    done: bool


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


def _made_on(path: Path) -> str | None:
    """The day a file was made, YYYY-MM-DD, by its birth time, or by its last change where the system keeps none; None
    while it isn't there."""
    try:
        made = path.stat()
    except FileNotFoundError:
        return None
    return datetime.fromtimestamp(getattr(made, "st_birthtime", made.st_mtime)).date().isoformat()


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
    switch: Optional[Callable[[bool, Optional[Path]], None]] = None,
    day_jobs: Optional[bool] = None,
    library: Optional[ModelLibrary] = None,
) -> FastAPI:
    settings = load_settings()
    # Ava's rounds while DayWright runs (see check_starts) go over DayWright's own data only, not a database handed in,
    # as a test's, unless one asks for them.
    day_jobs = (database is None and database_path is None) if day_jobs is None else day_jobs
    # How a change of workspace starts the service again (see workspace.switch); a test records it instead.
    switch = switch or workspace.switch
    # This start of the service, told apart from the one before a switch, so the window reloads once the new one answers.
    started = secrets.token_hex(8)
    # The demo is made the first time it opens, and again after Reset deleted it, ending today (see demo). One that
    # can't be made leaves the user's own workspace open, as quitting would, and is made again the next time.
    demo_failed = False
    if settings.demo_mode and database is None and database_path is None and not settings.database_path.exists():
        try:
            build_demo(settings.database_path, CalendarDate.today(), at=datetime.now().time())
        except Exception as error:
            print(f"DayWright couldn't make the demo, so the user's own workspace opens: {error}", file=sys.stderr)
            os.environ.pop(DEMO_VARIABLE, None)
            settings, demo_failed = load_settings(), True
    # Where the demo's database is, or will be once it is first opened, from either workspace.
    demo_database = settings.data_directory / DEMO_FOLDER / settings.database_path.name
    store = database or Database(database_path or settings.database_path)
    # Repeats copied without their series before v5.6 are linked once, in the user's own workspace alone; the demo
    # is made linked (see repeat_repair). What it did goes to the service's log.
    if database is None and database_path is None and not settings.demo_mode:
        repaired = repair_repeats(store, CalendarDate.today())
        if repaired:
            print(repaired, file=sys.stderr)
    # The person's own choices, in DayWright's data folder, for both workspaces; only the user's own database seeds them.
    shared = AppSettings((settings.data_directory if settings.demo_mode else store.path.parent) / SETTINGS_FILE,
                         seed_from=None if settings.demo_mode else store.path)
    # The statutory holidays imported in Settings › Schedule, kept beside the settings; DayWright goes online for them
    # on Import alone (see holidays).
    holiday_list = Holidays(shared.path.parent / HOLIDAYS_FILE)

    def holiday_on(day: str) -> Optional[dict]:
        """The statutory holiday `day` is while holidays are on, as holidays.on gives it; else None."""
        chosen = shared.holiday_settings()
        return holidays.on(holiday_list.kept(), day, chosen["country"], chosen["region"]) if chosen["enabled"] else None

    store.holiday_for = holiday_on
    # Plans fill Your day, set in Settings › Schedule, and the day is over at its end.
    store.your_day = shared.your_day
    # Plans keep the work schedule set in Settings › Schedule on the days it holds (see schedule.day_schedule).
    store.schedule_for = lambda day: day_schedule(shared.work_schedule(), day, store.holiday_for(day))
    domains = DomainRecords(store)
    # Every model is read from the folder chosen in Settings, none until one is; the demo, as it is made, reads none.
    library = library or ModelLibrary(shared, development_folder=settings.model_library, runner=settings.llama_binary)
    # Ava's and search's models run where Run models on, kept for both workspaces, allows.
    model = gateway or ModelGateway(settings, library, run_on=shared.run_models_on)
    embedder = embedding_gateway or EmbeddingGateway(settings, library, run_on=shared.run_models_on)
    rag = RagService(VectorStore(store.path), embedder)
    shelf = SourceStore(store)
    learning = LearningTasks(store, shelf)
    speech = speech_gateway or SpeechGateway(library)
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

    stopping = threading.Event()

    def noted(doing: str, error: Exception | None = None) -> None:
        """Log work that didn't finish, named by what it was to `doing`: once DayWright is stopping, which cuts short
        what is still running after the wait for it (see finish_background), as left for the next start, which carries
        it on; else as a failure, with why."""
        if stopping.is_set():
            print(f"DayWright stopped before it could {doing}; it's left for the next start.", file=sys.stderr)
        else:
            print(f"DayWright couldn't {doing}: {error}", file=sys.stderr)

    def later(work: Callable[[], object], doing: str) -> None:
        """Run some work in the background, so an answer never waits for it; one that fails is only logged (see
        noted), naming what it was to `doing`, and what was there before stays."""
        def run() -> None:
            try:
                work()
            except Exception as error:
                noted(doing, error)

        thread = threading.Thread(target=run, daemon=True)
        # Kept, while it runs, so the tests can wait for it before their throwaway folders go.
        app.state.indexing = [running for running in app.state.indexing if running.is_alive()] + [thread]
        thread.start()

    def index_later(folder_id: str, changed: list[str] | tuple = ()) -> None:
        """Index a folder's files for search in the background; see SourceStore.index. The next refresh retries."""
        later(lambda: shelf.index(rag, folder_id, changed), "index a folder for search")

    def check_later(folder_id: str) -> None:
        """Check a folder's new and changed files in the background, and have Ava report them; see folder_check. The
        folder shows it is being checked from now, before the files are counted."""
        ask_check(folder_id)
        later(lambda: check_folder(store, shelf, model, folder_id), "check a folder's files")

    def suggest_later(task: dict) -> None:
        """Have Ava suggest Library sources for a new Learn task in the background; see suggest_links."""
        if task["domain"] == "learning":
            later(lambda: suggest_links(store, rag, task["id"]), "suggest sources for a task")

    def profiles_after(folder_id: str, result: dict) -> dict:
        """Read again the tasks still to do from a refreshed folder's files that changed or moved, and their
        passages for search; answer with the refresh."""
        touched = set(result["changed"] + result["moved"])
        ids = [source["id"] for source in shelf.folder(folder_id)["sources"] if source["relativePath"] in touched]
        learning.refresh_profiles(ids)
        if result["found"]:
            index_later(folder_id, ids)
            check_later(folder_id)
        return result

    def refreshed(folder_id: str) -> dict:
        """Refresh a connected folder, and read again the tasks from its files that changed or moved."""
        return profiles_after(folder_id, shelf.refresh(folder_id))

    def refresh_sources() -> None:
        """Refresh every connected folder as the app opens, without holding up its start; a folder not
        found is only marked so."""
        try:
            for folder in shelf.folders():
                refreshed(folder["id"])
        except Exception as error:  # The Library keeps what it read before.
            noted("refresh the Library's folders", error)

    def keep_memory() -> None:
        """Ava's pass over the conversation (see recall.keep); a rule kept from its card of offers changes nothing
        until the user confirms it."""
        recall.keep(store, model, rag, CalendarDate.today().isoformat())

    def check_starts() -> None:
        """Look up again, as each starts, the websites of timed Learning tasks, now and then every
        START_CHECK_SECONDS while DayWright runs; one missed while it was closed is looked up now. Each round Ava
        also condenses any day over and clears the chat older than her window (see recall.keep), and brings the
        records' index in step with the records (see record_search.sync), the whole history at the first."""
        while not stopping.is_set():
            try:
                learning.check_due(datetime.now())
            except Exception as error:  # The tasks keep what they had; the next round tries again.
                noted("look a learning task's website up again", error)
            try:
                keep_memory()
            except Exception as error:  # The conversation stays as it is; the next round tries again.
                noted("condense or clear Ava's conversation", error)
            try:
                synced = record_search.sync(store, rag, CalendarDate.today().isoformat(), stop=stopping)
                if synced and synced["left"] and stopping.is_set():
                    noted("index the records for Ava")
            except Exception as error:  # The index keeps what it had; the next round carries on.
                noted("index the records for Ava", error)
            stopping.wait(START_CHECK_SECONDS)

    def finish_background() -> None:
        """Wait, up to STOP_WAIT_SECONDS in all, for Ava's round and the background work under way to finish."""
        deadline = time.monotonic() + STOP_WAIT_SECONDS
        for thread in [app.state.rounds, *app.state.indexing]:
            if thread is not None:
                thread.join(max(0.0, deadline - time.monotonic()))

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        later(refresh_sources, "refresh the Library's folders")
        if day_jobs:
            app.state.rounds = threading.Thread(target=check_starts, daemon=True)
            app.state.rounds.start()
        yield
        stopping.set()
        # Quitting, or a switch of workspace, lets the work under way finish first, so nothing is left half written.
        await run_in_threadpool(finish_background)
        model.stop()
        embedder.stop()

    app = FastAPI(title="DayWright local service", version="7.4.0", lifespan=lifespan)
    app.state.indexing = []
    app.state.rounds = None

    def relay(*days: Optional[str], areas: Optional[set[str]] = None) -> None:
        """Tell the Orchestrator a saved change touched tasks on these days, in these areas (None for
        every area, empty for none), to hand on to those area agents and Summary; they then look at
        today again."""
        try:
            orchestrator.relay_task_change(store, days, areas=areas)
        except Exception as error:  # The change is saved; the agents keep their earlier view of it.
            print(f"DayWright couldn't hand a task change on to the agents: {error}", file=sys.stderr)

    def energy_changed(day: str) -> None:
        """Tell every agent the day's energy changed; see AgentOrchestrator.relay_energy_change."""
        try:
            orchestrator.relay_energy_change(store, day)
        except Exception as error:  # The reading is saved; the agents keep their earlier view of it.
            print(f"DayWright couldn't hand an energy change on to the agents: {error}", file=sys.stderr)

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
                "voice": speech.status(), "models": library.states(), "demoMode": settings.demo_mode,
                "demoMade": demo_database.exists(), "demoMadeOn": _made_on(demo_database), "demoFailed": demo_failed,
                "started": started}

    def notices() -> dict:
        """Ava's messages about issues; how many are still unread, reminders left out as they never reach her chat; and
        today's reminders, which Today shows."""
        posted = store.notices()
        return {"notices": posted,
                "unreadNotices": sum(notice["readAt"] is None and notice["group"] != "reminder" for notice in posted),
                "reminders": store.reminders(CalendarDate.today().isoformat())}

    @app.post("/api/reminders/dismiss")
    def dismiss_reminders(dismissed: ReminderIds):
        store.dismiss_reminders(dismissed.ids)
        return notices()

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
            # Ava's panel holds the conversation of the last recall.CHAT_DAYS days; earlier days live on as summaries.
            "messages": recall.recent(store.messages(thread_id), CalendarDate.today().isoformat()),
            "model": model.status(),
            "agents": orchestrator.contract(),
            "rag": rag.status(),
            "voice": speech.status(),
            "models": library.states(),
            "demoMode": settings.demo_mode,
            # Today alone lists what yesterday left to fix.
            "yesterdayNotice": store.yesterday_notice(date_value) if date_value == CalendarDate.today().isoformat() else None,
            # On today, the year whose holidays to import (see holiday_reminder); the day carries its own holiday.
            "holidayReminder": holiday_reminder() if date_value == CalendarDate.today().isoformat() else None,
        }

    @app.post("/api/yesterday-notice/dismiss")
    def dismiss_yesterday_notice(day: PlanDate):
        """Hide Today's notice about the day it lists."""
        try:
            store.dismiss_yesterday_notice(date_from_iso(day.date))
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Use a valid YYYY-MM-DD date") from error
        return {"date": day.date}

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
        # The month's statutory holidays by date while holidays are on, as Today names them (see holidays.listed).
        chosen = shared.holiday_settings()
        marked = holidays.listed(holiday_list.kept(), chosen["country"], chosen["region"]) if chosen["enabled"] else []
        return {"month": month, "days": store.calendar_month(month),
                "holidays": {holiday["date"]: holiday for holiday in marked if holiday["date"].startswith(f"{month}-")}}

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
        # Each period with the one before it, whose energy its own is set against.
        last_month_end = month_start - timedelta(days=1)
        periods = (
            ("day", keys["day"], chosen, chosen, (chosen - timedelta(days=1),) * 2),
            ("week", keys["week"], week_start, week_end, (week_start - timedelta(days=7), week_start - timedelta(days=1))),
            ("month", keys["month"], month_start, month_end, (last_month_end.replace(day=1), last_month_end)),
        )
        profiles = store.task_profiles()
        reports = {}
        for kind, key, start, end, before in periods:
            frozen = store.saved_summary(kind, key) if end < CalendarDate.today() else None
            if frozen is not None:
                reports[kind] = frozen
            else:
                facts = store.summary_facts(start.isoformat(), end.isoformat(),
                                            before=tuple(day.isoformat() for day in before))
                reports[kind] = store.save_summary(
                    kind, key, orchestrator.summary_report(kind, key, facts, profiles)
                )
            store.sync_suggestion_pool(reports[kind])
            # The graphs read the records as they are now, even beside a report saved before them.
            reports[kind] = {**reports[kind], "graphs": store.report_graphs(start.isoformat(), end.isoformat())}
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
                "pool": {kind: store.suggestion_pool(kind, key) for kind, key, *_ in periods},
                "futurePrepared": prepared}

    @app.get("/api/patterns")
    def pattern_tab(date: str, period: Literal["week", "month", "all"]):
        """Calendar's Patterns tab for the period ending on the day on show (see Database.pattern_tab)."""
        try:
            day = date_from_iso(date)
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Use a valid YYYY-MM-DD date") from error
        return store.pattern_tab(day, period)

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
            suggest_later(saved)
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
            offered(item_id, saved["completion_status"])
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
            # What every recorded time shows of the area's repeating tasks, and Learn's pace and Life's energy line.
            return {**domains.snapshot(domain, day), "notes": notes, "patterns": store.area_patterns(domain)}
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
            saved = store.add_energy(date_from_iso(date), reading.level)
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Use a valid YYYY-MM-DD date") from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        # Every agent reads the day's new average, and Summary makes the day's reports again with it.
        energy_changed(saved["date"])
        return saved

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
        """The Library: its sources, each file with how far its latest pass has come if a task was made from it,
        and each with the tasks that use it (see Database.source_tasks)."""
        progress, tasks = learning.progress_by_source(), store.source_tasks()
        return {"sources": [{**source, "progress": progress.get(source["id"]), "tasks": tasks.get(source["id"], [])}
                            for source in rag.sources()], "rag": rag.status(),
                # A folder being checked says how far the check has come.
                "folders": [{**folder, "checking": check_progress.get(folder["id"])} for folder in shelf.folders()],
                "openWith": shared.open_with(), "obsidian": obsidian_installed()}

    @app.post("/api/knowledge/sources")
    def add_knowledge_source(source: KnowledgeSourceRequest):
        try:
            return rag.ingest(source.title, source.sourceType, source.text, datetime.now(timezone.utc).isoformat())
        except (ValueError, RuntimeError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.delete("/api/knowledge/sources/{source_id}")
    def remove_knowledge_source(source_id: str):
        try:
            shelf.forget(source_id)
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

    def source_answer(work: Callable[[], dict]) -> dict:
        """Run a source request, answering 404 for a source, folder or topic the Library doesn't have and
        422 with the reason for one that can't be read, reached or opened."""
        try:
            return work()
        except SourceNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except (SourceError, OpenError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/api/sources/folder/choose")
    def choose_folder():
        """Ask the Mac for a folder in its own window; the path is None when the user cancels."""
        answer = subprocess.run(["osascript", "-e", FOLDER_PICK_SCRIPT], capture_output=True, text=True,
                                timeout=FOLDER_PICK_SECONDS)
        return {"path": (answer.stdout.strip() or None) if answer.returncode == 0 else None}

    @app.post("/api/sources/files/choose")
    def choose_files(pick: FilesPick):
        """Ask the Mac for files in its own window, so each one imported remembers where it is; none when the
        user cancels."""
        lines = [line.replace("{multiple}", " with multiple selections allowed" if pick.multiple else "") for line in FILES_PICK_SCRIPT]
        answer = subprocess.run(["osascript", *(part for line in lines for part in ("-e", line))], capture_output=True,
                                text=True, timeout=FOLDER_PICK_SECONDS)
        return {"paths": [line for line in answer.stdout.splitlines() if line.strip()] if answer.returncode == 0 else []}

    @app.post("/api/sources/files/import")
    def import_files(request: FilesImport):
        """Import files chosen in the Mac's own window: each one's text, indexed as an upload's is, and where it
        is, so it opens there. One that can't be read is named with why, and the rest are imported."""
        saved, failed = [], []
        for path_text in request.paths:
            path = Path(path_text).expanduser()
            try:
                if path.suffix.lower() not in (".md", ".markdown", ".pdf", ".docx"):
                    raise ValueError("Supported files are Markdown (.md), PDF (.pdf), and Word (.docx)")
                if not path.is_file():
                    raise ValueError("It isn't there any more")
                if path.stat().st_size > MAX_FILE_BYTES:
                    raise ValueError("Choose a file smaller than 2 MB")
                data = path.read_bytes()
                title, text = extract_local_file(path.name, data)
                source = rag.ingest(f"{title} · {hashlib.sha256(data).hexdigest()[:12]}", "document", text,
                                    datetime.now(timezone.utc).isoformat())
                saved.append(shelf.remember_original(source["id"], str(path)))
            except (ValueError, SourceError) as error:
                failed.append({"name": path.name, "reason": str(error)})
            except RuntimeError as error:
                raise HTTPException(status_code=503, detail=str(error)) from error
        return {"saved": saved, "failed": failed}

    @app.post("/api/sources/{source_id}/original")
    def locate_original(source_id: str, original: OriginalPath):
        """Give an imported file whose original moved its new place on this Mac."""
        return source_answer(lambda: shelf.remember_original(source_id, original.path))

    @app.post("/api/sources/folder/preview")
    def preview_folder(folder: FolderPath):
        return source_answer(lambda: shelf.preview(folder.path))

    @app.post("/api/sources/folder")
    def connect_folder(folder: FolderConnect):
        connected = source_answer(lambda: shelf.connect(folder.path, folder.unticked, folder.website))
        index_later(connected["id"])
        check_later(connected["id"])
        return connected

    @app.post("/api/sources/folder/{folder_id}/refresh")
    def refresh_folder(folder_id: str):
        return source_answer(lambda: refreshed(folder_id))

    @app.post("/api/sources/folder/{folder_id}/relocate")
    def relocate_folder(folder_id: str, folder: FolderPath):
        return source_answer(lambda: profiles_after(folder_id, shelf.relocate(folder_id, folder.path)))

    @app.put("/api/sources/folder/{folder_id}/ticks")
    def change_folder_files(folder_id: str, ticks: FolderTicks):
        """Change files…: files newly ticked join the Library, indexed and checked as Refresh's new files are, and files
        newly unticked leave it; a file a task uses stays (see SourceStore.change_files)."""
        changed = source_answer(lambda: shelf.change_files(folder_id, ticks.unticked))
        if changed["added"]:
            index_later(folder_id)
            check_later(folder_id)
        return changed

    @app.post("/api/sources/{source_id}/locate")
    def locate_file(source_id: str, location: FileLocation):
        return source_answer(lambda: shelf.locate(source_id, location.relativePath))

    @app.post("/api/sources/website")
    def add_website(site: WebsiteSource):
        return source_answer(lambda: shelf.add_website(site.address, site.briefing))

    @app.post("/api/sources/{source_id}/look-up")
    def look_up_website(source_id: str):
        return source_answer(lambda: shelf.look_up(source_id))

    @app.post("/api/sources/{source_id}/suggest-briefing")
    def suggest_source_briefing(source_id: str):
        """Ava's suggested briefing for a source without one of its own, shown for editing and kept only on Confirm."""
        return source_answer(lambda: suggest_briefing(shelf, model, source_id))

    @app.put("/api/sources/{source_id}/briefing")
    def confirm_source_briefing(source_id: str, choice: BriefingChoice):
        return source_answer(lambda: shelf.set_briefing(source_id, choice.briefing, choice.outline, choice.by))

    @app.post("/api/sources/{source_id}/open")
    def open_library_source(source_id: str, request: OpenRequest):
        return source_answer(lambda: {"opened": open_source(shelf.open_target(source_id, request.where), shared.open_with(),
                                                            obsidian_installed())[1:]})

    @app.put("/api/sources/open-with")
    def set_open_with(choice: OpenWithChoice):
        return shared.set_open_with({kind: app for kind, app in choice.model_dump().items() if app})

    @app.get("/api/sources/entries")
    def source_entries(folderId: Optional[str] = None, sourceId: Optional[str] = None):
        if not folderId and not sourceId:
            raise HTTPException(status_code=422, detail="Choose a folder or a source")
        return {"entries": source_answer(lambda: learning.entries(folder_id=folderId, source_id=sourceId))}

    @app.post("/api/learning-tasks")
    def tasks_from_source(request: TasksFromSource):
        """Make a Learning task of each ticked file or page; a day with plans proposed and none set has them
        proposed again with them, as for any new task."""
        try:
            day = date_from_iso(request.date)
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Use a valid YYYY-MM-DD date") from error
        goal = request.goal and {key: value for key, value in request.goal.model_dump().items() if value}
        try:
            made = source_answer(lambda: learning.create_tasks(request.sourceIds, day, goal or None, request.oneADay, request.fresh))
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        days = sorted({task["date"] for task in made["tasks"]})
        relay(*days, areas={"learning"})
        for when in days:
            drafts_again(when)
        return made

    def checklist_answer(work: Callable[[], dict]) -> dict:
        """Run a change to a task's checklist, answering 404 for a task or item that isn't there, 422 for one
        that can't be made, and 409 for a past task's, which changes only through Ava."""
        try:
            return source_answer(work)
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    def link_answer(item_id: str, source_ids: list[str], link: bool) -> dict:
        """Link or unlink a Learn task's Library sources, answering with the task's checklist and links: 404 for a
        task or source that isn't there, 422 for a task outside Learn, 409 for a past task's, which change only
        through Ava."""
        try:
            store.link_sources(item_id, source_ids, link)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return learning.task(item_id)

    @app.post("/api/learning-tasks/{item_id}/sources")
    def link_task_source(item_id: str, source: SourceLink):
        return link_answer(item_id, [source.sourceId], True)

    @app.delete("/api/learning-tasks/{item_id}/sources/{source_id}")
    def unlink_task_source(item_id: str, source_id: str):
        """Unlink a source from a Learn task, its checklist source too: the task keeps its checklist and ticks."""
        return link_answer(item_id, [source_id], False)

    @app.get("/api/learning-tasks/{item_id}/checklist")
    def task_checklist(item_id: str):
        return checklist_answer(lambda: learning.task(item_id))

    @app.post("/api/learning-tasks/{item_id}/checklist")
    def add_checklist_item(item_id: str, entry: ChecklistName):
        return checklist_answer(lambda: learning.add_to_checklist(item_id, entry.title, datetime.now()))

    @app.put("/api/learning-tasks/{item_id}/checklist/{entry_id}")
    def rename_checklist_item(item_id: str, entry_id: str, entry: ChecklistName):
        return checklist_answer(lambda: learning.rename_in_checklist(item_id, entry_id, entry.title, datetime.now()))

    @app.delete("/api/learning-tasks/{item_id}/checklist/{entry_id}")
    def remove_checklist_item(item_id: str, entry_id: str):
        return checklist_answer(lambda: learning.remove_from_checklist(item_id, entry_id, datetime.now()))

    @app.post("/api/learning-tasks/{item_id}/checklist/{entry_id}/move")
    def move_checklist_item(item_id: str, entry_id: str, place: ChecklistPlace):
        return checklist_answer(lambda: learning.move_in_checklist(item_id, entry_id, place.index, datetime.now()))

    @app.post("/api/learning-tasks/{item_id}/checklist/{entry_id}/tick")
    def tick_checklist_item(item_id: str, entry_id: str, tick: ChecklistTick):
        return checklist_answer(lambda: learning.tick(item_id, entry_id, tick.done, datetime.now()))

    @app.put("/api/learning-tasks/{item_id}/effort")
    def set_task_effort(item_id: str, effort: TaskEffort):
        return checklist_answer(lambda: learning.set_effort(item_id, effort.effort))

    @app.post("/api/learning-tasks/{item_id}/briefing-opened")
    def briefing_opened(item_id: str):
        """An untimed Learning task's briefing opened: on its day, the first time, its website is looked up again
        as it starts; answer with the task's checklist and check as they are then."""
        def opened() -> dict:
            learning.briefing_opened(item_id, datetime.now())
            return learning.task(item_id)
        return checklist_answer(opened)

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
            offered(reported["itemId"], update.status)
            return relayed(reported, reported["date"], areas={reported["domain"]})
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    def offered(item_id: Optional[str], status: str) -> Optional[dict]:
        """Have a task reported done offer, through its area agent, the length its done times keep
        taking, when they keep differing from the one the user set (see Database.offer_usual_length).
        Returns the notice offering it, or None."""
        if status == "done" and item_id:
            try:
                return store.offer_usual_length(item_id)
            except sqlite3.OperationalError as error:  # The report is saved; the next one offers it.
                print(f"DayWright made no length offer this time: {error}", file=sys.stderr)
        return None

    @app.patch("/api/daily-items/{item_id}/status")
    def report_item(item_id: str, update: EntryUpdate):
        """Report one of today's tasks, as the menu bar's panel does."""
        try:
            reported = store.report_item(item_id, update.status)
            offered(item_id, update.status)
            return relayed(reported, reported["date"], areas={reported["domain"]})
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    def caught_up(items: list[dict]) -> list[str]:
        """What a catch-up's statuses bring, as each one reported alone does: a done task's usual length
        offered, and, as catching up asks, a partly done Learning task's follow-up offered once (see
        offer_continue). Returns the ids of the cards offered, for the save's undo to withdraw."""
        cards = []
        for item in items:
            if notice := offered(item["id"], item["status"]):
                cards.append(notice["values"]["actionId"])
            if item["status"] == "partial":
                try:
                    if proposal := offer_continue(store, item["id"]):
                        cards.append(proposal["id"])
                except sqlite3.OperationalError as error:  # The status is saved; the user can still ask Ava.
                    print(f"DayWright made no continue offer this time: {error}", file=sys.stderr)
        return cards

    @app.get("/api/catch-up")
    def catch_up_tasks():
        """Today's tasks as the catch-up sheet lists them, each with its status now."""
        day = CalendarDate.today().isoformat()
        return {"date": day, "tasks": store.catch_up_tasks(day)}

    @app.post("/api/catch-up")
    def catch_up(request: CatchUp):
        """Set several of today's tasks' statuses in one save, as Today's catch-up sheet does."""
        try:
            saved = store.catch_up(request.statuses)
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        store.keep_catch_up_offers(caught_up(saved["items"]))
        return relayed(saved, saved["date"], areas={item["domain"] for item in saved["items"]})

    @app.post("/api/catch-up/undo")
    def undo_catch_up():
        """Undo the last catch-up save, once, as its notice's Undo does."""
        try:
            undone = store.undo_catch_up()
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return relayed(undone, undone["date"], areas={item["domain"] for item in undone["items"]})

    @app.post("/api/day/pause")
    def pause_day():
        """Pause today: nothing is current and no time counts until Resume or the day's end."""
        try:
            return store.pause_day()
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/api/day/resume")
    def resume_day():
        """Resume today: the task then current is chosen as time_taken says."""
        try:
            return store.resume_day()
        except PermissionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get(MENU_PATH)
    def now_menu():
        """The menu bar's title and menu for today's current and next task, as the desktop shell reads them once a
        minute and after each change, in the interface's language; in the demo the title says so first (see menubar)."""
        language = shared.interface_language()
        return menu_model(store.now(language), language, demo=settings.demo_mode)

    @app.put("/api/interface-language")
    def interface_language(choice: InterfaceLanguage):
        """Keep the interface's language, in which the menu bar's title is written."""
        shared.set_interface_language(choice.language)
        return {"language": choice.language}

    @app.post("/api/workspace", status_code=202)
    def choose_workspace(choice: WorkspaceChoice, background: BackgroundTasks):
        """Open the demo workspace, or go back to the user's own: once this answer is sent the service stops, its
        background work finished, and starts again in place in the workspace chosen (see workspace). Reset deletes
        the demo first, so it is made anew, ending today."""
        demo = choice.workspace == "demo"
        if choice.reset and not demo:
            raise HTTPException(status_code=422, detail="Only the demo can be reset")
        if demo == settings.demo_mode and not choice.reset:
            raise HTTPException(status_code=409, detail="That workspace is already open")
        background.add_task(switch, demo, settings.data_directory / DEMO_FOLDER if choice.reset else None)
        return {"workspace": choice.workspace, "reset": choice.reset}

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
        # Without her model and its runner, Ava doesn't answer at all: no reply by rules and no card, and
        # nothing is kept; everything else works through its own buttons and sheets.
        if model.status()["state"] == "unavailable":
            raise HTTPException(status_code=409, detail=AVA_NEEDS_MODEL)
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
            settings=shared,
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

    def apply_settings_card(card: dict) -> None:
        """Keep what one of Ava's Settings › Schedule cards asks, before the card is confirmed: the work schedule, Your
        day, or the holidays imported for its years, with holidays turned on for its country and region.

        Raises:
            HTTPException: 503 when the Import fails, 409 when the schedule can't be kept; nothing changed, and the
                card stays to confirm.
        """
        payload = card["payload"]
        try:
            if card["actionType"] == "set_schedule":
                shared.set_work_schedule(payload["schedule"])
                return
            if card["actionType"] == "set_your_day":
                shared.set_your_day(payload["day"])
                return
            holiday_list.import_years(payload["country"], tuple(payload["years"]))
            shared.set_holiday_settings({"enabled": True, "country": payload["country"], "region": payload["region"]})
        except ImportFailed as error:
            raise HTTPException(status_code=503, detail=f"{error}. Nothing changed.") from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/api/actions/{action_id}")
    def decide_action(action_id: str, decision: ActionDecision):
        try:
            # A card changing Settings › Schedule is kept before it is decided, so one whose Import fails stays.
            card = store.pending_action(action_id)
            settings_card = card if card and card["actionType"] in SETTINGS_CARDS else None
            if settings_card and decision.decision == "confirmed":
                apply_settings_card(settings_card)
            decided = store.decide_action(action_id, decision.decision, decision.domain, decision.statuses, decision.ticked,
                                          decision.times, decision.memory and decision.memory.model_dump(), decision.kept)
            if settings_card:
                # Today's proposed plans follow it, as after a change in Settings.
                if decided["applied"]:
                    schedule_changed()
                return {**decided, "settings": schedule_view()}
            if "memory" in decided:
                # A rule kept, changed or deleted through Ava has today's proposed plans made again under the rules.
                memory_changed(*decided["memory"])
                return decided
            if "folderCheck" in decided:
                # The files left unticked on Ava's card leave the Library and their folder's ticks; the folder stays as it is.
                for source_id in decided["folderCheck"]["remove"]:
                    try:
                        shelf.forget(source_id)
                        rag.delete_source(source_id)
                    except (SourceError, ValueError):  # Removed meanwhile.
                        continue
                return decided
            if "created" in decided:
                # New tasks reach their areas' agents, an estimated length is refined, and a day with
                # plans proposed and none set has them proposed again with them.
                relay(*{task["date"] for task in decided["created"]}, areas={task["domain"] for task in decided["created"]})
                for task in decided["created"]:
                    suggest_later(task)
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
            if "caughtUp" in decided:
                # Ava's catch-up card brings what the sheet's save does, for the tasks it changed.
                caught_up(decided["caughtUp"])
                return relayed(decided, decided["date"], areas={item["domain"] for item in decided["caughtUp"]})
            if "energy" in decided:
                # A reading through Ava reaches every agent, as one made on Today does.
                energy_changed(decided["date"])
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

    @app.post("/api/model/stop")
    def stop_model():
        model.stop()
        return model.status()

    def models_view() -> dict:
        """Settings › Models: the models folder and each model's state in it (see ModelLibrary.states), Run models on
        as "runOn", and where each model runs as "devices" (see LlamaRuntime.device); voice runs on the processor."""
        return {**library.states(), "runOn": shared.run_models_on(),
                "devices": {"chat": model.status().get("device"), "embedding": embedder.status().get("device"),
                            "speech": {"state": "processor", "reason": None}}}

    @app.get("/api/models")
    def model_states():
        """The models, as Settings shows them (see models_view)."""
        return models_view()

    @app.post("/api/models/folder")
    def choose_models_folder(folder: FolderPath):
        """Read every model from this folder from now on; one running from another place stops first."""
        try:
            library.choose(folder.path)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        model.stop()
        embedder.stop()
        return models_view()

    @app.delete("/api/models/folder")
    def forget_models_folder():
        """Stop using the models folder: the models stop, and its files stay as they are."""
        model.stop()
        embedder.stop()
        library.forget()
        return models_view()

    @app.put("/api/models/run-on")
    def choose_run_models_on(choice: RunModelsOn):
        """Run the models on Automatic or Processor only: the servers running stop, so the next use starts there.
        Choosing Automatic lets go of any trouble with the graphics held this launch, so both try them again."""
        try:
            shared.set_run_models_on(choice.runOn)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        model.stop()
        embedder.stop()
        if choice.runOn == AUTOMATIC:
            model.retry_graphics()
            embedder.retry_graphics()
        return models_view()

    @app.post("/api/models/folder/choose")
    def pick_models_folder():
        """Ask the Mac for the models folder in its own window; the path is None when the user cancels."""
        answer = subprocess.run(["osascript", "-e", MODELS_PICK_SCRIPT], capture_output=True, text=True,
                                timeout=FOLDER_PICK_SECONDS)
        return {"path": (answer.stdout.strip() or None) if answer.returncode == 0 else None}

    def memory_changed(*entries: Optional[dict]) -> None:
        """After a rule changed: today's plans, proposed and none set, are made again under the rules as they are now,
        and the Orchestrator looks at today again. A note binds no plan, so one changing needs neither."""
        if any(entry and entry["kind"] == "rule" for entry in entries):
            today = CalendarDate.today().isoformat()
            drafts_again(today)
            relay(today, areas=set())

    @app.get("/api/memory")
    def memory_view():
        """Settings › Memory: the rules and notes Ava reads now, and the past ones (see Database.memory_view); and, as
        "records", how the user works from their records, in the interface's language (see how_you_work)."""
        today = CalendarDate.today().isoformat()
        return {**store.memory_view(today), "records": how_you_work.of_store(store, today, shared.interface_language())}

    @app.put("/api/memory/{entry_id}")
    def edit_memory(entry_id: str, entry: MemoryEntry):
        """Change an entry as Settings › Memory edits it, once it is complete (see memory.checked_entry)."""
        before = next((kept for kept in store.memory_entries() if kept["id"] == entry_id), None)
        if before is None:
            raise HTTPException(status_code=404, detail="That entry is no longer kept")
        try:
            after = store.save_memory(entry.model_dump(), entry_id)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        memory_changed(before, after)
        return memory_view()

    @app.delete("/api/memory/{entry_id}")
    def delete_memory(entry_id: str):
        """Delete an entry for good."""
        before = next((kept for kept in store.memory_entries() if kept["id"] == entry_id), None)
        if before is None:
            raise HTTPException(status_code=404, detail="That entry is no longer kept")
        store.delete_memory([entry_id])
        memory_changed(before)
        return memory_view()

    def holidays_view() -> dict:
        """Settings › Schedule's statutory holidays: the choice kept (see AppSettings.holiday_settings); the list kept
        for its country and region ("list", see holidays.listed), when it was imported ("importedAt") and for which
        "years", and the regions it has ("regions"); the "countries" and "regionNames" DayWright comes with (see
        holiday_places); and the one place DayWright goes online for them, on Import alone ("source")."""
        chosen, kept = shared.holiday_settings(), holiday_list.kept()
        mine = kept if kept and kept["country"] == chosen["country"] else None
        return {**chosen, "list": holidays.listed(kept, chosen["country"], chosen["region"]),
                "importedAt": mine["importedAt"] if mine else None, "years": mine["years"] if mine else [],
                "regions": holidays.regions(kept, chosen["country"]), "countries": [code for code, _ in COUNTRIES],
                "regionNames": REGION_NAMES, "source": SOURCE_HOST}

    def holiday_reminder() -> Optional[int]:
        """The year whose holidays Today reminds the user to import while holidays are on (see holidays.reminder)."""
        chosen = shared.holiday_settings()
        return holidays.reminder(holiday_list.kept(), chosen["country"], CalendarDate.today()) if chosen["enabled"] else None

    def schedule_view() -> dict:
        """Settings › Schedule: Your day ("day"), the work schedule and the statutory holidays (see holidays_view),
        kept for both workspaces."""
        return {"day": shared.your_day(), "schedule": shared.work_schedule(), "holidays": holidays_view()}

    def schedule_changed() -> None:
        """After the work schedule or the holidays changed: today's plans, proposed and none set, are made again under
        them, and the Orchestrator looks at today again, as after a rule changed."""
        today = CalendarDate.today().isoformat()
        drafts_again(today)
        relay(today, areas=set())

    def import_holidays(country: str) -> None:
        """Fetch this year's and next year's statutory holidays for the country from Nager.Date, the one time DayWright
        goes online for them, and keep them in place of those kept before.

        Raises:
            ImportFailed: When the fetch fails; nothing changed.
        """
        year = CalendarDate.today().year
        holiday_list.import_years(country, (year, year + 1))

    @app.get("/api/schedule")
    def schedule_settings():
        """Settings › Schedule, as schedule_view gives it."""
        return schedule_view()

    @app.put("/api/schedule")
    def keep_schedule(schedule: WorkSchedule):
        """Keep the work schedule, whole; today's plans follow it at once (see schedule_changed)."""
        try:
            shared.set_work_schedule(schedule.model_dump())
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        schedule_changed()
        return schedule_view()

    @app.put("/api/your-day")
    def keep_your_day(day: YourDay):
        """Keep Your day, whole, at least MIN_DAY_MINUTES long; today's plans follow it at once (see schedule_changed)."""
        try:
            shared.set_your_day(day.model_dump())
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        schedule_changed()
        return schedule_view()

    @app.put("/api/holidays")
    def keep_holidays(chosen: HolidayChoice):
        """Turn statutory holidays on or off and choose their country and region; nothing is fetched. Turning them
        off keeps the list imported. Today's plans follow at once (see schedule_changed)."""
        try:
            shared.set_holiday_settings(chosen.model_dump())
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        schedule_changed()
        return schedule_view()

    @app.post("/api/holidays/import")
    def import_holiday_list():
        """Import the chosen country's statutory holidays for this year and next (see import_holidays); a fetch that
        fails says so, and nothing changes."""
        country = shared.holiday_settings()["country"]
        if not country:
            raise HTTPException(status_code=422, detail="Choose a country to import its holidays")
        try:
            import_holidays(country)
        except ImportFailed as error:
            raise HTTPException(status_code=503, detail=f"{error}. Nothing changed.") from error
        schedule_changed()
        return schedule_view()

    @app.delete("/api/holidays")
    def remove_holidays():
        """Remove every holiday imported; the country and region chosen stay."""
        holiday_list.remove()
        schedule_changed()
        return schedule_view()

    return app


app = create_app()
