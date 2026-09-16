# Wellspent — Product Design and Implementation Specification

**Document status:** Revised product specification  
**Product status:** Local multi-agent/RAG slice with calendar and plan desk implemented  
**Date:** 2026-09-15  
**Audience:** Product design, engineering, and future contributors

## 1. Product definition

Wellspent is a private, single-user, local-first, multi-agent workbench for deciding how to spend
limited time, attention, energy, and money. It unifies self-directed learning, everyday life, and
personal finance without turning the day into an optimization contest.

The product is **workbench-first and conversation-enabled**. The durable state is a visible plan,
not a chat transcript. Conversation helps the user understand, adjust, and report on that state,
but never changes consequential data silently.

### The central promise

> Help me shape a day I can believe in, explain the tradeoffs, and remember what actually happened.

### Why the name fits

“Wellspent” describes the product’s common unit: a life can be well spent, a day can be well spent,
attention can be well spent, and money can be well spent. The name supports all three domains
without reducing the product to productivity, education, or budgeting alone.

## 2. Product principles

1. **A balanced day is the output.** The product’s main artifact is a believable schedule across
   learning, life, money, and rest.
2. **The user keeps authorship.** AI can explain or propose; the user confirms every consequential
   change.
3. **Structure is authoritative.** SQLite records plans, tasks, events, preferences, and decisions.
   A conversation is evidence and interface, not the system of record.
4. **Deterministic facts stay deterministic.** Date arithmetic, durations, budget totals, collision
   checks, recurrence, and currency arithmetic are implemented in code.
5. **Local-first is visible.** Model readiness, runtime state, persistence, and any network boundary
   are disclosed in the interface.
6. **Progress is reported, not inferred.** The system does not mark work complete from elapsed time
   or conversational implication.
7. **Calm beats density.** The interface should feel like a considered day folio, not another generic
   analytics dashboard.
8. **Central dispatch preserves boundaries.** Learning, Life, Finance, and Summary contribute
   bounded assessments; only the Orchestrator may turn them into a plan proposal.

## 3. User and jobs to be done

### Primary user

A single person managing overlapping learning goals, everyday responsibilities, health and energy,
and personal financial awareness on one Mac.

### Core jobs

- See a realistic plan for today with fixed commitments, flexible work, and recovery.
- Compare alternative plans before committing.
- Ask why the day is arranged this way.
- Describe a change in natural language and review its effect before applying it.
- Report an item as Done, Partial, or Skipped.
- Keep learning, life, and money records in one local source of truth.
- Use a local model without uploading the day’s private context.

## 4. Scope

### Local management slice — implemented in source; verification pending

- Today folio with a time-ordered schedule.
- Learning, Life, Finance, and Rest allocation.
- Fixed and flexible constraints.
- Balanced, Focused, and Gentle plan variants.
- One confirmed plan per date.
- Explicit Done, Partial, Skipped, and Planned states.
- Suggestion keep/dismiss flow.
- Ask, Adjust, and Report conversation modes.
- Orchestrator, Learning, Life, Finance, and Summary agents with explicit read/write permissions.
- Persisted, user-visible agent routing and contribution summaries.
- Persisted conversation threads, messages, proposed actions, and decisions.
- Local Qwen chat through `llama-server`, started only when needed.
- Local private-note capture, overlapping chunking, Qwen embeddings, `sqlite-vec` search, retrieved
  context, and visible source provenance.
- Selected Markdown, text-based PDF, or Word `.docx` import with bounded local extraction before
  chunking and indexing; unsupported formats receive an immediate error.
- Separate checkpointed KnowledgeState topic flow: check local vectors first, then fetch and filter
  a short attributed Wikipedia introduction only on no match or explicit web request; propose three
  organizational import choices and index it only after the user confirms one.
- Honest empty/offline state when the local service is not running; no simulated agent answers.
- Navigable Learning, Life, Money, Library, and Goals sections.
- Today management overview with an explicit daily summary and active-plan status.
- Recorded-day month calendar, selected-day schedule, and past-month browsing.
- Integrated Plans desk for materially distinct same-date alternatives and reviewed replacement.
- Learn, Life (including Rest), and Money schedule ledgers drawn from the same active day as Calendar.
- User-owned goals and timed daily records with domain, goal link, recurrence, fixed/flexible and
  important-to-keep flags; explicit progress reporting across Today, Calendar, and domain areas.
- An empty first run that asks for actual records, followed by an explicit Orchestrator plan proposal.
- Read-only past records and non-today plans; future user/agent commitments can be prepared now,
  while outcomes and confirmation wait until that date becomes today.
- Recomputable, persisted Summary-agent day, week, and month reports with explicit feedback evidence.
- Persisted soft/strong Summary suggestion pool filtered by period and domain. Discarding the same
  normalized idea stops its dispatch across periods; repeats are notices only. Week/domain clearing
  requires exact typed confirmation and retains a noncontent marker against regeneration.
- Prior repeated requests to shorten a named task inform later proposals; beneficial protected tasks
  may be shortened but never silently removed. The current-week Summary can preset the next
  occurrence of an important recurring task after at least two explicit Done days; it carries
  recorded-outcome evidence and stays editable.
- Area state sheets now manage Learning subject difficulty and reported sessions; Life daily
  sleep/energy/mood, habits, and categorized timed events; and manual Money account balance,
  transactions, and category budgets. A timed Life event atomically owns a daily Calendar item;
  unscheduled domain facts appear in the Summary, not as invented timed commitments. Bounded domain
  agents read only their matching area state.

### Next product slice — designed, not yet implemented

- Native macOS/Tauri packaging and supervised Python sidecar lifecycle.
- Complete, tested push-to-talk transcription with the existing Core ML Whisper package; browser
  capture and a local short-WAV endpoint exist, while a compatible CLI install/load check remains.
- User-controlled folder import, scanned-document OCR, and additional file formats for the library.
- Learning mastery/review/resource workflows, richer Life routines, Money category/account tools,
  and edit/regenerate saved day plans rather than only the user-owned daily-item record.
- Backup, export, delete, and retention controls in Settings.
- Rich qualitative weekly reflection, aggregation across all domain records and indexed source
  contents, and semantic similarity for paraphrased suggestions.

### Deferred until the local core is proven

- Broader web/MCP providers beyond conditional public-topic acquisition.
- Finance-provider connections and market data.
- Multi-account support and household collaboration.
- Proactive background prompts and long-horizon recommendations (no autonomous background daemon).
- Similarity-driven proactive suggestions.

## 5. Information architecture

| Section | Purpose | First-slice behavior |
|---|---|---|
| Today | Management overview, goals, daily records, current plan, and Summary-agent report | Actionable control desk |
| Calendar | Browse retained months/days, plans, owned records, and period reports | Past read-only; future commitments editable |
| Plans | Compare available same-date alternatives, confirm, or explicitly replace | One integrated decision desk |
| Learn | Learning records, goal links, and applied plan items | Synchronized area ledger |
| Life | Life and Rest records, goal links, and applied plan items | Synchronized area ledger |
| Money | Money daily records and applied plan items | Finance transactions pending |
| Library | Saved material and retrieved evidence | Private note capture, index totals, and retrieved-source labels |
| Goals | Durable directions and linked daily-item progress | Create, rename, pause, complete |

Conversation is a drawer available from every section. It is not a separate destination because it
acts on the current workbench context.

## 6. Visual direction

The approved direction is an **editorial day folio** inspired by physical planners, filing tabs,
margin annotations, ledger rules, and typographic publishing. The visual reference is
[design-reference.png](design-reference.png).

### Composition

- A narrow paper-tab rail creates the primary navigation.
- Today is a calm warm-paper control desk with summary and next steps, not a full plan review.
- Calendar uses a ruled month sheet and selected-day ledger; empty past days remain empty.
- Plans pairs the warm-paper alternative schedule with a dark aubergine review sheet for tradeoffs,
  constraints, and commitment only in that destination.
- A clipped suggestion card sits at the bottom of the folio.
- Conversation slides in as a paper work layer rather than replacing the plan.

### Visual vocabulary

- Warm ivory paper, graphite ink, and aubergine form the base.
- Learning uses vermilion, Life uses cobalt, Finance uses green, and Rest uses neutral graphite.
- Condensed display typography carries dates and field names.
- Serif typography is reserved for reflection, explanation, and conversation.
- Monospaced typography carries operational details and reinforces the ledger metaphor.
- Square controls, fine rules, paper depth, and restrained shadows replace generic rounded cards.

### Responsive behavior

- Desktop: indexed rail and one destination at a time; only Plans pairs folio and review sheet.
- Medium window: calendar/detail and overview columns stack; Plans review follows its schedule.
- Mobile: all eight destinations remain visible in a two-row bottom rail and each destination stacks.

## 7. Core flows

### 7.1 Review and confirm today

1. On first run, set goals and record actual timed commitments/tasks for today; no sample day is
   automatically created. Recurring owned items from prior days are eligible when proposing today.
2. Ask the Orchestrator to propose; its bounded domain/summary route is retained with the saved
   alternatives. Open the single Plans desk to compare schedule, allocation, notes, and constraints.
3. Compare the materially distinct variants for that same date. One to three may be offered when
   fixed times or short blocks make a variation impossible; no agent invents user commitments.
4. Select one variant and confirm it. Today, Calendar, and area ledgers now show that variant.
5. To change an already confirmed day, preview another variant, review the named replacement, and
   explicitly approve it; a normal confirmation request without replacement approval is rejected.
   Completion reports stay with the original alternative and may differ on the new current plan.

### 7.1a Browse a day and its areas

1. Open Calendar and move to a past or future month.
2. Read the month’s recorded/confirmed/completed totals, then select a date. Existing recorded days
   show a day summary and schedule; an unrecorded day stays empty and is never backfilled with a
   sample plan merely because it was viewed.
3. Open Learn, Life, or Money for the same selected date. They show the owned daily records and
   items from the confirmed plan (or an unconfirmed draft, labelled as such); Rest belongs under Life.
4. Past dates are read-only. Future commitments may be preset by the user or added by agents from
   Summary evidence, each with origin. Their outcomes/plans cannot be confirmed early; the items
   are considered when the date becomes today. Ask why an agent item appeared or request a change.
5. Library sources and unscheduled Notes are not calendar items unless a plan item explicitly
   schedules work involving them.

### 7.2 Ask about the plan

1. Open “Ask Wellspent.”
2. Enter a question.
3. The Orchestrator routes the request to the relevant bounded domain agents.
4. Their structured assessments are synthesized through the shared local model.
5. The answer and agent route are saved to the active conversation thread.
6. No plan state changes.

### 7.3 Adjust through conversation

1. Open “Mark up the plan” or choose Adjust.
2. Describe the desired change.
3. Learning and Life assess the tradeoff; Finance joins when the request affects money.
4. Summary combines cross-domain findings without overriding them.
5. The Orchestrator selects a deterministic valid candidate and explains the tradeoff through the
   shared local model.
6. Wellspent records a `proposed_action` with a visible preview and agent route.
7. When a plan is already confirmed, the preview names both the current and proposed variants.
   The action records the reviewed current variant; a stale or unreviewed replacement is rejected.
   The user approves the named replacement or dismisses it.
8. Only confirmation applies the structured change and records an `action_confirmation`.

### 7.4 Report progress

1. Confirm the day’s plan, then report progress on an owned daily item or current schedule row.
2. Choose Done, Partial, Skipped, or Planned.
3. The exact state is persisted.
4. A later reflection may use the report; elapsed time never marks completion automatically.

## 8. Conversation contract

### Modes

| Mode | May do | Must not do silently |
|---|---|---|
| Ask | Explain, compare, retrieve, clarify | Change records |
| Adjust | Produce a structured proposal and rationale | Apply the proposal |
| Report | Help the user reflect and locate status controls | Infer completion |

### Persistence

- `conversation_threads` groups a continuing planning context.
- `conversation_messages` stores the user and assistant turns with mode and model provenance.
- `proposed_actions` stores an action type, structured payload, explanation, and status.
- `action_confirmations` records the user’s explicit decision.
- `agent_runs` records the ordered agents, phase, bounded read/write scopes, and contribution summary
  associated with an assistant message.
- `preferences` may store a durable preference only with provenance back to the message that created
  it.

Raw conversation text is not automatically embedded or treated as memory. Retrieval indexes should
contain selected notes or structured records rather than indiscriminate chat history.

## 9. Multi-agent and planning policy

### Non-negotiable architecture

Wellspent is not a single-agent wrapper. Its agents are logical, permission-bounded participants
that share one model runtime rather than separate model copies. Their collaboration is explicit,
ordered, persisted, and visible to the user.

| Agent | Reads | Writes | Plan authority |
|---|---|---|---|
| Orchestrator | All bounded domain assessments | Plan proposals and suggestion dispatch | Sole proposer |
| Learning | Learning entries, selected plan, related constraints | Learning assessment | None |
| Life | Life/rest entries, energy notes, fixed commitments | Life assessment | None |
| Finance | Finance entries, selected plan, financial constraints | Finance assessment | None |
| Summary | Domain assessments and reported completion | Summary assessment and suggestion draft | None |

### Coordination model

1. Orchestrator classifies the request and records a dispatch step.
2. Relevant domain agents independently read only their declared state slices.
3. Summary joins when more than one domain contributes or the user is reporting progress.
4. Orchestrator synthesizes the bounded reports and may create a typed proposal.
5. The route is persisted with the assistant message and shown in the conversation drawer.
6. No agent directly applies a plan, completion state, preference, or financial record.

### Retrieval-augmented generation

RAG is local infrastructure used by the Orchestrator; it is not a sixth agent and has no authority
to mutate a plan.

1. User-controlled Library text is normalized and split into 180-word chunks with a 30-word overlap.
2. The separate Qwen3 Embedding 0.6B runtime converts every chunk into a normalized
   1,024-dimensional vector.
3. `sqlite-vec` stores those vectors in the same SQLite file as source metadata and chunk text.
4. On a question, the embedding runtime creates an instruction-aware vector for the original query.
5. `sqlite-vec` finds the nearest chunks; Wellspent retains their rank, distance, and source.
   A distance threshold rejects unrelated results instead of treating the nearest item as relevant
   by default.
6. The conversation model receives the original question, structured day state, bounded agent
   assessments, and retrieved text passages. It does not receive the raw vector arrays.
7. The answer shows private or attributed public sources used, including the latter's URL/license.
   Retrieved content is evidence, never an instruction.

The day-proposal path uses LangGraph PlatformState nodes with SQLite checkpoints. Knowledge-topic
acquisition uses a separately checkpointed KnowledgeState graph whose conditional branch runs only
after a local relevance check. Conversation routing remains a bounded Python pipeline with durable
agent runs; complete graph coverage and checkpoint retention controls are not yet implemented.

### Code responsibilities

- Compute date/time arithmetic and recurrence.
- Detect schedule collisions and invalid duration.
- Preserve fixed commitments.
- Store currency as integer minor units plus an ISO currency code.
- Calculate balances and plan summaries.
- Enforce one confirmation per date.
- Make writes transactional and idempotent where retries are possible.

### Model responsibilities

- Interpret natural-language intent.
- Explain tradeoffs in plain language.
- Propose priorities or alternatives.
- Summarize selected context.
- Ask for missing information when a safe proposal cannot be formed.

The model never performs financial arithmetic, invents completion, mutates SQLite directly, or
chooses a network tool without an explicit product path and disclosure.

In this slice, domain agents calculate their bounded assessments deterministically from structured
state. The Orchestrator alone uses Qwen to turn those reports into natural-language synthesis. A
future domain model call must still use the same agent permissions and shared runtime; it does not
gain additional write authority.

## 10. Architecture

```text
React workbench
    │ relative /api requests
    ▼
FastAPI local service (127.0.0.1)
    ├── deterministic planner and validators
    ├── SQLite repository and transactions
    │      └── sqlite-vec (1,024-dimensional local vector index)
    ├── RAG service
    │      ├── chunker and source provenance
    │      └── EmbeddingGateway
    │             └── embedding-only llama-server
    │                    └── shared Qwen3 Embedding 0.6B GGUF
    ├── multi-agent core
    │      Orchestrator
    │        ├── Learning
    │        ├── Life
    │        ├── Finance
    │        └── Summary
    ├── conversation/action and confirmation policy
    └── ModelGateway
           └── llama-server (dynamic loopback port + per-launch token)
                   └── shared Qwen GGUF model
```

### State ownership

| State | Owner | Notes |
|---|---|---|
| Plans, entries, decisions, finance, preferences | SQLite | Authoritative durable state |
| Agent dispatch, assessments, and synthesis | `agent_runs` | Persisted execution trace linked to conversation |
| Knowledge sources, chunks, retrieval matches | SQLite | Authoritative text and answer provenance |
| Embedding vectors | `sqlite-vec` in the same database | Rebuildable index derived from source chunks |
| Current form, drawer, menu, selected preview | React | Ephemeral presentation state |
| Model process, port, auth token | ModelGateway | Per-launch runtime state |
| Day-proposal and KnowledgeState checkpoints | LangGraph SQLite saver in a separate `wellspent.checkpoints.sqlite3` file | Execution snapshots only, never primary business state or vector-index writes |

LangGraph is active for day proposals and conditional knowledge topics. The domain record is still
authoritative in SQLite; checkpoint rows record execution progress, not a second confirmed plan.
Writes are guarded by the database's day/plan constraints; later resumable flows need explicit
idempotency keys, replay-safe nodes, and a user-visible checkpoint retention policy.

## 11. Local models

Wellspent uses the shared AI-Models library in the Mac’s Documents folder rather than keeping model
copies inside the project.

| Capability | Library-relative path | First-slice status |
|---|---|---|
| Chat | `gguf/Qwen3-4B-Q4_K_M.gguf` | Connected through installed `llama-server` |
| Embeddings | `gguf/Qwen3-Embedding-0.6B-Q8_0.gguf` | Connected through a separate embedding-only `llama-server` |
| Voice transcription | `whisper/faster-whisper-small/` | Browser PCM capture and local `faster-whisper` adapter; converted weights sit beside the preserved Core ML package |

One shared chat process receives the Orchestrator prompt plus the routed agents’ permission-bounded
reports and retrieved passages. A smaller, separate embedding process indexes passages and embeds
questions because generation and retrieval require different model outputs. Wellspent does not load
a separate 2.5 GB chat-model copy for each logical agent.

### ModelGateway contract

The gateway exposes these conceptual operations:

- `health` — disclose binary, model, and process readiness.
- `chat` — send structured context and receive a bounded response.
- `embed_documents` and `embed_query` — handled by the separate embedding gateway.
- `transcribe` — reserved for the native Whisper adapter.
- `cancel` — end a pending generation.
- `stream` — reserved for incremental desktop responses.

Each implemented gateway starts `llama-server` on an operating-system-selected loopback port,
uses a random per-launch token, disables its web UI, enables offline mode, and selects the CPU-safe
backend so restricted hosts do not fail when Metal is unavailable. The service stops the child
processes during graceful shutdown and escalates to a kill only when one does not exit promptly.

## 12. Data model

### Implemented tables

| Table | Role |
|---|---|
| `plan_sets` | One generation event per date |
| `plan_variants` | Named, versioned alternatives with rationale and supersession support |
| `plan_entries` | Ordered schedule blocks and explicit completion status |
| `daily_confirmations` | Exactly one confirmed variant per date |
| `conversation_threads` | Durable conversation containers |
| `conversation_messages` | Turns with role, mode, time, and model provenance |
| `proposed_actions` | Structured, unapplied mutations |
| `action_confirmations` | Explicit confirm/dismiss decision |
| `preferences` | Durable values with message provenance |
| `suggestions` | Keep/dismiss lifecycle |
| `suggestion_pool` | Summary-period advice with domain, soft/strong priority, active/discarded status, and exact normalized matching key |
| `suggestion_notices` | Later repeats of previously discarded normalized ideas, never dispatched as active |
| `cleared_suggestion_periods` | Noncontent week/domain markers to prevent hard-cleared advice from silently regenerating |
| `finance_entries` | Integer minor units plus currency code |
| `agent_runs` | Ordered dispatch, assessment, summary, and synthesis trace with permission scopes |
| `knowledge_sources` | User-controlled note/document identity, type, and content hash |
| `knowledge_chunks` | Normalized chunk text and source position |
| `knowledge_chunk_vectors` | `sqlite-vec` virtual table containing 1,024-dimensional embeddings |
| `knowledge_acquisitions` | Locally staged public introduction, filtering receipt, and chosen import/source identity |
| `knowledge_import_plans` | Three alternative organization-scheme labels tied to one acquisition; exactly one confirmed import |
| `retrieval_matches` | Ranked source/chunk snapshots retained with an assistant response, even if the live source is later revised |
| `goals` | Durable user-authored direction, area, and active/paused/completed status |
| `daily_items` | Dated user/agent-origin records, goal links, explicit outcome, recurrence, constraints, evidence, and important-to-keep flag |
| `learning_items`, `learning_sessions` | Learning subjects with difficulty/estimate/lifecycle and explicitly reported dated effort/results |
| `life_habits`, `life_habit_logs`, `life_daily` | Habit definitions and dated outcomes plus sleep, energy, mood, and reflection |
| `life_events` | Category metadata attached one-to-one to a timed Life daily item shared with Calendar |
| `finance_account`, `finance_transactions`, `finance_budgets` | Manual opening balance, dated income/expense in integer cents, and category budgets by month |
| `feedback_signals` | Explicit named-task shortening requests linked to their conversation message |
| `summary_reports` | Persisted day/week/month evidence and advice, recomputed on request |
| `plan_generation_routes` | Orchestrator/domain/Summary proposal trace separate from confirmation |

### Future domain detail

- Learning: resources, practice attempts, review scheduling, and mastery evidence beyond the
  implemented subject/session records.
- Life: richer routines and event lifecycle beyond the implemented habits, daily check-ins, and
  timed events.
- Finance: multiple accounts, governed categories and review periods beyond the implemented
  manual single balance, transactions, and budgets.
- Knowledge: file import metadata, parsing status, and retention controls.

Past records are read-only. Today and future commitments are editable, but future completion and
plan confirmation are not. Agent-origin future records are added directly when Summary evidence
warrants them, not placed in an approval queue; source and evidence stay visible. A user may ask
why or request a change. This permission does not waive present-day plan confirmation. Separately
auditable past correction remains a later capability.

## 13. Local API

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/health` | Service and model readiness |
| GET | `/api/agents` | Public agent roles and permission contract |
| GET | `/api/bootstrap` | Goals, owned records, plan snapshot/variants, constraints, and messages; default never generates an example |
| GET | `/api/calendar` | User-recorded days, saved plans, and current confirmed-plan progress for one `YYYY-MM` month |
| GET | `/api/summaries` | Day, ISO week, and month Summary-agent evidence/advice plus the persisted area-filterable suggestion pool |
| POST/PUT | `/api/goals`, `/api/goals/{id}` | Create/rename and change goal status |
| POST/PUT | `/api/daily-items`, `/api/daily-items/{id}` | Record/edit today or future items; only today may report outcomes |
| GET | `/api/areas/{learning|life|finance}` | Read selected-date domain state independently of the shared day plan |
| POST/PATCH | `/api/learning/items`, `/api/learning/items/{id}` | Manage subject difficulty/estimate and lifecycle |
| POST | `/api/learning/sessions` | Report today's explicit subject effort and result |
| POST/PATCH/PUT | `/api/life/habits`, `/api/life/habits/{id}`, `/api/life/habits/{id}/logs/{date}` | Manage habits and explicitly report today's outcome |
| PUT | `/api/life/daily/{date}` | Save today's reported sleep, energy, mood, and reflection |
| POST | `/api/life/events` | Add a categorized today/future timed event and Calendar item atomically |
| PUT/POST | `/api/money/opening-balance`, `/api/money/transactions`, `/api/money/budgets` | Manage a local manual balance, today's entries in cents, and current/future monthly budgets |
| POST | `/api/plan/generate` | Orchestrator asks bounded agents and proposes retained alternatives from user-owned items |
| GET | `/api/knowledge` | Indexed source inventory and local RAG readiness |
| POST | `/api/knowledge/sources` | Chunk, embed, and index user-supplied private text |
| POST | `/api/knowledge/import` | Accept a bounded user-selected local Markdown/PDF/Word file, extract text, chunk/embed/index, and discard the original bytes |
| POST | `/api/knowledge/search` | Retrieve nearest private chunks for a question |
| POST | `/api/knowledge/topic` | Check local semantic relevance; conditionally fetch/filter a public introduction and stage three choices without indexing, with personal-topic guard |
| GET | `/api/knowledge/import-plans` | Revisit pending fetched topics and import choices |
| POST | `/api/knowledge/import-plans/{id}/confirm` | Confirm exactly one choice, then chunk/embed/index attributed public text |
| POST | `/api/voice/transcribe` | Accept a short user-initiated mono 16-bit PCM WAV and return editable local transcription text when the converted Whisper model is available |
| POST | `/api/plan/confirm` | Confirm one variant; a different current plan needs explicit `replaceExisting=true` approval |
| PATCH | `/api/entries/{id}` | Report Planned, Done, Partial, or Skipped on the confirmed variant only |
| POST | `/api/suggestions/{id}` | Keep or dismiss a suggestion |
| POST | `/api/suggestion-pool/{id}/discard` | Suppress a matching idea across periods and future agent dispatch |
| POST | `/api/suggestion-pool/clear-week` | Irreversibly clear an exact week and domain with typed target confirmation |
| POST | `/api/chat` | Ask, Adjust, or Report |
| POST | `/api/actions/{id}` | Confirm or dismiss a proposed action |
| POST | `/api/model/start` | Start the private local chat runtime |
| POST | `/api/model/stop` | Stop the chat runtime |

## 14. Security and privacy

“Local-first” describes data flow, not automatic encryption.

### Required guarantees

- Bind local services to loopback only.
- Use a per-launch token between the application service and model runtime.
- Keep model files read-only from the product’s point of view.
- Keep the SQLite database and model logs out of version control.
- Never put credentials, private records, or raw user content in runtime logs.
- Provide future export, backup, retention, and delete controls before production release.
- Use platform key storage for any future connector secret.
- Treat imported documents and web results as untrusted content, not instructions.
- Never place raw embedding vectors in a chat prompt or runtime log.
- Send only a sanitized topic to a web tool unless the user explicitly opts into sharing more.
- Show when a response used a local model, deterministic rules, or an external source.

### Desktop packaging requirements

The production Tauri wrapper must package a target-specific service binary, supervise startup and
shutdown, discover ports without collision, deliver an application API token out of band, expose
readiness, support cancellation/streaming, clean orphaned processes, and show a recoverable missing-
model state. These are release requirements; the current browser-hosted local slice is not presented
as a packaged desktop release.

## 15. Accessibility

- All navigation and actions use semantic buttons.
- Color is paired with text labels and position; it is not the only domain indicator.
- Keyboard focus is visible.
- The conversation drawer has dialog semantics and a labelled close action.
- Status controls expose the task title in their accessible name.
- The layout preserves a 320-pixel minimum and supports a stacked small-screen mode.
- Reduced-motion preference removes meaningful transition duration.
- Final desktop release requires keyboard traversal, screen-reader, zoom, and contrast checks.

## 16. Failure and recovery behavior

- Without the FastAPI service, the interface opens in clearly labelled preview mode.
- Without the model runtime, deterministic planning remains usable and chat explains the limitation.
- Without the embedding runtime, stored sources remain intact and the answer discloses that private
  knowledge retrieval was unavailable.
- A failed model request leaves the plan unchanged.
- A proposed action remains pending until one explicit decision.
- Retried confirmation of the same variant is idempotent. A different variant is refused unless the
  user has explicitly reviewed and approved replacement; a Talk action also checks the reviewed
  current variant at decision time. No duplicate date rows are created.
- SQLite transactions roll back partial writes.
- Service shutdown stops the child model process.

## 17. Acceptance criteria for the first slice

- The app renders the approved folio layout at desktop width and remains usable at small widths.
- Every primary tab is navigable.
- A genuine first run stays empty until goals or dated user-owned items are recorded; explicit
  generation produces only materially distinct alternatives, potentially fewer than three.
- No generated variant contains overlapping schedule entries.
- One variant can be confirmed and retrieved as the confirmed plan for that date.
- A past unrecorded date can be viewed without generating a fictitious plan.
- Calendar can move between months, show a selected-day summary, and use the confirmed variant’s
  completion count. It also shows simple operational totals for recorded days in the selected
  month; long-horizon trend analysis remains deferred.
- Today, Calendar, Plans, Goals, and Learn/Life/Money show the same owned records and current
  confirmed variant; variant previews remain in Plans until confirmed.
- Past plans are retained read-only, calendar history is not fabricated, and day/week/month
  Summary-agent reports describe explicit outcomes and repeated task-adjustment evidence.
- A second direct plan confirmation is rejected until a named replacement is explicitly approved.
- A schedule entry can be set to Done, Partial, Skipped, or Planned.
- Suggestions can be kept or dismissed.
- Ask mode answers without mutating the plan.
- Adjust mode creates a proposal that changes nothing until confirmation.
- Cross-domain requests route through the relevant agents and persist the complete route.
- Only the Orchestrator is permitted to produce a plan proposal.
- The existing shared Qwen file can answer one local request through the installed runtime.
- A Library note can be chunked and indexed by the existing embedding model.
- A question retrieves the semantically closest private chunk, persists its provenance, and shows
  its source beside the answer.
- Build, API tests, Sites contract tests, interaction checks, and design comparison must pass before
  a verified-delivery claim; writing source does not itself establish those results.

## 18. Delivery stages

1. **Multi-agent RAG vertical slice:** prove bounded domain collaboration, visible routing, local
   persistence, explicit confirmation, knowledge indexing, semantic retrieval, and local conversation.
2. **Daily-life management:** add owned goals/dated records, record-based alternatives, read-only
   calendar history, period summaries, and explicit preference evidence; source implementation is
   present, with checks and user-facing QA pending.
3. **Deeper personal data:** complete domain forms, suggestion-pool history, explicit correction,
   backup/export/delete, and retention; summaries must use all authorized relevant records, not
   merely plan labels. Use on-demand startup/catch-up, not autonomous background mutation.
4. **Native app:** package Tauri and the supervised service; add local Whisper transcription.
5. **Expanded recall:** add file parsing, folder import, re-index controls, and retention settings.
6. **Optional reach:** add disclosed, narrowly scoped web and finance connectors.

The next stage begins only after the preceding stage is usable and its data boundaries are explicit.

## 19. Original design contract and fidelity ledger

The retained [original 767-line product design](Original%20Product%20Design.md) remains the
product-level source for component relationships. This specification is an implementation ledger,
not permission to discard original requirements. Where an earlier slice described sample plans,
past-date correction, or editable future events, the user's later explicit decisions govern: no
automatic sample for a new user; saved past plans are read-only; only today's plan is applied.

| Original contract | Present slice | Still required before the full platform claim |
|---|---|---|
| Structured state and local SQLite authority; plan differs from execution | Goals, dated items, domain subject/session/habit/daily/event/transaction/budget state, plan/outcome snapshots and reports in SQLite; checkpointed PlatformState graph for day proposals | Graph coverage for every interaction, startup/catch-up and full domain lifecycle/mastery tools |
| Permission-bounded Orchestrator, Learning, Life, Finance, Summary | Visible bounded routing with selected-date area facts restricted to matching domain assessments, Orchestrator-only proposal and explicit approval; a separate conditional KnowledgeState graph | Conversation graph coverage, evaluable agent decisions and richer domain tools |
| User input and local knowledge acquisition | Timed records, pasted notes, and selected Markdown/PDF/Word files; local chunk/embedding/`sqlite-vec` retrieval; conditional topic-only attributed encyclopedia fetch, ordered filtering receipt, three staged organization schemes and one explicit import choice before indexing | Folder import, scanned-document OCR, real multi-source credibility/timeliness comparison, verified passage classification, similarity checks, revision lifecycle and broader providers |
| Several valid plans and conversational adjustment | Record-based variants, proposal/decision trail, explicit replacement | In-place task-level replan/versioning with complete constraint evaluation |
| Strong soft suggestions and persistent suggestion pool | Soft/strong Summary advice saved by day/week/month and domain; active ideas reach bounded agents, one gentler variation can reflect timing advice; discard suppresses exact normalized repeats, later repeats notify only; typed week/domain hard clear keeps a noncontent tombstone | Semantic similarity for paraphrases, user-owned priority editing, broader provenance and proactive but approved knowledge intake |
| Daily workbench, calendar and retained history | Today management, integrated Plans, month/day browsing, read-only past, advance user/agent future intake with origin, owned area ledgers | Full timeline and governed past correction |
| Summary as all-available-context memory for later plans | On-demand day/week/month reports summarize goals, plan outcomes, Learning sessions, Life check-ins/habit notes, manual Money transaction and budget figures, protected recurring done-day evidence, source count, and exact named-task shortening requests; active and prior Summary advice can influence a later gentle area block | Incorporate authorized Library source content, mastery/finance history, richer qualitative cross-period preferences and fully inspectable summary-to-planner provenance |
| Local-only desktop and voice conversation | Loopback browser/service, shared Qwen chat+separate embedding model, visible Talk entry, short-WAV push-to-talk, installed local `faster-whisper` runtime, and verified converted Whisper-small transcription | Tauri sidecar lifecycle, backup/export/delete and broader privacy validation |

Public acquisition for a user-entered topic is conditional: check local `sqlite-vec` relevance
first; fetch public sources only without a local match or on an explicit web request. Never place
private documents or personal health, finance, identity, or contact details in an automatic query.
Web sources carry URL/provenance and do not silently change a present-day plan. Voice is
push-to-talk, never always-listening.
Fetched public text stays locally pending until one classification-organization choice is
confirmed; no vector is created by fetch alone. The three schemes currently name intended labels,
not verified passage-level assignments; full classification remains an agent capability to build.

Repeated requests are not inferred from mere time elapsed or a model's guess: the named task and
request text are retained with message provenance. When an important-to-keep task is disliked, a
later variant may reduce its flexible duration but keeps it scheduled; the Summary agent explains
that tradeoff to the user. The current rule recognizes explicit shortening words and a full stored
task title, not paraphrased dislikes. The full memory loop must later account for all user-approved
signals, including rejections and conversations, with inspectable correction controls.
Conversely, the current-week report can prepare the next occurrence of a protected recurring task
after two distinct recorded Done days. It keeps the existing duration and an outcome citation,
unless repeated explicit shortening feedback calls for a smaller but still scheduled block.
