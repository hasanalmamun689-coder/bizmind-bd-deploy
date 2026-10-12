"""Regression net: every GET endpoint must return 200 on a *populated* business.
(An earlier bug — naive vs aware datetimes — made /api/customers return 500 for any customer with a purchase,
and no test noticed because none listed customers who had sales.)"""
import re
from datetime import datetime, timedelta

from app.db.session import SessionLocal
from app.main import app
from app.models.sales import Sale, SaleItem


def _populate(client, owner):
    cust = client.post("/api/customers", headers=owner, json={"name": "Salma Begum", "contact": "0171"}).json()
    sup = client.post("/api/suppliers", headers=owner, json={"name": "ABC Wholesale"}).json()
    cat = client.post("/api/products/meta/categories", headers=owner, json={"name": "Grocery"}).json()
    prod = client.post("/api/products", headers=owner, json={
        "name": "Rice 5kg", "sku": "R5", "category_id": cat["id"], "supplier_id": sup["id"],
        "purchase_price": 380, "selling_price": 440, "current_stock": 300, "minimum_stock": 40, "maximum_stock": 600}).json()
    client.put(f"/api/suppliers/{sup['id']}/prices", headers=owner, json={"product_id": prod["id"], "price": 385, "minimum_order_quantity": 10})
    sale = client.post("/api/sales", headers=owner, json={"customer_id": cust["id"], "items": [{"product_id": prod["id"], "quantity": 5}]}).json()
    bid = client.get("/api/auth/me", headers=owner).json()["business_id"]
    with SessionLocal() as db:
        for d in range(40, 0, -1):
            ts = datetime.utcnow() - timedelta(days=d)
            s = Sale(business_id=bid, customer_id=cust["id"], total_amount=440 * 4, total_cost=380 * 4, created_at=ts)
            db.add(s); db.flush()
            db.add(SaleItem(sale_id=s.id, product_id=prod["id"], quantity=4, unit_price=440, unit_cost=380, created_at=ts))
        db.commit()
    client.post("/api/expenses", headers=owner, json={"category": "rent", "amount": 1000, "expense_date": datetime.utcnow().date().isoformat()})
    po = client.post("/api/purchase-orders", headers=owner, json={"supplier_id": sup["id"], "items": [{"product_id": prod["id"], "quantity": 10, "unit_price": 385}]}).json()
    client.post("/api/ai/chat", headers=owner, json={"message": "What should I purchase this week?"})
    client.post("/api/ai/recommendations/generate", headers=owner)
    return {"customer_id": cust["id"], "supplier_id": sup["id"], "product_id": prod["id"], "sale_id": sale["id"],
            "order_id": po["id"], "product_id_": prod["id"]}


def test_customers_with_purchases_do_not_crash_and_are_segmented(client, owner, product):
    _populate(client, owner)
    rows = client.get("/api/customers", headers=owner).json()
    assert len(rows) == 1 and rows[0]["total_orders"] == 41 and rows[0]["segment"] == "high-value"
    assert rows[0]["last_purchase_at"] is not None
    assert client.get(f"/api/customers/{rows[0]['id']}", headers=owner).status_code == 200


def test_inactive_customer_segment(client, owner):
    bid = client.get("/api/auth/me", headers=owner).json()["business_id"]
    cust = client.post("/api/customers", headers=owner, json={"name": "Old Customer"}).json()
    with SessionLocal() as db:
        db.add(Sale(business_id=bid, customer_id=cust["id"], total_amount=100, total_cost=50, created_at=datetime.utcnow() - timedelta(days=200)))
        db.commit()
    assert client.get("/api/customers", headers=owner).json()[0]["segment"] == "inactive"


def test_every_get_endpoint_returns_200_on_populated_business(client, owner, manager, product):
    ids = _populate(client, owner)
    ids["product_id"] = ids["product_id"]
    checked = 0
    for route in app.routes:
        methods = getattr(route, "methods", set()) or set()
        path = getattr(route, "path", "")
        if "GET" not in methods or not path.startswith("/api/") or path == "/api/auth/me":
            continue
        url = path
        for name in re.findall(r"{(\w+)}", path):
            key = {"product_id": "product_id", "supplier_id": "supplier_id", "sale_id": "sale_id",
                   "order_id": "order_id", "customer_id": "customer_id"}.get(name)
            assert key, f"add a fixture id for {{{name}}} in {path}"
            url = url.replace("{" + name + "}", ids[key])
        params = {"product_id": ids["product_id"]} if path.endswith("/suppliers/compare") else {}
        r = client.get(url, headers=owner, params=params)
        assert r.status_code == 200, f"GET {url} -> {r.status_code} {r.text[:200]}"
        checked += 1
    assert checked >= 30   # guards against the sweep silently checking nothing
