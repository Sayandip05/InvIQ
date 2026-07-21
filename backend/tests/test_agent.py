"""
Agent tool tests — unit tests for LangChain @tool functions.

Tests that:
  - Core tools return the correct data structure
  - Pharmacy tools (get_near_expiry_items, get_cold_chain_items) are registered
    and return expected shapes when DB is not connected (graceful error handling)
"""

import pytest
from unittest.mock import patch, MagicMock
from app.application.agent_tools import (
    get_inventory_overview,
    get_critical_items,
    get_near_expiry_items,
    get_cold_chain_items,
)
from app.application.agent_service import INVENTORY_TOOLS


class TestAgentTools:
    """Test that agent tools return the expected data shapes."""

    def test_get_inventory_overview_structure(self):
        """get_inventory_overview should return a dict with expected keys."""
        result = get_inventory_overview.invoke({})
        assert isinstance(result, dict)
        # When DB is not set up in isolation, should return error or valid data
        assert "error" in result or "total_items" in result

    def test_get_critical_items_structure(self):
        """get_critical_items should return a list."""
        result = get_critical_items.invoke({})
        assert isinstance(result, list)

    def test_get_near_expiry_items_no_db(self):
        """get_near_expiry_items with no DB returns error list."""
        # Patch the thread-local DB getter to return None
        with patch("app.application.agent_tools._get_db", return_value=None):
            result = get_near_expiry_items.invoke({"days": 60})
        assert isinstance(result, list)
        assert len(result) == 1
        assert "error" in result[0]

    def test_get_cold_chain_items_no_db(self):
        """get_cold_chain_items with no DB returns error list."""
        with patch("app.application.agent_tools._get_db", return_value=None):
            result = get_cold_chain_items.invoke({"location": ""})
        assert isinstance(result, list)
        assert len(result) == 1
        assert "error" in result[0]

    def test_get_near_expiry_items_default_days(self):
        """get_near_expiry_items accepts default days=60."""
        with patch("app.application.agent_tools._get_db", return_value=None):
            result = get_near_expiry_items.invoke({})
        assert isinstance(result, list)

    def test_get_cold_chain_items_with_location_filter(self):
        """get_cold_chain_items accepts optional location filter."""
        with patch("app.application.agent_tools._get_db", return_value=None):
            result = get_cold_chain_items.invoke({"location": "Delhi"})
        assert isinstance(result, list)


class TestAgentToolRegistration:
    """Verify all 9 tools are registered in the agent service."""

    def test_all_tools_registered(self):
        """INVENTORY_TOOLS should contain exactly 9 tools."""
        assert len(INVENTORY_TOOLS) == 9

    def test_pharmacy_tools_in_registry(self):
        """Pharmacy-specific tools should be in the registry."""
        tool_names = [t.name for t in INVENTORY_TOOLS]
        assert "get_near_expiry_items" in tool_names
        assert "get_cold_chain_items" in tool_names

    def test_core_tools_in_registry(self):
        """Core inventory tools should all still be present."""
        tool_names = [t.name for t in INVENTORY_TOOLS]
        for expected in [
            "get_inventory_overview",
            "get_critical_items",
            "get_stock_health",
            "calculate_reorder_suggestions",
            "get_location_summary",
            "get_category_analysis",
            "get_consumption_trends",
        ]:
            assert expected in tool_names, f"Missing tool: {expected}"
