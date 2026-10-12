def test_supplier_create_and_compare(client, owner, product):
    a = client.post("/api/suppliers", headers=owner, json={"name": "A", "reliability_score": 90, "delivery_time_days": 2}).json()
    b = client.post("/api/suppliers", headers=owner, json={"name": "B", "reliability_score": 50, "delivery_time_days": 6}).json()
    from app.db.session import SessionLocal
    from app.models.supplier import SupplierProduct
    with SessionLocal() as db:
        db.add_all([SupplierProduct(supplier_id=a["id"], product_id=product["id"], price=400, minimum_order_quantity=10),
                    SupplierProduct(supplier_id=b["id"], product_id=product["id"], price=370, minimum_order_quantity=20)])
        db.commit()
    rows = client.get(f"/api/suppliers/compare?product_id={product['id']}", headers=owner).json()
    assert [r["supplier"]["name"] for r in rows] == ["B", "A"]  # sorted by price
    assert "50" in rows[0]["composite_note"] and rows[0]["minimum_order_quantity"] == 20  # evidence shown, not one opaque score


def test_purchase_order_lifecycle_and_invalid_transition(client, owner, product, supplier):
    po = client.post("/api/purchase-orders", headers=owner, json={"supplier_id": supplier["id"],
         "items": [{"product_id": product["id"], "quantity": 20, "unit_price": 380}]}).json()
    assert po["status"] == "draft" and po["total_cost"] == 7600 and po["source"] == "manual"
    bad = client.put(f"/api/purchase-orders/{po['id']}/status", headers=owner, json={"status": "delivered"})
    assert bad.status_code == 400  # cannot skip approval steps
    for s in ("pending_approval",):
        assert client.put(f"/api/purchase-orders/{po['id']}/status", headers=owner, json={"status": s}).status_code == 200
    assert client.post(f"/api/purchase-orders/{po['id']}/approve", headers=owner).json()["status"] == "approved"
    for s in ("ordered", "delivered", "completed"):
        assert client.put(f"/api/purchase-orders/{po['id']}/status", headers=owner, json={"status": s}).status_code == 200


def test_expense_create_edit_and_summary(client, owner):
    e = client.post("/api/expenses", headers=owner, json={"category": "rent", "amount": 16000, "expense_date": "2026-09-01"}).json()
    client.post("/api/expenses", headers=owner, json={"category": "electricity", "amount": 6000, "expense_date": "2026-09-05"})
    u = client.put(f"/api/expenses/{e['id']}", headers=owner, json={"amount": 17000}).json()
    assert u["amount"] == 17000
    s = client.get("/api/expenses/summary", headers=owner).json()
    assert s["by_category"] == {"rent": 17000.0, "electricity": 6000.0}
    assert s["monthly"] == [{"month": "2026-09", "total": 23000.0}]
    assert client.post("/api/expenses", headers=owner, json={"category": "rent", "amount": -5, "expense_date": "2026-09-01"}).status_code == 422


def test_set_supplier_price_and_history(client, owner, product, supplier):
    r = client.put(f"/api/suppliers/{supplier['id']}/prices", headers=owner,
                   json={"product_id": product["id"], "price": 380, "minimum_order_quantity": 20})
    assert r.status_code == 200 and r.json()["price"] == 380
    client.put(f"/api/suppliers/{supplier['id']}/prices", headers=owner, json={"product_id": product["id"], "price": 380})  # unchanged
    client.put(f"/api/suppliers/{supplier['id']}/prices", headers=owner, json={"product_id": product["id"], "price": 400})
    cmp = client.get(f"/api/suppliers/compare?product_id={product['id']}", headers=owner).json()
    assert len(cmp) == 1 and cmp[0]["price"] == 400          # upsert, not duplicate
    from app.db.session import SessionLocal
    from app.models.supplier import SupplierPriceHistory
    with SessionLocal() as db:
        assert db.query(SupplierPriceHistory).count() == 2   # only real changes are logged
    assert client.put(f"/api/suppliers/{supplier['id']}/prices", headers=owner, json={"product_id": product["id"], "price": -1}).status_code == 422


def test_supplier_price_cannot_cross_tenants(client, owner, product, supplier):
    other = client.post("/api/auth/register", json={"business_name": "Other Co", "email": "x@test.bd", "password": "Password123", "full_name": "Xan"}).json()
    oh = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.put(f"/api/suppliers/{supplier['id']}/prices", headers=oh, json={"product_id": product["id"], "price": 1}).status_code == 404
