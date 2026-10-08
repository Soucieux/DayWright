import { useContext, useEffect, useId, useRef, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { useLibrary } from "../library/libraryContext";
import { AvaOnly, ModelsContext, NeedsModel } from "../settings/NeedsModel";
import { isReady } from "../settings/models";
import { linkChoices, sourceView } from "../library/libraryData";
import { BriefingButton } from "../library/SourceBriefing";
import { ActionMenu } from "../ui/ActionMenu";
import { dateTime } from "../time";
import { Icon } from "../ui/Icon";
import { MenuSelect } from "../ui/MenuSelect";
import { Lead } from "../patterns/PatternParts";
import { taskPaceLine } from "../patterns/patternText";
import { checklistMark, continueRequest, movedIndex, offersContinue, pastTickRequest, startCheckLine, suggestsDone } from "./learningTasks";

/** How much a task asks of a study session, as the local service names it, with its text. */
const EFFORTS = [["light", "effortLight"], ["steady", "effortSteady"], ["deep", "effortDeep"]];
/** The icon for each place a task's source came from. */
const ORIGIN_ICONS = { website: "globe", folder: "folder", file: "file", note: "note" };
/** How often, and how many times, a briefing asks again while its website's look-up is under way: past the service's 10-second limit. */
const CHECK_WAIT_MS = 1000;
const CHECK_WAIT_TRIES = 15;

/**
 * A Learning task's briefing in its sheet: the Library item its checklist came from, with its own briefing,
 * the website's check as the task started, and Unlink; its effort, which the user may set while it has a
 * checklist from a source, linked or not; its references from the Library; its checklist; the Done
 * suggestion once every item is ticked; and Continue next session for a task partly done. Opening it on
 * an untimed task's day is when that task starts, so its website is looked up then, once.
 * @param {object} props
 * @param {object} props.task - The stored task.
 * @param {object} props.row - The row on show, with its status.
 * @param {string} props.today - Today's YYYY-MM-DD date; an earlier task's checklist is read-only.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(row: object, status: string) => void} props.onStatus - Report the row's status.
 * @param {(text: string, send?: boolean) => void} props.onAskAva - Open Ava with a request, sent at once when `send`.
 * @param {() => void} props.onUpdated - Reload the day once its website's look-up changed the task.
 */
export function LearningBriefing({ task, row, today, backendConnected, onStatus, onAskAva, onUpdated }) {
  const { t, demoText } = useI18n();
  const { items, refresh } = useLibrary();
  const [learned, setLearned] = useState(null);
  const [error, setError] = useState("");
  const [dismissed, setDismissed] = useState(false);
  const base = `/api/learning-tasks/${encodeURIComponent(task.id)}`;
  const past = task.date < today;

  useEffect(() => {
    if (!backendConnected) return undefined;
    let live = true;
    // An untimed task starts when its briefing is first opened on its day; the service looks its website up then.
    // While a look-up is under way, here or in the service's own round, the briefing waits for what it brings.
    async function load() {
      const opening = task.date === today && !task.start_time;
      let answer = await (opening ? api(`${base}/briefing-opened`, { method: "POST" }) : api(`${base}/checklist`));
      if (live) setLearned(answer);
      for (let tries = 0; live && answer.startCheckedAt && !answer.startCheck && tries < CHECK_WAIT_TRIES; tries += 1) {
        await new Promise((done) => { setTimeout(done, CHECK_WAIT_MS); });
        answer = await api(`${base}/checklist`);
        if (live) setLearned(answer);
      }
      // A page that changed may have changed the task's estimated length too, which the day on show then shows.
      if (live && opening && answer.startCheck === "updated") onUpdated();
    }
    load().catch((caught) => { if (live) setError(caught.message); });
    return () => { live = false; };
  }, [base, backendConnected, task.date, task.start_time, today]);

  if (!learned) return error ? <p className="dw-alert" role="alert">{error}</p> : null;
  const source = learned.sourceId && items.find((item) => item.id === learned.sourceId);
  const check = startCheckLine(learned);

  /**
   * Set how much the task asks of a session; reading its source again keeps it.
   * @param {string} effort - `light`, `steady` or `deep`.
   */
  async function setEffort(effort) {
    setError("");
    try {
      setLearned(await api(`${base}/effort`, { method: "PUT", body: JSON.stringify({ effort }) }));
    } catch (caught) {
      setError(caught.message);
    }
  }

  /**
   * Link a Library item to the task, or unlink one, the checklist's own included, which keeps the checklist and
   * its ticks; then show the Library's counts as they are now.
   * @param {string} sourceId - The item.
   * @param {boolean} link - Link it, or unlink it.
   */
  async function changeLink(sourceId, link) {
    setError("");
    try {
      setLearned(await api(link ? `${base}/sources` : `${base}/sources/${encodeURIComponent(sourceId)}`,
        link ? { method: "POST", body: JSON.stringify({ sourceId }) } : { method: "DELETE" }));
      await refresh?.();
    } catch (caught) {
      setError(caught.message);
    }
  }

  return (
    <section className="dw-learning-briefing" aria-label={t("learning")}>
      {learned.sourceId && (
        <div className="dw-learning-source">
          <p className="dw-learning-source-line"><Icon name={ORIGIN_ICONS[learned.sourceOrigin] || "file"} size={18} />
            <span className="dw-caption">{t("taskLibraryChecklistFrom")}</span>
            {source ? <BriefingButton source={source} /> : <span>{demoText(learned.sourceTitle || "")}</span>}
            {!past && <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected}
              onClick={() => changeLink(learned.sourceId, false)}>{t("taskLibraryUnlinkAction")}</button>}</p>
          {source?.briefing && <p className="dw-muted">{demoText(source.briefing)}</p>}
          {check && <p className={`dw-caption dw-learning-check${check.key === "websiteCheckFailed" ? " dw-learning-check-failed" : ""}`}>
            <Icon name="globe" size={16} />{t(check.key, check)}</p>}
        </div>
      )}
      {learned.passId && (
        <div className="dw-learning-effort">
          <span className="dw-field-label">{t("taskEffortLabel")}</span>
          <MenuSelect variant="compact" label={t("taskEffortLabel")} value={learned.effort} disabled={!backendConnected || past}
            onChange={setEffort} options={EFFORTS.map(([value, key]) => ({ value, label: t(key) }))} />
          {learned.effortBy === "you" && <span className="dw-caption">{t("effortSetByYou")}</span>}
        </div>
      )}
      <TaskLibrary learned={learned} past={past} backendConnected={backendConnected} onLink={changeLink} />
      {suggestsDone(row.completion_status, learned, dismissed) && (
        <div className="dw-evidence dw-pencilled dw-done-suggestion" role="status">
          <Icon name="agent" size={16} />
          <span>{t("doneSuggestion")}</span>
          <span className="dw-done-suggestion-actions">
            <button type="button" className="dw-button" disabled={!backendConnected} onClick={() => onStatus(row, "done")}>
              <Icon name="check" size={18} />{t("markDoneAction")}</button>
            <button type="button" className="dw-button dw-button-quiet" onClick={() => setDismissed(true)}>{t("notNowAction")}</button>
          </span>
        </div>
      )}
      <Checklist base={base} title={task.title} learned={learned} past={past} minutes={task.duration_minutes}
        backendConnected={backendConnected} onChanged={setLearned} onAskAva={onAskAva} />
      {offersContinue(row.completion_status, learned) && (
        <AvaOnly>
          <button type="button" className="dw-button" disabled={!backendConnected}
            onClick={() => onAskAva(continueRequest(task.title, t), true)}><Icon name="talk" size={18} />{t("continueNextSession")}</button>
        </AvaOnly>
      )}
      {error && <p className="dw-alert" role="alert">{error}</p>}
    </section>
  );
}

/**
 * A Learn task's references: the Library items it links besides its checklist's own, each with Unlink, and Link
 * from Library for the items it doesn't use yet. The Library never makes one here. A past day's links change
 * only through Ava.
 * @param {object} props
 * @param {object} props.learned - The task's checklist and links, as the service gives them.
 * @param {boolean} props.past - Whether the task is on a past day.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(sourceId: string, link: boolean) => void} props.onLink - Link an item to the task, or unlink one.
 */
function TaskLibrary({ learned, past, backendConnected, onLink }) {
  const { t, demoText } = useI18n();
  const { items } = useLibrary();
  const { models } = useContext(ModelsContext);
  const choices = linkChoices(items, [learned.sourceId, ...learned.references.map((reference) => reference.id)]);

  return (
    <div className="dw-task-library">
      <h3 className="dw-section-label">{t("taskLibraryTitle")}</h3>
      {learned.references.length ? (
        <ul className="dw-task-library-items">
          {learned.references.map((reference) => {
            const item = items.find((candidate) => candidate.id === reference.id);
            return (
              <li key={reference.id}>
                {item ? <BriefingButton source={item} /> : <span>{demoText(reference.title)}</span>}
                {!past && <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected}
                  onClick={() => onLink(reference.id, false)}>{t("taskLibraryUnlinkAction")}</button>}
              </li>
            );
          })}
        </ul>
      ) : <p className="dw-muted">{t("taskLibraryNone")}</p>}
      {/* The items suggested for a Learn task come from Library search, which needs its model. */}
      {!past && backendConnected && !isReady(models, "embedding") && <NeedsModel feature="suggestionsNeedModel" role="embedding" />}
      {past ? <p className="dw-caption">{t("taskLibraryPast")}</p> : choices.length > 0 && (
        <ActionMenu plain label={t("taskLibraryLinkAction")} text={t("taskLibraryLinkAction")} disabled={!backendConnected}
          items={choices.map((item) => ({ value: item.id, label: demoText(sourceView(item).name) }))}
          onChoose={(sourceId) => onLink(sourceId, true)} />
      )}
    </div>
  );
}

/**
 * A task's checklist: one line per item, a real checkbox in front of each, ticked by clicking or Space.
 * Today or later, items are added, renamed in place, removed, and reordered by dragging or with Alt+↑ and
 * Alt+↓; Enter on an item renames it, and Backspace or Delete in an empty name removes it. Each item says
 * whose it is, or how its source's latest reading found it, and when it was ticked. A past day's
 * checklist is read-only, and Ava's card changes it.
 * @param {object} props
 * @param {string} props.base - The task's learning-task route.
 * @param {string} props.title - The task's title, as Ava is asked about it.
 * @param {object} props.learned - The task's checklist, as the service gives it.
 * @param {boolean} props.past - Whether the task is on a past day.
 * @param {number} props.minutes - The task's length, set against what its sections left will take.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(learned: object) => void} props.onChanged - Show the checklist as the service now has it.
 * @param {(text: string, send?: boolean) => void} props.onAskAva - Open Ava with a request.
 */
function Checklist({ base, title, learned, past, minutes, backendConnected, onChanged, onAskAva }) {
  const { t, language, demoText } = useI18n();
  const [renaming, setRenaming] = useState(null);
  const [name, setName] = useState("");
  const [adding, setAdding] = useState(false);
  const [newItem, setNewItem] = useState("");
  const [dragging, setDragging] = useState(null);
  const [focusId, setFocusId] = useState(null);
  const [said, setSaid] = useState("");
  const [error, setError] = useState("");
  const boxes = useRef({});
  const keysNote = useId();
  const { checklist, progress } = learned;
  // Once its source has a pace, what the sections still unticked will take.
  const paceLine = taskPaceLine(learned.pace, progress, minutes, t, language);
  const editable = !past && backendConnected;

  // A moved or renamed item keeps the keyboard's focus.
  useEffect(() => {
    if (!focusId) return;
    boxes.current[focusId]?.focus();
    setFocusId(null);
  }, [focusId, learned]);

  /**
   * Make a change to the checklist, then show it as the service has it.
   * @param {string} path - The route.
   * @param {string} method - The request's method.
   * @param {object} [body] - What it sends.
   * @returns {Promise<boolean>} Whether it was made.
   */
  async function change(path, method, body) {
    setError("");
    try {
      onChanged(await api(path, { method, ...(body ? { body: JSON.stringify(body) } : {}) }));
      return true;
    } catch (caught) {
      setError(caught.message);
      return false;
    }
  }

  /**
   * Tick or untick an item at once, as the service then keeps it with its time; a refusal puts it back.
   * @param {object} entry - The item.
   * @param {boolean} done - Ticked or not.
   */
  async function tick(entry, done) {
    const shown = checklist.map((other) => (other.id === entry.id ? { ...other, tickedAt: done ? new Date().toISOString() : null } : other));
    const count = shown.filter((other) => other.tickedAt).length;
    onChanged({ ...learned, checklist: shown, progress: { done: count, total: shown.length }, allTicked: count === shown.length });
    if (!(await change(`${base}/checklist/${encodeURIComponent(entry.id)}/tick`, "POST", { done }))) onChanged(learned);
  }

  /**
   * Move an item to a place on the list, saying where it went.
   * @param {object} entry - The item.
   * @param {number} index - Its new place, from 0.
   * @param {boolean} [keepFocus=false] - Keep the keyboard on it, as a key moved it.
   */
  async function move(entry, index, keepFocus = false) {
    if (await change(`${base}/checklist/${encodeURIComponent(entry.id)}/move`, "POST", { index })) {
      setSaid(t("checklistMoved", { item: demoText(entry.title), position: index + 1, total: checklist.length }));
      if (keepFocus) setFocusId(entry.id);
    }
  }

  /**
   * An item's keys: Alt+↑ and Alt+↓ move it, Enter renames it.
   * @param {KeyboardEvent} event - The key pressed on its checkbox.
   * @param {object} entry - The item.
   */
  function onItemKey(event, entry) {
    if (!editable) return;
    if (event.altKey && (event.key === "ArrowUp" || event.key === "ArrowDown")) {
      event.preventDefault();
      const index = movedIndex(checklist, entry.id, event.key === "ArrowUp" ? -1 : 1);
      if (index !== null) move(entry, index, true);
    } else if (event.key === "Enter") {
      event.preventDefault();
      startRename(entry);
    }
  }

  /** @param {object} entry - The item to rename in place. */
  function startRename(entry) {
    setRenaming(entry.id);
    setName(entry.title);
  }

  /**
   * Keep an item's new name; an empty one changes nothing.
   * @param {object} entry - The item.
   */
  async function rename(entry) {
    const words = name.trim();
    setRenaming(null);
    if (words && words !== entry.title) await change(`${base}/checklist/${encodeURIComponent(entry.id)}`, "PUT", { title: words });
    setFocusId(entry.id);
  }

  /**
   * The rename box's keys: Enter keeps the name, Escape leaves it, Backspace or Delete in an empty name removes the item.
   * @param {KeyboardEvent} event - The key pressed.
   * @param {object} entry - The item.
   */
  function onRenameKey(event, entry) {
    if (event.key === "Enter") { event.preventDefault(); rename(entry); }
    else if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); setRenaming(null); setFocusId(entry.id); }
    else if ((event.key === "Backspace" || event.key === "Delete") && !name) { event.preventDefault(); setRenaming(null); remove(entry); }
  }

  /** @param {object} entry - The item to remove. */
  async function remove(entry) {
    await change(`${base}/checklist/${encodeURIComponent(entry.id)}`, "DELETE");
  }

  /**
   * Add the item typed, keeping the box open for the next one.
   * @param {Event} event - The add form's submit.
   */
  async function add(event) {
    event.preventDefault();
    const words = newItem.trim();
    if (!words) return;
    if (await change(`${base}/checklist`, "POST", { title: words })) setNewItem("");
  }

  // A past task without a checklist has none to show, and none can be made for it.
  if (past && !checklist.length) return null;
  return (
    <div className="dw-checklist">
      <div className="dw-checklist-head">
        <h3 className="dw-section-label">{t("checklistHeading")}</h3>
        {progress.total > 0 && <span className="dw-caption">{t("checklistProgress", progress)}</span>}
      </div>
      {paceLine && <Lead parts={paceLine} className="dw-pace-line" />}
      {checklist.length > 0 ? (
        <ol className="dw-checklist-items" aria-describedby={editable && checklist.length > 1 ? keysNote : undefined}>
          {checklist.map((entry, index) => {
            const mark = checklistMark(entry, learned.sourceOrigin);
            const box = `dw-check-${entry.id}`;
            return (
              <li key={entry.id} className={`dw-checklist-item${entry.tickedAt ? " dw-checklist-ticked" : ""}${dragging === entry.id ? " dw-checklist-dragging" : ""}`}
                draggable={editable && renaming !== entry.id}
                onDragStart={(event) => { setDragging(entry.id); event.dataTransfer.effectAllowed = "move"; event.dataTransfer.setData("text/plain", entry.id); }}
                onDragEnd={() => setDragging(null)}
                onDragOver={(event) => { if (dragging) event.preventDefault(); }}
                onDrop={(event) => {
                  event.preventDefault();
                  const moved = checklist.find((other) => other.id === dragging);
                  setDragging(null);
                  if (moved && moved.id !== entry.id) move(moved, index);
                }}>
                {editable && <span className="dw-checklist-grip" title={t("checklistMoveLabel", { item: demoText(entry.title) })} aria-hidden="true">
                  <Icon name="grip" size={16} /></span>}
                <input type="checkbox" id={box} ref={(node) => { boxes.current[entry.id] = node; }} checked={Boolean(entry.tickedAt)}
                  disabled={!editable} onKeyDown={(event) => onItemKey(event, entry)}
                  onChange={(event) => tick(entry, event.target.checked)} />
                {renaming === entry.id ? (
                  <input className="dw-checklist-rename" autoFocus maxLength={200} value={name}
                    aria-label={t("checklistRenameLabel", { item: demoText(entry.title) })}
                    onChange={(event) => setName(event.target.value)} onKeyDown={(event) => onRenameKey(event, entry)} onBlur={() => rename(entry)} />
                ) : (
                  <label htmlFor={box} className="dw-checklist-text">
                    <span className="dw-checklist-title">{demoText(entry.title)}</span>
                    {mark && <span className="dw-chip dw-chip-small">{t(mark)}</span>}
                    {entry.tickedAt && <span className="dw-caption">{t("checklistTickedAt", { when: dateTime(entry.tickedAt, language) })}</span>}
                  </label>
                )}
                {editable && renaming !== entry.id && (
                  <span className="dw-checklist-actions">
                    <button type="button" className="dw-button dw-button-quiet dw-icon-only" aria-label={t("checklistRenameLabel", { item: demoText(entry.title) })}
                      onClick={() => startRename(entry)}><Icon name="pencil" size={16} /></button>
                    <button type="button" className="dw-button dw-button-quiet dw-icon-only" aria-label={t("checklistRemoveLabel", { item: demoText(entry.title) })}
                      onClick={() => remove(entry)}><Icon name="x" size={16} /></button>
                  </span>
                )}
              </li>
            );
          })}
        </ol>
      ) : !past && <p className="dw-muted">{t("checklistEmpty")}</p>}
      {editable && checklist.length > 1 && <p id={keysNote} className="dw-caption">{t("checklistKeysNote")}</p>}
      {editable && (adding ? (
        <form className="dw-checklist-add" onSubmit={add}>
          <input autoFocus maxLength={200} value={newItem} aria-label={t("checklistNewItemLabel")} placeholder={t("checklistNewItemLabel")}
            onChange={(event) => setNewItem(event.target.value)}
            onKeyDown={(event) => { if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); setAdding(false); } }} />
          <button type="submit" className="dw-button" disabled={!newItem.trim()}><Icon name="plus" size={18} />{t("checklistAddAction")}</button>
          <button type="button" className="dw-button dw-button-quiet" onClick={() => setAdding(false)}>{t("cancel")}</button>
        </form>
      ) : (
        <button type="button" className="dw-button dw-button-quiet dw-checklist-add-button" onClick={() => setAdding(true)}>
          <Icon name="plus" size={18} />{t("checklistAddAction")}</button>
      ))}
      {past && checklist.length > 0 && (
        <AvaOnly>
          <p className="dw-checklist-past"><Icon name="lock" size={16} /><span>{t("checklistPastNote")}</span>
            <button type="button" className="dw-link" onClick={() => onAskAva(pastTickRequest(title, checklist, t))}>
              <Icon name="talk" size={16} />{t("checklistAskAva")}</button></p>
        </AvaOnly>
      )}
      <p className="dw-visually-hidden" role="status">{said}</p>
      {error && <p className="dw-alert" role="alert">{error}</p>}
    </div>
  );
}
