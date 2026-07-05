"""Clients module - Full CRUD with rich profiles, communication log, purchase history."""

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QLabel, QDialog, QFormLayout, QTextEdit,
    QComboBox, QDoubleSpinBox, QHeaderView, QMessageBox, QTabWidget,
    QAbstractItemView, QSplitter
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QShortcut, QKeySequence

from app.database import DatabaseManager, Client, Communication


class ClientDialog(QDialog):
    """Dialog for creating/editing a client."""

    def __init__(self, parent=None, client=None, db=None):
        super().__init__(parent)
        self.db = db
        self.client = client
        self.setWindowTitle("Edit Client" if client else "New Client")
        self.setMinimumWidth(500)
        self.setup_ui()
        if client:
            self.populate(client)

    def setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)

        self.first_name = QLineEdit()
        self.first_name.setPlaceholderText("First name")
        layout.addRow("First Name *", self.first_name)

        self.last_name = QLineEdit()
        self.last_name.setPlaceholderText("Last name")
        layout.addRow("Last Name *", self.last_name)

        self.company = QLineEdit()
        self.company.setPlaceholderText("Company name")
        layout.addRow("Company", self.company)

        self.email = QLineEdit()
        self.email.setPlaceholderText("email@example.com")
        layout.addRow("Email", self.email)

        self.phone = QLineEdit()
        self.phone.setPlaceholderText("555-555-5555")
        layout.addRow("Phone", self.phone)

        self.address = QLineEdit()
        layout.addRow("Address", self.address)

        row = QHBoxLayout()
        self.city = QLineEdit()
        self.city.setPlaceholderText("City")
        self.state = QLineEdit()
        self.state.setPlaceholderText("ST")
        self.state.setMaximumWidth(60)
        self.zip_code = QLineEdit()
        self.zip_code.setPlaceholderText("Zip")
        self.zip_code.setMaximumWidth(100)
        row.addWidget(self.city, 3)
        row.addWidget(self.state, 1)
        row.addWidget(self.zip_code, 1)
        layout.addRow("City/State/Zip", row)

        self.tags = QLineEdit()
        self.tags.setPlaceholderText("comma-separated tags")
        layout.addRow("Tags", self.tags)

        self.preferred_brands = QLineEdit()
        self.preferred_brands.setPlaceholderText("comma-separated brands")
        layout.addRow("Preferred Brands", self.preferred_brands)

        self.credit_limit = QDoubleSpinBox()
        self.credit_limit.setRange(0, 999999)
        self.credit_limit.setPrefix("$")
        self.credit_limit.setDecimals(2)
        layout.addRow("Credit Limit", self.credit_limit)

        self.payment_terms = QComboBox()
        self.payment_terms.addItems(["Net 15", "Net 30", "Net 45", "Net 60", "COD", "Prepaid"])
        self.payment_terms.setEditable(True)
        layout.addRow("Payment Terms", self.payment_terms)

        self.notes = QTextEdit()
        self.notes.setMaximumHeight(80)
        self.notes.setPlaceholderText("Additional notes...")
        layout.addRow("Notes", self.notes)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addRow("", btn_row)

    def populate(self, c):
        self.first_name.setText(c.first_name)
        self.last_name.setText(c.last_name)
        self.company.setText(c.company or "")
        self.email.setText(c.email or "")
        self.phone.setText(c.phone or "")
        self.address.setText(c.address or "")
        self.city.setText(c.city or "")
        self.state.setText(c.state or "")
        self.zip_code.setText(c.zip_code or "")
        self.tags.setText(c.tags or "")
        self.preferred_brands.setText(c.preferred_brands or "")
        self.credit_limit.setValue(c.credit_limit or 0)
        idx = self.payment_terms.findText(c.payment_terms or "Net 30")
        if idx >= 0:
            self.payment_terms.setCurrentIndex(idx)
        else:
            self.payment_terms.setEditText(c.payment_terms or "")
        self.notes.setPlainText(c.notes or "")

    def get_data(self):
        return {
            "first_name": self.first_name.text().strip(),
            "last_name": self.last_name.text().strip(),
            "company": self.company.text().strip(),
            "email": self.email.text().strip(),
            "phone": self.phone.text().strip(),
            "address": self.address.text().strip(),
            "city": self.city.text().strip(),
            "state": self.state.text().strip(),
            "zip_code": self.zip_code.text().strip(),
            "tags": self.tags.text().strip(),
            "preferred_brands": self.preferred_brands.text().strip(),
            "credit_limit": self.credit_limit.value(),
            "payment_terms": self.payment_terms.currentText(),
            "notes": self.notes.toPlainText().strip(),
        }

    def accept(self):
        if not self.first_name.text().strip() or not self.last_name.text().strip():
            QMessageBox.warning(self, "Validation", "First and last name are required.")
            return
        super().accept()


class CommDialog(QDialog):
    """Dialog for adding a communication log entry."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Log Communication")
        self.setMinimumWidth(450)
        layout = QFormLayout(self)

        self.comm_type = QComboBox()
        self.comm_type.addItems(["Email", "Call", "Meeting", "Note"])
        layout.addRow("Type", self.comm_type)

        self.subject = QLineEdit()
        self.subject.setPlaceholderText("Subject")
        layout.addRow("Subject", self.subject)

        self.body = QTextEdit()
        self.body.setMaximumHeight(120)
        self.body.setPlaceholderText("Details...")
        layout.addRow("Details", self.body)

        btn_row = QHBoxLayout()
        save = QPushButton("Save")
        save.setObjectName("primaryBtn")
        save.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        layout.addRow("", btn_row)

    def get_data(self):
        return {
            "comm_type": self.comm_type.currentText(),
            "subject": self.subject.text().strip(),
            "body": self.body.toPlainText().strip(),
        }


class ClientsTab(QWidget):
    """Main clients view with list, detail, and communication log."""

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_client_id = None
        self.setup_ui()
        self.load_clients()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        header = QHBoxLayout()
        title = QLabel("Clients")
        title.setObjectName("sectionHeader")
        header.addWidget(title)
        header.addStretch()

        self.search = QLineEdit()
        self.search.setObjectName("searchField")
        self.search.setPlaceholderText("Search clients... (Ctrl+F)")
        self.search.setMinimumWidth(250)
        self.search.textChanged.connect(self.filter_clients)
        header.addWidget(self.search)

        add_btn = QPushButton("+ New Client")
        add_btn.setObjectName("primaryBtn")
        add_btn.setToolTip("Add new client (Ctrl+N)")
        add_btn.clicked.connect(self.add_client)
        header.addWidget(add_btn)

        layout.addLayout(header)

        # Splitter: table on left, detail on right
        splitter = QSplitter(Qt.Horizontal)

        # Client table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Name", "Company", "Email", "Phone", "Tags", "Credit"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.table.doubleClicked.connect(self.edit_client)
        splitter.addWidget(self.table)

        # Detail panel
        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(8, 0, 0, 0)

        self.detail_name = QLabel("Select a client")
        self.detail_name.setObjectName("sectionHeader")
        detail_layout.addWidget(self.detail_name)

        self.detail_info = QLabel("")
        self.detail_info.setWordWrap(True)
        detail_layout.addWidget(self.detail_info)

        # Action buttons
        btn_row = QHBoxLayout()
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self.edit_client)
        self.edit_btn.setEnabled(False)
        btn_row.addWidget(self.edit_btn)

        self.del_btn = QPushButton("Delete")
        self.del_btn.setObjectName("dangerBtn")
        self.del_btn.clicked.connect(self.delete_client)
        self.del_btn.setEnabled(False)
        btn_row.addWidget(self.del_btn)

        self.comm_btn = QPushButton("+ Log Comm")
        self.comm_btn.clicked.connect(self.add_communication)
        self.comm_btn.setEnabled(False)
        btn_row.addWidget(self.comm_btn)

        btn_row.addStretch()
        detail_layout.addLayout(btn_row)

        # Tabs for comm log and order history
        self.detail_tabs = QTabWidget()

        # Communication log
        self.comm_table = QTableWidget()
        self.comm_table.setColumnCount(4)
        self.comm_table.setHorizontalHeaderLabels(["Date", "Type", "Subject", "Details"])
        self.comm_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.comm_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.comm_table.setAlternatingRowColors(True)
        self.comm_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.comm_table.verticalHeader().setVisible(False)
        self.detail_tabs.addTab(self.comm_table, "Communications")

        # Order history
        self.order_table = QTableWidget()
        self.order_table.setColumnCount(4)
        self.order_table.setHorizontalHeaderLabels(["Date", "Status", "Items", "Total"])
        self.order_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.order_table.setAlternatingRowColors(True)
        self.order_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.order_table.verticalHeader().setVisible(False)
        self.detail_tabs.addTab(self.order_table, "Order History")

        # Multiple contacts per client (buyer, assistant, …)
        from app.contacts import ContactsPanel
        self.contacts_panel = ContactsPanel(self.db, "client")
        self.detail_tabs.addTab(self.contacts_panel, "Contacts")

        detail_layout.addWidget(self.detail_tabs)
        splitter.addWidget(detail)

        splitter.setSizes([500, 400])
        layout.addWidget(splitter)

        # Shortcuts
        QShortcut(QKeySequence("Ctrl+N"), self, self.add_client)
        QShortcut(QKeySequence("Ctrl+F"), self, lambda: self.search.setFocus())
        QShortcut(QKeySequence("Delete"), self, self.delete_client)

    def load_clients(self, filter_text=""):
        self.table.setRowCount(0)
        session = self.db.session()
        try:
            q = session.query(Client)
            if filter_text:
                ft = f"%{filter_text}%"
                q = q.filter(
                    (Client.first_name.ilike(ft)) |
                    (Client.last_name.ilike(ft)) |
                    (Client.company.ilike(ft)) |
                    (Client.email.ilike(ft)) |
                    (Client.tags.ilike(ft))
                )
            clients = q.order_by(Client.last_name, Client.first_name).all()
            self.table.setRowCount(len(clients))
            for row, c in enumerate(clients):
                name_item = QTableWidgetItem(c.full_name)
                name_item.setData(Qt.UserRole, c.id)
                self.table.setItem(row, 0, name_item)
                self.table.setItem(row, 1, QTableWidgetItem(c.company or ""))
                self.table.setItem(row, 2, QTableWidgetItem(c.email or ""))
                self.table.setItem(row, 3, QTableWidgetItem(c.phone or ""))
                self.table.setItem(row, 4, QTableWidgetItem(c.tags or ""))
                self.table.setItem(row, 5, QTableWidgetItem(f"${c.credit_limit:,.2f}"))
        finally:
            session.close()

    def filter_clients(self, text):
        self.load_clients(text)

    def on_selection_changed(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.current_client_id = None
            self.detail_name.setText("Select a client")
            self.detail_info.setText("")
            self.edit_btn.setEnabled(False)
            self.del_btn.setEnabled(False)
            self.comm_btn.setEnabled(False)
            self.comm_table.setRowCount(0)
            self.order_table.setRowCount(0)
            self.contacts_panel.set_owner(None)
            return

        item = self.table.item(rows[0].row(), 0)
        client_id = item.data(Qt.UserRole)
        self.current_client_id = client_id
        self.edit_btn.setEnabled(True)
        self.del_btn.setEnabled(True)
        self.comm_btn.setEnabled(True)
        self.contacts_panel.set_owner(client_id)
        self.load_detail(client_id)

    def load_detail(self, client_id):
        session = self.db.session()
        try:
            c = session.query(Client).get(client_id)
            if not c:
                return
            self.detail_name.setText(c.full_name)
            info = []
            if c.company:
                info.append(f"<b>Company:</b> {c.company}")
            if c.email:
                info.append(f"<b>Email:</b> {c.email}")
            if c.phone:
                info.append(f"<b>Phone:</b> {c.phone}")
            loc_parts = [p for p in [c.city, c.state, c.zip_code] if p]
            if loc_parts:
                info.append(f"<b>Location:</b> {', '.join(loc_parts)}")
            if c.address:
                info.append(f"<b>Address:</b> {c.address}")
            if c.tags:
                info.append(f"<b>Tags:</b> {c.tags}")
            if c.preferred_brands:
                info.append(f"<b>Preferred Brands:</b> {c.preferred_brands}")
            info.append(f"<b>Credit Limit:</b> ${c.credit_limit:,.2f}")
            info.append(f"<b>Terms:</b> {c.payment_terms}")
            if c.notes:
                info.append(f"<b>Notes:</b> {c.notes}")
            self.detail_info.setText("<br>".join(info))

            # Load communications
            comms = sorted(c.communications, key=lambda x: x.timestamp, reverse=True)
            self.comm_table.setRowCount(len(comms))
            for row, comm in enumerate(comms):
                self.comm_table.setItem(row, 0, QTableWidgetItem(comm.timestamp.strftime("%Y-%m-%d %H:%M")))
                self.comm_table.setItem(row, 1, QTableWidgetItem(comm.comm_type))
                self.comm_table.setItem(row, 2, QTableWidgetItem(comm.subject))
                self.comm_table.setItem(row, 3, QTableWidgetItem(comm.body or ""))

            # Load orders
            orders = sorted(c.orders, key=lambda x: x.order_date, reverse=True)
            self.order_table.setRowCount(len(orders))
            for row, order in enumerate(orders):
                self.order_table.setItem(row, 0, QTableWidgetItem(str(order.order_date)))
                self.order_table.setItem(row, 1, QTableWidgetItem(order.status))
                self.order_table.setItem(row, 2, QTableWidgetItem(str(len(order.items))))
                self.order_table.setItem(row, 3, QTableWidgetItem(f"${order.total:,.2f}"))
        finally:
            session.close()

    def add_client(self):
        dlg = ClientDialog(self, db=self.db)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            session = self.db.session()
            try:
                c = Client(**data)
                session.add(c)
                session.commit()
            finally:
                session.close()
            self.load_clients(self.search.text())

    def edit_client(self):
        if not self.current_client_id:
            return
        session = self.db.session()
        try:
            c = session.query(Client).get(self.current_client_id)
            if not c:
                return
            dlg = ClientDialog(self, client=c, db=self.db)
            if dlg.exec() == QDialog.Accepted:
                data = dlg.get_data()
                for k, v in data.items():
                    setattr(c, k, v)
                c.updated_at = datetime.now()
                session.commit()
                self.load_clients(self.search.text())
                self.load_detail(self.current_client_id)
        finally:
            session.close()

    def delete_client(self):
        if not self.current_client_id:
            return
        reply = QMessageBox.question(
            self, "Delete Client",
            "Are you sure you want to delete this client and all related data?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            session = self.db.session()
            try:
                c = session.query(Client).get(self.current_client_id)
                if c:
                    session.delete(c)
                    session.commit()
            finally:
                session.close()
            self.current_client_id = None
            self.load_clients(self.search.text())

    def add_communication(self):
        if not self.current_client_id:
            return
        dlg = CommDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            session = self.db.session()
            try:
                comm = Communication(client_id=self.current_client_id, **data)
                session.add(comm)
                session.commit()
            finally:
                session.close()
            self.load_detail(self.current_client_id)
