"""
Vector Memory Store using Qdrant Cloud.

Provides long-term semantic memory across all chat sessions.
Messages are embedded (sentence-transformers) and stored in Qdrant Cloud
so the agent can recall relevant facts from past conversations via
cosine-similarity search.
"""

from datetime import datetime
import logging
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger("smart_inventory.memory")

# Embedding model — 384-dim, fast, runs CPU-only
_EMBED_MODEL = "all-MiniLM-L6-v2"
_VECTOR_DIM = 384


class VectorMemory:
    """Qdrant Cloud-backed semantic memory for the inventory chatbot."""

    def __init__(self):
        # Initialize as unavailable by default
        self._available = False
        self._client: QdrantClient | None = None
        self._encoder: SentenceTransformer | None = None
        self._collection: str = settings.QDRANT_COLLECTION

        if not settings.QDRANT_ENABLED:
            logger.info("Qdrant disabled via config — running without vector memory")
            return

        if not settings.QDRANT_URL or not settings.QDRANT_API_KEY:
            logger.warning(
                "QDRANT_URL or QDRANT_API_KEY not set — running without vector memory"
            )
            return

        try:
            self._encoder = SentenceTransformer(_EMBED_MODEL)
            self._client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
                timeout=10,
            )
            self._ensure_collection()
            self._available = True
            logger.info(
                "Qdrant Cloud initialized → cluster: %s, collection: %s",
                settings.QDRANT_URL,
                self._collection,
            )
        except Exception as e:
            logger.warning("Qdrant Cloud unavailable — vector memory disabled: %s", e)
            self._available = False
            self._client = None
            self._encoder = None

    # ── Internal helpers ──────────────────────────────────────────────────

    def _ensure_collection(self) -> None:
        """Create the collection if it does not already exist."""
        existing = {c.name for c in self._client.get_collections().collections}
        if self._collection not in existing:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=_VECTOR_DIM,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Qdrant collection created: %s", self._collection)

    def _embed(self, text: str) -> list[float]:
        """Return a normalised embedding vector for the given text."""
        return self._encoder.encode(text, normalize_embeddings=True).tolist()

    # ── Public API (unchanged from ChromaDB version) ──────────────────────

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

        ts_str = timestamp.strftime("%Y-%m-%d %H:%M")
        # Use a deterministic UUID derived from session+role+timestamp so
        # repeated upserts are idempotent (same behaviour as ChromaDB upsert).
        point_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"{session_id}_{role}_{timestamp.strftime('%Y%m%d%H%M%S%f')}",
            )
        )

        try:
            vector = self._embed(content)
            self._client.upsert(
                collection_name=self._collection,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "session_id": session_id,
                            "role": role,
                            "timestamp": ts_str,
                            "content": content,
                        },
                    )
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
            vector = self._embed(query)

            # Build an optional filter to exclude the current session
            query_filter = None
            if exclude_session:
                # Qdrant doesn't support "not-equal" directly in free tier filters;
                # we fetch more results and filter client-side instead.
                pass

            response = self._client.query_points(
                collection_name=self._collection,
                query=vector,
                limit=n_results * 2 if exclude_session else n_results,
                with_payload=True,
            )

            matches = []
            for hit in response.points:
                payload = hit.payload or {}
                sid = payload.get("session_id", "")

                if exclude_session and sid == exclude_session:
                    continue

                matches.append(
                    {
                        "content": payload.get("content", ""),
                        "role": payload.get("role", "unknown"),
                        "timestamp": payload.get("timestamp", "unknown"),
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
            info = self._client.get_collection(self._collection)
            # vectors_count was renamed to points_count in qdrant-client >=1.10
            count = getattr(info, "points_count", None) or getattr(info, "vectors_count", 0) or 0
            return {
                "available": True,
                "count": count,
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
