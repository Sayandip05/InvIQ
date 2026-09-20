"""
Supplier / Distributor API endpoint tests.
"""

import pytest
from tests.conftest import get_auth_header


class TestSupplierManagement:
    """Tests for Admin managing medicine suppliers/distributors."""

    def test_list_suppliers(self, client, admin_user):
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        response = client.get("/api/admin/suppliers", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

    def test_create_and_update_supplier(self, client, admin_user):
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        
        # 1. Create Supplier
        payload = {
            "name": "Shree Pharma Distributors",
            "username": "shreepharma_test",
            "email": "shree_test@pharma.com",
            "password": "vendorSecret123!",  # meets stricter policy: upper+lower+digit+special
            "phone": "+91 98765 43210",
        }
        create_res = client.post("/api/admin/suppliers", json=payload, headers=headers)
        assert create_res.status_code == 200
        created_data = create_res.json()
        assert created_data["success"] is True
        supplier_id = created_data["data"]["id"]
        assert created_data["data"]["name"] == "Shree Pharma Distributors"

        # 2. Update Supplier
        update_payload = {
            "name": "Shree Pharma Wholesale Agency",
            "email": "shree_updated@pharma.com",
        }
        update_res = client.put(f"/api/admin/suppliers/{supplier_id}", json=update_payload, headers=headers)
        assert update_res.status_code == 200
        assert update_res.json()["data"]["name"] == "Shree Pharma Wholesale Agency"

        # 3. Delete / Deactivate Supplier
        del_res = client.delete(f"/api/admin/suppliers/{supplier_id}", headers=headers)
        assert del_res.status_code == 200
        assert del_res.json()["success"] is True

    def test_create_supplier_without_password_generates_temporary_password(self, client, admin_user):
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        payload = {
            "name": "Auto Pass Distributors",
            "username": "autopass_vendor",
            "email": "autopass@pharma.com",
        }
        res = client.post("/api/admin/suppliers", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "temporary_password" in data["data"]
        assert len(data["data"]["temporary_password"]) >= 12

    def test_create_supplier_with_weak_password_fails(self, client, admin_user):
        headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        payload = {
            "name": "Weak Pass Agency",
            "username": "weak_vendor",
            "email": "weak@pharma.com",
            "password": "123",  # Too short
        }
        res = client.post("/api/admin/suppliers", json=payload, headers=headers)
        assert res.status_code in [400, 422]

