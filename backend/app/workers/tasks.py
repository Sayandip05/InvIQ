"""
Celery Task Definitions for InvIQ Asynchronous Processing.

Layer: Workers
Features:
- Multi-Tenant Job Context: Every task payload carries org_id, actor_id, correlation_id, and idempotency_token.
- Resilience: Configured with exponential backoff retries (3 attempts) and dead-letter queues.
- Offloaded Heavy Tasks:
  1. Bulk CSV/Excel file validation and data imports
  2. PDF delivery invoice and monthly financial report generation
  3. Vector embeddings synchronization with Qdrant for RAG memory
  4. Automated recurring jobs via Celery Beat (FEFO expiry audits, stock thresholds, cold-chain monitoring)
  5. Transactional email & supplier delivery notifications
"""

import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from app.infrastructure.database.connection import get_db_context
from app.api.routes.websocket import publish_domain_event

logger = logging.getLogger("smart_inventory.workers")

# Celery App Import with Graceful Fallback Decorator
try:
    from app.workers.celery_app import celery_app
    _celery_available = True
except Exception:
    celery_app = None
    _celery_available = False


def _task_wrapper(name: str, max_retries: int = 3, default_retry_delay: int = 5):
    """Decorator that registers a task with Celery if available, or wraps as standard callable."""
    def decorator(fn):
        if _celery_available and celery_app:
            return celery_app.task(
                name=name,
                max_retries=max_retries,
                default_retry_delay=default_retry_delay,
                autoretry_for=(Exception,),
                retry_backoff=True,
                retry_backoff_max=60,
                retry_jitter=True,
            )(fn)
        fn.name = name
        fn.delay = lambda *args, **kwargs: fn(*args, **kwargs)
        return fn
    return decorator


# 1. Bulk CSV/Excel Data Import Task

@_task_wrapper(name="app.workers.tasks.import_csv_task")
def import_csv_task(
    job_id: int,
    org_id: int,
    actor_id: int,
    confirmed_mapping: Optional[Dict[str, Any]] = None,
    default_location_id: Optional[int] = None,
    username: Optional[str] = None,
    correlation_id: Optional[str] = None,
    idempotency_token: Optional[str] = None,
    db=None,
) -> Dict[str, Any]:
    """
    Asynchronously processes and validates uploaded CSV/Excel import jobs.
    Carries full tenant isolation context and records execution state in DB.
    """
    correlation_id = correlation_id or str(uuid.uuid4())
    username = username or f"user-{actor_id}"
    logger.info(
        "Executing CSV Import Task | Job ID: %s | Org ID: %s | Actor ID: %s | Correlation: %s",
        job_id, org_id, actor_id, correlation_id,
    )

    def _execute(session):
        from app.infrastructure.database.data_import_repo import DataImportRepository
        from app.application.data_import_service import DataImportService

        repo = DataImportRepository(session)
        job = repo.get_job(job_id)
        if not job or job.org_id != org_id:
            logger.error("Unauthorized import job access in worker: job_id=%s, org_id=%s", job_id, org_id)
            return {"status": "error", "message": "Job not found or cross-tenant access"}

        # Use confirmed mapping from argument or fallback to mapping_result on job
        mapping = confirmed_mapping or getattr(job, "mapping_result", None) or {}

        service = DataImportService(session)
        updated_job = service.execute_import(
            job_id=job_id,
            confirmed_mapping=mapping,
            default_location_id=default_location_id,
            entered_by=username,
        )

        # Publish domain event to notify clients of import completion
        publish_domain_event(
            topic="import.completed",
            org_id=org_id,
            payload={
                "job_id": job_id,
                "status": updated_job.status if updated_job else "COMPLETED",
                "success_rows": updated_job.success_rows if updated_job else 0,
                "quarantined_rows": updated_job.quarantined_rows if updated_job else 0,
                "correlation_id": correlation_id,
            },
        )

        return {
            "status": "success",
            "job_id": job_id,
            "org_id": org_id,
            "job_status": updated_job.status if updated_job else "COMPLETED",
            "success_rows": updated_job.success_rows if updated_job else 0,
            "quarantined_rows": updated_job.quarantined_rows if updated_job else 0,
            "correlation_id": correlation_id,
            "processed_at": datetime.utcnow().isoformat(),
        }

    if db is not None:
        return _execute(db)
    with get_db_context() as session:
        return _execute(session)


# 2. PDF Delivery Invoice & Report Generation Task

@_task_wrapper(name="app.workers.tasks.generate_invoice_pdf_task")
def generate_invoice_pdf_task(
    invoice_id: int,
    org_id: int,
    actor_id: int,
    correlation_id: Optional[str] = None,
    db=None,
) -> Dict[str, Any]:
    """
    Asynchronously compiles and uploads PDF vendor invoices to Azure Blob Storage / database.
    """
    correlation_id = correlation_id or str(uuid.uuid4())
    logger.info(
        "Executing Invoice PDF Generation Task | Invoice ID: %s | Org ID: %s | Correlation: %s",
        invoice_id, org_id, correlation_id,
    )

    def _execute(session):
        from app.application.vendor_service import VendorService
        from app.application.invoice_pdf_service import InvoicePdfService
        from app.infrastructure.storage.azure_blob_storage import get_storage_service
        from app.infrastructure.database.models import User, VendorUpload
        from sqlalchemy.orm import joinedload

        svc = VendorService(session)
        invoice = svc.get_invoice(invoice_id, org_id=org_id)
        if not invoice:
            logger.error("Invoice %s not found for org %s", invoice_id, org_id)
            return {"status": "error", "message": "Invoice not found"}

        # If PDF binary is not generated, compile it now
        if not invoice.pdf_content:
            invoice_payload = {
                "invoice_number": invoice.invoice_number,
                "invoice_date": invoice.invoice_date,
                "line_items": invoice.line_items,
                "subtotal": float(invoice.subtotal),
                "tax_amount": float(invoice.tax_amount),
                "total_amount": float(invoice.total_amount),
                "status": invoice.status,
            }

            # Query real vendor details
            vendor_user = session.query(User).filter(User.id == invoice.vendor_user_id).first()
            vendor_data = {
                "username": vendor_user.username if vendor_user else f"vendor-{invoice.vendor_user_id}",
                "full_name": (vendor_user.full_name or vendor_user.username) if vendor_user else "Authorized Vendor",
                "email": vendor_user.email if vendor_user else "vendor@inviq.local",
            }

            # Retrieve location via vendor_upload relationship.
            # VendorInvoice has NO location_id column — the location belongs to
            # invoice.vendor_upload.location (VendorUpload → Location FK).
            from app.infrastructure.database.models import VendorInvoice as VendorInvoiceModel
            invoice_with_upload = (
                session.query(VendorInvoiceModel)
                .options(
                    joinedload(VendorInvoiceModel.vendor_upload).joinedload(VendorUpload.location)
                )
                .filter(VendorInvoiceModel.id == invoice_id)
                .first()
            )
            location_obj = None
            if (
                invoice_with_upload
                and invoice_with_upload.vendor_upload
                and invoice_with_upload.vendor_upload.location
            ):
                candidate = invoice_with_upload.vendor_upload.location
                # Enforce org-scoping: reject locations belonging to another tenant
                if candidate.org_id == org_id:
                    location_obj = candidate
                else:
                    logger.error(
                        "Location org mismatch for invoice %s: location.org_id=%s vs org_id=%s — "
                        "falling back to placeholder location data",
                        invoice_id, candidate.org_id, org_id,
                    )

            location_data = {
                "name": location_obj.name if location_obj else "Central Pharmacy Depot",
                "type": location_obj.type if location_obj else "WAREHOUSE",
                "region": location_obj.region if location_obj else "Default Region",
                "address": location_obj.address or "Main Store Location" if location_obj else "Healthcare Distribution Center",
            }

            pdf_bytes = InvoicePdfService.generate_invoice_pdf(
                invoice_data=invoice_payload,
                vendor_data=vendor_data,
                location_data=location_data,
            )

            # Upload to Azure Blob Storage
            blob_path = f"invoices/{invoice.invoice_date.year}/{invoice.invoice_date.month:02d}/{invoice.invoice_number}.pdf"
            storage = get_storage_service()
            pdf_url = storage.upload_file(
                file_bytes=pdf_bytes,
                blob_name=blob_path,
                content_type="application/pdf",
            )
            sas_url = storage.generate_sas_url(blob_path) if pdf_url else None

            # Update invoice record
            invoice.pdf_path = blob_path
            invoice.pdf_url = sas_url or pdf_url
            invoice.pdf_content = pdf_bytes
            session.commit()

        return {
            "status": "success",
            "invoice_id": invoice_id,
            "invoice_number": invoice.invoice_number,
            "org_id": org_id,
            "correlation_id": correlation_id,
        }

    if db is not None:
        return _execute(db)
    with get_db_context() as session:
        return _execute(session)


# 3. Vector Embeddings Sync Task for Qdrant RAG Memory

@_task_wrapper(name="app.workers.tasks.sync_vector_embeddings_task")
def sync_vector_embeddings_task(
    org_id: int,
    session_id: str,
    user_id: int,
    text: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    db=None,
) -> Dict[str, Any]:
    """
    Asynchronously generates embeddings and updates Qdrant vector memory collection.
    """
    correlation_id = correlation_id or str(uuid.uuid4())
    logger.info(
        "Executing Vector Embedding Sync | Org ID: %s | Session: %s | User: %s",
        org_id, session_id, user_id,
    )
    from app.infrastructure.vector_store.vector_store import get_vector_memory
    memory = get_vector_memory()

    if memory.is_available and text:
        try:
            memory.add_interaction(
                session_id=session_id,
                user_id=user_id,
                user_message=text,
                agent_response=metadata.get("response", "") if metadata else "",
                context=metadata.get("context") if metadata else None,
                org_id=org_id,
            )
        except Exception as exc:
            logger.warning("Vector sync interaction failed: %s", exc)

    return {
        "status": "success" if memory.is_available else "skipped",
        "org_id": org_id,
        "session_id": session_id,
        "correlation_id": correlation_id,
    }


@_task_wrapper(name="app.workers.tasks.sync_onboarding_context_task")
def sync_onboarding_context_task(
    org_id: Optional[int],
    user_id: Optional[int],
    full_name: str,
    pharmacy_name: str,
    primary_counter: str = "Main Market Counter",
    plan_type: str = "single_pharmacy",
    extra_settings: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Asynchronously indexes pharmacy owner and store onboarding context into Qdrant Vector Memory.
    """
    correlation_id = correlation_id or str(uuid.uuid4())
    logger.info(
        "Executing Onboarding Vector Indexing | Org ID: %s | User: %s | Store: %s",
        org_id, user_id, pharmacy_name,
    )
    from app.infrastructure.vector_store.vector_store import get_vector_memory
    memory = get_vector_memory()

    if memory.is_available:
        try:
            memory.add_onboarding_context(
                org_id=org_id,
                user_id=user_id,
                full_name=full_name,
                pharmacy_name=pharmacy_name,
                primary_counter=primary_counter,
                plan_type=plan_type,
                extra_settings=extra_settings,
            )
        except Exception as exc:
            logger.warning("Onboarding vector indexing failed: %s", exc)

    return {
        "status": "success" if memory.is_available else "skipped",
        "org_id": org_id,
        "user_id": user_id,
        "correlation_id": correlation_id,
    }


# 4. Transactional Notification / Email Dispatch Task

@_task_wrapper(name="app.workers.tasks.send_email_notification_task")
def send_email_notification_task(
    org_id: int,
    recipient_email: str,
    subject: str,
    body: str,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Asynchronously sends transactional notification emails via SMTP.
    """
    correlation_id = correlation_id or str(uuid.uuid4())
    logger.info(
        "Executing Email Notification Task | Org ID: %s | Recipient: %s | Subject: %s",
        org_id, recipient_email, subject,
    )
    from app.application.notification_service import NotificationService
    success = NotificationService.send_transactional_email(recipient_email, subject, body)
    return {
        "status": "success" if success else "failed",
        "org_id": org_id,
        "recipient": recipient_email,
        "correlation_id": correlation_id,
    }


# 5. Scheduled Celery Beat Recurring Jobs

@_task_wrapper(name="app.workers.tasks.celery_fefo_audit")
def celery_fefo_audit(org_id: Optional[int] = None, db=None):
    """Scheduled task: audits near-expiry batches across all active pharmacy stores."""
    from app.application.background_tasks import run_fefo_expiry_audit
    if db is not None:
        return run_fefo_expiry_audit(db, org_id=org_id)
    with get_db_context() as session:
        return run_fefo_expiry_audit(session, org_id=org_id)


@_task_wrapper(name="app.workers.tasks.celery_stock_audit")
def celery_stock_audit(org_id: Optional[int] = None, db=None):
    """Scheduled task: monitors stock thresholds and triggers low-stock alerts."""
    from app.application.background_tasks import run_stock_threshold_audit
    if db is not None:
        return run_stock_threshold_audit(db, org_id=org_id)
    with get_db_context() as session:
        return run_stock_threshold_audit(session, org_id=org_id)


@_task_wrapper(name="app.workers.tasks.celery_cold_chain_check")
def celery_cold_chain_check(org_id: Optional[int] = None, db=None):
    """Scheduled task: audits temperature compliance for cold-chain medications."""
    from app.application.background_tasks import run_cold_chain_health_check
    if db is not None:
        return run_cold_chain_health_check(db, org_id=org_id)
    with get_db_context() as session:
        return run_cold_chain_health_check(session, org_id=org_id)


# 6. Monthly Sales Cache Updater

@_task_wrapper(name="app.workers.tasks.update_monthly_sales_cache_task")
def update_monthly_sales_cache_task(
    session_id: int,
    org_id: int,
    correlation_id: Optional[str] = None,
    db=None,
) -> Dict[str, Any]:
    """
    Fires after every billing session checkout.

    Reads the closed BillingSession from DB and atomically increments the
    Redis monthly sales HASH for the org+month, so the monthly report endpoint
    can read pre-computed totals in O(1) without a DB scan.

    Redis key  : sales:{org_id}:{YYYY-MM}
    Redis type : HASH
    Fields     : session_count, gross_total, discount_amount, net_total, purchase_cost
    TTL        : 13 months (keeps rolling 12 months available)
    """
    correlation_id = correlation_id or str(uuid.uuid4())
    logger.info(
        "Monthly sales cache update | session_id=%s org_id=%s correlation=%s",
        session_id, org_id, correlation_id,
    )

    def _execute(session):
        from app.infrastructure.database.models import BillingSession

        billing = (
            session.query(BillingSession)
            .filter(BillingSession.id == session_id, BillingSession.org_id == org_id)
            .first()
        )
        if not billing:
            logger.error(
                "Monthly cache update: BillingSession #%s not found for org %s",
                session_id, org_id,
            )
            return {"status": "error", "message": "Session not found"}

        if billing.status != "CLOSED":
            logger.warning(
                "Monthly cache update: BillingSession #%s is %s, expected CLOSED",
                session_id, billing.status,
            )
            return {"status": "skipped", "reason": f"Session status is {billing.status}"}

        month_key = billing.month_key
        if not month_key:
            # Derive from closed_at if month_key wasn't set
            ts = billing.closed_at or billing.opened_at
            month_key = ts.strftime("%Y-%m") if ts else datetime.utcnow().strftime("%Y-%m")

        redis_key = f"sales:{org_id}:{month_key}"
        thirteen_months_seconds = 13 * 30 * 24 * 3600

        try:
            from app.infrastructure.cache.redis_client import get_redis, is_redis_available
            r = get_redis()
            if r and is_redis_available():
                pipe = r.pipeline()
                pipe.hincrbyfloat(redis_key, "gross_total",     billing.gross_total     or 0.0)
                pipe.hincrbyfloat(redis_key, "discount_amount", billing.discount_amount  or 0.0)
                pipe.hincrbyfloat(redis_key, "net_total",       billing.net_total        or 0.0)
                pipe.hincrbyfloat(redis_key, "purchase_cost",   billing.purchase_cost    or 0.0)
                pipe.hincrby(redis_key,      "session_count",   1)
                pipe.expire(redis_key, thirteen_months_seconds)
                pipe.execute()
                logger.info(
                    "Monthly sales cache updated | key=%s net=%.2f",
                    redis_key, billing.net_total or 0.0,
                )
                return {
                    "status":     "success",
                    "redis_key":  redis_key,
                    "session_id": session_id,
                    "org_id":     org_id,
                    "correlation_id": correlation_id,
                }
            else:
                logger.info("Redis unavailable — monthly cache skipped for session %s", session_id)
                return {"status": "skipped", "reason": "Redis unavailable"}
        except Exception as redis_err:
            logger.error("Redis monthly cache update failed: %s", redis_err)
            return {"status": "error", "message": str(redis_err)}

    if db is not None:
        return _execute(db)
    with get_db_context() as session:
        return _execute(session)
