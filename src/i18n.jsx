import { createContext, useContext, useEffect, useMemo, useState } from "react";

const messages = {
  en: {
    navToday: "Today", navCalendar: "Calendar", navRecords: "Records", navLibrary: "Library", navTalk: "Talk",
    mainNavigation: "Main", languageLabel: "Language", areasHeading: "Areas", lifeAndRest: "Life & Rest",
    saveLocal: "Locally saved · Private", saveLocalShort: "Saved · Private",
    savePreview: "Preview mode · Not saved", savePreviewShort: "Preview · Not saved",
    saveDemo: "Demo workspace · Sample data", saveDemoShort: "Demo · Sample data",
    modelReady: "Local model ready", modelReadyShort: "Model ready",
    modelStandby: "Local model on standby", modelStandbyShort: "Model on standby",
    modelUnavailable: "Local model unavailable", modelUnavailableShort: "Model unavailable",
    newTaskTitle: "New task", editTaskTitle: "Edit task", taskDetailTitle: "Task", taskForDate: "For", openDetails: "Open details", closeAction: "Close",
    fieldTitle: "Title", fieldDetail: "Detail", fieldArea: "Area", fieldStart: "Start", fieldDuration: "Duration (minutes)", fieldTiming: "Timing",
    fieldRepeats: "Repeats", fieldGoal: "Goal", optionalLabel: "(optional)", repeatNone: "None", noGoalOption: "No goal",
    timingFlexible: "Flexible", timingFlexibleHelp: "Plans may move it within the day.", timingFixedHelp: "It stays at this time; plans work around it.",
    protectedLine: "Plans won't shorten, move or drop it.", saveTask: "Save task", savingLabel: "Saving…",
    previewCannotSave: "Nothing can be saved while the local service isn't running.", agentOrigin: "Added by an agent",
    editAction: "Edit", removeEllipsis: "Remove…", stepTwoOfTwo: "Step 2 of 2", removeTaskQuestion: "Remove", removeTaskAction: "Remove task",
    removeTaskConsequence: "It's removed from this day and from any draft plans. Past days and confirmed plans stay as they were.",
    cantRemoveTask: "Can't remove this task", nothingWasRemoved: "Nothing was removed.", reportSkipped: "Report Skipped", okAction: "OK",
    scheduleTitle: "Schedule", entriesCount: "entries", tasksCount: "tasks", plannedSuffix: "planned", nowLabel: "Now", nextLabel: "Next", inPrefix: "in",
    planSetChip: "Plan set", draftsNotSet: "drafts · not set yet", reportedChip: "Reported", plansProposedView: "plans were proposed · view",
    nothingRecordedToday: "Nothing recorded for today", addTaskAction: "Add task", askReplacement: "Ask for a replacement plan",
    compareAndSet: "Compare and set one", proposePlansAction: "Propose plans", proposeNeedsTask: "Needs at least one task.",
    previewBanner: "Preview mode: the local service isn't running, so nothing you do here is saved.", aboutTheDay: "About the day",
    notReportedYet: "Not reported yet — time passing doesn't mark it done", notInSetPlan: "Not in today's set plan", setPlanKeepsTask: "Today's set plan includes it, and a set plan stays as it was set.", titleNeeded: "Give the task a title.", flagFixed: "Fixed", flagProtected: "Protected", flagDaily: "Daily", flagWeekly: "Weekly",
    statusFor: "Status for", changeStatus: "Change status", reportWhatHappened: "Report what actually happened",
    adviceLabel: "Advice", adviceEvidence: "From today's report", adviceStaysActive: "It stays active until you dismiss it.", dismissAction: "Dismiss",
    noAdviceYet: "Nothing to advise on yet. Advice appears once you have tasks or a plan — and always shows what it's based on.",
    strong: "Strong", soft: "Soft", balanceTitle: "Balance", plannedReported: "planned · reported",
    balanceFootnote: "Planned time by area. The filled part is what you've reported.", balanceEmpty: "Balance appears once something is planned.",
    goalsTitle: "Goals", allGoals: "All goals", linkedTasksReported: "linked tasks done", noGoalsYet: "No goals yet.", goalsOptional: "Goals are optional; tasks can stand alone.",
    nothingPlannedYet: "Nothing is planned yet", nothingPlannedHelp: "DayWright plans only from what you record. It won't fill the day with guesses or sample tasks.",
    stepGoal: "Add a goal (optional)", stepGoalHelp: "Something you're working toward in Learn, Life, Money or Rest.", newGoalAction: "New goal",
    stepTasks: "Add today's tasks and fixed commitments", stepTasksHelp: "Work hours, appointments, anything that can't move — and things you'd like to fit in.",
    stepPropose: "Ask for plans", stepProposeHelp: "Local agents propose up to three schedules. You choose one; nothing is set until you do.",
    savedOnMac: "Saved on this Mac", savedOnMacHelp: "Everything you add stays here. No account, no cloud.",
    nothingInvented: "Nothing invented", nothingInventedHelp: "No sample tasks, no guessed days. Empty stays empty.",
    nothingSetWithoutYou: "Nothing set without you", nothingSetWithoutYouHelp: "Agents propose; you confirm every plan and change.",
    today: "Today", calendar: "Calendar", plans: "Plans", learning: "Learn",
    life: "Life", finance: "Money", rest: "Rest", goals: "Goals",
    demoCopy: "Sample goals, tasks, and outcomes are isolated from your personal workspace. Generate the plan options yourself.",
    none: "NONE", draft: "DRAFT", 
    buildItems: "Build from your items →", 
    start: "START", ready: "READY", askAdjust: "Ask or adjust today →", activeGoals: "ACTIVE GOALS",
    reviewDirection: "Review direction →", 
    agentBrief: "AGENT BRIEF", 
    noNewAdvice: "No new intervention", noNewAdviceHelp: "The agents have not found a supported adjustment that needs your attention.",
    
    linkedTo: "Linked to", planned: "Planned", done: "Done",
    partial: "Partial", skipped: "Skipped", 
    schedule: "SCHEDULE", 
    reviewReplacement: "Review a replacement",
    
    ordinaryTasks: "INDEPENDENT TASKS", ordinaryHelp: "Useful work that does not need to belong to a goal.",
    areaGoals: "GOALS + THEIR TASKS", noAreaGoals: "No goals recorded in this area.",
    date: "DATE", time: "Time", 
    kind: "Kind", repeat: "Repeat", 
    cancel: "Cancel", goalConnection: "GOAL CONNECTION",
    ask: "Ask", adjust: "Adjust", send: "Send message", 
    consulting: "Consulting the relevant agents locally…",
    
    subjects: "LEARNING SUBJECTS", 
    subject: "Subject",
    habits: "LIFE HABITS",
    balance: "MANUAL BALANCE", transactions: "TRANSACTIONS", budgets: "CATEGORY BUDGETS",
    localAiReady: "Local AI is ready",
    manage: "MANAGE →", active: "Active", paused: "Paused", completed: "Completed", 
    
    confirmed: "CONFIRMED", 
    summaryAgent: "Summary agent", 
    
    previousMonth: "Previous month", nextMonth: "Next month", 
    
    
    
    askHelp: "Ask about your plan, records or Library. Nothing changes.", adjustHelp: "Adjust proposes changes to your plan or records. Nothing changes until you confirm.",
    reportHelp: "Tell DayWright what happened. Nothing is marked done from a message; use each task's status control.", 
    voiceTranscribing: "Transcribing locally…", 
    voiceSetup: "Local speech runtime needs setup", 
    
    note: "Note",
    noTransactions: "No manual transactions on this date.", expense: "Expense", income: "Income",
    noBudgets: "No category budget recorded for this month.", 
    adjustPlaceholder: "Make the afternoon lighter…", askPlaceholder: "Ask about your day…",
    confirmChange: "Confirm change", 
    edgeLine1: "A calmer", edgeLine2: "brighter", edgeLine3: "you", 
    orchestratorHelp: "The Orchestrator consults Learning, Life, Finance, and Summary as needed—then shows you the route.",
    protected: "protected",
    planning: "Planning", context: "Context", learningAgent: "Learning Agent",
    cross: "Cross-domain", 
    
    
    suggestionFiled: "SUGGESTION FILED", addedNotes: "Added to your notes.", dismissedSuggestion: "No problem — it’s out of the way.",
    suggestion: "SUGGESTION", keep: "Keep", dismiss: "Dismiss", high: "High", normal: "Normal", startTime: "Start",
    
    examplePlan: "Example plan, not your personal data", examplePlanHelp: "This earlier prototype day contains sample commitments and notes. Your own records remain separate.",
    todayOverview: "Today's execution overview", 
    
    planBalanced: "Balanced", planFocused: "Focused", planGentle: "Gentle", plansFor: "Plans for {date}", draftsProposed: "{count} drafts · proposed by local agents", noPlanSetYet: "No plan set yet", nothingScheduledUntil: "Nothing is scheduled until you set one plan.", askDifferentPlans: "Ask for different plans", draftChip: "Draft", chosenChip: "Chosen", setChip: "Set", timeByArea: "Time by area", constraintsHeading: "Constraints", keptFixed: "Kept fixed: {items}", keptProtected: "Kept protected: {items}", notIncluded: "Not in this plan: {items}", noConstraints: "No fixed or protected tasks.", chooseName: "Choose {name}", chosenReviewBelow: "Chosen — review below", setAtTime: "Set at {time}", setTodayQuestion: "Set “{name}” as today's plan?", setDayQuestion: "Set “{name}” as the plan for {date}?", setConsequence: "{count} entries will be scheduled. Nothing counts as done until you report it. Replacing a set plan later needs a review.", keepComparing: "Keep comparing", setName: "Set {name}", planOfCount: "{index} of {count}", previousPlan: "Previous plan", nextPlan: "Next plan", plansSwitch: "Plans", readOnlyPastDay: "Read-only · past day", pastPlansHelp: "This day has passed. Its plans are kept as they were, and nothing here can change.", noPlansTitle: "No plans for this day yet", noPlansHelp: "Plans are proposed from the tasks you record for the day. Nothing is invented, and nothing is set without you.", noPlansPast: "No plan was set for this day.", loadingPlans: "Loading the plans…", agentNotesHeading: "How the agents made these plans", reviewReplacementToday: "Review a replacement for today's plan", reviewReplacementDay: "Review a replacement for {date}", underReview: "Under review", setNow: "Set now: {name}", replacementName: "Replacement: “{name}”", changeColumn: "Change", changeReported: "Reported", changeSame: "Same", changeShorter: "Shorter", changeLonger: "Longer", changeMoved: "Moved", changeRemoved: "Removed", changeAdded: "Added", staysAsReported: "{status} — stays as reported", notInThisPlan: "Not in this plan", rowsChangeNote: "Highlighted rows change. Entries you already reported keep their status in both plans.", whyAgentsPropose: "Why the agents propose this", approveReplacement: "Approve the replacement", changesCount: "{count} changes", reportedKeep: "Your {count} reported entries keep their status.", oldPlanStays: "“{name}” stays among this day's plans, no longer set.", goalsOnlyOnReport: "Goals change only when you report progress.", reviewedAll: "I've reviewed all {count} changes", reviewedNone: "I've checked that no entries change", replaceWith: "Replace with “{name}”", keepName: "Keep {name}", replaceNeedsReview: "Tick the box once you've reviewed the changes.",
    agentOrchestrator: "Orchestrator", agentLearning: "Learning agent", agentLife: "Life agent", agentFinance: "Finance agent", reviewReplaceWith: "Review replacing with {name}", planIsSet: "“{name}” is set for this day.",
    agentDetails: "What each agent considered",
    listSeparator: ", ",
    suggestionLabel: "suggestion", evidenceLabel: "Evidence:", addToDay: "Add to {day}", suggestionWaits: "Nothing is scheduled from this until you add it.", reportsLabel: "reports", reportPeriod: "Report period", periodDay: "Day", periodWeek: "Week", periodMonth: "Month", noReportYet: "No report for this period yet.", reportsNeedService: "Reports appear while the local service is running.", recordedDaysCount: "Recorded days: {count}", doneOfScheduled: "{done} of {total} done", noReportedWorkYet: "Nothing reported in this period yet.", readReport: "Read the report", adviceHeading: "Advice", noActiveAdvice: "No active advice for this period.", raisedAgain: "Raised again after you dismissed it: {content}", adviceDismissNote: "Dismissing stops an idea being used in future plans, in every period.", clearWeekOfArea: "Clear this week's {area} advice…", clearWeekQuestion: "Clear this week's {area} advice?", clearWeekConsequence: "This week's saved {area} advice and its repeat notices are deleted for good. It can't be undone. Other weeks and areas stay as they are.", clearAdviceAction: "Clear advice",
    tomorrow: "Tomorrow", yesterday: "Yesterday", inDays: "In {count} days", daysAgo: "{count} days ago", readOnlyPastBody: "You can view this day and its plan, not change them.", futureNoPlanNote: "Preset commitments are kept when plans are proposed for this day. No plan exists yet.", statusUnreported: "Unreported", asReported: "as reported", dayEmptyPast: "Nothing was recorded on this day.", dayEmptyFuture: "Nothing recorded for this day yet. Days you don't record stay empty.", openPlansAction: "Open plans", openFullDay: "Open full day", askAboutDay: "Ask about this day", openTodayAction: "Open Today", addAction: "Add", agentAccepted: "Prepared by an agent · added by you", monthGridLabel: "{month}, one button per day", cellSetOf: "plan set, {done} of {total} done", cellRecorded: "recorded, no plan set", cellRecordedShort: "Recorded", cellPresets: "{count} preset", cellSuggested: "{count} suggested by an agent", cellSuggestedShort: "Suggested", cellReadOnly: "read-only", cellEmpty: "nothing recorded", legendSet: "Set — a plan was confirmed; the bar shows entries reported done", legendRecorded: "Recorded — tasks or reports, but no plan set", legendPreset: "Preset commitments", legendSuggested: "Suggested by an agent — not yours until you add it", legendPast: "Past — read-only", legendEmpty: "Empty — nothing recorded, nothing filled in",
    clauseSeparator: ", ",
    areasNote: "Each area keeps its own records. Rest has its own identity in plans and balance; its check-ins live with Life.", goalsFilter: "Show goals", filterAll: "All", goalsIntroLine: "Progress comes only from what you report on tasks and plan entries.", showingCount: "Showing {shown} of {total}.", noGoalsBody: "Goals are optional. Add one when there's something you're working toward; tasks can link to it, and its progress comes from what you report.", noGoalsInFilter: "No goals with this status.", goalActiveHelp: "plans may use it", goalPausedHelp: "plans skip it", goalCompletedHelp: "kept in history", goalStatusFor: "Status of {title}", goalProgress: "{done} of {total} linked tasks done", reportedNotInferred: "reported, not inferred", linkedTasksHeading: "Linked tasks · {count}", noLinkedTasks: "No linked tasks", cantRemoveGoal: "Can't remove this goal yet", goalStillLinked: "{count} tasks are still linked to it. Remove those tasks, or link them to no goal, then try again.", showLinkedTasks: "Show the {count} linked tasks", removeGoalQuestion: "Remove “{title}”?", removeGoalConsequence: "It has no linked tasks. Its history in past days stays readable. This can't be undone.", removeGoalAction: "Remove goal", newGoalTitle: "New goal", editGoalTitle: "Edit goal", saveGoal: "Save goal", goalTitleNeeded: "Give the goal a title.", goalAreaFixed: "A goal's area stays fixed, because its tasks belong to that area.", tasksTitle: "Tasks", tasksRangeNote: "Showing the last {past} days and the next {ahead}. Past days are read-only; agent suggestions wait in Calendar.", linkedToGoal: "Linked to {title}", showAllTasks: "Show all tasks", tasksNeedService: "Tasks across days appear while the local service is running.", noTasksInRange: "No tasks in this range.", pastDaysHeading: "Past {count} days · read-only", tabOverview: "Overview", tabSessions: "Sessions", tabSubjects: "Subjects", tabTasks: "Tasks", tabCheckIn: "Check-in", tabHabits: "Habits", tabEvents: "Events", tabBalance: "Balance", tabTransactions: "Transactions", tabBudgets: "Budgets", recordSessionAction: "Record session", checkInAction: "Check in", recordTransactionAction: "Record transaction", tasksInArea: "Tasks in {area}", noAreaTasks: "No tasks in this area for this day.", areaPastDay: "Showing {date}, a past day. It's read-only.", areaFutureDay: "Showing {date}. Reports can be made on the day itself.", showTodayAction: "Show today", areaNeedsService: "This area's records appear while the local service is running.", loadingArea: "Loading this area…", areaReportsToday: "Reports are made on the day itself; past days stay as they were.", checkInCardTitle: "Check-in", noCheckIn: "No check-in for this day.", editCheckInAction: "Edit check-in", checkInTitle: "Check in", editCheckInTitle: "Edit check-in", saveCheckIn: "Save check-in", checkInPrivacy: "Agents may read your check-in to shape plans. They never edit it.", sleepLabel: "Sleep", lessSleep: "Less sleep", moreSleep: "More sleep", notReportedShort: "Not reported", energyLabel: "Energy", energyScale: "1 low · 5 high", energyOf: "{level} of 5", moodLabel: "Mood", moodLow: "Low", moodFlat: "Flat", moodSteady: "Steady", moodGood: "Good", moodBright: "Bright", noteLabel: "Note", habitsTitle: "Habits", habitsWeekNote: "this week · reported only", reportedThisWeek: "{count} reported this week", pausedLabel: "Paused", habitMarkDone: "Done", habitMarkMissed: "Missed", habitMarkUnreported: "Not reported", habitDoneAction: "Done today", habitMissedAction: "Missed today", pauseAction: "Pause", resumeAction: "Resume", noHabitsYet: "No habits yet.", newHabitAction: "New habit", newHabitTitle: "New habit", saveHabitAction: "Save habit", eventsTitle: "Timed events", noEventsYet: "No timed events for this day.", newEventTitle: "New timed event", saveEventAction: "Save event", eventCalendarNote: "It also appears in Calendar as a Life task.", fieldEnd: "End", fieldCategory: "Category", categorySport: "Sport", categorySocial: "Social", categoryChore: "Chore", categoryHealth: "Health", categoryOther: "Other", sessionsTitle: "Study sessions", sessionNeedsSubject: "Add a subject first; sessions are recorded against one.", noSessions: "No study sessions recorded for this day.", recordSessionTitle: "Record a study session", saveSessionAction: "Save session", fieldSubject: "Subject", fieldResult: "What happened", subjectsTitle: "Subjects", newSubjectAction: "New subject", newSubjectTitle: "New subject", saveSubjectAction: "Save subject", subjectNote: "A subject is something you're studying. It isn't scheduled until you add a task.", fieldDifficulty: "Difficulty", fieldEstimate: "Usual session (minutes)", difficultyEasy: "Easy", difficultyMedium: "Medium", difficultyHard: "Hard", subjectFinished: "finished", markFinishedAction: "Mark finished", reopenAction: "Reopen", noSubjectsYet: "No subjects yet.", balanceHeading: "Balance", balanceExplained: "Your opening balance of {opening}, plus the income and expenses you record.", setOpeningAction: "Set opening balance", openingBalanceTitle: "Opening balance", saveOpeningAction: "Save balance", openingNote: "The amount you start from. Use a minus sign for money owed.", fieldAmount: "Amount", transactionsTitle: "Transactions", recordTransactionTitle: "Record a transaction", saveTransactionAction: "Save transaction", fieldType: "Type", expenseLabel: "Expense", incomeLabel: "Income", budgetsTitle: "Budgets · {month}", setBudgetAction: "Set budget", setBudgetTitle: "Set a monthly budget", saveBudgetAction: "Save budget", budgetNote: "For {month}. Past months stay as they were.", fieldMonthlyAmount: "Monthly amount", spentOfBudget: "{spent} of {budget}", amountInvalid: "Enter an amount with at most two decimal places.",
    report: "Report",
    libraryCaption: "Private notes and imported files. Everything here stays on this Mac.", newNoteAction: "New note", importFilesAction: "Import files", importingLabel: "Importing…", importLimits: "Import Markdown, PDF or Word · under 2 MB per file, PDFs up to 20 pages, at most 50,000 characters of text · only the text is indexed; images are skipped.", savedToLibrary: "Saved to the Library: {names}", importFailed: "{name} wasn't imported: {reason}", wrongFileType: "Choose a Markdown (.md), PDF (.pdf) or Word (.docx) file.", fileTooLarge: "It's larger than 2 MB. Split it into smaller files first.", loadingLibrary: "Loading the Library…", libraryNeedsService: "The Library appears while the local service is running.", libraryLoadFailed: "The Library couldn't be loaded: {reason}", saveNoteAction: "Save note", noteTextLabel: "Text", noteTitleNeeded: "Give the note a title.", noteTextNeeded: "Write the note's text.", notePrivacy: "Saved and indexed on this Mac. Talk can quote it; it's never sent online.", sourcesHeading: "Sources", filterSources: "Filter sources", filterByName: "Filter by name", showSources: "Show sources", filesFilter: "Files", notesFilter: "Notes", newestFirst: "Newest first", columnName: "Name", columnKind: "Kind", columnText: "Text", columnAdded: "Added", columnActions: "Actions", kindMarkdown: "Markdown", kindPdf: "PDF", kindWord: "Word", kindFile: "File", kindNote: "Note", charactersCount: "{count} characters", todayWord: "today", fromTheWeb: "From the web", removeSourceLabel: "Remove {name}…", removeSourceQuestion: "Remove “{name}” from the Library?", removeSourceConsequence: "DayWright deletes its copy of the text and its search entries, so Talk can't draw on it again. Earlier replies keep the passages they quoted.", removeFileConsequence: "DayWright deletes its copy of the text and its search entries, so Talk can't draw on it again. The original file isn't touched, and earlier replies keep the passages they quoted.", removeSourceAction: "Remove", removingLabel: "Removing…", noSourcesMatch: "No sources match.", showAllAction: "Show all", libraryEmptyTitle: "Nothing in your Library yet", libraryEmptyBody: "Notes you write and files you import appear here, and Talk can quote them. DayWright answers only from what's here and invents nothing.", lookUpTitle: "Look up a topic", topicLabel: "Topic", lookUpAction: "Look up", searchingLabel: "Searching…", allowPublicIntro: "Allow a short public introduction", allowPublicOff: "Off: only your notes and files are searched. When nothing local matches, DayWright asks first.", allowPublicOn: "On for this lookup only: sends only the words you type to {destination}. Nothing else is sent.", lookupNeedsService: "Lookups need the local service to be running.", fromYourLibrary: "From your Library · {count}", localOnly: "Local only", askTalkAboutThis: "Ask Talk about this", noLocalMatch: "No match in your notes or files.", libraryEmptySearch: "Your Library is empty, so nothing local matched.", localSearchUnavailable: "Local search isn't available right now: it needs the local embedding model. Nothing was sent online.", fetchIntroQuestion: "Fetch a short public introduction?", consentSends: "Sends", consentTo: "To", consentKeeps: "Keeps", consentNeverSends: "Never sends", consentSendsWords: "only the words “{topic}”", consentKeepsWhat: "a short introduction, saved as a note marked “From the web” only if you choose to keep it", consentNeverWhat: "your notes, files, plans or conversations", fetchIntroAction: "Fetch intro", fetchingLabel: "Fetching…", notNowAction: "Not now", asksEveryTime: "DayWright asks every time. There's no always-allow.", nothingSentNote: "Nothing was sent.", personalTopicTitle: "Not sent: this topic looks personal", personalTopicBody: "Online lookups are for general topics. Remove words like “my”, email addresses and long numbers, then try again. Nothing was sent.", publicLookupFailed: "The public introduction couldn't be fetched, and nothing was saved. Any request that went out is in the network log.", keepIntroQuestion: "Keep this introduction?", encyclopediaNote: "An attributed encyclopedia page. DayWright hasn't checked it independently.", lastEdited: "Last edited {date}.", organizeAs: "Organize it", organizeByLevel: "By level", organizeByMethod: "By method", organizeByProgression: "By progression", labelBasic: "Basic", labelAdvanced: "Advanced", labelPractical: "Practical", labelTheory: "Theory", labelCaseStudy: "Case study", labelExercise: "Exercise", labelIntroduction: "Introduction", labelCore: "Core", labelExtension: "Extension", saveAsNoteAction: "Save as note", choiceWaits: "Not now keeps it waiting here until you decide.", introSaved: "Saved as a note marked “From the web”.", waitingForChoice: "Waiting for your choice", reviewTopicChoice: "{topic} · Review", whatStaysTitle: "What stays, what goes", staysOnMac: "Stays on this Mac", staysOnMacList: "Your files and notes, the search index, all conversations, and all plans and records.", onlineLookupsToday: "Online lookups today: {count}", onlineLookupsShort: "Online: {count}", nothingOnlineToday: "Nothing went online today.", sentWordsTo: "Sent the words “{sent}” to {destination}.", networkReply: "Reply: {received}. You approved it.", neverSentLine: "Never sent: your notes, files, tasks, goals, money records or conversations.", openNetworkLog: "Open network log", networkLogTitle: "Network log", networkLogIntro: "Every request that has left this Mac, newest first. DayWright asks before each one.", networkLogEmpty: "Nothing has gone online.",
    contextChip: "Context: {place} · {date}", talkModes: "Talk mode", closeTalk: "Close Talk", replyLabel: "DayWright's reply · {mode}", answeredByRules: "Answered by DayWright's local rules; the chat model isn't running.", agentsCount: "Agents · {count}", sourcesCount: "Sources · {count}", sourcesNone: "Sources · none", routeHeading: "Route", hideAction: "Hide", usedFromLibrary: "Used from Library:", noSourcesUsed: "No Library sources were used.", voiceTag: "Voice · transcribed on this Mac", proposedNotApplied: "Proposed change · not applied", proposalSetTitle: "Set the plan for {date}", proposalSetLine: "Set “{name}” as the plan", proposalReplaceTitle: "Replace the set plan for {date}", proposalReplaceLine: "“{from}” → “{to}”", reportedKeepStatus: "Entries you already reported keep their status.", proposalShortenTitle: "Change 1 task on {date}", proposalShortenLine: "{title}: {from} → {to}", proposalShortenTo: "Shorten a task to {to}", proposalStaysOnCalendar: "It stays on the calendar; only its length changes.", proposalOtherTitle: "A change to review", nothingChangedYet: "Nothing has changed yet.", proposalConfirmed: "Confirmed. The change is applied.", proposalDismissed: "Dismissed. Nothing changed.", messageLabel: "Message", reportPlaceholder: "Tell DayWright what happened…", holdToTalk: "Hold to talk", micStarting: "Starting…", releaseToSend: "Release to send", listeningStatus: "Listening… release to send · slide away or press Escape to cancel", voiceHint: "Hold the button, or hold Space on it, to talk. Speech is transcribed on this Mac.", talkNeedsService: "Talk needs the local service to be running. Nothing was sent.", modelFooterReady: "Local model · Ready · nothing leaves this Mac", modelFooterStandby: "Local model · Starts when you send · nothing leaves this Mac", modelFooterOff: "Local model unavailable · replies use DayWright's rules · nothing is sent elsewhere",
    noticeSetPlanNeedsService: "Start the local service to set a plan.", noticePlanReplaced: "Plan replaced for this day. Reported entries kept their status.", noticePlanSet: "Plan set. Calendar and your areas show it now.", noticeReportNeedsService: "Start the local service to report progress.", noticeMarked: "Marked {status}.", noticeAdviceDismissed: "Advice dismissed. Periods affected: {count}.", noticeWeekCleared: "Weekly advice cleared: {count}.", noticeGoalUpdated: "Goal updated.", noticeGoalAdded: "Goal added.", noticeTaskUpdated: "Task updated.", noticeTaskAdded: "Task added. It shows in Calendar and its area.", noticeTaskRemoved: "Task removed. Days with a set plan keep their own record.", noticeSuggestionAdded: "Suggestion added to its day.", noticeSuggestionDismissed: "Suggestion dismissed; it won't be suggested again for that day.", noticeGoalRemoved: "Goal removed.", noticeProposeNeedsService: "Start the local service to propose plans.", noticePlansProposed: "Plans proposed from your tasks. Compare them before you set one.", noticeProposalApplied: "Change applied. Calendar shows it now.", noticeFutureTaskUpdated: "Future task updated; who proposed it stays visible.",
    modelUnavailableBody: "Planning, reporting and your records all still work. Talk answers with DayWright's own rules until the model is set up.", noFallbackSent: "Nothing is sent elsewhere as a fallback.", tryAgainAction: "Try again", modelChecking: "Checking…", detailsAction: "Details", modelPartRuntime: "Model runtime", modelPartChat: "Chat model", modelPartSearch: "Library search model", modelPartSpeech: "Speech model", partFound: "Found", partMissing: "Missing",
  },
  zh: {
    navToday: "今天", navCalendar: "日历", navRecords: "记录", navLibrary: "资料库", navTalk: "对话",
    mainNavigation: "主导航", languageLabel: "语言", areasHeading: "领域", lifeAndRest: "生活与休息",
    saveLocal: "已保存在本机 · 私密", saveLocalShort: "已保存 · 私密",
    savePreview: "预览模式 · 未保存", savePreviewShort: "预览 · 未保存",
    saveDemo: "演示空间 · 示例数据", saveDemoShort: "演示 · 示例数据",
    modelReady: "本地模型已就绪", modelReadyShort: "模型已就绪",
    modelStandby: "本地模型待命", modelStandbyShort: "模型待命",
    modelUnavailable: "本地模型不可用", modelUnavailableShort: "模型不可用",
    newTaskTitle: "新建任务", editTaskTitle: "编辑任务", taskDetailTitle: "任务", taskForDate: "日期", openDetails: "查看详情", closeAction: "关闭",
    fieldTitle: "标题", fieldDetail: "详情", fieldArea: "领域", fieldStart: "开始", fieldDuration: "时长（分钟）", fieldTiming: "时间安排",
    fieldRepeats: "重复", fieldGoal: "目标", optionalLabel: "（可选）", repeatNone: "不重复", noGoalOption: "不关联目标",
    timingFlexible: "灵活", timingFlexibleHelp: "计划可以在当天内调整它的时间。", timingFixedHelp: "它固定在这个时间；计划会绕开它。",
    protectedLine: "计划不会缩短、移动或删除它。", saveTask: "保存任务", savingLabel: "保存中…",
    previewCannotSave: "本地服务未运行时无法保存。", agentOrigin: "由智能体添加",
    editAction: "编辑", removeEllipsis: "移除…", stepTwoOfTwo: "第 2 步，共 2 步", removeTaskQuestion: "移除", removeTaskAction: "移除任务",
    removeTaskConsequence: "它会从这一天和草案计划中移除。过去的日子和已确定的计划保持不变。",
    cantRemoveTask: "暂时无法移除这项任务", nothingWasRemoved: "没有移除任何内容。", reportSkipped: "报告为已跳过", okAction: "好",
    scheduleTitle: "日程", entriesCount: "项安排", tasksCount: "项任务", plannedSuffix: "已计划", nowLabel: "现在", nextLabel: "下一项", inPrefix: "还有",
    planSetChip: "计划已确定", draftsNotSet: "份草案 · 尚未确定", reportedChip: "已报告", plansProposedView: "份计划已提出 · 查看",
    nothingRecordedToday: "今天还没有记录", addTaskAction: "添加任务", askReplacement: "请求替换计划",
    compareAndSet: "比较并确定一份", proposePlansAction: "提出计划", proposeNeedsTask: "至少需要一项任务。",
    previewBanner: "预览模式：本地服务未运行，你在这里的任何操作都不会保存。", aboutTheDay: "关于今天",
    notReportedYet: "尚未报告——时间过去不代表已完成", notInSetPlan: "不在今天已设定的计划中", setPlanKeepsTask: "今天已设定的计划包含它，已设定的计划会保持原样。", titleNeeded: "请为任务填写标题。", flagFixed: "固定", flagProtected: "受保护", flagDaily: "每天", flagWeekly: "每周",
    statusFor: "状态", changeStatus: "更改状态", reportWhatHappened: "报告实际发生的情况",
    adviceLabel: "建议", adviceEvidence: "来自今天的报告", adviceStaysActive: "在你忽略之前，它会一直有效。", dismissAction: "忽略",
    noAdviceYet: "暂无建议。有了任务或计划后才会出现建议，并且始终说明依据。",
    strong: "强烈", soft: "温和", balanceTitle: "平衡", plannedReported: "计划 · 已报告",
    balanceFootnote: "按领域计划的时间；填充部分是你已报告的。", balanceEmpty: "有了计划后才会显示平衡。",
    goalsTitle: "目标", allGoals: "全部目标", linkedTasksReported: "项关联任务已完成", noGoalsYet: "还没有目标。", goalsOptional: "目标是可选的；任务也可以独立存在。",
    nothingPlannedYet: "还没有任何计划", nothingPlannedHelp: "DayWright 只根据你记录的内容来规划，不会用猜测或示例任务填满这一天。",
    stepGoal: "添加目标（可选）", stepGoalHelp: "你在学习、生活、财务或休息方面努力的方向。", newGoalAction: "新建目标",
    stepTasks: "添加今天的任务和固定安排", stepTasksHelp: "工作时间、约会、任何不能移动的事项——以及你想安排进去的事情。",
    stepPropose: "请求计划", stepProposeHelp: "本地智能体最多提出三份日程。由你选择一份；在你选择之前不会确定任何内容。",
    savedOnMac: "保存在本机", savedOnMacHelp: "你添加的一切都留在这里。没有账户，没有云端。",
    nothingInvented: "不虚构任何内容", nothingInventedHelp: "没有示例任务，也不猜测日程。空的就保持为空。",
    nothingSetWithoutYou: "没有你就不会确定", nothingSetWithoutYouHelp: "智能体只提出建议；每个计划和更改都由你确认。",
    today: "今日", calendar: "日历", plans: "计划", learning: "学习",
    life: "生活", finance: "财务", rest: "休息", goals: "目标",
    demoCopy: "预设目标、任务和结果与个人空间隔离。请亲自生成计划选项。",
    none: "未生成", draft: "草案", 
    buildItems: "根据任务生成 →", 
    start: "启动", ready: "就绪", askAdjust: "询问或调整今日计划 →", activeGoals: "进行中的目标",
    reviewDirection: "查看方向 →", 
    agentBrief: "智能体简报", 
    noNewAdvice: "暂无新干预建议", noNewAdviceHelp: "智能体尚未发现有充分依据、需要你关注的调整。",
    
    linkedTo: "属于目标", planned: "计划中", done: "已完成",
    partial: "部分完成", skipped: "已跳过", 
    schedule: "日程", 
    reviewReplacement: "查看替换方案",
    
    ordinaryTasks: "独立任务", ordinaryHelp: "不需要归属于目标，但仍值得完成的事项。",
    areaGoals: "目标及其任务", noAreaGoals: "该领域还没有目标。",
    date: "日期", time: "时间", 
    kind: "类型", repeat: "重复", 
    cancel: "取消", goalConnection: "目标关联",
    ask: "询问", adjust: "调整", send: "发送消息", 
    consulting: "正在本地咨询相关智能体…",
    
    subjects: "学习主题", 
    subject: "学习主题",
    habits: "生活习惯",
    balance: "手动余额", transactions: "收支记录", budgets: "分类预算",
    localAiReady: "本地 AI 已就绪", manage: "管理 →",
    active: "进行中", paused: "已暂停", completed: "已完成", 
    
    confirmed: "已确认", 
    summaryAgent: "总结智能体", 
    
    previousMonth: "上个月", nextMonth: "下个月",
    
    
    askHelp: "询问你的计划、记录或资料库。不会改变任何内容。",
    adjustHelp: "调整会提出对计划或记录的修改。在你确认之前，不会改变任何内容。", reportHelp: "告诉 DayWright 发生了什么。消息不会把任何事项标记为完成；请使用每个任务的状态控件。",
    voiceTranscribing: "正在本地转写…",
    voiceSetup: "本地语音运行环境需要设置",
    
    note: "备注", 
    noTransactions: "该日期没有手动收支记录。", expense: "支出", income: "收入", 
    noBudgets: "本月还没有分类预算。", 
    adjustPlaceholder: "让下午轻松一点……", askPlaceholder: "询问今天的安排……", 
    confirmChange: "确认修改", edgeLine1: "更从容",
    edgeLine2: "更明亮", edgeLine3: "成为更好的你", 
    orchestratorHelp: "协调智能体会按需咨询学习、生活、财务和总结智能体，并展示协作路径。", 
    protected: "受到保护", 
    planning: "规划", context: "上下文", learningAgent: "学习智能体", cross: "跨领域",
    
    suggestionFiled: "建议已处理",
    addedNotes: "已添加到你的笔记。", dismissedSuggestion: "好的，已移除此建议。", suggestion: "建议", keep: "保留", dismiss: "忽略",
    high: "高", normal: "普通", startTime: "开始", 
    
    examplePlan: "样例计划，不是你的个人数据", examplePlanHelp: "这是早期原型中的样例安排和备注，你自己的记录与其完全分开。",
    todayOverview: "今日执行概览", 
    
    planBalanced: "均衡", planFocused: "专注", planGentle: "从容", plansFor: "{date}的计划", draftsProposed: "{count} 份草案 · 由本地智能体提出", noPlanSetYet: "尚未确定计划", nothingScheduledUntil: "确定一份计划之前，不会安排任何事项。", askDifferentPlans: "请求其他方案", draftChip: "草案", chosenChip: "已选", setChip: "已确定", timeByArea: "各领域时间", constraintsHeading: "约束", keptFixed: "保持固定：{items}", keptProtected: "保持受保护：{items}", notIncluded: "未纳入此方案：{items}", noConstraints: "没有固定或受保护的任务。", chooseName: "选择{name}", chosenReviewBelow: "已选——请在下方确认", setAtTime: "{time} 已确定", setTodayQuestion: "将“{name}”确定为今天的计划？", setDayQuestion: "将“{name}”确定为{date}的计划？", setConsequence: "将安排 {count} 个条目。在你报告之前，没有任何事项算作完成。之后替换已确定的计划需要先审阅。", keepComparing: "继续比较", setName: "确定{name}", planOfCount: "第 {index} 份，共 {count} 份", previousPlan: "上一份方案", nextPlan: "下一份方案", plansSwitch: "方案", readOnlyPastDay: "只读 · 已过去的日期", pastPlansHelp: "这一天已经过去。它的计划保持原样，这里无法更改。", noPlansTitle: "这一天还没有计划", noPlansHelp: "方案根据你为这一天记录的任务提出。不会凭空编造，也不会未经你同意就确定。", noPlansPast: "这一天没有确定过计划。", loadingPlans: "正在载入方案…", agentNotesHeading: "智能体如何拟定这些方案", reviewReplacementToday: "审阅今天计划的替换方案", reviewReplacementDay: "审阅{date}的替换方案", underReview: "审阅中", setNow: "当前确定：{name}", replacementName: "替换方案：“{name}”", changeColumn: "变化", changeReported: "已报告", changeSame: "不变", changeShorter: "缩短", changeLonger: "延长", changeMoved: "移动", changeRemoved: "移除", changeAdded: "新增", staysAsReported: "{status}——保持已报告状态", notInThisPlan: "不在此方案中", rowsChangeNote: "高亮的行会变化。你已报告的条目在两份方案中都保持其状态。", whyAgentsPropose: "智能体为何提出此方案", approveReplacement: "批准替换", changesCount: "{count} 处变化", reportedKeep: "你已报告的 {count} 个条目保持其状态。", oldPlanStays: "“{name}”仍保留在这一天的方案中，但不再是确定的计划。", goalsOnlyOnReport: "只有你报告进度时，目标才会变化。", reviewedAll: "我已审阅全部 {count} 处变化", reviewedNone: "我已确认没有条目变化", replaceWith: "替换为“{name}”", keepName: "保留{name}", replaceNeedsReview: "审阅变化后请勾选上方选项。",
    agentOrchestrator: "协调", agentLearning: "学习智能体", agentLife: "生活智能体", agentFinance: "财务智能体", reviewReplaceWith: "审阅替换为{name}", planIsSet: "“{name}”已确定为这一天的计划。",
    agentDetails: "各智能体考虑了什么",
    listSeparator: "、",
    suggestionLabel: "建议", evidenceLabel: "依据：", addToDay: "添加到{day}", suggestionWaits: "在你添加之前，不会据此安排任何事项。", reportsLabel: "报告", reportPeriod: "报告周期", periodDay: "日", periodWeek: "周", periodMonth: "月", noReportYet: "这个周期还没有报告。", reportsNeedService: "本地服务运行时才会显示报告。", recordedDaysCount: "已记录天数：{count}", doneOfScheduled: "完成 {done} / {total}", noReportedWorkYet: "这个周期还没有报告任何事项。", readReport: "阅读报告", adviceHeading: "建议", noActiveAdvice: "这个周期没有有效建议。", raisedAgain: "你忽略后再次提出：{content}", adviceDismissNote: "忽略后，这条建议不会再用于任何周期的后续计划。", clearWeekOfArea: "清除本周的{area}建议…", clearWeekQuestion: "清除本周的{area}建议？", clearWeekConsequence: "本周已保存的{area}建议及其重复提示将被永久删除，且无法撤销。其他周和其他领域不受影响。", clearAdviceAction: "清除建议",
    tomorrow: "明天", yesterday: "昨天", inDays: "{count} 天后", daysAgo: "{count} 天前", readOnlyPastBody: "你可以查看这一天及其计划，但不能更改。", futureNoPlanNote: "为这一天提出方案时会保留预设安排。目前还没有计划。", statusUnreported: "未报告", asReported: "按你的报告", dayEmptyPast: "这一天没有任何记录。", dayEmptyFuture: "这一天还没有记录。你不记录的日子会保持空白。", openPlansAction: "打开方案", openFullDay: "查看完整的一天", askAboutDay: "询问这一天", openTodayAction: "打开今天", addAction: "添加", agentAccepted: "由智能体准备 · 由你添加", monthGridLabel: "{month}，每天一个按钮", cellSetOf: "计划已确定，完成 {done} / {total}", cellRecorded: "有记录，未确定计划", cellRecordedShort: "有记录", cellPresets: "预设 {count} 项", cellSuggested: "智能体建议 {count} 项", cellSuggestedShort: "建议", cellReadOnly: "只读", cellEmpty: "无记录", legendSet: "已确定——计划已确认；进度条显示已报告完成的条目", legendRecorded: "有记录——有任务或报告，但未确定计划", legendPreset: "预设安排", legendSuggested: "智能体建议——在你添加之前不属于你", legendPast: "过去——只读", legendEmpty: "空白——没有记录，也不会被填充",
    clauseSeparator: "，",
    areasNote: "每个领域都有自己的记录。休息在计划和平衡中单独计算；它的状态记录归在生活中。", goalsFilter: "显示目标", filterAll: "全部", goalsIntroLine: "进度只来自你对任务和计划条目的报告。", showingCount: "显示 {shown} / {total}。", noGoalsBody: "目标是可选的。当你有想要推进的事情时再添加；任务可以关联到它，进度来自你的报告。", noGoalsInFilter: "没有处于此状态的目标。", goalActiveHelp: "计划可以使用", goalPausedHelp: "计划会跳过", goalCompletedHelp: "保留在历史中", goalStatusFor: "{title}的状态", goalProgress: "已完成 {done} / {total} 个关联任务", reportedNotInferred: "来自报告，而非推测", linkedTasksHeading: "关联任务 · {count}", noLinkedTasks: "没有关联任务", cantRemoveGoal: "暂时无法移除这个目标", goalStillLinked: "仍有 {count} 个任务关联到它。请先移除这些任务，或取消它们与目标的关联，然后再试。", showLinkedTasks: "查看 {count} 个关联任务", removeGoalQuestion: "移除“{title}”？", removeGoalConsequence: "它没有关联任务。过去日子里的记录仍可查看。此操作无法撤销。", removeGoalAction: "移除目标", newGoalTitle: "新建目标", editGoalTitle: "编辑目标", saveGoal: "保存目标", goalTitleNeeded: "请为目标填写标题。", goalAreaFixed: "目标的领域不能更改，因为它的任务属于该领域。", tasksTitle: "任务", tasksRangeNote: "显示过去 {past} 天和未来 {ahead} 天。过去的日子只读；智能体建议在日历中等待你决定。", linkedToGoal: "关联到{title}", showAllTasks: "显示全部任务", tasksNeedService: "本地服务运行时才会显示跨日期的任务。", noTasksInRange: "这个范围内没有任务。", pastDaysHeading: "过去 {count} 天 · 只读", tabOverview: "概览", tabSessions: "学习记录", tabSubjects: "科目", tabTasks: "任务", tabCheckIn: "状态记录", tabHabits: "习惯", tabEvents: "活动", tabBalance: "余额", tabTransactions: "收支", tabBudgets: "预算", recordSessionAction: "记录学习", checkInAction: "记录状态", recordTransactionAction: "记录收支", tasksInArea: "{area}中的任务", noAreaTasks: "这一天在这个领域没有任务。", areaPastDay: "正在显示已过去的{date}，只读。", areaFutureDay: "正在显示{date}。当天才能报告。", showTodayAction: "显示今天", areaNeedsService: "本地服务运行时才会显示这个领域的记录。", loadingArea: "正在载入这个领域…", areaReportsToday: "报告只能在当天进行；过去的日子保持原样。", checkInCardTitle: "状态记录", noCheckIn: "这一天没有状态记录。", editCheckInAction: "编辑状态记录", checkInTitle: "记录状态", editCheckInTitle: "编辑状态记录", saveCheckIn: "保存状态记录", checkInPrivacy: "智能体可以读取你的状态记录来调整计划，但绝不会修改它。", sleepLabel: "睡眠", lessSleep: "减少睡眠时长", moreSleep: "增加睡眠时长", notReportedShort: "未报告", energyLabel: "精力", energyScale: "1 低 · 5 高", energyOf: "{level} / 5", moodLabel: "心情", moodLow: "低落", moodFlat: "平淡", moodSteady: "平稳", moodGood: "不错", moodBright: "愉快", noteLabel: "备注", habitsTitle: "习惯", habitsWeekNote: "本周 · 只显示报告", reportedThisWeek: "本周已报告 {count} 次", pausedLabel: "已暂停", habitMarkDone: "已完成", habitMarkMissed: "未完成", habitMarkUnreported: "未报告", habitDoneAction: "今天已完成", habitMissedAction: "今天未完成", pauseAction: "暂停", resumeAction: "恢复", noHabitsYet: "还没有习惯。", newHabitAction: "新建习惯", newHabitTitle: "新建习惯", saveHabitAction: "保存习惯", eventsTitle: "定时活动", noEventsYet: "这一天没有定时活动。", newEventTitle: "新建定时活动", saveEventAction: "保存活动", eventCalendarNote: "它也会作为生活任务显示在日历中。", fieldEnd: "结束", fieldCategory: "类别", categorySport: "运动", categorySocial: "社交", categoryChore: "家务", categoryHealth: "健康", categoryOther: "其他", sessionsTitle: "学习记录", sessionNeedsSubject: "请先添加科目；学习记录需要对应一个科目。", noSessions: "这一天没有学习记录。", recordSessionTitle: "记录一次学习", saveSessionAction: "保存学习记录", fieldSubject: "科目", fieldResult: "实际情况", subjectsTitle: "科目", newSubjectAction: "新建科目", newSubjectTitle: "新建科目", saveSubjectAction: "保存科目", subjectNote: "科目是你正在学习的内容。在你添加任务之前，它不会被安排。", fieldDifficulty: "难度", fieldEstimate: "通常时长（分钟）", difficultyEasy: "简单", difficultyMedium: "中等", difficultyHard: "困难", subjectFinished: "已完成", markFinishedAction: "标记为已完成", reopenAction: "重新开始", noSubjectsYet: "还没有科目。", balanceHeading: "余额", balanceExplained: "期初余额 {opening}，加上你记录的收入和支出。", setOpeningAction: "设置期初余额", openingBalanceTitle: "期初余额", saveOpeningAction: "保存余额", openingNote: "你开始记账时的金额。欠款请使用负号。", fieldAmount: "金额", transactionsTitle: "收支", recordTransactionTitle: "记录一笔收支", saveTransactionAction: "保存收支", fieldType: "类型", expenseLabel: "支出", incomeLabel: "收入", budgetsTitle: "预算 · {month}", setBudgetAction: "设置预算", setBudgetTitle: "设置月度预算", saveBudgetAction: "保存预算", budgetNote: "适用于 {month}。过去的月份保持原样。", fieldMonthlyAmount: "每月金额", spentOfBudget: "{spent} / {budget}", amountInvalid: "请输入最多两位小数的金额。",
    report: "汇报",
    libraryCaption: "私密笔记和导入的文件。这里的一切都保存在这台 Mac 上。", newNoteAction: "新建笔记", importFilesAction: "导入文件", importingLabel: "正在导入…", importLimits: "可导入 Markdown、PDF 或 Word · 每个文件小于 2 MB，PDF 最多 20 页，文字最多 50,000 字符 · 只索引文字，图片会被跳过。", savedToLibrary: "已保存到资料库：{names}", importFailed: "{name} 未导入：{reason}", wrongFileType: "请选择 Markdown（.md）、PDF（.pdf）或 Word（.docx）文件。", fileTooLarge: "文件大于 2 MB。请先拆分成较小的文件。", loadingLibrary: "正在载入资料库…", libraryNeedsService: "本地服务运行时才会显示资料库。", libraryLoadFailed: "无法载入资料库：{reason}", saveNoteAction: "保存笔记", noteTextLabel: "正文", noteTitleNeeded: "请为笔记填写标题。", noteTextNeeded: "请填写笔记正文。", notePrivacy: "保存在这台 Mac 上并建立索引。对话可以引用它，但它绝不会被发送到网上。", sourcesHeading: "来源", filterSources: "筛选来源", filterByName: "按名称筛选", showSources: "显示来源", filesFilter: "文件", notesFilter: "笔记", newestFirst: "最新的在前", columnName: "名称", columnKind: "类型", columnText: "文字量", columnAdded: "添加时间", columnActions: "操作", kindMarkdown: "Markdown", kindPdf: "PDF", kindWord: "Word", kindFile: "文件", kindNote: "笔记", charactersCount: "{count} 字符", todayWord: "今天", fromTheWeb: "来自网络", removeSourceLabel: "移除{name}…", removeSourceQuestion: "从资料库中移除“{name}”？", removeSourceConsequence: "DayWright 会删除保存的文字副本和搜索索引，对话将不能再引用它。之前的回复会保留当时引用的段落。", removeFileConsequence: "DayWright 会删除保存的文字副本和搜索索引，对话将不能再引用它。原始文件不受影响，之前的回复会保留当时引用的段落。", removeSourceAction: "移除", removingLabel: "正在移除…", noSourcesMatch: "没有匹配的来源。", showAllAction: "全部显示", libraryEmptyTitle: "资料库里还没有内容", libraryEmptyBody: "你写的笔记和导入的文件会显示在这里，对话可以引用它们。DayWright 只根据这里的内容回答，不会凭空编造。", lookUpTitle: "查找主题", topicLabel: "主题", lookUpAction: "查找", searchingLabel: "正在查找…", allowPublicIntro: "允许获取简短的公开介绍", allowPublicOff: "关闭：只搜索你的笔记和文件。本地没有匹配时，DayWright 会先征求你的同意。", allowPublicOn: "仅对这次查找开启：只把你输入的词语发送到 {destination}，不发送其他任何内容。", lookupNeedsService: "本地服务运行时才能查找。", fromYourLibrary: "来自你的资料库 · {count}", localOnly: "仅限本地", askTalkAboutThis: "在对话中询问", noLocalMatch: "你的笔记和文件中没有匹配的内容。", libraryEmptySearch: "你的资料库是空的，所以本地没有匹配的内容。", localSearchUnavailable: "本地搜索暂时不可用：它需要本地嵌入模型。没有任何内容被发送到网上。", fetchIntroQuestion: "获取一段简短的公开介绍？", consentSends: "发送", consentTo: "发往", consentKeeps: "保留", consentNeverSends: "绝不发送", consentSendsWords: "仅“{topic}”这几个字", consentKeepsWhat: "一段简短介绍；只有你选择保留时，才会保存为标记“来自网络”的笔记", consentNeverWhat: "你的笔记、文件、计划或对话", fetchIntroAction: "获取介绍", fetchingLabel: "正在获取…", notNowAction: "暂不", asksEveryTime: "DayWright 每次都会询问，没有“始终允许”。", nothingSentNote: "没有发送任何内容。", personalTopicTitle: "未发送：这个主题看起来涉及个人信息", personalTopicBody: "在线查找只用于一般性主题。请去掉“我的”之类的个人词语、电子邮件地址和长串数字后再试。没有发送任何内容。", publicLookupFailed: "无法获取公开介绍，也没有保存任何内容。已发出的请求都记录在网络日志中。", keepIntroQuestion: "保留这段介绍？", encyclopediaNote: "来自一个注明出处的百科页面，DayWright 没有独立核实。", lastEdited: "最后编辑于{date}。", organizeAs: "整理方式", organizeByLevel: "按层次", organizeByMethod: "按方法", organizeByProgression: "按进度", labelBasic: "基础", labelAdvanced: "进阶", labelPractical: "实践", labelTheory: "理论", labelCaseStudy: "案例", labelExercise: "练习", labelIntroduction: "入门", labelCore: "核心", labelExtension: "拓展", saveAsNoteAction: "保存为笔记", choiceWaits: "选择“暂不”时，它会留在这里等你决定。", introSaved: "已保存为标记“来自网络”的笔记。", waitingForChoice: "等待你决定", reviewTopicChoice: "{topic} · 查看", whatStaysTitle: "什么留下，什么发出", staysOnMac: "保存在这台 Mac 上", staysOnMacList: "你的文件和笔记、搜索索引、所有对话，以及所有计划和记录。", onlineLookupsToday: "今天的在线查找：{count}", onlineLookupsShort: "在线：{count}", nothingOnlineToday: "今天没有任何内容发送到网上。", sentWordsTo: "已将“{sent}”发送到 {destination}。", networkReply: "回复：{received}。由你批准。", neverSentLine: "绝不发送：你的笔记、文件、任务、目标、财务记录或对话。", openNetworkLog: "打开网络日志", networkLogTitle: "网络日志", networkLogIntro: "所有离开这台 Mac 的请求，最新的在前。DayWright 每次发送前都会询问。", networkLogEmpty: "还没有任何内容发送到网上。",
    contextChip: "上下文：{place} · {date}", talkModes: "对话模式", closeTalk: "关闭对话", replyLabel: "DayWright 的回复 · {mode}", answeredByRules: "由 DayWright 的本地规则回答；对话模型没有运行。", agentsCount: "智能体 · {count}", sourcesCount: "来源 · {count}", sourcesNone: "来源 · 无", routeHeading: "路径", hideAction: "收起", usedFromLibrary: "引用自资料库：", noSourcesUsed: "没有引用资料库中的来源。", voiceTag: "语音 · 在这台 Mac 上转写", proposedNotApplied: "建议修改 · 尚未应用", proposalSetTitle: "确定{date}的计划", proposalSetLine: "将“{name}”确定为计划", proposalReplaceTitle: "替换{date}已确定的计划", proposalReplaceLine: "“{from}” → “{to}”", reportedKeepStatus: "你已报告的条目保持其状态。", proposalShortenTitle: "修改{date}的 1 个任务", proposalShortenLine: "{title}：{from} → {to}", proposalShortenTo: "将一个任务缩短到 {to}", proposalStaysOnCalendar: "它仍保留在日历中，只改变时长。", proposalOtherTitle: "待审阅的修改", nothingChangedYet: "目前还没有任何改变。", proposalConfirmed: "已确认，修改已生效。", proposalDismissed: "已忽略，没有任何改变。", messageLabel: "消息", reportPlaceholder: "告诉 DayWright 发生了什么……", holdToTalk: "按住说话", micStarting: "正在启动…", releaseToSend: "松开发送", listeningStatus: "正在聆听……松开即发送 · 移开或按 Esc 取消", voiceHint: "按住按钮，或在按钮上按住空格键说话。语音在这台 Mac 上转写。", talkNeedsService: "对话需要本地服务运行。没有发送任何内容。", modelFooterReady: "本地模型 · 已就绪 · 数据不会离开这台 Mac", modelFooterStandby: "本地模型 · 发送时启动 · 数据不会离开这台 Mac", modelFooterOff: "本地模型不可用 · 由 DayWright 的规则回答 · 不会发送到其他地方",
    noticeSetPlanNeedsService: "请启动本地服务以确定计划。", noticePlanReplaced: "这一天的计划已替换，已报告的条目保持其状态。", noticePlanSet: "计划已确定，日历和各领域中已更新。", noticeReportNeedsService: "请启动本地服务以报告进度。", noticeMarked: "已标记为{status}。", noticeAdviceDismissed: "建议已忽略，涉及的周期：{count}。", noticeWeekCleared: "已清除的每周建议：{count}。", noticeGoalUpdated: "目标已更新。", noticeGoalAdded: "目标已添加。", noticeTaskUpdated: "任务已更新。", noticeTaskAdded: "任务已添加，会显示在日历和它的领域中。", noticeTaskRemoved: "任务已移除。已确定计划的日子保留各自的记录。", noticeSuggestionAdded: "建议已加入对应的日子。", noticeSuggestionDismissed: "建议已忽略；这一天不会再次建议它。", noticeGoalRemoved: "目标已移除。", noticeProposeNeedsService: "请启动本地服务以提出方案。", noticePlansProposed: "已根据你的任务提出方案。请先比较，再确定一份。", noticeProposalApplied: "修改已生效，日历中已更新。", noticeFutureTaskUpdated: "未来任务已更新；提出者仍然可见。",
    modelUnavailableBody: "计划、报告和记录都照常可用。模型设置好之前，对话由 DayWright 自己的规则回答。", noFallbackSent: "不会改为发送到其他地方处理。", tryAgainAction: "重试", modelChecking: "正在检查…", detailsAction: "详情", modelPartRuntime: "模型运行环境", modelPartChat: "对话模型", modelPartSearch: "资料库搜索模型", modelPartSpeech: "语音模型", partFound: "已找到", partMissing: "缺失",
  },
};

const demoMessages = {
  "Finish the local AI course": "完成本地 AI 课程", "Keep evenings restorative": "保持有助恢复的夜晚",
  "Build a three-month buffer": "建立三个月的应急储备", "Review retrieval notes": "复习检索笔记",
  "Turn three notes into questions.": "把三条笔记整理成问题。", "Lunch walk": "午间散步",
  "A short reset before the afternoon.": "下午开始前短暂恢复。", "Weekly spending check": "每周支出检查",
  "Review groceries and subscriptions.": "检查杂货和订阅支出。", "Local RAG foundations": "本地 RAG 基础",
  "Evening wind-down": "晚间放松", "Screens off by 10:30.": "22:30 前关闭屏幕。",
  "Good energy; keep the evening light.": "精力不错，今晚保持轻松。", Learning: "学习", "Reference book": "参考书",
  "How DayWright uses local RAG": "DayWright 如何使用本地 RAG", Balanced: "均衡", Focused: "专注", Gentle: "轻松",
  "French listening": "法语听力", "Podcast + notes (Beginner A2)": "播客与笔记（A2 初级）",
  "Deep work — Course project": "深度工作 — 课程项目", "Build section 2 and write notes": "完成第 2 部分并整理笔记",
  "Strength session": "力量训练", "Gym · Full body": "健身房 · 全身训练", "Shower & clear inbox": "淋浴并清理收件箱",
  "Tidy up and prep for afternoon": "整理并准备下午的安排", Lunch: "午餐", "Good food, short walk": "好好吃饭，短暂散步",
  "Budget review": "预算检查", "Check spending, update categories": "检查支出并更新分类", "Open buffer": "开放缓冲时间",
  "Use for catch-up or personal task": "用于补进度或处理个人事务", "Course project": "课程项目", "Continue build + polish": "继续完成并优化",
  "Prepare for call": "准备通话", "Review notes and agenda": "查看笔记和议程", "Call with Alex": "与 Alex 通话", "Project sync": "项目同步",
  "Evening reset": "晚间恢复", "Journal, plan tomorrow, wind down": "写日记、规划明天并放松", "Focused build block": "专注推进时段",
  "Finish the hardest course milestone": "完成最困难的课程里程碑", "One clear milestone, then stop": "完成一个明确里程碑后停止",
  "Recovery buffer": "恢复缓冲时间", "Walk, errands, or unplanned needs": "散步、办事或应对临时需求", "Light course review": "轻量课程复习",
  "Review notes; no new build work": "复习笔记，不开始新的开发任务", "Try a 10-minute walk after lunch.": "午饭后尝试散步 10 分钟。",
  "A short walk can restore energy and focus for the afternoon.": "短暂散步有助于恢复下午的精力与专注。",
  "Steady progress across learning, life, and money with a protected buffer.": "在学习、生活和财务之间稳步推进，并保留缓冲时间。",
  "Uses the open buffer for the course milestone while preserving fixed commitments.": "在保留固定安排的同时，把开放缓冲时间用于课程里程碑。",
  "Shortens deep work and protects more recovery time for a lower-energy day.": "缩短深度工作，为精力较低的一天保留更多恢复时间。",
  "Keeps your times and commitments; repeated shortening requests reduce flexible blocks by 15 minutes but never remove them.": "保留原有时间与安排；反复要求缩短的灵活任务会减少 15 分钟，但不会被删除。",
};

function localizeDemo(value, language) {
  if (language !== "zh" || typeof value !== "string") return value;
  if (demoMessages[value]) return demoMessages[value];
  return value
    .replace(/^(.+) was (.+) across (\d+) recorded plans?\. In the next plan, try a (\d+)-minute version at (\d{2}:\d{2}) and make the first step: (.+)\.$/,
      (_, task, outcome, plans, minutes, time, step) => `${demoMessages[task] || task}在 ${plans} 份已记录计划中${outcome.replace(/skipped once/, "跳过 1 次").replace(/skipped (\d+) times/, "跳过 $1 次").replace(/partly completed once/, "部分完成 1 次").replace(/partly completed (\d+) times/, "部分完成 $1 次").replace(" and ", "，且")}。下一份计划在 ${time} 安排 ${minutes} 分钟，第一步是：${demoMessages[step] || step}。`)
    .replace(/^You recorded (\d+) learning sessions? for (.+) \((\d+) minutes; (\d+) completed\)\. Keep (.+) at (\d{2}:\d{2}) for (\d+) minutes and begin with: (.+)\.$/,
      (_, sessions, subject, minutes, done, task, time, taskMinutes, step) => `你为${demoMessages[subject] || subject}记录了 ${sessions} 次学习（共 ${minutes} 分钟，完成 ${done} 次）。下一份计划在 ${time} 保留${demoMessages[task] || task}的 ${taskMinutes} 分钟，并先做：${demoMessages[step] || step}。`)
    .replace(/^On (\d{4}-\d{2}-\d{2}), (.+)\. Keep (.+) at (\d{2}:\d{2}) for (\d+) minutes in the next plan; your note says: (.+)\.$/,
      (_, date, evidence, task, time, minutes, note) => `${date} 的记录显示：${evidence.replace(/energy was (\d+)\/5/, "精力为 $1/5").replace(/(\d+)\/(\d+) habit report was completed/, "习惯记录完成 $1/$2").replace(/(\d+)\/(\d+) habit reports were completed/, "习惯记录完成 $1/$2")}。下一份计划在 ${time} 保留${demoMessages[task] || task}的 ${minutes} 分钟；你的备注是：${demoMessages[note] || note}。`)
    .replace(/^Recorded (.+) expenses are ([\d.]+) of the saved ([\d.]+) (\d{4}-\d{2}) budget, leaving ([\d.]+)\. In the next plan, use (.+) at (\d{2}:\d{2}) for (\d+) minutes to check the next purchase\.$/,
      (_, category, spent, budget, month, remaining, task, time, minutes) => `${month} 的${demoMessages[category] || category}支出已记录 ${spent} / ${budget}，剩余 ${remaining}。下一份计划在 ${time} 用 ${minutes} 分钟完成${demoMessages[task] || task}，再决定下一笔购买。`)
    .replace(/^Review the size or timing of learning work before the next plan\.$/, "在制定下一份计划前，重新评估学习任务的时长或时间安排。")
    .replace(/^Review the size or timing of life work before the next plan\.$/, "在制定下一份计划前，重新评估生活任务的时长或时间安排。")
    .replace(/^Review the size or timing of money work before the next plan\.$/, "在制定下一份计划前，重新评估财务任务的时长或时间安排。")
    .replace(/^Review the size or timing of rest work before the next plan\.$/, "在制定下一份计划前，重新评估休息安排的时长或时间。")
    .replace(/^Adds 15 minutes to (.+) where the saved calendar has room; fixed times and repeatedly disliked tasks stay unchanged\.$/,
      (_, item) => `在已保存日程有空间时，为${demoMessages[item] || item}增加 15 分钟；固定时间和反复不喜欢的任务保持不变。`)
    .replace(/^Shortens (.+) by 15 minutes, never removes it; fixed commitments stay unchanged\.$/,
      (_, item) => `将${demoMessages[item] || item}缩短 15 分钟但不删除；固定安排保持不变。`);
}

const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => localStorage.getItem("daywright-language") || "en");
  useEffect(() => { document.documentElement.lang = language === "zh" ? "zh-Hans" : "en"; }, [language]);
  const value = useMemo(() => ({
    language,
    setLanguage(next) {
      localStorage.setItem("daywright-language", next);
      document.documentElement.lang = next === "zh" ? "zh-Hans" : "en";
      setLanguage(next);
    },
    /**
     * Look up interface text in the current language, falling back to English and then the key.
     * @param {string} key - The message key.
     * @param {object} [values] - Replacements for `{name}` placeholders in the message.
     * @returns {string} The message.
     */
    t(key, values) {
      const normalized = typeof key === "string" ? key.toLowerCase() : key;
      const text = messages[language][key] || messages[language][normalized] || messages.en[key] || messages.en[normalized] || key;
      return values ? text.replace(/\{(\w+)\}/g, (match, name) => (name in values ? String(values[name]) : match)) : text;
    },
    demoText(value) { return localizeDemo(value, language); },
  }), [language]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useI18n() {
  return useContext(LanguageContext);
}
