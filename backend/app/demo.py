"""The demo workspace: two months of one made-up person's use of DayWright, ending today, with two weeks planned ahead.

It is made the first time the demo opens, and again on Reset (see workspace), in the demo's own folder in DayWright's
data folder: its database, which holds its vector store, and its Library folder of study files the demo writes.
Nothing outside that folder is written while it is made. The two months are lived through DayWright's own service,
day by day, at the times a person would act, so every record, plan, report, pattern and notice comes from the same code
as the user's own; a fixed seed makes the same day give the same demo. While the demo is made no model runs: a stand-in
answers the questions the service puts to one (whether a file is study material, which plans suit a day, and Ava's
replies in the last week's conversation), and says it isn't running to everything else.
"""

from __future__ import annotations

import calendar
import io
import json
import os
import random
import shutil
import uuid
import zipfile
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Callable, Iterator
from unittest.mock import patch
from xml.sax.saxutils import escape

from docx.opc.constants import CONTENT_TYPE, NAMESPACE, RELATIONSHIP_TYPE
from docx.oxml.ns import nsmap

from .config import DEMO_VARIABLE
from .memory import CLASSIFY_ROLE
from .plan_choice import CHOICE_ROLE
from .recall import CONDENSE_ROLE
from .retrieval import EMBEDDING_DIMENSION, EmbeddingUnavailable

# The seed every demo is made from, so the same day gives the same demo.
SEED = 56
# How far past today the demo has its days planned.
PLANNED_AHEAD_DAYS = 14
# The moment of its last day a demo is made at when none is given, as a test makes it: the service gives the moment
# it is opened.
MADE_AT = time(18, 0)
# The demo's study folder, connected to its Library and named as a person's own would be, and the folder its imported
# file comes from, inside its own folder.
LIBRARY_FOLDER = "Study notes"
IMPORTS_FOLDER = "Imports"
# The folder, inside the demo's, that its database and the files beside it are made in, then moved out of.
_MAKING = ".making"
# A made-up website, on this Mac's own loopback address: a look-up from the demo never goes beyond this Mac.
_WEBSITE = "http://127.0.0.1/spanish-drills/irregular-verbs"


def demo_span(end: date) -> tuple[date, date]:
    """Return the demo's first and last day: the same calendar date two months before `end`, or that month's last day
    when it has no such date, through `end`. Two months always hold the whole month before `end`'s, and more than 30
    days, whatever day the demo is made on."""
    year, month = (end.year, end.month - 2) if end.month > 2 else (end.year - 1, end.month + 10)
    return date(year, month, min(end.day, calendar.monthrange(year, month)[1])), end


def carry_over_day(end: date) -> date:
    """Return the last weekday before `end`, whose email is left partly done, so Work carries something over into the
    demo's today whatever weekday it is made on; the other days' outcomes are drawn, and may leave none."""
    return next(end - timedelta(days=back) for back in range(1, 8) if (end - timedelta(days=back)).weekday() < 5)


class _Moment:
    """The moment the made-up person acts at, which every module of the service reads as now while the demo is made."""
    now = datetime(2000, 1, 1)


class _Today(date):
    """The calendar's date, as the demo's moment says it is."""

    @classmethod
    def today(cls) -> date:
        return date(_Moment.now.year, _Moment.now.month, _Moment.now.day)


class _Now(datetime):
    """The clock, as the demo's moment says it is: the Mac's local time, or in the time zone asked for."""

    @classmethod
    def now(cls, tz=None) -> datetime:
        return _Moment.now if tz is None else _Moment.now.astimezone(tz)


@contextmanager
def _lived(seed: int) -> Iterator[None]:
    """Have the service's modules read the demo's moment as now, and make every new id from the seed, while the demo is
    made; both as they were afterwards."""
    from . import (agents, conversation, database, domain_records, folder_check, learning_tasks, main, recall, retrieval,
                   source_store, state_graph)
    ids = random.Random(seed)
    swapped = []
    for module in (agents, conversation, database, domain_records, folder_check, learning_tasks, main, recall, retrieval,
                   source_store, state_graph):
        for name, stand_in in (("date", _Today), ("CalendarDate", _Today), ("datetime", _Now)):
            if getattr(module, name, None) in (date, datetime):
                swapped.append((module, name, getattr(module, name)))
                setattr(module, name, stand_in)
    try:
        with patch.object(uuid, "uuid4", lambda: uuid.UUID(int=ids.getrandbits(128), version=4)):
            yield
    finally:
        for module, name, real in swapped:
            setattr(module, name, real)


# The stand-in model's reason for choosing each kind of plan, in English and Chinese.
_WHY = {
    "deep-focus": ("The day's longest tasks fit back to back before the afternoon meetings.",
                   "当天最长的几项任务可以在下午会议前连续完成。"),
    "lighter": ("Energy was low, so the day keeps its fixed times and leaves room to rest.",
                "精力偏低，因此保留固定安排并留出休息时间。"),
    "other": ("It keeps the fixed times and moves the flexible tasks to the free windows.",
              "保留固定安排，把灵活任务移到空闲时段。"),
}
# What the stand-in reads each of the person's statements to Ava as, by words in it; the last when none match.
_READINGS = (
    ("study best", {"lasting": True, "kind": "note", "rule": None, "area": "learning", "task": None, "updates": None}),
    ("Sunday mornings free", {"lasting": True, "kind": "rule", "rule": "keep-free", "area": None, "task": None,
                              "updates": None}),
    ("", {"lasting": True, "kind": "note", "rule": None, "area": "general", "task": None, "updates": None}),
)
# Ava's answers, through the stand-in, to the questions in the last week's conversation that neither her rules nor the
# records answer; what was done on a day, the records answer.
_ANSWERS = (
    ("How did this week go?", "Most of this week went as planned: the stand-ups, Spanish practice and the runs held "
                              "steady. The personal website hasn't moved for over a week; one small step would get it "
                              "going again."),
)


class _StandIn:
    """The local model while the demo is made: it judges the Library folder's files, chooses the day's plans, and gives
    Ava's answers while the person talks to her, as the made-up person's model would have; for everything else it is not
    running."""

    def __init__(self) -> None:
        # Whether the person is talking to Ava, when she answers; DayWright's own rules make her cards.
        self.talking = False

    def status(self) -> dict:
        state = "ready" if self.talking else "unavailable"
        return {"state": state, "running": self.talking, "runtimeAvailable": self.talking,
                "chatModelAvailable": self.talking, "embeddingModelAvailable": False, "voiceModelAvailable": False,
                "label": "Demo"}

    def reply(self, message: str, context: str, system_prompt: str | None = None, max_tokens: int | None = None):
        if message.endswith("Is this study material?"):
            return ("no" if "Title: Receipt" in message else "yes"), "demo"
        if system_prompt == CHOICE_ROLE:
            kinds = [candidate["kind"] for candidate in json.loads(context).get("candidates", [])
                     if candidate.get("kind") != "balanced"]
            return json.dumps({"plans": [{"kind": kind, "why": _WHY.get(kind, _WHY["other"])[0],
                                          "whyZh": _WHY.get(kind, _WHY["other"])[1]} for kind in kinds[:2]]}), "demo"
        if system_prompt == CLASSIFY_ROLE:
            said = f"{message} {context}"
            return json.dumps(next((reading for words, reading in _READINGS if words in said), _READINGS[-1][1])), "demo"
        if system_prompt == CONDENSE_ROLE:
            asked = [line[len("You: "):] for line in message.splitlines() if line.startswith("You: ")]
            return json.dumps({"asked": asked, "mentioned": [], "open": [], "remember": []}), "demo"
        if self.talking:
            return next((answer for question, answer in _ANSWERS if question in message), ""), "demo"
        return "", "rules"

    def stop(self) -> None:
        return None


class _NoSearch:
    """The embedding model while the demo is made: not running, so the Library folder's files wait to be indexed until
    the demo runs with the user's model; notes and the imported file, which are kept with their vectors, take empty
    ones."""

    def __init__(self) -> None:
        self.empty = False

    def status(self) -> dict:
        return {"state": "unavailable", "running": False, "modelAvailable": False, "runtimeAvailable": False,
                "label": "Demo", "dimensions": EMBEDDING_DIMENSION}

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not self.empty:
            raise EmbeddingUnavailable("No embedding model runs while the demo is made")
        return [[0.0] * EMBEDDING_DIMENSION for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        raise EmbeddingUnavailable("No embedding model runs while the demo is made")

    def stop(self) -> None:
        return None


class _NoVoice:
    """Speech while the demo is made: not running."""

    def status(self) -> dict:
        return {"state": "unavailable", "modelAvailable": False, "runtimeAvailable": False, "label": "Demo"}


class _NoModels:
    """The models folder while the demo is made: none, so nothing reads or checks a model."""

    def states(self) -> dict:
        return {"folder": None, "state": "none", "models": [], "runner": None}

    def path(self, role: str) -> None:
        return None


# --- The Library folder: about fifteen study files of the made-up person's, as Markdown, a PDF and a Word file -------

def _lesson(title: str, sections: tuple[tuple[str, str], ...]) -> str:
    """A Markdown study file: its title, then each section's heading and text."""
    return f"# {title}\n\n" + "\n\n".join(f"## {heading}\n\n{text}" for heading, text in sections) + "\n"


_FILES = {
    "Spanish/01 Greetings and introductions.md": _lesson("Greetings and introductions", (
        ("Saying hello", "Hola, buenos días and buenas tardes cover most of the day; buenas noches is for the evening."),
        ("Introducing yourself", "Me llamo Alex. Soy de Leeds. Encantado or encantada answers a new name."),
        ("Asking how someone is", "¿Qué tal? is casual; ¿Cómo está usted? is polite. Answer with bien, gracias."))),
    "Spanish/02 Present tense verbs.md": _lesson("Present tense verbs", (
        ("Regular -ar verbs", "hablar: hablo, hablas, habla, hablamos, habláis, hablan."),
        ("Regular -er and -ir verbs", "comer: como, comes, come; vivir: vivo, vives, vive."),
        ("Common irregulars", "tener, ir and hacer change their stem; learn tengo, voy and hago first."),
        ("Practice sentences", "Write five sentences about your week using one verb from each group."))),
    "Spanish/03 Ser and estar.md": _lesson("Ser and estar", (
        ("Ser for what something is", "Identity, origin, time and lasting traits: soy profesor, es lunes."),
        ("Estar for how and where", "Location and passing states: estoy cansado, el libro está en la mesa."),
        ("Pairs that change meaning", "ser listo is clever, estar listo is ready; ser aburrido is boring."))),
    "Spanish/04 Food and ordering.md": _lesson("Food and ordering", (
        ("At the café", "Un café con leche, por favor. ¿Me trae la cuenta?"),
        ("Menus", "Primer plato, segundo plato and postre make up a menú del día."),
        ("Saying what you like", "Me gusta el pan; me gustan las aceitunas. Gustar agrees with the thing liked."))),
    "Spanish/05 Past tense.md": _lesson("The preterite", (
        ("Regular endings", "hablé, hablaste, habló; comí, comiste, comió."),
        ("Irregular stems", "estuve, tuve, hice, fui: memorise them as a set."),
        ("Telling a story", "Ayer fui al mercado, compré fruta y volví a casa."))),
    "Spanish/06 Travel and directions.md": _lesson("Travel and directions", (
        ("Asking the way", "¿Dónde está la estación? Siga recto y gire a la derecha."),
        ("Tickets", "Un billete de ida y vuelta a Sevilla, por favor."),
        ("At the hotel", "Tengo una reserva a nombre de Alex."))),
    "Statistics/Descriptive statistics.md": _lesson("Descriptive statistics", (
        ("Mean, median and mode", "The median resists outliers; the mean uses every value."),
        ("Spread", "Variance is the mean squared distance from the mean; the standard deviation is its root."),
        ("Reading a box plot", "The box holds the middle half of the data; whiskers reach the rest."))),
    "Statistics/Probability basics.md": _lesson("Probability basics", (
        ("Events and outcomes", "A probability is a number from 0 to 1 that an event happens."),
        ("Independence", "Two events are independent when one tells you nothing about the other."),
        ("Expected value", "Weigh each outcome by its probability and add them up."))),
    "Reading/Thinking in Systems - notes.md": _lesson("Thinking in Systems - notes", (
        ("Stocks and flows", "A stock changes only through its inflows and outflows."),
        ("Feedback loops", "Balancing loops seek a goal; reinforcing loops grow or collapse."),
        ("Leverage points", "Rules and goals change a system more than its numbers do."))),
    "Piano/Scales and fingering.md": _lesson("Scales and fingering", (
        ("C major", "Thumb under after the third finger going up; third over the thumb coming down."),
        ("G major", "One sharp, F sharp; the same fingering as C major."),
        ("Practising slowly", "Play at half speed with a metronome before speeding up."))),
    "Spanish/Pronunciation tips.md": _lesson("Pronunciation tips", (
        ("Vowels", "Five pure vowels, never reduced: a, e, i, o, u."),
        ("The letter r", "A single r is tapped; rr and an r at the start of a word are rolled."),
        ("Stress", "Words ending in a vowel, n or s stress the second-to-last syllable."))),
    "Receipt - language school.md": "# Receipt\n\nLanguage school, autumn term. Paid 240.00 EUR by card.\n",
}
# The PDF of the folder, as lines of text, and the Word file, as its headings and paragraphs.
_PDF = ("Spanish/Verb tables.pdf", ("Spanish verb tables", "hablar: hablo hablas habla hablamos hablan",
                                    "comer: como comes come comemos comen", "vivir: vivo vives vive vivimos viven",
                                    "ser: soy eres es somos son", "estar: estoy estás está estamos están"))
_DOCX = ("Spanish/Grammar cheat sheet.docx", (
    ("Heading1", "Grammar cheat sheet"), ("Heading2", "Articles"),
    (None, "el and la are the; un and una are a; plurals add -s or -es."),
    ("Heading2", "Adjectives"), (None, "Adjectives follow the noun and agree with it: una casa blanca."),
    ("Heading2", "Questions"), (None, "Questions open with ¿ and close with ?; the verb often comes first.")))
# A scanned worksheet: a PDF with a page and no text, which can't be studied from; it arrives late in the two months.
_SCANNED = "Spanish/Scanned worksheet.pdf"
# A file imported from outside the folder.
_IMPORTED = ("Conference talk - learning languages as an adult.md", _lesson("Learning languages as an adult", (
    ("Spacing", "Short daily practice beats long weekly sessions."),
    ("Speaking early", "Speak from the first week, however badly."))))


def _pdf(lines: tuple[str, ...]) -> bytes:
    """A one-page PDF of `lines` in Helvetica, or of a grey block with no text when there are none."""
    text = "".join(f"({line.translate({40: '[', 41: ']'}).encode('latin-1', 'replace').decode('latin-1')}) Tj T* "
                   for line in lines)
    stream = f"BT /F1 12 Tf 72 720 Td 16 TL {text}ET" if lines else "0.85 g 72 300 468 400 re f"
    objects = ("<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
               "/Resources << /Font << /F1 5 0 R >> >> >>",
               f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream",
               "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1")
    table = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{offset:010d} 00000 n \n" for offset in offsets).encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{table}\n%%EOF\n".encode()
    return bytes(out)


def _docx(paragraphs: tuple[tuple[str | None, str], ...]) -> bytes:
    """A Word file of `paragraphs`, each with its style ("Heading1", "Heading2" or None) and text; every part carries
    the same date, so the same paragraphs make the same file."""
    body = "".join(f'<w:p>{f"<w:pPr><w:pStyle w:val=\"{style}\"/></w:pPr>" if style else ""}'
                   f'<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>' for style, text in paragraphs)
    # The package's namespaces and types, as python-docx, which reads the file back, names them.
    head = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    parts = {
        "[Content_Types].xml": f'{head}<Types xmlns="{NAMESPACE.OPC_CONTENT_TYPES}"><Default Extension="rels" '
        f'ContentType="{CONTENT_TYPE.OPC_RELATIONSHIPS}"/><Default Extension="xml" ContentType="{CONTENT_TYPE.XML}"/>'
        f'<Override PartName="/word/document.xml" ContentType="{CONTENT_TYPE.WML_DOCUMENT_MAIN}"/></Types>',
        "_rels/.rels": f'{head}<Relationships xmlns="{NAMESPACE.OPC_RELATIONSHIPS}"><Relationship Id="rId1" '
        f'Type="{RELATIONSHIP_TYPE.OFFICE_DOCUMENT}" Target="word/document.xml"/></Relationships>',
        "word/document.xml": f'{head}<w:document xmlns:w="{nsmap["w"]}"><w:body>{body}</w:body></w:document>',
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, text in parts.items():
            archive.writestr(zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)), text)
    return buffer.getvalue()


def _write_library(folder: Path) -> None:
    """Write the demo's Library folder and the file it imports from outside it."""
    for relative, text in _FILES.items():
        (folder / LIBRARY_FOLDER / relative).parent.mkdir(parents=True, exist_ok=True)
        (folder / LIBRARY_FOLDER / relative).write_text(text, encoding="utf-8")
    (folder / LIBRARY_FOLDER / _PDF[0]).write_bytes(_pdf(_PDF[1]))
    (folder / LIBRARY_FOLDER / _DOCX[0]).write_bytes(_docx(_DOCX[1]))
    (folder / IMPORTS_FOLDER).mkdir()
    (folder / IMPORTS_FOLDER / _IMPORTED[0]).write_text(_IMPORTED[1], encoding="utf-8")


# --- The made-up person's goals and tasks ----------------------------------------------------------------------------

# Each goal: the key the script knows it by, its area and its title.
_GOALS = (
    ("spanish", "learning", "Spanish to B1"), ("statistics", "learning", "Statistics refresher"),
    ("systems", "learning", "Read Thinking in Systems"), ("piano", "learning", "Piano basics"),
    ("shed", "project", "Build the garden shed"), ("website", "project", "Personal website"),
    ("photos", "project", "Photo book of the summer"), ("bike", "project", "Restore the old bike"),
    ("run", "life", "Run three times a week"), ("cook", "life", "Cook at home more"),
    ("report", "work", "Q4 report"), ("onboarding", "work", "Onboarding guide"),
)
# Each repeating task: the weekdays it falls on (Monday 0; None for every day), title, area, start (None for one
# without a set time), minutes and goal.
# The weekly task whose advice is discarded and raised again (see _week_report).
_REVIEW = "Weekly review"
_REPEATS = (
    ((0, 1, 2, 3, 4), "Team stand-up", "work", "09:30", 30, None),
    ((3,), "1:1 with Sam", "work", "14:00", 30, "onboarding"),
    (None, "Spanish practice", "learning", None, 30, "spanish"),
    ((6,), _REVIEW, "learning", "16:30", 45, None),
    ((0, 2, 5), "Morning run", "life", "07:00", 40, "run"),
    (None, "Evening journaling", "life", "21:15", 30, None),
    ((1, 4), "Piano practice", "learning", "19:00", 30, "piano"),
    ((5,), "Groceries", "life", "10:30", 45, "cook"),
)
# Work's one-off tasks on weekdays, one a day in turn, beside Answer email every weekday.
_WORK = (
    ("Q4 report: gather the numbers", None, 60, "report"), ("Onboarding guide: outline", None, 45, "onboarding"),
    ("Review pull requests", None, 45, None), ("Planning meeting", "11:00", 60, None),
    ("Q4 report: draft the summary", None, 90, "report"), ("Onboarding guide: first-week checklist", None, 60, "onboarding"),
    ("Write meeting notes", None, 30, None), ("Q4 report: charts", None, 60, "report"),
    ("Onboarding guide: tools section", None, 60, "onboarding"), ("Review pull requests", None, 45, None),
)
# Life's one-off tasks by weekday.
_LIFE = {0: ("Laundry", None, 45, None), 2: ("Cook a new recipe", None, 60, "cook"), 4: ("Call Mum", "20:00", 30, None),
         5: ("Meal prep for the week", None, 45, "cook"), 6: ("Tidy the flat", None, 60, None)}
# The shed's steps, one each Saturday, in order; the last two are still ahead.
_SHED = ("Shed: clear and level the ground", "Shed: lay the base", "Shed: build the floor frame",
         "Shed: frame the back wall", "Shed: frame the side walls", "Shed: frame the front wall", "Shed: raise the walls",
         "Shed: fit the roof rafters", "Shed: lay the roof boards", "Shed: felt the roof", "Shed: hang the door",
         "Shed: paint the walls", "Shed: fit the shelves", "Shed: move the tools in")
# The website's steps, on Thursday evenings, until they stop: those of its last days are skipped.
_WEBSITE_STEPS = ("Website: pick a theme", "Website: write the About page", "Website: set up hosting",
                  "Website: projects page", "Website: contact form", "Website: blog layout", "Website: first post")
# The bike's steps, before it is paused.
_BIKE = ("Bike: strip the frame", "Bike: order a new chain", "Bike: clean the gears")
# The six chapters read toward Thinking in Systems, every one done.
_CHAPTERS = tuple(f"Thinking in Systems: chapter {number}" for number in range(1, 7))


class _Life:
    """The made-up person, acting through DayWright's own service at the moments they would."""

    def __init__(self, folder: Path, database: Path, seed: int) -> None:
        from fastapi.testclient import TestClient
        from .database import Database
        from .main import create_app

        self.folder = folder
        self.model, self.search = _StandIn(), _NoSearch()
        self.app = create_app(database_path=database, gateway=self.model, embedding_gateway=self.search,
                              speech_gateway=_NoVoice(), library=_NoModels(), switch=lambda *_: None, day_jobs=False)
        self.client = TestClient(self.app)
        # The same database, for what the person did earlier through cards whose conversation is condensed by now.
        self.store = Database(database)
        self.rng = random.Random(seed)
        # What the person has made so far: the goals and Library sources by the script's names for them, the Learn tasks
        # made from the Library, the other tasks in a Learning goal that don't repeat, how many shed and website steps
        # were added, and the two Sundays whose weekly review is partly done: the first one's advice is discarded, and
        # the second one raises it again.
        self.goals: dict[str, str] = {}
        self.sources: dict[str, str] = {}
        self.lessons: set[str] = set()
        self.studies: set[str] = set()
        self.shed = self.website = 0
        self.reviews: tuple[date, ...] = ()
        self.folder_id: str | None = None
        self.website_source: str | None = None
        # The title of the last task left without a status, as a later message to Ava names it, and whether a task
        # was moved to the next day yet.
        self.left = ""
        self.moved = False

    def at(self, day: date, clock: str) -> None:
        """Move the clock to `clock` on `day`."""
        _Moment.now = datetime.combine(day, time.fromisoformat(clock))

    def call(self, method: str, path: str, **request) -> dict:
        """Ask the service, a second after the last request, and wait for the work it starts in the background.

        Raises:
            RuntimeError: When the service refuses, as only a mistake in the demo's script can make it.
        """
        _Moment.now += timedelta(seconds=1)
        answer = self.client.request(method, path, **request)
        for thread in list(self.app.state.indexing):
            thread.join()
        if answer.status_code >= 400:
            raise RuntimeError(f"The demo's {method} {path} was refused: {answer.status_code} {answer.text}")
        return answer.json()

    def add(self, day: date, title: str, area: str, start: str | None, minutes: int, goal: str | None = None,
            repeat: str = "none") -> dict:
        """Add a task, as the task form does."""
        made = self.call("POST", "/api/daily-items", json={
            "date": day.isoformat(), "title": title, "domain": area, "startTime": start, "durationMinutes": minutes,
            "constraintKind": "fixed" if start else "flexible", "repeatKind": repeat, "goalId": self.goals.get(goal)})
        if area == "learning" and goal and repeat == "none":
            self.studies.add(made["id"])
        return made

    def say(self, day: date, message: str, decision: str | None, shown: date) -> None:
        """Talk to Ava, with `shown` the day on show; her card, when she makes one, confirmed or dismissed
        (`decision`) a minute later, or left waiting.

        Raises:
            RuntimeError: When Ava makes no card where the script expects one, as only a mistake in it can.
        """
        self.model.talking = True
        try:
            reply = self.call("POST", "/api/chat", json={"date": shown.isoformat(), "message": message})
        finally:
            self.model.talking = False
        card = reply.get("proposedAction")
        if decision and not card:
            raise RuntimeError(f"Ava made no card for the demo's message {message!r}: "
                               f"{reply.get('assistantMessage', {}).get('content')!r}")
        if decision:
            _Moment.now += timedelta(minutes=1)
            self.call("POST", f"/api/actions/{card['id']}", json={"decision": decision})


def build_demo(database: Path, end: date, seed: int = SEED, at: time = MADE_AT) -> None:
    """Make the demo workspace, its database at `database` and its Library folder beside it, ending on `end`, at the
    moment `at` of that day, up to which its tasks are reported.

    A demo half made, as by a stop while it was made, is made again: the database is made apart and moved in place,
    last, only once everything is in it, and the demo's folder is cleared before a new one is made in it.
    """
    folder = database.parent
    shutil.rmtree(folder, ignore_errors=True)
    making = folder / _MAKING
    making.mkdir(parents=True)
    _write_library(folder)
    # The demo is made as the demo: the person's settings file is only read, and no real database is reached.
    with patch.dict(os.environ, {DEMO_VARIABLE: "1"}), _lived(seed):
        _live(_Life(folder, making / database.name, seed), *demo_span(end), at)
    for made in sorted(making.iterdir(), key=lambda path: path.name == database.name):
        os.replace(made, folder / made.name)
    making.rmdir()


# Days counted back from the demo's last day (0 is today), each with something of its own.
_LOW_ENERGY = (3, 17, 26, 40)        # energy 2, which Ava's notice of a low-energy day follows
_NO_READING = (12, 31, 47)           # no energy reading
_UNPLANNED = (4, 11, 22, 33, 52)     # no plan set: the tasks keep their own times
_PAUSED = (37,)                      # paused from 13:10 to 15:00
_ENDED_PAUSED = 19                   # paused before lunch and never resumed, so the day ended paused
_UNANSWERED = (9, 29)                # one task left without a status
_TO_CHECK = 24                       # one task done at twice its length and more, a time to check
_STATISTICS_PAUSED = 21              # the Statistics goal is paused
_WEBSITE_STALLS = 12                 # the website's last step done; nothing toward it after
_LATE_SKIP = 7                       # a task of the day before skipped through Ava, after that day ended
_SCANNED_ARRIVES = 3                 # a scanned worksheet put in the Library folder; its check's card waits
_MOVED = 16                          # the first Monday to Thursday from here back four days moves its work task to the next day
_RECENT_STUDY = 7                    # a lesson or other task in a Learning goal left undone is no older: earlier ones are done
_EVENING_STUDY = time(19, 30)        # when an older one the set plan left out is studied
# Days counted from the demo's first day.
_LIBRARY_DAY = 1                     # the Library folder connected and checked, the notes, an import and a website
_BIKE_PAUSED = 14                    # the bike goal is paused
_CHAPTER_DAYS = (8, 11, 15, 18, 22, 25)
# How many of yesterday's last tasks wait for today's catch-up.
_LEFT_FOR_TODAY = 2
# The Work task of every weekday; the last weekday's before today is left partly done (see carry_over_day).
_EMAIL = "Answer email"
# Days whose evening tasks may go unreported or unplanned, so neither weekly review partly done falls on one.
_REVIEW_UNSURE = (1, _ENDED_PAUSED, _LATE_SKIP + 1, *_UNANSWERED, *_UNPLANNED)
# A pause's times on a paused day, and the pause that ends a day paused.
_PAUSE = ("13:10", "15:00")
_LAST_PAUSE = "11:30"
# The latest a task is reported, before the day ends at 22:00.
_LAST_REPORT = time(21, 55)


def _live(life: _Life, first: date, end: date, at: time) -> None:
    """Live the demo's days from `first` to `end`, the last up to the moment `at`, and plan the days after it."""
    _begin(life, first)
    sundays = [day for day in (first + timedelta(days=offset) for offset in range((end - first).days))
               if day.weekday() == 6 and (end - day).days not in _REVIEW_UNSURE]
    life.reviews = (sundays[1], sundays[-2])
    day = first
    while day <= end:
        _day(life, first, day, end)
        day += timedelta(days=1)
    _condense(life, end)
    _ahead(life, end)
    # Today as the person has lived it so far: what ended before the demo is made is reported, as on any day.
    _report(life, end, 0, until=datetime.combine(end, at))


def _condense(life: _Life, end: date) -> None:
    """Ava's pass over the conversation as the demo opens today, as her model makes it: each earlier day condensed to
    its summary, and the full conversation older than her window cleared."""
    from . import recall

    life.at(end, "07:55")
    life.model.talking = True
    try:
        recall.keep(life.store, life.model, None, end.isoformat())
    finally:
        life.model.talking = False


def _begin(life: _Life, first: date) -> None:
    """The first morning: the goals and the repeating tasks."""
    life.at(first, "07:00")
    for key, area, title in _GOALS:
        life.goals[key] = life.call("POST", "/api/goals", json={"title": title, "domain": area})["id"]
    for weekdays, title, area, start, minutes, goal in _REPEATS:
        for weekday in weekdays if weekdays is not None else (None,):
            day = first if weekday is None else first + timedelta(days=(weekday - first.weekday()) % 7)
            life.add(day, title, area, start, minutes, goal, "daily" if weekday is None else "weekly")


def _day(life: _Life, first: date, day: date, end: date) -> None:
    """One day of the two months: the morning's energy, tasks and plan, then each task reported as it ends, and on
    Sunday evening the week's report."""
    index, back = (day - first).days, (end - day).days
    life.at(day, "07:20")
    if back not in _NO_READING:
        level = 2 if back in _LOW_ENERGY else life.rng.choice((3, 3, 4, 4, 4, 5))
        life.call("PUT", f"/api/energy/{day.isoformat()}", json={"level": level})
    view = life.call("GET", "/api/bootstrap", params={"date": day.isoformat()})
    if day < end:
        _decide(life, view["dayItems"])
    for said_back, entry in _MEMORY:
        if said_back == back:
            life.at(day, "07:25")
            ends = entry.get("ends")
            life.store.save_memory({**entry, "saidOn": day.isoformat(),
                                    "endsOn": (end - timedelta(days=ends)).isoformat() if ends is not None else None})
    if index == _LIBRARY_DAY:
        _library(life, day)
    if back == _SCANNED_ARRIVES:
        life.at(day, "08:00")
        (life.folder / LIBRARY_FOLDER / _SCANNED).write_bytes(_pdf(()))
        life.call("POST", f"/api/sources/folder/{life.folder_id}/refresh")
    if index == _BIKE_PAUSED:
        life.call("PUT", f"/api/goals/{life.goals['bike']}", json={"title": "Restore the old bike", "status": "paused"})
    if back == _STATISTICS_PAUSED:
        life.call("PUT", f"/api/goals/{life.goals['statistics']}", json={"title": "Statistics refresher", "status": "paused"})
    _tasks(life, index, day, back)
    _lessons(life, index, day, back)
    if day == end:
        life.call("POST", "/api/plan/generate", json={"date": day.isoformat()})
        return
    if back not in _UNPLANNED:
        planned = life.call("POST", "/api/plan/generate", json={"date": day.isoformat()})
        life.call("POST", "/api/plan/confirm", json={"date": day.isoformat(),
                                                     "variantId": life.rng.choice(planned["variants"])["id"]})
    _report(life, day, back)
    if day.weekday() == 6:
        _week_report(life, day)


def _decide(life: _Life, items: list[dict]) -> None:
    """The morning's look at what the Summary agent prepared for the day, before it is planned: each suggestion
    accepted, as the person keeps the repeats it prepares, or dismissed when the day can't take it. Today's wait."""
    for item in items:
        if item["acceptance"] == "pending":
            try:
                life.call("POST", f"/api/daily-items/{item['id']}/accept")
            except RuntimeError:
                life.call("POST", f"/api/daily-items/{item['id']}/dismiss")


def _tasks(life: _Life, index: int, day: date, back: int) -> None:
    """The one-off tasks the person adds on the morning of a day."""
    weekday = day.weekday()
    if weekday < 5:
        life.add(day, _EMAIL, "work", None, 30)
        title, start, minutes, goal = _WORK[index % len(_WORK)]
        made = life.add(day, title, "work", start, minutes, goal)
        if _MOVED <= back <= _MOVED + 4 and weekday < 4 and not life.moved:
            life.moved = True
            life.call("PUT", f"/api/daily-items/{made['id']}", json={
                "date": (day + timedelta(days=1)).isoformat(), "title": title, "domain": "work", "startTime": start,
                "durationMinutes": minutes, "constraintKind": "fixed" if start else "flexible", "repeatKind": "none",
                "goalId": made["goalId"]})
    if weekday in _LIFE:
        title, start, minutes, goal = _LIFE[weekday]
        life.add(day, title, "life", start, minutes, goal)
    if weekday in (0, 3) and back > _STATISTICS_PAUSED:
        life.add(day, "Statistics: practice problems", "learning", None, 45, "statistics")
    if index in _CHAPTER_DAYS:
        life.add(day, _CHAPTERS[_CHAPTER_DAYS.index(index)], "learning", None, 60, "systems")
    if weekday == 5 and life.shed < len(_SHED) - 2:
        life.add(day, _SHED[life.shed], "project", "14:00", 90, "shed")
        life.shed += 1
    if weekday == 3 and life.website < len(_WEBSITE_STEPS) - 1 and back >= _WEBSITE_STALLS - 6:
        life.add(day, _WEBSITE_STEPS[life.website], "project", "20:00", 60, "website")
        life.website += 1
    if index in (2, 6, 16):
        life.add(day, _BIKE[(2, 6, 16).index(index)], "project", None, 60, "bike")
    # A small step for the shed yesterday, whatever the weekday, so a project is on track today.
    if back == 1:
        life.add(day, "Shed: order the roofing felt", "project", "13:15", 30, "shed")
    # Sunday is the week's lightest day: as today it holds two tasks more, so Today is as full as on any other day.
    if back == 0 and weekday == 6:
        life.add(day, "Long walk", "life", None, 60)
        life.add(day, "Plan the week ahead", "life", "19:30", 30)


def _lessons(life: _Life, index: int, day: date, back: int) -> None:
    """Learn tasks made from the Library's files, as From a source makes them: the Spanish units one a day, a pass back
    over the first two, and the Statistics files."""
    spanish = [life.sources[path] for path in sorted(life.sources) if path.startswith("Spanish/0")]
    if index == _LIBRARY_DAY:
        sources, goal, fresh = spanish[:3], "spanish", False
    elif index == 15:
        sources, goal, fresh = spanish[3:6], "spanish", False
    elif index in (3, 20):
        sources = [life.sources["Statistics/Descriptive statistics.md" if index == 3 else "Statistics/Probability basics.md"]]
        goal, fresh = "statistics", False
    elif back == 20:
        sources, goal, fresh = spanish[:2], "spanish", True
    else:
        return
    made = life.call("POST", "/api/learning-tasks", json={
        "sourceIds": sources, "date": (day + timedelta(days=1)).isoformat(), "goal": {"goalId": life.goals[goal]},
        "oneADay": True, "fresh": fresh})
    life.lessons.update(task["id"] for task in made["tasks"])


def _library(life: _Life, day: date) -> None:
    """The Library on its first morning: the folder connected and its check's card confirmed with the receipt
    unticked, two notes, a file imported from outside the folder, and a website, looked up once."""
    from . import source_store

    folder = life.call("POST", "/api/sources/folder", json={"path": str(life.folder / LIBRARY_FOLDER)})
    life.folder_id = folder["id"]
    card = next(notice["proposal"] for notice in life.call("GET", "/api/bootstrap", params={"date": day.isoformat()})["notices"]
                if notice["kind"] == "folder-check")
    life.call("POST", f"/api/actions/{card['id']}", json={
        "decision": "confirmed", "ticked": [file["path"] for file in card["payload"]["files"] if file["verdict"] == "ready"]})
    life.sources = {source["relativePath"]: source["id"] for source in
                    life.call("GET", "/api/knowledge")["sources"] if source.get("relativePath")}
    life.search.empty = True
    for title, text in _NOTES:
        life.call("POST", "/api/knowledge/sources", json={"title": title, "sourceType": "note", "text": text})
    life.call("POST", "/api/sources/files/import", json={"paths": [str(life.folder / IMPORTS_FOLDER / _IMPORTED[0])]})
    life.search.empty = False
    website = life.call("POST", "/api/sources/website", json={"address": _WEBSITE, "briefing": "Drills for irregular verbs."})
    with patch.object(source_store, "fetch_page", lambda address: _PAGE):
        life.call("POST", f"/api/sources/{website['id']}/look-up")
    life.website_source = website["id"]


# The Library's notes, and the website's page as its look-up reads it.
_NOTES = (("Spanish false friends", "Embarazada means pregnant, not embarrassed. Constipado means a cold. "
                                    "Librería is a bookshop; a library is a biblioteca."),
          ("Shed materials", "Treated timber 47 x 75 for the frame, 12 mm OSB for the floor, roofing felt and clout "
                             "nails, two hinges and a hasp."))
_PAGE = {"title": "Irregular Spanish verbs", "briefing": "Drills for the twenty most common irregular verbs.",
         "outline": [{"title": "Present tense", "topics": [{"title": "Stem changes"}, {"title": "Yo forms"}]},
                     {"title": "Preterite", "topics": [{"title": "Irregular stems"}]}]}


def _report(life: _Life, day: date, back: int, until: datetime | None = None) -> None:
    """Report the day's tasks as each ends, promptly: mostly done, some over or under their time, the odd one partly
    done or skipped, and on one day one done at twice its length and more, a time to check; with the day's pause, and
    what is left without a status. Today's, `until` the moment the demo is made, are done, at their own times: the
    task under way then, and those after it, wait."""
    view = life.call("GET", "/api/bootstrap", params={"date": day.isoformat()})
    # A steady learner catches up: of the lessons and other tasks in a Learning goal, only the last week's may still
    # wait, so each goal's next to study is recent or ahead.
    studied = lambda item_id: back > _RECENT_STUDY and (item_id in life.lessons or item_id in life.studies)  # noqa: E731
    if view["confirmedVariantId"]:
        rows = [(entry["start_time"], entry["duration_minutes"], entry["source_item_id"], entry["title"], entry["id"])
                for entry in view["entries"] if entry["start_time"] and entry["source_item_id"]]
    else:
        rows = [(item["start_time"], item["duration_minutes"], item["id"], item["title"], None)
                for item in view["dayItems"] if item["acceptance"] == "accepted"]
    # Without a set plan a task without a time is current from the morning, in turn: each from the moment the one
    # before it is reported (see time_taken), so each is reported from then, before its limit.
    loose = datetime.combine(day, time(7, 25))
    timeline = []
    checked = back != _TO_CHECK
    for start_text, length, item_id, title, entry_id in rows:
        start = datetime.combine(day, time.fromisoformat(start_text)) if start_text else loose
        status, after = life.rng.choices((("done", length + life.rng.randint(-8, 12)),
                                          ("done", round(length * 1.3) + life.rng.randint(0, 5)),
                                          ("partial", round(length * 0.6)), ("skipped", -2)),
                                         weights=(74, 10, 9, 7) if until is None else (86, 14, 0, 0))[0]
        if title.startswith(("Shed:", "Thinking in Systems:")):
            status, after = "done", length + 5
        if title.startswith("Website:") and back < _WEBSITE_STALLS:
            status, after = "skipped", -2
        if title == _REVIEW and day in life.reviews:
            status, after = "partial", round(length * 0.6)
        if title == _EMAIL and day == carry_over_day(day + timedelta(days=back)):
            status, after = "partial", round(length * 0.6)
        if studied(item_id):
            status, after = "done", length + 5
        if not checked:
            status, after, checked = "done", 2 * length + 5, True
        moment = min(start + timedelta(minutes=after), datetime.combine(day, _LAST_REPORT))
        if not start_text:
            loose = moment + timedelta(minutes=5)
        timeline.append([moment, item_id, entry_id, status, title])
    # One the set plan left out is studied in the evening.
    placed = {row[2] for row in rows}
    timeline += [[datetime.combine(day, _EVENING_STUDY), item["id"], None, "done", item["title"]] for item in view["dayItems"]
                 if item["acceptance"] == "accepted" and studied(item["id"]) and item["id"] not in placed]
    timeline.sort(key=lambda row: row[0])
    if until:
        timeline = [row for row in timeline if row[0] <= until]
    if back == 1:
        # The day's last tasks wait for today's catch-up; the shed's step was done, so a project is on track.
        left = [row for row in timeline if not row[4].startswith("Shed:")][-_LEFT_FOR_TODAY:]
        timeline = [row for row in timeline if row not in left]
    if back in _UNANSWERED or back == _LATE_SKIP + 1:
        left = [row for row in timeline if not studied(row[1])][-1]
        life.left = left[4]
        timeline.remove(left)
    steps: list[tuple[datetime, Callable[[], None]]] = []
    if back in _PAUSED:
        paused, resumed = (datetime.combine(day, time.fromisoformat(clock)) for clock in _PAUSE)
        steps += [(paused, lambda: life.call("POST", "/api/day/pause")), (resumed, lambda: life.call("POST", "/api/day/resume"))]
        for row in timeline:
            if paused <= row[0] < resumed:
                row[0] = resumed + timedelta(minutes=5)
    if back == _ENDED_PAUSED:
        paused = datetime.combine(day, time.fromisoformat(_LAST_PAUSE))
        steps.append((paused, lambda: life.call("POST", "/api/day/pause")))
        # The rest wait, but for what was studied, which is reported while paused.
        timeline = [row for row in timeline if row[0] < paused or studied(row[1])]
    for moment, item_id, entry_id, status, _ in timeline:
        steps.append((moment, lambda item_id=item_id, entry_id=entry_id, status=status: _status(life, item_id, entry_id, status)))
    for said_back, clock, message, decision, before in _CHAT:
        if said_back == back:
            steps.append((datetime.combine(day, time.fromisoformat(clock)),
                          lambda message=message, decision=decision, before=before:
                          life.say(day, message.format(left=life.left), decision, day - timedelta(days=before))))
    for moment, step in sorted(steps, key=lambda step: step[0]):
        life.at(day, moment.strftime("%H:%M"))
        step()


def _status(life: _Life, item_id: str, entry_id: str | None, status: str) -> None:
    """Report one task: a set plan's entry, or the task itself on a day without one; a Learn task made from the
    Library has its checklist ticked first, as its sections are studied."""
    if item_id in life.lessons and status in ("done", "partial"):
        _tick(life, item_id, status)
    if entry_id:
        life.call("PATCH", f"/api/entries/{entry_id}", json={"status": status})
    else:
        life.call("PATCH", f"/api/daily-items/{item_id}/status", json={"status": status})


# What the person said to Ava: days back, the time, the message, what becomes of her card (None when she makes none, or
# it is left waiting), and how many days before that day the day on show was, as a repeat is stopped from a past day.
_CHAT = (
    (45, "21:00", "Stop repeating Evening journaling", "confirmed", 1),
    (_LATE_SKIP, "08:05", "Catch up yesterday: I skipped {left}", "confirmed", 0),
    (6, "12:30", "Remember that I study best before ten in the morning", "confirmed", 0),
    (6, "20:10", "How did this week go?", None, 0),
    (5, "07:35", "My energy is 2 today", "confirmed", 0),
    (5, "12:40", "Add Call the landlord tomorrow at 16:00", "confirmed", 0),
    (4, "07:40", "Add Buy a birthday card tomorrow at 15:00", "dismissed", 0),
    (3, "21:00", "Remember: keep Sunday mornings free from 8:00 to 11:00", "confirmed", 0),
    (2, "12:15", "I like to cook on Sundays", "dismissed", 0),
    (1, "21:05", "How much did I get done today?", None, 0),
)
# What the person told Ava earlier, kept through cards whose conversation is condensed by now: days back, and the entry.
_MEMORY = (
    (55, {"kind": "note", "area": "learning", "wording": "Verb tables stick better when I say them aloud."}),
    (50, {"kind": "rule", "ruleKind": "keep-off", "area": "work", "days": [5, 6], "wording": "No work at the weekend."}),
    (46, {"kind": "rule", "ruleKind": "finish-by", "latest": "21:00", "days": [4], "wording": "Nothing after nine on Fridays."}),
    (42, {"kind": "note", "area": "project", "wording": "The shed's base must be level within a centimetre."}),
    (40, {"kind": "rule", "ruleKind": "keep-off", "task": "Groceries", "days": [5],
          "wording": "No grocery run on Saturdays while the shop delivers.", "ends": 25}),
    (38, {"kind": "note", "area": "life", "wording": "Runs feel easier before breakfast."}),
    (34, {"kind": "note", "area": "work", "wording": "Sam prefers written updates on Fridays."}),
    (30, {"kind": "rule", "ruleKind": "keep-free", "start": "18:00", "end": "21:00", "days": [3],
          "wording": "Keep Thursday evenings free."}),
    (12, {"kind": "note", "area": "general", "wording": "Away at Jo's wedding.", "ends": -12}),
)


def _tick(life: _Life, item_id: str, status: str) -> None:
    """Tick a Learn task's checklist as its sections are studied: all of them for a task done, half for one partly
    done."""
    checklist = life.call("GET", f"/api/learning-tasks/{item_id}/checklist")["checklist"]
    for entry in checklist[:len(checklist) if status == "done" else len(checklist) // 2]:
        life.call("POST", f"/api/learning-tasks/{item_id}/checklist/{entry['id']}/tick", json={"done": True})


def _week_report(life: _Life, day: date) -> None:
    """Sunday evening: the week's report read in Calendar, and its advice weighed; on the first Sunday whose weekly
    review is partly done, the advice about it is discarded, and the second such Sunday's report raises it again."""
    life.at(day, "21:30")
    read = life.call("POST", "/api/summaries", params={"date": day.isoformat()})
    if day == life.reviews[0]:
        review = next(item for item in read["pool"]["week"]["items"] if item["content"].startswith(f"{_REVIEW} "))
        life.call("POST", f"/api/suggestion-pool/{review['id']}/discard")


def _ahead(life: _Life, end: date) -> None:
    """The days after today, as already planned: the shed's last steps and its felt collected, a meeting on the next
    weekday, the report's last edits, an appointment, the guide's last section and a pass back over two Spanish units."""
    life.at(end, "08:00")
    saturdays = [end + timedelta(days=offset) for offset in range(1, PLANNED_AHEAD_DAYS + 1)
                 if (end + timedelta(days=offset)).weekday() == 5]
    for step, saturday in zip(_SHED[-2:], saturdays):
        life.add(saturday, step, "project", "14:00", 90, "shed")
    # Booked for the next weekday, so Work's coming week holds a meeting whatever day the demo is made on: on a weekend,
    # next week's stand-ups are not yet prepared.
    weekday = next(end + timedelta(days=offset) for offset in range(1, 4) if (end + timedelta(days=offset)).weekday() < 5)
    life.add(weekday, "Quarterly planning", "work", "10:30", 60)
    # The felt ordered yesterday is collected in two days, so Project's coming week holds a step whatever day the demo
    # is made on: on a Saturday the shed's own step is today's, and its next a week on.
    life.add(end + timedelta(days=2), "Shed: collect the roofing felt", "project", None, 30, "shed")
    for offset, title, area, start, minutes, goal in _AHEAD:
        life.add(end + timedelta(days=offset), title, area, start, minutes, goal)
    spanish = [life.sources[path] for path in sorted(life.sources) if path.startswith("Spanish/0")]
    life.call("POST", "/api/learning-tasks", json={
        "sourceIds": spanish[4:6], "date": (end + timedelta(days=2)).isoformat(),
        "goal": {"goalId": life.goals["spanish"]}, "oneADay": True, "fresh": True})


# Tasks already planned for the days ahead: days after today, title, area, start, minutes and goal.
_AHEAD = (
    (3, "Q4 report: final edits", "work", None, 90, "report"),
    (5, "Dentist", "life", "08:30", 45, None),
    (6, "Onboarding guide: FAQ", "work", None, 60, "onboarding"),
    (8, "Website: first post", "project", "20:00", 60, "website"),
    (10, "Pay the council tax", "life", None, 30, None),
    (12, "Mum's birthday dinner", "life", "19:00", 120, None),
)
