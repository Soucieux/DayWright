import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app.database import Database
from backend.app.main import create_app
from backend.tests.test_api import FakeEmbeddingGateway, FakeGateway

TODAY = date.today()

REMINDERS = ("due-for-review", "stalled", "slipping", "low-energy", "low-energy-full", "day-wont-fit", "length-off")
OFFERS = ("continue-offer", "link-offer", "folder-check", "memory-review", "usual-length")
REPLIES = ("doubt-usual-time", "doubt-too-short", "clarify-task", "clarify-past-task", "clarify-repeat-scope",
           "clarify-meal-scope", "clarify-which")


def back(days: int) -> str:
    """The ISO date `days` before TODAY."""
    return (TODAY - timedelta(days=days)).isoformat()


class ReminderTests(unittest.TestCase):
    """What the agents raise about the day is a reminder on Today, never a message in Ava's chat; what offers a change,
    with its card, stays in Ava, as does an answer to a request."""

    def setUp(self):
        """A client of the service on a throwaway database, with no day jobs running."""
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Database(Path(self.folder.name) / "daywright.sqlite3")
        self.client = TestClient(create_app(database=self.store, gateway=FakeGateway(), embedding_gateway=FakeEmbeddingGateway(),
                                            day_jobs=False))

    def post(self, day: str, kind: str, key: str | None = None, agent: str = "learning", **values):
        """Post `agent`'s notice of `kind` on `day`, keyed by `key` (its kind when not given), with `values`."""
        self.store.post_notices(day, [{"issueKey": key or kind, "agent": agent, "kind": kind, "values": values}])

    def day(self) -> dict:
        """What the interface gets for a day other than today, so opening it posts nothing itself."""
        return self.client.get("/api/bootstrap", params={"date": back(30)}).json()

    def test_each_kind_is_a_reminder_an_offer_or_a_reply(self):
        for kind in (*REMINDERS, *OFFERS, *REPLIES):
            self.post(back(0), kind)
        groups = {notice["kind"]: notice["group"] for notice in self.store.notices()}
        self.assertEqual(groups, {**{kind: "reminder" for kind in REMINDERS}, **{kind: "offer" for kind in OFFERS},
                                  **{kind: "reply" for kind in REPLIES}})

    def test_the_unread_dot_counts_offers_and_replies_never_reminders(self):
        self.post(back(0), "slipping", "slipping:learning:read", taskTitle="Read")
        self.post(back(0), "continue-offer", "continue-offer:item", taskTitle="Lesson 4")
        self.post(back(0), "clarify-task", "clarify-task:message", requested="15:00")
        self.assertEqual(self.day()["unreadNotices"], 2)

    def test_today_lists_todays_reminders_each_with_the_day_it_first_came_up(self):
        self.post(back(2), "slipping", "slipping:learning:read", taskTitle="Read", unfinished=2)
        self.post(back(0), "slipping", "slipping:learning:read", taskTitle="Read", unfinished=3)
        self.post(back(0), "due-for-review", "due-for-review:goal", goalId="goal", goalTitle="Spanish to B1", days=9)
        self.post(back(1), "stalled", "stalled:other", goalId="other", goalTitle="Piano", days=20)
        self.post(back(0), "continue-offer", "continue-offer:item", taskTitle="Lesson 4")
        shown = [(reminder["kind"], reminder["since"], reminder["values"].get("taskTitle") or reminder["values"]["goalTitle"])
                 for reminder in self.day()["reminders"]]
        self.assertEqual(shown, [("slipping", back(2), "Read"), ("due-for-review", back(0), "Spanish to B1")])

    def test_a_reminder_dismissed_stays_away_until_it_is_raised_with_other_figures(self):
        self.post(back(1), "slipping", "slipping:learning:read", taskTitle="Read", unfinished=2)
        yesterday = self.store.reminders(back(1))[0]
        answer = self.client.post("/api/reminders/dismiss", json={"ids": [yesterday["id"]]})
        self.assertEqual(answer.status_code, 200, answer.text)
        self.assertEqual(self.store.reminders(back(1)), [])
        self.post(back(0), "slipping", "slipping:learning:read", taskTitle="Read", unfinished=2)
        self.assertEqual(self.store.reminders(back(0)), [], "raised again as it was, it stays dismissed")
        self.post(back(0), "length-off", "length-off:learning:read", taskTitle="Read", minutes=40)
        self.store.post_notices(back(0), [{"issueKey": "slipping:learning:read", "agent": "learning", "kind": "slipping",
                                           "values": {"taskTitle": "Read", "unfinished": 3}}])
        self.assertEqual([reminder["kind"] for reminder in self.store.reminders(back(0))], ["length-off"],
                         "a day posts each issue once, so the next day's other figures bring it back")
        self.post(back(-1), "slipping", "slipping:learning:read", taskTitle="Read", unfinished=3)
        self.assertEqual([reminder["kind"] for reminder in self.store.reminders(back(-1))], ["slipping"])

    def test_dismissing_the_group_dismisses_every_reminder_shown_and_nothing_else(self):
        self.post(back(0), "slipping", "slipping:learning:read", taskTitle="Read")
        self.post(back(0), "day-wont-fit", agent="orchestrator", count=3, taskMinutes=240, freeMinutes=120)
        self.post(back(0), "usual-length", "usual-length:read:45", taskTitle="Read", usualMinutes=45, setMinutes=30)
        ids = [reminder["id"] for reminder in self.day()["reminders"]]
        self.assertEqual(len(ids), 2)
        day = self.client.post("/api/reminders/dismiss", json={"ids": ids}).json()
        self.assertEqual(day["reminders"], [])
        self.assertEqual([notice["kind"] for notice in day["notices"]], ["slipping", "day-wont-fit", "usual-length"],
                         "Ava's messages are kept; only Today's reminders go")


if __name__ == "__main__":
    unittest.main()
