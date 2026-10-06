"""Open a source where it belongs: a file in the Mac's app for its type, or the one chosen for that type
under Open with, Markdown in Obsidian when it's installed; a website in the browser. Only a source's own
stored path or address is ever opened, never one a request names.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from urllib.parse import quote, urlsplit

# How long the Mac's open command may take to hand a source to its app.
OPEN_TIMEOUT = 15
# The file types Open with chooses an app for, by suffix.
OPEN_TYPES = {".md": "md", ".markdown": "md", ".pdf": "pdf", ".docx": "docx"}
# Where Obsidian is installed, when it is.
OBSIDIAN_APPS = (Path("/Applications/Obsidian.app"), Path.home() / "Applications" / "Obsidian.app")


class OpenError(ValueError):
    """A source that can't be opened, with the reason in words for the user."""


def obsidian_installed() -> bool:
    """Whether Obsidian is installed on this Mac, for itself or for everyone."""
    return any(app.exists() for app in OBSIDIAN_APPS)


def open_command(target: dict, chosen: dict, obsidian: bool) -> list[str]:
    """The Mac's open command for a source.

    Args:
        target: {"kind": "file", "path"} for a folder's file, or {"kind": "website", "address"}.
        chosen: Open with's app for each file type ("md", "pdf", "docx"): "default" for the Mac's
            own, "obsidian" for Markdown, or an app's name; a type not chosen goes by its default.
        obsidian: Whether Obsidian is installed; Markdown opens in it unless another app is chosen.

    Returns:
        The command's words, such as ["open", "-a", "Skim", "/…/book.pdf"].

    Raises:
        OpenError: For an address that isn't a web address, or a file of a type DayWright doesn't read.
    """
    if target["kind"] == "website":
        address = target["address"]
        if urlsplit(address).scheme not in ("http", "https") or not urlsplit(address).netloc:
            raise OpenError("Only a web address can open in the browser.")
        return ["open", address]
    path = Path(target["path"])
    kind = OPEN_TYPES.get(path.suffix.lower())
    if kind is None:
        raise OpenError("Only Markdown, PDF and Word files open from DayWright.")
    app = chosen.get(kind) or ("obsidian" if kind == "md" else "default")
    if app == "obsidian":
        return ["open", f"obsidian://open?path={quote(str(path), safe='')}"] if obsidian else ["open", str(path)]
    return ["open", str(path)] if app == "default" else ["open", "-a", app, str(path)]


def open_source(target: dict, chosen: dict, obsidian: bool) -> list[str]:
    """Open a source, as open_command says, and return the command run. DAYWRIGHT_OPEN_COMMAND, when
    set, stands in for the Mac's open command, so a check can see what would open without opening it.

    Raises:
        OpenError: When the file is no longer there, or the command fails.
    """
    command = open_command(target, chosen, obsidian)
    if target["kind"] == "file" and not Path(target["path"]).is_file():
        raise OpenError("The file isn't there any more.")
    command[0] = os.environ.get("DAYWRIGHT_OPEN_COMMAND") or command[0]
    try:
        subprocess.run(command, check=True, timeout=OPEN_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as error:
        raise OpenError("The Mac couldn't open it.") from error
    return command
