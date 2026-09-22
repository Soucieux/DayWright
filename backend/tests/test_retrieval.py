from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from backend.app.database import Database
from backend.app.retrieval import EMBEDDING_DIMENSION, VectorStore

CREATED_AT = "2026-09-21T09:00:00+00:00"


def _vector(first: float) -> list[float]:
    """Build one normalized-length embedding that differs only in its first component."""
    return [first] + [0.0] * (EMBEDDING_DIMENSION - 1)


class VectorStoreTests(unittest.TestCase):
    def _store(self, folder: str) -> VectorStore:
        path = Path(folder) / "retrieval.sqlite3"
        Database(path)
        return VectorStore(path)

    def test_an_ingested_chunk_is_retrievable_by_its_own_vector(self):
        with TemporaryDirectory() as folder:
            store = self._store(folder)

            store.replace_source("Recovery notes", "note", ["A screen-free wind-down at 22:30."],
                                 [_vector(1.0)], CREATED_AT)
            matches = store.search(_vector(1.0), 3)

            self.assertEqual([match["sourceTitle"] for match in matches], ["Recovery notes"])
            self.assertEqual(matches[0]["content"], "A screen-free wind-down at 22:30.")

    def test_a_rejected_vector_leaves_the_stored_source_unchanged(self):
        with TemporaryDirectory() as folder:
            store = self._store(folder)
            store.replace_source("Recovery notes", "note", ["The kept chunk."],
                                 [_vector(1.0)], CREATED_AT)

            with self.assertRaises(sqlite3.Error):
                store.replace_source(
                    "Recovery notes", "note", ["First replacement.", "Second replacement."],
                    [_vector(2.0), [0.5, 0.5]], CREATED_AT,
                )

            matches = store.search(_vector(1.0), 3)
            self.assertEqual([match["content"] for match in matches], ["The kept chunk."])
            self.assertEqual([source["title"] for source in store.sources()], ["Recovery notes"])


if __name__ == "__main__":
    unittest.main()
