import { useEffect, useState } from "react";
import { api } from "./api";
import { useI18n } from "./i18n";

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
function LearningRecords({ data, date, today, disabled, mutate, demoMode }) {
  const { t, demoText } = useI18n();
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
    <section className="area-state-sheet"><small>{t("subjects")}</small>
      <p>{t("subjectsHelp")}</p>
      {data.items.length ? data.items.map((item) => <div className="area-record-line" key={item.id}>
        <span><strong>{demoMode ? demoText(item.title) : item.title}</strong><small>{t(item.difficulty)} · {item.estimatedMinutes} {t("minutes")} · {t(item.status)}</small></span>
        {canCatalog && <button type="button" onClick={() => mutate(`/api/learning/items/${item.id}`, "PATCH", { status: item.status === "active" ? "done" : "active" })}>{item.status === "active" ? t("markComplete") : t("reopen")}</button>}
      </div>) : <p className="empty-copy">{t("noSubjects")}</p>}
      {canCatalog && <form onSubmit={(event) => { event.preventDefault(); mutate("/api/learning/items", "POST", { title, difficulty, estimatedMinutes: Number(estimate) }).then((saved) => saved && setTitle("")); }}>
        <label>{t("newSubject")}<input value={title} onChange={(event) => setTitle(event.target.value)} maxLength="200" required /></label>
        <div className="area-form-pair"><label>{t("difficulty")}<select value={difficulty} onChange={(event) => setDifficulty(event.target.value)}><option value="easy">{t("easy")}</option><option value="medium">{t("medium")}</option><option value="hard">{t("hard")}</option></select></label>
          <label>{t("estimate")}<input type="number" min="1" max="1440" value={estimate} onChange={(event) => setEstimate(event.target.value)} required /></label></div>
        <button disabled={!title.trim()}>{t("addSubject")}</button>
      </form>}
    </section>
    <section className="area-state-sheet"><small>{date} / {t("sessionRecord")}</small>
      {data.sessions.length ? data.sessions.map((session) => <div className="area-record-line" key={session.id}><span><strong>{demoMode ? demoText(session.itemTitle) : session.itemTitle}</strong><small>{session.minutes} {t("minutes")} · {t(session.result)}</small></span></div>) : <p className="empty-copy">{t("noSession")}</p>}
      {canReport && <form onSubmit={(event) => { event.preventDefault(); mutate("/api/learning/sessions", "POST", { date, itemId, minutes: Number(minutes), result }); }}>
        <label>{t("subject")}<select value={itemId} onChange={(event) => setItemId(event.target.value)} required><option value="">{t("chooseSubject")}</option>{active.map((item) => <option value={item.id} key={item.id}>{demoMode ? demoText(item.title) : item.title}</option>)}</select></label>
        <div className="area-form-pair"><label>{t("minutes")}<input type="number" min="1" max="1440" value={minutes} onChange={(event) => setMinutes(event.target.value)} required /></label>
          <label>{t("result")}<select value={result} onChange={(event) => setResult(event.target.value)}><option value="done">{t("done")}</option><option value="partial">{t("partial")}</option><option value="skipped">{t("skipped")}</option></select></label></div>
        <button disabled={!itemId}>{t("recordSession")}</button>
      </form>}
      {date > today && <p className="empty-copy">{t("futureSessions")}</p>}
    </section>
  </div>;
}

/** Show explicit Life check-ins, habit reports, and Calendar-linked timed events. */
function LifeRecords({ data, date, today, disabled, mutate, demoMode }) {
  const { t, demoText } = useI18n();
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
    <section className="area-state-sheet"><small>{date} / {t("dailyState")}</small>
      <p>{t("stateHelp")}</p>
      {data.daily && <div className="area-record-line"><span><strong>{data.daily.sleepHours ?? "—"}h · {t("energy")} {data.daily.energyLevel ?? "—"}/5 · {t("mood")} {data.daily.mood ?? "—"}/5</strong><small>{data.daily.note ? (demoMode ? demoText(data.daily.note) : data.daily.note) : t("noNote")}</small></span></div>}
      {canReport && <form onSubmit={(submit) => { submit.preventDefault(); mutate(`/api/life/daily/${date}`, "PUT", { sleepHours: daily.sleepHours === "" ? null : Number(daily.sleepHours), energyLevel: daily.energyLevel === "" ? null : Number(daily.energyLevel), mood: daily.mood === "" ? null : Number(daily.mood), note: daily.note }); }}>
        <div className="area-form-triple"><label>{t("sleepHours")}<input type="number" min="0" max="24" step="0.25" value={daily.sleepHours} onChange={(input) => setDaily({ ...daily, sleepHours: input.target.value })} /></label>
          <label>{t("energy")}<select value={daily.energyLevel} onChange={(input) => setDaily({ ...daily, energyLevel: input.target.value })}><option value="">{t("notReported")}</option>{[1,2,3,4,5].map((level) => <option key={level}>{level}</option>)}</select></label>
          <label>{t("mood")}<select value={daily.mood} onChange={(input) => setDaily({ ...daily, mood: input.target.value })}><option value="">{t("notReported")}</option>{[1,2,3,4,5].map((level) => <option key={level}>{level}</option>)}</select></label></div>
        <label>{t("reflection")}<textarea value={daily.note} maxLength="1000" onChange={(input) => setDaily({ ...daily, note: input.target.value })} /></label>
        <button>{t("saveDaily")}</button>
      </form>}
    </section>
    <section className="area-state-sheet"><small>{t("habits")}</small>
      {data.habits.length ? data.habits.map((habit) => <div className="area-record-line" key={habit.id}><span><strong>{demoMode ? demoText(habit.title) : habit.title}</strong><small>{t(habit.frequency)} · {habit.active ? t("active") : t("paused")}</small></span>{canCatalog && <button type="button" onClick={() => mutate(`/api/life/habits/${habit.id}`, "PATCH", { active: !habit.active })}>{habit.active ? t("pause") : t("resume")}</button>}</div>) : <p className="empty-copy">{t("noHabits")}</p>}
      {canCatalog && <form onSubmit={(submit) => { submit.preventDefault(); mutate("/api/life/habits", "POST", { title: habitTitle, frequency }).then((saved) => saved && setHabitTitle("")); }}><label>{t("newHabit")}<input required maxLength="200" value={habitTitle} onChange={(input) => setHabitTitle(input.target.value)} /></label><label>{t("frequency")}<select value={frequency} onChange={(input) => setFrequency(input.target.value)}><option value="daily">{t("daily")}</option><option value="weekly">{t("weekly")}</option></select></label><button disabled={!habitTitle.trim()}>{t("addHabit")}</button></form>}
      {canReport && <form onSubmit={(submit) => { submit.preventDefault(); mutate(`/api/life/habits/${habitId}/logs/${date}`, "PUT", { done: habitDone, note: habitNote }); }}><label>{t("reportHabit")}<select required value={habitId} onChange={(input) => setHabitId(input.target.value)}><option value="">{t("chooseHabit")}</option>{active.map((habit) => <option value={habit.id} key={habit.id}>{demoMode ? demoText(habit.title) : habit.title}</option>)}</select></label><label>{t("outcome")}<select value={habitDone ? "done" : "not_done"} onChange={(input) => setHabitDone(input.target.value === "done")}><option value="done">{t("done")}</option><option value="not_done">{t("notDone")}</option></select></label><label>{t("note")}<input maxLength="1000" value={habitNote} onChange={(input) => setHabitNote(input.target.value)} /></label><button disabled={!habitId}>{t("saveHabit")}</button></form>}
    </section>
    <section className="area-state-sheet area-state-wide"><small>{date} / {t("timedEvents")}</small>
      <p>{t("eventsHelp")}</p>
      {data.events.length ? data.events.map((entry) => <div className="area-record-line" key={entry.id}><span><strong>{entry.startTime} · {demoMode ? demoText(entry.title) : entry.title}</strong><small>{t(entry.category)} · {entry.durationMinutes} {t("minutes")} · {t(entry.constraintKind)}</small></span></div>) : <p className="empty-copy">{t("noEvents")}</p>}
      {canCatalog && <form onSubmit={(submit) => { submit.preventDefault(); mutate("/api/life/events", "POST", { date, ...event }).then((saved) => saved && setEvent({ ...event, title: "" })); }}><label>{t("eventName")}<input maxLength="200" required value={event.title} onChange={(input) => setEvent({ ...event, title: input.target.value })} /></label><div className="area-form-triple"><label>{t("startTime")}<input type="time" required value={event.startTime} onChange={(input) => setEvent({ ...event, startTime: input.target.value })} /></label><label>{t("end")}<input type="time" required value={event.endTime} onChange={(input) => setEvent({ ...event, endTime: input.target.value })} /></label><label>{t("category")}<select value={event.category} onChange={(input) => setEvent({ ...event, category: input.target.value })}>{["sport","social","chore","health","other"].map((value) => <option key={value} value={value}>{t(value)}</option>)}</select></label></div><label className="area-check"><input type="checkbox" checked={event.flexible} onChange={(input) => setEvent({ ...event, flexible: input.target.checked })} /> {t("flexibleTime")}</label><button disabled={!event.title.trim()}>{t("addLifeCalendar")}</button></form>}
    </section>
  </div>;
}

/** Show a manual Money balance, recorded transactions, and dated budgets. */
function MoneyRecords({ data, date, today, disabled, mutate, demoMode }) {
  const { t, demoText } = useI18n();
  const [opening, setOpening] = useState("");
  const [transaction, setTransaction] = useState({ type: "expense", amount: "", category: "", note: "" });
  const [budget, setBudget] = useState({ amount: "", category: "" });
  useEffect(() => { setOpening((data.openingBalanceCents / 100).toFixed(2)); }, [data.openingBalanceCents]);
  const canCatalog = !disabled && date >= today;
  const canReport = !disabled && date === today;
  return <div className="area-state-grid">
    <section className="area-state-sheet"><small>{t("balance")}</small><strong className="area-money-figure">{money(data.balanceCents)}</strong><p>{t("openingHelp")}</p>
      {canCatalog && <form onSubmit={(submit) => { submit.preventDefault(); try { mutate("/api/money/opening-balance", "PUT", { cents: enteredCents(opening, true) }); } catch (error) { mutate(null, null, null, error.message); } }}><label>{t("openingAmount")}<input inputMode="decimal" value={opening} onChange={(input) => setOpening(input.target.value)} required /></label><button>{t("setOpening")}</button></form>}
    </section>
    <section className="area-state-sheet"><small>{date} / {t("transactions")}</small>
      {data.transactions.length ? data.transactions.map((entry) => <div className="area-record-line" key={entry.id}><span><strong>{entry.type === "expense" ? "−" : "+"}{money(entry.amountCents)} · {demoMode ? demoText(entry.category) : entry.category}</strong><small>{entry.note ? (demoMode ? demoText(entry.note) : entry.note) : t("noNote")}</small></span></div>) : <p className="empty-copy">{t("noTransactions")}</p>}
      {canReport && <form onSubmit={(submit) => { submit.preventDefault(); try { mutate("/api/money/transactions", "POST", { date, type: transaction.type, amountCents: enteredCents(transaction.amount), category: transaction.category, note: transaction.note }).then((saved) => saved && setTransaction({ ...transaction, amount: "", note: "" })); } catch (error) { mutate(null, null, null, error.message); } }}><div className="area-form-pair"><label>{t("type")}<select value={transaction.type} onChange={(input) => setTransaction({ ...transaction, type: input.target.value })}><option value="expense">{t("expense")}</option><option value="income">{t("income")}</option></select></label><label>{t("amount")}<input inputMode="decimal" required value={transaction.amount} onChange={(input) => setTransaction({ ...transaction, amount: input.target.value })} placeholder="12.50" /></label></div><label>{t("category")}<input required maxLength="100" value={transaction.category} onChange={(input) => setTransaction({ ...transaction, category: input.target.value })} /></label><label>{t("note")}<input maxLength="1000" value={transaction.note} onChange={(input) => setTransaction({ ...transaction, note: input.target.value })} /></label><button disabled={!transaction.amount || !transaction.category.trim()}>{t("recordTransaction")}</button></form>}
    </section>
    <section className="area-state-sheet area-state-wide"><small>{date.slice(0,7)} / {t("budgets")}</small>
      {data.budgets.length ? data.budgets.map((entry) => <div className="area-record-line" key={entry.id}><span><strong>{demoMode ? demoText(entry.category) : entry.category}</strong><small>{money(entry.spentCents)} / {money(entry.budgetCents)}</small></span></div>) : <p className="empty-copy">{t("noBudgets")}</p>}
      {canCatalog && <form onSubmit={(submit) => { submit.preventDefault(); try { mutate("/api/money/budgets", "PUT", { month: date.slice(0,7), category: budget.category, budgetCents: enteredCents(budget.amount) }).then((saved) => saved && setBudget({ ...budget, amount: "" })); } catch (error) { mutate(null, null, null, error.message); } }}><div className="area-form-pair"><label>{t("category")}<input required maxLength="100" value={budget.category} onChange={(input) => setBudget({ ...budget, category: input.target.value })} /></label><label>{t("monthlyAmount")}<input inputMode="decimal" required value={budget.amount} onChange={(input) => setBudget({ ...budget, amount: input.target.value })} placeholder="250.00" /></label></div><button disabled={!budget.category.trim() || !budget.amount}>{t("saveBudget")}</button></form>}
    </section>
  </div>;
}

/** Load and mutate only the selected area's records; parent reload keeps Summary/Calendar in sync. */
export function DomainRecordsBoard({ domain, date, today, backendConnected, onSaved, demoMode = false }) {
  const { t } = useI18n();
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
      setNotice(t("savedLocal"));
      return true;
    } catch (caught) { setError(caught.message); return false; }
    finally { setBusy(false); }
  }

  if (!backendConnected) return <section className="area-state-offline"><small>{t("areaOffline")}</small><p>{t("areaOfflineHelp")}</p></section>;
  if (!data) return <section className="area-state-offline"><small>{t("areaState")}</small><p>{error || t("loadingState")}</p></section>;
  return <div className="area-state-board" aria-busy={busy}>
    <div className="section-line"><small>{t(domain).toUpperCase()} / {t("areaState")} / {date}</small><span>{date < today ? t("pastRecord") : date > today ? t("futurePreparation") : t("todayReported")}</span></div>
    {error && <p className="area-state-error" role="alert">{error}</p>}{notice && <p className="area-state-notice" role="status">{notice}</p>}
    {domain === "learning" && <LearningRecords data={data} date={date} today={today} disabled={busy} mutate={mutate} demoMode={demoMode} />}
    {domain === "life" && <LifeRecords data={data} date={date} today={today} disabled={busy} mutate={mutate} demoMode={demoMode} />}
    {domain === "finance" && <MoneyRecords data={data} date={date} today={today} disabled={busy} mutate={mutate} demoMode={demoMode} />}
  </div>;
}
