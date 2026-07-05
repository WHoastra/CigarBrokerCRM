"""Shared multi-contact management: clients and companies can each carry any
number of people (buyer, assistant, rep). One ContactsPanel is embedded in the
client detail tabs and the company detail tabs, parameterized by owner kind."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QDialog, QFormLayout, QLineEdit, QTextEdit, QCheckBox,
    QHeaderView, QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Qt

from app.database import DatabaseManager, Contact


class ContactDialog(QDialog):
    def __init__(self, parent=None, contact=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Contact" if contact else "New Contact")
        self.setMinimumWidth(420)
        form = QFormLayout(self)

        self.name = QLineEdit()
        form.addRow("Name *", self.name)
        self.role = QLineEdit()
        self.role.setPlaceholderText("Buyer, Owner, Rep, Assistant…")
        form.addRow("Role / Title", self.role)
        self.email = QLineEdit()
        form.addRow("Email", self.email)
        self.phone = QLineEdit()
        form.addRow("Phone", self.phone)
        self.is_primary = QCheckBox("Primary contact")
        form.addRow("", self.is_primary)
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

        if contact:
            self.name.setText(contact.name)
            self.role.setText(contact.role or "")
            self.email.setText(contact.email or "")
            self.phone.setText(contact.phone or "")
            self.is_primary.setChecked(bool(contact.is_primary))
            self.notes.setPlainText(contact.notes or "")

    def get_data(self):
        return {
            "name": self.name.text().strip(),
            "role": self.role.text().strip(),
            "email": self.email.text().strip(),
            "phone": self.phone.text().strip(),
            "is_primary": self.is_primary.isChecked(),
            "notes": self.notes.toPlainText().strip(),
        }

    def accept(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Validation", "Contact name is required.")
            return
        super().accept()


class ContactsPanel(QWidget):
    """Contact list + CRUD for one owner. owner_kind: 'client' | 'company'.
    Call set_owner(id) when the selected client/company changes."""

    def __init__(self, db: DatabaseManager, owner_kind: str, parent=None):
        super().__init__(parent)
        self.db = db
        self.owner_kind = owner_kind
        self.owner_id = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("+ Add Contact")
        self.add_btn.setObjectName("primaryBtn")
        self.add_btn.clicked.connect(self.add_contact)
        self.add_btn.setEnabled(False)
        btn_row.addWidget(self.add_btn)
        self.edit_btn = QPushButton("Edit Contact")
        self.edit_btn.clicked.connect(self.edit_contact)
        self.edit_btn.setEnabled(False)
        btn_row.addWidget(self.edit_btn)
        self.del_btn = QPushButton("Delete Contact")
        self.del_btn.setObjectName("dangerBtn")
        self.del_btn.clicked.connect(self.delete_contact)
        self.del_btn.setEnabled(False)
        btn_row.addWidget(self.del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Name", "Role", "Email", "Phone", "Primary"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._sync_buttons)
        self.table.doubleClicked.connect(self.edit_contact)
        layout.addWidget(self.table)

    # ---- data ----

    def _owner_filter(self):
        return {"client_id": self.owner_id} if self.owner_kind == "client" else {"company_id": self.owner_id}

    def set_owner(self, owner_id):
        self.owner_id = owner_id
        self.add_btn.setEnabled(owner_id is not None)
        self.reload()

    def reload(self):
        self.table.setRowCount(0)
        if self.owner_id is None:
            self._sync_buttons()
            return
        session = self.db.session()
        try:
            contacts = (
                session.query(Contact).filter_by(**self._owner_filter())
                .order_by(Contact.is_primary.desc(), Contact.name).all()
            )
            self.table.setRowCount(len(contacts))
            for row, c in enumerate(contacts):
                name_item = QTableWidgetItem(c.name)
                name_item.setData(Qt.UserRole, c.id)
                self.table.setItem(row, 0, name_item)
                self.table.setItem(row, 1, QTableWidgetItem(c.role or ""))
                self.table.setItem(row, 2, QTableWidgetItem(c.email or ""))
                self.table.setItem(row, 3, QTableWidgetItem(c.phone or ""))
                self.table.setItem(row, 4, QTableWidgetItem("★" if c.is_primary else ""))
        finally:
            session.close()
        self._sync_buttons()

    def _sync_buttons(self):
        has = bool(self.table.selectionModel() and self.table.selectionModel().selectedRows())
        self.edit_btn.setEnabled(has)
        self.del_btn.setEnabled(has)

    def _selected_id(self):
        rows = self.table.selectionModel().selectedRows()
        return self.table.item(rows[0].row(), 0).data(Qt.UserRole) if rows else None

    def _clear_other_primaries(self, session, keep_id):
        """Only one primary per owner — flipping one on turns the others off."""
        for other in session.query(Contact).filter_by(**self._owner_filter(), is_primary=True).all():
            if other.id != keep_id:
                other.is_primary = False

    # ---- CRUD ----

    def add_contact(self):
        if self.owner_id is None:
            return
        dlg = ContactDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            session = self.db.session()
            try:
                contact = Contact(**data, **self._owner_filter())
                session.add(contact)
                session.flush()
                if contact.is_primary:
                    self._clear_other_primaries(session, contact.id)
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
            self.reload()

    def edit_contact(self):
        cid = self._selected_id()
        if cid is None:
            return
        session = self.db.session()
        try:
            contact = session.query(Contact).get(cid)
            if not contact:
                return
            dlg = ContactDialog(self, contact=contact)
            if dlg.exec() == QDialog.Accepted:
                for k, v in dlg.get_data().items():
                    setattr(contact, k, v)
                if contact.is_primary:
                    self._clear_other_primaries(session, contact.id)
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
        self.reload()

    def delete_contact(self):
        cid = self._selected_id()
        if cid is None:
            return
        if QMessageBox.question(self, "Delete Contact", "Delete this contact?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        session = self.db.session()
        try:
            contact = session.query(Contact).get(cid)
            if contact:
                session.delete(contact)
                session.commit()
        finally:
            session.close()
        self.reload()
