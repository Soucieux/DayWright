import { useCallback, useEffect, useId, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { MenuSelect } from "../ui/MenuSelect";
import { Segmented } from "../ui/Segmented";
import { dayName } from "./memory";
import { countryOptions, holidayDate, holidayName, importedLine, regionOptions, scheduleProblem } from "./schedule";

/** The weekdays a work schedule can hold on, Monday (0) to Sunday (6). */
const WEEK = [0, 1, 2, 3, 4, 5, 6];

/**
 * Settings › Schedule, kept for both workspaces. Work schedule: a switch, off until turned on; working hours, which
 * plans keep free, or focus time, which holds the day's Work tasks; from and to; and the days it holds on. Each
 * change is kept once the schedule is whole. Statutory holidays: a switch; the country and region; Import, the one
 * time DayWright goes online for them, to date.nager.at, for this year and next; when they were last imported; and
 * the list, which Remove all forgets in two steps. Turning holidays off keeps the list.
 * @param {object} props
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {() => void} props.onChanged - Read the day again, as today's plans follow the schedule and holidays.
 */
export function ScheduleSection({ backendConnected, onChanged }) {
  const { t, language } = useI18n();
  const id = useId();
  const [view, setView] = useState(null);
  const [draft, setDraft] = useState(null);
  const [problem, setProblem] = useState(null);
  const [busy, setBusy] = useState(false);
  const [importing, setImporting] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState("");

  const show = useCallback((answer) => {
    setView(answer);
    setDraft(answer.schedule);
  }, []);

  const load = useCallback(async () => {
    try {
      show(await api("/api/schedule"));
    } catch (caught) {
      setError(caught.message);
    }
  }, [show]);

  useEffect(() => {
    if (backendConnected) load();
  }, [backendConnected, load]);

  /** Keep a change, then show the schedule and holidays as kept and read the day again; whether it was kept. */
  async function change(request) {
    setBusy(true);
    setError("");
    try {
      show(await request());
      onChanged();
      return true;
    } catch (caught) {
      setError(caught.message);
      return false;
    } finally {
      setBusy(false);
    }
  }

  /**
   * Change one part of the work schedule, and keep it once it is whole; until then the pane says what it needs.
   * @param {object} part - The fields changed.
   */
  function setSchedule(part) {
    const next = { ...draft, ...part };
    const missing = scheduleProblem(next);
    setDraft(next);
    setProblem(missing);
    if (!missing) change(() => api("/api/schedule", { method: "PUT", body: JSON.stringify(next) }));
  }

  /**
   * Turn holidays on or off, or choose their country or region; nothing is fetched.
   * @param {object} part - The fields changed.
   */
  function setHolidays(part) {
    const { enabled, country, region } = { ...view.holidays, ...part };
    const next = { enabled, country, region };
    change(() => api("/api/holidays", { method: "PUT", body: JSON.stringify(next) }));
  }

  /** Import this year's and next year's holidays for the country chosen: the one time DayWright goes online for them. */
  async function importHolidays() {
    setImporting(true);
    await change(() => api("/api/holidays/import", { method: "POST" }));
    setImporting(false);
  }

  /** Forget every holiday imported; the country and region chosen stay. */
  async function removeAll() {
    if (await change(() => api("/api/holidays", { method: "DELETE" }))) setRemoving(false);
  }

  if (!backendConnected) {
    return <section className="dw-settings-section"><p className="dw-set-lead">{t("settingsServiceOff")}</p></section>;
  }
  const holidays = view?.holidays;
  const year = new Date().getFullYear();
  const days = new Set(draft?.days || []);
  // A region chosen before its holidays were imported, as Ava's card may choose one, stays on show.
  const regions = holidays ? [...new Set([...holidays.regions, ...(holidays.region ? [holidays.region] : [])])] : [];
  return (
    <section className="dw-settings-section">
      <p className="dw-set-lead">{t("workScheduleLead")}</p>
      {view && draft && (
        <>
          <ul className="dw-set-list">
            <li className="dw-set-row">
              <span className="dw-set-row-icon"><Icon name="clock" size={20} /></span>
              <span className="dw-set-row-main">
                <span className="dw-set-title" id={`${id}-work`}>{t("workScheduleSwitch")}</span>
                <span className="dw-set-caption">{t("workScheduleSwitchNote")}</span>
              </span>
              <span className="dw-set-row-end">
                <span className="dw-switch"><input type="checkbox" role="switch" aria-labelledby={`${id}-work`} checked={draft.enabled}
                  disabled={busy} onChange={(event) => setSchedule({ enabled: event.target.checked })} /></span>
              </span>
            </li>
            {draft.enabled && (
              <li className="dw-set-row dw-schedule-details">
                <Segmented label={t("workScheduleKind")} value={draft.mode} onChange={(mode) => mode !== draft.mode && setSchedule({ mode })}
                  options={[["working", t("workScheduleWorking")], ["focus", t("workScheduleFocus")]]} />
                <p className="dw-set-caption">{t(draft.mode === "focus" ? "workScheduleFocusNote" : "workScheduleWorkingNote")}</p>
                <div className="dw-entry-times">
                  <label className="dw-field"><span className="dw-field-label">{t("workScheduleFrom")}</span>
                    <input type="time" value={draft.start} onChange={(event) => setSchedule({ start: event.target.value })} /></label>
                  <label className="dw-field"><span className="dw-field-label">{t("workScheduleTo")}</span>
                    <input type="time" value={draft.end} onChange={(event) => setSchedule({ end: event.target.value })} /></label>
                </div>
                <fieldset className="dw-entry-days">
                  <legend className="dw-field-label">{t("workScheduleDays")}</legend>
                  {WEEK.map((day) => (
                    <button key={day} type="button" className="dw-chip" aria-pressed={days.has(day)} disabled={busy}
                      onClick={() => setSchedule({ days: days.has(day) ? draft.days.filter((other) => other !== day)
                        : [...draft.days, day].sort((first, second) => first - second) })}>{dayName(day, language)}</button>
                  ))}
                </fieldset>
                {problem && <p className="dw-caption dw-over-limit" role="alert">{t(problem)}</p>}
              </li>
            )}
          </ul>
          <div className="dw-set-group">
            <ul className="dw-set-list">
              <li className="dw-set-row">
                <span className="dw-set-row-icon"><Icon name="calendar" size={20} /></span>
                <span className="dw-set-row-main">
                  <span className="dw-set-title" id={`${id}-holidays`}>{t("holidaysTitle")}</span>
                  <span className="dw-set-caption">{t("holidaysSwitchNote")}</span>
                </span>
                <span className="dw-set-row-end">
                  <span className="dw-switch"><input type="checkbox" role="switch" aria-labelledby={`${id}-holidays`}
                    checked={holidays.enabled} disabled={busy} onChange={(event) => setHolidays({ enabled: event.target.checked })} /></span>
                </span>
              </li>
              <li className="dw-set-row dw-schedule-details">
                <div className="dw-entry-times">
                  <div className="dw-field"><span className="dw-field-label">{t("holidaysCountry")}</span>
                    <MenuSelect label={t("holidaysCountry")} value={holidays.country || ""} disabled={busy}
                      options={[...(holidays.country ? [] : [{ value: "", label: t("holidaysChooseCountry"), disabled: true }]),
                        ...countryOptions(holidays.countries, language)]}
                      onChange={(country) => country !== holidays.country && setHolidays({ country, region: null })} /></div>
                  <div className="dw-field"><span className="dw-field-label">{t("holidaysRegion")}</span>
                    <MenuSelect label={t("holidaysRegion")} value={holidays.region || ""} disabled={busy || !holidays.country}
                      options={regionOptions(regions, holidays.regionNames, language, t)}
                      onChange={(region) => setHolidays({ region: region || null })} /></div>
                </div>
                {holidays.country && !holidays.regions.length && <p className="dw-set-caption">{t("holidaysRegionsLater")}</p>}
                <div className="dw-actions">
                  <button type="button" className="dw-button dw-button-primary" disabled={busy || !holidays.country} aria-busy={importing}
                    onClick={importHolidays}><Icon name="globe" size={18} />
                    {importing ? t("holidaysImporting") : t("holidaysImport", { first: year, second: year + 1 })}</button>
                </div>
                <p className="dw-set-caption dw-schedule-privacy"><Icon name="lock" size={14} />{t("holidaysPrivacy")}</p>
                <p className="dw-set-caption">{importedLine(holidays, t, language)}</p>
              </li>
            </ul>
          </div>
          {holidays.list.length > 0 && (
            <div className="dw-set-group">
              <div className="dw-set-head"><h3 className="dw-set-heading">{t("holidaysListHeading", { count: holidays.list.length })}</h3>
                <button type="button" className="dw-button dw-button-quiet dw-set-head-action" disabled={busy} onClick={() => setRemoving(true)}>
                  <Icon name="trash" size={16} />{t("holidaysRemoveAll")}</button></div>
              {removing && (
                <div className="dw-confirm-remove" role="alertdialog" aria-label={t("holidaysRemoveQuestion")}>
                  <p><strong>{t("holidaysRemoveQuestion")}</strong></p>
                  <p className="dw-caption">{t("holidaysRemoveNote")}</p>
                  <div className="dw-actions">
                    <button type="button" className="dw-button dw-button-danger" disabled={busy} onClick={removeAll}>
                      <Icon name="trash" size={18} />{t("holidaysRemoveAction")}</button>
                    <button type="button" className="dw-button dw-button-quiet" autoFocus onClick={() => setRemoving(false)}>{t("cancel")}</button>
                  </div>
                </div>
              )}
              <ul className="dw-set-list">
                {holidays.list.map((holiday) => (
                  <li key={`${holiday.date}-${holiday.name}`} className="dw-set-row">
                    <span className="dw-set-row-main">
                      <span className="dw-set-title">{holidayName(holiday, language)}</span>
                      <span className="dw-set-caption">{holidayDate(holiday.date, language)}</span>
                    </span>
                    <span className="dw-set-row-end"><span className="dw-set-tag">{t(holiday.regional ? "holidayRegional" : "holidayNational")}</span></span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
      {error && <p className="dw-alert" role="alert">{error}</p>}
    </section>
  );
}
