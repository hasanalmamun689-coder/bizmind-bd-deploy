"""
Seed realistic Bangladesh SME demo data (BDT) — section 31/32.
Run:  cd backend && python ../database/seed/seed.py
Demo logins (password: Demo@1234):  owner@demo.bd  /  manager@demo.bd

Data is internally consistent: every stock level equals opening stock + stock-ins - sales +/- adjustments,
and each movement has an inventory_transactions row. Patterns included: growing, declining, seasonal,
low/critical/overstock, dead stock, expense spike, recent sales decline, one unreliable supplier.
"""
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlalchemy import select  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import *  # noqa: E402,F401,F403

random.seed(42)
NOW = datetime.utcnow()
DAYS = 180

CATEGORIES = ["Grocery Staples", "Cooking Oil & Ghee", "Beverages", "Snacks & Biscuits",
              "Household", "Personal Care", "Stationery"]

# name, category idx, unit, purchase, selling, pattern, target_stock_state
PRODUCTS = [
    ("Miniket Rice 5kg", 0, "bag", 385, 440, "steady", "low"),
    ("Nazirshail Rice 25kg", 0, "bag", 1850, 2050, "growing", "critical"),
    ("Atta Flour 2kg", 0, "pack", 88, 105, "steady", "ok"),
    ("Moong Dal 1kg", 0, "pack", 145, 170, "seasonal", "ok"),
    ("Masoor Dal 1kg", 0, "pack", 118, 140, "steady", "ok"),
    ("Chickpeas 1kg", 0, "pack", 105, 125, "declining", "over"),
    ("Sugar 1kg", 0, "pack", 118, 135, "growing", "low"),
    ("Salt 1kg", 0, "pack", 32, 40, "steady", "ok"),
    ("Turmeric Powder 200g", 0, "pack", 70, 90, "steady", "ok"),
    ("Chilli Powder 200g", 0, "pack", 85, 110, "steady", "ok"),
    ("Soybean Oil 5L", 1, "bottle", 810, 890, "growing", "critical"),
    ("Soybean Oil 1L", 1, "bottle", 168, 190, "steady", "ok"),
    ("Mustard Oil 1L", 1, "bottle", 245, 280, "seasonal", "ok"),
    ("Ghee 500g", 1, "tin", 520, 600, "steady", "ok"),
    ("Mineral Water 1.5L", 2, "bottle", 26, 35, "seasonal", "ok"),
    ("Mango Juice 1L", 2, "pack", 75, 95, "seasonal", "over"),
    ("Cola 2L", 2, "bottle", 82, 100, "steady", "ok"),
    ("Orange Drink 250ml", 2, "bottle", 18, 25, "declining", "ok"),
    ("Tea Leaves 400g", 2, "pack", 210, 250, "steady", "ok"),
    ("Instant Coffee 100g", 2, "jar", 265, 320, "steady", "ok"),
    ("Malted Drink 500g", 2, "jar", 340, 395, "growing", "ok"),
    ("Cream Biscuits 200g", 3, "pack", 42, 55, "steady", "ok"),
    ("Salted Crackers 150g", 3, "pack", 34, 45, "steady", "ok"),
    ("Potato Chips 50g", 3, "pack", 22, 30, "growing", "ok"),
    ("Chocolate Wafer 30g", 3, "pack", 14, 20, "declining", "ok"),
    ("Instant Noodles 5pk", 3, "pack", 88, 110, "growing", "low"),
    ("Chanachur 200g", 3, "pack", 48, 65, "steady", "ok"),
    ("Toffee Jar 300g", 3, "jar", 95, 130, "steady", "dead"),
    ("Laundry Powder 1kg", 4, "pack", 118, 145, "steady", "ok"),
    ("Dishwash Liquid 500ml", 4, "bottle", 72, 95, "steady", "ok"),
    ("Floor Cleaner 1L", 4, "bottle", 115, 150, "steady", "ok"),
    ("Toilet Tissue 4pk", 4, "pack", 95, 125, "steady", "ok"),
    ("Mosquito Coil 10pc", 4, "pack", 38, 50, "seasonal", "ok"),
    ("Matchbox 10pk", 4, "pack", 20, 30, "steady", "over"),
    ("Bath Soap 100g", 5, "pcs", 32, 42, "steady", "ok"),
    ("Shampoo 340ml", 5, "bottle", 235, 290, "steady", "ok"),
    ("Toothpaste 150g", 5, "tube", 92, 115, "steady", "ok"),
    ("Toothbrush", 5, "pcs", 28, 40, "steady", "ok"),
    ("Talcum Powder 100g", 5, "tin", 88, 115, "declining", "dead"),
    ("Hair Oil 200ml", 5, "bottle", 110, 140, "steady", "ok"),
    ("Face Wash 100ml", 5, "tube", 165, 215, "growing", "ok"),
    ("Exercise Book 200pg", 6, "pcs", 42, 60, "seasonal", "ok"),
    ("Ball Pen Blue (10pk)", 6, "pack", 55, 80, "steady", "ok"),
    ("Pencil HB (12pk)", 6, "pack", 60, 85, "steady", "ok"),
    ("A4 Paper Ream", 6, "ream", 430, 500, "steady", "ok"),
    ("Marker Pen Black", 6, "pcs", 22, 35, "steady", "ok"),
    ("Glue Stick", 6, "pcs", 24, 38, "steady", "dead"),
    ("Geometry Box", 6, "pcs", 68, 95, "seasonal", "ok"),
    ("Sanitary Pads 8pc", 5, "pack", 78, 100, "growing", "ok"),
    ("Baby Diaper M 20pc", 4, "pack", 620, 720, "steady", "ok"),
    ("Hand Sanitizer 100ml", 5, "bottle", 65, 90, "declining", "over"),
]

SUPPLIERS = [
    ("ABC Wholesale", "Chawkbazar, Dhaka", 2, 92, 90, 96, "Net 15"),
    ("Karim Traders", "Khatunganj, Chattogram", 3, 88, 85, 93, "Net 30"),
    ("Dhaka Grocery Depot", "Mouchak, Dhaka", 1, 90, 88, 95, "Cash on delivery"),
    ("Rahman Oil & Foods", "Narayanganj", 2, 84, 86, 91, "Net 15"),
    ("Sylhet Agro Supply", "Zindabazar, Sylhet", 4, 79, 82, 88, "Net 30"),
    ("Khulna Distribution Co.", "Khulna Sadar", 3, 86, 84, 92, "Net 21"),
    ("Metro Household Supplies", "Tejgaon, Dhaka", 2, 91, 89, 94, "Net 15"),
    ("Star Stationery House", "Nilkhet, Dhaka", 2, 89, 90, 95, "Cash on delivery"),
    ("Prime Personal Care Ltd", "Gulshan, Dhaka", 3, 87, 91, 93, "Net 30"),
    ("Bogura Bulk Traders", "Bogura", 5, 52, 70, 74, "Advance payment"),  # unreliable
]
# category idx -> supplier idxs able to supply it
CAT_SUPPLIERS = {0: [0, 1, 2, 9], 1: [3, 0, 5], 2: [0, 2, 6], 3: [2, 6, 1], 4: [6, 2], 5: [8, 6], 6: [7]}

CUSTOMER_NAMES = [
    "Mahmud Store", "Salma Begum", "Rafiq Uddin", "Nasrin Akter", "Habib General Store", "Jahanara Khatun",
    "Kamal Hossain", "Shirin Sultana", "Bismillah Mudi Dokan", "Anwar Hossain", "Fatema Tuz Zohra",
    "Tanvir Ahmed", "Rokeya Begum", "Mizanur Rahman", "Sumaiya Akter", "Delwar Hossain", "Lutfa Begum",
    "Al-Amin Traders", "Farhana Yasmin", "Sohel Rana", "Monira Khatun", "Abdul Jalil", "Rina Akter",
    "Shahjahan Mia", "Taslima Nasrin", "Golam Mostafa", "Ayesha Siddika", "Babul Hossain", "Nurjahan Begum",
    "Hasan Mahmud", "Sabina Yeasmin", "Mostafizur Rahman", "Champa Rani Das", "Nazrul Islam", "Runa Laila",
    "Jamal Uddin", "Khadija Begum", "Ibrahim Khalil", "Shapla Restaurant", "Moushumi Akter", "Belal Hossain",
    "Parveen Sultana", "Alamgir Kabir", "Nilufar Yasmin", "Mohsin Ali", "Rumana Afroz", "Sagor Ahmed",
    "Happy Tea Stall", "Dolon Chapa", "Kabir Hossain", "Sharmin Akter", "Ruhul Amin", "Green Valley Canteen",
]


def growth_factor(pattern: str, day_index: int, dt: datetime) -> float:
    """Multiplier on base daily demand. day_index 0 = oldest day."""
    t = day_index / DAYS
    if pattern == "growing":
        return 0.6 + 1.0 * t
    if pattern == "declining":
        return 1.4 - 1.0 * t
    if pattern == "seasonal":
        return 1.0 + 0.5 * (1 if dt.month in (4, 5, 6) else -0.2 if dt.month in (11, 12, 1) else 0)
    return 1.0


def reset(db) -> None:
    from sqlalchemy import text
    tables = [t.name for t in Base.metadata.sorted_tables]
    db.execute(text("TRUNCATE TABLE " + ", ".join(tables) + " RESTART IDENTITY CASCADE"))
    db.commit()
    print("Database cleared.")


def main() -> None:
    db = SessionLocal()
    if "--reset" in sys.argv:
        reset(db)
    if db.scalar(select(User).where(User.email == "owner@demo.bd")):
        print("Demo data already present — skipping.")
        return

    biz = Business(name="Rahman General Store & Wholesale", industry="Retail / Wholesale grocery",
                   currency="BDT", address="Mirpur, Dhaka")
    db.add(biz)
    db.flush()
    owner = User(business_id=biz.id, email="owner@demo.bd", password_hash=hash_password("Demo@1234"),
                 full_name="Abdur Rahman", job_title="Owner", role=UserRole.OWNER)
    manager = User(business_id=biz.id, email="manager@demo.bd", password_hash=hash_password("Demo@1234"),
                   full_name="Nusrat Jahan", job_title="Store Manager", role=UserRole.MANAGER)
    db.add_all([owner, manager])

    cats = [Category(business_id=biz.id, name=n) for n in CATEGORIES]
    db.add_all(cats)
    sups = [Supplier(business_id=biz.id, name=n, location=loc, contact=f"+8801{random.randint(700000000, 999999999)}",
                     delivery_time_days=d, reliability_score=r, quality_score=q, fulfillment_rate=f, payment_terms=pt)
            for n, loc, d, r, q, f, pt in SUPPLIERS]
    db.add_all(sups)
    customers = [Customer(business_id=biz.id, name=n, contact=f"+8801{random.randint(300000000, 999999999)}")
                 for n in CUSTOMER_NAMES]
    db.add_all(customers)
    db.flush()

    products, meta = [], {}
    for i, (name, ci, unit, pp, sp, pattern, state) in enumerate(PRODUCTS):
        sup_idx = CAT_SUPPLIERS[ci][0]
        base_daily = random.choice([2, 3, 4, 5, 6, 8, 10]) if pattern != "steady" or state != "dead" else 0
        p = Product(business_id=biz.id, category_id=cats[ci].id, supplier_id=sups[sup_idx].id, name=name,
                    sku=f"SKU-{1000 + i}", brand=None, unit=unit, purchase_price=pp, selling_price=sp,
                    current_stock=0, minimum_stock=0, maximum_stock=0,
                    expiry_date=(date.today() + timedelta(days=random.randint(60, 400))) if ci in (0, 1, 2, 3, 5) else None)
        products.append(p)
        meta[i] = {"pattern": pattern, "state": state, "base": base_daily}
    db.add_all(products)
    db.flush()

    # Supplier-product prices (>=2 suppliers per product; slight price differences)
    for i, p in enumerate(products):
        ci = PRODUCTS[i][1]
        for j, si in enumerate(CAT_SUPPLIERS[ci][:3]):
            offer = round(float(p.purchase_price) * (1 + random.uniform(-0.03, 0.06) + 0.02 * j), 2)
            if si == 9:  # unreliable supplier is cheapest — a trap for naive price-only choices
                offer = round(float(p.purchase_price) * 0.93, 2)
            db.add(SupplierProduct(supplier_id=sups[si].id, product_id=p.id, price=offer,
                                   minimum_order_quantity=random.choice([10, 12, 20, 24, 50])))
            # Price history: most suppliers are stable; ABC Wholesale raised prices on the first few
            # products in the last 3 weeks (a genuine supplier-cost anomaly for the AI to explain).
            old_price = offer
            if si == 0 and i in (0, 6, 10):
                old_price = round(offer / random.uniform(1.18, 1.22), 2)
            db.add(SupplierPriceHistory(supplier_id=sups[si].id, product_id=p.id, price=old_price,
                                        created_at=NOW - timedelta(days=75)))
            if old_price != offer:
                db.add(SupplierPriceHistory(supplier_id=sups[si].id, product_id=p.id, price=offer,
                                            created_at=NOW - timedelta(days=18)))

    # ---- Simulate 180 days of sales, tracking stock ----
    stock = {}
    for i, p in enumerate(products):
        opening = meta[i]["base"] * 60 + 200 if meta[i]["state"] != "dead" else 60
        stock[i] = opening
        db.add(InventoryTransaction(business_id=biz.id, product_id=p.id, created_by=owner.id,
                                    type=InventoryTransactionType.STOCK_IN, quantity_delta=opening,
                                    resulting_stock=opening, reason="Opening stock",
                                    created_at=NOW - timedelta(days=DAYS)))

    restocks = {}
    for d in range(DAYS):
        day = NOW - timedelta(days=DAYS - d)
        n_sales = random.randint(6, 14)
        for _ in range(n_sales):
            sale_time = day.replace(hour=random.randint(9, 20), minute=random.randint(0, 59))
            lines, chosen = [], random.sample(range(len(products)), k=random.randint(1, 4))
            for i in chosen:
                m = meta[i]
                if m["state"] == "dead" and d > DAYS - 75:
                    continue  # dead stock: nothing sells in the last 75 days
                base = m["base"] or 1
                f = growth_factor(m["pattern"], d, sale_time)
                if d > DAYS - 30 and i in (5, 17, 24, 39, 8):  # recent sales-decline scenario
                    f *= 0.35
                qty = max(1, round(base * f * random.uniform(0.3, 1.0)))
                if stock[i] < qty:
                    # restock event (recorded) so history stays realistic
                    add = base * 40 + 100
                    stock[i] += add
                    db.add(InventoryTransaction(business_id=biz.id, product_id=products[i].id, created_by=manager.id,
                                                type=InventoryTransactionType.STOCK_IN, quantity_delta=add,
                                                resulting_stock=stock[i], reason="Supplier delivery", created_at=sale_time))
                lines.append((i, qty))
            if not lines:
                continue
            cust = random.choice(customers) if random.random() < 0.7 else None
            sale = Sale(business_id=biz.id, customer_id=cust.id if cust else None, created_by=manager.id,
                        payment_method=random.choice(["cash", "cash", "bkash", "card"]), created_at=sale_time)
            db.add(sale)
            db.flush()
            total = cost = 0.0
            for i, qty in lines:
                p = products[i]
                db.add(SaleItem(sale_id=sale.id, product_id=p.id, quantity=qty,
                                unit_price=p.selling_price, unit_cost=p.purchase_price, created_at=sale_time))
                stock[i] -= qty
                total += float(p.selling_price) * qty
                cost += float(p.purchase_price) * qty
                db.add(InventoryTransaction(business_id=biz.id, product_id=p.id, created_by=manager.id,
                                            type=InventoryTransactionType.SALE, quantity_delta=-qty,
                                            resulting_stock=stock[i], reason=f"Sale {sale.id}",
                                            related_sale_id=sale.id, created_at=sale_time))
            sale.total_amount, sale.total_cost = total, cost
        if d % 25 == 0:
            db.flush()

    # ---- Land each product in its intended stock state via a recorded adjustment ----
    for i, p in enumerate(products):
        base = meta[i]["base"] or 1
        state = meta[i]["state"]
        min_stock = max(20, base * 12)
        max_stock = min_stock * 4
        target = {"low": int(min_stock * 0.8), "critical": int(min_stock * 0.3),
                  "over": int(max_stock * 1.4), "dead": int(min_stock * 3), "ok": int(min_stock * 2)}[state]
        if state == "low":
            target = max(int(min_stock * 0.7), 1)
        p.minimum_stock, p.maximum_stock = min_stock, max_stock
        delta = target - stock[i]
        p.current_stock = target
        p.recompute_status()
        db.add(InventoryTransaction(business_id=biz.id, product_id=p.id, created_by=owner.id,
                                    type=InventoryTransactionType.ADJUSTMENT, quantity_delta=delta,
                                    resulting_stock=target, reason="Physical stock count reconciliation",
                                    created_at=NOW - timedelta(hours=2)))
        if p.status in (ProductStatus.LOW_STOCK, ProductStatus.CRITICAL, ProductStatus.OUT_OF_STOCK):
            db.add(Alert(business_id=biz.id, type="inventory",
                         severity=AlertSeverity.CRITICAL if p.status != ProductStatus.LOW_STOCK else AlertSeverity.WARNING,
                         title=f"{p.name} is {p.status.value.replace('_', ' ')}",
                         description=f"Current stock is {p.current_stock} vs minimum {p.minimum_stock}.",
                         related_entity_type="product", related_entity_id=p.id,
                         suggested_action="Review the forecast and consider a purchase order."))
        if p.status == ProductStatus.OVERSTOCK:
            db.add(Alert(business_id=biz.id, type="inventory", severity=AlertSeverity.INFO,
                         title=f"{p.name} is overstocked",
                         description=f"Stock {p.current_stock} exceeds maximum {p.maximum_stock}; capital is tied up.",
                         related_entity_type="product", related_entity_id=p.id,
                         suggested_action="Consider a promotion or pausing reorders."))

    # ---- Expenses: 6 months, with a recent electricity/marketing spike ----
    for m in range(6, -1, -1):
        month_start = (NOW.replace(day=1) - timedelta(days=30 * m)).date().replace(day=1)
        fixed = [(ExpenseCategory.RENT, 16000, "Shop rent"), (ExpenseCategory.SALARY, 24000, "Staff salaries"),
                 (ExpenseCategory.ELECTRICITY, random.randint(5500, 7000), "Electricity bill"),
                 (ExpenseCategory.TRANSPORTATION, random.randint(6000, 8500), "Delivery & transport"),
                 (ExpenseCategory.MAINTENANCE, random.randint(1200, 3000), "Shop maintenance"),
                 (ExpenseCategory.MARKETING, random.randint(2000, 3500), "Flyers & promotions")]
        for cat, amt, desc in fixed:
            if m == 0 and cat in (ExpenseCategory.ELECTRICITY, ExpenseCategory.MARKETING):
                amt = int(amt * 3.2)  # anomaly
                desc += " (unusually high)"
            dte = min(month_start + timedelta(days=random.randint(1, 27)), date.today())
            db.add(Expense(business_id=biz.id, created_by=owner.id, category=cat, amount=amt,
                           description=desc, expense_date=dte))

    # ---- Purchase history ----
    for k in range(6):
        s = sups[k % 4]
        prods = random.sample(products, 3)
        po = PurchaseOrder(business_id=biz.id, supplier_id=s.id, created_by=manager.id, approved_by=owner.id,
                           status=PurchaseOrderStatus.COMPLETED, source=PurchaseOrderSource.MANUAL,
                           expected_delivery_date=(NOW - timedelta(days=20 * k + 5)).date(),
                           created_at=NOW - timedelta(days=20 * k + 9))
        db.add(po)
        db.flush()
        tot = 0
        for p in prods:
            q = random.choice([50, 100, 120])
            db.add(PurchaseOrderItem(purchase_order_id=po.id, product_id=p.id, quantity=q, unit_price=p.purchase_price))
            tot += q * float(p.purchase_price)
        po.total_cost = tot
    db.add(PurchaseOrder(business_id=biz.id, supplier_id=sups[0].id, created_by=manager.id,
                         status=PurchaseOrderStatus.PENDING_APPROVAL, total_cost=38400,
                         expected_delivery_date=date.today() + timedelta(days=2), notes="Weekly rice restock"))

    audit_seed = AuditLog(business_id=biz.id, user_id=owner.id, action="demo.seeded", entity_type="business",
                          entity_id=biz.id, log_metadata={"note": "Demo dataset generated"})
    db.add(audit_seed)
    db.commit()
    print("Seeded:", len(products), "products,", len(sups), "suppliers,", len(customers), "customers.")
    print("Login: owner@demo.bd / Demo@1234   |   manager@demo.bd / Demo@1234")


if __name__ == "__main__":
    main()
