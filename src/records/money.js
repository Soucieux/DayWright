/**
 * Convert an entered money amount to exact integer cents for the local service.
 * @param {string} value - What the user typed, such as "12.50".
 * @param {boolean} [allowNegative=false] - Whether a leading minus is allowed, as for an opening balance.
 * @returns {number} The amount in cents.
 * @throws {Error} When the amount has more than two decimal places or is too large to be exact.
 */
export function enteredCents(value, allowNegative = false) {
  const entered = value.trim();
  if (!new RegExp(allowNegative ? "^-?\\d+(?:\\.\\d{1,2})?$" : "^\\d+(?:\\.\\d{1,2})?$").test(entered)) {
    throw new Error("Enter a money amount with no more than two decimal places.");
  }
  const negative = entered.startsWith("-");
  const [whole, fraction = ""] = (negative ? entered.slice(1) : entered).split(".");
  const cents = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
  if (!Number.isSafeInteger(cents)) throw new Error("This money amount is too large.");
  return negative ? -cents : cents;
}

/**
 * Show an integer-cent amount without floating-point rounding.
 * @param {number} cents - The amount in cents.
 * @returns {string} Such as "2,721.50" or "−12.00".
 */
export function money(cents) {
  const sign = cents < 0 ? "−" : "";
  const amount = Math.abs(cents);
  return `${sign}${Math.floor(amount / 100).toLocaleString("en-GB")}.${String(amount % 100).padStart(2, "0")}`;
}
