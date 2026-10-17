"""
Discount Service — pure stateless math helper.

Layer: Application

No DB access. Receives gross_total and discount_config (from org.settings),
returns a complete billing breakdown dict.

Supported discount models:
  - "none"   : No discount applied.
  - "flat"   : Fixed percentage off the entire bill (e.g. always 10%).
  - "tiered" : Percentage determined by the bill total (slab-based).

Usage:
    from app.application.discount_service import apply_discount
    breakdown = apply_discount(gross_total=450.0, discount_config=org.settings)
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("smart_inventory.discount_service")


# Public API

def apply_discount(gross_total: float, discount_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Compute the discount and return a full billing breakdown.

    Args:
        gross_total:     Σ (qty × mrp) across all items in the cart.
        discount_config: Dict from org.settings containing discount keys.
                         If None or missing 'discount_model', model defaults to "none".

    Returns:
        {
          "gross_total":     float,
          "discount_model":  str,    # "flat" | "tiered" | "none"
          "discount_pct":    float,  # 0.0 – 100.0
          "discount_amount": float,  # rupees deducted
          "net_total":       float,  # what the customer pays
        }
    """
    if not discount_config:
        discount_config = {}

    model = str(discount_config.get("discount_model", "none")).lower()
    gross_total = round(float(gross_total), 2)

    if model == "flat":
        pct = _get_flat_pct(discount_config)

    elif model == "tiered":
        pct = _get_tiered_pct(gross_total, discount_config)

    else:
        # "none" or any unrecognised value
        model = "none"
        pct = 0.0

    pct = max(0.0, min(100.0, round(float(pct), 4)))   # clamp 0–100
    discount_amount = round(gross_total * pct / 100.0, 2)
    net_total = round(gross_total - discount_amount, 2)

    logger.debug(
        "Discount applied | model=%s pct=%.2f gross=%.2f discount=%.2f net=%.2f",
        model, pct, gross_total, discount_amount, net_total,
    )

    return {
        "gross_total":     gross_total,
        "discount_model":  model,
        "discount_pct":    pct,
        "discount_amount": discount_amount,
        "net_total":       net_total,
    }


def validate_discount_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate a discount configuration dict.

    Returns a list of human-readable error messages (empty = valid).
    Called by the PUT /admin/discount-settings endpoint before persisting.
    """
    errors = []
    model = str(config.get("discount_model", "")).lower()

    if model not in ("flat", "tiered", "none"):
        errors.append("discount_model must be one of: 'flat', 'tiered', 'none'")
        return errors  # Can't validate further without a valid model

    if model == "flat":
        pct = config.get("flat_discount_pct")
        if pct is None:
            errors.append("flat_discount_pct is required when discount_model is 'flat'")
        else:
            try:
                pct_f = float(pct)
                if not (0.0 < pct_f <= 100.0):
                    errors.append("flat_discount_pct must be between 0 (exclusive) and 100")
            except (TypeError, ValueError):
                errors.append("flat_discount_pct must be a number")

    elif model == "tiered":
        slabs = config.get("tiered_discount_config")
        if not slabs or not isinstance(slabs, list):
            errors.append("tiered_discount_config must be a non-empty list of slabs")
        else:
            errors.extend(_validate_slabs(slabs))

    return errors


# Internal helpers

def _get_flat_pct(config: Dict[str, Any]) -> float:
    try:
        return float(config.get("flat_discount_pct", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _get_tiered_pct(gross_total: float, config: Dict[str, Any]) -> float:
    slabs: List[Dict] = config.get("tiered_discount_config", [])
    for slab in slabs:
        try:
            min_b = float(slab.get("min_bill", 0))
            max_b = slab.get("max_bill")           # None = no ceiling
            pct   = float(slab.get("discount_pct", 0.0))
            if gross_total >= min_b and (max_b is None or gross_total < float(max_b)):
                return pct
        except (TypeError, ValueError):
            continue
    return 0.0  # No slab matched → no discount


def _validate_slabs(slabs: List[Dict]) -> List[str]:
    errors = []
    for i, slab in enumerate(slabs):
        label = f"Slab #{i + 1}"
        min_b = slab.get("min_bill")
        max_b = slab.get("max_bill")
        pct   = slab.get("discount_pct")

        if min_b is None:
            errors.append(f"{label}: 'min_bill' is required")
        else:
            try:
                if float(min_b) < 0:
                    errors.append(f"{label}: 'min_bill' must be >= 0")
            except (TypeError, ValueError):
                errors.append(f"{label}: 'min_bill' must be a number")

        if max_b is not None:
            try:
                if float(max_b) <= float(min_b or 0):
                    errors.append(f"{label}: 'max_bill' must be greater than 'min_bill'")
            except (TypeError, ValueError):
                errors.append(f"{label}: 'max_bill' must be a number or null")

        if pct is None:
            errors.append(f"{label}: 'discount_pct' is required")
        else:
            try:
                pct_f = float(pct)
                if not (0.0 <= pct_f <= 100.0):
                    errors.append(f"{label}: 'discount_pct' must be between 0 and 100")
            except (TypeError, ValueError):
                errors.append(f"{label}: 'discount_pct' must be a number")

    return errors
