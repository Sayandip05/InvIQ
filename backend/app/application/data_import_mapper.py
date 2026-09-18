"""
AI-powered Column Mapper for CSV/Excel data import.

Role:
  Takes uploaded file headers and a small sample of rows (first 3 rows),
  introspects the target SQLAlchemy model schema, and queries Groq LLM
  to determine the best column mapping and confidence score per field.

Rules & Guarantees:
  - NEVER receives full row data — only headers + first N sample rows.
  - NEVER writes to the database.
  - Caches mapping results in Redis/in-memory cache keyed by SHA-256(headers + target).
  - Provides a deterministic heuristic/fuzzy fallback if LLM is unavailable.
"""

import hashlib
import json
import logging
import re
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.application.cache_service import cache_get, cache_set
from app.infrastructure.database.models import Location, Item, InventoryTransaction

logger = logging.getLogger("smart_inventory.data_import_mapper")


TARGET_MODELS: Dict[str, Any] = {
    "inventory_transaction": InventoryTransaction,
    "item": Item,
    "location": Location,
}

# High-risk fields require higher confidence (settings.IMPORT_HIGH_RISK_CONFIDENCE)
HIGH_RISK_FIELDS: Dict[str, set] = {
    "inventory_transaction": {"item_name", "item_id", "location_name", "location_id", "date", "batch_number"},
    "item": {"name"},
    "location": {"name"},
}


class DataImportMapper:
    """Handles AI-assisted column mapping with caching and deterministic fallback."""

    def __init__(self):
        self.cache_ttl = settings.IMPORT_MAPPING_CACHE_TTL

    @staticmethod
    def get_target_schema_meta(target_entity: str) -> Dict[str, Any]:
        """Introspect model to return target fields, data types, and required status."""
        model = TARGET_MODELS.get(target_entity)
        if not model:
            raise ValueError(f"Unsupported target entity: {target_entity}")

        schema_fields = {}
        # Custom virtual field mappings for transactions to allow name-based lookup
        if target_entity == "inventory_transaction":
            schema_fields["item_name"] = {
                "type": "string",
                "required": True,
                "description": "Name of the medicine or inventory item",
                "high_risk": True,
            }
            schema_fields["location_name"] = {
                "type": "string",
                "required": False,
                "description": "Facility or location name (if not using target location parameter)",
                "high_risk": True,
            }

        for col in model.__table__.columns:
            # Skip internal system columns
            if col.name in ("id", "org_id", "created_at", "updated_at", "opening_stock", "closing_stock", "entered_by"):
                continue

            is_high_risk = col.name in HIGH_RISK_FIELDS.get(target_entity, set())
            is_required = not col.nullable and col.default is None and col.server_default is None

            schema_fields[col.name] = {
                "type": str(col.type).lower(),
                "required": is_required,
                "description": f"{col.name} field for {target_entity}",
                "high_risk": is_high_risk,
            }

        return schema_fields

    @staticmethod
    def build_cache_key(headers: List[str], target_entity: str) -> str:
        """Create a deterministic SHA-256 cache key from headers and target entity."""
        normalized_headers = sorted([h.strip().lower() for h in headers if h])
        raw_key = f"{target_entity}:" + "|".join(normalized_headers)
        digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        return f"import_mapping:{digest}"

    def map_columns(
        self,
        headers: List[str],
        sample_rows: List[Dict[str, Any]],
        target_entity: str,
    ) -> Dict[str, Any]:
        """
        Map CSV/Excel columns to target schema.
        
        Returns:
            {
                "mappings": {
                    "csv_col": {"target_field": "db_field_or_null", "confidence": 0.95}
                },
                "unmapped_columns": ["extra_col"],
                "missing_required": ["name"],
                "cache_hit": bool
            }
        """
        if target_entity not in TARGET_MODELS:
            raise ValueError(f"Invalid target entity: {target_entity}")

        cache_key = self.build_cache_key(headers, target_entity)
        cached_result = cache_get(cache_key)
        if cached_result:
            logger.info("Cache HIT for column mapping key=%s", cache_key)
            cached_result["cache_hit"] = True
            return cached_result

        schema = self.get_target_schema_meta(target_entity)

        # Ingestion is strictly deterministic with zero AI/LLM calls
        mapping_result = self._heuristic_mapper(headers, sample_rows, target_entity, schema)
        mapping_result["cache_hit"] = False
        cache_set(cache_key, mapping_result, ttl=self.cache_ttl)
        return mapping_result

    def _call_llm_mapper(
        self,
        headers: List[str],
        sample_rows: List[Dict[str, Any]],
        target_entity: str,
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send prompt to ChatGroq for strict JSON column mapping."""
        from langchain_groq import ChatGroq
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = ChatGroq(
            model=settings.LLM_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=0.0,
            max_tokens=1024,
        )

        # Truncate sample cell values to protect token limits
        safe_sample = []
        for row in sample_rows[: settings.IMPORT_SAMPLE_ROWS]:
            safe_row = {
                k: (str(v)[:80] if v is not None else "")
                for k, v in row.items()
            }
            safe_sample.append(safe_row)

        prompt_data = {
            "target_entity": target_entity,
            "target_schema": schema,
            "uploaded_headers": headers,
            "sample_rows": safe_sample,
        }

        system_msg = SystemMessage(
            content=(
                "You are an expert data schema integration assistant for a healthcare inventory system.\n"
                "Your job is to map uploaded spreadsheet column headers to target database fields.\n"
                "You MUST output valid JSON ONLY, strictly adhering to this structure:\n"
                "{\n"
                '  "mappings": {\n'
                '    "<header_name>": {\n'
                '      "target_field": "<matched_target_field_name or null>",\n'
                '      "confidence": <float between 0.0 and 1.0>\n'
                "    }\n"
                "  },\n"
                '  "unmapped_columns": ["<list of headers with no match>"],\n'
                '  "missing_required": ["<list of required target fields not mapped>"]\n'
                "}\n"
                "Rules:\n"
                "1. If a column clearly matches (e.g. 'Item Name' -> 'item_name' or 'name', 'Qty' -> 'received'), assign high confidence (0.9-1.0).\n"
                "2. If ambiguous or partial match, assign 0.5-0.8.\n"
                "3. If no reasonable match, set target_field to null and confidence to 0.0.\n"
                "4. Do NOT hallucinate fields outside the provided target_schema.\n"
                "5. Return pure JSON without markdown backticks."
            )
        )

        user_msg = HumanMessage(content=json.dumps(prompt_data, indent=2))

        response = llm.invoke([system_msg, user_msg])
        raw_text = response.content.strip()

        # Clean markdown wrappers if any
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(?:json)?", "", raw_text)
            raw_text = re.sub(r"```$", "", raw_text)
            raw_text = raw_text.strip()

        parsed = json.loads(raw_text)
        return self._normalize_mapping_output(parsed, headers, schema)

    def _heuristic_mapper(
        self,
        headers: List[str],
        sample_rows: List[Dict[str, Any]],
        target_entity: str,
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Deterministic keyword / substring matcher used when LLM is unavailable."""
        mappings = {}
        unmapped = []
        assigned_targets = set()

        synonyms: Dict[str, List[str]] = {
            "name": ["item_name", "itemname", "item", "product", "medicine", "drug", "title", "location_name", "location", "facility"],
            "item_name": ["item_name", "itemname", "item", "product_name", "productname", "product", "medicine_name", "medicine", "drug_name", "drug"],
            "location_name": ["location_name", "locationname", "location", "facility", "warehouse", "clinic", "hospital", "branch"],
            "category": ["category", "cat", "class", "group", "type"],
            "unit": ["unit", "uom", "package", "pack", "measure"],
            "lead_time_days": ["lead_time", "leadtime", "days_lead", "delivery_days"],
            "min_stock": ["min_stock", "minstock", "min_qty", "threshold", "minimum_stock", "reorder_level"],
            "storage_temp": ["storage_temp", "storagetemp", "temp", "temperature", "cold_chain", "storage"],
            "received": ["received", "received_qty", "receivedqty", "qty_received", "quantity_received", "quantityreceived", "inbound", "qty_in", "in", "quantity", "qty"],
            "issued": ["issued", "issued_qty", "issuedqty", "qty_issued", "quantity_issued", "quantityissued", "outbound", "qty_out", "out", "dispensed"],
            "date": ["date", "transaction_date", "transactiondate", "tx_date", "txdate", "delivery_date", "entry_date"],
            "batch_number": ["batch_number", "batchnumber", "batch_no", "batchno", "batch", "lot_number", "lotnumber", "lot_no", "lot"],
            "expiry_date": ["expiry_date", "expirydate", "exp_date", "expdate", "expiry", "exp", "expiration_date", "expirationdate"],
            "notes": ["notes", "note", "remarks", "comment", "description"],
            "region": ["region", "zone", "state", "area", "district"],
            "address": ["address", "street", "city"],
            "type": ["type", "loc_type", "facility_type"],
        }


        for header in headers:
            norm_header = re.sub(r"[^a-z0-9]", "", header.lower())
            matched_target = None
            confidence = 0.0

            # 1. Exact match
            for target_field in schema:
                norm_target = re.sub(r"[^a-z0-9]", "", target_field.lower())
                if norm_header == norm_target:
                    matched_target = target_field
                    confidence = 1.0
                    break

            # 2. Exact synonym match (Pass 1)
            if not matched_target:
                for target_field, syn_list in synonyms.items():
                    if target_field not in schema:
                        continue
                    for syn in syn_list:
                        norm_syn = re.sub(r"[^a-z0-9]", "", syn)
                        if norm_header == norm_syn:
                            matched_target = target_field
                            confidence = 0.95
                            break
                    if matched_target:
                        break

            # 3. Partial/substring synonym match (Pass 2 - only if no exact match found)
            if not matched_target:
                for target_field, syn_list in synonyms.items():
                    if target_field not in schema:
                        continue
                    for syn in syn_list:
                        norm_syn = re.sub(r"[^a-z0-9]", "", syn)
                        if len(norm_syn) >= 3 and (norm_syn in norm_header or norm_header in norm_syn):
                            matched_target = target_field
                            confidence = 0.75
                            break
                    if matched_target:
                        break


            if matched_target and matched_target not in assigned_targets:
                mappings[header] = {
                    "target_field": matched_target,
                    "confidence": confidence,
                }
                assigned_targets.add(matched_target)
            else:
                mappings[header] = {
                    "target_field": None,
                    "confidence": 0.0,
                }
                unmapped.append(header)

        missing_required = [
            field for field, meta in schema.items()
            if meta.get("required") and field not in assigned_targets
        ]

        return {
            "mappings": mappings,
            "unmapped_columns": unmapped,
            "missing_required": missing_required,
        }

    def _normalize_mapping_output(
        self,
        raw_output: Dict[str, Any],
        headers: List[str],
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate and clean LLM mapping output."""
        raw_mappings = raw_output.get("mappings", {})
        cleaned_mappings = {}
        assigned_targets = set()
        unmapped = []

        for h in headers:
            m = raw_mappings.get(h) or {}
            target = m.get("target_field")
            confidence = float(m.get("confidence", 0.0))

            if target and target in schema:
                cleaned_mappings[h] = {
                    "target_field": target,
                    "confidence": max(0.0, min(1.0, confidence)),
                }
                assigned_targets.add(target)
            else:
                cleaned_mappings[h] = {
                    "target_field": None,
                    "confidence": 0.0,
                }
                unmapped.append(h)

        missing_required = [
            field for field, meta in schema.items()
            if meta.get("required") and field not in assigned_targets
        ]

        return {
            "mappings": cleaned_mappings,
            "unmapped_columns": unmapped,
            "missing_required": missing_required,
        }
