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

***Template *** [PENDING]
- Make a proper standardized template for XLSX files to be followed by all users.

***Others ***
- Check everything logically & physically, not intermediately.



