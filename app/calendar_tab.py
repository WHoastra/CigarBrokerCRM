"""Calendar module - brokerage events (meetings, calls, deliveries,
follow-ups) plus a read-only overlay of order dates. The same date-formatting
helper drives the dashboard's mini calendar."""

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCalendarWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QDialog, QFormLayout, QLineEdit,
    QTextEdit, QComboBox, QDateEdit, QHeaderView, QMessageBox,
    QAbstractItemView, QSplitter
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QTextCharFormat, QColor, QFont, QShortcut, QKeySequence

from sqlalchemy import func

from app.database import DatabaseManager, Event, Order, Client, Company, Communication
from app.theme import GOLD

EVENT_KINDS = ["Meeting", "Call", "Delivery", "Follow-up", "Other"]
ORDER_BLUE = "#4aa3c9"


def apply_month_formats(calendar: QCalendarWidget, db: DatabaseManager):
    """Highlight dates that hold events (gold, bold) or orders (blue) for the
    calendar's currently visible month ±1 (so edges of the grid show too)."""
    calendar.setDateTextFormat(QDate(), QTextCharFormat())  # clear all custom formats

    shown = date(calendar.yearShown(), calendar.monthShown(), 1)
    start = date(shown.year if shown.month > 1 else shown.year - 1,
                 shown.month - 1 if shown.month > 1 else 12, 1)
    if shown.month >= 11:
        end = date(shown.year + 1, shown.month - 10, 28)
    else:
        end = date(shown.year, shown.month + 2, 28)

    session = db.session()
    try:
        event_dates = {e.date for e in session.query(Event)
                       .filter(Event.date >= start, Event.date <= end).all()}
        order_dates = {o.order_date for o in session.query(Order)
                       .filter(Order.order_date >= start, Order.order_date <= end).all()}
    finally:
        session.close()

    order_fmt = QTextCharFormat()
    order_fmt.setForeground(QColor(ORDER_BLUE))
    for d in order_dates:
        calendar.setDateTextFormat(QDate(d.year, d.month, d.day), order_fmt)

    event_fmt = QTextCharFormat()
    event_fmt.setForeground(QColor(GOLD))
    event_fmt.setFontWeight(QFont.Bold)
    both_fmt = QTextCharFormat(event_fmt)
    both_fmt.setFontUnderline(True)  # events AND orders that day
    for d in event_dates:
        fmt = both_fmt if d in order_dates else event_fmt
        calendar.setDateTextFormat(QDate(d.year, d.month, d.day), fmt)


class EventDialog(QDialog):
    def __init__(self, parent=None, db=None, event=None, default_date=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Edit Event" if event else "New Event")
        self.setMinimumWidth(420)
        form = QFormLayout(self)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        d = event.date if event else (default_date or date.today())
        self.date_edit.setDate(QDate(d.year, d.month, d.day))
        form.addRow("Date", self.date_edit)

        self.time = QLineEdit()
        self.time.setPlaceholderText("2:30 PM (optional)")
        form.addRow("Time", self.time)

        self.title = QLineEdit()
        form.addRow("Title *", self.title)

        self.kind = QComboBox()
        self.kind.addItems(EVENT_KINDS)
        form.addRow("Type", self.kind)

        # Optional links back to a client / company.
        self.client_combo = QComboBox()
        self.client_combo.addItem("(none)", None)
        self.company_combo = QComboBox()
        self.company_combo.addItem("(none)", None)
        session = db.session()
        try:
            for c in session.query(Client).order_by(Client.last_name).all():
                self.client_combo.addItem(c.full_name, c.id)
            for co in session.query(Company).order_by(Company.name).all():
                self.company_combo.addItem(co.name, co.id)
        finally:
            session.close()
        form.addRow("Client", self.client_combo)
        form.addRow("Company", self.company_combo)

        self.notes = QTextEdit()
        self.notes.setMaximumHeight(60)
        form.addRow("Notes", self.notes)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        save = QPushButton("Save")
        save.setObjectName("primaryBtn")
        save.clicked.connect(self.accept)
        btns.addWidget(save)
        form.addRow(btns)

        if event:
            self.time.setText(event.time or "")
            self.title.setText(event.title)
            idx = self.kind.findText(event.kind or "Meeting")
            if idx >= 0:
                self.kind.setCurrentIndex(idx)
            for combo, val in ((self.client_combo, event.client_id),
                               (self.company_combo, event.company_id)):
                for i in range(combo.count()):
                    if combo.itemData(i) == val:
                        combo.setCurrentIndex(i)
                        break
            self.notes.setPlainText(event.notes or "")

    def get_data(self):
        qd = self.date_edit.date()
        return {
            "date": date(qd.year(), qd.month(), qd.day()),
            "time": self.time.text().strip(),
            "title": self.title.text().strip(),
            "kind": self.kind.currentText(),
            "client_id": self.client_combo.currentData(),
            "company_id": self.company_combo.currentData(),
            "notes": self.notes.toPlainText().strip(),
        }

    def accept(self):
        if not self.title.text().strip():
            QMessageBox.warning(self, "Validation", "Event title is required.")
            return
        super().accept()


class CalendarTab(QWidget):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        title = QLabel("Calendar")
        title.setObjectName("sectionHeader")
        header.addWidget(title)
        legend = QLabel(f'<span style="color:{GOLD};">■</span> events&nbsp;&nbsp;'
                        f'<span style="color:{ORDER_BLUE};">■</span> orders')
        legend.setStyleSheet("color: #888;")
        header.addWidget(legend)
        header.addStretch()
        add_btn = QPushButton("+ New Event")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self.add_event)
        header.addWidget(add_btn)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)

        self.calendar = QCalendarWidget()
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.selectionChanged.connect(self.load_day)
        self.calendar.currentPageChanged.connect(lambda *_: apply_month_formats(self.calendar, self.db))
        splitter.addWidget(self.calendar)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)

        self.day_label = QLabel("")
        self.day_label.setStyleSheet(f"font-weight: bold; color: {GOLD}; font-size: 15px;")
        right_layout.addWidget(self.day_label)

        self.day_table = QTableWidget()
        self.day_table.setColumnCount(3)
        self.day_table.setHorizontalHeaderLabels(["Time", "Type", "What"])
        self.day_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.day_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.day_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.day_table.setAlternatingRowColors(True)
        self.day_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.day_table.verticalHeader().setVisible(False)
        self.day_table.itemSelectionChanged.connect(self._sync_buttons)
        self.day_table.doubleClicked.connect(self.edit_event)
        right_layout.addWidget(self.day_table)

        btn_row = QHBoxLayout()
        self.edit_btn = QPushButton("Edit Event")
        self.edit_btn.clicked.connect(self.edit_event)
        self.edit_btn.setEnabled(False)
        btn_row.addWidget(self.edit_btn)
        self.del_btn = QPushButton("Delete Event")
        self.del_btn.setObjectName("dangerBtn")
        self.del_btn.clicked.connect(self.delete_event)
        self.del_btn.setEnabled(False)
        btn_row.addWidget(self.del_btn)
        btn_row.addStretch()
        right_layout.addLayout(btn_row)

        splitter.addWidget(right)
        splitter.setSizes([440, 460])
        layout.addWidget(splitter)

        QShortcut(QKeySequence("Ctrl+N"), self, self.add_event)

    # ---- data ----

    def selected_date(self):
        qd = self.calendar.selectedDate()
        return date(qd.year(), qd.month(), qd.day())

    def refresh(self):
        apply_month_formats(self.calendar, self.db)
        self.load_day()

    def load_day(self):
        d = self.selected_date()
        self.day_label.setText(d.strftime("%A, %B %d, %Y"))
        session = self.db.session()
        try:
            events = (session.query(Event).filter(Event.date == d)
                      .order_by(Event.time).all())
            orders = session.query(Order).filter(Order.order_date == d).all()
            rows = []
            for e in events:
                who = e.client.full_name if e.client else (e.company.name if e.company else "")
                rows.append((e.id, e.time or "—", e.kind,
                             e.title + (f"  ({who})" if who else "")))
            for o in orders:
                rows.append((None, "—", "Order",
                             f"ORD-{o.id:04d} — {o.client.full_name} — ${o.total:,.2f}"))
            # Communication log entries (client OR company) from that day.
            comms = (session.query(Communication)
                     .filter(func.date(Communication.timestamp) == d.isoformat()).all())
            for cm in comms:
                who = cm.client.full_name if cm.client else (cm.company.name if cm.company else "")
                when = cm.timestamp.strftime("%I:%M %p").lstrip("0")
                rows.append((None, when, f"Log: {cm.comm_type}",
                             f"{cm.subject or '(no subject)'}" + (f" — {who}" if who else "")))
        finally:
            session.close()

        self.day_table.setRowCount(len(rows))
        for row, (eid, time_s, kind, what) in enumerate(rows):
            t_item = QTableWidgetItem(time_s)
            t_item.setData(Qt.UserRole, eid)  # None for read-only order rows
            self.day_table.setItem(row, 0, t_item)
            self.day_table.setItem(row, 1, QTableWidgetItem(kind))
            self.day_table.setItem(row, 2, QTableWidgetItem(what))
        self._sync_buttons()

    def _selected_event_id(self):
        rows = self.day_table.selectionModel().selectedRows()
        return self.day_table.item(rows[0].row(), 0).data(Qt.UserRole) if rows else None

    def _sync_buttons(self):
        eid = self._selected_event_id()
        self.edit_btn.setEnabled(eid is not None)
        self.del_btn.setEnabled(eid is not None)

    # ---- CRUD ----

    def add_event(self):
        dlg = EventDialog(self, db=self.db, default_date=self.selected_date())
        if dlg.exec() == QDialog.Accepted:
            session = self.db.session()
            try:
                session.add(Event(**dlg.get_data()))
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
            self.refresh()

    def edit_event(self):
        eid = self._selected_event_id()
        if eid is None:
            return
        session = self.db.session()
        try:
            event = session.query(Event).get(eid)
            if not event:
                return
            dlg = EventDialog(self, db=self.db, event=event)
            if dlg.exec() == QDialog.Accepted:
                for k, v in dlg.get_data().items():
                    setattr(event, k, v)
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
        self.refresh()

    def delete_event(self):
        eid = self._selected_event_id()
        if eid is None:
            return
        if QMessageBox.question(self, "Delete Event", "Delete this event?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        session = self.db.session()
        try:
            event = session.query(Event).get(eid)
            if event:
                session.delete(event)
                session.commit()
        finally:
            session.close()
        self.refresh()
