from app.db.models import Vendor
from app.services.vendor_resolver import VendorResolver


def test_vendor_normalization_handles_apostrophes_ampersands_and_suffixes():
    vendors = [
        Vendor(
            vendor_id="V-1",
            legal_name="O'Connor & Fuller, Incorporated",
            aliases=["OConnor and Fuller Inc."],
            status="active",
        )
    ]

    result = VendorResolver().resolve("Oconnor and Fuller Ltd", None, vendors)

    assert result["status"] == "RESOLVED"
    assert result["vendor_id"] == "V-1"
    assert result["confidence"] == 1.0
