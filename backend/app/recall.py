"""Ava's memory of the conversation itself: the full chat of the last CHAT_DAYS days, a day summary of every day before,
and what she reads of both for an answer.

Within the window Ava reads the LATEST_MESSAGES newest messages and up to EARLIER_MESSAGES earlier ones that best match
the question by meaning, with the Library's embedding model (none without it). Each day over is condensed at the next
pass (see keep, run as DayWright opens and while it runs) into a day summary of at most SUMMARY_WORDS words: what was
Asked, Mentioned and left Open, by the local model, and what was Decided or changed, from the cards confirmed that day,
never from the model's words. Greetings are left out before the model reads the day, Ava's replies are read only in
part, and the Library's passages never reach it: a reply names its sources only. The notes and rules found in a day
are read as memory.read_statement reads any statement, kept with its summary, and offered on one card at the end of
the pass.

A day's full text, with its cards and Ava's messages about it, is deleted once it is older than the window and its
summary exists: without the model, a day that needs one keeps its text until the model is back. Summaries stay,
searchable by meaning across all history: for a question about past conversations Ava reads up to SUMMARIES_READ of
them. A newer statement replaces the summary lines it makes out of date: they keep their words and are no longer read.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import date, datetime, timedelta

from .database import Database
from .memory import classify, entry_line, mentions, offer_key, parse_object, read_statement
from .model_gateway import ModelGateway
from .retrieval import EmbeddingUnavailable, RagService
from .wording import count_words, cut_words

# How many days of the conversation Ava keeps in full, today included.
CHAT_DAYS = 7
# What Ava reads of the window: its newest messages, and the earlier ones that best match the question.
LATEST_MESSAGES = 6
EARLIER_MESSAGES = 6
# How much of each message she reads back.
MESSAGE_WORDS = 40
# The most words a day summary holds, its lines together, and the most decided lines it keeps.
SUMMARY_WORDS = 80
DECIDED_LINES = 5
# The most words one line of a summary holds.
LINE_WORDS = 20
# How many summaries Ava reads for a question about past conversations.
SUMMARIES_READ = 5
# The most statements from one day she reads as notes or rules to offer.
OFFERS_PER_DAY = 3
# How near, by meaning, a summary line must lie to a new statement for the model to weigh whether it replaces it.
REPLACE_DISTANCE = 0.9
# The most lines weighed for a replacement at once.
REPLACE_CANDIDATES = 6
# The sections of a summary, in the order it reads.
SECTIONS = ("asked", "mentioned", "open", "decided")
SECTION_WORDS = {"asked": "Asked", "mentioned": "Mentioned", "open": "Open", "decided": "Decided or changed"}

# Words that ask about past conversations, for which Ava reads day summaries.
PAST_TALK = re.compile(
    r"\b(?:did i|have i|what did (?:i|we)|when did (?:i|we)|did we|last time (?:i|we)|we (?:talked|spoke|discussed)|"
    r"i (?:said|told you|mentioned)|you said|our (?:conversation|chat)|remind me what)\b"
    r"|我(?:说过|提过|提到过|跟你说过|告诉过你)|我们(?:聊过|谈过|说过|讨论过)|上次(?:我|我们|你)|你说过", re.IGNORECASE)
# A message that is only a greeting or a thank-you, which no summary keeps.
GREETING = re.compile(r"^\s*(?:hi|hello|hey|thanks|thank you|thx|ok|okay|good (?:morning|afternoon|evening|night)|bye|"
                      r"你好|您好|谢谢|好的|早上好|晚上好|晚安|再见|嗯)[\s!.,。！，~]*$", re.IGNORECASE)

CONDENSE_ROLE = (
    "You condense one day of a user's conversation with Ava, their planning assistant, so that Ava can recall it "
    "later. Write short lines in the conversation's own language: asked (the questions and topics the user raised), "
    "mentioned (facts, plans and concerns the user said), open (what was left unanswered or unresolved). Leave out "
    "greetings, repetition, Ava's explanations and anything quoted from the user's Library. Also give, in the user's "
    "own words, any lasting statement worth remembering beyond that day: a habit, a preference, a priority, or a rule "
    f"for their plans. At most {SUMMARY_WORDS} words in all. Answer with JSON only."
)
CONDENSE_REQUEST = ('Reply exactly in this form: {"asked": ["..."], "mentioned": ["..."], "open": ["..."], '
                    '"remember": ["..."]}')
CONDENSE_MAX_TOKENS = 300
REPLACE_ROLE = (
    "The user has just said something new. From the earlier summary lines listed, give only those it makes out of "
    "date or contradicts, as \"my exam moved to January\" does a line saying the exam is in December. Give none when "
    "none is. Answer with JSON only."
)
REPLACE_REQUEST = 'Reply exactly in this form: {"replaces": [<line id>, ...]}'
REPLACE_MAX_TOKENS = 60
# How much of each of Ava's replies the model reads when it condenses a day.
REPLY_WORDS = 30


def local_day(stamp: str) -> str:
    """The day, on this Mac's clock, of a time kept in UTC."""
    return datetime.fromisoformat(stamp).astimezone().date().isoformat()


def window_start(today: str) -> str:
    """The first day of the conversation Ava keeps in full."""
    return (date.fromisoformat(today) - timedelta(days=CHAT_DAYS - 1)).isoformat()


def recent(messages: list[dict], today: str) -> list[dict]:
    """The messages of the window, as Ava's panel shows them."""
    first = window_start(today)
    return [message for message in messages if local_day(message["created_at"]) >= first]


def _days(connection: sqlite3.Connection) -> dict[str, dict]:
    """Each day with conversation, by its local date: its messages, the cards confirmed on it and Ava's messages."""
    days: dict[str, dict] = {}

    def day(stamp: str) -> dict:
        """The local day a timestamp falls on, with its messages, decided cards and notices gathered so far."""
        return days.setdefault(local_day(stamp), {"messages": [], "decided": [], "notices": []})

    for row in connection.execute("""SELECT rowid AS row_id, id, role, content, created_at FROM conversation_messages
                                     ORDER BY created_at, rowid"""):
        day(row["created_at"])["messages"].append(dict(row))
    for row in connection.execute(
            """SELECT a.id, a.action_type, a.payload_json, a.explanation, c.decided_at FROM action_confirmations c
               JOIN proposed_actions a ON a.id = c.action_id WHERE c.decision = 'confirmed' ORDER BY c.decided_at"""):
        day(row["decided_at"])["decided"].append(dict(row))
    for row in connection.execute("SELECT id, created_at FROM ava_notices"):
        day(row["created_at"])["notices"].append(row["id"])
    return days


def decided_line(card: dict) -> str:
    """What a confirmed card did, from the card itself: the entry it kept in memory, or its first sentence."""
    payload = json.loads(card["payload_json"])
    if card["action_type"] == "remember":
        return f"Remembered: {entry_line(payload['entry'])}"
    first = re.split(r"(?<=[.!?])\s", card["explanation"].strip(), maxsplit=1)[0]
    return "Confirmed: " + cut_words(re.sub(r"^(?:Propose|Review)\s+", "", first).rstrip("."), LINE_WORDS)


def _fitted(sections: dict[str, list[str]]) -> list[tuple[str, str]]:
    """A summary's lines held to SUMMARY_WORDS: each line cut to LINE_WORDS, the decided ones first, as records, then
    asked, mentioned and open, each in turn, while the words last."""
    lines = [("decided", text) for text in sections.get("decided", [])[:DECIDED_LINES]]
    left = SUMMARY_WORDS - sum(count_words(text) for _, text in lines)
    for section in ("asked", "mentioned", "open"):
        for text in sections.get(section, []):
            text = cut_words(" ".join(str(text).split()), LINE_WORDS)
            if text and count_words(text) <= left:
                lines.append((section, text))
                left -= count_words(text)
    return lines


def condense(gateway: ModelGateway, day: str, messages: list[dict]) -> dict | None:
    """Have the local model condense a day's conversation: the user's words in full, greetings left out, and the
    start of Ava's replies.

    Returns:
        Its "asked", "mentioned" and "open" lines and the statements to "remember", each a list of strings; None when
        the model isn't available or its answer can't be read.
    """
    told = "\n".join(f"You: {message['content']}" if message["role"] == "user"
                     else f"Ava: {cut_words(message['content'].splitlines()[0] if message['content'] else '', REPLY_WORDS)}"
                     for message in messages if not (message["role"] == "user" and GREETING.match(message["content"])))
    answer, mode = gateway.reply(f"The conversation on {day}:\n{told}\n{CONDENSE_REQUEST}", "",
                                 system_prompt=CONDENSE_ROLE, max_tokens=CONDENSE_MAX_TOKENS)
    data = None if mode == "rules" else parse_object(answer)
    if data is None:
        return None
    return {name: [str(text) for text in data.get(name) or [] if isinstance(text, str) and text.strip()]
            for name in ("asked", "mentioned", "open", "remember")}


def _offers(store: Database, gateway: ModelGateway, day: str, statements: list[str]) -> list[dict]:
    """The notes and rules a day's statements read as (see memory.read_statement), said that day; those already kept
    and those the user dismissed before are left out."""
    offers = []
    for statement in statements[:OFFERS_PER_DAY]:
        entries = store.memory_entries()
        read = read_statement(statement, classify(gateway, statement, entries, day), day, entries)
        if read["outcome"] != "duplicate" and not store.offer_dismissed(offer_key(read["entry"])):
            offers.append({**read, "day": day})
    return offers


def keep(store: Database, gateway: ModelGateway, rag: RagService | None, today: str) -> dict:
    """Ava's pass over the conversation, as DayWright opens and while it runs: condense each day over without a
    summary, oldest first; offer the notes and rules found on one card; then clear each day older than the window
    whose summary exists, and index what the window and the summaries hold for search by meaning.

    A day the user said nothing on but confirmed cards gets its summary without the model; one they spoke on waits,
    with all after it, until the model is available and answers.

    Returns:
        The days condensed ("condensed"), the card offered, or None ("offer"), and the days cleared ("cleared").
    """
    with store.connect() as connection:
        days = _days(connection)
        done = {row["day"] for row in connection.execute("SELECT day FROM day_summaries")}
    condensed = []
    for day in sorted(day for day in days if day < today and day not in done):
        held = days[day]
        said = [message for message in held["messages"] if message["role"] == "user" and not GREETING.match(message["content"])]
        sections: dict = {"decided": [decided_line(card) for card in held["decided"]]}
        offers: list[dict] = []
        if said:
            if gateway.status()["state"] == "unavailable":
                break
            read = condense(gateway, day, held["messages"])
            if read is None:
                break
            sections |= read
            offers = _offers(store, gateway, day, read["remember"])
        _save(store, day, _fitted(sections), offers)
        condensed.append(day)
    offer = _offer(store, today)
    cleared = clear(store, rag, today)
    if rag is not None:
        index(store, rag, today)
    return {"condensed": condensed, "offer": offer, "cleared": cleared}


def _save(store: Database, day: str, lines: list[tuple[str, str]], offers: list[dict]) -> None:
    """Keep a day's summary: its lines by section, and the entries Ava may offer to remember, marked offered when
    there are none."""
    with store.connect() as connection:
        connection.execute("INSERT INTO day_summaries (day, made_at, offers_json, offered) VALUES (?, ?, ?, ?)",
                           (day, datetime.now().astimezone().isoformat(), json.dumps(offers, ensure_ascii=False),
                            0 if offers else 1))
        connection.executemany("INSERT INTO summary_lines (day, section, text) VALUES (?, ?, ?)",
                               [(day, section, text) for section, text in lines])


def _offer(store: Database, today: str) -> dict | None:
    """Offer every note and rule found in days condensed and not yet offered, on one card through Ava, posted as her
    message; each is kept on Confirm if left ticked, and one unticked is never offered again."""
    with store.connect() as connection:
        rows = connection.execute("SELECT day, offers_json FROM day_summaries WHERE offered = 0 ORDER BY day").fetchall()
        connection.execute("UPDATE day_summaries SET offered = 1 WHERE offered = 0")
    offers = [offer for row in rows for offer in json.loads(row["offers_json"])]
    if not offers:
        return None
    listed = "; ".join(entry_line(offer["entry"]) for offer in offers)
    explanation = (f"From our conversations, {len(offers)} thing{'s' if len(offers) != 1 else ''} to remember: {listed}. "
                   "Keep the ones you want; nothing is kept until you confirm.")
    proposal = store.propose_action(store.thread(), "review_memory", {
        "entries": [{key: offer.get(key) for key in ("entry", "outcome", "updates", "before", "day", "rule", "missing")}
                    for offer in offers],
        "days": sorted({offer["day"] for offer in offers}), "proposedBy": "orchestrator"}, explanation)
    store.post_notices(today, [{"issueKey": f"memory-review:{proposal['id']}", "agent": "orchestrator",
                                "kind": "memory-review", "values": {"count": len(offers), "actionId": proposal["id"]}}])
    return proposal


def clear(store: Database, rag: RagService | None, today: str) -> list[str]:
    """Delete the full text of each day older than the window whose summary exists: its messages, with what Ava drew
    on for them, the cards made that day and Ava's messages posted that day. A request to shorten a task outlives
    them, as the plans still act on it.

    Returns:
        The days cleared.
    """
    first = window_start(today)
    with store.connect() as connection:
        gone = sorted(row["day"] for row in connection.execute("SELECT day FROM day_summaries") if row["day"] < first)
        if not gone:
            return []
        messages = [(row["row_id"], row["id"]) for row in connection.execute(
            "SELECT rowid AS row_id, id, created_at FROM conversation_messages") if local_day(row["created_at"]) in gone]
        actions = [row["id"] for row in connection.execute("SELECT id, created_at FROM proposed_actions")
                   if local_day(row["created_at"]) in gone]
        notices = [row["id"] for row in connection.execute("SELECT id, created_at FROM ava_notices")
                   if local_day(row["created_at"]) in gone]
        ids = [message_id for _, message_id in messages]
        if ids:
            connection.execute(f"""UPDATE preferences SET provenance_message_id = NULL
                                   WHERE provenance_message_id IN ({','.join('?' * len(ids))})""", ids)
        for table, values in (("conversation_messages", ids), ("proposed_actions", actions), ("ava_notices", notices)):
            if values:
                connection.execute(f"DELETE FROM {table} WHERE id IN ({','.join('?' * len(values))})", values)
    if rag is not None and messages:
        rag.vector_store.drop_vectors("message_vectors", [row_id for row_id, _ in messages])
    return gone


def index(store: Database, rag: RagService, today: str) -> None:
    """Index for search by meaning the window's messages and the summary lines without vectors, and drop the vectors
    of rows gone; with the embedding model not running, what is missing waits for the next pass."""
    first = window_start(today)
    with store.connect() as connection:
        messages = {row["row_id"]: row["content"] for row in connection.execute(
            "SELECT rowid AS row_id, content, created_at FROM conversation_messages") if local_day(row["created_at"]) >= first}
        lines = {row["id"]: row["text"] for row in connection.execute("SELECT id, text FROM summary_lines")}
    for table, rows in (("message_vectors", messages), ("summary_vectors", lines)):
        have = rag.vector_store.vector_ids(table)
        rag.vector_store.drop_vectors(table, have - set(rows))
        try:
            rag.index_memory(table, [(row_id, text) for row_id, text in rows.items() if row_id not in have])
        except EmbeddingUnavailable:
            return


def chat_context(store: Database, rag: RagService, question: str, today: str, before: str) -> list[dict]:
    """What Ava reads of the window for a question: the LATEST_MESSAGES newest messages before it, and up to
    EARLIER_MESSAGES earlier ones in the window that best match it by meaning; in the order said, each with its day.
    Without the embedding model, the newest alone.

    Args:
        before: The question's own message id; it, and everything after it, is left out.
    """
    window = recent(store.messages(store.thread()), today)
    cut = next((place for place, message in enumerate(window) if message["id"] == before), len(window))
    window = window[:cut]
    latest, earlier = window[-LATEST_MESSAGES:], window[:-LATEST_MESSAGES]
    chosen: list[dict] = []
    if earlier:
        index(store, rag, today)
        with store.connect() as connection:
            rows = {row["id"]: row["row_id"] for row in connection.execute(
                f"SELECT rowid AS row_id, id FROM conversation_messages WHERE id IN ({','.join('?' * len(earlier))})",
                [message["id"] for message in earlier])}
        order = {row_id: rank for rank, (row_id, _) in enumerate(rag.nearest_memory("message_vectors", question,
                                                                                    len(window)) or [])}
        best = sorted((message for message in earlier if rows.get(message["id"]) in order),
                      key=lambda message: order[rows[message["id"]]])[:EARLIER_MESSAGES]
        chosen = [message for message in earlier if message in best]
    return [{"day": local_day(message["created_at"]), "role": message["role"],
             "content": cut_words(" ".join(message["content"].split()), MESSAGE_WORDS)} for message in (*chosen, *latest)]


def summaries(store: Database, day_list: list[str] | None = None) -> dict[str, dict[str, list[dict]]]:
    """Day summaries by day, each its lines by section, those replaced left out; every day's, or those listed."""
    with store.connect() as connection:
        rows = connection.execute(
            "SELECT id, day, section, text FROM summary_lines WHERE replaced_on IS NULL ORDER BY day, id").fetchall()
    found: dict[str, dict[str, list[dict]]] = {}
    for row in rows:
        if day_list is None or row["day"] in day_list:
            found.setdefault(row["day"], {}).setdefault(row["section"], []).append(dict(row))
    return found


def summary_context(store: Database, rag: RagService, question: str) -> list[dict]:
    """The day summaries Ava reads for a question about past conversations: the SUMMARIES_READ whose lines best match
    it by meaning, the nearest first; none without the embedding model.

    Returns:
        Each day's "day" and its "lines" by section.
    """
    near = rag.nearest_memory("summary_vectors", question, SUMMARIES_READ * 6)
    if not near:
        return []
    with store.connect() as connection:
        days = {row["id"]: row["day"] for row in connection.execute(
            f"SELECT id, day FROM summary_lines WHERE replaced_on IS NULL AND id IN ({','.join('?' * len(near))})",
            [row_id for row_id, _ in near])}
    ranked = list(dict.fromkeys(days[row_id] for row_id, _ in near if row_id in days))[:SUMMARIES_READ]
    held = summaries(store, ranked)
    return [{"day": day, "lines": held[day]} for day in ranked if day in held]


def replace_lines(store: Database, gateway: ModelGateway, rag: RagService, statement: str, today: str) -> list[dict]:
    """Have a newer statement replace the summary lines it makes out of date: of those near it by meaning, mentioned
    or left open, the model chooses; each keeps its words and is no longer read.

    Returns:
        The lines replaced, each its "id", "day" and "text"; none without the models.
    """
    near = rag.nearest_memory("summary_vectors", statement, REPLACE_CANDIDATES)
    candidates = [row_id for row_id, distance in near or [] if distance <= REPLACE_DISTANCE]
    if not candidates:
        return []
    with store.connect() as connection:
        lines = [dict(row) for row in connection.execute(
            f"""SELECT id, day, section, text FROM summary_lines WHERE replaced_on IS NULL AND section IN ('mentioned', 'open')
                AND id IN ({','.join('?' * len(candidates))}) ORDER BY day, id""", candidates)]
    if not lines:
        return []
    listed = "\n".join(f"[{line['id']}] {line['day']}: {line['text']}" for line in lines)
    answer, mode = gateway.reply(f"New: {statement}\nEarlier lines:\n{listed}\n{REPLACE_REQUEST}", "",
                                 system_prompt=REPLACE_ROLE, max_tokens=REPLACE_MAX_TOKENS)
    data = None if mode == "rules" else parse_object(answer)
    named = {value for value in (data or {}).get("replaces") or [] if isinstance(value, int)}
    replaced = [line for line in lines if line["id"] in named]
    if replaced:
        with store.connect() as connection:
            connection.executemany("UPDATE summary_lines SET replaced_on = ?, replaced_by = ? WHERE id = ?",
                                   [(today, statement, line["id"]) for line in replaced])
    return replaced


def forget_lines(store: Database, topic: str) -> list[dict]:
    """Every summary line that names a topic, replaced or not, as a request to forget it lists them."""
    with store.connect() as connection:
        rows = connection.execute("SELECT id, day, section, text FROM summary_lines ORDER BY day, id").fetchall()
    return [dict(row) for row in rows if mentions(row["text"], topic)]


def delete_lines(store: Database, line_ids: list[int]) -> None:
    """Delete summary lines for good; their vectors go at the next pass."""
    if line_ids:
        with store.connect() as connection:
            connection.execute(f"DELETE FROM summary_lines WHERE id IN ({','.join('?' * len(line_ids))})", line_ids)
