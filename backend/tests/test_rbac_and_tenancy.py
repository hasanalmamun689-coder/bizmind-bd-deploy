def test_owner_only_endpoints_block_manager(client, owner, manager):
    assert client.get("/api/employees", headers=owner).status_code == 200
    assert client.get("/api/employees", headers=manager).status_code == 403
    assert client.get("/api/audit-logs", headers=manager).status_code == 403
    assert client.get("/api/audit-logs", headers=owner).status_code == 200


def test_manager_can_use_operational_endpoints(client, manager, product):
    assert client.get("/api/products", headers=manager).status_code == 200
    r = client.post("/api/sales", headers=manager, json={"items": [{"product_id": product["id"], "quantity": 1}]})
    assert r.status_code == 201


def test_only_owner_can_approve_purchase_order(client, owner, manager, product, supplier):
    po = client.post("/api/purchase-orders", headers=manager, json={
        "supplier_id": supplier["id"], "items": [{"product_id": product["id"], "quantity": 10, "unit_price": 380}]}).json()
    client.put(f"/api/purchase-orders/{po['id']}/status", headers=manager, json={"status": "pending_approval"})
    assert client.post(f"/api/purchase-orders/{po['id']}/approve", headers=manager).status_code == 403
    r = client.post(f"/api/purchase-orders/{po['id']}/approve", headers=owner)
    assert r.status_code == 200 and r.json()["status"] == "approved"


def test_only_owner_can_delete_expense(client, owner, manager):
    e = client.post("/api/expenses", headers=manager, json={"category": "rent", "amount": 100, "expense_date": "2026-09-01"}).json()
    assert client.delete(f"/api/expenses/{e['id']}", headers=manager).status_code == 403
    assert client.delete(f"/api/expenses/{e['id']}", headers=owner).status_code == 204


def test_tenant_isolation(client, owner, product):
    other = client.post("/api/auth/register", json={"business_name": "Other", "email": "o2@test.bd",
                        "password": "Password123", "full_name": "O2"}).json()
    other_h = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get(f"/api/products/{product['id']}", headers=other_h).status_code == 404
    assert client.get("/api/products", headers=other_h).json() == []
    r = client.post("/api/sales", headers=other_h, json={"items": [{"product_id": product["id"], "quantity": 1}]})
    assert r.status_code == 400


def test_settings_owner_only_and_never_leaks_secrets(client, owner, manager):
    assert client.get("/api/settings", headers=manager).status_code == 403
    s = client.get("/api/settings", headers=owner).json()
    assert s["system"]["ai_mode"] == "deterministic_fallback"
    assert "key" not in str(s).lower()
    u = client.put("/api/settings/business", headers=owner, json={"name": "New Name", "address": "Dhaka"}).json()
    assert u["business"]["name"] == "New Name"
    assert client.put("/api/settings/business", headers=manager, json={"name": "Hack"}).status_code == 403
    assert "settings.business_updated" in [a["action"] for a in client.get("/api/audit-logs", headers=owner).json()]
