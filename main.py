"""CigarBrokerCRM - Desktop CRM for cigar brokerage.
Main entry point with sidebar navigation."""

import sys
import os

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget, QLabel, QStatusBar,
    QMessageBox, QFileDialog, QPushButton, QMenuBar
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QAction, QFont, QShortcut, QKeySequence, QIcon

from app.database import DatabaseManager, Client, Order, Company, Product
from app.theme import DARK_THEME
from app.clients_tab import ClientsTab
from app.companies_tab import CompaniesTab
from app.orders_tab import OrdersTab
from app.reports_tab import ReportsTab
from app.calendar_tab import CalendarTab
from app.settings_tab import SettingsTab


class DashboardTab(QWidget):
    """Command-center home: the whole brokerage at a glance — money cards,
    gross-vs-net and status charts, a mini calendar, and what's coming up."""

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure
        from app.theme import BG_DARK

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)

        head = QHBoxLayout()
        self.title_label = QLabel(self.db.app_title())
        self.title_label.setStyleSheet("font-size: 26px; font-weight: bold; color: #c9a84c;")
        head.addWidget(self.title_label)
        subtitle = QLabel("  — the whole brokerage at a glance")
        subtitle.setStyleSheet("font-size: 13px; color: #888;")
        head.addWidget(subtitle)
        head.addStretch()
        tips = QLabel("Ctrl+1-7 sections · Ctrl+N new · Ctrl+F search · Ctrl+B backup")
        tips.setStyleSheet("font-size: 11px; color: #666;")
        head.addWidget(tips)
        layout.addLayout(head)

        # Money + volume cards
        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.client_count = self._make_card("Clients", "0")
        cards.addWidget(self.client_count[0])
        self.open_orders = self._make_card("Open Orders", "0")
        cards.addWidget(self.open_orders[0])
        self.unpaid = self._make_card("Unpaid Invoices", "$0")
        cards.addWidget(self.unpaid[0])
        self.gross_ytd = self._make_card("Gross YTD", "$0")
        cards.addWidget(self.gross_ytd[0])
        self.net_ytd = self._make_card("Net YTD (your cut)", "$0")
        cards.addWidget(self.net_ytd[0])
        layout.addLayout(cards)

        # Charts row
        charts = QHBoxLayout()
        charts.setSpacing(14)
        self.trend_fig = Figure(figsize=(5, 2.6), facecolor=BG_DARK)
        self.trend_canvas = FigureCanvas(self.trend_fig)
        self.trend_canvas.setMinimumHeight(210)
        charts.addWidget(self.trend_canvas, 3)
        self.status_fig = Figure(figsize=(3, 2.6), facecolor=BG_DARK)
        self.status_canvas = FigureCanvas(self.status_fig)
        self.status_canvas.setMinimumHeight(210)
        charts.addWidget(self.status_canvas, 2)
        layout.addLayout(charts)

        # Bottom row: mini calendar + next 7 days
        bottom = QHBoxLayout()
        bottom.setSpacing(14)
        from PySide6.QtWidgets import QCalendarWidget
        self.mini_cal = QCalendarWidget()
        self.mini_cal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.mini_cal.setMaximumWidth(420)
        bottom.addWidget(self.mini_cal, 2)

        upcoming_box = QVBoxLayout()
        up_label = QLabel("Next 7 days")
        up_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #c9a84c;")
        upcoming_box.addWidget(up_label)
        self.upcoming = QLabel("—")
        self.upcoming.setStyleSheet("font-size: 12.5px; line-height: 1.7;")
        self.upcoming.setWordWrap(True)
        self.upcoming.setAlignment(Qt.AlignTop)
        upcoming_box.addWidget(self.upcoming, 1)
        bottom.addLayout(upcoming_box, 3)
        layout.addLayout(bottom, 1)

    def _make_card(self, label_text, value_text):
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: #12122a;
                border: 1px solid #2a2a4a;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        cl = QVBoxLayout(card)
        cl.setAlignment(Qt.AlignCenter)
        val = QLabel(value_text)
        val.setObjectName("statLabel")
        val.setAlignment(Qt.AlignCenter)
        cl.addWidget(val)
        lbl = QLabel(label_text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #888; font-size: 12px;")
        cl.addWidget(lbl)
        return card, val

    def refresh(self):
        from datetime import date, timedelta
        from sqlalchemy import func
        from app.earnings import earnings_rows
        from app.theme import GOLD, BG_DARK, TEXT_COLOR, GRID_COLOR
        from app.reports_tab import style_axes
        from app.calendar_tab import apply_month_formats
        from app.database import Event

        today = date.today()
        session = self.db.session()
        try:
            self.client_count[1].setText(str(session.query(Client).count()))
            open_statuses = ["Pending", "Confirmed", "Shipped"]
            self.open_orders[1].setText(
                str(session.query(Order).filter(Order.status.in_(open_statuses)).count()))

            unpaid_q = session.query(func.count(Order.id), func.sum(Order.total)).filter(
                Order.is_paid == False, Order.status != "Cancelled")  # noqa: E712
            u_count, u_sum = unpaid_q.one()
            self.unpaid[1].setText(f"${u_sum or 0:,.0f} ({u_count})")

            # YTD gross/net from the same engine the earnings report uses.
            ytd_rows, ytd_gross, ytd_net = earnings_rows(
                session, date(today.year, 1, 1), today, "month")
            self.gross_ytd[1].setText(f"${ytd_gross:,.0f}")
            self.net_ytd[1].setText(f"${ytd_net:,.0f}")

            # Last 6 months gross vs net.
            six_ago = date(today.year if today.month > 5 else today.year - 1,
                           (today.month - 5 - 1) % 12 + 1, 1)
            rows, _, _ = earnings_rows(session, six_ago, today, "month")

            # Status counts for the donut.
            status_counts = dict(
                session.query(Order.status, func.count(Order.id)).group_by(Order.status).all())

            # Next 7 days: events + any expected activity.
            week_end = today + timedelta(days=7)
            events = (session.query(Event)
                      .filter(Event.date >= today, Event.date <= week_end)
                      .order_by(Event.date, Event.time).all())
            lines = []
            for e in events[:8]:
                who = e.client.full_name if e.client else (e.company.name if e.company else "")
                when = "today" if e.date == today else e.date.strftime("%a %b %d")
                lines.append(f"<span style='color:{GOLD};'>▸</span> {when}"
                             f"{' ' + e.time if e.time else ''} — {e.kind}: {e.title}"
                             f"{' (' + who + ')' if who else ''}")
        finally:
            session.close()

        self.upcoming.setText("<br>".join(lines) if lines
                              else "Nothing scheduled — add events in the Calendar section (Ctrl+5).")

        # Trend chart: gross vs net by month.
        self.trend_fig.clear()
        ax = self.trend_fig.add_subplot(111)
        style_axes(ax)
        if rows:
            labels = [r["label"][5:] + "/" + r["label"][2:4] for r in rows]  # MM/YY
            x = range(len(labels))
            w = 0.38
            ax.bar([i - w / 2 for i in x], [r["gross"] for r in rows], w, label="Gross", color=GOLD)
            ax.bar([i + w / 2 for i in x], [r["net"] for r in rows], w, label="Net", color="#3aa657")
            ax.set_xticks(list(x))
            ax.set_xticklabels(labels)
            ax.legend(facecolor=BG_DARK, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR, fontsize=8)
        ax.set_title("Gross vs Net — last 6 months", fontsize=11, color=GOLD)
        self.trend_fig.tight_layout()
        self.trend_canvas.draw()

        # Status donut.
        self.status_fig.clear()
        ax2 = self.status_fig.add_subplot(111)
        if status_counts:
            colors = {"Pending": "#c9a84c", "Confirmed": "#4aa3c9", "Shipped": "#8b6914",
                      "Delivered": "#3aa657", "Completed": "#2e7d4f", "Cancelled": "#8b2252"}
            names = list(status_counts.keys())
            wedges, texts, autotexts = ax2.pie(
                [status_counts[n] for n in names],
                labels=names, autopct="%1.0f%%", startangle=90,
                colors=[colors.get(n, "#666") for n in names],
                wedgeprops={"width": 0.45, "edgecolor": BG_DARK},
                textprops={"color": TEXT_COLOR, "fontsize": 8})
            for at in autotexts:
                at.set_fontsize(7)
        ax2.set_title("Orders by status", fontsize=11, color=GOLD)
        self.status_fig.patch.set_facecolor(BG_DARK)
        self.status_fig.tight_layout()
        self.status_canvas.draw()

        # Mini calendar highlights (events gold, orders blue).
        apply_month_formats(self.mini_cal, self.db)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()

        # Seed sample data on first run
        if not self.db.has_data():
            self.db.seed_sample_data()

        self.setWindowTitle(self.db.app_title())
        self.setMinimumSize(1200, 750)
        self.resize(1400, 850)
        self.setup_menu()
        self.setup_ui()
        self.setup_shortcuts()
        self.setup_statusbar()

    def apply_branding(self):
        """Re-read the company name and update every place the app names itself.
        Called live when Settings is saved."""
        title = self.db.app_title()
        self.setWindowTitle(title)
        if hasattr(self, "dashboard"):
            self.dashboard.title_label.setText(title)
        cur = self.sidebar.currentRow()
        names = ["Dashboard", "Clients", "Companies", "Orders", "Calendar", "Reports", "Settings"]
        if 0 <= cur < len(names):
            self.statusBar().showMessage(f"{names[cur]} — {title}")

    def setup_menu(self):
        menu = self.menuBar()

        file_menu = menu.addMenu("&File")

        backup_action = QAction("&Backup Database", self)
        backup_action.setShortcut(QKeySequence("Ctrl+B"))
        backup_action.triggered.connect(self.backup_db)
        file_menu.addAction(backup_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menu.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(200)
        self.sidebar.setIconSize(QSize(20, 20))

        sections = [
            ("  Dashboard", "Home"),
            ("  Clients", "Clients"),
            ("  Companies", "Companies"),
            ("  Orders", "Orders"),
            ("  Calendar", "Events, meetings, deliveries"),
            ("  Reports", "Reports"),
            ("  Settings", "Your company info & invoicing"),
        ]
        for text, tooltip in sections:
            item = QListWidgetItem(text)
            item.setToolTip(tooltip)
            item.setSizeHint(QSize(0, 48))
            self.sidebar.addItem(item)

        self.sidebar.setCurrentRow(0)
        self.sidebar.currentRowChanged.connect(self.switch_tab)
        main_layout.addWidget(self.sidebar)

        # Content stack
        self.stack = QStackedWidget()

        self.dashboard = DashboardTab(self.db)
        self.stack.addWidget(self.dashboard)

        self.clients_tab = ClientsTab(self.db)
        self.stack.addWidget(self.clients_tab)

        self.companies_tab = CompaniesTab(self.db)
        self.stack.addWidget(self.companies_tab)

        self.orders_tab = OrdersTab(self.db)
        self.stack.addWidget(self.orders_tab)

        self.calendar_tab = CalendarTab(self.db)
        self.stack.addWidget(self.calendar_tab)

        self.reports_tab = ReportsTab(self.db)
        self.stack.addWidget(self.reports_tab)

        self.settings_tab = SettingsTab(self.db)
        self.stack.addWidget(self.settings_tab)

        main_layout.addWidget(self.stack)

    def setup_shortcuts(self):
        for i in range(7):
            QShortcut(QKeySequence(f"Ctrl+{i+1}"), self, lambda idx=i: self.sidebar.setCurrentRow(idx))

    def setup_statusbar(self):
        self.statusBar().showMessage("Ready")

    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.dashboard.refresh()
        elif index == 4:
            self.calendar_tab.refresh()  # pick up orders/events added elsewhere
        elif index == 6:
            self.settings_tab.load()  # re-read in case another path changed settings
        names = ["Dashboard", "Clients", "Companies", "Orders", "Calendar", "Reports", "Settings"]
        if 0 <= index < len(names):
            self.statusBar().showMessage(f"{names[index]} — {self.db.app_title()}")

    def backup_db(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Backup Database", "cigarbroker_backup.db", "SQLite Database (*.db)"
        )
        if path:
            try:
                dest = self.db.backup(path)
                QMessageBox.information(self, "Backup", f"Database backed up to:\n{dest}")
            except Exception as e:
                QMessageBox.critical(self, "Backup Error", str(e))

    def show_about(self):
        title = self.db.app_title()
        QMessageBox.about(
            self, f"About {title}",
            f"<h2 style='color:#c9a84c;'>{title}</h2>"
            "<p>Desktop CRM for cigar brokerage operations.</p>"
            "<p>Manage clients, companies, orders, and generate reports.</p>"
            "<p style='color:#888;'>Built with PySide6 + SQLAlchemy</p>"
            "<p style='color:#888;'>Data stored locally in SQLite.</p>"
        )


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CigarBrokerCRM")
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_THEME)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
