import unittest
from pathlib import Path
from unittest.mock import patch

from backend.tests import isolation  # Imported first: keeps the tests off DayWright's own data.
from backend.app import opener
from backend.app.opener import OpenError, open_command, open_source


class OpenCommandTests(unittest.TestCase):
    FILE = Path("/tmp/Notes/Guides/01 Basics.md")

    def test_markdown_opens_in_obsidian_when_it_is_installed_in_the_vault_that_holds_it(self):
        self.assertEqual(open_command({"kind": "file", "path": self.FILE}, {}, obsidian=True),
                         ["open", "obsidian://open?path=%2Ftmp%2FNotes%2FGuides%2F01%20Basics.md"])

    def test_markdown_opens_in_the_macs_default_app_without_obsidian(self):
        self.assertEqual(open_command({"kind": "file", "path": self.FILE}, {}, obsidian=False), ["open", str(self.FILE)])

    def test_other_files_open_in_the_default_app_for_their_type(self):
        for name in ("book.pdf", "guide.docx"):
            with self.subTest(name):
                self.assertEqual(open_command({"kind": "file", "path": Path("/tmp") / name}, {}, obsidian=True),
                                 ["open", f"/tmp/{name}"])

    def test_open_with_chooses_the_app_per_file_type(self):
        chosen = {"md": "default", "pdf": "Skim", "docx": "Pages"}
        self.assertEqual(open_command({"kind": "file", "path": self.FILE}, chosen, obsidian=True), ["open", str(self.FILE)])
        self.assertEqual(open_command({"kind": "file", "path": Path("/tmp/book.pdf")}, chosen, obsidian=True),
                         ["open", "-a", "Skim", "/tmp/book.pdf"])
        self.assertEqual(open_command({"kind": "file", "path": Path("/tmp/guide.docx")}, chosen, obsidian=False),
                         ["open", "-a", "Pages", "/tmp/guide.docx"])
        self.assertEqual(open_command({"kind": "file", "path": self.FILE}, {"md": "obsidian"}, obsidian=False),
                         ["open", str(self.FILE)], "Obsidian chosen but not installed opens the default app")

    def test_a_website_opens_in_the_browser_and_nothing_else_is_ever_opened(self):
        self.assertEqual(open_command({"kind": "website", "address": "https://example.com/a"}, {}, obsidian=True),
                         ["open", "https://example.com/a"])
        for address in ("file:///etc/passwd", "javascript:alert(1)", "obsidian://open?path=/etc"):
            with self.subTest(address), self.assertRaises(OpenError):
                open_command({"kind": "website", "address": address}, {}, obsidian=True)
        with self.assertRaises(OpenError):
            open_command({"kind": "file", "path": Path("/tmp/run.sh")}, {}, obsidian=True)


class OpenSourceTests(unittest.TestCase):
    def test_the_command_runs_without_waiting_for_a_shell_and_a_test_command_can_stand_in(self):
        with patch.object(opener.subprocess, "run") as run, patch.dict("os.environ", {}, clear=False) as environ:
            environ.pop("DAYWRIGHT_OPEN_COMMAND", None)
            open_source({"kind": "website", "address": "https://example.com/"}, {}, obsidian=False)
        run.assert_called_once_with(["open", "https://example.com/"], check=True, timeout=opener.OPEN_TIMEOUT)

        with patch.object(opener.subprocess, "run") as run, patch.dict("os.environ", {"DAYWRIGHT_OPEN_COMMAND": "/tmp/log-open"}):
            open_source({"kind": "website", "address": "https://example.com/"}, {}, obsidian=False)
        run.assert_called_once_with(["/tmp/log-open", "https://example.com/"], check=True, timeout=opener.OPEN_TIMEOUT)

    def test_a_missing_file_is_refused_before_anything_runs(self):
        with patch.object(opener.subprocess, "run") as run, self.assertRaises(OpenError):
            open_source({"kind": "file", "path": Path("/tmp/no-such-folder-here/a.md")}, {}, obsidian=False)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
