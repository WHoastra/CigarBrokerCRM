"""Help section — the built-in user guide, branded Whoastra Labs LLC.
Static rich-text rendered in a QTextBrowser; no database access needed."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser

from app.theme import GOLD

HELP_HTML = f"""
<div style="color:#e0e0e0;">

<table width="100%"><tr>
  <td><span style="font-size:22pt; font-weight:bold; color:{GOLD};">Help &amp; User Guide</span></td>
  <td align="right" style="color:#888;">CigarBrokerCRM<br>
  <span style="color:{GOLD};">Whoastra Labs LLC</span></td>
</tr></table>
<hr>

<h2 style="color:{GOLD};">Getting started</h2>
<p>The app starts empty. A good first session:</p>
<ol>
  <li><b>Settings (Ctrl+7)</b> — enter your company name, address, license #, tax rate,
      and upload a logo. This becomes the letterhead on every invoice, manifest, and report,
      and the app re-titles itself "&lt;Your Company&gt; CRM".</li>
  <li><b>Companies (Ctrl+3)</b> — add the suppliers you represent, set
      <b>Your commission %</b> on each (this drives all net-earnings math), and build
      their product catalogs.</li>
  <li><b>Clients (Ctrl+2)</b> — add the shops and lounges you sell to.</li>
  <li><b>Orders (Ctrl+4)</b> — write orders with line items; totals and tax are automatic.</li>
</ol>

<h2 style="color:{GOLD};">Sections</h2>
<p><b>Dashboard (Ctrl+1)</b> — money cards (unpaid invoices, gross/net YTD), a 6-month
gross-vs-net chart, order-status donut, mini calendar, and the next 7 days.</p>
<p><b>Clients (Ctrl+2)</b> — profiles with tags, preferred brands, credit limit and terms;
multiple contacts per client (★ marks the primary); a communication log; and order history.</p>
<p><b>Companies (Ctrl+3)</b> — the suppliers you represent: product catalog
(double-click a product to edit), contacts, communication log, and your commission %.</p>
<p><b>Orders (Ctrl+4)</b> — line items, status tracking, and per order:
<b>🧾 Invoice</b> (auto INV-YYYY-#### number, print or save as PDF, PAID stamp),
<b>✔ Mark Paid</b>, and <b>📦 Manifest</b> (a per-supplier purchase list for just
that order). The batch <b>📦 Manifest</b> button up top builds manifests from all
open orders, filtered by status, supplier, or date.</p>
<p><b>Calendar (Ctrl+5)</b> — meetings, calls, deliveries and follow-ups, linked to
clients or companies. Colors on the month grid:
<span style="color:{GOLD};"><b>■ gold</b></span> events ·
<span style="color:#4aa3c9;">■ blue</span> order dates ·
<span style="color:#9c6bd4;">■ purple</span> communication-log entries.
Click a day to see everything that happened on it.</p>
<p><b>Reports (Ctrl+6)</b> — Earnings Gross vs Net (weekly/monthly/quarterly/yearly,
printable, one-click PDF into your reports folder), plus sales by client, top products,
top companies, revenue over time, aging receivables, and order status. All export CSV.</p>
<p><b>Settings (Ctrl+7)</b> — letterhead, logo, tax rate, invoice footer, reports folder,
and config export/import.</p>

<h2 style="color:{GOLD};">How the money math works</h2>
<p><b>Gross</b> = product line totals (sales tax is collected, not earned, so it's excluded).<br>
<b>Net (your cut)</b> = each line total × the commission % of the product's supplier company.<br>
If a company's commission % isn't set, its net reports as $0 — set it in Companies.</p>

<h2 style="color:{GOLD};">Saving &amp; moving your setup</h2>
<p><b>File &gt; Save Config (Ctrl+S)</b> — instantly overwrites your config file, no dialog.
By default it lives at <code>~/.cigarbrokercrm/cigarbrokercrm-config.json</code>; if you've
used <b>Settings &gt; Export / Import Config</b>, Save targets that file instead.</p>
<p><b>File &gt; Backup Database (Ctrl+B)</b> — copies your whole database (clients, orders,
everything) to a file. <b>File &gt; Restore Database</b> loads one back.</p>
<p><b>Moving to a new computer:</b> on the old machine, Save Config + Backup Database.
On the new one, run the exe, Import Config, Restore Database. Done.</p>
<p>Your data lives in <code>~/.cigarbrokercrm/cigarbroker.db</code> and is saved
automatically the moment you click Save on anything — closing the app never loses data.</p>

<h2 style="color:{GOLD};">Keyboard shortcuts</h2>
<table cellpadding="4" style="color:#e0e0e0;">
  <tr><td><b>Ctrl+1…8</b></td><td>Switch sections</td></tr>
  <tr><td><b>Ctrl+N</b></td><td>New item in the current section</td></tr>
  <tr><td><b>Ctrl+F</b></td><td>Focus search</td></tr>
  <tr><td><b>Ctrl+S</b></td><td>Save config</td></tr>
  <tr><td><b>Ctrl+B</b></td><td>Backup database</td></tr>
  <tr><td><b>Ctrl+Q</b></td><td>Quit</td></tr>
  <tr><td><b>Delete</b></td><td>Delete selected (Clients)</td></tr>
  <tr><td><b>Double-click</b></td><td>Edit almost anything in a table</td></tr>
</table>

<hr>
<p align="center" style="color:#888;">
CigarBrokerCRM — built by <span style="color:{GOLD};"><b>Whoastra Labs LLC</b></span><br>
All data stays on this computer. Nothing is sent anywhere.
</p>
</div>
"""


class HelpTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setStyleSheet(
            "QTextBrowser { background-color: #16162e; border: 1px solid #2a2a4a;"
            " border-radius: 6px; padding: 18px; font-size: 13.5px; }")
        browser.setHtml(HELP_HTML)
        layout.addWidget(browser)
