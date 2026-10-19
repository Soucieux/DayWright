import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app import holidays
from backend.app.app_settings import DEFAULT_HOLIDAYS, SETTINGS_FILE, AppSettings
from backend.app.holiday_places import COUNTRIES, REGION_NAMES
from backend.app.holidays import HOLIDAYS_FILE, SOURCE, Holidays, ImportFailed, listed, on, parse, regions, reminder
from backend.tests.test_repeats import SeriesDay, days_ago


def answer(year, country="CA"):
    """A synthetic Nager.Date answer for one year: a national holiday, two regional ones and one that isn't a day off."""
    return [
        {"date": f"{year}-01-01", "localName": "New Year's Day", "name": "New Year's Day", "countryCode": country,
         "fixed": True, "global": True, "counties": None, "launchYear": None, "types": ["Public"]},
        {"date": f"{year}-02-16", "localName": "Family Day", "name": "Family Day", "countryCode": country,
         "fixed": False, "global": False, "counties": ["CA-SK", "CA-ON", "CA-AB"], "launchYear": None,
         "types": ["Public"]},
        {"date": f"{year}-06-24", "localName": "Fête nationale du Québec", "name": "Saint-Jean-Baptiste Day",
         "countryCode": country, "fixed": True, "global": False, "counties": ["CA-QC"], "launchYear": None,
         "types": ["Public"]},
        {"date": f"{year}-10-31", "localName": "Halloween", "name": "Halloween", "countryCode": country, "fixed": True,
         "global": True, "counties": None, "launchYear": None, "types": ["Observance"]},
    ]


def network(answers):
    """Stand in for urlopen: answer each Nager.Date address from `answers`, by year, and record what was asked."""
    asked = []

    def fake(url, timeout):
        asked.append(url)
        year = int(url.rsplit("/", 2)[-2])
        if isinstance(answers.get(year), Exception):
            raise answers[year]
        return io.BytesIO(json.dumps(answers[year]).encode())

    return fake, asked


class ParseTests(unittest.TestCase):
    """Only statutory holidays are kept: national ones everywhere, regional ones in their regions."""

    def test_public_holidays_are_kept_with_their_regions(self):
        self.assertEqual(parse(answer(2026)), [
            {"date": "2026-01-01", "name": "New Year's Day", "localName": "New Year's Day", "regions": None},
            {"date": "2026-02-16", "name": "Family Day", "localName": "Family Day", "regions": ["CA-AB", "CA-ON", "CA-SK"]},
            {"date": "2026-06-24", "name": "Saint-Jean-Baptiste Day", "localName": "Fête nationale du Québec",
             "regions": ["CA-QC"]},
        ])

    def test_an_answer_that_isnt_a_list_of_holidays_is_refused(self):
        for broken in ({"title": "Not Found"}, [{"name": "No date"}], [{"date": "2026-13-01", "name": "x"}]):
            with self.subTest(broken=broken), self.assertRaises(ImportFailed):
                parse(broken)


class ImportTests(unittest.TestCase):
    """Import fetches the years asked for from date.nager.at and keeps them beside the settings; a failure keeps
    whatever was there."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / HOLIDAYS_FILE
        self.store = Holidays(self.path)

    def test_two_years_are_fetched_and_kept_together(self):
        fake, asked = network({2026: answer(2026), 2027: answer(2027)})
        with patch.object(holidays, "urlopen", fake):
            kept = self.store.import_years("CA", (2026, 2027))
        self.assertEqual(asked, [SOURCE.format(year=2026, country="CA"), SOURCE.format(year=2027, country="CA")])
        self.assertTrue(all(url.startswith("https://date.nager.at/") for url in asked))
        self.assertEqual((kept["country"], kept["years"]), ("CA", [2026, 2027]))
        self.assertEqual(len(kept["holidays"]), 6)
        self.assertEqual(json.loads(self.path.read_text()), kept)
        self.assertEqual(self.store.kept(), kept)
        self.assertTrue(kept["importedAt"])

    def test_offline_the_import_says_so_and_changes_nothing(self):
        fake, _ = network({2026: answer(2026), 2027: answer(2027)})
        with patch.object(holidays, "urlopen", fake):
            self.store.import_years("CA", (2026, 2027))
        before = self.path.read_bytes()
        for answers in ({2026: URLError("offline"), 2027: answer(2027)},
                        {2026: answer(2026), 2027: TimeoutError("timed out")}):
            fake, _ = network(answers)
            with self.subTest(answers=list(answers.values())), patch.object(holidays, "urlopen", fake):
                with self.assertRaisesRegex(ImportFailed, "date.nager.at"):
                    self.store.import_years("CA", (2026, 2027))
            self.assertEqual(self.path.read_bytes(), before)

    def test_remove_forgets_every_holiday(self):
        fake, _ = network({2026: answer(2026)})
        with patch.object(holidays, "urlopen", fake):
            self.store.import_years("CA", (2026,))
        self.store.remove()
        self.assertIsNone(self.store.kept())
        self.assertFalse(self.path.exists())
        self.store.remove()  # Nothing kept is nothing to remove.


class LookupTests(unittest.TestCase):
    """The list kept answers for the country and region chosen without another fetch."""

    KEPT = {"country": "CA", "importedAt": "2026-10-19T14:00:00+00:00", "years": [2026],
            "holidays": parse(answer(2026))}

    def test_a_day_is_a_national_holiday_or_one_of_the_regions(self):
        self.assertEqual(on(self.KEPT, "2026-01-01", "CA", "CA-ON"),
                         {"date": "2026-01-01", "name": "New Year's Day", "localName": "New Year's Day", "regional": False})
        self.assertEqual(on(self.KEPT, "2026-02-16", "CA", "CA-ON")["regional"], True)
        self.assertIsNone(on(self.KEPT, "2026-02-16", "CA", "CA-QC"))
        self.assertIsNone(on(self.KEPT, "2026-02-16", "CA", None), "with no region, national holidays alone")
        self.assertIsNone(on(self.KEPT, "2026-03-03", "CA", "CA-ON"))
        self.assertIsNone(on(self.KEPT, "2026-01-01", "US", None), "the list kept is for another country")
        self.assertIsNone(on(None, "2026-01-01", "CA", None))

    def test_the_list_shows_the_regions_holidays_and_the_national_ones(self):
        self.assertEqual([(holiday["name"], holiday["regional"]) for holiday in listed(self.KEPT, "CA", "CA-ON")],
                         [("New Year's Day", False), ("Family Day", True)])
        self.assertEqual(listed(self.KEPT, "US", None), [])

    def test_the_regions_come_from_the_list_kept(self):
        self.assertEqual(regions(self.KEPT, "CA"), ["CA-AB", "CA-ON", "CA-QC", "CA-SK"])
        self.assertEqual(regions(self.KEPT, "US"), [])


class ReminderTests(unittest.TestCase):
    """From 1 December, Today reminds the user to import next year's holidays while they are missing."""

    KEPT = {"country": "CA", "importedAt": "2026-01-05T10:00:00+00:00", "years": [2026], "holidays": []}

    def test_from_the_first_of_december_while_next_years_list_is_missing(self):
        self.assertIsNone(reminder(self.KEPT, "CA", date(2026, 11, 30)))
        self.assertEqual(reminder(self.KEPT, "CA", date(2026, 12, 1)), 2027)
        self.assertEqual(reminder(None, "CA", date(2026, 12, 31)), 2027)
        self.assertEqual(reminder(self.KEPT, "US", date(2026, 12, 1)), 2027, "the list kept is for another country")

    def test_not_once_next_years_list_is_kept_or_with_no_country(self):
        self.assertIsNone(reminder({**self.KEPT, "years": [2026, 2027]}, "CA", date(2026, 12, 15)))
        self.assertIsNone(reminder(self.KEPT, None, date(2026, 12, 15)))


class PlacesTests(unittest.TestCase):
    """The countries Nager.Date covers come with DayWright; region names come with it for a few countries."""

    def test_the_bundled_countries_and_region_names(self):
        codes = [code for code, _ in COUNTRIES]
        self.assertEqual(len(codes), 204)
        self.assertEqual(codes, sorted(set(codes)))
        self.assertIn(("CA", "Canada"), COUNTRIES)
        self.assertEqual(REGION_NAMES["CA-ON"], {"en": "Ontario", "zh": "安大略省"})
        self.assertEqual(sum(code.startswith("CA-") for code in REGION_NAMES), 13)
        self.assertTrue(all(code[:2] in codes for code in REGION_NAMES))


class HolidaySettingTests(unittest.TestCase):
    """Holidays are off until turned on, with the country and region kept for both workspaces."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = AppSettings(Path(self.temp.name) / SETTINGS_FILE)

    def test_off_until_set_then_kept(self):
        self.assertEqual(self.settings.holiday_settings(), DEFAULT_HOLIDAYS)
        self.assertEqual(DEFAULT_HOLIDAYS, {"enabled": False, "country": None, "region": None})
        chosen = {"enabled": True, "country": "CA", "region": "CA-ON"}
        self.assertEqual(self.settings.set_holiday_settings(chosen), chosen)
        self.assertEqual(AppSettings(self.settings.path).holiday_settings(), chosen)

    def test_only_a_country_nager_covers_and_one_of_its_regions(self):
        good = {"enabled": True, "country": "CA", "region": None}
        for broken in ({"country": "XX"}, {"region": "US-CA"}, {"region": "CA-ON; drop"}, {"country": None, "region": "CA-ON"},
                       {"enabled": "yes"}):
            with self.subTest(broken=broken), self.assertRaises(ValueError):
                self.settings.set_holiday_settings({**good, **broken})


class HolidayRouteTests(SeriesDay):
    """Settings › Schedule's holidays: DayWright goes online for them on Import alone, and uses them while on."""

    def setUp(self):
        super().setUp()
        self.file = Path(self.temp_dir.name) / HOLIDAYS_FILE
        self.year = date.today().year

    def keep(self, *days):
        """Keep national holidays on `days` directly, as an Import would."""
        self.file.write_text(json.dumps({"country": "CA", "importedAt": "2026-10-19T14:00:00+00:00", "years": [self.year],
                                         "holidays": [{"date": day, "name": "Test Day", "localName": "Test Day",
                                                       "regions": None} for day in days]}))

    def turn_on(self, enabled=True, region="CA-ON"):
        return self.client.put("/api/holidays", json={"enabled": enabled, "country": "CA", "region": region})

    def test_nothing_but_import_goes_online(self):
        with patch.object(holidays, "urlopen", side_effect=AssertionError("went online")) as reached:
            self.assertEqual(self.turn_on().status_code, 200)
            self.client.get("/api/schedule")
            self.client.put("/api/schedule", json={"enabled": True, "mode": "focus", "start": "09:00", "end": "12:00",
                                                   "days": [0, 1, 2, 3, 4, 5, 6]})
            self.client.post("/api/daily-items", json=self.task("Read", None, 45))
            self.client.post("/api/plan/generate", json={"date": self.today})
            self.client.get("/api/bootstrap", params={"date": self.today})
            self.client.get("/api/calendar", params={"month": self.today[:7]})
            self.client.delete("/api/holidays")
        reached.assert_not_called()

    def test_import_fetches_this_year_and_next_for_the_country_chosen(self):
        self.turn_on()
        fake, asked = network({self.year: answer(self.year), self.year + 1: answer(self.year + 1)})
        with patch.object(holidays, "urlopen", fake):
            imported = self.client.post("/api/holidays/import")
        self.assertEqual(imported.status_code, 200)
        self.assertEqual(asked, [SOURCE.format(year=self.year, country="CA"), SOURCE.format(year=self.year + 1, country="CA")])
        view = imported.json()["holidays"]
        self.assertEqual(view["years"], [self.year, self.year + 1])
        self.assertTrue(view["importedAt"])
        self.assertEqual([holiday["name"] for holiday in view["list"]],
                         ["New Year's Day", "Family Day", "New Year's Day", "Family Day"])
        self.assertEqual(view["regions"], ["CA-AB", "CA-ON", "CA-QC", "CA-SK"])
        self.assertEqual(view["source"], "date.nager.at")
        self.assertEqual(self.client.get("/api/schedule").json()["holidays"], view)

    def test_offline_import_says_so_and_changes_nothing(self):
        self.turn_on()
        fake, _ = network({self.year: URLError("offline")})
        with patch.object(holidays, "urlopen", fake):
            refused = self.client.post("/api/holidays/import")
        self.assertEqual(refused.status_code, 503)
        self.assertIn("date.nager.at", refused.json()["detail"])
        self.assertIn("Nothing changed", refused.json()["detail"])
        self.assertFalse(self.file.exists())

    def test_import_needs_a_country(self):
        self.assertEqual(self.client.post("/api/holidays/import").status_code, 422)

    def test_a_holiday_shows_on_today_and_in_the_calendar_while_holidays_are_on(self):
        self.keep(self.today)
        self.turn_on()
        day = self.client.get("/api/bootstrap", params={"date": self.today}).json()
        self.assertEqual(day["holiday"], {"date": self.today, "name": "Test Day", "localName": "Test Day", "regional": False})
        month = self.client.get("/api/calendar", params={"month": self.today[:7]}).json()
        self.assertEqual(month["holidays"], {self.today: {"date": self.today, "name": "Test Day", "localName": "Test Day",
                                                          "regional": False}})
        self.assertEqual(day["holidayReminder"], reminder(json.loads(self.file.read_text()), "CA", date.today()))

    def test_turning_holidays_off_keeps_the_list_but_stops_using_it(self):
        self.keep(self.today)
        self.turn_on(enabled=False)
        self.assertIsNone(self.client.get("/api/bootstrap", params={"date": self.today}).json()["holiday"])
        self.assertEqual(self.client.get("/api/calendar", params={"month": self.today[:7]}).json()["holidays"], {})
        self.assertEqual(len(self.client.get("/api/schedule").json()["holidays"]["list"]), 1)
        self.assertTrue(self.file.exists())

    def test_work_repeats_arent_carried_onto_a_holiday(self):
        self.keep(self.today)
        self.turn_on()
        self.repeat_day("Standup", days_ago(1), domain="work")
        self.repeat_day("Stretch", days_ago(1), domain="life", start="06:30")
        self.assertEqual(self.client.post("/api/plan/generate", json={"date": self.today}).status_code, 200)
        titles = {item["title"] for item in self.client.get("/api/bootstrap", params={"date": self.today}).json()["dayItems"]}
        self.assertEqual(titles, {"Stretch"})

    def test_remove_all_forgets_the_list_and_keeps_the_choice(self):
        self.keep(self.today)
        self.turn_on()
        view = self.client.delete("/api/holidays").json()["holidays"]
        self.assertEqual((view["list"], view["enabled"], view["country"]), ([], True, "CA"))
        self.assertFalse(self.file.exists())

    def test_a_choice_that_isnt_whole_is_refused(self):
        refused = self.client.put("/api/holidays", json={"enabled": True, "country": "XX", "region": None})
        self.assertEqual(refused.status_code, 422)


if __name__ == "__main__":
    unittest.main()
