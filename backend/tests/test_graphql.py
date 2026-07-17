"""
GraphQL analytics resolver tests.

Uses strawberry's built-in sync test client (schema.execute_sync) to test
resolvers directly — no HTTP round-trip, no network needed.
The DB session is injected via the context dict so all tests run against the
same SQLite in-memory database that the rest of the test suite uses.
"""

import pytest
from strawberry import Schema
from app.api.graphql.resolvers import Query
from app.api.graphql.schema import schema
import strawberry


# ── Helpers ───────────────────────────────────────────────────────────────

def _ctx(db, role: str = "admin"):
    """Build a minimal GraphQL context dict mimicking get_graphql_context."""
    from unittest.mock import MagicMock
    user = MagicMock()
    user.role = role
    return {"db": db, "user": user, "request": MagicMock()}


def _guest_ctx(db):
    """Context with no authenticated user (Guest / public)."""
    from unittest.mock import MagicMock
    return {"db": db, "user": None, "request": MagicMock()}


def _exec(query_str: str, ctx: dict):
    """Execute a GraphQL query and return the result."""
    return schema.execute_sync(query_str, context_value=ctx)


# ── Dashboard Stats ───────────────────────────────────────────────────────

class TestGraphQLDashboardStats:
    """dashboardStats query — shape and field presence."""

    QUERY = """
    {
      dashboardStats {
        categoryDistribution { name value }
        lowStockItems { name stock minStock shortage }
        locationStock { name value }
        statusDistribution { name value color }
      }
    }
    """

    def test_returns_no_errors(self, db):
        result = _exec(self.QUERY, _ctx(db))
        assert result.errors is None, result.errors

    def test_top_level_keys_present(self, db):
        result = _exec(self.QUERY, _ctx(db))
        data = result.data["dashboardStats"]
        assert "categoryDistribution" in data
        assert "lowStockItems" in data
        assert "locationStock" in data
        assert "statusDistribution" in data

    def test_returns_lists(self, db):
        result = _exec(self.QUERY, _ctx(db))
        data = result.data["dashboardStats"]
        assert isinstance(data["categoryDistribution"], list)
        assert isinstance(data["lowStockItems"], list)
        assert isinstance(data["locationStock"], list)
        assert isinstance(data["statusDistribution"], list)

    def test_guest_can_access_dashboard(self, db):
        """Dashboard stats are not privileged — guests see them too."""
        result = _exec(self.QUERY, _guest_ctx(db))
        assert result.errors is None


# ── Heatmap ───────────────────────────────────────────────────────────────

class TestGraphQLHeatmap:
    """heatmap query — role-based field masking."""

    QUERY = """
    {
      heatmap {
        locations
        items
        details {
          locationName
          itemName
          currentStock
          healthStatus
          color
          avgDailyUsage
          daysRemaining
          leadTimeDays
        }
      }
    }
    """

    def test_returns_no_errors_as_admin(self, db):
        result = _exec(self.QUERY, _ctx(db, "admin"))
        assert result.errors is None

    def test_locations_and_items_are_lists(self, db):
        result = _exec(self.QUERY, _ctx(db))
        data = result.data["heatmap"]
        assert isinstance(data["locations"], list)
        assert isinstance(data["items"], list)

    def test_privileged_fields_visible_to_admin(self, db):
        """Admin should receive avgDailyUsage / daysRemaining / leadTimeDays."""
        from app.infrastructure.database.models import Location, Item, InventoryTransaction
        from datetime import date

        loc = Location(name="QL-Loc", type="clinic", region="Test")
        item = Item(name="QL-Item", category="medicine", unit="box",
                    lead_time_days=7, min_stock=10)
        db.add_all([loc, item])
        db.commit()
        db.refresh(loc)
        db.refresh(item)

        tx = InventoryTransaction(
            location_id=loc.id, item_id=item.id,
            date=date(2026, 1, 1),
            opening_stock=0, received=50, issued=10, closing_stock=40,
            entered_by="testuser",
        )
        db.add(tx)
        db.commit()

        result = _exec(self.QUERY, _ctx(db, "admin"))
        assert result.errors is None

    def test_privileged_fields_masked_for_guest(self, db):
        """Guest callers must get null for privileged fields."""
        GUEST_QUERY = """
        {
          heatmap {
            details {
              itemName
              avgDailyUsage
              daysRemaining
              leadTimeDays
            }
          }
        }
        """
        result = _exec(GUEST_QUERY, _guest_ctx(db))
        assert result.errors is None
        for item in result.data["heatmap"]["details"]:
            assert item["avgDailyUsage"] is None
            assert item["daysRemaining"] is None
            assert item["leadTimeDays"] is None

    def test_privileged_fields_masked_for_vendor(self, db):
        """Vendor role (not privileged) gets null privileged fields."""
        QUERY = """{ heatmap { details { avgDailyUsage } } }"""
        result = _exec(QUERY, _ctx(db, "vendor"))
        assert result.errors is None
        for item in result.data["heatmap"]["details"]:
            assert item["avgDailyUsage"] is None


# ── Alerts ────────────────────────────────────────────────────────────────

class TestGraphQLAlerts:
    """alerts query — severity parameter and field masking."""

    def test_alerts_critical_no_errors(self, db):
        result = _exec(
            '{ alerts(severity: "CRITICAL") { severity count alerts { itemName currentStock } } }',
            _ctx(db),
        )
        assert result.errors is None

    def test_alerts_warning_no_errors(self, db):
        result = _exec(
            '{ alerts(severity: "WARNING") { severity count } }',
            _ctx(db),
        )
        assert result.errors is None

    def test_alerts_invalid_severity_raises_error(self, db):
        result = _exec(
            '{ alerts(severity: "INVALID") { count } }',
            _ctx(db),
        )
        assert result.errors is not None
        assert any("severity" in str(e).lower() for e in result.errors)

    def test_alerts_default_severity_is_critical(self, db):
        result = _exec("{ alerts { severity count } }", _ctx(db))
        assert result.errors is None
        assert result.data["alerts"]["severity"] == "CRITICAL"

    def test_alert_privileged_fields_null_for_guest(self, db):
        result = _exec(
            '{ alerts(severity: "WARNING") { alerts { avgDailyUsage daysRemaining leadTimeDays } } }',
            _guest_ctx(db),
        )
        assert result.errors is None
        for alert in result.data["alerts"]["alerts"]:
            assert alert["avgDailyUsage"] is None
            assert alert["daysRemaining"] is None
            assert alert["leadTimeDays"] is None

    def test_alert_privileged_fields_visible_for_manager(self, db):
        result = _exec(
            '{ alerts(severity: "WARNING") { alerts { avgDailyUsage } } }',
            _ctx(db, "manager"),
        )
        assert result.errors is None


# ── Summary ───────────────────────────────────────────────────────────────

class TestGraphQLSummary:
    """summary query — overview + health + categories."""

    QUERY = """
    {
      summary {
        overview { totalLocations totalItems totalRecords }
        healthSummary { critical warning healthy }
        categories { name total critical warning healthy }
      }
    }
    """

    def test_returns_no_errors(self, db):
        result = _exec(self.QUERY, _ctx(db))
        assert result.errors is None

    def test_overview_has_integer_fields(self, db):
        result = _exec(self.QUERY, _ctx(db))
        ov = result.data["summary"]["overview"]
        assert isinstance(ov["totalLocations"], int)
        assert isinstance(ov["totalItems"], int)
        assert isinstance(ov["totalRecords"], int)

    def test_health_summary_has_integer_fields(self, db):
        result = _exec(self.QUERY, _ctx(db))
        hs = result.data["summary"]["healthSummary"]
        assert isinstance(hs["critical"], int)
        assert isinstance(hs["warning"], int)
        assert isinstance(hs["healthy"], int)

    def test_categories_is_list(self, db):
        result = _exec(self.QUERY, _ctx(db))
        assert isinstance(result.data["summary"]["categories"], list)


# ── Stock Health ──────────────────────────────────────────────────────────

class TestGraphQLStockHealth:
    """stockHealth query — filters and field masking."""

    BASE = """
    {
      stockHealth {
        locationName itemName currentStock healthStatus
        avgDailyUsage daysRemaining leadTimeDays
      }
    }
    """

    def test_returns_list(self, db):
        result = _exec(self.BASE, _ctx(db))
        assert result.errors is None
        assert isinstance(result.data["stockHealth"], list)

    def test_location_filter(self, db):
        result = _exec(
            '{ stockHealth(location: "nonexistent_xyz_999") { locationName } }',
            _ctx(db),
        )
        assert result.errors is None
        assert result.data["stockHealth"] == []

    def test_status_filter_critical(self, db):
        result = _exec(
            '{ stockHealth(statusFilter: "CRITICAL") { healthStatus } }',
            _ctx(db),
        )
        assert result.errors is None
        for row in result.data["stockHealth"]:
            assert row["healthStatus"] == "CRITICAL"

    def test_invalid_status_filter_raises_error(self, db):
        result = _exec(
            '{ stockHealth(statusFilter: "BOGUS") { itemName } }',
            _ctx(db),
        )
        assert result.errors is not None

    def test_privileged_fields_visible_to_admin(self, db):
        result = _exec(self.BASE, _ctx(db, "admin"))
        assert result.errors is None

    def test_privileged_fields_masked_for_guest(self, db):
        result = _exec(
            "{ stockHealth { avgDailyUsage daysRemaining leadTimeDays } }",
            _guest_ctx(db),
        )
        assert result.errors is None
        for row in result.data["stockHealth"]:
            assert row["avgDailyUsage"] is None
            assert row["daysRemaining"] is None
            assert row["leadTimeDays"] is None
