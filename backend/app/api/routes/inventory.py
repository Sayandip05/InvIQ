"""
Inventory API routes.

Routes receive pre-configured services via FastAPI's Depends() system.
No direct DB queries here — everything goes through the service layer.
"""

from fastapi import APIRouter, Depends, Request
from app.core.rate_limiter import limiter

from app.core.dependencies import (
    get_inventory_service,
    get_inventory_repo,
    get_current_user,
    require_staff,
)
from app.core.exceptions import (
    NotFoundError,
    DuplicateError,
)
from app.application.inventory_service import InventoryService
from app.application.cache_service import cache_invalidate_pattern
from app.infrastructure.database.inventory_repo import InventoryRepository
from app.infrastructure.database.models import User
from app.api.schemas.inventory_schemas import (
    TransactionItem,
    SingleTransactionRequest,
    BulkTransactionRequest,
    CreateLocationRequest,
    CreateItemRequest,
    ResetDataRequest,
)

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("/locations")
def get_all_locations(
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(get_current_user),
):
    locations = repo.get_all_locations()
    return {
        "success": True,
        "data": [
            {"id": loc.id, "name": loc.name, "type": loc.type, "region": loc.region}
            for loc in locations
        ],
    }


@router.get("/items")
def get_all_items(
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(get_current_user),
):
    items = repo.get_all_items()
    return {
        "success": True,
        "data": [
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "unit": item.unit,
            }
            for item in items
        ],
    }


@router.get("/location/{location_id}/items")
def get_location_items(
    location_id: int,
    repo: InventoryRepository = Depends(get_inventory_repo),
    service: InventoryService = Depends(get_inventory_service),
    current_user: User = Depends(get_current_user),
):
    location = repo.get_location_by_id(location_id)
    if not location:
        raise NotFoundError("Location", location_id)

    items = service.get_location_items(location_id)
    return {
        "success": True,
        "location": {"id": location.id, "name": location.name},
        "data": items,
    }


@router.get("/stock/{location_id}/{item_id}")
def get_current_stock(
    location_id: int,
    item_id: int,
    service: InventoryService = Depends(get_inventory_service),
    current_user: User = Depends(get_current_user),
):
    stock = service.get_latest_stock(location_id, item_id)

    if stock is None:
        return {
            "success": True,
            "message": "No transaction history found",
            "current_stock": 0,
        }

    return {"success": True, "current_stock": stock}


@router.post("/locations")
@limiter.limit("20/minute")
def create_location(
    request: Request,
    body: CreateLocationRequest,
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(require_staff),
):
    existing = repo.get_location_by_name(body.name.strip())
    if existing:
        raise DuplicateError(f"Location '{body.name}' already exists")

    location = repo.create_location(
        name=body.name.strip(),
        type=body.type.strip().lower(),
        region=body.region.strip(),
        address=body.address.strip() if body.address else None,
    )

    return {
        "success": True,
        "message": "Location created successfully",
        "data": {
            "id": location.id,
            "name": location.name,
            "type": location.type,
            "region": location.region,
            "address": location.address,
        },
    }


@router.post("/items")
@limiter.limit("20/minute")
def create_item(
    request: Request,
    body: CreateItemRequest,
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(require_staff),
):
    existing = repo.get_item_by_name(body.name.strip())
    if existing:
        raise DuplicateError(f"Item '{body.name}' already exists")

    item = repo.create_item(
        name=body.name.strip(),
        category=body.category.strip().lower(),
        unit=body.unit.strip().lower(),
        lead_time_days=body.lead_time_days,
        min_stock=body.min_stock,
    )

    return {
        "success": True,
        "message": "Item created successfully",
        "data": {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "unit": item.unit,
            "lead_time_days": item.lead_time_days,
            "min_stock": item.min_stock,
        },
    }


@router.post("/reset-data")
@limiter.limit("3/minute")
def reset_inventory_data(
    request: Request,
    body: ResetDataRequest,
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(require_staff),
):
    if not body.confirm:
        from app.core.exceptions import ValidationError

        raise ValidationError("Set confirm=true to reset data")

    deleted_transactions = repo.delete_all_transactions()
    deleted_items = repo.delete_all_items()
    deleted_locations = repo.delete_all_locations()

    return {
        "success": True,
        "message": "All inventory data cleared",
        "data": {
            "deleted_transactions": deleted_transactions,
            "deleted_items": deleted_items,
            "deleted_locations": deleted_locations,
        },
    }


@router.post("/transaction")
@limiter.limit("30/minute")
def add_single_transaction(
    request: Request,
    body: SingleTransactionRequest,
    repo: InventoryRepository = Depends(get_inventory_repo),
    service: InventoryService = Depends(get_inventory_service),
    current_user: User = Depends(require_staff),
):
    if not repo.get_location_by_id(body.location_id):
        raise NotFoundError("Location", body.location_id)
    if not repo.get_item_by_id(body.item_id):
        raise NotFoundError("Item", body.item_id)

    result = service.add_transaction(
        location_id=body.location_id,
        item_id=body.item_id,
        transaction_date=body.date,
        received=body.received,
        issued=body.issued,
        notes=body.notes,
        entered_by=str(current_user.username),
    )
    cache_invalidate_pattern("analytics:*")
    return result


@router.post("/bulk-transaction")
@limiter.limit("10/minute")
def add_bulk_transactions(
    request: Request,
    body: BulkTransactionRequest,
    repo: InventoryRepository = Depends(get_inventory_repo),
    service: InventoryService = Depends(get_inventory_service),
    current_user: User = Depends(require_staff),
):
    if not repo.get_location_by_id(body.location_id):
        raise NotFoundError("Location", body.location_id)

    items_data = [
        {
            "item_id": item.item_id,
            "received": item.received,
            "issued": item.issued,
            "notes": item.notes,
        }
        for item in body.items
    ]

    result = service.bulk_add_transactions(
        location_id=body.location_id,
        transaction_date=body.date,
        items_data=items_data,
        entered_by=str(current_user.username),
    )
    cache_invalidate_pattern("analytics:*")
    return result


