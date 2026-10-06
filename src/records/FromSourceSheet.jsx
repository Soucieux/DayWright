import { useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { FolderConnector } from "../library/FolderSheets";
import { useLibrary } from "../library/libraryContext";
import { sourceView } from "../library/libraryData";
import { BriefingButton } from "../library/SourceBriefing";
import { Icon } from "../ui/Icon";
import { MenuSelect } from "../ui/MenuSelect";
import { Segmented } from "../ui/Segmented";
import { Sheet } from "../ui/Sheet";
import { goalPicks } from "./goalSources";

/** Where goals can come from, in the order the switch shows them. */
const ORIGINS = [["folder", "fromSourceFolder", "folder"], ["website", "fromSourceWebsite", "globe"], ["library", "fromSourceLibrary", "book"]];

/**
 * The first-level entries of a folder or a source to tick, each becoming a Learning goal, its
 * second-level headings shown under it as the topics that goal would have.
 * @param {object} props
 * @param {{key: string, sourceId: string, title: string, topics: string[]}[]} props.entries - The entries.
 * @param {Set<string>} props.ticked - The entries ticked.
 * @param {(ticked: Set<string>) => void} props.onChange - Tick or untick entries.
 * @param {object[]} props.items - The Library's items, to brief a folder's file named by its entry.
 * @param {boolean} props.byFile - Whether each entry is a folder's file, so its name opens its briefing.
 */
function EntryChoice({ entries, ticked, onChange, items, byFile }) {
  const { t, demoText } = useI18n();
  if (!entries.length) return <p className="dw-muted">{t("fromSourceNoEntries")}</p>;

  function toggle(key, tick) {
    const next = new Set(ticked);
    if (tick) next.add(key); else next.delete(key);
    onChange(next);
  }

  return (
    <fieldset className="dw-entry-choice">
      <legend className="dw-caption">{t("fromSourceNote")}</legend>
      <ul>
        {entries.map((entry) => {
          const item = byFile && items.find((source) => source.id === entry.sourceId);
          return (
            <li key={entry.key}>
              <div className="dw-entry-head">
                <input type="checkbox" id={`dw-entry-${entry.key}`} checked={ticked.has(entry.key)}
                  aria-label={demoText(entry.title)} onChange={(event) => toggle(entry.key, event.target.checked)} />
                {item ? <BriefingButton source={item} /> : <label htmlFor={`dw-entry-${entry.key}`}>{demoText(entry.title)}</label>}
                <span className="dw-caption">{entry.topics.length === 1 ? t("entryOneTopic")
                  : entry.topics.length ? t("entryTopicsCount", { count: entry.topics.length }) : t("entryNoTopics")}</span>
              </div>
              {entry.topics.length > 0 && (
                <details className="dw-entry-topics">
                  <summary>{t("topicsLabel")}</summary>
                  <ol>{entry.topics.map((topic, index) => <li key={`${index}-${topic}`}>{demoText(topic)}</li>)}</ol>
                </details>
              )}
            </li>
          );
        })}
      </ul>
    </fieldset>
  );
}

/**
 * Learning goals from a source: pick a connected folder, or connect one; enter a website, looked up
 * this once with a banner while it is; or choose an item in the Library. Its first-level entries are
 * listed to tick, each becoming a Learning goal whose second-level headings become its topics; the
 * source joins the Library linked to its goals.
 * @param {object} props
 * @param {() => void} props.onBack - Go back to the New goal sheet.
 * @param {() => void} props.onClose - Close the sheet.
 */
export function FromSourceSheet({ onBack, onClose }) {
  const { t, demoText } = useI18n();
  const { items, folders, backendConnected, refresh, goalsMade } = useLibrary();
  const [origin, setOrigin] = useState(folders.length ? "folder" : "website");
  const [picked, setPicked] = useState(null);
  const [connecting, setConnecting] = useState(!folders.length);
  const [address, setAddress] = useState("");
  const [looking, setLooking] = useState("");
  const [entries, setEntries] = useState(null);
  const [ticked, setTicked] = useState(new Set());
  const [error, setError] = useState("");
  const [making, setMaking] = useState(false);
  const chosen = picked?.sourceId ? items.find((item) => item.id === picked.sourceId) : null;
  const offered = items.filter((item) => item.origin === "website" || item.outline?.length);

  /**
   * List what a connected folder or one source offers to tick.
   * @param {{folderId?: string, sourceId?: string}} pick - The folder or the source.
   */
  async function list(pick) {
    setPicked(pick);
    setEntries(null);
    setTicked(new Set());
    setError("");
    try {
      setEntries(await api(`/api/sources/entries?${new URLSearchParams(pick)}`));
    } catch (caught) {
      setError(caught.message);
    }
  }

  /**
   * Look a website up, this once, then list its headings. One already looked up isn't fetched again.
   * @param {object} site - The website, as the Library lists it.
   */
  async function lookUp(site) {
    setLooking(new URL(site.address).host);
    setError("");
    try {
      const found = await api(`/api/sources/${encodeURIComponent(site.id)}/look-up`, { method: "POST" });
      await refresh();
      if (found.outline.length) await list({ sourceId: found.id });
      else { setPicked({ sourceId: found.id }); setEntries([]); setError(t("siteTooLittle")); }
    } catch (caught) {
      setPicked({ sourceId: site.id });
      setError(caught.message);
    } finally {
      setLooking("");
    }
  }

  /**
   * Save the address typed, unless the Library has it, and look it up.
   * @param {Event} event - The form's submit.
   */
  async function website(event) {
    event.preventDefault();
    const typed = address.trim();
    const known = items.find((item) => item.origin === "website" && item.address === typed);
    try {
      const site = known || await api("/api/sources/website", { method: "POST",
        body: JSON.stringify({ address: typed, briefing: "", domain: "learning" }) });
      if (site.lookedUp) await list({ sourceId: site.id });
      else await lookUp(site);
    } catch (caught) {
      setError(caught.message);
    }
  }

  /**
   * Pick an item in the Library; a website not yet looked up is looked up first.
   * @param {string} sourceId - The item's id.
   */
  async function pickItem(sourceId) {
    const item = items.find((entry) => entry.id === sourceId);
    if (!item) return;
    if (item.origin === "website" && !item.lookedUp) await lookUp(item);
    else await list({ sourceId });
  }

  async function make() {
    setMaking(true);
    setError("");
    try {
      const made = await api("/api/goals/from-source", { method: "POST", body: JSON.stringify({ picks: goalPicks(entries, ticked) }) });
      await goalsMade(made.goals);
      onClose();
    } catch (caught) {
      setError(caught.message);
      setMaking(false);
    }
  }

  /**
   * Show another way to pick, clearing what the last one listed.
   * @param {string} next - `folder`, `website` or `library`.
   */
  function switchTo(next) {
    setOrigin(next);
    setPicked(null);
    setEntries(null);
    setError("");
  }

  return (
    <Sheet title={t("fromSourceTitle")} view={entries ? "entries" : origin} onClose={onClose}>
      <div className="dw-form dw-from-source">
        <Segmented label={t("fromSourceTitle")} value={origin} onChange={switchTo}
          options={ORIGINS.map(([value, key, icon]) => [value, <><Icon key="icon" name={icon} size={18} />{t(key)}</>])} />
        {origin === "folder" && (connecting ? (
          <FolderConnector backendConnected={backendConnected} onCancel={folders.length ? () => setConnecting(false) : undefined}
            onConnected={async (folder) => { await refresh(); setConnecting(false); await list({ folderId: folder.id }); }} />
        ) : (
          <div className="dw-field">
            <span className="dw-field-label">{t("pickFolderLabel")}</span>
            <MenuSelect label={t("pickFolderLabel")} value={picked?.folderId || ""} onChange={(folderId) => folderId && list({ folderId })}
              options={[{ value: "", label: t("chooseLibraryItem") },
                ...folders.map((folder) => ({ value: folder.id, label: folder.found ? folder.title : `${folder.title} · ${t("folderNotFound", { path: folder.path })}` }))]} />
            <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected} onClick={() => setConnecting(true)}>
              <Icon name="folder" size={18} />{t("connectFolderAction")}</button>
          </div>
        ))}
        {origin === "website" && (
          <form className="dw-field" onSubmit={website}>
            <label className="dw-field">{t("websiteAddressLabel")}
              <input type="url" inputMode="url" required spellCheck={false} placeholder="https://" maxLength={2000} pattern="https?://.+"
                value={address} onInvalid={(event) => event.target.setCustomValidity(t("websiteNeedsAddress"))}
                onChange={(event) => { event.target.setCustomValidity(""); setAddress(event.target.value); }} /></label>
            <span className="dw-caption">{t("websiteLookupOnce")}</span>
            <button type="submit" className="dw-button" disabled={!backendConnected || Boolean(looking)}>
              <Icon name="globe" size={18} />{t("lookIntoAction")}</button>
          </form>
        )}
        {origin === "library" && (
          <div className="dw-field">
            <span className="dw-field-label">{t("pickLibraryLabel")}</span>
            <MenuSelect label={t("pickLibraryLabel")} value={picked?.sourceId || ""} onChange={pickItem}
              options={[{ value: "", label: t("chooseLibraryItem") },
                ...offered.map((item) => ({ value: item.id, label: demoText(sourceView(item).name) }))]} />
          </div>
        )}
        {looking && <p className="dw-banner" role="status"><Icon name="globe" size={18} />{t("lookingIntoSite", { site: looking })}</p>}
        {chosen && <p className="dw-from-source-chosen"><Icon name={chosen.origin === "website" ? "globe" : "file"} size={18} /><BriefingButton source={chosen} /></p>}
        {error && <p className="dw-alert" role="alert">{error}</p>}
        {entries && <EntryChoice entries={entries} ticked={ticked} onChange={setTicked} items={items} byFile={Boolean(picked?.folderId)} />}
        <div className="dw-actions">
          <button type="button" className="dw-button dw-button-primary" disabled={!backendConnected || !ticked.size || making} onClick={make}>
            <Icon name="check" size={18} />{making ? t("savingLabel") : ticked.size === 1 ? t("makeOneGoalAction") : t("makeGoalsAction", { count: ticked.size })}</button>
          <button type="button" className="dw-button dw-button-quiet" onClick={onBack}><Icon name="left" size={18} />{t("backToNewGoal")}</button>
        </div>
      </div>
    </Sheet>
  );
}
