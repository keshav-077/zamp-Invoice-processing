import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Invoice, InvoiceLine, PurchaseOrder, PurchaseOrderLine, Vendor
from app.utils.normalize import normalize_invoice_number, normalize_text

# apps/api/app/fixtures/seed.py -> fixtures live alongside this module
FIXTURES_DIR = Path(__file__).resolve().parent
VENDORS_JSON = FIXTURES_DIR / "vendors.json"
PURCHASE_ORDERS_JSON = FIXTURES_DIR / "purchase_orders.json"

PRIOR_INVOICE = {
    "vendor_id": "V-009",
    "vendor_name": "Metro Logistics Inc.",
    "invoice_number": "ML-2025-442",
    "invoice_date": date(2025, 12, 15),
    "currency": "USD",
    "subtotal": Decimal("1200.00"),
    "tax": Decimal("96.00"),
    "total": Decimal("1296.00"),
    "po_reference": "PO-1010",
    "matched_po_id": "PO-1010",
    "decision": "APPROVE",
    "file_hash": "seed-historical-invoice",
}

PRIOR_INVOICE_LINE = {
    "description": "Freight services",
    "item_code": "LOG-01",
    "quantity": Decimal("1"),
    "unit_price": Decimal("1200.00"),
    "line_total": Decimal("1200.00"),
}


def _load_json(path: Path) -> list | dict:
    if not path.is_file():
        raise FileNotFoundError(f"Required seed file not found: {path}")
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e


def _parse_date(value: str | date) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value))


def _parse_decimal(value: str | int | float | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def load_vendors_from_json() -> list[dict]:
    data = _load_json(VENDORS_JSON)
    if not isinstance(data, list):
        raise ValueError(f"{VENDORS_JSON} must contain a JSON array")
    return data


def load_purchase_orders_from_json() -> list[dict]:
    data = _load_json(PURCHASE_ORDERS_JSON)
    if not isinstance(data, list):
        raise ValueError(f"{PURCHASE_ORDERS_JSON} must contain a JSON array")
    return data


async def _seed_vendors(session: AsyncSession, vendors: list[dict]) -> int:
    existing = set(
        (await session.execute(select(Vendor.vendor_id))).scalars().all()
    )
    added = 0
    for v in vendors:
        vendor_id = v["vendor_id"]
        if vendor_id in existing:
            continue
        session.add(
            Vendor(
                vendor_id=vendor_id,
                legal_name=v["legal_name"],
                normalized_name=normalize_text(v["legal_name"]),
                aliases=v.get("aliases") or [],
                tax_id=v.get("tax_id"),
                currency=v.get("currency", "USD"),
                status=v.get("status", "active"),
            )
        )
        added += 1
    return added


async def _seed_purchase_orders(session: AsyncSession, pos: list[dict]) -> tuple[int, int]:
    existing_pos = set(
        (await session.execute(select(PurchaseOrder.po_id))).scalars().all()
    )
    existing_lines = set(
        (await session.execute(select(PurchaseOrderLine.line_id))).scalars().all()
    )
    pos_added = 0
    lines_added = 0

    for po in pos:
        po_id = po["po_id"]
        if po_id not in existing_pos:
            session.add(
                PurchaseOrder(
                    po_id=po_id,
                    vendor_id=po["vendor_id"],
                    currency=po.get("currency", "USD"),
                    status=po.get("status", "open"),
                    issue_date=_parse_date(po["issue_date"]),
                    total_value=_parse_decimal(po["total_value"]),
                    remaining_value=_parse_decimal(po["remaining_value"]),
                    reference_text=po.get("reference_text"),
                )
            )
            pos_added += 1

        for line in po.get("lines") or []:
            line_id = line["line_id"]
            if line_id in existing_lines:
                continue
            session.add(
                PurchaseOrderLine(
                    po_id=po_id,
                    line_id=line_id,
                    item_code=line.get("item_code"),
                    description=line["description"],
                    normalized_description=normalize_text(line["description"]),
                    ordered_qty=_parse_decimal(line["ordered_qty"]),
                    invoiced_qty=_parse_decimal(line.get("invoiced_qty", "0")),
                    remaining_qty=_parse_decimal(line["remaining_qty"]),
                    unit_price=_parse_decimal(line["unit_price"]),
                    line_total=_parse_decimal(line["line_total"]),
                )
            )
            lines_added += 1

    return pos_added, lines_added


async def _seed_prior_invoice(session: AsyncSession) -> bool:
    file_hash = PRIOR_INVOICE["file_hash"]
    result = await session.execute(
        select(Invoice).where(Invoice.file_hash == file_hash)
    )
    if result.scalar_one_or_none():
        return False

    inv = Invoice(
        vendor_id=PRIOR_INVOICE["vendor_id"],
        vendor_name=PRIOR_INVOICE["vendor_name"],
        normalized_invoice_number=normalize_invoice_number(PRIOR_INVOICE["invoice_number"]),
        invoice_number=PRIOR_INVOICE["invoice_number"],
        invoice_date=PRIOR_INVOICE["invoice_date"],
        currency=PRIOR_INVOICE["currency"],
        subtotal=PRIOR_INVOICE["subtotal"],
        tax=PRIOR_INVOICE["tax"],
        total=PRIOR_INVOICE["total"],
        po_reference=PRIOR_INVOICE["po_reference"],
        matched_po_id=PRIOR_INVOICE["matched_po_id"],
        file_hash=file_hash,
        decision=PRIOR_INVOICE["decision"],
    )
    session.add(inv)
    await session.flush()
    session.add(
        InvoiceLine(
            invoice_id=inv.invoice_id,
            description=PRIOR_INVOICE_LINE["description"],
            item_code=PRIOR_INVOICE_LINE["item_code"],
            quantity=PRIOR_INVOICE_LINE["quantity"],
            unit_price=PRIOR_INVOICE_LINE["unit_price"],
            line_total=PRIOR_INVOICE_LINE["line_total"],
        )
    )
    return True


async def seed_reference_data(session: AsyncSession) -> None:
    vendors = load_vendors_from_json()
    pos = load_purchase_orders_from_json()

    await _seed_vendors(session, vendors)
    await _seed_purchase_orders(session, pos)
    await _seed_prior_invoice(session)
    await session.commit()


async def get_seed_counts(session: AsyncSession) -> dict[str, int]:
    vendor_count = await session.scalar(select(func.count()).select_from(Vendor))
    po_count = await session.scalar(select(func.count()).select_from(PurchaseOrder))
    line_count = await session.scalar(select(func.count()).select_from(PurchaseOrderLine))
    invoice_count = await session.scalar(select(func.count()).select_from(Invoice))
    invoice_line_count = await session.scalar(select(func.count()).select_from(InvoiceLine))
    return {
        "vendors": vendor_count or 0,
        "purchase_orders": po_count or 0,
        "purchase_order_lines": line_count or 0,
        "invoices": invoice_count or 0,
        "invoice_lines": invoice_line_count or 0,
    }


if __name__ == "__main__":
    import asyncio

    from app.db.models import Base
    from app.db.session import AsyncSessionLocal, engine

    async def main():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with AsyncSessionLocal() as session:
            await seed_reference_data(session)
            counts = await get_seed_counts(session)
            print("Seed complete.", counts)

    asyncio.run(main())
