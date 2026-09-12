"""Generate synthetic supplier contract PDFs -- the unstructured data source for
Phase 4/8's document intelligence story (AI_PARSE_DOCUMENT -> Cortex Search).

Every other Bronze source in this project is structured or semi-structured
(sensor JSON). Contracts are genuinely unstructured: free-form legal prose with
payment terms and SLA penalty clauses buried in paragraphs, not columns. That's
the point of building Cortex Search over them instead of a table.

Run: python data_generation/generate_supplier_contracts.py
Output: data_generation/supplier_contracts/SUP-00NN_contract.pdf (one per supplier)
"""

from __future__ import annotations

import random
from pathlib import Path

from fpdf import FPDF

OUTPUT_DIR = Path(__file__).parent / "supplier_contracts"

# A representative subset of the 50 suppliers in SILVER.suppliers -- enough to
# make the document-intelligence demo real without generating 50 PDFs.
SUPPLIER_IDS = [f"SUP-{i:04d}" for i in [1, 2, 3, 5, 7, 11, 15, 20, 26, 38, 41]]

PAYMENT_TERMS_OPTIONS = ["Net 30", "Net 45", "Net 60"]
PENALTY_OPTIONS = [
    ("2% of shipment value per day late, capped at 15%", True),
    ("1.5% of shipment value per week late, capped at 10%", True),
    ("None -- no late delivery penalty clause is included in this agreement", False),
    ("Flat fee of $500 per late shipment, no cap", True),
]

CARRIERS = ["FedEx Freight", "UPS Freight", "DHL Global"]


def _contract_text(supplier_id: str) -> dict:
    rng = random.Random(supplier_id)  # deterministic per supplier
    supplier_num = int(supplier_id.split("-")[1])
    supplier_name = f"Supplier {supplier_num:03d}"
    payment_terms = rng.choice(PAYMENT_TERMS_OPTIONS)
    penalty_clause, has_penalty = rng.choice(PENALTY_OPTIONS)
    effective_year = rng.choice([2024, 2025])
    term_years = rng.choice([1, 2, 3])

    return {
        "supplier_id": supplier_id,
        "supplier_name": supplier_name,
        "payment_terms": payment_terms,
        "penalty_clause": penalty_clause,
        "has_penalty": has_penalty,
        "effective_year": effective_year,
        "term_years": term_years,
    }


def _render_pdf(info: dict, path: Path) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "SUPPLY AGREEMENT", ln=True, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.ln(4)

    pdf.multi_cell(
        0, 6,
        f"This Supply Agreement (\"Agreement\") is entered into as of January 1, "
        f"{info['effective_year']}, by and between SUPPLY_CHAIN Manufacturing Inc. "
        f"(\"Buyer\") and {info['supplier_name']} (\"Supplier\", internal reference "
        f"{info['supplier_id']}).",
    )
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "1. Term", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0, 6,
        f"This Agreement shall remain in effect for {info['term_years']} year(s) "
        f"from the effective date, renewing automatically unless terminated by "
        f"either party with 90 days' written notice.",
    )
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "2. Payment Terms", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0, 6,
        f"Buyer shall remit payment to Supplier under terms of {info['payment_terms']} "
        f"from the date of invoice, subject to receipt of a valid Advance Ship "
        f"Notice (ASN) and matching purchase order.",
    )
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "3. Service Level Agreement (SLA)", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0, 6,
        "Supplier shall deliver all shipments to the designated plant dock no "
        "later than the planned receipt date communicated via the Supplier "
        "Portal. On-time delivery performance shall be measured at the point "
        "of physical receipt at the destination plant, not at carrier "
        "hand-off or promised ship date.",
    )
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "3.1 Late Delivery Penalty", ln=True)
    pdf.set_font("Helvetica", "", 11)
    if info["has_penalty"]:
        pdf.multi_cell(
            0, 6,
            f"In the event Supplier fails to meet the planned receipt date for "
            f"any shipment, Buyer shall be entitled to a penalty credit equal "
            f"to {info['penalty_clause']}. Penalty credits shall be applied "
            f"against Supplier's next invoice.",
        )
    else:
        pdf.multi_cell(0, 6, info["penalty_clause"] + ".")
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "4. Quality Requirements", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0, 6,
        "Supplier warrants that all delivered parts conform to the agreed "
        "specifications. Any quality defect event resulting in rejected "
        "material shall be reported within 5 business days and is subject "
        "to return, rework, or scrap disposition at Buyer's discretion.",
    )
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "5. Freight and Landed Cost", ln=True)
    pdf.set_font("Helvetica", "", 11)
    carrier = random.Random(info["supplier_id"] + "carrier").choice(CARRIERS)
    pdf.multi_cell(
        0, 6,
        f"Unless otherwise agreed, Supplier shall arrange freight via "
        f"{carrier} or an equivalent carrier. Freight cost, customs duty, "
        f"and handling fees are itemized separately from unit price on all "
        f"invoices and are the responsibility of Buyer per the landed-cost "
        f"provisions of the Master Purchasing Agreement.",
    )

    pdf.output(str(path))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for supplier_id in SUPPLIER_IDS:
        info = _contract_text(supplier_id)
        path = OUTPUT_DIR / f"{supplier_id}_contract.pdf"
        _render_pdf(info, path)
        print(f"Generated {path.name} -- payment_terms={info['payment_terms']!r}, "
              f"has_penalty={info['has_penalty']}")

    print(f"\n{len(SUPPLIER_IDS)} contract PDFs written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
