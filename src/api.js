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
