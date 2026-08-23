from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base, Invoice, PurchaseOrder, PurchaseOrderLine, Vendor
from app.fixtures.seed import (
    get_seed_counts,
    load_purchase_orders_from_json,
    load_vendors_from_json,
    seed_reference_data,
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def seed_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def test_load_vendors_from_json():
    vendors = load_vendors_from_json()
    assert len(vendors) == 10
    assert vendors[0]["vendor_id"] == "V-001"
    assert vendors[0]["status"] == "active"


def test_load_purchase_orders_from_json():
    pos = load_purchase_orders_from_json()
    assert len(pos) == 11
    po1005 = next(p for p in pos if p["po_id"] == "PO-1005")
    assert po1005["status"] == "partial"
    assert po1005["remaining_value"] == "16200.00"
    assert len(po1005["lines"]) == 1


@pytest.mark.asyncio
async def test_seed_creates_expected_counts(seed_session):
    await seed_reference_data(seed_session)
    counts = await get_seed_counts(seed_session)
    assert counts == {
        "vendors": 10,
        "purchase_orders": 11,
        "purchase_order_lines": 11,
        "invoices": 1,
        "invoice_lines": 1,
    }


@pytest.mark.asyncio
async def test_seed_is_idempotent(seed_session):
    await seed_reference_data(seed_session)
    first = await get_seed_counts(seed_session)
    await seed_reference_data(seed_session)
    second = await get_seed_counts(seed_session)
    assert first == second


@pytest.mark.asyncio
async def test_seed_representative_values(seed_session):
    await seed_reference_data(seed_session)

    vendor = (
        await seed_session.execute(select(Vendor).where(Vendor.vendor_id == "V-006"))
    ).scalar_one()
    assert vendor.currency == "EUR"
    assert vendor.normalized_name == "eurosupply gmbh"

    po = (
        await seed_session.execute(select(PurchaseOrder).where(PurchaseOrder.po_id == "PO-1005"))
    ).scalar_one()
    assert po.status == "partial"
    assert po.issue_date == date(2025, 12, 1)
    assert po.remaining_value == Decimal("16200.00")

    line = (
        await seed_session.execute(
            select(PurchaseOrderLine).where(PurchaseOrderLine.line_id == "POL-1005-1")
        )
    ).scalar_one()
    assert line.invoiced_qty == Decimal("30")
    assert line.normalized_description == "steel beams grade a"

    prior = (
        await seed_session.execute(
            select(Invoice).where(Invoice.file_hash == "seed-historical-invoice")
        )
    ).scalar_one()
    assert prior.invoice_number == "ML-2025-442"
    assert prior.matched_po_id == "PO-1010"


@pytest.mark.asyncio
async def test_partial_database_does_not_duplicate_prior_invoice(seed_session):
    await seed_reference_data(seed_session)

    vendor = Vendor(
        vendor_id="V-999",
        legal_name="Temp Vendor",
        normalized_name="temp vendor",
        aliases=[],
        currency="USD",
        status="active",
    )
    seed_session.add(vendor)
    await seed_session.commit()

    await seed_reference_data(seed_session)
    counts = await get_seed_counts(seed_session)
    assert counts["vendors"] == 11
    assert counts["invoices"] == 1
