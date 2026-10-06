import { useRef, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { AreaTag } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { addedLabel, openActions, sourceView } from "./libraryData";
import { LibraryLinksSheet } from "./LibrarySheets";
import { BriefingButton } from "./SourceBriefing";

/** Rows a group lists before the user asks for all of them. */
const FIRST_ROWS = 10;

/** Interface text for each kind of item. */
const KIND_KEYS = { markdown: "kindMarkdown", pdf: "kindPdf", word: "kindWord", file: "kindFile", note: "kindNote", website: "kindWebsite" };

/** The icon for each group of items. */
const GROUP_ICONS = { folders: "file", websites: "globe", files: "file", notes: "note" };

/** What removing an item does, by its group. */
const REMOVE_KEYS = { folders: "removeFolderFileConsequence", websites: "removeWebsiteConsequence", files: "removeFileConsequence",
  notes: "removeSourceConsequence" };

/**
 * The goal an item is linked to, as a chip.
 * @param {object} props
 * @param {{title: string}} props.goal - The goal.
 */
export function GoalChip({ goal }) {
  const { demoText } = useI18n();
  return <span className="dw-chip dw-chip-small dw-library-goal"><Icon name="target" size={14} />{demoText(goal.title)}</span>;
}

/**
 * A short list of Library items, as a goal's sheet and an area's page show them: each one's name,
 * which opens its briefing, and its kind, or its goal when the list spans several.
 * @param {object} props
 * @param {object[]} props.items - The items, newest first.
 * @param {object[]} [props.goals] - The user's goals, to name each item's goal; left out, no goal is shown.
 */
export function LibraryItemList({ items, goals }) {
  const { t } = useI18n();
  return (
    <ul className="dw-library-items">
      {items.map((item) => {
        const view = sourceView(item);
        const goal = goals?.find((entry) => entry.id === item.goalId);
        return (
          <li key={item.id}>
            <Icon name={GROUP_ICONS[view.group]} size={16} />
            <BriefingButton source={item} className="dw-library-item-name" />
            {goal ? <GoalChip goal={goal} /> : <span className="dw-caption">{t(KIND_KEYS[view.kind])}</span>}
          </li>
        );
      })}
    </ul>
  );
}

/**
 * One Library item: its name, which opens its briefing, its kind and size or place in its folder, its
 * area and goal, and when it was added; Open where it opens, Edit for its area and goal, and a
 * two-step Remove. A connected folder's file not found in it is marked so, with Locate beside Remove.
 * @param {object} props
 * @param {object} props.source - The item as the local service lists it.
 * @param {object|undefined} props.folder - Its connected folder, for a folder's file.
 * @param {object|undefined} props.goal - Its goal, if it has one that still exists.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be changed.
 * @param {() => void} props.onEdit - Change its area and goal.
 * @param {() => void} props.onLocate - Find a missing file's new place in its folder.
 * @param {() => Promise<void>} props.onRemove - Remove it; throws to report a failure.
 */
function SourceRow({ source, folder, goal, today, backendConnected, onEdit, onLocate, onRemove }) {
  const { t, language, demoText } = useI18n();
  const [confirming, setConfirming] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState("");
  const removeRef = useRef(null);
  const view = sourceView(source);
  const name = demoText(view.name);
  const opens = openActions(source, folder);
  const missing = source.origin === "folder" && source.missing;
  const size = t("charactersCount", { count: new Intl.NumberFormat(language === "zh" ? "zh-Hans" : "en-GB").format(source.characterCount || 0) });
  const detail = source.origin === "folder" ? source.relativePath
    : source.origin === "website" ? `${source.address} · ${t("opensInBrowser")}` : size;
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

  /**
   * Open the item in its app, on its folder's website, or in the browser.
   * @param {"app"|"website"} where - Where it opens.
   */
  async function open(where) {
    setError("");
    try {
      await api(`/api/sources/${encodeURIComponent(source.id)}/open`, { method: "POST", body: JSON.stringify({ where }) });
    } catch (caught) {
      setError(t("openFailed", { reason: caught.message }));
    }
  }

  return (
    <>
      <tr className={[confirming && "dw-source-removing", missing && "dw-source-missing"].filter(Boolean).join(" ") || undefined}>
        <th scope="row">
          <span className="dw-source-name">
            <Icon name={GROUP_ICONS[view.group]} size={20} />
            <span className="dw-source-title">
              <BriefingButton source={source} />
              <span className="dw-caption dw-source-kind">{t(KIND_KEYS[view.kind])} · {detail}</span>
              {missing && <span className="dw-source-flag"><Icon name="alert" size={14} />{t("fileNotFound")}</span>}
              <span className="dw-source-meta"><AreaTag domain={source.domain} />{goal && <GoalChip goal={goal} />}<span className="dw-caption">{added}</span></span>
              {error && <span className="dw-alert" role="alert">{error}</span>}
            </span>
          </span>
        </th>
        <td><AreaTag domain={source.domain} /></td>
        <td>{goal ? <GoalChip goal={goal} /> : <span className="dw-caption">{t("noGoalOption")}</span>}</td>
        <td>{added}</td>
        <td>
          <span className="dw-source-actions">
            {missing && <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected || !folder?.found}
              onClick={onLocate}>{t("locateAction")}</button>}
            {(opens.app || opens.browser) && (
              <button type="button" className="dw-button dw-button-quiet dw-icon-only" disabled={!backendConnected}
                aria-label={t("openNameLabel", { name })} title={opens.browser ? t("opensInBrowser") : t("openNameLabel", { name })}
                onClick={() => open("app")}><Icon name={opens.browser ? "globe" : "external"} size={18} /></button>
            )}
            {opens.website && (
              <button type="button" className="dw-button dw-button-quiet dw-icon-only" disabled={!backendConnected}
                aria-label={t("openOnWebsiteLabel", { name })} title={t("openOnWebsiteLabel", { name })}
                onClick={() => open("website")}><Icon name="globe" size={18} /></button>
            )}
            <button type="button" className="dw-button dw-button-quiet dw-icon-only" aria-label={t("libraryLinksLabel", { name })}
              title={t("libraryLinksLabel", { name })} disabled={!backendConnected} onClick={onEdit}><Icon name="pencil" size={18} /></button>
            <button type="button" className="dw-button dw-button-quiet dw-icon-only" ref={removeRef} aria-label={t("removeSourceLabel", { name })}
              title={missing ? t("removeFromLibraryAction") : t("removeSourceLabel", { name })} aria-expanded={confirming}
              disabled={!backendConnected} onClick={() => setConfirming(true)}><Icon name="trash" size={18} /></button>
          </span>
        </td>
      </tr>
      {confirming && (
        <tr className="dw-source-confirm-row">
          <td colSpan={5}>
            <div className="dw-confirm-remove" role="alertdialog" aria-labelledby={`dw-remove-${source.id}`} aria-describedby={`dw-remove-${source.id}-body`}>
              <p className="dw-step">{t("stepTwoOfTwo")}</p>
              <h3 id={`dw-remove-${source.id}`}>{t("removeSourceQuestion", { name })}</h3>
              <p id={`dw-remove-${source.id}-body`}>{t(REMOVE_KEYS[view.group])}</p>
              {error && <p className="dw-alert" role="alert">{error}</p>}
              <div className="dw-actions">
                <button type="button" className="dw-button dw-button-danger" disabled={removing} onClick={remove}><Icon name="trash" size={18} />
                  {removing ? t("removingLabel") : missing ? t("removeFromLibraryAction") : t("removeSourceAction")}</button>
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
 * One group of the Library's items, as a card: its heading, anything its heading needs, such as a
 * folder's Refresh, and its items, the first few until the user asks for all.
 * @param {object} props
 * @param {string} props.id - The group's id, for its heading.
 * @param {string} props.icon - The group's icon.
 * @param {React.ReactNode} props.heading - The group's heading.
 * @param {React.ReactNode} [props.head] - What follows the heading, such as a folder's place and actions.
 * @param {object[]} props.sources - The group's items, in their order.
 * @param {object[]} props.folders - The connected folders.
 * @param {object[]} props.goals - The user's goals, to name each item's goal as it is now.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be changed.
 * @param {() => Promise<void>} props.onChanged - Refresh after an item's area or goal changes.
 * @param {(source: object) => void} props.onLocate - Find a missing file's new place.
 * @param {(source: object) => Promise<void>} props.onRemove - Remove an item; throws to report a failure.
 */
export function SourceGroup({ id, icon, heading, head, sources, folders, goals, today, backendConnected, onChanged, onLocate, onRemove }) {
  const { t, demoText } = useI18n();
  const [showAll, setShowAll] = useState(false);
  const [editing, setEditing] = useState(null);
  const headingRef = useRef(null);
  const shown = showAll ? sources : sources.slice(0, FIRST_ROWS);
  const goalOf = (source) => goals.find((goal) => goal.id === source.goalId);
  const folderOf = (source) => folders.find((folder) => folder.id === source.folderId);

  /**
   * Remove an item, then keep focus in the group once its row is gone.
   * @param {object} source - The item to remove.
   */
  async function remove(source) {
    await onRemove(source);
    headingRef.current?.focus();
  }

  return (
    <section className="dw-card dw-sources" aria-labelledby={`dw-library-${id}`}>
      <div className="dw-card-head">
        <h2 id={`dw-library-${id}`} className="dw-heading" ref={headingRef} tabIndex={-1}>
          <Icon name={icon} size={20} />{heading} <span className="dw-caption">{sources.length}</span></h2>
        {!head && <span className="dw-caption">{t("newestFirst")}</span>}
      </div>
      {head}
      {sources.length ? (
        <table className="dw-sources-table">
          <caption className="dw-visually-hidden">{heading}</caption>
          <thead>
            <tr>
              <th scope="col">{t("columnName")}</th><th scope="col">{t("fieldArea")}</th><th scope="col">{t("fieldGoal")}</th>
              <th scope="col">{t("columnAdded")}</th><th scope="col"><span className="dw-visually-hidden">{t("columnActions")}</span></th>
            </tr>
          </thead>
          <tbody>
            {shown.map((source) => (
              <SourceRow key={source.id} source={source} folder={folderOf(source)} goal={goalOf(source)} today={today}
                backendConnected={backendConnected} onEdit={() => setEditing(source)} onLocate={() => onLocate(source)}
                onRemove={() => remove(source)} />
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

/**
 * A connected folder's place and actions under its heading: where it is, the website its files are
 * also on, and Refresh; or, when it isn't found at its place, a notice that keeps everything from it
 * and offers Update location, with Refresh paused.
 * @param {object} props
 * @param {object} props.folder - The connected folder.
 * @param {boolean} props.backendConnected - Whether anything can be changed.
 * @param {() => Promise<void>} props.onRefreshed - Reload the Library after a refresh.
 * @param {() => void} props.onRelocate - Give the folder its new place.
 */
export function FolderHead({ folder, backendConnected, onRefreshed, onRelocate }) {
  const { t } = useI18n();
  const [refreshing, setRefreshing] = useState(false);
  const [result, setResult] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    setRefreshing(true);
    setError("");
    try {
      const done = await api(`/api/sources/folder/${encodeURIComponent(folder.id)}/refresh`, { method: "POST" });
      setResult(done.found ? t("refreshedLine", { added: done.added.length, changed: done.changed.length + done.moved.length,
        missing: done.missing.length }) : "");
      await onRefreshed();
    } catch (caught) {
      setError(caught.message);
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div className="dw-folder-head">
      {folder.found ? (
        <p className="dw-caption dw-folder-place"><span className="dw-folder-path">{folder.path}</span>
          {folder.website && <span>{t("folderWebsiteLine", { site: folder.website })}</span>}</p>
      ) : (
        <div className="dw-folder-notice" role="status">
          <Icon name="alert" size={18} />
          <span><strong>{t("folderNotFound", { path: folder.path })}</strong><span className="dw-caption">{t("folderNotFoundBody")}</span></span>
          <button type="button" className="dw-button" disabled={!backendConnected} onClick={onRelocate}>
            <Icon name="folder" size={18} />{t("updateLocationAction")}</button>
        </div>
      )}
      <div className="dw-folder-actions">
        <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected || refreshing || !folder.found}
          aria-label={t("refreshFolderLabel", { title: folder.title })} onClick={refresh}>
          <Icon name="repeat" size={18} />{refreshing ? t("refreshingLabel") : t("refreshAction")}</button>
        {result && <span className="dw-caption" role="status">{result}</span>}
        {error && <span className="dw-alert" role="alert">{error}</span>}
      </div>
    </div>
  );
}
