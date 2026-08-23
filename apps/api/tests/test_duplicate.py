from datetime import date
from decimal import Decimal

import pytest

from app.db.models import Invoice, ProcessingRun
from app.domain.invoice import NormalizedInvoice
from app.services.duplicate import DuplicateService


@pytest.mark.asyncio
async def test_duplicate_levels_are_classified_without_overlap(db_session):
    session, _, _ = db_session
    exact_run = ProcessingRun(
        run_id="run-exact",
        status="completed",
        file_hash="same-content",
    )
    probable = Invoice(
        invoice_id="invoice-probable",
        run_id=None,
        vendor_id="V-001",
        normalized_invoice_number="prob1",
        invoice_number="PROB-1",
        invoice_date=date(2026, 3, 1),
        total=Decimal("100.00"),
        currency="USD",
    )
    possible = Invoice(
        invoice_id="invoice-possible",
        run_id=None,
        vendor_id="V-001",
        normalized_invoice_number="different",
        invoice_number="DIFFERENT",
        invoice_date=date(2026, 3, 1),
        total=Decimal("100.00"),
        currency="USD",
    )
    session.add_all([exact_run, probable, possible])
    await session.flush()

    matches = await DuplicateService(session).check(
        current_run_id="current",
        file_hash="same-content",
        invoice=NormalizedInvoice(
            invoice_number="PROB-1",
            invoice_date=date(2026, 3, 1),
            total=Decimal("100.00"),
            currency="USD",
        ),
        vendor_id="V-001",
    )

    assert {match.match_type for match in matches} == {
        "exact",
        "probable",
        "possible",
    }
