"""Orders module - Order entry, line items, history linked to clients and products."""

from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QLabel, QDialog, QFormLayout, QTextEdit,
    QComboBox, QDoubleSpinBox, QSpinBox, QHeaderView, QMessageBox,
    QAbstractItemView, QDateEdit, QSplitter, QCheckBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QShortcut, QKeySequence
from sqlalchemy.orm import selectinload

from app.database import DatabaseManager, Order, OrderItem, Client, Product, Company
from app.documents import DocPreviewDialog, invoice_html, manifest_html


class OrderItemWidget(QWidget):
    """Single line item row for the order dialog."""
    def __init__(self, products, parent=None):
        super().__init__(parent)
        self.products = products
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        self.product_combo = QComboBox()
        self.product_combo.setMinimumWidth(250)
        for p in products:
            self.product_combo.addItem(p.display_name, p.id)
        self.product_combo.currentIndexChanged.connect(self.on_product_changed)
        layout.addWidget(self.product_combo, 3)

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 9999)
        self.qty_spin.setValue(1)
        self.qty_spin.valueChanged.connect(self.update_total)
        layout.addWidget(self.qty_spin, 1)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 9999.99)
        self.price_spin.setPrefix("$")
        self.price_spin.setDecimals(2)
        self.price_spin.valueChanged.connect(self.update_total)
        layout.addWidget(self.price_spin, 1)

        self.total_label = QLabel("$0.00")
        self.total_label.setMinimumWidth(80)
        layout.addWidget(self.total_label, 1)

        self.remove_btn = QPushButton("X")
        self.remove_btn.setObjectName("dangerBtn")
        self.remove_btn.setMaximumWidth(30)
        layout.addWidget(self.remove_btn)

        # Set initial price
        if products:
            self.price_spin.setValue(products[0].price)

    def on_product_changed(self, idx):
        if idx >= 0 and idx < len(self.products):
            self.price_spin.setValue(self.products[idx].price)

    def update_total(self):
        total = self.qty_spin.value() * self.price_spin.value()
        self.total_label.setText(f"${total:,.2f}")

    def get_data(self):
        idx = self.product_combo.currentIndex()
        return {
            "product_id": self.product_combo.currentData(),
            "quantity": self.qty_spin.value(),
            "unit_price": self.price_spin.value(),
            "line_total": round(self.qty_spin.value() * self.price_spin.value(), 2),
        }


class OrderDialog(QDialog):
    def __init__(self, parent=None, order=None, db=None):
        super().__init__(parent)
        self.db = db
        self.order = order
        self.tax_rate = db.tax_rate()  # from Settings (invoice.tax_rate), not hardcoded
        self.item_widgets = []
        self.setWindowTitle("Edit Order" if order else "New Order")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        self.setup_ui()
        if order:
            self.populate(order)

    def setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        # Client selection
        self.client_combo = QComboBox()
        session = self.db.session()
        try:
            clients = session.query(Client).order_by(Client.last_name).all()
            for c in clients:
                self.client_combo.addItem(f"{c.full_name} ({c.company})" if c.company else c.full_name, c.id)
        finally:
            session.close()
        form.addRow("Client *", self.client_combo)

        self.order_date = QDateEdit()
        self.order_date.setDate(QDate.currentDate())
        self.order_date.setCalendarPopup(True)
        form.addRow("Date", self.order_date)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Pending", "Confirmed", "Shipped", "Delivered", "Completed", "Cancelled"])
        form.addRow("Status", self.status_combo)

        self.notes = QTextEdit()
        self.notes.setMaximumHeight(60)
        form.addRow("Notes", self.notes)

        layout.addLayout(form)

        # Line items header
        items_header = QHBoxLayout()
        items_label = QLabel("Line Items")
        items_label.setStyleSheet("font-weight: bold; color: #c9a84c; font-size: 14px;")
        items_header.addWidget(items_label)
        items_header.addStretch()
        add_item_btn = QPushButton("+ Add Item")
        add_item_btn.setObjectName("primaryBtn")
        add_item_btn.clicked.connect(self.add_item_row)
        items_header.addWidget(add_item_btn)
        layout.addLayout(items_header)

        # Column headers
        col_header = QHBoxLayout()
        for label, stretch in [("Product", 3), ("Qty", 1), ("Unit Price", 1), ("Total", 1), ("", 0)]:
            lbl = QLabel(label)
            lbl.setStyleSheet("font-weight: bold; color: #888;")
            if stretch:
                col_header.addWidget(lbl, stretch)
            else:
                col_header.addWidget(lbl)
                lbl.setMaximumWidth(30)
        layout.addLayout(col_header)

        # Items container
        self.items_layout = QVBoxLayout()
        layout.addLayout(self.items_layout)

        # Totals
        totals = QHBoxLayout()
        totals.addStretch()
        self.subtotal_label = QLabel("Subtotal: $0.00")
        self.tax_label = QLabel(f"Tax ({self.tax_rate * 100:g}%): $0.00")
        self.total_label = QLabel("Total: $0.00")
        self.total_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #c9a84c;")
        totals.addWidget(self.subtotal_label)
        totals.addWidget(QLabel("  |  "))
        totals.addWidget(self.tax_label)
        totals.addWidget(QLabel("  |  "))
        totals.addWidget(self.total_label)
        layout.addLayout(totals)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        save = QPushButton("Save Order")
        save.setObjectName("primaryBtn")
        save.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

        # Load products for item rows
        session = self.db.session()
        try:
            self.all_products = session.query(Product).order_by(Product.brand).all()
            # Detach from session
            for p in self.all_products:
                session.expunge(p)
        finally:
            session.close()

        if not self.order:
            self.add_item_row()

    def add_item_row(self):
        if not self.all_products:
            QMessageBox.warning(self, "No Products", "Add products to a company first.")
            return
        widget = OrderItemWidget(self.all_products)
        widget.remove_btn.clicked.connect(lambda: self.remove_item_row(widget))
        widget.qty_spin.valueChanged.connect(self.update_totals)
        widget.price_spin.valueChanged.connect(self.update_totals)
        self.item_widgets.append(widget)
        self.items_layout.addWidget(widget)
        self.update_totals()

    def remove_item_row(self, widget):
        if len(self.item_widgets) <= 1:
            return
        self.item_widgets.remove(widget)
        self.items_layout.removeWidget(widget)
        widget.deleteLater()
        self.update_totals()

    def update_totals(self):
        subtotal = sum(w.qty_spin.value() * w.price_spin.value() for w in self.item_widgets)
        tax = subtotal * self.tax_rate
        total = subtotal + tax
        self.subtotal_label.setText(f"Subtotal: ${subtotal:,.2f}")
        self.tax_label.setText(f"Tax ({self.tax_rate * 100:g}%): ${tax:,.2f}")
        self.total_label.setText(f"Total: ${total:,.2f}")

    def populate(self, order):
        # Set client
        for i in range(self.client_combo.count()):
            if self.client_combo.itemData(i) == order.client_id:
                self.client_combo.setCurrentIndex(i)
                break
        self.order_date.setDate(QDate(order.order_date.year, order.order_date.month, order.order_date.day))
        idx = self.status_combo.findText(order.status)
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)
        self.notes.setPlainText(order.notes or "")

        # Populate line items
        session = self.db.session()
        try:
            items = session.query(OrderItem).filter_by(order_id=order.id).all()
            for item in items:
                widget = OrderItemWidget(self.all_products)
                # Find product in combo
                for i in range(widget.product_combo.count()):
                    if widget.product_combo.itemData(i) == item.product_id:
                        widget.product_combo.setCurrentIndex(i)
                        break
                widget.qty_spin.setValue(item.quantity)
                widget.price_spin.setValue(item.unit_price)
                widget.remove_btn.clicked.connect(lambda w=widget: self.remove_item_row(w))
                widget.qty_spin.valueChanged.connect(self.update_totals)
                widget.price_spin.valueChanged.connect(self.update_totals)
                self.item_widgets.append(widget)
                self.items_layout.addWidget(widget)
        finally:
            session.close()
        self.update_totals()

    def get_data(self):
        qd = self.order_date.date()
        return {
            "client_id": self.client_combo.currentData(),
            "order_date": date(qd.year(), qd.month(), qd.day()),
            "status": self.status_combo.currentText(),
            "notes": self.notes.toPlainText().strip(),
            "items": [w.get_data() for w in self.item_widgets],
        }

    def accept(self):
        if self.client_combo.currentData() is None:
            QMessageBox.warning(self, "Validation", "Select a client.")
            return
        if not self.item_widgets:
            QMessageBox.warning(self, "Validation", "Add at least one line item.")
            return
        super().accept()


class OrdersTab(QWidget):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.setup_ui()
        self.load_orders()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        title = QLabel("Orders")
        title.setObjectName("sectionHeader")
        header.addWidget(title)
        header.addStretch()

        self.search = QLineEdit()
        self.search.setObjectName("searchField")
        self.search.setPlaceholderText("Search orders...")
        self.search.setMinimumWidth(200)
        self.search.textChanged.connect(self.filter_orders)
        header.addWidget(self.search)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Statuses", "Pending", "Confirmed", "Shipped", "Delivered", "Completed", "Cancelled"])
        self.status_filter.currentTextChanged.connect(lambda: self.load_orders())
        header.addWidget(self.status_filter)

        manifest_btn = QPushButton("📦 Manifest (batch)…")
        manifest_btn.setToolTip("Build per-supplier purchase manifests from all open orders")
        manifest_btn.clicked.connect(self.open_manifest)
        header.addWidget(manifest_btn)

        add_btn = QPushButton("+ New Order")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self.add_order)
        header.addWidget(add_btn)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Vertical)

        # Orders table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Order #", "Date", "Client", "Status", "Items", "Total", "Invoice", "Paid"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self.edit_order)
        self.table.itemSelectionChanged.connect(self.on_selection)
        splitter.addWidget(self.table)

        # Detail panel
        detail = QWidget()
        detail_layout = QVBoxLayout(detail)

        det_header = QHBoxLayout()
        self.detail_label = QLabel("Select an order to view details")
        self.detail_label.setStyleSheet("font-weight: bold; color: #c9a84c;")
        det_header.addWidget(self.detail_label)
        det_header.addStretch()

        self.invoice_btn = QPushButton("🧾 Invoice")
        self.invoice_btn.setObjectName("primaryBtn")
        self.invoice_btn.setToolTip("Generate / view the invoice for this order (print or save as PDF)")
        self.invoice_btn.clicked.connect(self.make_invoice)
        self.invoice_btn.setEnabled(False)
        det_header.addWidget(self.invoice_btn)

        self.paid_btn = QPushButton("✔ Mark Paid")
        self.paid_btn.setToolTip("Toggle whether this order's invoice has been paid")
        self.paid_btn.clicked.connect(self.toggle_paid)
        self.paid_btn.setEnabled(False)
        det_header.addWidget(self.paid_btn)

        self.order_manifest_btn = QPushButton("📦 Manifest (this order)")
        self.order_manifest_btn.setToolTip("Per-supplier purchase manifests for just this order's items")
        self.order_manifest_btn.clicked.connect(self.manifest_for_order)
        self.order_manifest_btn.setEnabled(False)
        det_header.addWidget(self.order_manifest_btn)

        self.edit_order_btn = QPushButton("Edit")
        self.edit_order_btn.clicked.connect(self.edit_order)
        self.edit_order_btn.setEnabled(False)
        det_header.addWidget(self.edit_order_btn)

        self.del_order_btn = QPushButton("Delete")
        self.del_order_btn.setObjectName("dangerBtn")
        self.del_order_btn.clicked.connect(self.delete_order)
        self.del_order_btn.setEnabled(False)
        det_header.addWidget(self.del_order_btn)
        detail_layout.addLayout(det_header)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels(["Product", "SKU", "Qty", "Unit Price", "Line Total"])
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.items_table.verticalHeader().setVisible(False)
        detail_layout.addWidget(self.items_table)

        splitter.addWidget(detail)
        splitter.setSizes([400, 200])
        layout.addWidget(splitter)

        QShortcut(QKeySequence("Ctrl+N"), self, self.add_order)
        QShortcut(QKeySequence("Ctrl+F"), self, lambda: self.search.setFocus())

    def load_orders(self, filter_text=""):
        self.table.setRowCount(0)
        session = self.db.session()
        try:
            q = session.query(Order).join(Client)
            sf = self.status_filter.currentText() if hasattr(self, 'status_filter') else "All Statuses"
            if sf != "All Statuses":
                q = q.filter(Order.status == sf)
            if filter_text:
                ft = f"%{filter_text}%"
                q = q.filter(
                    (Client.first_name.ilike(ft)) |
                    (Client.last_name.ilike(ft)) |
                    (Client.company.ilike(ft))
                )
            orders = (
                q.options(selectinload(Order.client), selectinload(Order.items))
                .order_by(Order.order_date.desc()).all()
            )
            self.table.setRowCount(len(orders))
            for row, o in enumerate(orders):
                id_item = QTableWidgetItem(f"ORD-{o.id:04d}")
                id_item.setData(Qt.UserRole, o.id)
                self.table.setItem(row, 0, id_item)
                self.table.setItem(row, 1, QTableWidgetItem(str(o.order_date)))
                self.table.setItem(row, 2, QTableWidgetItem(o.client.full_name))
                self.table.setItem(row, 3, QTableWidgetItem(o.status))
                self.table.setItem(row, 4, QTableWidgetItem(str(len(o.items))))
                self.table.setItem(row, 5, QTableWidgetItem(f"${o.total:,.2f}"))
                self.table.setItem(row, 6, QTableWidgetItem(o.invoice_number or "—"))
                paid_item = QTableWidgetItem("✓ Paid" if o.is_paid else "—")
                if o.is_paid:
                    paid_item.setForeground(Qt.green)
                self.table.setItem(row, 7, paid_item)
        finally:
            session.close()

    def filter_orders(self, text):
        self.load_orders(text)

    def on_selection(self):
        rows = self.table.selectionModel().selectedRows()
        has = len(rows) > 0
        self.edit_order_btn.setEnabled(has)
        self.del_order_btn.setEnabled(has)
        self.invoice_btn.setEnabled(has)
        self.paid_btn.setEnabled(has)
        self.order_manifest_btn.setEnabled(has)
        if has:
            order_id = self.table.item(rows[0].row(), 0).data(Qt.UserRole)
            self.load_detail(order_id)
        else:
            self.detail_label.setText("Select an order to view details")
            self.items_table.setRowCount(0)

    def selected_order_id(self):
        rows = self.table.selectionModel().selectedRows()
        return self.table.item(rows[0].row(), 0).data(Qt.UserRole) if rows else None

    def load_detail(self, order_id):
        session = self.db.session()
        try:
            # Eager-load client + items->product so nothing lazy-loads after close.
            order = (
                session.query(Order)
                .options(selectinload(Order.client),
                         selectinload(Order.items).selectinload(OrderItem.product))
                .get(order_id)
            )
            if not order:
                return
            inv = order.invoice_number or "not invoiced"
            pay = f"PAID {order.paid_date}" if order.is_paid else "unpaid"
            self.detail_label.setText(
                f"ORD-{order.id:04d} | {order.client.full_name} | {order.status} | "
                f"Total: ${order.total:,.2f} | {inv} | {pay}"
            )
            self.paid_btn.setText("Mark Unpaid" if order.is_paid else "✔ Mark Paid")
            self.items_table.setRowCount(len(order.items))
            for row, item in enumerate(order.items):
                self.items_table.setItem(row, 0, QTableWidgetItem(item.product.display_name if item.product else "(deleted product)"))
                self.items_table.setItem(row, 1, QTableWidgetItem(item.product.sku if item.product else ""))
                self.items_table.setItem(row, 2, QTableWidgetItem(str(item.quantity)))
                self.items_table.setItem(row, 3, QTableWidgetItem(f"${item.unit_price:,.2f}"))
                self.items_table.setItem(row, 4, QTableWidgetItem(f"${item.line_total:,.2f}"))
        finally:
            session.close()

    def add_order(self):
        dlg = OrderDialog(self, db=self.db)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            items_data = data.pop("items")
            session = self.db.session()
            try:
                order = Order(**data)
                session.add(order)
                session.flush()
                subtotal = 0.0
                for idata in items_data:
                    idata["order_id"] = order.id
                    subtotal += idata["line_total"]
                    session.add(OrderItem(**idata))
                order.subtotal = round(subtotal, 2)
                order.tax = round(subtotal * self.db.tax_rate(), 2)
                order.total = round(subtotal + order.tax, 2)
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
            self.load_orders(self.search.text())

    def edit_order(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        order_id = self.table.item(rows[0].row(), 0).data(Qt.UserRole)
        session = self.db.session()
        try:
            order = session.query(Order).get(order_id)
            if not order:
                return
            dlg = OrderDialog(self, order=order, db=self.db)
            if dlg.exec() == QDialog.Accepted:
                data = dlg.get_data()
                items_data = data.pop("items")
                for k, v in data.items():
                    setattr(order, k, v)
                # Replace items
                for old_item in order.items[:]:
                    session.delete(old_item)
                session.flush()
                subtotal = 0.0
                for idata in items_data:
                    idata["order_id"] = order.id
                    subtotal += idata["line_total"]
                    session.add(OrderItem(**idata))
                order.subtotal = round(subtotal, 2)
                order.tax = round(subtotal * self.db.tax_rate(), 2)
                order.total = round(subtotal + order.tax, 2)
                session.commit()
                self.load_orders(self.search.text())
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_order(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        order_id = self.table.item(rows[0].row(), 0).data(Qt.UserRole)
        reply = QMessageBox.question(self, "Delete Order", "Delete this order?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            session = self.db.session()
            try:
                order = session.query(Order).get(order_id)
                if order:
                    session.delete(order)
                    session.commit()
            finally:
                session.close()
            self.load_orders(self.search.text())

    # ---------- invoicing ----------

    def _company_settings(self):
        """Broker company info from Settings; nudge to fill it in if empty."""
        company = self.db.get_settings("company.")
        if not company.get("name"):
            QMessageBox.information(
                self, "Set up your company first",
                "Put your company information in the Settings section (Ctrl+7) — "
                "it goes at the top of every invoice and manifest.",
            )
            try:
                self.window().sidebar.setCurrentRow(6)  # jump to Settings
            except AttributeError:
                pass
            return None
        return company

    def make_invoice(self):
        order_id = self.selected_order_id()
        if order_id is None:
            return
        company = self._company_settings()
        if company is None:
            return
        session = self.db.session()
        try:
            order = (
                session.query(Order)
                .options(selectinload(Order.client),
                         selectinload(Order.items).selectinload(OrderItem.product))
                .get(order_id)
            )
            if not order:
                return
            # First invoice for this order gets the next number; reprints reuse it.
            if not order.invoice_number:
                order.invoice_number = self.db.next_invoice_number()
                order.invoiced_date = date.today()
                session.commit()
            c = order.client
            tax_pct = (order.tax / order.subtotal * 100) if order.subtotal else self.db.tax_rate() * 100
            inv = {
                "number": order.invoice_number,
                "order_no": f"ORD-{order.id:04d}",
                "order_date": str(order.order_date),
                "invoiced_date": str(order.invoiced_date or date.today()),
                "is_paid": order.is_paid,
                "paid_date": str(order.paid_date) if order.paid_date else "",
                "client": {
                    "name": c.full_name,
                    "company": c.company,
                    "address": c.address,
                    "city_state": ", ".join(x for x in [c.city, c.state] if x) + (f" {c.zip_code}" if c.zip_code else ""),
                    "email": c.email,
                    "phone": c.phone,
                    "terms": c.payment_terms,
                },
                "items": [
                    {
                        "name": i.product.display_name if i.product else "(deleted product)",
                        "sku": i.product.sku if i.product else "",
                        "qty": i.quantity,
                        "unit": i.unit_price,
                        "total": i.line_total,
                    }
                    for i in order.items
                ],
                "subtotal": order.subtotal,
                "tax": order.tax,
                "tax_pct": round(tax_pct, 2),
                "total": order.total,
                "company": company,
                "footer": self.db.get_setting("invoice.footer"),
            }
            title = order.invoice_number
        finally:
            session.close()

        DocPreviewDialog(self, [{"title": title, "html": invoice_html(inv)}],
                         window_title=f"Invoice {title}").exec()
        self.load_orders(self.search.text())

    def toggle_paid(self):
        order_id = self.selected_order_id()
        if order_id is None:
            return
        session = self.db.session()
        try:
            order = session.query(Order).get(order_id)
            if not order:
                return
            if order.is_paid:
                msg = f"Mark ORD-{order.id:04d} as UNPAID again?"
            else:
                msg = f"Mark ORD-{order.id:04d} (${order.total:,.2f}) as PAID today?"
            if QMessageBox.question(self, "Payment", msg, QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                return
            order.is_paid = not order.is_paid
            order.paid_date = date.today() if order.is_paid else None
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
        self.load_orders(self.search.text())
        self.load_detail(order_id)

    # ---------- supplier manifests ----------

    def open_manifest(self):
        """Batch mode: manifests from all orders matching chosen statuses."""
        company = self._company_settings()
        if company is None:
            return
        dlg = ManifestDialog(self, db=self.db)
        if dlg.exec() != QDialog.Accepted:
            return
        statuses, supplier_id, date_from = dlg.get_criteria()
        criteria = (
            f"Covers orders with status {', '.join(statuses)}"
            + (f" from {date_from} onward" if date_from else "")
            + f", as of {date.today()}."
        )
        docs = self._build_manifest_docs(company, criteria, statuses=statuses,
                                         supplier_id=supplier_id, date_from=date_from)
        if not docs:
            QMessageBox.information(self, "Nothing to order",
                                    "No order items match those statuses.")
            return
        DocPreviewDialog(self, docs, window_title="Purchase Manifests").exec()

    def manifest_for_order(self):
        """Single-order mode: manifests for JUST the selected order's items."""
        order_id = self.selected_order_id()
        if order_id is None:
            return
        company = self._company_settings()
        if company is None:
            return
        criteria = f"Covers ORD-{order_id:04d} only, as of {date.today()}."
        docs = self._build_manifest_docs(company, criteria, order_ids=[order_id])
        if not docs:
            QMessageBox.information(self, "Nothing to order",
                                    "This order has no line items.")
            return
        DocPreviewDialog(self, docs,
                         window_title=f"Purchase Manifests — ORD-{order_id:04d}").exec()

    def _build_manifest_docs(self, company, criteria, order_ids=None, statuses=None,
                             supplier_id=None, date_from=None):
        """Shared builder: per-supplier manifest docs from matching order items."""
        session = self.db.session()
        try:
            q = (
                session.query(OrderItem)
                .join(Order).join(Product)
                .options(selectinload(OrderItem.product).selectinload(Product.company),
                         selectinload(OrderItem.order))
            )
            if order_ids is not None:
                q = q.filter(OrderItem.order_id.in_(order_ids))
            if statuses is not None:
                q = q.filter(Order.status.in_(statuses))
            if supplier_id is not None:
                q = q.filter(Product.company_id == supplier_id)
            if date_from is not None:
                q = q.filter(Order.order_date >= date_from)
            items = q.all()

            # Group by supplier company, then aggregate by product.
            by_company = {}
            for it in items:
                if not it.product or not it.product.company:
                    continue
                comp = it.product.company
                agg = by_company.setdefault(comp.id, {"company": comp, "products": {}})
                p = agg["products"].setdefault(it.product_id, {
                    "product": it.product, "qty": 0, "unit": it.unit_price, "refs": [],
                })
                p["qty"] += it.quantity
                p["refs"].append(f"ORD-{it.order_id:04d}×{it.quantity}")

            docs = []
            for agg in sorted(by_company.values(), key=lambda a: a["company"].name):
                comp = agg["company"]
                rows, total_qty, total_cost = [], 0, 0.0
                csv_rows = [["Product", "SKU", "Size", "Qty", "Unit $ (ref)", "Ext $ (ref)", "Order refs"]]
                for p in sorted(agg["products"].values(), key=lambda x: x["product"].display_name):
                    ext = round(p["qty"] * p["unit"], 2)
                    total_qty += p["qty"]
                    total_cost += ext
                    row = {
                        "product": p["product"].display_name,
                        "sku": p["product"].sku,
                        "size": p["product"].size,
                        "qty": p["qty"],
                        "unit": p["unit"],
                        "ext": ext,
                        "refs": ", ".join(p["refs"]),
                    }
                    rows.append(row)
                    csv_rows.append([row["product"], row["sku"], row["size"], row["qty"],
                                     f"{row['unit']:.2f}", f"{ext:.2f}", row["refs"]])
                man = {
                    "supplier": {
                        "name": comp.name, "contact": comp.contact_name,
                        "email": comp.email, "phone": comp.phone, "address": comp.address,
                    },
                    "rows": rows,
                    "total_qty": total_qty,
                    "total_cost": round(total_cost, 2),
                    "company": company,
                    "criteria": criteria,
                }
                docs.append({
                    "title": f"Manifest — {comp.name}",
                    "html": manifest_html(man),
                    "csv": csv_rows,
                })
            return docs
        finally:
            session.close()


class ManifestDialog(QDialog):
    """Pick which orders feed the manifests: statuses, supplier, from-date."""

    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Build Purchase Manifests")
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Include orders with status:"))
        self.status_checks = {}
        for status, default_on in [("Pending", True), ("Confirmed", True),
                                   ("Shipped", False), ("Delivered", False),
                                   ("Completed", False)]:
            cb = QCheckBox(status)
            cb.setChecked(default_on)
            self.status_checks[status] = cb
            layout.addWidget(cb)

        form = QFormLayout()
        self.company_combo = QComboBox()
        self.company_combo.addItem("All suppliers", None)
        session = self.db.session()
        try:
            for comp in session.query(Company).order_by(Company.name).all():
                self.company_combo.addItem(comp.name, comp.id)
        finally:
            session.close()
        form.addRow("Supplier", self.company_combo)

        from_row = QHBoxLayout()
        self.from_check = QCheckBox("Only orders from")
        self.from_date = QDateEdit()
        self.from_date.setDate(QDate.currentDate().addMonths(-1))
        self.from_date.setCalendarPopup(True)
        self.from_date.setEnabled(False)
        self.from_check.toggled.connect(self.from_date.setEnabled)
        from_row.addWidget(self.from_check)
        from_row.addWidget(self.from_date)
        from_row.addStretch()
        layout.addLayout(form)
        layout.addLayout(from_row)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        go = QPushButton("Build Manifests")
        go.setObjectName("primaryBtn")
        go.clicked.connect(self.accept)
        btns.addWidget(go)
        layout.addLayout(btns)

    def get_criteria(self):
        statuses = [s for s, cb in self.status_checks.items() if cb.isChecked()] or ["Pending"]
        supplier_id = self.company_combo.currentData()
        date_from = None
        if self.from_check.isChecked():
            qd = self.from_date.date()
            date_from = date(qd.year(), qd.month(), qd.day())
        return statuses, supplier_id, date_from
