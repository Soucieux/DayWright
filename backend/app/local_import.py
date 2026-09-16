"""Bounded extraction from a user-selected local Markdown, PDF, or Word file."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from lxml.etree import XMLSyntaxError
from pypdf import PdfReader
from pypdf.errors import PdfReadError


MAX_FILE_BYTES = 2_000_000
MAX_TEXT_CHARS = 50_000


def extract_local_file(filename: str, data: bytes) -> tuple[str, str]:
    """Return a clean title and extractable text; no file is stored or sent online."""
    name = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    suffix = Path(name).suffix.lower()
    if suffix not in (".md", ".markdown", ".pdf", ".docx"):
        raise ValueError("Supported files are Markdown (.md), PDF (.pdf), and Word (.docx)")
    if not name or len(name) > 200 or not data or len(data) > MAX_FILE_BYTES:
        raise ValueError("Choose a nonempty file smaller than 2 MB with a short name")

    try:
        if suffix in (".md", ".markdown"):
            text = data.decode("utf-8-sig")
        elif suffix == ".pdf":
            if not data.startswith(b"%PDF-"):
                raise ValueError("This file is not a valid PDF")
            reader = PdfReader(BytesIO(data), strict=True)
            if reader.is_encrypted:
                raise ValueError("Unlock the PDF before importing it")
            if len(reader.pages) > 20:
                raise ValueError("PDF import supports up to 20 pages at a time")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            with ZipFile(BytesIO(data)) as archive:
                parts = archive.infolist()
                if (len(parts) > 1000 or sum(part.file_size for part in parts) > 8_000_000
                        or "word/document.xml" not in archive.namelist()
                        or any(part.filename.lower().endswith("vbaproject.bin") for part in parts)):
                    raise ValueError("This Word file is too complex or contains macros")
            document = Document(BytesIO(data))
            blocks = []
            for block in document.iter_inner_content():
                if isinstance(block, Table):
                    blocks.extend(" | ".join(cell.text for cell in row.cells)
                                  for row in block.rows)
                else:
                    blocks.append(block.text)
            text = "\n".join(blocks)
    except (BadZipFile, UnicodeError, OSError, PdfReadError,
            PackageNotFoundError, XMLSyntaxError) as error:
        raise ValueError("This file could not be read; check its format and encoding") from error

    text = text.strip()
    if not text:
        raise ValueError("No extractable text was found; scanned files need OCR before import")
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError("Extracted text exceeds 50,000 characters; split the file first")
    return name, text
