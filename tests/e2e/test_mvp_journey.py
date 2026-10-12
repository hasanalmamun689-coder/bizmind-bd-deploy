"""
Browser end-to-end test of the MASTER PROMPT section 49 acceptance journey, driven through the real UI.

Prerequisites: PostgreSQL running, demo data seeded (database/seed/seed.py --reset),
API on :8000 (CORS_ORIGINS=http://localhost:3000) and the built frontend on :3000.
Run from the repo root:  python3 tests/e2e/test_mvp_journey.py
"""
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

WEB = "http://localhost:3000"
SHOTS = Path(__file__).resolve().parents[2] / "docs" / "screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)
problems: list[str] = []
steps: list[str] = []


def step(name: str) -> None:
    steps.append(name)
    print(f"  ok  {name}")


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1366, "height": 850})
    page = ctx.new_page()
    page.on("console", lambda m: m.type == "error" and "401" not in m.text and "403" not in m.text and problems.append(f"console: {m.text[:160]}"))
    page.on("pageerror", lambda e: problems.append(f"pageerror: {str(e)[:160]}"))
    page.on("response", lambda r: r.status >= 500 and problems.append(f"HTTP {r.status} {r.url}"))
    page.set_default_timeout(15000)

    # 1. Login (wrong password first -> friendly error)
    page.goto(f"{WEB}/login")
    page.fill("input[type=email]", "owner@demo.bd")
    page.fill("input[type=password]", "wrong-password")
    page.click('button:has-text("Sign in")')
    expect(page.get_by_text("Incorrect email or password.")).to_be_visible()
    step("wrong password shows a friendly error")
    page.fill("input[type=password]", "Demo@1234")
    page.click('button:has-text("Sign in")')
    page.wait_for_url("**/dashboard")
    step("owner can sign in")

    # 2. Dashboard from real data
    expect(page.get_by_text("Estimated profit").first).to_be_visible()
    page.wait_for_selector("svg.recharts-surface", state="visible")
    expect(page.get_by_text("Expense spike").first).to_be_visible()
    step("dashboard shows KPIs, charts and detected risks (expense spike)")
    page.wait_for_timeout(800)
    page.screenshot(path=str(SHOTS / "dashboard.png"), full_page=True)

    # 2b. Sweep: every page loads real data without an error state, console error or 5xx
    ROUTES = ["dashboard", "sales", "products", "inventory", "customers", "suppliers", "procurement", "expenses",
              "analytics", "forecast", "alerts", "recommendations", "ai-assistant", "employees", "audit-logs", "settings"]
    for route in ROUTES:
        page.goto(f"{WEB}/{route}")
        page.wait_for_selector("main h1")
        page.wait_for_timeout(900)
        errs = page.locator("main [role=alert]").all_inner_texts()
        assert not errs, f"/{route} shows an error state: {errs}"
    step(f"all {len(ROUTES)} pages load without error states")
    page.goto(f"{WEB}/customers")
    page.wait_for_selector("tbody tr")
    expect(page.locator("tbody tr").first).to_contain_text("৳")
    step("customers page lists customers with real spend and segments")
    page.screenshot(path=str(SHOTS / "customers.png"), full_page=True)
    page.goto(f"{WEB}/dashboard")

    # 3. Add a product through the UI
    page.click('a:has-text("Products")')
    page.wait_for_url("**/products")
    page.click('button:has-text("Add product")')
    page.fill('label:has-text("Name") input', "E2E Test Lentils 1kg")
    page.fill('label:has-text("SKU") input', "E2E-001")
    page.fill('label:has-text("Purchase price") input', "100")
    page.fill('label:has-text("Selling price") input', "130")
    page.fill('label:has-text("Opening stock") input', "50")
    page.fill('label:has-text("Minimum stock") input', "40")
    page.fill('label:has-text("Maximum stock") input', "200")
    page.click('div[role=dialog] button:has-text("Save")')
    page.fill('input[aria-label="Search products"]', "E2E Test")
    expect(page.get_by_text("E2E Test Lentils 1kg")).to_be_visible()
    expect(page.locator("tr", has_text="E2E Test Lentils 1kg")).to_contain_text("23.08%")
    step("product added; margin (23.08% of selling price) calculated")

    # 4. Record a sale via the UI -> stock drops and becomes Low stock
    page.click('a:has-text("Sales")')
    page.wait_for_url("**/sales")
    page.click('button:has-text("New sale")')
    page.select_option("div[role=dialog] select >> nth=0", label="E2E Test Lentils 1kg (50 in stock)")
    page.fill("div[role=dialog] input[type=number]", "15")
    page.click('div[role=dialog] button:has-text("Record sale")')
    expect(page.get_by_text("Sale recorded. Inventory updated.")).to_be_visible()
    step("sale recorded via UI")
    page.click('a:has-text("Inventory")')
    page.wait_for_url("**/inventory")
    row = page.locator("tr", has_text="E2E Test Lentils 1kg")
    expect(row).to_contain_text("35")
    expect(row).to_contain_text("Low stock")
    step("inventory dropped 50 -> 35 and status flipped to Low stock automatically")
    page.click('a:has-text("Alerts")')
    page.wait_for_url("**/alerts")
    expect(page.get_by_text("E2E Test Lentils 1kg is low stock")).to_be_visible()
    step("low-stock alert generated")

    # 5. Cancel the sale -> stock restored
    page.click('a:has-text("Sales")')
    page.wait_for_url("**/sales")
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Cancel sale").first.click()
    expect(page.get_by_text("Sale cancelled. Stock restored.")).to_be_visible()
    step("sale cancelled; stock restored")

    # 6. Forecast
    page.click('a:has-text("Forecast")')
    page.wait_for_url("**/forecast")
    page.select_option('select[aria-label="Product"]', label="Miniket Rice 5kg")
    expect(page.get_by_text("Expected demand (14d)")).to_be_visible()
    page.wait_for_selector("svg.recharts-surface")
    step("forecast renders demand, stockout estimate and history chart")
    page.select_option('select[aria-label="Product"]', label="E2E Test Lentils 1kg")
    expect(page.get_by_text("Not enough sales history")).to_be_visible()
    step("forecast honestly refuses when there is insufficient data")
    page.select_option('select[aria-label="Product"]', label="Miniket Rice 5kg")
    page.wait_for_timeout(700)
    page.screenshot(path=str(SHOTS / "forecast.png"), full_page=True)

    # 7. AI assistant answers from real data, with evidence
    page.click('a:has-text("AI Assistant")')
    page.wait_for_url("**/ai-assistant")
    page.click('button:has-text("What should I purchase this week?")')
    expect(page.get_by_text("Evidence", exact=True)).to_be_visible()
    expect(page.get_by_text("Reasoning", exact=True)).to_be_visible()
    expect(page.get_by_text("Low Stock Products").first).to_be_visible()
    expect(page.get_by_text("Data-only mode").first).to_be_visible()
    step("AI assistant returns Answer / Evidence / Reasoning and states it is in data-only mode")
    page.wait_for_timeout(500)
    page.screenshot(path=str(SHOTS / "ai-assistant.png"), full_page=True)

    # 8. Recommendation -> human approval -> DRAFT purchase order
    page.click('a:has-text("Recommendations")')
    page.wait_for_url("**/recommendations")
    page.click('button:has-text("Analyze")')
    expect(page.get_by_text("Approve → create purchase draft").first).to_be_visible()
    step("recommendations generated with evidence")
    page.screenshot(path=str(SHOTS / "recommendations.png"), full_page=True)
    page.locator('button:has-text("Approve → create purchase draft")').first.click()
    expect(page.get_by_text("nothing has been ordered")).to_be_visible()
    step("approval created a purchase DRAFT (UI states nothing was ordered)")
    page.click('a:has-text("Procurement")')
    page.wait_for_url("**/procurement")
    expect(page.locator("tr", has_text="From AI recommendation").first).to_contain_text("Draft")
    step("procurement lists the AI-sourced order with status Draft")

    # 9. Audit log recorded it
    page.click('a:has-text("Audit Logs")')
    page.wait_for_url("**/audit-logs")
    expect(page.get_by_text("Recommendation · Approved").first).to_be_visible()
    expect(page.get_by_text("Purchase Draft · Created").first).to_be_visible()
    step("audit log recorded recommendation approval and purchase draft creation")

    # 10. Manager: restricted navigation and blocked pages
    page.click('button:has-text("Sign out")')
    page.wait_for_url("**/login")
    page.fill("input[type=email]", "manager@demo.bd")
    page.fill("input[type=password]", "Demo@1234")
    page.click('button:has-text("Sign in")')
    page.wait_for_url("**/dashboard")
    nav = page.get_by_role("navigation", name="Main")
    expect(nav.get_by_role("link", name="Employees")).to_have_count(0)
    expect(nav.get_by_role("link", name="Audit Logs")).to_have_count(0)
    step("manager's sidebar hides Employees / Audit Logs / Settings")
    page.goto(f"{WEB}/audit-logs")
    expect(page.get_by_text("Only the business owner can view audit logs.")).to_be_visible()
    step("manager is blocked from /audit-logs in the UI (API also returns 403)")

    # 11. Mobile layout
    mobile = browser.new_context(viewport={"width": 390, "height": 800}, is_mobile=True).new_page()
    mobile.on("pageerror", lambda e: problems.append(f"mobile pageerror: {str(e)[:160]}"))
    mobile.set_default_timeout(15000)
    mobile.goto(f"{WEB}/login")
    mobile.fill("input[type=email]", "owner@demo.bd")
    mobile.fill("input[type=password]", "Demo@1234")
    mobile.click('button:has-text("Sign in")')
    mobile.wait_for_url("**/dashboard")
    mobile.wait_for_selector("svg.recharts-surface")
    expect(mobile.get_by_role("button", name="Open menu")).to_be_visible()
    overflow = "document.documentElement.scrollWidth > document.documentElement.clientWidth"
    assert not mobile.evaluate(overflow), "dashboard scrolls horizontally on mobile"
    mobile.screenshot(path=str(SHOTS / "dashboard-mobile.png"))
    step("mobile: hamburger menu present, no horizontal page overflow on the dashboard")
    for path in ("/products", "/sales", "/inventory", "/procurement", "/analytics"):
        mobile.goto(WEB + path)
        mobile.wait_for_timeout(1200)
        assert not mobile.evaluate(overflow), f"page overflows horizontally on mobile: {path}"
    step("mobile: products, sales, inventory, procurement, analytics do not overflow")
    browser.close()

print(f"\n{len(steps)} steps passed.")
if problems:
    print("\nBrowser problems detected:")
    for x in sorted(set(problems)):
        print(" -", x)
    sys.exit(1)
print("No console errors, page errors or 5xx responses.")
