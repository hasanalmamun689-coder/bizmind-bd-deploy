import os

# Must be set BEFORE the app is imported so tests never touch the dev database.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg2://smeuser:smepassword@localhost:5432/sme_intelligence_test"
)
os.environ["AI_PROVIDER"] = "none"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402
import app.models as _models  # noqa: E402,F401


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture(autouse=True)
def _clean():
    yield
    with engine.begin() as conn:
        names = ", ".join(t.name for t in Base.metadata.sorted_tables)
        conn.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client():
    return TestClient(app)


def _register(client, email, business="Test Store"):
    r = client.post("/api/auth/register", json={
        "business_name": business, "email": email, "password": "Password123",
        "full_name": "Test Owner"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def owner(client):
    return _register(client, "owner@test.bd")


@pytest.fixture
def manager(client, owner):
    r = client.post("/api/employees", headers=owner, json={
        "email": "mgr@test.bd", "password": "Password123", "full_name": "Mgr", "role": "manager"})
    assert r.status_code == 201, r.text
    login = client.post("/api/auth/login", json={"email": "mgr@test.bd", "password": "Password123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture
def product(client, owner):
    r = client.post("/api/products", headers=owner, json={
        "name": "Rice 5kg", "sku": "RICE5", "purchase_price": 380, "selling_price": 440,
        "current_stock": 100, "minimum_stock": 40, "maximum_stock": 300})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def supplier(client, owner):
    r = client.post("/api/suppliers", headers=owner, json={"name": "ABC Wholesale", "delivery_time_days": 2})
    assert r.status_code == 201, r.text
    return r.json()
