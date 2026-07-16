"""Database models and session management for CigarBrokerCRM."""

import os
import shutil
from datetime import datetime, date, timedelta
from decimal import Decimal
import random

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float,
    DateTime, Date, ForeignKey, Enum, event, Boolean, text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

Base = declarative_base()

DB_DIR = os.path.join(os.path.expanduser("~"), ".cigarbrokercrm")
DB_PATH = os.path.join(DB_DIR, "cigarbroker.db")


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
    # Net earnings on reports = line totals × this rate.
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
    # Nullable: deleting a company (and its products) keeps order history —
    # the line's qty/price/total stay, the product reference is cleared.
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, default=0.0)
    line_total = Column(Float, default=0.0)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Contact(Base):
    """A person at a client OR a company — one of the two FKs is set. Clients
    and companies can carry any number of these (buyer, assistant, rep…);
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
        os.makedirs(DB_DIR, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
        Base.metadata.create_all(self.engine)
        self._migrate()
        self._Session = sessionmaker(bind=self.engine)

    def _migrate(self):
        """Add columns that create_all() can't: it creates missing TABLES but
        never alters existing ones, and users already have live databases.
        Idempotent — checks PRAGMA table_info before each ALTER."""
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
        # table — but only on an OLD db that still has the constraint. A fresh
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
        # reference, so drop the constraint by rebuilding — only on an OLD db
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
        """Write every setting — plus the logo image, embedded as base64 — to
        one portable JSON file that import_config loads on another machine."""
        import base64
        import json
        with self.session() as s:
            settings = {r.key: r.value or "" for r in s.query(Setting).all()}
        logo = None
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

    def has_data(self) -> bool:
        with self.session() as s:
            return s.query(Client).count() > 0

    def needs_seed(self) -> bool:
        """Sample data goes in exactly once, on a truly fresh install. The
        app.seeded flag (not row counts) decides — deleting every client must
        NOT bring the samples back on the next launch."""
        if self.get_setting("app.seeded") == "1":
            return False
        if self.has_data():
            # Existing install that predates the flag: mark it, don't reseed.
            self.set_setting("app.seeded", "1")
            return False
        return True

    def seed_sample_data(self):
        s = self.session()
        try:
            # Companies
            companies_data = [
                {"name": "Arturo Fuente", "contact_name": "Carlos Fuente Jr.", "email": "sales@arturofuente.com", "phone": "813-555-0101", "address": "Tampa, FL", "website": "arturofuente.com"},
                {"name": "Padron Cigars", "contact_name": "Jorge Padron", "email": "orders@padron.com", "phone": "305-555-0202", "address": "Miami, FL", "website": "padron.com"},
                {"name": "Oliva Cigar Co.", "contact_name": "Fred Vandermarliere", "email": "sales@oliva.com", "phone": "305-555-0303", "address": "Miami, FL", "website": "olivacigar.com"},
                {"name": "Drew Estate", "contact_name": "Jonathan Drew", "email": "info@drewestate.com", "phone": "305-555-0404", "address": "Miami, FL", "website": "drewestate.com"},
                {"name": "My Father Cigars", "contact_name": "Jaime Garcia", "email": "sales@myfathercigars.com", "phone": "305-555-0505", "address": "Doral, FL", "website": "myfathercigars.com"},
            ]
            companies = []
            for cd in companies_data:
                c = Company(**cd)
                s.add(c)
                companies.append(c)
            s.flush()

            # Products
            products_data = [
                # Arturo Fuente
                {"company": companies[0], "brand": "Arturo Fuente", "line": "Hemingway", "sku": "AF-HEM-001", "size": "6x52 Toro", "wrapper": "Cameroon", "strength": "Medium", "price": 14.50, "availability": "In Stock"},
                {"company": companies[0], "brand": "Arturo Fuente", "line": "Don Carlos", "sku": "AF-DC-001", "size": "5.5x44 Corona", "wrapper": "Cameroon", "strength": "Medium-Full", "price": 18.00, "availability": "Limited"},
                {"company": companies[0], "brand": "Arturo Fuente", "line": "OpusX", "sku": "AF-OX-001", "size": "6.25x52 Belicoso", "wrapper": "Rosado", "strength": "Full", "price": 35.00, "availability": "Allocated"},
                # Padron
                {"company": companies[1], "brand": "Padron", "line": "1964 Anniversary", "sku": "PAD-64-001", "size": "6.5x52 Torpedo", "wrapper": "Maduro", "strength": "Full", "price": 22.00, "availability": "In Stock"},
                {"company": companies[1], "brand": "Padron", "line": "1926 Serie", "sku": "PAD-26-001", "size": "5.5x52 No. 35", "wrapper": "Natural", "strength": "Full", "price": 28.00, "availability": "In Stock"},
                {"company": companies[1], "brand": "Padron", "line": "Damaso", "sku": "PAD-DAM-001", "size": "6x52 Toro", "wrapper": "Connecticut", "strength": "Mild-Medium", "price": 16.00, "availability": "In Stock"},
                # Oliva
                {"company": companies[2], "brand": "Oliva", "line": "Serie V Melanio", "sku": "OLI-VM-001", "size": "6x52 Toro", "wrapper": "Habano", "strength": "Full", "price": 15.00, "availability": "In Stock"},
                {"company": companies[2], "brand": "Oliva", "line": "Serie G", "sku": "OLI-SG-001", "size": "6x50 Toro", "wrapper": "Cameroon", "strength": "Medium", "price": 8.50, "availability": "In Stock"},
                # Drew Estate
                {"company": companies[3], "brand": "Liga Privada", "line": "No. 9", "sku": "DE-LP9-001", "size": "6x52 Toro", "wrapper": "Connecticut Broadleaf", "strength": "Full", "price": 18.50, "availability": "Limited"},
                {"company": companies[3], "brand": "Liga Privada", "line": "T52", "sku": "DE-T52-001", "size": "6x50 Toro", "wrapper": "Stalk Cut Habano", "strength": "Full", "price": 17.00, "availability": "In Stock"},
                {"company": companies[3], "brand": "Undercrown", "line": "Shade", "sku": "DE-UCS-001", "size": "6x50 Toro", "wrapper": "Connecticut Shade", "strength": "Mild-Medium", "price": 9.00, "availability": "In Stock"},
                # My Father
                {"company": companies[4], "brand": "My Father", "line": "Le Bijou 1922", "sku": "MF-LB-001", "size": "6.5x52 Torpedo", "wrapper": "Oscuro", "strength": "Full", "price": 16.50, "availability": "In Stock"},
                {"company": companies[4], "brand": "My Father", "line": "Flor de las Antillas", "sku": "MF-FLA-001", "size": "6.5x52 Toro Gordo", "wrapper": "Sun Grown", "strength": "Medium-Full", "price": 10.50, "availability": "In Stock"},
            ]
            products = []
            for pd in products_data:
                comp = pd.pop("company")
                p = Product(company_id=comp.id, **pd)
                s.add(p)
                products.append(p)
            s.flush()

            # Clients
            clients_data = [
                {"first_name": "Anthony", "last_name": "Marconi", "company": "Marconi's Fine Tobaccos", "email": "tony@marconistobacco.com", "phone": "212-555-1001", "city": "New York", "state": "NY", "tags": "premium,loyal", "preferred_brands": "Padron,Arturo Fuente", "credit_limit": 25000, "payment_terms": "Net 30"},
                {"first_name": "Sarah", "last_name": "Chen", "company": "The Smoke Room", "email": "sarah@thesmokeroom.com", "phone": "312-555-2002", "city": "Chicago", "state": "IL", "tags": "boutique,growing", "preferred_brands": "Liga Privada,My Father", "credit_limit": 15000, "payment_terms": "Net 15"},
                {"first_name": "Robert", "last_name": "Hayes", "company": "Hayes Luxury Cigars", "email": "rhayes@hayesluxury.com", "phone": "310-555-3003", "city": "Los Angeles", "state": "CA", "tags": "premium,high-volume", "preferred_brands": "Arturo Fuente,Padron,Oliva", "credit_limit": 50000, "payment_terms": "Net 45"},
                {"first_name": "Maria", "last_name": "Vasquez", "company": "Casa Vasquez", "email": "maria@casavasquez.com", "phone": "305-555-4004", "city": "Miami", "state": "FL", "tags": "wholesale,new", "preferred_brands": "My Father,Drew Estate", "credit_limit": 10000, "payment_terms": "Net 30"},
                {"first_name": "James", "last_name": "O'Brien", "company": "Celtic Smoke Shop", "email": "james@celticsmoke.com", "phone": "617-555-5005", "city": "Boston", "state": "MA", "tags": "retail,steady", "preferred_brands": "Oliva,Undercrown", "credit_limit": 20000, "payment_terms": "Net 30"},
                {"first_name": "David", "last_name": "Blackwell", "company": "Blackwell's Lounge", "email": "david@blackwellslounge.com", "phone": "404-555-6006", "city": "Atlanta", "state": "GA", "tags": "lounge,premium", "preferred_brands": "Padron,Liga Privada", "credit_limit": 35000, "payment_terms": "Net 30"},
            ]
            clients = []
            for cd in clients_data:
                c = Client(**cd)
                s.add(c)
                clients.append(c)
            s.flush()

            # Communications
            comm_types = ["Email", "Call", "Meeting", "Note"]
            comm_subjects = [
                ("Email", "Follow-up on recent order", "Touched base regarding their latest shipment."),
                ("Call", "Pricing discussion", "Discussed volume pricing for Q3 orders."),
                ("Meeting", "Product tasting event", "Met at trade show to review new lines."),
                ("Note", "Credit review", "Reviewed account standing - all current."),
                ("Email", "New product announcement", "Sent catalog of new arrivals for the season."),
                ("Call", "Order status inquiry", "Client called to check on pending delivery."),
            ]
            for i, client in enumerate(clients):
                for j in range(random.randint(2, 4)):
                    ct, subj, body = comm_subjects[(i + j) % len(comm_subjects)]
                    comm = Communication(
                        client_id=client.id,
                        comm_type=ct,
                        subject=subj,
                        body=body,
                        timestamp=datetime.now() - timedelta(days=random.randint(1, 90))
                    )
                    s.add(comm)

            # Orders
            statuses = ["Completed", "Completed", "Completed", "Pending", "Shipped"]
            for i, client in enumerate(clients):
                for j in range(random.randint(1, 3)):
                    order_date = date.today() - timedelta(days=random.randint(5, 120))
                    order = Order(
                        client_id=client.id,
                        order_date=order_date,
                        status=random.choice(statuses),
                        notes=""
                    )
                    s.add(order)
                    s.flush()

                    subtotal = 0.0
                    num_items = random.randint(1, 4)
                    chosen = random.sample(products, min(num_items, len(products)))
                    for prod in chosen:
                        qty = random.randint(5, 50)
                        unit = prod.price
                        lt = round(qty * unit, 2)
                        subtotal += lt
                        item = OrderItem(
                            order_id=order.id,
                            product_id=prod.id,
                            quantity=qty,
                            unit_price=unit,
                            line_total=lt
                        )
                        s.add(item)

                    tax = round(subtotal * 0.07, 2)
                    order.subtotal = round(subtotal, 2)
                    order.tax = tax
                    order.total = round(subtotal + tax, 2)

            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()
        self.set_setting("app.seeded", "1")
