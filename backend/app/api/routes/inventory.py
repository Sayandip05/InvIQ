"""
Inventory API routes.

Routes receive pre-configured services via FastAPI's Depends() system.
No direct DB queries here — everything goes through the service layer.

All routes are strictly org-scoped to the caller's organization.
"""

from fastapi import APIRouter, Depends, Request
from typing import Optional
from app.core.rate_limiter import limiter
from app.core.dependencies import (
    get_inventory_service,
    get_inventory_repo,
    get_current_user,
    require_staff,
    require_admin,
    get_caller_org_id,
)

from app.core.exceptions import (
    NotFoundError,
    DuplicateError,
    AuthorizationError,
    ValidationError,
)

from app.application.inventory_service import InventoryService
from app.application.cache_service import (
    cache_get,
    cache_set,
    cache_invalidate_pattern,
)
from app.infrastructure.database.inventory_repo import InventoryRepository
from app.infrastructure.database.models import User, ItemPackaging
from app.api.schemas.inventory_schemas import (
    TransactionItem,
    SingleTransactionRequest,
    BulkTransactionRequest,
    CreateLocationRequest,
    UpdateLocationRequest,
    CreateItemRequest,
    UpdateItemRequest,
    ResetDataRequest,
    ScanDispenseRequest,
    CreateItemPackagingRequest,
    UpdateItemPackagingRequest,
)



router = APIRouter(prefix="/inventory", tags=["Inventory"])


def _caller_org_id(user: User) -> Optional[int]:
    """Return org_id for tenant-scoped operations using central dependency rule."""
    return get_caller_org_id(user)


def _has_location_access(user: User, target_location_id: int) -> bool:
    """Check if staff or vendor user is permitted to access/mutate this location."""
    raw = getattr(user, "location_ids", None)
    if not raw:
        return True  # None or empty means unrestricted/all branches in user's org
    if isinstance(raw, str):
        import json
        try:
            raw = json.loads(raw)
        except Exception:
            raw = [raw]
    if isinstance(raw, (list, set, tuple)):
        allowed_ids = set()
        for item in raw:
            try:
                allowed_ids.add(int(item))
            except (ValueError, TypeError):
                pass
        if not allowed_ids:
            return True
        return target_location_id in allowed_ids
    return True



@router.get("/locations")
def get_all_locations(
    limit: int = 50,
    offset: int = 0,
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(get_current_user),
):
    """List locations for the caller's organization with 5-minute tiered cache."""
    org_id = _caller_org_id(current_user)
    cache_key = f"ref:locations:{org_id}:{limit}:{offset}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    locations = repo.get_all_locations(limit=limit, offset=offset, org_id=org_id)
    res = {
        "success": True,
        "data": [
            {"id": loc.id, "name": loc.name, "type": loc.type, "region": loc.region}
            for loc in locations
        ],
    }
    cache_set(cache_key, res, ttl=300)
    if limit == 50 and offset == 0:
        cache_set(f"ref:locations:{org_id}", res, ttl=300)
        cache_set("ref:locations", res, ttl=300)
    return res


@router.get("/items")
def get_all_items(
    limit: int = 50,
    offset: int = 0,
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(get_current_user),
):
    """List items for the caller's organization with 5-minute tiered cache."""
    org_id = _caller_org_id(current_user)
    cache_key = f"ref:items:{org_id}:{limit}:{offset}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    items = repo.get_all_items(limit=limit, offset=offset, org_id=org_id)
    res = {
        "success": True,
        "data": [
            {
                "id": it.id,
                "name": it.name,
                "category": it.category,
                "storage_temp": it.storage_temp,
                "strength": it.strength,
                "unit": it.unit,
                "min_stock": it.min_stock,
                "barcode": it.barcode,
            }
            for it in items
        ],
    }
    cache_set(cache_key, res, ttl=300)
    if limit == 50 and offset == 0:
        cache_set(f"ref:items:{org_id}", res, ttl=300)
        cache_set("ref:items", res, ttl=300)
    return res




@router.get("/location/{location_id}/items")
def get_location_items(
    location_id: int,
    repo: InventoryRepository = Depends(get_inventory_repo),
    service: InventoryService = Depends(get_inventory_service),
    current_user: User = Depends(get_current_user),
):
    """Get location item stock list with a 5-minute Redis cache (org-scoped)."""
    org_id = _caller_org_id(current_user)
    cache_key = f"ref:location_items:{org_id}:{location_id}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    location = repo.get_location_by_id(location_id, org_id=org_id)
    if not location:
        raise NotFoundError("Location", location_id)

    items = service.get_location_items(location_id, org_id=org_id)
    res = {
        "success": True,
        "location": {"id": location.id, "name": location.name},
        "data": items,
    }
    cache_set(cache_key, res, ttl=300)
    return res


@router.get("/stock/{location_id}/{item_id}")
def get_current_stock(
    location_id: int,
    item_id: int,
    repo: InventoryRepository = Depends(get_inventory_repo),
    service: InventoryService = Depends(get_inventory_service),
    current_user: User = Depends(get_current_user),
):
    org_id = _caller_org_id(current_user)
    # Ownership check
    if not repo.get_location_by_id(location_id, org_id=org_id):
        raise NotFoundError("Location", location_id)
    if not repo.get_item_by_id(item_id, org_id=org_id):
        raise NotFoundError("Item", item_id)

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
    org_id = _caller_org_id(current_user)
    existing = repo.get_location_by_name(body.name.strip(), org_id=org_id)
    if existing:
        raise DuplicateError(f"Location '{body.name}' already exists")

    location = repo.create_location(
        name=body.name.strip(),
        type=body.type.strip().lower(),
        region=body.region.strip(),
        address=body.address.strip() if body.address else None,
        org_id=org_id,
    )

    cache_invalidate_pattern("ref:*")

    return {
        "success": True,
        "message": "Location created successfully",
        "data": {
            "id": location.id,
            "name": location.name,
            "type": location.type,
            "region": location.region,
            "address": location.address,
            "is_active": location.is_active,
        },
    }


@router.put("/locations/{location_id}")
@limiter.limit("20/minute")
def update_location(
    location_id: int,
    request: Request,
    body: UpdateLocationRequest,
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(require_admin),
):
    """Update or rename an organization branch/location."""
    org_id = _caller_org_id(current_user)
    location = repo.get_location_by_id(location_id, org_id=org_id)
    if not location:
        raise NotFoundError("Location", location_id)

    update_fields = {}
    if body.name is not None:
        new_name = body.name.strip()
        existing = repo.get_location_by_name(new_name, org_id=org_id)
        if existing and existing.id != location_id:
            raise DuplicateError(f"A branch named '{new_name}' already exists in your organization")
        update_fields["name"] = new_name
    if body.type is not None:
        update_fields["type"] = body.type.strip().lower()
    if body.region is not None:
        update_fields["region"] = body.region.strip()
    if body.address is not None:
        update_fields["address"] = body.address.strip()
    if body.phone is not None:
        update_fields["phone"] = body.phone.strip()
    if body.pincode is not None:
        update_fields["pincode"] = body.pincode.strip()
    if body.radius_meters is not None:
        update_fields["radius_meters"] = body.radius_meters
    if body.is_active is not None:
        update_fields["is_active"] = body.is_active

    updated = repo.update_location(location, **update_fields)
    cache_invalidate_pattern("ref:*")

    return {
        "success": True,
        "message": f"Branch '{updated.name}' updated successfully",
        "data": {
            "id": updated.id,
            "name": updated.name,
            "type": updated.type,
            "region": updated.region,
            "address": updated.address,
            "phone": updated.phone,
            "pincode": updated.pincode,
            "radius_meters": updated.radius_meters,
            "is_active": updated.is_active,
        },
    }


@router.delete("/locations/{location_id}")
@limiter.limit("20/minute")
def delete_or_archive_location(
    location_id: int,
    request: Request,
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(require_admin),
):
    """
    Remove or safely archive a branch.
    If historical transactions or stock exist, the branch is safely archived (is_active=False).
    If no transactions exist, it is permanently deleted.
    """
    org_id = _caller_org_id(current_user)
    location = repo.get_location_by_id(location_id, org_id=org_id)
    if not location:
        raise NotFoundError("Location", location_id)

    has_history = repo.has_location_transactions(location_id)
    if has_history:
        # Safe archive
        repo.update_location(location, is_active=False)
        cache_invalidate_pattern("ref:*")
        return {
            "success": True,
            "action": "archived",
            "message": f"Branch '{location.name}' has been safely archived because historical stock records exist.",
            "data": {"id": location.id, "name": location.name, "is_active": False},
        }
    else:
        # Safe hard delete
        loc_name = location.name
        loc_id = location.id
        repo.delete_location(location)
        cache_invalidate_pattern("ref:*")
        return {
            "success": True,
            "action": "deleted",
            "message": f"Branch '{loc_name}' has been permanently deleted.",
            "data": {"id": loc_id, "name": loc_name},
        }


@router.patch("/locations/{location_id}/toggle-active")
@limiter.limit("20/minute")
def toggle_location_active(
    location_id: int,
    request: Request,
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(require_admin),
):
    """Toggle a branch between active and inactive/archived status."""
    org_id = _caller_org_id(current_user)
    location = repo.get_location_by_id(location_id, org_id=org_id)
    if not location:
        raise NotFoundError("Location", location_id)

    new_status = not bool(location.is_active)
    updated = repo.update_location(location, is_active=new_status)
    cache_invalidate_pattern("ref:*")

    status_str = "activated" if new_status else "deactivated/archived"
    return {
        "success": True,
        "message": f"Branch '{updated.name}' is now {status_str}.",
        "data": {"id": updated.id, "name": updated.name, "is_active": updated.is_active},
    }



@router.post("/items")
@limiter.limit("20/minute")
def create_item(
    request: Request,
    body: CreateItemRequest,
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(require_staff),
):
    org_id = _caller_org_id(current_user)
    existing = repo.get_item_by_name(body.name.strip(), org_id=org_id)
    if existing:
        raise DuplicateError(f"Item '{body.name}' already exists")

    item = repo.create_item(
        name=body.name.strip(),
        category=body.category.strip().lower(),
        unit=body.unit.strip().lower(),
        barcode=body.barcode.strip() if body.barcode else None,
        strength=body.strength.strip() if body.strength else None,
        mrp=body.mrp or 0.0,
        purchase_rate=body.purchase_rate or 0.0,
        lead_time_days=body.lead_time_days,
        min_stock=body.min_stock,
        storage_temp=body.storage_temp or "ambient",
        org_id=org_id,
    )

    created_packagings = []
    if body.packagings:
        for p in body.packagings:
            pkg = repo.create_packaging(
                item_id=item.id,
                org_id=org_id,
                unit_name=p.unit_name.strip().lower(),
                multiplier=p.multiplier,
                barcode=p.barcode.strip() if p.barcode else None,
                mrp=p.mrp,
                purchase_rate=p.purchase_rate,
                is_default_dispense=p.is_default_dispense,
                is_default_purchase=p.is_default_purchase,
            )
            created_packagings.append({
                "id": pkg.id,
                "unit_name": pkg.unit_name,
                "multiplier": pkg.multiplier,
                "barcode": pkg.barcode,
                "mrp": pkg.mrp,
                "purchase_rate": pkg.purchase_rate,
                "is_default_dispense": pkg.is_default_dispense,
                "is_default_purchase": pkg.is_default_purchase,
            })

    cache_invalidate_pattern("ref:*")

    return {
        "success": True,
        "message": "Item created successfully",
        "data": {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "unit": item.unit,
            "barcode": item.barcode,
            "strength": item.strength,
            "mrp": item.mrp,
            "purchase_rate": item.purchase_rate,
            "lead_time_days": item.lead_time_days,
            "min_stock": item.min_stock,
            "storage_temp": item.storage_temp,
            "packagings": created_packagings,
        },
    }


# ── Item Packaging / Multi-UOM Endpoints ─────────────────────────────────────

@router.get("/items/{item_id}/packagings")
def get_item_packagings(
    item_id: int,
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(get_current_user),
):
    """List all packaging tiers defined for a medicine."""
    org_id = _caller_org_id(current_user)
    item = repo.get_item_by_id(item_id, org_id=org_id)
    if not item:
        raise NotFoundError("Item", item_id)

    pkgs = repo.get_item_packagings(item_id, org_id=org_id)
    return {
        "success": True,
        "base_unit": item.unit,
        "base_mrp": item.mrp,
        "data": [
            {
                "id": p.id,
                "item_id": p.item_id,
                "unit_name": p.unit_name,
                "multiplier": p.multiplier,
                "barcode": p.barcode,
                "mrp": p.mrp if p.mrp is not None else round(float(item.mrp or 0.0) * p.multiplier, 2),
                "purchase_rate": p.purchase_rate if p.purchase_rate is not None else round(float(item.purchase_rate or 0.0) * p.multiplier, 2),
                "is_default_dispense": p.is_default_dispense,
                "is_default_purchase": p.is_default_purchase,
            }
            for p in pkgs
        ],
    }


@router.post("/items/{item_id}/packagings")
@limiter.limit("30/minute")
def add_item_packaging(
    request: Request,
    item_id: int,
    body: CreateItemPackagingRequest,
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(require_staff),
):
    """Add a packaging tier (e.g. strip = 10 tabs, box = 100 tabs) to a medicine."""
    org_id = _caller_org_id(current_user)
    item = repo.get_item_by_id(item_id, org_id=org_id)
    if not item:
        raise NotFoundError("Item", item_id)

    pkg = repo.create_packaging(
        item_id=item.id,
        org_id=org_id,
        unit_name=body.unit_name.strip().lower(),
        multiplier=body.multiplier,
        barcode=body.barcode.strip() if body.barcode else None,
        mrp=body.mrp,
        purchase_rate=body.purchase_rate,
        is_default_dispense=body.is_default_dispense,
        is_default_purchase=body.is_default_purchase,
    )
    cache_invalidate_pattern("ref:*")

    return {
        "success": True,
        "message": f"Packaging unit '{pkg.unit_name}' added successfully",
        "data": {
            "id": pkg.id,
            "item_id": pkg.item_id,
            "unit_name": pkg.unit_name,
            "multiplier": pkg.multiplier,
            "barcode": pkg.barcode,
            "mrp": pkg.mrp if pkg.mrp is not None else round(float(item.mrp or 0.0) * pkg.multiplier, 2),
            "purchase_rate": pkg.purchase_rate,
            "is_default_dispense": pkg.is_default_dispense,
            "is_default_purchase": pkg.is_default_purchase,
        },
    }


@router.put("/items/{item_id}/packagings/{pkg_id}")
@limiter.limit("30/minute")
def update_item_packaging(
    request: Request,
    item_id: int,
    pkg_id: int,
    body: UpdateItemPackagingRequest,
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(require_staff),
):
    """Update packaging tier properties (barcode, multiplier, pricing)."""
    org_id = _caller_org_id(current_user)
    pkg = repo.get_packaging_by_id(pkg_id, org_id=org_id)
    if not pkg or pkg.item_id != item_id:
        raise NotFoundError("ItemPackaging", pkg_id)

    update_kwargs = {}
    if body.unit_name is not None:
        update_kwargs["unit_name"] = body.unit_name.strip().lower()
    if body.multiplier is not None:
        update_kwargs["multiplier"] = body.multiplier
    if body.barcode is not None:
        update_kwargs["barcode"] = body.barcode.strip() if body.barcode else None
    if body.mrp is not None:
        update_kwargs["mrp"] = body.mrp
    if body.purchase_rate is not None:
        update_kwargs["purchase_rate"] = body.purchase_rate
    if body.is_default_dispense is not None:
        update_kwargs["is_default_dispense"] = body.is_default_dispense
    if body.is_default_purchase is not None:
        update_kwargs["is_default_purchase"] = body.is_default_purchase

    updated = repo.update_packaging(pkg, **update_kwargs)
    cache_invalidate_pattern("ref:*")

    return {
        "success": True,
        "message": f"Packaging unit '{updated.unit_name}' updated successfully",
        "data": {
            "id": updated.id,
            "item_id": updated.item_id,
            "unit_name": updated.unit_name,
            "multiplier": updated.multiplier,
            "barcode": updated.barcode,
            "mrp": updated.mrp,
            "purchase_rate": updated.purchase_rate,
            "is_default_dispense": updated.is_default_dispense,
            "is_default_purchase": updated.is_default_purchase,
        },
    }


@router.delete("/items/{item_id}/packagings/{pkg_id}")
@limiter.limit("30/minute")
def delete_item_packaging(
    request: Request,
    item_id: int,
    pkg_id: int,
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(require_staff),
):
    """Delete a packaging tier from an item."""
    org_id = _caller_org_id(current_user)
    pkg = repo.get_packaging_by_id(pkg_id, org_id=org_id)
    if not pkg or pkg.item_id != item_id:
        raise NotFoundError("ItemPackaging", pkg_id)

    unit_name = pkg.unit_name
    repo.delete_packaging(pkg)
    cache_invalidate_pattern("ref:*")

    return {
        "success": True,
        "message": f"Packaging unit '{unit_name}' deleted successfully",
    }


@router.get("/items/barcode/{barcode}")
@limiter.limit("60/minute")
def get_item_by_barcode(
    request: Request,
    barcode: str,
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(require_staff),
):
    """Look up a medicine/item by its barcode or packaging barcode for the caller's organization."""
    org_id = _caller_org_id(current_user)
    item = None
    matched_pkg = None

    # Check packaging barcode first
    pkg_obj = repo.get_packaging_by_barcode(barcode, org_id=org_id)
    if pkg_obj:
        matched_pkg = pkg_obj
        item = pkg_obj.item

    if not item:
        item = repo.get_item_by_barcode(barcode, org_id=org_id)

    if not item:
        raise NotFoundError("Item", barcode)

    packagings = repo.get_item_packagings(item.id, org_id=org_id)
    return {
        "success": True,
        "data": {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "unit": item.unit,
            "base_unit": item.unit,
            "barcode": item.barcode,
            "matched_packaging": {
                "id": matched_pkg.id,
                "unit_name": matched_pkg.unit_name,
                "multiplier": matched_pkg.multiplier,
                "barcode": matched_pkg.barcode,
                "mrp": matched_pkg.mrp if matched_pkg.mrp is not None else round(float(item.mrp or 0.0) * matched_pkg.multiplier, 2),
            } if matched_pkg else None,
            "strength": item.strength,
            "mrp": item.mrp,
            "purchase_rate": item.purchase_rate,
            "lead_time_days": item.lead_time_days,
            "min_stock": item.min_stock,
            "storage_temp": item.storage_temp,
            "packagings": [
                {
                    "id": p.id,
                    "unit_name": p.unit_name,
                    "multiplier": p.multiplier,
                    "barcode": p.barcode,
                    "mrp": p.mrp if p.mrp is not None else round(float(item.mrp or 0.0) * p.multiplier, 2),
                    "purchase_rate": p.purchase_rate,
                    "is_default_dispense": p.is_default_dispense,
                    "is_default_purchase": p.is_default_purchase,
                }
                for p in packagings
            ],
        },
    }


@router.get("/items/{item_id}")
@limiter.limit("60/minute")
def get_item_detail(
    request: Request,
    item_id: int,
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(require_staff),
):
    """Get single item detail by ID."""
    org_id = _caller_org_id(current_user)
    item = repo.get_item_by_id(item_id, org_id=org_id)
    if not item:
        raise NotFoundError("Item", item_id)

    return {
        "success": True,
        "data": {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "unit": item.unit,
            "barcode": item.barcode,
            "strength": item.strength,
            "mrp": item.mrp,
            "purchase_rate": item.purchase_rate,
            "lead_time_days": item.lead_time_days,
            "min_stock": item.min_stock,
            "storage_temp": item.storage_temp,
        },
    }


@router.put("/items/{item_id}")
@limiter.limit("30/minute")
def update_item(
    request: Request,
    item_id: int,
    body: UpdateItemRequest,
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(require_admin),
):
    """Update medicine/item master metadata."""
    org_id = _caller_org_id(current_user)
    item = repo.get_item_by_id(item_id, org_id=org_id)
    if not item:
        raise NotFoundError("Item", item_id)

    update_kwargs = {}
    if body.name is not None:
        update_kwargs["name"] = body.name.strip()
    if body.category is not None:
        update_kwargs["category"] = body.category.strip().lower()
    if body.unit is not None:
        update_kwargs["unit"] = body.unit.strip().lower()
    if body.barcode is not None:
        update_kwargs["barcode"] = body.barcode.strip() if body.barcode else None
    if body.strength is not None:
        update_kwargs["strength"] = body.strength.strip() if body.strength else None
    if body.mrp is not None:
        update_kwargs["mrp"] = body.mrp
    if body.purchase_rate is not None:
        update_kwargs["purchase_rate"] = body.purchase_rate
    if body.lead_time_days is not None:
        update_kwargs["lead_time_days"] = body.lead_time_days
    if body.min_stock is not None:
        update_kwargs["min_stock"] = body.min_stock
    if body.storage_temp is not None:
        update_kwargs["storage_temp"] = body.storage_temp

    updated = repo.update_item(item, **update_kwargs)
    cache_invalidate_pattern("ref:*")
    cache_invalidate_pattern("analytics:*")

    return {
        "success": True,
        "message": f"Item '{updated.name}' updated successfully",
        "data": {
            "id": updated.id,
            "name": updated.name,
            "category": updated.category,
            "unit": updated.unit,
            "barcode": updated.barcode,
            "strength": updated.strength,
            "mrp": updated.mrp,
            "purchase_rate": updated.purchase_rate,
            "lead_time_days": updated.lead_time_days,
            "min_stock": updated.min_stock,
            "storage_temp": updated.storage_temp,
        },
    }


@router.delete("/items/{item_id}")
@limiter.limit("20/minute")
def delete_item(
    request: Request,
    item_id: int,
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(require_admin),
):
    """
    Remove an item.
    Safe deletion rule: Rejects deletion if historical transactions exist.
    """
    org_id = _caller_org_id(current_user)
    item = repo.get_item_by_id(item_id, org_id=org_id)
    if not item:
        raise NotFoundError("Item", item_id)

    if repo.has_item_transactions(item_id):
        raise ValidationError(
            f"Cannot delete item '{item.name}' because historical inventory transactions exist. "
            "Archive or update the item instead."
        )

    deleted_name = item.name
    repo.delete_item(item)
    cache_invalidate_pattern("ref:*")
    cache_invalidate_pattern("analytics:*")

    return {
        "success": True,
        "message": f"Item '{deleted_name}' deleted successfully",
    }



@router.post("/reset-data")
@limiter.limit("3/minute")
def reset_inventory_data(
    request: Request,
    body: ResetDataRequest,
    repo: InventoryRepository = Depends(get_inventory_repo),
    current_user: User = Depends(require_admin),
):
    """Delete inventory data for the caller's organization only. Strictly org-scoped."""
    if not body.confirm:
        from app.core.exceptions import ValidationError
        raise ValidationError("Set confirm=true to reset data")

    org_id = _caller_org_id(current_user)

    deleted_transactions = repo.delete_all_transactions(org_id=org_id)
    deleted_items = repo.delete_all_items(org_id=org_id)
    deleted_locations = repo.delete_all_locations(org_id=org_id)

    cache_invalidate_pattern("ref:*")
    cache_invalidate_pattern("analytics:*")

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
    org_id = _caller_org_id(current_user)
    if not repo.get_location_by_id(body.location_id, org_id=org_id):
        raise NotFoundError("Location", body.location_id)
    if not repo.get_item_by_id(body.item_id, org_id=org_id):
        raise NotFoundError("Item", body.item_id)

    if current_user.role == "staff" and not _has_location_access(current_user, body.location_id):
        raise AuthorizationError(f"Staff account is not authorized for Location #{body.location_id}")

    result = service.add_transaction(
        location_id=body.location_id,
        item_id=body.item_id,
        transaction_date=body.date,
        received=body.received,
        issued=body.issued,
        notes=body.notes,
        entered_by=str(current_user.username),
        batch_number=body.batch_number,
        expiry_date=body.expiry_date,
    )
    cache_invalidate_pattern("ref:location_items:*")
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
    org_id = _caller_org_id(current_user)
    if not repo.get_location_by_id(body.location_id, org_id=org_id):
        raise NotFoundError("Location", body.location_id)

    if current_user.role == "staff" and not _has_location_access(current_user, body.location_id):
        raise AuthorizationError(f"Staff account is not authorized for Location #{body.location_id}")

    for item in body.items:
        if not repo.get_item_by_id(item.item_id, org_id=org_id):
            raise NotFoundError("Item", item.item_id)

    items_data = [
        {
            "item_id": item.item_id,
            "received": item.received,
            "issued": item.issued,
            "notes": item.notes,
            "batch_number": item.batch_number,
            "expiry_date": item.expiry_date,
        }
        for item in body.items
    ]

    result = service.bulk_add_transactions(
        location_id=body.location_id,
        transaction_date=body.date,
        items_data=items_data,
        entered_by=str(current_user.username),
    )
    cache_invalidate_pattern("ref:location_items:*")
    cache_invalidate_pattern("analytics:*")
    return result


@router.post("/scan-dispense")
@limiter.limit("60/minute")
def scan_dispense_item(
    request: Request,
    body: ScanDispenseRequest,
    repo: InventoryRepository = Depends(get_inventory_repo),
    service: InventoryService = Depends(get_inventory_service),
    current_user: User = Depends(require_staff),
):
    """
    High-speed barcode dispense for pharmacy retail counters.
    Validates barcode, selects earliest-expiring active batch (FEFO order),
    atomically decrements stock, records transaction, and broadcasts real-time updates.
    """
    org_id = _caller_org_id(current_user)
    location = repo.get_location_by_id(body.location_id, org_id=org_id)
    if not location:
        raise NotFoundError("Location", body.location_id)

    # Scoped staff validation: if user has assigned location_ids, check authorization
    if current_user.role == "staff" and not _has_location_access(current_user, body.location_id):
        raise AuthorizationError(f"Staff account is not authorized to dispense at Location #{body.location_id}")

    return service.dispense_by_barcode(
        barcode_or_id=body.barcode,
        location_id=body.location_id,
        quantity=body.quantity,
        unit=body.unit,
        entered_by=str(current_user.username),
        org_id=org_id,
    )

