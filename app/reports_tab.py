"""Reports module - Sales by client, top products, revenue over time, aging receivables.
Uses matplotlib for charts, supports CSV/PDF export."""

import csv
import os
from datetime import date, timedelta
from collections import defaultdict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QHeaderView, QFileDialog,
    QAbstractItemView, QMessageBox, QStackedWidget
)
from PySide6.QtCore import Qt

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from app.database import DatabaseManager, Order, OrderItem, Client, Product, Company
# Chart colors matching the dark theme (palette lives in app.theme)
from app.theme import GOLD, BG_DARK, TEXT_COLOR, GRID_COLOR

BAR_COLORS = [GOLD, "#8b6914", "#d4b85c", "#a08030", "#e6cc80", "#6b5010"]


def style_axes(ax):
    ax.set_facecolor(BG_DARK)
    ax.tick_params(colors=TEXT_COLOR, which="both")
    ax.xaxis.label.set_color(TEXT_COLOR)
    ax.yaxis.label.set_color(TEXT_COLOR)
    ax.title.set_color(GOLD)
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)
    ax.grid(True, color=GRID_COLOR, alpha=0.5)


class ReportsTab(QWidget):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.setup_ui()
        self.on_report_changed()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        title = QLabel("Reports")
        title.setObjectName("sectionHeader")
        header.addWidget(title)
        header.addStretch()

        self.report_combo = QComboBox()
        self.report_combo.addItems([
            "Earnings — Gross vs Net",
            "Sales by Client",
            "Top Products",
            "Top Companies",
            "Revenue Over Time",
            "Aging Receivables",
            "Order Status Summary",
        ])
        self.report_combo.setMinimumWidth(200)
        self.report_combo.currentIndexChanged.connect(self.on_report_changed)
        header.addWidget(self.report_combo)

        # Period picker + print/save — earnings report only.
        self.period_combo = QComboBox()
        self.period_combo.addItems(["This Week", "This Month", "This Quarter", "This Year", "All Time"])
        self.period_combo.setCurrentText("This Month")
        self.period_combo.currentIndexChanged.connect(self.on_report_changed)
        header.addWidget(self.period_combo)

        self.print_btn = QPushButton("🖨 Print / PDF")
        self.print_btn.clicked.connect(self.print_earnings)
        header.addWidget(self.print_btn)

        self.save_btn = QPushButton("💾 Save to Reports Folder")
        self.save_btn.setObjectName("primaryBtn")
        self.save_btn.clicked.connect(self.save_earnings)
        header.addWidget(self.save_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.on_report_changed)
        header.addWidget(self.refresh_btn)

        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.clicked.connect(self.export_csv)
        header.addWidget(self.export_csv_btn)

        layout.addLayout(header)

        # Chart area
        self.figure = Figure(figsize=(8, 4), facecolor=BG_DARK)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(300)
        layout.addWidget(self.canvas)

        # Data table
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

    def on_report_changed(self):
        idx = self.report_combo.currentIndex()
        report_funcs = [
            self.report_earnings,
            self.report_sales_by_client,
            self.report_top_products,
            self.report_top_companies,
            self.report_revenue_over_time,
            self.report_aging_receivables,
            self.report_order_status,
        ]
        # Period picker + print/save only apply to the earnings report.
        is_earnings = idx == 0
        self.period_combo.setVisible(is_earnings)
        self.print_btn.setVisible(is_earnings)
        self.save_btn.setVisible(is_earnings)
        if 0 <= idx < len(report_funcs):
            report_funcs[idx]()

    def _fill_table(self, headers, data):
        """Generic table fill: headers + rows of stringable tuples."""
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setRowCount(len(data))
        for row, values in enumerate(data):
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))

    # ---- earnings (gross vs the broker's net cut) ----

    def _earnings_report_data(self):
        from datetime import date as _date
        from app.earnings import earnings_rows, earnings_by_company, period_range
        period = self.period_combo.currentText()
        start, end, label, bucket = period_range(period)
        session = self.db.session()
        try:
            rows, total_gross, total_net = earnings_rows(session, start, end, bucket)
            companies = earnings_by_company(session, start, end)
        finally:
            session.close()
        note = ""
        if any(c["pct"] == 0 and c["gross"] > 0 for c in companies):
            note = ("Some companies have no commission % set (net reports as $0 for them) — "
                    "set 'Your commission' on each company in the Companies section.")
        return {
            "period_label": f"{period} ({label})",
            "file_label": label,
            "generated": _date.today().isoformat(),
            "rows": rows,
            "total_gross": total_gross,
            "total_net": total_net,
            "companies": companies,
            "company": self.db.get_settings("company."),
            "note": note,
        }

    def report_earnings(self):
        rep = self._earnings_report_data()
        self._last_earnings = rep

        headers = ["Period", "Gross", "Net", "Net %"]
        data = [
            (r["label"], f"${r['gross']:,.2f}", f"${r['net']:,.2f}",
             f"{(r['net'] / r['gross'] * 100) if r['gross'] else 0:.1f}%")
            for r in rep["rows"]
        ]
        data.append(("TOTAL", f"${rep['total_gross']:,.2f}", f"${rep['total_net']:,.2f}",
                     f"{(rep['total_net'] / rep['total_gross'] * 100) if rep['total_gross'] else 0:.1f}%"))
        self._fill_table(headers, data)

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        style_axes(ax)
        if rep["rows"]:
            labels = [r["label"] for r in rep["rows"]]
            x = range(len(labels))
            width = 0.38
            ax.bar([i - width / 2 for i in x], [r["gross"] for r in rep["rows"]],
                   width, label="Gross", color=GOLD)
            ax.bar([i + width / 2 for i in x], [r["net"] for r in rep["rows"]],
                   width, label="Net (your cut)", color="#3aa657")
            ax.set_xticks(list(x))
            ax.set_xticklabels(labels, rotation=30, ha="right")
            leg = ax.legend(facecolor=BG_DARK, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)
            ax.set_title(f"Earnings — {rep['period_label']}", fontsize=14, color=GOLD)
        else:
            ax.set_title("No orders in this period", fontsize=14, color=GOLD)
        self.figure.tight_layout()
        self.canvas.draw()

    def print_earnings(self):
        from app.documents import DocPreviewDialog, earnings_html
        rep = getattr(self, "_last_earnings", None) or self._earnings_report_data()
        DocPreviewDialog(self, [{"title": f"Earnings {rep['file_label']}", "html": earnings_html(rep)}],
                         window_title="Earnings Report").exec()

    def save_earnings(self):
        import os
        from app.documents import earnings_html, save_html_pdf
        rep = getattr(self, "_last_earnings", None) or self._earnings_report_data()
        folder = self.db.reports_dir()
        path = os.path.join(folder, f"Earnings-{rep['file_label']}.pdf")
        save_html_pdf(earnings_html(rep), path)
        box = QMessageBox(self)
        box.setWindowTitle("Report Saved")
        box.setText(f"Saved {os.path.basename(path)} to your reports folder.")
        open_btn = box.addButton("Open Folder", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Ok)
        box.exec()
        if box.clickedButton() is open_btn:
            os.startfile(folder)

    def report_sales_by_client(self):
        session = self.db.session()
        try:
            clients = session.query(Client).all()
            data = []
            for c in clients:
                total = sum(o.total for o in c.orders if o.status != "Cancelled")
                count = sum(1 for o in c.orders if o.status != "Cancelled")
                if total > 0:
                    data.append((c.full_name, c.company or "", count, total))
            data.sort(key=lambda x: x[3], reverse=True)
        finally:
            session.close()

        # Table
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Client", "Company", "Orders", "Total Sales"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setRowCount(len(data))
        for row, (name, comp, cnt, total) in enumerate(data):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(comp))
            self.table.setItem(row, 2, QTableWidgetItem(str(cnt)))
            self.table.setItem(row, 3, QTableWidgetItem(f"${total:,.2f}"))

        # Chart
        self.figure.clear()
        if data:
            ax = self.figure.add_subplot(111)
            style_axes(ax)
            names = [d[0][:20] for d in data[:10]]
            totals = [d[3] for d in data[:10]]
            bars = ax.barh(names[::-1], totals[::-1], color=BAR_COLORS[:len(names)])
            ax.set_title("Top Clients by Sales", fontsize=14)
            ax.set_xlabel("Total Sales ($)")
            for bar, val in zip(bars, totals[::-1]):
                ax.text(bar.get_width() + max(totals) * 0.01, bar.get_y() + bar.get_height()/2,
                       f"${val:,.0f}", va="center", color=TEXT_COLOR, fontsize=9)
        self.figure.tight_layout()
        self.canvas.draw()

    def report_top_products(self):
        session = self.db.session()
        try:
            items = session.query(OrderItem).join(Order).filter(Order.status != "Cancelled").all()
            prod_sales = defaultdict(lambda: {"qty": 0, "revenue": 0.0, "name": ""})
            for item in items:
                pid = item.product_id
                prod_sales[pid]["qty"] += item.quantity
                prod_sales[pid]["revenue"] += item.line_total
                if item.product:
                    prod_sales[pid]["name"] = item.product.display_name
            data = [(v["name"], v["qty"], v["revenue"]) for v in prod_sales.values() if v["name"]]
            data.sort(key=lambda x: x[2], reverse=True)
        finally:
            session.close()

        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Product", "Units Sold", "Revenue"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setRowCount(len(data))
        for row, (name, qty, rev) in enumerate(data):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(str(qty)))
            self.table.setItem(row, 2, QTableWidgetItem(f"${rev:,.2f}"))

        self.figure.clear()
        if data:
            ax = self.figure.add_subplot(111)
            style_axes(ax)
            names = [d[0][:25] for d in data[:8]]
            revs = [d[2] for d in data[:8]]
            ax.bar(range(len(names)), revs, color=BAR_COLORS[:len(names)])
            ax.set_xticks(range(len(names)))
            ax.set_xticklabels(names, rotation=35, ha="right", fontsize=9)
            ax.set_title("Top Products by Revenue", fontsize=14)
            ax.set_ylabel("Revenue ($)")
        self.figure.tight_layout()
        self.canvas.draw()

    def report_top_companies(self):
        session = self.db.session()
        try:
            items = session.query(OrderItem).join(Order).join(Product).join(Company).filter(
                Order.status != "Cancelled"
            ).all()
            comp_sales = defaultdict(lambda: {"revenue": 0.0, "units": 0})
            for item in items:
                if item.product and item.product.company:
                    cname = item.product.company.name
                    comp_sales[cname]["revenue"] += item.line_total
                    comp_sales[cname]["units"] += item.quantity
            data = [(k, v["units"], v["revenue"]) for k, v in comp_sales.items()]
            data.sort(key=lambda x: x[2], reverse=True)
        finally:
            session.close()

        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Company", "Units Sold", "Revenue"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setRowCount(len(data))
        for row, (name, units, rev) in enumerate(data):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(str(units)))
            self.table.setItem(row, 2, QTableWidgetItem(f"${rev:,.2f}"))

        self.figure.clear()
        if data:
            ax = self.figure.add_subplot(111)
            style_axes(ax)
            names = [d[0] for d in data]
            revs = [d[2] for d in data]
            wedges, texts, autotexts = ax.pie(
                revs, labels=names, autopct="%1.1f%%",
                colors=BAR_COLORS[:len(names)],
                textprops={"color": TEXT_COLOR, "fontsize": 10}
            )
            ax.set_title("Revenue by Company", fontsize=14, color=GOLD)
        self.figure.tight_layout()
        self.canvas.draw()

    def report_revenue_over_time(self):
        session = self.db.session()
        try:
            orders = session.query(Order).filter(Order.status != "Cancelled").order_by(Order.order_date).all()
            monthly = defaultdict(float)
            for o in orders:
                key = o.order_date.strftime("%Y-%m")
                monthly[key] += o.total
            data = sorted(monthly.items())
        finally:
            session.close()

        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Month", "Revenue"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setRowCount(len(data))
        for row, (month, rev) in enumerate(data):
            self.table.setItem(row, 0, QTableWidgetItem(month))
            self.table.setItem(row, 1, QTableWidgetItem(f"${rev:,.2f}"))

        self.figure.clear()
        if data:
            ax = self.figure.add_subplot(111)
            style_axes(ax)
            months = [d[0] for d in data]
            revs = [d[1] for d in data]
            ax.plot(months, revs, color=GOLD, linewidth=2, marker="o", markersize=6)
            ax.fill_between(range(len(months)), revs, alpha=0.15, color=GOLD)
            ax.set_xticks(range(len(months)))
            ax.set_xticklabels(months, rotation=45, ha="right", fontsize=9)
            ax.set_title("Revenue Over Time", fontsize=14)
            ax.set_ylabel("Revenue ($)")
        self.figure.tight_layout()
        self.canvas.draw()

    def report_aging_receivables(self):
        session = self.db.session()
        try:
            pending = session.query(Order).filter(
                Order.status.in_(["Pending", "Confirmed", "Shipped"])
            ).all()
            today = date.today()
            data = []
            for o in pending:
                days = (today - o.order_date).days
                if days <= 30:
                    bucket = "0-30 days"
                elif days <= 60:
                    bucket = "31-60 days"
                elif days <= 90:
                    bucket = "61-90 days"
                else:
                    bucket = "90+ days"
                data.append((f"ORD-{o.id:04d}", o.client.full_name, str(o.order_date), o.status, days, bucket, o.total))
            data.sort(key=lambda x: x[4], reverse=True)
        finally:
            session.close()

        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Order", "Client", "Date", "Status", "Days", "Amount"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setRowCount(len(data))
        for row, (oid, client, dt, status, days, bucket, total) in enumerate(data):
            self.table.setItem(row, 0, QTableWidgetItem(oid))
            self.table.setItem(row, 1, QTableWidgetItem(client))
            self.table.setItem(row, 2, QTableWidgetItem(dt))
            self.table.setItem(row, 3, QTableWidgetItem(status))
            self.table.setItem(row, 4, QTableWidgetItem(f"{days}d ({bucket})"))
            self.table.setItem(row, 5, QTableWidgetItem(f"${total:,.2f}"))

        # Bucket summary chart
        buckets = defaultdict(float)
        for d in data:
            buckets[d[5]] += d[6]
        bucket_order = ["0-30 days", "31-60 days", "61-90 days", "90+ days"]
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        style_axes(ax)
        labels = [b for b in bucket_order if b in buckets]
        vals = [buckets[b] for b in labels]
        if vals:
            colors = ["#4a9c4a", "#c9a84c", "#c97a4c", "#c94c4c"][:len(labels)]
            ax.bar(labels, vals, color=colors)
            ax.set_title("Aging Receivables", fontsize=14)
            ax.set_ylabel("Outstanding ($)")
            for i, v in enumerate(vals):
                ax.text(i, v + max(vals) * 0.02, f"${v:,.0f}", ha="center", color=TEXT_COLOR, fontsize=10)
        self.figure.tight_layout()
        self.canvas.draw()

    def report_order_status(self):
        session = self.db.session()
        try:
            orders = session.query(Order).all()
            status_counts = defaultdict(lambda: {"count": 0, "total": 0.0})
            for o in orders:
                status_counts[o.status]["count"] += 1
                status_counts[o.status]["total"] += o.total
            data = [(k, v["count"], v["total"]) for k, v in status_counts.items()]
            data.sort(key=lambda x: x[2], reverse=True)
        finally:
            session.close()

        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Status", "Orders", "Total Value"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setRowCount(len(data))
        for row, (status, count, total) in enumerate(data):
            self.table.setItem(row, 0, QTableWidgetItem(status))
            self.table.setItem(row, 1, QTableWidgetItem(str(count)))
            self.table.setItem(row, 2, QTableWidgetItem(f"${total:,.2f}"))

        self.figure.clear()
        if data:
            ax = self.figure.add_subplot(111)
            style_axes(ax)
            labels = [d[0] for d in data]
            counts = [d[1] for d in data]
            wedges, texts, autotexts = ax.pie(
                counts, labels=labels, autopct="%1.0f%%",
                colors=BAR_COLORS[:len(labels)],
                textprops={"color": TEXT_COLOR, "fontsize": 11}
            )
            ax.set_title("Orders by Status", fontsize=14, color=GOLD)
        self.figure.tight_layout()
        self.canvas.draw()

    def export_csv(self):
        if self.table.rowCount() == 0:
            QMessageBox.information(self, "Export", "No data to export.")
            return
        report_name = self.report_combo.currentText().replace(" ", "_").lower()
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", f"{report_name}.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            headers = []
            for col in range(self.table.columnCount()):
                headers.append(self.table.horizontalHeaderItem(col).text())
            writer.writerow(headers)
            for row in range(self.table.rowCount()):
                row_data = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else "")
                writer.writerow(row_data)
        QMessageBox.information(self, "Export", f"Exported to {path}")
