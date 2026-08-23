# AI Generation Prompt — Synthetic Invoice & PO Data

Copy everything inside the **PROMPT START** / **PROMPT END** block below and paste it into Claude, ChatGPT, or any LLM. Use it as-is for the full dataset, or add a line at the end like: *"Start with deliverables 1–3 only"* or *"Generate inv-001.pdf content first."*

---

## PROMPT START

```text
You are a data-generation specialist building synthetic accounts-payable (AP) test data for an invoice-processing system. The system uploads vendor invoice PDFs, extracts fields with AI, matches them to purchase orders (POs) in a database, runs deterministic validation rules, and outputs APPROVE, REVIEW, or REJECT.

Your job is to CREATE all synthetic reference data and invoice documents exactly as specified below. Do not invent alternate vendors, PO numbers, amounts, or scenarios unless I ask for extensions.

================================================================================
CONTEXT — HOW THE SYSTEM USES THIS DATA
================================================================================

Three data layers must align:

1. VENDOR MASTER (JSON/CSV) — who we buy from
2. PURCHASE ORDERS + PO LINES (JSON/CSV) — what we approved to buy
3. INVOICE PDFs (8 files) — what vendors billed; uploaded and read by AI

Matching logic uses:
- Vendor tax ID and legal name (strongest)
- PO number on invoice (very strong if present)
- Currency (hard constraint — must match)
- Invoice total vs PO remaining_value (strong)
- Item code (SKU) overlap between invoice lines and PO lines (strong)
- Quantity vs PO remaining_qty (validation)
- Line description similarity (supporting only)

Financial rules enforced by code (not AI):
- subtotal + tax must equal total (±0.05 rounding)
- quantity × unit_price must equal line_total (±0.05)
- Invoice total must be within 2% OR $50 of PO remaining_value for auto-APPROVE
- Invoiced quantity cannot exceed PO remaining_qty
- Duplicate = same vendor + same invoice number → REJECT
- Vendor on invoice must match vendor on PO
- Closed/cancelled PO cannot auto-approve

Default tax rate for ALL examples: 8%
Default currency: USD (except PO-1009 / V-006 uses EUR)

================================================================================
DELIVERABLES — CREATE ALL OF THE FOLLOWING
================================================================================

DELIVERABLE 1: vendors.json
- JSON array of exactly 10 vendor records

DELIVERABLE 2: purchase_orders.json
- JSON array of exactly 11 PO headers, each with a "lines" array

DELIVERABLE 3: Three CSV files
- vendors.csv
- purchase_orders.csv
- po_lines.csv

DELIVERABLE 4: invoices_worksheet.csv
- One row per invoice PDF (8 rows) — tracking sheet for PDF generation

DELIVERABLE 5: Eight invoice document specifications
- For each PDF (inv-001.pdf through inv-008.pdf):
  a) Full field-by-field content spec
  b) ASCII/text layout mockup of how the PDF should look
  c) Design notes (clean scan vs poor scan)

DELIVERABLE 6: HTML files OR print-ready Markdown for each invoice
- Generate 8 standalone HTML files (inv-001.html … inv-008.html) that I can open in a browser and "Print to PDF"
- Each HTML must contain ALL fields listed in the spec, clearly labeled and readable
- Use a professional invoice layout (header, line table, totals block)
- For inv-008: make the invoice number visually smudged/unreadable (SQ-???)

DELIVERABLE 7: Validation report
- Table showing each invoice → matched PO → expected decision → which rules pass/fail

Do NOT skip any deliverable. If output length is a concern, ask me which deliverable to produce next — but follow the exact data values below with zero substitutions.

================================================================================
DELIVERABLE 1 & 3 — VENDOR MASTER (EXACT VALUES)
================================================================================

Create exactly these 10 vendors:

| vendor_id | legal_name | aliases | tax_id | currency | status |
|-----------|------------|---------|--------|----------|--------|
| V-001 | Acme Office Supplies Inc. | Acme Office, ACME | TAX-ACME-001 | USD | active |
| V-002 | TechPro Solutions LLC | TechPro, Tech Pro Solutions | TAX-TECH-002 | USD | active |
| V-003 | Global Paper Co | GPC, Global Paper Company | TAX-GPC-003 | USD | active |
| V-004 | BuildRight Construction | BuildRight | TAX-BRC-004 | USD | active |
| V-005 | CleanServe Facilities | CleanServe | TAX-CSF-005 | USD | active |
| V-006 | EuroSupply GmbH | Euro Supply | TAX-EURO-006 | EUR | active |
| V-007 | DataStream Analytics | DataStream | TAX-DS-007 | USD | active |
| V-008 | ScanQuality Ltd | Scan Quality | TAX-SQ-008 | USD | active |
| V-009 | Metro Logistics Inc. | Metro Log | TAX-ML-009 | USD | active |
| V-010 | SecureNet Systems | SecureNet | TAX-SN-010 | USD | active |

JSON format per vendor:
{
  "vendor_id": "V-001",
  "legal_name": "Acme Office Supplies Inc.",
  "aliases": ["Acme Office", "ACME"],
  "tax_id": "TAX-ACME-001",
  "currency": "USD",
  "status": "active"
}

================================================================================
DELIVERABLE 2 & 3 — PURCHASE ORDERS (EXACT VALUES)
================================================================================

Create exactly these 11 POs with line items.

PO HEADER FIELDS:
- po_id, vendor_id, currency, status, issue_date, total_value, remaining_value

PO LINE FIELDS:
- line_id, po_id, item_code, description, ordered_qty, invoiced_qty, remaining_qty, unit_price, line_total

RULE: remaining_qty = ordered_qty - invoiced_qty
RULE: total_value and remaining_value INCLUDE tax (8% on line subtotal unless noted)

--- PO-1001 (open, happy path) ---
vendor_id: V-001 | currency: USD | status: open | issue_date: 2026-01-01
Line POL-1001-1: CHR-001 | Office chairs ergonomic | ordered 10, invoiced 0, remaining 10 | unit 450.00 | line 4500.00
Subtotal 4500 + tax 360 = total_value 4860.00, remaining_value 4860.00

--- PO-1002 (open, no PO on invoice scenario) ---
vendor_id: V-002 | issue_date: 2026-01-05
Line POL-1002-1: LAP-T14 | ThinkPad T14 laptops | 8, 0, 8 | 1500.00 | 12000.00
Subtotal 12000 + tax 960 = total 12960.00, remaining 12960.00

--- PO-1003 (open, ambiguous match #1) ---
vendor_id: V-003 | issue_date: 2026-01-10
Line POL-1003-1: PAP-A4 | Copy paper A4 80gsm | 500, 0, 500 | 5.00 | 2500.00
Subtotal 2500 + tax 200 = total 2700.00, remaining 2700.00

--- PO-1004 (open, ambiguous match #2 — same vendor/amount/SKU as PO-1003) ---
vendor_id: V-003 | issue_date: 2026-01-12
Line POL-1004-1: PAP-A4 | Copy paper A4 80gsm premium | 500, 0, 500 | 5.00 | 2500.00
Subtotal 2500 + tax 200 = total 2700.00, remaining 2700.00

--- PO-1005 (partial — half already invoiced, split invoice scenario) ---
vendor_id: V-004 | status: partial | issue_date: 2025-12-01
Line POL-1005-1: STL-A | Steel beams grade A | ordered 60, invoiced 30, remaining 30 | 500.00 | 30000.00
Full PO: subtotal 30000 + tax 2400 = total_value 32400.00
remaining_value: 16200.00 (half left)

--- PO-1006 (open, over-tolerance scenario) ---
vendor_id: V-005 | issue_date: 2026-01-08
Line POL-1006-1: SVC-JAN | Monthly janitorial services | 1, 0, 1 | 5400.00 | 5400.00
total_value 5400.00, remaining_value 5400.00

--- PO-1007 (open, wrong vendor scenario) ---
vendor_id: V-007 | issue_date: 2026-01-15
Line POL-1007-1: MISC-01 | Misc supplies | 1, 0, 1 | 3000.00 | 3000.00
Subtotal 3000 + tax 240 = total 3240.00, remaining 3240.00

--- PO-1008 (open, poor scan scenario) ---
vendor_id: V-008 | issue_date: 2026-01-03
Line POL-1008-1: SVC-SCAN | Document scanning services | 1, 0, 1 | 800.00 | 800.00
Subtotal 800 + tax 64 = total 864.00, remaining 864.00

--- PO-1009 (open, EUR currency) ---
vendor_id: V-006 | currency: EUR | issue_date: 2026-01-06
Line POL-1009-1: EUR-01 | European office supplies | 100, 0, 100 | 45.00 | 4500.00
Subtotal 4500 + tax 500 = total 5000.00 EUR

--- PO-1010 (closed — fully consumed) ---
vendor_id: V-009 | status: closed | issue_date: 2025-06-01
Line POL-1010-1: LOG-01 | Freight services | 1, 1, 0 | 1500.00 | 1500.00
total_value 1500.00, remaining_value 0.00

--- PO-1011 (cancelled) ---
vendor_id: V-010 | status: cancelled | issue_date: 2025-11-01
Line POL-1011-1: SEC-01 | Security audit | 1, 0, 1 | 8000.00 | 8000.00
total_value 8000.00, remaining_value 8000.00

================================================================================
DELIVERABLE 5 & 6 — EIGHT INVOICE PDFs (EXACT CONTENT)
================================================================================

Each invoice PDF must print these fields clearly (except where noted):

HEADER (all invoices):
- Vendor legal name
- Vendor tax ID
- Invoice number
- Invoice date (YYYY-MM-DD)
- Due date (optional)
- Currency
- PO reference (when specified)
- Subtotal, Tax, Total

LINE TABLE (all invoices):
- Item code (SKU)
- Description
- Quantity
- Unit price
- Line total

Filename must be exactly: inv-001.pdf … inv-008.pdf

--- inv-001.pdf → EXPECTED: APPROVE ---
Vendor: Acme Office Supplies Inc.
Tax ID: TAX-ACME-001
Invoice #: INV-2026-001
Date: 2026-01-15 | Due: 2026-02-14
Currency: USD
PO Reference: PO-1001
Line: CHR-001 | Office chairs ergonomic | 10 × 450.00 = 4500.00
Subtotal: 4500.00 | Tax: 360.00 | Total: 4860.00
Design: Clean digital invoice, high contrast, standard font

--- inv-002.pdf → EXPECTED: APPROVE (no PO number on document) ---
Vendor: TechPro Solutions LLC
Tax ID: TAX-TECH-002
Invoice #: TP-8842
Date: 2026-01-20
Currency: USD
PO Reference: LEAVE BLANK / DO NOT PRINT
Line: LAP-T14 | ThinkPad T14 laptops | 8 × 1500.00 = 12000.00
Subtotal: 12000.00 | Tax: 960.00 | Total: 12960.00
Design: Clean digital invoice

--- inv-003.pdf → EXPECTED: REVIEW (ambiguous — two POs match) ---
Vendor: Global Paper Co
Tax ID: TAX-GPC-003
Invoice #: GPC-5521
Date: 2026-01-18
Currency: USD
PO Reference: LEAVE BLANK (critical — do not print PO-1003 or PO-1004)
Line: PAP-A4 | Copy paper A4 80gsm | 500 × 5.00 = 2500.00
Subtotal: 2500.00 | Tax: 200.00 | Total: 2700.00
Design: Standard invoice; ambiguity comes from data not layout

--- inv-004.pdf → EXPECTED: APPROVE (split/partial PO) ---
Vendor: BuildRight Construction
Tax ID: TAX-BRC-004
Invoice #: BR-2026-104
Date: 2026-02-01
Currency: USD
PO Reference: PO-1005
Line: STL-A | Steel beams grade A | 30 × 500.00 = 15000.00  ← half of PO qty
Subtotal: 15000.00 | Tax: 1200.00 | Total: 16200.00
Design: Clean invoice; total must equal PO remaining_value

--- inv-005.pdf → EXPECTED: REVIEW (over tolerance) ---
Vendor: CleanServe Facilities
Tax ID: TAX-CSF-005
Invoice #: CS-7788
Date: 2026-01-25
Currency: USD
PO Reference: PO-1006
Line: SVC-JAN | Monthly janitorial services | 1 × 5500.00 = 5500.00  ← PO unit was 5400
Subtotal: 5500.00 | Tax: 440.00 | Total: 5940.00  ← PO remaining was 5400
Design: Clean invoice; overbilling is intentional

--- inv-006.pdf → EXPECTED: REJECT (duplicate) ---
IDENTICAL CONTENT TO inv-001.pdf:
Vendor: Acme Office Supplies Inc. | Tax: TAX-ACME-001
Invoice #: INV-2026-001 | Date: 2026-01-15 | PO: PO-1001
Line: CHR-001 | 10 × 450.00 = 4500.00
Total: 4860.00
Note: Upload only AFTER inv-001 was already processed. Same PDF content, filename inv-006.pdf

--- inv-007.pdf → EXPECTED: REVIEW (wrong vendor) ---
Vendor: Wrong Vendor Corp  ← NOT in vendor master as PO owner
Tax ID: TAX-WRONG-999
Invoice #: WV-001
Date: 2026-01-22
Currency: USD
PO Reference: PO-1007  ← belongs to DataStream Analytics (V-007)
Line: MISC-01 | Misc supplies | 1 × 3000.00 = 3000.00
Subtotal: 3000.00 | Tax: 240.00 | Total: 3240.00
Design: Clean invoice; vendor name deliberately wrong

--- inv-008.pdf → EXPECTED: REVIEW (poor scan / low confidence) ---
Vendor: ScanQuality Ltd
Tax ID: TAX-SQ-008
Invoice #: SQ-???  ← SMUDGED, BLURRED, or LOW CONTRAST — hard to read
Date: 2026-01-10
Currency: USD
PO Reference: PO-1008
Line: SVC-SCAN | Document scanning services | 1 × 800.00 = 800.00
Subtotal: 800.00 | Tax: 64.00 | Total: 864.00
Design: Simulate scanned document — slight skew OK; invoice NUMBER must be unclear; vendor name and totals should remain readable

================================================================================
HTML INVOICE GENERATION RULES (DELIVERABLE 6)
================================================================================

For each inv-00X.html file:

1. Use a single-page A4 layout
2. Include a visible header with vendor name and "INVOICE" title
3. Show Tax ID prominently below vendor name
4. Use a table for line items with columns: SKU | Description | Qty | Unit Price | Line Total
5. Right-align numeric columns
6. Show Subtotal, Tax (label "Tax (8%)"), and TOTAL in a totals box
7. Use professional styling (minimal colors, clear borders, 12–14px body font)
8. Add a footer: "Synthetic demo invoice — [filename]"
9. For inv-008: apply CSS blur or low opacity ONLY to the invoice number field
10. For inv-002 and inv-003: omit the PO Reference row entirely (or show "—")

I will print each HTML to PDF using browser Print → Save as PDF.

================================================================================
CSV FORMAT RULES (DELIVERABLE 3)
================================================================================

vendors.csv columns:
vendor_id,legal_name,aliases,tax_id,currency,status
(aliases separated by | pipe character)

purchase_orders.csv columns:
po_id,vendor_id,currency,status,issue_date,total_value,remaining_value

po_lines.csv columns:
line_id,po_id,item_code,description,ordered_qty,invoiced_qty,remaining_qty,unit_price,line_total

invoices_worksheet.csv columns:
pdf_file,scenario,expected_decision,vendor_name,tax_id,invoice_number,invoice_date,po_reference,item_code,qty,unit_price,subtotal,tax,total,matched_po,notes

================================================================================
VALIDATION REPORT (DELIVERABLE 7)
================================================================================

Produce a markdown table:

| PDF | Scenario | Expected | PO | Vendor Match | Amount vs Remaining | Qty OK | Duplicate? | Arithmetic OK |
|-----|----------|----------|-----|--------------|---------------------|--------|------------|---------------|

Fill Pass/Fail/N/A for each check per invoice.

================================================================================
QUALITY RULES — DO NOT VIOLATE
================================================================================

1. Use EXACT IDs, names, amounts, and dates from this prompt — no substitutions
2. All arithmetic must reconcile: line extensions, subtotal + tax = total
3. PO total_value includes tax; remaining_value reflects partial consumption
4. inv-003 must NOT have a PO number on the PDF
5. inv-006 must be identical to inv-001 in content
6. inv-007 vendor must NOT match PO-1007 owner (V-007)
7. inv-005 total (5940) must exceed PO-1006 remaining (5400) by more than 2% and $50
8. inv-004 quantity (30) must equal PO-1005 remaining_qty
9. Item codes on invoices must match PO line item codes for APPROVE scenarios
10. Currency on invoice must match PO currency

================================================================================
OUTPUT ORDER
================================================================================

Produce deliverables in this order:

1. vendors.json
2. purchase_orders.json
3. vendors.csv, purchase_orders.csv, po_lines.csv, invoices_worksheet.csv
4. Validation report (Deliverable 7)
5. inv-001.html through inv-008.html (complete, one code block per file)
6. Brief instructions: "Open each HTML in Chrome → Print → Save as PDF → name inv-00X.pdf"

If you hit length limits, stop after complete JSON/CSV + validation report, and ask: "Ready for HTML batch 1 (inv-001 to inv-004)?"

Begin now.
```

## PROMPT END

---

## Optional follow-up prompts

Use these after the main prompt if you need to work in batches.

### Batch HTML generation

```text
Continue from the synthetic AP data task. Generate print-ready HTML for inv-001.html through inv-004.html only. Use the exact field values from the master prompt. Each file must be a complete standalone HTML document I can print to PDF. Do not summarize — output full HTML code blocks.
```

```text
Continue from the synthetic AP data task. Generate inv-005.html through inv-008.html. For inv-008, blur only the invoice number. Output full HTML code blocks.
```

### JSON/CSV only (no HTML)

```text
From the synthetic AP data master prompt, produce ONLY:
1. vendors.json
2. purchase_orders.json
3. vendors.csv, purchase_orders.csv, po_lines.csv, invoices_worksheet.csv
4. Validation report table

No HTML. Use exact values from the prompt. Output each file in a separate fenced code block with the filename as a comment on the first line.
```

### Redesign invoices with more realistic layouts

```text
Regenerate inv-001.html through inv-008.html with more realistic vendor-branded layouts (different header style per vendor), while keeping ALL field values exactly unchanged from the master prompt. Maintain the scenario rules (no PO on inv-002/003, smudged number on inv-008, wrong vendor on inv-007).
```

### Generate Python seed script

```text
Using the exact vendor and PO data from the master prompt, generate a Python script that loads vendors.json and purchase_orders.json and inserts them into SQLAlchemy models matching this schema:
- Vendor(vendor_id, legal_name, normalized_name, aliases, tax_id, currency, status)
- PurchaseOrder(po_id, vendor_id, currency, status, issue_date, total_value, remaining_value)
- PurchaseOrderLine(line_id, po_id, item_code, description, normalized_description, ordered_qty, invoiced_qty, remaining_qty, unit_price, line_total)

Include a normalized_name / normalized_description helper that lowercases and strips extra spaces.
```

---

## Tips for best results

| Tip | Why |
|-----|-----|
| Paste the full **PROMPT START → PROMPT END** block | It is self-contained; the model does not need your repo |
| Ask for **one deliverable at a time** if the model truncates | HTML files are long |
| Say **"Use exact values, no substitutions"** if the model drifts | LLMs sometimes rename vendors or round amounts |
| Verify arithmetic yourself | Check subtotal + tax = total for every PO and invoice |
| Print HTML at **100% scale, A4, no headers/footers** | Cleanest PDF output |
| Name PDFs exactly `inv-001.pdf` … `inv-008.pdf` | Matches demo upload conventions |

---

## Related project doc

Full field reference and checklists: [`SYNTHETIC_DATA_SPEC.md`](SYNTHETIC_DATA_SPEC.md)
