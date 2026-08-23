import asyncio
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.strip().lower())


def normalize_vendor_name(value: str | None) -> str:
    if not value:
        return ""
    text = value.lower().replace("&", " and ")
    text = re.sub(r"['’]", "", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    legal_suffixes = {
        "co",
        "company",
        "corp",
        "corporation",
        "gmbh",
        "inc",
        "incorporated",
        "limited",
        "llc",
        "ltd",
        "plc",
    }
    tokens = [token for token in text.split() if token not in legal_suffixes]
    return " ".join(tokens)


def normalize_invoice_number(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def normalize_po_reference(value: str | None) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"[^a-z0-9\-]", "", value.lower())
    return cleaned.replace("po", "").strip("-") or cleaned


def parse_decimal(value: str | float | int | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        cleaned = str(value).replace(",", "").replace("$", "").replace("€", "").strip()
        if not cleaned:
            return None
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def parse_date(value: str | date | datetime | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%b %d, %Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def format_currency(amount: Decimal | None, currency: str = "USD") -> str:
    if amount is None:
        return "—"
    return f"{currency} {amount:,.2f}"


def confidence_status(score: float) -> str:
    if score >= 0.85:
        return "high"
    if score >= 0.6:
        return "medium"
    if score > 0:
        return "low"
    return "missing"
