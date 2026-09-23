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
    life: "Life", finance: "Money", rest: "Rest", library: "Library", goals: "Goals",
    localPrivate: "LOCALLY SAVED · PRIVATE", 
    demoCopy: "Sample goals, tasks, and outcomes are isolated from your personal workspace. Generate the plan options yourself.",
    
    none: "NONE", draft: "DRAFT", 
    buildItems: "Build from your items →", localAi: "LOCAL AI",
    start: "START", ready: "READY", askAdjust: "Ask or adjust today →", activeGoals: "ACTIVE GOALS",
    reviewDirection: "Review direction →", dailyRecords: "YOUR DAILY RECORDS", addItem: "+ ADD TASK",
    
    
    agentBrief: "AGENT BRIEF", 
    
    noNewAdvice: "No new intervention", noNewAdviceHelp: "The agents have not found a supported adjustment that needs your attention.",
    
    
    
    noItems: "No tasks are recorded for this date.", addRealTask: " Add a real task or commitment here.",
    linkedTo: "Linked to", independentTask: "Independent task", planned: "Planned", done: "Done",
    partial: "Partial", skipped: "Skipped", edit: "EDIT", remove: "REMOVE", confirmRemove: "CONFIRM REMOVE", manageArea: "MANAGE AN AREA",
    
    
    
    schedule: "SCHEDULE", 
    reviewReplacement: "Review a replacement",
    
    
    goalManagement: "GOAL MANAGEMENT", longerHorizon: "LONGER HORIZON",
    goalsIntro: "Set direction in each area, connect tasks, and trace progress in both places.", yourGoals: "YOUR GOALS",
    recorded: "RECORDED", setGoal: "SET A GOAL", whatMatters: "What matters?", area: "Area", addGoal: "ADD GOAL",
    linkedTasks: "linked tasks done", goalPath: "GOAL PATH", goalTasks: "TASKS MOVING THIS GOAL FORWARD",
    noGoalTasks: "No tasks are linked to this goal yet.", addGoalTask: "+ ADD TASK TO THIS GOAL",
    ordinaryTasks: "INDEPENDENT TASKS", ordinaryHelp: "Useful work that does not need to belong to a goal.",
    areaGoals: "GOALS + THEIR TASKS", manageGoals: "MANAGE ALL GOALS →", noAreaGoals: "No goals recorded in this area.",
    areaState: "AREA STATE", dayLedger: "TASKS + DAY PLAN", relatedGoal: "Related goal",
    allTasks: "ALL TASKS", allTasksHelp: "Goal-linked and independent work live together here. Linked work carries its goal and overall progress.",
    goalLinked: "MOVES THIS GOAL", 
    noGoal: "No goal — independent task", taskName: "Task name", date: "DATE", time: "Time", minutes: "Minutes",
    kind: "Kind", repeat: "Repeat", details: "Details (optional)", addDailyItem: "ADD TASK",
    saveChanges: "SAVE CHANGES", cancel: "Cancel", goalConnection: "GOAL CONNECTION",
    goalConnectionHelp: "Link this task to a goal so progress appears here and on the Goals page.",
    talk: "TALK TO DAYWRIGHT", talkTitle: "Talk it through.",
    ask: "Ask", adjust: "Adjust", send: "Send message", 
    private: "PRIVATE", consulting: "Consulting the relevant agents locally…",
    learningTitle: "Learning", learningIntro: "Manage learning goals, their tasks, subjects, and recorded sessions.",
    lifeTitle: "Life + rest", lifeIntro: "Manage life goals, their tasks, daily state, habits, events, and recovery.",
    moneyTitle: "Money", moneyIntro: "Manage financial goals, their tasks, balances, transactions, and budgets.",
    libraryTitle: "Library", libraryIntro: "Index private notes or enter a topic for local-first research.",
    subjects: "LEARNING SUBJECTS", subjectsHelp: "Subjects are reference areas. Add a linked timed task when it should advance a goal and appear on Calendar.",
    newSubject: "New subject", difficulty: "Difficulty", estimate: "Estimate / min", addSubject: "ADD SUBJECT",
    sessionRecord: "SESSION RECORD", noSession: "No session outcome recorded for this date.", subject: "Subject",
    result: "Reported result", recordSession: "RECORD SESSION", dailyState: "DAILY STATE",
    stateHelp: "Sleep, energy, and mood are your reports—not inferred by an agent.", habits: "LIFE HABITS",
    timedEvents: "TIMED EVENTS", eventsHelp: "Events are also daily tasks: Calendar, Plans, and Life read the same record.",
    balance: "MANUAL BALANCE", transactions: "TRANSACTIONS", budgets: "CATEGORY BUDGETS",
    savedLocal: "Saved locally. Related summaries and dated ledgers have been refreshed.",
    previewMode: "PREVIEW MODE · NOT SAVED", 
    localAiReady: "Local AI is ready",
    manage: "MANAGE →", active: "Active", paused: "Paused", completed: "Completed", saveName: "Save name",
    noGoals: "No goals yet. Add your first learning, life, money, or rest goal.", startServiceGoals: "Start the local service to save goals.",
    editDailyRecord: "EDIT DAILY RECORD", addTo: "ADD TO", yourOwnData: "YOUR OWN DATA", flexibleTask: "Flexible task",
    fixedCommitment: "Fixed commitment", oneTime: "One time", everyDay: "Every day", everyWeek: "Every week",
    protectedHelp: "Important to keep even if I later ask to shorten it", saving: "SAVING…", startServiceSave: "Start the local service to save your records.",
    readOnlyHistory: "READ-ONLY HISTORY", fixed: "FIXED", flexible: "FLEXIBLE", 
    confirmed: "CONFIRMED", 
    
    summaryAgent: "Summary agent", 
    
    
    
    
    
    
    previousMonth: "Previous month", nextMonth: "Next month", 
    
    
    
    
    
    
    
    
    
    
    
    
    agentWorkbench: "LOCAL MULTI-AGENT WORKBENCH", agentModel: "5 agents · local RAG + Qwen synthesis", indexedSources: "indexed sources",
    askHelp: "Understand the plan or weigh a tradeoff.", adjustHelp: "Describe a change. DayWright will propose it for confirmation.",
    reportHelp: "Talk through what happened; completion remains explicit.", voiceRecording: "Recording on this Mac · press the microphone again to finish",
    voiceStarting: "Requesting microphone access…", voiceTranscribing: "Transcribing locally…", voiceRecognized: "Text added locally · review it before sending",
    voiceReady: "Voice ready · press the microphone to talk", voiceSetup: "Local speech runtime needs setup", proposalControl: "A proposal is not an action. You stay in control.",
    chooseSubject: "Choose a subject", easy: "Easy", medium: "Medium", hard: "Hard", markComplete: "MARK COMPLETE", reopen: "REOPEN",
    noSubjects: "No learning subject recorded yet.", futureSessions: "Future sessions cannot be reported early.", sleepHours: "Sleep / hours",
    energy: "Energy / 1–5", mood: "Mood / 1–5", notReported: "Not reported", reflection: "Reflection", saveDaily: "SAVE DAILY STATE",
    noNote: "No note", noHabits: "No habits recorded yet.", newHabit: "New habit", frequency: "Frequency", daily: "Daily", weekly: "Weekly",
    addHabit: "ADD HABIT", reportHabit: "Report habit", chooseHabit: "Choose a habit", outcome: "Outcome", notDone: "Not done", note: "Note",
    saveHabit: "SAVE HABIT REPORT", pause: "PAUSE", resume: "RESUME", eventName: "Event name", end: "End", category: "Category",
    flexibleTime: "Flexible time; uncheck for a fixed commitment", addLifeCalendar: "ADD TO LIFE + CALENDAR", noEvents: "No categorized Life event on this date.",
    openingHelp: "Opening amount plus manually recorded income and expenses through this date. No bank account is connected.", openingAmount: "Opening amount",
    setOpening: "SET OPENING AMOUNT", noTransactions: "No manual transactions on this date.", type: "Type", expense: "Expense", income: "Income",
    amount: "Amount", recordTransaction: "RECORD TRANSACTION", noBudgets: "No category budget recorded for this month.", monthlyAmount: "Monthly amount",
    saveBudget: "SAVE MONTHLY BUDGET", areaOffline: "AREA STATE / LOCAL SERVICE OFFLINE", areaOfflineHelp: "Start the local service to read or save real area records. Nothing here is simulated.",
    loadingState: "Loading your recorded state…", pastRecord: "PAST RECORD · READ-ONLY", futurePreparation: "FUTURE PREPARATION · NO EARLY OUTCOMES", todayReported: "TODAY · USER REPORTED",
    adjustPlaceholder: "Make the afternoon lighter…", askPlaceholder: "Ask about your day…",
    agentRoute: "AGENT ROUTE", close: "Close", confirmChange: "Confirm change", keepCurrent: "Keep current", proposedChange: "PROPOSED CHANGE",
    edgeLine1: "A calmer", edgeLine2: "brighter", edgeLine3: "you", you: "YOU",
    roomToBreathe: "Your day has room to breathe.", orchestratorHelp: "The Orchestrator consults Learning, Life, Finance, and Summary as needed—then shows you the route.",
    
    
    libraryRagHelp: "Chunked notes are retrieved through sqlite-vec and a separate local embedding model. Only saved sources can support an answer.", talkSources: "TALK ABOUT YOUR SOURCES →",
    protected: "protected",
    orchestrator: "Orchestrator", summary: "Summary", synthesis: "Synthesis", planning: "Planning", context: "Context", dispatch: "Dispatch", assessment: "Assessment", learningAgent: "Learning Agent",
    cross: "Cross-domain", sport: "Sport", social: "Social", chore: "Chore", health: "Health", other: "Other",
    addKnowledge: "ADD PRIVATE KNOWLEDGE", title: "Title", text: "Text", indexing: "Indexing locally…", indexNote: "Chunk + index note",
    findTopic: "FIND A TOPIC", topic: "Topic", fetchWeb: "Fetch from the public web even when local notes match",
    topicPrivacy: "Only the entered topic goes to Wikipedia when local knowledge has no semantic match or when you explicitly request it. Your notes and calendar never go with it.",
    searching: "Searching…", localAndWeb: "Check local + fetch public", findLocal: "Find local match", importFile: "IMPORT A LOCAL FILE",
    chooseFile: "Choose Markdown, PDF, or Word (.docx)", filePrivacy: "Text is extracted and indexed on this Mac. No file or private note is sent to the public web. Scanned PDFs need text recognition first.",
    extracting: "Extracting and indexing locally…", importSelected: "Import selected file",
    retrievedSources: "RETRIEVED SOURCES", chunk: "chunk",
    suggestionFiled: "SUGGESTION FILED", addedNotes: "Added to your notes.", dismissedSuggestion: "No problem — it’s out of the way.",
    suggestion: "SUGGESTION", keep: "Keep", dismiss: "Dismiss", high: "High", normal: "Normal", startTime: "Start",
    
    
    
    
    
    examplePlan: "Example plan, not your personal data", examplePlanHelp: "This earlier prototype day contains sample commitments and notes. Your own records remain separate.",
    
    
    
    todayOverview: "Today's execution overview", progressFor: "Progress for",
    publicFetched: "Public introduction fetched. Choose how to organize it before indexing; your local library is unchanged.", organizationIndexed: "Your chosen organization was indexed locally.",
    generalTopicNeeded: "This looks personal. Try a general topic without personal details; no public search was made.", foundLocal: "Found in your local knowledge",
    localUnavailable: "Local search unavailable; nothing was fetched", sourceAttribution: "Wikipedia source and attribution", pendingImports: "PENDING PUBLIC IMPORTS",
    reviewChoices: "review choices →", publicSource: "PUBLIC SOURCE", sourceFilterHelp: "Filtered by credibility, timeliness, then format. Last edit:",
    organizationHelp: "The choices below are organization labels. The source text is indexed without invented classification claims.", confirmImport: "CONFIRM IMPORT CHOICE",
    planBalanced: "Balanced", planFocused: "Focused", planGentle: "Gentle", plansFor: "Plans for {date}", draftsProposed: "{count} drafts · proposed by local agents", noPlanSetYet: "No plan set yet", nothingScheduledUntil: "Nothing is scheduled until you set one plan.", askDifferentPlans: "Ask for different plans", draftChip: "Draft", chosenChip: "Chosen", setChip: "Set", timeByArea: "Time by area", constraintsHeading: "Constraints", keptFixed: "Kept fixed: {items}", keptProtected: "Kept protected: {items}", notIncluded: "Not in this plan: {items}", noConstraints: "No fixed or protected tasks.", chooseName: "Choose {name}", chosenReviewBelow: "Chosen — review below", setAtTime: "Set at {time}", setTodayQuestion: "Set “{name}” as today's plan?", setDayQuestion: "Set “{name}” as the plan for {date}?", setConsequence: "{count} entries will be scheduled. Nothing counts as done until you report it. Replacing a set plan later needs a review.", keepComparing: "Keep comparing", setName: "Set {name}", planOfCount: "{index} of {count}", previousPlan: "Previous plan", nextPlan: "Next plan", plansSwitch: "Plans", readOnlyPastDay: "Read-only · past day", pastPlansHelp: "This day has passed. Its plans are kept as they were, and nothing here can change.", noPlansTitle: "No plans for this day yet", noPlansHelp: "Plans are proposed from the tasks you record for the day. Nothing is invented, and nothing is set without you.", noPlansPast: "No plan was set for this day.", loadingPlans: "Loading the plans…", agentNotesHeading: "How the agents made these plans", reviewReplacementToday: "Review a replacement for today's plan", reviewReplacementDay: "Review a replacement for {date}", underReview: "Under review", setNow: "Set now: {name}", replacementName: "Replacement: “{name}”", changeColumn: "Change", changeReported: "Reported", changeSame: "Same", changeShorter: "Shorter", changeLonger: "Longer", changeMoved: "Moved", changeRemoved: "Removed", changeAdded: "Added", staysAsReported: "{status} — stays as reported", notInThisPlan: "Not in this plan", rowsChangeNote: "Highlighted rows change. Entries you already reported keep their status in both plans.", whyAgentsPropose: "Why the agents propose this", approveReplacement: "Approve the replacement", changesCount: "{count} changes", reportedKeep: "Your {count} reported entries keep their status.", oldPlanStays: "“{name}” stays among this day's plans, no longer set.", goalsOnlyOnReport: "Goals change only when you report progress.", reviewedAll: "I've reviewed all {count} changes", reviewedNone: "I've checked that no entries change", replaceWith: "Replace with “{name}”", keepName: "Keep {name}", replaceNeedsReview: "Tick the box once you've reviewed the changes.",
    agentOrchestrator: "Orchestrator", agentLearning: "Learning agent", agentLife: "Life agent", agentFinance: "Finance agent", reviewReplaceWith: "Review replacing with {name}", planIsSet: "“{name}” is set for this day.",
    agentDetails: "What each agent considered",
    listSeparator: ", ",
    suggestionLabel: "suggestion", evidenceLabel: "Evidence:", addToDay: "Add to {day}", suggestionWaits: "Nothing is scheduled from this until you add it.", reportsLabel: "reports", reportPeriod: "Report period", periodDay: "Day", periodWeek: "Week", periodMonth: "Month", noReportYet: "No report for this period yet.", reportsNeedService: "Reports appear while the local service is running.", recordedDaysCount: "Recorded days: {count}", doneOfScheduled: "{done} of {total} done", noReportedWorkYet: "Nothing reported in this period yet.", readReport: "Read the report", adviceHeading: "Advice", noActiveAdvice: "No active advice for this period.", raisedAgain: "Raised again after you dismissed it: {content}", adviceDismissNote: "Dismissing stops an idea being used in future plans, in every period.", clearWeekOfArea: "Clear this week's {area} advice…", clearWeekQuestion: "Clear this week's {area} advice?", clearWeekConsequence: "This week's saved {area} advice and its repeat notices are deleted for good. It can't be undone. Other weeks and areas stay as they are.", clearAdviceAction: "Clear advice",
    tomorrow: "Tomorrow", yesterday: "Yesterday", inDays: "In {count} days", daysAgo: "{count} days ago", readOnlyPastBody: "You can view this day and its plan, not change them.", futureNoPlanNote: "Preset commitments are kept when plans are proposed for this day. No plan exists yet.", statusUnreported: "Unreported", asReported: "as reported", dayEmptyPast: "Nothing was recorded on this day.", dayEmptyFuture: "Nothing recorded for this day yet. Days you don't record stay empty.", openPlansAction: "Open plans", openFullDay: "Open full day", askAboutDay: "Ask about this day", openTodayAction: "Open Today", addAction: "Add", agentAccepted: "Prepared by an agent · added by you", monthGridLabel: "{month}, one button per day", cellSetOf: "plan set, {done} of {total} done", cellRecorded: "recorded, no plan set", cellRecordedShort: "Recorded", cellPresets: "{count} preset", cellSuggested: "{count} suggested by an agent", cellSuggestedShort: "Suggested", cellReadOnly: "read-only", cellEmpty: "nothing recorded", legendSet: "Set — a plan was confirmed; the bar shows entries reported done", legendRecorded: "Recorded — tasks or reports, but no plan set", legendPreset: "Preset commitments", legendSuggested: "Suggested by an agent — not yours until you add it", legendPast: "Past — read-only", legendEmpty: "Empty — nothing recorded, nothing filled in",
    clauseSeparator: ", ",
    report: "Report",
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
    life: "生活", finance: "财务", rest: "休息", library: "资料库", goals: "目标",
    localPrivate: "本地保存 · 隐私保护", 
    demoCopy: "预设目标、任务和结果与个人空间隔离。请亲自生成计划选项。",
    
    none: "未生成", draft: "草案", 
    buildItems: "根据任务生成 →", localAi: "本地 AI",
    start: "启动", ready: "就绪", askAdjust: "询问或调整今日计划 →", activeGoals: "进行中的目标",
    reviewDirection: "查看方向 →", dailyRecords: "今日任务", addItem: "+ 添加任务",
    
    
    agentBrief: "智能体简报", 
    
    noNewAdvice: "暂无新干预建议", noNewAdviceHelp: "智能体尚未发现有充分依据、需要你关注的调整。",
    
    
    
    noItems: "该日期还没有任务。", addRealTask: " 请添加真实任务或承诺。",
    linkedTo: "属于目标", independentTask: "独立任务", planned: "计划中", done: "已完成",
    partial: "部分完成", skipped: "已跳过", edit: "编辑", remove: "移除", confirmRemove: "确认移除", manageArea: "管理领域",
    
    
    
    schedule: "日程", 
    reviewReplacement: "查看替换方案",
    
    
    goalManagement: "目标管理", longerHorizon: "长期方向",
    goalsIntro: "在每个领域设定方向、关联任务，并在两个页面追踪进度。", yourGoals: "你的目标",
    recorded: "个目标", setGoal: "设定目标", whatMatters: "你想实现什么？", area: "领域", addGoal: "添加目标",
    linkedTasks: "个关联任务已完成", goalPath: "目标路径", goalTasks: "推动此目标的任务",
    noGoalTasks: "此目标还没有关联任务。", addGoalTask: "+ 为此目标添加任务",
    ordinaryTasks: "独立任务", ordinaryHelp: "不需要归属于目标，但仍值得完成的事项。",
    areaGoals: "目标及其任务", manageGoals: "管理全部目标 →", noAreaGoals: "该领域还没有目标。",
    areaState: "领域状态", dayLedger: "任务与今日计划", relatedGoal: "关联目标",
    allTasks: "全部任务", allTasksHelp: "目标任务和独立任务统一显示；关联目标的任务会标出目标及整体进度。",
    goalLinked: "推动此目标", 
    noGoal: "不关联目标 — 独立任务", taskName: "任务名称", date: "日期", time: "时间", minutes: "分钟",
    kind: "类型", repeat: "重复", details: "补充说明（可选）", addDailyItem: "添加任务",
    saveChanges: "保存修改", cancel: "取消", goalConnection: "目标关联",
    goalConnectionHelp: "将任务关联到目标，进度会同时显示在此页面和目标页面。",
    talk: "与 DAYWRIGHT 对话", talkTitle: "一起讨论。",
    ask: "询问", adjust: "调整", send: "发送消息", 
    private: "私密", consulting: "正在本地咨询相关智能体…",
    learningTitle: "学习", learningIntro: "管理学习目标、目标任务、学习主题和训练记录。",
    lifeTitle: "生活与休息", lifeIntro: "管理生活目标、目标任务、每日状态、习惯、事件和恢复。",
    moneyTitle: "财务", moneyIntro: "管理财务目标、目标任务、余额、收支和预算。",
    libraryTitle: "资料库", libraryIntro: "索引私人笔记，或输入主题进行本地优先的研究。",
    subjects: "学习主题", subjectsHelp: "主题用于整理学习方向。需要推进目标并显示在日历时，请添加关联的定时任务。",
    newSubject: "新学习主题", difficulty: "难度", estimate: "预计分钟", addSubject: "添加主题",
    sessionRecord: "学习记录", noSession: "该日期还没有学习结果记录。", subject: "学习主题",
    result: "完成情况", recordSession: "记录学习", dailyState: "每日状态",
    stateHelp: "睡眠、精力和情绪由你填写，不由智能体推断。", habits: "生活习惯",
    timedEvents: "定时事件", eventsHelp: "事件也是每日任务；日历、计划和生活页面读取同一条记录。",
    balance: "手动余额", transactions: "收支记录", budgets: "分类预算",
    savedLocal: "已在本地保存，并刷新了相关总结和日期记录。",
    previewMode: "预览模式 · 未保存", 
    localAiReady: "本地 AI 已就绪", manage: "管理 →",
    active: "进行中", paused: "已暂停", completed: "已完成", saveName: "保存名称", noGoals: "还没有目标。请添加第一个学习、生活、财务或休息目标。",
    startServiceGoals: "请启动本地服务以保存目标。", editDailyRecord: "编辑每日记录", addTo: "添加到", yourOwnData: "你的数据",
    flexibleTask: "灵活任务", fixedCommitment: "固定安排", oneTime: "单次", everyDay: "每天", everyWeek: "每周",
    protectedHelp: "即使以后要求缩短，也要尽量保留", saving: "保存中…", startServiceSave: "请启动本地服务以保存记录。",
    readOnlyHistory: "只读历史", fixed: "固定", flexible: "灵活", 
    confirmed: "已确认", 
    summaryAgent: "总结智能体", 
    
    
    
    
    previousMonth: "上个月", nextMonth: "下个月",
    
    
    
    
    
    
    
    
    
    agentWorkbench: "本地多智能体工作台",
    agentModel: "5 个智能体 · 本地 RAG + Qwen 综合处理", indexedSources: "个已索引来源", askHelp: "了解计划或权衡取舍。",
    adjustHelp: "描述要修改的内容，DayWright 会提出方案供你确认。", reportHelp: "讲述发生了什么；完成状态仍由你明确确认。",
    voiceRecording: "正在本机录音 · 再按一次麦克风结束", voiceStarting: "正在请求麦克风权限…", voiceTranscribing: "正在本地转写…",
    voiceRecognized: "文字已在本地添加 · 发送前请检查", voiceReady: "语音已就绪 · 按麦克风开始说话", voiceSetup: "本地语音运行环境需要设置",
    proposalControl: "建议不等于执行，决定权始终在你。", chooseSubject: "选择学习主题", easy: "简单", medium: "中等", hard: "困难",
    markComplete: "标记完成", reopen: "重新打开", noSubjects: "还没有学习主题。", futureSessions: "未来的学习结果不能提前汇报。",
    sleepHours: "睡眠 / 小时", energy: "精力 / 1–5", mood: "情绪 / 1–5", notReported: "未汇报", reflection: "回顾",
    saveDaily: "保存每日状态", noNote: "无备注", noHabits: "还没有习惯记录。", newHabit: "新习惯", frequency: "频率", daily: "每天",
    weekly: "每周", addHabit: "添加习惯", reportHabit: "汇报习惯", chooseHabit: "选择习惯", outcome: "结果", notDone: "未完成",
    note: "备注", saveHabit: "保存习惯记录", pause: "暂停", resume: "恢复", eventName: "事件名称", end: "结束", category: "分类",
    flexibleTime: "时间可调整；取消勾选则为固定安排", addLifeCalendar: "添加到生活与日历", noEvents: "该日期没有分类的生活事件。",
    openingHelp: "余额由初始金额加上截至所选日期手动记录的收入和支出组成，未连接银行账户。", openingAmount: "初始金额", setOpening: "设置初始金额",
    noTransactions: "该日期没有手动收支记录。", type: "类型", expense: "支出", income: "收入", amount: "金额", recordTransaction: "记录收支",
    noBudgets: "本月还没有分类预算。", monthlyAmount: "每月金额", saveBudget: "保存月度预算", areaOffline: "领域状态 / 本地服务离线",
    areaOfflineHelp: "请启动本地服务以读取或保存真实领域记录。这里不会模拟数据。", loadingState: "正在载入已记录状态…",
    pastRecord: "过去记录 · 只读", futurePreparation: "未来准备 · 不能提前汇报结果", todayReported: "今日 · 用户汇报",
    adjustPlaceholder: "让下午轻松一点……", askPlaceholder: "询问今天的安排……", agentRoute: "智能体协作路径",
    close: "关闭", confirmChange: "确认修改", keepCurrent: "保持当前安排", proposedChange: "建议修改", edgeLine1: "更从容",
    edgeLine2: "更明亮", edgeLine3: "成为更好的你", you: "你", roomToBreathe: "今天的安排留有呼吸空间。",
    orchestratorHelp: "协调智能体会按需咨询学习、生活、财务和总结智能体，并展示协作路径。", 
    
    libraryRagHelp: "笔记会被分块，并通过 sqlite-vec 和独立的本地嵌入模型检索。回答只能引用已保存来源。", talkSources: "讨论你的资料 →",
    protected: "受到保护", orchestrator: "协调智能体",
    summary: "总结", synthesis: "综合", planning: "规划", context: "上下文", dispatch: "分派", assessment: "评估", learningAgent: "学习智能体", cross: "跨领域",
    sport: "运动", social: "社交", chore: "家务", health: "健康", other: "其他",
    addKnowledge: "添加私人资料", title: "标题", text: "内容", indexing: "正在本地索引…", indexNote: "分块并索引笔记",
    findTopic: "查找主题", topic: "主题", fetchWeb: "即使本地笔记匹配，也从公开网络获取",
    topicPrivacy: "仅在本地没有语义匹配或你明确要求时，输入的主题才会发送到 Wikipedia；你的笔记和日历不会一并发送。",
    searching: "正在搜索…", localAndWeb: "检查本地并获取公开资料", findLocal: "查找本地匹配", importFile: "导入本地文件",
    chooseFile: "选择 Markdown、PDF 或 Word（.docx）", filePrivacy: "文本会在这台 Mac 上提取和索引，不会把文件或私人笔记发送到公开网络。扫描版 PDF 需要先进行文字识别。",
    extracting: "正在本地提取并索引…", importSelected: "导入所选文件",
    retrievedSources: "检索到的来源", chunk: "分块", suggestionFiled: "建议已处理",
    addedNotes: "已添加到你的笔记。", dismissedSuggestion: "好的，已移除此建议。", suggestion: "建议", keep: "保留", dismiss: "忽略",
    high: "高", normal: "普通", startTime: "开始", 
    
    
    
    
    examplePlan: "样例计划，不是你的个人数据", examplePlanHelp: "这是早期原型中的样例安排和备注，你自己的记录与其完全分开。",
    
    
    
    todayOverview: "今日执行概览", progressFor: "进度",
    publicFetched: "已获取公开简介。请先选择整理方式再索引；本地资料库尚未改变。", organizationIndexed: "所选整理方式已在本地完成索引。",
    generalTopicNeeded: "这个主题似乎涉及个人信息。请改用不含个人详情的一般主题；尚未进行公开搜索。", foundLocal: "已在本地资料中找到",
    localUnavailable: "本地搜索不可用，未获取任何内容", sourceAttribution: "Wikipedia 来源与署名", pendingImports: "待处理的公开资料导入",
    reviewChoices: "查看选项 →", publicSource: "公开来源", sourceFilterHelp: "按可信度、时效性和格式筛选。最后编辑：",
    organizationHelp: "下方选项是整理标签，来源文本会被索引，但不会添加未经验证的分类结论。", confirmImport: "确认导入选项",
    planBalanced: "均衡", planFocused: "专注", planGentle: "从容", plansFor: "{date}的计划", draftsProposed: "{count} 份草案 · 由本地智能体提出", noPlanSetYet: "尚未确定计划", nothingScheduledUntil: "确定一份计划之前，不会安排任何事项。", askDifferentPlans: "请求其他方案", draftChip: "草案", chosenChip: "已选", setChip: "已确定", timeByArea: "各领域时间", constraintsHeading: "约束", keptFixed: "保持固定：{items}", keptProtected: "保持受保护：{items}", notIncluded: "未纳入此方案：{items}", noConstraints: "没有固定或受保护的任务。", chooseName: "选择{name}", chosenReviewBelow: "已选——请在下方确认", setAtTime: "{time} 已确定", setTodayQuestion: "将“{name}”确定为今天的计划？", setDayQuestion: "将“{name}”确定为{date}的计划？", setConsequence: "将安排 {count} 个条目。在你报告之前，没有任何事项算作完成。之后替换已确定的计划需要先审阅。", keepComparing: "继续比较", setName: "确定{name}", planOfCount: "第 {index} 份，共 {count} 份", previousPlan: "上一份方案", nextPlan: "下一份方案", plansSwitch: "方案", readOnlyPastDay: "只读 · 已过去的日期", pastPlansHelp: "这一天已经过去。它的计划保持原样，这里无法更改。", noPlansTitle: "这一天还没有计划", noPlansHelp: "方案根据你为这一天记录的任务提出。不会凭空编造，也不会未经你同意就确定。", noPlansPast: "这一天没有确定过计划。", loadingPlans: "正在载入方案…", agentNotesHeading: "智能体如何拟定这些方案", reviewReplacementToday: "审阅今天计划的替换方案", reviewReplacementDay: "审阅{date}的替换方案", underReview: "审阅中", setNow: "当前确定：{name}", replacementName: "替换方案：“{name}”", changeColumn: "变化", changeReported: "已报告", changeSame: "不变", changeShorter: "缩短", changeLonger: "延长", changeMoved: "移动", changeRemoved: "移除", changeAdded: "新增", staysAsReported: "{status}——保持已报告状态", notInThisPlan: "不在此方案中", rowsChangeNote: "高亮的行会变化。你已报告的条目在两份方案中都保持其状态。", whyAgentsPropose: "智能体为何提出此方案", approveReplacement: "批准替换", changesCount: "{count} 处变化", reportedKeep: "你已报告的 {count} 个条目保持其状态。", oldPlanStays: "“{name}”仍保留在这一天的方案中，但不再是确定的计划。", goalsOnlyOnReport: "只有你报告进度时，目标才会变化。", reviewedAll: "我已审阅全部 {count} 处变化", reviewedNone: "我已确认没有条目变化", replaceWith: "替换为“{name}”", keepName: "保留{name}", replaceNeedsReview: "审阅变化后请勾选上方选项。",
    agentOrchestrator: "协调", agentLearning: "学习智能体", agentLife: "生活智能体", agentFinance: "财务智能体", reviewReplaceWith: "审阅替换为{name}", planIsSet: "“{name}”已确定为这一天的计划。",
    agentDetails: "各智能体考虑了什么",
    listSeparator: "、",
    suggestionLabel: "建议", evidenceLabel: "依据：", addToDay: "添加到{day}", suggestionWaits: "在你添加之前，不会据此安排任何事项。", reportsLabel: "报告", reportPeriod: "报告周期", periodDay: "日", periodWeek: "周", periodMonth: "月", noReportYet: "这个周期还没有报告。", reportsNeedService: "本地服务运行时才会显示报告。", recordedDaysCount: "已记录天数：{count}", doneOfScheduled: "完成 {done} / {total}", noReportedWorkYet: "这个周期还没有报告任何事项。", readReport: "阅读报告", adviceHeading: "建议", noActiveAdvice: "这个周期没有有效建议。", raisedAgain: "你忽略后再次提出：{content}", adviceDismissNote: "忽略后，这条建议不会再用于任何周期的后续计划。", clearWeekOfArea: "清除本周的{area}建议…", clearWeekQuestion: "清除本周的{area}建议？", clearWeekConsequence: "本周已保存的{area}建议及其重复提示将被永久删除，且无法撤销。其他周和其他领域不受影响。", clearAdviceAction: "清除建议",
    tomorrow: "明天", yesterday: "昨天", inDays: "{count} 天后", daysAgo: "{count} 天前", readOnlyPastBody: "你可以查看这一天及其计划，但不能更改。", futureNoPlanNote: "为这一天提出方案时会保留预设安排。目前还没有计划。", statusUnreported: "未报告", asReported: "按你的报告", dayEmptyPast: "这一天没有任何记录。", dayEmptyFuture: "这一天还没有记录。你不记录的日子会保持空白。", openPlansAction: "打开方案", openFullDay: "查看完整的一天", askAboutDay: "询问这一天", openTodayAction: "打开今天", addAction: "添加", agentAccepted: "由智能体准备 · 由你添加", monthGridLabel: "{month}，每天一个按钮", cellSetOf: "计划已确定，完成 {done} / {total}", cellRecorded: "有记录，未确定计划", cellRecordedShort: "有记录", cellPresets: "预设 {count} 项", cellSuggested: "智能体建议 {count} 项", cellSuggestedShort: "建议", cellReadOnly: "只读", cellEmpty: "无记录", legendSet: "已确定——计划已确认；进度条显示已报告完成的条目", legendRecorded: "有记录——有任务或报告，但未确定计划", legendPreset: "预设安排", legendSuggested: "智能体建议——在你添加之前不属于你", legendPast: "过去——只读", legendEmpty: "空白——没有记录，也不会被填充",
    clauseSeparator: "，",
    report: "汇报",
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
