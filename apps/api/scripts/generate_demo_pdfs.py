"""Generate minimal demo PDF fixtures for case-study scenarios."""
from pathlib import Path

import fitz

SCENARIOS = [
    "inv-001", "inv-002", "inv-003", "inv-004",
    "inv-005", "inv-006", "inv-007", "inv-008",
]

OUTPUT = Path(__file__).resolve().parents[3] / "fixtures" / "invoices"


def create_pdf(name: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), f"Demo Invoice Fixture: {name.upper()}", fontsize=14)
    page.insert_text((72, 100), "This PDF triggers mock extraction by filename.", fontsize=10)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUTPUT / f"{name}.pdf"))
    doc.close()


if __name__ == "__main__":
    for s in SCENARIOS:
        create_pdf(s)
    print(f"Created {len(SCENARIOS)} demo PDFs in {OUTPUT}")
