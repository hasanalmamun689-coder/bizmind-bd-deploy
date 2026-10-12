export type Role = "owner" | "manager";
export interface User { id: string; business_id: string; email: string; full_name: string; job_title: string | null; role: Role }
export interface TokenResponse { access_token: string; token_type: string; user: User }

export type ProductStatus = "healthy" | "low_stock" | "critical" | "out_of_stock" | "overstock";
export interface Product {
  id: string; name: string; sku: string; category_id: string | null; supplier_id: string | null;
  brand: string | null; unit: string; purchase_price: number; selling_price: number;
  current_stock: number; minimum_stock: number; maximum_stock: number; expiry_date: string | null;
  status: ProductStatus; is_active: boolean; profit_per_unit: number; margin_percent: number; created_at: string;
}
export interface Category { id: string; name: string }
export interface InventoryTxn { id: string; product_id: string; type: string; quantity_delta: number; resulting_stock: number; reason: string | null; created_at: string }
export interface SaleItem { id: string; product_id: string; quantity: number; unit_price: number; unit_cost: number; subtotal: number }
export interface Sale { id: string; customer_id: string | null; total_amount: number; total_cost: number; gross_profit: number; payment_method: string; status: string; created_at: string; items: SaleItem[] }
export interface SalesSummary { total_revenue: number; total_cost: number; gross_profit: number; total_transactions: number; average_order_value: number }
export interface Customer { id: string; name: string; contact: string | null; created_at: string; total_spent: number; total_orders: number; last_purchase_at: string | null; segment: string }
export interface Supplier { id: string; name: string; contact: string | null; location: string | null; delivery_time_days: number; reliability_score: number; quality_score: number; fulfillment_rate: number; payment_terms: string | null; created_at: string }
export interface SupplierComparison { supplier: Supplier; price: number | null; minimum_order_quantity: number | null; composite_note: string }
export interface POItem { id: string; product_id: string; quantity: number; unit_price: number }
export interface PurchaseOrder { id: string; supplier_id: string; status: string; source: string; total_cost: number; expected_delivery_date: string | null; notes: string | null; created_at: string; items: POItem[] }
export interface Expense { id: string; category: string; amount: number; description: string | null; expense_date: string; created_at: string }
export interface ExpenseSummary { by_category: Record<string, number>; monthly: { month: string; total: number }[] }
export interface Kpis {
  total_sales: number; revenue: number; cost_of_goods_sold: number; gross_profit: number; total_expenses: number;
  estimated_profit: number; inventory_value: number; low_stock_items: number; pending_purchases: number; active_customers: number;
}
export interface TopProduct { product_id: string; name: string; units_sold: number; revenue: number }
export interface Dashboard { kpis: Kpis; sales_trend: { date: string; revenue: number; orders: number }[]; top_products: TopProduct[]; unresolved_alerts: number }
export interface ProfitBreakdown { period_days: number; revenue: number; cost_of_goods_sold: number; gross_profit: number; gross_margin_percent: number; operating_expenses: number; estimated_profit: number }
export interface InventoryAnalytics { total_inventory_value: number; status_breakdown: Record<string, number>; dead_stock: { product_id: string; name: string; current_stock: number }[] }
export interface SupplierAnalytics { supplier_id: string; name: string; reliability_score: number; quality_score: number; fulfillment_rate: number; delivery_time_days: number; order_count: number }
export interface HealthScore { overall_score: number; components: { name: string; score: number; detail: string }[]; disclaimer: string }
export interface Forecast { id: string; product_id: string; horizon_days: number; model_used: string; predicted_demand: number; current_stock_at_run: number; estimated_stockout_date: string | null; risk_level: string; insufficient_data: boolean; created_at: string }
export interface Alert { id: string; type: string; severity: "info" | "warning" | "critical"; title: string; description: string; related_entity_type: string | null; related_entity_id: string | null; suggested_action: string | null; status: string; created_at: string }
export interface Risk { risk: string; severity: "info" | "warning" | "critical"; evidence: Record<string, unknown>; explanation: string; recommended_investigation: string }
export interface Recommendation { id: string; type: string; title: string; evidence: Record<string, any>; reasoning: string; suggested_action: string; status: "pending" | "approved" | "rejected"; related_purchase_order_id: string | null; created_at: string }
export interface ChatResponse { conversation_id: string; answer: string; evidence: { tool_results: { tool: string; result?: unknown; error?: string }[] }; reasoning: string; suggested_action: string | null; used_live_model: boolean }
export interface AuditLog { id: string; user_id: string | null; action: string; entity_type: string; entity_id: string | null; log_metadata: Record<string, unknown> | null; created_at: string }
