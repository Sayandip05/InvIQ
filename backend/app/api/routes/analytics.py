"""
Analytics API routes — heatmap, alerts, summary, dashboard stats.

All GET endpoints are publicly accessible for Guest Demo Mode.
Authenticated users and guests receive identical data (no personalisation here).
Cache is invalidated when inventory data changes.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.infrastructure.database.connection import get_db
from app.application.analytics_service import AnalyticsService
from app.application.cache_service import cache_get, cache_set, ANALYTICS_TTL, DASHBOARD_TTL
from app.core.exceptions import ValidationError
from app.core.dependencies import get_optional_user
from app.core.rate_limiter import limiter
from app.infrastructure.database.models import User

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/heatmap")
@limiter.limit("30/minute")
def get_heatmap(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    cache_key = "analytics:heatmap"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    result = AnalyticsService.get_heatmap(db)
    cache_set(cache_key, result, ttl=ANALYTICS_TTL)
    return result


@router.get("/alerts")
@limiter.limit("30/minute")
def get_alerts(
    request: Request,
    severity: str = "CRITICAL",
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    if severity not in ["CRITICAL", "WARNING"]:
        raise ValidationError("Severity must be CRITICAL or WARNING")

    cache_key = f"analytics:alerts:{severity}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    result = AnalyticsService.get_alerts(db, severity)
    cache_set(cache_key, result, ttl=ANALYTICS_TTL)
    return result


@router.get("/summary")
@limiter.limit("30/minute")
def get_summary(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    cache_key = "analytics:summary"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    result = AnalyticsService.get_summary(db)
    cache_set(cache_key, result, ttl=ANALYTICS_TTL)
    return result


@router.get("/dashboard/stats")
@limiter.limit("30/minute")
def get_dashboard_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    cache_key = "analytics:dashboard_stats"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    result = AnalyticsService.get_dashboard_stats(db)
    cache_set(cache_key, result, ttl=DASHBOARD_TTL)
    return result
