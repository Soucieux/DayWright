"""Local-first topic acquisition with a separately checkpointed KnowledgeState flow."""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from typing import TypedDict
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from .database import Database
from .retrieval import RagService


class PublicSourceUnavailable(RuntimeError):
    """The optional public lookup could not return a usable topic extract."""


class KnowledgeState(TypedDict, total=False):
    task_id: str
    topic: str
    explicit_web: bool
    local_result: dict
    public_source: dict
    stored_source: dict
    filtering: dict
    import_choices: list[dict]
    pending_import: dict
    result: dict
    public_fetch: str


class WikipediaFetcher:
    """Fetch a short, attributed public encyclopedia extract for an entered topic only."""

    endpoint = "https://en.wikipedia.org/w/api.php"
    user_agent = "DayWrightLocalBot/0.1 (https://github.com/Soucieux)"

    def _request(self, parameters: dict) -> dict:
        url = f"{self.endpoint}?{urlencode(parameters)}"
        request = Request(url, headers={"User-Agent": self.user_agent,
                                        "Accept": "application/json"})
        try:
            with urlopen(request, timeout=8) as response:
                return json.loads(response.read(256_000).decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError) as error:
            raise PublicSourceUnavailable("Public encyclopedia lookup is unavailable") from error

    def fetch(self, topic: str) -> dict:
        """Search Wikipedia and read at most ten introductory sentences, without private context."""
        found = self._request({"action": "query", "format": "json", "list": "search",
                               "srsearch": topic, "srlimit": 1, "srnamespace": 0})
        pages = found.get("query", {}).get("search", [])
        if not pages:
            raise PublicSourceUnavailable("No public encyclopedia page matched this topic")
        title = pages[0]["title"]
        extracted = self._request({"action": "query", "format": "json", "formatversion": 2,
                                   "prop": "extracts", "titles": title, "explaintext": 1,
                                   "exintro": 1, "exsentences": 10})
        page = extracted.get("query", {}).get("pages", [{}])[0]
        text = page.get("extract", "").strip()
        if not text:
            raise PublicSourceUnavailable("The public page has no usable introductory text")
        return {"title": f"Wikipedia · {title}", "text": text[:6000],
                "sourceUrl": f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}",
                "sourceLicense": "Wikipedia contributors · CC BY-SA 4.0",
                "sourceUpdatedAt": pages[0].get("timestamp")}


def _safe_public_topic(topic: str) -> bool:
    """Avoid sending obvious personal context or identifiers as an automatic topic query."""
    return not (re.search(r"\b(my|mine|our|me|i|i'm|i've)\b", topic, re.I)
                or re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", topic, re.I)
                or re.search(r"(?:\d[\s().-]?){7,}", topic))


def acquire_topic(rag: RagService, store: Database, topic: str, explicit_web: bool,
                  fetcher: WikipediaFetcher) -> dict:
    """Retrieve locally first; stage bounded public material for user-chosen import."""

    def search_local(state: KnowledgeState) -> dict:
        return {"local_result": rag.retrieve(state["topic"]).public()}

    def next_step(state: KnowledgeState) -> str:
        if state["explicit_web"] or state["local_result"]["status"] in ("empty", "no_match"):
            return "public" if _safe_public_topic(state["topic"]) else "private_topic"
        return "finish"

    def fetch_public(state: KnowledgeState) -> dict:
        return {"public_source": fetcher.fetch(state["topic"]), "public_fetch": "fetched"}

    def filter_public(state: KnowledgeState) -> dict:
        source = state["public_source"]
        return {"filtering": {"priority": ["credibility", "timeliness", "other"],
                              "credibility": "Attributed encyclopedia page; not independently verified",
                              "timeliness": source.get("sourceUpdatedAt") or "Last edit unavailable",
                              "other": "Short plain-text introduction; one public source only"}}

    def classify_public(state: KnowledgeState) -> dict:
        return {"import_choices": [
            {"name": "By level", "labels": ["Basic", "Advanced", "Practical"]},
            {"name": "By method", "labels": ["Theory", "Case Study", "Exercise"]},
            {"name": "By progression", "labels": ["Introduction", "Core", "Extension"]},
        ]}

    def propose_import(state: KnowledgeState) -> dict:
        staged = store.stage_knowledge_acquisition(
            state["topic"], state["public_source"], state["filtering"],
            state["import_choices"])
        return {"pending_import": staged, "result": state["local_result"],
                "public_fetch": "awaiting_import_choice"}

    def finish(state: KnowledgeState) -> dict:
        return {"result": state["local_result"], "public_fetch": "not_requested"}

    def private_topic(state: KnowledgeState) -> dict:
        return {"result": state["local_result"], "public_fetch": "needs_general_topic"}

    builder = StateGraph(KnowledgeState)
    builder.add_node("search_local", search_local)
    builder.add_node("fetch_public", fetch_public)
    builder.add_node("filter_public", filter_public)
    builder.add_node("classify_public", classify_public)
    builder.add_node("propose_import", propose_import)
    builder.add_node("finish", finish)
    builder.add_node("private_topic", private_topic)
    builder.add_edge(START, "search_local")
    builder.add_conditional_edges("search_local", next_step,
                                  {"public": "fetch_public", "finish": "finish",
                                   "private_topic": "private_topic"})
    builder.add_edge("fetch_public", "filter_public")
    builder.add_edge("filter_public", "classify_public")
    builder.add_edge("classify_public", "propose_import")
    builder.add_edge("propose_import", END)
    builder.add_edge("finish", END)
    builder.add_edge("private_topic", END)
    task_id = f"knowledge-topic:{uuid.uuid4().hex}"
    # Keep checkpoint writes outside the vector index: sqlite3 and APSW bundle
    # different SQLite runtimes, and concurrent writes to one file can corrupt vec0.
    checkpoint_path = store.path.with_name(f"{store.path.stem}.checkpoints.sqlite3")
    connection = sqlite3.connect(checkpoint_path, timeout=15, check_same_thread=False)
    try:
        graph = builder.compile(checkpointer=SqliteSaver(
            connection, serde=JsonPlusSerializer(allowed_msgpack_modules=())))
        state = graph.invoke({"task_id": task_id, "topic": topic,
                              "explicit_web": explicit_web},
                             {"configurable": {"thread_id": task_id}})
    finally:
        connection.close()
    return {"taskId": task_id, "retrieval": state["result"],
            "source": state.get("stored_source"), "publicFetch": state["public_fetch"],
            "importOptions": state.get("pending_import")}
