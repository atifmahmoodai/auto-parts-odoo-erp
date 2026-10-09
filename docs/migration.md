# Reviewed migration

## Scope and ordering

Obtain an approved export and mapping workbook from the current system. Keep a read-only original, source timestamp, row counts and SHA-256 hash. Do not import customer/vendor personal data into this repository. Resolve duplicate SKUs, units, currencies, tax mappings and warehouse codes before loading.

1. Configure company and accountant-approved localization/chart.
2. Use native Odoo import for reviewed vendors/customers, categories, units and warehouse/location records, with stable external IDs. Grant only required company visibility.
3. Load product catalog through this extension in batches of at most 1,000. `source_key` is a stable per-company migration key, not a supplier barcode. Never recycle it. Source key/company cannot be changed after assignment, including after untagging a part. SKU/barcode collisions with accessible shared/current-company products are rejected.
4. Configure vendor price lists through native Odoo purchasing, preserving source vendor, vendor product code, currency, quantity breaks and validity dates. This importer does not create them.
5. Count opening stock by warehouse/location/lot as required. An authorized reviewer must approve native inventory adjustments. **Do not manufacture purchases or silently insert stock quants to create opening quantities.** Reconcile physical counts and approved valuation.
6. The accountant handles opening receivables/payables, journals, valuation and tax balances using the approved localization and cutover process. Do not interpret the example cost as a financial migration decision.
7. Reconcile counts and sampled records; freeze source changes for cutover, import the approved delta, then have business owners sign acceptance.

## Catalog contract

Exact headers, in order:

```csv
source_key,name,sku,barcode,brand,oem_reference,condition,sale_price,cost,uom_external_id,category_external_id
```

Name, SKU, source key, condition, both amounts and relation IDs are required. Brand/OEM/barcode may be blank. Source keys use letters, digits, `_ . : -`, maximum 64 characters. Text is single-line and at most 200 characters. Conditions: `new`, `remanufactured`, `used`. Amounts: plain digits with optional decimal point and up to four decimal places, 0–1,000,000,000. Currency is the selected company currency. No scientific notation, formula expressions or automatic FX conversion. Built-in example references `uom.product_uom_unit` and `auto_parts_dealer.category_parts`; replace with reviewed IDs where appropriate.

New parts are single-variant, stock-tracked goods. Existing archived/non-part/multi-variant targets are rejected. Existing units, categories and costs must match; use native reviewed workflows for changes. The review summary shows creates/updates and identifies SKUs; reviewers must also inspect the original CSV prices/attributes. Editing a batch clears validation. Apply rechecks the file/catalog state and applies all rows in one transaction. Applying the same completed batch is idempotent; independently submitted duplicate batches resolve by the stable company/source key and are revalidated. Applied batches cannot be edited or deleted through normal model methods.

This protects normal application callers, not a database administrator with direct SQL access. Keep database access restricted and backups/audit exports independently protected.

## Reconciliation record

For each batch retain: source filename/hash, company/currency, batch ID, reviewer, row count, creates/updates, applied actor/time, rejected rows and remediation. Compare source and destination products/SKUs, unit/category, sampled prices/costs and stock by location. Stock and financial reconciliations are separate signed records. No client migration has been performed by this repository.
