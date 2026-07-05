"""Companies module - CRUD for supplier companies and their product catalogs."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QLabel, QDialog, QFormLayout, QTextEdit,
    QComboBox, QDoubleSpinBox, QHeaderView, QMessageBox, QSplitter,
    QAbstractItemView, QTabWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence

from app.database import DatabaseManager, Company, Product, Communication
from app.clients_tab import CommDialog


class CompanyDialog(QDialog):
    def __init__(self, parent=None, company=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Company" if company else "New Company")
        self.setMinimumWidth(450)
        self.setup_ui()
        if company:
            self.populate(company)

    def setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)

        self.name = QLineEdit()
        self.name.setPlaceholderText("Company name")
        layout.addRow("Name *", self.name)

        self.contact_name = QLineEdit()
        self.contact_name.setPlaceholderText("Primary contact")
        layout.addRow("Contact", self.contact_name)

        self.email = QLineEdit()
        layout.addRow("Email", self.email)

        self.phone = QLineEdit()
        layout.addRow("Phone", self.phone)

        self.address = QLineEdit()
        layout.addRow("Address", self.address)

        self.website = QLineEdit()
        layout.addRow("Website", self.website)

        # The broker's cut of sales of this company's products — drives the
        # NET numbers on earnings reports and the dashboard.
        self.commission = QDoubleSpinBox()
        self.commission.setRange(0.0, 100.0)
        self.commission.setDecimals(2)
        self.commission.setSuffix(" %")
        self.commission.setToolTip("Your percentage of every sale of this company's products")
        layout.addRow("Your commission", self.commission)

        self.notes = QTextEdit()
        self.notes.setMaximumHeight(80)
        layout.addRow("Notes", self.notes)

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

    def populate(self, c):
        self.name.setText(c.name)
        self.contact_name.setText(c.contact_name or "")
        self.email.setText(c.email or "")
        self.phone.setText(c.phone or "")
        self.address.setText(c.address or "")
        self.website.setText(c.website or "")
        self.commission.setValue(c.commission_pct or 0.0)
        self.notes.setPlainText(c.notes or "")

    def get_data(self):
        return {
            "name": self.name.text().strip(),
            "contact_name": self.contact_name.text().strip(),
            "email": self.email.text().strip(),
            "phone": self.phone.text().strip(),
            "address": self.address.text().strip(),
            "website": self.website.text().strip(),
            "commission_pct": self.commission.value(),
            "notes": self.notes.toPlainText().strip(),
        }

    def accept(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Validation", "Company name is required.")
            return
        super().accept()


class ProductDialog(QDialog):
    def __init__(self, parent=None, product=None, company_id=None):
        super().__init__(parent)
        self.company_id = company_id
        self.setWindowTitle("Edit Product" if product else "New Product")
        self.setMinimumWidth(450)
        self.setup_ui()
        if product:
            self.populate(product)

    def setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)

        self.brand = QLineEdit()
        self.brand.setPlaceholderText("Brand name")
        layout.addRow("Brand *", self.brand)

        self.line = QLineEdit()
        self.line.setPlaceholderText("Product line")
        layout.addRow("Line", self.line)

        self.sku = QLineEdit()
        self.sku.setPlaceholderText("SKU code")
        layout.addRow("SKU", self.sku)

        self.size = QLineEdit()
        self.size.setPlaceholderText("e.g., 6x52 Toro")
        layout.addRow("Size", self.size)

        self.wrapper = QLineEdit()
        self.wrapper.setPlaceholderText("e.g., Maduro, Connecticut")
        layout.addRow("Wrapper", self.wrapper)

        self.strength = QComboBox()
        self.strength.addItems(["Mild", "Mild-Medium", "Medium", "Medium-Full", "Full"])
        self.strength.setCurrentIndex(2)
        layout.addRow("Strength", self.strength)

        self.price = QDoubleSpinBox()
        self.price.setRange(0, 9999.99)
        self.price.setPrefix("$")
        self.price.setDecimals(2)
        layout.addRow("Price", self.price)

        self.availability = QComboBox()
        self.availability.addItems(["In Stock", "Limited", "Allocated", "Out of Stock", "Discontinued"])
        self.availability.setEditable(True)
        layout.addRow("Availability", self.availability)

        self.notes = QTextEdit()
        self.notes.setMaximumHeight(60)
        layout.addRow("Notes", self.notes)

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

    def populate(self, p):
        self.brand.setText(p.brand)
        self.line.setText(p.line or "")
        self.sku.setText(p.sku or "")
        self.size.setText(p.size or "")
        self.wrapper.setText(p.wrapper or "")
        idx = self.strength.findText(p.strength or "Medium")
        if idx >= 0:
            self.strength.setCurrentIndex(idx)
        self.price.setValue(p.price or 0)
        aidx = self.availability.findText(p.availability or "In Stock")
        if aidx >= 0:
            self.availability.setCurrentIndex(aidx)
        else:
            self.availability.setEditText(p.availability or "")
        self.notes.setPlainText(p.notes or "")

    def get_data(self):
        return {
            "brand": self.brand.text().strip(),
            "line": self.line.text().strip(),
            "sku": self.sku.text().strip(),
            "size": self.size.text().strip(),
            "wrapper": self.wrapper.text().strip(),
            "strength": self.strength.currentText(),
            "price": self.price.value(),
            "availability": self.availability.currentText(),
            "notes": self.notes.toPlainText().strip(),
        }

    def accept(self):
        if not self.brand.text().strip():
            QMessageBox.warning(self, "Validation", "Brand is required.")
            return
        super().accept()


class CompaniesTab(QWidget):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_company_id = None
        self.setup_ui()
        self.load_companies()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        title = QLabel("Companies Represented")
        title.setObjectName("sectionHeader")
        header.addWidget(title)
        header.addStretch()

        self.search = QLineEdit()
        self.search.setObjectName("searchField")
        self.search.setPlaceholderText("Search companies...")
        self.search.setMinimumWidth(250)
        self.search.textChanged.connect(self.filter_companies)
        header.addWidget(self.search)

        add_btn = QPushButton("+ New Company")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self.add_company)
        header.addWidget(add_btn)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)

        # Company list
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Name", "Contact", "Phone", "Products", "Comm %"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self.on_selection)
        self.table.doubleClicked.connect(self.edit_company)
        splitter.addWidget(self.table)

        # Right panel: company detail + products
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)

        self.detail_name = QLabel("Select a company ← to manage its products")
        self.detail_name.setObjectName("sectionHeader")
        right_layout.addWidget(self.detail_name)

        self.detail_info = QLabel("")
        self.detail_info.setWordWrap(True)
        right_layout.addWidget(self.detail_info)

        btn_row = QHBoxLayout()
        self.edit_btn = QPushButton("Edit Company")
        self.edit_btn.clicked.connect(self.edit_company)
        self.edit_btn.setEnabled(False)
        btn_row.addWidget(self.edit_btn)

        self.del_btn = QPushButton("Delete")
        self.del_btn.setObjectName("dangerBtn")
        self.del_btn.clicked.connect(self.delete_company)
        self.del_btn.setEnabled(False)
        btn_row.addWidget(self.del_btn)
        btn_row.addStretch()

        self.add_prod_btn = QPushButton("+ Add Product")
        self.add_prod_btn.setObjectName("primaryBtn")
        self.add_prod_btn.clicked.connect(self.add_product)
        self.add_prod_btn.setEnabled(False)
        btn_row.addWidget(self.add_prod_btn)
        right_layout.addLayout(btn_row)

        # Tabs: product catalog + the company's people
        self.detail_tabs = QTabWidget()

        prod_page = QWidget()
        prod_layout = QVBoxLayout(prod_page)
        prod_layout.setContentsMargins(0, 4, 0, 0)

        prod_header = QHBoxLayout()
        prod_hint = QLabel("double-click a product to edit it")
        prod_hint.setStyleSheet("color: #888;")
        prod_header.addWidget(prod_hint)
        prod_header.addStretch()
        prod_layout.addLayout(prod_header)

        self.prod_table = QTableWidget()
        self.prod_table.setColumnCount(7)
        self.prod_table.setHorizontalHeaderLabels(["Brand", "Line", "SKU", "Size", "Wrapper", "Price", "Avail."])
        self.prod_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.prod_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.prod_table.setAlternatingRowColors(True)
        self.prod_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.prod_table.verticalHeader().setVisible(False)
        self.prod_table.doubleClicked.connect(self.edit_product)
        prod_layout.addWidget(self.prod_table)

        prod_btn_row = QHBoxLayout()
        self.edit_prod_btn = QPushButton("Edit Product")
        self.edit_prod_btn.clicked.connect(self.edit_product)
        self.edit_prod_btn.setEnabled(False)
        prod_btn_row.addWidget(self.edit_prod_btn)

        self.del_prod_btn = QPushButton("Delete Product")
        self.del_prod_btn.setObjectName("dangerBtn")
        self.del_prod_btn.clicked.connect(self.delete_product)
        self.del_prod_btn.setEnabled(False)
        prod_btn_row.addWidget(self.del_prod_btn)
        prod_btn_row.addStretch()
        prod_layout.addLayout(prod_btn_row)

        self.detail_tabs.addTab(prod_page, "Product Catalog")

        from app.contacts import ContactsPanel
        self.contacts_panel = ContactsPanel(self.db, "company")
        self.detail_tabs.addTab(self.contacts_panel, "Contacts")

        # Communication log for the company (calls, emails, meetings, notes).
        comm_page = QWidget()
        comm_layout = QVBoxLayout(comm_page)
        comm_layout.setContentsMargins(0, 4, 0, 0)
        comm_btn_row = QHBoxLayout()
        self.log_comm_btn = QPushButton("+ Log Comm")
        self.log_comm_btn.setObjectName("primaryBtn")
        self.log_comm_btn.clicked.connect(self.add_communication)
        self.log_comm_btn.setEnabled(False)
        comm_btn_row.addWidget(self.log_comm_btn)
        comm_btn_row.addStretch()
        comm_layout.addLayout(comm_btn_row)
        self.comm_table = QTableWidget()
        self.comm_table.setColumnCount(4)
        self.comm_table.setHorizontalHeaderLabels(["Date", "Type", "Subject", "Details"])
        self.comm_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.comm_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.comm_table.setAlternatingRowColors(True)
        self.comm_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.comm_table.verticalHeader().setVisible(False)
        comm_layout.addWidget(self.comm_table)
        self.detail_tabs.addTab(comm_page, "Communications")

        right_layout.addWidget(self.detail_tabs)

        self.prod_table.itemSelectionChanged.connect(self.on_product_selection)

        splitter.addWidget(right)
        splitter.setSizes([400, 500])
        layout.addWidget(splitter)

        QShortcut(QKeySequence("Ctrl+N"), self, self.add_company)
        QShortcut(QKeySequence("Ctrl+F"), self, lambda: self.search.setFocus())

    def load_companies(self, filter_text=""):
        self.table.setRowCount(0)
        session = self.db.session()
        try:
            q = session.query(Company)
            if filter_text:
                ft = f"%{filter_text}%"
                q = q.filter(
                    (Company.name.ilike(ft)) |
                    (Company.contact_name.ilike(ft))
                )
            companies = q.order_by(Company.name).all()
            self.table.setRowCount(len(companies))
            for row, c in enumerate(companies):
                item = QTableWidgetItem(c.name)
                item.setData(Qt.UserRole, c.id)
                self.table.setItem(row, 0, item)
                self.table.setItem(row, 1, QTableWidgetItem(c.contact_name or ""))
                self.table.setItem(row, 2, QTableWidgetItem(c.phone or ""))
                self.table.setItem(row, 3, QTableWidgetItem(str(len(c.products))))
                self.table.setItem(row, 4, QTableWidgetItem(f"{c.commission_pct:g}%" if c.commission_pct else "—"))
        finally:
            session.close()

    def filter_companies(self, text):
        self.load_companies(text)

    def on_selection(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.current_company_id = None
            self.detail_name.setText("Select a company")
            self.detail_info.setText("")
            self.edit_btn.setEnabled(False)
            self.del_btn.setEnabled(False)
            self.add_prod_btn.setEnabled(False)
            self.log_comm_btn.setEnabled(False)
            self.prod_table.setRowCount(0)
            self.comm_table.setRowCount(0)
            self.contacts_panel.set_owner(None)
            return
        item = self.table.item(rows[0].row(), 0)
        self.current_company_id = item.data(Qt.UserRole)
        self.edit_btn.setEnabled(True)
        self.del_btn.setEnabled(True)
        self.add_prod_btn.setEnabled(True)
        self.log_comm_btn.setEnabled(True)
        self.contacts_panel.set_owner(self.current_company_id)
        self.load_detail()

    def load_detail(self):
        if not self.current_company_id:
            return
        session = self.db.session()
        try:
            c = session.query(Company).get(self.current_company_id)
            if not c:
                return
            self.detail_name.setText(c.name)
            info = []
            info.append(f"<b>Your commission:</b> {c.commission_pct:g}%" if c.commission_pct
                        else "<b>Your commission:</b> not set — net earnings from this company report as $0")
            if c.contact_name:
                info.append(f"<b>Contact:</b> {c.contact_name}")
            if c.email:
                info.append(f"<b>Email:</b> {c.email}")
            if c.phone:
                info.append(f"<b>Phone:</b> {c.phone}")
            if c.address:
                info.append(f"<b>Address:</b> {c.address}")
            if c.website:
                info.append(f"<b>Website:</b> {c.website}")
            if c.notes:
                info.append(f"<b>Notes:</b> {c.notes}")
            self.detail_info.setText("<br>".join(info))

            # Products
            self.prod_table.setRowCount(len(c.products))
            for row, p in enumerate(c.products):
                item = QTableWidgetItem(p.brand)
                item.setData(Qt.UserRole, p.id)
                self.prod_table.setItem(row, 0, item)
                self.prod_table.setItem(row, 1, QTableWidgetItem(p.line or ""))
                self.prod_table.setItem(row, 2, QTableWidgetItem(p.sku or ""))
                self.prod_table.setItem(row, 3, QTableWidgetItem(p.size or ""))
                self.prod_table.setItem(row, 4, QTableWidgetItem(p.wrapper or ""))
                self.prod_table.setItem(row, 5, QTableWidgetItem(f"${p.price:.2f}"))
                self.prod_table.setItem(row, 6, QTableWidgetItem(p.availability or ""))

            # Communications (newest first)
            comms = sorted(c.communications, key=lambda x: x.timestamp, reverse=True)
            self.comm_table.setRowCount(len(comms))
            for row, cm in enumerate(comms):
                self.comm_table.setItem(row, 0, QTableWidgetItem(cm.timestamp.strftime("%Y-%m-%d")))
                self.comm_table.setItem(row, 1, QTableWidgetItem(cm.comm_type or ""))
                self.comm_table.setItem(row, 2, QTableWidgetItem(cm.subject or ""))
                self.comm_table.setItem(row, 3, QTableWidgetItem(cm.body or ""))
        finally:
            session.close()

    def add_communication(self):
        if not self.current_company_id:
            return
        dlg = CommDialog(self)
        if dlg.exec() == QDialog.Accepted:
            session = self.db.session()
            try:
                session.add(Communication(company_id=self.current_company_id, **dlg.get_data()))
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
            self.load_detail()

    def on_product_selection(self):
        has = len(self.prod_table.selectionModel().selectedRows()) > 0
        self.edit_prod_btn.setEnabled(has)
        self.del_prod_btn.setEnabled(has)

    def add_company(self):
        dlg = CompanyDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            session = self.db.session()
            try:
                session.add(Company(**data))
                session.commit()
            finally:
                session.close()
            self.load_companies(self.search.text())

    def edit_company(self):
        if not self.current_company_id:
            return
        session = self.db.session()
        try:
            c = session.query(Company).get(self.current_company_id)
            if not c:
                return
            dlg = CompanyDialog(self, company=c)
            if dlg.exec() == QDialog.Accepted:
                data = dlg.get_data()
                for k, v in data.items():
                    setattr(c, k, v)
                session.commit()
                self.load_companies(self.search.text())
                self.load_detail()
        finally:
            session.close()

    def delete_company(self):
        if not self.current_company_id:
            return
        reply = QMessageBox.question(
            self, "Delete Company",
            "Delete this company and all its products?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            session = self.db.session()
            try:
                c = session.query(Company).get(self.current_company_id)
                if c:
                    session.delete(c)
                    session.commit()
            finally:
                session.close()
            self.current_company_id = None
            self.load_companies(self.search.text())

    def add_product(self):
        if not self.current_company_id:
            return
        dlg = ProductDialog(self, company_id=self.current_company_id)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            session = self.db.session()
            try:
                session.add(Product(company_id=self.current_company_id, **data))
                session.commit()
            finally:
                session.close()
            self.load_detail()
            self.load_companies(self.search.text())

    def edit_product(self):
        rows = self.prod_table.selectionModel().selectedRows()
        if not rows:
            return
        prod_id = self.prod_table.item(rows[0].row(), 0).data(Qt.UserRole)
        session = self.db.session()
        try:
            p = session.query(Product).get(prod_id)
            if not p:
                return
            dlg = ProductDialog(self, product=p)
            if dlg.exec() == QDialog.Accepted:
                data = dlg.get_data()
                for k, v in data.items():
                    setattr(p, k, v)
                session.commit()
                self.load_detail()
        finally:
            session.close()

    def delete_product(self):
        rows = self.prod_table.selectionModel().selectedRows()
        if not rows:
            return
        prod_id = self.prod_table.item(rows[0].row(), 0).data(Qt.UserRole)
        reply = QMessageBox.question(self, "Delete Product", "Delete this product?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            session = self.db.session()
            try:
                p = session.query(Product).get(prod_id)
                if p:
                    session.delete(p)
                    session.commit()
            finally:
                session.close()
            self.load_detail()
            self.load_companies(self.search.text())
