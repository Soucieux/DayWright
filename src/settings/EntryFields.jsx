import { useId } from "react";
import { useI18n } from "../i18n";
import { WORD_LIMIT, countWords } from "../wording";
import { MEMORY_AREAS, areaName, dayName } from "./memory";

/** A keep-off rule names one of the four areas, or a task by its title. */
const RULE_AREAS = MEMORY_AREAS.slice(0, 4);
const TASK = "task";

/**
 * The fields of an entry Ava remembers that the user fills or changes, on a card that needs them or in Settings ›
 * Memory: a rule's times, its days and the area or task it keeps off, by its kind; a note's words, at most WORD_LIMIT,
 * and its area; and, in Settings, the day it ends, if any. The service checks them again when they are saved.
 * @param {object} props
 * @param {object} props.entry - The entry as it stands: a note, or a rule with its `ruleKind`.
 * @param {(entry: object) => void} props.onChange - Take the entry with a field changed.
 * @param {boolean} [props.withEnd=false] - Whether its end date can be set, as Settings sets it.
 */
export function EntryFields({ entry, onChange, withEnd = false }) {
  const { t, language } = useI18n();
  const id = useId();
  const set = (field, value) => onChange({ ...entry, [field]: value });
  const days = new Set(entry.days || []);
  const words = countWords(entry.wording || "");
  return (
    <div className="dw-entry-fields">
      {entry.kind === "note" ? (
        <>
          <label className="dw-field"><span className="dw-field-label">{t("memoryFieldWording")}</span>
            <textarea rows={2} value={entry.wording} aria-describedby={`${id}-count`} onChange={(event) => set("wording", event.target.value)} />
            <span id={`${id}-count`} className={`dw-caption${words > WORD_LIMIT ? " dw-over-limit" : ""}`}>
              {t("memoryWordCount", { count: words, limit: WORD_LIMIT })}</span></label>
          <label className="dw-field"><span className="dw-field-label">{t("fieldArea")}</span>
            <select value={entry.area} onChange={(event) => set("area", event.target.value)}>
              {MEMORY_AREAS.map((area) => <option key={area} value={area}>{areaName(area, t)}</option>)}
            </select></label>
        </>
      ) : (
        <>
          {entry.ruleKind === "keep-free" && (
            <div className="dw-entry-times">
              <label className="dw-field"><span className="dw-field-label">{t("fieldStart")}</span>
                <input type="time" value={entry.start || ""} onChange={(event) => set("start", event.target.value)} /></label>
              <label className="dw-field"><span className="dw-field-label">{t("memoryFieldEnd")}</span>
                <input type="time" value={entry.end || ""} onChange={(event) => set("end", event.target.value)} /></label>
            </div>
          )}
          {entry.ruleKind === "finish-by" && (
            <label className="dw-field"><span className="dw-field-label">{t("memoryFieldLatest")}</span>
              <input type="time" value={entry.latest || ""} onChange={(event) => set("latest", event.target.value)} /></label>
          )}
          {entry.ruleKind === "keep-off" && (
            <div className="dw-entry-times">
              <label className="dw-field"><span className="dw-field-label">{t("memoryFieldArea")}</span>
                <select value={entry.task != null && !entry.area ? TASK : entry.area || ""}
                  onChange={(event) => onChange(event.target.value === TASK ? { ...entry, area: null, task: entry.task || "" }
                    : { ...entry, area: event.target.value || null, task: null })}>
                  <option value="" disabled>{t("memoryChooseArea")}</option>
                  {RULE_AREAS.map((area) => <option key={area} value={area}>{t(area)}</option>)}
                  <option value={TASK}>{t("memoryAreaTask")}</option>
                </select></label>
              {entry.task != null && !entry.area && (
                <label className="dw-field"><span className="dw-field-label">{t("memoryFieldTask")}</span>
                  <input type="text" maxLength={200} value={entry.task} onChange={(event) => set("task", event.target.value)} /></label>
              )}
            </div>
          )}
          <fieldset className="dw-entry-days">
            <legend className="dw-field-label">{t("memoryFieldDays")}</legend>
            {[0, 1, 2, 3, 4, 5, 6].map((day) => (
              <button key={day} type="button" className="dw-chip" aria-pressed={days.has(day)}
                onClick={() => set("days", days.has(day) ? [...days].filter((other) => other !== day) : [...days, day].sort())}>
                {dayName(day, language)}</button>
            ))}
          </fieldset>
        </>
      )}
      {withEnd && (
        <label className="dw-field"><span className="dw-field-label">{t("memoryFieldEnds")}</span>
          <input type="date" value={entry.endsOn || ""} onChange={(event) => set("endsOn", event.target.value || null)} /></label>
      )}
    </div>
  );
}
