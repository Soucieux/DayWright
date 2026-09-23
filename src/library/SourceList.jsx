import { useRef, useState } from "react";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { Segmented } from "../ui/Segmented";
import { addedLabel, sourceView } from "./libraryData";

/** Rows listed before the user asks for all of them. */
const FIRST_ROWS = 10;

/** Interface text for each kind of source. */
const KIND_KEYS = { markdown: "kindMarkdown", pdf: "kindPdf", word: "kindWord", file: "kindFile", note: "kindNote" };

/**
 * One source: its name, kind, how much text is indexed, when it was added, and a two-step Remove.
 * @param {object} props
 * @param {object} props.source - The source as the local service lists it.
 * @param {object} props.view - Its name, kind and group, from `sourceView`.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be removed.
 * @param {() => Promise<void>} props.onRemove - Remove the source; throws to report a failure.
 */
function SourceRow({ source, view, today, backendConnected, onRemove }) {
  const { t, language, demoText } = useI18n();
  const [confirming, setConfirming] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState("");
  const removeRef = useRef(null);
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
              {view.fromWeb && <span className="dw-chip dw-chip-small dw-chip-caution"><Icon name="globe" size={14} />{t("fromTheWeb")}</span>}
              <span className="dw-caption dw-source-meta">{kind} · {size} · {added}</span>
            </span>
          </span>
        </th>
        <td>{kind}</td>
        <td>{size}</td>
        <td>{added}</td>
        <td>
          <button type="button" className="dw-icon-button" ref={removeRef} aria-label={t("removeSourceLabel", { name })} aria-expanded={confirming}
            disabled={!backendConnected} onClick={() => setConfirming(true)}><Icon name="trash" size={18} /></button>
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
 * Every source in the Library, filterable by name and by files or notes, newest first.
 * @param {object} props
 * @param {object[]} props.sources - The sources, newest first.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether anything can be removed.
 * @param {(source: object) => Promise<void>} props.onRemove - Remove a source; throws to report a failure.
 */
export function SourceList({ sources, today, backendConnected, onRemove }) {
  const { t, demoText } = useI18n();
  const [group, setGroup] = useState("all");
  const [query, setQuery] = useState("");
  const [showAll, setShowAll] = useState(false);
  const filterRef = useRef(null);
  const views = sources.map((source) => [source, sourceView(source)]);
  const count = (name) => views.filter(([, view]) => view.group === name).length;
  const needle = query.trim().toLocaleLowerCase();
  const matching = views.filter(([, view]) => (group === "all" || view.group === group)
    && (!needle || demoText(view.name).toLocaleLowerCase().includes(needle)));
  const shown = showAll ? matching : matching.slice(0, FIRST_ROWS);

  /**
   * Remove a source, then keep focus in the list once its row is gone.
   * @param {object} source - The source to remove.
   */
  async function remove(source) {
    await onRemove(source);
    filterRef.current?.focus();
  }

  if (!sources.length) {
    return (
      <section className="dw-card dw-empty-card">
        <span className="dw-empty-tile"><Icon name="book" size={24} /></span>
        <h2 className="dw-title">{t("libraryEmptyTitle")}</h2>
        <p className="dw-body-lg">{t("libraryEmptyBody")}</p>
      </section>
    );
  }

  return (
    <section className="dw-card dw-sources" aria-labelledby="dw-sources-title">
      <h2 id="dw-sources-title" className="dw-heading">{t("sourcesHeading")} <span className="dw-caption">{sources.length}</span></h2>
      <div className="dw-sources-tools">
        <label className="dw-search">
          <Icon name="search" size={18} /><span className="dw-visually-hidden">{t("filterSources")}</span>
          <input ref={filterRef} type="search" value={query} placeholder={t("filterByName")} onChange={(event) => setQuery(event.target.value)} />
        </label>
        <Segmented label={t("showSources")} value={group} onChange={setGroup}
          options={[["all", `${t("filterAll")} · ${sources.length}`], ["files", `${t("filesFilter")} · ${count("files")}`], ["notes", `${t("notesFilter")} · ${count("notes")}`]]} />
        <span className="dw-caption dw-sources-order">{t("newestFirst")}</span>
      </div>
      {matching.length ? (
        <table className="dw-sources-table">
          <caption className="dw-visually-hidden">{t("sourcesHeading")}</caption>
          <thead>
            <tr>
              <th scope="col">{t("columnName")}</th><th scope="col">{t("columnKind")}</th><th scope="col">{t("columnText")}</th>
              <th scope="col">{t("columnAdded")}</th><th scope="col"><span className="dw-visually-hidden">{t("columnActions")}</span></th>
            </tr>
          </thead>
          <tbody>
            {shown.map(([source, view]) => (
              <SourceRow key={source.id} source={source} view={view} today={today} backendConnected={backendConnected} onRemove={() => remove(source)} />
            ))}
          </tbody>
        </table>
      ) : <p className="dw-muted dw-sources-none">{t("noSourcesMatch")}</p>}
      <p className="dw-sources-foot">
        <span className="dw-caption">{t("showingCount", { shown: shown.length, total: matching.length })}</span>
        {shown.length < matching.length && <button type="button" className="dw-link" onClick={() => setShowAll(true)}>{t("showAllAction")}</button>}
      </p>
    </section>
  );
}
