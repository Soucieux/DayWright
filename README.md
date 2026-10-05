# DayWright

![Interface](https://img.shields.io/badge/Interface-React-61dafb) ![Desktop](https://img.shields.io/badge/Desktop-Tauri%20on%20macOS%2015%2B-24c8db) ![Service](https://img.shields.io/badge/Service-Python%20%2B%20FastAPI-05998b) ![Storage](https://img.shields.io/badge/Storage-SQLite%20%2B%20sqlite--vec-3f6e9b) ![Release](https://img.shields.io/badge/Release-v3.8%20build%2038-2f6f4f) ![Status](https://img.shields.io/badge/Status-Multi--agent%20RAG%20slice-f1512e)

<!-- project-control:section=overview -->
## Overview

DayWright is a private, single-user, local-first multi-agent daily-life management workbench for
goals, owned commitments, learning, life, work, and projects. Its central artifact is a user-approved
plan grounded in actual daily records. Bounded Learning,
Life, Work, Project, and Summary agents contribute assessments; the Orchestrator may propose today's plan
or a change for approval. Summary-informed future tasks that an agent prepares are pencilled in
with their evidence and wait until the user adds or dismisses them; they are not confirmed day plans.

The interface follows the Open Bench design: four places — Today (with Plans), Calendar, Goal,
and Library — and Ava, the assistant, which is reachable from each of them. Agents pencil and the user sets:
anything an agent proposes is dashed and names its agent until the user confirms it.

<!-- project-control:section=overview -->
## Current capabilities

- Open DayWright as a [Mac app](#desktop-app) that starts its own local service and stops it when
  you quit. The browser setup under [Quick start](#quick-start) remains for development.
- Set goals, record today's or future tasks, mark recurring commitments, and
  explicitly report progress. A fixed task has a start time; a flexible one has none until a plan
  you set places it. A fixed task can't overlap another timed task that day: taken start times are
  greyed out with what takes them. A length is optional: left blank, the task's area agent
  estimates it from your own records as soon as it is saved, then asks the local model, and plans
  use the estimate, shown as ≈. A length, given in the form or through Ava or estimated, is at
  least 30 minutes. A task added to a day with plans proposed and none set is placed in them,
  from the form or through Ava. The date defaults to today. Lunch (12:00–13:00) and dinner (18:00–19:00) are kept
  free: a fixed task can't start where it would run into them. Ava moves either, from today or a
  day you name on, or for one day, ending by midnight, and today's set plan is fitted around the
  new time or put up for review. A new user starts with an empty account, never an invented schedule.
- Create goal-linked or independent tasks directly in Learn, Life, Work, and Project. Areas go by
  purpose, in order: Work when someone else expects it, Project for a step toward something you're
  building that has an end, Learn when the point is getting better at something, and Life for
  everything else; the task form lists each meaning. A new task added without an area or goal of
  its own gets the area the Orchestrator suggests by that rule, by keywords for each purpose when
  one matches, else through the local model while it runs, and you can change it. Ask Ava to add a task ("Add Read chapter 4
  tomorrow at 9 for 45 min to my Spanish goal") or start a goal, with its first tasks, and it shows
  a card with the day, start, length, repeat and goal, or the suggested area you can change;
  nothing is added until you confirm, and the form's checks apply. Goals shows the linked work and overall
  completion progress, two goals to a row. Each goal shows the time it spans, from when you made it to that plus the length of
  every task in it, given or estimated; editing a goal lists all its tasks, with Edit on a task
  today or later and Delete on a past one. Every goal card is the same height and lists up to
  three tasks, with Show all for the rest. Pausing a goal pauses its tasks: plans skip them, and
  they can't be reported until the goal resumes.
- See the day at a glance in Today's header, even before anything is recorded: a 09:00–22:00
  strip with its timed tasks, lunch and dinner, a mark at the time now with the time gone shaded,
  what is next, and how much of the day is left and still open.
- Say how your energy is on Today, 1 to 5, once a day and only that day; you can change it until
  the day ends. At 2 or below the Life agent asks for a lighter day, as plans and Ava then show.
- See owned records, the next task, balance, and area links on Today. Beside the schedule, a Plan
  tab says which plan you are following, what it changed from your tasks and which agent finding
  led to each change, and a Summary agent tab reports on today. Flexible tasks without a start
  time sit in their own table under the schedule. Every schedule row, on Today, in Calendar and
  in Plans, shows its start time with its length below it.
- Browse past and future months in Calendar, see recorded-day month totals, select a day, and
  inspect its schedule, with the Summary agent's reports on a second tab. A past day is read-only
  there. Unrecorded dates stay empty rather than receiving invented history.
- Explicitly ask the Orchestrator to propose clearly different same-date alternatives from
  today's items and eligible recurrence. Each plan keeps fixed times, places tasks without a start
  time between 09:00 and 22:00 after the current moment, and keeps lunch and dinner free, shown
  in its schedule. Balanced is always offered: the areas take turns by priority, work and project
  first, then life, then learning. Beside it, each area agent votes for up to three plans that
  suit its own tasks, and the local model reads the day, from its tasks and their details to the
  agents' findings and votes, your energy and the plans you set most often, and picks two of Deep
  focus, Lighter day, Finish early, Quick wins first, Easiest first, Your usual rhythm, and
  Breathing room, saying why; without the model, the votes decide, and DayWright's own ranking
  fills any place left. A day gets
  three plans whenever three different ones can be made. Plans compares them side by side, or one at a time
  on a phone: each says in one line how it works, lists its first task, when the day ends, and the
  lengths it changed, says why it was suggested, and names what sets it apart. Plans never shorten
  a length you set; an estimated length may be shortened, never below 15 minutes. Task names in a
  plan are always in quotation marks.
- Before proposing, each area agent reviews its tasks for the day against all your records, kept
  as one profile per task: a task
  often left partly done or skipped gets a shorter block when its length is an estimate, a task
  usually finished keeps its length, and a flexible task usually done at a steady time is placed
  near that time by Your usual rhythm. Plans follow these findings, which Plans lists and Today's
  Plan tab cites beside each change. When the Life agent finds low energy, it advises a lighter
  day and Lighter day is listed first. Plans proposed by
  an earlier version get their agent list rebuilt by the current agents when DayWright starts.
- Confirm exactly one plan for a date; replacing it requires a named, explicit approval. Today's
  set plan can also be deselected: the proposed plans stay, to compare and set one again, and the
  tasks keep what was reported for them. Propose again rebuilds today's plans that aren't set from
  the tasks as they are now.
- Mark owned daily items and entries in the confirmed plan Planned, Done, Partial, or Skipped;
  linked records and goal progress stay synchronized.
- View saved Summary-agent reports and suggestions for a day, ISO week, or month, and in Calendar
  a report on all time, made fresh each time and holding no saved advice. Each report is laid out
  as outcomes by area, what the area agents see (tasks that keep slipping, whose length looks off,
  or that go well), unfinished tasks, and area records. In Calendar, Week lists its days, Month
  its weeks and All time its months, newest first, each with its own outcomes and advice. Explicit
  named-
  task shortening requests inform later plans and traceable agent-prepared future tasks. The
  current-week report can also suggest the next date of a repeat explicitly completed on at least
  two recorded days, its days linked whatever each is called: tomorrow when its latest day repeats
  daily, that day's weekday when weekly, and none once a day stops it or while its goal is paused;
  shortening feedback takes precedence. A
  suggestion waits on Today and in Calendar until the user adds or dismisses it.
- Open an area as one page of cards, built from its tasks, goals and repeats, each card with its
  days, what it counts, its numbers and a small visual: in every area the day's tasks with the
  area's own strip, and its agent's notes for today; Learn's subjects, with time done against
  planned, a practice row and the next session, and the week's practice bars; Life's habits with
  their rule and week grid, the day's shape with its free windows, and seven days of energy;
  Work's load bars, the week's meetings and what carried over, which Ava can move; and each
  project's status, step bar, next steps and what was done lately.
  A Learning goal with nothing done for 3 days is due for review and a Project goal stalls, which
  its area agent tells you through Ava once a day; a paused goal never does. Past reports stay
  read-only, and are made again when one of their tasks is edited.
- Manage saved soft/strong Summary advice by period and area. An active idea is dispatched to its
  relevant agent, and size/timing advice can prioritize a gentler variation. Discarding an idea
  stops its dispatch across periods; a matching later report shows a notice only. Clearing one
  exact week and area permanently requires typing its target, and cleared advice stays cleared.
- Keep or dismiss a contextual suggestion.
- Ask Ava, the assistant, about the plan, ask for a change, or report what happened, without
  choosing a mode: Ava works out which from the words and labels its reply Question, Change or
  Report. A proposed change lists exactly what would change, stays pencilled, and applies only when
  the user confirms it. Naming a task and a time, such as "Move Review to 10:30", proposes moving
  it there, or to the nearest free time when that one is taken. Ava answers from the day's tasks,
  its set and proposed plans with why each was suggested, the area agents' findings, goals with
  their progress, and the last 7 days, and suggests three questions for the place on show.
- Ask Ava for a different plan, and it offers the one the area agents vote for among the day's
  other plans; an area your words name counts double, and asking for a lighter day offers Lighter
  day.
- Hear from Ava when something needs attention: when an area agent finds a task that keeps
  slipping or whose length looks off, a Learning goal due for review or a stalled project, or the
  Orchestrator finds that today's tasks won't fit the time left, or fill most of it after you
  report low energy, Ava posts a message once that day, naming the agent. A red dot on Ava's button marks it until you open Ava.
- Ask Ava to change a task, and its area agent speaks up when its records disagree, such as a move
  far from when you usually do it or a length it was mostly left partly done at; the change stays
  ready to confirm. When a change names no task, or several, Ava asks which one. A question about
  nothing in your day is answered by the Orchestrator alone.
- Correct, remove or move forward a task on a past day through Ava, the only way such a task
  changes besides Delete in its goal's task list: name it and say what to change, its title,
  detail, area, goal or a status reported late, or move it to today or a later day, where it can
  be placed again; on its past day a task keeps its start, length and timing. Ava shows each
  change before and after, names what it left out, and nothing changes until you confirm.
  "Remove that task" or "change it" right after naming one means that task. A past task its day's
  set plan scheduled can be removed or moved too, and the plan keeps its entry, marked Removed or
  Moved to its new day, out of the counts. From a past day, a repeating task's change can reach
  that day alone or its repeat from today on too, and a repeat can start, stop or switch from today.
- Every change to a task, a plan or a goal goes to the Orchestrator, which hands it to the area
  agent of the task's area and to Summary; those agents then look at today again, and Ava posts
  anything new that needs your attention.
- On desktop Ava is a window floating over the page, so the page never narrows: it opens in the
  bottom-right corner, or beside an open sheet, and can be moved, made taller or shorter from its
  top edge, or put back with a double-click. A click anywhere outside it closes it. On a phone it
  opens as a sheet.
- Speak to Ava: press the microphone beside the empty box, and the words appear in the box as you
  say them, transcribed on this Mac; press stop, read them over and send.
- Switch the interface between English and Simplified Chinese; the same preference tells the local
  Orchestrator which language to use for its response.
- Open the route behind every reply and plan, Orchestrator → area agents → Summary, with each
  agent's one job under its name, and the Library sources a reply used.
- Persist agent contributions and their bounded read/write scopes with the conversation.
- Add private notes to the Library, chunk them locally, index their embeddings in `sqlite-vec`,
  and show which sources were retrieved for an answer. Browse every note and imported file, filter
  them by name or kind, and remove one in two steps.
- Select a Markdown, text-based PDF, or Word `.docx` file for bounded local extraction and indexing;
  unsupported formats and scanned PDFs produce a clear message. Files are not uploaded to a public
  provider or stored as originals. Changed files with the same name retain separate indexed versions.
- Look up a learning topic: a separate KnowledgeState graph searches the Library first. Going
  online needs the user's say-so every time — a switch that covers one lookup, or a card that
  appears when nothing local matches and shows exactly which words would go to
  `en.wikipedia.org`, what would be kept, and what is never sent. A fetched introduction and its
  URL/license are staged locally and indexed only once the user chooses one of three ways to
  organize it. Other choices cannot subsequently index the same acquisition. The graph keeps
  obvious personal identifiers out of a public query even when the user allows one.
- See every request that left the Mac in the network log, with the words sent, where they went,
  and what came back. A title-bar pill counts today's online lookups once there is one.
- Persist plans, conversation, proposals, and decisions in local SQLite storage.
- Use the existing local Qwen model for Orchestrator synthesis through `llama-server`; no model copy
  is kept here. When it can't run, Today says what still works, which local parts are missing, and
  that nothing is sent elsewhere instead.
- Open Goals, Tasks across dates, and the Learn, Life, Work, and Project areas from Goal, each
  on its own row. Each area is one page of cards, and its forms open in a sheet beside the page. Scheduled items still match
  the same day's records in Calendar. Library sources are not automatically calendar events.

## Quick start

Requirements: Node.js 20 or newer, Python 3.12 or newer, and the model setup described under
[Local models](#local-models) for model-backed conversation.

1. In a terminal, move into the `DayWright` folder.
2. Prepare the local service once:

   ```sh
   python3.12 -m venv .venv12
   .venv12/bin/pip install -r backend/requirements.txt
   ```

3. Start the local service:

   ```sh
   npm run api
   ```

4. In a second terminal, from the same `DayWright` folder, start the interface:

   ```sh
   npm run dev
   ```

5. Open the local address shown by the interface command. The title bar's status pill reads
   “Private on this Mac · Model on standby” until the first model-backed conversation starts the
   model, then “Model ready”.

For a populated walkthrough that cannot mix with personal records, start `npm run api:demo`, then
start the interface with `DAYWRIGHT_API_TARGET=http://127.0.0.1:8423 npm run dev`. The demo uses
`backend/data/daywright.demo.sqlite3`, shows a persistent demo banner, and contains sample goals,
today tasks, domain records, and read-only historical plans. It intentionally starts before today's
plan is generated, so the presenter can begin by selecting “Propose plans” on Today, compare the
alternatives, and set one.

If an older local service and interface are already running, stop those two terminal commands and
start them again to load this source revision. Refreshing an older preview alone may still show its
previously loaded service routes.

**Success check:** A fresh account has no plan. Add a goal, a fixed task with a start time, and a
flexible task without one for today, then select “Propose plans” on Today. Plans shows the available alternatives side by side;
setting one updates Today, Calendar, Goals, and the areas. Calendar can move to a
previous month without creating history, and day/week/month Summary-agent reports stay visible.

If the service is not running, the interface opens in an honest offline view. Nothing is sent,
generated, or saved, and it does not simulate an agent answer.

## Desktop app

`DayWright.app` runs the same interface and local service without a terminal, on macOS 15 or
later. Open it like any Mac app: a start screen shows while its service starts, then Today opens.
DayWright's own title bar holds the window buttons, and links to web pages open in your browser.
The window opens at, and can't be made smaller than, 1412 × 938 points. Quitting stops the
service and any model it started.

- **Your records:** kept in `~/Library/Application Support/DayWright/`, apart from the development
  database in `backend/data/`. The app starts with an empty account.
- **Models:** the same shared library and `llama-server` as [Local models](#local-models). macOS
  asks once for access to the Documents folder, where the models live, and may ask again after a
  rebuild, because the app is signed on this Mac rather than with an Apple developer ID.
- **If it doesn't start:** the start screen says so, and the reason is in
  `~/Library/Logs/DayWright/service.log`, which each launch begins afresh.
- **Release:** v3.8 build 38. About DayWright, in the app menu, shows it as Version 3.8.0 (38).

To build it you also need Rust (stable, through rustup) and Xcode's command-line tools. From the
`DayWright` folder:

```sh
npm install
npm run desktop
```

The first build downloads the service's Python packages into `build/desktop-venv` and Tauri's Rust
crates; later builds reuse them. The app is written to
`src-tauri/target/release/bundle/macos/DayWright.app`. Keep the copy you use at `DayWright.app` in
this folder, which Git ignores, or wherever you keep your apps.

<!-- project-control:section=workflows -->
## Workflow

```text
Open Today
set goals and record your actual daily items
  ↓
ask the Orchestrator to propose from owned/eligible recurring items
  ↓
each plan places tasks without a start time in free time, its own way
  ↓
compare the proposed plans side by side in Plans
  ↓
set one plan for the day
  ↓
report Done / Partial / Skipped on today's owned items/current plan
  ↓
review day/week/month Summary-agent advice and explicit preference evidence
  ↓
inspect past plans as read-only snapshots; preset future commitments now
  ↓
add or dismiss agent-prepared future tasks, each showing its Summary evidence
  ↓
explicitly review a replacement if another plan becomes preferable

Ask or mark up the plan
embed the question with Qwen3 Embedding 0.6B
  ↓
retrieve the nearest locally indexed private or attributed public chunks from sqlite-vec
  ↓
Orchestrator routes the request
  ↓
Learning / Life / Work / Project review their tasks against all your records
  ↓
Summary sums up what they found
  ↓
the Orchestrator answers as Ava through the shared local Qwen runtime
  ↓
structured proposal appears
  ↓
user confirms or dismisses it
```

A plan proposal does not set or replace a plan by itself, and a Summary-informed future task is
prepared with its provenance but stays pencilled until the user adds it. The SQLite record, not
conversational wording, is the source of truth.

For a selected local file, DayWright accepts at most 2 MB, 20 PDF pages, and 50,000 extracted
characters. Only readable text is indexed; a scanned or encrypted PDF needs preparation first.
For a new Library topic, the entered words alone go to Wikipedia, and only after the user allows it
for that lookup: by switching on the public introduction before looking up, or by choosing “Fetch
intro” on the card that appears when nothing local matches. DayWright asks every time; there is no
always-allow. Each request is written to the local network log with what was sent and what came
back. Private source text, goals, and daily records are never in that request. An unavailable local
embedding service does not lead to a public-lookup offer, because DayWright cannot establish that
the local library has no match.
The fetched introduction remains a pending local import until the user selects and confirms one of
three organization schemes; only then are its text chunks embedded and indexed. These labels do not
yet constitute verified paragraph-level classification.

<!-- project-control:section=models -->
## Local models

**Shared model storage:** DayWright uses the shared **AI-Models library in the Mac's Documents
folder**, rather than maintaining separate project-owned model copies.

| Capability | Library-relative path | Connection |
|---|---|---|
| Conversation | `gguf/Qwen3-4B-Q4_K_M.gguf` | Loaded directly by the installed `llama-server` on first use |
| Semantic retrieval | `gguf/Qwen3-Embedding-0.6B-Q8_0.gguf` | Loaded by a separate embedding-only `llama-server` when indexing or retrieval begins |
| Voice transcription | `whisper/faster-whisper-small/` | Browser WAV capture and local `faster-whisper` CPU inference; original Core ML model remains untouched |

For a new local setup, after installing `backend/requirements.txt`, download the converted
multilingual small model once from the [publisher's model repository](https://huggingface.co/Systran/faster-whisper-small)
into the default shared library:

```sh
.venv12/bin/python -c 'from pathlib import Path; from faster_whisper.utils import download_model; download_model("small", output_dir=str(Path.home() / "Documents/AI-Models/whisper/faster-whisper-small"))'
```

The local service uses only this saved path for transcription; it does not fetch a model when a
user presses the microphone. Listening begins only when the microphone beside Ava's empty box is
pressed; the Mac app asks once for microphone access. While the user speaks, the words so far are
transcribed every 1.5 seconds and shown in the box; stop transcribes the whole clip, up to 30
seconds, and leaves it in the box to read over and send, and Escape discards it. The audio is
discarded after recognition.

The service expands the shared library from the current macOS home folder. Override only for a
deliberate alternate setup:

```sh
DAYWRIGHT_MODEL_LIBRARY=/absolute/path/to/AI-Models npm run api
```

The chat and embedding runtimes use separate `llama-server` processes because they serve different
model contracts, while one shared supervisor owns their duplicated process lifecycle. It serializes
concurrent first-use requests until the relevant health check succeeds, binds a dynamically selected
loopback port, supplies a random per-launch token through the child process environment, disables
the web interface and request logs, runs offline on the CPU-safe backend, and stops each process
with the DayWright service. A failed launch returns the existing rule-based or unavailable state
instead of crashing the API. The app continues to plan and persist data if either model cannot start.

The embedding model produces 1,024-dimensional normalized vectors. DayWright stores those vectors
in a `vec0` virtual table inside the same local SQLite database as the source text and metadata.
Documents are currently chunked into 180-word windows with a 30-word overlap. A question is embedded
with a retrieval instruction, nearest chunks are selected, and the chat model receives the original
question plus those passages. Raw embedding arrays are never placed in the chat prompt.
An explicit distance threshold prevents an unrelated nearest neighbor from being treated as useful
evidence merely because it is the closest item in a small library.

Each agent has one job. Each area agent reviews its own tasks for the day against all your
records, and its own records, deterministically. It reads them from one profile per task, kept in
the same SQLite database and rebuilt from every record when DayWright starts and after each change,
so history never needs a second store; an agent reads only its own area's profiles. The planner
applies its findings and the interface shows them, for plans and for Ava's replies alike. Each area
agent also votes for up to three plans that suit its own tasks, and reports to the Orchestrator what
needs your attention. Summary sums up what was recorded, with how each area agent sees its tasks:
the day in a route, and each day, week, month or all time in its reports, the wider ones broken
down by day, week or month. The Orchestrator routes each request to the area agents it concerns, or
answers alone a question about nothing in your day, hands a change to its task's own agent for any
doubt, weighs their reviews, votes and Summary's sum-up, and alone decides: it builds the
plans, which needs no chat model, has Qwen choose among them with the votes, answers as Ava with
Qwen once per reply, and has Ava post each issue once a day. This preserves meaningful agent boundaries without loading the same 2.5 GB model
six times.

The existing Qwen3 4B model passed the current cross-domain workload, so no additional model was
downloaded or copied into the project. A larger replacement should be considered only after a
repeatable quality benchmark shows that its improvement outweighs local memory and response-time
costs.

<!-- project-control:section=architecture -->
## Architecture

| Layer | Responsibility |
|---|---|
| React interface | Open Bench places — Today with Plans, Calendar, Goal (Goals, Tasks, and the four areas), and Library — with Ava floating over each of them |
| Desktop shell (Tauri) | One window with DayWright's title bar; starts the bundled service with a new secret for each launch, shows the interface once the service answers, sends other web addresses to the browser, and stops the service on quit |
| FastAPI service | Local API, validation, conversation policy, and model lifecycle |
| Desktop service entry | The service frozen into the app: serves the interface and API from one loopback address (port 8425 when free), answers only the app's window, exits with the app, and stops model servers a crash left behind |
| Multi-agent core | PlatformState day-proposal graph with a separate SQLite checkpoint file, the area agents' all-time reviews, votes and issues, Summary's sum-up, and the Orchestrator's one run that proposes |
| KnowledgeState graph | Local-first topic lookup checkpointed outside the vector database; a public fetch only with the user's consent for that lookup, logged, then bounded filtering and three staged import choices before indexing |
| Deterministic planner | Valid record-based alternatives, each placing tasks without a start time in free time around fixed ones; repeated named-task evidence, the area agents' findings on length and usual time, duration arithmetic, and lengths you set, which no plan shortens |
| SQLite repository | Goals, owned items, plan snapshots, reports, the area agents' task profiles, explicit feedback, conversations, Ava's messages, decisions, sources, retrieval provenance, and the network log |
| `sqlite-vec` index | Local 1,024-dimensional nearest-neighbor search beside the authoritative records |
| Shared `LlamaRuntime` supervisor | Authenticated loopback process startup, health readiness, concurrent first-use serialization, failure recovery, and shutdown |
| ModelGateway | Local chat-model response contract over the shared runtime supervisor |
| EmbeddingGateway | Separate embedding-only contract for indexing and question retrieval over the shared supervisor |
| SpeechGateway | Short, user-initiated local WAV transcription through a converted Whisper-small model; temporary audio is removed after the request |

The service is loopback-only, in the documented development command and in the desktop app.
Generated private data and `daywright.checkpoints.sqlite3` live in `backend/data/`, which Git
ignores, or in the desktop app's Application Support folder. Checkpoints are
execution snapshots; the main database remains the authority for confirmed plans and sources.

## Project map

| Path | Contents |
|---|---|
| `src/` | React interface organized by place (`today/`, `plans/`, `calendar/`, `records/`, `library/`, `talk/`), with the shell in `shell/`, shared controls in `ui/`, and the Open Bench styles in `bench.css` |
| `design/` | Open Bench handoff: the interface specification, colour and type tokens, and icons |
| `backend/app/` | Local service, multi-agent core, SQLite/`sqlite-vec` storage, planner, retrieval, and model gateways |
| `backend/tests/` | Planner, API, database-migration, and desktop-service behavior checks, kept off local data by `isolation.py` |
| `src-tauri/` | Desktop shell: the window, service supervision, app icons, and bundle settings |
| `splash.html`, `src/desktop/` | The desktop app's start screen |
| `scripts/build-desktop-service.sh`, `backend/desktop_service.py`, `backend/requirements-desktop.txt` | Freezing the local service for the desktop app |
| `docs/Original Product Design.md` | Full original 767-line product design text retained as the detailed architecture source |
| `docs/DayWright — Product Design.md` | Revised product, UX, data, AI, privacy, and delivery specification |
| `docs/design-reference.png` | Approved visual source used for implementation and QA |
| `design-qa.md` and `design-qa-*.png` | Desktop, mobile, and multi-agent drawer evidence for the earlier folio interface |
| `worker/`, `.openai/`, `scripts/prepare-sites-build.mjs` | Preserved local prototype packaging contract; no hosted deployment is claimed |

## Design source

The current interface follows the [Open Bench handoff](design/HANDOFF.md), with its tokens in
`design/tokens/` and its icons in `design/icons/`.

The [original product design](docs/Original%20Product%20Design.md) retains the detailed component
contract. The [revised product design specification](docs/DayWright%20%E2%80%94%20Product%20Design.md) defines product
scope, confirmation rules, state ownership, local-model policy, privacy requirements, and staged
delivery. The approved visual reference at `docs/design-reference.png` established the first
slice’s palette, typographic hierarchy, and editorial materials. The specification's
[fidelity ledger](docs/DayWright%20%E2%80%94%20Product%20Design.md#19-original-design-contract-and-fidelity-ledger)
maps the original platform contract to present source and remaining work. The retained
[design QA](design-qa.md) distinguishes the original comparison from subsequent management-flow
browser inspection and isolated behavior checks.

## Checks

Run the implementation checks from the `DayWright` folder:

```sh
npm test
```

This builds the interface, checks the static packaging contract, exercises the interface's date,
plan-comparison, task, Library, and Ava helpers, and exercises the local planner, the API, and
the desktop service's session check, port choice, and model-process cleanup. The backend tests run
on a temporary database and fail if any of them reaches `backend/data/`, so they never touch local
records. Model loading is checked separately because it uses the 2.5 GB shared model at runtime.
`npm run desktop` builds the [desktop app](#desktop-app).

## Current boundaries

- The desktop app is signed only on the Mac that builds it: it has no Apple developer ID or
  notarization, no installer, and no automatic updates. Replies are not streamed and a running
  request cannot be cancelled.
- Supervised folder import is the next stage. Library currently
  accepts private pasted notes, selected Markdown/PDF/Word files, and locally checked public topics.
  Voice capture, the local transcription endpoint, the installed `faster-whisper` runtime, and
  converted Whisper-small inference have been exercised through the real API with synthetic
  speech, and the words shown while speaking with a simulated microphone and transcriber; no user
  microphone recording was made during those checks.
- Goal-linked today/future records, daily/weekly carry-forward, and traceable agent-origin
  future commitments exist. Every area keeps tasks, goals and repeats only, and its page reads
  them; mastery/review workflows still remain.
- A plan places tasks without a start time between 09:00 and 22:00, never before the moment it is
  proposed, and keeps lunch and dinner free (12:00–13:00 and 18:00–19:00 unless moved through
  Ava); a meal a fixed task already takes is left out. When today's free time can't hold them all,
  it says so rather than leaving one out.
- Summary now uses goals, plan outcomes, repeats, the energy you report, indexed-source counts, and
  exact-title shortening requests. It does
  not yet reason over all Library text or every conversational nuance. Its
  current-period reports run on demand and saved past reports freeze after the period ends; full
  summary-to-plan provenance and semantic suggestion-similarity detection remain. Matching repeats
  are presently based on exact normalized domain/content, not a semantic model.
- Day proposals and topic acquisition use separate LangGraph states and a separate SQLite
  checkpoint file to avoid concurrent checkpoint writes in the `sqlite-vec` database, while
  conversation routing has not joined a complete main graph; the original architecture is not
  claimed fully implemented. Checkpoint retention controls are not yet present.
- Public research is limited to short attributed Wikipedia introductions; wider web/MCP providers,
  multi-source credibility comparison, verified passage-level classification, finance providers,
  and remote AI are intentionally absent. Pending public text remains locally stored until import
  choice/retention controls are implemented.
- Ava proposes plans and replacements for them, moves, lengths, meal times, corrections to past
  tasks, repeats started, stopped or switched, and new tasks and goals, each on a card you
  confirm. The design's schedule preview of a pending change, and Report-mode
  proposals that record several things at once, are not built; progress is still reported with
  each task's status control.
- The personal-topic guard recognizes English personal words, email addresses, and long numbers,
  but not a Chinese word such as 我的. The consent card still shows the exact words before anything
  is sent.
- Local storage is not yet encrypted and the user-facing backup/export/delete controls required for
  production are not built.

<!-- project-control:section=ignore -->
## Contributing

For source changes, follow the [DayWright contribution guide](CONTRIBUTING.md).

<!-- project-control:section=history -->
## Change history

**Change-history numbering:** This project uses marketing versions and integer build numbers, from
v1.0 build 10; earlier records are dated. Follow the [version and build policy](CONTRIBUTING.md#version-and-build-policy).

One record per change; complete details and evidence are below. Older work dates and Git checkpoints remain labelled when they differ.

**Historical status:** Each record describes its own delivery checkpoint. Later records supersede older pending work or recovery locations; historical checks are not new validation.

| Record | Date | Highlights | Details |
|---|---|---|---|
| v3.8 / build 38 | 2026-10-05 | <ul><li><strong>Areas:</strong> Each area is one page of cards with no tabs, two to a row: the day's tasks, its agent's notes, and its own cards, each with its days, numbers and a small visual.</li><li><strong>Work:</strong> Ask Ava to move types the request for a carried-over task into Ava's box, to send when you choose.</li><li><strong>Tasks:</strong> Every estimated length is at least 30 minutes, a task added in the form joins its day's proposed plans, and keywords decide a suggested area when one matches.</li></ul> | [Full record](#v3-8-build-38) |
| v3.7 / build 37 | 2026-10-04 | <ul><li><strong>Ava:</strong> Ava adds a task from your words, with its day, start, length, repeat and goal, or starts a goal with its first tasks; a card shows it all and nothing is added before Confirm.</li><li><strong>Areas:</strong> A task without a goal, or a new goal, gets the suggested area on the card, and you can change it there.</li><li><strong>Thinking:</strong> The dots beside "Consulting the relevant agents locally" sit centred on the line.</li></ul> | [Full record](#v3-7-build-37) |
| v3.6 / build 36 | 2026-10-04 | <ul><li><strong>Repeats:</strong> Stopping a repeat from a past day removes its days still to do from today, unless today's was reported or set; switching to weekly removes those off its weekday; the card names them.</li><li><strong>Move:</strong> An event's Detail that was only its category is cleared when the area records fold in.</li><li><strong>Work:</strong> Carried over leaves out skipped tasks.</li></ul> | [Full record](#v3-6-build-36) |
| v3.5 / build 35 | 2026-10-04 | <ul><li><strong>Areas:</strong> Areas go by purpose, each one's meaning is in the task form, and the Orchestrator suggests a new task's area.</li><li><strong>Overviews:</strong> Each area's Overview is built from its tasks, goals and repeats, and goals due for review or stalled reach Ava; Learning's and Life's own records fold into tasks and goals once.</li><li><strong>Today:</strong> Energy in one tap, 1 to 5; 2 or below brings Lighter day.</li><li><strong>Goals:</strong> Two goals to a row.</li></ul> | [Full record](#v3-5-build-35) |
| v3.4 / build 34 | 2026-10-04 | <ul><li><strong>Past days:</strong> Ava corrects, removes or moves a past task forward, but its start, length and timing stay put; a moved task is marked Moved to its new day and counts there.</li><li><strong>Repeats:</strong> A repeat's days are linked, so renaming a day keeps the habit whole; from a past day a repeat can start, stop or switch from today, and a change to a repeating task asks whether the repeat changes too.</li><li><strong>Plans:</strong> A deleted task leaves today's proposed plans rewritten without it, a meal change reaches every proposed plan of today, and a past plan's time by area leaves out Removed and Moved entries.</li><li><strong>Cards:</strong> "Move dinner today" and "on Fri 9 Oct".</li></ul> | [Full record](#v3-4-build-34) |
| v3.3 / build 33 | 2026-10-04 | <ul><li><strong>Past plans:</strong> A removed task's entry stays on show, marked Removed, but leaves Calendar's counts, Summary's reports and the area profiles.</li><li><strong>Drafts:</strong> A task deleted today leaves today's proposed plans.</li><li><strong>Summary:</strong> A paused goal's task still to do isn't counted as scheduled, and its repeat gets no keep advice.</li><li><strong>Meals:</strong> "From Friday on" moves a meal for good from that day, replacing one-day times; a meal ends by midnight; a paused goal's fixed task is in the way of a move.</li></ul> | [Full record](#v3-3-build-33) |
| v3.2 / build 32 | 2026-10-04 | <ul><li><strong>Ava:</strong> Moving lunch or dinner on a past day is refused in words, where a past day whose plan left that meal out used to fail.</li><li><strong>Repeats:</strong> A weekly task's next date is prepared on its own weekday, and a paused goal's repeating task is no longer prepared.</li><li><strong>Goals:</strong> A task with no start is listed last in its day on a goal card.</li></ul> | [Full record](#v3-2-build-32) |
| v3.1 / build 31 | 2026-10-04 | <ul><li><strong>Meals:</strong> Ava moves lunch or dinner, from now on or for one day, and today's set plan is fitted around the new time or put up for review.</li><li><strong>Schedules:</strong> Every row on Today, in Calendar and in Plans shows its start with its length below it; a meal reads just Lunch or Dinner.</li><li><strong>Goals:</strong> Cards of one height, each listing up to three tasks, with Show all for the rest.</li></ul> | [Full record](#v3-1-build-31) |
| v3.0 / build 30 | 2026-10-03 | <ul><li><strong>Past plans:</strong> A removed task's entry stays in its past plan, marked Removed.</li><li><strong>Ava:</strong> "Remove that task" or "change it" right after naming a task means that task.</li><li><strong>Refusal:</strong> A direct change to a past task is refused in English or Chinese.</li></ul> | [Full record](#v3-0-build-30) |
| v2.9 / build 29 | 2026-10-03 | <ul><li><strong>Agents:</strong> Each change goes to its task's own area agent and Summary, and they look at today again at once; a goal's pause reaches its area agent too.</li><li><strong>Past days:</strong> Only Ava and Delete in a goal's list change a past task, and a past task its plan scheduled can be removed, the plan keeping its entry.</li></ul> | [Full record](#v2-9-build-29) |
| v2.8 / build 28 | 2026-10-03 | <ul><li><strong>Past days:</strong> Read-only on screen again; a past task changes or is removed only through Ava, applied when you confirm, or is deleted from its goal's task list.</li><li><strong>Agents:</strong> Every change to a task, and every change to a goal, reaches the agents it concerns.</li><li><strong>Goals and Tasks:</strong> Clearer refusals with bordered OK buttons, and no goal filter on Tasks.</li></ul> | [Full record](#v2-8-build-28) |
| v2.7 / build 27 | 2026-10-03 | <ul><li><strong>Ava:</strong> No more folding down; a click anywhere outside Ava closes it, and its own button still opens and closes it.</li></ul> | [Full record](#v2-7-build-27) |
| v2.6 / build 26 | 2026-10-03 | <ul><li><strong>Agents:</strong> The Orchestrator hands a task's change only to the agents it concerns, and a task moved or resized on its form gets its area agent's doubt in Ava.</li><li><strong>Tasks:</strong> Protected is gone; a length you set is what no plan shortens, and Summary prepares any repeating task you keep finishing.</li></ul> | [Full record](#v2-6-build-26) |
| v2.5 / build 25 | 2026-10-03 | <ul><li><strong>Goals:</strong> A tidier Edit goal sheet where every task, past ones included, can be edited, and matching buttons on each card.</li><li><strong>Agents:</strong> Every change to a task reaches its area agent and Summary through the Orchestrator, so reports and advice follow it.</li><li><strong>Ava:</strong> Names the day it answers about, marks where the conversation turns to another day, shows when it is thinking, and folds to a small bar.</li><li><strong>Today, plans and Calendar:</strong> A day strip that shows the time now, the time gone and what the time left holds; paused tasks named wherever a plan shows them; past days that name the plan they used.</li></ul> | [Full record](#v2-5-build-25) |
| v2.4 / build 24 | 2026-10-03 | <ul><li><strong>Tasks:</strong> Editing a task keeps the outcome already reported for it, including when its goal is paused.</li><li><strong>Service:</strong> Times of day are worked out in one shared place, with no change in behaviour.</li></ul> | [Full record](#v2-4-build-24) |
| v2.3 / build 23 | 2026-10-03 | <ul><li><strong>Agents:</strong> A task's area agent sends back its doubts about a change, Ava asks which task when unsure, and unrelated questions go to the Orchestrator alone.</li><li><strong>Goals:</strong> A time span set by their tasks, every task in the edit sheet, and pausing that pauses the tasks.</li><li><strong>Summary and Today:</strong> Week, month and all time broken down; a day strip that always shows the time left.</li></ul> | [Full record](#v2-3-build-23) |
| v2.2 / build 22 | 2026-10-03 | <ul><li><strong>Agents:</strong> Each area agent knows every task from all your records, one profile per task, and votes for up to three plans; the Orchestrator decides.</li><li><strong>Ava:</strong> A message when a task keeps slipping, a length looks off, the day won't fit, or energy is low on a full day, with a red dot on Ava's button until you open it.</li><li><strong>Summary:</strong> All time in Calendar, and what the area agents see in every report.</li></ul> | [Full record](#v2-2-build-22) |
| v2.1 / build 21 | 2026-10-02 | <ul><li><strong>Today:</strong> A day strip in the header: timed tasks, meals, now, what is next and the open time before 22:00.</li><li><strong>Agents:</strong> Orchestrator, area agents, Summary, each with its one job under its name; the closing Orchestrator step is gone.</li><li><strong>Ava:</strong> No repeated place, date or model line; wider, a 12 px gap and an adjustable height; the microphone in the send button, with words shown as you speak.</li></ul> | [Full record](#v2-1-build-21) |
| v2.0 / build 20 | 2026-10-02 | <ul><li><strong>Ava:</strong> The assistant is now Ava, a window floating over the page that never narrows it, opening beside an open sheet; it can be moved and folded down.</li><li><strong>Questions:</strong> No mode switch: Ava works out whether a message asks, changes or reports, suggests three questions for the place on show, and answers from the plans, findings, goals and last week.</li><li><strong>Title bar:</strong> A larger icon and wordmark.</li></ul> | [Full record](#v2-0-build-20) |
| v1.9 / build 19 | 2026-10-02 | <ul><li><strong>Plans:</strong> Propose again rebuilds today's plans that aren't set from your tasks as they are now, and today's plans from an earlier version are proposed again when DayWright starts; a set plan stays as set.</li><li><strong>At a glance:</strong> The box spans its plan's column again.</li></ul> | [Full record](#v1-9-build-19) |
| v1.8 / build 18 | 2026-10-02 | <ul><li><strong>Plans:</strong> A Plan types tab beside How the agents made these plans lists every kind of plan, what it does and when it is offered, and each plan's At a glance box is centred.</li></ul> | [Full record](#v1-8-build-18) |
| v1.7 / build 17 | 2026-10-02 | <ul><li><strong>Icon:</strong> A new icon: the day from 09:00 to 22:00 as a ring in the four area colours, with lunch and dinner left open, around a check.</li></ul> | [Full record](#v1-7-build-17) |
| v1.6 / build 16 | 2026-10-02 | <ul><li><strong>Plans:</strong> The local model reads the day and picks the two plans beside Balanced, with its reason in English and Chinese; DayWright's own ranking picks when the model is off, and a day gets three plans whenever three different ones can be made.</li><li><strong>Meals:</strong> Lunch 12:00–13:00 and dinner 18:00–19:00 are kept free, and no task can be fixed over them.</li><li><strong>Lengths:</strong> A length you give, in the form or through Talk, is at least 30 minutes.</li></ul> | [Full record](#v1-6-build-16) |
| v1.5 / build 15 | 2026-10-02 | <ul><li><strong>Lengths:</strong> A task's length is optional; its area agent estimates a blank one, and plans shorten only estimated lengths, never below 15 minutes.</li><li><strong>Plans:</strong> Balanced plus up to two of seven kinds that suit the day, each clearly different and saying why it was suggested and what sets it apart, between 09:00 and 22:00 with lunch and dinner kept free.</li><li><strong>Talk:</strong> Talk can give a task any length.</li><li><strong>Goal:</strong> The Records place is now called Goal, and the model status has no dot.</li></ul> | [Full record](#v1-5-build-15) |
| v1.4 / build 14 | 2026-10-02 | <ul><li><strong>Plans:</strong> The At a glance box is only as wide as its content, leaving no empty band on its right.</li></ul> | [Full record](#v1-4-build-14) |
| v1.3 / build 13 | 2026-10-02 | <ul><li><strong>Text:</strong> Paragraphs and list text that wrap are justified to both edges, with English hyphenated where it helps.</li><li><strong>Plans:</strong> At a glance shows each task on one line and its time or length change, such as 30 min → 45 min, on the next.</li></ul> | [Full record](#v1-3-build-13) |
| v1.2 / build 12 | 2026-10-02 | <ul><li><strong>Notices:</strong> A notice with a title, such as Read-only · past day, shows the title on its own line and the explanation under it.</li></ul> | [Full record](#v1-2-build-12) |
| v1.1 / build 11 | 2026-10-02 | <ul><li><strong>Plans:</strong> Proposed plans read "Proposed" instead of "Draft", and Starts with names a plan's first task.</li><li><strong>Quotes:</strong> Task names are quoted in every plan description, old ones included, and in the plan lists and the agents' findings.</li></ul> | [Full record](#v1-1-build-11) |
| v1.0 / build 10 | 2026-10-02 | <ul><li><strong>Numbering:</strong> DayWright now carries a version and build, starting at v1.0 build 10; the Mac app reports Version 1.0.0 (10).</li><li><strong>Contents:</strong> The first numbered build holds the six changes recorded below on 2026-10-02, from the four areas to one dropdown and one set of buttons.</li></ul> | [Full record](#v1-0-build-10) |
| Maintenance | 2026-10-02 | <ul><li><strong>Dropdowns:</strong> Every dropdown, from a task's or goal's status to start times, goals, and subjects, is now the same menu, with notes and a check on the choice.</li><li><strong>Buttons:</strong> Icon-only buttons share one style, and standalone text links became quiet buttons.</li></ul> | [Full record](#consistent-controls) |
| Maintenance | 2026-10-02 | <ul><li><strong>Fixed tasks:</strong> A start time taken by another timed task, for the task's length, is greyed out and names that task.</li><li><strong>Talk:</strong> "Move Review to 10:30" proposes moving the task there, or to the nearest free time.</li><li><strong>Plans:</strong> Each plan says in one line how it works and shows its first task, when the day ends, and the lengths it changed.</li><li><strong>Quotes:</strong> Task names in a plan's description are in quotation marks.</li></ul> | [Full record](#start-times-and-plan-glance) |
| Maintenance | 2026-10-02 | <ul><li><strong>Agents:</strong> Each area agent reviews its tasks for the day against the last 30 days and says what it found, task by task.</li><li><strong>Plans:</strong> A task often left partly done or skipped gets 15 minutes less, and a flexible task usually done at a steady time goes near that time.</li><li><strong>Lighter day:</strong> When the Life agent finds low energy, Gentle is listed first and says why.</li><li><strong>Earlier plans:</strong> Plans proposed by an earlier version get their agent list rebuilt by every current agent at start.</li><li><strong>Overlaps:</strong> When tasks with a start time overlap, proposing names them and their times.</li><li><strong>Shown:</strong> Plans and Today's Plan tab list each agent's findings in English or Chinese.</li></ul> | [Full record](#agent-findings) |

<details>
<summary>Full records for this table</summary>

<a id="v3-8-build-38"></a>

### v3.8 build 38: area screens as one page of cards, with visuals — 2026-10-05

- **Why:** each area split its day between an Overview tab and a Tasks tab, its cards were lists of
  text, and goals due for review or stalled sat in cards of their own.
- **One page:** an area has no tabs. Its purpose sits under its name, and its cards come two to a
  row, each row as tall as its tallest card, one to a row on a phone; a card alone on the last row
  keeps its half.
- **Every card:** a title with the days it covers ("Load · Mon 28 Sep – Sun 4 Oct"), a line saying
  what it counts, its numbers with labels, rows that open their item (a goal its Edit sheet, a
  task its details on its own day), and when it has nothing, what fills it with the button that
  does. In English and Chinese; the week runs Monday to Sunday, and done includes partly done.
- **In every area:** Today in the area, with the day strip showing the area's tasks alone, the
  day's tasks and their statuses, Add task from today on, and See all, which opens Tasks set to
  the area; and the area agent's notes for today, each with an icon for its kind (slipping, length
  off, due for review, stalled, a doubt about a time, a day that won't fit, low energy), or
  "Nothing to flag." On another day the notes say they are for today.
- **Learn:** Subjects, each Learning goal with its time done against planned this week, a practice
  row (● practised, ○ planned but not done, · nothing planned), when you last practised and its next
  session or a button to add one, then the time on Learning tasks without a goal. Practice this
  week, a bar per day with its time and the part done darker.
- **Life:** Habits, each repeat with its rule and start ("Daily since 25 Sep"), a week grid of done,
  partly done, missed, still to come and days its rule skips, and its count and streak; a repeat
  stopped this week stays, marked "Stopped Thu", until the week ends. Today's shape, the whole
  day's strip with meals, booked time and open time, Life's appointments and the meals, and the
  free windows between 09:00 and 22:00. Energy, seven days of readings with a dashed line at 2.
- **Work:** Load, a bar per day of Work planned this week, the part done darker, with the week's
  totals. Meetings, Work tasks with a start time over seven days from the day on show, by day.
  Carried over, each with its day and Not reported, Partly done or Moved to a day; Ask Ava to move
  types "Move “Email Anna” from Fri 2 Oct to today" into Ava's box without sending it, and Ava
  looks for the task on the day the request names, whatever day is on show.
- **Project:** Projects, each with On track, Stalled N days, Paused or No steps yet, a step bar with
  a segment per task, "Steps done: 2 of 4", and its last and next step; a partly done step now
  counts as done. Next steps over the next seven days and Recently done over the last seven, each
  with its project.
- **Estimates and plans:** every estimated length is at least 30 minutes, the form's too, and the
  local model's refinement as well. A task added in the form joins its day's proposed plans when
  none is set, as one Ava adds does.
- **Suggested areas:** keywords for each purpose decide when one matches; the local model is asked
  only when none does, and now works from examples ("Kitchen renovation": Project, "Call the
  plumber": Life, "Read chapter 4": Learning).
- **Release:** the Mac app reports Version 3.8.0 (38), and the service 3.8.0.
- **Evidence:** the service tests (451) and the interface helper tests (159) pass, and the
  interface build succeeds; each figure, visual and rule has its own test, written to fail first.
  In WebKit, on a throwaway database, each area was checked wide and at phone width in English
  and wide in Chinese: no tabs, one task list, rows matched, nothing scrolling sideways, an empty account's
  cards each offering their action, Ask Ava to move typing its request without sending it, See
  all opening Tasks set to the area, and a goal's row opening its Edit sheet. DayWright has no
  dark theme, so with the Mac in dark mode the pages stay light.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-05 as
  `a2c6a66`, `418caae`, and `b76a300`, with this record in the commit after them, on the branch
  `worktree-daywright-tasks-areas`.

[Back to change history](#change-history)

<a id="v3-7-build-37"></a>

### v3.7 build 37: Ava adds tasks and starts goals — 2026-10-04

- **Why:** new tasks and goals came only from the forms, so asking Ava for one got no further than
  advice.
- **Adding a task:** "Add Read chapter 4 tomorrow at 9 for 45 min to my Spanish goal" / "添加
  读第4章 明天上午9点 45分钟" proposes the task. Ava reads its title, quoted or what's left of the
  message, and its day: one you name, else the day on show when that's later than today, else
  today. A past day is refused and nothing is saved. A start, a length and a daily or weekly repeat
  are taken when you give them; an hour alone before 7, as "at 3", is in the afternoon. Without a
  start the task is flexible, and without a length its area agent estimates one, never under 30
  minutes.
- **Goal or area:** a goal you name, by its title or part of it, gives the task its area. A paused
  or completed goal is explained ("“Spanish” is paused, so no task can join it; resume it in Goals,
  or add the task without a goal."), and so is a name that fits none or several. Without a goal,
  the area you name is taken, else the Orchestrator suggests one by purpose, as the task form does.
- **Starting a goal:** "Start a goal: Kitchen renovation" / "新建目标：厨房装修" proposes the goal
  with its suggested area; "…and add pick tiles on Saturday" adds its first tasks to the same card,
  and they're created with it. A goal title you already have is refused.
- **The card:** titled "Add a task tomorrow" or "Start the goal “Kitchen renovation”", one line
  per task ("“Read chapter 4” · tomorrow · 09:00 · 45 min · repeats daily"), "Joins your goal …
  and takes its area." for a goal's task, and "Checked as the task form checks it: no overlap with
  timed tasks or meals." Without a goal it shows the area control with the suggestion named
  ("Orchestrator suggests Life from the task's purpose. Change it if it's wrong."), and the area you
  pick is the one saved. In English and Chinese.
- **Checks:** each task passes the task form's checks before the card shows, so an overlap or a
  meal is answered in words with no card, and again on Confirm. Nothing is created before Confirm.
  Then the tasks' area agents are told, an estimated length is refined by the local model when it
  can be, and a day of theirs with plans proposed and none set has them made again.
- **Thinking dots:** the three dots beside "Consulting the relevant agents locally" sit centred on
  the line instead of at its top, and still rise in turn.
- **Release:** the Mac app reports Version 3.7.0 (37), and the service 3.7.0.
- **Evidence:** the service tests (426) and the interface helper tests (139) pass, and the
  interface build succeeds; each of Ava's new rules has its own test, written to fail first. In
  WebKit, on throwaway databases in English and Chinese, a goal with a first task, a goal's task
  with a time, length and repeat, and a task whose suggested area was changed on its card were each
  created only on Confirm, as shown; the dots sat on the line's centre.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-05 as
  `a2c6a66`, `418caae`, and `b76a300`, with this record in the commit after them, on the branch
  `worktree-daywright-tasks-areas`.

[Back to change history](#change-history)

<a id="v3-6-build-36"></a>

### v3.6 build 36: a stopped repeat removes its days still to do, and event Details cleared — 2026-10-04

- **Why:** a repeat stopped or switched from a past day relabelled its later days, so a stopped
  repeat still left its days on the calendar to do; and an event's category, which v3.5 drops, was
  also written into its task's Detail.
- **Stopping a repeat:** "Stop repeating Stretch" about a past day deletes today's own day if it
  wasn't reported and today's set plan didn't schedule it, and every later day still to do; a
  reported or scheduled day today stays, and the stop starts tomorrow. Each day goes as a delete
  would: it leaves proposed plans, and its area agent and Summary are told.
- **Switching a repeat:** to weekly, the days still to do that aren't on the past task's weekday are
  deleted the same way, the rest repeat weekly, and the next day is prepared on that weekday; to
  daily, every day stays and repeats daily. A reported day is never touched.
- **The card:** a stop or switch that removes days names them, as "Its days still to do are
  removed: today, tomorrow." / "以下尚未完成的那几天将被删除：今天、明天。", and Ava's
  explanation does too.
- **Event Details:** when Learning's and Life's records fold into tasks and goals, an event task's
  Detail that is exactly its category ("sport") is cleared; any other text stays.
- **Carried over:** Work's overview lists the Work tasks of the 7 days before that are still to do
  or partly done, and those a set plan moved on; a skipped one is left out.
- **Tidying:** three interface texts no screen used are gone, and the goal card's design note reads
  "3 of 5 linked tasks done", as the card does.
- **Release:** the Mac app reports Version 3.6.0 (36), and the service 3.6.0.
- **Evidence:** the service tests (414) and the interface helper tests (137) pass, and the
  interface build succeeds; each rule has its own test, written to fail first. On a throwaway
  database made as v3.4 left one, the move cleared an event's Detail that was only its category and
  kept one with other words.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-04 as
  `e711f48`, `e2803c7`, and `8b686dc`, with this record in the commit after them, on the branch
  `worktree-daywright-tasks-areas`.

[Back to change history](#change-history)

<a id="v3-5-build-35"></a>

### v3.5 build 35: areas by purpose, overviews from tasks, and energy in one tap — 2026-10-04

- **Why:** Learning and Life kept records of their own beside the tasks they described, so the
  same work was reported twice, and nothing said which area a task belonged in.
- **Areas by purpose:** a task's area goes by its purpose, the first that fits: Work when someone
  else expects it, Project for a step toward something you're building that has an end, Learn when
  the point is getting better at something, Life for everything else. The task form lists each
  meaning, in English and Chinese. A new task added without an area or goal of its own, as from
  Today, gets the Orchestrator's suggestion once it has a title: from the local model while it
  runs, from keywords for each purpose otherwise. It is chosen for you and named on a pencilled
  line until you choose an area yourself; a task added from an area takes that area, and a goal's
  task the goal's.
- **The one-time move:** the first time this version opens a database, each active habit becomes a
  flexible Life task on that day that repeats as the habit did, a weekly one on that day's weekday,
  with the Life agent's estimated length, and each learning subject becomes a Learning goal, active
  while the subject was and completed once done or archived. A habit already on that day as a Life
  task, or a subject already a Learning goal, of the same name isn't made twice. Life events were
  already fixed tasks and stay so; their category goes, and their Detail keeps what it said. Habit
  logs, study sessions, inactive habits, every check-in (sleep, mood and energy), and subjects'
  difficulty and estimated minutes are dropped with their six tables, as are saved Summary
  reports, made again on request, and the plan checkpoints that copied them. One transaction does
  it all, so a failure leaves the database as it was; there is no backup, as chosen.
- **Area screens:** every area has Overview and Tasks; the Check-in, Habits, Events, Sessions and
  Subjects tabs are gone, with their forms and their service routes. Learn shows each open goal's
  time this week, the time without a goal and when you last practised. Life shows its repeats as
  habits, with how many were done this week and a streak of days, or weeks for a weekly one, done
  in a row, where today's copy still to do doesn't break it; and the day's appointments (fixed Life
  tasks outside a repeat), lunch and dinner, free time left and energy. Work shows the week's load
  by day, the day's meetings (fixed Work tasks) and what carried over from the 7 days before: tasks
  moved on from a set plan, and tasks still not done. Project shows each open project's progress,
  last step done and next step, or Add the next step, which opens the task form for that goal.
- **Due for review and stalled:** an active Learning goal with nothing done or partly done for 3
  days is due for review, and an active Project goal stalls, counting from its last such day or
  from when it was made. Each shows on its area's Overview, pencilled under its agent, and the
  Learning or Project agent tells you through Ava once a day per goal; a paused or completed goal
  never does.
- **Energy on Today:** "How's your energy?", 1 to 5 under Today's header, one reading a day that
  can change only that day. At 2 or below the Life agent asks for a lighter day as the check-in
  did: Lighter day comes first in plans proposed then, the row says so, and on a full day Ava says
  you reported low energy.
- **Agents and Summary:** the Learning and Life agents read their area's tasks, goals, repeats and
  energy. Learning's finding names when you last practised and its goals due for review; Life's
  the energy reported in the last 30 days and how its repeats went. Summary's reports count repeats
  done of scheduled and the latest energy in place of the habit, session and note lines, and
  Life's advice draws on that energy.
- **Goals:** two goal cards to a row, of one height; one under 640 px.
- **Not in this release:** Ava can't add a task yet, so the area suggestion is the task form's.
- **Release:** the Mac app reports Version 3.5.0 (35), and the service 3.5.0.
- **Evidence:** the service tests (411) and the interface helper tests (137) pass, and the interface
  build succeeds; each rule has its own test, written to fail first. On a throwaway database made
  as v3.4 left one, the move ran when the service opened it, and Today's energy row, the area
  suggestion, Goals at 1600 and 375 px wide, each area's Overview and Ava's two new messages showed
  as described, with no errors.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-04 as
  `e711f48`, `e2803c7`, and `8b686dc`, with this record in the commit after them, on the branch
  `worktree-daywright-tasks-areas`.

[Back to change history](#change-history)

<a id="v3-4-build-34"></a>

### v3.4 build 34: past tasks keep their place, linked repeats, and cleaner proposed plans — 2026-10-04

- **Why:** Ava's changes are aimed at today and later days. A past day should be corrected, never
  rearranged; a repeat should hold together however its days are called; and a proposed plan
  should never keep a task that is gone.
- **Past tasks:** about a past day, Ava corrects what a task is (its title, detail, goal, area or
  status), removes it, or moves it to today or a later day. On its past day a task keeps its start,
  length and timing, and nothing moves onto a past day: such a request gets "a task keeps its
  place … Nothing was changed.", and a mixed one, such as "Review took 45 minutes and was partly
  done", proposes the status and says "Left out: its length, as a past task keeps its place." The
  service refuses the same changes, whatever proposes them.
- **Moving a task forward:** on its new day the task is planned again, and a start, length or
  timing can be given there, with the overlap and meal checks; a day that already has its repeat's
  own day refuses it. The past day's set plan keeps its entry, marked "Moved to {day}" /
  "已移到{day}", left out of that day's reports, area profiles, Calendar counts and time by area,
  and the task counts on its new day. Both days' reports are made again and their area agents
  told; a new day today with plans proposed and none set has them proposed again with the task.
- **Linked repeats:** a new repeating task starts a repeat whose days carry one link; repeats
  recorded before are linked by their name and area the first time this version opens the
  database. The next day is copied from the repeat's latest day by its link: daily, weekly on that
  day's weekday, or not at all once a day says it doesn't repeat; v3.2's weekday rule and v3.3's
  paused-goal rule still hold. Summary counts a repeat's done days by link, under its latest name,
  so renaming a day doesn't split the habit.
- **Repeats from a past day:** "Make Read repeat daily" starts a new repeat from the past task, on
  today while there's still time (a start not yet passed, or a flexible task today's plan can still
  place), else tomorrow, and a weekly one on the next day of the past task's weekday; the card says
  "Repeats daily from {day}; earlier days stay as they were.", and the past task and the days
  between stay as they were. "Stop repeating Stretch" or "Repeat Stretch weekly" changes today's
  own day, unless it was reported or today's set plan scheduled it, when the change starts
  tomorrow; the days prepared after it follow.
- **A repeating task's past day:** changing its title, detail, goal or area makes Ava ask whether
  the change is for that day alone or for the repeat from today on too ("just that day" or "and the
  repeat"; 只改那天 or 连同以后). The card says how many days change, and no other past day does.
  Removing or moving its day changes that day alone.
- **Proposed plans after a deletion:** a task deleted, or moved away, from today or a later day
  leaves that day's proposed plans at once: each one's description and what sets it apart are
  rewritten from the tasks it has left, so nothing in it names the task, its time by area follows,
  and the other tasks keep their times. A past day's plans stay as they were.
- **Meals:** a confirmed meal change reaches every one of today's proposed plans, beside a set plan
  too; plans are proposed for today alone, so a change from a later day on reaches none yet.
- **Time by area:** a past plan's time by area, in Plans and in its day's totals, leaves out entries
  marked Removed or Moved to, which stay listed.
- **Card titles:** today and tomorrow drop "on" ("Move dinner today", "Move 1 task tomorrow"), and
  any other day keeps it before a short date ("Move dinner on Fri 9 Oct"); Chinese reads
  "调整今天的晚餐时间" and "调整10月9日周五的晚餐时间".
- **Release:** the Mac app reports Version 3.4.0 (34), and the service 3.4.0.
- **Evidence:** the service tests (379) and the interface helper tests (130) pass, and the interface
  build succeeds; each rule has its own test, written to fail first, and the earlier tests that
  changed a past task's length or start were rewritten to the new rules.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-04 as
  `e711f48`, `e2803c7`, and `8b686dc`, with this record in the commit after them, on the branch
  `worktree-daywright-tasks-areas`.

[Back to change history](#change-history)

<a id="v3-3-build-33"></a>

### v3.3 build 33: removed entries out of the counts, cleaner drafts, paused goals in Summary, and meal rules — 2026-10-04

- **Why:** a few rules left counts, plans or meal times showing something other than what had
  happened or what was asked for.
- **Removed entries out of the counts:** a past task its day's set plan scheduled, once removed,
  keeps its entry in that plan, marked "Removed" / "已移除", in Calendar and in Plans, but the
  entry no longer counts: Calendar's day counts, the day's tallies, Summary's day, week, month and
  all-time reports, and the area agents' profiles all leave it out. This replaces v3.0's rule that
  the plan's counts stayed as they were.
- **Drafts:** a task deleted today, or on a later day, leaves the plans proposed for that day and
  not yet set, so setting one can no longer schedule a task that is gone. A past day's proposed
  plans keep their own copy, as before.
- **Paused goals in Summary:** a task whose goal is paused, while it is still to do, isn't counted
  as scheduled; one reported before the pause still counts. A paused goal's repeating task gets no
  "Keep its next recurring block" advice.
- **Meals from a day on:** "Lunch 12:30–13:30 from Friday on", "starting tomorrow" or "从周五起"
  moves the meal for good from that day, where it used to be read as Friday alone. A change from a
  day on replaces the meal's one-day times from that day, and the card names them, such as "It
  replaces the one-day lunch time on Friday 9 October (13:00–14:00)."; a one-day time set later
  still wins on its day.
- **Meals end by midnight:** "Dinner 23:00–24:00" reads 23:00–24:00 on the card as in Ava's answer,
  where the card used to show 00:00. "Dinner 23:30–00:30" is now taken as a meal request and
  answered "Dinner 23:30–00:30 would run past midnight; a meal ends by 24:00. Nothing was
  changed.", with no card, before any question about the day.
- **Paused tasks in the way:** a fixed task whose goal is paused now stands in the way of a meal
  move as any other does, so it can't end up inside the meal once its goal resumes.
- **Release:** the Mac app reports Version 3.3.0 (33), and the service 3.3.0.
- **Evidence:** the service tests (349) and the interface helper tests (124) pass, and the
  interface build succeeds; each rule has its own test, written to fail first, among them one
  showing Calendar's counts for a day drop a removed entry while it stays on show as Removed.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-04 as
  `e711f48`, `e2803c7`, and `8b686dc`, with this record in the commit after them, on the branch
  `worktree-daywright-tasks-areas`.

[Back to change history](#change-history)

<a id="v3-2-build-32"></a>

### v3.2 build 32: past-day meal moves, repeat dates, and goal card order — 2026-10-04

- **Why:** a closer look at the behaviour added from v2.6 to v3.1 found four places where DayWright
  did something other than what it describes.
- **Past-day meal moves:** asking Ava to move lunch or dinner on a past day now gets "Past days
  keep the lunch times they had. Nothing was changed." in every case. Before, a past day whose set
  plan had left that meal out, as a plan set after lunch does, made the request fail with no
  answer.
- **Weekly repeats:** a weekly task finished on two recorded days now has its next date prepared on
  the weekday it was last on, the next one after today; it used to land a week after the day the
  Summary report was made, whatever the task's weekday. A daily task's next date is still tomorrow.
- **Paused goals:** a repeating task whose goal is paused is on hold, so its next date is no longer
  prepared.
- **Goal cards:** a task with no start is listed after the timed ones of its day, for days ahead
  and past days alike; it used to come first among a day ahead's tasks.
- **Release:** the Mac app reports Version 3.2.0 (32), and the service 3.2.0.
- **Evidence:** the service tests (338) and the interface helper tests (122) pass, and the
  interface build succeeds; each fix has its own test, written to fail first. In WebKit, on a
  throwaway database, a goal card listed "Early", "Late" and "No start" for one day, and Ava
  answered a lunch move on a past day whose plan kept dinner alone with that sentence and no card.
- **Status:** built in a separate worktree and committed on 2026-10-04 as `c5000bc`, `c1d4672`, and
  `664d89e`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

[Back to change history](#change-history)

<a id="v3-1-build-31"></a>

### v3.1 build 31: meal times through Ava, start over length on every schedule row, and goal cards of one height — 2026-10-04

- **Why:** lunch and dinner were fixed at 12:00 and 18:00 with no way to move them; schedule rows
  showed a task's time and length differently from place to place; and goal cards grew with their
  task lists, so their buttons never lined up.
- **Meal times through Ava:** "Lunch 12:30–13:30 from now on" or "Dinner 17:00–18:00 on Friday"
  proposes the change on a card, "Lunch: 12:00–13:00 → 12:30–13:30"; without "from now on" or a
  day, the Orchestrator asks which. A change from now on starts today, so earlier days keep their
  meals, and a past day can't be changed. The change is refused, with nothing saved, when the new
  time would take any of a timed task whose length you set, or the first 30 minutes of one whose
  length an agent estimated; the reply names the task. On Confirm, the agents look at the day
  again. A set plan the meal overlaps by 30 minutes or less is fitted in place, an estimate
  shortened or a flexible task moved, and the card lists each change, such as
  "“Read”: 11:45–12:45 → 11:30–12:30". With more, new plans are proposed and the set plan stays as
  it is until you pick one with Use Deep focus, or compare them in Plans. With no plan set,
  today's proposed plans are made again around the new time. Plans, the day strip, the task form's
  start times and the agents' checks all use the meal times of that day.
- **Start over length:** every schedule row, on Today, in Calendar's day panel and in Plans, shows
  its start time with its length directly below it, and so do the meal rows on Today and in
  Plans; a task with no start shows its length alone. A meal row reads just "Lunch" or "Dinner" / "午餐" or "晚餐".
- **Goal cards:** every card in Goals is the same height, with its buttons in line. A card lists up
  to three tasks, today's and later ones first, then the most recent past ones, and keeps room
  for three; with more, "Show all 7 tasks" / "查看全部 7 个任务" opens the goal's Edit sheet at
  its task list.
- **Release:** the Mac app reports Version 3.1.0 (31), and the service 3.1.0.
- **Evidence:** the service tests (335) and the interface helper tests (121) pass, and the
  interface build succeeds. In WebKit, on a throwaway database: Today, Calendar and Plans showed
  "11:45 / 1 h" and "15:00 / 30 min" in their time columns, with meals named "Lunch" and "Dinner";
  goal cards with 0, 2 and 7 tasks were all 439 px tall with their buttons at the same height, and
  "Show all 7 tasks" opened the Edit sheet at TASKS IN THIS GOAL · 7; "Lunch 12:30–13:30 from now
  on" moved "Read" from 11:45–12:45 to 11:30–12:30 on Confirm; "Dinner 17:00–18:00 today" put the
  set plan up for review, and Use Deep focus set a plan that keeps 17:00–18:00 free; and "Move
  lunch to 13:00" asked whether from now on or on one day.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-04 as
  `c5000bc`, `c1d4672`, and `664d89e`, with this record in the commit after them, on the branch
  `worktree-daywright-tasks-areas`.

[Back to change history](#change-history)

<a id="v3-0-build-30"></a>

### v3.0 build 30: removed entries in past plans, Ava's "that task", and refusals in both languages — 2026-10-03

- **Why:** a past plan that scheduled a task now removed should still show what it held, and say
  that the task is gone; "Remove that task" should mean the task just talked about; and a refused
  direct change to a past task should read in the interface's language.
- **Removed in past plans:** when a past task its day's set plan scheduled is removed, through Ava
  or from its goal's task list, that plan keeps the entry marked "Removed" / "已移除", in Calendar
  and in Plans. Nothing else in the plan changes: the entry keeps its time and reported status, and
  the plan's counts stay as they were. The removal reaches the task's area agent and Summary as
  any removal does. Removing a task today's set plan scheduled is still refused, with Report
  Skipped and Review a replacement offered.
- **Ava's "that task":** "Remove that task", "change it" or "删除那个任务", right after a message that
  named exactly one task, means that task, for a change or a removal. After a message that named
  several tasks, the Orchestrator asks which of them; after one that named none, it asks which
  task, as before.
- **Refusal in both languages:** the service's refusal of a direct change to a past task, or of a
  move onto a past day, reads "A past task changes only through Ava. Ask Ava to change it." or
  "过去的任务只能通过 Ava 更改。请告诉 Ava 要改什么。" wherever it shows: a notice or the task form.
- **Release:** the Mac app reports Version 3.0.0 (30), and the service 3.0.0.
- **Evidence:** the service tests (299) and the interface helper tests (109) pass, and the
  interface build succeeds. In WebKit, on a throwaway database: Ava's card for removing a past task
  its set plan scheduled said "The plan set for that day keeps its entry, as history."; Delete in
  the goal's sheet took two steps, with no refusal, and removed it; Calendar and Plans then showed
  its entry "Openings · Removed · Done"; and "How did Morning chess go?" then "Remove that task"
  proposed removing "Morning chess", which applied on Confirm.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-04 as
  `c5000bc`, `c1d4672`, and `664d89e`, with this record in the commit after them, on the branch
  `worktree-daywright-tasks-areas`.

[Back to change history](#change-history)

<a id="v2-9-build-29"></a>

### v2.9 build 29: changes reach their own agents, and past tasks only through Ava — 2026-10-03

- **Why:** every change to a task should reach the Orchestrator, which hands it to the right area
  agent and to Summary and has them look again; until now each change rebuilt every area's
  profiles, and the agents looked at today only when it was opened. A past task could still be
  edited by a request that bypassed Ava, and one its day's set plan scheduled couldn't be removed.
- **The right agents:** the Orchestrator hands each change to the area agent of the task's own
  area, both areas when a task moves between them, and every area a day holds when a plan is set,
  replaced, unset or proposed; only those agents' task profiles are rebuilt, and Summary remakes
  the reports of the days it touched. Pausing, resuming or completing a goal now reaches its area's
  agent as well as Summary; creating, renaming or removing one reaches Summary.
- **A second look at today:** after every saved change, the concerned area agents look at today
  again, with the Orchestrator's checks of the whole day, and Ava posts anything new, such as a
  task that now keeps slipping, without waiting for today to be opened. Each message is still
  posted once a day.
- **Past tasks only through Ava:** the service refuses any other edit of a past task, and a move
  of a task onto a past day: "A past task changes only through Ava; ask Ava to change it". The
  task form no longer offers a past date. A confirmed change from Ava and Delete in a goal's task
  list still work.
- **Removing a past task a plan scheduled:** through Ava or from its goal's task list, a past task
  its day's set plan scheduled is now removed like any other; the plan keeps its entry, as history
  of what was scheduled and reported, and Ava's card says so. Today's rule stays: a task today's
  set plan scheduled can't be removed, with Report Skipped and Review a replacement offered.
- **Release:** the Mac app reports Version 2.9.0 (29), and the service 2.9.0.
- **Evidence:** the service tests (297) and the interface helper tests (107) pass, and the
  interface build succeeds. The tests show a change reaching only its task's area profiles, the
  agents posting a slipping message as soon as a task changes, a goal's pause reaching its area's
  agent while a rename doesn't, direct edits of a past task and moves onto a past day refused, and
  a past task its set plan scheduled removed through Ava and from its goal with the plan's entry
  kept, while today's stays.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-04 as
  `c5000bc`, `c1d4672`, and `664d89e`, with this record in the commit after them, on the branch
  `worktree-daywright-tasks-areas`.

[Back to change history](#change-history)

<a id="v2-8-build-28"></a>

### v2.8 build 28: past tasks change only through Ava — 2026-10-03

- **Why:** since v2.5 a past task could be edited from its goal's sheet while Calendar showed its
  day as history. Now a past day is read-only on every screen, and a past task changes only through
  Ava, which shows the change before anything applies.
- **Calendar:** a past day's banner shows a lock and "Read-only · past day · You can view this day
  and its plan, not change them.", then the note when no plan was set, then, in small text, "To
  change or remove a task, ask Ava." Its rows still have no status buttons and open nothing.
- **Through Ava:** about a past day, name a task and say what to change in your own words: its
  title, detail, area, goal, day, start or length, or its status, reported late or put right
  ("Review took 45 minutes and was partly done", "Rename Review to “Read notes”", "Move Review to
  2 Oct"), or ask to remove it ("Remove Review"). The Orchestrator asks which task when several fit
  or none does. Ava proposes the change on a card titled "Change “Review” on {day}" with each field
  before and after, or "Remove 1 task on {day}", and nothing changes until you confirm. The checks
  a task's form has still apply: a start that overlaps another task is refused before anything is
  proposed, and a task moved after today goes back to planned. A task its day's set plan scheduled
  can't be removed, the same as removing today's task the set plan scheduled; Ava says so, and its
  status can still change. A past day's plans stay as they were: a removed task's entries in plans
  that were only proposed lose their link to it, and an edit keeps the plan's times while the
  plan's entry takes the new title, area and status.
- **Goals:** in a goal's Edit sheet a past task is history: a shaded row with a lock, its status as
  text, and Delete…, in two steps; one its day's set plan scheduled can't be deleted, which Delete
  says instead. Under the list: "To change a past task, ask Ava." Today's and later tasks keep
  Edit. A goal that can't be removed yet says how many tasks still link to it, one or several, and
  how to free them, and its button opens the goal's Edit sheet at its task list. On both refusal
  cards, OK has the same border as the button beside it.
- **Tasks:** the "Linked to {goal} · Show all tasks" filter is gone; the area switch stays. The
  note reads "A past task can be changed only through Ava", past days are headed "change through
  Ava", and an area showing a past day says the same.
- **Agents:** every change to a task reaches the agents it concerns: the form, the status control,
  each Ava proposal (move, length, shorten, plan, and now edit and remove), deleting from a goal's
  list, setting, replacing or unsetting a plan, proposing plans, accepting or dismissing a
  suggestion, a timed Life event, and the area agent's refined estimate. An edit confirmed through
  Ava reaches the area agents and Summary as one made on a form does; a task left on a past day
  raises no doubt, being a record put right. Creating, renaming, pausing, completing or removing a
  goal now makes Summary's saved reports for today and for its tasks' days again, as reports list
  the goals; before, those changes reached no agent.
- **Also:** the capabilities list no longer offers important-to-keep commitments, which went with
  Protected in v2.6.
- **Release:** the Mac app reports Version 2.8.0 (28), and the service 2.8.0.
- **Evidence:** the service tests (292) and the interface helper tests (107) pass, and the
  interface build succeeds. In WebKit, on a throwaway database: the past-day banner showed its lock
  and three lines and no status buttons; a goal's refusal named its 4 tasks, had two bordered
  buttons, and opened the goal's sheet with focus on its task list; the sheet's two past tasks had
  Delete… and its two later ones Edit, with the note under them; deleting the past task its set
  plan scheduled was refused, and deleting the other took two steps and kept focus in the list;
  Tasks had no goal filter and the new note; and through Ava, "Review took 45 minutes and was partly
  done" proposed "Length: 1 h → 45 min" and "Status: Planned → Partial", applied on Confirm, and
  "Remove Review" removed it on Confirm.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-04 as
  `c5000bc`, `c1d4672`, and `664d89e`, with this record in the commit after them, on the branch
  `worktree-daywright-tasks-areas`.

[Back to change history](#change-history)

<a id="v2-7-build-27"></a>

### v2.7 build 27: Ava closes with a click outside it — 2026-10-03

- **Why:** Ava's minus button folded it into a bar that still sat over the page, and closing Ava
  meant finding its close button or pressing Escape.
- **No folding:** the minus button and the folded bar are gone. Ava is either open or closed.
- **A click outside closes it:** a click anywhere outside Ava closes it, as Escape does, and Ava's
  own button in the top bar or bottom bar still opens and closes it. A click that starts inside
  Ava, such as selecting its words, keeps it open wherever the pointer ends up, and a button
  elsewhere that opens Ava for a question, such as Ask about this day, keeps it open with that
  question. A draft and an open proposal survive closing, as before.
- **Release:** the Mac app reports Version 2.7.0 (27), and the service 2.7.0.
- **Evidence:** the service tests (275) and the interface helper tests (97) pass, and the interface
  build succeeds. In WebKit, on a throwaway database, Ava had no minus button; a click on the page
  closed it; its own button opened and closed it; a click on its title and a selection dragged out
  of its conversation kept it open; and Ask about this day opened it, and kept it open when clicked
  again while Ava was showing. The rebuilt Mac app reports Version 2.7.0 (27) with the microphone
  entitlement, and its frozen service carries 2.7.0.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="v2-6-build-26"></a>

### v2.6 build 26: changes handed only where they matter, doubts on form edits, and no more Protected — 2026-10-03

- **Why:** every change to a task, however small, rebuilt every area agent's profiles and Summary's
  saved reports, and an edit made on a task's form never got the area agent's view that the same
  change made through Ava did. Protected overlapped with a length you set, which no plan shortens
  anyway, so it added a switch without adding a rule.
- **Only where it matters:** the Orchestrator looks at what an edit changed. A new title, area,
  day, start, length or status reaches the area agents and Summary; a new detail, repeat or goal
  reaches Summary alone, as its advice reads them; an edit that changes none of these reaches no
  one, and the day's saved report stays as it was. A task added, removed, reported or planned
  still reaches both.
- **Doubts on form edits:** when you move a task or change its length on its form, its area agent
  checks the change against the task's records, as it does for a request to Ava, and posts any
  doubt to Ava under its own name: a start at least two hours from when you usually do it, or a
  length you have mostly left partly done. The edit stays saved; the doubt is only advice.
- **Protected is gone:** the switch, its flag on tasks and in plans, and "Kept protected" leave.
  Plans no longer put such tasks first in their area, and Lighter day may trim any estimated
  length; a length you set is still never shortened. Summary's advice no longer treats a task as
  protected, and it prepares the next date of any repeating task you finished on two days, or
  asked twice to shorten, for your Accept. Tasks already marked keep working as ordinary tasks.
- **Release:** the Mac app reports Version 2.6.0 (26), and the service 2.6.0.
- **Evidence:** the service tests (275) and the interface helper tests (97) pass, and the interface
  build succeeds. New tests show that an edit that changes nothing keeps the day's saved report,
  that moving a task far from its usual time on its form posts its area agent's doubt, which agents
  an edit concerns, and that repeating tasks are prepared whether or not they were ever protected.
  The rebuilt Mac app reports Version 2.6.0 (26) with the microphone entitlement, and its frozen
  service carries 2.6.0.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="v2-5-build-25"></a>

### v2.5 build 25: tasks editable from their goal, changes every agent hears of, and a clearer day strip — 2026-10-03

- **Why:** the Edit goal sheet listed a goal's tasks without a way to edit them, and spent its
  space on a full-width area tag and long notes; the goal card's buttons didn't match. A change to
  a past task couldn't be made, and Summary's saved reports wouldn't have followed it. The day
  strip's past shading was too faint to see, the time now sat far from its mark, lengths read
  "11 h 40" without "min", and nothing said the hours it left out were for meals. Plans that still
  held a paused goal's tasks didn't say so, and Calendar showed those tasks as Planned. Calendar
  called a past day read-only and didn't say which plan it used. Ava didn't say which day it was
  answering about, showed nothing while it thought, and folded down to a bar as wide as itself.
- **Edit goal:** the area and the time it spans sit side by side in one panel, a span within one
  day names its day once, and the tasks follow in a bordered list with their total length. Every
  task has Edit, whatever its status and on whatever day, past ones included; it opens the task's
  form, and the goal's sheet comes back once the form is saved or cancelled, with anything typed
  in it kept. The form keeps the task's own goal while that goal is paused. Edit, Remove… and Add
  task on each goal card now share one bordered style.
- **Past tasks:** a task on a past day can now be edited from its goal; its status stays as
  reported, and past days stay read-only everywhere else. A task renamed on a day with a plan is
  renamed in that plan too, so Today's schedule and Summary show the new name; the plan keeps the
  times and lengths it set.
- **The Orchestrator hears of every change:** whenever a task or a plan changes, from a form,
  Ava, a report or setting a plan, the Orchestrator hands it on. The area agents' task profiles
  are rebuilt from every record, and Summary makes the saved reports for the day, week and month
  of each date the change touched again, with their advice, the next time you open them. A task
  moved to another day touches both days, and a report nothing touched stays as it was saved. An
  agent doesn't send a doubt about an edit made on a form; that stays with requests to Ava.
- **Day strip:** the time already gone is shaded clearly, the time now is printed under its
  mark, and a key under the hours splits the time left into meals, tasks and open time, with
  swatches like the strip's, adding up to the time left. Every length reads like "3 h 30 min".
- **Paused tasks in plans:** a plan that still holds a paused goal's tasks, because it was made
  before the pause, marks each one Paused and says so under Constraints, and a plan made after the
  pause says which tasks it left out and why. Today's Plan tab, the replacement review and
  Calendar's day panel do the same; Calendar used to show those tasks as Planned.
- **Calendar's past days:** the banner no longer calls a past day read-only. Titled "Past day", it
  says nothing changes there, that a task in a goal can still be edited from that goal in Goals,
  and, when no plan was set, that the day's tasks show as recorded. The day's card names the plan
  it used, as "Plan used · Lighter day · 10:21", over its counts, with Open full day and Ask about
  this day at its foot, in one style. The Area and Tasks screens word their past days the same way.
- **Ava:** its header names the day it answers about, "About today" or "About Fri 2 Oct", as
  "Ask about this day" in Calendar opens it, and keeps that chip while Ava is folded down, so
  reopening it shows which day the conversation carries on with; the box's placeholder names the
  day too. Each message keeps the day it was about, and the conversation is marked where it turned
  to another day. Three dots pulse while Ava thinks, and stay still when motion is reduced. Folded
  down, Ava is now a small bar at its corner instead of a full-width title bar.
- **Release:** the Mac app reports Version 2.5.0 (25), and the service 2.5.0.
- **Evidence:** the service tests (273) and the interface helper tests (97) pass, and the interface
  build succeeds. New tests show that a past task can be edited and its day's, week's and month's
  reports are made again with it, on a day with or without a set plan, that moving a task off a
  past day remakes that day's report, that a renamed task is renamed in its set plan and its
  report, how the time left splits, how a plan's
  paused tasks are named, and how lengths and spans read. In WebKit, on a throwaway database, the
  goal sheet edited a past, done task and came back with its new title; plans named paused tasks
  as held or left out; Calendar showed them Paused, named a past day's plan and put its buttons in
  the day's card; the strip showed the time now, the shading and its key; and Ava, opened from a
  past day, named that day, showed its dots while thinking, marked the turn to today, and folded
  to a 292 × 46 px bar. The rebuilt Mac app
  reports Version 2.5.0 (25) with the microphone entitlement, and its frozen service carries 2.5.0.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="v2-4-build-24"></a>

### v2.4 build 24: edits that keep a task's reported outcome — 2026-10-03

- **Why:** saving a task from its details sent back the status the form had when it opened, so an
  outcome reported in the meantime was overwritten, and an edit to a paused goal's task could be
  refused over a status nobody had changed.
- **Editing a task:** the task form has no status, and saving it no longer sends one. A saved edit
  keeps the outcome already reported for the task, whether done, partly done or skipped, and a
  paused goal's task can still be edited. Reporting it stays closed until the goal resumes.
- **Inside the service:** times of day are converted to and from minutes in one shared place, with
  no change in behaviour.
- **Release:** the Mac app reports Version 2.4.0 (24), and the service 2.4.0.
- **Evidence:** the service tests (267) and the interface helper tests (88) pass, and the interface
  build succeeds. New tests show that an edit sent without a status keeps "done", also on a paused
  goal's task, that the task form sends no status, and that a paused goal's plan entry can't be
  reported. The rebuilt Mac app reports Version 2.4.0 (24) with the microphone entitlement, and its
  frozen service carries 2.4.0.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="v2-3-build-23"></a>

### v2.3 build 23: agents that answer back, goals that keep time, and a strip that always shows — 2026-10-03

- **Why:** A change asked through Ava went ahead even when the task's own records said otherwise,
  an unclear request fell back to proposing another plan, and every question went to every agent.
  Goals had no time span, a paused goal's tasks still went into plans, Summary's week, month and
  all time couldn't be broken down, Ava showed Markdown marks as typed, and Today hid its timeline
  until a task was recorded.
- **Doubts and questions:** when you ask Ava to move a task or change its length, the Orchestrator
  hands the change to that task's area agent. When its records disagree, it says so under its own
  name in Ava's conversation: a move at least two hours from when you usually do the task, or a
  length at which the task was mostly left partly done. The change stays ready to confirm, because
  a doubt is only advice. A change naming no task Ava can find, or one that fits several, gets a
  question asking which task, instead of a proposal to switch plans.
- **The right agents:** a request reaches the area agent of each task it names, as well as the
  areas its words name. A question about the day, its plans or your records, in English or
  Chinese, goes to every area agent; one about nothing in your day is answered by the Orchestrator
  alone. A change no longer always asks Learning and Life.
- **Ava's text:** bold, italics and headings the local model writes show as such instead of as
  asterisks and hashes.
- **Goals:** each goal shows the time it spans, from when you made it to that plus the length of
  every task in it, given or estimated by the task's area agent as it is saved; adding a task
  extends it, from Goals or from Today, and nobody sets it by hand. Editing a goal lists every task
  in it with its day and status. Pausing a goal pauses its tasks: plans skip them, they can't be
  reported until the goal resumes, and Today, its day strip, the task's details and its area show
  them in a paused colour with a pause sign and a label. A task is never paused on its own.
- **Summary:** in Calendar, Week lists its days, Month its weeks and All time its months, newest
  first, each with what was done by area and its own advice, made fresh when you open it. "Read the
  report" and the other expanders end with a chevron that turns when open.
- **Today:** the day strip always shows, even before anything is recorded, when it says "No tasks
  yet". The time already gone is shaded, the now mark stays at the strip's ends before 09:00 and
  after 22:00, and the caption says the time now, how much of the day is left before 22:00, and
  how much of that is open.
- **Release:** the Mac app reports Version 2.3.0 (23), and the service 2.3.0.
- **Evidence:** the service tests (264) and the interface helper tests (87) pass, and the interface
  build succeeds; the helper tests cover the Markdown marks in Ava's replies. On a throwaway
  database, Ava asked which task for a move naming none, gave the Project agent's length doubt, and
  kept the user's message above its reply; a paused goal's tasks showed in the paused colour on
  Today and on the strip, with their time left
  open; a goal showed its span and the edit sheet its tasks; Week and All time listed their days and
  months; and an empty day showed the strip with the time left. The rebuilt Mac app reports Version
  2.3.0 (23) with the microphone entitlement, and its frozen service carries 2.3.0.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="v2-2-build-22"></a>

### v2.2 build 22: agents that know every record, vote on plans, and speak up — 2026-10-03

- **Why:** The area agents looked back only 30 days, the Orchestrator chose plans without asking
  them, nothing told you when a task kept slipping or the day couldn't fit, and Summary covered a
  month at most.
- **All your records:** each area agent now knows every task from all your records. They are
  summed up in one profile per task, in the same local SQLite database: how often it was done,
  partly done or skipped, its latest reports and whether it is lately slipping or improving, its
  usual length and start time, how often a plan or you changed its length, and how often you asked
  to shorten it. The profiles are rebuilt when DayWright starts and after every change to a task, a
  report, a plan or a message to Ava, so the database keeps one row per task rather than a second
  history. An agent reads only its own area's profiles. A new task's estimated length draws on every
  length you ever gave it. Summary's advice to the plans still draws on the 30 days before the day,
  so it stays current, and a Life check-in older than that no longer advises a lighter day.
- **Votes:** before plans are proposed, each area agent votes for up to three plans that suit its
  own tasks: Deep focus for tasks to keep together, Your usual rhythm for tasks with a usual time,
  Easiest first or Lighter day for a task that is slipping, Quick wins first for short tasks,
  Breathing room or Lighter day for Life, and Finish early around Work's fixed meetings. The
  Orchestrator has the local model choose the two plans beside Balanced with every agent's votes
  in front of it; without the model the votes decide, and a plan chosen that way names the agents
  that voted for it. Plans lists each area agent's votes under its findings.
- **A different plan:** asked for another plan, Ava offers the one the area agents vote for among
  the day's other plans, and an area your message names counts double; asking for a lighter day
  still offers Lighter day.
- **Ava's messages:** each time today is opened, the Orchestrator asks the area agents what needs
  your attention. Each of these becomes one message from Ava, once a day, naming the agent that
  found it: a task that keeps slipping; a task mostly left partly done, or whose length you keep
  changing; tasks without a time that won't fit what is left of the day before 22:00, when no plan
  is set; and low energy in today's check-in on a day whose tasks without a time fill at least 70%
  of the free time, unless Lighter day is already set. A red dot on Ava's button, in the title bar
  and in a phone's bottom bar, marks a new message until Ava is open and unfolded, and is read
  aloud as "New message". Opening today never waits on these messages.
- **Summary:** Calendar's Summary agent tab adds All time to Day, Week and Month, covering every
  record so far; it is made fresh each time and is never saved or used as advice. Every report now
  lists what the area agents see among its tasks: the ones that keep slipping, whose length looks
  off, and that are going well. Each agent's one line says it now votes and reports issues.
- **Release:** the Mac app reports Version 2.2.0 (22), and the service 2.2.0.
- **Evidence:** the service tests (232) and the interface helper tests (76) pass, and the interface
  build succeeds. On a throwaway database with a slipping task, a task mostly left partly done and
  a low-energy full day, Ava posted the three messages once, the red dot showed in the title bar
  and on a phone's bottom bar and cleared when Ava opened, Plans listed each area agent's votes,
  and Calendar's All time showed what the area agents see, in English and Chinese. The rebuilt Mac
  app reports Version 2.2.0 (22) with the microphone entitlement, and its frozen service carries
  2.2.0.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="v2-1-build-21"></a>

### v2.1 build 21: one job per agent, a day strip, and Ava by voice — 2026-10-02

- **Why:** Today's header left a wide empty gap; the Orchestrator's closing step and the Summary
  agent both claimed to combine the agents' work; and Ava's window repeated what the page already
  shows, could not change height, and could not use the microphone in the Mac app.
- **Day strip:** Today's header shows the day from 09:00 to 22:00 between the date and the
  buttons: timed tasks in their area colours, lunch and dinner kept free, a mark for now, what is
  next, and how much time is still open before 22:00. Beside a sheet or on a phone it takes its
  own row.
- **One job per agent:** a route now reads Orchestrator, the four area agents, Summary. The
  Orchestrator runs once and says whom it asked and what came of it, such as the plans it chose;
  the closing "Orchestrator · finish" step is gone. Summary sums up what the area agents found and,
  for plans, the days before. In Ava's replies the area agents now review their tasks against the
  last 30 days, as they do for plans, instead of giving stock advice. Under each agent's name, one
  line says its job, in Plans and in a reply's agents. When DayWright starts, a plan route saved
  before is rebuilt by the current agents; the plans stay as they were.
- **Ava's panel:** the context chip with the place and date, and the model line under the box,
  are gone, since the page and the top bar already show them; replies show Ava's avatar without
  repeating its name. The window is a little wider, so the three suggested questions sit on one
  row, and sits 12 px from the window's edges instead of 24. Drag its top edge, or use the arrow
  keys on it, to change its height; DayWright remembers it, and a double-click restores it.
- **Voice:** the Hold to talk button is gone. Press the microphone beside an empty box and speak:
  the words appear in the box as you say them, transcribed on this Mac every 1.5 seconds; press
  stop to finish, then read them over and send. The Mac app now carries the microphone
  entitlement, so macOS asks once instead of refusing.
- **Release:** the Mac app reports Version 2.1.0 (21), and the service 2.1.0.
- **Evidence:** the service tests, the interface helper tests and the interface build pass. On a
  throwaway demo database, the strip filled the header at every width checked, Plans showed the
  new route with a role under each agent, and Ava's questions fit one row in every place in both
  languages; with a simulated microphone and transcriber, words appeared in the box while speaking
  and the full sentence after stop.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="v2-0-build-20"></a>

### v2.0 build 20: Ava, a floating assistant — 2026-10-02

- **Why:** the assistant, called Talk, docked beside the page and narrowed it, most of all with the
  New task sheet open too; it needed its mode chosen before each message; and it answered from
  little more than the day's tasks.
- **Name:** the assistant is now Ava (艾娃 in Chinese), on the ⌘K button, the phone's bottom bar,
  its window and its replies.
- **Floating window:** on desktop Ava is a 420 × 600 window floating over the page, which never
  narrows it. It opens in the bottom-right corner, or just left of an open sheet. Drag its title
  bar to move it, and DayWright remembers where; double-click the title bar to put it back. The
  minus button folds it down to its title bar. A phone keeps the sheet.
- **No modes:** the Ask, Adjust and Report switch is gone. Ava works out from the words whether a
  message asks, changes or reports, and labels its reply Question, Change or Report: "Can you move
  Review to 3pm?" is a change, "Show me what I did yesterday" a question, and "I spent 30 minutes on
  Review" a report. Proposed changes still wait for Confirm.
- **Suggested questions:** with the box empty, Ava offers three questions for the place on show,
  such as "What should I do next?" on Today, "How do these plans differ?" on Plans, and "Which
  goal needs attention?" on Goal. Asking for a different plan opens Ava with "Replace this day's
  plan with a better one" ready to send, which proposes one.
- **Smarter answers:** Ava now reads the day's frame and meal hours, the set and proposed plans
  with why each was suggested, the area agents' findings, goals with how many of their tasks are
  done, and the last 7 days by area (up to today for a day still ahead), and is asked to name the
  tasks, times and plans its answer rests on. A long day is shortened to fit the model. A reply can
  run a little longer.
- **Title bar:** the app icon and the DayWright wordmark are larger: 34 px and 22 px, and 30 px
  and 19 px on a phone.
- **Release:** the Mac app reports Version 2.0.0 (20), and the service 2.0.0.
- **Evidence:** the service tests, the interface helper tests and the interface build pass. On a
  throwaway demo database, the page kept its width with the New task sheet and Ava open together,
  Ava sat beside the sheet, moved, folded and put itself back, offered its questions, and the local
  model answered "What should I do next?" naming two tasks and their goals; Ava was also checked in
  Chinese and at phone width.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="v1-9-build-19"></a>

### v1.9 build 19: Propose again, and no stale plans — 2026-10-02

- **Why:** plans proposed before a length was set, or by an earlier version, kept trimming or
  stretching lengths the user had set, and nothing could propose them again.
- **Propose again:** today's Plans page has a Propose again button. It proposes the plans you
  haven't set again, from your tasks as they are now, with the local model choosing; a plan you set
  stays exactly as set, and the new plans take the other places. The plan route says so.
- **Earlier plans:** when DayWright starts, today's plans proposed by an earlier version, before
  plans kept their sentences, are proposed again the same way by DayWright's own ranking, without
  waiting for the model. Past days stay as they were.
- **Proposing:** both propose buttons read "Proposing…" and wait while the local model chooses,
  which can take up to about 40 seconds.
- **At a glance:** the box spans its plan's column again.
- **Release:** the Mac app reports Version 1.9.0 (19), and the service 1.9.0.
- **Evidence:** the service tests, the interface helper tests and the interface build pass. On a
  throwaway demo database, each plan's box spanned its column and Plans offered Propose again.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="v1-8-build-18"></a>

### v1.8 build 18: plan types explained, and a centred At a glance box — 2026-10-02

- **Why:** each plan's At a glance box sat against the left of its column, and nowhere listed the
  kinds of plan DayWright can propose.
- **At a glance:** the box stays only as wide as its content and is now centred in its column.
- **Plan types:** under the plans, "How the agents made these plans" gains a second tab, Plan types.
  It lists every kind of plan, Balanced first, each with its one-line description and when it is
  offered, under a line saying Balanced is always offered and the local model picks two others for
  the day.
- **Release:** the Mac app reports Version 1.8.0 (18), and the service 1.8.0.
- **Evidence:** the interface helper tests and the interface build pass. On a throwaway demo
  database, each plan's box measured the same space on both sides, and the Plan types tab listed
  all eight kinds in English and Chinese.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="v1-7-build-17"></a>

### v1.7 build 17: the day-ring icon — 2026-10-02

- **Why:** the icon still showed the earlier planner, its tabs in colours DayWright no longer uses.
- **Icon:** the day from 09:00 to 22:00 as a ring in the four area colours, in priority order,
  work, project, life, then learning, with lunch and dinner left open, around the set plan's check,
  on DayWright's indigo. It was chosen from four drafts drawn in the app's own colours.
- **Where it is used:** `Resources/DayWrightIcon.png` is the 1024-pixel master in the macOS rounded
  square. The favicon and title-bar icon `public/icon.png`, the five app icons in
  `src-tauri/icons/`, and the project folder's Finder icon are made from it.
- **Release:** the Mac app reports Version 1.7.0 (17), and the service 1.7.0.
- **Evidence:** the rebuilt app's `icon.icns` matches the regenerated one and its signature
  verifies; drawn as Finder draws them, the app and the project folder show the ring in the macOS
  rounded square with no frame, and the opened app shows it in its title bar.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="v1-6-build-16"></a>

### v1.6 build 16: the local model chooses the plans; lunch and dinner at set hours — 2026-10-02

- **Why:** plans should be chosen from the day itself by the local AI, three every time, around
  fixed mealtimes, and a length you give should be at least 30 minutes however you give it.
- **Plans:** Balanced is always first. The planner builds every other kind of plan the day allows,
  then the Orchestrator has the local model read the day, from the tasks, their details and
  lengths, fixed times and free time to the agents' findings, energy, Summary advice and the plans
  you set most often, and pick the two that suit it best. Each comes with the model's reason, in
  English and Chinese, shown after the agent icon as the Orchestrator's. When the model is off or
  answers unusably, DayWright's own ranking picks, and the plan route says which happened.
- **Three plans:** a day gets three plans whenever three different ones can be made, clearly
  different ones first. Lighter day and Breathing room leave their gap after fixed tasks too, and
  Lighter day starts later still, an hour at a time, when 10:00 would repeat another plan. A day
  with nothing to place keeps Balanced alone.
- **Meals:** lunch is 12:00–13:00 and dinner 18:00–19:00. The task form greys out start times that
  would run into them ("Kept for lunch"), the service refuses them, and Talk moves a task to the
  next free time after them. A meal a Life event already takes is left out of that day's plans.
- **Lengths:** a length you give, in the form or through Talk, is at least 30 minutes; asking Talk
  for less proposes 30. A task that already has a shorter length can still be reported; editing it
  in the form asks for 30 or more. An area agent's estimate, and plans' trims of it, keep their
  15-minute floor.
- **Release:** the Mac app reports Version 1.6.0 (16), and the service 1.6.0.
- **Evidence:** the service tests, the interface helper tests and the interface build pass. Plans,
  the task form and Today were checked on a throwaway demo database in English and Chinese.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="v1-5-build-15"></a>

### v1.5 build 15: optional lengths and a pool of clearly different plans — 2026-10-02

- **Why:** with every task at least 30 minutes long, Balanced, Focused, and Gentle differed by little
  more than a quarter hour, and plans could shorten lengths the user had chosen.
- **Lengths:** the task form's length is optional. Left blank, the task's area agent gives it a
  length at once, from the same task's lengths over the last 90 days, else the area's, else 30
  minutes, and then asks the local model in the background; the answer replaces the first estimate
  unless you have given a length meanwhile. Estimates read "≈ 40 min" and name their agent. A length
  you type is at least 30 minutes; Talk ("make Review 10 minutes", "把 Review 改成 20分钟") can set
  any length once you confirm it.
- **Shortening:** plans never shorten a length you set. A length an agent estimated can lose 15
  minutes at a time, never going below 15, when you asked to shorten the task, when its agent found
  it often unfinished, or in Lighter day. A finding about a task with your own length says it keeps
  that length.
- **Day frame:** plans place tasks between 09:00 and 22:00 and keep an hour free for lunch and for
  dinner, at the free hour nearest 12:00 within 11:30–14:00 and nearest 18:00 within 17:30–20:00. A
  meal whose window has passed or is taken is left out. Plans and Today show the meals in the
  schedule.
- **Plans:** Balanced is always first: the areas take turns by priority, work and project first,
  then life, then learning. Beside it come up to two of:
  - Deep focus: work, project, and learning back to back in the day's longest free stretch;
  - Lighter day: nothing before 10:00, life first, 15 minutes after each task, and an estimated
    length trimmed;
  - Finish early: the gaps between fixed times filled as fully as possible;
  - Quick wins first: tasks of 30 minutes or less first;
  - Easiest first: the tasks you usually finish first;
  - Your usual rhythm: tasks near the times you usually do them;
  - Breathing room: an even gap of up to an hour between the tasks of a light day.
- **Choice:** the kinds that suit the day come first, and the kinds you set most often in the last
  30 days before them; on a day with fewer than three tasks to place, Deep focus and Lighter day
  lead. On a low-energy day Lighter day is listed first.
- **Clearly different:** a plan is offered only when, against every plan before it, its tasks come
  in another order and move at least an hour in all, or it ends at least an hour sooner or later. A
  day may therefore get one or two plans.
- **Descriptions:** each plan says why it was suggested, then, under "What sets it apart", what only
  it does, naming its tasks and times, in English and Chinese.
- **Interface:** the Records place is now called Goal, and the model status in the title bar has no
  dot.
- **Release:** the Mac app reports Version 1.5.0 (15), and the service 1.5.0.
- **Evidence:** the service tests, the interface helper tests and the interface build pass. On a
  throwaway demo database, Plans, the task form and Today with a set plan were checked in English and
  Chinese, with no page errors.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="v1-4-build-14"></a>

### v1.4 build 14: a narrower At a glance box — 2026-10-02

- **Why:** each plan's At a glance box spanned the whole column, leaving a wide empty band to the
  right of short values such as 09:30.
- **At a glance:** the box is now only as wide as its labels and values, and never wider than the
  column; a long task name still wraps inside it.
- **Release:** the Mac app reports Version 1.4.0 (14), and the service 1.4.0.
- **Evidence:** the interface builds and its helper tests pass; Plans was captured on a throwaway
  database to check the box in each column.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="v1-3-build-13"></a>

### v1.3 build 13: justified text and a clearer glance — 2026-10-02

- **Why:** text that wrapped left a ragged right edge, as in a plan's rationale, and At a glance
  ran a task's name and its length change together, so "(was 30 min)" broke across lines.
- **Text:** every paragraph, list item, and glance value that wraps is justified, lining up on
  both edges; its last line, and any text on one line, stays at the start. English text is
  hyphenated where that avoids wide gaps; Chinese spreads between characters. Headings, buttons,
  chips, and tables keep their own alignment.
- **At a glance:** the labels take only the width they need. Starts with shows the quoted task on
  one line and its start time under it; Lengths shows each changed task the same way, with its
  change under it, such as 30 min → 45 min.
- **Release:** the Mac app reports Version 1.3.0 (13), and the service 1.3.0.
- **Evidence:** the interface builds and its helper tests pass; Plans was captured on a throwaway
  database, in English and Chinese, to check the glance and the justified rationale.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="v1-2-build-12"></a>

### v1.2 build 12: notices with a title line — 2026-10-02

- **Why:** a notice such as "Read-only · past day · You can view this day and its plan, not
  change them." ran its title and its explanation together in one line.
- **Notices:** the three notices that have a title, Read-only · past day in Calendar, Demo
  workspace, and Example plan, now show the title in bold on its own line, the explanation under
  it, and their icon beside the title.
- **Release:** the Mac app reports Version 1.2.0 (12), and the service 1.2.0.
- **Evidence:** the interface builds and its helper tests pass; a past day in Calendar was
  captured on a throwaway database to check the layout.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="v1-1-build-11"></a>

### v1.1 build 11: proposed plans, their first task, and quoted names — 2026-10-02

- **Why:** each plan carried a "Draft" chip, as if it were unfinished; Starts with read "Nothing to
  place" when a plan held only fixed tasks; and plans proposed by older versions still named tasks
  without quotation marks, as did the plan lists and the agents' findings.
- **Proposed:** a plan the agents proposed carries a "Proposed" chip, and the counts read "3
  proposed by local agents" in Plans and "3 proposed plans · none set yet" on Today's Plan tab, in
  English and Chinese.
- **Starts with:** names the plan's first task and its time, fixed or placed, and reads "No
  tasks" only for an empty plan.
- **Quotes:** every plan description is quoted when DayWright starts, including the oldest
  wordings, such as Adds 15 minutes to “this is title” where the saved calendar has room. The
  plan lists (Kept fixed, Kept protected, Not in this plan, Kept as you set them) and every agent
  finding, such as “Evening walk”: done 3 times, quote the task too.
- **Release:** the Mac app reports Version 1.1.0 (11), and the service 1.1.0.
- **Evidence:** 97 backend tests pass, including quoting the two oldest wordings once; 37
  interface helper tests pass, including a plan with only fixed tasks; the interface builds.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="v1-0-build-10"></a>

### v1.0 build 10: the first numbered release — 2026-10-02

- **Why:** DayWright had only dated history, so nothing in the app or the README said which build
  you were running.
- **Numbering:** versions read v1.0, v1.1 … v1.9, v2.0, and the build is major × 10 + minor; every
  change except a documentation-only one advances both. The [version and build
  policy](CONTRIBUTING.md#version-and-build-policy) lists where the numbers live. Records before
  this one stay dated.
- **In the app:** the Mac app's version is 1.0.0 and its build 10, so About DayWright reads
  Version 1.0.0 (10); the local service reports 1.0.0 too.
- **Contents:** this build holds every change recorded on 2026-10-02 after the pypdf rebuild:
  [areas and untimed tasks](history/2026-10.md#areas-and-untimed-tasks),
  [fitted screens](history/2026-10.md#fitted-screens),
  [Today's tabs and the Plan tab](history/2026-10.md#today-tabs-and-plan-tab), [the agents' review](#agent-findings),
  [fixed start times and plans at a glance](#start-times-and-plan-glance), and
  [one dropdown and one set of buttons](#consistent-controls).
- **Evidence:** the built app's `Info.plist` reads `CFBundleShortVersionString` 1.0.0 and
  `CFBundleVersion` 10.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="consistent-controls"></a>

### One dropdown and one set of buttons — 2026-10-02

- **Why:** a goal's status, a task's goal, a learning subject, and event times used the system's
  own lists and time fields while a task's status used DayWright's menu, and icon-only buttons
  came in two styles.
- **Dropdowns:** every dropdown is now the same component: a button naming the choice, and a menu
  whose options can carry a glyph and a note, with a check on the chosen one and disabled options
  that say why. It comes in two sizes: compact, for a task's or a goal's status, and field, for
  start and end times, a task's goal, and a learning subject. Escape closes only the menu, never
  the sheet around it.
- **Goal status:** reads Active, Paused, or Completed, each with its note (plans may use it, plans
  skip it, kept in history), in the same menu as a task's status.
- **Buttons:** icon-only buttons, such as Close in sheets and Talk, a Library source's Remove, the
  plan pager, the month arrows, and steppers, are all the shared button at 40 × 40: quiet for
  close and remove, outlined for the rest. "Open network log" and "Show all" in Library became
  quiet buttons; text links remain only inside a line of text, such as a banner.
- **Evidence:** the interface builds and its 37 helper tests pass. On a throwaway database the
  task status, goal status, a task's start time and goal, and a Life event's start were opened
  and closed with Escape, with taken times disabled and named; Escape inside the task sheet now
  leaves the sheet open.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="start-times-and-plan-glance"></a>

### Fixed start times, moving tasks in Talk, and plans at a glance — 2026-10-02

- **Why:** a fixed task could be given a start that overlapped another, which later stopped plans
  from being proposed; there was no quick way to move a task; and the three plans were told apart
  only by long rationales that ran task names into the surrounding words.
- **Start times:** a fixed task's Start is a dropdown of quarter hours. A start that would overlap
  another accepted timed task that day for the task's length, or run past midnight, stays in the
  list, greyed out, with a note such as "Overlaps “Team stand-up”". Switching to Fixed picks the
  next free start; if a longer length makes the start clash, an alert names the task and its time,
  suggests asking Talk to move it, and Save waits. A timed Life event's start and end use the same
  lists. The service also refuses an overlapping task, naming the one in the way; an edit that
  keeps a task's day, start, and length is never refused.
- **Talk:** in Adjust, naming a task and a time ("Move Review to 10:30", "3pm", "下午3点") proposes
  moving it, as a fixed task, to that time. When the time is taken, the reply says by what and
  proposes the nearest free start instead. Nothing moves until you confirm, and the time is
  checked again then. Plans already proposed keep their schedule.
- **Overlaps found later:** when tasks already overlap and plans are proposed, the message names
  both, such as "“Meeting” (10:00–11:00) and “Call” (10:30–11:00) overlap".
- **Plans at a glance:** each plan opens with one line saying how it works: Balanced "Even spread:
  the areas take turns, from your first free time.", Focused "Focus first: learning, then project
  and work, while you are fresh.", and Gentle "Easy pace: starts later, life first, with a break
  after each task." Below it, every column shows the same three facts: Starts with (the first task
  it places, and when), Done by, and Lengths (each task it lengthened or shortened, with its
  recorded length). The full rationale follows in smaller type.
- **Quotes:** a plan's rationale puts task names in quotation marks, such as gives “Review notes”
  15 more minutes, in English and Chinese; plans saved before get the quotes when DayWright starts.
- **Evidence:** 97 backend tests pass, including: refusing an overlapping task while allowing one
  that starts as another ends, the same time on another day, and a rename; Talk proposing the
  nearest free time and moving the task once confirmed, from "10:30", "3pm", and "下午4点半";
  naming overlapping tasks; and quoting saved rationales once. 37 interface helper tests pass,
  including the start-time list, a plan's glance, and reading a move proposal. On a throwaway
  database the Start list greyed out 09:45–10:30 around a 10:00 stand-up and a 10:15 call, a
  2-hour task at 09:00 showed the clash and held Save, and Talk proposed 10:45 for "Move Evening
  walk to 10:15".
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

<a id="agent-findings"></a>

### Area agents review each task against the last 30 days — 2026-10-02

- **Why:** a plan's route listed five agents, but the area agents only counted the day's tasks, so
  nothing showed how they took part or what they knew about your habits.
- **Review:** before plans are proposed, the Learning, Life, Work, and Project agents each review
  their tasks for the day against the reports of the 30 days before it, task by task, by name and
  area:
  - partly done or skipped at least twice, and in at least half its reports: 15 minutes shorter,
    never under 30, with the task's first step named when it has one;
  - the same, but fixed, protected, or already 30 minutes: it keeps its length, and says why;
  - done at least twice and in three of every four reports: it keeps its length;
  - a flexible task done at least twice, with starts no more than two hours apart: plans place it
    near its usual time, on the quarter hour;
  - asked to be shortened twice or more: 15 minutes shorter, as before;
  - not on the list in that time, or never reported: nothing to learn from yet.
- **Area records:** Learning adds its sessions in those 30 days; Life adds today's check-in, or
  the latest one before it, and the habit reports, asking for a lighter day at energy 2 of 5 or
  lower; Work adds today's fixed meetings, which flexible work goes around.
- **Plans:** all three plans apply the shorter blocks and usual times. A task with a usual time
  is placed first, at the first free time from then; when nothing is free after it, it takes the
  day's first free time like any other. The Balanced rationale says so. When the Life agent
  advises a lighter day, Gentle is listed first, shown first on a phone, and its rationale opens
  with "Listed first because the Life agent advised a lighter day." When two tasks with a start
  time overlap, or one runs past midnight, proposing stops and names them with their times, such
  as "Meeting (10:00–11:00) and Call (10:30–11:00) overlap".
- **Shown:** at the foot of Plans, "How the agents made these plans" lists every agent in order
  with its findings, in English or Chinese; the Orchestrator and Summary rows keep their
  summaries. Today's Plan tab shows only the finding behind each change.
- **Earlier plans:** a plan's agent list is saved when it is proposed, so plans proposed by an
  earlier version listed only the agents of that time, in their earlier wording and without
  findings. When DayWright starts, each such list is rebuilt: Orchestrator, Learning, Life, Work,
  Project, and Summary review that day again, and the Orchestrator's last line says so. The plans,
  the set one, and reported statuses stay as they were, so tasks that now overlap don't prevent
  it; a day that still can't be reviewed keeps its list and is reported in the service log.
- **Evidence:** 94 backend tests pass, including nine for the review itself, two for placing a
  task near its usual time or falling back, one for listing Gentle first on a lighter day, one
  for naming overlapping tasks, and three through the service: a list saved by an earlier version
  is rebuilt with every agent at start, keeping its plans, the set one, and with tasks that
  overlap; each area agent reviews
  only its own tasks, and with 30 days of backdated reports a task often left unfinished comes
  back 15 minutes shorter and a task usually done at 10:30 is placed there. 30 interface helper
  tests pass, three of them for wording the findings, and the interface builds. On a throwaway
  database with a week of reports and a low-energy check-in that morning, Plans listed every
  agent's findings, and the Plan tab of the set Balanced plan showed each placed or shortened task
  with the finding behind it, in English and Chinese. On a fresh copy of that database the service
  listed Gentle first, and Talk, answered by the local Qwen3 4B model, said it was first because
  the Life agent advised a lighter day. With an earlier version's list saved for a set plan and
  two work tasks overlapping, restarting the service rebuilt that list with all seven rows and
  their findings.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as
  `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and
  merged into `main` the same day.

[Back to change history](#change-history)

</details>

### Earlier history

Older records are archived by period, newest first. Each archive keeps the same table
and full records; the count after a link is how many records it holds.

- **Months** — [October 2026](history/2026-10.md) (6) · [September 2026](history/2026-09.md) (16)

---

<!-- project-control:section=ignore -->
## 🔒 License

**PROPRIETARY SOFTWARE — ALL RIGHTS RESERVED**

Copyright © 2024–2026 Soucieux. All rights reserved.

The original source code, documentation, and other original materials in this repository are proprietary and are not open-source software.

Except where applicable law expressly permits otherwise, no permission is granted to copy, modify, publish, distribute, sublicense, sell, deploy, or create derivative works from these materials, in whole or in part, without prior written authorization from the copyright owner.

Access to this repository does not grant a license. Third-party software and materials remain subject to their respective license terms.

*This private project is not open for external contributions.*
