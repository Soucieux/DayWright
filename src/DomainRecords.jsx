import { useEffect, useState } from "react";
import { api } from "./api";

/** Convert an entered decimal money amount to exact integer cents for the local API. */
function enteredCents(value, allowNegative = false) {
  const entered = value.trim();
  if (!new RegExp(allowNegative ? "^-?\\d+(?:\\.\\d{1,2})?$" : "^\\d+(?:\\.\\d{1,2})?$").test(entered)) {
    throw new Error("Enter a money amount with no more than two decimal places.");
  }
  const negative = entered.startsWith("-");
  const [whole, fraction = ""] = (negative ? entered.slice(1) : entered).split(".");
  const cents = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
  if (!Number.isSafeInteger(cents)) throw new Error("This money amount is too large.");
  return negative ? -cents : cents;
}

/** Render an integer-cent amount without binary floating-point rounding on entry. */
function money(cents) {
  const sign = cents < 0 ? "−" : "";
  const amount = Math.abs(cents);
  return `${sign}${Math.floor(amount / 100).toLocaleString()}.${String(amount % 100).padStart(2, "0")}`;
}

/** Show Learning subjects and explicitly reported sessions for the selected day. */
function LearningRecords({ data, date, today, disabled, mutate }) {
  const [title, setTitle] = useState("");
  const [difficulty, setDifficulty] = useState("medium");
  const [estimate, setEstimate] = useState("30");
  const [itemId, setItemId] = useState("");
  const [minutes, setMinutes] = useState("30");
  const [result, setResult] = useState("done");
  const active = data.items.filter((item) => item.status === "active");
  const canCatalog = !disabled && date >= today;
  const canReport = !disabled && date === today;
  return <div className="area-state-grid">
    <section className="area-state-sheet"><small>LEARNING / SUBJECTS</small>
      <p>Subjects are a catalog. Add a timed task separately when you want one on Calendar.</p>
      {data.items.length ? data.items.map((item) => <div className="area-record-line" key={item.id}>
        <span><strong>{item.title}</strong><small>{item.difficulty} · {item.estimatedMinutes} min estimate · {item.status}</small></span>
        {canCatalog && <button type="button" onClick={() => mutate(`/api/learning/items/${item.id}`, "PATCH", { status: item.status === "active" ? "done" : "active" })}>{item.status === "active" ? "MARK COMPLETE" : "REOPEN"}</button>}
      </div>) : <p className="empty-copy">No learning subject recorded yet.</p>}
      {canCatalog && <form onSubmit={(event) => { event.preventDefault(); mutate("/api/learning/items", "POST", { title, difficulty, estimatedMinutes: Number(estimate) }).then((saved) => saved && setTitle("")); }}>
        <label>New subject<input value={title} onChange={(event) => setTitle(event.target.value)} maxLength="200" required placeholder="French pronunciation" /></label>
        <div className="area-form-pair"><label>Difficulty<select value={difficulty} onChange={(event) => setDifficulty(event.target.value)}><option value="easy">Easy</option><option value="medium">Medium</option><option value="hard">Hard</option></select></label>
          <label>Estimate / min<input type="number" min="1" max="1440" value={estimate} onChange={(event) => setEstimate(event.target.value)} required /></label></div>
        <button disabled={!title.trim()}>ADD SUBJECT</button>
      </form>}
    </section>
    <section className="area-state-sheet"><small>{date} / SESSION RECORD</small>
      {data.sessions.length ? data.sessions.map((session) => <div className="area-record-line" key={session.id}><span><strong>{session.itemTitle}</strong><small>{session.minutes} min · {session.result}</small></span></div>) : <p className="empty-copy">No session outcome recorded for this date.</p>}
      {canReport && <form onSubmit={(event) => { event.preventDefault(); mutate("/api/learning/sessions", "POST", { date, itemId, minutes: Number(minutes), result }); }}>
        <label>Subject<select value={itemId} onChange={(event) => setItemId(event.target.value)} required><option value="">Choose a subject</option>{active.map((item) => <option value={item.id} key={item.id}>{item.title}</option>)}</select></label>
        <div className="area-form-pair"><label>Minutes<input type="number" min="1" max="1440" value={minutes} onChange={(event) => setMinutes(event.target.value)} required /></label>
          <label>Reported result<select value={result} onChange={(event) => setResult(event.target.value)}><option value="done">Done</option><option value="partial">Partial</option><option value="skipped">Skipped</option></select></label></div>
        <button disabled={!itemId}>RECORD SESSION</button>
      </form>}
      {date > today && <p className="empty-copy">Future sessions cannot be reported early.</p>}
    </section>
  </div>;
}

/** Show explicit Life check-ins, habit reports, and Calendar-linked timed events. */
function LifeRecords({ data, date, today, disabled, mutate }) {
  const [daily, setDaily] = useState({ sleepHours: "", energyLevel: "", mood: "", note: "" });
  const [habitTitle, setHabitTitle] = useState("");
  const [frequency, setFrequency] = useState("daily");
  const [habitId, setHabitId] = useState("");
  const [habitDone, setHabitDone] = useState(true);
  const [habitNote, setHabitNote] = useState("");
  const [event, setEvent] = useState({ title: "", startTime: "09:00", endTime: "10:00", category: "other", flexible: true });
  useEffect(() => { setDaily({ sleepHours: data.daily?.sleepHours ?? "", energyLevel: data.daily?.energyLevel ?? "", mood: data.daily?.mood ?? "", note: data.daily?.note ?? "" }); }, [date, data.daily]);
  const canCatalog = !disabled && date >= today;
  const canReport = !disabled && date === today;
  const active = data.habits.filter((habit) => habit.active);
  return <div className="area-state-grid">
    <section className="area-state-sheet"><small>{date} / DAILY STATE</small>
      <p>Sleep, energy, and mood are your reports—not inferred by an agent.</p>
      {data.daily && <div className="area-record-line"><span><strong>{data.daily.sleepHours ?? "—"}h sleep · energy {data.daily.energyLevel ?? "—"}/5 · mood {data.daily.mood ?? "—"}/5</strong><small>{data.daily.note || "No note"}</small></span></div>}
      {canReport && <form onSubmit={(submit) => { submit.preventDefault(); mutate(`/api/life/daily/${date}`, "PUT", { sleepHours: daily.sleepHours === "" ? null : Number(daily.sleepHours), energyLevel: daily.energyLevel === "" ? null : Number(daily.energyLevel), mood: daily.mood === "" ? null : Number(daily.mood), note: daily.note }); }}>
        <div className="area-form-triple"><label>Sleep / hours<input type="number" min="0" max="24" step="0.25" value={daily.sleepHours} onChange={(input) => setDaily({ ...daily, sleepHours: input.target.value })} /></label>
          <label>Energy / 1–5<select value={daily.energyLevel} onChange={(input) => setDaily({ ...daily, energyLevel: input.target.value })}><option value="">Not reported</option>{[1,2,3,4,5].map((level) => <option key={level}>{level}</option>)}</select></label>
          <label>Mood / 1–5<select value={daily.mood} onChange={(input) => setDaily({ ...daily, mood: input.target.value })}><option value="">Not reported</option>{[1,2,3,4,5].map((level) => <option key={level}>{level}</option>)}</select></label></div>
        <label>Reflection<textarea value={daily.note} maxLength="1000" onChange={(input) => setDaily({ ...daily, note: input.target.value })} placeholder="What affected your day?" /></label>
        <button>SAVE DAILY STATE</button>
      </form>}
    </section>
    <section className="area-state-sheet"><small>LIFE / HABITS</small>
      {data.habits.length ? data.habits.map((habit) => <div className="area-record-line" key={habit.id}><span><strong>{habit.title}</strong><small>{habit.frequency} · {habit.active ? "active" : "paused"}{data.logs.find((log) => log.habitId === habit.id) && ` · ${data.logs.find((log) => log.habitId === habit.id).done ? "done" : "not done"} on ${date}`}</small></span>{canCatalog && <button type="button" onClick={() => mutate(`/api/life/habits/${habit.id}`, "PATCH", { active: !habit.active })}>{habit.active ? "PAUSE" : "RESUME"}</button>}</div>) : <p className="empty-copy">No habits recorded yet.</p>}
      {canCatalog && <form onSubmit={(submit) => { submit.preventDefault(); mutate("/api/life/habits", "POST", { title: habitTitle, frequency }).then((saved) => saved && setHabitTitle("")); }}><label>New habit<input required maxLength="200" value={habitTitle} onChange={(input) => setHabitTitle(input.target.value)} placeholder="Evening walk" /></label><label>Frequency<select value={frequency} onChange={(input) => setFrequency(input.target.value)}><option value="daily">Daily</option><option value="weekly">Weekly</option></select></label><button disabled={!habitTitle.trim()}>ADD HABIT</button></form>}
      {canReport && <form onSubmit={(submit) => { submit.preventDefault(); mutate(`/api/life/habits/${habitId}/logs/${date}`, "PUT", { done: habitDone, note: habitNote }); }}><label>Report habit<select required value={habitId} onChange={(input) => setHabitId(input.target.value)}><option value="">Choose a habit</option>{active.map((habit) => <option value={habit.id} key={habit.id}>{habit.title}</option>)}</select></label><label>Outcome<select value={habitDone ? "done" : "not_done"} onChange={(input) => setHabitDone(input.target.value === "done")}><option value="done">Done</option><option value="not_done">Not done</option></select></label><label>Note<input maxLength="1000" value={habitNote} onChange={(input) => setHabitNote(input.target.value)} /></label><button disabled={!habitId}>SAVE HABIT REPORT</button></form>}
    </section>
    <section className="area-state-sheet area-state-wide"><small>{date} / TIMED EVENTS</small>
      <p>Events are also daily items: Calendar, Plans, and the Life ledger read the same record.</p>
      {data.events.length ? data.events.map((entry) => <div className="area-record-line" key={entry.id}><span><strong>{entry.startTime} · {entry.title}</strong><small>{entry.category} · {entry.durationMinutes} min · {entry.constraintKind}</small></span></div>) : <p className="empty-copy">No categorized Life event on this date.</p>}
      {canCatalog && <form onSubmit={(submit) => { submit.preventDefault(); mutate("/api/life/events", "POST", { date, ...event }).then((saved) => saved && setEvent({ ...event, title: "" })); }}><label>Event name<input maxLength="200" required value={event.title} onChange={(input) => setEvent({ ...event, title: input.target.value })} placeholder="Gym appointment" /></label><div className="area-form-triple"><label>Start<input type="time" required value={event.startTime} onChange={(input) => setEvent({ ...event, startTime: input.target.value })} /></label><label>End<input type="time" required value={event.endTime} onChange={(input) => setEvent({ ...event, endTime: input.target.value })} /></label><label>Category<select value={event.category} onChange={(input) => setEvent({ ...event, category: input.target.value })}>{["sport","social","chore","health","other"].map((value) => <option key={value} value={value}>{value}</option>)}</select></label></div><label className="area-check"><input type="checkbox" checked={event.flexible} onChange={(input) => setEvent({ ...event, flexible: input.target.checked })} /> Flexible time; uncheck for a fixed commitment</label><button disabled={!event.title.trim()}>ADD TO LIFE + CALENDAR</button></form>}
    </section>
  </div>;
}

/** Show a manual Money balance, recorded transactions, and dated budgets. */
function MoneyRecords({ data, date, today, disabled, mutate }) {
  const [opening, setOpening] = useState("");
  const [transaction, setTransaction] = useState({ type: "expense", amount: "", category: "", note: "" });
  const [budget, setBudget] = useState({ amount: "", category: "" });
  useEffect(() => { setOpening((data.openingBalanceCents / 100).toFixed(2)); }, [data.openingBalanceCents]);
  const canCatalog = !disabled && date >= today;
  const canReport = !disabled && date === today;
  return <div className="area-state-grid">
    <section className="area-state-sheet"><small>MONEY / MANUAL BALANCE</small><strong className="area-money-figure">{money(data.balanceCents)}</strong><p>Opening amount plus manually recorded income and expenses through {date}. No bank account is connected.</p>
      {canCatalog && <form onSubmit={(submit) => { submit.preventDefault(); try { mutate("/api/money/opening-balance", "PUT", { cents: enteredCents(opening, true) }); } catch (error) { mutate(null, null, null, error.message); } }}><label>Opening amount<input inputMode="decimal" value={opening} onChange={(input) => setOpening(input.target.value)} required /></label><button>SET OPENING AMOUNT</button></form>}
    </section>
    <section className="area-state-sheet"><small>{date} / TRANSACTIONS</small>
      {data.transactions.length ? data.transactions.map((entry) => <div className="area-record-line" key={entry.id}><span><strong>{entry.type === "expense" ? "−" : "+"}{money(entry.amountCents)} · {entry.category}</strong><small>{entry.note || "No note"}</small></span></div>) : <p className="empty-copy">No manual transactions on this date.</p>}
      {canReport && <form onSubmit={(submit) => { submit.preventDefault(); try { mutate("/api/money/transactions", "POST", { date, type: transaction.type, amountCents: enteredCents(transaction.amount), category: transaction.category, note: transaction.note }).then((saved) => saved && setTransaction({ ...transaction, amount: "", note: "" })); } catch (error) { mutate(null, null, null, error.message); } }}><div className="area-form-pair"><label>Type<select value={transaction.type} onChange={(input) => setTransaction({ ...transaction, type: input.target.value })}><option value="expense">Expense</option><option value="income">Income</option></select></label><label>Amount<input inputMode="decimal" required value={transaction.amount} onChange={(input) => setTransaction({ ...transaction, amount: input.target.value })} placeholder="12.50" /></label></div><label>Category<input required maxLength="100" value={transaction.category} onChange={(input) => setTransaction({ ...transaction, category: input.target.value })} placeholder="Groceries" /></label><label>Note<input maxLength="1000" value={transaction.note} onChange={(input) => setTransaction({ ...transaction, note: input.target.value })} /></label><button disabled={!transaction.amount || !transaction.category.trim()}>RECORD TRANSACTION</button></form>}
    </section>
    <section className="area-state-sheet area-state-wide"><small>{date.slice(0,7)} / CATEGORY BUDGETS</small>
      {data.budgets.length ? data.budgets.map((entry) => <div className="area-record-line" key={entry.id}><span><strong>{entry.category}</strong><small>{money(entry.spentCents)} spent / {money(entry.budgetCents)} saved budget{entry.spentCents > entry.budgetCents && " · OVER BUDGET"}</small></span></div>) : <p className="empty-copy">No category budget recorded for this month.</p>}
      {canCatalog && <form onSubmit={(submit) => { submit.preventDefault(); try { mutate("/api/money/budgets", "PUT", { month: date.slice(0,7), category: budget.category, budgetCents: enteredCents(budget.amount) }).then((saved) => saved && setBudget({ ...budget, amount: "" })); } catch (error) { mutate(null, null, null, error.message); } }}><div className="area-form-pair"><label>Category<input required maxLength="100" value={budget.category} onChange={(input) => setBudget({ ...budget, category: input.target.value })} placeholder="Groceries" /></label><label>Monthly amount<input inputMode="decimal" required value={budget.amount} onChange={(input) => setBudget({ ...budget, amount: input.target.value })} placeholder="250.00" /></label></div><button disabled={!budget.category.trim() || !budget.amount}>SAVE MONTHLY BUDGET</button></form>}
    </section>
  </div>;
}

/** Load and mutate only the selected area's records; parent reload keeps Summary/Calendar in sync. */
export function DomainRecordsBoard({ domain, date, today, backendConnected, onSaved }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let live = true;
    setData(null);
    setError("");
    setNotice("");
    if (backendConnected) api(`/api/areas/${domain}?${new URLSearchParams({ date })}`)
      .then((result) => live && setData(result))
      .catch((caught) => live && setError(caught.message));
    return () => { live = false; };
  }, [domain, date, backendConnected]);

  async function mutate(path, method, body, localError = null) {
    if (localError) { setError(localError); return false; }
    if (!path || !backendConnected || busy) return false;
    setError(""); setNotice(""); setBusy(true);
    try {
      await api(path, { method, body: JSON.stringify(body) });
      setData(await api(`/api/areas/${domain}?${new URLSearchParams({ date })}`));
      await onSaved();
      setNotice("Saved locally. Related summaries and dated ledgers have been refreshed.");
      return true;
    } catch (caught) { setError(caught.message); return false; }
    finally { setBusy(false); }
  }

  if (!backendConnected) return <section className="area-state-offline"><small>AREA STATE / LOCAL SERVICE OFFLINE</small><p>Start the local service to read or save real area records. Nothing here is simulated.</p></section>;
  if (!data) return <section className="area-state-offline"><small>AREA STATE</small><p>{error || "Loading your recorded state…"}</p></section>;
  return <div className="area-state-board" aria-busy={busy}>
    <div className="section-line"><small>{domain.toUpperCase()} STATE / {date}</small><span>{date < today ? "PAST RECORD · READ-ONLY" : date > today ? "FUTURE PREPARATION · NO EARLY OUTCOMES" : "TODAY · USER REPORTED"}</span></div>
    {error && <p className="area-state-error" role="alert">{error}</p>}{notice && <p className="area-state-notice" role="status">{notice}</p>}
    {domain === "learning" && <LearningRecords data={data} date={date} today={today} disabled={busy} mutate={mutate} />}
    {domain === "life" && <LifeRecords data={data} date={date} today={today} disabled={busy} mutate={mutate} />}
    {domain === "finance" && <MoneyRecords data={data} date={date} today={today} disabled={busy} mutate={mutate} />}
  </div>;
}
