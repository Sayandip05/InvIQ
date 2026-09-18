***Dashboard *** [COMPLETED]
- Made all words easy, plain, and user-friendly; removed developer error messages and technical jargon.
- Eradicated all occurrences of "SKU" (replaced with "Total Medicines").
- Simplified the pie chart and removed all green (enforced theme dark/charcoal palette).
- Replaced horizontal pills diagram with a dynamic spline line chart for medicine expiration forecasts.
- Replaced bulky "Total: 310 units" & "High Risk" badges with a compact 6/12 Month selector, reducing header space.
- Removed all hard pharmaceutical & medical words (Analgesics, Cardiovascular, Endocrine, Cold-Chain SOPs, FEFO, Recombinant, Dispensary) across dashboard, preview, and frontend with simple everyday words.

***Billing counter *** [COMPLETED]
- Converted billing counter and barcode scanner into an inactive hardware placeholder with "Placeholder / Coming Soon".

***Inventory *** [COMPLETED]
- Removed all packaging features, packaging tiers, and multipliers from frontend and backend to keep inventory simple and direct.

***Stock acquisition *** [COMPLETED]
- Mixed stock acquisition and requisition gracefully into one unified page with sub-tab switcher ("Upload Delivery Bills" & "Store Stock Orders & Requests").
- Gracefully redirected legacy /admin/requisitions route and removed standalone Requisitions from navigation.
- Fixed data fetching for nearby expired medicines by querying real batch expiry dates (InventoryTransaction.expiry_date) instead of consumption rate days_remaining, plus added /inventory/near-expiry endpoint.

***Template *** [COMPLETED]
- Created official 11-column standardized Excel template (item_name, quantity, unit, batch_number, expiry_date, purchase_rate, mrp, category, storage_temp, delivery_date, invoice_no).
- Implemented deterministic All-or-Nothing dry-run pre-validation with plain language line-by-line error reporting (zero database writes on validation errors).
- Enabled automatic catalog item creation on the fly for missing medicines using manifest pricing, category, and storage details.
- Ensured atomic database transactions with full rollback on failure.
- Eradicated AI from data ingestion and import mapping while keeping agent_service.py untouched.

***Others ***
- Check everything logically & physically, not intermediately.



