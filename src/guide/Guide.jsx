import { Fragment, useEffect, useId, useRef } from "react";
import { Icon } from "../ui/Icon";
import { Sheet } from "../ui/Sheet";
import guide from "./guide.json";
import { guideRows, guideSections } from "./guideCards";

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
 * on a phone or in a sheet. Every card is the size of the tallest.
 * @param {object} props
 * @param {object[]} props.sections - The sections to show, from guideSections.
 */
export function GuideCards({ sections }) {
  return (
    <div className="dw-guide" lang="en">
      <div className="dw-guide-grid" style={{ "--dw-guide-rows-two": guideRows(sections, 2), "--dw-guide-rows-one": guideRows(sections, 1) }}>
        {sections.map((section) => (
          <Fragment key={section.id}>
            <h2 className={`dw-guide-section dw-guide-${section.id}`}>{section.title}</h2>
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
 * The Guide: every card in its five sections. Opened from one of Ava's See Guide links, it brings that
 * card into view and moves focus to it.
 * @param {object} props
 * @param {{card: string, at: number}|null} props.focus - The card asked for, and when, so asking again moves to it again.
 */
export function GuideScreen({ focus }) {
  const pageRef = useRef(null);

  useEffect(() => {
    const card = focus && pageRef.current?.querySelector(`[data-guide-card="${focus.card}"]`);
    card?.scrollIntoView({ block: "center" });
    card?.focus({ preventScroll: true });
  }, [focus]);

  return (
    <main className="dw-page dw-guide-page" tabIndex={-1} ref={pageRef} lang="en">
      <header className="dw-page-head"><h1 className="dw-display">{guide.title}</h1></header>
      <GuideCards sections={guideSections(guide)} />
    </main>
  );
}

/**
 * The small "?" beside a screen's title, which opens that screen's cards; its name lists them.
 * @param {object} props
 * @param {string} props.screen - The screen, as guide.json's `screens` names it.
 * @param {(screen: string) => void} props.onOpen - Show the screen's cards.
 * @param {boolean} [props.pressed] - Whether the cards are showing, for a "?" that also hides them.
 */
export function GuideButton({ screen, onOpen, pressed }) {
  const cards = guideSections(guide, screen).flatMap((section) => section.cards.map((card) => card.title));
  const label = guide.labels.help.replace("{cards}", cards.join(", "));
  return (
    <button type="button" className="dw-guide-help" lang="en" aria-label={label} title={label} aria-pressed={pressed}
      onClick={() => onOpen(screen)}>?</button>
  );
}

/**
 * A screen's cards in a sheet beside the page, as its "?" opens them.
 * @param {object} props
 * @param {string} props.screen - The screen.
 * @param {() => void} props.onClose - Close the sheet.
 */
export function GuideSheet({ screen, onClose }) {
  return (
    <Sheet title={guide.title} view={screen} onClose={onClose}>
      <ScreenGuide screen={screen} />
    </Sheet>
  );
}
