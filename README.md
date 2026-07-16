# CigarBrokerCRM

Desktop CRM application for cigar brokerage operations. Built with PySide6, SQLAlchemy, and SQLite. Dark professional theme.

## Quick Start

Run the pre-built executable:
```
dist\CigarBrokerCRM.exe
```

No installation needed. The app starts empty — see the built-in Help section (Ctrl+8 or F1) for a getting-started walkthrough.

## Features

- **Clients** — Full CRUD with rich profiles (addresses, tags, preferred brands, credit/terms), MULTIPLE contacts per client (buyer, assistant… with a ★ primary), communication log, and linked order history.
- **Companies Represented** — Manage supplier companies, their product catalogs (double-click a product to edit), multiple contacts per company, and **your commission %** per company — the basis for net earnings.
- **Orders** — Line items, automatic totals (tax rate from Settings), status tracking, invoicing, paid/unpaid tracking, and per-order supplier manifests.
- **Invoices** — Printable invoice per order (🧾): your letterhead from Settings, auto INV-YYYY-#### numbers, print/save-PDF, PAID stamp via Mark Paid.
- **Manifests** — 📦 per-supplier purchase manifests, either for ONE selected order or batch-built from open orders (statuses / supplier / date range). Print, PDF, or CSV per supplier.
- **Calendar** — Full calendar of brokerage events (meetings, calls, deliveries, follow-ups, linked to clients/companies) with order dates overlaid; clicking a day also lists that day's communication-log entries from clients and companies. Mini calendar on the Dashboard.
- **Branding** — Set your company name in Settings and the whole app titles itself "<Your Company> CRM". Upload a logo and it appears at the top of every invoice, manifest, and earnings report.
- **Company log** — Companies now have their own communication log (calls/emails/meetings/notes), alongside multiple contacts and their product catalog.
- **Earnings reports** — Weekly / monthly / quarterly / yearly **Gross vs Net** (net = each company's commission % of its sales), printable with letterhead and one-click saved as PDF to your reports folder (Settings).
- **Reports** — Plus sales by client, top products, top companies, revenue over time, aging receivables, order status summary. Charts + CSV export.
- **Dashboard** — Command center: money cards (unpaid invoices, gross/net YTD), gross-vs-net trend chart, order-status donut, mini calendar, next-7-days agenda.
- **Settings** — Company letterhead + license #, tax rate, invoice footer, reports folder.
- **Config transfer** — File > Save Config (Ctrl+S) overwrites your latest config file; Settings > Export/Import Config for explicit file choices. Your whole setup (logo included) in one portable JSON file for moving to another computer.
- **Help** — Built-in user guide (Ctrl+8 / F1) covering every section, the money math, and machine moves. By Whoastra Labs LLC.
- **Backup / Restore** — File > Backup Database (Ctrl+B) and File > Restore Database to move or recover your data.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+1-8 | Switch sections |
| Ctrl+N | New item |
| Ctrl+F | Focus search |
| Ctrl+S | Save config |
| Ctrl+B | Backup database |
| F1 | Help / user guide |
| Ctrl+Q | Quit |
| Delete | Delete selected |

## Data Storage

All data is stored locally in `~/.cigarbrokercrm/cigarbroker.db` (SQLite) and persists between launches. Use File > Backup Database to create backups and File > Restore Database to load one.

**Moving to a new computer:** copy `CigarBrokerCRM.exe` over, then on the old machine do Settings > Export Config and File > Backup Database; on the new machine do Settings > Import Config and File > Restore Database.

## Development

### Requirements
- Python 3.10+
- PySide6, SQLAlchemy, matplotlib, pyinstaller

### Install dependencies
```
pip install -r requirements.txt
```

### Run from source
```
python main.py
```

### Build executable
```
pyinstaller cigarbrokercrm.spec --clean
```

Output: `dist/CigarBrokerCRM.exe`
