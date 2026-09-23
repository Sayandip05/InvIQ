📋 Core Backend Features to Test Manually
1. Unified Stock Acquisition & Excel Manifest Upload
(Location in UI: Stock Acquisition -> Upload Delivery Bills)

Test 1A: Dry-Run Pre-Validation (All-or-Nothing)
Upload an Excel file with an intentional error (e.g., negative quantity, an invalid expiry date format, or empty medicine name).
Expected Behavior: The system shows a clear line-by-line error summary and writes zero rows to the database (full rollback).
Test 1B: Valid Delivery Manifest Ingestion
Upload a valid 11-column Excel file (item_name, quantity, unit, batch_number, expiry_date, purchase_rate, mrp, category, storage_temp, delivery_date, invoice_no).
Click Confirm & Ingest.
Expected Behavior:
Success banner with total items added.
New medicine catalog entries are created automatically on the fly if they didn't exist before.
Stock balances update in the inventory ledger under the designated location.
2. Store Stock Requests & Requisitions
(Location in UI: Stock Acquisition -> Store Stock Orders & Requests)

Test 2A: Staff Requisition Creation
Log in or select Counter 1 / Counter 2.
Request a quantity of a medicine from the Central Warehouse.
Expected Behavior: The requisition is saved with status PENDING.
Test 2B: Approval & Stock Transfer
As Admin, open the pending request and click Approve.
Expected Behavior:
Status updates to APPROVED.
Stock is deducted from the source location and credited to the target counter.
Test 2C: Rejection Audit Trail
Create another request and click Reject, entering a reason (e.g., "Insufficient warehouse stock").
Expected Behavior:
Status updates to REJECTED.
approved_by remains empty/null, and the rejection reason is saved.
3. Inventory Catalog & Direct Stock Adjustment
(Location in UI: Inventory)

Test 3A: Add New Medicine & Batches
Click Add Medicine, fill in Name, Category, Storage Type (e.g., Room Temp vs Cold Storage), and Reorder Level.
Save and verify it appears in the catalog table.
Test 3B: Stock In / Stock Out (Audit Ledger)
Adjust stock manually: record an entry for Received (e.g., +20 units) and Issued (e.g., -5 units).
Expected Behavior: Opening stock, incoming/outgoing qty, and closing stock calculate accurately in the ledger without discrepancies.
4. Expiry Forecast & Near-Expiry Batches
(Location in UI: Dashboard & Near-Expiry Tab)

Test 4A: Expiry Horizon Switcher
On the Dashboard, toggle the 6 Month / 12 Month selector on the Expiry Forecast chart.
Expected Behavior: Spline line graph dynamically updates showing projected batches nearing expiration based on real batch dates (expiry_date), not estimated consumption math.
Test 4B: Health Status Distribution
Check the Stock Health summary cards (CRITICAL, WARNING, HEALTHY).
Expected Behavior: Numbers load reliably without any 500 error or page crash.
5. Real-Time Alert Notifications (WebSockets)
(Location in UI: Top Bar -> Bell Icon)

Test 5A: Live Expiry & Shortage Alerts
Open DevTools (Network tab -> filter WS). Verify ws://localhost:8000/api/v1/ws/... is connected (101 Switching Protocols).
Open the notification dropdown.
Expected Behavior: Batches nearing expiration (within 30/60 days) appear with badge counts and risk indicators.
6. AI Chemist Assistant (Groq LLaMA 3.3)
(Location in UI: AI Assistant / Chat)

Test 6A: Live Stock Inquiries
Open the AI Assistant and ask:
"What medicines are currently low on stock?"
"Which batches are expiring in the next 60 days?"
"Do we have any cold storage medicines?"
Expected Behavior: The AI responds quickly using live inventory data from your Supabase database.