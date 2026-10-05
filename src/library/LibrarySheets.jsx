import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useI18n } from "../i18n";
import { linkableGoals } from "../records/taskDraft";
import { SheetForm } from "../records/SheetForm";
import { AreaTag, DOMAINS } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";
import { MenuSelect } from "../ui/MenuSelect";
import { Segmented } from "../ui/Segmented";
import { agentName } from "../ui/agentName";
import { importHeaders } from "./libraryData";

/** The largest file the local service imports, in bytes. */
const MAX_IMPORT_BYTES = 2_000_000;

/** File types the local service can read. */
const IMPORTABLE = /\.(md|markdown|pdf|docx)$/i;

/** How long the sheet waits after typing stops before asking for an area. */
const SUGGEST_DELAY_MS = 500;

/** How much of a note's text, from its start, the area suggestion reads, as the purpose rule does. */
const OPENING_CHARACTERS = 500;

/** The area a note or file starts in when it isn't added from an area or goal, until one is suggested or picked. */
const FIRST_AREA = "life";

/**
 * Send one chosen file to the local service to be read and indexed, in its area and goal. It never leaves this Mac.
 * @param {File} file - The chosen file.
 * @param {{domain: string, goalId: string|null}} links - The area and goal it joins.
 * @param {(key: string) => string} t - The interface text lookup, for the reasons checked here.
 * @returns {Promise<object>} The indexed file.
 * @throws {Error} With the reason the file wasn't imported.
 */
async function importFile(file, links, t) {
  if (!IMPORTABLE.test(file.name)) throw new Error(t("wrongFileType"));
  if (file.size > MAX_IMPORT_BYTES) throw new Error(t("fileTooLarge"));
  const response = await fetch("/api/knowledge/import", { method: "POST", headers: importHeaders(file.name, links), body: file });
  if (!response.ok) {
    const failure = await response.json().catch(() => ({}));
    throw new Error(failure.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

/**
 * A note's or file's area, required, and its goal in that area, optional. Choosing another area
 * clears the goal, as a goal belongs to one area.
 * @param {object} props
 * @param {{domain: string, goalId: string}} props.links - The area and goal chosen so far; no goal is "".
 * @param {(links: {domain: string, goalId: string}) => void} props.onChange - Choose an area or goal.
 * @param {object[]} props.goals - The user's goals.
 * @param {string} [props.keepGoalId=""] - A goal already linked, or the one it is added from, kept on offer even when it isn't active.
 * @param {string|null} [props.suggested=null] - The area the Orchestrator suggested, shown while it is the one chosen.
 */
function LinkFields({ links, onChange, goals, keepGoalId = "", suggested = null }) {
  const { t, demoText } = useI18n();
  const goalsHere = linkableGoals(goals, links.domain, keepGoalId);
  return (
    <>
      <div className="dw-field"><span className="dw-field-label">{t("fieldArea")}</span>
        <Segmented label={t("fieldArea")} value={links.domain} onChange={(domain) => onChange({ domain, goalId: "" })}
          options={DOMAINS.map((domain) => [domain, <AreaTag key={domain} domain={domain} plain />])} />
        {suggested && suggested === links.domain && (
          <p className="dw-evidence dw-pencilled"><Icon name="agent" size={16} />
            <span>{t("libraryAreaSuggested", { agent: agentName("orchestrator", t), area: t(suggested) })}</span></p>
        )}
      </div>
      <div className="dw-field"><span className="dw-field-label">{t("fieldGoal")} <span className="dw-optional">{t("optionalLabel")}</span></span>
        <MenuSelect label={t("fieldGoal")} value={links.goalId} onChange={(goalId) => onChange({ ...links, goalId })}
          options={[{ value: "", label: t("noGoalOption") }, ...goalsHere.map((goal) => ({ value: goal.id, label: demoText(goal.title) }))]} />
        <span className="dw-caption">{t("libraryGoalNote")}</span>
      </div>
    </>
  );
}

/**
 * Add to the Library: write a note, or import files, into an area and, if chosen, a goal in it.
 * Added from a goal or an area, it starts linked to it; otherwise the Orchestrator suggests an area
 * from the note's title and opening text, or the files' names, until the user picks one. Files that
 * fail to import stay chosen, with the reason, while the rest are saved.
 * @param {object} props
 * @param {"note"|"files"} props.kind - Whether it opens to write a note or to import files.
 * @param {{domain: string, goalId: string|null}|null} props.links - The area and goal it was added from, if any.
 * @param {object[]} props.goals - The user's goals.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {(names: string[]) => Promise<void>} props.onSaved - Refresh after notes or files were saved, naming them.
 * @param {() => void} props.onClose - Close the sheet.
 */
export function LibraryAddSheet({ kind: firstKind, links: from, goals, backendConnected, onSaved, onClose }) {
  const { t } = useI18n();
  const [kind, setKind] = useState(firstKind);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [files, setFiles] = useState([]);
  const [links, setLinks] = useState({ domain: from?.domain || FIRST_AREA, goalId: from?.goalId || "" });
  // The area the Orchestrator suggested, until the user picks one, or the sheet was opened from one.
  const [picked, setPicked] = useState(Boolean(from));
  const [suggested, setSuggested] = useState(null);
  const fileRef = useRef(null);
  const subject = kind === "note" ? { title, detail: text.slice(0, OPENING_CHARACTERS) }
    : { title: files.map((file) => file.name).join(", "), detail: "" };
  const asking = backendConnected && !picked && Boolean(subject.title.trim());

  useEffect(() => {
    if (!asking) return undefined;
    let live = true;
    const timer = setTimeout(() => {
      api("/api/areas/suggest", { method: "POST", body: JSON.stringify({ title: subject.title.slice(0, 200), detail: subject.detail }) })
        .then((answer) => {
          if (!live) return;
          setSuggested(answer.domain);
          setLinks({ domain: answer.domain, goalId: "" });
        })
        // Without a suggestion the area stays as it is; the user chooses it either way.
        .catch(() => {});
    }, SUGGEST_DELAY_MS);
    return () => { live = false; clearTimeout(timer); };
  }, [asking, subject.title, subject.detail]);

  const chosen = { domain: links.domain, goalId: links.goalId || null };

  async function submit() {
    if (kind === "note") {
      await api("/api/knowledge/sources", { method: "POST", body: JSON.stringify({ title: title.trim(), text: text.trim(), sourceType: "note", ...chosen }) });
      await onSaved([title.trim()]);
      return;
    }
    if (!files.length) throw new Error(t("chooseFilesFirst"));
    const saved = [];
    const failed = [];
    for (const file of files) {
      try {
        await importFile(file, chosen, t);
        saved.push(file.name);
      } catch (caught) {
        failed.push([file, caught.message]);
      }
    }
    if (saved.length) await onSaved(saved);
    if (failed.length) {
      setFiles(failed.map(([file]) => file));
      throw new Error(failed.map(([file, reason]) => t("importFailed", { name: file.name, reason })).join(" "));
    }
  }

  return (
    <SheetForm title={t("addToLibraryTitle")} submitLabel={kind === "note" ? t("saveNoteAction") : t("importFilesAction")}
      note={t("notePrivacy")} backendConnected={backendConnected} onSubmit={submit} onClose={onClose}>
      <Segmented label={t("addToLibraryTitle")} value={kind} onChange={setKind}
        options={[["note", <><Icon key="icon" name="note" size={18} />{t("newNoteAction")}</>], ["files", <><Icon key="icon" name="upload" size={18} />{t("importFilesAction")}</>]]} />
      {kind === "note" ? (
        <>
          <label className="dw-field">{t("fieldTitle")}
            <input required pattern=".*\S.*" maxLength={200} value={title}
              onInvalid={(event) => event.target.setCustomValidity(t("noteTitleNeeded"))}
              onChange={(event) => { event.target.setCustomValidity(""); setTitle(event.target.value); }} /></label>
          <label className="dw-field">{t("noteTextLabel")}
            <textarea required rows={8} value={text}
              onInvalid={(event) => event.target.setCustomValidity(t("noteTextNeeded"))}
              onChange={(event) => { event.target.setCustomValidity(""); setText(event.target.value); }} /></label>
        </>
      ) : (
        <div className="dw-field"><span className="dw-field-label">{t("filesLabel")}</span>
          <div className="dw-file-choice">
            <button type="button" className="dw-button" onClick={() => fileRef.current?.click()}><Icon name="upload" size={18} />{t("chooseFilesAction")}</button>
            <input ref={fileRef} type="file" multiple accept=".md,.markdown,.pdf,.docx" hidden
              onChange={(event) => { setFiles([...(event.target.files || [])]); event.target.value = ""; }} />
            {files.length > 0 && <ul className="dw-file-list">{files.map((file) => <li key={file.name}><Icon name="file" size={16} />{file.name}</li>)}</ul>}
          </div>
          <span className="dw-caption">{t("importLimits")}</span>
        </div>
      )}
      <LinkFields links={links} goals={goals} keepGoalId={from?.goalId || ""} suggested={picked ? null : suggested}
        onChange={(next) => { setPicked(true); setLinks(next); }} />
    </SheetForm>
  );
}

/**
 * Change a note's or file's area and goal.
 * @param {object} props
 * @param {object} props.source - The note or file, as the local service lists it.
 * @param {string} props.name - Its name as listed.
 * @param {object[]} props.goals - The user's goals.
 * @param {boolean} props.backendConnected - Whether anything can be saved.
 * @param {() => Promise<void>} props.onSaved - Refresh after the change is saved.
 * @param {() => void} props.onClose - Close the sheet.
 */
export function LibraryLinksSheet({ source, name, goals, backendConnected, onSaved, onClose }) {
  const { t } = useI18n();
  const [links, setLinks] = useState({ domain: source.domain, goalId: source.goalId || "" });

  async function submit() {
    await api(`/api/knowledge/sources/${encodeURIComponent(source.id)}`, {
      method: "PUT", body: JSON.stringify({ domain: links.domain, goalId: links.goalId || null }),
    });
    await onSaved();
  }

  return (
    <SheetForm title={t("libraryLinksTitle", { name })} submitLabel={t("saveAction")} backendConnected={backendConnected}
      onSubmit={submit} onClose={onClose}>
      <LinkFields links={links} goals={goals} keepGoalId={source.goalId || ""} onChange={setLinks} />
    </SheetForm>
  );
}
