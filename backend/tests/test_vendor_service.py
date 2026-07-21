"""
Vendor service tests — Excel upload parsing and processing.

Tests the application/vendor_service.py module.
"""

import pytest
from io import BytesIO
from unittest.mock import Mock, patch

from app.application.vendor_service import VendorService


class TestVendorService:
    """Test vendor service Excel parsing logic."""

    @pytest.fixture
    def service(self, db):
        """Create vendor service with test database."""
        return VendorService(db)

    def test_parse_excel_missing_openpyxl(self, service):
        """Parse Excel without openpyxl should return error."""
        with patch.dict('sys.modules', {'openpyxl': None}):
            result = service.parse_and_process_excel(
                file_content=b"fake",
                filename="test.xlsx",
                location_id=1,
                vendor_user_id=1,
            )
            assert result["success"] is False
            assert "openpyxl" in result["error"]

    def test_parse_excel_invalid_file(self, service):
        """Parse invalid Excel file should return error."""
        result = service.parse_and_process_excel(
            file_content=b"not an excel file",
            filename="test.xlsx",
            location_id=1,
            vendor_user_id=1,
        )
        assert result["success"] is False

    def test_get_uploads_for_vendor_empty(self, service):
        """Get uploads for vendor with no uploads should return empty list."""
        uploads = service.get_uploads_for_vendor(vendor_user_id=999)
        assert uploads == []

    def test_get_uploads_for_vendor(self, service, db):
        """Get uploads for vendor should return upload history."""
        from app.infrastructure.database.models import VendorUpload
        
        upload = VendorUpload(
            vendor_user_id=1,
            filename="test.xlsx",
            location_id=1,
            total_rows=10,
            success_rows=8,
            error_rows=2,
            status="COMPLETED_WITH_ERRORS",
        )
        db.add(upload)
        db.commit()
        
        uploads = service.get_uploads_for_vendor(vendor_user_id=1)
        assert len(uploads) == 1
        assert uploads[0]["filename"] == "test.xlsx"
        assert uploads[0]["success_rows"] == 8


class TestHasLocationAccess:
    """Test _has_location_access helper in vendor routes."""

    def test_location_access_unrestricted(self):
        from app.api.routes.vendor import _has_location_access
        user = Mock(location_ids=None)
        assert _has_location_access(user, 1) is True

        user_empty = Mock(location_ids=[])
        assert _has_location_access(user_empty, 1) is True

    def test_location_access_list_of_ints(self):
        from app.api.routes.vendor import _has_location_access
        user = Mock(location_ids=[1, 2, 5])
        assert _has_location_access(user, 1) is True
        assert _has_location_access(user, 3) is False

    def test_location_access_list_of_strings(self):
        from app.api.routes.vendor import _has_location_access
        user = Mock(location_ids=["1", "2", "5"])
        assert _has_location_access(user, 1) is True
        assert _has_location_access(user, 3) is False

    def test_location_access_json_string(self):
        from app.api.routes.vendor import _has_location_access
        user = Mock(location_ids='[1, 2, 5]')
        assert _has_location_access(user, 2) is True
        assert _has_location_access(user, 4) is False

