import { useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { AreaTag, DOMAINS } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { PageBanners } from "../ui/PageBanners";
import { Segmented } from "../ui/Segmented";
import { libraryOf } from "./libraryData";
import { LibrarySearch } from "./LibrarySearch";
import { SourceList } from "./SourceList";

/** The area switch's choices: every area, then each one. */
const AREA_FILTERS = ["all", ...DOMAINS];

/**
 * The Library: the notes and imported files the user keeps on this Mac, each in an area and, if
 * chosen, a goal in it. An area switch shows every note and file or one area's; the search box
 * searches them all, the area on show first. New note and Import files ask for the area and goal.
 * @param {object} props
 * @param {object} props.day - The day on show, for its goals and the page banners.
 * @param {string} props.today - Today's YYYY-MM-DD date.
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {{items: object[]|null, error: string}} props.library - The notes and files, newest first, or why they couldn't be loaded.
 * @param {string} [props.initialArea="all"] - The area the switch opens on, as an area page's Library card sets it.
 * @param {(kind: "note"|"files") => void} props.onAdd - Write a note or import files.
 * @param {(text: string) => void} props.onAskAva - Open Ava with a question typed in and not sent.
 * @param {() => Promise<void>} props.onChanged - Refresh what depends on the Library after a change.
 */
export function LibraryScreen({ day, today, backendConnected, library, initialArea = "all", onAdd, onAskAva, onChanged }) {
  const { t } = useI18n();
  const [area, setArea] = useState(initialArea);
  const items = library.items;
  const count = (domain) => libraryOf(items || [], { domain }).length;

  /**
   * Remove a note or file from the Library.
   * @param {object} source - The note or file.
   */
  async function removeSource(source) {
    await api(`/api/knowledge/sources/${encodeURIComponent(source.id)}`, { method: "DELETE" });
    await onChanged();
  }

  return (
    <main className="dw-page dw-library" tabIndex={-1}>
      <header className="dw-page-head">
        <div className="dw-records-title">
          <h1 className="dw-display">{t("navLibrary")}</h1>
          <Segmented label={t("fieldArea")} value={area} onChange={setArea}
            options={AREA_FILTERS.map((value) => [value, value === "all" ? `${t("filterAll")} · ${count(value)}`
              : <span key={value} className="dw-area-count"><AreaTag domain={value} plain /><span>{` · ${count(value)}`}</span></span>])} />
        </div>
        <div className="dw-page-actions">
          <button type="button" className="dw-button" disabled={!backendConnected} aria-label={t("newNoteAction")} onClick={() => onAdd("note")}>
            <Icon name="note" size={18} /><span className="dw-phone-hidden">{t("newNoteAction")}</span></button>
          <button type="button" className="dw-button dw-button-primary" disabled={!backendConnected} aria-label={t("importFilesAction")} onClick={() => onAdd("files")}>
            <Icon name="upload" size={18} /><span className="dw-phone-hidden">{t("importFilesAction")}</span></button>
        </div>
      </header>
      <p className="dw-offline-line"><Icon name="laptop" size={18} /><span>{t("libraryOfflineLine")}</span></p>
      <PageBanners day={day} backendConnected={backendConnected} />
      <div className="dw-page-body dw-library-body">
        <LibrarySearch domain={area} backendConnected={backendConnected} onAskAva={onAskAva} />
        {items ? (
          <SourceList key={area} sources={libraryOf(items, { domain: area })} total={items.length} goals={day.goals} today={today}
            backendConnected={backendConnected} onChanged={onChanged} onRemove={removeSource} />
        ) : (
          <section className="dw-card">
            <p className="dw-muted">{library.error ? t("libraryLoadFailed", { reason: library.error }) : backendConnected ? t("loadingLibrary") : t("libraryNeedsService")}</p>
          </section>
        )}
      </div>
    </main>
  );
}
