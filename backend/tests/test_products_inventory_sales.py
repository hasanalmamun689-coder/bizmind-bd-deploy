def test_product_crud_and_margin(client, owner):
    r = client.post("/api/products", headers=owner, json={"name": "Oil 1L", "sku": "OIL1",
                    "purchase_price": 168, "selling_price": 190, "current_stock": 50, "minimum_stock": 20, "maximum_stock": 100})
    assert r.status_code == 201
    p = r.json()
    assert p["profit_per_unit"] == 22 and p["margin_percent"] == 11.58 and p["status"] == "healthy"
    assert client.get(f"/api/products/{p['id']}", headers=owner).status_code == 200
    u = client.put(f"/api/products/{p['id']}", headers=owner, json={"selling_price": 200})
    assert u.json()["profit_per_unit"] == 32
    assert client.delete(f"/api/products/{p['id']}", headers=owner).status_code == 204
    assert client.get(f"/api/products/{p['id']}", headers=owner).json()["is_active"] is False


def test_negative_price_rejected(client, owner):
    r = client.post("/api/products", headers=owner, json={"name": "X", "sku": "X", "purchase_price": -1, "selling_price": 5})
    assert r.status_code == 422


def test_sale_reduces_inventory_and_writes_ledger(client, owner, product):
    r = client.post("/api/sales", headers=owner, json={"items": [{"product_id": product["id"], "quantity": 10}]})
    assert r.status_code == 201
    assert r.json()["total_amount"] == 4400 and r.json()["gross_profit"] == 600
    assert client.get(f"/api/products/{product['id']}", headers=owner).json()["current_stock"] == 90
    hist = client.get(f"/api/inventory/{product['id']}/history", headers=owner).json()
    assert hist[0]["type"] == "sale" and hist[0]["quantity_delta"] == -10 and hist[0]["resulting_stock"] == 90


def test_sale_invalid_product(client, owner):
    r = client.post("/api/sales", headers=owner, json={"items": [{"product_id": "00000000-0000-0000-0000-000000000000", "quantity": 1}]})
    assert r.status_code == 400


def test_sale_invalid_quantity(client, owner, product):
    assert client.post("/api/sales", headers=owner, json={"items": [{"product_id": product["id"], "quantity": 0}]}).status_code == 422
    assert client.post("/api/sales", headers=owner, json={"items": []}).status_code == 422


def test_sale_insufficient_stock_is_atomic(client, owner, product):
    r = client.post("/api/sales", headers=owner, json={"items": [{"product_id": product["id"], "quantity": 5000}]})
    assert r.status_code == 400 and "Insufficient stock" in r.json()["detail"]
    assert client.get(f"/api/products/{product['id']}", headers=owner).json()["current_stock"] == 100
    assert client.get("/api/sales", headers=owner).json() == []


def test_low_stock_detection_and_alert(client, owner, product):
    client.post("/api/sales", headers=owner, json={"items": [{"product_id": product["id"], "quantity": 65}]})
    p = client.get(f"/api/products/{product['id']}", headers=owner).json()
    assert p["current_stock"] == 35 and p["status"] == "low_stock"
    alerts = client.get("/api/inventory/alerts", headers=owner).json()
    assert len(alerts) == 1 and "low stock" in alerts[0]["title"].lower()
    # further sales that stay in the same status must not spam duplicate alerts
    client.post("/api/sales", headers=owner, json={"items": [{"product_id": product["id"], "quantity": 2}]})
    assert len(client.get("/api/inventory/alerts", headers=owner).json()) == 1


def test_stock_in_stock_out_adjustment(client, owner, product):
    r = client.post("/api/inventory/adjust", headers=owner, json={"product_id": product["id"], "type": "stock_in", "quantity": 50})
    assert r.status_code == 201 and r.json()["resulting_stock"] == 150
    r = client.post("/api/inventory/adjust", headers=owner, json={"product_id": product["id"], "type": "stock_out", "quantity": 30, "reason": "damaged"})
    assert r.json()["resulting_stock"] == 120 and r.json()["quantity_delta"] == -30
    assert client.post("/api/inventory/adjust", headers=owner, json={"product_id": product["id"], "type": "stock_in", "quantity": 0}).status_code == 422


def test_overstock_and_out_of_stock_status(client, owner, product):
    client.post("/api/inventory/adjust", headers=owner, json={"product_id": product["id"], "type": "stock_in", "quantity": 250})
    assert client.get(f"/api/products/{product['id']}", headers=owner).json()["status"] == "overstock"
    client.post("/api/sales", headers=owner, json={"items": [{"product_id": product["id"], "quantity": 350}]})
    assert client.get(f"/api/products/{product['id']}", headers=owner).json()["status"] == "out_of_stock"


def test_sales_summary(client, owner, product):
    client.post("/api/sales", headers=owner, json={"items": [{"product_id": product["id"], "quantity": 5}]})
    client.post("/api/sales", headers=owner, json={"items": [{"product_id": product["id"], "quantity": 5}]})
    s = client.get("/api/sales/summary", headers=owner).json()
    assert s["total_transactions"] == 2 and s["total_revenue"] == 4400 and s["average_order_value"] == 2200


def test_manual_adjustment_can_correct_up_or_down(client, owner, product):
    up = client.post("/api/inventory/adjust", headers=owner, json={"product_id": product["id"], "type": "adjustment", "direction": "increase", "quantity": 5, "reason": "count higher"}).json()
    assert up["quantity_delta"] == 5 and up["resulting_stock"] == 105
    down = client.post("/api/inventory/adjust", headers=owner, json={"product_id": product["id"], "type": "adjustment", "quantity": 8}).json()
    assert down["quantity_delta"] == -8 and down["resulting_stock"] == 97


def test_cancel_sale_restores_stock_and_excludes_from_analytics(client, owner, product):
    sale = client.post("/api/sales", headers=owner, json={"items": [{"product_id": product["id"], "quantity": 10}]}).json()
    assert client.get(f"/api/products/{product['id']}", headers=owner).json()["current_stock"] == 90
    r = client.post(f"/api/sales/{sale['id']}/cancel", headers=owner)
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    assert client.get(f"/api/products/{product['id']}", headers=owner).json()["current_stock"] == 100
    # revenue no longer counts it, and the ledger shows the reversal
    assert client.get("/api/analytics/dashboard", headers=owner).json()["kpis"]["revenue"] == 0
    assert client.get("/api/sales/summary", headers=owner).json()["total_transactions"] == 0
    hist = client.get(f"/api/inventory/{product['id']}/history", headers=owner).json()
    assert hist[0]["quantity_delta"] == 10 and hist[0]["resulting_stock"] == 100
    # cannot cancel twice (would double-restore stock)
    assert client.post(f"/api/sales/{sale['id']}/cancel", headers=owner).status_code == 400
    assert client.get(f"/api/products/{product['id']}", headers=owner).json()["current_stock"] == 100
    assert "sale.cancelled" in [a["action"] for a in client.get("/api/audit-logs", headers=owner).json()]


def test_cancelled_sale_does_not_inflate_forecast(client, owner, product):
    from datetime import datetime, timedelta
    from app.db.session import SessionLocal
    from app.models.sales import Sale, SaleItem, SaleStatus
    bid = client.get("/api/auth/me", headers=owner).json()["business_id"]
    with SessionLocal() as db:
        for d in range(20, 0, -1):
            ts = datetime.utcnow() - timedelta(days=d)
            s = Sale(business_id=bid, total_amount=0, total_cost=0, created_at=ts, status=SaleStatus.CANCELLED)
            db.add(s); db.flush()
            db.add(SaleItem(sale_id=s.id, product_id=product["id"], quantity=50, unit_price=1, unit_cost=1, created_at=ts))
        db.commit()
    f = client.get(f"/api/forecast/{product['id']}?horizon_days=7", headers=owner).json()
    assert f["insufficient_data"] is True   # only cancelled sales exist -> no real demand history


def test_duplicate_sku_rejected_within_business_but_allowed_across_businesses(client, owner, product):
    dup = client.post("/api/products", headers=owner, json={"name": "Other", "sku": "RICE5", "purchase_price": 1, "selling_price": 2})
    assert dup.status_code == 409 and "RICE5" in dup.json()["detail"]
    assert len(client.get("/api/products", headers=owner).json()) == 1
    other = client.post("/api/auth/register", json={"business_name": "Other Co", "email": "o3@test.bd", "password": "Password123", "full_name": "Olu"}).json()
    oh = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.post("/api/products", headers=oh, json={"name": "Rice", "sku": "RICE5", "purchase_price": 1, "selling_price": 2}).status_code == 201
