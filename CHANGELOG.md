# DayWright changelog

Every change to DayWright, newest first, in one shape: the summary from the history table, then what changed, what was checked and how it was delivered. The README's Change history table lists the newest 10 and links here.

<a id="old-design-qa-removed"></a>

## Old design QA removed — 2026-10-07

- **Maintenance:** The design QA notes and four screenshots of the folio interface, from 14–15 September, left the project; Open Bench has replaced every screen they show.

### Removed

- **Design QA:** `design-qa.md` and its screenshots `design-qa-render.png`, `design-qa-mobile.png`, `design-qa-rag-library-mobile.png` and `design-qa-agent-drawer.png`, which compared the first folio slice with its visual reference.
  - Earlier commits keep them. The visual reference and the original design stay in `docs/`, where the product design specification links them.
- **README:** Project structure no longer lists them, and References no longer points to the QA notes.

### Checked

- `readme_check.py`, `link_check.py` and `history_rotation.py --check` pass from the repository root: 9 project READMEs follow the shared layout, and every link in 27 documents resolves.

<a id="capabilities-in-one-section"></a>

## Capabilities in one section — 2026-10-07

- **Documentation:** The rules behind the Capabilities map moved from Usage into Capabilities itself, under one In detail subsection with a heading per map item; Project Control still shows the map alone.

### Changed

- **Why:** the map and its rules read best together; Quick start no longer separates them.
- **In detail:** the Usage subsections became fourth-level headings under `### In detail`, marked `ignore` for Project Control, every line as it was; the Usage section is gone.
- **Scope:** Documentation only.

<a id="capabilities-as-a-map"></a>

## Capabilities as a map — 2026-10-07

- **Documentation:** Capabilities is a map of nine labelled lines, one per place; every rule moved under a new Usage section with one labelled list per place, word for word.

### Changed

- **Why:** the repository now asks every README's Capabilities to be a short map of what the user can do, with the rules behind it under Usage, so a newcomer reads the map first.
- **Capabilities:** Today, Tasks and goals, Plans, Calendar and Summary, Ava, Library and learning, Guide and languages, Desktop app, and Private by design, one sentence each.
- **Usage:** the forty-odd rules sit under subsections of those names as labelled bullets whose labels name the rule, such as Lengths, Meals, Time taken and Catch up; every sentence kept its words.
- **Scope:** Documentation only.

<a id="readme-in-the-shared-form"></a>

## README in the shared form — 2026-10-07

- **Documentation:** The README follows the shared form: the skeleton's sections, a badge row and three quick links, every block within fifty words, architecture tables by category, and the complete history in `CHANGELOG.md` with its strip under Change history.

### Changed

- **Why:** DayWright was exempt from the repository's README rules while its branch was open; the branch has landed, so its README and history join the form every other project has.
- **Sections:** Current capabilities is Capabilities, Desktop app and the build sit under Quick start, Local models is Models, Project map is Project structure, Design source sits under References, Checks under Maintenance as Run the checks, and Current boundaries is Limits; Current release holds the release line.
- **Badges and links:** the badge row opens with Platform, React and Release, then Service, Storage and Desktop; the quick links are Quick start, Architecture and Change history.
- **Blocks:** every paragraph, list item and table cell holds at most fifty words; a longer one became a lead with sub-points at its own sentence boundaries, the wording moved, not rewritten.
- **Architecture:** the one table is grouped under AI & Intelligence, Frontend & Presentation, Backend & Application Logic, Data & Storage, Integrations & Security and Build & Delivery, every row kept.
  - Rows the source called for joined it: LangGraph with its checkpoint file, retrieval over `sqlite-vec`, the two Qwen models, `faster-whisper`, Vite, the Fontsource typefaces and the two interface languages.
  - Also Python and uvicorn, `httpx`, `pypdf` and `python-docx`, the local folders, the loopback boundary, the website lookup, macOS permissions, Tauri and Rust, PyInstaller, the test suites and the static packaging contract.
- **Structure:** the table gained `tests/`, `public/` with the Vite files, `Resources/`, `CONTRIBUTING.md`, `CHANGELOG.md` and `CHANGELOG.svg`.
- **History:** the 64 records of the README and its two archives are entries of `CHANGELOG.md`, each with its summary, its title, and its bullets under Changed, Checked and Delivered; the README table keeps the newest ten and opens with the history strip. The `history/` folder is gone.
- **Scope:** Documentation only.

<a id="v4-8-build-48"></a>

## v4.8 / build 48 — 2026-10-06

- **Title:** catch up on several tasks at once, and a limit for every task
- **Catch up:** On Today and Tasks, one sheet of every task today, each left as it is or set Done, Partly done or Skipped; one Save applies all, with Undo for a few seconds.
- **Ava:** Catch up, or a sentence such as "Did Review and Email, skipped Gym, half of Reading", brings one card of the day's tasks, applied on Confirm; yesterday's notice opens it for yesterday.
- **Learning:** A partly done Learning task with items left gets one Continue next session card.
- **Time taken:** Every task stops at twice its length without a status; one interrupted resumes after, and its time adds up every stretch.

### Changed

- **Why:** a day often ends with several tasks still unreported. Catching up takes one sheet or one sentence instead of a tap for each, and never stands in the way of carrying work forward.
- **On Today and Tasks:** Catch up, beside Add task, opens a sheet of every task today in time order, untimed ones last, each with its time and its status now.
  - A task without a status starts As is; one with a status shows it chosen, to change to Done, Partly done or Skipped.
  - One Save applies them all, then "3 tasks updated · Undo" shows for a few seconds; Undo gives each task back its status and time, unless it changed again since, and withdraws a Continue next session or "usually takes" card the save posted.
  - The sheet covers today only, and the menu bar has no Catch up. Its choices use the status controls' own words, Done · Partly done · Skipped, now one set everywhere.
- **Through Ava:** Catch up in Ava's panel, or a sentence such as "Did Review and Email, skipped Gym, half of Reading" ("做完了 Review 和 Email，跳过了 Gym，Reading 做了一半"), brings one card listing every task of the day with its status now and the one she read, each to change,
  - applied on Confirm. It works on today or an earlier day; a task changed or moved since the card was made is left as it is. A question or a change naming several tasks stays what it was, and a sentence about one task still gets the status controls answer.
- **The next day:** Today's notice of what yesterday left has Catch up with Ava, which sends "Catch up on yesterday" and brings her card of yesterday's tasks; the sentence begun about one task is gone. Confirming it keeps Today on show and refreshes the notice.
  - A task with a status now leaves the notice unless its time is one to check; one still without a status reads "stopped at its limit without a status" or "no status".
  - The time a task took is still corrected by telling Ava ("Yesterday Review took 45 minutes"); for a time added up from stretches her card says the minutes beside the range, "10:00–11:30 · 1 h 10 min → 10:00–12:00 · 2 h".
- **Times:** changing a status a task already had keeps its recorded time. A task with no status follows the time rules below: one still running ends at the save, one already stopped keeps its stop.
  - Each task in a save is timed from the day as it stood before the save, so one task's status never changes another's; an earlier day's statuses are kept as set after that day.
- **A limit for every task:** every task, with a start time or not, has a limit of twice its length, set or estimated.
  - Without a status it stops only at its limit or at 22:00, no longer at the next task's start or a meal: those interrupt it, and it resumes when they end, until its limit.
  - Current is a started timed task with no status under its limit, then the task interrupted most recently, then the first untimed task.
  - A task stopped at its limit keeps no status, is a time to check (the check now counts twice the length, not only over it), and is listed the next day; marked later, it keeps its stop.
  - Reading, 45 min, current 09:00–10:00, interrupted by Review until 11:00, resumes and stops at its limit at 11:30, 90 minutes in all. A timed task left unmarked now runs past its planned end until its limit, unless something interrupts it.
- **Every stretch adds up:** a task's time taken is the sum of every stretch it was current, each from when it became current to its status, an interruption, its limit or 22:00:
  - Reading current 10:00–10:40, then Standup until 11:00, then Reading again until Done at 11:30, took 70 minutes, not 30.
  - Estimates, the time to check, time spent, the menu bar's time taken so far and Ava's corrections, where a time told sets the whole of it, all read the sum; a row and sheet show the first stretch's start and the last one's stop.
  - A stretch from the day's start that DayWright didn't see counts only when it is the task's one stretch, and never toward its limit, so tasks made the evening before aren't used up overnight. Times kept before keep theirs.
- **Continue next session:** after a catch-up, either way, a Learning task left partly done with checklist items unticked gets one card through Ava from the Learning agent, "“Study chapter 4” is partly done, with items still unticked. Continue it next session?", adding its follow-up on Confirm.
- **Carrying work forward:** never waits on a catch-up. Continue next session, Ava's move to today and Work's carry-overs all take a task left without a status.
- **Guide:** Today: "set your energy, report statuses or Catch up on several; follow the day strip; the menu bar shows now and next."
- **Release:** the Mac app reports Version 4.8.0 (48), and the service 4.8.0; the badge and the Desktop app's release line read v4.8.
- **Also fixed:** on a phone, yesterday's notice puts its buttons below its lines, and a long time taken in a row's time column no longer spreads out. Status words are one set everywhere, Done · Partly done · Skipped: the status controls' "Partial" and the sheet's "Skip" changed to match.

### Checked

- **Evidence:** the service tests (749), the interface helper tests (261) and the site checks (5) pass, and the interface build succeeds.
  - The tests, written to fail first, cover the sheet's list of every task today with its status, mixed statuses in one save with each task's own time, re-marking keeping a time, Undo once and only for tasks not changed since, withdrawing the continue and usual-length cards its save posted,
  - today only, Ava's sentence in English and Chinese becoming one card applied on Confirm with the choices changed on it, Catch up alone, yesterday from Today with no reply and times kept as after the day, a later day refused, the continue offer once,
  - carrying forward without a status (Continue next session, Ava's move, Work's carry-overs), Catch up only on Today, Tasks and Ava's panel, the Guide's Today card within 40 words, every stretch added up (40 and 30 minutes making 70, three stretches, a meal between, the menu bar's running sum,
  - re-marking keeping the sum, the time to check, estimates and time spent on the sum, Ava's told time setting the whole, and her card's minutes), and the limit: an untimed task resuming after Review and stopping at its limit with the next untimed one taking over,
  - a timed task left unmarked stopping at its limit and not at its planned end or lunch, a timed task resuming after the next, a meal interrupting, the most recently interrupted resuming first, a status or the limit ending a task for the day, 22:00 still ending it,
  - no limit used overnight before DayWright saw a task, a task stopped at its limit keeping its stop when marked and staying in the notice until its time is confirmed, a task with a status leaving the notice, and one set of status words.
  - In WebKit, on a throwaway database: the sheet from Today and Tasks, Save with its notice and Undo, the continue offer, Ava's Catch up card filling her panel, yesterday's notice listing tasks stopped at their limit (an untimed one kept 11:00–14:00, 90 minutes,
  - around a call and lunch) and sending its catch-up with Today kept on show, those tasks then listed as times to check until confirmed, a Chinese sentence, the menu bar's panel without Catch up and with Partly done fitting, a summed time on a row,
  - and Today and the sheet at phone width.
  - The Mac app was built and checked without opening it: Version 4.8.0 (48), its signature, the Guide's and the word limit's files in its service, and the catch-up routes, its undo and withdrawal, the continue offer, the summed time and the limit in its service.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-07 as `a58ca49`, `6e48c60`, and `3175381`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v4-7-build-47"></a>

## v4.7 / build 47 — 2026-10-06

- **Title:** DayWright in the menu bar, the time each task took, and no reply at 22:00
- **Menu bar:** The task now, its time taken over its set time, and the next, renewed each minute; a click opens a panel to report either; closing the window keeps DayWright there.
- **Time taken:** Kept for every status, from a task's start to when you set it, stopping at the next task, a meal or 22:00; rows and sheets show it.
- **No reply:** At 22:00 a task with no status reads Not done · no reply, and the next day Today lists what to fix through Ava, who corrects past times too.
- **Agents:** Lengths come from the time Done tasks took; skipped and unanswered tasks are signals; a set length that keeps differing gets a card to change it.

### Changed

- **Why:** a day runs while the window is shut, and what a task really took is the best guide to the next one. Only you mark a task Done; DayWright now keeps the time it took, and says plainly what was left without a word.
- **The rule, changed:** "progress is reported, never inferred" becomes "only you mark Done; time taken is always kept". DayWright never sets Done, Partial or Skipped, but at 22:00 a task still without a status reads Not done · no reply, which any status replaces.
- **Menu bar:** DayWright's mark and one line, renewed at each minute's turn: "Review · 32 / 60 min · next: Email Anna", a name over 16 characters cut, "Next: Email Anna" with nothing current, the mark alone with neither, in English or Chinese as the interface is.
  - A click opens a small panel: Now and Next, each with its full title, its area, the time taken (or its start, or Untimed), its set time, "you set" or "estimated", and its own status control; then Open DayWright. Its menu opens the window or quits.
  - Closing the window keeps DayWright in the menu bar. Nothing notifies or counts down.
- **Current and next:** the timed task (a fixed task or a set plan's entry) whose time covers now, running past its length until it gets a status, but stopping at the next timed task's or a meal's start, and at 22:00;
  - with none running, the first task in the Untimed list. Next is the next timed task today, else the next untimed one. Nothing is current during a meal or after 22:00.
- **Untimed:** Today's "No start time" list is now Untimed, in the order its tasks were made, and the word changes everywhere it showed.
- **Time taken:** setting any status keeps when it was set and the time the task took: from its planned start, or for an untimed task from when it became current, to that moment, never past where it stops.
  - One task's status never ends or changes another's: marking Review Done late changes nothing on Email Anna, which started at its own time. A task given a status without ever being current took its set length back from then; a skip then took none.
  - A status changed later keeps the time, and Planned clears it. Rows show when it started and the time it took, and its sheet "Took 1 h 10 min · 14:00–15:10" beside its planned time.
  - A time over twice the task's length is one to check, shown on its sheet, and counts nowhere until you confirm it.
- **No reply and the next day:** at 22:00 a task with no status reads Not done · no reply, with a dashed glyph, on every screen that shows statuses; before 22:00 today's is still not yet reported.
  - The next day Today lists what yesterday left: tasks with no status, stopped at the next task's start without one, or with a time to check; Fix with Ava opens Ava with a sentence begun about the first of them, "Yesterday Journal ", to finish and send, and Dismiss hides it.
  - A message sent from Today that says "yesterday" is about yesterday's tasks.
- **Past days through Ava:** "Review took 2 hours", "I started Review at 9:30", "Review finished at 10:45" or "Write's time is right" proposes a card changing the time it took ("Time it took: 09:00–10:00 → 09:00–11:00"), saved on Confirm; a time you give counts as confirmed.
  - A task with no status needs one with it. Its planned start and length stay, so "Move Review to 11:00" still keeps its place.
- **Learning from it:** a new task's estimate is the median time the same task took on its done days; a partly done day only raises it; skipped and unanswered days, and times to check, never count; the local model no longer replaces it. Profiles take the same times.
  - When 3 of a task's last 4 done times differ by 10 minutes or more from the length you set, its area agent says through Ava "“Review” usually takes 1 h 15 min; you set 1 h.
  - Change it?", with a card for its days to come, saved only on Confirm and offered once for each usual length.
- **Signals:** a task skipped, or left without a status, at least twice and in half its records is a note on its area ("“Stretch” was skipped 2 of 3 times.") and in Summary, as Often skipped or Often left without a status, and never changes an estimate.
  - Summary counts tasks left without a status apart from Skipped.
- **Graphs and time spent:** Done by area counts the time tasks fully done took (a task done before times were kept, its planned time); the follow-through bar gains Not done · no reply, dotted, apart from today's not yet reported. Today's chip and balance count time spent across every status.
- **Guide:** Today: "set your energy, report each task's status, follow the day strip; the menu bar shows now and next." / "only you mark Done; time taken is kept;
  - at 22:00 what's left reads Not done · no reply." Past days: "through Ava, correct a status or the time a task took, remove it, or move it to today or later." / "its planned time and length stay;
  - yesterday's tasks to fix show on Today." Agents: "they learn lengths from the time Done tasks took" / "agents estimate only lengths you didn't set, never from skipped or unanswered tasks."
- **Release:** the Mac app reports Version 4.7.0 (47), and the service 4.7.0. The README's badge and the Desktop app's release line, which still read v4.5, read v4.7.

### Checked

- **Evidence:** the service tests (705), the interface helper tests (252) and the site checks (5) pass, and the interface build succeeds.
  - The tests, written to fail first, cover current and next with the Untimed order, meals and 22:00, the time each status keeps, a late status changing no other task, untimed starts and returns, never-current tasks and skips, the title's form and cut names in both languages, the panel's session,
  - no reply before and after 22:00, yesterday's notice and its dismissal, estimates from done times with partly done only raising them, times to check, profiles, graphs and Summary, the usual-length offer, Ava's past-day corrections and a message from Today about yesterday, the Guide's cards within 40 words,
  - and the menu bar's helpers.
  - In WebKit, on a throwaway database: Today's rows, chip and Untimed list, yesterday's notice through Fix with Ava to a card for yesterday's task, Dismiss across a reload, no reply on Tasks, a time to check on a sheet, the panel against the service's current and next and its report,
  - the usual-length card confirmed, the title in English and Chinese, and Today at phone width.
  - The Mac app was built and checked without opening it: Version 4.7.0 (47), its signature, the Guide's and the word limit's files in its service, its time rules, title route and panel view, and its shell's menu bar.
  - Run against a throwaway home, the built app's title thread reached the service with its session and the window passed on its language. macOS draws menu bar items where no capture reads them, and clicks couldn't be scripted here, so the title's look,
  - the panel opening and closing on the mark, and Open DayWright from it are your first sight of them.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-06 as `0a5ca78`, `5cf992e`, `60c0e90`, and `f19f040`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v4-6-build-46"></a>

## v4.6 / build 46 — 2026-10-06

- **Title:** learning tasks with checklists, a website checked as its task starts, and imports that remember where they came from
- **Learning tasks:** From a source moves to the task form: each ticked file or page is one Learning task, all on one day or one a day, alone or in a goal you choose; v4.5's goals from headings are reversed.
- **Checklists:** A task's headings are a checklist of real checkboxes, or one you make; tick as you go, Continue next session keeps the ticks, and only you mark Done.
- **Websites:** Looked up when a task is made from one and again as it starts; a changed page updates the checklist and the estimate.
- **Library:** A file chosen in the Mac's own window opens where it is.

### Changed

- **Why:** studying a file is one task, and a goal is a group of tasks you choose. v4.5 made each file a goal and its sections topics, which split one study session into several and put goals out of your hands.
- **Reversed:** v4.5's goals from headings and their topics.
  - Each goal made from a file was moved once: it keeps its name and its tasks, and gains one untimed Learning task for the file on the day of the move, its checklist the goal's topics in order, a topic already studied ticked. Topics are gone.
- **From a source:** in the task form for Learn, and Learn's + Add → Task, no longer in New goal: a connected folder, a website or a Library item.
  - Each ticked file or page becomes one untimed Learning task, named by its first heading or its file name, all on one day or one a day from it in the order listed, alone or in a Learning goal, existing or new.
  - A file worked through before carries on where you left off, its ticks kept, unless you Start fresh.
- **Checklists:** a task's second-level headings, a website's too, or with none its first-level ones below the title, are its checklist: one line per item, a checkbox in front of each. Any Learning task can have one you make.
  - Items are added, renamed in place, removed, and reordered by dragging or with Alt+↑ and Alt+↓; yours are marked so. A tick keeps its time; the briefing shows "3 of 5 sections done". A past day's checklist is read-only, corrected through Ava's card.
- **Done and next session:** every item ticked brings a pencilled card, "All sections ticked: mark it Done?", with Mark done and Not now; only you mark Done.
  - A partly done task offers Continue next session: Ava proposes a follow-up for the next day, saved on Confirm, carrying the whole checklist with its ticks, its length from the items still to do, at the pace earlier ones went.
- **Effort and length:** from the whole file's text, or a website's headings, 15 minutes a section and at least 30; both yours to change, and a length from the source says so.
  - Plans put deep tasks early and in focus, light ones in gaps, by energy, and a goal's tasks in its order.
- **Websites:** looked up when a task is made from one and again once as that task starts: a timed task at its start time, or the next time DayWright runs; an untimed one when its briefing is first opened on its day.
  - A changed page updates the briefing, "Updated from the website at 10:05", the checklist, new headings added and ones gone kept and marked, your items untouched, and the estimate, never a length you set. A site out of reach keeps what was stored, "Couldn't check the website".
  - A folder's Refresh brings a changed file's checklist up to date the same way.
- **Subjects and Ava:** Subjects show each goal's next task to study with its checklist's progress, and Ask Ava to plan it moves it to the day on show, or says it is planned.
  - Ava answers "What will I learn today?" from the day's Learning tasks and their items still to do, and a goal's progress counts its tasks done again.
- **Imports:** Choose files… opens the Mac's own window, so a file imported there remembers where it is and opens there, or shows "Original not found" with Locate. A file uploaded from the browser, or imported before, keeps only its text. A file's briefing shows its checklist's progress.
- **Online:** the line under the Library's title and this README now say "Everything stays on this Mac; DayWright only looks a website up when you create a learning task from it, and again when that task starts."
- **Guide:** a Learning tasks card in Your work, after Tasks. The Library card's Do adds "make learning tasks from them", and its Rule reads "websites go online only for their learning tasks." Learn's ? opens Learning tasks and Areas, and a learning task's sheet has its own ?.
- **The word limit:** one number, 40, and one way of counting, which the service and the interface both read from `src/wording.json`: a word is a run between spaces holding a letter or a digit, and each Chinese character is one.
  - It holds a Guide card's For, Do and Rule together, a file's own briefing, a website's own description, the briefing you write or type with a website, and Ava's suggestion, each cut at a word boundary with "…"; a briefing kept before reads within it too.
  - Writing one shows "12 of 40 words", and Confirm waits while it runs past.
- **Removed:** New goal's From a source, a goal's topics and their burn-up, and Ava's study-task card.
- **Release:** the Mac app reports Version 4.6.0 (46), and the service 4.6.0.

### Checked

- **Evidence:** the service tests (652), the interface helper tests (237) and the site checks (5) pass, and the interface build succeeds.
  - The tests, written to fail first, cover one task per ticked file in either spread, checklists from either heading level or none, editing and reordering, ticks with their times and passes, the Done suggestion, follow-ups and their pace, past days through Ava,
  - a website's checks at creation and start and a changed page's merge, the move from v4.5's topics, Subjects' next task, imported files' originals, the Guide's cards, and the word limit in each place, with both counters giving the same counts and cuts.
  - In WebKit, on a throwaway database, folder and local website, wide, at phone width, keyboard only and in Chinese:
  - tasks made from a folder and a website, a checklist ticked, edited, dragged and moved by keys, Mark done and Not now, Continue next session confirmed, a website looked up again as its briefing opened, a past day's checklist read-only, an imported file's original lost.
  - Choose files… and Choose folder… open the Mac's own window, which the checks replaced with typed paths and a seeded import. The Mac app was built and checked without opening it: Version 4.6.0 (46), its signature, and the new parts of its service.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-06 as `51fe278`, `666e175`, and `5d20590`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v4-5-build-45"></a>

## v4.5 / build 45 — 2026-10-06

- **Title:** folders and websites in the Library, briefings, and goals from headings
- **Library:** Connect a folder anywhere on this Mac, only ever read, or save a website; items are grouped by where they came from, and any name opens a briefing of what it is about and its headings, written by Ava or you where missing.
- **Opening:** A folder's file opens in its app, Markdown in Obsidian, or on its folder's website; a website in your browser; Open with sets an app for each kind.
- **Goals:** From a source makes Learning goals from ticked headings, their subheadings becoming topics with an effort; plans, Ava and the Subjects card take them in order.
- **Online:** A website is looked up once, when a goal is made from it; nothing else goes online.

### Changed

- **Why:** study material lives in folders and on websites, and a lesson's headings already lay out what to learn; the Library held only notes and imported text, and a Learning goal couldn't follow a course.
- **Connect a folder:** Connect folder picks a folder in the Mac's own window or takes its typed path; no folder is assumed.
  - Its Markdown, PDF and Word files show as a tree to tick: hidden files and the history, node_modules and dist folders start unticked, and a file over 20 MB or 300 pages stays unticked with its reason.
  - Each ticked file joins the Library, named by its first heading, and may open on a website its files are also on. DayWright only reads the folder; nothing in it is changed, moved or deleted.
- **Refresh:** a folder's Refresh, and opening DayWright, picks up new and changed files and follows one renamed with the same content.
  - A file gone from its folder is marked Not found in the folder, with Locate, to pick its new name, and Remove from Library, which also leaves it out of later Refreshes; only you remove it.
  - A folder no longer at its place keeps every item, briefing, goal and topic, says "Folder not found at …" with Update location, and Refresh waits for it.
- **Websites:** Add website saves one by its address, with what it is about if you like, without looking it up.
  - It is looked up once, when a goal is first made from it, keeping its title, its own description and its first- and second-level headings, never its text, and is never fetched again.
- **Briefings:** an item's name, in the Library, a goal's sheet, an area's Library card, search results and From a source, opens its briefing: what it is about, its first paragraph to about 40 words or a site's own description, and its headings, never its text.
  - Where these are missing or say too little, Ava suggests them with the local model, from a file's text read on this Mac or a site's title and headings; the suggestion is shown to edit and kept only on Confirm, marked as Ava's or, once changed, yours.
  - Without the model, or for a site that gives too little, the card says so and you type it.
- **Opening:** a folder's file opens in the Mac's app for its kind, Markdown in Obsidian, in the vault holding it, when Obsidian is installed; Open with sets an app for Markdown, PDF and Word.
  - A file opens on its folder's website, at its own lesson page for the Learning Atlas Observatory site. A website opens in your browser, marked so.
- **Library:** grouped by where each item came from: each connected folder with its files, then websites, imported files and notes. Search lists first the items whose name, briefing or headings hold the words, websites among them, then passages.
- **Goals from headings:** New goal, for Learn, offers From a source: a connected folder, connected in place if you like, a website, looked up with "Looking into {site}…", or a Library item.
  - Each ticked first-level heading, or a folder's file, becomes a Learning goal and its second-level headings its topics; the source joins the Library linked to it.
- **Topics:** a goal's sheet lists its topics in order, each studied, planned or not, its estimated length, at least 30 minutes, and its effort, light, steady or deep, worked out from its text (words, code, exercises) and yours to change.
  - A topic is studied once a task for it is fully done, and the goal's progress counts topics studied.
- **Studying:** Learning's Subjects name each goal's next topic, and Ask Ava to plan it asks Ava, who proposes it as a study task, saved on Confirm, her card saying "Topic 1 of 3".
  - Plans carry each study task's effort and place: deep topics in focus blocks and earlier, light ones in gaps, by the day's energy, never ahead of an earlier topic. Ava answers "What will I learn today?" from the day's topics.
- **Online:** the line under the Library's title and this README now say "Everything stays on this Mac;
  - DayWright only looks a website up once, when you create a goal or task from it.", and the Guide's Library card's rule "only a website goes online once, when you make a goal from it." Until now DayWright never went online.
- **Removed:** the Library's one Notes and files table, replaced by its groups, and the Guide's Library rule "nothing goes online".
- **Release:** the Mac app reports Version 4.5.0 (45), and the service 4.5.0.

### Checked

- **Evidence:** the service tests (605), the interface helper tests (217) and the site checks (5) pass, and the interface build succeeds.
  - The tests, written to fail first, cover the folder tree and its limits, a folder left unchanged by everything done with it, Refresh, Locate and Remove, a folder not found keeping everything, no folder or path assumed anywhere,
  - a website looked up only for its first goal and never again with nothing else reaching the network, briefings by kind with Ava's kept only on Confirm, opening by kind with Obsidian and Open with, goals and topics from headings, study tasks and their lengths, placement by effort and energy,
  - the plan model's input, and "What will I learn today?". In WebKit, on a throwaway database, folder and local website, wide, at phone width and in Chinese:
  - a folder connected, briefed and opened, Ava's briefing without the model, a website saved and looked up once, Open with, search, a file located and one removed, a folder moved and found again, goals from a folder and a website with their topics, and the next topic proposed through Ava.
  - Choose folder… opens the Mac's own window, which the checks replaced with a typed path. The Mac app was built and checked without opening it: Version 4.5.0 (45), its signature, and the new parts of its service.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-06 as `3710b83`, `5761bfa`, and `20f3e46`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v4-4-build-44"></a>

## v4.4 / build 44 — 2026-10-05

- **Title:** graphs of what you finish, how plans go, and a goal's progress
- **Summary:** Week and month reports show, a bar per day, the time fully done by area, the share of tasks fully done, and how the set plan was followed; a day's report shows its plan's follow-through.
- **Today and Calendar:** A Finishing card for the last 7 days in Day details; a day's plan card shows a follow-through bar with Moved counted.
- **Goals:** The Edit sheet shows the goal's steps done week by week, the weeks ahead outlined to what is planned.

### Changed

- **Why:** the reports gave each period's totals but not how the days within it went, and nothing showed whether set plans were kept or how far a goal had come week by week.
- **What counts:** as in Summary's figures: a day with a set plan counts its entries, any other day its own tasks; a task removed or moved on, and one still to do whose goal is paused, are left out. Done means fully done.
  - The graphs read your records as they are now, so a report saved before 4.4 shows them too.
- **Done by area:** in a week's or month's report, a bar per day of the planned time fully done, stacked by area in the areas' colours, with each day's time above it in a week, then the period's total and each area's.
- **Finishing:** a bar per day of the share of its tasks fully done, its percentage above it in a week, and the period's tasks fully done of those scheduled. It shows from 2 days with tasks.
  - On Today, a Finishing card under Balance draws the last 7 days small, with today's figure.
- **Plan follow-through:** a set plan's entries as one bar: done, partly done, moved on to another day, skipped and not reported, with a key giving each count.
  - It is in a day's report and, in place of the plan's four counts, in Calendar's day panel, where an entry moved on now counts as Moved. A week or month draws a column per day with a set plan.
  - Done as planned means an entry reported done, as DayWright doesn't record when a task was done.
- **A goal's progress:** its Edit sheet shows a column per week of the steps fully done so far, under a dashed line at all its steps; this week and the weeks ahead are outlined to the steps planned through them, with the figures in words.
- **Empty states:** each graph says why it is empty: nothing fully done yet, fewer than 2 days with tasks, no plan set, or a goal with no tasks.
- **Removed:** the day panel's four count tiles (Done, Partial, Skipped, Unreported), replaced by the follow-through bar and its key.
- **Release:** the Mac app reports Version 4.4.0 (44), and the service 4.4.0.

### Checked

- **Evidence:** the interface helper tests (202), the service tests (515) and the site checks (5) pass, and the interface build succeeds.
  - The graph tests, written to fail first, check each day's counts and time fully done by area against Summary's own, the days running to today, a set plan followed with moved entries in, and removed ones and a paused goal's entries still to do out, in Calendar as in Summary,
  - the graphs in the day, week and month reports and not all time, a report saved before them, Today's seven days, the marks of each graph, and every graph's words and empty line in both languages.
  - In WebKit, on a throwaway database, wide and at phone width: Today's Finishing card; yesterday's follow-through in Calendar; Summary's day, week and month graphs; a month to come with every empty line; the Kitchen renovation's weeks and a goal with no steps.
  - The Mac app was built and checked without opening it: Version 4.4.0 (44), its signature, and the graphs in its service.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-05 as `bdd5295`, `c36bdbf`, and `91c2d44`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v4-3-build-43"></a>

## v4.3 / build 43 — 2026-10-05

- **Title:** energy through the day, and its average everywhere
- **Energy:** Report it on Today as often as you like that day, or tell Ava and confirm her card; each reading is kept with its time, and the day's average counts everywhere.
- **Plans and agents:** 2 or below puts Lighter day first, 4 or above Deep focus; Ava and each area agent suggest what suits the day.
- **Summary and Calendar:** Reports show the day's readings or each day's average, and set low days against the others from 5 reported days; each Calendar day shows a small meter.

### Changed

- **Why:** energy was one reading a day that only the Life agent and Lighter day used, and nothing showed how a day's energy went or what low days did to your tasks.
- **Reporting:** optional, with no preset. Tap 1–5 at the top of Today any time today, or tell Ava ("energy 4", "I'm drained", "我很累"): her card, "Energy today", shows the reading and today's average before and after, and nothing is saved until Confirm.
  - Each reading is kept with its time; tapping the level already shown adds nothing. Only today's energy changes: asked about another day, Ava says so and changes nothing.
- **The day's average:** the one value plans, Ava, the area agents, Summary and Calendar use. Plans proposed after a change put Lighter day first at 2 or below and Deep focus first at 4 or above; plans already proposed and the set plan stay.
  - Each change reaches the Orchestrator, all four area agents and Summary: they look at today again, and the day's saved reports are made again.
- **Ava:** knows today's average, and when suggesting what to do next leans to short or easy tasks on a low day and to the hardest or most important task on a high one.
- **Area notes:** at a low or high average, where it applies, Learn suggests a short review or a harder session; Work flags a heavy load with 3 hours or more of Work on a low day, or names your biggest Work task on a high one;
  - Project suggests a small step or the next big step. Life still advises rest on a low day. A middle average adds no note.
- **Summary:** a report's Energy part reads only the readings in its period: the average and days reported, the lowest and highest days, and the change from the period before.
  - From 5 reported days, at least 2 low and 2 others, it sets the share of tasks fully done on low days against the other days, overall and per area, and advises planning lighter on low days when they went worse; with fewer, it compares nothing and advises nothing.
- **Graphs:** Life's Energy card and a day's report show the day's readings as steps from 09:00 to 22:00. Life's card and week and month reports show a bar per day for its average, with a thin line from its lowest to its highest reading where they differ.
- **Calendar:** each day with a reading has a small five-step meter under its completion bar, in the caution colour at 2 or below; the day panel shows a larger one, outlined and empty with no reading. The level is read out to screen readers, never printed.
- **Guide:** the Energy card reads "For: matching the day to you. Do: tap 1–5 at the top of Today, or tell Ava; change it any time today.
  - Rule: the day's average counts; 2 or below suggests Lighter day, 4 or above Deep focus." It names the plan as the screen does.
  - Two Rules now say what DayWright does: Repeats, "a change made from a past day applies from today on, or tomorrow if today's is already reported or planned.", and Agents, "the Orchestrator proposes;
  - the agents advise, and only estimate lengths you didn't set." Every card stays within 40 words, and the Today and Plans cards still hold.
- **Removed:** the one-reading-a-day energy store, whose readings move into the new log, each at the time it was saved, when 4.3 first opens your records; Summary's advice from a single latest reading; and the Life agent counting a low reading from an earlier day as today's.
- **Release:** the Mac app reports Version 4.3.0 (43), and the service 4.3.0.

### Checked

- **Evidence:** the interface helper tests (193) and the service tests (506) pass, the interface build succeeds, and the site checks (5) pass.
  - The energy tests, written to fail first, check the log and its average, today-only readings, the plan order at each end, the relay to every agent, Ava's card and context, each area's note, Summary's figures and when it compares or advises, the move of the old readings, the steps,
  - bars and meters, and the three Guide cards.
  - In WebKit, on a throwaway database, wide and at phone width: the Learn and Project notes on a low day; Life's steps and bars; every Calendar meter and the day panel's, filled and empty; Summary's day, week and month; Today's row; and Ava's card, saved only on Confirm.
  - The Mac app was built and checked without opening it: Version 4.3.0 (43), its signature, the energy log in its service, and the Guide's cards, the same as the project's.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-05 as `de6285c`, `29b8197`, and `221e3e6`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v4-2-build-42"></a>

## v4.2 / build 42 — 2026-10-05

- **Title:** the Guide, a ? beside every title, and Ava's answers from it
- **Guide:** Guide, beside EN/中文, opens thirteen cards in five coloured sections, each saying in three labelled lines what a part is for, what you do there and the rule it keeps.
- **?:** A small ? beside each screen's title, and Ava's, opens that screen's cards.
- **Ava:** Asked how something works, Ava answers from the matching cards, changing nothing, and links to them.

### Changed

- **Why:** what each part of DayWright is for, and the rules it keeps, were spread over captions, notes and refusals, with no one place to read them.
- **The Guide:** Guide, beside EN/中文 in the title bar and the phone header, opens a page of thirteen cards in five sections: The day (Today, Plans, Calendar), Your work (Goals, Tasks, Areas), Library, Ava and the agents (Ava, Agents), and Rules everywhere (Past days, Meals, Repeats, Energy).
  - It is in English in either language.
  - Each card shows its icon in a circle of its section's colour beside its title, then three labelled lines, For, Do and Rule, the Rule in a callout of that colour; the sections are amber, violet, blue, rose and grey, and the labels always show.
  - Cards sit two to a row, one on a phone, all the same size.
- **The ?:** a small ? beside each screen's title opens its cards in a sheet: Today's opens Today, Energy and Meals; Plans', Plans; Calendar's, Calendar and Past days; Goals', Goals; Tasks', Tasks and Repeats; each area page's, Areas; the Library's, Library.
  - The ? beside Ava's name shows Ava and Agents in Ava's own panel, with a link back to the conversation.
- **Ava:** asked in English how something works, such as "How do meals work?", "What is the Library for?" or "How do I use goals?", Ava answers from the matching cards alone, without the model, and ends with "See Guide: Meals"; each name there opens its card in the Guide.
  - Such an answer changes nothing and brings no card, even about meals or repeats on a past day.
- **One source:** the cards' text is kept in one file, `src/guide/guide.json`, which the screens and Ava both read; the Mac app's service carries a copy.
- **Card text:** as written for the Guide, except two lines that now say what DayWright does:
  - Calendar's Do line names "day, week, month and all-time reports", as its Summary also covers all time, and the Plans Rule ends "Only today's plan can be set.", as a past day keeps the plan set on it.
- **Release:** the Mac app reports Version 4.2.0 (42), and the service 4.2.0.

### Checked

- **Evidence:** the interface helper tests (180) and the service tests (480) pass, and the interface build succeeds.
  - The Guide's own tests, written to fail first, check that each ? opens exactly its cards, that every card has For, Do and Rule in at most 40 words, that the five sections come in order, that each card shows its icon, labels and Rule callout in its section's colour,
  - and that Ava's answer draws on the matching card, ends with its See Guide line and asks no model.
  - In WebKit, on a throwaway database, wide and at phone width: the Guide page and the Today and Tasks sheets, every card the same size, two to a row or one, in its section's colours; every screen's ? and Ava's;
  - Ava's answer about meals, whose link opened the Meals card, and the Guide's own link later opening it with no card picked out; the Guide in English with the interface in Chinese; and every screen's title, and what follows it, where v4.1 had them.
  - The Mac app was built and checked without opening it: Version 4.2.0 (42), its signature, and the cards in its service, the same as the project's.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-05 as `101a024`, `b27e14c`, and `650c52c`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v4-1-build-41"></a>

## v4.1 / build 41 — 2026-10-05

- **Title:** today's energy above the day's buttons
- **Today:** Energy, one line with its 1–5 scale, sits in the header right above Add task and Propose plans, with or without tasks; the text beside the scale is gone, and the day strip keeps its width.

### Changed

- **Why:** the energy row sat under Today's header and its banners, apart from the buttons whose plans it changes.
- **Today's header:** the energy row now sits at the top of the header's actions column, directly above Add task and Propose plans, or Compare and set, whether or not the day has tasks; on a day with none it is there alone, and the empty state keeps its own buttons.
  - It is one line, "Energy" and the 1–5 scale, its right edge on the buttons' right edge and no wider than them, so the day strip keeps its width; screen readers still hear "How's your energy?". On a phone the same line sits above the buttons, aligned with them.
- **Unchanged:** the reading itself: 1 to 5, today only, and a lighter day at 2 or below.
- **Removed:** the row's old place under the header and banners, and the text beside the scale: both "1 low · 5 high" and the low-energy note. A reading shows only as its selected button, and the Life agent's notes explain a low one.
- **Release:** the Mac app reports Version 4.1.0 (41), and the service 4.1.0.

### Checked

- **Evidence:** the interface helper tests (172) and the service tests (473) pass, and the interface build succeeds; the header's order and the one-line row without a caption have their own tests, written to fail first.
  - In WebKit, on throwaway databases, Today was checked with tasks and 2 selected and on an empty day, wide, at the Mac app's narrowest window and at phone width: the energy row in the header above the buttons, one line with no caption,
  - its right edge on the buttons' right edge and no wider than them (aligned with them on a phone), the buttons below it or the empty state's own, the day strip as wide as before (640 px, and 358 on a phone), and nothing scrolling sideways.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-05 as `c96d856` and `be48a62`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v4-0-build-40"></a>

## v4.0 / build 40 — 2026-10-05

- **Title:** fully done, fixed times at any hour, and one + Add per area
- **Done:** Area figures and the idle days behind due for review and stalled count only tasks fully done; a partly done task still shows Partial.
- **Times:** A fixed task may start at any hour, from the form or through Ava; plans place tasks without a time between 09:00 and 22:00.
- **Areas:** One + Add at the top of each area page adds a task, goal, or note or file; no card has an add button, and a day that won't fit is no longer an area note.
- **Library:** Search keeps to the area switched to.

### Changed

- **Why:** the area cards counted a partly done task as done; Ava was told DayWright plans tasks between 09:00 and 22:00, as if fixed ones had to fall there; a day that won't fit showed both on Today and in an area's notes; every card carried its own add button;
  - and Library search ranked the area on show first rather than keeping to it.
- **Done means fully done:** Learning's time done per subject, when each was last practised, the practice dots and the done part of the practice bars; Work's load bars; Project's steps done, step bar, last step and Recently done; the Done count in each area's Today card;
  - and the idle days behind "due for review" and "stalled" now count only tasks fully done. A partly done task still shows Partial, and Summary keeps its own counts of done and partly done. This replaces v3.5's rule that done included partly done.
- **Fixed times at any hour:** a fixed start may be at any hour, 06:30 or 22:30, from the form or through Ava, and it shows on Today and in the area's Today list; the day strips still run 09:00–22:00.
  - Plans place only tasks without a time, and only between 09:00 and 22:00. Ava is told so, and never refuses a fixed time for falling outside that window: only another task, a meal or midnight stands in its way.
  - A task Ava adds that would run past midnight is now refused, as the form already prevented, and a fixed task after 22:00 no longer counts the time before it as free.
- **A day that won't fit, once:** removed from the areas' notes, it stays the Orchestrator's notice on Today. With no free time left at all it reads "No free time is left today for tasks without a time (1 h 15 min)." in place of "only 0 min is free".
- **One + Add per area:** each area page has a single + Add at the top right of its header, level with the area's name as New goal is with Goals, the area's purpose now under the header;
  - its menu adds a Task (the task form set to the area, with no goal; on a past day shown it starts at today), a Goal in the area, or a Note or file in the area, by mouse or keyboard.
  - Removed from the cards: Today in the area's Add task, Subjects' add-session +, Projects' Add the next step and the Library card's Add.
  - A subject with no session planned and a project with no next step say so in words, and an empty card says "Use + Add to add one."; links that add nothing stay. This replaces a "+ Add a session" label planned in the same round.
- **Habits:** a weekly habit's grid shows a faint · on the days its rule skips.
- **Library search:** with an area switched, Search your library finds only that area's notes and files; with All, every one. This replaces v3.9's ranking of the area on show first.
- **Tidying:** an import nothing used was removed from the service's database module.
- **Release:** the Mac app reports Version 4.0.0 (40), and the service 4.0.0.

### Checked

- **Evidence:** the service tests (473) and the interface helper tests (169) pass, and the interface build succeeds; each change has its own test, written to fail first, and the tests that held v3.5's rule now hold the new one.
  - In WebKit, on a throwaway database, every area page was checked wide and at phone width: one + Add at the top, its menu opening on screen and by keyboard, each choice opening its sheet set to the area, no add button in any card,
  - the words in place of the removed buttons, the habit grid's faint marks, a 06:30 task on Today, and Library search keeping to the area switched to.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-05 as `16a49df`, `690aa8b`, and `30e6bc1`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v3-9-build-39"></a>

## v3.9 / build 39 — 2026-10-05

- **Title:** an offline Library tied to goals and areas
- **Offline:** DayWright never goes online: the Wikipedia lookup, the network log and the pages it imported are removed, and the Library says so in one line.
- **Library:** Every note and file belongs to an area and, if you choose, a goal; Search your library shows each passage with its note or file, area and goal.
- **Goals and areas:** A goal's sheet and each area page list their notes and files, with Add.
- **Ava:** The areas lead; Library passages support facts and details, and a reply names the notes and files it used.

### Changed

- **Why:** DayWright could send a topic's words to Wikipedia when you allowed it and kept a network log of those requests, and the Library's notes and files belonged to no area or goal, so Ava weighed them all alike.
- **Removed, the online lookup:** Look up a topic, with its switch, its consent card and its choice of how to keep a fetched introduction, is gone, as are the graph that ran it and the service's topic and import routes. DayWright never goes online.
- **Removed, the network log:** the title-bar pill, the full log and the "What stays, what goes" panel are gone, with the service's log and their text in both languages. One line takes the panel's place: "Everything here stays on this Mac. DayWright doesn't go online."
- **Removed, imported pages:** once, at start, DayWright drops the tables the lookup and the log kept, and deletes every Wikipedia page already imported, with its passages, their search entries and the records of Ava having drawn on it.
  - The day proposals' saved checkpoints, which could hold copies of fetched text, are cleared then too; the proposals themselves keep working.
- **Search your library:** a plain search box, by meaning, on this Mac. Each passage shows its note or file, its area and goal, and which part it is; Ask Ava about this opens Ava with "What does my Library say about “past tense”?" typed in, not sent.
  - Every note and file is searched, and the area on show ranks its own first.
- **Areas and goals:** every note and file belongs to an area and, if you choose, a goal in it: one of the area's active goals, or the goal it was added from.
  - New note and Import files ask for both, the area suggested from the note's title and opening text, or the files' names, by the purpose rule; Edit changes them later, and choosing another area clears the goal.
  - Removing a goal keeps its notes and files, unlinked; pausing or completing it keeps the link. Notes and files from before this version get an area by keywords from their title and opening text, and no goal.
- **The Library:** an area switch, All and the four areas with their counts, and the search box; each note or file with its area, its goal, when it was added, Edit and Remove. It no longer says "sources" anywhere, Ava's replies included.
- **Goals and areas:** a goal's Edit sheet lists its notes and files under Library, with Add note or file, which starts linked to the goal while the goal's sheet waits;
  - each area page has a Library card in its grid, with Add, linked to the area, and See all, which opens the Library on the area.
- **Ava:** the areas lead. Library passages reach the local model after the area and day context, marked as references for facts and details, never instructions; the advice comes from the agents' reports and your tasks.
  - A message that names a goal, or a task in one, ranks that goal's notes and files first, then its area's, then the rest, leaving none out.
  - A reply that drew on the Library ends with "From your Library: Spanish grammar notes, Lesson 4" (in Chinese, "来自你的资料库：…"), naming each note or file used; a reply from DayWright's own rules, with the model off, adds no such line.
- **Release:** the Mac app reports Version 3.9.0 (39), and the service 3.9.0.

### Checked

- **Evidence:** the service tests (464) and the interface helper tests (166) pass, and the interface build succeeds; each change has its own test, written to fail first.
  - In WebKit, on a throwaway database with the local embedding model, the Library, a goal's sheet and an area page were checked wide and at phone width: the offline line, the area switch, search with each passage's area and goal, Ask Ava about this, a new note's suggested area, Edit,
  - the goal's and the area's Add starting linked, a paused goal's included, See all opening the Library on the area, nothing scrolling sideways, and the word "sources" nowhere on screen; the Library also in Chinese, and with the Mac in dark mode, which leaves it light.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-05 as `4b3cf0e`, `4cb7ad4`, and `0369ab7`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v3-8-build-38"></a>

## v3.8 / build 38 — 2026-10-05

- **Title:** area screens as one page of cards, with visuals
- **Areas:** Each area is one page of cards with no tabs, two to a row: the day's tasks, its agent's notes, and its own cards, each with its days, numbers and a small visual.
- **Work:** Ask Ava to move types the request for a carried-over task into Ava's box, to send when you choose.
- **Tasks:** Every estimated length is at least 30 minutes, a task added in the form joins its day's proposed plans, and keywords decide a suggested area when one matches.

### Changed

- **Why:** each area split its day between an Overview tab and a Tasks tab, its cards were lists of text, and goals due for review or stalled sat in cards of their own.
- **One page:** an area has no tabs. Its purpose sits under its name, and its cards come two to a row, each row as tall as its tallest card, one to a row on a phone; a card alone on the last row keeps its half.
- **Every card:** a title with the days it covers ("Load · Mon 28 Sep – Sun 4 Oct"), a line saying what it counts, its numbers with labels, rows that open their item (a goal its Edit sheet, a task its details on its own day), and when it has nothing,
  - what fills it with the button that does. In English and Chinese; the week runs Monday to Sunday, and done includes partly done.
- **In every area:** Today in the area, with the day strip showing the area's tasks alone, the day's tasks and their statuses, Add task from today on, and See all, which opens Tasks set to the area;
  - and the area agent's notes for today, each with an icon for its kind (slipping, length off, due for review, stalled, a doubt about a time, a day that won't fit, low energy), or "Nothing to flag." On another day the notes say they are for today.
- **Learn:** Subjects, each Learning goal with its time done against planned this week, a practice row (● practised, ○ planned but not done, · nothing planned), when you last practised and its next session or a button to add one, then the time on Learning tasks without a goal.
  - Practice this week, a bar per day with its time and the part done darker.
- **Life:** Habits, each repeat with its rule and start ("Daily since 25 Sep"), a week grid of done, partly done, missed, still to come and days its rule skips, and its count and streak; a repeat stopped this week stays, marked "Stopped Thu", until the week ends.
  - Today's shape, the whole day's strip with meals, booked time and open time, Life's appointments and the meals, and the free windows between 09:00 and 22:00. Energy, seven days of readings with a dashed line at 2.
- **Work:** Load, a bar per day of Work planned this week, the part done darker, with the week's totals. Meetings, Work tasks with a start time over seven days from the day on show, by day.
  - Carried over, each with its day and Not reported, Partly done or Moved to a day;
  - Ask Ava to move types "Move “Email Anna” from Fri 2 Oct to today" into Ava's box without sending it, and Ava looks for the task on the day the request names, whatever day is on show.
- **Project:** Projects, each with On track, Stalled N days, Paused or No steps yet, a step bar with a segment per task, "Steps done: 2 of 4", and its last and next step; a partly done step now counts as done.
  - Next steps over the next seven days and Recently done over the last seven, each with its project.
- **Estimates and plans:** every estimated length is at least 30 minutes, the form's too, and the local model's refinement as well. A task added in the form joins its day's proposed plans when none is set, as one Ava adds does.
- **Suggested areas:** keywords for each purpose decide when one matches; the local model is asked only when none does, and now works from examples ("Kitchen renovation": Project, "Call the plumber": Life, "Read chapter 4": Learning).
- **Release:** the Mac app reports Version 3.8.0 (38), and the service 3.8.0.

### Checked

- **Evidence:** the service tests (451) and the interface helper tests (159) pass, and the interface build succeeds; each figure, visual and rule has its own test, written to fail first.
  - In WebKit, on a throwaway database, each area was checked wide and at phone width in English and wide in Chinese:
  - no tabs, one task list, rows matched, nothing scrolling sideways, an empty account's cards each offering their action, Ask Ava to move typing its request without sending it, See all opening Tasks set to the area, and a goal's row opening its Edit sheet.
  - DayWright has no dark theme, so with the Mac in dark mode the pages stay light.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-05 as `a2c6a66`, `418caae`, and `b76a300`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v3-7-build-37"></a>

## v3.7 / build 37 — 2026-10-04

- **Title:** Ava adds tasks and starts goals
- **Ava:** Ava adds a task from your words, with its day, start, length, repeat and goal, or starts a goal with its first tasks; a card shows it all and nothing is added before Confirm.
- **Areas:** A task without a goal, or a new goal, gets the suggested area on the card, and you can change it there.
- **Thinking:** The dots beside "Consulting the relevant agents locally" sit centred on the line.

### Changed

- **Why:** new tasks and goals came only from the forms, so asking Ava for one got no further than advice.
- **Adding a task:** "Add Read chapter 4 tomorrow at 9 for 45 min to my Spanish goal" / "添加 读第4章 明天上午9点 45分钟" proposes the task.
  - Ava reads its title, quoted or what's left of the message, and its day: one you name, else the day on show when that's later than today, else today. A past day is refused and nothing is saved.
  - A start, a length and a daily or weekly repeat are taken when you give them; an hour alone before 7, as "at 3", is in the afternoon. Without a start the task is flexible, and without a length its area agent estimates one, never under 30 minutes.
- **Goal or area:** a goal you name, by its title or part of it, gives the task its area.
  - A paused or completed goal is explained ("“Spanish” is paused, so no task can join it; resume it in Goals, or add the task without a goal."), and so is a name that fits none or several.
  - Without a goal, the area you name is taken, else the Orchestrator suggests one by purpose, as the task form does.
- **Starting a goal:** "Start a goal: Kitchen renovation" / "新建目标：厨房装修" proposes the goal with its suggested area; "…and add pick tiles on Saturday" adds its first tasks to the same card, and they're created with it. A goal title you already have is refused.
- **The card:** titled "Add a task tomorrow" or "Start the goal “Kitchen renovation”", one line per task ("“Read chapter 4” · tomorrow · 09:00 · 45 min · repeats daily"), "Joins your goal … and takes its area." for a goal's task, and "Checked as the task form checks it:
  - no overlap with timed tasks or meals." Without a goal it shows the area control with the suggestion named ("Orchestrator suggests Life from the task's purpose. Change it if it's wrong."), and the area you pick is the one saved. In English and Chinese.
- **Thinking dots:** the three dots beside "Consulting the relevant agents locally" sit centred on the line instead of at its top, and still rise in turn.
- **Release:** the Mac app reports Version 3.7.0 (37), and the service 3.7.0.

### Checked

- **Checks:** each task passes the task form's checks before the card shows, so an overlap or a meal is answered in words with no card, and again on Confirm. Nothing is created before Confirm.
  - Then the tasks' area agents are told, an estimated length is refined by the local model when it can be, and a day of theirs with plans proposed and none set has them made again.
- **Evidence:** the service tests (426) and the interface helper tests (139) pass, and the interface build succeeds; each of Ava's new rules has its own test, written to fail first.
  - In WebKit, on throwaway databases in English and Chinese, a goal with a first task, a goal's task with a time, length and repeat, and a task whose suggested area was changed on its card were each created only on Confirm, as shown; the dots sat on the line's centre.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-05 as `a2c6a66`, `418caae`, and `b76a300`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v3-6-build-36"></a>

## v3.6 / build 36 — 2026-10-04

- **Title:** a stopped repeat removes its days still to do, and event Details cleared
- **Repeats:** Stopping a repeat from a past day removes its days still to do from today, unless today's was reported or set; switching to weekly removes those off its weekday; the card names them.
- **Move:** An event's Detail that was only its category is cleared when the area records fold in.
- **Work:** Carried over leaves out skipped tasks.

### Changed

- **Why:** a repeat stopped or switched from a past day relabelled its later days, so a stopped repeat still left its days on the calendar to do; and an event's category, which v3.5 drops, was also written into its task's Detail.
- **Stopping a repeat:** "Stop repeating Stretch" about a past day deletes today's own day if it wasn't reported and today's set plan didn't schedule it, and every later day still to do; a reported or scheduled day today stays, and the stop starts tomorrow.
  - Each day goes as a delete would: it leaves proposed plans, and its area agent and Summary are told.
- **Switching a repeat:** to weekly, the days still to do that aren't on the past task's weekday are deleted the same way, the rest repeat weekly, and the next day is prepared on that weekday; to daily, every day stays and repeats daily. A reported day is never touched.
- **The card:** a stop or switch that removes days names them, as "Its days still to do are removed: today, tomorrow." / "以下尚未完成的那几天将被删除：今天、明天。", and Ava's explanation does too.
- **Event Details:** when Learning's and Life's records fold into tasks and goals, an event task's Detail that is exactly its category ("sport") is cleared; any other text stays.
- **Carried over:** Work's overview lists the Work tasks of the 7 days before that are still to do or partly done, and those a set plan moved on; a skipped one is left out.
- **Tidying:** three interface texts no screen used are gone, and the goal card's design note reads "3 of 5 linked tasks done", as the card does.
- **Release:** the Mac app reports Version 3.6.0 (36), and the service 3.6.0.

### Checked

- **Evidence:** the service tests (414) and the interface helper tests (137) pass, and the interface build succeeds; each rule has its own test, written to fail first.
  - On a throwaway database made as v3.4 left one, the move cleared an event's Detail that was only its category and kept one with other words.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-04 as `e711f48`, `e2803c7`, and `8b686dc`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v3-5-build-35"></a>

## v3.5 / build 35 — 2026-10-04

- **Title:** areas by purpose, overviews from tasks, and energy in one tap
- **Areas:** Areas go by purpose, each one's meaning is in the task form, and the Orchestrator suggests a new task's area.
- **Overviews:** Each area's Overview is built from its tasks, goals and repeats, and goals due for review or stalled reach Ava; Learning's and Life's own records fold into tasks and goals once.
- **Today:** Energy in one tap, 1 to 5; 2 or below brings Lighter day.
- **Goals:** Two goals to a row.

### Changed

- **Why:** Learning and Life kept records of their own beside the tasks they described, so the same work was reported twice, and nothing said which area a task belonged in.
- **Areas by purpose:** a task's area goes by its purpose, the first that fits: Work when someone else expects it, Project for a step toward something you're building that has an end, Learn when the point is getting better at something, Life for everything else.
  - The task form lists each meaning, in English and Chinese. A new task added without an area or goal of its own, as from Today, gets the Orchestrator's suggestion once it has a title: from the local model while it runs, from keywords for each purpose otherwise.
  - It is chosen for you and named on a pencilled line until you choose an area yourself; a task added from an area takes that area, and a goal's task the goal's.
- **The one-time move:** the first time this version opens a database, each active habit becomes a flexible Life task on that day that repeats as the habit did, a weekly one on that day's weekday, with the Life agent's estimated length, and each learning subject becomes a Learning goal,
  - active while the subject was and completed once done or archived. A habit already on that day as a Life task, or a subject already a Learning goal, of the same name isn't made twice.
  - Life events were already fixed tasks and stay so; their category goes, and their Detail keeps what it said.
  - Habit logs, study sessions, inactive habits, every check-in (sleep, mood and energy), and subjects' difficulty and estimated minutes are dropped with their six tables, as are saved Summary reports, made again on request, and the plan checkpoints that copied them.
  - One transaction does it all, so a failure leaves the database as it was; there is no backup, as chosen.
- **Area screens:** every area has Overview and Tasks; the Check-in, Habits, Events, Sessions and Subjects tabs are gone, with their forms and their service routes. Learn shows each open goal's time this week, the time without a goal and when you last practised.
  - Life shows its repeats as habits, with how many were done this week and a streak of days, or weeks for a weekly one, done in a row, where today's copy still to do doesn't break it;
  - and the day's appointments (fixed Life tasks outside a repeat), lunch and dinner, free time left and energy.
  - Work shows the week's load by day, the day's meetings (fixed Work tasks) and what carried over from the 7 days before: tasks moved on from a set plan, and tasks still not done.
  - Project shows each open project's progress, last step done and next step, or Add the next step, which opens the task form for that goal.
- **Due for review and stalled:** an active Learning goal with nothing done or partly done for 3 days is due for review, and an active Project goal stalls, counting from its last such day or from when it was made.
  - Each shows on its area's Overview, pencilled under its agent, and the Learning or Project agent tells you through Ava once a day per goal; a paused or completed goal never does.
- **Energy on Today:** "How's your energy?", 1 to 5 under Today's header, one reading a day that can change only that day.
  - At 2 or below the Life agent asks for a lighter day as the check-in did: Lighter day comes first in plans proposed then, the row says so, and on a full day Ava says you reported low energy.
- **Agents and Summary:** the Learning and Life agents read their area's tasks, goals, repeats and energy. Learning's finding names when you last practised and its goals due for review; Life's the energy reported in the last 30 days and how its repeats went.
  - Summary's reports count repeats done of scheduled and the latest energy in place of the habit, session and note lines, and Life's advice draws on that energy.
- **Goals:** two goal cards to a row, of one height; one under 640 px.
- **Not in this release:** Ava can't add a task yet, so the area suggestion is the task form's.
- **Release:** the Mac app reports Version 3.5.0 (35), and the service 3.5.0.

### Checked

- **Evidence:** the service tests (411) and the interface helper tests (137) pass, and the interface build succeeds; each rule has its own test, written to fail first.
  - On a throwaway database made as v3.4 left one, the move ran when the service opened it, and Today's energy row, the area suggestion, Goals at 1600 and 375 px wide, each area's Overview and Ava's two new messages showed as described, with no errors.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-04 as `e711f48`, `e2803c7`, and `8b686dc`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v3-4-build-34"></a>

## v3.4 / build 34 — 2026-10-04

- **Title:** past tasks keep their place, linked repeats, and cleaner proposed plans
- **Past days:** Ava corrects, removes or moves a past task forward, but its start, length and timing stay put; a moved task is marked Moved to its new day and counts there.
- **Repeats:** A repeat's days are linked, so renaming a day keeps the habit whole; from a past day a repeat can start, stop or switch from today, and a change to a repeating task asks whether the repeat changes too.
- **Plans:** A deleted task leaves today's proposed plans rewritten without it, a meal change reaches every proposed plan of today, and a past plan's time by area leaves out Removed and Moved entries.
- **Cards:** "Move dinner today" and "on Fri 9 Oct".

### Changed

- **Why:** Ava's changes are aimed at today and later days. A past day should be corrected, never rearranged; a repeat should hold together however its days are called; and a proposed plan should never keep a task that is gone.
- **Past tasks:** about a past day, Ava corrects what a task is (its title, detail, goal, area or status), removes it, or moves it to today or a later day. On its past day a task keeps its start, length and timing, and nothing moves onto a past day:
  - such a request gets "a task keeps its place … Nothing was changed.", and a mixed one, such as "Review took 45 minutes and was partly done", proposes the status and says "Left out:
  - its length, as a past task keeps its place." The service refuses the same changes, whatever proposes them.
- **Moving a task forward:** on its new day the task is planned again, and a start, length or timing can be given there, with the overlap and meal checks; a day that already has its repeat's own day refuses it.
  - The past day's set plan keeps its entry, marked "Moved to {day}" / "已移到{day}", left out of that day's reports, area profiles, Calendar counts and time by area, and the task counts on its new day.
  - Both days' reports are made again and their area agents told; a new day today with plans proposed and none set has them proposed again with the task.
- **Linked repeats:** a new repeating task starts a repeat whose days carry one link; repeats recorded before are linked by their name and area the first time this version opens the database.
  - The next day is copied from the repeat's latest day by its link: daily, weekly on that day's weekday, or not at all once a day says it doesn't repeat; v3.2's weekday rule and v3.3's paused-goal rule still hold.
  - Summary counts a repeat's done days by link, under its latest name, so renaming a day doesn't split the habit.
- **Repeats from a past day:** "Make Read repeat daily" starts a new repeat from the past task, on today while there's still time (a start not yet passed, or a flexible task today's plan can still place), else tomorrow,
  - and a weekly one on the next day of the past task's weekday; the card says "Repeats daily from {day}; earlier days stay as they were.", and the past task and the days between stay as they were.
  - "Stop repeating Stretch" or "Repeat Stretch weekly" changes today's own day, unless it was reported or today's set plan scheduled it, when the change starts tomorrow; the days prepared after it follow.
- **A repeating task's past day:** changing its title, detail, goal or area makes Ava ask whether the change is for that day alone or for the repeat from today on too ("just that day" or "and the repeat"; 只改那天 or 连同以后).
  - The card says how many days change, and no other past day does. Removing or moving its day changes that day alone.
- **Proposed plans after a deletion:** a task deleted, or moved away, from today or a later day leaves that day's proposed plans at once:
  - each one's description and what sets it apart are rewritten from the tasks it has left, so nothing in it names the task, its time by area follows, and the other tasks keep their times. A past day's plans stay as they were.
- **Meals:** a confirmed meal change reaches every one of today's proposed plans, beside a set plan too; plans are proposed for today alone, so a change from a later day on reaches none yet.
- **Time by area:** a past plan's time by area, in Plans and in its day's totals, leaves out entries marked Removed or Moved to, which stay listed.
- **Card titles:** today and tomorrow drop "on" ("Move dinner today", "Move 1 task tomorrow"), and any other day keeps it before a short date ("Move dinner on Fri 9 Oct"); Chinese reads "调整今天的晚餐时间" and "调整10月9日周五的晚餐时间".
- **Release:** the Mac app reports Version 3.4.0 (34), and the service 3.4.0.

### Checked

- **Evidence:** the service tests (379) and the interface helper tests (130) pass, and the interface build succeeds; each rule has its own test, written to fail first, and the earlier tests that changed a past task's length or start were rewritten to the new rules.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-04 as `e711f48`, `e2803c7`, and `8b686dc`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v3-3-build-33"></a>

## v3.3 / build 33 — 2026-10-04

- **Title:** removed entries out of the counts, cleaner drafts, paused goals in Summary, and meal rules
- **Past plans:** A removed task's entry stays on show, marked Removed, but leaves Calendar's counts, Summary's reports and the area profiles.
- **Drafts:** A task deleted today leaves today's proposed plans.
- **Summary:** A paused goal's task still to do isn't counted as scheduled, and its repeat gets no keep advice.
- **Meals:** "From Friday on" moves a meal for good from that day, replacing one-day times; a meal ends by midnight; a paused goal's fixed task is in the way of a move.

### Changed

- **Why:** a few rules left counts, plans or meal times showing something other than what had happened or what was asked for.
- **Removed entries out of the counts:** a past task its day's set plan scheduled, once removed, keeps its entry in that plan, marked "Removed" / "已移除", in Calendar and in Plans, but the entry no longer counts:
  - Calendar's day counts, the day's tallies, Summary's day, week, month and all-time reports, and the area agents' profiles all leave it out. This replaces v3.0's rule that the plan's counts stayed as they were.
- **Drafts:** a task deleted today, or on a later day, leaves the plans proposed for that day and not yet set, so setting one can no longer schedule a task that is gone. A past day's proposed plans keep their own copy, as before.
- **Paused goals in Summary:** a task whose goal is paused, while it is still to do, isn't counted as scheduled; one reported before the pause still counts. A paused goal's repeating task gets no "Keep its next recurring block" advice.
- **Meals from a day on:** "Lunch 12:30–13:30 from Friday on", "starting tomorrow" or "从周五起" moves the meal for good from that day, where it used to be read as Friday alone.
  - A change from a day on replaces the meal's one-day times from that day, and the card names them, such as "It replaces the one-day lunch time on Friday 9 October (13:00–14:00)."; a one-day time set later still wins on its day.
- **Meals end by midnight:** "Dinner 23:00–24:00" reads 23:00–24:00 on the card as in Ava's answer, where the card used to show 00:00. "Dinner 23:30–00:30" is now taken as a meal request and answered "Dinner 23:30–00:30 would run past midnight; a meal ends by 24:00.
  - Nothing was changed.", with no card, before any question about the day.
- **Paused tasks in the way:** a fixed task whose goal is paused now stands in the way of a meal move as any other does, so it can't end up inside the meal once its goal resumes.
- **Release:** the Mac app reports Version 3.3.0 (33), and the service 3.3.0.

### Checked

- **Evidence:** the service tests (349) and the interface helper tests (124) pass, and the interface build succeeds; each rule has its own test, written to fail first, among them one showing Calendar's counts for a day drop a removed entry while it stays on show as Removed.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-04 as `e711f48`, `e2803c7`, and `8b686dc`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v3-2-build-32"></a>

## v3.2 / build 32 — 2026-10-04

- **Title:** past-day meal moves, repeat dates, and goal card order
- **Ava:** Moving lunch or dinner on a past day is refused in words, where a past day whose plan left that meal out used to fail.
- **Repeats:** A weekly task's next date is prepared on its own weekday, and a paused goal's repeating task is no longer prepared.
- **Goals:** A task with no start is listed last in its day on a goal card.

### Changed

- **Why:** a closer look at the behaviour added from v2.6 to v3.1 found four places where DayWright did something other than what it describes.
- **Past-day meal moves:** asking Ava to move lunch or dinner on a past day now gets "Past days keep the lunch times they had. Nothing was changed." in every case.
  - Before, a past day whose set plan had left that meal out, as a plan set after lunch does, made the request fail with no answer.
- **Weekly repeats:** a weekly task finished on two recorded days now has its next date prepared on the weekday it was last on, the next one after today; it used to land a week after the day the Summary report was made, whatever the task's weekday.
  - A daily task's next date is still tomorrow.
- **Paused goals:** a repeating task whose goal is paused is on hold, so its next date is no longer prepared.
- **Goal cards:** a task with no start is listed after the timed ones of its day, for days ahead and past days alike; it used to come first among a day ahead's tasks.
- **Release:** the Mac app reports Version 3.2.0 (32), and the service 3.2.0.

### Checked

- **Evidence:** the service tests (338) and the interface helper tests (122) pass, and the interface build succeeds; each fix has its own test, written to fail first.
  - In WebKit, on a throwaway database, a goal card listed "Early", "Late" and "No start" for one day, and Ava answered a lunch move on a past day whose plan kept dinner alone with that sentence and no card.

### Delivered

- **Status:** built in a separate worktree and committed on 2026-10-04 as `c5000bc`, `c1d4672`, and `664d89e`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v3-1-build-31"></a>

## v3.1 / build 31 — 2026-10-04

- **Title:** meal times through Ava, start over length on every schedule row, and goal cards of one height
- **Meals:** Ava moves lunch or dinner, from now on or for one day, and today's set plan is fitted around the new time or put up for review.
- **Schedules:** Every row on Today, in Calendar and in Plans shows its start with its length below it; a meal reads just Lunch or Dinner.
- **Goals:** Cards of one height, each listing up to three tasks, with Show all for the rest.

### Changed

- **Why:** lunch and dinner were fixed at 12:00 and 18:00 with no way to move them; schedule rows showed a task's time and length differently from place to place; and goal cards grew with their task lists, so their buttons never lined up.
- **Meal times through Ava:** "Lunch 12:30–13:30 from now on" or "Dinner 17:00–18:00 on Friday" proposes the change on a card, "Lunch: 12:00–13:00 → 12:30–13:30"; without "from now on" or a day, the Orchestrator asks which.
  - A change from now on starts today, so earlier days keep their meals, and a past day can't be changed.
  - The change is refused, with nothing saved, when the new time would take any of a timed task whose length you set, or the first 30 minutes of one whose length an agent estimated; the reply names the task. On Confirm, the agents look at the day again.
  - A set plan the meal overlaps by 30 minutes or less is fitted in place, an estimate shortened or a flexible task moved, and the card lists each change, such as "“Read”: 11:45–12:45 → 11:30–12:30".
  - With more, new plans are proposed and the set plan stays as it is until you pick one with Use Deep focus, or compare them in Plans. With no plan set, today's proposed plans are made again around the new time.
  - Plans, the day strip, the task form's start times and the agents' checks all use the meal times of that day.
- **Start over length:** every schedule row, on Today, in Calendar's day panel and in Plans, shows its start time with its length directly below it, and so do the meal rows on Today and in Plans; a task with no start shows its length alone.
  - A meal row reads just "Lunch" or "Dinner" / "午餐" or "晚餐".
- **Goal cards:** every card in Goals is the same height, with its buttons in line.
  - A card lists up to three tasks, today's and later ones first, then the most recent past ones, and keeps room for three; with more, "Show all 7 tasks" / "查看全部 7 个任务" opens the goal's Edit sheet at its task list.
- **Release:** the Mac app reports Version 3.1.0 (31), and the service 3.1.0.

### Checked

- **Evidence:** the service tests (335) and the interface helper tests (121) pass, and the interface build succeeds. In WebKit, on a throwaway database: Today, Calendar and Plans showed "11:45 / 1 h" and "15:00 / 30 min" in their time columns, with meals named "Lunch" and "Dinner";
  - goal cards with 0, 2 and 7 tasks were all 439 px tall with their buttons at the same height, and "Show all 7 tasks" opened the Edit sheet at TASKS IN THIS GOAL · 7; "Lunch 12:30–13:30 from now on" moved "Read" from 11:45–12:45 to 11:30–12:30 on Confirm;
  - "Dinner 17:00–18:00 today" put the set plan up for review, and Use Deep focus set a plan that keeps 17:00–18:00 free; and "Move lunch to 13:00" asked whether from now on or on one day.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-04 as `c5000bc`, `c1d4672`, and `664d89e`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v3-0-build-30"></a>

## v3.0 / build 30 — 2026-10-03

- **Title:** removed entries in past plans, Ava's "that task", and refusals in both languages
- **Past plans:** A removed task's entry stays in its past plan, marked Removed.
- **Ava:** "Remove that task" or "change it" right after naming a task means that task.
- **Refusal:** A direct change to a past task is refused in English or Chinese.

### Changed

- **Why:** a past plan that scheduled a task now removed should still show what it held, and say that the task is gone; "Remove that task" should mean the task just talked about; and a refused direct change to a past task should read in the interface's language.
- **Removed in past plans:** when a past task its day's set plan scheduled is removed, through Ava or from its goal's task list, that plan keeps the entry marked "Removed" / "已移除", in Calendar and in Plans.
  - Nothing else in the plan changes: the entry keeps its time and reported status, and the plan's counts stay as they were. The removal reaches the task's area agent and Summary as any removal does.
  - Removing a task today's set plan scheduled is still refused, with Report Skipped and Review a replacement offered.
- **Ava's "that task":** "Remove that task", "change it" or "删除那个任务", right after a message that named exactly one task, means that task, for a change or a removal.
  - After a message that named several tasks, the Orchestrator asks which of them; after one that named none, it asks which task, as before.
- **Refusal in both languages:** the service's refusal of a direct change to a past task, or of a move onto a past day, reads "A past task changes only through Ava.
  - Ask Ava to change it." or "过去的任务只能通过 Ava 更改。请告诉 Ava 要改什么。" wherever it shows: a notice or the task form.
- **Release:** the Mac app reports Version 3.0.0 (30), and the service 3.0.0.

### Checked

- **Evidence:** the service tests (299) and the interface helper tests (109) pass, and the interface build succeeds.
  - In WebKit, on a throwaway database: Ava's card for removing a past task its set plan scheduled said "The plan set for that day keeps its entry, as history."; Delete in the goal's sheet took two steps, with no refusal, and removed it;
  - Calendar and Plans then showed its entry "Openings · Removed · Done"; and "How did Morning chess go?" then "Remove that task" proposed removing "Morning chess", which applied on Confirm.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-04 as `c5000bc`, `c1d4672`, and `664d89e`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v2-9-build-29"></a>

## v2.9 / build 29 — 2026-10-03

- **Title:** changes reach their own agents, and past tasks only through Ava
- **Agents:** Each change goes to its task's own area agent and Summary, and they look at today again at once; a goal's pause reaches its area agent too.
- **Past days:** Only Ava and Delete in a goal's list change a past task, and a past task its plan scheduled can be removed, the plan keeping its entry.

### Changed

- **Why:** every change to a task should reach the Orchestrator, which hands it to the right area agent and to Summary and has them look again; until now each change rebuilt every area's profiles, and the agents looked at today only when it was opened.
  - A past task could still be edited by a request that bypassed Ava, and one its day's set plan scheduled couldn't be removed.
- **The right agents:** the Orchestrator hands each change to the area agent of the task's own area, both areas when a task moves between them, and every area a day holds when a plan is set, replaced, unset or proposed;
  - only those agents' task profiles are rebuilt, and Summary remakes the reports of the days it touched. Pausing, resuming or completing a goal now reaches its area's agent as well as Summary; creating, renaming or removing one reaches Summary.
- **A second look at today:** after every saved change, the concerned area agents look at today again, with the Orchestrator's checks of the whole day, and Ava posts anything new, such as a task that now keeps slipping, without waiting for today to be opened.
  - Each message is still posted once a day.
- **Past tasks only through Ava:** the service refuses any other edit of a past task, and a move of a task onto a past day: "A past task changes only through Ava; ask Ava to change it". The task form no longer offers a past date.
  - A confirmed change from Ava and Delete in a goal's task list still work.
- **Removing a past task a plan scheduled:** through Ava or from its goal's task list, a past task its day's set plan scheduled is now removed like any other; the plan keeps its entry, as history of what was scheduled and reported, and Ava's card says so.
  - Today's rule stays: a task today's set plan scheduled can't be removed, with Report Skipped and Review a replacement offered.
- **Release:** the Mac app reports Version 2.9.0 (29), and the service 2.9.0.

### Checked

- **Evidence:** the service tests (297) and the interface helper tests (107) pass, and the interface build succeeds.
  - The tests show a change reaching only its task's area profiles, the agents posting a slipping message as soon as a task changes, a goal's pause reaching its area's agent while a rename doesn't, direct edits of a past task and moves onto a past day refused,
  - and a past task its set plan scheduled removed through Ava and from its goal with the plan's entry kept, while today's stays.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-04 as `c5000bc`, `c1d4672`, and `664d89e`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v2-8-build-28"></a>

## v2.8 / build 28 — 2026-10-03

- **Title:** past tasks change only through Ava
- **Past days:** Read-only on screen again; a past task changes or is removed only through Ava, applied when you confirm, or is deleted from its goal's task list.
- **Agents:** Every change to a task, and every change to a goal, reaches the agents it concerns.
- **Goals and Tasks:** Clearer refusals with bordered OK buttons, and no goal filter on Tasks.

### Changed

- **Why:** since v2.5 a past task could be edited from its goal's sheet while Calendar showed its day as history. Now a past day is read-only on every screen, and a past task changes only through Ava, which shows the change before anything applies.
- **Calendar:** a past day's banner shows a lock and "Read-only · past day · You can view this day and its plan, not change them.", then the note when no plan was set, then, in small text, "To change or remove a task,
  - ask Ava." Its rows still have no status buttons and open nothing.
- **Through Ava:** about a past day, name a task and say what to change in your own words:
  - its title, detail, area, goal, day, start or length, or its status, reported late or put right ("Review took 45 minutes and was partly done", "Rename Review to “Read notes”", "Move Review to 2 Oct"), or ask to remove it ("Remove Review").
  - The Orchestrator asks which task when several fit or none does. Ava proposes the change on a card titled "Change “Review” on {day}" with each field before and after, or "Remove 1 task on {day}", and nothing changes until you confirm.
  - The checks a task's form has still apply: a start that overlaps another task is refused before anything is proposed, and a task moved after today goes back to planned.
  - A task its day's set plan scheduled can't be removed, the same as removing today's task the set plan scheduled; Ava says so, and its status can still change.
  - A past day's plans stay as they were: a removed task's entries in plans that were only proposed lose their link to it, and an edit keeps the plan's times while the plan's entry takes the new title, area and status.
- **Goals:** in a goal's Edit sheet a past task is history: a shaded row with a lock, its status as text, and Delete…, in two steps; one its day's set plan scheduled can't be deleted, which Delete says instead.
  - Under the list: "To change a past task, ask Ava." Today's and later tasks keep Edit.
  - A goal that can't be removed yet says how many tasks still link to it, one or several, and how to free them, and its button opens the goal's Edit sheet at its task list. On both refusal cards, OK has the same border as the button beside it.
- **Tasks:** the "Linked to {goal} · Show all tasks" filter is gone; the area switch stays. The note reads "A past task can be changed only through Ava", past days are headed "change through Ava", and an area showing a past day says the same.
- **Agents:** every change to a task reaches the agents it concerns:
  - the form, the status control, each Ava proposal (move, length, shorten, plan, and now edit and remove), deleting from a goal's list, setting, replacing or unsetting a plan, proposing plans, accepting or dismissing a suggestion, a timed Life event, and the area agent's refined estimate.
  - An edit confirmed through Ava reaches the area agents and Summary as one made on a form does; a task left on a past day raises no doubt, being a record put right.
  - Creating, renaming, pausing, completing or removing a goal now makes Summary's saved reports for today and for its tasks' days again, as reports list the goals; before, those changes reached no agent.
- **Also:** the capabilities list no longer offers important-to-keep commitments, which went with Protected in v2.6.
- **Release:** the Mac app reports Version 2.8.0 (28), and the service 2.8.0.

### Checked

- **Evidence:** the service tests (292) and the interface helper tests (107) pass, and the interface build succeeds.
  - In WebKit, on a throwaway database: the past-day banner showed its lock and three lines and no status buttons; a goal's refusal named its 4 tasks, had two bordered buttons, and opened the goal's sheet with focus on its task list;
  - the sheet's two past tasks had Delete… and its two later ones Edit, with the note under them; deleting the past task its set plan scheduled was refused, and deleting the other took two steps and kept focus in the list; Tasks had no goal filter and the new note;
  - and through Ava, "Review took 45 minutes and was partly done" proposed "Length: 1 h → 45 min" and "Status: Planned → Partial", applied on Confirm, and "Remove Review" removed it on Confirm.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-04 as `c5000bc`, `c1d4672`, and `664d89e`, with this record in the commit after them, on the branch `worktree-daywright-tasks-areas`.

<a id="v2-7-build-27"></a>

## v2.7 / build 27 — 2026-10-03

- **Title:** Ava closes with a click outside it
- **Ava:** No more folding down; a click anywhere outside Ava closes it, and its own button still opens and closes it.

### Changed

- **Why:** Ava's minus button folded it into a bar that still sat over the page, and closing Ava meant finding its close button or pressing Escape.
- **No folding:** the minus button and the folded bar are gone. Ava is either open or closed.
- **A click outside closes it:** a click anywhere outside Ava closes it, as Escape does, and Ava's own button in the top bar or bottom bar still opens and closes it.
  - A click that starts inside Ava, such as selecting its words, keeps it open wherever the pointer ends up, and a button elsewhere that opens Ava for a question, such as Ask about this day, keeps it open with that question.
  - A draft and an open proposal survive closing, as before.
- **Release:** the Mac app reports Version 2.7.0 (27), and the service 2.7.0.

### Checked

- **Evidence:** the service tests (275) and the interface helper tests (97) pass, and the interface build succeeds.
  - In WebKit, on a throwaway database, Ava had no minus button; a click on the page closed it; its own button opened and closed it; a click on its title and a selection dragged out of its conversation kept it open;
  - and Ask about this day opened it, and kept it open when clicked again while Ava was showing. The rebuilt Mac app reports Version 2.7.0 (27) with the microphone entitlement, and its frozen service carries 2.7.0.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="v2-6-build-26"></a>

## v2.6 / build 26 — 2026-10-03

- **Title:** changes handed only where they matter, doubts on form edits, and no more Protected
- **Agents:** The Orchestrator hands a task's change only to the agents it concerns, and a task moved or resized on its form gets its area agent's doubt in Ava.
- **Tasks:** Protected is gone; a length you set is what no plan shortens, and Summary prepares any repeating task you keep finishing.

### Changed

- **Why:** every change to a task, however small, rebuilt every area agent's profiles and Summary's saved reports, and an edit made on a task's form never got the area agent's view that the same change made through Ava did.
  - Protected overlapped with a length you set, which no plan shortens anyway, so it added a switch without adding a rule.
- **Only where it matters:** the Orchestrator looks at what an edit changed.
  - A new title, area, day, start, length or status reaches the area agents and Summary; a new detail, repeat or goal reaches Summary alone, as its advice reads them; an edit that changes none of these reaches no one, and the day's saved report stays as it was.
  - A task added, removed, reported or planned still reaches both.
- **Doubts on form edits:** when you move a task or change its length on its form, its area agent checks the change against the task's records, as it does for a request to Ava, and posts any doubt to Ava under its own name:
  - a start at least two hours from when you usually do it, or a length you have mostly left partly done. The edit stays saved; the doubt is only advice.
- **Protected is gone:** the switch, its flag on tasks and in plans, and "Kept protected" leave. Plans no longer put such tasks first in their area, and Lighter day may trim any estimated length; a length you set is still never shortened.
  - Summary's advice no longer treats a task as protected, and it prepares the next date of any repeating task you finished on two days, or asked twice to shorten, for your Accept. Tasks already marked keep working as ordinary tasks.
- **Release:** the Mac app reports Version 2.6.0 (26), and the service 2.6.0.

### Checked

- **Evidence:** the service tests (275) and the interface helper tests (97) pass, and the interface build succeeds.
  - New tests show that an edit that changes nothing keeps the day's saved report, that moving a task far from its usual time on its form posts its area agent's doubt, which agents an edit concerns, and that repeating tasks are prepared whether or not they were ever protected.
  - The rebuilt Mac app reports Version 2.6.0 (26) with the microphone entitlement, and its frozen service carries 2.6.0.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="v2-5-build-25"></a>

## v2.5 / build 25 — 2026-10-03

- **Title:** tasks editable from their goal, changes every agent hears of, and a clearer day strip
- **Goals:** A tidier Edit goal sheet where every task, past ones included, can be edited, and matching buttons on each card.
- **Agents:** Every change to a task reaches its area agent and Summary through the Orchestrator, so reports and advice follow it.
- **Ava:** Names the day it answers about, marks where the conversation turns to another day, shows when it is thinking, and folds to a small bar.
- **Today, plans and Calendar:** A day strip that shows the time now, the time gone and what the time left holds; paused tasks named wherever a plan shows them; past days that name the plan they used.

### Changed

- **Why:** the Edit goal sheet listed a goal's tasks without a way to edit them, and spent its space on a full-width area tag and long notes; the goal card's buttons didn't match. A change to a past task couldn't be made, and Summary's saved reports wouldn't have followed it.
  - The day strip's past shading was too faint to see, the time now sat far from its mark, lengths read "11 h 40" without "min", and nothing said the hours it left out were for meals.
  - Plans that still held a paused goal's tasks didn't say so, and Calendar showed those tasks as Planned. Calendar called a past day read-only and didn't say which plan it used.
  - Ava didn't say which day it was answering about, showed nothing while it thought, and folded down to a bar as wide as itself.
- **Edit goal:** the area and the time it spans sit side by side in one panel, a span within one day names its day once, and the tasks follow in a bordered list with their total length.
  - Every task has Edit, whatever its status and on whatever day, past ones included; it opens the task's form, and the goal's sheet comes back once the form is saved or cancelled, with anything typed in it kept. The form keeps the task's own goal while that goal is paused.
  - Edit, Remove… and Add task on each goal card now share one bordered style.
- **Past tasks:** a task on a past day can now be edited from its goal; its status stays as reported, and past days stay read-only everywhere else.
  - A task renamed on a day with a plan is renamed in that plan too, so Today's schedule and Summary show the new name; the plan keeps the times and lengths it set.
- **The Orchestrator hears of every change:** whenever a task or a plan changes, from a form, Ava, a report or setting a plan, the Orchestrator hands it on.
  - The area agents' task profiles are rebuilt from every record, and Summary makes the saved reports for the day, week and month of each date the change touched again, with their advice, the next time you open them.
  - A task moved to another day touches both days, and a report nothing touched stays as it was saved. An agent doesn't send a doubt about an edit made on a form; that stays with requests to Ava.
- **Day strip:** the time already gone is shaded clearly, the time now is printed under its mark, and a key under the hours splits the time left into meals, tasks and open time, with swatches like the strip's, adding up to the time left.
  - Every length reads like "3 h 30 min".
- **Paused tasks in plans:** a plan that still holds a paused goal's tasks, because it was made before the pause, marks each one Paused and says so under Constraints, and a plan made after the pause says which tasks it left out and why.
  - Today's Plan tab, the replacement review and Calendar's day panel do the same; Calendar used to show those tasks as Planned.
- **Calendar's past days:** the banner no longer calls a past day read-only. Titled "Past day", it says nothing changes there, that a task in a goal can still be edited from that goal in Goals, and, when no plan was set, that the day's tasks show as recorded.
  - The day's card names the plan it used, as "Plan used · Lighter day · 10:21", over its counts, with Open full day and Ask about this day at its foot, in one style. The Area and Tasks screens word their past days the same way.
- **Ava:** its header names the day it answers about, "About today" or "About Fri 2 Oct", as "Ask about this day" in Calendar opens it, and keeps that chip while Ava is folded down, so reopening it shows which day the conversation carries on with;
  - the box's placeholder names the day too. Each message keeps the day it was about, and the conversation is marked where it turned to another day. Three dots pulse while Ava thinks, and stay still when motion is reduced.
  - Folded down, Ava is now a small bar at its corner instead of a full-width title bar.
- **Release:** the Mac app reports Version 2.5.0 (25), and the service 2.5.0.

### Checked

- **Evidence:** the service tests (273) and the interface helper tests (97) pass, and the interface build succeeds.
  - New tests show that a past task can be edited and its day's, week's and month's reports are made again with it, on a day with or without a set plan, that moving a task off a past day remakes that day's report,
  - that a renamed task is renamed in its set plan and its report, how the time left splits, how a plan's paused tasks are named, and how lengths and spans read.
  - In WebKit, on a throwaway database, the goal sheet edited a past, done task and came back with its new title; plans named paused tasks as held or left out; Calendar showed them Paused, named a past day's plan and put its buttons in the day's card;
  - the strip showed the time now, the shading and its key; and Ava, opened from a past day, named that day, showed its dots while thinking, marked the turn to today, and folded to a 292 × 46 px bar.
  - The rebuilt Mac app reports Version 2.5.0 (25) with the microphone entitlement, and its frozen service carries 2.5.0.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="v2-4-build-24"></a>

## v2.4 / build 24 — 2026-10-03

- **Title:** edits that keep a task's reported outcome
- **Tasks:** Editing a task keeps the outcome already reported for it, including when its goal is paused.
- **Service:** Times of day are worked out in one shared place, with no change in behaviour.

### Changed

- **Why:** saving a task from its details sent back the status the form had when it opened, so an outcome reported in the meantime was overwritten, and an edit to a paused goal's task could be refused over a status nobody had changed.
- **Editing a task:** the task form has no status, and saving it no longer sends one. A saved edit keeps the outcome already reported for the task, whether done, partly done or skipped, and a paused goal's task can still be edited. Reporting it stays closed until the goal resumes.
- **Inside the service:** times of day are converted to and from minutes in one shared place, with no change in behaviour.
- **Release:** the Mac app reports Version 2.4.0 (24), and the service 2.4.0.

### Checked

- **Evidence:** the service tests (267) and the interface helper tests (88) pass, and the interface build succeeds.
  - New tests show that an edit sent without a status keeps "done", also on a paused goal's task, that the task form sends no status, and that a paused goal's plan entry can't be reported.
  - The rebuilt Mac app reports Version 2.4.0 (24) with the microphone entitlement, and its frozen service carries 2.4.0.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="v2-3-build-23"></a>

## v2.3 / build 23 — 2026-10-03

- **Title:** agents that answer back, goals that keep time, and a strip that always shows
- **Agents:** A task's area agent sends back its doubts about a change, Ava asks which task when unsure, and unrelated questions go to the Orchestrator alone.
- **Goals:** A time span set by their tasks, every task in the edit sheet, and pausing that pauses the tasks.
- **Summary and Today:** Week, month and all time broken down; a day strip that always shows the time left.

### Changed

- **Why:** A change asked through Ava went ahead even when the task's own records said otherwise, an unclear request fell back to proposing another plan, and every question went to every agent.
  - Goals had no time span, a paused goal's tasks still went into plans, Summary's week, month and all time couldn't be broken down, Ava showed Markdown marks as typed, and Today hid its timeline until a task was recorded.
- **Doubts and questions:** when you ask Ava to move a task or change its length, the Orchestrator hands the change to that task's area agent.
  - When its records disagree, it says so under its own name in Ava's conversation: a move at least two hours from when you usually do the task, or a length at which the task was mostly left partly done.
  - The change stays ready to confirm, because a doubt is only advice. A change naming no task Ava can find, or one that fits several, gets a question asking which task, instead of a proposal to switch plans.
- **The right agents:** a request reaches the area agent of each task it names, as well as the areas its words name.
  - A question about the day, its plans or your records, in English or Chinese, goes to every area agent; one about nothing in your day is answered by the Orchestrator alone. A change no longer always asks Learning and Life.
- **Ava's text:** bold, italics and headings the local model writes show as such instead of as asterisks and hashes.
- **Goals:** each goal shows the time it spans, from when you made it to that plus the length of every task in it, given or estimated by the task's area agent as it is saved;
  - adding a task extends it, from Goals or from Today, and nobody sets it by hand. Editing a goal lists every task in it with its day and status.
  - Pausing a goal pauses its tasks: plans skip them, they can't be reported until the goal resumes, and Today, its day strip, the task's details and its area show them in a paused colour with a pause sign and a label. A task is never paused on its own.
- **Summary:** in Calendar, Week lists its days, Month its weeks and All time its months, newest first, each with what was done by area and its own advice, made fresh when you open it. "Read the report" and the other expanders end with a chevron that turns when open.
- **Today:** the day strip always shows, even before anything is recorded, when it says "No tasks yet".
  - The time already gone is shaded, the now mark stays at the strip's ends before 09:00 and after 22:00, and the caption says the time now, how much of the day is left before 22:00, and how much of that is open.
- **Release:** the Mac app reports Version 2.3.0 (23), and the service 2.3.0.

### Checked

- **Evidence:** the service tests (264) and the interface helper tests (87) pass, and the interface build succeeds; the helper tests cover the Markdown marks in Ava's replies.
  - On a throwaway database, Ava asked which task for a move naming none, gave the Project agent's length doubt, and kept the user's message above its reply; a paused goal's tasks showed in the paused colour on Today and on the strip, with their time left open;
  - a goal showed its span and the edit sheet its tasks; Week and All time listed their days and months; and an empty day showed the strip with the time left. The rebuilt Mac app reports Version 2.3.0 (23) with the microphone entitlement, and its frozen service carries 2.3.0.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="v2-2-build-22"></a>

## v2.2 / build 22 — 2026-10-03

- **Title:** agents that know every record, vote on plans, and speak up
- **Agents:** Each area agent knows every task from all your records, one profile per task, and votes for up to three plans; the Orchestrator decides.
- **Ava:** A message when a task keeps slipping, a length looks off, the day won't fit, or energy is low on a full day, with a red dot on Ava's button until you open it.
- **Summary:** All time in Calendar, and what the area agents see in every report.

### Changed

- **Why:** The area agents looked back only 30 days, the Orchestrator chose plans without asking them, nothing told you when a task kept slipping or the day couldn't fit, and Summary covered a month at most.
- **All your records:** each area agent now knows every task from all your records. They are summed up in one profile per task, in the same local SQLite database:
  - how often it was done, partly done or skipped, its latest reports and whether it is lately slipping or improving, its usual length and start time, how often a plan or you changed its length, and how often you asked to shorten it.
  - The profiles are rebuilt when DayWright starts and after every change to a task, a report, a plan or a message to Ava, so the database keeps one row per task rather than a second history. An agent reads only its own area's profiles.
  - A new task's estimated length draws on every length you ever gave it. Summary's advice to the plans still draws on the 30 days before the day, so it stays current, and a Life check-in older than that no longer advises a lighter day.
- **Votes:** before plans are proposed, each area agent votes for up to three plans that suit its own tasks:
  - Deep focus for tasks to keep together, Your usual rhythm for tasks with a usual time, Easiest first or Lighter day for a task that is slipping, Quick wins first for short tasks, Breathing room or Lighter day for Life, and Finish early around Work's fixed meetings.
  - The Orchestrator has the local model choose the two plans beside Balanced with every agent's votes in front of it; without the model the votes decide, and a plan chosen that way names the agents that voted for it. Plans lists each area agent's votes under its findings.
- **A different plan:** asked for another plan, Ava offers the one the area agents vote for among the day's other plans, and an area your message names counts double; asking for a lighter day still offers Lighter day.
- **Ava's messages:** each time today is opened, the Orchestrator asks the area agents what needs your attention.
  - Each of these becomes one message from Ava, once a day, naming the agent that found it: a task that keeps slipping; a task mostly left partly done, or whose length you keep changing;
  - tasks without a time that won't fit what is left of the day before 22:00, when no plan is set; and low energy in today's check-in on a day whose tasks without a time fill at least 70% of the free time, unless Lighter day is already set.
  - A red dot on Ava's button, in the title bar and in a phone's bottom bar, marks a new message until Ava is open and unfolded, and is read aloud as "New message". Opening today never waits on these messages.
- **Summary:** Calendar's Summary agent tab adds All time to Day, Week and Month, covering every record so far; it is made fresh each time and is never saved or used as advice.
  - Every report now lists what the area agents see among its tasks: the ones that keep slipping, whose length looks off, and that are going well. Each agent's one line says it now votes and reports issues.
- **Release:** the Mac app reports Version 2.2.0 (22), and the service 2.2.0.

### Checked

- **Evidence:** the service tests (232) and the interface helper tests (76) pass, and the interface build succeeds.
  - On a throwaway database with a slipping task, a task mostly left partly done and a low-energy full day, Ava posted the three messages once, the red dot showed in the title bar and on a phone's bottom bar and cleared when Ava opened, Plans listed each area agent's votes,
  - and Calendar's All time showed what the area agents see, in English and Chinese. The rebuilt Mac app reports Version 2.2.0 (22) with the microphone entitlement, and its frozen service carries 2.2.0.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="v2-1-build-21"></a>

## v2.1 / build 21 — 2026-10-02

- **Title:** one job per agent, a day strip, and Ava by voice
- **Today:** A day strip in the header: timed tasks, meals, now, what is next and the open time before 22:00.
- **Agents:** Orchestrator, area agents, Summary, each with its one job under its name; the closing Orchestrator step is gone.
- **Ava:** No repeated place, date or model line; wider, a 12 px gap and an adjustable height; the microphone in the send button, with words shown as you speak.

### Changed

- **Why:** Today's header left a wide empty gap; the Orchestrator's closing step and the Summary agent both claimed to combine the agents' work; and Ava's window repeated what the page already shows, could not change height, and could not use the microphone in the Mac app.
- **Day strip:** Today's header shows the day from 09:00 to 22:00 between the date and the buttons: timed tasks in their area colours, lunch and dinner kept free, a mark for now, what is next, and how much time is still open before 22:00.
  - Beside a sheet or on a phone it takes its own row.
- **One job per agent:** a route now reads Orchestrator, the four area agents, Summary. The Orchestrator runs once and says whom it asked and what came of it, such as the plans it chose; the closing "Orchestrator · finish" step is gone.
  - Summary sums up what the area agents found and, for plans, the days before. In Ava's replies the area agents now review their tasks against the last 30 days, as they do for plans, instead of giving stock advice.
  - Under each agent's name, one line says its job, in Plans and in a reply's agents. When DayWright starts, a plan route saved before is rebuilt by the current agents; the plans stay as they were.
- **Ava's panel:** the context chip with the place and date, and the model line under the box, are gone, since the page and the top bar already show them; replies show Ava's avatar without repeating its name.
  - The window is a little wider, so the three suggested questions sit on one row, and sits 12 px from the window's edges instead of 24. Drag its top edge, or use the arrow keys on it, to change its height; DayWright remembers it, and a double-click restores it.
- **Voice:** the Hold to talk button is gone. Press the microphone beside an empty box and speak: the words appear in the box as you say them, transcribed on this Mac every 1.5 seconds; press stop to finish, then read them over and send.
  - The Mac app now carries the microphone entitlement, so macOS asks once instead of refusing.
- **Release:** the Mac app reports Version 2.1.0 (21), and the service 2.1.0.

### Checked

- **Evidence:** the service tests, the interface helper tests and the interface build pass. On a throwaway demo database, the strip filled the header at every width checked, Plans showed the new route with a role under each agent, and Ava's questions fit one row in every place in both languages;
  - with a simulated microphone and transcriber, words appeared in the box while speaking and the full sentence after stop.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="v2-0-build-20"></a>

## v2.0 / build 20 — 2026-10-02

- **Title:** Ava, a floating assistant
- **Ava:** The assistant is now Ava, a window floating over the page that never narrows it, opening beside an open sheet; it can be moved and folded down.
- **Questions:** No mode switch: Ava works out whether a message asks, changes or reports, suggests three questions for the place on show, and answers from the plans, findings, goals and last week.
- **Title bar:** A larger icon and wordmark.

### Changed

- **Why:** the assistant, called Talk, docked beside the page and narrowed it, most of all with the New task sheet open too; it needed its mode chosen before each message; and it answered from little more than the day's tasks.
- **Name:** the assistant is now Ava (艾娃 in Chinese), on the ⌘K button, the phone's bottom bar, its window and its replies.
- **Floating window:** on desktop Ava is a 420 × 600 window floating over the page, which never narrows it. It opens in the bottom-right corner, or just left of an open sheet. Drag its title bar to move it, and DayWright remembers where; double-click the title bar to put it back.
  - The minus button folds it down to its title bar. A phone keeps the sheet.
- **No modes:** the Ask, Adjust and Report switch is gone.
  - Ava works out from the words whether a message asks, changes or reports, and labels its reply Question, Change or Report: "Can you move Review to 3pm?" is a change, "Show me what I did yesterday" a question, and "I spent 30 minutes on Review" a report.
  - Proposed changes still wait for Confirm.
- **Suggested questions:** with the box empty, Ava offers three questions for the place on show, such as "What should I do next?" on Today, "How do these plans differ?" on Plans, and "Which goal needs attention?" on Goal.
  - Asking for a different plan opens Ava with "Replace this day's plan with a better one" ready to send, which proposes one.
- **Smarter answers:** Ava now reads the day's frame and meal hours, the set and proposed plans with why each was suggested, the area agents' findings, goals with how many of their tasks are done, and the last 7 days by area (up to today for a day still ahead),
  - and is asked to name the tasks, times and plans its answer rests on. A long day is shortened to fit the model. A reply can run a little longer.
- **Title bar:** the app icon and the DayWright wordmark are larger: 34 px and 22 px, and 30 px and 19 px on a phone.
- **Release:** the Mac app reports Version 2.0.0 (20), and the service 2.0.0.

### Checked

- **Evidence:** the service tests, the interface helper tests and the interface build pass.
  - On a throwaway demo database, the page kept its width with the New task sheet and Ava open together, Ava sat beside the sheet, moved, folded and put itself back, offered its questions, and the local model answered "What should I do next?" naming two tasks and their goals;
  - Ava was also checked in Chinese and at phone width.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="v1-9-build-19"></a>

## v1.9 / build 19 — 2026-10-02

- **Title:** Propose again, and no stale plans
- **Plans:** Propose again rebuilds today's plans that aren't set from your tasks as they are now, and today's plans from an earlier version are proposed again when DayWright starts; a set plan stays as set.
- **At a glance:** The box spans its plan's column again.

### Changed

- **Why:** plans proposed before a length was set, or by an earlier version, kept trimming or stretching lengths the user had set, and nothing could propose them again.
- **Propose again:** today's Plans page has a Propose again button. It proposes the plans you haven't set again, from your tasks as they are now, with the local model choosing; a plan you set stays exactly as set, and the new plans take the other places.
  - The plan route says so.
- **Earlier plans:** when DayWright starts, today's plans proposed by an earlier version, before plans kept their sentences, are proposed again the same way by DayWright's own ranking, without waiting for the model. Past days stay as they were.
- **Proposing:** both propose buttons read "Proposing…" and wait while the local model chooses, which can take up to about 40 seconds.
- **At a glance:** the box spans its plan's column again.
- **Release:** the Mac app reports Version 1.9.0 (19), and the service 1.9.0.

### Checked

- **Evidence:** the service tests, the interface helper tests and the interface build pass. On a throwaway demo database, each plan's box spanned its column and Plans offered Propose again.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="v1-8-build-18"></a>

## v1.8 / build 18 — 2026-10-02

- **Title:** plan types explained, and a centred At a glance box
- **Plans:** A Plan types tab beside How the agents made these plans lists every kind of plan, what it does and when it is offered, and each plan's At a glance box is centred.

### Changed

- **Why:** each plan's At a glance box sat against the left of its column, and nowhere listed the kinds of plan DayWright can propose.
- **At a glance:** the box stays only as wide as its content and is now centred in its column.
- **Plan types:** under the plans, "How the agents made these plans" gains a second tab, Plan types.
  - It lists every kind of plan, Balanced first, each with its one-line description and when it is offered, under a line saying Balanced is always offered and the local model picks two others for the day.
- **Release:** the Mac app reports Version 1.8.0 (18), and the service 1.8.0.

### Checked

- **Evidence:** the interface helper tests and the interface build pass. On a throwaway demo database, each plan's box measured the same space on both sides, and the Plan types tab listed all eight kinds in English and Chinese.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="v1-7-build-17"></a>

## v1.7 / build 17 — 2026-10-02

- **Title:** the day-ring icon
- **Icon:** A new icon: the day from 09:00 to 22:00 as a ring in the four area colours, with lunch and dinner left open, around a check.

### Changed

- **Why:** the icon still showed the earlier planner, its tabs in colours DayWright no longer uses.
- **Icon:** the day from 09:00 to 22:00 as a ring in the four area colours, in priority order, work, project, life, then learning, with lunch and dinner left open, around the set plan's check, on DayWright's indigo. It was chosen from four drafts drawn in the app's own colours.
- **Where it is used:** `Resources/DayWrightIcon.png` is the 1024-pixel master in the macOS rounded square. The favicon and title-bar icon `public/icon.png`, the five app icons in `src-tauri/icons/`, and the project folder's Finder icon are made from it.
- **Release:** the Mac app reports Version 1.7.0 (17), and the service 1.7.0.

### Checked

- **Evidence:** the rebuilt app's `icon.icns` matches the regenerated one and its signature verifies; drawn as Finder draws them, the app and the project folder show the ring in the macOS rounded square with no frame, and the opened app shows it in its title bar.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="v1-6-build-16"></a>

## v1.6 / build 16 — 2026-10-02

- **Title:** the local model chooses the plans; lunch and dinner at set hours
- **Plans:** The local model reads the day and picks the two plans beside Balanced, with its reason in English and Chinese; DayWright's own ranking picks when the model is off, and a day gets three plans whenever three different ones can be made.
- **Meals:** Lunch 12:00–13:00 and dinner 18:00–19:00 are kept free, and no task can be fixed over them.
- **Lengths:** A length you give, in the form or through Talk, is at least 30 minutes.

### Changed

- **Why:** plans should be chosen from the day itself by the local AI, three every time, around fixed mealtimes, and a length you give should be at least 30 minutes however you give it.
- **Plans:** Balanced is always first.
  - The planner builds every other kind of plan the day allows, then the Orchestrator has the local model read the day, from the tasks, their details and lengths, fixed times and free time to the agents' findings, energy, Summary advice and the plans you set most often,
  - and pick the two that suit it best. Each comes with the model's reason, in English and Chinese, shown after the agent icon as the Orchestrator's. When the model is off or answers unusably, DayWright's own ranking picks, and the plan route says which happened.
- **Three plans:** a day gets three plans whenever three different ones can be made, clearly different ones first. Lighter day and Breathing room leave their gap after fixed tasks too, and Lighter day starts later still, an hour at a time, when 10:00 would repeat another plan.
  - A day with nothing to place keeps Balanced alone.
- **Meals:** lunch is 12:00–13:00 and dinner 18:00–19:00. The task form greys out start times that would run into them ("Kept for lunch"), the service refuses them, and Talk moves a task to the next free time after them.
  - A meal a Life event already takes is left out of that day's plans.
- **Lengths:** a length you give, in the form or through Talk, is at least 30 minutes; asking Talk for less proposes 30. A task that already has a shorter length can still be reported; editing it in the form asks for 30 or more.
  - An area agent's estimate, and plans' trims of it, keep their 15-minute floor.
- **Release:** the Mac app reports Version 1.6.0 (16), and the service 1.6.0.

### Checked

- **Evidence:** the service tests, the interface helper tests and the interface build pass. Plans, the task form and Today were checked on a throwaway demo database in English and Chinese.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="v1-5-build-15"></a>

## v1.5 / build 15 — 2026-10-02

- **Title:** optional lengths and a pool of clearly different plans
- **Lengths:** A task's length is optional; its area agent estimates a blank one, and plans shorten only estimated lengths, never below 15 minutes.
- **Plans:** Balanced plus up to two of seven kinds that suit the day, each clearly different and saying why it was suggested and what sets it apart, between 09:00 and 22:00 with lunch and dinner kept free.
- **Talk:** Talk can give a task any length.
- **Goal:** The Records place is now called Goal, and the model status has no dot.

### Changed

- **Why:** with every task at least 30 minutes long, Balanced, Focused, and Gentle differed by little more than a quarter hour, and plans could shorten lengths the user had chosen.
- **Lengths:** the task form's length is optional.
  - Left blank, the task's area agent gives it a length at once, from the same task's lengths over the last 90 days, else the area's, else 30 minutes, and then asks the local model in the background; the answer replaces the first estimate unless you have given a length meanwhile.
  - Estimates read "≈ 40 min" and name their agent. A length you type is at least 30 minutes; Talk ("make Review 10 minutes", "把 Review 改成 20分钟") can set any length once you confirm it.
- **Shortening:** plans never shorten a length you set. A length an agent estimated can lose 15 minutes at a time, never going below 15, when you asked to shorten the task, when its agent found it often unfinished, or in Lighter day.
  - A finding about a task with your own length says it keeps that length.
- **Day frame:** plans place tasks between 09:00 and 22:00 and keep an hour free for lunch and for dinner, at the free hour nearest 12:00 within 11:30–14:00 and nearest 18:00 within 17:30–20:00. A meal whose window has passed or is taken is left out.
  - Plans and Today show the meals in the schedule.
- **Plans:** Balanced is always first: the areas take turns by priority, work and project first, then life, then learning.
  - Beside it come up to two of: - Deep focus: work, project, and learning back to back in the day's longest free stretch; - Lighter day: nothing before 10:00, life first, 15 minutes after each task, and an estimated length trimmed;
  - - Finish early: the gaps between fixed times filled as fully as possible; - Quick wins first: tasks of 30 minutes or less first; - Easiest first: the tasks you usually finish first; - Your usual rhythm: tasks near the times you usually do them;
  - - Breathing room: an even gap of up to an hour between the tasks of a light day.
- **Choice:** the kinds that suit the day come first, and the kinds you set most often in the last 30 days before them; on a day with fewer than three tasks to place, Deep focus and Lighter day lead. On a low-energy day Lighter day is listed first.
- **Clearly different:** a plan is offered only when, against every plan before it, its tasks come in another order and move at least an hour in all, or it ends at least an hour sooner or later. A day may therefore get one or two plans.
- **Descriptions:** each plan says why it was suggested, then, under "What sets it apart", what only it does, naming its tasks and times, in English and Chinese.
- **Interface:** the Records place is now called Goal, and the model status in the title bar has no dot.
- **Release:** the Mac app reports Version 1.5.0 (15), and the service 1.5.0.

### Checked

- **Evidence:** the service tests, the interface helper tests and the interface build pass. On a throwaway demo database, Plans, the task form and Today with a set plan were checked in English and Chinese, with no page errors.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="v1-4-build-14"></a>

## v1.4 / build 14 — 2026-10-02

- **Title:** a narrower At a glance box
- **Plans:** The At a glance box is only as wide as its content, leaving no empty band on its right.

### Changed

- **Why:** each plan's At a glance box spanned the whole column, leaving a wide empty band to the right of short values such as 09:30.
- **At a glance:** the box is now only as wide as its labels and values, and never wider than the column; a long task name still wraps inside it.
- **Release:** the Mac app reports Version 1.4.0 (14), and the service 1.4.0.

### Checked

- **Evidence:** the interface builds and its helper tests pass; Plans was captured on a throwaway database to check the box in each column.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="v1-3-build-13"></a>

## v1.3 / build 13 — 2026-10-02

- **Title:** justified text and a clearer glance
- **Text:** Paragraphs and list text that wrap are justified to both edges, with English hyphenated where it helps.
- **Plans:** At a glance shows each task on one line and its time or length change, such as 30 min → 45 min, on the next.

### Changed

- **Why:** text that wrapped left a ragged right edge, as in a plan's rationale, and At a glance ran a task's name and its length change together, so "(was 30 min)" broke across lines.
- **Text:** every paragraph, list item, and glance value that wraps is justified, lining up on both edges; its last line, and any text on one line, stays at the start. English text is hyphenated where that avoids wide gaps; Chinese spreads between characters.
  - Headings, buttons, chips, and tables keep their own alignment.
- **At a glance:** the labels take only the width they need. Starts with shows the quoted task on one line and its start time under it; Lengths shows each changed task the same way, with its change under it, such as 30 min → 45 min.
- **Release:** the Mac app reports Version 1.3.0 (13), and the service 1.3.0.

### Checked

- **Evidence:** the interface builds and its helper tests pass; Plans was captured on a throwaway database, in English and Chinese, to check the glance and the justified rationale.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="v1-2-build-12"></a>

## v1.2 / build 12 — 2026-10-02

- **Title:** notices with a title line
- **Notices:** A notice with a title, such as Read-only · past day, shows the title on its own line and the explanation under it.

### Changed

- **Why:** a notice such as "Read-only · past day · You can view this day and its plan, not change them." ran its title and its explanation together in one line.
- **Notices:** the three notices that have a title, Read-only · past day in Calendar, Demo workspace, and Example plan, now show the title in bold on its own line, the explanation under it, and their icon beside the title.
- **Release:** the Mac app reports Version 1.2.0 (12), and the service 1.2.0.

### Checked

- **Evidence:** the interface builds and its helper tests pass; a past day in Calendar was captured on a throwaway database to check the layout.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="v1-1-build-11"></a>

## v1.1 / build 11 — 2026-10-02

- **Title:** proposed plans, their first task, and quoted names
- **Plans:** Proposed plans read "Proposed" instead of "Draft", and Starts with names a plan's first task.
- **Quotes:** Task names are quoted in every plan description, old ones included, and in the plan lists and the agents' findings.

### Changed

- **Why:** each plan carried a "Draft" chip, as if it were unfinished; Starts with read "Nothing to place" when a plan held only fixed tasks; and plans proposed by older versions still named tasks without quotation marks, as did the plan lists and the agents' findings.
- **Proposed:** a plan the agents proposed carries a "Proposed" chip, and the counts read "3 proposed by local agents" in Plans and "3 proposed plans · none set yet" on Today's Plan tab, in English and Chinese.
- **Starts with:** names the plan's first task and its time, fixed or placed, and reads "No tasks" only for an empty plan.
- **Quotes:** every plan description is quoted when DayWright starts, including the oldest wordings, such as Adds 15 minutes to “this is title” where the saved calendar has room.
  - The plan lists (Kept fixed, Kept protected, Not in this plan, Kept as you set them) and every agent finding, such as “Evening walk”: done 3 times, quote the task too.
- **Release:** the Mac app reports Version 1.1.0 (11), and the service 1.1.0.

### Checked

- **Evidence:** 97 backend tests pass, including quoting the two oldest wordings once; 37 interface helper tests pass, including a plan with only fixed tasks; the interface builds.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="v1-0-build-10"></a>

## v1.0 / build 10 — 2026-10-02

- **Title:** the first numbered release
- **Numbering:** DayWright now carries a version and build, starting at v1.0 build 10; the Mac app reports Version 1.0.0 (10).
- **Contents:** The first numbered build holds the six changes recorded below on 2026-10-02, from the four areas to one dropdown and one set of buttons.

### Changed

- **Why:** DayWright had only dated history, so nothing in the app or the README said which build you were running.
- **Numbering:** versions read v1.0, v1.1 … v1.9, v2.0, and the build is major × 10 + minor; every change except a documentation-only one advances both. The [version and build policy](CONTRIBUTING.md#version-and-build-policy) lists where the numbers live. Records before this one stay dated.
- **In the app:** the Mac app's version is 1.0.0 and its build 10, so About DayWright reads Version 1.0.0 (10); the local service reports 1.0.0 too.
- **Contents:** this build holds every change recorded on 2026-10-02 after the pypdf rebuild: [areas and untimed tasks](CHANGELOG.md#areas-and-untimed-tasks), [fitted screens](CHANGELOG.md#fitted-screens), [Today's tabs and the Plan tab](CHANGELOG.md#today-tabs-and-plan-tab), [the agents' review](CHANGELOG.md#agent-findings), [fixed start times and plans at a glance](CHANGELOG.md#start-times-and-plan-glance), and [one dropdown and one set of buttons](CHANGELOG.md#consistent-controls).

### Checked

- **Evidence:** the built app's `Info.plist` reads `CFBundleShortVersionString` 1.0.0 and `CFBundleVersion` 10.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="consistent-controls"></a>

## One dropdown and one set of buttons — 2026-10-02

- **Dropdowns:** Every dropdown, from a task's or goal's status to start times, goals, and subjects, is now the same menu, with notes and a check on the choice.
- **Buttons:** Icon-only buttons share one style, and standalone text links became quiet buttons.

### Changed

- **Why:** a goal's status, a task's goal, a learning subject, and event times used the system's own lists and time fields while a task's status used DayWright's menu, and icon-only buttons came in two styles.
- **Dropdowns:** every dropdown is now the same component: a button naming the choice, and a menu whose options can carry a glyph and a note, with a check on the chosen one and disabled options that say why.
  - It comes in two sizes: compact, for a task's or a goal's status, and field, for start and end times, a task's goal, and a learning subject. Escape closes only the menu, never the sheet around it.
- **Goal status:** reads Active, Paused, or Completed, each with its note (plans may use it, plans skip it, kept in history), in the same menu as a task's status.
- **Buttons:** icon-only buttons, such as Close in sheets and Talk, a Library source's Remove, the plan pager, the month arrows, and steppers, are all the shared button at 40 × 40: quiet for close and remove, outlined for the rest.
  - "Open network log" and "Show all" in Library became quiet buttons; text links remain only inside a line of text, such as a banner.

### Checked

- **Evidence:** the interface builds and its 37 helper tests pass.
  - On a throwaway database the task status, goal status, a task's start time and goal, and a Life event's start were opened and closed with Escape, with taken times disabled and named; Escape inside the task sheet now leaves the sheet open.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="start-times-and-plan-glance"></a>

## Fixed start times, moving tasks in Talk, and plans at a glance — 2026-10-02

- **Fixed tasks:** A start time taken by another timed task, for the task's length, is greyed out and names that task.
- **Talk:** "Move Review to 10:30" proposes moving the task there, or to the nearest free time.
- **Plans:** Each plan says in one line how it works and shows its first task, when the day ends, and the lengths it changed.
- **Quotes:** Task names in a plan's description are in quotation marks.

### Changed

- **Why:** a fixed task could be given a start that overlapped another, which later stopped plans from being proposed; there was no quick way to move a task; and the three plans were told apart only by long rationales that ran task names into the surrounding words.
- **Start times:** a fixed task's Start is a dropdown of quarter hours. A start that would overlap another accepted timed task that day for the task's length, or run past midnight, stays in the list, greyed out, with a note such as "Overlaps “Team stand-up”".
  - Switching to Fixed picks the next free start; if a longer length makes the start clash, an alert names the task and its time, suggests asking Talk to move it, and Save waits. A timed Life event's start and end use the same lists.
  - The service also refuses an overlapping task, naming the one in the way; an edit that keeps a task's day, start, and length is never refused.
- **Talk:** in Adjust, naming a task and a time ("Move Review to 10:30", "3pm", "下午3点") proposes moving it, as a fixed task, to that time. When the time is taken, the reply says by what and proposes the nearest free start instead.
  - Nothing moves until you confirm, and the time is checked again then. Plans already proposed keep their schedule.
- **Overlaps found later:** when tasks already overlap and plans are proposed, the message names both, such as "“Meeting” (10:00–11:00) and “Call” (10:30–11:00) overlap".
- **Plans at a glance:** each plan opens with one line saying how it works: Balanced "Even spread: the areas take turns, from your first free time.", Focused "Focus first: learning, then project and work, while you are fresh.", and Gentle "Easy pace:
  - starts later, life first, with a break after each task." Below it, every column shows the same three facts: Starts with (the first task it places, and when), Done by, and Lengths (each task it lengthened or shortened, with its recorded length). The full rationale follows in smaller type.
- **Quotes:** a plan's rationale puts task names in quotation marks, such as gives “Review notes” 15 more minutes, in English and Chinese; plans saved before get the quotes when DayWright starts.

### Checked

- **Evidence:** 97 backend tests pass, including: refusing an overlapping task while allowing one that starts as another ends, the same time on another day, and a rename; Talk proposing the nearest free time and moving the task once confirmed, from "10:30", "3pm", and "下午4点半"; naming overlapping tasks;
  - and quoting saved rationales once. 37 interface helper tests pass, including the start-time list, a plan's glance, and reading a move proposal.
  - On a throwaway database the Start list greyed out 09:45–10:30 around a 10:00 stand-up and a 10:15 call, a 2-hour task at 09:00 showed the clash and held Save, and Talk proposed 10:45 for "Move Evening walk to 10:15".

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="agent-findings"></a>

## Area agents review each task against the last 30 days — 2026-10-02

- **Agents:** Each area agent reviews its tasks for the day against the last 30 days and says what it found, task by task.
- **Plans:** A task often left partly done or skipped gets 15 minutes less, and a flexible task usually done at a steady time goes near that time.
- **Lighter day:** When the Life agent finds low energy, Gentle is listed first and says why.
- **Earlier plans:** Plans proposed by an earlier version get their agent list rebuilt by every current agent at start.
- **Overlaps:** When tasks with a start time overlap, proposing names them and their times.
- **Shown:** Plans and Today's Plan tab list each agent's findings in English or Chinese.

### Changed

- **Why:** a plan's route listed five agents, but the area agents only counted the day's tasks, so nothing showed how they took part or what they knew about your habits.
- **Review:** before plans are proposed, the Learning, Life, Work, and Project agents each review their tasks for the day against the reports of the 30 days before it, task by task, by name and area: - partly done or skipped at least twice, and in at least half its reports:
  - 15 minutes shorter, never under 30, with the task's first step named when it has one; - the same, but fixed, protected, or already 30 minutes: it keeps its length, and says why; - done at least twice and in three of every four reports:
  - it keeps its length; - a flexible task done at least twice, with starts no more than two hours apart: plans place it near its usual time, on the quarter hour; - asked to be shortened twice or more:
  - 15 minutes shorter, as before; - not on the list in that time, or never reported: nothing to learn from yet.
- **Area records:** Learning adds its sessions in those 30 days; Life adds today's check-in, or the latest one before it, and the habit reports, asking for a lighter day at energy 2 of 5 or lower; Work adds today's fixed meetings, which flexible work goes around.
- **Plans:** all three plans apply the shorter blocks and usual times. A task with a usual time is placed first, at the first free time from then; when nothing is free after it, it takes the day's first free time like any other. The Balanced rationale says so.
  - When the Life agent advises a lighter day, Gentle is listed first, shown first on a phone, and its rationale opens with "Listed first because the Life agent advised a lighter day." When two tasks with a start time overlap, or one runs past midnight,
  - proposing stops and names them with their times, such as "Meeting (10:00–11:00) and Call (10:30–11:00) overlap".
- **Shown:** at the foot of Plans, "How the agents made these plans" lists every agent in order with its findings, in English or Chinese; the Orchestrator and Summary rows keep their summaries. Today's Plan tab shows only the finding behind each change.
- **Earlier plans:** a plan's agent list is saved when it is proposed, so plans proposed by an earlier version listed only the agents of that time, in their earlier wording and without findings.
  - When DayWright starts, each such list is rebuilt: Orchestrator, Learning, Life, Work, Project, and Summary review that day again, and the Orchestrator's last line says so.
  - The plans, the set one, and reported statuses stay as they were, so tasks that now overlap don't prevent it; a day that still can't be reviewed keeps its list and is reported in the service log.

### Checked

- **Evidence:** 94 backend tests pass, including nine for the review itself, two for placing a task near its usual time or falling back, one for listing Gentle first on a lighter day, one for naming overlapping tasks,
  - and three through the service: a list saved by an earlier version is rebuilt with every agent at start, keeping its plans, the set one, and with tasks that overlap; each area agent reviews only its own tasks,
  - and with 30 days of backdated reports a task often left unfinished comes back 15 minutes shorter and a task usually done at 10:30 is placed there. 30 interface helper tests pass, three of them for wording the findings, and the interface builds.
  - On a throwaway database with a week of reports and a low-energy check-in that morning, Plans listed every agent's findings, and the Plan tab of the set Balanced plan showed each placed or shortened task with the finding behind it, in English and Chinese.
  - On a fresh copy of that database the service listed Gentle first, and Talk, answered by the local Qwen3 4B model, said it was first because the Life agent advised a lighter day.
  - With an earlier version's list saved for a set plan and two work tasks overlapping, restarting the service rebuilt that list with all seven rows and their findings.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="today-tabs-and-plan-tab"></a>

## Today tabs, the Plan tab and structured reports — 2026-10-02

- **Today:** Day details, Plan, and Summary agent are three tabs beside the schedule; the Summary agent reports on today only, and the Goals card and the header's draft count are gone.
- **Status menu:** Each status lines up after its glyph, with the check at the right edge.
- **Plan tab:** Says which plan you are following, what it changed from your tasks and why, and holds View plans, Ask for a replacement plan, and Deselect plan.
- **Deselect:** Stops following the set plan and keeps the proposed plans, to set one again.
- **Reports:** A Summary report reads as outcomes by area, unfinished tasks, and area records instead of a paragraph.
- **Route:** The Orchestrator's two steps are named, so no two agents in a plan's route read the same.

### Changed

- **Why:** Today's side column mixed the next task, advice, balance, and goals in one long stack; "3 plans were proposed · view" looked like a label, not a button;
  - once a plan was set, nothing on Today said which plan it was or what it changed, and it could not be undone; the Summary report was one paragraph; and a plan's agent list named the Orchestrator twice.
- **Today:** beside the schedule are three tabs, as in Calendar. Day details holds the Next card and Balance; Summary agent holds only today's report and today's advice, with no week or month switch. The Goals card is gone from Today; Goals in Records still shows every goal's progress.
  - The header keeps Add task, plus Propose plans or Compare and set one until a plan is set, and only the Reported chip; the draft count is on the Plan tab.
- **Status menu:** each status sits after its glyph at the left, with the check on the current one at the right edge. The labels used to drift toward the middle, and the current one sat apart.
- **Plan tab:** before a plan is set, it counts the draft plans, with View plans (3). Once one is set, it reads "Following" with the plan's name and the time it was set, the plan's rationale, and "What this plan changed":
  - each task the plan placed, moved, or shortened, such as "placed at 08:00" or "45 min instead of 1 h", with the agent finding behind it. Tasks the plan kept as you set them are listed after, then the buttons.
  - How the agents made the plans is on the Plans screen only.
- **Buttons:** stacked at one width under the changes. View plans (3) opens the day's plans; Ask for a replacement plan works as before; Deselect plan, last and quiet, stops following the set plan.
  - The proposed plans stay, so you can compare them and set one again without a replacement review, and the tasks keep what was reported for them. Past days stay read-only.
- **Reports:** Read the report opens a table of done, partial, skipped, and scheduled tasks by area, a list of tasks partly done or skipped, and the area records: learning sessions, habit reports, latest energy, latest Life note, and goal count.
- **Route:** in a plan's route and in Talk, the Orchestrator's first row reads "Orchestrator · start", where it loads the day and hands each area agent its part, and its last reads "Orchestrator · finish", where it writes the plans or the reply.

### Checked

- **Evidence:** two backend tests cover deselecting: it keeps the proposals, the tasks, and their reported status and lets a plan be set again, and only today's plan can be deselected.
  - On a fresh demo database at 1412 × 938, proposing and setting a plan, the Plan tab's changes and buttons, deselecting, the Summary tab, and the route's names were checked in English and Chinese.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="fitted-screens"></a>

## Fitted screens, one status pill and Calendar tabs — 2026-10-02

- **Screens:** Every place fills the window: its heading stays put and only the part below scrolls, as one, so each place shows at most one scroll bar.
- **Window:** The Mac app opens at, and can't shrink below, 1412 × 938 points.
- **Status:** One pill now says where your records are kept and how the local model is doing.
- **Spacing:** Less room above each heading, and a task's flags sit on its title line.
- **Calendar:** Day details and the Summary agent are two tabs beside the month, Open Today is gone, and the legend is a tidy grid.
- **Wording:** "3 drafts" now reads "3 draft plans · none set yet".

### Changed

- **Why:** some places scrolled as a whole page and others did not, two title-bar pills said the same thing, and screens left wide gaps above each heading and beside each task.
  - In Calendar, the Summary agent lengthened the side column, the legend wrapped unevenly, and "3 drafts" didn't say what the drafts were.
- **Screens:** on a desktop or tablet window every place fills the window. Its heading, actions and banners stay where they are, and only the part below scrolls when it is longer than the window.
  - That part scrolls as one, columns and cards together, so a place shows at most one scroll bar, at the window's right edge. A phone keeps one scrolling page.
- **Window:** the Mac app opens at 1412 × 938 points and can't be made smaller, a size picked by resizing the app.
- **Calendar:** day cells are 96 px tall in two-column windows. Beside the month are two tabs. Day details holds the selected day's plan, schedule, tasks without a start time, suggestions, and Ask about this day; Summary agent holds its day, week, and month reports.
  - The Open Today button is gone: Open plans now shows for today as well, and leaving plans opened from Calendar returns to Calendar. The legend under the month is a three-column grid, two on a phone, each mark with its name and a short explanation.
- **Draft plans:** "3 drafts · not set yet" now reads "3 draft plans · none set yet": the plans the agents proposed for that day, waiting for you to compare them and set one.
- **Spacing:** less room above and below each place's heading, and a task's Fixed, Protected, and repeat flags follow its name on the title line.

### Checked

- **Evidence:** in a 1400 × 1041 window, every place was opened on a throwaway demo database: none scrolls as a page, each has at most one scroll area, below the heading and reaching the right edge, and no calendar label or cell is cut short.
  - Calendar's tabs switch by click and with the arrow keys, plans opened from Calendar return there, and the legend reads as three columns in English and Chinese and two on a 390 px phone, with no sideways scrolling. 27 interface helper tests pass and the interface builds.

### Delivered

- **Status:** the title bar's "Locally saved · Private" and "Local model on standby" pills are one pill, such as "Private on this Mac · Model on standby", coloured by where your records are kept; the preview and demo states read "Not saved" and "Demo data".
  - The online-lookups pill stays separate, because it opens the network log.
- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="areas-and-untimed-tasks"></a>

## Work and Project areas and untimed tasks — 2026-10-02

- **Areas:** Learn, Life, Work, and Project, each on its own row with its own agent; Money and Rest are gone.
- **Records:** Rest and Money tasks and goals move to Life, and Money's own records are deleted, the first time DayWright opens its database after this change.
- **Tasks:** A flexible task has no start time and waits in its own table under the schedule, coming up as Next once the timed tasks are past; every task lasts at least 30 minutes, and its date defaults to today.
- **Plans:** Each plan places today's untimed tasks in free time its own way, and protected tasks keep their length.
- **Colour:** A tinted background, area-coloured tasks, and an accent for the active place.

### Changed

- **Why:** Money and Rest didn't match how the day is used, a flexible task still needed a start time, the task form kept Timing apart from Start and Duration, and the interface was mostly white.
- **Areas:** Learn, Life, Work, and Project, each on its own row in Records with its own colour and glyph; Work is a square and Project a star. Work and Project each have an Overview and a Tasks tab and a bounded agent that assesses only its own tasks.
  - The Finance agent is gone.
- **Your records:** the first time DayWright opens a database after this change, Rest and Money goals, tasks, and plan entries move to Life.
  - Money's own records — opening balance, transactions, and budgets — are deleted, with Money's advice, the Finance agent's past reports, saved Summary reports (rebuilt when next asked for), and the plan checkpoints that held money figures. This runs once, in one transaction.
- **Tasks:** the form's Timing choice now holds the start time: Flexible shows only a duration, and Fixed adds a start time. Every task lasts at least 30 minutes, and the form's date defaults to today, or to the later day on show.
  - A flexible task has no start time until a plan you set places it, and Today and Calendar list such tasks in a "No start time" table under the schedule.
  - Once no timed task is left today, Today's Next card offers them one by one, showing their length instead of a time. Flexible tasks dated today or later lost the start time they had; past days keep theirs, and timed Life events became fixed.
- **Plans:** each plan keeps fixed times and places today's tasks without a start time between 08:00 and 22:00, after the moment it is proposed.
  - Balanced takes the areas in turn; Focused puts learning, project, and work first and gives one focus task 15 more minutes; Gentle starts at 09:30 or later with life tasks first and leaves 15 minutes after each task it places.
  - A protected task now keeps its length in every plan, as the task form promises, and no plan shortens a task below 30 minutes.
- **Colour:** the background carries a soft blue tint, tasks carry their area's tint with a coloured edge, the Next card and goal cards carry their area's colour, and the active place, the day's weekday, and today's calendar marker use a new accent.
  - Every text pair keeps at least 4.5:1 contrast, and colour still travels with each area's glyph and label.
- **Summary:** unchanged. Today shows today's advice; Calendar's Summary opens on the selected day, with its week and month a tap away.

### Checked

- **Evidence:** 76 backend tests pass, including new ones for placing untimed tasks, protected lengths, the 30-minute minimum, the Work and Project agents, and moving an older database; 27 interface helper tests and 5 Sites tests pass, and the interface builds.
  - Today, the task form, Plans, Records, Goals, and Calendar were checked on a throwaway demo database at desktop width, and Today at 390 px with no sideways scrolling. The desktop app was not rebuilt.

### Delivered

- **Status:** built in a separate worktree and uncommitted at delivery; committed on 2026-10-03 as `e5033fc`, `9a29c47`, `df28ad8`, and `c0f949c`, with this record in the commit after them, and merged into `main` the same day.

<a id="desktop-app-pypdf-rebuild"></a>

## Desktop app rebuilt with pypdf 6.19.0 — 2026-10-02

- **Desktop app:** Rebuilt so the Mac app's bundled service carries pypdf 6.19.0, the same release as the service requirements.

### Changed

- **Why:** the app built on 2026-09-26 froze pypdf 6.18.1 into its service, and the service requirements moved to 6.19.0 on 2026-10-01. The app keeps the packages it was built with.
- **Change:** `npm run desktop` rebuilt the app from the current source, with the service's packages installed afresh, and the new app replaced `DayWright.app` in the project folder. Since the previous build, the pypdf release is the only change that reaches the app.

### Checked

- **Evidence:** the new app's frozen service reports pypdf 6.19.0, where the previous app's reported 6.18.1. Its bundle identifier, minimum macOS version and icon match the previous app, and its signature verifies.
  - Opened from `DayWright.app`, its service listened on the loopback port within 2 seconds and the window showed Today; quitting left no DayWright, service, or model process, and the service log recorded no error. The start screen passed too quickly to capture.

### Delivered

- **Status:** the app is delivered locally, in a folder Git ignores. Uncommitted at delivery; this record was committed on 2026-10-02. The previous app, and the build output this rebuild left, were moved to the Trash once the new app passed its checks.

<a id="backend-tests-isolated"></a>

## Backend tests isolated from local data — 2026-10-01

- **Tests:** The backend tests run on a temporary database that is removed when they finish; running them used to open and migrate the local database in `backend/data/`.
- **Guard:** A test that creates or opens anything in `backend/data/` now fails instead of reaching local records.

### Changed

- **Why:** importing `backend.app.main` builds the service from `load_settings()`, whose database defaults to `backend/data/daywright.sqlite3`. The API tests import it, so every backend test run opened and migrated that database, creating `backend/data/` in a copy that had none; in a copy that holds real records, it is the user's own database.
  - Tests that build settings with `replace(load_settings(), …)` also kept that default path, although the model and speech gateways they build never read it.
- **Change:** every backend test module first imports `backend/tests/isolation.py`. It points `DAYWRIGHT_DATABASE` at a temporary folder for the run, so the service built on import, every `load_settings()` call, and the checkpoint files kept beside the database all stay there, and the folder is removed when the run ends.
  - It also refuses any test that creates or opens anything in `backend/data/`, so a new path to local data fails the suite instead of reaching it.

### Checked

- **Checks:** `backend/tests/test_isolation.py` confirms that the settings point at the temporary database, that the service built on import created its database there, and that creating or opening anything in `backend/data/` is refused while other paths are not.
  - The full backend suite passed, 64 tests, from a copy without `backend/data/`, and the folder still did not exist afterwards. With the redirect removed, three of the four isolation checks fail and the folder is still not created.

### Delivered

- **Status:** uncommitted at delivery; committed together with this record on 2026-10-01. Application behaviour is unchanged.

<a id="pypdf-6-19"></a>

## pypdf 6.19.0 — 2026-10-01

- **Dependencies:** pypdf moves to 6.19.0, which fixes three ways a crafted PDF could make it run for a long time or use a lot of memory; DayWright's PDF import uses none of the affected features.

### Changed

- **Why:** three pypdf advisories published on 2026-10-01 (GHSA-v247-6f48-mgcj, GHSA-php9-fj8v-98fj and GHSA-w23x-9jrw-r45c) describe crafted PDFs that make pypdf before 6.19.0 run for a long time or use a lot of memory:
  - when embedded files are read through its dictionary API, when appearance streams are generated while form fields are flattened, or when alphabetical page labels are read.
- **Change:** `backend/requirements.txt` pins `pypdf==6.19.0`, and the desktop build's requirements include that file.
  - DayWright's PDF import opens a file strictly, rejects encrypted PDFs, accepts at most 20 pages and 2 MB, and only extracts text, so none of the affected features was reachable; the update keeps the dependency on its patched release.

### Checked

- **Evidence:** the 60 backend tests pass with pypdf 6.19.0, the PDF import tests included.

### Delivered

- **Status:** committed together with this record. The installed Mac app still bundles pypdf 6.18.1 until its next `npm run desktop` build; none of the affected features is reachable from it either.

<a id="desktop-app-icon-rebuilt"></a>

## Desktop app icon — 2026-09-26

- **Desktop app:** The Mac app's icons are rebuilt from the aligned master, so the app shows the same icon as the project folder and the start screen.

### Changed

- **Why:** the Mac app was built on 2026-09-23 from the earlier artwork, which filled its whole canvas, so macOS drew it smaller inside a light-grey frame. The aligned master recorded next fixes the shape, but an app keeps the icon it was built with.
- **Change:** the five icon files in `src-tauri/icons/` are regenerated from `Resources/DayWrightIcon.png`, and the app was rebuilt with `npm run desktop`, so its app icon, title bar, and start screen all use the aligned artwork.

### Checked

- **Evidence:** the rebuilt app's `icon.icns` matches the regenerated one, and its signature verifies. Drawn the way Finder and the Dock draw it, the new app's icon sits in the macOS rounded square with no frame; the previous build showed the grey frame.
  - Opened from `DayWright.app` in the project folder, the window reached its service in 3 seconds and showed Today with the new title-bar icon, and quitting left no DayWright process.

### Delivered

- **Status:** uncommitted at delivery; committed on 2026-09-26 as `22c2743` and merged into `main` on 2026-09-27. The previous app, and the build output this rebuild left, were moved to the Trash once the new app passed its checks.

<a id="aligned-app-icon"></a>

## Aligned app icon — 2026-09-26

- **Icon:** Redrew the app icon in the macOS icon shape at the standard size; the favicon and the project folder's icon come from the same master.

### Changed

- **Why:** on current macOS an app icon whose outline does not match the system's rounded square is drawn smaller inside a light-grey frame. The document stack filled its whole canvas, so an app built from it looked like a different icon from the project folder.
- **Icon:** `Resources/DayWrightIcon.png` keeps the same artwork on its cream paper colour, clipped to the rounded square macOS draws for app icons, 824 of 1024 pixels. The 256-pixel favicon at `public/icon.png` was regenerated from it, and the project folder's Finder icon was set from the same master.
- **Desktop app:** an app bundle built before this change keeps the previous artwork until it is rebuilt from the new master.

### Checked

- **Checks:** `npm run build` rebuilt `dist/` with the new favicon, after `npm ci` installed the locked font packages this checkout was missing, and `npm run test:sites` passed all five cases. No interface, backend, or data behaviour changed.

<a id="desktop-app-release"></a>

## Desktop app — 2026-09-23

- **Desktop app:** DayWright opens as a Mac app that starts its own local service and stops it on quit, with no terminal commands.
- **Privacy:** The app's service answers only its own window, which gets a new secret at every launch.
- **Records:** The app keeps its records in the Mac's Application Support folder and starts with an empty account.
- **Recovery:** A model server left running by a crash is stopped at the next launch.

### Changed

- **Why:** DayWright ran only as two terminal commands and a browser tab.
- **What opens:** `DayWright.app` shows a start screen, in English and Chinese, while its local service starts, then Today. The Mac window buttons sit in DayWright's own 60 px title bar, as the Open Bench design shows, and its empty space moves the window.
  - Links to web pages open in the default browser; the window shows only its start screen and its own service.
- **Service:** the app carries a self-contained copy of the local service, so it needs no Python or project folder. The service serves the interface and API from one address on this Mac, port 8425 when it is free, so the chosen language is kept between launches.
  - Each launch creates a new secret that the window exchanges for a private cookie; any other program or web page is refused.
- **Stopping:** Quit stops the service and the models it started. If the app is force-quit, the service notices and stops within a second.
  - If the service itself crashes while a model runs, the next launch stops that model server; only processes the service recorded, and whose parent has gone, are stopped.
- **Records and log:** the app keeps its database in `~/Library/Application Support/DayWright/`, apart from the development database, and starts with an empty account. The service's errors go to `~/Library/Logs/DayWright/service.log`, which each launch begins afresh.
- **Build:** `npm run desktop` builds the interface, freezes the service with PyInstaller in its own environment under `build/`, and bundles the app with Tauri 2. It needs macOS 15 or later, because one of the service's bundled libraries does.
  - Xcode 27's `strip` leaves Rust's build-time macro libraries unloadable with a macOS 13 or later target, so the build leaves those unstripped.

### Checked

- **Evidence:** 60 backend tests pass, including 10 new ones for the session check, the port choice, and recording and stopping model servers; 27 interface helper tests and 5 Sites tests pass; Clippy reports nothing.
  - The built app was opened both from Finder's `open` and directly: the start screen and then Today appeared, with the window buttons centred in the title bar.
  - Quitting left no DayWright or model process; force-quitting the app stopped its service within half a second; and a real chat model server left by a killed service was stopped at the next start.
  - Dragging the window, a link opening in the browser, the microphone prompt, and the language kept across launches were not exercised, because this Mac did not allow synthetic input.

### Delivered

- **Status:** built on the `daywright-desktop-app` branch and uncommitted at delivery; committed on 2026-09-23 as `c8969a1`, `231cb61`, `38c14fe`, `07d1c24`, and `af02389`, and merged into `main` on 2026-09-27. The checked app is at `DayWright.app` in the project folder.

<a id="open-bench-icons-tracked"></a>

## Open Bench icons in Git — 2026-09-23

- **Icons:** The Open Bench icons are now kept in Git; a fresh copy of DayWright used to build without error but show no icons.

### Changed

- **Why:** the interface draws every icon from `design/icons/`, but a repository-wide ignore rule meant for Finder's hidden folder-icon file also matched that folder on a case-insensitive Mac. The 49 icons were therefore never kept in Git, and a fresh copy built without error but showed no icons.
- **Change:** `.gitignore` in this folder re-includes `design/icons/`, and the 49 icons from the Open Bench handoff are tracked unchanged. Finder's folder-icon file stays ignored.

### Delivered

- **Status:** uncommitted at delivery; committed on 2026-09-23 as `cf98a10` and merged into `main` on 2026-09-27.

<a id="open-bench-interface"></a>

## Open Bench interface — 2026-09-23

- **Interface:** Every place now follows the Open Bench design — Today with Plans, Calendar, Records, Library, and Talk docked beside the page — in English and Simplified Chinese, from 320 px phones up.
- **Online lookups:** Nothing goes online without the user's say-so for that lookup, and every request is logged with exactly what was sent.
- **Agent suggestions:** Future tasks an agent prepares now wait for Add or Dismiss instead of being placed directly.
- **Plans:** Setting a plan keeps the statuses already reported for the tasks it schedules.

### Changed

- **Why:** most screens still used the earlier folio interface. The [Open Bench handoff](design/HANDOFF.md) replaces it everywhere, with its own tokens and icons.
- **Navigation:** the eight-tab rail gives way to four places — Today, Calendar, Records, and Library — and Talk, beside the app icon in the title bar. A phone gets one header and one bottom bar, with Talk in the centre and nothing floating over the page.
- **Today and Plans:** the schedule has a now line, the next action, advice, balance, and goals; a task's details and edits open in a side sheet. Plans are compared side by side, or one at a time on a phone, and set after a confirmation.
  - Replacing a set plan is reviewed entry by entry.
- **Calendar:** month cells show set plans with their completion, recorded days, presets, and suggestions. Past days are read-only with a lock, and the selected day shows its summary, schedule, and Summary reports.
- **Records:** Goals, Tasks across dates, and the Learn, Life & Rest, and Money areas, each with its own tabs. Forms open in sheets beside the page.
- **Library:** a source list with a name filter, Files and Notes counts, the text indexed for each source, and two-step removal; the real import limits; a lookup that stays local unless allowed; a "What stays, what goes" account;
  - and a network log, reachable from a title-bar pill that counts today's online lookups.
- **Talk:** a panel docked beside the page, or a sheet on a phone, that carries the place and day on show. Ask, Adjust, and Report each say what they do.
  - A reply can show its agent route and Library sources, and says when DayWright's own rules answered instead of the model. A proposal is pencilled, lists exactly what would change, and applies only on Confirm. Hold to talk records while held; Escape or sliding away cancels.
- **States:** preview and demo banners on every screen; a card on Today when the local model can't run, listing which local parts are missing; notices in both languages; and the design's focus ring on every control.
- **Behaviour changes:** - A topic with no local match used to be fetched from Wikipedia automatically. DayWright now asks every time, showing the exact words and destination, and records each request in a local network log. - Agent-prepared future tasks used to be placed directly.
  - They now stay pencilled until added, and plans, counts, reports, and goals leave them out until then. - Setting a plan now keeps the statuses already reported for the tasks it schedules. - Push-to-talk now sends the transcript on release, marked as voice, instead of placing it in the composer.
- **Removed:** the earlier stylesheet and the icon package it relied on; the interface draws only the design's own icons.

### Checked

- **Evidence:** 50 backend tests pass, including the new consent and network-log checks, and 27 interface helper tests pass.
  - Each place was checked in the browser against the design on the demo workspace at desktop and phone widths, and at 320 px no place scrolls sideways; the Library and Talk were also checked in Chinese.
  - Online lookups, Talk replies, and the model card were exercised with stand-in responses in the browser, so nothing was sent online and no model was started.

### Delivered

- **Status:** built on the `daywright-open-bench` branch and merged into `main` on 2026-09-23.

<a id="daywright-project-icon"></a>

## Project identity icon — 2026-09-22

- **Identity:** Added the selected DayWright project icon, built around one approved daily plan and the four life-area tabs; its full-size master lives in `Resources/`.
- **Browser:** The local interface uses a 256-pixel copy as its favicon.
- **Finder:** The project folder mirrors the full-size master without changing application behavior.

### Changed

- Added the selected 1,024-pixel DayWright artwork at `Resources/DayWrightIcon.png`. Its daily ledger, approval mark, and orange, blue, green, and graphite tabs represent the user-approved plan and the four bounded life areas.
- `index.html` loads a 256-pixel copy at `public/icon.png` as the local interface favicon, so the page does not download the 2.1 MB master. The Finder folder uses the master's pixels through ignored macOS custom-icon metadata.
- This is an identity and presentation change only. Planning, storage, model use, privacy, and deployment status are unchanged.

<a id="explicit-removal"></a>

## Explicit removal — 2026-09-22

- **Removal:** A goal, an owned dated record, or an indexed source can now be removed explicitly.
- **Kept:** Past records and anything a confirmed plan scheduled refuse removal with a stated reason.
- **Interface:** The day ledger and goal ledger carry a two-step remove control in both languages.

### Changed

- **Why:** the service offered 39 operations and none of them removed anything. Nine could edit a record, so a goal set by mistake, or a task recorded while first trying the app, could be renamed but never taken out. Records only ever accumulated.
- **What can be removed:** a goal that no dated record links to; an owned record for today or later that no confirmed plan scheduled; an indexed knowledge source, with its chunks and their vectors.
- **What stays:** a past record, and any record a confirmed plan scheduled. Both refuse with a stated reason rather than silently declining, keeping the promise that confirmed days and past outcomes are read-only history.
- **Ordering:** a goal reports how many dated records still link to it, so records are removed one at a time and no dated work disappears as a side effect of removing a goal.
- **Dependent rows:** an unconfirmed plan proposal keeps its own copy of an entry and loses only the link; a record derived from another loses its origin link; a categorized Life event is removed with the record it describes.
- **Interface:** the day ledger and the goal ledger carry a remove control beside their edit control, in one right-aligned group, and it asks for confirmation in a second click, in English and Simplified Chinese. A narrow layout moves the whole group onto its own row.
  - The Library shows a source count rather than a source list, so removing an indexed source is available through the local API but not yet from a screen.

### Checked

- **Evidence:** 46 backend tests pass, including three new ones for removal and its two refusals.
  - Against the demo workspace the interface removed a task and refreshed, a goal with two linked records returned a 409 naming the count, and a record scheduled by a confirmed plan returned a 409 naming the reason.

### Delivered

- **Status:** source change with local checks. No packaging or publication is claimed by this record, and no stored record of the owner's was altered while checking.

<a id="one-sqlite-engine-for-the-database"></a>

## One SQLite engine for the database — 2026-09-21

- **Storage engine:** One SQLite library now owns the database file: the vector store moved onto the built-in module and `apsw` left the service requirements.
- **Atomicity:** Replacing an indexed source is one transaction, so a rejected vector can no longer leave a partly replaced note behind.

### Changed

- **What was wrong:** `database.py` opened the management database with Python's built-in `sqlite3` (SQLite 3.50.4) while `retrieval.py` opened the same file with `apsw` (SQLite 3.51.0).
  - Two engines in one process keep separate lock state, and a POSIX advisory lock belongs to the process, so one engine closing a connection could release a lock the other still relied on. Across the API's request threads that risks a busy failure or a damaged file.
- **Why it existed:** `apsw` was the straightforward way to load the `sqlite-vec` extension. The interpreter this project runs on supports extension loading in the built-in module, so that reason no longer holds.
- **Change:** the vector store connects with `sqlite3` in autocommit mode and loads the same `sqlite-vec` binary as before. `apsw` is removed from the service requirements. The stored index is untouched, because the extension that reads it is unchanged.
- **Atomicity:** `apsw` treats `with connection:` as a transaction while the built-in module does not, so replacing a source now runs inside an explicit transaction. Without it, a rejected vector left the previous note deleted and its replacement half written.

### Checked

- **Evidence:** all 43 backend tests pass, including two new retrieval tests. The atomicity test was first run against the unguarded version, where it failed and reproduced the partial replacement, before the guard was in place.

### Delivered

- **Status:** source and dependency change with local checks. The database file's format and contents are untouched, and no packaging or publication is claimed by this record.

<a id="dependency-advisories-cleared"></a>

## Dependency advisories cleared — 2026-09-21

- **Security:** Cleared the nine dependency advisories GitHub reported against the interface build — six high, three moderate.
- **Versions:** Vite moves to 6.4.3; PostCSS, nanoid, browserslist and its data companions resolve to their patched releases.
- **Backend:** Every pinned Python requirement was checked and carries no advisory, so the service dependencies are unchanged.

### Changed

- **What was reported:** nine open advisories against the interface dependencies — six high, three moderate — in `browserslist` (GHSA-c83g-rgw3-j3cx, GHSA-73wf-gq98-2v4g), `nanoid` (GHSA-2v37-7h3g-55p8, GHSA-28wg-ghj8-5hjv), `postcss` (GHSA-r28c-9q8g-f849, GHSA-fxqj-rqcc-2cmp), `vite` (GHSA-fx2h-pf6j-xcff, GHSA-v6wh-96g9-6wx3) and `baseline-browser-mapping` (GHSA-w5vr-8v7q-w6rv). All nine sit in the lockfile, none in the service requirements.
- **Fix:** `vite` advances to 6.4.3 in the manifest, keeping the project's exact-pin style. The other four are transitive and their declared ranges already permitted the patched releases, so they resolved to `postcss` 8.5.28, `nanoid` 3.3.19, `browserslist` 4.29.0 and `baseline-browser-mapping` 2.11.25.
- **Scope of the lockfile change:** nine locked versions, including the four browserslist data companions (`caniuse-lite`, `electron-to-chromium`, `node-releases`, `update-browserslist-db`) that travel with it. No package was added or removed, and no major version changed.
- **Backend:** all ten pinned Python requirements were checked at their exact versions and report no advisory, so `backend/requirements.txt` is unchanged.

### Checked

- **Evidence:** `npm test` rebuilt the production bundle on Vite 6.4.3, transforming 1,583 modules, and passed all 5 Sites/package tests and all 41 API/planner tests.

### Delivered

- **Status:** dependency and lockfile change with local checks. A published advisory list refreshes on its own schedule, so the reported count clears after the next scan rather than on this commit.

<a id="renamed-to-daywright"></a>

## Renamed to DayWright — 2026-09-20

- **Name:** The project was renamed to DayWright across the interface, documents, and service identity.
- **Local interfaces:** The package name, environment variables, upload header, and Wikipedia user agent carry the new name.
- **Storage:** The database, demo, and checkpoint files use the `daywright` stem, and the existing local databases were renamed from verified copies.
- **Preserved:** Product behavior, privacy boundaries, architecture, and stored records are unchanged.

### Changed

- **Name:** The project was renamed to DayWright in every document, interface string, and identifier. A wright is a maker, and the unit this product makes is the day; the specification's naming rationale was rewritten to say so, and the folio mark now reads `D/`.
- **Interface:** the page title and description, workbench section headers, assistant labels, and both the English and Simplified Chinese string tables carry the new name.
- **Local interfaces:** the package is `daywright`; `DAYWRIGHT_DATABASE`, `DAYWRIGHT_MODEL_LIBRARY`, `DAYWRIGHT_LLAMA_SERVER`, `DAYWRIGHT_DEMO`, and `DAYWRIGHT_API_TARGET` replace the previous environment names; the local upload header is `X-DayWright-Filename`; and the Wikipedia user agent is `DayWrightLocalBot`.
- **Storage:** the default database is `backend/data/daywright.sqlite3`, and the demo and checkpoint files follow the same stem. The existing local databases were renamed from byte-identical verified copies, so recorded days, goals, plans, knowledge chunks, and the demo workspace are preserved.
- **Saved preference:** the stored interface language key is now `daywright-language`. An earlier saved choice is not carried across, so the interface language is selected once after the rename.

### Checked

- **Evidence:** `npm test` rebuilt the production bundle and passed all 5 Sites/package tests and all 41 API/planner tests. The repository history check reported every change history inside its inline window, and the activity index was regenerated.

### Delivered

- **Status:** delivered as uncommitted source, then committed canonically and published. The public repository carries the new name, and its tip's tree matches this folder exactly.

<a id="local-boundary-and-runtime-privacy"></a>

## Local boundary and runtime privacy — 2026-09-19

- **Local boundary:** The development UI now binds only to loopback, matching the API and model processes.
- **Explicit mutation:** Summary generation uses POST because it saves reports, suggestion state, and eligible future commitments.
- **Runtime privacy:** Chat and embedding tokens stay out of process arguments, while model request logging is disabled.
- **Runtime structure:** One shared supervisor now owns both local-model lifecycles, waits for health under concurrent first use, and handles launch failure without an API crash.
- **Reliability:** Added focused regressions, removed unused bundled sample data and test deprecation warnings, completed missing theme variables, and reconciled the product status documentation.

### Changed

- **Network boundary:** Vite now listens on `127.0.0.1`, so the browser workbench no longer exposes its proxied local API to other devices on the network. A packaging test locks that host setting.
- **Summary contract:** `/api/summaries` is now POST-only because generating a report persists reports, synchronizes the suggestion pool, and can prepare an eligible future commitment. The client and API regressions exercise the explicit write method and reject GET.
- **Model privacy:** chat and embedding runtimes receive their random API token through `LLAMA_API_KEY`, keep it out of the process list, disable `llama-server` logging, and discard standard output and error rather than retaining prompts or private source text in runtime logs.
  - The obsolete ignored runtime logs were removed after confirming no process still held them.
- **Runtime structure:** both gateways now delegate process ownership to one `LlamaRuntime` supervisor. A concurrent first request waits for the same health-verified process instead of treating a merely spawned child as ready, while an executable launch failure returns the normal unavailable/rule-based path.
  - The unused frontend-only sample-plan module was removed; the isolated SQLite demo remains the single source of sample product data.
- **Reliability and consistency:** focused tests cover both model launch contracts; demo tests use the database's ISO-date contract without deprecation warnings; the two theme variables already referenced by the interface are defined; current README and product-specification status now match the verified local voice implementation.

### Checked

- **Evidence:** `npm test` rebuilt the production bundle and passed all 5 Sites/package tests and all 41 API/planner tests. The actual installed Qwen chat runtime reached health and returned a local-model response; the actual embedding runtime returned a non-zero 1,024-dimensional vector, and both stopped without recreating their old log files.
  - Repository link and history checks also passed; the repository-wide README layout check reported only pre-existing OpenClaw departures outside this project.

### Delivered

- **Status:** the audited local batch is canonically integrated; no public-mirror update or hosted deployment is claimed.

<a id="goal-paths-and-bilingual-planning"></a>

## Goal paths and bilingual planning — 2026-09-18

- **Planning demo:** Preset goals and tasks now lead directly into generating and comparing plan alternatives instead of opening on an already confirmed plan.
- **Daily command center:** Today now manages the next action, plan state, workload, area balance, agent advice, and goal progress instead of presenting three isolated counters.
- **Unified area work:** Learn, Life, and Money now keep goal-linked and independent tasks in one list, with goal tags and progress visible on linked work.
- **Languages:** English and Simplified Chinese can be selected for the interface and local Orchestrator response.
- **Management navigation:** Management screens and the three life areas are grouped; Library is nested under Learn, and the assistant has one persistent entry.

### Changed

- **Demo flow:** the isolated demo keeps its predefined goals, dated tasks, domain records, Library source, and past plans, but resets today's generated plan on startup. Plans therefore opens at the multi-agent generation step with real sample inputs already present.
- **Daily command center:** Today prioritizes the next action and places plan state, completion, scheduled time, protected work, area allocation, linked-goal progress, and the Summary Agent's day/week/month evidence in one actionable management surface.
  - The former Agent Brief duplicate is removed; next-plan guidance and saved-advice controls now live only inside the command center. Advice names the supporting task or area record and recommends a concrete time, duration, or financial decision instead of repeating a generic category phrase.
  - Source records never appear as an active Today schedule before confirmation; after confirmation, Today switches to the chosen schedule with explicit start–end times and progress reporting.
- **Bidirectional goal work:** every goal response includes its linked dated tasks. Learn, Life, and Money keep all dated work in one task board; goal-linked tasks carry a visible goal tag and the goal's progress, while independent tasks remain in the same list with a neutral label.
  - Goals presents the same linked work and progress from the goal direction.
- **Bilingual operation:** a persistent English/Chinese selector changes every management screen, form, summary, calendar label, multi-agent control, and predefined demo record. User-authored content and prior conversation text stay unchanged.
  - New conversation requests carry the selected language, and the local Orchestrator is instructed to answer in English or Simplified Chinese without changing its data permissions or confirmation rules.
- **Management navigation:** the rail separates Today, Calendar, Plans, and Goals from the Learn, Life, and Money areas. Library is visually nested beneath Learn instead of appearing as a fourth life area, group headings are readable dividers, and transformed tabs no longer create a bottom scrollbar.
  - The wider rail preserves full tab names and keeps its closing message inside the visible column. Calendar owns navigation and past read-only review without repeating today's task board or Summary Agent report.
  - Summary advice is consolidated on Today, where the next-plan guidance includes active saved advice when the selected period has no new recommendation. The persistent Talk to DayWright control is the sole assistant entry card.

### Delivered

- **Status:** committed canonically as `a3e1da0`, `2e097ba`, and `fd04233`; the filtered public mirror was published through `6fb66ba`. No hosted deployment is claimed.

<a id="readme-alignment"></a>

## Documentation — 2026-09-18

- **Structure:** Aligned the README's sections, markers and change history with the repository's other project READMEs.
- **License:** Added the approved Soucieux proprietary-software notice.

### Changed

- **Recorded date:** 2026-09-18.
- Aligned this README with the repository's other project READMEs: an Overview section, section markers for the sections an overview reader shows, a Contributing section pointing to the contribution guide, the standard change-history declaration and status note, labelled highlight cells, and newest-first records that each link back to the table.
- Added the approved Soucieux proprietary-software notice, reserving rights in original project materials while retaining third-party license terms.
- Documentation only; application behavior, dependencies, builds, deployment, and publication status are unchanged.

<a id="local-voice-transcription"></a>

## Local voice transcription — 2026-09-16

- **Change:** Installed offline push-to-talk transcription, simplified the management surface, rebuilt Summary around scannable evidence and actions, added an isolated populated demo workspace, and verified local Qwen conversation end to end.

### Changed

- **Simpler management surface:** Today removes the duplicate schedule summary, shortens its hero, keeps the management state in three direct controls, and promotes one explicit local-AI action. Summary now presents recorded days, completion, suggestions, per-area outcomes, and at most two next steps; detailed preference memory is disclosed only on request.
- **Isolated demo:** `npm run api:demo` uses a separate SQLite file and idempotently creates three goals, three current-day records, a confirmed plan with three alternatives, four past confirmed plan snapshots, a Learning subject/session, a Life check-in/habit, a Money transaction/budget, and an indexed Library note.
  - A banner identifies the workspace so examples cannot be mistaken for personal data.
- **Today versus Calendar:** Today is the execution surface for the current plan, records, progress, and local AI. Calendar owns history, read-only past-plan inspection, and period summaries. A dedicated recent-plan strip exposes past confirmed dates and their outcomes before the month grid.
- **Local conversation evidence:** A real demo request through `/api/chat` was synthesized by the Qwen3 4B GGUF model and answered from the saved learning item with `model_mode=local-model`.
- **Runtime:** Installed pinned `faster-whisper` 1.2.1 and its CPU dependencies in DayWright's Python 3.12 environment, without requiring acceptance of the machine's outstanding Xcode license.
- **Model:** Added the publisher's multilingual converted Whisper-small files under the shared `AI-Models/whisper/faster-whisper-small/` directory. The original Core ML package remains intact. The 483,546,902-byte weights file matched the publisher's pinned SHA-256 `3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671`.
- **Privacy and UX:** Push-to-talk remains user-initiated; WAV recordings use a temporary directory and are removed after recognition. The drawer always states unavailable, ready, recording, transcribing, or editable-review status. Recognition runs outside the API event loop.

### Checked

- **Evidence:** Focused readiness/API tests passed. A 2.24-second synthetic mono 16-bit 16 kHz WAV sent through the real `/api/voice/transcribe` route returned the exact editable sentence “Plan a shorter learning session tomorrow.” with HTTP 200. The refreshed UI visibly reported “Voice ready” against the updated service.
  - The demo-seeding regression and production build also passed, and the populated Today/Summary view was visually checked. No user microphone recording was made.

<a id="calendar-and-plan-desk"></a>

## Calendar and plan desk — 2026-09-15

- **Change:** Expanded management views with owned goals/items, record-based alternatives, conversation entry, read-only history, period reports, explicit preference evidence, and original-design trace.

### Changed

- **Management view:** Today focuses on summary, active-plan state, goals, owned items, area links, and Calendar/Plans actions. Plans combines alternatives, rationale, schedule, and decision.
- **Calendar:** Month navigation includes past months; recorded days reveal the current plan, operational month totals, progress, domain allocation, and scheduled items. Browsing an unrecorded day is read-only and does not seed a fictional historical plan.
- **Plan choice:** Balanced, Focused, and Gentle are explicitly labelled as alternatives for one date. A preview cannot change the current plan. Replacing a confirmed variant requires a named review and approval; direct unapproved replacements return a conflict.
  - Completion reports remain attached to their original alternative and may differ after a replacement.
- **Shared state:** Reporting is accepted only on entries belonging to the confirmed variant; Calendar’s completion count and the Learn, Life/Rest, and Money ledgers use that same variant. Library sources and unscheduled Notes are intentionally separate from calendar events.
- **Personal intake and memory:** Fresh accounts show no sample plan. Users set goals and timed today/future items before Orchestrator proposals. Recurrence, fixed/important commitments, exact-title shortening feedback, and period reports persist locally.
  - Summary can directly add an agent-origin future item with evidence; it remains distinct from a confirmed plan and can be explained or edited. Past plans stay read-only. The Talk entry is visible on every screen.
- **Beneficial recurring evidence:** Summary now retains per-task done-day counts for protected recurrence. Two completed days in a reviewed week can place the next user-editable future record with outcome provenance at its original duration.
  - If the user repeatedly asks to shorten the same task, the shorter block wins, while the task remains included.
- **Architecture fidelity:** The revised specification maps the original agent, state, suggestion, knowledge, UI, local-model, and voice contracts to current source and remaining work. The day-proposal and conditional KnowledgeState graphs checkpoint outside the vector database; complete conversation graph coverage, full domain context, and native packaging remain pending.
  - Local push-to-talk transcription is now model-backed and checked through the real API.
- **Design authority:** The full original product design text is retained inside `docs/` beside the revised specification and its explicit implementation-versus-remaining fidelity ledger.
- **Local knowledge import:** User-selected Markdown, text-based PDF, and Word `.docx` are parsed with size/page/text limits and indexed as local documents without retaining the original bytes. Different content with the same filename retains distinct indexed sources rather than overwriting the earlier import.
  - Unsupported formats and scanned PDFs report an error; folder import and OCR remain future work.
- **Suggestion management:** Summary advice now persists as soft/strong entries keyed by day, week, and month. Today offers an area-filtered review; discarding a content-matched idea affects all periods, and a later repeat creates a notice rather than an active idea.
  - Active guidance reaches bounded domain agents and can prioritize a gentler record-based variation. An exact week/area reset hard-deletes its content behind a typed confirmation and retains only a noncontent clearing marker, preventing regenerated advice from silently reappearing.
- **Public import choice:** KnowledgeState now runs local lookup, bounded encyclopedia fetch, a credibility/timeliness/format receipt, and three organization-scheme choices. It retains the fetched text locally as pending and performs chunking/embedding/indexing only when one choice is confirmed; a second choice conflicts.
  - Labels name the organizational intention, while verified per-passage classification and multi-source comparison remain pending.
- **Talk replacement guard:** A conversation proposal names the confirmed and proposed day plans. Approval is accepted only if the reviewed current plan is still current; an unreviewed or stale chat action cannot switch the confirmed date.
- **Domain management:** Learning subjects and sessions; Life daily state, habits, and categorized events; and manual Money balance, transactions, and category budgets now have separate local records and state sheets. Timed events write a linked Calendar item atomically; sessions and transactions remain unscheduled.
  - Summary and bounded domain-agent assessments read these actual records. A recorded low-energy state can guide a gentler Life block, and over-budget advice names the saved category figures without claiming a bank connection.
- **New checks:** Fresh-account, linked-state, future-provenance, local-first knowledge, and voice endpoint tests are added. The isolated browser check demonstrated three alternatives from two user-owned items, one confirmed plan, updated Today/Calendar, completion, and an editable future record.
  - A real public French-language introduction was first staged with zero new vectors, then one chosen import indexed and retrieved two attributed chunks in a clean, isolated database; separate checkpoint persistence and both SQLite files' integrity were checked. The choice sheet was also checked at desktop and 390-pixel width.

### Checked

- **Checks:** The documented `npm test` command passed 30 API checks, four static packaging tests, and the production build. Browser interaction and visual checks covered an empty account, Today, Calendar, Plans, synchronized areas, reviewed replacement, Library, and 390-/320-pixel responsive states.
  - After the domain-management slice, three new domain API scenarios and two affected plan/ Summary regressions passed as focused checks; the production build passed again. The current isolated browser pass verified Learning-session saving, Life/Money area navigation, and the 390-pixel Life layout, but did not visually submit Life/Money forms.
  - The compatible speech CLI was unavailable during that earlier pass. No commit, native installation, or hosted publication is claimed.

<a id="initial-vertical-slice"></a>

## Initial multi-agent vertical slice — 2026-09-14

- **Change:** Created the DayWright specification and folio interface; implemented the local day workbench, SQLite/`sqlite-vec` state, deterministic plans, explicit confirmation, separate Qwen chat and embedding runtimes, local RAG, and a visible permission-bounded multi-agent core.

### Changed

- **Product:** Reframed the platform as a workbench-first, conversation-enabled system where structured state is authoritative and consequential AI suggestions require confirmation.
- **Experience:** Implemented the approved editorial folio with indexed tabs, daily schedule, alternative-plan review, hard constraints, explicit commitment, suggestion handling, progress reporting, domain summaries, and a contextual conversation drawer.
- **Planning:** Added deterministic Balanced, Focused, and Gentle plans and checks for domain coverage and schedule collisions.
- **Persistence:** Added SQLite tables for plan sets, versioned variants, plan entries, one daily confirmation, conversation history, proposed actions, action decisions, preference provenance, suggestions, integer-minor-unit finance entries, knowledge sources/chunks, and retrieval evidence; `sqlite-vec` stores the associated 1,024-dimensional vectors in the same database.
- **Local AI:** Connected the existing Qwen3 4B GGUF through the installed `llama-server` using a dynamic loopback port, per-launch token, bounded context, offline mode, and supervised shutdown. Connected the existing Qwen3 Embedding 0.6B GGUF through a separate embedding-only runtime. The existing Whisper package is recorded but not yet active.
- **RAG:** Added local note capture, 180-word overlapping chunks, vector indexing, instruction-aware question embeddings, nearest-chunk retrieval, prompt grounding, persisted retrieval provenance, a relevance-distance gate, and visible private-source labels. Retrieved text is treated as untrusted reference material; source snapshots keep historical answers explainable after a note is revised.
- **Multi-agent:** Added Orchestrator, Learning, Life, Finance, and Summary roles with bounded state access, deterministic domain assessments, persisted execution traces, visible conversation routing, and Orchestrator-only plan proposals. Qwen provides the Orchestrator’s language synthesis through one shared local runtime.
- **Boundaries:** Kept the first delivery browser-hosted and local. Native packaging, voice, file-format import, external research, and finance connectors remain future work and are not represented as delivered.

### Checked

- **Checks:** Passed the production interface build, static packaging contract, eleven planner/API tests, primary browser interactions, real local-model multi-agent routing, persisted-route retrieval, separate real embedding-model output validation, 390-pixel responsive inspection, and final design comparison.
