import { useState } from "react";
import { api } from "../api";
import { GuideButton } from "../guide/Guide";
import { useI18n } from "../i18n";
import { Icon } from "../ui/Icon";
import { PageBanners } from "../ui/PageBanners";
import { TabList } from "../ui/TabList";
import { AddWebsiteSheet, ChangeFilesSheet, ConnectFolderSheet, LocateSheet, OpenWithSheet, UpdateLocationSheet } from "./FolderSheets";
import { LIBRARY_TABS, libraryCounts, libraryGroups, libraryTabOf, sourceView } from "./libraryData";
import { LibrarySearch } from "./LibrarySearch";
import { FolderHead, FolderRow, SourceGroup } from "./SourceList";

/** The groups after the folders, by their tab, with their headings and icons. */
const GROUPS = { website: ["libraryWebsiteGroup", "globe"], file: ["libraryFileGroup", "file"], note: ["libraryNoteGroup", "note"] };

/**
 * An empty tab of the Library: that it holds nothing yet, and its own way to add its kind.
 * @param {object} props
 * @param {string} props.tab - The tab's id (see LIBRARY_TABS).
 * @param {() => void} props.onAdd - Add an item of the tab's kind.
 * @param {boolean} props.backendConnected - Whether anything can be added.
 */
function TabEmpty({ tab, onAdd, backendConnected }) {
  const { t } = useI18n();
  const [, , empty, action, icon] = LIBRARY_TABS.find(([id]) => id === tab);
  return (
    <section className="dw-card dw-library-empty">
      <p className="dw-muted">{t(empty)}</p>
      <button type="button" className="dw-button" disabled={!backendConnected} onClick={onAdd}><Icon name={icon} size={18} />{t(action)}</button>
    </section>
  );
}

/**
 * The Library, for studying: the notes, imported files, connected folders and websites the user keeps, in four tabs
 * by where each came from, Folders, Websites, Files and Notes, each with its count, under the search box, which
 * searches them all whatever the tab, a folder's files included. Each connected folder is one row in Folders; opening
 * it shows its own view there, with its files, Refresh and Change files…, and a way back. An empty tab offers its own
 * way to add. New note and Import
 * files ask for the goal; Connect folder reads a folder anywhere on this Mac, never changing it; Add website saves a
 * website by its address; Open with sets the app each kind of file opens in. A folder not found at its place keeps
 * everything from it, with Update location; a file not found in its folder is marked, with Locate, and leaves only
 * when the user removes it.
 * @param {object} props
 * @param {object} props.day - The day on show, for its goals and the page banners.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {{items: object[]|null, folders: object[], openWith: object, obsidian: boolean, error: string}} props.library -
 *   The items, newest first, the connected folders and Open with's apps, or why they couldn't be loaded.
 * @param {string|null} props.tab - The tab last chosen while the app runs, or null before any is (see libraryTabOf).
 * @param {(tab: string) => void} props.onTab - Show a tab, and keep it as the Library's while the app runs.
 * @param {(kind: "note"|"files") => void} props.onAdd - Write a note or import files.
 * @param {(text: string) => void} props.onAskAva - Open Ava with a question typed in and not sent.
 * @param {(saved?: string[]) => Promise<void>} props.onChanged - Refresh what depends on the Library after a change, naming what was saved.
 * @param {(screen: string) => void} props.onGuide - Open the Library card from the Guide.
 */
export function LibraryScreen({ day, today, backendConnected, library, tab, onTab, onAdd, onAskAva, onChanged, onGuide }) {
  const { t } = useI18n();
  // The sheet open over the Library, if any: connect, website, open-with, or a folder to relocate or change the files
  // of, or a file to locate.
  const [sheet, setSheet] = useState(null);
  // The connected folder whose own view shows, by its id.
  const [openFolder, setOpenFolder] = useState(null);
  const items = library.items;
  const folders = library.folders || [];
  const groups = items ? libraryGroups(items, folders) : null;
  const counts = groups && libraryCounts(groups);
  const current = libraryTabOf(tab, counts || {});
  const allEmpty = Boolean(counts) && Object.values(counts).every((count) => count === 0);
  const shown = openFolder && groups?.folders.find(({ folder }) => folder.id === openFolder);
  // Each tab's own way to add its kind, offered when it is empty.
  const adders = { folders: () => setSheet({ kind: "connect" }), website: () => setSheet({ kind: "website" }),
    file: () => onAdd("files"), note: () => onAdd("note") };
  const common = { folders, today, backendConnected, onChanged: () => onChanged(),
    onLocate: (source) => setSheet({ kind: "locate", source }), onRemove: removeSource };

  /**
   * Remove an item from the Library; a connected folder's file stays in its folder.
   * @param {object} source - The item.
   */
  async function removeSource(source) {
    await api(`/api/knowledge/sources/${encodeURIComponent(source.id)}`, { method: "DELETE" });
    await onChanged();
  }

  return (
    <main className="dw-page dw-library" tabIndex={-1}>
      <header className="dw-page-head">
        <div className="dw-records-title">
          <div className="dw-title-guide">
            <h1 className="dw-display">{t("navLibrary")}</h1>
            <GuideButton screen="library" onFullGuide={onGuide} />
          </div>
        </div>
        <div className="dw-page-actions dw-library-actions">
          <button type="button" className="dw-button dw-button-quiet" disabled={!backendConnected} aria-label={t("openWithAction")}
            onClick={() => setSheet({ kind: "open-with" })}><Icon name="external" size={18} /><span className="dw-phone-hidden">{t("openWithAction")}</span></button>
          <button type="button" className="dw-button" disabled={!backendConnected} aria-label={t("addWebsiteAction")}
            onClick={() => setSheet({ kind: "website" })}><Icon name="globe" size={18} /><span className="dw-phone-hidden">{t("addWebsiteAction")}</span></button>
          <button type="button" className="dw-button" disabled={!backendConnected} aria-label={t("connectFolderAction")}
            onClick={() => setSheet({ kind: "connect" })}><Icon name="folder" size={18} /><span className="dw-phone-hidden">{t("connectFolderAction")}</span></button>
          <button type="button" className="dw-button" disabled={!backendConnected} aria-label={t("newNoteAction")} onClick={() => onAdd("note")}>
            <Icon name="note" size={18} /><span className="dw-phone-hidden">{t("newNoteAction")}</span></button>
          <button type="button" className="dw-button dw-button-primary" disabled={!backendConnected} aria-label={t("importFilesAction")} onClick={() => onAdd("files")}>
            <Icon name="upload" size={18} /><span className="dw-phone-hidden">{t("importFilesAction")}</span></button>
        </div>
      </header>
      <p className="dw-offline-line"><Icon name="laptop" size={18} /><span>{t("libraryOfflineLine")}</span></p>
      <PageBanners day={day} backendConnected={backendConnected} />
      <div className="dw-page-body dw-library-body">
        <LibrarySearch items={items || []} backendConnected={backendConnected} onAskAva={onAskAva} />
        {!items ? (
          <section className="dw-card">
            <p className="dw-muted">{library.error ? t("libraryLoadFailed", { reason: library.error }) : backendConnected ? t("loadingLibrary") : t("libraryNeedsService")}</p>
          </section>
        ) : (
          <>
            {allEmpty && <p className="dw-muted dw-library-intro">{t("libraryEmptyBody")}</p>}
            <TabList label={t("navLibrary")} idBase="dw-library"
              tabs={LIBRARY_TABS.map(([id, key]) => [id, t("libraryTabText", { name: t(key), count: counts[id] })])}
              names={Object.fromEntries(LIBRARY_TABS.map(([id, key]) => [id, t("libraryTabName", { name: t(key), count: counts[id] })]))}
              selected={current} onSelect={onTab} />
            <div id="dw-library-panel" role="tabpanel" aria-labelledby={`dw-library-tab-${current}`}>
              {!counts[current] ? (
                <TabEmpty tab={current} onAdd={adders[current]} backendConnected={backendConnected} />
              ) : current === "folders" ? (
                shown ? (
                  <>
                    <button type="button" className="dw-back" onClick={() => setOpenFolder(null)}><Icon name="left" size={18} />{t("navLibrary")} / {shown.folder.title}</button>
                    <SourceGroup id={shown.folder.id} icon="folder" heading={shown.folder.title} sources={shown.items} {...common}
                      head={<FolderHead folder={shown.folder} backendConnected={backendConnected} onRefreshed={() => onChanged()}
                        onRelocate={() => setSheet({ kind: "relocate", folder: shown.folder })}
                        onChangeFiles={() => setSheet({ kind: "files", folder: shown.folder })} />} />
                  </>
                ) : (
                  <section className="dw-card dw-sources">
                    <ul className="dw-folder-rows">
                      {groups.folders.map(({ folder, items: inFolder }) => (
                        <FolderRow key={folder.id} folder={folder} items={inFolder} backendConnected={backendConnected}
                          onOpen={() => setOpenFolder(folder.id)} onRelocate={() => setSheet({ kind: "relocate", folder })} />
                      ))}
                    </ul>
                  </section>
                )
              ) : (
                <SourceGroup id={current} icon={GROUPS[current][1]} heading={t(GROUPS[current][0])} labelledBy={`dw-library-tab-${current}`}
                  sources={groups[current]} {...common} />
              )}
            </div>
          </>
        )}
      </div>
      {sheet?.kind === "connect" && (
        <ConnectFolderSheet backendConnected={backendConnected} onClose={() => setSheet(null)}
          onConnected={(folder) => onChanged([folder.title])} />
      )}
      {sheet?.kind === "website" && (
        <AddWebsiteSheet backendConnected={backendConnected} onClose={() => setSheet(null)} onSaved={(site) => onChanged([site.title])} />
      )}
      {sheet?.kind === "open-with" && (
        <OpenWithSheet openWith={library.openWith || {}} obsidian={Boolean(library.obsidian)} backendConnected={backendConnected}
          onClose={() => setSheet(null)} onSaved={() => onChanged()} />
      )}
      {sheet?.kind === "relocate" && (
        <UpdateLocationSheet folder={sheet.folder} backendConnected={backendConnected} onClose={() => setSheet(null)} onSaved={() => onChanged()} />
      )}
      {sheet?.kind === "files" && (
        <ChangeFilesSheet folder={sheet.folder} inFolder={(items || []).filter((item) => item.folderId === sheet.folder.id)}
          backendConnected={backendConnected} onClose={() => setSheet(null)} onSaved={() => onChanged()} />
      )}
      {sheet?.kind === "locate" && (
        <LocateSheet source={sheet.source} name={sourceView(sheet.source).name} backendConnected={backendConnected}
          folder={folders.find((folder) => folder.id === sheet.source.folderId)}
          inFolder={(items || []).filter((item) => item.folderId === sheet.source.folderId)}
          onClose={() => setSheet(null)} onSaved={() => onChanged()} />
      )}
    </main>
  );
}
