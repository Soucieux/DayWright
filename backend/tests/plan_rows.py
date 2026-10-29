"""The rows a test writes straight into its throwaway store to stand for the plan the user set on a day."""

import sqlite3

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.


def set_plan_rows(connection: sqlite3.Connection, day: str) -> str:
    """Set a Balanced plan on `day` the first time a test asks, so its entries can be added one at a time.

    Args:
        connection: An open connection to the test's store.
        day: The plan's YYYY-MM-DD day.

    Returns:
        The set plan's variant id, which its entries name.
    """
    variant = f"plan:{day}"
    if not connection.execute("SELECT 1 FROM plan_sets WHERE id = ?", (f"set:{day}",)).fetchone():
        connection.execute("INSERT INTO plan_sets (id, plan_date, source, created_at) VALUES (?, ?, 'test', ?)",
                           (f"set:{day}", day, day))
        connection.execute("""INSERT INTO plan_variants (id, plan_set_id, name, slug, rationale, created_at)
                              VALUES (?, ?, 'Balanced', 'balanced', '', ?)""", (variant, f"set:{day}", day))
        connection.execute("INSERT INTO daily_confirmations (plan_date, variant_id, confirmed_at) VALUES (?, ?, ?)",
                           (day, variant, day))
    return variant
