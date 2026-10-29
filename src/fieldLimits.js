/**
 * The most characters each field takes, as the local service's request models (backend/app/main.py) take them, so a
 * field stops the typing at the limit instead of the service refusing what was typed.
 */

/** A title or a name: a task's, a goal's, a note's, a checklist item's, or a task a rule keeps off. */
export const TITLE_CHARACTERS = 200;
/** A task's details. */
export const DETAIL_CHARACTERS = 1000;
/** A folder's path on this Mac, as typed; Settings shows a shorter cut of it (see settings/panes.js). */
export const FOLDER_PATH_CHARACTERS = 4096;
/** A website's address. */
export const ADDRESS_CHARACTERS = 2000;
/** A source's briefing. */
export const BRIEFING_CHARACTERS = 600;
/** The app a kind of file opens in. */
export const APP_NAME_CHARACTERS = 80;
/** A Library search's words; the service takes longer questions, as Ava asks them, but a search box needs no more. */
export const SEARCH_CHARACTERS = 200;
