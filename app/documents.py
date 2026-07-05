"""Printable documents: client invoices and per-supplier purchase manifests.

Everything renders through QTextDocument (rich-text HTML subset — keep the
markup to tables + inline color/size styles), so printing and save-as-PDF
come from QtPrintSupport with no extra dependencies. Documents are built from
plain dicts, never live ORM objects, so there are no detached-session issues.
"""

import base64
import csv
import html
import os
from datetime import date

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTextBrowser,
    QFileDialog, QMessageBox, QTabWidget, QWidget
)
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter, QPrintDialog


def _e(s):
    return html.escape(str(s if s is not None else ""))


def _money(v):
    return f"${float(v or 0):,.2f}"


def _logo_img_tag(path):
    """A logo <img> as a base64 data URI so it's self-contained in the printed
    doc / PDF. Returns '' if the file is missing or unreadable."""
    try:
        if not path or not os.path.isfile(path):
            return ""
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif",
                "bmp": "bmp"}.get(ext, "png")
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return (f'<img src="data:image/{mime};base64,{b64}" '
                f'height="64" style="margin-bottom:6px;"><br>')
    except OSError:
        return ""


def _broker_block(company):
    """The broker's own letterhead block, from Settings (company.* keys),
    with the uploaded logo (if any) above the name."""
    name = _e(company.get("name") or "Your Company")
    lines = [
        company.get("address"),
        company.get("city_state_zip"),
        " · ".join(x for x in [company.get("phone"), company.get("email")] if x),
        f"License # {company['license']}" if company.get("license") else "",
    ]
    body = "<br>".join(_e(l) for l in lines if l)
    return (
        f'{_logo_img_tag(company.get("logo"))}'
        f'<span style="font-size:16pt; font-weight:bold; color:#7a5c00;">{name}</span><br>'
        f'<span style="font-size:9pt; color:#444;">{body}</span>'
    )


def invoice_html(inv):
    """inv: {number, order_no, order_date, invoiced_date, is_paid, paid_date,
    client:{name, company, address, city_state, email, phone, terms},
    items:[{name, sku, qty, unit, total}], subtotal, tax, tax_pct, total,
    company:{...settings}, footer}"""
    c = inv["client"]
    bill_to = "<br>".join(_e(x) for x in [
        c.get("name"), c.get("company"), c.get("address"), c.get("city_state"),
        c.get("email"), c.get("phone"),
    ] if x)

    rows = "".join(
        f'<tr>'
        f'<td style="padding:5px;">{_e(i["name"])}</td>'
        f'<td style="padding:5px;">{_e(i["sku"])}</td>'
        f'<td style="padding:5px;" align="right">{i["qty"]}</td>'
        f'<td style="padding:5px;" align="right">{_money(i["unit"])}</td>'
        f'<td style="padding:5px;" align="right">{_money(i["total"])}</td>'
        f'</tr>'
        for i in inv["items"]
    )

    paid_stamp = ""
    if inv.get("is_paid"):
        paid_stamp = (
            f'<table cellpadding="8"><tr><td style="border:3px solid #1a7a2e;">'
            f'<span style="font-size:20pt; font-weight:bold; color:#1a7a2e;">PAID</span>'
            f'<span style="font-size:10pt; color:#1a7a2e;"> — {_e(inv.get("paid_date") or "")}</span>'
            f'</td></tr></table>'
        )

    footer = f'<p style="font-size:9pt; color:#444;">{_e(inv["footer"])}</p>' if inv.get("footer") else ""

    return f"""
<html><body style="background-color:#ffffff; color:#111; font-family:Segoe UI, sans-serif;">
<table width="100%"><tr>
  <td valign="top">{_broker_block(inv["company"])}</td>
  <td valign="top" align="right">
    <span style="font-size:22pt; font-weight:bold; color:#333;">INVOICE</span><br>
    <span style="font-size:10pt;">{_e(inv["number"])}</span><br>
    <span style="font-size:9pt; color:#444;">Invoice date: {_e(inv["invoiced_date"])}</span><br>
    <span style="font-size:9pt; color:#444;">Order {_e(inv["order_no"])} · {_e(inv["order_date"])}</span>
  </td>
</tr></table>
<hr>
<table width="100%"><tr>
  <td valign="top">
    <span style="font-size:9pt; font-weight:bold; color:#7a5c00;">BILL TO</span><br>
    <span style="font-size:10pt;">{bill_to}</span><br>
    <span style="font-size:9pt; color:#444;">Terms: {_e(c.get("terms") or "—")}</span>
  </td>
  <td valign="top" align="right">{paid_stamp}</td>
</tr></table>
<br>
<table width="100%" border="1" cellspacing="0" cellpadding="4" style="border-color:#999;">
  <tr style="background-color:#f0e6c8;">
    <th align="left" style="padding:5px;">Product</th>
    <th align="left" style="padding:5px;">SKU</th>
    <th align="right" style="padding:5px;">Qty</th>
    <th align="right" style="padding:5px;">Unit Price</th>
    <th align="right" style="padding:5px;">Total</th>
  </tr>
  {rows}
</table>
<table width="100%"><tr><td></td><td width="220" align="right">
  <span style="font-size:10pt;">Subtotal: {_money(inv["subtotal"])}</span><br>
  <span style="font-size:10pt;">Tax ({inv["tax_pct"]:g}%): {_money(inv["tax"])}</span><br>
  <span style="font-size:14pt; font-weight:bold; color:#7a5c00;">Total: {_money(inv["total"])}</span>
</td></tr></table>
{footer}
</body></html>"""


def manifest_html(man):
    """man: {supplier:{name, contact, email, phone, address},
    rows:[{product, sku, size, qty, unit, ext, refs}], total_qty, total_cost,
    company:{...settings}, criteria}"""
    s = man["supplier"]
    supplier_block = "<br>".join(_e(x) for x in [
        s.get("contact"), s.get("address"),
        " · ".join(x for x in [s.get("phone"), s.get("email")] if x),
    ] if x)

    rows = "".join(
        f'<tr>'
        f'<td style="padding:5px;">{_e(r["product"])}</td>'
        f'<td style="padding:5px;">{_e(r["sku"])}</td>'
        f'<td style="padding:5px;">{_e(r["size"])}</td>'
        f'<td style="padding:5px;" align="right">{r["qty"]}</td>'
        f'<td style="padding:5px;" align="right">{_money(r["unit"])}</td>'
        f'<td style="padding:5px;" align="right">{_money(r["ext"])}</td>'
        f'<td style="padding:5px; font-size:8pt; color:#444;">{_e(r["refs"])}</td>'
        f'</tr>'
        for r in man["rows"]
    )

    return f"""
<html><body style="background-color:#ffffff; color:#111; font-family:Segoe UI, sans-serif;">
<table width="100%"><tr>
  <td valign="top">{_broker_block(man["company"])}</td>
  <td valign="top" align="right">
    <span style="font-size:18pt; font-weight:bold; color:#333;">PURCHASE MANIFEST</span><br>
    <span style="font-size:9pt; color:#444;">Generated {_e(date.today().isoformat())}</span>
  </td>
</tr></table>
<hr>
<span style="font-size:9pt; font-weight:bold; color:#7a5c00;">TO SUPPLIER</span><br>
<span style="font-size:13pt; font-weight:bold;">{_e(s["name"])}</span><br>
<span style="font-size:10pt;">{supplier_block}</span>
<br><br>
<table width="100%" border="1" cellspacing="0" cellpadding="4" style="border-color:#999;">
  <tr style="background-color:#f0e6c8;">
    <th align="left" style="padding:5px;">Product</th>
    <th align="left" style="padding:5px;">SKU</th>
    <th align="left" style="padding:5px;">Size</th>
    <th align="right" style="padding:5px;">Qty</th>
    <th align="right" style="padding:5px;">Unit $ (ref)</th>
    <th align="right" style="padding:5px;">Ext. $ (ref)</th>
    <th align="left" style="padding:5px;">Order refs</th>
  </tr>
  {rows}
</table>
<table width="100%"><tr><td></td><td width="260" align="right">
  <span style="font-size:11pt; font-weight:bold;">Total units: {man["total_qty"]}</span><br>
  <span style="font-size:11pt; font-weight:bold; color:#7a5c00;">Reference value: {_money(man["total_cost"])}</span>
</td></tr></table>
<p style="font-size:8pt; color:#444;">{_e(man["criteria"])} Unit prices are client-sale reference prices, not negotiated supplier cost.</p>
</body></html>"""


def earnings_html(rep):
    """rep: {period_label, generated, rows:[{label, gross, net}], total_gross,
    total_net, companies:[{name, pct, gross, net}], company:{...settings},
    note (optional footnote)}"""
    period_rows = "".join(
        f'<tr>'
        f'<td style="padding:5px;">{_e(r["label"])}</td>'
        f'<td style="padding:5px;" align="right">{_money(r["gross"])}</td>'
        f'<td style="padding:5px;" align="right">{_money(r["net"])}</td>'
        f'<td style="padding:5px;" align="right">{(r["net"] / r["gross"] * 100) if r["gross"] else 0:.1f}%</td>'
        f'</tr>'
        for r in rep["rows"]
    )
    company_rows = "".join(
        f'<tr>'
        f'<td style="padding:5px;">{_e(c["name"])}</td>'
        f'<td style="padding:5px;" align="right">{c["pct"]:g}%</td>'
        f'<td style="padding:5px;" align="right">{_money(c["gross"])}</td>'
        f'<td style="padding:5px;" align="right">{_money(c["net"])}</td>'
        f'</tr>'
        for c in rep["companies"]
    )
    note = f'<p style="font-size:8pt; color:#444;">{_e(rep["note"])}</p>' if rep.get("note") else ""
    header_style = 'style="background-color:#f0e6c8; padding:5px;"'

    return f"""
<html><body style="background-color:#ffffff; color:#111; font-family:Segoe UI, sans-serif;">
<table width="100%"><tr>
  <td valign="top">{_broker_block(rep["company"])}</td>
  <td valign="top" align="right">
    <span style="font-size:18pt; font-weight:bold; color:#333;">EARNINGS REPORT</span><br>
    <span style="font-size:11pt;">{_e(rep["period_label"])}</span><br>
    <span style="font-size:9pt; color:#444;">Generated {_e(rep["generated"])}</span>
  </td>
</tr></table>
<hr>
<table width="100%"><tr>
  <td align="center">
    <span style="font-size:9pt; color:#444;">GROSS SALES</span><br>
    <span style="font-size:20pt; font-weight:bold; color:#333;">{_money(rep["total_gross"])}</span>
  </td>
  <td align="center">
    <span style="font-size:9pt; color:#444;">YOUR NET EARNINGS</span><br>
    <span style="font-size:20pt; font-weight:bold; color:#1a7a2e;">{_money(rep["total_net"])}</span>
  </td>
</tr></table>
<br>
<table width="100%" border="1" cellspacing="0" cellpadding="4" style="border-color:#999;">
  <tr>
    <th align="left" {header_style}>Period</th>
    <th align="right" {header_style}>Gross</th>
    <th align="right" {header_style}>Net</th>
    <th align="right" {header_style}>Net %</th>
  </tr>
  {period_rows}
</table>
<br>
<span style="font-size:10pt; font-weight:bold; color:#7a5c00;">BY COMPANY</span>
<table width="100%" border="1" cellspacing="0" cellpadding="4" style="border-color:#999;">
  <tr>
    <th align="left" {header_style}>Company</th>
    <th align="right" {header_style}>Your %</th>
    <th align="right" {header_style}>Gross</th>
    <th align="right" {header_style}>Net</th>
  </tr>
  {company_rows}
</table>
{note}
<p style="font-size:8pt; color:#444;">Gross = product sales (line totals, excludes sales tax). Net = gross × your commission % per supplier company.</p>
</body></html>"""


def save_html_pdf(html, path):
    """Render HTML straight to a PDF file, no dialog."""
    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(path)
    doc = QTextDocument()
    doc.setHtml(html)
    doc.print_(printer)


class DocPreviewDialog(QDialog):
    """Preview one or more printable documents. docs = [{title, html, csv?}]
    where csv is an optional list of rows (first row = header) enabling the
    Export CSV button for that tab. Print / Save PDF act on the current tab."""

    def __init__(self, parent, docs, window_title="Document"):
        super().__init__(parent)
        self.docs = docs
        self.setWindowTitle(window_title)
        self.setMinimumSize(760, 640)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        for d in docs:
            page = QWidget()
            pl = QVBoxLayout(page)
            pl.setContentsMargins(0, 0, 0, 0)
            browser = QTextBrowser()
            browser.setHtml(d["html"])
            # The documents are print-styled (white); keep them white on screen
            # too instead of inheriting the app's dark theme.
            browser.setStyleSheet("background-color: #ffffff;")
            pl.addWidget(browser)
            self.tabs.addTab(page, d["title"])
        layout.addWidget(self.tabs)

        btns = QHBoxLayout()
        self.csv_btn = QPushButton("Export CSV")
        self.csv_btn.clicked.connect(self.export_csv)
        btns.addWidget(self.csv_btn)
        btns.addStretch()
        pdf_btn = QPushButton("Save PDF…")
        pdf_btn.clicked.connect(self.save_pdf)
        btns.addWidget(pdf_btn)
        print_btn = QPushButton("Print…")
        print_btn.setObjectName("primaryBtn")
        print_btn.clicked.connect(self.print_doc)
        btns.addWidget(print_btn)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btns.addWidget(close_btn)
        layout.addLayout(btns)

        self.tabs.currentChanged.connect(self._sync_csv_btn)
        self._sync_csv_btn()

    def _current(self):
        return self.docs[self.tabs.currentIndex()]

    def _sync_csv_btn(self):
        self.csv_btn.setVisible(bool(self._current().get("csv")))

    def _text_doc(self):
        doc = QTextDocument()
        doc.setHtml(self._current()["html"])
        return doc

    def print_doc(self):
        printer = QPrinter(QPrinter.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() == QPrintDialog.Accepted:
            self._text_doc().print_(printer)

    def save_pdf(self):
        d = self._current()
        default = d["title"].replace(" ", "_").replace("/", "-") + ".pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", default, "PDF Files (*.pdf)")
        if not path:
            return
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        self._text_doc().print_(printer)
        QMessageBox.information(self, "Saved", f"Saved to {path}")

    def export_csv(self):
        d = self._current()
        rows = d.get("csv")
        if not rows:
            return
        default = d["title"].replace(" ", "_").replace("/", "-") + ".csv"
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", default, "CSV Files (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerows(rows)
        QMessageBox.information(self, "Exported", f"Saved to {path}")
