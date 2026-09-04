"""
Data Import API — AI-assisted CSV/Excel column mapping and deterministic data ingestion.

Workflow:
  1. POST /data-import/upload
     - Reads file headers + 3 sample rows
     - Calls AI mapper (Groq LLM) or heuristic fallback (cached by header set)
     - Stores file bytes in DataImportJob (status=PENDING)
     - Returns proposed mapping for review
  2. POST /data-import/confirm
     - Accepts user-confirmed or edited column mapping
     - Runs deterministic row processing & validation
     - Small files (<= 500 rows) process synchronously in request
     - Large files (> 500 rows) process in background thread
  3. GET /data-import/jobs/{job_id}
     - Returns current job status, total rows, successes, and quarantine count
  4. GET /data-import/jobs/{job_id}/quarantine
     - Returns list of quarantined rows with rejection reasons
"""

import logging
import threading
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Request, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_staff
from app.core.rate_limiter import limiter
from app.core.config import settings
from app.core.exceptions import ValidationError, NotFoundError, AuthorizationError
from app.infrastructure.database.models import User, DataImportJob, Location

from app.infrastructure.database.connection import SessionLocal
from app.application.data_import_service import DataImportService
from app.application.data_import_mapper import DataImportMapper
from app.application.audit_service import AuditService
from app.api.schemas.data_import_schemas import (
    ImportPreviewResponse,
    ImportConfirmRequest,
    ImportStatusResponse,
    QuarantineListResponse,
    QuarantineRowItem,
)

logger = logging.getLogger("smart_inventory.data_import")

router = APIRouter(prefix="/data-import", tags=["Data Import"])

ALLOWED_EXTENSIONS = (".csv", ".xlsx", ".xls")
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB matches existing vendor upload limit
SUPPORTED_ENTITIES = {"inventory_transaction", "item", "location"}


def _run_background_import(
    job_id: int,
    confirmed_mapping: dict,
    default_location_id: Optional[int],
    username: str,
) -> None:
    """Worker function for asynchronous background import of large files."""
    db = SessionLocal()
    try:
        service = DataImportService(db)
        service.execute_import(
            job_id=job_id,
            confirmed_mapping=confirmed_mapping,
            default_location_id=default_location_id,
            entered_by=username,
        )
        logger.info("Background import job #%d completed successfully", job_id)
    except Exception as e:
        logger.error("Background import job #%d failed: %s", job_id, str(e))
    finally:
        db.close()


# ── 1. Upload & AI Mapping ───────────────────────────────────────────────────

@router.post("/upload", response_model=ImportPreviewResponse)
@limiter.limit("10/minute")
def upload_and_map_file(
    request: Request,
    target_entity: str = Query("inventory_transaction", description="Target entity: inventory_transaction | item | location"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Step 1: Upload CSV or Excel file.
    Extracts headers and 3 sample rows, queries LLM for column mapping,
    and returns a preview for user review/editing.
    """
    target_entity = target_entity.strip().lower()
    if target_entity not in SUPPORTED_ENTITIES:
        raise ValidationError(f"Invalid target entity '{target_entity}'. Must be one of: {', '.join(SUPPORTED_ENTITIES)}")

    if not file.filename or not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise ValidationError(f"Invalid file type. Supported formats: {', '.join(ALLOWED_EXTENSIONS)}")

    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise ValidationError("File size exceeds 5MB limit")
    if len(content) == 0:
        raise ValidationError("Uploaded file is empty")

    service = DataImportService(db)
    try:
        headers, sample_rows, total_rows = service.inspect_file(content, file.filename)
    except Exception as e:
        raise ValidationError(f"Failed to parse file: {str(e)}")

    if not headers:
        raise ValidationError("No column headers found in file")

    mapper = DataImportMapper()
    target_schema = mapper.get_target_schema_meta(target_entity)
    mapping_result = mapper.map_columns(
        headers=headers,
        sample_rows=sample_rows,
        target_entity=target_entity,
    )

    if current_user.org_id is None:
        raise AuthorizationError("User is not assigned to an organization")

    # Upload raw file to Azure Blob Storage if configured
    import uuid
    from app.infrastructure.storage.azure_blob_storage import get_storage_service

    storage = get_storage_service()
    file_blob_path = None
    file_blob_url = None

    if storage.is_available:
        file_blob_path = f"imports/{current_user.org_id or 'global'}/{uuid.uuid4().hex[:12]}/{file.filename}"
        content_type = "text/csv" if file.filename.lower().endswith(".csv") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        uploaded_url = storage.upload_file(
            file_bytes=content,
            blob_name=file_blob_path,
            content_type=content_type,
        )
        if uploaded_url:
            sas_url = storage.generate_sas_url(file_blob_path)
            file_blob_url = sas_url or uploaded_url
            logger.info("Uploaded data import file to Azure Blob: %s", file_blob_path)

    # Save job record with raw file bytes + blob storage metadata for step 2
    job = service.import_repo.create_job(
        uploaded_by_user_id=current_user.id,
        org_id=current_user.org_id,
        filename=file.filename,
        target_entity=target_entity,
        file_content=content,
        file_blob_path=file_blob_path,
        file_blob_url=file_blob_url,
        total_rows=total_rows,
        mapping_result=mapping_result,
        mapping_cache_hit=mapping_result.get("cache_hit", False),
        status="PENDING",
    )

    return ImportPreviewResponse(
        success=True,
        job_id=job.id,
        filename=file.filename,
        target_entity=target_entity,
        headers=headers,
        sample_rows=sample_rows,
        mapping_result=mapping_result,
        mapping_cache_hit=mapping_result.get("cache_hit", False),
        total_rows=total_rows,
        target_schema=target_schema,
    )


# ── 2. Confirm & Ingest ──────────────────────────────────────────────────────

@router.post("/confirm", response_model=ImportStatusResponse)
@limiter.limit("10/minute")
def confirm_and_execute_import(
    request: Request,
    body: ImportConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Step 2: Confirm mapping and start ingestion.
    Processes rows deterministically in batches and applies confidence gating.
    """
    service = DataImportService(db)
    job = service.import_repo.get_job(body.job_id)
    if not job:
        raise NotFoundError("DataImportJob", body.job_id)

    # ── Tenant isolation and user ownership checks ──
    if current_user.org_id is None or job.org_id != current_user.org_id:
        raise AuthorizationError("Import job does not belong to your organization")
    if job.uploaded_by_user_id != current_user.id and current_user.role != "admin":
        raise AuthorizationError("You do not have permission to execute this import job")

    if job.status not in ("PENDING", "FAILED"):
        raise ValidationError(f"Job #{job.id} cannot be confirmed (current status: {job.status})")


    # ── Default location validation against tenant ──
    if body.default_location_id is not None:
        if current_user.org_id is None:
            raise AuthorizationError("User is not assigned to an organization")
        loc = db.query(Location).filter(
            Location.id == body.default_location_id,
            Location.org_id == current_user.org_id,
        ).first()
        if not loc:
            raise ValidationError(f"Default location {body.default_location_id} not found or does not belong to your organization")

    # Use confirmed mapping from request or saved mapping
    confirmed_mapping = body.mapping or job.mapping_result
    if not confirmed_mapping or "mappings" not in confirmed_mapping:
        raise ValidationError("Missing column mapping configuration")


    # Audit log
    audit = AuditService(db)
    audit.log(
        username=current_user.username,
        action="DATA_IMPORT_CONFIRMED",
        resource_type="data_import_job",
        resource_id=str(job.id),
        user_id=current_user.id,
        org_id=current_user.org_id,
        details={"filename": job.filename, "target_entity": job.target_entity, "total_rows": job.total_rows},
        ip_address=request.client.host if request.client else "unknown",
    )

    # Branch: synchronous vs asynchronous background processing
    is_large_file = (job.total_rows or 0) > settings.IMPORT_SYNC_ROW_LIMIT

    if is_large_file:
        job.is_background = True
        job.status = "PROCESSING"
        service.import_repo.update_job(job)

        try:
            from app.workers.tasks import import_csv_task, _celery_available
            if _celery_available:
                import_csv_task.delay(
                    job_id=job.id,
                    org_id=job.org_id,
                    actor_id=current_user.id,
                    confirmed_mapping=confirmed_mapping,
                    default_location_id=body.default_location_id,
                    username=current_user.username,
                )
                logger.info("Queued Celery background import task for job #%d (org_id=%s)", job.id, job.org_id)
            else:
                thread = threading.Thread(
                    target=_run_background_import,
                    args=(job.id, confirmed_mapping, body.default_location_id, current_user.username),
                    daemon=True,
                    name=f"data-import-job-{job.id}",
                )
                thread.start()
        except Exception as queue_err:
            logger.warning("Celery queue dispatch failed, using worker thread fallback: %s", queue_err)
            thread = threading.Thread(
                target=_run_background_import,
                args=(job.id, confirmed_mapping, body.default_location_id, current_user.username),
                daemon=True,
                name=f"data-import-job-{job.id}",
            )
            thread.start()

        return ImportStatusResponse(
            success=True,
            job_id=job.id,
            status="PROCESSING",
            target_entity=job.target_entity,
            filename=job.filename,
            total_rows=job.total_rows,
            success_rows=0,
            quarantined_rows=0,
            error_message=None,
            is_background=True,
            created_at=str(job.created_at) if job.created_at else None,
            updated_at=str(job.updated_at) if job.updated_at else None,
        )

    # Synchronous path (for files <= 500 rows)
    updated_job = service.execute_import(
        job_id=job.id,
        confirmed_mapping=confirmed_mapping,
        default_location_id=body.default_location_id,
        entered_by=current_user.username,
    )

    return ImportStatusResponse(
        success=True,
        job_id=updated_job.id,
        status=updated_job.status,
        target_entity=updated_job.target_entity,
        filename=updated_job.filename,
        total_rows=updated_job.total_rows,
        success_rows=updated_job.success_rows,
        quarantined_rows=updated_job.quarantined_rows,
        error_message=updated_job.error_message,
        is_background=False,
        created_at=str(updated_job.created_at) if updated_job.created_at else None,
        updated_at=str(updated_job.updated_at) if updated_job.updated_at else None,
    )


# ── 3. Check Job Status ──────────────────────────────────────────────────────

@router.get("/jobs/{job_id}", response_model=ImportStatusResponse)
def get_import_job_status(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Check progress/status of an import job."""
    service = DataImportService(db)
    job = service.import_repo.get_job(job_id)
    if not job:
        raise NotFoundError("DataImportJob", job_id)

    if current_user.org_id is None or job.org_id != current_user.org_id:
        raise AuthorizationError("Import job does not belong to your organization")
    if job.uploaded_by_user_id != current_user.id and current_user.role != "admin":
        raise AuthorizationError("You do not have permission to view this import job")

    return ImportStatusResponse(
        success=True,
        job_id=job.id,
        status=job.status,
        target_entity=job.target_entity,
        filename=job.filename,
        total_rows=job.total_rows,
        success_rows=job.success_rows,
        quarantined_rows=job.quarantined_rows,
        error_message=job.error_message,
        is_background=bool(job.is_background),
        created_at=str(job.created_at) if job.created_at else None,
        updated_at=str(job.updated_at) if job.updated_at else None,
    )


# ── 4. View Quarantined Rows ─────────────────────────────────────────────────

@router.get("/jobs/{job_id}/quarantine", response_model=QuarantineListResponse)
def get_quarantined_rows(
    job_id: int,
    limit: int = Query(200, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Retrieve rows quarantined during import with reasons."""
    service = DataImportService(db)
    job = service.import_repo.get_job(job_id)
    if not job:
        raise NotFoundError("DataImportJob", job_id)

    if current_user.org_id is None or job.org_id != current_user.org_id:
        raise AuthorizationError("Import job does not belong to your organization")
    if job.uploaded_by_user_id != current_user.id and current_user.role != "admin":
        raise AuthorizationError("You do not have permission to view this import job")

    rows = service.import_repo.get_quarantined_rows(job_id=job_id, limit=limit, skip=skip)
    total_count = service.import_repo.count_quarantined(job_id=job_id)

    items = [
        QuarantineRowItem(
            id=r.id,
            row_number=r.row_number,
            raw_data=r.raw_data,
            reason=r.reason,
            field_name=r.field_name,
            confidence_score=r.confidence_score,
            created_at=str(r.created_at) if r.created_at else None,
        )
        for r in rows
    ]

    return QuarantineListResponse(
        success=True,
        job_id=job.id,
        total_quarantined=total_count,
        rows=items,
    )
