from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import sqlite_vec

from .config import Settings
from .llama_runtime import LlamaRuntime


EMBEDDING_DIMENSION = 1024
MAX_RETRIEVAL_DISTANCE = 1.15
QUERY_INSTRUCTION = (
    "Instruct: Retrieve relevant passages for answering a private personal learning, life, "
    "or money-management question.\nQuery: "
)


class EmbeddingUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class RetrievalResult:
    status: str
    matches: tuple[dict, ...] = ()
    detail: str | None = None

    def public(self) -> dict:
        payload = {"status": self.status, "matches": list(self.matches)}
        if self.detail:
            payload["detail"] = self.detail
        return payload


def chunk_text(text: str, chunk_words: int = 180, overlap_words: int = 30) -> list[str]:
    words = text.split()
    if not words:
        return []
    if chunk_words <= overlap_words:
        raise ValueError("Chunk size must be larger than its overlap")

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap_words
    return chunks


class EmbeddingGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._runtime = LlamaRuntime(
            settings.llama_binary,
            settings.embedding_path,
            [
                "--embedding",
                "--pooling",
                "last",
                "--ctx-size",
                str(settings.embedding_context),
                "--batch-size",
                "512",
                "--ubatch-size",
                "512",
            ],
        )

    @property
    def files_ready(self) -> bool:
        return self._runtime.files_ready

    def status(self) -> dict:
        running = self._runtime.running
        return {
            "state": "ready" if running else "available" if self.files_ready else "unavailable",
            "running": running,
            "modelAvailable": self.settings.embedding_path.is_file(),
            "runtimeAvailable": self.settings.llama_binary.is_file(),
            "label": (
                "Qwen3 Embedding 0.6B · on this Mac"
                if self.files_ready
                else "Embedding model needs setup"
            ),
            "dimensions": EMBEDDING_DIMENSION,
        }

    def start(self, timeout: float = 90.0) -> dict:
        self._runtime.start(timeout)
        return self.status()

    def stop(self) -> None:
        self._runtime.stop()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([f"{QUERY_INSTRUCTION}{text}"])[0]

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        status = self.start()
        connection = self._runtime.connection()
        if not status["running"] or connection is None:
            raise EmbeddingUnavailable("The local embedding model is not available")

        payload = json.dumps(
            {"model": "local-qwen-embedding", "input": texts}
        ).encode("utf-8")
        port, token = connection
        request = Request(
            f"http://127.0.0.1:{port}/v1/embeddings",
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=90) as response:
                body = json.loads(response.read().decode("utf-8"))
            rows = sorted(body["data"], key=lambda row: int(row["index"]))
            embeddings = [row["embedding"] for row in rows]
            if len(embeddings) != len(texts) or any(
                len(vector) != EMBEDDING_DIMENSION for vector in embeddings
            ):
                raise EmbeddingUnavailable("The embedding model returned an unexpected shape")
            return embeddings
        except (HTTPError, URLError, TimeoutError, KeyError, json.JSONDecodeError) as error:
            raise EmbeddingUnavailable("The local embedding request failed") from error


@contextmanager
def _transaction(connection: sqlite3.Connection):
    """Run a block as one transaction, rolling it back if the block raises.

    Store connections run in autocommit mode, so a multi-statement write needs an explicit
    transaction to remain atomic.
    """
    connection.execute("BEGIN")
    try:
        yield connection
    except Exception:
        connection.execute("ROLLBACK")
        raise
    connection.execute("COMMIT")


class VectorStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        """Open the store with the vector extension loaded.

        Autocommit keeps single statements immediate; `_transaction` wraps multi-statement writes.
        """
        connection = sqlite3.connect(str(self.database_path), timeout=15, isolation_level=None)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.enable_load_extension(True)
        connection.load_extension(sqlite_vec.loadable_path())
        connection.enable_load_extension(False)
        return connection

    def _migrate(self) -> None:
        connection = self._connect()
        try:
            connection.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunk_vectors "
                f"USING vec0(embedding float[{EMBEDDING_DIMENSION}])"
            )
        finally:
            connection.close()

    def status(self) -> dict:
        connection = self._connect()
        try:
            source_count = next(
                connection.execute("SELECT COUNT(*) FROM knowledge_sources")
            )[0]
            chunk_count = next(
                connection.execute("SELECT COUNT(*) FROM knowledge_chunks")
            )[0]
            version = next(connection.execute("SELECT vec_version()"))[0]
        finally:
            connection.close()
        return {
            "engine": "sqlite-vec",
            "engineVersion": version,
            "sourceCount": source_count,
            "chunkCount": chunk_count,
            "dimensions": EMBEDDING_DIMENSION,
        }

    def sources(self) -> list[dict]:
        connection = self._connect()
        try:
            rows = list(
                connection.execute(
                    """SELECT s.id, s.title, s.source_type, s.created_at, COUNT(c.id),
                              s.source_url, s.source_license
                       FROM knowledge_sources s
                       LEFT JOIN knowledge_chunks c ON c.source_id = s.id
                       GROUP BY s.id
                       ORDER BY s.created_at DESC"""
                )
            )
        finally:
            connection.close()
        return [
            {
                "id": row[0],
                "title": row[1],
                "sourceType": row[2],
                "createdAt": row[3],
                "chunkCount": row[4],
                "sourceUrl": row[5],
                "sourceLicense": row[6],
            }
            for row in rows
        ]

    def replace_source(
        self,
        title: str,
        source_type: str,
        chunks: list[str],
        embeddings: list[list[float]],
        created_at: str,
        source_url: str = "",
        source_license: str = "",
    ) -> dict:
        if len(chunks) != len(embeddings):
            raise ValueError("Every knowledge chunk requires one embedding")
        source_key = f"{source_type}\0{title.strip().lower()}".encode("utf-8")
        source_id = f"source_{hashlib.sha256(source_key).hexdigest()[:16]}"
        content_hash = hashlib.sha256("\n".join(chunks).encode("utf-8")).hexdigest()
        connection = self._connect()
        try:
            with _transaction(connection):
                old_ids = [
                    row[0]
                    for row in connection.execute(
                        "SELECT id FROM knowledge_chunks WHERE source_id = ?", (source_id,)
                    )
                ]
                for chunk_id in old_ids:
                    connection.execute(
                        "DELETE FROM knowledge_chunk_vectors WHERE rowid = ?", (chunk_id,)
                    )
                connection.execute("DELETE FROM knowledge_chunks WHERE source_id = ?", (source_id,))
                connection.execute(
                    """INSERT INTO knowledge_sources
                       (id, title, source_type, source_url, source_license, content_hash, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id) DO UPDATE SET
                         title = excluded.title,
                         source_type = excluded.source_type,
                         source_url = excluded.source_url,
                         source_license = excluded.source_license,
                         content_hash = excluded.content_hash,
                         created_at = excluded.created_at""",
                    (source_id, title.strip(), source_type, source_url, source_license,
                     content_hash, created_at),
                )
                for index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    cursor = connection.execute(
                        """INSERT INTO knowledge_chunks
                           (source_id, chunk_index, content, created_at)
                           VALUES (?, ?, ?, ?)""",
                        (source_id, index, chunk, created_at),
                    )
                    chunk_id = cursor.lastrowid
                    connection.execute(
                        "INSERT INTO knowledge_chunk_vectors(rowid, embedding) VALUES (?, ?)",
                        (chunk_id, sqlite_vec.serialize_float32(embedding)),
                    )
        finally:
            connection.close()
        return {
            "id": source_id,
            "title": title.strip(),
            "sourceType": source_type,
            "chunkCount": len(chunks),
            "createdAt": created_at,
            "sourceUrl": source_url,
            "sourceLicense": source_license,
        }

    def search(self, embedding: list[float], limit: int) -> list[dict]:
        connection = self._connect()
        try:
            nearest = list(
                connection.execute(
                    """SELECT rowid, distance
                       FROM knowledge_chunk_vectors
                       WHERE embedding MATCH ? AND k = ?""",
                    (sqlite_vec.serialize_float32(embedding), limit),
                )
            )
            matches = []
            for rank, (chunk_id, distance) in enumerate(nearest, start=1):
                row = next(
                    connection.execute(
                        """SELECT c.id, c.content, c.chunk_index, s.id, s.title, s.source_type,
                                  s.source_url, s.source_license
                           FROM knowledge_chunks c
                           JOIN knowledge_sources s ON s.id = c.source_id
                           WHERE c.id = ?""",
                        (chunk_id,),
                    ),
                    None,
                )
                if row:
                    matches.append(
                        {
                            "rank": rank,
                            "chunkId": row[0],
                            "content": row[1],
                            "chunkIndex": row[2],
                            "sourceId": row[3],
                            "sourceTitle": row[4],
                            "sourceType": row[5],
                            "distance": round(float(distance), 6),
                            "sourceUrl": row[6],
                            "sourceLicense": row[7],
                        }
                    )
            return matches
        finally:
            connection.close()


class RagService:
    def __init__(self, vector_store: VectorStore, embedder: EmbeddingGateway) -> None:
        self.vector_store = vector_store
        self.embedder = embedder

    def status(self) -> dict:
        return {
            "vectorStore": self.vector_store.status(),
            "embeddingModel": self.embedder.status(),
        }

    def sources(self) -> list[dict]:
        return self.vector_store.sources()

    def ingest(self, title: str, source_type: str, text: str, created_at: str,
               source_url: str = "", source_license: str = "") -> dict:
        """Embed a bounded source and persist its text, vectors, and public attribution."""
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("Knowledge source text is empty")
        embeddings = self.embedder.embed_documents(chunks)
        return self.vector_store.replace_source(
            title, source_type, chunks, embeddings, created_at, source_url, source_license
        )

    def retrieve(self, query: str, limit: int = 4) -> RetrievalResult:
        status = self.vector_store.status()
        if status["chunkCount"] == 0:
            return RetrievalResult("empty")
        try:
            embedding = self.embedder.embed_query(query)
            matches = tuple(
                match
                for match in self.vector_store.search(embedding, limit)
                if match["distance"] <= MAX_RETRIEVAL_DISTANCE
            )
            return RetrievalResult("ready" if matches else "no_match", matches)
        except EmbeddingUnavailable as error:
            return RetrievalResult("unavailable", detail=str(error))
