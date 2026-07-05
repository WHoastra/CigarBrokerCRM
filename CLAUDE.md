# CigarBrokerCRM

Standalone Windows desktop CRM for cigar brokerage, built with PySide6 + SQLAlchemy + SQLite. Dark themed (Whoastra style). Modules: Dashboard, Clients (CRUD + comm log + order history), Companies (CRUD + product catalog), Orders (line items, totals, status), Reports (6 built-in reports with matplotlib charts, CSV export). Data stored in `~/.cigarbrokercrm/cigarbroker.db`. Packaged as single-file exe via PyInstaller (`dist/CigarBrokerCRM.exe`). Sample data seeded on first run.

## Project Structure
- `main.py` — Entry point, main window with sidebar navigation + dashboard
- `app/database.py` — SQLAlchemy models (Client, Company, Product, Order, OrderItem, Communication) + seed data
- `app/theme.py` — Dark theme stylesheet
- `app/clients_tab.py` — Clients CRUD + communication log + order history panel
- `app/companies_tab.py` — Companies CRUD + product catalog management
- `app/orders_tab.py` — Order entry with line items, status, totals
- `app/reports_tab.py` — 6 reports with charts and CSV export
- `cigarbrokercrm.spec` — PyInstaller build spec (single-file exe)

## Recent changes

- (2026-07-02) Project created.
- (2026-07-02) Built full CRM application: clients, companies, orders, reports modules with dark theme, sidebar nav, sample data, and PyInstaller single-file exe.
- (2026-07-02) Round 3 (Claude Code, session-driven): company communication log (Communication.client_id made nullable + company_id added via a guarded table-rebuild in _migrate that only fires on the old NOT-NULL schema; Companies detail gains a Communications tab reusing clients' CommDialog); calendar day list now also shows communication-log entries for that day from BOTH clients and companies (read-only); app branding — `DatabaseManager.app_title()` returns "<company name> CRM" (falls back to CigarBrokerCRM), applied to window title / dashboard header / status bar / About / app name and re-applied live via `MainWindow.apply_branding()` when Settings saves; logo upload in Settings (copied into ~/.cigarbrokercrm/logo.<ext>, base64-embedded by `_broker_block`/`_logo_img_tag` so it appears on every invoice, manifest, and earnings report and survives deleting the original).
- (2026-07-02) Round 2 (Claude Code, session-driven): multiple contacts per client AND company (new `contacts` table + shared `app/contacts.py` ContactsPanel embedded in both detail views); per-order supplier manifests (`Manifest (this order)` button; grouping refactored into `_build_manifest_docs`); commission % per company (`companies.commission_pct` via _migrate) driving the new earnings engine (`app/earnings.py`: gross = line totals excl. tax, net = gross × company %); "Earnings — Gross vs Net" report with This Week/Month/Quarter/Year/All-Time periods, printable via `earnings_html` and one-click PDF into a configurable reports folder (`reports.dir` setting + `save_html_pdf`); Calendar tab (`app/calendar_tab.py`, new `events` table, order-date overlay, `apply_month_formats` shared with the dashboard's mini calendar; sidebar is now 7 sections — Settings index moved to 6, jump in orders_tab updated); Dashboard rebuilt as a command center (unpaid/gross-YTD/net-YTD cards, 6-month gross-vs-net chart, status donut, mini calendar, next-7-days agenda).
- (2026-07-02) Major upgrade (Claude Code, session-driven): Settings tab (broker company letterhead, tax rate, invoice footer — stored in a new `settings` table); invoices per order (`app/documents.py`, INV-YYYY-#### numbering, print/save-PDF via QtPrintSupport, PAID stamp) with Mark Paid tracking (new Order columns via idempotent `_migrate()` — never drop the user's DB); per-supplier purchase manifests (📦 Manifest… in Orders: status/supplier/date filters, aggregated per product, print/PDF/CSV per supplier); tax rate de-hardcoded from 7% to Settings; eager-loading fixes; palette constants centralized in theme.py; PyInstaller spec fixed (upx=False + collect matplotlib data — the silent-crash cause) and exe rebuilt.
