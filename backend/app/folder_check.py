"""The study check of a connected folder's files.

Each file the Library keeps from a folder is read to see that it can be studied from, and the local model, when
it can run, judges from its title, headings and opening whether it is study material at all. A file is checked
once for its content: a refresh checks only what is new or changed. What a check finds reaches the user through
Ava, as one card from the Learning agent: files ready to study start ticked, the rest unticked, and Confirm
removes the unticked ones from the Library (see Database.decide_action). Nothing in the folder is ever written.
"""

from __future__ import annotations

import re
import threading
from datetime import date
from pathlib import Path

from .database import Database
from .model_gateway import ModelGateway
from .source_store import SourceStore
from .sources import SourceError, file_hash, inside, read_file

# The notice the Learning agent posts, through Ava, with what a folder's check found.
FOLDER_CHECK = "folder-check"
# How much of a file's text, from its start, the local model reads to judge it.
EXCERPT_WORDS = 120
# The most headings the local model reads of a file.
MOST_HEADINGS = 16
# Why a file whose text is empty can't be studied from, as a scanned PDF's pages hold no text.
NO_TEXT = "No text to read: it may be scanned pages."
_ANSWER = re.compile(r"\b(yes|no)\b", re.IGNORECASE)
_JUDGE = ("You sort the files of a folder the user keeps for studying. Answer yes when a file is material to learn "
          "from, such as notes, lessons, chapters, papers or articles, and no when it is something else, such as an "
          "invoice, a form, a receipt or a contract. Answer with one word: yes or no.")

# The files a check is going through, by folder id: how many it has done, of how many (None until it has counted
# them), from when a check is asked for until every check asked for that folder has ended.
progress: dict[str, dict] = {}
# How many checks are asked for and not ended yet, by folder id.
_asked: dict[str, int] = {}
# Keeps `progress` and `_asked` in step between the service and its checks.
_marks = threading.Lock()
# One check at a time, so a refresh during a check waits its turn and no file is recorded or reported twice.
_one_at_a_time = threading.Lock()


def ask(folder_id: str) -> None:
    """Mark a folder as being checked from now, as its check is asked for and before it starts; see check_folder."""
    with _marks:
        _asked[folder_id] = _asked.get(folder_id, 0) + 1
        progress.setdefault(folder_id, {"done": 0, "total": None})


def readable(path: Path) -> tuple[str | None, str]:
    """Read a file to see whether it can be studied from.

    Returns:
        Why it can't, or None, and its text when it can.
    """
    try:
        text = read_file(path)
    except SourceError as error:
        return str(error), ""
    return (None, text) if text.strip() else (NO_TEXT, "")


def study_material(gateway: ModelGateway, title: str, headings: list[str], text: str) -> str:
    """Whether the local model takes a file for study material.

    Returns:
        "yes", "no", or "unchecked" when the model can't run; an answer that is neither counts as yes.
    """
    opening = " ".join(text.split()[:EXCERPT_WORDS])
    answer, mode = gateway.reply(
        f"Title: {title}\nHeadings: {'; '.join(headings[:MOST_HEADINGS]) or 'none'}\nOpening: {opening}\n\n"
        "Is this study material?", "", system_prompt=_JUDGE)
    if mode == "rules":
        return "unchecked"
    found = _ANSWER.search(answer)
    return "no" if found and found[1].lower() == "no" else "yes"


def check_folder(store: Database, shelf: SourceStore, gateway: ModelGateway, folder_id: str) -> dict | None:
    """Check a connected folder's files the Library keeps and hasn't checked at their content yet, showing its
    progress in `progress`, then have Ava report every file checked and not reported yet (see report). Checks run
    one at a time: one asked for while another runs waits its turn.

    Returns:
        Ava's card, or None for a folder not found or nothing new to report.
    """
    with _one_at_a_time:
        try:
            folder = shelf.folder(folder_id)
            if not folder["found"]:
                return None
            root = Path(folder["path"])
            checked = store.folder_checks(folder_id)
            pending = []
            for source in folder["sources"]:
                path = inside(root, source["relativePath"])
                if source["missing"] or not path.is_file():
                    continue
                content = file_hash(path)
                if checked.get(source["relativePath"]) != content:
                    pending.append((source, path, content))
            counted = {"done": 0, "total": len(pending)}
            progress[folder_id] = counted
            for source, path, content in pending:
                reason, text = readable(path)
                headings = [heading for group in source["outline"] for heading in (group["title"], *(topic["title"] for topic in group["topics"]))]
                study = "unchecked" if reason else study_material(gateway, source["title"], headings, text)
                store.record_check(folder_id, source["relativePath"], content, reason, study)
                counted["done"] += 1
            return report(store, shelf.folder(folder_id))
        finally:
            # The folder stays marked while another check of it is still asked for.
            with _marks:
                left = _asked.pop(folder_id, 1) - 1
                if left > 0:
                    _asked[folder_id] = left
                    progress[folder_id] = {"done": 0, "total": None}
                else:
                    progress.pop(folder_id, None)


def report(store: Database, folder: dict) -> dict | None:
    """Have the Learning agent report, through Ava, the files of a folder checked and not reported yet: one card
    saying how many are ready to study, can't be read (with why) or don't look like study material (by name),
    each ready one ticked and the rest unticked, and whether the study check could run. Each file is reported once.

    Returns:
        The card, or None when there is nothing to report.
    """
    sources = {source["relativePath"]: source for source in folder["sources"]}
    rows = store.unreported_checks(folder["id"])
    store.mark_reported(folder["id"], [row["path"] for row in rows])
    files = []
    for row in rows:
        source = sources.get(row["path"])
        if source:
            verdict = "unreadable" if row["reason"] else "not-study" if row["study"] == "no" else "ready"
            files.append({"path": row["path"], "title": source["title"], "sourceId": source["id"], "verdict": verdict,
                          "reason": row["reason"], "ticked": verdict == "ready"})
    if not files:
        return None
    counts = {verdict: sum(file["verdict"] == verdict for file in files) for verdict in ("ready", "unreadable", "not-study")}
    checked = not any(row["study"] == "unchecked" and not row["reason"] for row in rows)
    answer = (f"I checked {len(files)} file{'s' if len(files) != 1 else ''} in “{folder['title']}”. Ready to study: "
              f"{counts['ready']} · Can't read: {counts['unreadable']} · Doesn't look like study material: "
              f"{counts['not-study']}."
              + ("" if checked else " The study check couldn't run, as the local model isn't available, so only "
                                    "whether each file can be read was checked.")
              + (" Files that can't be read or don't look like study material are unticked; tick any you want to keep, "
                 "then confirm." if counts["unreadable"] or counts["not-study"] else " Confirm to keep them all."))
    proposal = store.propose_action(store.thread(), "folder_check", {
        "folderId": folder["id"], "title": folder["title"], "files": files, "modelChecked": checked,
        "proposedBy": "learning"}, answer)
    store.post_notices(date.today().isoformat(), [{
        "issueKey": f"{FOLDER_CHECK}:{proposal['id']}", "agent": "learning", "kind": FOLDER_CHECK,
        "values": {"folderId": folder["id"], "title": folder["title"], "ready": counts["ready"],
                   "unreadable": counts["unreadable"], "notStudy": counts["not-study"], "actionId": proposal["id"]}}])
    return proposal
