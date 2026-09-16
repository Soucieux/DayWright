# Self Learning & Life Management Platform — Design Document

**Version:** 1.0  
**Status:** Final  
**Scope:** Single-user, local-first, multi-agent personal management platform

---

**End of Document**
## 1. Overview

### 1.1 Goal

Build a **self learning and life management platform** for personal use. The platform manages three domains — **Learning, Life, Finance** — using multiple collaborative agents. It is **state-centric**, not chat-centric, and runs **entirely locally** except for optional web knowledge acquisition.

### 1.2 Core Definition

> A single-user, local-first personal management platform that tracks learning, life, and finance states, uses multiple agents to generate balanced plans and recommendations, and visualizes everything in a desktop workspace.

### 1.3 What It Is Not

- Not a chatbot
- Not a simple to-do list
- Not a cloud SaaS
- Not a single-agent wrapper

---

## 2. Design Principles

| Principle | Meaning |
|---|---|
| State-centric | State drives orchestration, not the reverse |
| Local-first | All runtime data and models are local |
| Non-chat-first | Workbench UI, chat only as optional input |
| Central dispatch | Only the Orchestrator Agent schedules; sub-agents never call each other |
| Shared state coordination | Agents coordinate through LangGraph State, not direct calls |
| User confirmation | Plans are proposed, not auto-applied |
| Plan ≠ Execution | The platform never assumes a plan was executed without user feedback |
| Strong soft suggestions | Suggestions are references, not hard constraints, but carry strong weight |
| User control | Users can discard, reset, and configure suggestions |

---

## 3. System Architecture

### 3.1 High-Level Diagram

```
┌─────────────────────────────────────────────┐
│         Local Client (Tauri + React)        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐        │
│  │ Domain  │ │ Today   │ │ Pending │        │
│  │ Cards   │ │ Timeline│ │ Plans   │        │
│  └─────────┘ └─────────┘ └─────────┘        │
│  ┌─────────────────────────────────────┐     │
│  │ Feedback │ Month View │ Suggestions │     │
│  └─────────────────────────────────────┘     │
└──────────────────┬──────────────────────────┘
                   │ HTTP / WebSocket
┌──────────────────▼──────────────────────────┐
│      Local Core Service (Python + FastAPI)   │
│  ┌──────────────────────────────────────┐    │
│  │       LangGraph Main Graph           │    │
│  │  ┌────────────────────────────┐      │    │
│  │  │   Orchestrator Agent       │      │    │
│  │  └──┬────────┬────────┬───────┘      │    │
│  │     │        │        │              │    │
│  │  ┌──▼──┐ ┌───▼──┐ ┌───▼───┐          │    │
│  │  │Learn│ │ Life │ │Finance│          │    │
│  │  └─────┘ └──────┘ └───────┘          │    │
│  │  ┌────────────────────────────┐      │    │
│  │  │   Summary Agent            │      │    │
│  │  └────────────────────────────┘      │    │
│  └──────────────────────────────────────┘    │
│  ┌──────────────────────────────────────┐    │
│  │   Knowledge Acquisition Subgraph     │    │
│  │   Retrieve → Filter → Classify →    │    │
│  │   Propose Plans                     │    │
│  └──────────────────────────────────────┘    │
│  ┌──────────────┐  ┌───────────────────┐    │
│  │  RAG Layer   │  │  MCP Host/Client  │    │
│  │  sqlite-vec  │  │  langchain.mcp    │    │
│  └──────────────┘  └────────┬──────────┘    │
└─────────────────────────────┼───────────────┘
                              │ MCP
                    ┌─────────▼─────────┐
                    │  free-search-mcp  │
                    │  (project venv)   │
                    └───────────────────┘

┌─────────────────────────────────────────────┐
│                  SQLite                      │
│  · 16 business tables                        │
│  · sqlite-vec virtual tables                 │
│  · LangGraph checkpoints                     │
└─────────────────────────────────────────────┘
```

### 3.2 Layer Responsibilities

| Layer | Responsibility |
|---|---|
| Client | Visualization, confirmation, feedback, suggestion management |
| Core Service | Agent orchestration, state management, RAG, MCP client |
| State | LangGraph State (in-memory) + SQLite (persistent) |
| RAG | Slicing, embedding, retrieval, similarity detection |
| MCP | External tool integration via MCP protocol |

### 3.3 Deployment Model

- **Single machine, single user.**
- Client starts → Core Service starts → MCP Server starts.
- Client exits → Core Service exits → MCP Server exits.
- **No background daemon.**
- Automatic triggers are handled by **startup check-and-catch-up**.

---

## 4. Agent Design

### 4.1 Agent Roles

| Agent | Responsibility | Independence |
|---|---|---|
| Orchestrator | Sole scheduler; reads all state; dispatches suggestions; resolves conflicts; routes problems | Central |
| Learning Agent | Learning state, difficulty/effort estimation, review needs | Independent |
| Life Agent | Sleep, exercise, rest, overwork detection | Independent |
| Finance Agent | Budget, spending, alerts, constraint reports | Independent |
| Summary Agent | Structured weekly/daily/monthly suggestion report by domain | Independent |
| Knowledge Subgraph | Retrieve, filter, classify, propose import plans | Called by Orchestrator |

### 4.2 Coordination Model

- Sub-agents **never call each other directly**.
- All coordination happens through **LangGraph shared State**.
- The Orchestrator is the **only** agent that writes plans and dispatches suggestions.
- Sub-agents write only their own domain state.
- Sub-agents may read other domains' state if needed.

### 4.3 Agent Permissions

| Agent | Write | Read |
|---|---|---|
| Orchestrator | Plans, suggestion dispatch | All |
| Learning | Learning state | Learning + related suggestions + plans |
| Life | Life state | Life + related suggestions + plans |
| Finance | Finance state | Finance + related suggestions + plans |
| Summary | Suggestion pool | All (read-only for state) |

---

## 5. State Management

### 5.1 LangGraph State

The main graph and knowledge subgraph each have their own state schema.

**Main Graph State (PlatformState):**

```python
class PlatformState(TypedDict):
    session_id: str
    user_input: str
    messages: list
    current_date: str
    today_plan: dict
    pending_plans: list
    active_suggestions: dict          # {domain: [suggestion_id]}
    learning_snapshot: dict
    life_snapshot: dict
    finance_snapshot: dict
    knowledge_task_id: str | None
    next_agent: str
    needs_confirmation: bool
    user_feedback: dict
```

**Knowledge Subgraph State (KnowledgeState):**

```python
class KnowledgeState(TypedDict):
    topic: str
    source_mode: str                  # web / local
    candidates: list
    filtered: list
    classification_schemes: list
    proposed_plans: list
    selected_plan: dict | None
    import_status: str
```

### 5.2 State ↔ SQLite Sync Strategy

**Strategy A — Load on start, write back at key nodes:**

- Client starts → load State from SQLite
- Graph executes → Orchestrator and agents read/write State
- Key nodes → write back to SQLite
- Client exits → State discarded, SQLite persists

**Key write-back nodes:**

- User confirms plan → `daily_plans`, `time_blocks`
- Agent updates domain state → domain tables
- User provides feedback → `feedback_log`
- Summary Agent produces suggestions → `suggestions`, `rag_index`
- User discards suggestion → `suggestions.status`
- User modifies preference → `user_preferences`

---

## 6. Data Model

### 6.1 Database Choice Rationale

SQLite is chosen because:

- Local-first, zero configuration
- Single file, easy backup and export
- `sqlite-vec` provides vector search in the same stack
- No separate server process

### 6.2 MVP Tables (16 business tables + 1 framework table)

**Learning:**

```sql
learning_items(
  id INTEGER PK,
  name TEXT NOT NULL,
  difficulty TEXT,              -- easy / medium / hard
  estimated_minutes INTEGER,
  status TEXT DEFAULT 'active', -- active / done / archived
  created_at TEXT
)

learning_sessions(
  id INTEGER PK,
  item_id INTEGER FK,
  date TEXT,
  minutes INTEGER,
  result TEXT,                  -- done / partial / skipped
  created_at TEXT
)
```

**Life:**

```sql
life_habits(
  id INTEGER PK,
  name TEXT NOT NULL,
  frequency TEXT,               -- daily / weekly
  active INTEGER DEFAULT 1
)

life_habit_logs(
  id INTEGER PK,
  habit_id INTEGER FK,
  date TEXT,
  done INTEGER DEFAULT 0,
  note TEXT
)

life_daily(
  id INTEGER PK,
  date TEXT UNIQUE,
  sleep_hours REAL,
  energy_level INTEGER,         -- 1-5
  mood INTEGER,                 -- 1-5
  note TEXT
)

life_events(
  id INTEGER PK,
  date TEXT,
  start_time TEXT,
  end_time TEXT,
  category TEXT,                -- sport / social / chore / health / other
  name TEXT,
  flexible INTEGER DEFAULT 1    -- 1 adjustable / 0 hard constraint
)
```

**Finance:**

```sql
finance_account(
  id INTEGER PK CHECK(id=1),
  balance REAL DEFAULT 0,
  updated_at TEXT
)

finance_transactions(
  id INTEGER PK,
  date TEXT,
  type TEXT,                    -- income / expense
  amount REAL,
  category TEXT,
  note TEXT
)

finance_budgets(
  id INTEGER PK,
  year_month TEXT,              -- 2026-09
  category TEXT,
  budget_amount REAL,
  UNIQUE(year_month, category)
)
```

**Planning:**

```sql
daily_plans(
  id INTEGER PK,
  date TEXT UNIQUE,
  status TEXT,                  -- draft / pending / confirmed
  confirmed_at TEXT,
  plan_json TEXT,
  created_at TEXT
)

time_blocks(
  id INTEGER PK,
  plan_id INTEGER FK,
  start_time TEXT,              -- 08:00
  end_time TEXT,                -- 08:30
  domain TEXT,                  -- learning / life / finance / rest
  task_ref TEXT,
  task_type TEXT,
  status TEXT DEFAULT 'planned' -- planned / done / skipped
)
```

**Feedback:**

```sql
feedback_log(
  id INTEGER PK,
  date TEXT,
  type TEXT,                    -- modify_request / completion / preference / dissatisfaction
  domain TEXT,
  content TEXT,
  related_plan_id INTEGER,
  created_at TEXT
)
```

**Suggestions:**

```sql
suggestions(
  id INTEGER PK,
  frequency TEXT,               -- day / week / month
  period TEXT,                  -- 2026-W37 / 2026-09-14
  domain TEXT,                  -- learning / life / finance / cross
  content TEXT,
  status TEXT DEFAULT 'active', -- active / discarded
  discarded_at TEXT,
  created_at TEXT
)
```

**Preferences:**

```sql
user_preferences(
  key TEXT PK,
  value TEXT,
  updated_at TEXT
)
```

**RAG:**

```sql
rag_index(
  id INTEGER PK,
  source_type TEXT,             -- suggestion / plan / preference / state / knowledge
  source_id INTEGER,
  content TEXT,
  domain TEXT,
  period TEXT,
  created_at TEXT
)

rag_knowledge(
  id INTEGER PK,
  source_type TEXT,             -- web / local_file
  source_uri TEXT,
  title TEXT,
  content TEXT,
  domain TEXT,
  imported_at TEXT
)
```

**Framework:**

```sql
checkpoints(...)  -- auto-created by langgraph-checkpoint-sqlite
```

---

## 7. Knowledge Acquisition

### 7.1 Workflow

```
User requests a topic
      ↓
Orchestrator determines: knowledge need + web
      ↓
Invoke Knowledge Acquisition Subgraph
      ├─ Retrieve Agent: web search via MCP
      ├─ Filter Agent: credibility → timeliness → other
      ├─ Classify Agent: classify by topic
      └─ Plan Agent: generate 2-3 import plans by classification scheme
      ↓
Plans passed back via LangGraph State
      ↓
User selects plan
      ↓
Confirm → slice → embed → store in RAG
```

### 7.2 Filtering Criteria

| Priority | Criterion |
|---|---|
| 1 | Credibility |
| 2 | Timeliness |
| 3 | Others (difficulty, source, format) — equal weight |

### 7.3 Classification and Plan Generation

Plans differ by **classification scheme**. Example with same material set:

- Plan A: Basic / Advanced / Practical
- Plan B: Theory / Case Study / Exercise
- Plan C: Introduction / Core / Extension

### 7.4 Local Import

- Supported formats: PDF, Markdown, Word
- Unsupported formats → immediate user notification
- User selects file → automatic parse → slice → embed → store
- No secondary confirmation needed

---

## 8. RAG Layer

### 8.1 Purpose and Scope

RAG is a **shared infrastructure layer**, not a standalone agent. It serves:

- Similar suggestion detection
- Historical plan retrieval
- Preference retrieval
- Domain knowledge retrieval

### 8.2 Indexed Content

| Indexed | Not Indexed |
|---|---|
| Summary suggestions | Casual chat |
| Historical plans | Temporary conversations |
| Preferences (explicit/implicit) | Intermediate reasoning |
| Domain state history (aggregated) | Raw logs |
| Knowledge (web/local) | Unconfirmed drafts |

### 8.3 Technology Stack

| Component | Choice |
|---|---|
| Slicing | By suggestion item / by day / by event |
| Embedding | Local bge-small / nomic-embed |
| Vector store | sqlite-vec |
| Similarity threshold | 0.85 (adjustable) |

### 8.4 Similarity Detection

When new suggestions are generated:

1. Embed and query vector store
2. If similarity > threshold and previous suggestion was discarded
3. Notify user: "This suggestion appeared before and was discarded"
4. **No action taken** — notification only

---

## 9. Suggestion System

### 9.1 Strong Soft Suggestions

- **Soft**: Agents may weigh them
- **Strong**: Agents should prioritize them
- **Persistent**: Accumulate, do not auto-expire
- **User-controllable**: View, discard, reset

### 9.2 Suggestion Pool

Summary Agent writes structured suggestions by domain. Orchestrator dispatches to relevant agents. Each agent prioritizes suggestions in its state calculation and planning.

### 9.3 Discard and Reset

- Discarded suggestions are persisted in SQLite
- Orchestrator stops dispatching them
- If a similar suggestion appears later, user is notified only
- Clearing: by week + by domain, **hard delete, irreversible**
- Suggestion management UI: tabs by domain, filter by day/week/month

---

## 10. User Interface

### 10.1 Workbench Layout

```
┌─────────────────────────────────────┐
│  Domain Status Cards                │
│  ┌──────┐ ┌──────┐ ┌──────┐        │
│  │Learn │ │ Life │ │Finance│        │
│  │Progress│ │Status│ │Balance│      │
│  │Alerts│ │Alerts│ │Alerts│        │
│  └──────┘ └──────┘ └──────┘        │
├─────────────────────────────────────┤
│  Today Timeline (30-min blocks)     │
│  08:00 ████ Study                   │
│  08:30 ████ Study                   │
│  09:00 ████ Rest                    │
│  ...                                │
├─────────────────────────────────────┤
│  Pending Plans / Feedback Entry      │
├─────────────────────────────────────┤
│  Weekly Suggestions (Summary Agent)  │
└─────────────────────────────────────┘
```

### 10.2 Interaction Model

- Past and future days are **read-only**; no manual editing
- To change a plan, user requests adjustment → Orchestrator dispatches agent → new plan generated
- User can converse with agents to express preferences
- User selects from multiple proposed plans

### 10.3 Visualization

- Domain status cards (learning progress, life state, finance balance)
- Today timeline (30-min blocks)
- Month view (second version)
- Suggestion management (tabs by domain, filters)

---

## 11. Technology Stack and Rationale

### 11.1 Frontend: Tauri 2 + React

**Chosen because:**

- **Lightweight**: 1/5 to 1/10 the bundle size of Electron
- **Low memory**: 30-50% less than Electron
- **Cross-platform**: macOS, Windows, Linux; mobile in Tauri 2
- **Rich UI ecosystem**: ECharts, Recharts, timeline libraries
- **Future-proof**: React code reusable for web version

**Compared to:**

| Option | Why Not |
|---|---|
| Electron | Heavier, more memory |
| SwiftUI | Apple-only, weaker chart/timeline ecosystem |
| Pure Web | No desktop integration, no offline app feel |

### 11.2 Backend: Python + FastAPI

**Chosen because:**

- **LangGraph ecosystem** is Python-first
- **RAG ecosystem**: sqlite-vec, bge embeddings, PDF/Word parsers
- **Ollama SDK** is most complete in Python

**Compared to:**

| Option | Why Not |
|---|---|
| Node.js | Weaker LangGraph/RAG ecosystem |
| Rust | Steeper learning curve, less mature AI tooling |
| Go | Immature AI/agent libraries |

### 11.3 Orchestration: LangGraph

**Chosen because:**

- **StateGraph** natively supports shared state
- **Checkpointing** persists to SQLite
- **Interrupt** supports user confirmation flows
- **Subgraphs** support independent knowledge acquisition
- **Ecosystem**: LangChain tools, MCP adapters

**Compared to:**

| Option | Why Not |
|---|---|
| AutoGen | More conversation-centric, weaker state management |
| CrewAI | Less flexible for state-driven workflows |
| Custom state machine | More work, less ecosystem support |

### 11.4 Database: SQLite + sqlite-vec

**Chosen because:**

- **Local-first**: no server process
- **Single file**: easy backup, export, portability
- **sqlite-vec**: vector search in the same stack
- **LangGraph checkpoints**: `langgraph-checkpoint-sqlite` built-in
- **16 tables**: sufficient for MVP

**Compared to:**

| Option | Why Not |
|---|---|
| PostgreSQL | Requires server process, overkill for single user |
| Qdrant | Separate service, more complexity |
| Chroma | Separate service, less integrated with SQLite |
| DuckDB | Analytics-focused, less transactional |

### 11.5 LLM and Embedding

| Component | Choice | Rationale |
|---|---|---|
| LLM | Local Qwen via Ollama | Local, controllable, user already has it |
| Embedding | bge-small / nomic-embed | Lightweight, local, good quality |

### 11.6 MCP Integration

**MCP Client:** `langchain.mcp` adapter

**Chosen because:**

- Native LangGraph integration
- `MCPAdapter` produces LangChain Tools directly
- Minimal glue code
- Official maintenance

**Compared to:**

| Option | Why Not |
|---|---|
| Python official SDK | Lower-level, more manual connection management |
| Direct API calls | Less standardized, no unified tool management |

**Search MCP:** `free-search-mcp`

**Chosen because:**

- Python ecosystem, same stack as backend
- `research()` returns cited Markdown
- No API key required
- `uvx` startup, fits non-persistent model
- MIT license

**Installation:** Project venv, not global

```bash
uv venv .venv
source .venv/bin/activate
uv pip install free-search-mcp
```

**MCP config:**

```python
config = {
    "mcpServers": {
        "search": {
            "command": "/path/to/project/.venv/bin/free-search-mcp",
            "args": []
        }
    }
}
```

---

## 12. Technology Comparison Summary

| Decision | Chosen | Rejected | Reason |
|---|---|---|---|
| Frontend | Tauri + React | Electron, SwiftUI | Lightweight, cross-platform, rich UI ecosystem |
| Backend | Python + FastAPI | Node.js, Rust | LangGraph/RAG ecosystem |
| Orchestration | LangGraph | AutoGen, CrewAI | State-centric, checkpointing, subgraphs |
| Database | SQLite + sqlite-vec | PostgreSQL, Qdrant, Chroma | Local-first, single file, same stack |
| MCP Client | langchain.mcp | Official SDK | LangGraph integration, minimal glue |
| Search MCP | free-search-mcp | ai-search-mcp, search-box | Python ecosystem, research() tool, no API key |
| LLM | Local Qwen | Cloud APIs | Local-first principle |
| Embedding | bge-small / nomic-embed | Cloud embeddings | Local, lightweight |

---

## 13. MVP Scope and Roadmap

### 13.1 MVP Features

| Feature | Included |
|---|---|
| Three-domain state + tables | Yes |
| Habit + daily + events | Yes |
| Daily plan + time_blocks | Yes |
| Multi-plan generation + user confirmation | Yes |
| Daily rolling | Yes |
| Summary Agent (day/week/month configurable) | Yes |
| Suggestion pool + discard | Yes |
| Search MCP + knowledge acquisition | Yes |
| RAG basics | Yes |
| Status cards + timeline | Yes |

### 13.2 Second Version

| Feature | Deferred |
|---|---|
| Learning goals/subjects/reviews | Yes |
| Choice history | Yes |
| Month view aggregation | Yes |
| Weekly rolling | Yes |
| Suggestion similarity detection | Yes |
| Finance MCP | Yes |
| Multi-account | Yes |
| Mobile | Yes |

---

## 14. Consistency Check with Original Goal

| Original Goal Element | Current Architecture | Status |
|---|---|---|
| Self learning & life management platform | Single-user, local-first, three domains | Aligned |
| Multi-agent collaboration | Orchestrator + domain agents + summary + knowledge subgraph | Aligned |
| State-centric | State drives orchestration | Aligned |
| State-driven orchestration | LangGraph State + SQLite | Aligned |
| Visualization | Status cards + timeline + month view | Aligned |
| Dynamic adjustment | Suggestion pool + dispatch + RAG | Aligned |
| Summary Agent | Structured by domain, configurable frequency | Aligned |
| User control | Discard + reset + frequency | Aligned |
| Local-first | All runtime local, optional web for knowledge | Aligned |
| MCP extensibility | MCP Client + free-search-mcp | Aligned |

**Conclusion: Aligned, no deviation.**

---

## 15. Open Items for Next Layer

The following are implementation details, not architectural issues:

1. LangGraph node structure and routing logic
2. Orchestrator dispatch rules
3. UI layout and interaction details
4. Knowledge subgraph detailed flow
5. Prompt design

---
