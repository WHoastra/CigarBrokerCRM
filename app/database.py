"""Database models and session management for CigarBrokerCRM."""

import glob
import os
import shutil
from datetime import datetime, date

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float,
    DateTime, Date, ForeignKey, Enum, event, Boolean, text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

Base = declarative_base()


def _documents_dir():
    """The user's real Documents folder (handles OneDrive redirection);
    falls back to ~/Documents if Qt can't resolve it."""
    try:
        from PySide6.QtCore import QStandardPaths
        d = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        if d:
            return os.path.normpath(d)
    except ImportError:
        pass
    return os.path.join(os.path.expanduser("~"), "Documents")


# All app data (database, config, logo, reports) lives in Documents so users
# can find and back it up. OLD_DB_DIR is the pre-1.3 hidden home-dir location,
# migrated from automatically on startup.
DB_DIR = os.path.join(_documents_dir(), "CigarBrokerCRM")
OLD_DB_DIR = os.path.join(os.path.expanduser("~"), ".cigarbrokercrm")
DB_PATH = os.path.join(DB_DIR, "cigarbroker.db")


def _migrate_data_dir():
    """One-time move from ~/.cigarbrokercrm to Documents\\CigarBrokerCRM:
    copies the database, logo, config file, and reports folder. The old
    folder is left in place as a safety net. Skipped once the new database
    exists (or there's nothing to migrate)."""
    old_db = os.path.join(OLD_DB_DIR, "cigarbroker.db")
    if os.path.isfile(DB_PATH) or not os.path.isfile(old_db):
        return
    os.makedirs(DB_DIR, exist_ok=True)
    shutil.copy2(old_db, DB_PATH)
    for pattern in ("logo.*", "*config*.json"):
        for f in glob.glob(os.path.join(OLD_DB_DIR, pattern)):
            shutil.copy2(f, os.path.join(DB_DIR, os.path.basename(f)))
    old_reports = os.path.join(OLD_DB_DIR, "reports")
    if os.path.isdir(old_reports):
        shutil.copytree(old_reports, os.path.join(DB_DIR, "reports"), dirs_exist_ok=True)


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    company = Column(String(200), default="")
    email = Column(String(200), default="")
    phone = Column(String(50), default="")
    address = Column(String(300), default="")
    city = Column(String(100), default="")
    state = Column(String(50), default="")
    zip_code = Column(String(20), default="")
    tags = Column(String(500), default="")
    preferred_brands = Column(String(500), default="")
    credit_limit = Column(Float, default=0.0)
    payment_terms = Column(String(100), default="Net 30")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    orders = relationship("Order", back_populates="client", cascade="all, delete-orphan")
    communications = relationship("Communication", back_populates="client", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="client", cascade="all, delete-orphan")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def tag_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()] if self.tags else []

    @property
    def brand_list(self):
        return [b.strip() for b in self.preferred_brands.split(",") if b.strip()] if self.preferred_brands else []


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    contact_name = Column(String(200), default="")
    email = Column(String(200), default="")
    phone = Column(String(50), default="")
    address = Column(String(300), default="")
    website = Column(String(200), default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    # The broker's cut of sales of THIS company's products, as a percent.
    # Net earnings on reports = line totals Ã— this rate.
    commission_pct = Column(Float, default=0.0)

    products = relationship("Product", back_populates="company", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="company", cascade="all, delete-orphan")
    communications = relationship("Communication", back_populates="company", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    brand = Column(String(200), nullable=False)
    line = Column(String(200), default="")
    sku = Column(String(100), default="")
    size = Column(String(100), default="")
    wrapper = Column(String(100), default="")
    strength = Column(String(50), default="Medium")
    price = Column(Float, default=0.0)
    availability = Column(String(100), default="In Stock")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

    company = relationship("Company", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")

    @property
    def display_name(self):
        parts = [self.brand]
        if self.line:
            parts.append(self.line)
        if self.size:
            parts.append(f"({self.size})")
        return " ".join(parts)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    order_date = Column(Date, default=date.today)
    status = Column(String(50), default="Pending")
    subtotal = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    # Invoicing: one invoice per order. The number is assigned the first time
    # an invoice is generated and reused on reprints; paid state is separate
    # from fulfillment status (an order can be Delivered but unpaid).
    invoice_number = Column(String(50), default="")
    invoiced_date = Column(Date, nullable=True)
    is_paid = Column(Boolean, default=False)
    paid_date = Column(Date, nullable=True)

    client = relationship("Client", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    # Nullable: deleting a company (and its products) keeps order history â€”
    # the line's qty/price/total stay, the product reference is cleared.
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, default=0.0)
    line_total = Column(Float, default=0.0)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Contact(Base):
    """A person at a client OR a company â€” one of the two FKs is set. Clients
    and companies can carry any number of these (buyer, assistant, repâ€¦);
    the legacy single email/phone/contact_name fields remain the 'main line'."""
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    name = Column(String(200), nullable=False)
    role = Column(String(200), default="")
    email = Column(String(200), default="")
    phone = Column(String(50), default="")
    is_primary = Column(Boolean, default=False)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

    client = relationship("Client", back_populates="contacts")
    company = relationship("Company", back_populates="contacts")


class Event(Base):
    """Calendar entries: meetings, calls, deliveries, follow-ups."""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, default=date.today)
    time = Column(String(20), default="")  # free-form, e.g. "2:30 PM"
    title = Column(String(300), nullable=False)
    kind = Column(String(50), default="Meeting")  # Meeting, Call, Delivery, Follow-up, Other
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

    client = relationship("Client")
    company = relationship("Company")


class Setting(Base):
    """Key-value app settings (broker company info, tax rate, invoice counter).
    Lives in the same DB so File > Backup Database carries it along."""
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, default="")


class Communication(Base):
    __tablename__ = "communications"

    id = Column(Integer, primary_key=True)
    # A log entry belongs to a client OR a company (one of the two is set).
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    comm_type = Column(String(50), default="Note")  # Email, Call, Meeting, Note
    subject = Column(String(300), default="")
    body = Column(Text, default="")
    timestamp = Column(DateTime, default=datetime.now)

    client = relationship("Client", back_populates="communications")
    company = relationship("Company", back_populates="communications")


class DatabaseManager:
    def __init__(self):
        _migrate_data_dir()
        os.makedirs(DB_DIR, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
        Base.metadata.create_all(self.engine)
        self._migrate()
        self._Session = sessionmaker(bind=self.engine)
        self._fix_moved_paths()

    def _fix_moved_paths(self):
        """Stored absolute paths (logo, reports folder, config file) written
        before the data folder moved to Documents still point at the old
        location — rewrite them to the new one."""
        old = os.path.normcase(OLD_DB_DIR)
        for key in ("company.logo", "reports.dir", "config.path"):
            val = self.get_setting(key)
            if val and os.path.normcase(os.path.normpath(val)).startswith(old):
                rel = os.path.relpath(os.path.normpath(val), OLD_DB_DIR)
                self.set_setting(key, os.path.normpath(os.path.join(DB_DIR, rel)))

    def _migrate(self):
        """Add columns that create_all() can't: it creates missing TABLES but
        never alters existing ones, and users already have live databases.
        Idempotent â€” checks PRAGMA table_info before each ALTER."""
        new_columns = {
            "orders": [
                ("invoice_number", "VARCHAR(50) DEFAULT ''"),
                ("invoiced_date", "DATE"),
                ("is_paid", "BOOLEAN DEFAULT 0"),
                ("paid_date", "DATE"),
            ],
            "companies": [
                ("commission_pct", "FLOAT DEFAULT 0.0"),
            ],
            "communications": [
                ("company_id", "INTEGER"),
            ],
        }
        with self.engine.connect() as conn:
            for table, cols in new_columns.items():
                existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
                for name, decl in cols:
                    if name not in existing:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {decl}"))
            conn.commit()

        # communications.client_id was originally NOT NULL (client-only comms).
        # Company comms leave it NULL, so drop the constraint by rebuilding the
        # table â€” but only on an OLD db that still has the constraint. A fresh
        # db from create_all already has the nullable column, so this is skipped.
        with self.engine.connect() as conn:
            info = list(conn.execute(text("PRAGMA table_info(communications)")))
            client_col = next((r for r in info if r[1] == "client_id"), None)
            if client_col and client_col[3] == 1:  # notnull flag still set
                conn.execute(text("ALTER TABLE communications RENAME TO communications_old"))
                conn.commit()
                Base.metadata.tables["communications"].create(conn)
                conn.execute(text(
                    "INSERT INTO communications (id, client_id, company_id, comm_type, subject, body, timestamp) "
                    "SELECT id, client_id, NULL, comm_type, subject, body, timestamp FROM communications_old"
                ))
                conn.execute(text("DROP TABLE communications_old"))
                conn.commit()

        # order_items.product_id was originally NOT NULL. Deleting a company
        # (and its products) now keeps order history by clearing the product
        # reference, so drop the constraint by rebuilding â€” only on an OLD db
        # that still has it (a fresh create_all db is already nullable).
        with self.engine.connect() as conn:
            info = list(conn.execute(text("PRAGMA table_info(order_items)")))
            prod_col = next((r for r in info if r[1] == "product_id"), None)
            if prod_col and prod_col[3] == 1:  # notnull flag still set
                conn.execute(text("ALTER TABLE order_items RENAME TO order_items_old"))
                conn.commit()
                Base.metadata.tables["order_items"].create(conn)
                conn.execute(text(
                    "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, line_total) "
                    "SELECT id, order_id, product_id, quantity, unit_price, line_total FROM order_items_old"
                ))
                conn.execute(text("DROP TABLE order_items_old"))
                conn.commit()

    def session(self) -> Session:
        return self._Session()

    # ---- settings (key-value) ----

    def get_setting(self, key: str, default: str = "") -> str:
        with self.session() as s:
            row = s.get(Setting, key)
            return row.value if row and row.value is not None else default

    def set_setting(self, key: str, value: str):
        with self.session() as s:
            row = s.get(Setting, key)
            if row:
                row.value = str(value)
            else:
                s.add(Setting(key=key, value=str(value)))
            s.commit()

    def get_settings(self, prefix: str) -> dict:
        """All settings under a prefix, keyed without it: get_settings('company.')
        -> {'name': ..., 'address': ...}."""
        with self.session() as s:
            rows = s.query(Setting).filter(Setting.key.like(prefix + "%")).all()
            return {r.key[len(prefix):]: r.value for r in rows}

    def tax_rate(self) -> float:
        """Invoice tax rate as a fraction (0.07 for 7%). Stored as percent."""
        try:
            return float(self.get_setting("invoice.tax_rate", "7.0")) / 100.0
        except ValueError:
            return 0.07

    def app_title(self) -> str:
        """Display name for the app: '<Company> CRM' once set, else the default."""
        name = self.get_setting("company.name", "").strip()
        return f"{name} CRM" if name else "CigarBrokerCRM"

    def reports_dir(self) -> str:
        """Where earnings reports are saved (Settings > Reports folder).
        An empty saved value falls back to the default."""
        path = self.get_setting("reports.dir", "") or os.path.join(DB_DIR, "reports")
        os.makedirs(path, exist_ok=True)
        return path

    def next_invoice_number(self) -> str:
        """Assign the next INV-YYYY-#### number and bump the counter."""
        try:
            counter = int(self.get_setting("invoice.next_number", "1"))
        except ValueError:
            counter = 1
        self.set_setting("invoice.next_number", str(counter + 1))
        return f"INV-{date.today().year}-{counter:04d}"

    def backup(self, dest_path: str = None):
        if dest_path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_path = os.path.join(DB_DIR, f"cigarbroker_backup_{ts}.db")
        shutil.copy2(DB_PATH, dest_path)
        return dest_path

    def restore(self, src_path: str):
        """Replace the live database with a backup .db (e.g. when moving to a
        new computer). Verifies the file looks like ours before overwriting."""
        probe = create_engine(f"sqlite:///{src_path}")
        try:
            with probe.connect() as conn:
                names = {r[0] for r in conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table'"))}
        finally:
            probe.dispose()
        if "clients" not in names or "orders" not in names:
            raise ValueError("That file isn't a CigarBrokerCRM database backup.")
        self.engine.dispose()
        shutil.copy2(src_path, DB_PATH)
        self.engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
        Base.metadata.create_all(self.engine)
        self._migrate()  # the backup may predate newer columns
        self._Session = sessionmaker(bind=self.engine)

    # ---- config export / import (move your setup between computers) ----

    def export_config(self, path: str):
        """Write every setting â€” plus the logo image, embedded as base64 â€” to
        one portable JSON file that import_config loads on another machine."""
        import base64
        import json
        with self.session() as s:
            settings = {r.key: r.value or "" for r in s.query(Setting).all()}
        logo = None
        settings.pop("config.path", None)  # machine-specific; the importer sets its own
        logo_path = settings.pop("company.logo", "")  # machine-specific path; logo travels as bytes
        if logo_path and os.path.isfile(logo_path):
            with open(logo_path, "rb") as f:
                logo = {"ext": os.path.splitext(logo_path)[1].lower() or ".png",
                        "base64": base64.b64encode(f.read()).decode("ascii")}
        payload = {"app": "CigarBrokerCRM", "kind": "config", "version": 1,
                   "settings": settings, "logo": logo}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def import_config(self, path: str) -> int:
        """Load a config file written by export_config; returns how many
        settings were applied. Paths that don't exist here are dropped."""
        import base64
        import json
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if payload.get("app") != "CigarBrokerCRM" or payload.get("kind") != "config":
            raise ValueError("Not a CigarBrokerCRM config file.")
        settings = dict(payload.get("settings") or {})
        # A reports folder from another machine may not exist on this one.
        rd = settings.get("reports.dir", "")
        if rd and not os.path.isdir(rd):
            settings["reports.dir"] = ""
        logo = payload.get("logo")
        if logo and logo.get("base64"):
            dest = os.path.join(DB_DIR, "logo" + (logo.get("ext") or ".png"))
            with open(dest, "wb") as f:
                f.write(base64.b64decode(logo["base64"]))
            settings["company.logo"] = dest
        for key, value in settings.items():
            self.set_setting(key, str(value))
        return len(settings)
