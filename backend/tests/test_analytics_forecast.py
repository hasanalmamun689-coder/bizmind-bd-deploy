from datetime import datetime, timedelta

from app.db.session import SessionLocal
from app.models.sales import Sale, SaleItem


def _backfill_sales(business_id, product_id, daily_qty, days, price=440, cost=380):
    with SessionLocal() as db:
        for d in range(days, 0, -1):
            ts = datetime.utcnow() - timedelta(days=d)
            s = Sale(business_id=business_id, total_amount=price * daily_qty, total_cost=cost * daily_qty, created_at=ts)
            db.add(s); db.flush()
            db.add(SaleItem(sale_id=s.id, product_id=product_id, quantity=daily_qty, unit_price=price, unit_cost=cost, created_at=ts))
        db.commit()


def _biz_id(client, owner):
    return client.get("/api/auth/me", headers=owner).json()["business_id"]


def test_dashboard_and_profit_calculation(client, owner, product):
    client.post("/api/sales", headers=owner, json={"items": [{"product_id": product["id"], "quantity": 10}]})
    client.post("/api/expenses", headers=owner, json={"category": "rent", "amount": 200, "expense_date": datetime.utcnow().date().isoformat()})
    k = client.get("/api/analytics/dashboard", headers=owner).json()["kpis"]
    assert k["revenue"] == 4400 and k["cost_of_goods_sold"] == 3800
    assert k["gross_profit"] == 600 and k["total_expenses"] == 200 and k["estimated_profit"] == 400
    assert k["inventory_value"] == 90 * 380
    p = client.get("/api/analytics/profit", headers=owner).json()
    assert p["gross_margin_percent"] == 13.64 and p["estimated_profit"] == 400


def test_inventory_analytics_dead_stock(client, owner, product):
    inv = client.get("/api/analytics/inventory", headers=owner).json()
    assert inv["status_breakdown"] == {"healthy": 1}
    assert [d["name"] for d in inv["dead_stock"]] == ["Rice 5kg"]  # stock but never sold


def test_forecast_insufficient_data_is_explicit(client, owner, product):
    f = client.get(f"/api/forecast/{product['id']}?horizon_days=14", headers=owner).json()
    assert f["insufficient_data"] is True and f["predicted_demand"] == 0 and f["estimated_stockout_date"] is None


def test_forecast_generation_with_history(client, owner, product):
    _backfill_sales(_biz_id(client, owner), product["id"], daily_qty=10, days=30)
    f = client.get(f"/api/forecast/{product['id']}?horizon_days=7", headers=owner).json()
    assert f["insufficient_data"] is False and f["model_used"] == "exponential_smoothing"
    assert 65 <= f["predicted_demand"] <= 75          # ~10/day * 7
    # 100 units / ~10 per day = ~10 days of cover -> "moderate" (<=14d), not high (<=7d)
    assert f["risk_level"] == "moderate"
    days_left = (datetime.fromisoformat(f["estimated_stockout_date"]).date() - datetime.utcnow().date()).days
    assert 9 <= days_left <= 11


def test_forecast_rejects_bad_horizon(client, owner, product):
    assert client.get(f"/api/forecast/{product['id']}?horizon_days=5", headers=owner).status_code == 400


def test_risk_detection_says_insufficient_data(client, owner):
    risks = client.get("/api/alerts/risks", headers=owner).json()
    assert risks[0]["risk"] == "Insufficient sales history"


def test_sales_decline_risk_detected(client, owner, product):
    bid = _biz_id(client, owner)
    with SessionLocal() as db:
        for days_ago, amt in ((45, 100000), (10, 30000)):
            db.add(Sale(business_id=bid, total_amount=amt, total_cost=0, created_at=datetime.utcnow() - timedelta(days=days_ago)))
        db.commit()
    risks = client.get("/api/alerts/risks", headers=owner).json()
    decline = next(r for r in risks if r["risk"] == "Sales decline")
    assert decline["evidence"]["change_percent"] == -70.0 and decline["severity"] == "critical"


def test_health_score_shows_components(client, owner, product):
    h = client.get("/api/analytics/health-score", headers=owner).json()
    assert {c["name"] for c in h["components"]} == {"Profitability", "Inventory efficiency", "Supplier performance", "Expense control"}
    assert "not a certified" in h["disclaimer"]


def test_monthly_category_and_movement_analytics(client, owner, product):
    client.post("/api/sales", headers=owner, json={"items": [{"product_id": product["id"], "quantity": 10}]})
    today = datetime.utcnow().date().isoformat()
    client.post("/api/expenses", headers=owner, json={"category": "rent", "amount": 200, "expense_date": today})
    m = client.get("/api/analytics/monthly", headers=owner).json()[-1]
    assert m["revenue"] == 4400 and m["gross_profit"] == 600 and m["expenses"] == 200 and m["estimated_profit"] == 400
    cats = client.get("/api/analytics/categories", headers=owner).json()
    assert cats == [{"category": "Uncategorized", "revenue": 4400.0, "gross_profit": 600.0, "units": 10}]
    mv = client.get("/api/analytics/inventory-movement", headers=owner).json()
    assert mv[-1]["stock_out"] == 10


def test_forecast_history_endpoint(client, owner, product):
    client.post("/api/sales", headers=owner, json={"items": [{"product_id": product["id"], "quantity": 4}]})
    h = client.get(f"/api/forecast/{product['id']}/history", headers=owner).json()
    assert h[-1]["units"] == 4


def test_supplier_price_increase_risk_detected(client, owner, product, supplier):
    bid = _biz_id(client, owner)
    from app.models.supplier import SupplierPriceHistory
    with SessionLocal() as db:
        for days_ago, price in ((60, 300.0), (5, 360.0)):     # +20%
            db.add(SupplierPriceHistory(supplier_id=supplier["id"], product_id=product["id"], price=price,
                                        created_at=datetime.utcnow() - timedelta(days=days_ago)))
        db.commit()
    risks = client.get("/api/alerts/risks", headers=owner).json()
    r = next(x for x in risks if x["risk"].startswith("Supplier price increase"))
    assert r["evidence"]["change_percent"] == 20.0 and "Rice 5kg" in r["risk"] and "ABC Wholesale" in r["risk"]


def test_small_price_change_is_not_flagged(client, owner, product, supplier):
    from app.models.supplier import SupplierPriceHistory
    with SessionLocal() as db:
        for days_ago, price in ((60, 300.0), (5, 309.0)):      # +3%
            db.add(SupplierPriceHistory(supplier_id=supplier["id"], product_id=product["id"], price=price,
                                        created_at=datetime.utcnow() - timedelta(days=days_ago)))
        db.commit()
    assert not any(x["risk"].startswith("Supplier price") for x in client.get("/api/alerts/risks", headers=owner).json())


def test_dead_stock_and_overstock_risks(client, owner, product):
    client.post("/api/inventory/adjust", headers=owner, json={"product_id": product["id"], "type": "stock_in", "quantity": 250})  # 350 > max 300
    names = {x["risk"] for x in client.get("/api/alerts/risks", headers=owner).json()}
    assert {"Dead stock", "Overstock"} <= names


def test_rapid_depletion_risk(client, owner, product):
    bid = _biz_id(client, owner)
    with SessionLocal() as db:
        for d in (10, 14, 18, 22, 26):     # baseline: 60 units per 3 weeks-ish (>=10/wk)
            ts = datetime.utcnow() - timedelta(days=d)
            s = Sale(business_id=bid, total_amount=0, total_cost=0, created_at=ts); db.add(s); db.flush()
            db.add(SaleItem(sale_id=s.id, product_id=product["id"], quantity=12, unit_price=1, unit_cost=1, created_at=ts))
        ts = datetime.utcnow() - timedelta(days=2)
        s = Sale(business_id=bid, total_amount=0, total_cost=0, created_at=ts); db.add(s); db.flush()
        db.add(SaleItem(sale_id=s.id, product_id=product["id"], quantity=60, unit_price=1, unit_cost=1, created_at=ts))
        db.commit()
    risk = next(x for x in client.get("/api/alerts/risks", headers=owner).json() if x["risk"].startswith("Rapid depletion"))
    assert risk["evidence"]["units_last_7d"] == 60
