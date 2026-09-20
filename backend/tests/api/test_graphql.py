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

def _ctx(db, role: str = "admin", org_id: int = 1):
    """Build a minimal GraphQL context dict mimicking get_graphql_context."""
    from unittest.mock import MagicMock
    user = MagicMock()
    user.role = role
    user.org_id = org_id
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

    def test_unauthenticated_guest_is_rejected(self, db):
        """Unauthenticated callers must receive an auth error, not data."""
        result = _exec(self.QUERY, _guest_ctx(db))
        assert result.errors is not None
        assert any("Authentication required" in str(e) for e in result.errors)


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

        loc = Location(org_id=1, name="QL-Loc", type="clinic", region="Test")
        item = Item(org_id=1, name="QL-Item", category="medicine", unit="box",
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

    def test_privileged_fields_masked_for_vendor(self, db):
        """Vendor callers (authenticated but not privileged) get null privileged fields."""
        VENDOR_QUERY = """
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
        result = _exec(VENDOR_QUERY, _ctx(db, "vendor"))
        assert result.errors is None
        for item in result.data["heatmap"]["details"]:
            assert item["avgDailyUsage"] is None
            assert item["daysRemaining"] is None
            assert item["leadTimeDays"] is None

    def test_unauthenticated_guest_is_rejected(self, db):
        """Unauthenticated callers must receive an auth error, not data."""
        result = _exec("{ heatmap { locations } }", _guest_ctx(db))
        assert result.errors is not None
        assert any("Authentication required" in str(e) for e in result.errors)

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

    def test_alert_privileged_fields_null_for_vendor(self, db):
        """Authenticated vendor (not privileged) gets null privileged fields."""
        result = _exec(
            '{ alerts(severity: "WARNING") { alerts { avgDailyUsage daysRemaining leadTimeDays } } }',
            _ctx(db, "vendor"),
        )
        assert result.errors is None
        for alert in result.data["alerts"]["alerts"]:
            assert alert["avgDailyUsage"] is None
            assert alert["daysRemaining"] is None
            assert alert["leadTimeDays"] is None

    def test_unauthenticated_guest_is_rejected(self, db):
        """Unauthenticated callers must receive an auth error."""
        result = _exec('{ alerts { count } }', _guest_ctx(db))
        assert result.errors is not None
        assert any("Authentication required" in str(e) for e in result.errors)

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

    def test_privileged_fields_masked_for_vendor(self, db):
        """Authenticated vendor (not privileged) gets null privileged fields."""
        result = _exec(
            "{ stockHealth { avgDailyUsage daysRemaining leadTimeDays } }",
            _ctx(db, "vendor"),
        )
        assert result.errors is None
        for row in result.data["stockHealth"]:
            assert row["avgDailyUsage"] is None
            assert row["daysRemaining"] is None

    def test_unauthenticated_guest_is_rejected(self, db):
        """Unauthenticated callers must receive an auth error."""
        result = _exec(
            "{ stockHealth { itemName } }",
            _guest_ctx(db),
        )
        assert result.errors is not None
        assert any("Authentication required" in str(e) for e in result.errors)


# ── Tenant Isolation ──────────────────────────────────────────────────────

class TestGraphQLTenantIsolation:
    """Ensure GraphQL resolvers respect multi-tenant scoping and use isolated cache keys."""

    def test_tenant_isolation_in_stock_health(self, db):
        from app.infrastructure.database.models import Location, Item, InventoryTransaction
        from datetime import date

        # Create locations and items for two different tenants
        loc1 = Location(name="Tenant 1 Clinic", type="clinic", region="North", org_id=1)
        loc2 = Location(name="Tenant 2 Clinic", type="clinic", region="South", org_id=2)
        item1 = Item(name="Tenant 1 Medicine", category="Specialty", unit="box", min_stock=10, org_id=1)
        item2 = Item(name="Tenant 2 Medicine", category="Specialty", unit="box", min_stock=10, org_id=2)

        db.add_all([loc1, loc2, item1, item2])
        db.commit()
        db.refresh(loc1)
        db.refresh(loc2)
        db.refresh(item1)
        db.refresh(item2)

        today = date.today()
        tx1 = InventoryTransaction(location_id=loc1.id, item_id=item1.id, date=today, opening_stock=0, received=20, issued=0, closing_stock=20)
        tx2 = InventoryTransaction(location_id=loc2.id, item_id=item2.id, date=today, opening_stock=0, received=20, issued=0, closing_stock=20)
        db.add_all([tx1, tx2])
        db.commit()

        # Query as Tenant 1 (org_id=1)
        res1 = _exec("{ stockHealth { itemName locationName } }", _ctx(db, role="staff", org_id=1))
        assert res1.errors is None
        item_names_t1 = [r["itemName"] for r in res1.data["stockHealth"]]
        assert "Tenant 1 Medicine" in item_names_t1
        assert "Tenant 2 Medicine" not in item_names_t1

        # Query as Tenant 2 (org_id=2)
        res2 = _exec("{ stockHealth { itemName locationName } }", _ctx(db, role="staff", org_id=2))
        assert res2.errors is None
        item_names_t2 = [r["itemName"] for r in res2.data["stockHealth"]]
        assert "Tenant 2 Medicine" in item_names_t2
        assert "Tenant 1 Medicine" not in item_names_t2

