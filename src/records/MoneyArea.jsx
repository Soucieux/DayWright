import { useState } from "react";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { Segmented } from "../ui/Segmented";
import { enteredCents, money } from "./money";
import { SheetForm } from "./SheetForm";

/**
 * Read an entered amount as cents, explaining a mistake in the interface language.
 * @param {string} value - What the user typed.
 * @param {(key: string) => string} t - The interface text lookup.
 * @param {boolean} [allowNegative=false] - Whether a leading minus is allowed.
 * @returns {number} The amount in cents.
 * @throws {Error} With a translated message when the amount can't be read exactly.
 */
function centsOf(value, t, allowNegative = false) {
  try {
    return enteredCents(value, allowNegative);
  } catch {
    throw new Error(t("amountInvalid"));
  }
}

/**
 * The amount the balance starts from, before any recorded transaction.
 * @param {object} props
 * @param {number} props.openingCents - The current opening balance.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(path: string, method: string, body: object) => Promise<void>} props.mutate - Save a change.
 * @param {() => void} props.onClose - Close the sheet.
 */
function OpeningSheet({ openingCents, backendConnected, mutate, onClose }) {
  const { t } = useI18n();
  const [amount, setAmount] = useState((openingCents / 100).toFixed(2));
  return (
    <SheetForm title={t("openingBalanceTitle")} submitLabel={t("saveOpeningAction")} note={t("openingNote")} backendConnected={backendConnected} onClose={onClose}
      onSubmit={() => mutate("/api/money/opening-balance", "PUT", { cents: centsOf(amount, t, true) })}>
      <label className="dw-field">{t("fieldAmount")}
        <input inputMode="decimal" required value={amount} onChange={(event) => setAmount(event.target.value)} /></label>
    </SheetForm>
  );
}

/**
 * Record today's income or expense, exactly as entered.
 * @param {object} props
 * @param {string} props.date - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(path: string, method: string, body: object) => Promise<void>} props.mutate - Save a change.
 * @param {() => void} props.onClose - Close the sheet.
 */
function TransactionSheet({ date, backendConnected, mutate, onClose }) {
  const { t } = useI18n();
  const [entry, setEntry] = useState({ type: "expense", amount: "", category: "", note: "" });
  const set = (fields) => setEntry((current) => ({ ...current, ...fields }));
  return (
    <SheetForm title={t("recordTransactionTitle")} submitLabel={t("saveTransactionAction")} backendConnected={backendConnected} onClose={onClose}
      onSubmit={() => mutate("/api/money/transactions", "POST", {
        date, type: entry.type, amountCents: centsOf(entry.amount, t), category: entry.category.trim(), note: entry.note.trim(),
      })}>
      <div className="dw-field"><span className="dw-field-label">{t("fieldType")}</span>
        <Segmented label={t("fieldType")} value={entry.type} onChange={(type) => set({ type })}
          options={[["expense", t("expenseLabel")], ["income", t("incomeLabel")]]} /></div>
      <label className="dw-field">{t("fieldAmount")}
        <input inputMode="decimal" required placeholder="12.50" value={entry.amount} onChange={(event) => set({ amount: event.target.value })} /></label>
      <label className="dw-field">{t("fieldCategory")}
        <input required pattern=".*\S.*" maxLength={100} value={entry.category} onChange={(event) => set({ category: event.target.value })} /></label>
      <label className="dw-field"><span>{t("noteLabel")} <span className="dw-optional">{t("optionalLabel")}</span></span>
        <input maxLength={1000} value={entry.note} onChange={(event) => set({ note: event.target.value })} /></label>
    </SheetForm>
  );
}

/**
 * Set how much a category may spend in the month on show.
 * @param {object} props
 * @param {string} props.month - The YYYY-MM month.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(path: string, method: string, body: object) => Promise<void>} props.mutate - Save a change.
 * @param {() => void} props.onClose - Close the sheet.
 */
function BudgetSheet({ month, backendConnected, mutate, onClose }) {
  const { t } = useI18n();
  const [category, setCategory] = useState("");
  const [amount, setAmount] = useState("");
  return (
    <SheetForm title={t("setBudgetTitle")} submitLabel={t("saveBudgetAction")} note={t("budgetNote", { month })} backendConnected={backendConnected} onClose={onClose}
      onSubmit={() => mutate("/api/money/budgets", "PUT", { month, category: category.trim(), budgetCents: centsOf(amount, t) })}>
      <label className="dw-field">{t("fieldCategory")}
        <input required pattern=".*\S.*" maxLength={100} value={category} onChange={(event) => setCategory(event.target.value)} /></label>
      <label className="dw-field">{t("fieldMonthlyAmount")}
        <input inputMode="decimal" required placeholder="250.00" value={amount} onChange={(event) => setAmount(event.target.value)} /></label>
    </SheetForm>
  );
}

/**
 * Money's own records: the balance, the day's transactions and the month's budgets, shown by tab.
 * Only amounts the user entered count; nothing is estimated.
 * @param {object} props
 * @param {string} props.tab - The tab on show.
 * @param {object} props.data - The Money snapshot for the day on show.
 * @param {boolean} props.isToday - Whether transactions can be recorded.
 * @param {boolean} props.canPrepare - Whether the opening balance and budgets can change.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(path: string, method: string, body: object) => Promise<void>} props.mutate - Save a change from a form.
 * @param {string|null} props.sheet - The form open, if any.
 * @param {(sheet: string|null) => void} props.setSheet - Open or close a form.
 */
export function MoneyArea({ tab, data, isToday, canPrepare, backendConnected, mutate, sheet, setSheet }) {
  const { t, demoText } = useI18n();
  const show = (id) => tab === "overview" || tab === id;
  const month = data.date.slice(0, 7);
  const close = () => setSheet(null);
  return (
    <>
      {show("balance") && (
        <section className="dw-card" aria-labelledby="dw-balance-title">
          <h2 id="dw-balance-title" className="dw-heading dw-card-title">{t("balanceHeading")}</h2>
          <p className="dw-money-figure">{money(data.balanceCents)}</p>
          <p className="dw-caption">{t("balanceExplained", { opening: money(data.openingBalanceCents) })}</p>
          {canPrepare && <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected} onClick={() => setSheet("opening")}><Icon name="pencil" size={18} />{t("setOpeningAction")}</button>}
        </section>
      )}
      {show("transactions") && (
        <section className="dw-card" aria-labelledby="dw-transactions-title">
          <div className="dw-card-head">
            <h2 id="dw-transactions-title" className="dw-heading">{t("transactionsTitle")}</h2>
            {isToday && <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected} onClick={() => setSheet("transaction")}><Icon name="plus" size={18} />{t("recordTransactionAction")}</button>}
          </div>
          {data.transactions.length ? (
            <ul className="dw-day-rows">
              {data.transactions.map((entry) => (
                <li key={entry.id} className="dw-day-row dw-session-row">
                  <span className="dw-day-row-title">{demoText(entry.category)}{entry.note && <span className="dw-caption">{demoText(entry.note)}</span>}</span>
                  <strong className="dw-money-amount">{entry.type === "expense" ? "−" : "+"}{money(entry.amountCents)}
                    <span className="dw-visually-hidden"> {t(entry.type === "expense" ? "expenseLabel" : "incomeLabel")}</span></strong>
                </li>
              ))}
            </ul>
          ) : <p className="dw-muted">{t("noTransactions")}</p>}
        </section>
      )}
      {show("budgets") && (
        <section className="dw-card" aria-labelledby="dw-budgets-title">
          <div className="dw-card-head">
            <h2 id="dw-budgets-title" className="dw-heading">{t("budgetsTitle", { month })}</h2>
            {canPrepare && <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected} onClick={() => setSheet("budget")}><Icon name="plus" size={18} />{t("setBudgetAction")}</button>}
          </div>
          {data.budgets.length ? (
            <ul className="dw-balance">
              {data.budgets.map((budget) => (
                <li key={budget.id}>
                  <span>{demoText(budget.category)}</span>
                  <span className="dw-track dw-area-money"><span style={{ width: `${budget.budgetCents ? Math.min(100, Math.round((budget.spentCents / budget.budgetCents) * 100)) : 0}%` }} /></span>
                  <span className="dw-caption">{t("spentOfBudget", { spent: money(budget.spentCents), budget: money(budget.budgetCents) })}</span>
                </li>
              ))}
            </ul>
          ) : <p className="dw-muted">{t("noBudgets")}</p>}
        </section>
      )}
      {sheet === "opening" && <OpeningSheet openingCents={data.openingBalanceCents} backendConnected={backendConnected} mutate={mutate} onClose={close} />}
      {sheet === "transaction" && <TransactionSheet date={data.date} backendConnected={backendConnected} mutate={mutate} onClose={close} />}
      {sheet === "budget" && <BudgetSheet month={month} backendConnected={backendConnected} mutate={mutate} onClose={close} />}
    </>
  );
}
