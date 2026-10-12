def test_register_and_me(client):
    r = client.post("/api/auth/register", json={"business_name": "Shop", "email": "a@b.bd",
                    "password": "Password123", "full_name": "Ann"})
    assert r.status_code == 201
    token = r.json()["access_token"]
    assert r.json()["user"]["role"] == "owner"
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == "a@b.bd"


def test_password_is_hashed(client):
    from sqlalchemy import select
    from app.db.session import SessionLocal
    from app.models.user import User
    client.post("/api/auth/register", json={"business_name": "Shop", "email": "h@b.bd",
                "password": "Password123", "full_name": "Hana"})
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.email == "h@b.bd"))
        assert u.password_hash != "Password123" and u.password_hash.startswith("$2")


def test_duplicate_email_rejected(client):
    body = {"business_name": "Shop", "email": "d@b.bd", "password": "Password123", "full_name": "Dan"}
    assert client.post("/api/auth/register", json=body).status_code == 201
    assert client.post("/api/auth/register", json=body).status_code == 400


def test_short_password_rejected(client):
    r = client.post("/api/auth/register", json={"business_name": "Shop", "email": "s@b.bd",
                    "password": "short", "full_name": "S"})
    assert r.status_code == 422


def test_login_invalid_credentials(client, owner):
    r = client.post("/api/auth/login", json={"email": "owner@test.bd", "password": "wrongpass1"})
    assert r.status_code == 401
    assert "Incorrect" in r.json()["detail"]


def test_protected_routes_require_token(client):
    for path in ("/api/products", "/api/sales", "/api/analytics/dashboard", "/api/ai/recommendations"):
        assert client.get(path).status_code == 401
    assert client.get("/api/products", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_validation_errors_are_friendly_and_leak_no_internals(client, owner):
    r = client.get("/api/products/not-a-uuid", headers=owner)
    assert r.status_code == 422 and r.json()["detail"] == "Invalid input: product id is not a valid identifier."
    r = client.post("/api/products", headers=owner, json={"name": "x"})
    assert "sku is required" in r.json()["detail"]
    for text in (r.text, client.get("/api/products/not-a-uuid", headers=owner).text):
        assert "Traceback" not in text and "sqlalchemy" not in text.lower() and "urn:uuid" not in text
