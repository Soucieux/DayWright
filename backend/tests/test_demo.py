from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.database import Database
from backend.app.demo import seed_demo_workspace
from backend.app.domain_records import DomainRecords


class DemoWorkspaceTests(unittest.TestCase):
    def test_seed_is_separate_populated_and_idempotent(self):
        with TemporaryDirectory() as folder:
            store = Database(Path(folder) / "demo.sqlite3")
            seed_demo_workspace(store)
            seed_demo_workspace(store)

            today = date.today().isoformat()
            self.assertEqual(len(store.goals()), 3)
            items = store.daily_items(today)
            self.assertEqual(len(items), 4)
            self.assertEqual({item["domain"] for item in items}, {"learning", "life", "work", "project"})
            self.assertEqual({item["title"] for item in items if item["start_time"] is None},
                             {"Review retrieval notes", "Draft the onboarding guide"})
            today_day = store.bootstrap_day(today, None, False)
            self.assertIsNone(today_day["planSetId"])
            self.assertEqual(len(store.goals()[0]["linkedItems"]), 1)
            past = store.bootstrap_day(
                (date.today() - timedelta(days=1)).isoformat(), None, False
            )
            self.assertIsNotNone(past["confirmedVariantId"])
            domains = DomainRecords(store)
            self.assertEqual(len(domains.snapshot("learning", today)["sessions"]), 1)
            self.assertIsNotNone(domains.snapshot("life", today)["daily"])


if __name__ == "__main__":
    unittest.main()
