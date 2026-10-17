"""
Vector Memory Store using Qdrant Cloud and Google Gemini Embeddings.

Provides long-term semantic memory across all chat sessions.
Messages are embedded via Google Gemini Embeddings API (gemini-embedding-001, 768-dim)
and stored in Qdrant Cloud so the agent can recall relevant facts from past
conversations via cosine-similarity search.
"""

from datetime import datetime
import logging
import uuid
from typing import List, Dict, Any, Optional
import httpx
import time


from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from app.core.config import settings

logger = logging.getLogger("smart_inventory.memory")


class VectorMemory:
    """Qdrant Cloud-backed semantic memory using Google Gemini Embeddings."""

    def __init__(self):
        self._available = False
        self._client: Optional[QdrantClient] = None
        self._collection: str = settings.QDRANT_COLLECTION
        self._model: str = settings.GEMINI_EMBEDDING_MODEL
        self._dim: int = settings.GEMINI_EMBEDDING_DIM
        self._api_key: Optional[str] = settings.GEMINI_API_KEY
        self._embedding_cache: Dict[str, List[float]] = {}
        self._http_client = httpx.Client(
            timeout=5.0,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )

        if not settings.QDRANT_ENABLED:
            logger.info("Qdrant disabled via config — running without vector memory")
            return

        if not settings.QDRANT_URL or not settings.QDRANT_API_KEY:
            logger.warning(
                "QDRANT_URL or QDRANT_API_KEY not set — running without vector memory"
            )
            return

        if not self._api_key:
            logger.warning(
                "GEMINI_API_KEY not set — vector embedding disabled"
            )
            return

        try:
            # Ensure proper port on Qdrant Cloud endpoints
            url = settings.QDRANT_URL.strip()
            if url and not url.endswith(":6333") and "cloud.qdrant.io" in url:
                url = f"{url}:6333"

            self._client = QdrantClient(
                url=url,
                api_key=settings.QDRANT_API_KEY,
                timeout=5,
            )
            self._ensure_collection()
            self._available = True
            logger.info(
                "Qdrant Cloud initialized with Gemini Embeddings → cluster: %s, collection: %s, model: %s (%dd)",
                url,
                self._collection,
                self._model,
                self._dim,
            )
        except Exception as e:
            logger.warning("Qdrant Cloud unavailable — vector memory disabled: %s", e)
            self._available = False
            self._client = None

    # Internal helpers

    def _ensure_collection(self) -> None:
        """Create or recreate the collection with the correct vector dimensions."""
        try:
            existing_collections = {c.name for c in self._client.get_collections().collections}
            if self._collection not in existing_collections:
                self._client.create_collection(
                    collection_name=self._collection,
                    vectors_config=VectorParams(
                        size=self._dim,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info("Qdrant collection created: %s (%dd)", self._collection, self._dim)
        except Exception as e:
            logger.debug("Collection check skipped: %s", e)

    def _embed(self, text: str) -> List[float]:
        """Generate normalized embedding vector via Google Gemini API with in-memory caching."""
        clean_text = (text or "").strip()
        if not clean_text:
            return [0.0] * self._dim

        if clean_text in self._embedding_cache:
            return self._embedding_cache[clean_text]

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:embedContent?key={self._api_key}"
        payload = {
            "content": {"parts": [{"text": clean_text}]},
            "output_dimensionality": self._dim,
        }

        try:
            response = self._http_client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            vec = data["embedding"]["values"]
            if len(self._embedding_cache) < 2000:
                self._embedding_cache[clean_text] = vec
            return vec
        except Exception as e:
            logger.debug("Gemini embedding failed: %s", e)
            return [0.0] * self._dim

    # Public API

    @property
    def is_available(self) -> bool:
        return self._available


    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        timestamp: datetime = None,
        org_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> None:
        if not self._available or not content or not content.strip():
            return

        if timestamp is None:
            timestamp = datetime.now()

        ts_str = timestamp.strftime("%Y-%m-%d %H:%M")
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
                            "org_id": org_id,
                            "user_id": user_id,
                        },
                    )
                ],
            )
        except Exception as e:
            logger.warning("Failed to store message in vector memory: %s", e)

    def add_onboarding_context(
        self,
        org_id: Optional[int],
        user_id: Optional[int],
        full_name: str,
        pharmacy_name: str,
        primary_counter: str = "Main Market Counter",
        plan_type: str = "single_pharmacy",
        extra_settings: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Embed and store store owner/admin onboarding profile context for semantic RAG recall."""
        if not self._available:
            return

        now = datetime.now()
        ts_str = now.strftime("%Y-%m-%d %H:%M")
        content = (
            f"Pharmacy Owner Profile: {full_name or 'Store Admin'}. "
            f"Medical Store & Pharmacy Name: {pharmacy_name or 'Pharmacy Store'}. "
            f"Primary Retail Counter / Location: {primary_counter or 'Main Counter'}. "
            f"Subscription Tier: {plan_type or 'single_pharmacy'}. "
            f"Onboarded on: {ts_str}. "
            f"InvIQ Assistant should address this user as the owner of {pharmacy_name or 'their pharmacy store'}."
        )

        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"onboarding_org_{org_id}_user_{user_id}"))

        try:
            vector = self._embed(content)
            self._client.upsert(
                collection_name=self._collection,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "session_id": "onboarding_profile",
                            "role": "system",
                            "timestamp": ts_str,
                            "content": content,
                            "org_id": org_id,
                            "user_id": user_id,
                            "type": "onboarding_profile",
                        },
                    )
                ],
            )
            logger.info("✅ Onboarding context indexed in Vector Memory for org_id=%s, user_id=%s", org_id, user_id)
        except Exception as e:
            logger.warning("Failed to store onboarding profile in vector memory: %s", e)

    def search_relevant(
        self,
        query: str,
        n_results: int = 5,
        exclude_session: str = None,
        org_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        clean_q = (query or "").strip()

        if not self._available or not clean_q:
            return []

        cache_key = f"{clean_q}:{n_results}:{exclude_session}:{org_id}:{user_id}"
        now = time.time()
        if hasattr(self, "_search_cache"):
            cached = self._search_cache.get(cache_key)
            if cached and now < cached[0]:
                return cached[1]
        else:
            self._search_cache = {}

        try:
            vector = self._embed(clean_q)

            # Build Qdrant payload filter for tenant isolation
            from qdrant_client.http.models import Filter, FieldCondition, MatchValue
            conditions = []
            if org_id is not None:
                conditions.append(
                    FieldCondition(key="org_id", match=MatchValue(value=org_id))
                )
            if user_id is not None:
                conditions.append(
                    FieldCondition(key="user_id", match=MatchValue(value=user_id))
                )
            query_filter = Filter(must=conditions) if conditions else None

            response = self._client.query_points(
                collection_name=self._collection,
                query=vector,
                limit=n_results * 2 if exclude_session else n_results,
                with_payload=True,
                query_filter=query_filter,
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

            if len(self._search_cache) < 500:
                self._search_cache[cache_key] = (now + 60.0, matches)
            return matches

        except Exception as e:
            logger.warning("Vector memory search failed: %s", e)
            return []


    def get_stats(self) -> Dict[str, Any]:
        if not self._available:
            return {"available": False, "count": 0}

        try:
            info = self._client.get_collection(self._collection)
            count = getattr(info, "points_count", None) or getattr(info, "vectors_count", 0) or 0
            return {
                "available": True,
                "count": count,
            }
        except Exception:
            return {"available": False, "count": 0}


_memory_instance: Optional[VectorMemory] = None


def get_vector_memory() -> VectorMemory:
    """Get or create the singleton VectorMemory instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = VectorMemory()
    return _memory_instance
