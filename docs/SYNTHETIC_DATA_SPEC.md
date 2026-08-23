# Synthetic Data Specification — Invoice Processing MVP

This document defines how to create **vendors**, **purchase orders (POs)**, and **invoice PDFs** for the Invoice Processing case study. Follow these specs so uploaded invoices match reference data and produce the expected **APPROVE**, **REVIEW**, or **REJECT** outcomes.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Data Layers & Relationships](#2-data-layers--relationships)
3. [Vendor Master Data](#3-vendor-master-data)
4. [Purchase Order Data](#4-purchase-order-data)
5. [Invoice PDF Content](#5-invoice-pdf-content)
6. [Business Rules & Validation](#6-business-rules--validation)
7. [Complete Vendor Catalog](#7-complete-vendor-catalog)
8. [Complete PO Catalog](#8-complete-po-catalog)
9. [Eight Demo Invoice Scenarios](#9-eight-demo-invoice-scenarios)
10. [CSV Templates](#10-csv-templates)
11. [JSON Templates](#11-json-templates)
12. [PDF Layout Guide](#12-pdf-layout-guide)
13. [Pre-Generation Checklist](#13-pre-generation-checklist)
14. [Minimum Viable Dataset](#14-minimum-viable-dataset)
15. [Loading Data Into the System](#15-loading-data-into-the-system)

---

## 1. Overview

The system processes **invoice PDFs** against **seeded reference data**. You do not need a real ERP — you need:

| Layer | Format | Purpose |
|-------|--------|---------|
| Vendor master | JSON / CSV / DB seed | Resolve vendor identity from invoice |
| Purchase orders | JSON / CSV / DB seed | Match and validate invoice against approved spend |
| Invoice PDFs | PDF files | Upload via UI; AI extracts fields and compares to POs |

**Default currency:** USD (unless scenario specifies EUR).

**Default tax rate for examples:** 8% (adjust consistently across subtotal, tax, and total).

---

## 2. Data Layers & Relationships

```
Vendor (1) ──< Purchase Order (many)
                    │
                    └── PO Lines (many)

Invoice PDF ──extract──> Invoice fields ──match──> PO
                              │
                              └── compared to Vendor + PO lines + remaining balance
```

### Matching signals (what the system uses)

| Signal | Strength | Source |
|--------|----------|--------|
| Exact PO number on invoice | Very strong | Invoice header |
| Vendor tax ID | Very strong | Invoice header ↔ vendor master |
| Vendor legal name / alias | Strong | Invoice header ↔ vendor master |
| Currency | Hard constraint | Invoice ↔ PO |
| Invoice total vs PO remaining value | Strong | Invoice totals ↔ PO header |
| Item code (SKU) overlap | Strong | Invoice lines ↔ PO lines |
| Quantity vs remaining PO qty | Strong validation | Invoice lines ↔ PO lines |
| Line description similarity | Supporting | Fuzzy / semantic match |
| Invoice date vs PO issue date | Supporting | Dates |

**Important:** A PO number alone cannot override a vendor mismatch. Financial decisions are made by deterministic rules, not by the AI model.

---

## 3. Vendor Master Data

### 3.1 Field Definitions

| Field | Required | Type | Example | Notes |
|-------|----------|------|---------|-------|
| `vendor_id` | Yes | string | `V-001` | Unique internal ID; stable across POs and invoices |
| `legal_name` | Yes | string | `Acme Office Supplies Inc.` | Primary name; should appear on invoice header |
| `aliases` | Optional | string[] | `["Acme Office", "ACME"]` | Alternate names that may appear on invoices |
| `tax_id` | Strongly recommended | string | `TAX-ACME-001` | Vendor tax/VAT ID; best deterministic match |
| `email_domain` | Optional | string | `acme.com` | Supporting identifier (not used in MVP seed) |
| `currency` | Yes | string (3) | `USD` | Default currency for this vendor |
| `status` | Yes | enum | `active` | `active` or `blocked` |

### 3.2 Vendor JSON Schema (single record)

```json
{
  "vendor_id": "V-001",
  "legal_name": "Acme Office Supplies Inc.",
  "aliases": ["Acme Office", "ACME"],
  "tax_id": "TAX-ACME-001",
  "currency": "USD",
  "status": "active"
}
```

### 3.3 Vendor Creation Tips

- Use **consistent legal names** on both the vendor record and the invoice PDF.
- Always print **tax_id** on the invoice when possible — matching becomes near-certain.
- Use `blocked` status only if you want to test vendor-blocked rejection flows.
- One vendor can have many POs; each PO belongs to exactly one vendor.

---

## 4. Purchase Order Data

### 4.1 PO Header Fields

| Field | Required | Type | Example | Notes |
|-------|----------|------|---------|-------|
| `po_id` | Yes | string | `PO-1001` | Unique; often printed on invoice as "PO #", "Purchase Order", "Order Ref" |
| `vendor_id` | Yes | string | `V-001` | Must reference an existing vendor |
| `currency` | Yes | string (3) | `USD` | Must match invoice currency |
| `status` | Yes | enum | `open` | See status table below |
| `issue_date` | Yes | date | `2026-01-01` | ISO format `YYYY-MM-DD` |
| `total_value` | Yes | decimal | `4860.00` | Original PO value **including tax** |
| `remaining_value` | Yes | decimal | `4860.00` | Amount still available to invoice |
| `reference_text` | Optional | string | `Contract-2026-001` | Supporting reference (optional in MVP) |

### 4.2 PO Status Values

| Status | Meaning | Auto-approve? |
|--------|---------|---------------|
| `open` | Full balance available | Yes, if all checks pass |
| `partial` | Some amount already consumed | Yes, if invoice ≤ remaining |
| `closed` | Fully consumed | No → REJECT/REVIEW |
| `cancelled` | PO cancelled | No → REJECT |

### 4.3 PO Line Fields

| Field | Required | Type | Example | Notes |
|-------|----------|------|---------|-------|
| `line_id` | Yes | string | `POL-1001-1` | Unique per line |
| `po_id` | Yes | string | `PO-1001` | Parent PO |
| `item_code` | Strongly recommended | string | `CHR-001` | SKU; primary line-matching signal |
| `description` | Yes | string | `Office chairs ergonomic` | Human-readable item name |
| `ordered_qty` | Yes | decimal | `10` | Total quantity ordered |
| `invoiced_qty` | Yes | decimal | `0` | Quantity already invoiced against this line |
| `remaining_qty` | Yes | decimal | `10` | Must equal `ordered_qty - invoiced_qty` |
| `unit_price` | Yes | decimal | `450.00` | Price per unit |
| `line_total` | Yes | decimal | `4500.00` | Typically `ordered_qty × unit_price` (excl. tax) |

### 4.4 PO JSON Schema (full example)

```json
{
  "po_id": "PO-1001",
  "vendor_id": "V-001",
  "currency": "USD",
  "status": "open",
  "issue_date": "2026-01-01",
  "total_value": "4860.00",
  "remaining_value": "4860.00",
  "lines": [
    {
      "line_id": "POL-1001-1",
      "item_code": "CHR-001",
      "description": "Office chairs ergonomic",
      "ordered_qty": "10",
      "invoiced_qty": "0",
      "remaining_qty": "10",
      "unit_price": "450.00",
      "line_total": "4500.00"
    }
  ]
}
```

### 4.5 PO Value Calculations

For each PO, define amounts in this order:

1. **Line subtotal:** `ordered_qty × unit_price` → `line_total`
2. **PO subtotal:** sum of all `line_total`
3. **PO tax:** apply tax rate (e.g. 8%)
4. **PO total:** `subtotal + tax` → use for `total_value`

**Example (PO-1001):**

| Step | Calculation | Amount |
|------|-------------|--------|
| Line subtotal | 10 × 450.00 | 4,500.00 |
| Tax (8%) | 4500 × 0.08 | 360.00 |
| PO total | 4500 + 360 | **4,860.00** |

Set `total_value = 4860.00` and `remaining_value = 4860.00` for a new open PO.

### 4.6 Split / Partial PO Setup

For a PO that is **half consumed** (e.g. PO-1005):

| Field | Full PO | After half invoiced |
|-------|---------|---------------------|
| `status` | `open` → `partial` | `partial` |
| `total_value` | 32400.00 | 32400.00 (unchanged) |
| `remaining_value` | 32400.00 | **16200.00** |
| `ordered_qty` | 60 | 60 |
| `invoiced_qty` | 0 | **30** |
| `remaining_qty` | 60 | **30** |

The next invoice should bill **30 units** and total **16200.00** (15000 subtotal + 1200 tax).

---

## 5. Invoice PDF Content

These are the fields the multimodal extractor reads from the PDF. **Print them clearly** in a standard invoice layout.

### 5.1 Invoice Header Fields

| Field | Required | Example | Notes |
|-------|----------|---------|-------|
| Vendor name | Yes | `Acme Office Supplies Inc.` | Must match vendor master (exact or fuzzy) |
| Vendor tax ID | Recommended | `TAX-ACME-001` | Strongest vendor match |
| Invoice number | Yes | `INV-2026-001` | Unique per vendor |
| Invoice date | Yes | `2026-01-15` | `YYYY-MM-DD` or `MM/DD/YYYY` |
| Due date | Optional | `2026-02-14` | Payment due date |
| Currency | Yes | `USD` | Must match PO currency |
| PO reference | Optional | `PO-1001` | Omit for "no PO number" scenarios |
| Payment details | Optional | `Bank: ... IBAN: ...` | Not validated in MVP |
| Subtotal | Yes | `4500.00` | Before tax |
| Tax | Yes | `360.00` | Tax amount |
| Total | Yes | `4860.00` | Must equal subtotal + tax |

### 5.2 Invoice Line Fields

| Field | Recommended | Example |
|-------|-------------|---------|
| Item code / SKU | Yes | `CHR-001` |
| Description | Yes | `Office chairs ergonomic` |
| Quantity | Yes | `10` |
| Unit price | Yes | `450.00` |
| Tax rate | Optional | `8%` |
| Line total | Yes | `4500.00` |

### 5.3 Invoice Arithmetic Rules

The system independently recalculates and validates:

```
line_total ≈ quantity × unit_price     (tolerance: ±0.05)
total ≈ subtotal + tax                 (tolerance: ±0.05)
```

Failures route to **REVIEW** or **REJECT** — never silent approval.

### 5.4 Amount Tolerance (invoice vs PO)

Configured policy defaults:

| Tolerance | Value |
|-----------|-------|
| Percentage | 2% |
| Absolute | $50.00 |

Invoice total may differ from PO `remaining_value` only within these limits for auto-approval.

---

## 6. Business Rules & Validation

### 6.1 Decision Outcomes

| Outcome | Meaning |
|---------|---------|
| **APPROVE** | Straight-through processing; all hard controls pass |
| **REVIEW** | Human judgment required; exceptions, ambiguity, low confidence |
| **REJECT** | Policy violation; duplicate, cancelled PO, bad arithmetic |

### 6.2 Rules That Block Auto-Approval

| Rule | Condition | Typical outcome |
|------|-----------|-----------------|
| Missing critical field | No total, currency, or vendor | REVIEW |
| Vendor mismatch | Invoice vendor ≠ PO vendor | REVIEW |
| PO closed/cancelled | PO status not open/partial | REJECT |
| Currency mismatch | Invoice currency ≠ PO currency | REVIEW/REJECT |
| Over tolerance | Invoice total exceeds remaining + tolerance | REVIEW |
| Quantity exceeded | Invoiced qty > PO remaining qty | REVIEW |
| Arithmetic mismatch | Subtotal + tax ≠ total | REJECT |
| Duplicate | Same vendor + invoice number already processed | REJECT |
| Ambiguous PO match | Two POs score similarly; low margin | REVIEW |
| Low extraction confidence | Material fields uncertain (e.g. poor scan) | REVIEW |
| Credit note | Negative invoice total | REVIEW |

### 6.3 Duplicate Detection

Duplicates are detected by:

1. **Exact:** same `vendor_id` + same normalized invoice number
2. **File hash:** identical PDF uploaded twice
3. **Near:** same vendor + same date + same total (warning)

For duplicate testing: process **inv-001** first, then upload **inv-006** (identical content).

---

## 7. Complete Vendor Catalog

Use these 10 vendors for the full demo dataset:

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

### JSON array (copy-paste ready)

```json
[
  {"vendor_id": "V-001", "legal_name": "Acme Office Supplies Inc.", "aliases": ["Acme Office", "ACME"], "tax_id": "TAX-ACME-001", "currency": "USD", "status": "active"},
  {"vendor_id": "V-002", "legal_name": "TechPro Solutions LLC", "aliases": ["TechPro", "Tech Pro Solutions"], "tax_id": "TAX-TECH-002", "currency": "USD", "status": "active"},
  {"vendor_id": "V-003", "legal_name": "Global Paper Co", "aliases": ["GPC", "Global Paper Company"], "tax_id": "TAX-GPC-003", "currency": "USD", "status": "active"},
  {"vendor_id": "V-004", "legal_name": "BuildRight Construction", "aliases": ["BuildRight"], "tax_id": "TAX-BRC-004", "currency": "USD", "status": "active"},
  {"vendor_id": "V-005", "legal_name": "CleanServe Facilities", "aliases": ["CleanServe"], "tax_id": "TAX-CSF-005", "currency": "USD", "status": "active"},
  {"vendor_id": "V-006", "legal_name": "EuroSupply GmbH", "aliases": ["Euro Supply"], "tax_id": "TAX-EURO-006", "currency": "EUR", "status": "active"},
  {"vendor_id": "V-007", "legal_name": "DataStream Analytics", "aliases": ["DataStream"], "tax_id": "TAX-DS-007", "currency": "USD", "status": "active"},
  {"vendor_id": "V-008", "legal_name": "ScanQuality Ltd", "aliases": ["Scan Quality"], "tax_id": "TAX-SQ-008", "currency": "USD", "status": "active"},
  {"vendor_id": "V-009", "legal_name": "Metro Logistics Inc.", "aliases": ["Metro Log"], "tax_id": "TAX-ML-009", "currency": "USD", "status": "active"},
  {"vendor_id": "V-010", "legal_name": "SecureNet Systems", "aliases": ["SecureNet"], "tax_id": "TAX-SN-010", "currency": "USD", "status": "active"}
]
```

---

## 8. Complete PO Catalog

### 8.1 PO Summary Table

| po_id | vendor_id | status | issue_date | total_value | remaining_value | Purpose |
|-------|-----------|--------|------------|-------------|-----------------|---------|
| PO-1001 | V-001 | open | 2026-01-01 | 4860.00 | 4860.00 | Happy path (inv-001) |
| PO-1002 | V-002 | open | 2026-01-05 | 12960.00 | 12960.00 | No PO on invoice (inv-002) |
| PO-1003 | V-003 | open | 2026-01-10 | 2700.00 | 2700.00 | Ambiguous match (inv-003) |
| PO-1004 | V-003 | open | 2026-01-12 | 2700.00 | 2700.00 | Ambiguous match (inv-003) |
| PO-1005 | V-004 | partial | 2025-12-01 | 32400.00 | 16200.00 | Split invoice (inv-004) |
| PO-1006 | V-005 | open | 2026-01-08 | 5400.00 | 5400.00 | Over tolerance (inv-005) |
| PO-1007 | V-007 | open | 2026-01-15 | 3240.00 | 3240.00 | Wrong vendor (inv-007) |
| PO-1008 | V-008 | open | 2026-01-03 | 864.00 | 864.00 | Poor scan (inv-008) |
| PO-1009 | V-006 | open | 2026-01-06 | 5000.00 | 5000.00 | EUR currency testing |
| PO-1010 | V-009 | closed | 2025-06-01 | 1500.00 | 0.00 | Closed PO testing |
| PO-1011 | V-010 | cancelled | 2025-11-01 | 8000.00 | 8000.00 | Cancelled PO testing |

### 8.2 PO Line Details

#### PO-1001 (Acme — office chairs)

| line_id | item_code | description | ordered | invoiced | remaining | unit_price | line_total |
|---------|-----------|-------------|---------|----------|-----------|------------|------------|
| POL-1001-1 | CHR-001 | Office chairs ergonomic | 10 | 0 | 10 | 450.00 | 4500.00 |

Tax: 360.00 → **PO total: 4860.00**

---

#### PO-1002 (TechPro — laptops)

| line_id | item_code | description | ordered | invoiced | remaining | unit_price | line_total |
|---------|-----------|-------------|---------|----------|-----------|------------|------------|
| POL-1002-1 | LAP-T14 | ThinkPad T14 laptops | 8 | 0 | 8 | 1500.00 | 12000.00 |

Tax: 960.00 → **PO total: 12960.00**

---

#### PO-1003 (Global Paper — standard)

| line_id | item_code | description | ordered | invoiced | remaining | unit_price | line_total |
|---------|-----------|-------------|---------|----------|-----------|------------|------------|
| POL-1003-1 | PAP-A4 | Copy paper A4 80gsm | 500 | 0 | 500 | 5.00 | 2500.00 |

Tax: 200.00 → **PO total: 2700.00**

---

#### PO-1004 (Global Paper — premium, ambiguous sibling)

| line_id | item_code | description | ordered | invoiced | remaining | unit_price | line_total |
|---------|-----------|-------------|---------|----------|-----------|------------|------------|
| POL-1004-1 | PAP-A4 | Copy paper A4 80gsm premium | 500 | 0 | 500 | 5.00 | 2500.00 |

Tax: 200.00 → **PO total: 2700.00**

> **Note:** PO-1003 and PO-1004 have the same vendor, amount, and SKU. Invoices without a PO number will match both → **REVIEW**.

---

#### PO-1005 (BuildRight — split/partial)

| line_id | item_code | description | ordered | invoiced | remaining | unit_price | line_total |
|---------|-----------|-------------|---------|----------|-----------|------------|------------|
| POL-1005-1 | STL-A | Steel beams grade A | 60 | 30 | 30 | 500.00 | 30000.00 |

Full PO tax: 2400.00 → full total: 32400.00  
**Remaining value: 16200.00** (half already invoiced)

---

#### PO-1006 (CleanServe — janitorial)

| line_id | item_code | description | ordered | invoiced | remaining | unit_price | line_total |
|---------|-----------|-------------|---------|----------|-----------|------------|------------|
| POL-1006-1 | SVC-JAN | Monthly janitorial services | 1 | 0 | 1 | 5400.00 | 5400.00 |

Tax: 432.00 → **PO total: 5400.00** (subtotal equals total for single service line; tax embedded in remaining_value for matching)

> For inv-005, invoice bills **5500 + 440 tax = 5940**, exceeding PO remaining **5400**.

---

#### PO-1007 (DataStream — misc)

| line_id | item_code | description | ordered | invoiced | remaining | unit_price | line_total |
|---------|-----------|-------------|---------|----------|-----------|------------|------------|
| POL-1007-1 | MISC-01 | Misc supplies | 1 | 0 | 1 | 3000.00 | 3000.00 |

Tax: 240.00 → **PO total: 3240.00**

---

#### PO-1008 (ScanQuality — scanning)

| line_id | item_code | description | ordered | invoiced | remaining | unit_price | line_total |
|---------|-----------|-------------|---------|----------|-----------|------------|------------|
| POL-1008-1 | SVC-SCAN | Document scanning services | 1 | 0 | 1 | 800.00 | 800.00 |

Tax: 64.00 → **PO total: 864.00**

---

#### PO-1009 (EuroSupply — EUR)

| line_id | item_code | description | ordered | invoiced | remaining | unit_price | line_total |
|---------|-----------|-------------|---------|----------|-----------|------------|------------|
| POL-1009-1 | EUR-01 | European office supplies | 100 | 0 | 100 | 45.00 | 4500.00 |

Tax: 500.00 → **PO total: 5000.00 EUR**

---

#### PO-1010 (Metro Logistics — closed)

| line_id | item_code | description | ordered | invoiced | remaining | unit_price | line_total |
|---------|-----------|-------------|---------|----------|-----------|------------|------------|
| POL-1010-1 | LOG-01 | Freight services | 1 | 1 | 0 | 1500.00 | 1500.00 |

**Status: closed**, remaining: 0.00

---

#### PO-1011 (SecureNet — cancelled)

| line_id | item_code | description | ordered | invoiced | remaining | unit_price | line_total |
|---------|-----------|-------------|---------|----------|-----------|------------|------------|
| POL-1011-1 | SEC-01 | Security audit | 1 | 0 | 1 | 8000.00 | 8000.00 |

**Status: cancelled**

---

## 9. Eight Demo Invoice Scenarios

### Scenario Index

| PDF filename | Scenario | Expected | Matched PO | Key trick |
|--------------|----------|----------|------------|-----------|
| inv-001.pdf | Happy path | **APPROVE** | PO-1001 | Exact PO + vendor + amounts |
| inv-002.pdf | Missing PO number | **APPROVE** | PO-1002 | No PO on PDF; vendor + SKU + amount match |
| inv-003.pdf | Ambiguous PO | **REVIEW** | PO-1003 or PO-1004 | No PO on PDF; two equally plausible POs |
| inv-004.pdf | Split invoice | **APPROVE** | PO-1005 | Bill half of partial PO |
| inv-005.pdf | Over tolerance | **REVIEW** | PO-1006 | Invoice total > PO remaining |
| inv-006.pdf | Duplicate | **REJECT** | PO-1001 | Identical to inv-001; upload after inv-001 |
| inv-007.pdf | Wrong vendor | **REVIEW** | PO-1007 | Wrong vendor name; PO belongs to V-007 |
| inv-008.pdf | Poor scan | **REVIEW** | PO-1008 | Smudged/missing invoice number |

---

### inv-001.pdf — Happy Path (APPROVE)

**Purpose:** Clean straight-through processing.

| Field | Value |
|-------|-------|
| Vendor name | Acme Office Supplies Inc. |
| Vendor tax ID | TAX-ACME-001 |
| Invoice number | INV-2026-001 |
| Invoice date | 2026-01-15 |
| Due date | 2026-02-14 |
| Currency | USD |
| PO reference | PO-1001 |

**Lines:**

| item_code | description | qty | unit_price | line_total |
|-----------|-------------|-----|------------|------------|
| CHR-001 | Office chairs ergonomic | 10 | 450.00 | 4500.00 |

**Totals:** Subtotal 4500.00 | Tax 360.00 | **Total 4860.00**

---

### inv-002.pdf — No PO Number (APPROVE)

**Purpose:** System matches without explicit PO reference.

| Field | Value |
|-------|-------|
| Vendor name | TechPro Solutions LLC |
| Vendor tax ID | TAX-TECH-002 |
| Invoice number | TP-8842 |
| Invoice date | 2026-01-20 |
| Currency | USD |
| PO reference | *(leave blank)* |

**Lines:**

| item_code | description | qty | unit_price | line_total |
|-----------|-------------|-----|------------|------------|
| LAP-T14 | ThinkPad T14 laptops | 8 | 1500.00 | 12000.00 |

**Totals:** Subtotal 12000.00 | Tax 960.00 | **Total 12960.00**

---

### inv-003.pdf — Ambiguous PO (REVIEW)

**Purpose:** Two POs (PO-1003, PO-1004) score similarly → human review.

| Field | Value |
|-------|-------|
| Vendor name | Global Paper Co |
| Vendor tax ID | TAX-GPC-003 |
| Invoice number | GPC-5521 |
| Invoice date | 2026-01-18 |
| Currency | USD |
| PO reference | *(leave blank — critical)* |

**Lines:**

| item_code | description | qty | unit_price | line_total |
|-----------|-------------|-----|------------|------------|
| PAP-A4 | Copy paper A4 80gsm | 500 | 5.00 | 2500.00 |

**Totals:** Subtotal 2500.00 | Tax 200.00 | **Total 2700.00**

> Do **not** print PO-1003 or PO-1004 on the invoice — ambiguity requires no explicit PO number.

---

### inv-004.pdf — Split Invoice (APPROVE)

**Purpose:** Second invoice against a partial PO (PO-1005).

| Field | Value |
|-------|-------|
| Vendor name | BuildRight Construction |
| Vendor tax ID | TAX-BRC-004 |
| Invoice number | BR-2026-104 |
| Invoice date | 2026-02-01 |
| Currency | USD |
| PO reference | PO-1005 |

**Lines:**

| item_code | description | qty | unit_price | line_total |
|-----------|-------------|-----|------------|------------|
| STL-A | Steel beams grade A | **30** | 500.00 | 15000.00 |

**Totals:** Subtotal 15000.00 | Tax 1200.00 | **Total 16200.00**

> Quantity 30 = remaining_qty on PO-1005. Total 16200 = remaining_value.

---

### inv-005.pdf — Over Tolerance (REVIEW)

**Purpose:** Invoice exceeds PO remaining balance beyond policy tolerance.

| Field | Value |
|-------|-------|
| Vendor name | CleanServe Facilities |
| Vendor tax ID | TAX-CSF-005 |
| Invoice number | CS-7788 |
| Invoice date | 2026-01-25 |
| Currency | USD |
| PO reference | PO-1006 |

**Lines:**

| item_code | description | qty | unit_price | line_total |
|-----------|-------------|-----|------------|------------|
| SVC-JAN | Monthly janitorial services | 1 | **5500.00** | 5500.00 |

**Totals:** Subtotal 5500.00 | Tax 440.00 | **Total 5940.00**

> PO-1006 remaining is **5400.00**. Over by 540 → exceeds 2% / $50 tolerance.

---

### inv-006.pdf — Duplicate (REJECT)

**Purpose:** Exact duplicate of a previously processed invoice.

**Content:** Identical to **inv-001.pdf** in every field:

| Field | Value |
|-------|-------|
| Vendor name | Acme Office Supplies Inc. |
| Vendor tax ID | TAX-ACME-001 |
| Invoice number | INV-2026-001 |
| Invoice date | 2026-01-15 |
| PO reference | PO-1001 |
| Total | 4860.00 |

**Test procedure:**

1. Upload and process **inv-001.pdf** first → APPROVE
2. Upload **inv-006.pdf** → REJECT (duplicate)

You can use the same PDF file with a different filename for inv-006.

---

### inv-007.pdf — Wrong Vendor (REVIEW)

**Purpose:** PO number points to a PO owned by a different vendor.

| Field | Value |
|-------|-------|
| Vendor name | **Wrong Vendor Corp** |
| Vendor tax ID | **TAX-WRONG-999** |
| Invoice number | WV-001 |
| Invoice date | 2026-01-22 |
| Currency | USD |
| PO reference | **PO-1007** *(belongs to DataStream Analytics V-007)* |

**Lines:**

| item_code | description | qty | unit_price | line_total |
|-----------|-------------|-----|------------|------------|
| MISC-01 | Misc supplies | 1 | 3000.00 | 3000.00 |

**Totals:** Subtotal 3000.00 | Tax 240.00 | **Total 3240.00**

> Vendor on invoice does not match PO-1007 vendor (V-007 DataStream Analytics).

---

### inv-008.pdf — Poor Scan (REVIEW)

**Purpose:** Low extraction confidence on material fields.

| Field | Value |
|-------|-------|
| Vendor name | ScanQuality Ltd |
| Vendor tax ID | TAX-SQ-008 |
| Invoice number | **SQ-???** *(smudged, unclear, or partially redacted)* |
| Invoice date | 2026-01-10 |
| Currency | USD |
| PO reference | PO-1008 |

**Lines:**

| item_code | description | qty | unit_price | line_total |
|-----------|-------------|-----|------------|------------|
| SVC-SCAN | Document scanning services | 1 | 800.00 | 800.00 |

**Totals:** Subtotal 800.00 | Tax 64.00 | **Total 864.00**

**PDF design tips for this scenario:**

- Make invoice number hard to read (blur, low contrast, handwriting-style)
- Keep vendor name and totals readable
- Optionally skew or compress the scan slightly

---

## 10. CSV Templates

### vendors.csv

```csv
vendor_id,legal_name,aliases,tax_id,currency,status
V-001,Acme Office Supplies Inc.,Acme Office|ACME,TAX-ACME-001,USD,active
V-002,TechPro Solutions LLC,TechPro|Tech Pro Solutions,TAX-TECH-002,USD,active
V-003,Global Paper Co,GPC|Global Paper Company,TAX-GPC-003,USD,active
V-004,BuildRight Construction,BuildRight,TAX-BRC-004,USD,active
V-005,CleanServe Facilities,CleanServe,TAX-CSF-005,USD,active
V-006,EuroSupply GmbH,Euro Supply,TAX-EURO-006,EUR,active
V-007,DataStream Analytics,DataStream,TAX-DS-007,USD,active
V-008,ScanQuality Ltd,Scan Quality,TAX-SQ-008,USD,active
V-009,Metro Logistics Inc.,Metro Log,TAX-ML-009,USD,active
V-010,SecureNet Systems,SecureNet,TAX-SN-010,USD,active
```

> Use `|` as alias separator if loading via custom script.

### purchase_orders.csv

```csv
po_id,vendor_id,currency,status,issue_date,total_value,remaining_value
PO-1001,V-001,USD,open,2026-01-01,4860.00,4860.00
PO-1002,V-002,USD,open,2026-01-05,12960.00,12960.00
PO-1003,V-003,USD,open,2026-01-10,2700.00,2700.00
PO-1004,V-003,USD,open,2026-01-12,2700.00,2700.00
PO-1005,V-004,USD,partial,2025-12-01,32400.00,16200.00
PO-1006,V-005,USD,open,2026-01-08,5400.00,5400.00
PO-1007,V-007,USD,open,2026-01-15,3240.00,3240.00
PO-1008,V-008,USD,open,2026-01-03,864.00,864.00
PO-1009,V-006,EUR,open,2026-01-06,5000.00,5000.00
PO-1010,V-009,USD,closed,2025-06-01,1500.00,0.00
PO-1011,V-010,USD,cancelled,2025-11-01,8000.00,8000.00
```

### po_lines.csv

```csv
line_id,po_id,item_code,description,ordered_qty,invoiced_qty,remaining_qty,unit_price,line_total
POL-1001-1,PO-1001,CHR-001,Office chairs ergonomic,10,0,10,450.00,4500.00
POL-1002-1,PO-1002,LAP-T14,ThinkPad T14 laptops,8,0,8,1500.00,12000.00
POL-1003-1,PO-1003,PAP-A4,Copy paper A4 80gsm,500,0,500,5.00,2500.00
POL-1004-1,PO-1004,PAP-A4,Copy paper A4 80gsm premium,500,0,500,5.00,2500.00
POL-1005-1,PO-1005,STL-A,Steel beams grade A,60,30,30,500.00,30000.00
POL-1006-1,PO-1006,SVC-JAN,Monthly janitorial services,1,0,1,5400.00,5400.00
POL-1007-1,PO-1007,MISC-01,Misc supplies,1,0,1,3000.00,3000.00
POL-1008-1,PO-1008,SVC-SCAN,Document scanning services,1,0,1,800.00,800.00
POL-1009-1,PO-1009,EUR-01,European office supplies,100,0,100,45.00,4500.00
POL-1010-1,PO-1010,LOG-01,Freight services,1,1,0,1500.00,1500.00
POL-1011-1,PO-1011,SEC-01,Security audit,1,0,1,8000.00,8000.00
```

### invoices.csv (reference — for PDF generation tracking)

This file is **not loaded into the DB**; use it as a worksheet when creating PDFs.

```csv
pdf_file,scenario,expected,vendor_name,tax_id,invoice_number,invoice_date,po_reference,item_code,qty,unit_price,subtotal,tax,total,matched_po
inv-001.pdf,happy_path,APPROVE,Acme Office Supplies Inc.,TAX-ACME-001,INV-2026-001,2026-01-15,PO-1001,CHR-001,10,450.00,4500.00,360.00,4860.00,PO-1001
inv-002.pdf,no_po_number,APPROVE,TechPro Solutions LLC,TAX-TECH-002,TP-8842,2026-01-20,,LAP-T14,8,1500.00,12000.00,960.00,12960.00,PO-1002
inv-003.pdf,ambiguous_po,REVIEW,Global Paper Co,TAX-GPC-003,GPC-5521,2026-01-18,,PAP-A4,500,5.00,2500.00,200.00,2700.00,PO-1003/PO-1004
inv-004.pdf,split_invoice,APPROVE,BuildRight Construction,TAX-BRC-004,BR-2026-104,2026-02-01,PO-1005,STL-A,30,500.00,15000.00,1200.00,16200.00,PO-1005
inv-005.pdf,over_tolerance,REVIEW,CleanServe Facilities,TAX-CSF-005,CS-7788,2026-01-25,PO-1006,SVC-JAN,1,5500.00,5500.00,440.00,5940.00,PO-1006
inv-006.pdf,duplicate,REJECT,Acme Office Supplies Inc.,TAX-ACME-001,INV-2026-001,2026-01-15,PO-1001,CHR-001,10,450.00,4500.00,360.00,4860.00,PO-1001
inv-007.pdf,wrong_vendor,REVIEW,Wrong Vendor Corp,TAX-WRONG-999,WV-001,2026-01-22,PO-1007,MISC-01,1,3000.00,3000.00,240.00,3240.00,PO-1007
inv-008.pdf,poor_scan,REVIEW,ScanQuality Ltd,TAX-SQ-008,SQ-???,2026-01-10,PO-1008,SVC-SCAN,1,800.00,800.00,64.00,864.00,PO-1008
```

---

## 11. JSON Templates

### Full reference data bundle

Save as `fixtures/reference_data.json`:

```json
{
  "vendors": [
    {"vendor_id": "V-001", "legal_name": "Acme Office Supplies Inc.", "aliases": ["Acme Office", "ACME"], "tax_id": "TAX-ACME-001", "currency": "USD", "status": "active"},
    {"vendor_id": "V-002", "legal_name": "TechPro Solutions LLC", "aliases": ["TechPro", "Tech Pro Solutions"], "tax_id": "TAX-TECH-002", "currency": "USD", "status": "active"},
    {"vendor_id": "V-003", "legal_name": "Global Paper Co", "aliases": ["GPC", "Global Paper Company"], "tax_id": "TAX-GPC-003", "currency": "USD", "status": "active"},
    {"vendor_id": "V-004", "legal_name": "BuildRight Construction", "aliases": ["BuildRight"], "tax_id": "TAX-BRC-004", "currency": "USD", "status": "active"},
    {"vendor_id": "V-005", "legal_name": "CleanServe Facilities", "aliases": ["CleanServe"], "tax_id": "TAX-CSF-005", "currency": "USD", "status": "active"},
    {"vendor_id": "V-006", "legal_name": "EuroSupply GmbH", "aliases": ["Euro Supply"], "tax_id": "TAX-EURO-006", "currency": "EUR", "status": "active"},
    {"vendor_id": "V-007", "legal_name": "DataStream Analytics", "aliases": ["DataStream"], "tax_id": "TAX-DS-007", "currency": "USD", "status": "active"},
    {"vendor_id": "V-008", "legal_name": "ScanQuality Ltd", "aliases": ["Scan Quality"], "tax_id": "TAX-SQ-008", "currency": "USD", "status": "active"},
    {"vendor_id": "V-009", "legal_name": "Metro Logistics Inc.", "aliases": ["Metro Log"], "tax_id": "TAX-ML-009", "currency": "USD", "status": "active"},
    {"vendor_id": "V-010", "legal_name": "SecureNet Systems", "aliases": ["SecureNet"], "tax_id": "TAX-SN-010", "currency": "USD", "status": "active"}
  ],
  "purchase_orders": [
    {
      "po_id": "PO-1001", "vendor_id": "V-001", "currency": "USD", "status": "open",
      "issue_date": "2026-01-01", "total_value": "4860.00", "remaining_value": "4860.00",
      "lines": [{"line_id": "POL-1001-1", "item_code": "CHR-001", "description": "Office chairs ergonomic", "ordered_qty": "10", "invoiced_qty": "0", "remaining_qty": "10", "unit_price": "450.00", "line_total": "4500.00"}]
    },
    {
      "po_id": "PO-1002", "vendor_id": "V-002", "currency": "USD", "status": "open",
      "issue_date": "2026-01-05", "total_value": "12960.00", "remaining_value": "12960.00",
      "lines": [{"line_id": "POL-1002-1", "item_code": "LAP-T14", "description": "ThinkPad T14 laptops", "ordered_qty": "8", "invoiced_qty": "0", "remaining_qty": "8", "unit_price": "1500.00", "line_total": "12000.00"}]
    },
    {
      "po_id": "PO-1003", "vendor_id": "V-003", "currency": "USD", "status": "open",
      "issue_date": "2026-01-10", "total_value": "2700.00", "remaining_value": "2700.00",
      "lines": [{"line_id": "POL-1003-1", "item_code": "PAP-A4", "description": "Copy paper A4 80gsm", "ordered_qty": "500", "invoiced_qty": "0", "remaining_qty": "500", "unit_price": "5.00", "line_total": "2500.00"}]
    },
    {
      "po_id": "PO-1004", "vendor_id": "V-003", "currency": "USD", "status": "open",
      "issue_date": "2026-01-12", "total_value": "2700.00", "remaining_value": "2700.00",
      "lines": [{"line_id": "POL-1004-1", "item_code": "PAP-A4", "description": "Copy paper A4 80gsm premium", "ordered_qty": "500", "invoiced_qty": "0", "remaining_qty": "500", "unit_price": "5.00", "line_total": "2500.00"}]
    },
    {
      "po_id": "PO-1005", "vendor_id": "V-004", "currency": "USD", "status": "partial",
      "issue_date": "2025-12-01", "total_value": "32400.00", "remaining_value": "16200.00",
      "lines": [{"line_id": "POL-1005-1", "item_code": "STL-A", "description": "Steel beams grade A", "ordered_qty": "60", "invoiced_qty": "30", "remaining_qty": "30", "unit_price": "500.00", "line_total": "30000.00"}]
    },
    {
      "po_id": "PO-1006", "vendor_id": "V-005", "currency": "USD", "status": "open",
      "issue_date": "2026-01-08", "total_value": "5400.00", "remaining_value": "5400.00",
      "lines": [{"line_id": "POL-1006-1", "item_code": "SVC-JAN", "description": "Monthly janitorial services", "ordered_qty": "1", "invoiced_qty": "0", "remaining_qty": "1", "unit_price": "5400.00", "line_total": "5400.00"}]
    },
    {
      "po_id": "PO-1007", "vendor_id": "V-007", "currency": "USD", "status": "open",
      "issue_date": "2026-01-15", "total_value": "3240.00", "remaining_value": "3240.00",
      "lines": [{"line_id": "POL-1007-1", "item_code": "MISC-01", "description": "Misc supplies", "ordered_qty": "1", "invoiced_qty": "0", "remaining_qty": "1", "unit_price": "3000.00", "line_total": "3000.00"}]
    },
    {
      "po_id": "PO-1008", "vendor_id": "V-008", "currency": "USD", "status": "open",
      "issue_date": "2026-01-03", "total_value": "864.00", "remaining_value": "864.00",
      "lines": [{"line_id": "POL-1008-1", "item_code": "SVC-SCAN", "description": "Document scanning services", "ordered_qty": "1", "invoiced_qty": "0", "remaining_qty": "1", "unit_price": "800.00", "line_total": "800.00"}]
    },
    {
      "po_id": "PO-1009", "vendor_id": "V-006", "currency": "EUR", "status": "open",
      "issue_date": "2026-01-06", "total_value": "5000.00", "remaining_value": "5000.00",
      "lines": [{"line_id": "POL-1009-1", "item_code": "EUR-01", "description": "European office supplies", "ordered_qty": "100", "invoiced_qty": "0", "remaining_qty": "100", "unit_price": "45.00", "line_total": "4500.00"}]
    },
    {
      "po_id": "PO-1010", "vendor_id": "V-009", "currency": "USD", "status": "closed",
      "issue_date": "2025-06-01", "total_value": "1500.00", "remaining_value": "0.00",
      "lines": [{"line_id": "POL-1010-1", "item_code": "LOG-01", "description": "Freight services", "ordered_qty": "1", "invoiced_qty": "1", "remaining_qty": "0", "unit_price": "1500.00", "line_total": "1500.00"}]
    },
    {
      "po_id": "PO-1011", "vendor_id": "V-010", "currency": "USD", "status": "cancelled",
      "issue_date": "2025-11-01", "total_value": "8000.00", "remaining_value": "8000.00",
      "lines": [{"line_id": "POL-1011-1", "item_code": "SEC-01", "description": "Security audit", "ordered_qty": "1", "invoiced_qty": "0", "remaining_qty": "1", "unit_price": "8000.00", "line_total": "8000.00"}]
    }
  ]
}
```

---

## 12. PDF Layout Guide

### Recommended structure

```
┌─────────────────────────────────────────────────────────────┐
│  [VENDOR LEGAL NAME]                          INVOICE       │
│  Tax ID: [tax_id]                                           │
│  Address line (optional)                                    │
│                                                             │
│  Invoice #: [invoice_number]     Date: [invoice_date]       │
│  Due Date: [due_date]            PO #: [po_reference]        │
│  Currency: [currency]                                       │
├─────────────────────────────────────────────────────────────┤
│  SKU       Description              Qty    Price    Total   │
│  [code]    [description]            [n]   [0.00]  [0.00]   │
│  ...                                                        │
├─────────────────────────────────────────────────────────────┤
│                                    Subtotal:    [subtotal]  │
│                                    Tax:         [tax]       │
│                                    TOTAL:       [total]     │
└─────────────────────────────────────────────────────────────┘
```

### PDF quality guidelines

| Quality | Use for | Tips |
|---------|---------|------|
| Clean digital PDF | inv-001, inv-002, inv-004 | Standard fonts, clear labels, high contrast |
| Standard scan | inv-003, inv-005, inv-007 | Slight texture OK; keep numbers readable |
| Poor scan | inv-008 | Blur invoice #; keep vendor and totals readable |

### File naming

Name PDFs exactly:

```
inv-001.pdf
inv-002.pdf
inv-003.pdf
inv-004.pdf
inv-005.pdf
inv-006.pdf
inv-007.pdf
inv-008.pdf
```

Store in: `fixtures/invoices/`

When using **mock extraction mode** (`USE_MOCK_EXTRACTION=true`), the filename triggers the correct scenario even if PDF content is minimal. For **live Gemini extraction**, the visible fields on the PDF must match this spec.

---

## 13. Pre-Generation Checklist

Before generating each invoice PDF, verify:

### Vendor & PO alignment

- [ ] Vendor on invoice exists in vendor master
- [ ] Tax ID on invoice matches vendor record (when applicable)
- [ ] PO reference (if used) exists and belongs to the same vendor
- [ ] Currency on invoice matches PO currency

### Arithmetic

- [ ] Each line: `quantity × unit_price = line_total` (±0.05)
- [ ] Invoice: `subtotal + tax = total` (±0.05)
- [ ] PO: `total_value` includes tax and matches expected invoice for APPROVE cases

### Quantities & balances

- [ ] Invoice qty ≤ PO `remaining_qty` for each matched line
- [ ] Invoice total ≤ PO `remaining_value` (+ tolerance) for APPROVE cases
- [ ] Partial PO has correct `invoiced_qty` and reduced `remaining_qty`

### Scenario-specific

- [ ] inv-003: **no PO number** on PDF
- [ ] inv-005: invoice total **deliberately exceeds** PO remaining
- [ ] inv-006: **identical** to inv-001; test only after inv-001 processed
- [ ] inv-007: vendor name **does not** match PO owner
- [ ] inv-008: invoice number **unclear** on PDF

---

## 14. Minimum Viable Dataset

If time is limited, create at least:

| Entity | Count | Must include |
|--------|-------|--------------|
| Vendors | 5 | 1 vendor with 2 similar POs (V-003) |
| POs | 8 | 1 partial, 1 closed, 1 cancelled |
| Invoice PDFs | 4 | inv-001, inv-003, inv-005, inv-006 |

This covers: approve, ambiguous review, tolerance review, and duplicate reject.

---

## 15. Loading Data Into the System

### Option A — Use built-in seed (already in repo)

Reference data is defined in:

```
apps/api/app/fixtures/seed.py
```

It loads automatically on API startup. To re-seed manually:

```bash
cd apps/api
python -m app.fixtures.seed
```

### Option B — Generate placeholder PDFs

```bash
cd apps/api
python scripts/generate_demo_pdfs.py
```

Output: `fixtures/invoices/inv-001.pdf` … `inv-008.pdf`

These are minimal placeholders. Replace with fully designed invoices for live VLM extraction.

### Option C — Custom CSV/JSON import

1. Create CSV files from [Section 10](#10-csv-templates)
2. Write an import script or update `seed.py` with your data
3. Restart the API

### Demo upload order

| Step | Upload | Expected |
|------|--------|----------|
| 1 | inv-001.pdf | APPROVE |
| 2 | inv-003.pdf | REVIEW |
| 3 | inv-005.pdf | REVIEW |
| 4 | inv-001 already done → inv-006.pdf | REJECT |

---

## Appendix: Historical Invoice (optional seed)

One previously processed invoice can exist for history/duplicate context:

| Field | Value |
|-------|-------|
| vendor_id | V-009 |
| vendor_name | Metro Logistics Inc. |
| invoice_number | ML-2025-442 |
| invoice_date | 2025-12-15 |
| total | 1296.00 |
| matched_po_id | PO-1010 |
| decision | APPROVE |

This does **not** conflict with the inv-001 / inv-006 duplicate scenario.

---

*Document version: 1.0 — aligned with Invoice Processing MVP seed data and acceptance test matrix.*
