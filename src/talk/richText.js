/** A heading line the local model wrote in Markdown, such as "## Plan" or "### Plan ###". */
const HEADING = /^#{1,6}[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$/gm;
/**
 * Bold italic (`***text***`), bold (`**text**`) or italic (`*text*`) marks; an asterisk beside a
 * space or inside a word marks nothing.
 */
const EMPHASIS = /\*\*\*(?=\S)(.+?)(?<=\S)\*\*\*|\*\*(?=\S)(.+?)(?<=\S)\*\*|(?<![\w*])\*(?=\S)([^*\n]+?)(?<=\S)\*(?![\w*])/g;

/**
 * Split a reply into runs of plain, bold and italic text, so the Markdown marks the local model
 * sometimes writes show as emphasis rather than as asterisks. Nothing is read as HTML.
 * @param {string} text - The reply.
 * @returns {{text: string, strong?: boolean, em?: boolean}[]} The runs in order; a heading becomes
 *   bold, without the marks of any emphasis inside it.
 */
export function textRuns(text) {
  const source = text.replace(HEADING, (line, heading) => `**${heading.replace(/\*+/g, "")}**`);
  const runs = [];
  let last = 0;
  for (const match of source.matchAll(EMPHASIS)) {
    if (match.index > last) runs.push({ text: source.slice(last, match.index) });
    runs.push(match[1] !== undefined ? { text: match[1], strong: true, em: true }
      : match[2] !== undefined ? { text: match[2], strong: true } : { text: match[3], em: true });
    last = match.index + match[0].length;
  }
  if (last < source.length) runs.push({ text: source.slice(last) });
  return runs;
}
