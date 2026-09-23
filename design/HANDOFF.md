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
3. **Progress is reported, never inferred.** Status changes only through the user (the status control, or Talk › Report followed by Confirm). A past entry the user hasn't reported says "Not reported yet — time passing doesn't mark it done". Never auto-complete anything.
4. **Nothing is invented.** A new account shows empty states. Unrecorded dates render as blank cells. Sample data exists only in the **demo workspace**, which is striped and labelled everywhere.
5. **Local-first is visible.** The top bar always shows the save state and model state. A network pill appears as soon as anything has gone online that day, and it opens the network log.
6. **Calm beats density.** Body text is 16 px and nothing is smaller than 13 px. There is one status control per row. Edit and Remove live in the row's detail sheet, not on the row.
7. **History is read-only.** Past days and replaced plans render with no editable affordances at all. They aren't just disabled.

---

## 2. Tokens (summary — see `tokens/tokens.json`)

**Neutrals:** `ground #EDEFF2` (app background) · `ground-2 #E3E7EC` (tracks, segmented controls) · `surface #FFFFFF` (cards, sheets) · `sunken #F5F6F8` (read-only, wells) · `line #DCE0E6` · `line-2 #C3CAD3` (control borders) · `ink #18202B` (text, primary buttons) · `text-2 #475163` · `text-3 #5B6575` (captions; 5.9:1 on white).

**Areas.** Colour always travels with its glyph and its label. Never use colour alone.

| Area | EN / 中文 | Glyph | fg (text) | mid (bars, fills) | tint (backgrounds) |
|---|---|---|---|---|---|
| learn | Learn / 学习 | triangle | `#4B3FB0` | `#7B70D6` | `#ECEAFB` |
| life | Life / 生活 | circle | `#0B6E63` | `#2AA597` | `#DDF1EE` |
| money | Money / 财务 | diamond | `#8A5A06` | `#D39A2B` | `#F8EBD2` |
| rest | Rest / 休息 | crescent | `#9A3864` | `#D0729D` | `#F8E4EE` |

`fg` on `tint` is at least 5:1. `mid` is never used for text.

**Signals:**
- saved `#1D6B45` on `#E3F2E9`
- caution (preview mode, online use, under review) `#6B4800` on `#FFF1CC`
- refusal and destructive `#9B1C1C` on `#FDECEA`
- demo `#4A3A7A` on `#EFEAFB`, with a 135° stripe
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
| **Today** (default) | Next action, schedule, balance, goals, advice. Report progress. **Plans** sub-view: compare and set, review a replacement. |
| **Calendar** | Month view of past and future. Per day: recorded / set / completion. A selected day's summary and schedule. Preset future commitments. |
| **Records** | Side list: Goals, Tasks, then Areas (Learn, Life & Rest, Money). Each area has tabs: Overview · Check-in · Habits · Events · Tasks (varies per area). |
| **Library** | Browse and remove sources, notes, imports (with limits stated), topic lookup, what stays and what went online. |
| **Talk** (layer) | Reachable from everywhere. Carries the current context. Modes: Ask / Adjust / Report. Push-to-talk. |

**Desktop:** a 60 px unified title bar containing, left to right:
- the traffic lights
- the app icon and the "DayWright" wordmark
- the four places as a segmented group, with the active one on white
- a status cluster: save pill · network pill (only after online use) · model pill · EN/中文 toggle
- the **Talk ⌘K** button

When Talk is open it docks as a 480 px right panel and the page reflows beside it. **It never overlays content.** Side sheets for forms (for example "New task") are 440 px on the right and also push content. While a sheet is open, the Records side list collapses to a breadcrumb.

**Phone (≤ 640 px; the minimum width is 320 px):**
- **Header:** app icon, wordmark and EN/中文, with compact save and model pills below them.
- **Bottom bar:** one row of 5 items (Today · Calendar · **Talk** in the centre as an ink pill · Records · Library), always labelled. Page content ends above the bar. **No floating buttons.**
- **Talk:** opens as a sheet that leaves a strip of the page visible above it and closes back to the same place.
- **Plan comparison:** one plan at a time, with a Balanced / Focused / Gentle segmented switch and previous/next buttons. The Set button is pinned above the bottom bar.

**Suggested breakpoints:**
- ≥ 1100 px: two columns (main plus a 440 px right column)
- 641–1099 px: a single column with the top bar kept (place labels can shrink to icon + label)
- ≤ 640 px: the phone layout

---

## 4. Components

For each component: anatomy → states → accessibility.

### 4.1 Task row / plan entry (`03-Components`, `10-Today-Desktop`)
- **Anatomy:** a time column (64 px: start time in 15/600, duration in 13) · a block (radius 14, `surface`, 1 px `line`) holding:
  - area tag + title (16/600) on one line, plus a "Next" ink chip if it's the next action
  - optional detail (14, `text-2`)
  - flags: Fixed (pin), Protected (shield), Daily/Weekly (repeat), goal link (link icon + goal name)
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
- **Compact button:** status glyph + label + chevron, 40 px tall. It opens a menu of 4 items (44 px each) with a check on the current one.
- **Segmented form:** 4 options with glyph and label, used where reporting is the main action (Next card, Report sheet). On phone it becomes a 2×2 grid.
- **Values:** Planned ○ · Done ● · Partial ◐ · Skipped ⊘. The shape carries the meaning, so the glyph works without colour. All four use ink.
- **Read-only form:** glyph + text in `text-2`.
- **Accessibility:** `role="radiogroup"` / `menuitemradio`, and an accessible name such as "Status: Planned. Change status".
- Changing the status of a goal-linked item updates the goal's progress immediately. Show a toast only for undo.

### 4.3 Plan column (comparison)
- **Header:** radio + plan name (Balanced / Focused / Gentle) + a "Draft" chip (dashed) or a "Chosen" chip (ink).
- **Sections:** intent line → TIME BY AREA (a stacked bar with 2 px gaps, plus a 2×2 legend with glyph, label and duration) → SCHEDULE (compact rows: time · glyph · title · fixed/protected icons) → WHY THIS PLAN (per-agent notes, each with the agent icon and name) → CONSTRAINTS (icon + text).
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
- **Body:** why ("3 tasks are still linked to it"), what to do instead, and **"Nothing was removed."**
- **Actions:** a way forward ("Show the 3 linked tasks") and OK.
- **Task removal while a set plan scheduled it:** offer "Report Skipped" and "Review a replacement".

### 4.6 Goal card
- **Contents:**
  - area tag and a status select (Active / Paused / Completed; the menu explains each: "plans may use it / plans skip it / kept in history")
  - title (20/600)
  - a progress bar in area `mid`, with "14 of 40 sessions" on the left and "reported, not inferred" on the right
  - LINKED TASKS (link icon · name · cadence)
  - footer: [Edit] [Remove…] … [+ Add task]
- On desktop, lay the cards out as two independent columns (masonry) so no gaps form.

### 4.7 Advice card (Summary agent)
- **Contents:** a dashed card with the agent label ("Summary agent · Advice"), the advice (16/500), and an evidence well (`sunken`, info icon) such as "Based on your reports: …". Actions: [✓ Keep] [Dismiss].
- Kept advice appears read-only on that past day in Calendar ("You kept this at 21:48").

### 4.8 Proposal card (Talk › Adjust / Report, agent suggestions)
- **Contents:**
  - a dashed card with the chip "Proposed change · not applied"
  - a title, e.g. "Change 1 entry in today's set plan"
  - a list of changes (icon + text, with before → after in bold)
  - a note: "The preview is shown on your schedule. Nothing has changed yet."
  - actions: [✓ Confirm change] [Dismiss] (or [Edit first])
- **While the card is open,** the affected row on the schedule shows the preview box.

### 4.9 Next action card
- **Contents:**
  - an ink chip "Next · in 50 min"
  - the area tag
  - the time range
  - the title (22)
  - the goal link
  - "Report what actually happened" with the segmented status control

### 4.10 Balance card
- **Contents:**
  - a stacked bar of planned time by area
  - per area: glyph + label · a track showing planned time (tint) with the reported portion filled (mid) · "45 of 1 h 45"
  - a footnote on what is counted (e.g. fixed work is included in Life, sleep isn't counted)

### 4.11 Local-first pills (always in the chrome)
- **Save:**
  - "Locally saved · Private" (laptop icon, saved colours)
  - "Preview mode · Not saved" (caution colours, plus a full-width banner: "Changes disappear when you close DayWright. [Choose where to save…]")
  - "Demo workspace · Sample data" (demo colours, plus a striped banner with [Leave demo])
- **Model:**
  - "Local model starting…" (spinner). Proposals are disabled, with the reason written next to the button.
  - "Local model ready"
  - "Local model unavailable" (hollow red dot). Show a card: manual planning still works, [Try again] [Details], and "Nothing is sent elsewhere as a fallback".
- **Network:**
  - absent until something goes online
  - then "1 online lookup today" (globe, caution colours), which opens the log
- **On phone:** compact labels ("Saved · Private", "Model ready").

### 4.12 Empty state
- **Contents:** an icon tile (48 px, 1.5 px `line-2` border), a heading, one or two sentences that say what will appear and that nothing will be invented, and at most one primary action.
- **Empty Today:** 3 numbered steps (Add a goal (optional) → Add today's tasks → Propose plans; the last is disabled until there is at least one task, with the reason shown), plus three reassurances: Saved on this Mac · Nothing invented · Nothing set without you.

### 4.13 Forms (side sheet on desktop, full sheet on phone)
**New task:**
- Title
- Detail (optional)
- Area (a segmented control with glyphs)
- Start + Duration
- Timing (Flexible / Fixed, with a helper line)
- Repeats (None / Daily / Weekly)
- Protected (a switch, with the helper "Plans won't shorten, move or drop it")
- Goal (optional, a select)
- [Save task] [Cancel]

**Check-in:**
- Sleep stepper
- Energy 1–5 (segmented, with "1 low · 5 high")
- Mood chips (Low · Flat · Steady · Good · Bright)
- Note
- [Save check-in]
- a line saying agents may read it but never edit it

All inputs have visible labels, are 44 px tall, and show the focus ring.

---

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
| 40-Goals-Desktop | Goals | Masonry cards, **refusal** on a goal with tasks, **two-step remove** |
| 41-Goals-Phone-Preview | Goals (phone) | **Preview mode · Not saved** banner, open status menu |
| 42-Area-LifeRest-Desktop | Life & Rest | Area tabs, check-in / habits (reported only) / events / tasks, **New task** side sheet |
| 43-Area-LifeRest-Phone | Check-in form | Phone form controls |
| 50-Library-Desktop | Library | Browsable source table with two-step remove, stated import limits, local-first lookup, "What stays, what goes" ledger |
| 51-Library-Phone | Online lookup consent | "Fetch a short public introduction?" listing exactly what is sent, where, what is kept, what is never sent |
| 60-Talk-Desktop | Talk docked | Context chip, Ask/Adjust/Report, proposal card, preview on the schedule, **route** (Orchestrator → Learning → Life → Summary → Orchestrator), Library sources |
| 61-Talk-Phone | Talk sheet | Report mode, voice transcribed on the Mac, proposal touching task + expense + goal, push-to-talk while listening |
| 70-States | State reference | Save, model, network, plan lifecycle, read-only vs editable, refusals, who made it, empty states |
| 01–04 | Direction, Tokens, Components, Navigation | Reference boards |

---

## 6. State rules

| State | Rule |
|---|---|
| Plan lifecycle | `drafts (≤3, pencilled)` → `set (exactly one)` → `under review` (the set plan stays in force) → `replaced` (kept in history, read-only). Entries of a set plan can't be removed, only reported. |
| Reported entries | Keep their status across a replacement. |
| Past days | Read-only. Banner: "Read-only · past day". No status buttons, no edit sheet. |
| Future days | Accept preset commitments. Agent-proposed ones are pencilled, show evidence, and need Accept. |
| Unrecorded dates | Render as an empty cell. Don't estimate or fill. |
| Demo workspace | Its data is kept separate from the user's. It is striped and labelled in the chrome and in a banner on every screen, and is never used by the user's plans. |
| Preview mode | Caution pill plus a banner on every screen. |
| Model unavailable | Everything manual still works. Features that need the model are disabled, each with the reason written beside it. |
| Online use | Ask every time (no always-allow). Show exactly what is sent and to where. Log it and show the network pill. |

---

## 7. Language (EN / 简体中文)

- The toggle lives in the top bar and the phone header. Switching is instant, and the current screen and state are kept.
- Set `lang="zh-Hans"` on the root when in Chinese. It switches the font stack and type metrics (see `tokens.css`).
- Layouts must tolerate both languages: no fixed-width text containers, labels may wrap, and buttons use `white-space: nowrap` but sit in rows that wrap.

| Key | EN | 中文 |
|---|---|---|
| nav.today / calendar / records / library / talk | Today / Calendar / Records / Library / Talk | 今天 / 日历 / 记录 / 资料库 / 对话 |
| area.learn / life / money / rest | Learn / Life / Money / Rest | 学习 / 生活 / 财务 / 休息 |
| status.planned / done / partial / skipped | Planned / Done / Partial / Skipped | 计划中 / 已完成 / 部分完成 / 已跳过 |
| plan.balanced / focused / gentle | Balanced / Focused / Gentle | 均衡 / 专注 / 从容 |
| flag.fixed / flexible / protected | Fixed / Flexible / Protected | 固定 / 灵活 / 受保护 |
| save.local / preview / demo | Locally saved · Private / Preview mode · Not saved / Demo workspace · Sample data | 已保存在本机 · 私密 / 预览模式 · 未保存 / 演示空间 · 示例数据 |
| model.starting / ready / off | Local model starting… / Local model ready / Local model unavailable | 本地模型启动中… / 本地模型已就绪 / 本地模型不可用 |
| plan.drafts | 3 drafts · not set yet | 3 份草案 · 尚未确定 |
| plan.set | Plan set · {name} · {time} | 计划已确定 · {name} · {time} |
| action.keep / dismiss | Keep / Dismiss | 保留 / 忽略 |
| action.compare | Compare and set one | 比较并确定一份 |
| advice | Summary agent · Advice | 总结智能体 · 建议 |
| agents | Orchestrator / Learning / Life / Finance / Summary agent | 协调 / 学习 / 生活 / 财务 / 总结智能体 |
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
- Area pages as one long column. Now they have tabs and forms open in sheets.
- Eight flat destinations. Now there are four places plus Talk.

## 10. Open items (placeholders in the mockups)

- **App icon:** the mockups use an empty rounded-square slot. Use the existing icon (26 px in the top bar, 24 px on phone).
- **Import limits** ("up to 20 MB and 300 pages per file"): replace with the real limits.
- **All names, times and amounts** in the mockups are illustrative sample content, not product data.
