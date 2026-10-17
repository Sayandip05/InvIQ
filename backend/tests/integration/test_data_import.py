"""
Unit and integration tests for Data Import endpoints and service layer.
"""

import io
import pytest
from app.infrastructure.database.models import Location, Item, InventoryTransaction, DataImportJob, ImportQuarantineRow
from app.application.data_import_service import DataImportService
from app.application.data_import_mapper import DataImportMapper
from tests.conftest import get_auth_header


def test_inspect_csv_file():
    csv_content = b"item_name,quantity,date,batch_number\nParacetamol 500mg,100,2026-03-28,BT-01\nAmoxicillin 250mg,50,2026-03-28,BT-02\n"
    headers, sample_rows, total_rows = DataImportService.inspect_file(csv_content, "test.csv")

    assert headers == ["item_name", "quantity", "date", "batch_number"]
    assert len(sample_rows) == 2
    assert total_rows == 2
    assert sample_rows[0]["item_name"] == "Paracetamol 500mg"


def test_heuristic_mapper():
    mapper = DataImportMapper()
    headers = ["Item Name", "Quantity Received", "Transaction Date", "Batch #"]
    sample_rows = [{"Item Name": "Paracetamol", "Quantity Received": "100", "Transaction Date": "2026-03-28", "Batch #": "B1"}]
    
    result = mapper.map_columns(headers, sample_rows, "inventory_transaction")
    mappings = result["mappings"]

    assert mappings["Item Name"]["target_field"] == "item_name"
    assert mappings["Quantity Received"]["target_field"] == "received"
    assert mappings["Transaction Date"]["target_field"] == "date"
    assert mappings["Batch #"]["target_field"] == "batch_number"


import openpyxl


def _create_excel(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def test_upload_and_preview_endpoint(client, test_user, db):
    auth_header = get_auth_header(client, test_user["username"], test_user["password"])

    excel_content = _create_excel([
        ["Medicine", "Quantity", "Date"],
        ["Ibuprofen 400mg", 200, "2026-04-01"]
    ])
    files = {"file": ("medicines.xlsx", io.BytesIO(excel_content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}

    response = client.post(
        "/api/data-import/upload?target_entity=inventory_transaction",
        headers=auth_header,
        files=files,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "job_id" in data
    assert data["filename"] == "medicines.xlsx"
    assert data["total_rows"] == 1
    assert "mapping_result" in data


def test_confirm_import_and_quarantine(client, test_user, db):
    auth_header = get_auth_header(client, test_user["username"], test_user["password"])

    # Create location
    loc = db.query(Location).filter(Location.name == "Import Test Clinic").first()
    if not loc:
        loc = Location(name="Import Test Clinic", type="clinic", region="North", org_id=1)
        db.add(loc)
        db.commit()
        db.refresh(loc)
    elif loc.org_id != 1:
        loc.org_id = 1
        db.commit()
        db.refresh(loc)


    # Valid row + invalid quantity row
    excel_content = _create_excel([
        ["Item Name", "Received", "Date"],
        ["Cough Syrup 100ml", 50, "2026-04-10"],
        ["Invalid Item", "NOT_A_NUMBER", "2026-04-10"],
    ])
    files = {"file": ("mixed.xlsx", io.BytesIO(excel_content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}

    upload_res = client.post(
        "/api/data-import/upload?target_entity=inventory_transaction",
        headers=auth_header,
        files=files,
    )
    job_id = upload_res.json()["job_id"]

    # Confirm
    confirm_res = client.post(
        "/api/data-import/confirm",
        headers=auth_header,
        json={
            "job_id": job_id,
            "default_location_id": loc.id,
        },
    )

    assert confirm_res.status_code == 200
    res_data = confirm_res.json()
    assert res_data["success"] is True
    assert res_data["total_rows"] == 2
    assert res_data["success_rows"] == 1
    assert res_data["quarantined_rows"] == 1
    assert res_data["status"] == "PARTIAL"

    # Check job status endpoint
    status_res = client.get(f"/api/data-import/jobs/{job_id}", headers=auth_header)
    assert status_res.status_code == 200
    assert status_res.json()["success_rows"] == 1

    # Check quarantine endpoint
    quarantine_res = client.get(f"/api/data-import/jobs/{job_id}/quarantine", headers=auth_header)
    assert quarantine_res.status_code == 200
    q_data = quarantine_res.json()
    assert q_data["total_quarantined"] == 1
    assert q_data["rows"][0]["reason"] == "VALIDATION_ERROR"


def test_execute_import_azure_blob_fallback(db, test_user):
    """When job.file_content is empty, execute_import downloads from Azure Blob Storage."""
    from unittest.mock import patch, Mock
    from app.application.data_import_service import DataImportService
    from app.infrastructure.database.data_import_repo import DataImportRepository
    from app.infrastructure.database.models import DataImportJob, Location

    loc = db.query(Location).filter(Location.org_id == 1).first()
    if not loc:
        loc = Location(name="Blob Test Location", type="clinic", region="South", org_id=1)
        db.add(loc)
        db.commit()
        db.refresh(loc)

    repo = DataImportRepository(db)
    csv_bytes = b"item_name,received,date\nAmoxicillin 500mg,25,2026-05-01\n"

    # Create job with NULL file_content but valid file_blob_path
    job = repo.create_job(
        uploaded_by_user_id=test_user["user"].id,
        filename="remote_upload.csv",
        file_content=None,
        file_blob_path="imports/2026/08/remote_upload.csv",
        target_entity="inventory_transaction",
        mapping_result={
            "mappings": {
                "item_name": {"target_field": "item_name", "confidence": 1.0},
                "received": {"target_field": "received", "confidence": 1.0},
                "date": {"target_field": "date", "confidence": 1.0},
            }
        },
        org_id=1,
    )

    service = DataImportService(db)

    # 1. Mock Azure Blob Storage service returning CSV bytes
    mock_storage = Mock()
    mock_storage.download_file.return_value = csv_bytes

    with patch("app.infrastructure.storage.azure_blob_storage.get_storage_service", return_value=mock_storage):
        updated_job = service.execute_import(
            job_id=job.id,
            confirmed_mapping=job.mapping_result,
            default_location_id=loc.id,
        )
        assert updated_job.status in ["COMPLETED", "PARTIAL"]
        assert updated_job.success_rows == 1
        mock_storage.download_file.assert_called_once_with("imports/2026/08/remote_upload.csv")
