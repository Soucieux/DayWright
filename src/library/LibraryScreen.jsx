import { useState } from "react";
import { api } from "../api";
import { GuideButton } from "../guide/Guide";
import { useI18n } from "../i18n";
import { AreaTag, DOMAINS } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { PageBanners } from "../ui/PageBanners";
import { Segmented } from "../ui/Segmented";
import { AddWebsiteSheet, ConnectFolderSheet, LocateSheet, OpenWithSheet, UpdateLocationSheet } from "./FolderSheets";
import { libraryGroups, libraryOf, sourceView } from "./libraryData";
import { LibrarySearch } from "./LibrarySearch";
import { FolderHead, SourceGroup } from "./SourceList";

/** The area switch's choices: every area, then each one. */
const AREA_FILTERS = ["all", ...DOMAINS];

/** The groups after the folders, in the order they show, with their headings and icons. */
const GROUPS = [["website", "libraryWebsiteGroup", "globe"], ["file", "libraryFileGroup", "file"], ["note", "libraryNoteGroup", "note"]];

/**
 * The Library: the notes, imported files, connected folders' files and websites the user keeps, each
 * in an area and, if chosen, a goal in it, grouped by where each came from. An area switch shows every
 * item or one area's, and the search box searches the same ones. New note and Import files ask for
 * the area and goal; Connect folder reads a folder anywhere on this Mac, never changing it; Add website
 * saves a website by its address; Open with sets the app each kind of file opens in. A folder not
 * found at its place keeps everything from it, with Update location; a file not found in its folder
 * is marked, with Locate, and leaves only when the user removes it.
 * @param {object} props
 * @param {object} props.day - The day on show, for its goals and the page banners.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {{items: object[]|null, folders: object[], openWith: object, obsidian: boolean, error: string}} props.library -
 *   The items, newest first, the connected folders and Open with's apps, or why they couldn't be loaded.
 * @param {string} [props.initialArea="all"] - The area the switch opens on, as an area page's Library card sets it.
 * @param {(kind: "note"|"files") => void} props.onAdd - Write a note or import files.
 * @param {(text: string) => void} props.onAskAva - Open Ava with a question typed in and not sent.
 * @param {(saved?: string[]) => Promise<void>} props.onChanged - Refresh what depends on the Library after a change, naming what was saved.
 * @param {(screen: string) => void} props.onGuide - Open the Library card from the Guide.
 */
export function LibraryScreen({ day, today, backendConnected, library, initialArea = "all", onAdd, onAskAva, onChanged, onGuide }) {
  const { t, demoText } = useI18n();
  const [area, setArea] = useState(initialArea);
  // The sheet open over the Library, if any: connect, website, open-with, or a folder to relocate or a file to locate.
  const [sheet, setSheet] = useState(null);
  const items = library.items;
  const folders = library.folders || [];
  const count = (domain) => libraryOf(items || [], { domain }).length;
  const groups = items ? libraryGroups(items, folders, area) : null;
  const common = { folders, goals: day.goals, today, backendConnected, onChanged: () => onChanged(),
    onLocate: (source) => setSheet({ kind: "locate", source }), onRemove: removeSource };

  /**
   * Remove an item from the Library; a connected folder's file stays in its folder.
   * @param {object} source - The item.
   */
  async function removeSource(source) {
    await api(`/api/knowledge/sources/${encodeURIComponent(source.id)}`, { method: "DELETE" });
    await onChanged();
  }

  const empty = items && !items.length && !folders.length;
  return (
    <main className="dw-page dw-library" tabIndex={-1}>
      <header className="dw-page-head">
        <div className="dw-records-title">
          <div className="dw-title-guide">
            <h1 className="dw-display">{t("navLibrary")}</h1>
            <GuideButton screen="library" onOpen={onGuide} />
          </div>
          <Segmented label={t("fieldArea")} value={area} onChange={setArea}
            options={AREA_FILTERS.map((value) => [value, value === "all" ? `${t("filterAll")} · ${count(value)}`
              : <span key={value} className="dw-area-count"><AreaTag domain={value} plain /><span>{` · ${count(value)}`}</span></span>])} />
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
        <LibrarySearch domain={area} items={items || []} backendConnected={backendConnected} onAskAva={onAskAva} />
        {!items ? (
          <section className="dw-card">
            <p className="dw-muted">{library.error ? t("libraryLoadFailed", { reason: library.error }) : backendConnected ? t("loadingLibrary") : t("libraryNeedsService")}</p>
          </section>
        ) : empty ? (
          <section className="dw-card dw-empty-card">
            <span className="dw-empty-tile"><Icon name="book" size={24} /></span>
            <h2 className="dw-title">{t("libraryEmptyTitle")}</h2>
            <p className="dw-body-lg">{t("libraryEmptyBody")}</p>
          </section>
        ) : (
          <>
            {groups.folders.map(({ folder, items: inFolder }) => (
              <SourceGroup key={folder.id} id={folder.id} icon="folder" heading={t("libraryFolderGroup", { title: folder.title })}
                sources={inFolder} {...common}
                head={<FolderHead folder={folder} backendConnected={backendConnected} onRefreshed={() => onChanged()}
                  onRelocate={() => setSheet({ kind: "relocate", folder })} />} />
            ))}
            {GROUPS.filter(([origin]) => groups[origin].length).map(([origin, key, icon]) => (
              <SourceGroup key={origin} id={origin} icon={icon} heading={t(key)} sources={groups[origin]} {...common} />
            ))}
            {!groups.folders.length && GROUPS.every(([origin]) => !groups[origin].length) && (
              <section className="dw-card"><p className="dw-muted">{t("noItemsInArea")}</p></section>
            )}
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
      {sheet?.kind === "locate" && (
        <LocateSheet source={sheet.source} name={demoText(sourceView(sheet.source).name)} backendConnected={backendConnected}
          folder={folders.find((folder) => folder.id === sheet.source.folderId)}
          inFolder={(items || []).filter((item) => item.folderId === sheet.source.folderId)}
          onClose={() => setSheet(null)} onSaved={() => onChanged()} />
      )}
    </main>
  );
}
