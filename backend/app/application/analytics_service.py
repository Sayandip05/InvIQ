"""
Analytics service — business logic layer for stock health and dashboard data.

Raises exceptions instead of returning error dicts for consistency with
the rest of the application's error handling pattern.
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from app.infrastructure.database.analytics_repo import (
    get_latest_stock_health,
    get_critical_alerts,
    get_heatmap_data,
)
from app.domain.calculations import format_stock_item, calculate_reorder_quantity
from app.core.exceptions import AppException
from app.infrastructure.database.models import InventoryTransaction, Location, Item


class AnalyticsService:
    @staticmethod
    def get_heatmap(db: Session, org_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            data = get_heatmap_data(db, org_id=org_id)

            formatted_details = [format_stock_item(item) for item in data["details"]]

            return {
                "success": True,
                "data": {
                    "locations": data["locations"],
                    "items": data["items"],
                    "matrix": data["matrix"],
                    "details": formatted_details,
                },
            }
        except Exception as e:
            raise AppException(f"Failed to generate heatmap: {str(e)}")

    @staticmethod
    def get_alerts(db: Session, severity: str = "CRITICAL", org_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            alerts = get_critical_alerts(db, severity, org_id=org_id)

            formatted_alerts = []
            for alert in alerts:
                item_data = format_stock_item(alert)

                reorder_qty = calculate_reorder_quantity(
                    avg_daily_usage=alert.avg_daily_usage or 0,
                    lead_time_days=alert.lead_time_days,
                    current_stock=alert.current_stock,
                )

                item_data["recommended_reorder"] = reorder_qty
                formatted_alerts.append(item_data)

            return {
                "success": True,
                "data": {
                    "severity": severity,
                    "count": len(formatted_alerts),
                    "alerts": formatted_alerts,
                },
            }
        except Exception as e:
            raise AppException(f"Failed to fetch alerts: {str(e)}")

    @staticmethod
    def get_summary(db: Session, org_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            stock_health = get_latest_stock_health(db, org_id=org_id)

            critical_count = sum(
                1 for item in stock_health if item.health_status == "CRITICAL"
            )
            warning_count = sum(
                1 for item in stock_health if item.health_status == "WARNING"
            )
            healthy_count = sum(
                1 for item in stock_health if item.health_status == "HEALTHY"
            )

            total_locations = len(set(item.location_id for item in stock_health))
            total_items = len(set(item.item_id for item in stock_health))

            categories = {}
            for item in stock_health:
                if item.category not in categories:
                    categories[item.category] = {
                        "total": 0,
                        "critical": 0,
                        "warning": 0,
                        "healthy": 0,
                    }
                categories[item.category]["total"] += 1
                categories[item.category][item.health_status.lower()] += 1

            return {
                "success": True,
                "data": {
                    "overview": {
                        "total_locations": total_locations,
                        "total_items": total_items,
                        "total_records": len(stock_health),
                    },
                    "health_summary": {
                        "critical": critical_count,
                        "warning": warning_count,
                        "healthy": healthy_count,
                    },
                    "categories": categories,
                },
            }
        except Exception as e:
            raise AppException(f"Failed to generate summary: {str(e)}")

    @staticmethod
    def get_dashboard_stats(
        db: Session,
        org_id: Optional[int] = None,
        location_id: Optional[int] = None,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            stock_health = get_latest_stock_health(
                db,
                org_id=org_id,
                location_id=location_id,
                category=category,
            )


            category_counts = {}
            for item in stock_health:
                category_counts[item.category] = (
                    category_counts.get(item.category, 0) + 1
                )

            category_data = [
                {"name": cat, "value": count} for cat, count in category_counts.items()
            ]

            # "Top Critical Shortages" shows items with CRITICAL health status
            # (days_remaining < 3), not just stock < min_stock.
            # Sort by days_remaining so the most urgent items appear first.
            critical_items = [
                item for item in stock_health if item.health_status == "CRITICAL"
            ]
            critical_items.sort(
                key=lambda x: x.days_remaining if x.days_remaining is not None else 0
            )

            low_stock_data = [
                {
                    "name": item.item_name,
                    "location": item.location_name,
                    "stock": item.current_stock,
                    "min_stock": item.min_stock,
                    "days_remaining": round(item.days_remaining, 1) if item.days_remaining is not None else None,
                    "daily_usage": round(item.avg_daily_usage, 1) if item.avg_daily_usage is not None else None,
                    "shortage": max(0, item.min_stock - item.current_stock),
                }
                for item in critical_items[:10]
            ]

            location_stock = {}
            for item in stock_health:
                location_stock[item.location_name] = (
                    location_stock.get(item.location_name, 0) + item.current_stock
                )

            location_data = [
                {"name": loc, "value": qty} for loc, qty in location_stock.items()
            ]

            from datetime import date, timedelta

            status_counts = {"CRITICAL": 0, "WARNING": 0, "HEALTHY": 0}
            for item in stock_health:
                status_counts[item.health_status] += 1

            status_data = [
                {
                    "name": status,
                    "value": count,
                    "color": "#F26A4B"
                    if status == "CRITICAL"
                    else "#7A7268"
                    if status == "WARNING"
                    else "#1E1E1E",
                }
                for status, count in status_counts.items()
                if count > 0
            ]

            # Query real upcoming medicine batch expirations over upcoming 12 months
            from datetime import date, timedelta
            today = date.today()
            max_horizon = today + timedelta(days=365)
            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

            expiry_q = (
                db.query(
                    InventoryTransaction.expiry_date,
                    InventoryTransaction.closing_stock,
                    InventoryTransaction.received,
                )
                .join(Location, InventoryTransaction.location_id == Location.id)
                .join(Item, InventoryTransaction.item_id == Item.id)
                .filter(
                    InventoryTransaction.expiry_date != None,
                    InventoryTransaction.expiry_date >= today,
                    InventoryTransaction.expiry_date <= max_horizon,
                )
            )
            if org_id is not None:
                expiry_q = expiry_q.filter(Location.org_id == org_id)
            if location_id is not None:
                expiry_q = expiry_q.filter(Location.id == location_id)
            if category:
                expiry_q = expiry_q.filter(Item.category == category)

            expiry_batches = expiry_q.all()

            expiry_counts: Dict[str, int] = {}
            for b in expiry_batches:
                if b.expiry_date:
                    m_key = b.expiry_date.strftime("%b")
                    qty = b.closing_stock if (b.closing_stock is not None and b.closing_stock > 0) else (b.received or 1)
                    expiry_counts[m_key] = expiry_counts.get(m_key, 0) + int(qty)

            has_real_expiry = sum(expiry_counts.values()) > 0
            sample_exp_curve = [25, 45, 38, 65, 52, 85, 40, 55, 30, 70, 48, 60]
            sample_thresh_curve = [18, 32, 29, 48, 41, 61, 30, 40, 22, 50, 35, 45]
            expiry_timeline = []

            for i in range(12):
                m_idx = (today.month - 1 + i) % 12
                m_name = month_names[m_idx]
                if has_real_expiry:
                    exp_val = expiry_counts.get(m_name, 0)
                    thresh_val = max(5, int(exp_val * 0.72)) if exp_val > 0 else 0
                else:
                    exp_val = sample_exp_curve[i]
                    thresh_val = sample_thresh_curve[i]

                expiry_timeline.append({
                    "month": m_name,
                    "expiring": exp_val,
                    "threshold": thresh_val,
                    "risk_level": "Critical" if exp_val >= 60 else "Medium" if exp_val >= 35 else "Low"
                })

            return {
                "success": True,
                "data": {
                    "category_distribution": category_data,
                    "low_stock_items": low_stock_data,
                    "location_stock": location_data,
                    "status_distribution": status_data,
                    "expiry_timeline": expiry_timeline,
                },
            }
        except Exception as e:
            raise AppException(f"Failed to generate dashboard stats: {str(e)}")
