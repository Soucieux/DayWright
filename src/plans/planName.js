/**
 * Every kind of plan the local agents propose, Balanced first and then the planner's default order,
 * each with the message keys for its name, its one-line description, and when it is offered.
 */
export const PLAN_TYPES = [
  ["balanced", "planBalanced", "planTaglineBalanced", "planWhenBalanced"],
  ["focused", "planFocused", "planTaglineFocused", "planWhenFocused"],
  ["gentle", "planGentle", "planTaglineGentle", "planWhenGentle"],
  ["early", "planEarly", "planTaglineEarly", "planWhenEarly"],
  ["quickwins", "planQuickwins", "planTaglineQuickwins", "planWhenQuickwins"],
  ["easiest", "planEasiest", "planTaglineEasiest", "planWhenEasiest"],
  ["rhythm", "planRhythm", "planTaglineRhythm", "planWhenRhythm"],
  ["spacious", "planSpacious", "planTaglineSpacious", "planWhenSpacious"],
].map(([slug, name, tagline, when]) => ({ slug, name, tagline, when }));

const TYPES_BY_SLUG = Object.fromEntries(PLAN_TYPES.map((type) => [type.slug, type]));

/**
 * Name a plan in the interface language.
 * @param {object|undefined} variant - The plan, with its `slug` and stored `name`.
 * @param {(key: string) => string} t - The interface text lookup.
 * @param {(value: string) => string} demoText - Translates demo workspace text.
 * @returns {string} The plan's name, or an empty string when there is no plan.
 */
export function planName(variant, t, demoText) {
  if (!variant) return "";
  const type = TYPES_BY_SLUG[variant.slug];
  return type ? t(type.name) : demoText(variant.name);
}

/**
 * Say in one line how a kind of plan works, so plans can be told apart before reading on.
 * @param {string} slug - The kind of plan.
 * @param {(key: string) => string} t - The interface text lookup.
 * @returns {string} The line, or an empty string for a kind this interface doesn't know.
 */
export function planTagline(slug, t) {
  const type = TYPES_BY_SLUG[slug];
  return type ? t(type.tagline) : "";
}
