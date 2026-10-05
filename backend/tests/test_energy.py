import unittest

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.tests.test_meals import MealDay


class EnergyTests(MealDay):
    """Today's energy, out of 5: one reading a day, changed only that day."""

    def kinds(self):
        return [notice["kind"] for notice in self.client.get("/api/bootstrap", params={"date": self.today}).json()["notices"]]

    def test_todays_energy_is_one_reading_that_can_change_during_the_day(self):
        saved = self.client.put(f"/api/energy/{self.today}", json={"level": 4})
        self.client.put(f"/api/energy/{self.today}", json={"level": 3})

        self.assertEqual(saved.json(), {"date": self.today, "level": 4})
        self.assertEqual(self.client.get("/api/bootstrap", params={"date": self.today}).json()["energy"], 3)

    def test_another_days_energy_cant_change(self):
        for day in (self.yesterday, self.tomorrow):
            self.assertEqual(self.client.put(f"/api/energy/{day}", json={"level": 4}).status_code, 409)
            self.assertIsNone(self.store.energy(day))

    def test_a_level_outside_one_to_five_is_refused(self):
        for level in (0, 6):
            self.assertEqual(self.client.put(f"/api/energy/{self.today}", json={"level": level}).status_code, 422)
        self.assertIsNone(self.store.energy(self.today))

    def test_energy_of_two_or_below_brings_the_lighter_day_suggestion(self):
        for number in range(4):
            self.client.post("/api/daily-items", json={**self.task(f"Block {number}", None, 120), "domain": "work"})

        self.client.put(f"/api/energy/{self.today}", json={"level": 2})

        self.assertEqual([kind for kind in self.kinds() if "energy" in kind], ["low-energy-full"])
        plan = self.client.post("/api/plan/generate", json={"date": self.today}).json()
        findings = [finding for run in plan["planRoute"] for finding in run.get("findings") or []]
        self.assertTrue(any(finding.get("lighter") for finding in findings))

    def test_energy_of_three_asks_for_nothing_lighter(self):
        self.client.post("/api/daily-items", json={**self.task("Walk", None), "domain": "life"})

        self.client.put(f"/api/energy/{self.today}", json={"level": 3})

        self.assertFalse([kind for kind in self.kinds() if "energy" in kind])


class RemovedAreaRecordRoutesTests(MealDay):
    def test_the_old_learning_and_life_record_routes_are_gone(self):
        for method, path in (("post", "/api/learning/items"), ("patch", "/api/learning/items/x"),
                             ("post", "/api/learning/sessions"), ("post", "/api/life/habits"),
                             ("patch", "/api/life/habits/x"), ("put", f"/api/life/habits/x/logs/{self.today}"),
                             ("put", f"/api/life/daily/{self.today}"), ("post", "/api/life/events")):
            self.assertEqual(getattr(self.client, method)(path, json={}).status_code, 404, path)


if __name__ == "__main__":
    unittest.main()
