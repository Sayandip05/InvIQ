"""
Test fixtures — SQLite in-memory DB override + TestClient.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENVIRONMENT"] = "testing"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.infrastructure.database.connection import Base
from app.main import app
from app.infrastructure.database.connection import get_db
from app.core.security import hash_password
from app.infrastructure.database.models import User


TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def db():
    session = TestSessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="session")
def client():
    c = TestClient(app)
    yield c


@pytest.fixture(scope="function")
def test_user(db):
    user = db.query(User).filter(User.username == "testuser").first()
    if not user:
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=hash_password("testpass123"),
            full_name="Test User",
            role="staff",
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return {"username": "testuser", "password": "testpass123", "user": user}


@pytest.fixture(scope="function")
def admin_user(db):
    user = db.query(User).filter(User.username == "testadmin").first()
    if not user:
        user = User(
            email="admin@example.com",
            username="testadmin",
            hashed_password=hash_password("adminpass123"),
            full_name="Test Admin",
            role="admin",
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return {"username": "testadmin", "password": "adminpass123", "user": user}


def get_auth_header(client, username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": password,
        },
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
