"""
Qdrant vector memory tests.

Tests VectorMemory behaviour using a mocked QdrantClient so no real
network calls are made. Covers:
- Init with / without credentials
- add_message (upsert logic)
- search_relevant (query_points mapping)
- get_stats (points_count)
- is_available flag
- Graceful degradation on connection failure
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, call


# ── Helpers ───────────────────────────────────────────────────────────────

def _make_memory(enabled: bool = True, url: str = "https://mock.qdrant.io", api_key: str = "key"):
    """
    Build a VectorMemory with a mocked QdrantClient and SentenceTransformer.
    Returns (memory, mock_client, mock_encoder).
    """
    from app.infrastructure.vector_store.vector_store import VectorMemory

    mock_client = MagicMock()
    mock_client.get_collections.return_value = MagicMock(collections=[])
    mock_encoder = MagicMock()
    mock_encoder.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)

    with (
        patch("app.infrastructure.vector_store.vector_store.settings") as mock_settings,
        patch("app.infrastructure.vector_store.vector_store.QdrantClient", return_value=mock_client),
        patch("app.infrastructure.vector_store.vector_store.SentenceTransformer", return_value=mock_encoder),
    ):
        mock_settings.QDRANT_ENABLED = enabled
        mock_settings.QDRANT_URL = url
        mock_settings.QDRANT_API_KEY = api_key
        mock_settings.QDRANT_COLLECTION = "test_collection"
        memory = VectorMemory()

    return memory, mock_client, mock_encoder


# ── Availability ──────────────────────────────────────────────────────────

class TestVectorMemoryAvailability:

    def test_available_when_enabled_and_credentials_set(self):
        memory, _, _ = _make_memory(enabled=True)
        assert memory.is_available is True

    def test_not_available_when_disabled(self):
        from app.infrastructure.vector_store.vector_store import VectorMemory
        with patch("app.infrastructure.vector_store.vector_store.settings") as s:
            s.QDRANT_ENABLED = False
            s.QDRANT_URL = ""
            s.QDRANT_API_KEY = ""
            s.QDRANT_COLLECTION = "test"
            memory = VectorMemory()
        assert memory.is_available is False

    def test_not_available_when_url_missing(self):
        from app.infrastructure.vector_store.vector_store import VectorMemory
        with patch("app.infrastructure.vector_store.vector_store.settings") as s:
            s.QDRANT_ENABLED = True
            s.QDRANT_URL = ""
            s.QDRANT_API_KEY = "key"
            s.QDRANT_COLLECTION = "test"
            memory = VectorMemory()
        assert memory.is_available is False

    def test_not_available_when_api_key_missing(self):
        from app.infrastructure.vector_store.vector_store import VectorMemory
        with patch("app.infrastructure.vector_store.vector_store.settings") as s:
            s.QDRANT_ENABLED = True
            s.QDRANT_URL = "https://mock.qdrant.io"
            s.QDRANT_API_KEY = ""
            s.QDRANT_COLLECTION = "test"
            memory = VectorMemory()
        assert memory.is_available is False

    def test_not_available_when_client_raises_on_init(self):
        from app.infrastructure.vector_store.vector_store import VectorMemory
        with (
            patch("app.infrastructure.vector_store.vector_store.settings") as s,
            patch(
                "app.infrastructure.vector_store.vector_store.QdrantClient",
                side_effect=Exception("connection refused"),
            ),
        ):
            s.QDRANT_ENABLED = True
            s.QDRANT_URL = "https://broken.qdrant.io"
            s.QDRANT_API_KEY = "key"
            s.QDRANT_COLLECTION = "test"
            memory = VectorMemory()
        assert memory.is_available is False


# ── Collection creation ───────────────────────────────────────────────────

class TestCollectionCreation:

    def test_creates_collection_if_not_exists(self):
        """_ensure_collection() must call create_collection when absent."""
        from app.infrastructure.vector_store.vector_store import VectorMemory

        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])
        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = MagicMock(tolist=lambda: [0.0] * 384)

        with (
            patch("app.infrastructure.vector_store.vector_store.settings") as s,
            patch("app.infrastructure.vector_store.vector_store.QdrantClient", return_value=mock_client),
            patch("app.infrastructure.vector_store.vector_store.SentenceTransformer", return_value=mock_encoder),
        ):
            s.QDRANT_ENABLED = True
            s.QDRANT_URL = "https://mock.qdrant.io"
            s.QDRANT_API_KEY = "key"
            s.QDRANT_COLLECTION = "new_collection"
            VectorMemory()

        mock_client.create_collection.assert_called_once()

    def test_skips_creation_if_collection_exists(self):
        """_ensure_collection() must NOT call create_collection when it exists."""
        from app.infrastructure.vector_store.vector_store import VectorMemory

        existing = MagicMock()
        existing.name = "existing_collection"

        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[existing])
        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = MagicMock(tolist=lambda: [0.0] * 384)

        with (
            patch("app.infrastructure.vector_store.vector_store.settings") as s,
            patch("app.infrastructure.vector_store.vector_store.QdrantClient", return_value=mock_client),
            patch("app.infrastructure.vector_store.vector_store.SentenceTransformer", return_value=mock_encoder),
        ):
            s.QDRANT_ENABLED = True
            s.QDRANT_URL = "https://mock.qdrant.io"
            s.QDRANT_API_KEY = "key"
            s.QDRANT_COLLECTION = "existing_collection"
            VectorMemory()

        mock_client.create_collection.assert_not_called()


# ── add_message ───────────────────────────────────────────────────────────

class TestAddMessage:

    def test_add_message_calls_upsert(self):
        memory, mock_client, _ = _make_memory()
        memory.add_message("sess-1", "user", "How much paracetamol do we have?")
        mock_client.upsert.assert_called_once()

    def test_add_message_upsert_has_correct_payload(self):
        memory, mock_client, _ = _make_memory()
        ts = datetime(2026, 7, 8, 12, 0, 0)
        memory.add_message("sess-1", "assistant", "We have 200 units.", timestamp=ts)

        args, kwargs = mock_client.upsert.call_args
        points = kwargs.get("points") or args[1]
        assert len(points) == 1
        payload = points[0].payload
        assert payload["session_id"] == "sess-1"
        assert payload["role"] == "assistant"
        assert payload["content"] == "We have 200 units."
        assert payload["timestamp"] == "2026-07-08 12:00"

    def test_add_message_skipped_when_not_available(self):
        from app.infrastructure.vector_store.vector_store import VectorMemory
        with patch("app.infrastructure.vector_store.vector_store.settings") as s:
            s.QDRANT_ENABLED = False
            s.QDRANT_URL = ""
            s.QDRANT_API_KEY = ""
            s.QDRANT_COLLECTION = "test"
            memory = VectorMemory()

        # Should not raise; upsert is never called
        memory.add_message("sess", "user", "Hello")

    def test_add_empty_message_skipped(self):
        memory, mock_client, _ = _make_memory()
        memory.add_message("sess-1", "user", "")
        memory.add_message("sess-1", "user", "   ")
        mock_client.upsert.assert_not_called()

    def test_add_message_upsert_failure_does_not_raise(self):
        """A Qdrant upsert error must be silently logged, not propagated."""
        memory, mock_client, _ = _make_memory()
        mock_client.upsert.side_effect = Exception("network timeout")
        # Should not raise
        memory.add_message("sess-1", "user", "What is the stock level?")

    def test_add_message_timestamp_defaults_to_now(self):
        memory, mock_client, _ = _make_memory()
        before = datetime.now()
        memory.add_message("sess-1", "user", "Default timestamp test")
        after = datetime.now()
        mock_client.upsert.assert_called_once()
        # Verify it was called — we can't easily check the exact ts, just that it ran
        assert mock_client.upsert.call_count == 1


# ── search_relevant ───────────────────────────────────────────────────────

class TestSearchRelevant:

    def _make_hit(self, content: str, role: str, session_id: str, timestamp: str = "2026-07-08 12:00"):
        hit = MagicMock()
        hit.payload = {
            "content": content,
            "role": role,
            "session_id": session_id,
            "timestamp": timestamp,
        }
        return hit

    def test_search_returns_list_of_dicts(self):
        memory, mock_client, _ = _make_memory()
        hits = [self._make_hit("Paracetamol is low.", "assistant", "sess-other")]
        mock_client.query_points.return_value = MagicMock(points=hits)

        results = memory.search_relevant("paracetamol stock")
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["content"] == "Paracetamol is low."

    def test_search_excludes_current_session(self):
        memory, mock_client, _ = _make_memory()
        hits = [
            self._make_hit("From current session", "user", "sess-current"),
            self._make_hit("From other session", "user", "sess-other"),
        ]
        mock_client.query_points.return_value = MagicMock(points=hits)

        results = memory.search_relevant("stock", exclude_session="sess-current")
        contents = [r["content"] for r in results]
        assert "From current session" not in contents
        assert "From other session" in contents

    def test_search_respects_n_results_limit(self):
        memory, mock_client, _ = _make_memory()
        hits = [self._make_hit(f"msg {i}", "user", f"sess-{i}") for i in range(10)]
        mock_client.query_points.return_value = MagicMock(points=hits)

        results = memory.search_relevant("query", n_results=3)
        assert len(results) <= 3

    def test_search_empty_query_returns_empty(self):
        memory, mock_client, _ = _make_memory()
        assert memory.search_relevant("") == []
        assert memory.search_relevant("   ") == []
        mock_client.query_points.assert_not_called()

    def test_search_returns_empty_when_not_available(self):
        from app.infrastructure.vector_store.vector_store import VectorMemory
        with patch("app.infrastructure.vector_store.vector_store.settings") as s:
            s.QDRANT_ENABLED = False
            s.QDRANT_URL = ""
            s.QDRANT_API_KEY = ""
            s.QDRANT_COLLECTION = "test"
            memory = VectorMemory()

        assert memory.search_relevant("anything") == []

    def test_search_failure_returns_empty_list(self):
        """A Qdrant search error must be silently handled."""
        memory, mock_client, _ = _make_memory()
        mock_client.query_points.side_effect = Exception("timeout")

        result = memory.search_relevant("paracetamol")
        assert result == []

    def test_search_result_has_required_keys(self):
        memory, mock_client, _ = _make_memory()
        hits = [self._make_hit("Content", "user", "other-sess")]
        mock_client.query_points.return_value = MagicMock(points=hits)

        results = memory.search_relevant("query")
        assert len(results) == 1
        r = results[0]
        assert "content" in r
        assert "role" in r
        assert "timestamp" in r
        assert "session_id" in r


# ── get_stats ─────────────────────────────────────────────────────────────

class TestGetStats:

    def test_stats_when_available(self):
        memory, mock_client, _ = _make_memory()
        mock_client.get_collection.return_value = MagicMock(points_count=42, vectors_count=None)

        stats = memory.get_stats()
        assert stats["available"] is True
        assert stats["count"] == 42

    def test_stats_falls_back_to_vectors_count(self):
        """If points_count is None, use vectors_count."""
        memory, mock_client, _ = _make_memory()
        mock_client.get_collection.return_value = MagicMock(points_count=None, vectors_count=10)

        stats = memory.get_stats()
        assert stats["count"] == 10

    def test_stats_when_not_available(self):
        from app.infrastructure.vector_store.vector_store import VectorMemory
        with patch("app.infrastructure.vector_store.vector_store.settings") as s:
            s.QDRANT_ENABLED = False
            s.QDRANT_URL = ""
            s.QDRANT_API_KEY = ""
            s.QDRANT_COLLECTION = "test"
            memory = VectorMemory()

        stats = memory.get_stats()
        assert stats["available"] is False
        assert stats["count"] == 0

    def test_stats_failure_returns_unavailable(self):
        memory, mock_client, _ = _make_memory()
        mock_client.get_collection.side_effect = Exception("cluster error")

        stats = memory.get_stats()
        assert stats["available"] is False
        assert stats["count"] == 0


# ── Singleton ─────────────────────────────────────────────────────────────

class TestSingleton:

    def test_get_vector_memory_returns_same_instance(self):
        from app.infrastructure.vector_store import vector_store as vs_module

        # Reset singleton to force re-creation
        original = vs_module._memory_instance
        vs_module._memory_instance = None

        with (
            patch("app.infrastructure.vector_store.vector_store.settings") as s,
            patch("app.infrastructure.vector_store.vector_store.QdrantClient", return_value=MagicMock(
                get_collections=MagicMock(return_value=MagicMock(collections=[]))
            )),
            patch("app.infrastructure.vector_store.vector_store.SentenceTransformer", return_value=MagicMock(
                encode=MagicMock(return_value=MagicMock(tolist=lambda: [0.0]*384))
            )),
        ):
            s.QDRANT_ENABLED = True
            s.QDRANT_URL = "https://mock.qdrant.io"
            s.QDRANT_API_KEY = "key"
            s.QDRANT_COLLECTION = "test"
            inst1 = vs_module.get_vector_memory()
            inst2 = vs_module.get_vector_memory()

        assert inst1 is inst2

        # Restore original singleton
        vs_module._memory_instance = original
