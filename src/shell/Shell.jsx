import { useI18n } from "../i18n";
import { AreaGlyph } from "../ui/AreaTag";
import { Icon } from "../ui/Icon";

/** The four places in bar order: id, icon, label key. */
const PLACES = [
  ["today", "sun", "navToday"],
  ["calendar", "calendar", "navCalendar"],
  ["records", "records", "navRecords"],
  ["library", "book", "navLibrary"],
];

/** Record sections in side-list order: the section id, its icon and its label key. */
const RECORD_SECTIONS = [["goals", "target", "goalsTitle"], ["tasks", "check", "tasksTitle"]];

/** Areas in side-list order: the section id, the domains whose glyphs mark it, and its label key. */
const AREA_SECTIONS = [["learning", ["learning"], "learning"], ["life", ["life", "rest"], "lifeAndRest"], ["finance", ["finance"], "finance"]];

/**
 * Show a long label on wide windows and a short one on narrow ones.
 * @param {object} props
 * @param {string} props.long - Text for wide windows.
 * @param {string} props.short - Text for narrow windows.
 */
function Label({ long, short }) {
  return <><span className="dw-long">{long}</span><span className="dw-short">{short}</span></>;
}

/**
 * Where the day's records are kept: on this Mac, in the demo workspace, or nowhere yet.
 * @param {object} props
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {boolean} props.demoMode - Whether the local service is serving the demo workspace.
 */
function SavePill({ backendConnected, demoMode }) {
  const { t } = useI18n();
  if (!backendConnected) {
    return <span className="dw-pill dw-pill-caution"><Icon name="alert" size={16} /><Label long={t("savePreview")} short={t("savePreviewShort")} /></span>;
  }
  if (demoMode) {
    return <span className="dw-pill dw-pill-demo"><Icon name="laptop" size={16} /><Label long={t("saveDemo")} short={t("saveDemoShort")} /></span>;
  }
  return <span className="dw-pill dw-pill-saved"><Icon name="laptop" size={16} /><Label long={t("saveLocal")} short={t("saveLocalShort")} /></span>;
}

/**
 * The local chat model's state as the local service reports it.
 * @param {object} props
 * @param {object} props.model - The model status; `state` is `ready`, `available` or `unavailable`.
 * @param {boolean} [props.compact] - Use the short label, to leave room for the network pill.
 */
function ModelPill({ model, compact = false }) {
  const { t } = useI18n();
  const [dot, long, short] = model?.state === "ready"
    ? ["dw-dot-on", "modelReady", "modelReadyShort"]
    : model?.state === "available"
      ? ["dw-dot-idle", "modelStandby", "modelStandbyShort"]
      : ["dw-dot-off", "modelUnavailable", "modelUnavailableShort"];
  return (
    <span className="dw-pill dw-pill-plain">
      <Icon name="chip" size={16} /><span className={`dw-dot ${dot}`} aria-hidden="true" />
      {compact ? t(short) : <Label long={t(long)} short={t(short)} />}
    </span>
  );
}

/**
 * Today's online lookups, shown only once something has gone online; it opens the network log.
 * @param {object} props
 * @param {number} props.count - Requests that left this Mac today.
 * @param {() => void} props.onOpen - Open the network log.
 */
function NetworkPill({ count, onOpen }) {
  const { t } = useI18n();
  if (!count) return null;
  return (
    <button type="button" className="dw-pill dw-pill-caution dw-pill-button" aria-haspopup="dialog" onClick={onOpen}>
      <Icon name="globe" size={16} /><Label long={t("onlineLookupsToday", { count })} short={t("onlineLookupsShort", { count })} />
    </button>
  );
}

/** Switch the interface between English and Simplified Chinese without leaving the screen. */
function LanguageToggle() {
  const { t, language, setLanguage } = useI18n();
  return (
    <div className="dw-lang" role="group" aria-label={t("languageLabel")}>
      <button type="button" lang="en" aria-pressed={language === "en"} onClick={() => setLanguage("en")}>EN</button>
      <button type="button" lang="zh-Hans" aria-pressed={language === "zh"} onClick={() => setLanguage("zh")}>中文</button>
    </div>
  );
}

/** The slot the existing app icon occupies until its small copy is added. */
function AppIcon() {
  return <span className="dw-app-icon" aria-hidden="true" />;
}

/**
 * The desktop title bar: brand, the four places, the local-first status cluster and Talk.
 * @param {object} props
 * @param {string} props.place - The place on show.
 * @param {(place: string) => void} props.onPlace - Go to a place.
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {boolean} props.demoMode - Whether the demo workspace is loaded.
 * @param {object} props.model - The local model's status.
 * @param {number} props.lookupsToday - Requests that left this Mac today.
 * @param {() => void} props.onNetwork - Open the network log.
 * @param {boolean} props.talkOpen - Whether Talk is open.
 * @param {() => void} props.onTalk - Open or close Talk.
 */
export function TopBar({ place, onPlace, backendConnected, demoMode, model, lookupsToday, onNetwork, talkOpen, onTalk }) {
  const { t } = useI18n();
  return (
    <header className="dw-topbar">
      <div className="dw-topbar-lead">
        <div className="dw-brand"><AppIcon /><span className="dw-wordmark">DayWright</span></div>
        <nav className="dw-places" aria-label={t("mainNavigation")}>
          {PLACES.map(([id, icon, key]) => (
            <button key={id} type="button" aria-current={place === id ? "page" : undefined} onClick={() => onPlace(id)}>
              <Icon name={icon} size={18} />{t(key)}
            </button>
          ))}
        </nav>
      </div>
      <div className="dw-topbar-tail">
        <SavePill backendConnected={backendConnected} demoMode={demoMode} />
        <NetworkPill count={lookupsToday} onOpen={onNetwork} />
        <ModelPill model={model} compact={lookupsToday > 0} />
        <LanguageToggle />
        <button type="button" className="dw-talk" aria-pressed={talkOpen} aria-keyshortcuts="Meta+K" onClick={onTalk}>
          <Icon name="talk" size={18} />{t("navTalk")}<span className="dw-kbd" aria-hidden="true">⌘K</span>
        </button>
      </div>
    </header>
  );
}

/**
 * The phone header: brand and language on one row, compact save, network and model state below.
 * @param {object} props
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {boolean} props.demoMode - Whether the demo workspace is loaded.
 * @param {object} props.model - The local model's status.
 * @param {number} props.lookupsToday - Requests that left this Mac today.
 * @param {() => void} props.onNetwork - Open the network log.
 */
export function PhoneHeader({ backendConnected, demoMode, model, lookupsToday, onNetwork }) {
  return (
    <header className="dw-phone-header">
      <div className="dw-phone-brand"><AppIcon /><span className="dw-wordmark">DayWright</span><div className="dw-spacer" /><LanguageToggle /></div>
      <div className="dw-phone-status">
        <SavePill backendConnected={backendConnected} demoMode={demoMode} />
        <NetworkPill count={lookupsToday} onOpen={onNetwork} />
        <ModelPill model={model} />
      </div>
    </header>
  );
}

/**
 * The phone's one bottom bar: four places with Talk in the centre, always labelled.
 * @param {object} props
 * @param {string} props.place - The place on show.
 * @param {(place: string) => void} props.onPlace - Go to a place.
 * @param {boolean} props.talkOpen - Whether Talk is open.
 * @param {() => void} props.onTalk - Open or close Talk.
 */
export function BottomBar({ place, onPlace, talkOpen, onTalk }) {
  const { t } = useI18n();
  const tab = ([id, icon, key]) => (
    <button key={id} type="button" aria-current={place === id ? "page" : undefined} onClick={() => onPlace(id)}>
      <span className="dw-tab-mark"><Icon name={icon} size={20} /></span><span className="dw-tab-label">{t(key)}</span>
    </button>
  );
  return (
    <nav className="dw-bottombar" aria-label={t("mainNavigation")}>
      {PLACES.slice(0, 2).map(tab)}
      <button type="button" className="dw-tab-talk" aria-pressed={talkOpen} onClick={onTalk}>
        <span className="dw-tab-mark"><Icon name="talk" size={20} /></span><span className="dw-tab-label">{t("navTalk")}</span>
      </button>
      {PLACES.slice(2).map(tab)}
    </nav>
  );
}

/**
 * The Records side list: goals and tasks, then the three areas, and how Rest fits among them.
 * @param {object} props
 * @param {string} props.section - The record section on show.
 * @param {(section: string) => void} props.onSection - Show another record section.
 * @param {number} props.goalCount - How many goals there are.
 */
export function RecordsNav({ section, onSection, goalCount }) {
  const { t } = useI18n();
  const link = (id, mark, key, count) => (
    <button key={id} type="button" aria-current={section === id ? "page" : undefined} onClick={() => onSection(id)}>
      <span className="dw-records-mark">{mark}</span><span className="dw-records-label">{t(key)}</span>{count !== undefined && <span className="dw-caption">{count}</span>}
    </button>
  );
  return (
    <nav className="dw-records-nav" aria-label={t("navRecords")}>
      <h2 className="dw-heading dw-records-heading">{t("navRecords")}</h2>
      {RECORD_SECTIONS.map(([id, icon, key]) => link(id, <Icon name={icon} size={18} />, key, id === "goals" ? goalCount : undefined))}
      <small>{t("areasHeading")}</small>
      {AREA_SECTIONS.map(([id, domains, key]) => link(id, domains.map((domain) => <AreaGlyph key={domain} domain={domain} />), key))}
      <p className="dw-records-note">{t("areasNote")}</p>
    </nav>
  );
}
