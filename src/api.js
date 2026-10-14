/** The address the Mac app's window opens to have its shell renew the menu bar's title and menu; the shell answers it. */
export const RENEW_MENU_BAR = "daywright://refresh";

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

export function getDay(date, variantId, createIfMissing = false) {
  const query = new URLSearchParams({ date });
  if (variantId) query.set("variant_id", variantId);
  if (!createIfMissing) query.set("create_if_missing", "false");
  return api(`/api/bootstrap?${query}`);
}

export function getCalendar(month) {
  return api(`/api/calendar?${new URLSearchParams({ month })}`);
}

export function getSummaries(date) {
  return api(`/api/summaries?${new URLSearchParams({ date })}`, { method: "POST" });
}
