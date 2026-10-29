import { Fragment, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { DemoBanner } from "../ui/DemoBanner";
import { Icon } from "../ui/Icon";
import { PHONE_WIDTH, useViewport } from "../ui/viewport";
import guide from "./guide.json";
import { guideRows, guideSections, popoverPlace } from "./guideCards";

/**
 * One card: its icon in a circle of its section's colour beside its title, For and Do as labelled
 * lines, and its Rule in one callout of the same colour. The labels always show, so colour is never
 * the only sign.
 * @param {object} props
 * @param {object} props.card - The card, as guide.json holds it.
 * @param {{id: string}} props.section - The section it belongs to, which gives its colour.
 */
function GuideCard({ card, section }) {
  const titleId = useId();
  return (
    <article className={`dw-card dw-guide-card dw-guide-${section.id}`} data-guide-card={card.id} tabIndex={-1} aria-labelledby={titleId}>
      <div className="dw-guide-card-head">
        <span className="dw-guide-icon"><Icon name={card.icon} size={20} /></span>
        <h3 id={titleId} className="dw-heading">{card.title}</h3>
      </div>
      <p className="dw-guide-line"><span className="dw-guide-label">{guide.labels.for}</span> {card.for}</p>
      <p className="dw-guide-line"><span className="dw-guide-label">{guide.labels.do}</span> {card.do}</p>
      <p className="dw-guide-rule"><span className="dw-guide-label">{guide.labels.rule}</span> {card.rule}</p>
    </article>
  );
}

/**
 * Sections of cards in one grid, in English whatever the interface's language: each section's heading
 * in its colour on a row of its own, then its cards, two to a row, or one where the room is narrow, as
 * on a phone or in a "?"'s popover. Every card is the size of the tallest. A heading can take focus, so
 * the Guide can open at its section.
 * @param {object} props
 * @param {object[]} props.sections - The sections to show, from guideSections.
 */
export function GuideCards({ sections }) {
  return (
    <div className="dw-guide" lang="en">
      <div className="dw-guide-grid" style={{ "--dw-guide-rows-two": guideRows(sections, 2), "--dw-guide-rows-one": guideRows(sections, 1) }}>
        {sections.map((section) => (
          <Fragment key={section.id}>
            <h2 className={`dw-guide-section dw-guide-${section.id}`} data-guide-section={section.id} tabIndex={-1}>{section.title}</h2>
            {section.cards.map((card) => <GuideCard key={card.id} card={card} section={section} />)}
          </Fragment>
        ))}
      </div>
    </div>
  );
}

/**
 * The cards a screen's "?" opens, under their sections.
 * @param {object} props
 * @param {string} props.screen - The screen, as guide.json's `screens` names it.
 */
export function ScreenGuide({ screen }) {
  return <GuideCards sections={guideSections(guide, screen)} />;
}

/**
 * The Guide: every card in its five sections. Opened from one of Ava's See Guide links, it brings that card into view
 * and moves focus to it; opened from a "?"'s Open the full Guide, or from the top bar on a screen with a "?", it does
 * the same with that screen's section, its heading at the top.
 * @param {object} props
 * @param {{card?: string, section?: string, at: number}|null} props.focus - The card or section asked for, and when, so
 *   asking again moves to it again.
 * @param {boolean} props.demoMode - Whether the demo is open, which its banner says here too.
 */
export function GuideScreen({ focus, demoMode }) {
  const pageRef = useRef(null);

  useEffect(() => {
    if (!focus) return;
    const target = pageRef.current?.querySelector(focus.card ? `[data-guide-card="${focus.card}"]` : `[data-guide-section="${focus.section}"]`);
    target?.scrollIntoView({ block: focus.card ? "center" : "start" });
    target?.focus({ preventScroll: true });
  }, [focus]);

  return (
    <main className="dw-page dw-guide-page" tabIndex={-1} ref={pageRef} lang="en">
      <header className="dw-page-head"><h1 className="dw-display">{guide.title}</h1></header>
      {demoMode && <DemoBanner />}
      <GuideCards sections={guideSections(guide)} />
    </main>
  );
}

/**
 * A screen's cards in a popover by its "?": the screen's name and ✕, the cards, scrolling inside, then Open the full
 * Guide. It sits under the "?" with its pointer at it, shifted to stay on screen, or above it when there's no room
 * below (see popoverPlace), and follows it as the window changes; on a phone it fills the screen. Nothing behind it is
 * dimmed or moved, and a side panel stays open. Focus moves to its name on opening. Escape, ✕ or the "?" again close
 * it, focus going back to the "?"; a press anywhere else closes it and leaves focus where the press puts it, as does
 * moving focus out of it. It isn't modal, so nothing traps focus.
 * @param {object} props
 * @param {string} props.id - Its id, which its "?" controls.
 * @param {string} props.screen - The screen whose cards it holds.
 * @param {{current: HTMLElement|null}} props.anchor - Its "?".
 * @param {(back: boolean) => void} props.onClose - Close it, focus going back to the "?" when `back`.
 * @param {() => void} props.onFullGuide - Open the Guide at the screen's section.
 */
function GuidePopover({ id, screen, anchor, onClose, onFullGuide }) {
  const boxRef = useRef(null);
  const phone = useViewport().width <= PHONE_WIDTH;
  const [place, setPlace] = useState(null);

  // Measured before anything is drawn, and again whenever the window or anything holding the "?" moves.
  useLayoutEffect(() => {
    if (phone) return undefined;
    /** Place the popover by the "?" as the window and the "?" now stand. */
    const follow = () => {
      const box = boxRef.current;
      if (!box || !anchor.current) return;
      setPlace(popoverPlace(anchor.current.getBoundingClientRect(), { width: box.offsetWidth, height: box.offsetHeight },
        { width: window.innerWidth, height: window.innerHeight }));
    };
    follow();
    window.addEventListener("resize", follow);
    document.addEventListener("scroll", follow, true);
    return () => {
      window.removeEventListener("resize", follow);
      document.removeEventListener("scroll", follow, true);
    };
  }, [phone, anchor]);

  useEffect(() => {
    boxRef.current?.querySelector(".dw-guide-popover-title")?.focus();
    /** Close the popover, leaving focus where it is, for a press outside it and its "?". */
    const onDown = (event) => {
      if (boxRef.current?.contains(event.target) || anchor.current?.contains(event.target)) return;
      onClose(false);
    };
    /**
     * Close the popover alone on Escape, never Ava or a side panel holding its "?" too, focus going back to its "?":
     * caught on its way in, before their own, wherever focus is, as a click on its words leaves focus on the page.
     */
    const onKey = (event) => {
      if (event.key !== "Escape") return;
      event.stopPropagation();
      onClose(true);
    };
    document.addEventListener("pointerdown", onDown, true);
    document.addEventListener("keydown", onKey, true);
    return () => {
      document.removeEventListener("pointerdown", onDown, true);
      document.removeEventListener("keydown", onKey, true);
    };
  }, []);

  /**
   * Focus moving out of the popover, as Tab past its last control does, closes it. A press decides for itself (see the
   * pointerdown above): pressing its "?", WebKit moves focus to what holds the "?", which is left alone here.
   * @param {FocusEvent} event - The focus leaving one of its parts.
   */
  function onBlur(event) {
    const next = event.relatedTarget;
    if (next && !event.currentTarget.contains(next) && !next.contains(anchor.current)) onClose(false);
  }

  const style = phone || !place ? undefined : { left: place.left, top: place.top, "--dw-pointer": `${place.pointer}px` };
  return createPortal(
    <section id={id} ref={boxRef} className={`dw-guide-popover${place && !phone ? ` is-${place.placement}` : ""}`} style={style}
      role="dialog" aria-labelledby={`${id}-title`} lang="en" onBlur={onBlur}
      onPointerDown={(event) => event.stopPropagation()}>
      <span className="dw-guide-popover-pointer" aria-hidden="true" />
      <header className="dw-guide-popover-head">
        <h2 id={`${id}-title`} className="dw-heading dw-guide-popover-title" tabIndex={-1}>{guide.screenNames[screen]}</h2>
        <button type="button" className="dw-button dw-button-quiet dw-icon-only" aria-label={guide.labels.close} onClick={() => onClose(true)}>
          <Icon name="x" size={18} /></button>
      </header>
      <div className="dw-guide-popover-body"><ScreenGuide screen={screen} /></div>
      <footer className="dw-guide-popover-foot">
        <button type="button" className="dw-link dw-guide-full" onClick={onFullGuide}>{guide.labels.fullGuide}</button>
      </footer>
    </section>,
    document.body,
  );
}

/**
 * The small "?" beside a screen's title, which opens that screen's cards in a popover by it; its name lists them, and
 * it says whether the popover is open.
 * @param {object} props
 * @param {string} props.screen - The screen, as guide.json's `screens` names it.
 * @param {(screen: string) => void} props.onFullGuide - Open the Guide at the screen's section, from the popover's link.
 */
export function GuideButton({ screen, onFullGuide }) {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef(null);
  const popoverId = useId();
  const cards = guideSections(guide, screen).flatMap((section) => section.cards.map((card) => card.title));
  const label = guide.labels.help.replace("{cards}", cards.join(", "));
  /** Close the popover, focus going back to the "?" when `back`. */
  const close = (back) => { setOpen(false); if (back) buttonRef.current?.focus(); };
  return (
    <>
      <button ref={buttonRef} type="button" className="dw-guide-help" lang="en" aria-label={label} title={label}
        aria-haspopup="dialog" aria-expanded={open} aria-controls={open ? popoverId : undefined}
        onClick={() => (open ? close(true) : setOpen(true))}>?</button>
      {open && <GuidePopover id={popoverId} screen={screen} anchor={buttonRef} onClose={close} onFullGuide={() => { close(false); onFullGuide(screen); }} />}
    </>
  );
}
