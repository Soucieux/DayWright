import { useRef, useState } from "react";
import { useI18n } from "../i18n";
import { AreaTag } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { addedLabel, sourceView } from "./libraryData";
import { LibraryLinksSheet } from "./LibrarySheets";

/** Rows listed before the user asks for all of them. */
const FIRST_ROWS = 10;

/** Interface text for each kind of note or file. */
const KIND_KEYS = { markdown: "kindMarkdown", pdf: "kindPdf", word: "kindWord", file: "kindFile", note: "kindNote" };

/**
 * The goal a note or file is linked to, as a chip.
 * @param {object} props
 * @param {{title: string}} props.goal - The goal.
 */
export function GoalChip({ goal }) {
  const { demoText } = useI18n();
  return <span className="dw-chip dw-chip-small dw-library-goal"><Icon name="target" size={14} />{demoText(goal.title)}</span>;
}

/**
 * A short list of notes and files, as a goal's sheet and an area's page show them: each one's name
 * and kind, and its goal when the list spans several.
 * @param {object} props
 * @param {object[]} props.items - The notes and files, newest first.
 * @param {object[]} [props.goals] - The user's goals, to name each item's goal; left out, no goal is shown.
 */
export function LibraryItemList({ items, goals }) {
  const { t, demoText } = useI18n();
  return (
    <ul className="dw-library-items">
      {items.map((item) => {
        const view = sourceView(item);
        const goal = goals?.find((entry) => entry.id === item.goalId);
        return (
          <li key={item.id}>
            <Icon name={view.group === "files" ? "file" : "note"} size={16} />
            <span className="dw-library-item-name">{demoText(view.name)}</span>
            {goal ? <GoalChip goal={goal} /> : <span className="dw-caption">{t(KIND_KEYS[view.kind])}</span>}
          </li>
        );
      })}
    </ul>
  );
}

/**
 * One note or file: its name, kind and size, its area and goal, when it was added, Edit for its area
 * and goal, and a two-step Remove.
 * @param {object} props
 * @param {object} props.source - The note or file as the local service lists it.
 * @param {object|undefined} props.goal - Its goal, if it has one that still exists.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be changed.
 * @param {() => void} props.onEdit - Change its area and goal.
 * @param {() => Promise<void>} props.onRemove - Remove it; throws to report a failure.
 */
function SourceRow({ source, goal, today, backendConnected, onEdit, onRemove }) {
  const { t, language, demoText } = useI18n();
  const [confirming, setConfirming] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState("");
  const removeRef = useRef(null);
  const view = sourceView(source);
  const name = demoText(view.name);
  const kind = t(KIND_KEYS[view.kind]);
  const size = t("charactersCount", { count: new Intl.NumberFormat(language === "zh" ? "zh-Hans" : "en-GB").format(source.characterCount) });
  const added = addedLabel(source.createdAt, today, language, t("todayWord"));

  async function remove() {
    setRemoving(true);
    setError("");
    try {
      await onRemove();
    } catch (caught) {
      setError(caught.message);
      setRemoving(false);
    }
  }

  return (
    <>
      <tr className={confirming ? "dw-source-removing" : undefined}>
        <th scope="row">
          <span className="dw-source-name">
            <Icon name={view.group === "files" ? "file" : "note"} size={20} />
            <span className="dw-source-title">
              <span>{name}</span>
              <span className="dw-caption dw-source-kind">{kind} · {size}</span>
              <span className="dw-source-meta"><AreaTag domain={source.domain} />{goal && <GoalChip goal={goal} />}<span className="dw-caption">{added}</span></span>
            </span>
          </span>
        </th>
        <td><AreaTag domain={source.domain} /></td>
        <td>{goal ? <GoalChip goal={goal} /> : <span className="dw-caption">{t("noGoalOption")}</span>}</td>
        <td>{added}</td>
        <td>
          <span className="dw-source-actions">
            <button type="button" className="dw-button dw-button-quiet dw-icon-only" aria-label={t("libraryLinksLabel", { name })}
              title={t("libraryLinksLabel", { name })} disabled={!backendConnected} onClick={onEdit}><Icon name="pencil" size={18} /></button>
            <button type="button" className="dw-button dw-button-quiet dw-icon-only" ref={removeRef} aria-label={t("removeSourceLabel", { name })}
              title={t("removeSourceLabel", { name })} aria-expanded={confirming} disabled={!backendConnected} onClick={() => setConfirming(true)}>
              <Icon name="trash" size={18} /></button>
          </span>
        </td>
      </tr>
      {confirming && (
        <tr className="dw-source-confirm-row">
          <td colSpan={5}>
            <div className="dw-confirm-remove" role="alertdialog" aria-labelledby={`dw-remove-${source.id}`} aria-describedby={`dw-remove-${source.id}-body`}>
              <p className="dw-step">{t("stepTwoOfTwo")}</p>
              <h3 id={`dw-remove-${source.id}`}>{t("removeSourceQuestion", { name })}</h3>
              <p id={`dw-remove-${source.id}-body`}>{t(view.group === "files" ? "removeFileConsequence" : "removeSourceConsequence")}</p>
              {error && <p className="dw-alert" role="alert">{error}</p>}
              <div className="dw-actions">
                <button type="button" className="dw-button dw-button-danger" disabled={removing} onClick={remove}><Icon name="trash" size={18} />{removing ? t("removingLabel") : t("removeSourceAction")}</button>
                <button type="button" className="dw-button dw-button-quiet" autoFocus disabled={removing}
                  onClick={() => { setConfirming(false); removeRef.current?.focus(); }}>{t("cancel")}</button>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

/**
 * The Library's notes and files in the area on show, newest first, each with its area and goal.
 * @param {object} props
 * @param {object[]} props.sources - The notes and files to list, newest first.
 * @param {number} props.total - How many the whole Library holds.
 * @param {object[]} props.goals - The user's goals, to name each item's goal as it is now.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be changed.
 * @param {() => Promise<void>} props.onChanged - Refresh after an item's area or goal changes.
 * @param {(source: object) => Promise<void>} props.onRemove - Remove an item; throws to report a failure.
 */
export function SourceList({ sources, total, goals, today, backendConnected, onChanged, onRemove }) {
  const { t, demoText } = useI18n();
  const [showAll, setShowAll] = useState(false);
  const [editing, setEditing] = useState(null);
  const headingRef = useRef(null);
  const shown = showAll ? sources : sources.slice(0, FIRST_ROWS);
  const goalOf = (source) => goals.find((goal) => goal.id === source.goalId);

  /**
   * Remove an item, then keep focus in the list once its row is gone.
   * @param {object} source - The item to remove.
   */
  async function remove(source) {
    await onRemove(source);
    headingRef.current?.focus();
  }

  if (!total) {
    return (
      <section className="dw-card dw-empty-card">
        <span className="dw-empty-tile"><Icon name="book" size={24} /></span>
        <h2 className="dw-title">{t("libraryEmptyTitle")}</h2>
        <p className="dw-body-lg">{t("libraryEmptyBody")}</p>
      </section>
    );
  }

  return (
    <section className="dw-card dw-sources" aria-labelledby="dw-library-items">
      <div className="dw-card-head">
        <h2 id="dw-library-items" className="dw-heading" ref={headingRef} tabIndex={-1}>{t("libraryItemsHeading")} <span className="dw-caption">{sources.length}</span></h2>
        <span className="dw-caption">{t("newestFirst")}</span>
      </div>
      {sources.length ? (
        <table className="dw-sources-table">
          <caption className="dw-visually-hidden">{t("libraryItemsHeading")}</caption>
          <thead>
            <tr>
              <th scope="col">{t("columnName")}</th><th scope="col">{t("fieldArea")}</th><th scope="col">{t("fieldGoal")}</th>
              <th scope="col">{t("columnAdded")}</th><th scope="col"><span className="dw-visually-hidden">{t("columnActions")}</span></th>
            </tr>
          </thead>
          <tbody>
            {shown.map((source) => (
              <SourceRow key={source.id} source={source} goal={goalOf(source)} today={today} backendConnected={backendConnected}
                onEdit={() => setEditing(source)} onRemove={() => remove(source)} />
            ))}
          </tbody>
        </table>
      ) : <p className="dw-muted dw-sources-none">{t("noItemsInArea")}</p>}
      {sources.length > FIRST_ROWS && (
        <p className="dw-sources-foot">
          <span className="dw-caption">{t("showingCount", { shown: shown.length, total: sources.length })}</span>
          {!showAll && <button type="button" className="dw-button dw-button-quiet" onClick={() => setShowAll(true)}>{t("showAllAction")}</button>}
        </p>
      )}
      {editing && (
        <LibraryLinksSheet key={editing.id} source={editing} name={demoText(sourceView(editing).name)} goals={goals}
          backendConnected={backendConnected} onSaved={onChanged} onClose={() => setEditing(null)} />
      )}
    </section>
  );
}
