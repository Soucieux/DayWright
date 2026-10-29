/** The address the Mac app's window opens to have its shell renew the menu bar's title and menu; the shell answers it. */
export const RENEW_MENU_BAR = "daywright://refresh";

/**
 * Ask the local service: a JSON request to `path`. After any change the Mac app's shell renews the menu bar.
 * @param {string} path - The service's address, from /api.
 * @param {RequestInit} [options] - The fetch options; their headers join the JSON content type.
 * @returns {Promise<any>} The service's JSON answer.
 * @throws {Error} With the service's detail, or the status, when the request fails.
 */
export async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Request failed (${response.status})`);
  }
  // A change, such as a status, a pause or the language, can change what the menu bar shows: it is renewed at once.
  if (options.method && options.method !== "GET" && window.daywrightShell === "desktop") window.location.href = RENEW_MENU_BAR;
  return response.json();
}

/**
 * A day as the interface draws it (see the service's bootstrap); its plans are never made by opening it.
 * @param {string} date - The YYYY-MM-DD day.
 * @param {string|null} [variantId] - The plan to show; the set one, or the first, when not given.
 * @returns {Promise<object>} The day.
 */
export function getDay(date, variantId) {
  const query = new URLSearchParams({ date });
  if (variantId) query.set("variant_id", variantId);
  return api(`/api/bootstrap?${query}`);
}

/**
 * A month's days as Calendar marks them, with its statutory holidays while holidays are on.
 * @param {string} month - The YYYY-MM month.
 * @returns {Promise<object>} The month.
 */
export function getCalendar(month) {
  return api(`/api/calendar?${new URLSearchParams({ month })}`);
}

/**
 * Summary's reports for a day, its week, its month and all time, with each period's kept advice.
 * @param {string} date - The YYYY-MM-DD day.
 * @returns {Promise<{reports: object[], pool: object}>} The reports, and the advice by period kind.
 */
export function getSummaries(date) {
  return api(`/api/summaries?${new URLSearchParams({ date })}`, { method: "POST" });
}

/**
 * Open a Library item where it lives, as libraryData's openActions says it can: in its app, or on its folder's
 * website; a website always opens in the browser.
 * @param {string} id - The item's id.
 * @param {"app"|"website"} where - Where it opens.
 * @returns {Promise<object>} The service's answer.
 * @throws {Error} With the reason it didn't open.
 */
export function openSource(id, where) {
  return api(`/api/sources/${encodeURIComponent(id)}/open`, { method: "POST", body: JSON.stringify({ where }) });
}
