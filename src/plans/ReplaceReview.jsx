import { useState } from "react";
import { useI18n } from "../i18n";
import { AreaGlyph } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { PageBanners } from "../ui/PageBanners";
import { agentName } from "../ui/agentName";
import { formatMinutes } from "../time";
import { changeCounts, replacementRows } from "./planDiff";
import { planName } from "./planName";

/** Message key naming each kind of change. */
const CHANGE_LABELS = {
  reported: "changeReported", same: "changeSame", shorter: "changeShorter", longer: "changeLonger",
  moved: "changeMoved", removed: "changeRemoved", added: "changeAdded",
};

/** The icon beside each kind of change, so the badge doesn't rely on colour. */
const CHANGE_ICONS = {
  reported: "lock", same: "minus", shorter: "minus", longer: "plus", moved: "clock", removed: "x", added: "plus",
};

/**
 * One side of a compared row: when, which area, what, and a line on what happens to it.
 * @param {object} props
 * @param {object} props.entry - The plan entry.
 * @param {string} [props.note] - The line under the title.
 * @param {boolean} [props.struck=false] - Strike the title through, for an entry the replacement drops.
 */
function DiffEntry({ entry, note, struck = false }) {
  const { demoText } = useI18n();
  return (
    <div className="dw-diff-entry">
      <span className="dw-plan-time">{entry.start_time}</span>
      <AreaGlyph domain={entry.domain} />
      <span className="dw-diff-text">
        {struck ? <s>{demoText(entry.title)}</s> : <span>{demoText(entry.title)}</span>}
        {note && <span className="dw-caption">{note}</span>}
      </span>
    </div>
  );
}

/**
 * One row of the comparison: the set plan's entry, what changes, and the replacement's entry.
 * @param {object} props
 * @param {{kind: string, before: object|null, after: object|null}} props.row - A row from `replacementRows`.
 */
function DiffRow({ row }) {
  const { t, language } = useI18n();
  const { kind, before, after } = row;
  const length = (entry) => formatMinutes(entry.duration_minutes, language);
  // Setting a plan carries each task's reported status onto the entry that schedules it.
  const carried = before?.source_item_id ? before.completion_status : after?.completion_status;
  const beforeNote = kind === "reported" ? t(before?.completion_status) : kind === "same" || !before ? "" : length(before);
  const afterNote = kind === "reported"
    ? t("staysAsReported", { status: t(carried) })
    : kind === "same" ? "" : kind === "removed" ? t("notInThisPlan") : length(after);
  return (
    <tr className={kind === "same" || kind === "reported" ? undefined : "dw-diff-changed"}>
      <td>{before ? <DiffEntry entry={before} note={beforeNote} /> : <span className="dw-diff-absent">{t("notInThisPlan")}</span>}</td>
      <td><span className={`dw-change dw-change-${kind}`}><Icon name={CHANGE_ICONS[kind]} size={14} />{t(CHANGE_LABELS[kind])}</span></td>
      <td>{after ? <DiffEntry entry={after} note={afterNote} /> : <DiffEntry entry={before} note={afterNote} struck />}</td>
    </tr>
  );
}

/**
 * Review a replacement for a plan that is already set. Every entry is lined up with its
 * counterpart, reported entries keep their status, and nothing is replaced until the user ticks
 * that they reviewed each change and then chooses Replace.
 * @param {object} props
 * @param {object} props.day - The day on show.
 * @param {object} props.current - The plan that is set.
 * @param {object[]|null} props.currentEntries - Its entries, or null while they load.
 * @param {object} props.replacement - The plan proposed instead.
 * @param {object[]|null} props.replacementEntries - Its entries, or null while they load.
 * @param {string} props.setAt - When the current plan was set, as HH:MM.
 * @param {string} props.heading - The page heading.
 * @param {string} props.backLabel - Names the comparison the back link returns to.
 * @param {boolean} props.backendConnected - Whether the replacement can be saved.
 * @param {() => void} props.onReplace - Replace the set plan with the reviewed one.
 * @param {() => void} props.onKeep - Keep the set plan and return to the comparison.
 */
export function ReplaceReview({ day, current, currentEntries, replacement, replacementEntries, setAt, heading, backLabel, backendConnected, onReplace, onKeep }) {
  const { t, demoText } = useI18n();
  const [reviewed, setReviewed] = useState(false);
  const loaded = Boolean(currentEntries && replacementEntries);
  const rows = loaded ? replacementRows(currentEntries, replacementEntries) : [];
  const counts = changeCounts(rows);
  const currentName = planName(current, t, demoText);
  const nextName = planName(replacement, t, demoText);
  const canReplace = reviewed && loaded && backendConnected;
  const breakdown = Object.entries(counts.byKind).map(([kind, count]) => `${t(CHANGE_LABELS[kind])} ${count}`).join(" · ");

  return (
    <>
      <header className="dw-page-head">
        <div>
          <button type="button" className="dw-back" onClick={onKeep}><Icon name="left" size={18} />{backLabel}</button>
          <h1 className="dw-display">{heading}</h1>
          <div className="dw-chips">
            <span className="dw-chip dw-chip-ink"><Icon name="check" size={14} />{t("planSetChip")} · {currentName}{setAt && ` · ${setAt}`}</span>
            <span className="dw-chip dw-chip-caution"><Icon name="history" size={14} />{t("underReview")}</span>
          </div>
        </div>
      </header>
      <PageBanners day={day} backendConnected={backendConnected} />

      <div className="dw-columns">
        <section className="dw-card dw-diff-card" aria-label={t("changeColumn")}>
          {loaded ? (
            <table className="dw-diff">
              <thead>
                <tr>
                  <th scope="col"><span className="dw-diff-head">{t("setNow", { name: currentName })}</span>
                    {setAt && <span className="dw-chip dw-chip-small"><Icon name="lock" size={14} />{t("setAtTime", { time: setAt })}</span>}</th>
                  <th scope="col">{t("changeColumn")}</th>
                  <th scope="col"><span className="dw-diff-head">{t("replacementName", { name: nextName })}</span>
                    <span className="dw-chip dw-chip-dashed dw-chip-small"><Icon name="pencil" size={14} />{t("draftChip")}</span></th>
                </tr>
              </thead>
              <tbody>{rows.map((row) => <DiffRow key={(row.before || row.after).id} row={row} />)}</tbody>
            </table>
          ) : <p className="dw-muted">{t("loadingPlans")}</p>}
          <p className="dw-caption dw-diff-note"><Icon name="info" size={16} />{t("rowsChangeNote")}</p>
        </section>

        <aside className="dw-column-side" aria-label={t("approveReplacement")}>
          <section className="dw-card" aria-labelledby="dw-why-title">
            <h2 id="dw-why-title" className="dw-heading dw-card-title">{t("whyAgentsPropose")}</h2>
            {replacement.rationale && <ul className="dw-reasons"><li><Icon name="agent" size={16} /><span>{demoText(replacement.rationale)}</span></li></ul>}
            {day.planRoute?.length > 0 && (
              <details className="dw-more">
                <summary>{t("agentDetails")}</summary>
                <ul className="dw-reasons">
                  {day.planRoute.map((run, index) => (
                    <li key={`${run.agentKey}-${index}`}><Icon name="agent" size={16} /><span><strong>{agentName(run.agentKey, t)}:</strong> {demoText(run.summary)}</span></li>
                  ))}
                </ul>
              </details>
            )}
          </section>
          <section className="dw-card dw-approve" aria-labelledby="dw-approve-title">
            <h2 id="dw-approve-title" className="dw-heading dw-card-title">{t("approveReplacement")}</h2>
            <ul className="dw-reasons">
              <li><Icon name="info" size={16} /><span><strong>{t("changesCount", { count: counts.changed })}</strong>{breakdown && ` · ${breakdown}`}</span></li>
              {counts.reported > 0 && <li><Icon name="lock" size={16} /><span>{t("reportedKeep", { count: counts.reported })}</span></li>}
              <li><Icon name="history" size={16} /><span>{t("oldPlanStays", { name: currentName })}</span></li>
              <li><Icon name="link" size={16} /><span>{t("goalsOnlyOnReport")}</span></li>
            </ul>
            <label className="dw-check">
              <input type="checkbox" checked={reviewed} disabled={!loaded} onChange={(event) => setReviewed(event.target.checked)} />
              <span>{counts.changed ? t("reviewedAll", { count: counts.changed }) : t("reviewedNone")}</span>
            </label>
            <div className="dw-approve-actions">
              <button type="button" className="dw-button dw-button-primary" disabled={!canReplace}
                aria-describedby={canReplace ? undefined : "dw-replace-reason"} onClick={onReplace}>
                <Icon name="check" size={18} />{t("replaceWith", { name: nextName })}
              </button>
              {!canReplace && <p id="dw-replace-reason" className="dw-caption">{backendConnected ? t("replaceNeedsReview") : t("previewCannotSave")}</p>}
              <button type="button" className="dw-button" onClick={onKeep}>{t("keepName", { name: currentName })}</button>
            </div>
          </section>
        </aside>
      </div>
    </>
  );
}
