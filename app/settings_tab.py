"""Settings module - broker company info + invoicing configuration.

Values live in the settings table (app.database.Setting), so File > Backup
Database carries them along with everything else. The company block is the
letterhead on every invoice and purchase manifest.
"""

import os
import shutil

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QTextEdit, QDoubleSpinBox, QPushButton, QLabel, QFileDialog
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from app.database import DatabaseManager, DB_DIR


class SettingsTab(QWidget):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.setup_ui()
        self.load()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        title = QLabel("Settings")
        title.setObjectName("sectionHeader")
        header.addWidget(title)
        header.addStretch()
        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self.save)
        header.addWidget(save_btn)
        layout.addLayout(header)

        # --- Your company (invoice/manifest letterhead) ---
        company_group = QGroupBox("Your Company — appears on every invoice and manifest")
        cform = QFormLayout(company_group)
        self.name = QLineEdit()
        self.name.setPlaceholderText("e.g. Straley Premium Cigar Brokerage")
        cform.addRow("Company name *", self.name)
        self.address = QLineEdit()
        self.address.setPlaceholderText("Street address")
        cform.addRow("Address", self.address)
        self.city_state_zip = QLineEdit()
        self.city_state_zip.setPlaceholderText("City, ST 70360")
        cform.addRow("City / State / Zip", self.city_state_zip)
        self.phone = QLineEdit()
        cform.addRow("Phone", self.phone)
        self.email = QLineEdit()
        cform.addRow("Email", self.email)
        self.license = QLineEdit()
        self.license.setPlaceholderText("Tobacco license / tax ID shown on documents")
        cform.addRow("License #", self.license)

        # Logo — shown at the top of every invoice, manifest, and report.
        logo_row = QHBoxLayout()
        self.logo_preview = QLabel("(no logo)")
        self.logo_preview.setStyleSheet("color: #888; border: 1px solid #2a2a4a; border-radius: 4px;")
        self.logo_preview.setFixedSize(160, 64)
        self.logo_preview.setAlignment(Qt.AlignCenter)
        self.logo_preview.setScaledContents(False)
        logo_row.addWidget(self.logo_preview)
        logo_btns = QVBoxLayout()
        choose = QPushButton("Choose…")
        choose.clicked.connect(self.pick_logo)
        logo_btns.addWidget(choose)
        clear = QPushButton("Clear")
        clear.clicked.connect(self.clear_logo)
        logo_btns.addWidget(clear)
        logo_row.addLayout(logo_btns)
        logo_row.addStretch()
        cform.addRow("Logo", logo_row)
        layout.addWidget(company_group)

        # --- Invoicing ---
        invoice_group = QGroupBox("Invoicing")
        iform = QFormLayout(invoice_group)
        self.tax_rate = QDoubleSpinBox()
        self.tax_rate.setRange(0.0, 30.0)
        self.tax_rate.setDecimals(2)
        self.tax_rate.setSuffix(" %")
        iform.addRow("Tax rate", self.tax_rate)
        self.footer = QTextEdit()
        self.footer.setMaximumHeight(80)
        self.footer.setPlaceholderText("Payment instructions shown at the bottom of invoices — remit-to, bank info, thank-you line…")
        iform.addRow("Invoice footer", self.footer)
        self.next_number_label = QLabel("—")
        iform.addRow("Next invoice #", self.next_number_label)

        # Where earnings reports land when saved.
        folder_row = QHBoxLayout()
        self.reports_dir = QLineEdit()
        self.reports_dir.setPlaceholderText(os.path.join(DB_DIR, "reports"))
        folder_row.addWidget(self.reports_dir)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.pick_reports_dir)
        folder_row.addWidget(browse)
        iform.addRow("Reports folder", folder_row)
        layout.addWidget(invoice_group)

        # --- Config transfer (move your setup to another computer) ---
        config_group = QGroupBox("Config File — move your setup to another computer")
        cfg_row = QHBoxLayout(config_group)
        cfg_hint = QLabel("Everything on this page (logo included) in one portable file.\n"
                          "For the data itself, use File > Backup / Restore Database.")
        cfg_hint.setStyleSheet("color: #888; font-weight: normal;")
        cfg_row.addWidget(cfg_hint)
        cfg_row.addStretch()
        export_btn = QPushButton("Export Config…")
        export_btn.clicked.connect(self.export_config)
        cfg_row.addWidget(export_btn)
        import_btn = QPushButton("Import Config…")
        import_btn.clicked.connect(self.import_config)
        cfg_row.addWidget(import_btn)
        layout.addWidget(config_group)

        self.status = QLabel("")
        self.status.setStyleSheet("color: #888;")
        layout.addWidget(self.status)
        layout.addStretch()

    def load(self):
        company = self.db.get_settings("company.")
        self.name.setText(company.get("name", ""))
        self.address.setText(company.get("address", ""))
        self.city_state_zip.setText(company.get("city_state_zip", ""))
        self.phone.setText(company.get("phone", ""))
        self.email.setText(company.get("email", ""))
        self.license.setText(company.get("license", ""))
        try:
            self.tax_rate.setValue(float(self.db.get_setting("invoice.tax_rate", "7.0")))
        except ValueError:
            self.tax_rate.setValue(7.0)
        self.footer.setPlainText(self.db.get_setting("invoice.footer"))
        counter = self.db.get_setting("invoice.next_number", "1")
        from datetime import date
        self.next_number_label.setText(f"INV-{date.today().year}-{int(counter):04d}"
                                       if counter.isdigit() else counter)
        self.reports_dir.setText(self.db.get_setting("reports.dir"))
        self.logo_path = self.db.get_setting("company.logo")
        self._show_logo_preview()

    def _show_logo_preview(self):
        if self.logo_path and os.path.isfile(self.logo_path):
            pix = QPixmap(self.logo_path)
            if not pix.isNull():
                self.logo_preview.setPixmap(
                    pix.scaled(self.logo_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return
        self.logo_preview.setPixmap(QPixmap())
        self.logo_preview.setText("(no logo)")

    def pick_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Logo", DB_DIR,
            "Images (*.png *.jpg *.jpeg *.gif *.bmp)")
        if not path:
            return
        # Copy into the data dir so moving/deleting the original won't break docs.
        ext = os.path.splitext(path)[1].lower() or ".png"
        dest = os.path.join(DB_DIR, "logo" + ext)
        try:
            # Clear any prior logo of a different extension.
            for old in ("logo.png", "logo.jpg", "logo.jpeg", "logo.gif", "logo.bmp"):
                op = os.path.join(DB_DIR, old)
                if os.path.isfile(op) and op != dest:
                    os.remove(op)
            shutil.copy2(path, dest)
            self.logo_path = dest
            self._show_logo_preview()
        except OSError as e:
            self.status.setText(f"Couldn't load that image: {e}")

    def clear_logo(self):
        self.logo_path = ""
        self._show_logo_preview()

    def pick_reports_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Reports Folder",
                                                self.reports_dir.text() or DB_DIR)
        if path:
            self.reports_dir.setText(path)

    def export_config(self):
        self.save()  # capture what's on screen first, so the file matches it
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Config", "cigarbrokercrm-config.json", "Config Files (*.json)")
        if not path:
            return
        try:
            self.db.export_config(path)
            self.db.set_setting("config.path", path)  # File > Save targets this now
            self.status.setText(f"✓ Config exported to {path}")
        except OSError as e:
            self.status.setText(f"Export failed: {e}")

    def import_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Config", "", "Config Files (*.json)")
        if not path:
            return
        try:
            count = self.db.import_config(path)
            self.db.set_setting("config.path", path)  # File > Save targets this now
        except (OSError, ValueError, KeyError) as e:
            self.status.setText(f"Import failed: {e}")
            return
        self.load()
        win = self.window()
        if hasattr(win, "apply_branding"):
            win.apply_branding()
        self.status.setText(f"✓ Imported {count} settings from {os.path.basename(path)}")

    def save(self):
        self.db.set_setting("company.name", self.name.text().strip())
        self.db.set_setting("company.address", self.address.text().strip())
        self.db.set_setting("company.city_state_zip", self.city_state_zip.text().strip())
        self.db.set_setting("company.phone", self.phone.text().strip())
        self.db.set_setting("company.email", self.email.text().strip())
        self.db.set_setting("company.license", self.license.text().strip())
        self.db.set_setting("invoice.tax_rate", f"{self.tax_rate.value():g}")
        self.db.set_setting("invoice.footer", self.footer.toPlainText().strip())
        self.db.set_setting("reports.dir", self.reports_dir.text().strip())
        self.db.set_setting("company.logo", getattr(self, "logo_path", "") or "")
        # Re-brand the app live if the company name changed.
        win = self.window()
        if hasattr(win, "apply_branding"):
            win.apply_branding()
        self.status.setText("✓ Saved. New orders use the new tax rate; existing orders keep theirs.")
