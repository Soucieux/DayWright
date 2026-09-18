from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

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
            self.assertEqual(len(store.daily_items(today)), 3)
            today_day = store.bootstrap_day(date.today(), None, False)
            self.assertIsNone(today_day["planSetId"])
            self.assertEqual(len(store.goals()[0]["linkedItems"]), 1)
            past = store.bootstrap_day(date.today() - timedelta(days=1), None, False)
            self.assertIsNotNone(past["confirmedVariantId"])
            domains = DomainRecords(store)
            self.assertEqual(len(domains.snapshot("learning", today)["sessions"]), 1)
            self.assertIsNotNone(domains.snapshot("life", today)["daily"])
            self.assertEqual(len(domains.snapshot("finance", today)["transactions"]), 1)


if __name__ == "__main__":
    unittest.main()
