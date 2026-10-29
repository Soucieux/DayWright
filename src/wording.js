import wording from "./wording.json" with { type: "json" };

/**
 * How DayWright counts words: the one way, everywhere a text is held to a number of them. src/wording.json holds
 * the limit and the examples this counter and the service's (backend/app/wording.py) both answer to.
 *
 * A word is a run of text between spaces that holds a letter or a digit, and each Chinese character is a word of
 * its own, as Chinese is written without spaces.
 */

/** The most words a Guide card's For, Do and Rule hold together, and a source's briefing, its own, the user's or Ava's. */
export const WORD_LIMIT = wording.wordLimit;
/** The fewest words a briefing needs before Ava stops offering one. */
export const BRIEFING_MIN_WORDS = wording.briefingMinWords;
/** The Chinese characters, from CJK Extension A to the end of the Unified Ideographs. */
const HAN_RANGE = "㐀-鿿";
/** A Chinese character, a word of its own; split out of a run with the runs around it. */
const HAN = new RegExp(`([${HAN_RANGE}])`, "u");
/** A part that is one Chinese character and nothing else. */
const ONE_HAN = new RegExp(`^[${HAN_RANGE}]$`, "u");
/** What makes any other part a word. */
const LETTER_OR_DIGIT = /[\p{L}\p{N}]/u;

/**
 * Whether a text holds a Chinese character, as a name written in Chinese does.
 * @param {string} text - The text.
 * @returns {boolean} Whether it holds one.
 */
export function hasChinese(text) {
  return HAN.test(text);
}

/**
 * A run of text between spaces in its parts: each Chinese character, and the runs between them.
 * @param {string} token - The run.
 * @returns {string[]} Its parts.
 */
function pieces(token) {
  return token.split(HAN).filter(Boolean);
}

/**
 * Whether a part counts as a word: a Chinese character, or a run holding a letter or a digit.
 * @param {string} piece - The part.
 * @returns {boolean} Whether it counts.
 */
function isWord(piece) {
  return ONE_HAN.test(piece) || LETTER_OR_DIGIT.test(piece);
}

/**
 * How many words a text holds.
 * @param {string|null|undefined} text - The text.
 * @returns {number} Its words.
 */
export function countWords(text) {
  return (text || "").split(/\s+/).filter(Boolean).reduce((sum, token) => sum + pieces(token).filter(isWord).length, 0);
}

/**
 * A text held to `limit` words: as it is, its spaces run together, when it fits; else cut at the last word boundary
 * within the limit, never inside a word, with … where it was cut.
 * @param {string|null|undefined} text - The text.
 * @param {number} [limit=WORD_LIMIT] - The most words it may hold.
 * @returns {string} The text, "" for one with nothing in it.
 */
export function cutWords(text, limit = WORD_LIMIT) {
  const kept = [];
  let count = 0;
  for (const token of (text || "").split(/\s+/).filter(Boolean)) {
    const parts = pieces(token);
    const words = parts.filter(isWord).length;
    if (count + words <= limit) {
      kept.push(token);
      count += words;
      continue;
    }
    // A run of Chinese crosses the limit: keep its characters up to it.
    const part = [];
    for (const piece of parts) {
      if (isWord(piece)) {
        if (count === limit) break;
        count += 1;
      }
      part.push(piece);
    }
    while (part.length && !isWord(part[part.length - 1])) part.pop();
    if (part.length) kept.push(part.join(""));
    return `${kept.join(" ")}…`;
  }
  return kept.join(" ");
}
