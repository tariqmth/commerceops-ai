
# Inventory Discrepancy Investigation

## Purpose
Investigate differences between online store inventory and ERP inventory.

## Initial checks
1. Compare the SKU in both systems.
2. Record the online quantity and ERP quantity.
3. Calculate the difference as online quantity minus ERP quantity.
4. Check whether the SKU is missing from either system.
5. Review recent inventory synchronisation logs if available.

## Common causes
- A delayed synchronisation job.
- A failed API request.
- A sale or stock adjustment processed in only one system.
- An incorrect SKU mapping.
- Duplicate or out-of-order inventory events.

## Safe investigation procedure
1. Capture the discrepancy and relevant timestamps.
2. Inspect synchronisation logs and API error details.
3. Verify SKU mappings and recent stock changes.
4. Determine which system is authoritative for the affected stock.
5. Escalate if the source of truth is unclear.

## Safety requirements
- Do not change stock quantities during investigation.
- Do not assume the ERP is authoritative without confirming the business rule.
- Do not report a fix unless execution has been verified.
- Record evidence before proposing a corrective action.
