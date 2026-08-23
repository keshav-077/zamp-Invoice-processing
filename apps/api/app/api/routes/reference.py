from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.models import Vendor, PurchaseOrder
from app.db.session import get_db
from app.domain.schemas import VendorOut, POOut, POLineOut

router = APIRouter(tags=["reference"])


@router.get("/api/vendors", response_model=list[VendorOut])
async def list_vendors(db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    result = await db.execute(select(Vendor).order_by(Vendor.legal_name))
    vendors = result.scalars().all()
    return [VendorOut(vendor_id=v.vendor_id, legal_name=v.legal_name, aliases=v.aliases or [], tax_id=v.tax_id, currency=v.currency, status=v.status) for v in vendors]


@router.get("/api/pos", response_model=list[POOut])
async def list_pos(query: str | None = None, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    stmt = select(PurchaseOrder).options(selectinload(PurchaseOrder.lines), selectinload(PurchaseOrder.vendor))
    if query:
        stmt = stmt.where(PurchaseOrder.po_id.ilike(f"%{query}%"))
    result = await db.execute(stmt.order_by(PurchaseOrder.po_id))
    pos = result.scalars().all()
    return [
        POOut(
            po_id=po.po_id,
            vendor_id=po.vendor_id,
            vendor_name=po.vendor.legal_name if po.vendor else None,
            currency=po.currency,
            status=po.status,
            issue_date=po.issue_date,
            total_value=po.total_value,
            remaining_value=po.remaining_value,
            lines=[
                POLineOut(
                    line_id=l.line_id,
                    item_code=l.item_code,
                    description=l.description,
                    ordered_qty=l.ordered_qty,
                    invoiced_qty=l.invoiced_qty,
                    remaining_qty=l.remaining_qty,
                    unit_price=l.unit_price,
                    line_total=l.line_total,
                )
                for l in po.lines
            ],
        )
        for po in pos
    ]
