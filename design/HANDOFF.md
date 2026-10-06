# DayWright UI redesign — "Open Bench" · implementation handoff

This is the build spec for the redesign. It is written for Claude Code (or any engineer) replacing the current "day folio" UI.

- **Source of truth for values:** `tokens/tokens.json` (also available as CSS variables in `tokens/tokens.css`).
- **Source of truth for look and layout:** `screens/png/*.png`. The matching `screens/html/*.html` files are static mockups with inline styles. Read them for exact spacing, sizes and copy. **Do not copy their markup into the app**: build real components from the specs below.
- **Icons:** `icons/*.svg` are 24×24. Stroke icons use `currentColor` at 1.75 px. The area glyphs (`area-*.svg`) and status glyphs (`status-*.svg`) are filled.

The product, its principles and its jobs are unchanged. Only the interface changes.

---

## 1. The idea: agents pencil, you set

One visual rule runs through every screen:

| Kind of thing | How it looks | Meaning |
|---|---|---|
| **Pencilled** | 1.5 px **dashed** `pencil` border, plus a chip naming the agent (agent icon) | Proposed by an agent. Not yours yet. Always shows its evidence. Needs Confirm/Accept or Dismiss. |
| **Set** | Solid 1 px `line` border on `surface`. A confirmed plan gets an ink "Plan set · Name · HH:MM" chip | Yours: you confirmed it or entered it. |
| **History** | `sunken` background, a lock icon, and status shown as plain text (no buttons) | A past day or a replaced plan. Read-only. |

Every principle maps to an implementation rule:

1. **A believable day is the output.** Today is a single schedule plus one "Next" action. Balance is one quiet bar, not a dashboard.
2. **The user keeps authorship.** Anything an agent produces renders pencilled. Changes arrive as a *proposal card* with a preview and **Confirm / Dismiss**. No record changes before Confirm.
3. **Progress is reported, never inferred.** Status changes only through the user (the status control, or a report to Ava followed by Confirm). A past entry the user hasn't reported says "Not reported yet — time passing doesn't mark it done". Never auto-complete anything.
4. **Nothing is invented.** A new account shows empty states. Unrecorded dates render as blank cells. Sample data exists only in the **demo workspace**, which is striped and labelled everywhere.
5. **Local-first is visible.** The top bar always shows the save state and model state. DayWright never goes online, and the Library says so in one line.
6. **Calm beats density.** Body text is 16 px and nothing is smaller than 13 px. There is one status control per row. Edit and Remove live in the row's detail sheet, not on the row.
7. **History is read-only on screen.** Past days and replaced plans render with no editable affordances at all; they aren't just disabled. A past task changes only through Ava: the user says what to change, Ava proposes it on a proposal card, and it applies on Confirm. The one other way in is Delete on a past task in its goal's task list. Ava's changes are aimed at today and later days: on a past day it corrects what a task is, removes it, or moves it forward, but never rearranges that day.

---

## 2. Tokens (summary — see `tokens/tokens.json`)

**Neutrals:** `ground #E8ECF7` (app background, a soft blue tint) · `ground-2 #DDE3F2` (tracks, segmented controls) · `surface #FFFFFF` (cards, sheets) · `sunken #F5F6F8` (read-only, wells) · `line #DCE0E6` · `line-2 #C3CAD3` (control borders) · `ink #18202B` (text, primary buttons) · `text-2 #475163` · `text-3 #5B6575` (captions; 5.9:1 on white, 5.0:1 on ground).

**Accent:** `accent-fg #3B4DB8` on `accent-tint #E2E6FA` (5.8:1), for the active place and Records section, the page's weekday, and today's calendar marker.

**Area colour in use:** a task row or the Next card takes its area's `tint` as its background and a band in its area's `mid`; a goal card takes a top band in its area's `mid`. The area tag and glyph stay beside the colour.

**Areas.** Colour always travels with its glyph and its label. Never use colour alone.

| Area | EN / 中文 | Glyph | fg (text) | mid (bars, fills) | tint (backgrounds) |
|---|---|---|---|---|---|
| learn | Learn / 学习 | triangle | `#4B3FB0` | `#7B70D6` | `#ECEAFB` |
| life | Life / 生活 | circle | `#0B6E63` | `#2AA597` | `#DDF1EE` |
| work | Work / 工作 | square | `#8A5A06` | `#D39A2B` | `#F8EBD2` |
| project | Project / 项目 | star | `#9A3864` | `#D0729D` | `#F8E4EE` |

Money and Rest were the third and fourth areas until 2026-10-02; Work and Project took their colours.

`fg` on `tint` is at least 5:1. `mid` is never used for text.

**Signals:**
- saved `#1D6B45` on `#E3F2E9`
- caution (preview mode, online use, under review) `#6B4800` on `#FFF1CC`
- refusal and destructive `#9B1C1C` on `#FDECEA`
- demo `#4A3A7A` on `#EFEAFB`, with a 135° stripe
- paused (a task paused with its goal) `#46546B` on `#E9EDF3`, edged `#A9B4C4`, always with the pause glyph and a label
- pencil `#7C8698`
- focus `#1F5EFF` (a 3 px ring, 2 px offset)

**Type:**
- English: display Bricolage Grotesque, body Figtree.
- Chinese: PingFang SC, falling back to Noto Sans SC.

| Style | EN | 中文 |
|---|---|---|
| display | 40/48 | 36/48 |
| title | 28/36 | 26/36 |
| heading | 20/26 | 19/28 |
| body-lg | 17/26 | 17/28 |
| body | 16/24 | 16/26 |
| label | 14/20 (600) | 14/22 (600) |
| caption | 13/18 | 13/20 |

- Everything is sentence case. No uppercase monospace.
- Small section labels (e.g. "LINKED TASKS") are the only caps: 13 px, weight 700, 0.02em letter-spacing.
- Times and amounts use tabular numerals.
- Bundle the fonts in the app. No network font loading.

**Space:** 4 px base (4, 8, 12, 16, 20, 24, 32, 40, 48, 64).

**Radius:** chip 999 · control 10 · row 14 · card 16 · sheet 20.

**Controls:** 40 px tall on desktop and 44 px on phone. Touch targets are at least 44 px.

**Motion:** sheets and menus 160 ms ease-out; state changes 120 ms. With `prefers-reduced-motion`: no slides, instant changes, no animated waveform.

---

## 3. Navigation (replaces the 8-tab rail)

**Four places plus one layer:**

| Place | Contains |
|---|---|
| **Today** (default) | Schedule, then a "No start time" table for flexible tasks a set plan hasn't placed. Beside them three tabs: Day details (Next action, balance, finishing; see 4.21), Plan (see 4.14), and Summary agent (today's report and advice only). Header: the date with its report chip, the day strip (see 4.16), then the actions column: the energy row (see 4.18) above Add task, plus Propose plans or Compare and set one until a plan is set; on a day with no tasks, the energy row alone. Report progress. **Plans** sub-view: compare and set, review a replacement. |
| **Calendar** | Month view of past and future. Per day: recorded / set / completion, and the day's energy as a five-step meter (see 4.18). Beside the month, two tabs: Day details (the selected day's plan and schedule) and Summary agent (its day, week, month and all-time reports). Preset future commitments. A legend grid under the month: each mark, its name, and a short explanation. |
| **Goal** | Side list: Goals, Tasks, then Areas (Learn, Life, Work, Project), each on its own row. Goals lays its cards out in two equal columns, one under 640 px. Each area is one page of cards, two to a row and one under 640 px, with no tabs; the cards are built from the area's tasks, goals and repeats (see 4.17), and the area keeps no records of its own. |
| **Library** | The notes and files kept on this Mac, each in an area and, if chosen, a goal: an area switch, Search your library, and each one with its area, goal, date, Edit and Remove. New note and Import files ask for the area and goal (see 4.19). |
| **Guide** | Opened from Guide beside EN/中文, in English in either language: every card, in five sections (see 4.20). None of the four places is marked while it shows. |
| **Ava** (layer) | The assistant. Reachable from everywhere. Knows the place and day on show without repeating them, and suggests three questions for it. Works out from each message whether it asks, changes or reports; there is no mode switch. Speaks through the microphone beside its empty box, with the words shown as they are said. |

**Desktop:** a 60 px unified title bar containing, left to right:
- the traffic lights
- the app icon (34 px) and the "DayWright" wordmark (22 px)
- the four places as a segmented group, with the active one on white
- a status cluster: status pill · Guide · EN/中文 toggle
- the **Ava ⌘K** button. While Ava has a message you haven't seen, a 9 px red dot (`refusal-fg`, ringed 2 px in `surface`) sits on the top-right of its icon, and the button also says "New message" to a screen reader.

When Ava is open it floats over the page as a 540 × 600 px window (`float` shadow, sheet radius), 12 px from the bottom-right corner, or 12 px left of an open side sheet. **It never narrows the page.** Dragging its title bar moves it, and the position is remembered; a double-click puts it back. Its top edge changes its height (at least 320 px, also with the arrow keys; a double-click restores 600 px), and the height is remembered. It doesn't fold down: a click anywhere outside it closes it, as Escape does, and Ava's own button opens and closes it. A click that starts inside Ava, such as selecting its words, keeps it open wherever it ends; a button elsewhere that opens Ava for a question, such as Ask about this day, keeps it open with that question. Among the replies, Ava posts its messages about issues the agents found, each under Ava's avatar with a dashed chip naming the agent ("From the Learning agent"); opening Ava marks them read and clears the dot. When a request asks for a change, the task's area agent adds its doubt the same way, and when Ava can't tell which task is meant, it asks. The header holds the avatar, the name with its "?" beside it (see 4.20), an `accent` chip naming the day Ava answers about, which is the day on show ("About today", "About Fri 2 Oct"), and its close button, so reopening it shows which day the conversation carries on with. The box's placeholder names that day too, and the log marks where the conversation turned to another day with a centred rule ("About today"). While Ava answers, three dots pulse beside "Consulting the relevant agents locally", centred on its line with the avatar, and stay still when motion is reduced. Under the conversation: the three suggested questions on one row, the box, and one button, a microphone while the box is empty, stop while listening, send once there are words. One quiet line under the box appears only while listening or transcribing, or when something needs saying; the model's state shows in the top bar alone, and replies show Ava's avatar without its name. Side sheets for forms (for example "New task") are 440 px on the right and push content. While a sheet is open, the Records side list collapses to a breadcrumb.

**Every place fills the window.** Its heading, actions and banners stay put and only the part below scrolls, so no place scrolls as a page while another doesn't. That part scrolls as one, columns and cards together, so a place shows at most one scroll bar, at the window's right edge; no card or column scrolls on its own. The Mac app's window opens at, and can't shrink below, 1412 × 938 points. A phone keeps one scrolling page.

**Phone (≤ 640 px; the minimum width is 320 px):**
- **Header:** app icon, wordmark, Guide and EN/中文, with the status pill below them.
- **Bottom bar:** one row of 5 items (Today · Calendar · **Ava** in the centre as an ink pill · Goal · Library), always labelled. Ava's pill carries the same red dot. Page content ends above the bar. **No floating buttons.**
- **Ava:** opens as a sheet that leaves a strip of the page visible above it and closes back to the same place. It can't be moved or resized.
- **Plan comparison:** one plan at a time, with a segmented switch naming the day's plans, Balanced first, and previous/next buttons. The Set button is pinned above the bottom bar.

**Suggested breakpoints:**
- ≥ 1100 px: two columns (main plus a 440 px right column)
- 641–1099 px: a single column with the top bar kept (place labels can shrink to icon + label)
- ≤ 640 px: the phone layout

---

## 4. Components

For each component: anatomy → states → accessibility.

### 4.1 Task row / plan entry (`03-Components`, `10-Today-Desktop`)
- **Anatomy:** a time column (64 px: the start time in 15/600 with the length directly below it in 13, the same on Today, in Calendar's day panel and in Plans, and for the lunch and dinner rows on Today and in Plans; a task with no start shows its length alone) · a block (radius 14, `surface`, 1 px `line`) holding:
  - area tag + title (16/600) on one line, plus a "Next" ink chip if it's the next action
  - optional detail (14, `text-2`)
  - flags: Fixed (pin), Daily/Weekly (repeat), goal link (link icon + goal name)
  - optional note, e.g. "Not reported yet"
  - **one status control**, right-aligned on desktop and at the bottom-right of the block on phone
- Clicking the row opens a detail sheet, which holds Edit and Remove. **Never put Edit or Remove on the row itself.**
- **States:**
  - default and focus-visible (ring around the block)
  - done
  - skipped (title in `text-2`)
  - agent-proposed: dashed border, an agent chip, evidence in the note line, **Accept / Dismiss instead of a status control**
  - read-only: `sunken` background, status as plain text, no buttons
  - preview: a dashed inset box "Preview: 20:15–21:00 · not applied"
- **A "Now HH:MM" line** (2 px ink, with a label) sits between entries at the current time.

### 4.2 Status control
- **Compact button:** the shared dropdown (4.15) with status glyphs: glyph + label + chevron, 40 px tall. It opens a menu of 4 items (44 px each): glyph and label flush left, and a check at the right edge of the current one, so every label starts at the same place.
- **Segmented form:** 4 options with glyph and label, used where reporting is the main action (Next card, Report sheet). On phone it becomes a 2×2 grid.
- **Values:** Planned ○ · Done ● · Partial ◐ · Skipped ⊘. The shape carries the meaning, so the glyph works without colour. All four use ink.
- **Read-only form:** glyph + text in `text-2`.
- **Paused:** a task whose goal is paused shows a read-only pill instead (pause glyph and "Paused" in `paused-fg`, `paused-line` border, on `surface`). Its row turns `paused-bg` with a `paused-line` edge and the note "Paused with its goal; resume the goal to report it". A task is never paused on its own.
- **Accessibility:** `role="radiogroup"` / `menuitemradio`, and an accessible name such as "Status: Planned. Change status".
- Changing the status of a goal-linked item updates the goal's progress immediately. Show a toast only for undo.

### 4.3 Plan column (comparison)
- **Header:** radio + plan name (Balanced, or one of Deep focus, Lighter day, Finish early, Quick wins first, Easiest first, Your usual rhythm, Breathing room) + a "Proposed" chip (dashed) or a "Chosen" chip (ink).
- **Sections:** intent line (one sentence per kind of plan, such as Balanced "Even spread: the areas take turns by priority, from your first free time." or Deep focus "One long block: work, project and learning back to back, nothing in between.") → AT A GLANCE (a `sunken` box spanning the column, with the same three rows in every column, so they line up: Starts with: the plan's first task, quoted, with its start time on the line below · Done by · Lengths: each task whose length the plan changed, quoted, with its change on the line below, such as 1 h → 45 min; labels take only the width they need) → why it was suggested, in caption type (none for Balanced); a reason the local model wrote follows the agent icon and reads "Orchestrator · finish: …" → WHAT SETS IT APART (a small label over what only this plan does, with a 3 px accent rule on its left), with every task name in quotation marks → TIME BY AREA (a stacked bar with 2 px gaps, plus a 2×2 legend with glyph, label and duration; a past plan's entries marked "Removed" or "Moved to {day}" stay listed but leave the totals) → SCHEDULE (compact rows: the time column, start over length · glyph · title · fixed icon; lunch and dinner as muted rows with a fork-and-knife icon, named just "Lunch" or "Dinner"; a task paused with its goal since the plan was made has its title in `paused-fg` and a Paused chip) → WHY THIS PLAN (per-agent notes, each with the agent icon and name) → CONSTRAINTS (icon + text; paused tasks get their own lines with a pause sign: the ones the plan still holds, "Propose again for plans without them" on a draft and "can't be reported until the goal resumes" on the set plan, and the ones it left out because their goal is paused). A plan made after a pause never holds that goal's tasks. Today's Plan tab and the replacement review say the same about the set plan.
- **How the agents made these plans:** under the columns, the first of two tabs: every agent in the order it ran: the Orchestrator once (whom it asked and which plans it chose), the four area agents, then Summary. Under each name, one line says that agent's one job. Each area agent lists its findings, one line per task with its area glyph (for example "Draft the guide: partly done 2 and skipped 1 of 4 times, so 45 min instead of 1 h") and, under them, the plans it voted for ("Voted for: Deep focus, Your usual rhythm"), or "No Work tasks to review today.
- **Earlier route:** a route saved by an earlier version (fewer agents, no findings) is rebuilt by every current agent when the service starts, so this list always names Orchestrator, Learning, Life, Work, Project and Summary; the plans themselves are not changed. Nothing in the interface asks the user to do this. A route saved before v2.1, which closed with a second Orchestrator run, is rebuilt the same way.
- **Plan types:** the second tab: a line saying Balanced is always offered, the area agents vote, and the local model picks two others, then every kind of plan, Balanced first, each in a `sunken` card with its name, its intent line, and when it is offered, four to a row on a wide page.
- **Order:** Balanced, then the two plans the local model chose for the day, or DayWright's own ranking when the model is off. Three plans whenever three different ones can be made, clearly different ones first. When the Life agent advises a lighter day, Lighter day comes first (and is the one shown first on a phone), and its intent line opens with "Listed first because the Life agent advised a lighter day."
- **Button:** "Choose {Name}". Choosing does **not** set the plan: it shows the confirmation bar.
- **Chosen column:** 2 px ink border and the `chosen` shadow. The other columns stay dashed.

### 4.4 Confirmation bar and two-step confirmations
- **Set-a-plan bar** (ink background):
  - title: "Set “Balanced” as today's plan?"
  - consequence line: "10 entries will be scheduled. Nothing counts as done until you report it. Replacing a set plan later needs a review."
  - buttons: [Keep comparing] [✓ Set Balanced]
- **Two-step remove:** an inline card with a 2 px `refusal-fg` border and the heading "Step 2 of 2 · Remove “X”?". Its body says what happens and what stays (e.g. "history in past days stays readable"). Buttons: [Remove goal] (danger) [Cancel].
- **Replacement approval:** a checkbox "I've reviewed all N changes" enables [Replace with “Name”]. The secondary button is [Keep {current}].

### 4.5 Refusal
- An inline alert (`refusal` colours).
- **Title:** "Can't remove this goal yet".
- **Body:** why, and what to do instead: "3 tasks are still linked to it. Delete them from this goal's task list, or unlink them from the goal (for past tasks, ask Ava), then try again." (one task: "1 task is still linked to it. Delete it …"), then **"Nothing was removed."**
- **Actions:** a way forward ("Show the 3 linked tasks", or "Show the linked task" for one), which opens the goal's Edit sheet at its task list, and OK. OK uses the same bordered button as the way-forward action; keyboard focus starts on the way forward. The Cancel of a two-step remove stays quiet.
- **Task removal while a set plan scheduled it:** today, offer "Report Skipped" and "Review a replacement". A past task is removed instead, and its day's plan keeps its entry, marked "Removed", on show but no longer counted.

### 4.6 Goal card
- **Contents:**
  - area tag and a status dropdown (the shared dropdown: Active / Paused / Completed, each with its note "plans may use it / its tasks pause; plans skip them / kept in history")
  - title (20/600)
  - a clock line: "From Sat 3 Oct, 09:00 to Sat 3 Oct, 10:45", which DayWright sets from the tasks' lengths; a paused goal adds a pause line, "Paused: its tasks are paused too, and plans skip them"
  - a progress bar in area `mid`, with "3 of 5 linked tasks done" on the left and "reported, not inferred" on the right
  - LINKED TASKS · N: up to three (link icon · name · when), today's and later ones first, then the most recent past ones, a task with no start last in its day; with more, a "Show all N tasks" / "查看全部 N 个任务" link opens the goal's Edit sheet at TASKS IN THIS GOAL
  - footer: [Edit] [Remove…] … [+ Add task], all three the same bordered button
- Every card is the same height: the task list keeps room for three tasks, so the footers line up across the grid (two or more columns on desktop, one on a phone).
- **Edit sheet:** the title field; then one `sunken` panel holding the area tag (marked fixed) and the time it spans ("Sat 3 Oct, 09:00 – 10:45" within one day), label column on the left; then PROGRESS BY WEEK, the goal's burn-up (see 4.21); then TASKS IN THIS GOAL · N with the tasks' total length on the right, over a bordered list: status glyph · title over "day · status" · [Edit] for a task today or later. A past task is history: a `sunken` row with a lock in place of the glyph, its status as plain text, and [Delete…], which takes two steps ("Step 2 of 2 · Delete “X”?", [Delete task] (danger) [Cancel]); a plan set for its day keeps its entry, marked "Removed". Under the list, when it holds a past task: "To change a past task, ask Ava." Edit opens the task's form in place of the goal's sheet, which comes back, with what was typed in it, once the form is saved or cancelled. The form keeps offering the task's own goal while that goal is paused. Last comes LIBRARY · N, the goal's notes and files, with [+ Add note or file] (see 4.19).

### 4.7 Advice card (Summary agent)
- **Contents:** a dashed card with the agent label ("Summary agent · Advice"), the advice (16/500), and an evidence well (`sunken`, info icon) such as "Based on your reports: …". Actions: [✓ Keep] [Dismiss].
- Kept advice appears read-only on that past day in Calendar ("You kept this at 21:48").
- On Today and in Calendar, the Summary agent has its own side tab. Its report opens as a table of done, partial, skipped, and scheduled tasks by area, what the area agents see (tasks that keep slipping, whose length looks off, or that go well), a list of tasks partly done or skipped, and the area records, never as a paragraph; "Read the report" ends with a chevron that turns over when open. A task paused with its goal and still to do isn't counted as scheduled, and a paused goal's repeating task gets no advice to keep its next block. All time has no advice list of its own. In Calendar, Week, Month and All time end with BY DAY, BY WEEK or BY MONTH: one part per day, week or month with a record, newest first, each with done of scheduled by area and its own advice.
- **Graphs in a report:** right after BY AREA, a day shows PLAN FOLLOW-THROUGH, and a week or month DONE BY AREA, FINISHING and PLAN FOLLOW-THROUGH (see 4.21); All time shows none.
- **ENERGY in a report:** read from the readings reported in its period alone; a day without one counts in none of it. A day shows its readings as steps, a week or month a bar per day (see 4.18). Then "Days reported: 5 · average 3.1 of 5"; for a week or month, "Lowest: Fri 2 Oct, 1.5" and "Highest: …"; "Against the period before (2.8): +0.3" when the period before has readings (a day's is yesterday, a week's the week before, a month's the calendar month before). From 5 reported days, at least 2 low (2 or below) and 2 others, it sets them side by side: "Fully done on low days (2 or below): 67%, 2 of 3 tasks over 2 days", "On the other days: …", and a line per area ("Project: – on low days, 100% on the others", – where an area had no task). Below that, only "Low days are set against the others from 5 reported days, at least 2 of each.", and no advice. When low days went worse, the report's Life advice says by how much and which area fell most, and is strong from 25 points apart: "On days your energy averaged 2 or below, you fully finished 40% of your tasks, against 80% on other days. Work fell most: 0% against 100%. Plan lighter on low-energy days." A report saved before v4.3 keeps its single "Energy" line.

### 4.8 Proposal card (Ava's changes and reports, agent suggestions)
- **Contents:**
  - a dashed card with the chip "Proposed change · not applied"
  - a title, e.g. "Change 1 entry in today's set plan"
  - a list of changes (icon + text, with before → after in bold)
  - a note: "The preview is shown on your schedule. Nothing has changed yet."
  - actions: [✓ Confirm change] [Dismiss] (or [Edit first])
- **The day in a card's title:** today and tomorrow read as words, with no "on" ("Move dinner today", "Move 1 task tomorrow"; "调整今天的晚餐时间"); any other day keeps "on" before its short date ("Move dinner on Fri 9 Oct"; "调整10月9日周五的晚餐时间").
- **Moving a task:** in Adjust, naming a task and a time ("Move Review to 10:30", "3pm", "下午3点") proposes "Move 1 task today" with "“Review”: 13:00 → 11:00" and "It becomes a fixed task at that time. Plans already proposed keep their schedule." When the time is taken, the reply says by what and proposes the nearest free start instead.
- **Changing or removing a past task:** about a past day, the user names the task and says what to change, in their own words. Ava corrects what the task is: its title, detail, goal, area or status ("Mark Review as done", "Rename Review to Notes"); removes it ("Remove Review"); or moves it to today or a later day ("Move Review to today at 15:00"), where it is planned again and a start, length or timing can be given, with the overlap and meal checks. On its past day a task keeps its place: its start, length and timing don't change, and nothing moves onto a past day; such a request is answered "On {date} a task keeps its place … Nothing was changed.", and a mixed one ("Review took 45 minutes and was partly done") proposes the allowed part and names the rest ("Left out: its length, as a past task keeps its place."). The service refuses the same. A task can't move onto a day that already has its repeat's own day. The Orchestrator asks which task when several fit or none does. The card is titled "Change “Review” on Sat 3 Oct" with one line per change ("Status: Done → Partly done"), or "Remove 1 task on Sat 3 Oct"; its note says any plan for that day keeps its times and the agents update their reports once the user confirms. Moved, the past day's set plan keeps the entry marked "Moved to {day}" / "已移到{day}", left out of that day's counts like "Removed"; it counts on its new day, which joins its proposed plans when none is set there, and the agents look at both days again. When that day's set plan scheduled the task, the removal card adds "The plan set for that day keeps its entry, as history.", and once confirmed the plan shows that entry marked "Removed", in Calendar and in Plans, with nothing else in it changed; the entry no longer counts, in Calendar's day counts, Summary's reports or the area agents' profiles. "Remove that task", "change it" or "那个任务" right after a message that named one task means that task; after one that named several or none, the Orchestrator asks which.
- **A repeating task on a past day:** changing its title, detail, goal or area makes the Orchestrator ask "“Stretch” repeats. Should this change Sat 3 October alone, or Sat 3 October and the repeat from today on?"; "just that day" or "and the repeat" (只改那天, 连同以后) answers, and the card says how many days change ("Only Sat 3 Oct changes." or "3 days change: Sat 3 Oct, Sun 4 Oct, Mon 5 Oct."). No other past day changes. Removing or moving its day changes that day alone. From a past day, a repeat can also start, stop or switch between daily and weekly, from today on: "Make Read repeat daily" makes the past task the template of a new repeat whose first day is today while there's still time, a start not yet passed or a flexible task today's plan can still place, else tomorrow, or for weekly the next day on the past task's weekday; the card reads "Repeats daily from Fri 9 Oct; earlier days stay as they were.", the past task and the days between stay as they were, and a first day today gets the overlap and meal checks and joins today's proposed plans. "Stop repeating Stretch" or "Repeat Stretch weekly" applies from today unless today's own day was reported or today's set plan scheduled it, in which case that day stays and the change starts tomorrow ("Stops repeating from tomorrow; …"). From then on, the repeat's days still to do that the change leaves out are deleted, as a delete would (they leave proposed plans and their agents are told): every one for a stop, those not on the past task's weekday for a switch to weekly, none for a switch to daily. The card lists them ("Its days still to do are removed: today, tomorrow."), the days kept take the new repeat, a weekly one keeps the past task's weekday when its next day is prepared, and a reported day is never touched.
- **Moving a meal:** lunch (12:00–13:00) and dinner (18:00–19:00) are stored times that plans keep free, changed only through Ava. "Lunch 12:30–13:30 from now on", "Lunch 12:30–13:30 from Friday on" or "Dinner 17:00–18:00 on Friday" proposes "Move lunch from {date} on" or "Move dinner on {date}" with "Lunch: 12:00–13:00 → 12:30–13:30"; without "from now on", "from {day} on" or a day, the Orchestrator asks which. A past day keeps its meals, and so do days before a change made from a day on. A change from a day on replaces the meal's one-day times from that day, and the card names them ("It replaces the one-day lunch time on Friday 9 October (13:00–14:00)."); a one-day time set later wins on its day. A meal ends by midnight: "Dinner 23:00–24:00" is shown as 23:00–24:00 everywhere, and "Dinner 23:30–00:30" is answered "Dinner 23:30–00:30 would run past midnight; a meal ends by 24:00. Nothing was changed.", with no card. The change is refused, nothing saved, when the new time would take any of a timed task whose length the user set, or the first 30 minutes of one whose length an agent estimated, a task paused with its goal included, as it would sit inside the meal once the goal resumes; the reply names the task and its time. Otherwise the card adds "Today's set plan will change around it once you confirm." or "Plans will keep the new time free once you confirm." On Confirm, the agents re-inspect the day. A set plan the meal overlaps by 30 minutes or less is fitted in place, an estimate shortened or a flexible task moved, and the card lists each change ("“Read”: 11:45–12:45 → 11:30–12:30"); with more, new plans are proposed and the set plan stays until the user picks one with [Use Deep focus] or compares them in Plans. Whenever the change reaches today, today's proposed plans that aren't set are made again around the new time, beside a set plan too; plans are proposed for today alone, so a change from a later day on reaches none until that day's plans are proposed.
- **Adding a task or starting a goal:** "Add Read chapter 4 tomorrow at 9 for 45 min to my Spanish goal" ("添加 读第4章 明天上午9点 45分钟") proposes "Add a task tomorrow" ("明天添加一个任务") with one line, "“Read chapter 4” · tomorrow · 09:00 · 45 min", ending "· repeats daily" or "· repeats weekly" when asked. Ava takes the title (quoted, or what's left of the message), the day (the day on show when it's later than today, else today; a past day is refused, nothing saved), and the start, length and repeat when given. Without a start the task is flexible ("No start time"); without a length the line reads "length estimated by its area agent", and that estimate is never under 30 minutes. A named goal adds "Joins your goal “Spanish” and takes its area."; a paused or completed one is explained instead ("“Spanish” is paused, so no task can join it; resume it in Goals, or add the task without a goal."). Without a goal, the card shows the Area control under the lines, with the area the message named, or the Orchestrator's suggestion by purpose (keywords when one matches, else the local model while it runs, as in the task form) and the caption "Orchestrator suggests Life from the task's purpose. Change it if it's wrong." while it's unchanged. "Start a goal: Kitchen renovation" ("新建目标：厨房装修") proposes "Start the goal “Kitchen renovation”" with the same Area control ("… from the goal's purpose …"); "…and add pick tiles on Saturday" lists each first task on its own line, and they're created with the goal. A goal title already in use is refused. The task lines are followed, once, by "Checked as the task form checks it: no overlap with timed tasks or meals.": before the card shows, each task passes the form's checks, and an overlap or a meal is answered with what it hits, with no card. Nothing is created until Confirm, which runs the checks again; then the tasks' area agents are told, as for a task added in the form, and a day of theirs with plans proposed and none set has them made again.
- **Reporting energy:** "energy 4", "my energy is 2", or a feeling in the first person ("I'm drained", "I'm tired", "I'm full of energy", "我很累") with no change asked for, proposes "Energy today" / "今天的精力" with "Add a reading of 2", "Today's average: 3 → 2.5" (or "Today's average becomes 2" for the first), and "For today only; earlier days keep their readings."; Ava's line reads "Add a reading of 2 to today's energy? Today's average goes from 3 to 2.5. Nothing is saved until you confirm." "I'm tired, switch to the lighter plan" stays a change request. Asked on another day, Ava says "Energy is reported for today only; {date} keeps the readings it had. Nothing was changed.", with no card. Confirm adds the reading as Today's row does (see 4.18).
- **While the card is open,** the affected row on the schedule shows the preview box.

### 4.9 Next action card
- **Contents:**
  - an ink chip "Next · in 50 min"
  - the area tag
  - the time range
  - the title (22)
  - the goal link
  - "Report what actually happened" with the segmented status control
- **Which task:** the next timed task still to come; once none is left today, the first unreported task without a start time, whose chip reads "Next · No start time" and whose length replaces the time range.

### 4.10 Balance card
- **Contents:**
  - a stacked bar of planned time by area
  - per area: glyph + label · a track showing planned time (tint) with the reported portion filled (mid) · "45 of 1 h 45"
  - a footnote on what is counted (e.g. fixed work is included in Life, sleep isn't counted)

### 4.11 Local-first pills (always in the chrome)
Where the records are kept and the model's state share **one status pill**, since both say what stays on this Mac: the records part, a `·`, then the model's state in words, for example "Private on this Mac · Model on standby". The pill takes the records part's colours.
- **Records part:**
  - "Private on this Mac" (laptop icon, saved colours)
  - "Not saved" (alert icon, caution colours, plus a full-width banner: "Changes disappear when you close DayWright. [Choose where to save…]")
  - "Demo data" (laptop icon, demo colours, plus a striped banner with [Leave demo])
- **Model part:**
  - "Model starting…" (spinner). Proposals are disabled, with the reason written next to the button.
  - "Model ready" or "Model on standby"
  - "Model unavailable". Show a card, its heading marked with a hollow red dot: manual planning still works, [Try again] [Details], and "Nothing is sent elsewhere as a fallback".

### 4.12 Empty state
- **Contents:** an icon tile (48 px, 1.5 px `line-2` border), a heading, one or two sentences that say what will appear and that nothing will be invented, and at most one primary action.
- **Empty Today:** 3 numbered steps (Add a goal (optional) → Add today's tasks → Propose plans; the last is disabled until there is at least one task, with the reason shown), plus three reassurances: Saved on this Mac · Nothing invented · Nothing set without you.

### 4.13 Forms (side sheet on desktop, full sheet on phone)
**New task:**
- Title
- Detail (optional)
- Date (today by default, or the later day on show; past days can't be chosen)
- Area (a segmented control with glyphs). Areas go by purpose, and under the control each area's one-line meaning is listed in the order the rule takes them, the chosen one in `ink`: **Work**, someone else expects it; **Project**, a step toward something you're building that has an end; **Learn**, the point is getting better at something; **Life**, everything else. For a new task added without an area or goal of its own, as from Today, the Orchestrator suggests the area once it has a title: by keywords for each purpose when one matches, else by the local model while it runs, which works from examples ("Kitchen renovation": Project, "Call the plumber": Life, "Read chapter 4": Learning), else Life. The suggestion is chosen for the user and named on a pencilled line ("Orchestrator suggests Work from the task's purpose. Change it if it's wrong."); choosing an area themselves ends it. A task added from an area takes that area, and one linked to a goal takes the goal's.
- Timing (Flexible / Fixed, with a helper line), holding its times: Flexible shows Duration alone, since a plan places the task; Fixed adds Start, a dropdown of every quarter hour of the day, as a fixed start may be at any hour (06:30, 22:30); only a plan keeps to 09:00–22:00, for the tasks it places. A start that would overlap another timed task that day for the chosen length, or run past midnight, stays in the list disabled, with a note such as "Overlaps “Team stand-up”", and so does a start that would run into lunch or dinner that day (12:00–13:00 and 18:00–19:00 unless moved through Ava), noted "Kept for lunch" or "Kept for dinner"; switching to Fixed picks the next free start. If the length later makes the start clash, an alert names the task and its time, suggests asking Talk to move it, and Save waits. Duration is optional: left blank, the area agent estimates it, shown greyed as "≈ 40" when editing, as "≈ 40 min" elsewhere, and as "The Learning agent estimated this length" in the task's details. A duration typed in, set through Talk or estimated is at least 30 minutes. Saved, a new task on a day with plans proposed and none set has them proposed again with it, as one Ava adds does.
- Repeats (None / Daily / Weekly). A repeating task starts a repeat whose days are linked, whatever each is later called; the next day is copied from the repeat's latest day, daily or on its weekday, and a day set to None ends the repeat.
- Goal (optional, the shared dropdown)
- [Save task] [Cancel]

All inputs have visible labels, are 44 px tall, and show the focus ring.

### 4.14 Plan tab (Today)
- **No plan set:** the heading counts the proposed plans ("3 proposed plans · none set yet"), with [View plans (3)] below it, or reads "No plan set yet".
- The tab never lists how the agents made the plans; that lives at the foot of Plans (4.3).
- **A plan set:**
  - an eyebrow "Following" and the heading "{Plan} · Set at {time}", then the plan's rationale
  - WHAT THIS PLAN CHANGED: one row per task the plan placed, moved or shortened (area glyph · title · "placed at 09:00", "moved from 09:00 to 10:30", "45 min instead of 1 h"), each followed by the agent finding behind it (agent icon · "Life: …"). With no changes: "It keeps every task as you recorded it."
  - a caption for the tasks kept as set, and one for accepted tasks the plan doesn't hold
  - buttons stacked at the card's full width: [View plans (3)] [Ask for a replacement plan] [Deselect plan] (last, quiet, × icon)
- **Deselect** needs no second step: the proposed plans stay, so the user can compare and set one again without a replacement review, and reported statuses stay. A notice says so.


### 4.15 Dropdowns, buttons and text (one of each, everywhere)
- **Dropdown** (`src/ui/MenuSelect.jsx`): a button naming the choice and a chevron, opening a menu of options. Each option may carry a glyph and a note under its label; the chosen one has a check at the right edge. An option that cannot be chosen stays in the list, disabled, with its note saying why. Two sizes only: *compact* (40 px, as wide as its text: status, goal status) and *field* (44 px, full width, scrolling menu: start times, goal). Arrow keys, Home and End move between options; Escape closes only the menu, never the sheet it sits in. No native `<select>` or time input is used.
- **Buttons:** every action is a `dw-button`: primary (ink), default (outlined), quiet (no border) or danger. An icon-only button is the same button with `dw-icon-only` (40 × 40), outlined for steppers and pagers, quiet for close and remove.
- **Text:** every paragraph, list item and value that wraps is justified to both edges; its last line stays at the start, English is hyphenated where that avoids wide gaps, and headings, buttons, chips and tables keep their own alignment.
- **Text links** (`dw-link`) only inside a line of text: a banner, a filter row, or next to a section heading. A standalone action under content is a quiet button.

---

### 4.16 Day strip (Today's header)
- **Place:** between the date block and the header buttons, centred, at most 640 px wide; on a page under 1100 px it takes its own row under them, and on a phone it sits between the date and the buttons.
- **Contents:** one caption row (accent "Next", the task's title and time, and on the right "Now 14:05 · 7 h 55 min left" in `ink`; "No tasks yet" on the left before anything is recorded), a 16 px `sunken` track from 09:00 to 22:00, hour marks at 09:00, 12:00, 15:00, 18:00 and 22:00 (13 px, `text-3`) with the time now printed under its mark in `ink` 600 (an hour mark within 8% of it gives way), and a key under them that splits the time left, with swatches like the track's: "Meals 1 h · Tasks 3 h 55 min · Open 3 h". A task during a meal counts as meal time, so the three add up to the time left. All lengths read like "3 h 30 min".
- **Track:** each timed task is a block in its area colour: planned is the tint with a mid outline, done the mid colour, partly done half of each, skipped a dashed outline, and a task paused with its goal is striped in `paused-bg` and `paused-line`, its time counted as open. Lunch and dinner are hatched with a meal glyph. Now is an ink line with a dot, held at the track's start before 09:00 and at its end after 22:00, and the time already gone is shaded with `ink` at 14%. The strip shows even when nothing is recorded. Each block names its time, task and status when pointed at; the track's accessible name says how many timed tasks there are and how much time is open.

### 4.17 Area screens (Goal → an area)
Each area is one page, with no tabs: the area's name, its purpose under it ("Someone else expects it."), then cards in a grid of two columns (`repeat(2, minmax(0, 1fr))`), each row as tall as its tallest card by the grid's own stretch, one column under 640 px; a lone last card keeps its half. The cards read the area's tasks, goals and repeats for the day on show; Learning and Life keep no records of their own. The week is Monday to Sunday and holds the day on show; "done" means fully done: a partly done task shows Partial and counts as done in no figure (Summary keeps its own counts). The page header is the Goals and Tasks one (`dw-page-head`, the name in `dw-records-title`, the button in `dw-page-actions`), with the purpose under it: one primary [+ Add] at its top right, level with the area's name as New goal is with Goals; on a phone it stays at the right of the name. It opens a menu in the shared menu's look, by mouse or keyboard (arrow keys, Home, End, Escape): **Task**, the task form set to the area with no goal (on a past day shown it starts at today); **Goal**, the goal sheet set to the area; **Note or file**, the Library's add sheet set to the area. No card has an add button.
- **Every card:** a title with the days it covers in `text-2` ("Load · Mon 28 Sep – Sun 4 Oct", "Meetings · Sun 4 – Sat 10 Oct", "10月5日周一至11日周日"); one caption saying what it counts; its numbers in words with labels ("3 h done of 4 h 45 min planned", "Tasks 2 · Done 0 · Time 1 h 15 min"); rows that open their item, a goal's row its Edit sheet in place and a task's row its details, on its own day; and, when it has nothing, a line saying what fills it, then either its link, which adds nothing (See all {area} tasks, Ask Ava, Report energy on Today), or "Use + Add to add one." / "用上方的“+ 添加”来添加。".
- **Row 1, the same in every area:** **Today in {area}** ("Sun 4 Oct in Work" on another day): the day strip with the area's tasks alone, the day's tasks with their times and status controls, past days read-only, and [See all {area} tasks], which opens Tasks with its area switch set to the area. **{Area} agent notes**, a pencilled card: the agent's findings for today with an icon per kind (slipping, length off, due for review, stalled, a doubt about a time asked for, and for Life low energy, or a full day on low energy; a day that won't fit is the Orchestrator's notice on Today alone, worded "No free time is left today for tasks without a time (1 h 15 min)." when none is left), or "Nothing to flag." with [Ask Ava]; on another day, "These notes are for today." with [Show today]. They replace v3.5's Due for review and Stalled cards.
- **Learn:** **Subjects**, each Learning goal with its time done against planned this week as a figure and a track, a Mon–Sun practice row (● practised, ○ planned but not done, · nothing planned), "Last practised Wed 30 Sep", and its next session as a link, or "No session planned"; then "Not in a goal" with its time and [See all Learn tasks]. **Practice this week**, a bar per day of the time planned, the done part darker, each with its time above it ("1h30"), and the week's totals.
- **Life:** **Habits**, each Life repeat with a chip for its rule and start ("Daily since 25 Sep", "Weekly on Sun since 27 Sep"), a week grid (a square per day: filled done, light partly done, a `refusal` outline with ✗ when missed, dashed while still to come, a faint · in `text-3` when the rule skips the day; weekday letters beneath), and "4 done this week · 1-day streak"; a repeat stopped this week stays, with a caution chip "Stopped Thu", until the week ends. **Today's shape** (the date, not just the weekday): the whole day's strip with its key ("Meals 2 h · Booked 2 h 45 min · Open 8 h 15 min"), where booked is every timed task in any area and every entry of a set plan; Life's appointments and the meals with their times; and the free windows between 09:00 and 22:00 ("10:30–12:00 · 1 h 30 min"). **Energy**: when the day on show has readings, they come first as steps through 09:00–22:00 (see 4.18) with "Readings 08:30 · 2, 11:00 · 1 · average 1.5" under them; then the last seven days as bars from 1 to 5, each its day's average with a thin line from its lowest to its highest reading where they differ ("–" for none), a dashed guide at 2, averages of 2 or below in the caution colours, and "2 or below suggests Lighter day, 4 or above Deep focus".
- **Work:** **Load**, a bar per day of Work planned this week, the done part darker, its time above it, and the week's planned and done totals. **Meetings**, Work tasks with a start time from the day on show through the next six, under a row of seven day dots, each bigger for more meetings with its count inside, then grouped by day. **Carried over**, Work of the 7 days before, each with its day and a status chip: Not reported (caution), Partly done, or Moved to {day} (history); one not moved offers [Ask Ava to move], which opens Ava with "Move “Email Anna” from Fri 2 Oct to today" / "把“Email Anna”从10月2日周五移到今天" typed in and not sent. Ava takes the day the request names as the task's own, whatever day is on show.
- **Project:** **Projects**, each Project goal with a status chip in plain words (On track, Stalled N days after 3 days or more with nothing fully done, Paused, No steps yet), a step bar with a segment per step (one of its tasks), filled once fully done, "Steps done: 2 of 4", its last step and its next step, or "No next step yet". **Next steps**, Project tasks still to do from the day on show through the next six, with their project, under the day dots. **Recently done**, Project tasks fully done in the seven days to the day on show, newest first, with their project.
- **Energy notes:** with today's average at 2 or below, or 4 or above, and only where it applies, an area agent adds one note with the sparkline icon; a middle average adds none. Learn, with a session today: "Low energy today (1.5/5): a short review may suit “Spanish lesson”." or "High energy today (4/5): a good day for a harder session of “Spanish lesson”." Work: low with 3 h or more of Work planned (`WORK_HEAVY_MINUTES`), "Low energy today (2/5) with 3 h 30 min of Work planned: a heavy load."; high, its longest Work task still to do, "High energy today (4/5): a good day for your biggest Work task, “Quarterly report” (2 h)." Project, with a next step: "Low energy today (1.5/5): try a small step on “Pick tiles”." or "High energy today (4/5): a good day for the next big step, “Pick tiles”." Life keeps its low-energy and full-day notes. These notes stay on the area pages and don't reach Ava.
- **Visuals:** plain elements in small components (`src/ui/AreaVisuals.jsx`, their marks worked out in `src/ui/visuals.js`), sized by inline percentages and coloured by `dw-area-*`, status and caution tokens; no SVG or canvas. Each has its numbers in words beside it and an accessible name, and colour is never the only sign: bars carry their values, grid squares their fill, outline or ✗, dots their symbol or count.
- **To Ava:** the Learning agent's "due for review" and the Project agent's "stalled" still reach Ava as messages, once a day per goal.
- **Library, in every area:** the last card, the area's notes and files with See all (see 4.19).

### 4.18 Energy (Today)
- **Place:** at the top of Today's header actions column, directly above Add task and Propose plans (or Compare and set), and there alone on a day with no tasks, whose empty state keeps its own buttons: ONE line, the label "Energy" / "精力" and a segmented 1–5, its right edge on the buttons' right edge and no wider than them, so the day strip keeps its width. The full question "How's your energy?" stays for screen readers. No caption or note in any state: the latest reading shows only as its selected button, and a low or high day is explained by the agents' notes (see 4.17). On a phone the same line sits above the buttons in the stacked header, aligned left with them.
- **The log:** optional, with no preset; a day nobody reports stays empty. Each tap adds a reading to the day's log with its time, any time today, and tapping the level already shown adds nothing; Ava's card adds one the same way (see 4.8). Readings are for today alone: the service refuses another day's, past or future. v4.3's first launch moves each day's single reading from before into the log, at the time it was saved.
- **The average:** the day's average of every reading, to one decimal, is the one value plans, Ava, the area agents, Summary and Calendar use; 2 or below is low, 4 or above high (`LOW_ENERGY`, `HIGH_ENERGY`). Plans proposed after a change put Lighter day first on a low day ("Listed first because the Life agent advised a lighter day.") and Deep focus first on a high one ("Listed first because your energy today averages 4 or above."), else the agents' order; plans already proposed and the set plan stay. Only the day's own average counts: an earlier day's low reading no longer makes today low.
- **Relays:** each change goes through the Orchestrator to all four area agents and Summary. Summary's saved reports for the day, its week and its month are made again, the area agents look at today again with the Orchestrator's checks, and Ava posts anything new. No task profile is rebuilt.
- **Ava:** her context carries "Energy today: 1.5 out of 5, the average of 2 readings; a low day, so when suggesting what to do next, lean to short or easy tasks" (on a high day, "lean to the hardest or most important task"; with none, "Energy today: not reported."). She changes nothing without a card and Confirm.
- **Steps** (Life's Energy card, a day's report): a 72 px plot with a line per level, 1 at the foot and 5 at the top, and 09:00 and 22:00 under it. Each reading is a 9 px dot at its time and level, held as a 3 px step until the next, or until now on today and 22:00 on another day; a reading before 09:00 or after 22:00 sits at the edge, and a 2 px rise joins two levels. Dots of 2 or below are `caution-fg`, the rest and the line `life-fg`. A screen reader hears "Energy through the day: 08:30 · 2, 11:00 · 1; average 1.5 of 5".
- **Bars** (Life's Energy card, a week's or month's report): a bar per day, 96 px tall (64 px for a month, with dates under it and no values above), filled to its average in `life-tint` outlined `life-mid`, or `caution-bg` outlined `caution-fg` at 2 or below, a 2 px `ink` line from its lowest to its highest reading where they differ, and the dashed guide at 2; each bar is named "Fri 2 Oct: average 1.5, from 1 to 2".
- **Meter** (Calendar): five steps, as many filled as the average rounds to, in `life-fg`, or `caution-fg` at 2 or below, the rest `line`. A cell shows a 6 × 4 px meter under its completion bar (4 × 3 px in a narrow month), only on a day with a reading, with no text: it is hidden from screen readers, and the cell's name includes "energy 1.5 of 5". The day panel shows a larger one (14 × 8 px) under the date, named "Energy 1.5 of 5, the day's average", or with no reading five empty `text-3` dashed outlines named "No energy reported". The legend adds "Energy · The day's average in five steps; the caution colour at 2 or below".

### 4.19 Library
- **Header:** "Library" with the area switch beside it (All · 8, then each area's glyph, name and count), and on the right [New note] and [Import files]; on a phone they are icons beside the title and the switch takes the next row. Under it one line in `saved-fg` with the laptop icon: "Everything here stays on this Mac. DayWright doesn't go online." / "这里的一切都留在这台 Mac 上。DayWright 不会联网。" It replaces the "What stays, what goes" panel; the network pill and the network log are gone with the online lookup.
- **Search your library:** a 44 px search field (search icon, placeholder "Search your library") and [Search]. The results are one card, "Passages for “past tense” · 2" with [Clear]: each passage on `ground` with its note or file (icon and name) and "Part 1" on the right, its area tag and goal chip (target icon) under them, and the passage in quotes, at most three lines; then [Ask Ava about this], which opens Ava with "What does my Library say about “past tense”?" typed in and not sent. With an area switched, only its notes and files are searched, and with All, every one; switching area runs the same search again in it. Without the local embedding model a caution banner says search isn't available.
- **Notes and files · N**, newest first, never called "Sources": a table of Name (icon, name, and "Markdown · 111 characters" under it), Area (tag), Goal (chip, or "No goal"), Added ("today 14:02", "2 Sept") and two quiet icon buttons, Edit (pencil) and Remove (trash, two steps). Ten rows, then [Show all]. Under 700 px the table folds into its name cell: the name, then the area tag, goal chip and date. With nothing yet, the empty state "Nothing in your Library yet".
- **Add to the Library:** one side sheet for New note, Import files and every Add. A switch between New note and Import files; a note's title and text, or [Choose files…] with the chosen names listed and the import limits; then Area (the segmented control with glyphs) and Goal (optional, the shared dropdown: the area's active goals, the goal it was added from even when paused or completed, and "No goal"). Opened from the Library, the Orchestrator suggests the area from the note's title and opening text, or the files' names, by the purpose rule, chosen for the user and named on a pencilled line ("Orchestrator suggests Life from what it's for. Change it if it's wrong."); opened from a goal or an area, it starts linked to it. Choosing another area clears the goal. Files that fail stay chosen, each with its reason, while the rest are saved, and a notice says "Saved to the Library: …".
- **Edit:** a side sheet, "Area and goal of “Study tips”", with the same Area and Goal fields; the dropdown keeps an already linked goal on offer when it is paused or completed. Removing a goal unlinks its notes and files and keeps them.
- **In a goal's Edit sheet:** after the goal's tasks, LIBRARY · N lists its notes and files (icon, name, kind), or "No notes or files for this goal yet.", then [+ Add note or file], which opens Add to the Library linked to the goal; the goal's sheet waits behind it and comes back as it was.
- **On an area page:** a **Library** card, last in the grid, with no days in its title and the caption "Notes and files in {area}, newest first. Ava draws on them for facts and details."; up to four, each with its goal chip or its kind, and [See all N in the Library], which opens the Library on the area; a note or file is added with the page's + Add. Empty: "No notes or files in {area} yet." and "Use + Add to add one."
- **In Ava:** a reply that drew on the Library ends with "From your Library: Spanish grammar notes, Lesson 4" / "来自你的资料库：…", and its chip reads "Library · 2" / "资料库 · 2" ("Library · none" without any), opening the passages it drew on.

### 4.20 Guide
- **Where:** a page opened from Guide, beside EN/中文 in the title bar and the phone header (quiet 13 px text; on white with the `raised` shadow while the Guide shows), and a small "?" right after each screen's title: Today's date, "Plans for …", the month in Calendar, Goals, Tasks, each area's name, Library, and Ava's name. The "?" is a 28 px circle with a `line-2` border and "?" in label type; its accessible name lists its cards ("Guide: Today, Energy, Meals").
- **One source:** `src/guide/guide.json` holds every card's text, the labels, and which cards each "?" opens; the screens and Ava both read it, and the Mac app's service carries a copy. The Guide is in English, in Chinese too.
- **Cards:** thirteen, in five sections: The day (Today, Plans, Calendar), Your work (Goals, Tasks, Areas), Library, Ava and the agents (Ava, Agents), and Rules everywhere (Past days, Meals, Repeats, Energy). Each has three labelled lines, For, Do and Rule, at most 40 words together.
- **Look:** each section heading in its colour: The day `caution-fg`, Your work `demo-fg`, Library `accent-fg`, Ava and the agents `project-fg`, Rules everywhere `paused-fg`. A card shows its icon from `icons/` in a 36 px circle of its section's tint (`caution-bg`, `demo-bg`, `accent-tint`, `project-tint`, `paused-bg`) and colour, beside its title in heading type; For and Do as plain lines, each label in label type; and the Rule as one callout, the tint with a 3 px rule on its left and its label in the section's colour. Nothing else: no pictures, previews, per-line icons or chips. The labels always show, so colour is never the only sign.
- **Layout:** one grid, each section heading on a row of its own, the cards two to a row, or one where the room is under 640 px (a phone, a sheet, Ava). Every row of cards takes one share of the same height, so every card is the size of the tallest.
- **"?" sheets:** a screen's "?" opens its cards in a side sheet titled "Guide", under their sections' headings: Today: Today, Energy, Meals. Plans: Plans. Calendar: Calendar, Past days. Goals: Goals. Tasks: Tasks, Repeats. Each area page: Areas. Library: Library. A goal's sheet waits behind it. Ava's "?" shows Ava and Agents in Ava's own panel instead, in place of the conversation, with "‹ Ava" above them to go back; it turns ink while they show. (Ava floats over the page on desktop and is itself a sheet on a phone, so a sheet opened from it would sit under it there.)
- **Ava answers from the Guide:** a question, in English, about how something works ("How do meals work?", "What is the Library for?", "What does the Orchestrator do?", "How do I use goals?") that names a card by its words is answered from those cards alone, without the model or the agents: each card's title in bold, then "For: …", "Do: …" and "Rule: …", and a last line "See Guide: Meals" ("See Guide: Meals, Repeats" for two). It changes nothing and brings no card, and it reads as a Question. Each name in the last line is a link that closes Ava and opens the Guide with that card in view and focused.

### 4.21 Progress graphs
- **Where:** Summary's reports, inside Read the report (see 4.7); Today's Day details, a Finishing card under Balance; Calendar's day panel, the plan card's follow-through in place of its tallies; a goal's Edit sheet, PROGRESS BY WEEK. They read the records as they are now, so a report saved before v4.4 shows them too, and they are never saved.
- **What counts:** as Summary's figures: a day with a set plan counts its entries, any other day its own tasks; an entry for a task removed or moved on, and a task still to do whose goal is paused, are left out. Done means fully done.
- **Done by area:** a bar per day of the period: the planned time of the tasks fully done that day, stacked by area (Learn at the base, then Life, Work, Project) in each area's `mid` with a 1 px `surface` line between parts, against the period's fullest day. A week prints each day's time above its bar ("1h30", "–") and its weekday under it; a month, its date. Then "Fully done: 8 h 30 min over 5 days" and each area's total with its glyph. A bar is named "Tue 29 Sep: 2 h 45 min fully done, Learn 45 min, Life 30 min, Work 1 h 30 min". Empty: "Nothing fully done in this period yet."
- **Finishing:** a bar per day in `ink`, to the share of its tasks fully done, its percentage above it in a week ("67%", "–" with no tasks), then "Fully done: 12 of 20 tasks, 60%, over 6 days with tasks". A bar is named "Fri 2 Oct: 2 of 3 fully done, 67%". It shows from 2 days with tasks; before that, "Finishing shows once 2 days have tasks." Today's card, "Finishing · Each day's tasks fully done, last 7 days", draws the 7 days to the day on show at 40 px with no percentages, then the same line and "Today: 1 of 8 fully done".
- **Plan follow-through:** a day's set plan as one 14 px bar of its entries, left to right: done (`ink`), partly done (`ink` hatched on `surface`), moved on to another day (`accent-tint` outlined in `accent-fg`), skipped (`caution-bg`, a dashed `caution-fg` outline), unreported (`surface` outlined in `line-2`; on today, still to do). Under it, a key on one line that wraps, every part even at 0: its swatch, count and name ("2 Done · 1 Partial · 1 Moved · 1 Skipped · 1 Unreported"). The bar is named "Done 2, Partial 1, Moved 1, Skipped 1, Unreported 1, of 6 entries". A week or month draws a column per day stacked the same way, done at the base, empty on a day with no set plan, then "7 entries over 2 days with a set plan" and the key; empty: "No plan was set in this period." A day report without one says "No plan was set this day." Done as planned is an entry reported done, as no time a task was done is recorded.
- **Progress by week:** a goal's burn-up, a column per week, Monday to Sunday, from the week the goal was made (or its first step's, if earlier) to this week or its last step's, under a dashed `text-3` line at all its steps. Up to this week a column is filled in the goal's area `mid` to the steps fully done so far; this week and the weeks ahead are outlined in `mid` on `surface` to the steps planned through them. A past step never reported is neither done nor ahead; every step counts toward the total. Weeks are named under their columns ("28 Sep"; past 8 weeks, only the first, this one in bold, and the last). A column is named "Week of Mon 28 Sep: 1 of 4 steps done", this week's adding ", 3 planned by its end", one ahead "Week of Mon 12 Oct: 4 of 7 steps planned by then". Then "Steps done: 1 of 4", "2 more planned, through Thu 8 Oct", and "Dashed line: all 4 steps · outlined: planned ahead". Empty: "Add a task to this goal to see its progress."
- **Build:** React elements sized by inline percentages and tokens, no SVG or canvas (`src/ui/ProgressGraphs.jsx`, their marks worked out in `src/ui/progress.js`). Every graph says its numbers in words and names each bar, so colour is never the only sign.

## 5. Screens (`screens/png` · `screens/html`)

| File | Screen | Shows |
|---|---|---|
| 10-Today-Desktop | Today, plan set | Schedule with a Now line, an unreported past entry, Next card, advice, balance, goals |
| 11-Today-Phone | Today, plan set (phone) | Same content, stacked; status control at the bottom-right of each row |
| 12-Today-Phone-ZH | 今天 · 草案 | A day with drafts, in Simplified Chinese: three mini plan previews + "比较并确定一份", tasks reportable before any plan is set |
| 13-Today-Empty-Desktop | Empty account | Steps, disabled Propose with its reason, model starting, empty cards, demo entry |
| 20-Plans-Compare-Desktop | Compare and set | 3 columns, one chosen, confirmation bar |
| 21-Plans-Replace-Desktop | Review a replacement | Aligned before/after table with change badges (Reported / Same / Shorter / Removed / Moved / Added), agent reasons, approval with checkbox |
| 22-Plans-Compare-Phone-Demo | Compare on phone | Segmented plan switch, pinned Set button, **demo workspace** banner |
| 30-Calendar-Desktop | Month + past day | Cell states (Set + completion bar, Recorded, preset, Suggested, empty); past cells `sunken` with a lock; right panel read-only |
| 31-Calendar-Phone | Future day | Compact month, a preset commitment, an agent suggestion with evidence and Add/Dismiss |
| 40-Goals-Desktop | Goals | Cards of equal height with Show all, **refusal** on a goal with tasks, **two-step remove** |
| 41-Goals-Phone-Preview | Goals (phone) | **Preview mode · Not saved** banner, open status menu |
| 42-Area-LifeRest-Desktop | Life & Rest | **New task** side sheet. Its check-in, habits and events tabs were removed in v3.5, and the Overview and Tasks tabs in v3.8, when each area became one page of cards; see 4.17 |
| 43-Area-LifeRest-Phone | Check-in form | Phone form controls; the check-in itself became the energy row (4.18) |
| 50-Library-Desktop | Library | Browsable table with two-step remove and stated import limits. Its lookup and "What stays, what goes" ledger were removed in v3.9, when the Library went fully offline with areas and goals; see 4.19 |
| 51-Library-Phone | Online lookup consent | Removed in v3.9 with the online lookup; nothing asks to go online. See 4.19 |
| 60-Talk-Desktop | Talk docked | Context chip, Ask/Adjust/Report, proposal card, preview on the schedule, **route** (Orchestrator → Learning → Life → Summary → Orchestrator), the Library passages a reply drew on |
| 61-Talk-Phone | Talk sheet | Report mode, voice transcribed on the Mac, proposal touching task + expense + goal, push-to-talk while listening |
| 70-States | State reference | Save, model, network (removed in v3.9), plan lifecycle, read-only vs editable, refusals, who made it, empty states |
| 01–04 | Direction, Tokens, Components, Navigation | Reference boards |

---

## 6. State rules

| State | Rule |
|---|---|
| Plan lifecycle | `drafts (≤3, pencilled)` → `set (exactly one)` → `under review` (the set plan stays in force) → `replaced` (kept in history, read-only). Today's set plan can be deselected, back to `drafts`; reported statuses stay. Entries of a set plan can't be removed, only reported. |
| Reported entries | Keep their status across a replacement, and across an edit of the task: the task form has no status and doesn't send one. |
| Past days | Read-only on screen: no status buttons and no edit sheet in Calendar, Today, Tasks, Goals or an area. A past task is corrected (title, detail, goal, area, status), removed, or moved to today or a later day only through Ava, which proposes the change and applies it on Confirm; its start, length and timing stay as they were while it stays on its past day. The one other way in is Delete on a past task in its goal's task list. A task moved forward leaves its past day's set plan an entry marked "Moved to {day}" / "已移到{day}", treated like "Removed". The service refuses any other edit of a past task, and a move of a task onto a past day, which the interface words in both languages ("A past task changes only through Ava. Ask Ava to change it." / "过去的任务只能通过 Ava 更改。请告诉 Ava 要改什么。"), and the task form offers no past date. A past task its day's set plan scheduled is removed like any other, and that plan keeps its entry, marked "Removed" / "已移除", with its time and status, but the entry no longer counts: Calendar's day counts, Summary's reports and the area agents' profiles leave it out. A task deleted today or for a later day leaves the plans proposed for that day and not set, so setting one can't schedule it. Calendar's banner reads, with a lock, "Read-only · past day · You can view this day and its plan, not change them.", then says when no plan was set, then, in small text, "To change or remove a task, ask Ava."; the day's card names the plan it followed ("Plan used · Lighter day · 10:21") over how it was followed (see 4.21), with Open full day and Ask about this day at its foot. A task can't be added to a past day, and a past day's plans stay read-only ("Read-only · past day" on Plans). |
| Task changes | Every saved change to a task, a plan or a goal, from a form, a status control, Ava, a goal's task list or setting a plan, goes through the Orchestrator, which hands it only to the agents it concerns: the area agent of the task's area (both areas when it moves between them; every area the day holds for a plan) and Summary. A change to a task's title, area, day, start, length or status rebuilds that area agent's task profiles; that or a change to its detail, repeats or goal makes Summary's saved reports for the day, week and month of each date it touched again, with their advice. An edit that changes neither reaches no one, and a report for a period nothing touched stays as saved. After every change, the concerned area agents look at today again, with the Orchestrator's checks of the whole day, and Ava posts anything new once that day. When an edit on a task's form, or one confirmed through Ava, moves it or changes its length, its area agent checks it and posts any doubt to Ava; the edit stays saved, and a task left on a past day, a record put right, raises no doubt. A past task moved forward reaches both days: its past day's reports and profiles leave it, and its new day counts it. A task that leaves today or a later day, deleted or moved away, leaves that day's proposed plans too, each rewritten from the tasks it has left so nothing in it names the task, with the others keeping their times. Pausing, resuming or completing a goal reaches its area's agent and Summary; creating, renaming or removing one reaches Summary, for today and the goal's tasks' days, as its reports list the goals. |
| Future days | Accept preset commitments. Agent-proposed ones are pencilled, show evidence, and need Accept. |
| Unrecorded dates | Render as an empty cell. Don't estimate or fill. |
| Demo workspace | Its data is kept separate from the user's. It is striped and labelled in the chrome and in a banner on every screen, and is never used by the user's plans. |
| Preview mode | Caution pill plus a banner on every screen. |
| Model unavailable | Everything manual still works. Features that need the model are disabled, each with the reason written beside it. |
| Online use | None. DayWright never goes online, and the Library says so in one line. |

---

## 7. Language (EN / 简体中文)

- The toggle lives in the top bar and the phone header. Switching is instant, and the current screen and state are kept.
- Set `lang="zh-Hans"` on the root when in Chinese. It switches the font stack and type metrics (see `tokens.css`).
- Layouts must tolerate both languages: no fixed-width text containers, labels may wrap, and buttons use `white-space: nowrap` but sit in rows that wrap.

| Key | EN | 中文 |
|---|---|---|
| nav.today / calendar / records / library / talk | Today / Calendar / Goal / Library / Ava | 今天 / 日历 / 目标 / 资料库 / 艾娃 |
| area.learn / life / work / project | Learn / Life / Work / Project | 学习 / 生活 / 工作 / 项目 |
| status.planned / done / partial / skipped | Planned / Done / Partial / Skipped | 计划中 / 已完成 / 部分完成 / 已跳过 |
| plan.balanced / focused / gentle / early / quickwins / easiest / rhythm / spacious | Balanced / Deep focus / Lighter day / Finish early / Quick wins first / Easiest first / Your usual rhythm / Breathing room | 均衡 / 深度专注 / 轻松一天 / 早点收工 / 先做小事 / 先做拿手的 / 按你的习惯 / 留出余裕 |
| plan.apart | What sets it apart | 独特之处 |
| meal.lunch / dinner | Lunch / Dinner | 午餐 / 晚餐 |
| flag.fixed / flexible | Fixed / Flexible | 固定 / 灵活 |
| save.local / preview / demo | Locally saved · Private / Preview mode · Not saved / Demo workspace · Sample data | 已保存在本机 · 私密 / 预览模式 · 未保存 / 演示空间 · 示例数据 |
| model.starting / ready / off | Local model starting… / Local model ready / Local model unavailable | 本地模型启动中… / 本地模型已就绪 / 本地模型不可用 |
| plan.drafts | 3 proposed plans · none set yet | 3 份提议方案 · 尚未确定 |
| plan.set | Following · {name} · Set at {time} | 正在执行 · {name} · {time} 已确定 |
| plan.deselect | Deselect plan | 取消选定方案 |
| action.keep / dismiss | Keep / Dismiss | 保留 / 忽略 |
| action.compare | Compare and set one | 比较并确定一份 |
| advice | Summary agent · Advice | 总结智能体 · 建议 |
| agents | Orchestrator / Learning / Life / Work / Project / Summary agent | 协调 / 学习 / 生活 / 工作 / 项目 / 总结智能体 |
| no start time | No start time | 未定开始时间 |
| unreported | Not reported yet — time passing doesn't mark it done | 尚未报告——时间过去不代表已完成 |
| next | Next | 下一项 |

---

## 8. Accessibility checklist

- Use real `<button>`, `<a>`, `<input>` and `<label>`. Icon-only buttons get `aria-label`.
- Show the focus ring on every interactive element (`:focus-visible`, 3 px `#1F5EFF`, 2 px offset).
- Colour is never the only signal:
  - areas: glyph + label
  - statuses: shape + label
  - agent origin: dashed border + agent name
  - read-only: lock + banner
- Text contrast is at least 4.5:1 (all tokens pass on `surface`). The disabled style always sits next to a visible reason.
- Targets are at least 44 px on phone. The layout works at 320 px with no horizontal scroll.
- Honour `prefers-reduced-motion`.
- Alerts (refusals) use `role="alert"`. Confirmation steps use `role="alertdialog"` with a label.

## 9. Don't reintroduce (problems in the old UI)

- 9 px uppercase monospace labels. The minimum is now 13 px, in sentence case.
- Status, Edit and Remove competing in one narrow column. Now there is one status control, and the other actions are in the detail sheet.
- Floating controls over content on phone. Now everything is in the bottom bar.
- A Library showing a count with no list. The list is now browsable, with removal.
- Area pages as one long column. Now each is one page of cards, two to a row, and forms open in sheets.
- Eight flat destinations. Now there are four places plus Ava.

## 10. Open items (placeholders in the mockups)

- **App icon:** the mockups use an empty rounded-square slot. Use the existing icon (34 px in the top bar, 30 px on phone).
- **Import limits** ("up to 20 MB and 300 pages per file"): replace with the real limits.
- **All names, times and amounts** in the mockups are illustrative sample content, not product data.
