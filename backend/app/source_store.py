"""The Library's connected sources: folders the user picks, anywhere on this Mac, and websites.

A folder is read and never written. Each file the user leaves ticked is a Library source with origin
"folder", kept with its content hash, its briefing and its outline; Refresh picks up new, changed and
removed files. Nothing is removed on its own: a folder no longer at its path keeps all its sources and
waits for its new place, and a file gone from a folder that is still there is marked missing until the
user locates it or removes it. A website is saved by its address, and looked into at most once.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from .database import Database
from .retrieval import EmbeddingUnavailable, RagService, VectorStore
from .sources import (SourceError, SourceNotFound, cut_words, fetch_page, file_briefing, file_hash, file_outline,
                      inside, lesson_address, read_file, scan_folder)

# The preference under which Open with's app for each file type is kept.
OPEN_WITH_KEY = "openWith"
# The file types Open with chooses an app for, and the longest app name it keeps.
OPEN_WITH_TYPES = ("md", "pdf", "docx")
OPEN_WITH_NAME_LENGTH = 80

# Who a confirmed briefing is by: Ava, when her suggestion was kept as it was, or the user.
BRIEFED_BY = ("ava", "you")
# The longest heading a confirmed outline keeps.
OUTLINE_HEADING_CHARACTERS = 80

_SOURCE_COLUMNS = """id, title, origin, domain, goal_id, briefing, briefing_by, outline_json, outline_by, missing,
                     relative_path, folder_id, source_url, looked_up_at, content_hash, created_at"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _web_address(address: str) -> str:
    """A web address as given, refusing anything that isn't http or https.

    Raises:
        SourceError: For an address that isn't a web address.
    """
    parts = urlsplit(address.strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise SourceError("Give a web address that starts with http:// or https://.")
    return address.strip()


def _source(row) -> dict:
    """A source as the Library and the routes show it."""
    return {"id": row["id"], "title": row["title"], "origin": row["origin"], "domain": row["domain"],
            "goalId": row["goal_id"], "briefing": row["briefing"], "briefingBy": row["briefing_by"],
            "outline": json.loads(row["outline_json"] or "[]"), "outlineBy": row["outline_by"], "missing": bool(row["missing"]),
            "relativePath": row["relative_path"], "folderId": row["folder_id"], "address": row["source_url"] or None,
            "lookedUp": bool(row["looked_up_at"]), "createdAt": row["created_at"]}


class SourceStore:
    """Connected folders and saved websites, kept in the Library beside its notes and imported files."""

    def __init__(self, store: Database) -> None:
        self.store = store

    def preview(self, path: str) -> dict:
        """A folder's tree of readable files with their tick boxes, before anything is kept.

        Raises:
            SourceError: When the path isn't a folder.
        """
        root = Path(path).expanduser()
        if not root.is_dir():
            raise SourceError("That isn't a folder.")
        root = root.resolve()
        return {"path": str(root), "title": root.name, "files": scan_folder(root)}

    def _read(self, root: Path, relative: str) -> dict:
        """What a folder's file gives the Library: its title (its first # heading, or its name), briefing,
        outline and content hash; a file that can't be read gives its name and no briefing or outline."""
        path = inside(root, relative)
        try:
            outline, briefing = file_outline(path), file_briefing(path)
        except SourceError:
            outline, briefing = [], None
        return {"title": outline[0]["title"] if outline else PurePosixPath(relative).stem, "briefing": briefing,
                "outline": outline, "hash": file_hash(path)}

    def _add_file(self, connection, folder: dict, root: Path, relative: str) -> str:
        """Keep a folder's file as a Library source; return its id."""
        read = self._read(root, relative)
        source_id = f"source_{uuid.uuid4().hex[:16]}"
        connection.execute(
            """INSERT INTO knowledge_sources (id, title, origin, domain, goal_id, briefing, briefing_by, outline_json,
                                              outline_by, missing, relative_path, folder_id, content_hash, created_at,
                                              source_type)
               VALUES (?, ?, 'folder', ?, NULL, ?, ?, ?, ?, 0, ?, ?, ?, ?, 'document')""",
            (source_id, read["title"], folder["domain"], read["briefing"], "source" if read["briefing"] else "",
             json.dumps(read["outline"], ensure_ascii=False), "source" if read["outline"] else "", relative, folder["id"],
             read["hash"], _now()))
        return source_id

    def _update_file(self, connection, source_id: str, root: Path, relative: str) -> None:
        """Read a folder's file again into its source, and its place in the folder. A briefing the user
        wrote stays; a briefing or an outline confirmed for a file without its own stays until it has one."""
        read = self._read(root, relative)
        kept = connection.execute("SELECT briefing, briefing_by, outline_json, outline_by FROM knowledge_sources WHERE id = ?",
                                  (source_id,)).fetchone()
        if kept["briefing_by"] == "you" or (kept["briefing_by"] in BRIEFED_BY and not read["briefing"]):
            briefing, briefing_by = kept["briefing"], kept["briefing_by"]
        else:
            briefing, briefing_by = read["briefing"], "source" if read["briefing"] else ""
        if kept["outline_by"] in BRIEFED_BY and not read["outline"]:
            outline, outline_by = json.loads(kept["outline_json"]), kept["outline_by"]
        else:
            outline, outline_by = read["outline"], "source" if read["outline"] else ""
        connection.execute(
            """UPDATE knowledge_sources SET title = ?, briefing = ?, briefing_by = ?, outline_json = ?, outline_by = ?,
                      content_hash = ?, relative_path = ?, missing = 0 WHERE id = ?""",
            (read["title"], briefing, briefing_by, json.dumps(outline, ensure_ascii=False), outline_by, read["hash"],
             relative, source_id))

    def connect(self, path: str, unticked: list[str], website: str = "", domain: str = "learning") -> dict:
        """Connect a folder: keep each of its files the tree ticks and the user left ticked.

        Args:
            path: The folder, anywhere on this Mac.
            unticked: Files of the tree's the user unticked, by their paths in the folder.
            website: An address the folder's files also open on, or "" for none.
            domain: The area its sources join.

        Raises:
            SourceError: When the path isn't a folder, or the website isn't a web address.
        """
        preview = self.preview(path)
        folder = {"id": f"folder_{uuid.uuid4().hex[:12]}", "domain": domain}
        site = _web_address(website) if website.strip() else ""
        root = Path(preview["path"])
        with self.store.connect() as connection:
            connection.execute(
                """INSERT INTO source_folders (id, title, path, website, domain, unticked_json, found, created_at, refreshed_at)
                   VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)""",
                (folder["id"], preview["title"], preview["path"], site, domain, json.dumps(sorted(set(unticked))), _now(), _now()))
            for item in preview["files"]:
                if item["ticked"] and item["path"] not in unticked:
                    self._add_file(connection, folder, root, item["path"])
        return self.folder(folder["id"])

    def folder(self, folder_id: str) -> dict:
        """A connected folder with its sources, in path order.

        Raises:
            SourceError: When there is no such folder.
        """
        folders = [folder for folder in self.folders() if folder["id"] == folder_id]
        if not folders:
            raise SourceNotFound("That folder isn't in the Library.")
        return folders[0]

    def folders(self) -> list[dict]:
        """Every connected folder, in the order they were connected, each with its sources and whether it
        was found at its path when last refreshed."""
        with self.store.connect() as connection:
            folders = connection.execute("SELECT * FROM source_folders ORDER BY created_at, rowid").fetchall()
            files = connection.execute(
                f"SELECT {_SOURCE_COLUMNS} FROM knowledge_sources WHERE origin = 'folder' ORDER BY relative_path").fetchall()
        return [{"id": row["id"], "title": row["title"], "path": row["path"], "website": row["website"] or None,
                 "domain": row["domain"], "found": bool(row["found"]), "unticked": json.loads(row["unticked_json"]),
                 "refreshedAt": row["refreshed_at"],
                 "sources": [_source(file) for file in files if file["folder_id"] == row["id"]]} for row in folders]

    def refresh(self, folder_id: str) -> dict:
        """Read a folder again: add its new ticked files, read its changed ones again, follow a file renamed
        with the same content, and mark a file gone from it missing. A folder not at its path is marked
        not found, and nothing in it changes until its new place is given (see relocate).

        Returns:
            {"found", "added", "changed", "moved", "missing"}, each list by paths in the folder.
        """
        folder = self.folder(folder_id)
        root = Path(folder["path"])
        result = {"found": root.is_dir(), "added": [], "changed": [], "moved": [], "missing": []}
        with self.store.connect() as connection:
            connection.execute("UPDATE source_folders SET found = ?, refreshed_at = ? WHERE id = ?",
                               (int(result["found"]), _now(), folder_id))
            if not result["found"]:
                return result
            items = {item["path"]: item for item in scan_folder(root)}
            known = {source["relativePath"]: source for source in folder["sources"]}
            hashes = {row["id"]: row["content_hash"] for row in connection.execute(
                "SELECT id, content_hash FROM knowledge_sources WHERE folder_id = ?", (folder_id,))}
            gone = {}
            for relative, source in known.items():
                if relative in items and items[relative]["reason"] != "too large":
                    if file_hash(inside(root, relative)) != hashes[source["id"]]:
                        self._update_file(connection, source["id"], root, relative)
                        result["changed"].append(relative)
                    elif source["missing"]:
                        connection.execute("UPDATE knowledge_sources SET missing = 0 WHERE id = ?", (source["id"],))
                else:
                    gone[source["id"]] = relative
            for relative, item in items.items():
                if not item["ticked"] or relative in folder["unticked"] or relative in known:
                    continue
                content = file_hash(inside(root, relative))
                renamed = next((source_id for source_id in gone if hashes[source_id] == content), None)
                if renamed:
                    del gone[renamed]
                    self._update_file(connection, renamed, root, relative)
                    result["moved"].append(relative)
                else:
                    self._add_file(connection, folder, root, relative)
                    result["added"].append(relative)
            for source_id, relative in gone.items():
                connection.execute("UPDATE knowledge_sources SET missing = 1 WHERE id = ?", (source_id,))
                result["missing"].append(relative)
        return result

    def refresh_all(self) -> list[dict]:
        """Refresh every connected folder, as opening the app does; one not found is only marked so."""
        return [{"folderId": folder["id"], **self.refresh(folder["id"])} for folder in self.folders()]

    def relocate(self, folder_id: str, path: str) -> dict:
        """Give a folder that moved its new place, and refresh it there.

        Raises:
            SourceError: When the path isn't a folder.
        """
        root = self.preview(path)["path"]
        self.folder(folder_id)
        with self.store.connect() as connection:
            connection.execute("UPDATE source_folders SET path = ?, title = ? WHERE id = ?", (root, Path(root).name, folder_id))
        return self.refresh(folder_id)

    def locate(self, source_id: str, relative: str) -> dict:
        """Give a missing file its new place in its folder. When Refresh already added that file anew, the
        source located takes it over, as long as that copy has no goal or topic of its own.

        Raises:
            SourceError: When the file isn't in the folder, or is in the Library as a source with links.
        """
        source = self.source(source_id)
        folder = self.folder(source["folderId"])
        root = Path(folder["path"])
        if not inside(root, relative).is_file():
            raise SourceError("That file isn't in the folder.")
        relative = PurePosixPath(inside(root, relative).relative_to(root.resolve())).as_posix()
        copy = next((other for other in folder["sources"] if other["relativePath"] == relative and other["id"] != source_id), None)
        if copy:
            with self.store.connect() as connection:
                linked = copy["goalId"] or connection.execute("SELECT 1 FROM goal_topics WHERE source_id = ?", (copy["id"],)).fetchone()
            if linked:
                raise SourceError(f"That file is in the Library already, as “{copy['title']}”.")
            VectorStore(self.store.path).delete_source(copy["id"])
        with self.store.connect() as connection:
            self._update_file(connection, source_id, root, relative)
        return self.source(source_id)

    def forget(self, source_id: str) -> None:
        """Before a folder's file is removed from the Library, untick it in its folder, so Refresh leaves it
        out from then on. The file itself is not touched; any other source needs nothing.

        Raises:
            SourceError: When there is no such source.
        """
        source = self.source(source_id)
        if source["origin"] != "folder":
            return
        folder = self.folder(source["folderId"])
        unticked = sorted(set(folder["unticked"]) | {source["relativePath"]})
        with self.store.connect() as connection:
            connection.execute("UPDATE source_folders SET unticked_json = ? WHERE id = ?", (json.dumps(unticked), folder["id"]))

    def source(self, source_id: str) -> dict:
        """A Library source of any origin.

        Raises:
            SourceError: When there is no such source.
        """
        with self.store.connect() as connection:
            row = connection.execute(f"SELECT {_SOURCE_COLUMNS} FROM knowledge_sources WHERE id = ?", (source_id,)).fetchone()
        if not row:
            raise SourceNotFound("That source isn't in the Library.")
        return _source(row)

    def text(self, source_id: str) -> str:
        """A source's text, read on this Mac: a folder's file from the folder, a note's or an imported file's
        from the Library. A website's text is never kept, so it has none.

        Raises:
            SourceError: When a folder's file can't be found or read.
        """
        source = self.source(source_id)
        if source["origin"] == "website":
            return ""
        if source["origin"] == "folder":
            return read_file(self.open_target(source_id)["path"])
        with self.store.connect() as connection:
            return "\n".join(row[0] for row in connection.execute(
                "SELECT content FROM knowledge_chunks WHERE source_id = ? ORDER BY chunk_index", (source_id,)))

    def set_briefing(self, source_id: str, briefing: str | None, outline: list[str] | None, by: str) -> dict:
        """Keep the briefing the user confirmed, and for a source without headings of its own the outline:
        by "ava" when Ava's suggestion was kept as it was, by "you" when the user wrote or changed it.

        Args:
            briefing: What the source is about, or None to leave its briefing, and whose it is, as they are.
            outline: Second-level headings for the source, or None to leave its outline as it is.

        Raises:
            SourceError: When neither a briefing nor headings are given, or for one by anyone but Ava or the user.
        """
        if by not in BRIEFED_BY:
            raise SourceError("A briefing is either Ava's or yours.")
        briefing = cut_words(briefing or "")
        source = self.source(source_id)
        headings = [str(heading).strip()[:OUTLINE_HEADING_CHARACTERS] for heading in outline or [] if str(heading).strip()]
        if not briefing and not (headings and source["outlineBy"] != "source"):
            raise SourceError("Give the briefing a few words.")
        with self.store.connect() as connection:
            if briefing:
                connection.execute("UPDATE knowledge_sources SET briefing = ?, briefing_by = ? WHERE id = ?", (briefing, by, source_id))
            if headings and source["outlineBy"] != "source":
                kept = [{"title": source["title"], "line": None, "topics": [{"title": heading, "line": None} for heading in headings]}]
                connection.execute("UPDATE knowledge_sources SET outline_json = ?, outline_by = ? WHERE id = ?",
                                   (json.dumps(kept, ensure_ascii=False), by, source_id))
        return self.source(source_id)

    def add_website(self, address: str, briefing: str, domain: str) -> dict:
        """Save a website to the Library by its address, with the briefing the user typed, without looking it up.

        Raises:
            SourceError: For an address that isn't a web address.
        """
        address = _web_address(address)
        source_id = f"source_{uuid.uuid4().hex[:16]}"
        briefing = briefing.strip() or None
        with self.store.connect() as connection:
            connection.execute(
                """INSERT INTO knowledge_sources (id, title, source_type, source_url, domain, content_hash, created_at, origin,
                                                  briefing, briefing_by)
                   VALUES (?, ?, 'document', ?, ?, ?, ?, 'website', ?, ?)""",
                (source_id, urlsplit(address).netloc, address, domain, address, _now(), briefing, "you" if briefing else ""))
        return self.source(source_id)

    def look_up(self, source_id: str) -> dict:
        """Look a saved website up, the one time DayWright goes online for it: keep its title, its own
        briefing when it publishes one (else the user's stays) and its headings, and none of its text. A
        website looked up before is never fetched again.

        Raises:
            SourceError: When the source isn't a website, or the site can't be reached.
        """
        source = self.source(source_id)
        if source["origin"] != "website":
            raise SourceError("Only a website is looked up.")
        if source["lookedUp"]:
            return source
        page = fetch_page(source["address"])
        briefing, by = (page["briefing"], "source") if page["briefing"] else (source["briefing"], source["briefingBy"])
        with self.store.connect() as connection:
            connection.execute(
                """UPDATE knowledge_sources SET title = ?, briefing = ?, briefing_by = ?, outline_json = ?, outline_by = ?,
                          looked_up_at = ? WHERE id = ?""",
                (page["title"] or source["title"], briefing, by, json.dumps(page["outline"], ensure_ascii=False),
                 "source" if page["outline"] else "", _now(), source_id))
        return self.source(source_id)

    def open_target(self, source_id: str, where: str = "app") -> dict:
        """What opening a source opens: a folder's file by its own stored path, or on the folder's website;
        a website in the browser. A note or an imported file keeps only its text, so has nothing to open.

        Raises:
            SourceError: When the folder or the file isn't found, or the source has nothing to open.
        """
        source = self.source(source_id)
        if source["origin"] == "website":
            return {"kind": "website", "address": source["address"]}
        if source["origin"] != "folder":
            raise SourceError("The Library keeps only its text, so there is no file to open.")
        folder = self.folder(source["folderId"])
        if where == "website":
            if not folder["website"]:
                raise SourceError("The folder has no website.")
            return {"kind": "website", "address": lesson_address(folder["website"], source["relativePath"])}
        root = Path(folder["path"])
        if not root.is_dir():
            raise SourceError(f"Folder not found at {folder['path']}.")
        path = inside(root, source["relativePath"])
        if not path.is_file():
            raise SourceError("Not found in the folder.")
        return {"kind": "file", "path": path}

    def index(self, rag: RagService, folder_id: str, changed: list[str] | tuple = ()) -> int:
        """Index a folder's files for search, so the Library's search and Ava find their passages and name
        them: each not indexed yet, and each in `changed`, read again. A file missing or not found is left
        for later; without the embedding model nothing is indexed, and the next time catches up.

        Returns:
            How many files were indexed.
        """
        with self.store.connect() as connection:
            bare = {row[0] for row in connection.execute(
                """SELECT s.id FROM knowledge_sources s WHERE s.folder_id = ?
                   AND NOT EXISTS (SELECT 1 FROM knowledge_chunks c WHERE c.source_id = s.id)""", (folder_id,))}
        indexed = 0
        for source in self.folder(folder_id)["sources"]:
            if source["missing"] or (source["id"] not in bare and source["id"] not in changed):
                continue
            try:
                text = read_file(self.open_target(source["id"])["path"])
            except SourceError:
                continue
            try:
                rag.index_source(source["id"], text)
            except EmbeddingUnavailable:
                return indexed
            indexed += 1
        return indexed

    def open_with(self) -> dict:
        """Open with's app for each file type the user chose; a type not chosen opens in its default."""
        with self.store.connect() as connection:
            row = connection.execute("SELECT value_json FROM preferences WHERE key = ?", (OPEN_WITH_KEY,)).fetchone()
        return json.loads(row["value_json"]) if row else {}

    def set_open_with(self, chosen: dict) -> dict:
        """Keep Open with's app for each file type: "default", "obsidian", or an app's name."""
        kept = {kind: str(app).strip()[:OPEN_WITH_NAME_LENGTH] for kind, app in chosen.items()
                if kind in OPEN_WITH_TYPES and str(app).strip()}
        with self.store.connect() as connection:
            connection.execute(
                """INSERT INTO preferences (key, value_json, updated_at) VALUES (?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at""",
                (OPEN_WITH_KEY, json.dumps(kept), _now()))
        return kept
