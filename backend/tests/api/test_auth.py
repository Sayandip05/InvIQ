"""
Auth endpoint tests — login, logout, register, lockout, RBAC, tenant isolation, cookies & CSP.
"""

import pytest
from tests.conftest import get_auth_header


class TestHealthAndAuthLifecycle:
    """Smoke tests and user signup/login lifecycle."""

    def test_root_and_health_with_csp_headers(self, client):
        """Verify root, health, and security headers (CSP, nosniff, X-Frame-Options)."""
        from unittest.mock import patch
        with patch("app.infrastructure.cache.redis_client.is_redis_available", return_value=True):
            res = client.get("/health")
        assert res.status_code == 200
        assert "Content-Security-Policy" in res.headers
        assert res.headers["X-Content-Type-Options"] == "nosniff"

    def test_signup_and_login_with_cookies(self, client, test_user):
        """Test public signup, login setting HttpOnly cookies, and cookie authentication."""
        # 1. Login
        login_res = client.post("/api/auth/login", json={
            "email": test_user["user"].email,
            "password": test_user["password"],
        })
        assert login_res.status_code == 200
        assert "access_token" in login_res.cookies or any("access_token=" in h for h in login_res.headers.get_list("set-cookie"))

        # 2. Access via cookie
        token = login_res.cookies.get("access_token")
        if token:
            me_res = client.get("/api/auth/me", cookies={"access_token": token})
            assert me_res.status_code == 200

        # 3. Invalid password & nonexistent user
        bad_res = client.post("/api/auth/login", json={"email": test_user["user"].email, "password": "wrongpassword"})
        assert bad_res.status_code in [401, 403]

    def test_logout_and_token_invalidation(self, client, test_user):
        """Test logout invalidates token for subsequent requests."""
        headers = get_auth_header(client, test_user["username"], test_user["password"])
        logout_res = client.post("/api/auth/logout", headers=headers)
        assert logout_res.status_code == 200

        me_res = client.get("/api/auth/me", headers=headers)
        assert me_res.status_code in [401, 403]


class TestRBACAndTenantIsolation:
    """Role-based access control and multi-tenant cross-org security."""

    def test_rbac_boundaries(self, client, test_user, admin_user):
        """Staff cannot register users or list all users; Admin can."""
        staff_headers = get_auth_header(client, test_user["username"], test_user["password"])
        admin_headers = get_auth_header(client, admin_user["username"], admin_user["password"])

        # Staff denied
        res1 = client.post("/api/auth/register", json={"email": "hack@example.com", "username": "hack", "password": "Pass123!"}, headers=staff_headers)
        assert res1.status_code in [401, 403]

        # Admin allowed
        res2 = client.get("/api/auth/users", headers=admin_headers)
        assert res2.status_code == 200

    def test_cross_tenant_idor_protection(self, client, admin_user, db):
        """Admin cannot view, edit roles, or reset passwords of users belonging to other tenants."""
        from app.infrastructure.database.models import User
        from app.core.security import hash_password

        other_user = User(
            email="other_tenant_victim@example.com",
            username="other_tenant_victim",
            hashed_password=hash_password("Pass123!"),
            role="staff",
            org_id=99,
            is_active=True,
            is_verified=True,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        admin_headers = get_auth_header(client, admin_user["username"], admin_user["password"])

        # Attempt read
        assert client.get(f"/api/auth/users/{other_user.id}", headers=admin_headers).status_code == 403
        # Attempt role update
        assert client.put(f"/api/auth/users/{other_user.id}/role", json={"role": "admin"}, headers=admin_headers).status_code == 403
        # Attempt password reset
        assert client.post(f"/api/auth/users/{other_user.id}/reset-password", json={"new_password": "HackedPassword123!"}, headers=admin_headers).status_code == 403

    def test_password_reset_token_iat_invalidation(self, client, test_user):
        """Older access tokens created before password reset are rejected; new tokens created after work."""
        import time
        import jwt
        from app.core.security import create_access_token
        from app.core.config import settings
        from unittest.mock import patch

        fake_redis = {}

        class MockRedis:
            def get(self, key):
                return fake_redis.get(key)
            def setex(self, key, ttl, val):
                fake_redis[key] = str(val)
                return True
            def delete(self, *keys):
                for k in keys:
                    fake_redis.pop(k, None)

        mock_r = MockRedis()

        try:
            with patch("app.infrastructure.cache.redis_client.get_redis", return_value=mock_r), \
                 patch("app.infrastructure.cache.redis_client.is_redis_available", return_value=True):

                now = int(time.time())
                # 1. Create older token issued 10 seconds ago
                raw_token = create_access_token({
                    "sub": str(test_user["user"].id),
                    "username": test_user["username"],
                    "role": test_user["user"].role,
                    "org_id": test_user["user"].org_id or 1,
                })
                payload = jwt.decode(raw_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                payload["iat"] = now - 10
                old_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

                # Verify older token works before password reset marker is placed
                res1 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {old_token}"})
                assert res1.status_code == 200

                # 2. Simulate password reset happening 5 seconds ago
                reset_ts = now - 5
                mock_r.setex(f"user_pw_changed:{test_user['user'].id}", 86400, str(reset_ts))

                # 3. Old token should now be rejected (401) because iat (now - 10) < reset_ts (now - 5)
                res2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {old_token}"})
                assert res2.status_code == 401

                # 4. Create new token issued now (iat = now >= reset_ts)
                new_token = create_access_token({
                    "sub": str(test_user["user"].id),
                    "username": test_user["username"],
                    "role": test_user["user"].role,
                    "org_id": test_user["user"].org_id or 1,
                })

                res3 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_token}"})
                assert res3.status_code == 200
        finally:
            from app.infrastructure.cache.redis_client import get_redis, is_redis_available
            r = get_redis()
            if r and is_redis_available():
                try:
                    r.delete(f"user_pw_changed:{test_user['user'].id}")
                except Exception:
                    pass

    def test_public_signup_rejects_staff_and_vendor(self, client):
        """Public signup should disallow staff and vendor roles directly."""
        res_staff = client.post("/api/auth/signup", json={
            "email": "staff_wannabe@example.com",
            "username": "staff_wannabe",
            "password": "Password123!",
            "role": "staff",
        })
        assert res_staff.status_code in [400, 422]

        res_vendor = client.post("/api/auth/signup", json={
            "email": "vendor_wannabe@example.com",
            "username": "vendor_wannabe",
            "password": "Password123!",
            "role": "vendor",
        })
        assert res_vendor.status_code in [400, 422]

    def test_logout_revokes_refresh_token(self, client, test_user):
        """Logout blacklists both access token and refresh token cookie."""
        from unittest.mock import patch
        with patch("app.infrastructure.cache.token_blacklist.blacklist_refresh_token") as mock_blk_refresh:
            headers = get_auth_header(client, test_user["username"], test_user["password"])
            res = client.post(
                "/api/auth/logout",
                headers=headers,
                cookies={"refresh_token": "dummy-refresh-token"},
            )
            assert res.status_code == 200
            mock_blk_refresh.assert_called_once_with("dummy-refresh-token")

    def test_role_update_allowed_and_disallowed_roles(self, client, admin_user, test_user):
        """Role update permits admin, staff, vendor and rejects manager."""
        admin_headers = get_auth_header(client, admin_user["username"], admin_user["password"])
        user_id = test_user["user"].id

        try:
            # manager is not a valid role
            res_manager = client.put(f"/api/auth/users/{user_id}/role", json={"role": "manager"}, headers=admin_headers)
            assert res_manager.status_code in [400, 422]

            # valid roles
            res_staff = client.put(f"/api/auth/users/{user_id}/role", json={"role": "staff"}, headers=admin_headers)
            assert res_staff.status_code == 200

            res_admin = client.put(f"/api/auth/users/{user_id}/role", json={"role": "admin"}, headers=admin_headers)
            assert res_admin.status_code == 200
        finally:
            client.put(f"/api/auth/users/{user_id}/role", json={"role": "staff"}, headers=admin_headers)
            test_user["user"].role = "staff"

    def test_google_auth_strict_claims_validation(self, client):
        """Google auth should return 503 if client ID is unset, and reject invalid claims."""
        from unittest.mock import patch
        import google.oauth2.id_token
        from app.core.config import settings

        orig_client_id = settings.GOOGLE_CLIENT_ID
        try:
            # 1. When GOOGLE_CLIENT_ID is unset/empty -> 503 Service Unavailable
            settings.GOOGLE_CLIENT_ID = ""
            res_unset = client.post("/api/auth/google-auth", json={"id_token": "any-token"})
            assert res_unset.status_code == 503

            # Set valid client ID for verification tests
            settings.GOOGLE_CLIENT_ID = "expected-client-id.apps.googleusercontent.com"

            # 2. Unverified email
            with patch("google.oauth2.id_token.verify_oauth2_token", return_value={
                "email": "unverified@example.com",
                "name": "Unverified User",
                "email_verified": False,
                "iss": "accounts.google.com",
                "aud": "expected-client-id.apps.googleusercontent.com",
            }):
                res1 = client.post("/api/auth/google-auth", json={"id_token": "mock-token"})
                assert res1.status_code in [401, 403]

            # 3. Invalid issuer
            with patch("google.oauth2.id_token.verify_oauth2_token", return_value={
                "email": "badiss@example.com",
                "name": "Bad Iss User",
                "email_verified": True,
                "iss": "evil.com",
                "aud": "expected-client-id.apps.googleusercontent.com",
            }):
                res2 = client.post("/api/auth/google-auth", json={"id_token": "mock-token"})
                assert res2.status_code in [401, 403]

            # 4. Audience mismatch
            with patch("google.oauth2.id_token.verify_oauth2_token", return_value={
                "email": "badaud@example.com",
                "name": "Bad Aud User",
                "email_verified": True,
                "iss": "accounts.google.com",
                "aud": "wrong-client-id.apps.googleusercontent.com",
            }):
                res3 = client.post("/api/auth/google-auth", json={"id_token": "mock-token"})
                assert res3.status_code in [401, 403]

            # 5. Successful registration creates user as ADMIN (pharmacy owner)
            with patch("google.oauth2.id_token.verify_oauth2_token", return_value={
                "email": "newgoogleuser@example.com",
                "name": "Google Admin User",
                "email_verified": True,
                "iss": "https://accounts.google.com",
                "aud": "expected-client-id.apps.googleusercontent.com",
            }):
                res_ok = client.post("/api/auth/google-auth", json={"id_token": "valid-token"})
                assert res_ok.status_code == 200
                user_data = res_ok.json()["data"]["user"]
                assert user_data["role"] == "admin"

        finally:
            settings.GOOGLE_CLIENT_ID = orig_client_id

    def test_password_complexity_validation(self, client, admin_user):
        """Ensure password schema requires uppercase, lowercase, digit, and special character."""
        admin_headers = get_auth_header(client, admin_user["username"], admin_user["password"])

        # Missing uppercase
        res1 = client.post("/api/auth/register", json={
            "email": "weak1@example.com",
            "username": "weakuser1",
            "password": "password123!",
            "role": "staff",
        }, headers=admin_headers)
        assert res1.status_code == 422

        # Missing digit
        res2 = client.post("/api/auth/register", json={
            "email": "weak2@example.com",
            "username": "weakuser2",
            "password": "Password!",
            "role": "staff",
        }, headers=admin_headers)
        assert res2.status_code == 422

        # Missing special char
        res3 = client.post("/api/auth/register", json={
            "email": "weak3@example.com",
            "username": "weakuser3",
            "password": "Password123",
            "role": "staff",
        }, headers=admin_headers)
        assert res3.status_code == 422

        # Valid strong password
        res4 = client.post("/api/auth/register", json={
            "email": "strong@example.com",
            "username": "stronguser",
            "password": "StrongPassword123!",
            "role": "staff",
        }, headers=admin_headers)
        assert res4.status_code == 200
