"""Earnings math: gross sales vs the broker's NET cut.

Gross = sum of order-item line totals (product sales — tax is collected, not
earned). Net = each line total × the commission % of the product's supplier
company. Pure queries + math, no UI — used by the Reports tab, the printable
earnings report, and the Dashboard.
"""

from datetime import date, timedelta

from sqlalchemy.orm import selectinload

from app.database import Order, OrderItem, Product


def _items_in_range(session, start, end):
    """All order items from non-cancelled orders within [start, end]."""
    q = (
        session.query(OrderItem)
        .join(Order)
        .options(selectinload(OrderItem.product).selectinload(Product.company),
                 selectinload(OrderItem.order))
        .filter(Order.status != "Cancelled")
    )
    if start:
        q = q.filter(Order.order_date >= start)
    if end:
        q = q.filter(Order.order_date <= end)
    return q.all()


def _net_of(item):
    pct = 0.0
    if item.product and item.product.company:
        pct = item.product.company.commission_pct or 0.0
    return (item.line_total or 0.0) * pct / 100.0


def _bucket_label(d, bucket):
    if bucket == "day":
        return d.isoformat()
    if bucket == "week":
        iso = d.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    if bucket == "month":
        return f"{d.year}-{d.month:02d}"
    if bucket == "quarter":
        return f"{d.year}-Q{(d.month - 1) // 3 + 1}"
    return str(d.year)  # year


def earnings_rows(session, start, end, bucket):
    """Per-period rows [{label, gross, net}], sorted by label, plus totals.
    bucket: day | week | month | quarter | year."""
    buckets = {}
    for item in _items_in_range(session, start, end):
        label = _bucket_label(item.order.order_date, bucket)
        b = buckets.setdefault(label, {"label": label, "gross": 0.0, "net": 0.0})
        b["gross"] += item.line_total or 0.0
        b["net"] += _net_of(item)
    rows = sorted(buckets.values(), key=lambda r: r["label"])
    for r in rows:
        r["gross"] = round(r["gross"], 2)
        r["net"] = round(r["net"], 2)
    total_gross = round(sum(r["gross"] for r in rows), 2)
    total_net = round(sum(r["net"] for r in rows), 2)
    return rows, total_gross, total_net


def earnings_by_company(session, start, end):
    """Per-supplier rows [{name, pct, gross, net}], biggest gross first."""
    per = {}
    for item in _items_in_range(session, start, end):
        comp = item.product.company if item.product else None
        name = comp.name if comp else "(unknown)"
        pct = (comp.commission_pct or 0.0) if comp else 0.0
        c = per.setdefault(name, {"name": name, "pct": pct, "gross": 0.0, "net": 0.0})
        c["gross"] += item.line_total or 0.0
        c["net"] += _net_of(item)
    rows = sorted(per.values(), key=lambda r: -r["gross"])
    for r in rows:
        r["gross"] = round(r["gross"], 2)
        r["net"] = round(r["net"], 2)
    return rows


def period_range(period):
    """(start, end, label, bucket) for a named period. end=None = open-ended."""
    today = date.today()
    if period == "This Week":
        start = today - timedelta(days=today.weekday())
        iso = today.isocalendar()
        return start, today, f"{iso[0]}-W{iso[1]:02d}", "day"
    if period == "This Month":
        return date(today.year, today.month, 1), today, f"{today.year}-{today.month:02d}", "week"
    if period == "This Quarter":
        q = (today.month - 1) // 3
        return date(today.year, q * 3 + 1, 1), today, f"{today.year}-Q{q + 1}", "week"
    if period == "This Year":
        return date(today.year, 1, 1), today, str(today.year), "month"
    return None, None, "All-Time", "year"
