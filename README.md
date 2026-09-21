# DayWright

![Interface](https://img.shields.io/badge/Interface-React-61dafb) ![Service](https://img.shields.io/badge/Service-Python%20%2B%20FastAPI-05998b) ![Storage](https://img.shields.io/badge/Storage-SQLite%20%2B%20sqlite--vec-3f6e9b) ![Status](https://img.shields.io/badge/Status-Multi--agent%20RAG%20slice-f1512e)

<!-- project-control:section=overview -->
## Overview

DayWright is a private, single-user, local-first multi-agent daily-life management workbench for
goals, owned commitments, learning, life, money, and rest. Its central artifact is a user-approved
plan grounded in actual daily records. Bounded Learning,
Life, Finance, and Summary agents contribute assessments; the Orchestrator may propose today's plan
or a change for approval. Summary-informed agent-origin future commitments may be placed directly
with an explanation and remain editable by the user; they are not confirmed day plans.

The editorial filing-tab language now serves a management system: a Today control desk, retained
Calendar, one integrated Plans decision desk, goal/area ledgers, and visible local conversation.

<!-- project-control:section=overview -->
## Current capabilities

- Set goals, record timed today/future items, mark fixed/recurring or important-to-keep commitments, and
  explicitly report progress. A new user starts with an empty account, never an invented schedule.
- Create goal-linked or independent tasks directly in Learn, Life, and Money. Each domain shows the
  goal path and its tasks, while Goals shows the same linked work and overall completion progress.
- See owned records, goals, daily summary, active-plan state, and area links on Today.
- Browse past and future months in Calendar, see recorded-day month totals, select a day, and
  inspect its summary and schedule. Unrecorded dates stay empty rather than receiving invented
  history.
- Explicitly ask the Orchestrator to propose materially different same-date alternatives from
  today's items and eligible recurrence. One to three variants may be feasible. Comparison,
  schedule, rationale, and confirmation share a single Plans management desk.
- Confirm exactly one plan for a date; replacing it requires a named, explicit approval.
- Mark owned daily items and entries in the confirmed plan Planned, Done, Partial, or Skipped;
  linked records and goal progress stay synchronized.
- View saved Summary-agent reports and suggestions for a day, ISO week, or month. Explicit named-
  task shortening requests inform later plans and traceable agent-origin future commitments. The
  current-week report can also prepare the next recurring date when an important-to-keep task was
  explicitly completed on at least two recorded days; shortening feedback takes precedence.
- Manage Learning subjects and explicit session outcomes; Life sleep/energy/mood, habits, and timed
  events; and manual Money balances, income/expenses, and category budgets. Timed Life events are
  shared daily items in Calendar and Plans; subjects, check-ins, and transactions are domain facts,
  not invented calendar commitments. Past reports stay read-only.
- Manage saved soft/strong Summary advice by period and area. An active idea is dispatched to its
  relevant agent, and size/timing advice can prioritize a gentler variation. Discarding an idea
  stops its dispatch across periods; a matching later report shows a notice only. Clearing one
  exact week and area permanently requires typing its target, and cleared advice stays cleared.
- Keep or dismiss a contextual suggestion.
- Ask about the plan, request an adjustment, and review the proposed action before applying it.
- Switch the interface between English and Simplified Chinese; the same preference tells the local
  Orchestrator which language to use for its response.
- See the complete Orchestrator → domain agents → Summary → Orchestrator route for every response.
- Persist agent contributions and their bounded read/write scopes with the conversation.
- Add private notes to the Library, chunk them locally, index their embeddings in `sqlite-vec`,
  and show which sources were retrieved for an answer.
- Select a Markdown, text-based PDF, or Word `.docx` file for bounded local extraction and indexing;
  unsupported formats and scanned PDFs produce a clear message. Files are not uploaded to a public
  provider or stored as originals. Changed files with the same name retain separate indexed versions.
- Enter a learning topic: a separate KnowledgeState graph checks local semantic relevance first,
  then conditionally fetches a short Wikipedia introduction and presents three organizational
  import choices. The public text and its URL/license are staged locally, not indexed until one
  choice is confirmed. Other choices cannot subsequently index the same acquisition. The graph
  keeps obvious personal identifiers out of an automatic web query. An explicit web option
  overrides a local match but not the personal-topic guard.
- Persist plans, conversation, proposals, and decisions in local SQLite storage.
- Use the existing local Qwen model for Orchestrator synthesis through `llama-server`; no model copy
  is kept here.
- Open each Learn, Life (including Rest), and Money area as a state sheet or a day-ledger/plan view.
  Their scheduled items still match the same selected day's records in Calendar. Library sources
  are not automatically calendar events.

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

5. Open the local address shown by the interface command. A small model dot starts amber and turns
   green after the first model-backed conversation is ready.

For a populated walkthrough that cannot mix with personal records, start `npm run api:demo`, then
start the interface with `DAYWRIGHT_API_TARGET=http://127.0.0.1:8423 npm run dev`. The demo uses
`backend/data/daywright.demo.sqlite3`, shows a persistent demo banner, and contains sample goals,
today tasks, domain records, and read-only historical plans. It intentionally starts before today's
plan is generated, so the presenter can begin by selecting “Generate plan options,” compare the
Balanced, Focused, and Gentle alternatives, and confirm one.

If an older local service and interface are already running, stop those two terminal commands and
start them again to load this source revision. Refreshing an older preview alone may still show its
previously loaded service routes.

**Success check:** A fresh account has no plan. Add a goal and two nonoverlapping timed items for
today, then select “Propose day plans” on Calendar/Plans. The integrated desk shows the available
variants; confirming one updates Today, Calendar, Goals, and area ledgers. Calendar can move to a
previous month without creating history, and day/week/month Summary-agent reports stay visible.

If the service is not running, the interface opens in an honest offline view. Nothing is sent,
generated, or saved, and it does not simulate an agent answer.

<!-- project-control:section=workflows -->
## Workflow

```text
Open Today
  → set goals and record your actual daily items
  → ask the Orchestrator to propose from owned/eligible recurring items
  → compare available alternatives and one integrated decision file in Plans
  → confirm the day
  → report Done / Partial / Skipped on today's owned items/current plan
  → review day/week/month Summary-agent advice and explicit preference evidence
  → inspect past plans as read-only snapshots; preset future commitments now
  → see agent-origin future records with Summary evidence, and ask why/change them
  → explicitly review a replacement if another plan becomes preferable

Ask or mark up the plan
  → embed the question with Qwen3 Embedding 0.6B
  → retrieve the nearest locally indexed private or attributed public chunks from sqlite-vec
  → Orchestrator routes the request
  → Learning / Life / Finance assess only their state slices
  → Summary joins cross-domain findings
  → the shared local Qwen runtime explains the tradeoff
  → structured proposal appears
  → user confirms or dismisses it
```

A present-day plan proposal does not confirm or replace a plan by itself. Summary-informed future
records are the narrow exception: they can be directly prepared with provenance, and the user can
question or edit them. The SQLite record, not conversational wording, is the source of truth.

For a selected local file, DayWright accepts at most 2 MB, 20 PDF pages, and 50,000 extracted
characters. Only readable text is indexed; a scanned or encrypted PDF needs preparation first.
For a new Library topic, the entered topic alone is sent to Wikipedia only when local embedding
search has no match or the user checks the explicit public-web option. Private source text, goals,
and daily records are not in that request. An unavailable local embedding service does not trigger
an automatic public lookup, because DayWright cannot establish that the local library has no match.
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
user presses the microphone. A recording begins only after the push-to-talk button is pressed,
may require the browser's microphone permission, and is discarded after recognition. The recognized
text appears in the editable composer before it can be sent to the agents.

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

Domain agents currently derive typed assessments deterministically from their permitted state
slices. The Orchestrator uses Qwen once to synthesize those reports. This preserves meaningful agent
boundaries without loading the same 2.5 GB model five times.

The existing Qwen3 4B model passed the current cross-domain workload, so no additional model was
downloaded or copied into the project. A larger replacement should be considered only after a
repeatable quality benchmark shows that its improvement outweighs local memory and response-time
costs.

<!-- project-control:section=architecture -->
## Architecture

| Layer | Responsibility |
|---|---|
| React interface | Today/Goals management, retained Calendar, integrated Plans, synchronized area ledgers, and visible conversation drawer |
| FastAPI service | Local API, validation, conversation policy, and model lifecycle |
| Multi-agent core | PlatformState day-proposal graph with a separate SQLite checkpoint file, bounded domain assessments, Summary memory, and Orchestrator synthesis |
| KnowledgeState graph | Local-first topic lookup checkpointed outside the vector database; bounded public fetch/filter and three staged import choices before indexing |
| Deterministic planner | Valid record-based alternatives, repeated named-task evidence, duration arithmetic, and fixed constraints |
| SQLite repository | Goals, owned items, plan snapshots, reports, explicit feedback, conversations, decisions, sources, and retrieval provenance |
| `sqlite-vec` index | Local 1,024-dimensional nearest-neighbor search beside the authoritative records |
| Shared `LlamaRuntime` supervisor | Authenticated loopback process startup, health readiness, concurrent first-use serialization, failure recovery, and shutdown |
| ModelGateway | Local chat-model response contract over the shared runtime supervisor |
| EmbeddingGateway | Separate embedding-only contract for indexing and question retrieval over the shared supervisor |
| SpeechGateway | Short, user-initiated local WAV transcription through a converted Whisper-small model; temporary audio is removed after the request |

The service is loopback-only in the documented development command. Generated private data and
`daywright.checkpoints.sqlite3` live in `backend/data/` and are ignored by Git. Checkpoints are
execution snapshots; the main database remains the authority for confirmed plans and sources.

## Project map

| Path | Contents |
|---|---|
| `src/` | React workbench and editorial folio styling |
| `backend/app/` | Local service, multi-agent core, SQLite/`sqlite-vec` storage, planner, retrieval, and model gateways |
| `backend/tests/` | Planner and API behavior checks |
| `docs/Original Product Design.md` | Full original 767-line product design text retained as the detailed architecture source |
| `docs/DayWright — Product Design.md` | Revised product, UX, data, AI, privacy, and delivery specification |
| `docs/design-reference.png` | Approved visual source used for implementation and QA |
| `design-qa.md` and `design-qa-*.png` | Desktop, mobile, and multi-agent drawer visual evidence |
| `worker/`, `.openai/`, `scripts/prepare-sites-build.mjs` | Preserved local prototype packaging contract; no hosted deployment is claimed |

## Design source

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

This builds the interface, checks the static packaging contract, and exercises the local planner and
API. Model loading is checked separately because it uses the 2.5 GB shared model at runtime.

## Current boundaries

- This is a working local browser-hosted vertical slice, not a signed or packaged desktop release.
- Native Tauri sidecar packaging and supervised folder import are the next stage. Library currently
  accepts private pasted notes, selected Markdown/PDF/Word files, and locally checked public topics.
  Push-to-talk capture, the local transcription endpoint, the installed `faster-whisper` runtime,
  and converted Whisper-small inference have been exercised through the real API with synthetic
  speech; no user microphone recording was made during that check.
- Goal-linked timed today/future records, daily/weekly carry-forward, and traceable agent-origin
  future commitments exist. Learning subjects/sessions, Life habits/daily state/events, and manual
  Money accounts/transactions/budgets are implemented; mastery/review workflows, broader category
  tools, and governed past correction still remain.
- Summary now uses goals, plan outcomes, explicit Learning sessions, Life check-ins/habit reports,
  manual Money figures/budgets, indexed-source counts, and exact-title shortening requests. It does
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
- Local storage is not yet encrypted and the user-facing backup/export/delete controls required for
  production are not built.

<!-- project-control:section=ignore -->
## Contributing

For source changes, follow the [DayWright contribution guide](CONTRIBUTING.md).

<!-- project-control:section=history -->
## Change history

**Change-history numbering:** This project uses dated history and does not assign project-level
version or build numbers. Follow the [version and build policy](CONTRIBUTING.md#version-and-build-policy).

One record per change; complete details and evidence are below. Older work dates and Git checkpoints remain labelled when they differ.

**Historical status:** Each record describes its own delivery checkpoint. Later records supersede older pending work or recovery locations; historical checks are not new validation.

| Record | Date | Highlights | Details |
|---|---|---|---|
| Maintenance | 2026-09-21 | <ul><li><strong>Security:</strong> Cleared the nine dependency advisories GitHub reported against the interface build — six high, three moderate.</li><li><strong>Versions:</strong> Vite moves to 6.4.3; PostCSS, nanoid, browserslist and its data companions resolve to their patched releases.</li><li><strong>Backend:</strong> Every pinned Python requirement was checked and carries no advisory, so the service dependencies are unchanged.</li></ul> | [Full record](#dependency-advisories-cleared) |
| Maintenance | 2026-09-20 | <ul><li><strong>Name:</strong> The project was renamed to DayWright across the interface, documents, and service identity.</li><li><strong>Local interfaces:</strong> The package name, environment variables, upload header, and Wikipedia user agent carry the new name.</li><li><strong>Storage:</strong> The database, demo, and checkpoint files use the `daywright` stem, and the existing local databases were renamed from verified copies.</li><li><strong>Preserved:</strong> Product behavior, privacy boundaries, architecture, and stored records are unchanged.</li></ul> | [Full record](#renamed-to-daywright) |
| Maintenance | 2026-09-19 | <ul><li><strong>Local boundary:</strong> The development UI now binds only to loopback, matching the API and model processes.</li><li><strong>Explicit mutation:</strong> Summary generation uses POST because it saves reports, suggestion state, and eligible future commitments.</li><li><strong>Runtime privacy:</strong> Chat and embedding tokens stay out of process arguments, while model request logging is disabled.</li><li><strong>Runtime structure:</strong> One shared supervisor now owns both local-model lifecycles, waits for health under concurrent first use, and handles launch failure without an API crash.</li><li><strong>Reliability:</strong> Added focused regressions, removed unused bundled sample data and test deprecation warnings, completed missing theme variables, and reconciled the product status documentation.</li></ul> | [Full record](#local-boundary-and-runtime-privacy) |
| Maintenance | 2026-09-18 | <ul><li><strong>Planning demo:</strong> Preset goals and tasks now lead directly into generating and comparing plan alternatives instead of opening on an already confirmed plan.</li><li><strong>Daily command center:</strong> Today now manages the next action, plan state, workload, area balance, agent advice, and goal progress instead of presenting three isolated counters.</li><li><strong>Unified area work:</strong> Learn, Life, and Money now keep goal-linked and independent tasks in one list, with goal tags and progress visible on linked work.</li><li><strong>Languages:</strong> English and Simplified Chinese can be selected for the interface and local Orchestrator response.</li><li><strong>Management navigation:</strong> Management screens and the three life areas are grouped; Library is nested under Learn, and the assistant has one persistent entry.</li></ul> | [Full record](#goal-paths-and-bilingual-planning) |
| Documentation | 2026-09-18 | <ul><li><strong>Structure:</strong> Aligned the README's sections, markers and change history with the repository's other project READMEs.</li><li><strong>License:</strong> Added the approved Soucieux proprietary-software notice.</li></ul> | [Full record](#readme-alignment) |
| Maintenance | 2026-09-16 | <ul><li><strong>Change:</strong> Installed offline push-to-talk transcription, simplified the management surface, rebuilt Summary around scannable evidence and actions, added an isolated populated demo workspace, and verified local Qwen conversation end to end.</li></ul> | [Full record](#local-voice-transcription) |
| Maintenance | 2026-09-15 | <ul><li><strong>Change:</strong> Expanded management views with owned goals/items, record-based alternatives, conversation entry, read-only history, period reports, explicit preference evidence, and original-design trace.</li></ul> | [Full record](#calendar-and-plan-desk) |
| Maintenance | 2026-09-14 | <ul><li><strong>Change:</strong> Created the DayWright specification and folio interface; implemented the local day workbench, SQLite/`sqlite-vec` state, deterministic plans, explicit confirmation, separate Qwen chat and embedding runtimes, local RAG, and a visible permission-bounded multi-agent core.</li></ul> | [Full record](#initial-vertical-slice) |

<details>
<summary>Full records for this table</summary>

<a id="dependency-advisories-cleared"></a>

### Dependency advisories cleared — 2026-09-21

- **What was reported:** nine open advisories against the interface dependencies — six high, three moderate — in
  `browserslist` (GHSA-c83g-rgw3-j3cx, GHSA-73wf-gq98-2v4g), `nanoid` (GHSA-2v37-7h3g-55p8,
  GHSA-28wg-ghj8-5hjv), `postcss` (GHSA-r28c-9q8g-f849, GHSA-fxqj-rqcc-2cmp), `vite`
  (GHSA-fx2h-pf6j-xcff, GHSA-v6wh-96g9-6wx3) and `baseline-browser-mapping`
  (GHSA-w5vr-8v7q-w6rv). All nine sit in the lockfile, none in the service requirements.
- **Fix:** `vite` advances to 6.4.3 in the manifest, keeping the project's exact-pin style. The other four are
  transitive and their declared ranges already permitted the patched releases, so they resolved to
  `postcss` 8.5.28, `nanoid` 3.3.19, `browserslist` 4.29.0 and `baseline-browser-mapping` 2.11.25.
- **Scope of the lockfile change:** nine locked versions, including the four browserslist data companions
  (`caniuse-lite`, `electron-to-chromium`, `node-releases`, `update-browserslist-db`) that travel with it. No
  package was added or removed, and no major version changed.
- **Backend:** all ten pinned Python requirements were checked at their exact versions and report no advisory, so
  `backend/requirements.txt` is unchanged.
- **Evidence:** `npm test` rebuilt the production bundle on Vite 6.4.3, transforming 1,583 modules, and passed all
  5 Sites/package tests and all 41 API/planner tests.
- **Status:** dependency and lockfile change with local checks. A published advisory list refreshes on its own
  schedule, so the reported count clears after the next scan rather than on this commit.

[Back to change history](#change-history)


<a id="renamed-to-daywright"></a>

### Renamed to DayWright — 2026-09-20

- **Name:** The project was renamed to DayWright in every document, interface string, and identifier. A wright
  is a maker, and the unit this product makes is the day; the specification's naming rationale was
  rewritten to say so, and the folio mark now reads `D/`.
- **Interface:** the page title and description, workbench section headers, assistant labels, and
  both the English and Simplified Chinese string tables carry the new name.
- **Local interfaces:** the package is `daywright`; `DAYWRIGHT_DATABASE`, `DAYWRIGHT_MODEL_LIBRARY`,
  `DAYWRIGHT_LLAMA_SERVER`, `DAYWRIGHT_DEMO`, and `DAYWRIGHT_API_TARGET` replace the previous
  environment names; the local upload header is `X-DayWright-Filename`; and the Wikipedia user agent
  is `DayWrightLocalBot`.
- **Storage:** the default database is `backend/data/daywright.sqlite3`, and the demo and checkpoint
  files follow the same stem. The existing local databases were renamed from byte-identical verified
  copies, so recorded days, goals, plans, knowledge chunks, and the demo workspace are preserved.
- **Saved preference:** the stored interface language key is now `daywright-language`. An earlier
  saved choice is not carried across, so the interface language is selected once after the rename.
- **Evidence:** `npm test` rebuilt the production bundle and passed all 5 Sites/package tests and all
  41 API/planner tests. The repository history check reported every change history inside its inline
  window, and the activity index was regenerated.
- **Status:** delivered as uncommitted source, then committed canonically and published. The public
  repository carries the new name, and its tip's tree matches this folder exactly.

[Back to change history](#change-history)

<a id="local-boundary-and-runtime-privacy"></a>

### Local boundary and runtime privacy — 2026-09-19

- **Network boundary:** Vite now listens on `127.0.0.1`, so the browser workbench no longer exposes
  its proxied local API to other devices on the network. A packaging test locks that host setting.
- **Summary contract:** `/api/summaries` is now POST-only because generating a report persists
  reports, synchronizes the suggestion pool, and can prepare an eligible future commitment. The
  client and API regressions exercise the explicit write method and reject GET.
- **Model privacy:** chat and embedding runtimes receive their random API token through
  `LLAMA_API_KEY`, keep it out of the process list, disable `llama-server` logging, and discard
  standard output and error rather than retaining prompts or private source text in runtime logs.
  The obsolete ignored runtime logs were removed after confirming no process still held them.
- **Runtime structure:** both gateways now delegate process ownership to one `LlamaRuntime`
  supervisor. A concurrent first request waits for the same health-verified process instead of
  treating a merely spawned child as ready, while an executable launch failure returns the normal
  unavailable/rule-based path. The unused frontend-only sample-plan module was removed; the
  isolated SQLite demo remains the single source of sample product data.
- **Reliability and consistency:** focused tests cover both model launch contracts; demo tests use
  the database's ISO-date contract without deprecation warnings; the two theme variables already
  referenced by the interface are defined; current README and product-specification status now
  match the verified local voice implementation.
- **Evidence:** `npm test` rebuilt the production bundle and passed all 5 Sites/package tests and
  all 41 API/planner tests. The actual installed Qwen chat runtime reached health and returned a
  local-model response; the actual embedding runtime returned a non-zero 1,024-dimensional vector,
  and both stopped without recreating their old log files. Repository link and history checks also
  passed; the repository-wide README layout check reported only pre-existing OpenClaw departures
  outside this project.
- **Status:** the audited local batch is canonically integrated; no public-mirror update or
  hosted deployment is claimed.

[Back to change history](#change-history)

<a id="goal-paths-and-bilingual-planning"></a>

### Goal paths and bilingual planning — 2026-09-18

- **Demo flow:** the isolated demo keeps its predefined goals, dated tasks, domain records, Library
  source, and past plans, but resets today's generated plan on startup. Plans therefore opens at
  the multi-agent generation step with real sample inputs already present.
- **Daily command center:** Today prioritizes the next action and places plan state, completion,
  scheduled time, protected work, area allocation, linked-goal progress, and the Summary Agent's
  day/week/month evidence in one actionable management surface. The former Agent Brief duplicate
  is removed; next-plan guidance and saved-advice controls now live only inside the command center.
  Advice names the supporting task or area record and recommends a concrete time, duration, or
  financial decision instead of repeating a generic category phrase. Source records never appear
  as an active Today schedule before confirmation; after confirmation, Today switches to the chosen
  schedule with explicit start–end times and progress reporting.
- **Bidirectional goal work:** every goal response includes its linked dated tasks. Learn, Life, and
  Money keep all dated work in one task board; goal-linked tasks carry a visible goal tag and the
  goal's progress, while independent tasks remain in the same list with a neutral label. Goals
  presents the same linked work and progress from the goal direction.
- **Bilingual operation:** a persistent English/Chinese selector changes every management screen,
  form, summary, calendar label, multi-agent control, and predefined demo record. User-authored
  content and prior conversation text stay unchanged. New conversation requests carry the selected
  language, and the local Orchestrator is instructed to answer in English or Simplified Chinese
  without changing its data permissions or confirmation rules.
- **Management navigation:** the rail separates Today, Calendar, Plans, and Goals from the Learn,
  Life, and Money areas. Library is visually nested beneath Learn instead of appearing as a fourth
  life area, group headings are readable dividers, and transformed tabs no longer create a bottom
  scrollbar. The wider rail preserves full tab names and keeps its closing message inside the
  visible column. Calendar owns navigation and past read-only review without repeating today's task
  board or Summary Agent report. Summary advice is consolidated on Today, where the next-plan
  guidance includes active saved advice when the selected period has no new recommendation. The
  persistent Talk to DayWright control is the sole assistant entry card.
- **Status:** committed canonically as `e41f7ac`, `26d2693`, and `21dd191`; the filtered public
  mirror was published through `6fb66ba`. No hosted deployment is claimed.

[Back to change history](#change-history)

<a id="readme-alignment"></a>

### Documentation

- **Recorded date:** 2026-09-18.
- Aligned this README with the repository's other project READMEs: an Overview section, section
  markers for the sections an overview reader shows, a Contributing section pointing to the
  contribution guide, the standard change-history declaration and status note, labelled highlight
  cells, and newest-first records that each link back to the table.
- Added the approved Soucieux proprietary-software notice, reserving rights in original project
  materials while retaining third-party license terms.
- Documentation only; application behavior, dependencies, builds, deployment, and publication
  status are unchanged.

[Back to change history](#change-history)

<a id="local-voice-transcription"></a>

### Local voice transcription — 2026-09-16

- **Simpler management surface:** Today removes the duplicate schedule summary, shortens its hero,
  keeps the management state in three direct controls, and promotes one explicit local-AI action.
  Summary now presents recorded days, completion, suggestions, per-area outcomes, and at most two
  next steps; detailed preference memory is disclosed only on request.
- **Isolated demo:** `npm run api:demo` uses a separate SQLite file and idempotently creates three
  goals, three current-day records, a confirmed plan with three alternatives, four past confirmed
  plan snapshots, a Learning subject/session, a Life check-in/habit, a Money transaction/budget,
  and an indexed Library note. A banner identifies the workspace so examples cannot be mistaken
  for personal data.
- **Today versus Calendar:** Today is the execution surface for the current plan, records, progress,
  and local AI. Calendar owns history, read-only past-plan inspection, and period summaries. A
  dedicated recent-plan strip exposes past confirmed dates and their outcomes before the month grid.
- **Local conversation evidence:** A real demo request through `/api/chat` was synthesized by the
  Qwen3 4B GGUF model and answered from the saved learning item with `model_mode=local-model`.

- **Runtime:** Installed pinned `faster-whisper` 1.2.1 and its CPU dependencies in DayWright's
  Python 3.12 environment, without requiring acceptance of the machine's outstanding Xcode license.
- **Model:** Added the publisher's multilingual converted Whisper-small files under the shared
  `AI-Models/whisper/faster-whisper-small/` directory. The original Core ML package remains intact.
  The 483,546,902-byte weights file matched the publisher's pinned SHA-256
  `3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671`.
- **Privacy and UX:** Push-to-talk remains user-initiated; WAV recordings use a temporary directory
  and are removed after recognition. The drawer always states unavailable, ready, recording,
  transcribing, or editable-review status. Recognition runs outside the API event loop.
- **Evidence:** Focused readiness/API tests passed. A 2.24-second synthetic mono 16-bit 16 kHz WAV
  sent through the real `/api/voice/transcribe` route returned the exact editable sentence “Plan a
  shorter learning session tomorrow.” with HTTP 200. The refreshed UI visibly reported “Voice
  ready” against the updated service. The demo-seeding regression and production build also passed,
  and the populated Today/Summary view was visually checked. No user microphone recording was made.

[Back to change history](#change-history)

<a id="calendar-and-plan-desk"></a>

### Calendar and plan desk — 2026-09-15

- **Management view:** Today focuses on summary, active-plan state, goals, owned items, area links,
  and Calendar/Plans actions. Plans combines alternatives, rationale, schedule, and decision.
- **Calendar:** Month navigation includes past months; recorded days reveal the current plan,
  operational month totals, progress, domain allocation, and scheduled items. Browsing an
  unrecorded day is read-only and does not seed a fictional historical plan.
- **Plan choice:** Balanced, Focused, and Gentle are explicitly labelled as alternatives for one
  date. A preview cannot change the current plan. Replacing a confirmed variant requires a named
  review and approval; direct unapproved replacements return a conflict. Completion reports remain
  attached to their original alternative and may differ after a replacement.
- **Shared state:** Reporting is accepted only on entries belonging to the confirmed variant;
  Calendar’s completion count and the Learn, Life/Rest, and Money ledgers use that same variant.
  Library sources and unscheduled Notes are intentionally separate from calendar events.
- **Personal intake and memory:** Fresh accounts show no sample plan. Users set goals and timed
  today/future items before Orchestrator proposals. Recurrence, fixed/important commitments,
  exact-title shortening feedback, and period reports persist locally. Summary can directly add
  an agent-origin future item with evidence; it remains distinct from a confirmed plan and can be
  explained or edited. Past plans stay read-only. The Talk entry is visible on every screen.
- **Beneficial recurring evidence:** Summary now retains per-task done-day counts for protected
  recurrence. Two completed days in a reviewed week can place the next user-editable future record
  with outcome provenance at its original duration. If the user repeatedly asks to shorten the same
  task, the shorter block wins, while the task remains included.
- **Architecture fidelity:** The revised specification maps the original agent, state,
  suggestion, knowledge, UI, local-model, and voice contracts to current source and remaining
  work. The day-proposal and conditional KnowledgeState graphs checkpoint outside the vector
  database; complete conversation graph coverage, full domain context, and native packaging remain
  pending. Local push-to-talk transcription is now model-backed and checked through the real API.
- **Design authority:** The full original product design text is retained inside `docs/` beside
  the revised specification and its explicit implementation-versus-remaining fidelity ledger.
- **Local knowledge import:** User-selected Markdown, text-based PDF, and Word `.docx` are parsed
  with size/page/text limits and indexed as local documents without retaining the original bytes.
  Different content with the same filename retains distinct indexed sources rather than overwriting
  the earlier import. Unsupported formats and scanned PDFs report an error; folder import and OCR
  remain future work.
- **Suggestion management:** Summary advice now persists as soft/strong entries keyed by day,
  week, and month. Today offers an area-filtered review; discarding a content-matched idea affects
  all periods, and a later repeat creates a notice rather than an active idea. Active guidance
  reaches bounded domain agents and can prioritize a gentler record-based variation. An exact
  week/area reset hard-deletes its content behind a typed confirmation and retains only a noncontent
  clearing marker, preventing regenerated advice from silently reappearing.
- **Public import choice:** KnowledgeState now runs local lookup, bounded encyclopedia fetch,
  a credibility/timeliness/format receipt, and three organization-scheme choices. It retains
  the fetched text locally as pending and performs chunking/embedding/indexing only when one
  choice is confirmed; a second choice conflicts. Labels name the organizational intention,
  while verified per-passage classification and multi-source comparison remain pending.
- **Talk replacement guard:** A conversation proposal names the confirmed and proposed day plans.
  Approval is accepted only if the reviewed current plan is still current; an unreviewed or stale
  chat action cannot switch the confirmed date.
- **Domain management:** Learning subjects and sessions; Life daily state, habits, and categorized
  events; and manual Money balance, transactions, and category budgets now have separate local
  records and state sheets. Timed events write a linked Calendar item atomically; sessions and
  transactions remain unscheduled. Summary and bounded domain-agent assessments read these actual
  records. A recorded low-energy state can guide a gentler Life block, and over-budget advice names
  the saved category figures without claiming a bank connection.
- **New checks:** Fresh-account, linked-state, future-provenance, local-first knowledge, and voice
  endpoint tests are added. The isolated browser check demonstrated three alternatives from two
  user-owned items, one confirmed plan, updated Today/Calendar, completion, and an editable future
  record. A real public French-language introduction was first staged with zero new vectors,
  then one chosen import indexed and retrieved two attributed chunks in a clean, isolated database;
  separate checkpoint persistence and both SQLite files' integrity were checked. The choice sheet
  was also checked at desktop and 390-pixel width.
- **Checks:** The documented `npm test` command passed 30 API checks, four static packaging tests,
  and the production build. Browser interaction and visual checks covered an empty account, Today,
  Calendar, Plans, synchronized areas, reviewed replacement, Library, and 390-/320-pixel responsive
  states. After the domain-management slice, three new domain API scenarios and two affected plan/
  Summary regressions passed as focused checks; the production build passed again. The current
  isolated browser pass verified Learning-session saving, Life/Money area navigation, and the
  390-pixel Life layout, but did not visually submit Life/Money forms. The compatible speech CLI was
  unavailable during that earlier pass. No commit, native installation, or hosted publication is
  claimed.

[Back to change history](#change-history)

<a id="initial-vertical-slice"></a>

### Initial multi-agent vertical slice — 2026-09-14

- **Product:** Reframed the platform as a workbench-first, conversation-enabled system where
  structured state is authoritative and consequential AI suggestions require confirmation.
- **Experience:** Implemented the approved editorial folio with indexed tabs, daily schedule,
  alternative-plan review, hard constraints, explicit commitment, suggestion handling, progress
  reporting, domain summaries, and a contextual conversation drawer.
- **Planning:** Added deterministic Balanced, Focused, and Gentle plans and checks for domain coverage
  and schedule collisions.
- **Persistence:** Added SQLite tables for plan sets, versioned variants, plan entries, one daily
  confirmation, conversation history, proposed actions, action decisions, preference provenance,
  suggestions, integer-minor-unit finance entries, knowledge sources/chunks, and retrieval evidence;
  `sqlite-vec` stores the associated 1,024-dimensional vectors in the same database.
- **Local AI:** Connected the existing Qwen3 4B GGUF through the installed `llama-server` using a
  dynamic loopback port, per-launch token, bounded context, offline mode, and supervised shutdown.
  Connected the existing Qwen3 Embedding 0.6B GGUF through a separate embedding-only runtime. The
  existing Whisper package is recorded but not yet active.
- **RAG:** Added local note capture, 180-word overlapping chunks, vector indexing, instruction-aware
  question embeddings, nearest-chunk retrieval, prompt grounding, persisted retrieval provenance,
  a relevance-distance gate, and visible private-source labels. Retrieved text is treated as
  untrusted reference material; source snapshots keep historical answers explainable after a note
  is revised.
- **Multi-agent:** Added Orchestrator, Learning, Life, Finance, and Summary roles with bounded state
  access, deterministic domain assessments, persisted execution traces, visible conversation
  routing, and Orchestrator-only plan proposals. Qwen provides the Orchestrator’s language synthesis
  through one shared local runtime.
- **Checks:** Passed the production interface build, static packaging contract, eleven planner/API
  tests, primary browser interactions, real local-model multi-agent routing, persisted-route
  retrieval, separate real embedding-model output validation, 390-pixel responsive inspection, and
  final design comparison.
- **Boundaries:** Kept the first delivery browser-hosted and local. Native packaging, voice,
  file-format import, external research, and finance connectors remain future work and are not
  represented as delivered.

[Back to change history](#change-history)

</details>

---

<!-- project-control:section=ignore -->
## 🔒 License

**PROPRIETARY SOFTWARE — ALL RIGHTS RESERVED**

Copyright © 2024–2026 Soucieux. All rights reserved.

The original source code, documentation, and other original materials in this repository are proprietary and are not open-source software.

Except where applicable law expressly permits otherwise, no permission is granted to copy, modify, publish, distribute, sublicense, sell, deploy, or create derivative works from these materials, in whole or in part, without prior written authorization from the copyright owner.

Access to this repository does not grant a license. Third-party software and materials remain subject to their respective license terms.

*This private project is not open for external contributions.*
