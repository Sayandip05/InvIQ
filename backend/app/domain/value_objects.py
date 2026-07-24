"""
Domain value objects for InvIQ inventory management.

These are immutable, behaviour-rich types that encode core business rules.
They have no knowledge of databases, HTTP, or any infrastructure concern.

─────────────────────────────────────────────────────────────
Key design decisions
─────────────────────────────────────────────────────────────
• StockStatus — canonical enum for the three health states.
  Single source of truth; SQL queries, services and UI all derive
  their labels from this enum.

• StockThresholds — central home for every business-rule constant.
  Previously the magic numbers < 3 (CRITICAL) and 3–7 (WARNING)
  were hardcoded directly inside the SQLAlchemy case() expression
  in queries.py.  They are now imported from here, so changing a
  threshold is a one-line edit in one place.

• ReorderPolicy — groups reorder-calculation parameters so callers
  cannot accidentally mix up positional arguments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# StockStatus
# ---------------------------------------------------------------------------

class StockStatus(str, Enum):
    """
    Three-tier stock health classification used throughout the system.

    Inherits from str so instances compare equal to plain string literals
    ('CRITICAL' == StockStatus.CRITICAL evaluates True) — this keeps
    existing code that uses string comparisons working without change.
    """

    CRITICAL = "CRITICAL"   # < CRITICAL_DAYS_THRESHOLD days remaining
    WARNING  = "WARNING"    # < WARNING_DAYS_THRESHOLD days remaining
    HEALTHY  = "HEALTHY"    # all other items

    # UI colour palette — avoids scattering hex values across the codebase
    @property
    def color(self) -> str:
        return _STATUS_COLORS[self]

    @classmethod
    def from_days(cls, days_remaining: float | None) -> "StockStatus":
        """
        Classify a stock item based on days-of-supply remaining.

        Args:
            days_remaining: Computed as current_stock / avg_daily_usage.
                            None means no usage data → treated as HEALTHY.

        Returns:
            The appropriate StockStatus variant.
        """
        if days_remaining is None:
            return cls.HEALTHY
        if days_remaining < StockThresholds.CRITICAL_DAYS:
            return cls.CRITICAL
        if days_remaining < StockThresholds.WARNING_DAYS:
            return cls.WARNING
        return cls.HEALTHY


_STATUS_COLORS: dict[StockStatus, str] = {
    StockStatus.CRITICAL: "#ef4444",
    StockStatus.WARNING:  "#f59e0b",
    StockStatus.HEALTHY:  "#10b981",
}

# Sentinel returned by SQL queries when avg_daily_usage == 0
# (infinite days remaining → treated as HEALTHY)
DAYS_REMAINING_INFINITE: int = 999


# ---------------------------------------------------------------------------
# StockThresholds
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StockThresholds:
    """
    Business-rule constants for stock health classification.

    All threshold values are defined here and referenced everywhere else.
    The SQL query in queries.py imports CRITICAL_DAYS and WARNING_DAYS
    directly so there is a single source of truth.

    Fields are class-level constants (not instance fields) so they can be
    used without instantiation: StockThresholds.CRITICAL_DAYS.
    """

    # Days-of-supply thresholds
    CRITICAL_DAYS: float = field(default=3.0)   # < 3 days  → CRITICAL
    WARNING_DAYS:  float = field(default=7.0)   # < 7 days  → WARNING

    # Usage window (days of transaction history used to compute avg usage)
    USAGE_WINDOW_DAYS: int = field(default=7)

    # Default safety multiplier used in reorder quantity calculation
    DEFAULT_SAFETY_FACTOR: float = field(default=2.0)

    def __init_subclass__(cls, **kwargs: object) -> None:  # pragma: no cover
        raise TypeError("StockThresholds is a singleton constants class; do not subclass it.")


# Expose as module-level names for convenient import
StockThresholds = StockThresholds()  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# ReorderPolicy
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ReorderPolicy:
    """
    Reorder policy parameters for a specific item / location combination.

    Groups the inputs to calculate_reorder_quantity() so callers cannot
    accidentally swap positional arguments (avg_daily_usage vs lead_time).

    Example:
        policy = ReorderPolicy(avg_daily_usage=10.0, lead_time_days=7)
        qty = policy.recommended_quantity(current_stock=50)
    """

    avg_daily_usage: float
    lead_time_days: int
    safety_factor: float = StockThresholds.DEFAULT_SAFETY_FACTOR  # type: ignore[union-attr]

    def recommended_quantity(self, current_stock: int) -> int:
        """
        Compute the recommended reorder quantity.

        Formula:  max(0, (daily_usage × lead_time × safety_factor) − current_stock)

        Returns 0 if avg_daily_usage ≤ 0 (no usage data) or if current
        stock already exceeds the target buffer.
        """
        if self.avg_daily_usage <= 0:
            return 0
        target = self.avg_daily_usage * self.lead_time_days * self.safety_factor
        return max(0, int(target - current_stock))
