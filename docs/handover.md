# Training, acceptance and support plan

## Proposed 4–6 week engagement

This is a planning baseline, not an accepted contract or a statement that support has already occurred. The brief's $2,000 budget could be allocated as $300 discovery/mapping, $700 configuration/extension, $400 migration rehearsal, $400 testing/training and $200 handover/support allocation. Hosting, paid Odoo licenses, external services and material scope changes require separate agreement. A month of post-go-live support needs an agreed owner, hours, response times and start date.

| Stage | Work and exit evidence |
|---|---|
| Week 1 | Approve workflow map, roles, locations, localization, source mappings and acceptance criteria |
| Week 2 | Configure staging; demonstrate catalog, purchase, receipt, transfer and sales flows |
| Week 3 | Rehearse migration; reconcile catalogs, stock and accountant-controlled balances |
| Week 4 | Staff training, UAT, backup restore drill and go/no-go review |
| Weeks 5–6 if needed | Resolve UAT gaps, controlled cutover, monitored stabilization |
| 30 days after agreed go-live | Triage agreed defects, monitor scheduled jobs/backups, document fixes and close handover |

## Training exercises

- **Inventory administrator (60 min):** company selection, product identity, CSV validate/review/apply, stale-plan recovery, category/unit/cost boundaries and reconciliation.
- **Warehouse operator (60 min):** purchase receipt, lot/serial requirements if selected, internal transfer, reservation/delivery and discrepancy handling. Verify actual labels/scanners where required.
- **Sales and purchasing (60 min):** CRM opportunity, quotation, order confirmation, supplier price list, receipt/delivery status and exception handling.
- **Accounts (60 min with accountant):** draft invoice/bill from actual operations, approved taxes/journals, posting/credit-note permissions and reporting boundaries.
- **Administrator (60 min):** staff permissions, company isolation, configuration secrets, staged updates, backups and isolated recovery.

## Acceptance checklist (must be signed, not assumed)

- [ ] Approved client company/currency/localization, native role matrix and real warehouse map.
- [ ] Catalog reconciliation passes; duplicate/malformed/stale import rejection demonstrated.
- [ ] Operator cannot apply catalog imports; users cannot read another unselected company's import/stock records.
- [ ] Receive 10 fictional test units, transfer 4, sell/deliver 2 from destination; remaining quantities 6 and 2. Restore staging afterwards if required.
- [ ] Native draft invoice/bill totals and balanced entries verified under the actual approved localization, including returns/credit notes and applicable tax cases.
- [ ] Actual vendor/customer source samples, scanner workflows and required documents validated.
- [ ] Enterprise-only/reporting requirements explicitly accepted, licensed or scoped separately.
- [ ] HTTPS/admin access, approved mail recipients and selected scheduled jobs validated.
- [ ] Off-host database plus filestore restoration witnessed; recovery objectives/retention agreed.
- [ ] Staff training completed; known gaps, operating owner and support channel/date/hours agreed.

CI verifies a synthetic purchase/receive/transfer/sell/invoice/bill path and access/import safeguards. It does not replace real tax/accounting acceptance, physical stock reconciliation, actual scanner testing or an elapsed support period.

Catalog import administrators need both `stock.group_stock_manager` and native `product.group_product_manager` (product management). Inventory administration alone does not grant product creation in Odoo 19. No sudo or automatic elevation is used.
