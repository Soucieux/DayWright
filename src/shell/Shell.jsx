import { useI18n } from "../i18n";
import { AreaGlyph, DOMAINS } from "../ui/AreaTag";
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
 * What stays on this Mac, in one pill: where the day's records are kept (here, in the demo
 * workspace, or nowhere yet) and the local chat model's state, in words. Its colour follows where the
 * records are kept.
 * @param {object} props
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {boolean} props.demoMode - Whether the local service is serving the demo workspace.
 * @param {object} props.model - The model status; `state` is `ready`, `available` or `unavailable`.
 */
function LocalPill({ backendConnected, demoMode, model }) {
  const { t } = useI18n();
  const [tone, icon, records] = !backendConnected ? ["caution", "alert", "statusPreview"]
    : demoMode ? ["demo", "laptop", "statusDemo"] : ["saved", "laptop", "statusSaved"];
  const state = model?.state === "ready" ? "modelReadyShort"
    : model?.state === "available" ? "modelStandbyShort" : "modelUnavailableShort";
  return (
    <span className={`dw-pill dw-pill-${tone}`}>
      <Icon name={icon} size={16} />{t(records)}<span aria-hidden="true">·</span>{t(state)}
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

/**
 * Ava's icon on its button, with a red dot at its corner while Ava has a message the user hasn't
 * seen; the dot is also said aloud, so colour is never the only sign.
 * @param {object} props
 * @param {number} props.size - The icon's size in CSS pixels.
 * @param {boolean} props.unread - Whether Ava has a message the user hasn't seen.
 */
function TalkMark({ size, unread }) {
  const { t } = useI18n();
  return (
    <span className="dw-talk-mark">
      <Icon name="talk" size={size} />
      {unread && <span className="dw-unread-dot"><span className="dw-visually-hidden">{t("avaNewMessage")}</span></span>}
    </span>
  );
}

/** The app icon, from the small copy the page also uses as its favicon; the wordmark beside it names the app. */
function AppIcon() {
  return <img className="dw-app-icon" src="/icon.png" alt="" width="34" height="34" />;
}

/**
 * The desktop title bar: brand, the four places, the local-first status cluster and Ava. In the
 * desktop app its empty space and brand move the window (`data-tauri-drag-region`); a browser
 * ignores the attribute.
 * @param {object} props
 * @param {string} props.place - The place on show.
 * @param {(place: string) => void} props.onPlace - Go to a place.
 * @param {boolean} props.backendConnected - Whether the local service answered.
 * @param {boolean} props.demoMode - Whether the demo workspace is loaded.
 * @param {object} props.model - The local model's status.
 * @param {number} props.lookupsToday - Requests that left this Mac today.
 * @param {() => void} props.onNetwork - Open the network log.
 * @param {boolean} props.talkOpen - Whether Ava is open.
 * @param {boolean} props.unread - Whether Ava has posted a message the user hasn't seen.
 * @param {() => void} props.onTalk - Open or close Ava.
 */
export function TopBar({ place, onPlace, backendConnected, demoMode, model, lookupsToday, onNetwork, talkOpen, unread, onTalk }) {
  const { t } = useI18n();
  return (
    <header className="dw-topbar" data-tauri-drag-region>
      <div className="dw-topbar-lead" data-tauri-drag-region>
        <div className="dw-brand" data-tauri-drag-region><AppIcon /><span className="dw-wordmark" data-tauri-drag-region>DayWright</span></div>
        <nav className="dw-places" aria-label={t("mainNavigation")}>
          {PLACES.map(([id, icon, key]) => (
            <button key={id} type="button" aria-current={place === id ? "page" : undefined} onClick={() => onPlace(id)}>
              <Icon name={icon} size={18} />{t(key)}
            </button>
          ))}
        </nav>
      </div>
      <div className="dw-topbar-tail" data-tauri-drag-region>
        <LocalPill backendConnected={backendConnected} demoMode={demoMode} model={model} />
        <NetworkPill count={lookupsToday} onOpen={onNetwork} />
        <LanguageToggle />
        <button type="button" className="dw-talk" aria-pressed={talkOpen} aria-keyshortcuts="Meta+K" data-ava-toggle onClick={onTalk}>
          <TalkMark size={18} unread={unread} />{t("navTalk")}<span className="dw-kbd" aria-hidden="true">⌘K</span>
        </button>
      </div>
    </header>
  );
}

/**
 * The phone header: brand and language on one row, the local status and any network use below.
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
        <LocalPill backendConnected={backendConnected} demoMode={demoMode} model={model} />
        <NetworkPill count={lookupsToday} onOpen={onNetwork} />
      </div>
    </header>
  );
}

/**
 * The phone's one bottom bar: four places with Ava in the centre, always labelled.
 * @param {object} props
 * @param {string} props.place - The place on show.
 * @param {(place: string) => void} props.onPlace - Go to a place.
 * @param {boolean} props.talkOpen - Whether Ava is open.
 * @param {boolean} props.unread - Whether Ava has posted a message the user hasn't seen.
 * @param {() => void} props.onTalk - Open or close Ava.
 */
export function BottomBar({ place, onPlace, talkOpen, unread, onTalk }) {
  const { t } = useI18n();
  const tab = ([id, icon, key]) => (
    <button key={id} type="button" aria-current={place === id ? "page" : undefined} onClick={() => onPlace(id)}>
      <span className="dw-tab-mark"><Icon name={icon} size={20} /></span><span className="dw-tab-label">{t(key)}</span>
    </button>
  );
  return (
    <nav className="dw-bottombar" aria-label={t("mainNavigation")}>
      {PLACES.slice(0, 2).map(tab)}
      <button type="button" className="dw-tab-talk" aria-pressed={talkOpen} data-ava-toggle onClick={onTalk}>
        <span className="dw-tab-mark"><TalkMark size={20} unread={unread} /></span><span className="dw-tab-label">{t("navTalk")}</span>
      </button>
      {PLACES.slice(2).map(tab)}
    </nav>
  );
}

/**
 * The Records side list: goals and tasks, then each area on its own row.
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
      {DOMAINS.map((domain) => link(domain, <AreaGlyph domain={domain} />, domain))}
      <p className="dw-records-note">{t("areasNote")}</p>
    </nav>
  );
}
