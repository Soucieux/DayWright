from datetime import date
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app import holidays
from backend.app.agents import AgentOrchestrator
from backend.app.app_settings import DEFAULT_HOLIDAYS, DEFAULT_WORK_SCHEDULE
from backend.app.conversation import schedule_line
from backend.app.holidays import HOLIDAYS_FILE, SOURCE
from backend.tests.test_holidays import answer, network
from backend.tests.test_repeats import SeriesDay

WEEKDAYS = [0, 1, 2, 3, 4]


class CardDay(SeriesDay):
    """A fresh account to talk to Ava in, where no message reaches the network."""

    def say(self, message, language="en"):
        with patch.object(holidays, "urlopen", side_effect=AssertionError("went online")):
            reply = self.client.post("/api/chat", json={"date": self.today, "message": message, "language": language})
        self.assertEqual(reply.status_code, 200, reply.text)
        return reply.json()

    def decide(self, card, decision="confirmed"):
        return self.client.post(f"/api/actions/{card['id']}", json={"decision": decision})

    def schedule(self):
        return self.client.get("/api/schedule").json()


class ScheduleCardTests(CardDay):
    """Each schedule phrase brings one pencilled card; nothing changes until it is confirmed."""

    def test_each_phrase_pencils_the_whole_schedule_in_english_and_chinese(self):
        for message, language, expected in (
                ("my working hours are 9 to 6 on weekdays", "en",
                 {"enabled": True, "mode": "working", "start": "09:00", "end": "18:00", "days": WEEKDAYS}),
                ("Set focus time 9 to 12", "en",
                 {"enabled": True, "mode": "focus", "start": "09:00", "end": "12:00", "days": WEEKDAYS}),
                ("My working hours are 8:30am to 4:30pm Monday to Thursday", "en",
                 {"enabled": True, "mode": "working", "start": "08:30", "end": "16:30", "days": [0, 1, 2, 3]}),
                ("我的工作时间是工作日9点到18点", "zh",
                 {"enabled": True, "mode": "working", "start": "09:00", "end": "18:00", "days": WEEKDAYS}),
                ("设置专注时间上午9点到12点", "zh",
                 {"enabled": True, "mode": "focus", "start": "09:00", "end": "12:00", "days": WEEKDAYS})):
            with self.subTest(message=message):
                reply = self.say(message, language)
                card = reply["proposedAction"]
                self.assertEqual(card["actionType"], "set_schedule")
                self.assertEqual(card["payload"]["schedule"], expected)
                self.assertIn("Nothing changes until you confirm", reply["assistantMessage"]["content"])
                self.assertEqual(self.schedule()["schedule"], DEFAULT_WORK_SCHEDULE, "nothing changes until confirmed")

    def test_turning_it_off_keeps_the_rest_of_the_schedule(self):
        kept = {"enabled": True, "mode": "focus", "start": "10:00", "end": "13:00", "days": [1, 3]}
        self.client.put("/api/schedule", json=kept)
        for message, language in (("turn working hours off", "en"), ("Turn off focus time", "en"), ("关闭工作时间", "zh")):
            with self.subTest(message=message):
                card = self.say(message, language)["proposedAction"]
                self.assertEqual(card["payload"]["schedule"], {**kept, "enabled": False})

    def test_confirming_keeps_the_schedule_and_dismissing_keeps_it_as_it_was(self):
        dismissed = self.say("my working hours are 9 to 5 on weekdays")["proposedAction"]
        self.assertEqual(self.decide(dismissed, "dismissed").status_code, 200)
        self.assertEqual(self.schedule()["schedule"], DEFAULT_WORK_SCHEDULE)
        card = self.say("my working hours are 9 to 5 on weekdays")["proposedAction"]
        decided = self.decide(card)
        self.assertEqual(decided.status_code, 200, decided.text)
        self.assertEqual(self.schedule()["schedule"], card["payload"]["schedule"])
        self.assertEqual(decided.json()["settings"]["schedule"], card["payload"]["schedule"])

    def test_an_end_before_its_start_is_answered_in_words(self):
        reply = self.say("set focus time 12 to 12")
        self.assertIsNone(reply["proposedAction"])
        self.assertIn("Nothing was changed", reply["assistantMessage"]["content"])

    def test_words_about_working_hours_with_no_range_are_not_a_schedule(self):
        for message in ("Move Report out of my working hours", "My working hours were long today"):
            with self.subTest(message=message):
                self.assertNotEqual((self.say(message)["proposedAction"] or {}).get("actionType"), "set_schedule")


class HolidayCardTests(CardDay):
    """"Import Ontario's holidays" pencils one card naming date.nager.at; only its Confirm goes online."""

    def setUp(self):
        super().setUp()
        self.year = date.today().year
        self.file = Path(self.temp_dir.name) / HOLIDAYS_FILE

    def chosen(self):
        return {key: self.schedule()["holidays"][key] for key in DEFAULT_HOLIDAYS}

    def test_a_region_or_country_named_in_english_or_chinese(self):
        ontario, quebec = {"en": "Ontario", "zh": "安大略省"}, {"en": "Quebec", "zh": "魁北克省"}
        for message, language, place in (
                ("import Ontario's holidays", "en", ("CA", "CA-ON", ontario)),
                ("Import the statutory holidays for Quebec", "en", ("CA", "CA-QC", quebec)),
                ("import Canada's holidays", "en", ("CA", None, None)),
                ("导入安大略省的法定假日", "zh", ("CA", "CA-ON", ontario)),
                ("导入安大略的假日", "zh", ("CA", "CA-ON", ontario))):
            with self.subTest(message=message):
                reply = self.say(message, language)
                card = reply["proposedAction"]
                self.assertEqual(card["actionType"], "import_holidays")
                self.assertEqual(card["payload"], {"country": place[0], "region": place[1], "regionName": place[2],
                                                   "years": [self.year, self.year + 1], "source": "date.nager.at"})
                self.assertIn("date.nager.at", reply["assistantMessage"]["content"])
                self.assertEqual(self.chosen(), DEFAULT_HOLIDAYS)

    def test_with_no_place_named_the_country_chosen_is_used_or_asked_for(self):
        self.assertIsNone(self.say("import holidays")["proposedAction"])
        self.client.put("/api/holidays", json={"enabled": False, "country": "CA", "region": "CA-ON"})
        card = self.say("import holidays")["proposedAction"]
        self.assertEqual((card["payload"]["country"], card["payload"]["region"]), ("CA", "CA-ON"))
        self.assertIsNone(self.say("import Narnia's holidays")["proposedAction"])

    def test_confirming_imports_and_turns_holidays_on(self):
        card = self.say("import Ontario's holidays")["proposedAction"]
        fake, asked = network({self.year: answer(self.year), self.year + 1: answer(self.year + 1)})
        with patch.object(holidays, "urlopen", fake):
            decided = self.decide(card)
        self.assertEqual(decided.status_code, 200, decided.text)
        self.assertEqual(asked, [SOURCE.format(year=self.year, country="CA"), SOURCE.format(year=self.year + 1, country="CA")])
        view = self.schedule()["holidays"]
        self.assertEqual((view["enabled"], view["country"], view["region"]), (True, "CA", "CA-ON"))
        self.assertEqual(len(view["list"]), 4)

    def test_confirming_offline_says_so_changes_nothing_and_keeps_the_card(self):
        card = self.say("import Ontario's holidays")["proposedAction"]
        fake, _ = network({self.year: URLError("offline")})
        with patch.object(holidays, "urlopen", fake):
            refused = self.decide(card)
        self.assertEqual(refused.status_code, 503)
        self.assertIn("date.nager.at", refused.json()["detail"])
        self.assertEqual(self.chosen(), DEFAULT_HOLIDAYS)
        self.assertFalse(self.file.exists())
        fake, _ = network({self.year: answer(self.year), self.year + 1: answer(self.year + 1)})
        with patch.object(holidays, "urlopen", fake):
            self.assertEqual(self.decide(card).status_code, 200, "the card stays to confirm once back online")

    def test_dismissing_never_goes_online(self):
        card = self.say("import Ontario's holidays")["proposedAction"]
        with patch.object(holidays, "urlopen", side_effect=AssertionError("went online")) as reached:
            self.assertEqual(self.decide(card, "dismissed").status_code, 200)
        reached.assert_not_called()


class ScheduleContextTests(SeriesDay):
    """Ava and Summary read the day's work schedule and its holiday."""

    def test_the_day_carries_its_schedule_and_holiday_and_ava_reads_them(self):
        self.store.schedule_for = lambda day: {"mode": "working", "start": "09:00", "end": "17:00"}
        day = self.store.bootstrap_day(self.today)
        self.assertEqual((day["workSchedule"], day["holiday"]), ({"mode": "working", "start": "09:00", "end": "17:00"}, None))
        self.assertEqual(schedule_line(day), "Work schedule: working hours 09:00–17:00, which plans keep free.")
        self.assertEqual(schedule_line({"workSchedule": {"mode": "focus", "start": "09:00", "end": "12:00"}, "holiday": None}),
                         "Work schedule: focus time 09:00–12:00, where plans place Work tasks without a time.")
        self.assertEqual(schedule_line({"workSchedule": None, "holiday": {"name": "Thanksgiving"}}),
                         "Thanksgiving is a statutory holiday: the work schedule doesn't apply, and Work repeats aren't "
                         "carried.")
        self.assertEqual(schedule_line({"workSchedule": None, "holiday": None}), "Work schedule: none on this day.")

    def test_summary_says_on_how_many_days_the_schedule_held_and_names_the_holidays(self):
        self.repeat_day("Stretch", self.yesterday)
        self.repeat_day("Stretch", self.today)
        self.store.schedule_for = lambda day: {"mode": "working", "start": "09:00", "end": "17:00"} if day == self.today else None
        self.store.holiday_for = lambda day: {"name": "Thanksgiving"} if day == self.yesterday else None
        facts = self.store.summary_facts(self.yesterday, self.today)
        self.assertEqual(facts["schedule"], {"working": 1, "focus": 0, "holidays": ["Thanksgiving"]})
        report = AgentOrchestrator().summary_report("week", "synthetic-week", facts)
        self.assertIn("Working hours held on 1 recorded day(s), and plans kept them free.", report["text"])
        self.assertIn("Statutory holidays: Thanksgiving.", report["text"])
