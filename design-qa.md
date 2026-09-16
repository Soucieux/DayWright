# Wellspent design QA

The original visual-reference comparison below records the 2026-09-14 folio slice. The
2026-09-15 management-screen check is appended after it; the prior images do not depict the new
Today, Calendar, and Plans separation.

## Evidence

- **Visual source of truth:** `docs/design-reference.png` (1487 × 1058 pixels).
- **Primary implementation render:** `design-qa-render.png` (1440 × 1024 pixels, CSS viewport
  1440 × 1024, device scale factor 1).
- **Responsive evidence:** `design-qa-mobile.png` (390 × 844 pixels, CSS viewport 390 × 844,
  device scale factor 1).
- **RAG Library evidence:** `design-qa-rag-library-mobile.png` (390 × 844 pixels, CSS viewport
  390 × 844, device scale factor 1).
- **Multi-agent drawer evidence:** `design-qa-agent-drawer.png` (current desktop viewport with a
  persisted six-step cross-domain route and its `sqlite-vec` source provenance).
- **Compared state:** Today, Balanced, Draft 03; local API connected; local model available and idle.
- **Normalization:** the reference was viewed at its native size and compared with the complete
  desktop implementation render. The implementation is approximately 3.2% narrower while keeping
  the same landscape proportion and the full app shell in view.

The source and implementation were inspected together as the same comparison input. The responsive
render was inspected separately because it tests a different state and breakpoint.

## Visual comparison

The implementation preserves the reference's defining composition: staggered paper tabs, warm day
folio, oversized date lockup, dense ruled time ledger, clipped suggestion card, and a full-height
aubergine commitment sheet. It also preserves the intended typographic contrast, narrow domain
colors, square controls, restrained shadows, and editorial microcopy.

Intentional product differences are limited to the requested application behavior:

- Balanced, Focused, and Gentle controls make plan alternatives explicit.
- Ask Wellspent opens the contextual conversation layer.
- Status controls, model readiness, and proposal confirmation expose real application state.
- The Library adds one restrained capture sheet for chunking and indexing private notes.
- Retrieved source labels sit beside the answer without turning the drawer into a search dashboard.
- The `W/` folio mark gives the new Wellspent project its own identity.

## Focused-region checks

| Region | Evidence | Result |
|---|---|---|
| Date and week header | Date hierarchy, baseline, week spacing, and active-day rule compared with the reference | Pass |
| Schedule ledger | Ruled rows, time column, domain rails, fixed/flexible treatments, and density compared | Pass |
| Commitment sheet | Title, alternative selector, balance, notes, constraints, and primary actions compared | Pass |
| Suggestion | Paperclip, card position, clipped copy, Keep, and Dismiss treatment compared | Pass |
| Conversation layer | Ask, Adjust, and Report states inspected with proposal confirmation and a visible Orchestrator/domain/Summary route | Pass |
| RAG provenance | Indexed source label, chunk position, local-vector-store label, and grounded answer inspected together | Pass |
| Small screen | 390-pixel layout inspected; measured document width equals viewport width | Pass |
| Small-screen Library | Long editorial heading, real index totals, and note capture inspected at 390 pixels with no horizontal overflow | Pass |

## Primary interaction checks

- Switched among materially different Balanced, Focused, and Gentle schedules.
- Confirmed a plan and retrieved its confirmed state.
- Reported an item as Done and retrieved the updated state.
- Kept a suggestion.
- Asked a question through the live local Qwen runtime.
- Added a non-personal verification note, embedded it with the separate Qwen3 Embedding 0.6B
  runtime, retrieved it through `sqlite-vec`, and verified that the grounded answer exposed its
  source.
- Ran a deterministic API behavior check showing that the relevance-distance gate returns no
  private context for an unrelated question.
- Routed a cross-domain question through Orchestrator → Learning → Life → Finance → Summary →
  Orchestrator and retrieved the same trace from SQLite.
- Requested a lower-energy adjustment, reviewed the Gentle proposal, and explicitly applied it.
- Opened every main navigation section.
- Inspected browser console output; no errors or warnings remained.

## Comparison history

| Pass | Finding | Severity | Resolution |
|---|---|---|---|
| 1 | Week strip crowded the date header and clipped at the small-screen breakpoint | P2 | Rebalanced the header grid and stacked the week strip below the date on small screens |
| 1 | Suggestion card sat too high when the schedule used less vertical space | P2 | Anchored it to the folio's lower edge with flexible spacing |
| 2 | A few small controls used approximate hand-drawn symbols | P3 | Replaced them with Lucide icons, including the clipped paperclip |
| 3 | No remaining material visual, responsive, interaction, or accessibility mismatch | — | Passed |
| 4 | Multi-agent routing needed visible provenance without turning the drawer into a generic dashboard | P2 | Added compact, ordered editorial route labels beneath assistant responses; retained the existing folio language |
| 5 | RAG needed visible grounding and a usable ingestion path without adding a second dashboard | P2 | Added a folio-aligned Library capture sheet and compact private-context labels; corrected the long Library heading at the small-screen breakpoint |

## Final findings

No open P0, P1, or P2 findings remain. No P3 issue blocks the intended fidelity or interaction
quality.

## Final result

passed

## Management-screen QA — 2026-09-15

The revised screen direction keeps the paper tabs, ink, ledger rules, domain rails, and aubergine
review sheet, but assigns them clearer jobs: Today is a calm summary/control desk; Calendar is a
recorded-month and selected-day ledger; only Plans shows alternative schedules beside commitment.
This pass was inspected directly in the local browser; no new PNG capture was retained, so the
historical image evidence above must not be mistaken for this revised layout.

| Check | Observed result |
|---|---|
| Today | Summary, current-plan state, next four items, area links, and Calendar/Plans actions visible; no full schedule or commitment sheet on the landing view |
| Calendar | Previous-month control reaches an empty past month and selects its first day; no fictitious plan is created; day and month summaries remain clearly scoped to recorded data |
| Plans | Three alternatives are labelled for one date; Focused preview changes only the Plans schedule, not the current Today/Calendar state |
| Replacement | An already confirmed alternative requires a named review; cancelling preserves the current plan; direct unapproved replacement is refused by the API |
| Shared items | Calendar and Learn/Life/Money read the same selected day; Life includes Rest; only the confirmed variant exposes reporting controls |
| Progress | A Done report changes the selected-day count and Calendar month count/marker together in unsaved preview QA; persistent behavior is covered by the focused API test |
| Mobile | 390-pixel Calendar and 320-pixel minimum-width layout inspected; all eight destinations fit in a two-row bottom rail; the month controls move beneath the heading at the narrowest size |

Preview-mode confirmations used for interaction QA were not written to the user’s local database.
The separate API test uses a temporary database to check durable confirmation, replacement,
calendar counts, and confirmed-variant-only reporting.

## Isolated live management and retrieval check — 2026-09-15

The revised interface was checked again at desktop and 390-pixel mobile widths against an owned
local service using disposable temporary databases. No user record in the existing 5173 session
was changed; loading the updated service/test module also applied additive tables to the existing
local database schema, which passed a read-only integrity check. With two entered timed items,
Plans displayed distinct Balanced, Focused, and Gentle
options; confirming Gentle updated Today and Calendar once, and reporting French practice Done
updated the linked summary. A past date remained read-only and a future user preset remained editable
but not reportable before its date.

The Library accepted a generic French-language topic, fetched the bounded attributed Wikipedia
introduction after no local match, indexed two chunks with the shared Qwen embedding runtime, and
retrieved them locally with URL/license provenance. An initial combined checkpoint/vector write
failed SQLite integrity and retrieval; rerunning the real flow with separate checkpoint storage
returned both chunks and `PRAGMA quick_check = ok` for both SQLite files. A clean account was then
reopened with no goal, item, or draft plan, and an empty-plan request was refused. The full documented
`npm test` command passed its build, four static packaging tests, and 25 API tests. Actual speech
transcription remains unverified because the compatible local CLI is not installed.

The Library was then inspected at the desktop viewport and at 390 × 844. Local-first topic,
selected-file import, and pasted-note capture appear as separate tasks within the same scrollable
workbench. A synthetic Markdown upload indexed and retrieved in the API check, and Word/PDF extraction
was checked with generated in-memory files. A file-picker click-through was not performed in this
browser pass; unsupported/oversized/scanned-file handling is established by the focused API test.
The final documented `npm test` pass covered 26 API tests.
Two short synthetic Markdown versions with the same name were then indexed through the real local
embedding runtime in another disposable database. Both remained in the source inventory, a query
retrieved the first version, and SQLite integrity remained `ok` after each import. No actual user
document was selected.

The saved-advice management entry was inspected collapsed and expanded at desktop and 390 × 844
mobile widths using one synthetic soft suggestion in a disposable database. Day/week/month filters,
area selector, priority/status, and the cross-period discard label were exposed without crowding the
initial Today view. No real user's suggestion was discarded or cleared. Focused tests covered a
protected-task strong suggestion reaching the Learning agent, cross-period discard, a later repeat
appearing only as a notice, the typed week/area clear guard, and a cleared period not regenerating
on a repeated report read. The final `npm test` pass covered 28 API checks and four static checks.

The public-source import was subsequently corrected to stage a bounded introduction before
indexing. In a separate disposable database with the real shared Qwen embedding model, entering
“French language” returned three organization choices with zero indexed sources/chunks; confirming
one choice indexed two chunks, and a semantic search returned them with the Wikipedia URL. Both the
main/vector database and separate LangGraph checkpoint database returned `PRAGMA quick_check = ok`.
The confirmation conflict/idempotence cases are covered by the focused API test, not by this browser
pass. The UI was inspected at desktop and 390 × 844: a pending topic can be reopened, source URL,
license, and timeliness receipt remain visible, all three radio choices can be selected, the chosen
topic is no longer redundantly listed above the choice sheet, and the confirmation button is
reachable by vertical scroll without horizontal overflow (`documentElement.scrollWidth = 390`).
The categorization is still an organization label rather than verified passage-level tagging,
and the filter receipt does not establish multi-source quality comparison. No user document or
production record was imported in this pass.

The Talk replacement path was checked with a disposable API fixture: after Balanced was confirmed,
an Adjust proposal named Balanced → Gentle; an unreviewed switch was rejected without changing
the day. Replacing Balanced with Focused elsewhere made the earlier proposal stale and rejected it;
a newly reviewed Focused → Gentle proposal then applied once. The drawer now labels this as a
named replacement. This is focused API and source-level UI evidence, not a new live drawer capture.

A disposable Summary fixture with two Done dates for each of two protected recurring tasks produced
two traceable future commitments. The repeatedly shortened task was preset at 45 rather than 60
minutes; the other retained its 30-minute block with recorded-outcome provenance. Reading the same
report again created no duplicate future items. This behavior was checked directly through the
Summary/SQLite layer, not through a new browser recording.

The pre-existing user-facing processes on ports 5173 and 8421 remained running and were not
restarted. Read-only route/source checks after implementation showed that they still serve the
older version; the newest source changes are therefore build/API-tested and browser-checked against
an isolated temporary service, but are not claimed live in that pre-existing app session. Both
local commands must be restarted before the original browser tab can show this revision.

## Domain-management slice — 2026-09-15

Three focused disposable-database API scenarios checked Learning catalog/session history, Life
reported state/habits and atomic timed-event Calendar linkage, and manual Money balances,
transactions, and budgets. The Life check also confirmed a recorded low-energy state can influence
a later Gentle planning choice; historical outcomes are blocked, while future preparation remains
available. Two existing plan/Summary regressions passed alongside these tests. This was a focused
check, not a new full-suite run.

At the isolated live preview, a Learning subject and 30-minute Done session were saved through the
state sheet; Today’s schedule correctly remained empty while Summary reflected the recorded
Learning session. The UI then exposed separate Life and Money state sheets. A first navigation
attempt blanked when the restarted preview accidentally targeted the older 8421 service. With the
preview explicitly paired to the new isolated 8422 service, Money → Life and Learning → Life
rendered. At 390 × 844, the Life sheet had no horizontal overflow (`scrollWidth = 390`). This
browser pass did not submit a Life event or Money transaction through the visual forms; their
write/link behavior is evidenced by the focused API scenarios. The user's original 5173/8421
processes and data remained untouched by this browser pass.

## Local voice installation — 2026-09-16

The official `faster-whisper` 1.2.1 package and CPU dependencies were installed in the project's
Python 3.12 environment. A pinned multilingual converted Whisper-small model was added under the
shared AI-Models library without changing the pre-existing Core ML model. The weights matched the
publisher's recorded size and SHA-256. A readiness regression confirmed a partial model cannot
enable the microphone.

A synthetic macOS voice—not the user's microphone—produced a 2.24-second mono 16-bit 16 kHz WAV.
The current Wellspent endpoint transcribed it exactly as “Plan a shorter learning session tomorrow.”
and returned HTTP 200. The temporary audio was removed after the check. Because stopping the older
8421 user-facing API process was declined by the execution policy, the updated API and UI were
started on 8422 and 5174; a refreshed user-facing tab was opened there and visibly reported “Voice
ready · press the microphone to talk.” The earlier 5173/8421 processes remain running rather than
being terminated indirectly.
