# Auto Parts · Odoo Operations

A native **Odoo Community 19** extension for an automotive parts distributor. It adds company-scoped parts identity, reviewed catalog migration, and warehouse stock reporting to Odoo's sales, purchases, inventory, vendor, invoicing and CRM workflows. The original engagement brief is preserved in [docs/original-brief.md](docs/original-brief.md).

**Implementation status:** candidate under native Odoo/PostgreSQL CI verification. This repository is a reusable implementation, not a completed client rollout. Client data, accounting localization, hosting, operational acceptance and the proposed month of support remain outstanding.

## Delivered scope

| Area | Implementation |
|---|---|
| Catalog | Stable company/source key, brand, OEM reference and new/remanufactured/used condition; stock-tracked goods only |
| Migration | Exact CSV contract, validation and review, transactional apply, stale-plan rejection, repeat-apply protection, retained applied batches |
| Sales and purchasing | Native quotations/orders, supplier records, receipts, transfers, deliveries, draft invoices and vendor bills |
| Multiple locations | Native warehouses and internal locations; read-only quantity/reserved/available report with list, pivot and chart views |
| Roles | Native Odoo inventory, sales, purchase and accounting groups; catalog imports restricted to inventory administrators; company record rules |
| Operations | HTTPS Compose configuration, distinct secrets, non-superuser database role, controlled initialization, maintenance backup and handover guides |

Open **Parts Operations** after installing `auto_parts_dealer`. There is no separate mock ERP or replacement accounting ledger. Modules retain their native Odoo behavior and permissions.

## Run and verify

Requires a Linux Docker host with Docker Compose, at least 4 GB available RAM (size workers to actual load), an approved domain, and PostgreSQL storage/backup capacity.

1. Read [deployment](docs/deployment.md); copy `.env.example` to `.env` and replace every placeholder.
2. Export a unique `INITIAL_ADMIN_LOGIN` and `INITIAL_ADMIN_PASSWORD`, then run `bash scripts/initialize.sh` from this directory. The initialization script refuses an already installed database.
3. Configure the actual company, localization, roles and approval rules privately before exposing the proxy.
4. Start with `docker compose up -d` only after the acceptance gates are satisfied.

Local parser checks: `python3 -m unittest discover -s tests -v`.
The GitHub workflow installs the actual addon in Odoo 19 against PostgreSQL 17, runs addon tests, upgrades the module and restores a database backup. The US chart installed by CI is exclusively a disposable accounting test fixture; production initialization does **not** select a localization.

## Catalog import

Use [examples/catalog.csv](examples/catalog.csv), containing fictional parts. Each file is UTF-8, at most 2 MB/1,000 rows, with the exact supplied headers. Prices and initial costs use the selected company's currency; amounts are plain nonnegative decimal strings with up to four decimal places. IDs refer to existing Odoo units/categories. Importer supports one variant per part.

Inventory administrator: select company → upload → **Validate** → inspect the summary and original CSV → **Apply**. Any changed file or existing product requires another review. Applying an applied batch again returns without duplication. Applied batches remain immutable migration evidence. Updating existing inventory cost, unit or category is deliberately rejected; use a reviewed native Odoo workflow. No stock, tax, financial balance, invoice or bill is created by catalog upload. See [migration](docs/migration.md).

## Important boundaries

- OEM references are reference text, not verified vehicle fitment, interchange, authenticity or safety certification.
- Stock overview includes company-owned internal stock, excludes consignment, and is **not inventory valuation**. Compare quantities within the same unit/product; an all-product total may mix units.
- Native printed product labels/keyboard-wedge barcode entry can be evaluated with actual scanners. A dedicated enterprise barcode app, manufacturer interchange data and hardware integrations are not bundled.
- Community invoicing/journal workflows are exercised; licensed Enterprise financial reports, bank synchronization and local tax filings are not promised. Accountant approval and the correct localization are prerequisites for posting real transactions.
- No outbound messaging service is configured. SMTP defaults to a closed local port, and initialization disables scheduled actions. Enable only reviewed jobs and approved transport settings.
- Docker image tags are maintained upstream rather than digest-pinned here. Record tested image digests at release and rehearse upgrades on a restored staging copy.
- The extension does not add cross-company SKU uniqueness, a second-person import approval, automated valuation migration, or an immutable external audit archive. Use operational review and appropriate native access controls.

[Training and acceptance](docs/handover.md) · [Deployment and recovery](docs/deployment.md) · [Migration plan](docs/migration.md)

Addon source license: LGPL-3.0, as declared in its manifest. Odoo and third-party components retain their own licenses.
