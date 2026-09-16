const baseEntries = [
  ["08:00", "French listening", "Podcast + notes (Beginner A2)", "learning", 60, "flexible"],
  ["09:00", "Deep work — Course project", "Build section 2 and write notes", "learning", 90, "flexible"],
  ["10:30", "Strength session", "Gym · Full body", "life", 60, "fixed"],
  ["11:30", "Shower & clear inbox", "Tidy up and prep for afternoon", "life", 30, "flexible"],
  ["12:00", "Lunch", "Good food, short walk", "life", 60, "flexible"],
  ["13:00", "Budget review", "Check spending, update categories", "finance", 45, "flexible"],
  ["14:00", "Open buffer", "Use for catch-up or personal task", "life", 90, "flexible"],
  ["15:30", "Course project", "Continue build + polish", "learning", 90, "flexible"],
  ["17:00", "Prepare for call", "Review notes and agenda", "life", 30, "flexible"],
  ["17:30", "Call with Alex", "Project sync", "life", 60, "fixed"],
  ["18:30", "Evening reset", "Journal, plan tomorrow, wind down", "rest", 30, "flexible"],
];

function makeEntries(slug) {
  return baseEntries.map(([start_time, title, detail, domain, duration_minutes, constraint_kind], index) => {
    const entry = {
      id: `sample-entry-${index}`,
      start_time,
      title,
      detail,
      domain,
      duration_minutes,
      constraint_kind,
      completion_status: "planned",
    };

    if (slug === "focused" && title === "Open buffer") {
      return { ...entry, title: "Focused build block", detail: "Finish the hardest course milestone", domain: "learning" };
    }
    if (slug === "focused" && title === "Course project") {
      return { ...entry, duration_minutes: 75 };
    }
    if (slug === "gentle" && title === "Deep work — Course project") {
      return { ...entry, detail: "One clear milestone, then stop", duration_minutes: 60 };
    }
    if (slug === "gentle" && title === "Open buffer") {
      return { ...entry, title: "Recovery buffer", detail: "Walk, errands, or unplanned needs", duration_minutes: 120 };
    }
    if (slug === "gentle" && title === "Course project") {
      return { ...entry, start_time: "16:00", title: "Light course review", detail: "Review notes; no new build work", duration_minutes: 60 };
    }
    return entry;
  });
}

function balanceFor(entries) {
  return entries.reduce(
    (totals, entry) => ({ ...totals, [entry.domain]: totals[entry.domain] + entry.duration_minutes }),
    { learning: 0, life: 0, finance: 0, rest: 0 },
  );
}

export function sampleVariant(slug) {
  const entries = makeEntries(slug);
  return { entries, balance: balanceFor(entries) };
}

const balancedSample = sampleVariant("balanced");

export const sampleDay = {
  date: "2026-09-14",
  planSetId: "sample-set",
  selectedVariantId: "sample-balanced",
  confirmedVariantId: null,
  confirmedAt: null,
  variants: [
    {
      id: "sample-balanced",
      name: "Balanced",
      slug: "balanced",
      rationale: "Steady progress across learning, life, and money with a protected buffer.",
      version: 1,
    },
    {
      id: "sample-focused",
      name: "Focused",
      slug: "focused",
      rationale: "Uses the open buffer for the course milestone while preserving fixed commitments.",
      version: 1,
    },
    {
      id: "sample-gentle",
      name: "Gentle",
      slug: "gentle",
      rationale: "Shortens deep work and protects more recovery time for a lower-energy day.",
      version: 1,
    },
  ],
  entries: balancedSample.entries,
  balance: balancedSample.balance,
  suggestion: {
    id: "sample-suggestion",
    title: "Try a 10-minute walk after lunch.",
    detail: "A short walk can restore energy and focus for the afternoon.",
    decision: null,
  },
  hardConstraints: [
    "Call with Alex at 17:30 (fixed)",
    "Gym closes at 12:00",
    "Keep at least 30 minutes for evening reset",
    "Personal spending review today",
  ],
  plannerNotes: [
    "Energy is 3/5, so deep work ends by 16:00.",
    "7h 20m sleep supports a moderate training block.",
  ],
  messages: [],
  agents: [
    ["orchestrator", "Orchestrator", "cross-domain", true],
    ["learning", "Learning", "learning", false],
    ["life", "Life", "life", false],
    ["finance", "Finance", "finance", false],
    ["summary", "Summary", "cross-domain", false],
  ].map(([key, label, domain, mayProposePlan]) => ({ key, label, domain, mayProposePlan })),
  model: {
    state: "available",
    running: false,
    runtimeAvailable: true,
    chatModelAvailable: true,
    embeddingModelAvailable: true,
    voiceModelAvailable: true,
    label: "Qwen3 4B · on this Mac",
  },
  rag: {
    vectorStore: {
      engine: "sqlite-vec",
      engineVersion: "preview",
      sourceCount: 0,
      chunkCount: 0,
      dimensions: 1024,
    },
    embeddingModel: {
      state: "available",
      running: false,
      modelAvailable: true,
      runtimeAvailable: true,
      label: "Qwen3 Embedding 0.6B · on this Mac",
      dimensions: 1024,
    },
  },
};
