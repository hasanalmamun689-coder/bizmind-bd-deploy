from datetime import datetime, timedelta

from app.db.session import SessionLocal
from app.models.sales import Sale, SaleItem
from app.models.supplier import SupplierProduct
from app.models.procurement import PurchaseOrder


def _make_critical_scenario(client, owner, product, supplier):
    """Rice sells ~12/day with 30 in stock -> high stockout risk, with a supplier offering it."""
    bid = client.get("/api/auth/me", headers=owner).json()["business_id"]
    with SessionLocal() as db:
        for d in range(30, 0, -1):
            ts = datetime.utcnow() - timedelta(days=d)
            s = Sale(business_id=bid, total_amount=440 * 12, total_cost=380 * 12, created_at=ts)
            db.add(s); db.flush()
            db.add(SaleItem(sale_id=s.id, product_id=product["id"], quantity=12, unit_price=440, unit_cost=380, created_at=ts))
        db.add(SupplierProduct(supplier_id=supplier["id"], product_id=product["id"], price=385, minimum_order_quantity=20))
        db.commit()
    client.put(f"/api/products/{product['id']}", headers=owner, json={"minimum_stock": 40})
    client.post("/api/inventory/adjust", headers=owner, json={"product_id": product["id"], "type": "stock_out", "quantity": 70})


def test_chat_uses_real_data_and_returns_evidence(client, owner, product):
    client.post("/api/sales", headers=owner, json={"items": [{"product_id": product["id"], "quantity": 10}]})
    r = client.post("/api/ai/chat", headers=owner, json={"message": "Which products are selling fastest?"}).json()
    assert r["used_live_model"] is False
    tools = {t["tool"] for t in r["evidence"]["tool_results"]}
    assert {"get_sales_summary", "get_product_sales"} <= tools
    top = next(t for t in r["evidence"]["tool_results"] if t["tool"] == "get_product_sales")["result"]["top_products"]
    assert top[0]["name"] == "Rice 5kg" and top[0]["units_sold"] == 10   # real number, not invented
    assert r["reasoning"] and r["answer"]


def test_chat_with_empty_business_does_not_fabricate(client, owner):
    r = client.post("/api/ai/chat", headers=owner, json={"message": "Why did my profit decrease?"}).json()
    profit = next(t for t in r["evidence"]["tool_results"] if t["tool"] == "calculate_profit")["result"]
    assert profit["revenue"] == 0 and profit["estimated_profit"] == 0


def test_chat_risk_question_reports_insufficient_evidence(client, owner):
    r = client.post("/api/ai/chat", headers=owner, json={"message": "What are my biggest business risks?"}).json()
    risks = next(t for t in r["evidence"]["tool_results"] if t["tool"] == "get_business_risks")["result"]["risks"]
    assert risks[0]["risk"] == "Insufficient sales history"


def test_ai_tool_registry_is_closed_and_read_only():
    from app.services.ai.tools import TOOL_REGISTRY
    assert "create_purchase_draft" not in TOOL_REGISTRY          # AI cannot create orders itself
    assert not any("sql" in name or "execute" in name for name in TOOL_REGISTRY)


def test_unknown_tool_is_rejected():
    from app.services.ai.orchestrator import _run_tools
    from app.services.ai.provider import ToolCall
    out = _run_tools(None, None, [ToolCall(name="drop_all_tables")])
    assert out[0]["error"] == "unknown tool"


def test_chat_persists_conversation_and_audit(client, owner):
    r = client.post("/api/ai/chat", headers=owner, json={"message": "Which products are selling fastest?"}).json()
    r2 = client.post("/api/ai/chat", headers=owner, json={"conversation_id": r["conversation_id"], "message": "customers?"}).json()
    assert r2["conversation_id"] == r["conversation_id"]
    actions = [a["action"] for a in client.get("/api/audit-logs", headers=owner).json()]
    assert actions.count("ai.chat") == 2


def test_recommendation_requires_approval_and_creates_only_a_draft(client, owner, manager, product, supplier):
    _make_critical_scenario(client, owner, product, supplier)
    recs = client.post("/api/ai/recommendations/generate", headers=owner).json()
    assert len(recs) == 1 and recs[0]["status"] == "pending"
    ev = recs[0]["evidence"]
    assert ev["current_stock"] == 30 and ev["risk_level"] in ("high", "critical")
    assert ev["recommended_supplier"]["supplier"] == "ABC Wholesale" and ev["estimated_cost"] > 0
    assert "not a guarantee" in recs[0]["reasoning"]

    # Nothing is ordered before a human decides.
    with SessionLocal() as db:
        assert db.query(PurchaseOrder).count() == 0

    po = client.post(f"/api/ai/recommendations/{recs[0]['id']}/approve", headers=manager).json()
    assert po["status"] == "draft" and po["source"] == "ai_recommendation"     # DRAFT, never 'ordered'
    assert po["items"][0]["quantity"] == ev["suggested_quantity"]
    assert client.post(f"/api/ai/recommendations/{recs[0]['id']}/approve", headers=owner).status_code == 400  # no double-approve

    actions = [a["action"] for a in client.get("/api/audit-logs", headers=owner).json()]
    assert "recommendation.approved" in actions and "purchase_draft.created" in actions


def test_reject_recommendation_creates_no_order(client, owner, product, supplier):
    _make_critical_scenario(client, owner, product, supplier)
    rec = client.post("/api/ai/recommendations/generate", headers=owner).json()[0]
    r = client.post(f"/api/ai/recommendations/{rec['id']}/reject", headers=owner).json()
    assert r["status"] == "rejected"
    assert client.get("/api/purchase-orders", headers=owner).json() == []


def test_no_recommendation_when_insufficient_data(client, owner, product, supplier):
    assert client.post("/api/ai/recommendations/generate", headers=owner).json() == []
