"""
Vector Memory Store using ChromaDB.

Provides long-term semantic memory across all chat sessions.
Messages are embedded and stored so the agent can recall relevant
facts from past conversations via similarity search.
"""

import chromadb
from chromadb.config import Settings
from datetime import datetime
from pathlib import Path
import os
import logging

from app.core.config import settings

logger = logging.getLogger("smart_inventory.memory")


class VectorMemory:
    """ChromaDB-backed semantic memory for the inventory chatbot."""

    def __init__(self, persist_dir: str = None):
        if not settings.CHROMADB_ENABLED:
            logger.info("ChromaDB disabled via config - running without vector memory")
            self._available = False
            return
            
        if persist_dir is None:
            # Use configured path, resolve relative to project root
            if os.path.isabs(settings.CHROMADB_PATH):
                persist_dir = settings.CHROMADB_PATH
            else:
                base_dir = Path(__file__).resolve().parents[4]
                persist_dir = str(base_dir / settings.CHROMADB_PATH)

        os.makedirs(persist_dir, exist_ok=True)

        try:
            self._client = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=settings.CHROMADB_COLLECTION,
                metadata={"description": "Long-term chat conversation memory"},
            )
            self._available = True
            logger.info(
                "ChromaDB initialized → path: %s, collection: %s",
                persist_dir,
                settings.CHROMADB_COLLECTION
            )
        except Exception as e:
            logger.warning("ChromaDB init failed, running without vector memory: %s", e)
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        timestamp: datetime = None,
    ) -> None:
        if not self._available or not content or not content.strip():
            return

        if timestamp is None:
            timestamp = datetime.now()

        doc_id = f"{session_id}_{role}_{timestamp.strftime('%Y%m%d%H%M%S%f')}"
        ts_str = timestamp.strftime("%Y-%m-%d %H:%M")

        try:
            self._collection.upsert(
                ids=[doc_id],
                documents=[content],
                metadatas=[
                    {
                        "session_id": session_id,
                        "role": role,
                        "timestamp": ts_str,
                    }
                ],
            )
        except Exception as e:
            logger.warning("Failed to store message in vector memory: %s", e)

    def search_relevant(
        self, query: str, n_results: int = 5, exclude_session: str = None
    ) -> list[dict]:
        if not self._available or not query or not query.strip():
            return []

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=n_results * 2,
            )

            matches = []
            if results and results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    sid = meta.get("session_id", "")

                    if exclude_session and sid == exclude_session:
                        continue

                    matches.append(
                        {
                            "content": doc,
                            "role": meta.get("role", "unknown"),
                            "timestamp": meta.get("timestamp", "unknown"),
                            "session_id": sid,
                        }
                    )

                    if len(matches) >= n_results:
                        break

            return matches

        except Exception as e:
            logger.warning("Vector memory search failed: %s", e)
            return []

    def get_stats(self) -> dict:
        if not self._available:
            return {"available": False, "count": 0}

        try:
            return {
                "available": True,
                "count": self._collection.count(),
            }
        except Exception:
            return {"available": False, "count": 0}


_memory_instance: VectorMemory | None = None


def get_vector_memory() -> VectorMemory:
    """Get or create the singleton VectorMemory instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = VectorMemory()
    return _memory_instance
