# Parsers/parser_ibh.py
# Parser for IBH Ingenieurbüro Harm Elektrotechnik GmbH Purchase Orders
# Works with unified process_purchase_orders.py
# Detects "IBH Elektrotechnik GmbH" or "ibh-elektrotechnik.de"

import re
from datetime import datetime
import os

def detect_ibh(text: str) -> bool:
    """
    Detects IBH Ingenieurbüro Harm POs.
    Triggers on:
      - 'IBH Elektrotechnik GmbH'
      - 'IBH Ingenieurbüro Harm'
      - '@ibh-elektrotechnik.de' email domain
      - 'Bestellung' (German for 'Order')
    """
    t = (text or "").upper()
    return any([
        "IBH ELEKTROTECHNIK GMBH" in t,
        "IBH INGENIEURBÜRO HARM" in t,
        "@IBH-ELEKTROTECHNIK.DE" in t,
        "BESTELLUNG" in t
    ])


def parse_ibh(text: str, source_file: str = "") -> list:
    """
    Extracts IBH purchase order data into the unified RPA schema.
    Produces a list of line-item dicts matching TLA Distribution Order Entry Automation headers.
    """
    source_name = os.path.basename(source_file)
    results = []

    # --- HEADER EXTRACTION ---
    po_match = re.search(r"Bestellung\s*Nr\s*(\d+)", text, re.IGNORECASE)
    po_date_match = re.search(r"vom\s*(\d{2}\.\d{2}\.\d{4})", text)
    buyer_match = re.search(r"Ansprechpartner\s+([A-ZÄÖÜa-zäöüß\s\-]+)", text)
    delivery_week_match = re.search(r"Wunschtermin:\s*(KW\s*\d+/\d{4})", text)
    buyer_name = buyer_match.group(1).strip() if buyer_match else ""

    # --- LINE ITEM EXTRACTION ---
    pattern = re.compile(
        r"(?P<pos>\d+)\s+(?P<mat>[\d\.]+)\s+(?P<qty>[\d\.,]+)\s+m\s+(?P<price>[\d,]+)\s+(?P<total>[\d,]+)",
        re.MULTILINE
    )

    for m in pattern.finditer(text):
        results.append({
            "Purchase Order": po_match.group(1) if po_match else "",
            "Date on PO": po_date_match.group(1) if po_date_match else "",
            "Source.Name": source_name,
            "Quantity": m.group("qty"),
            "UoM": "m",
            "Customer Product number": m.group("mat"),
            "Description": extract_description(text),
            "TE Product No.": "",
            "Manufacturer's Part No.": "",
            "Delivery Date": delivery_week_match.group(1) if delivery_week_match else "",
            "Currency": "EUR",
            "Net Price": m.group("price"),
            "Total Net Value": m.group("total"),
            "Item Number": m.group("pos"),
            "Distribution Channel": "",
            "Sales Org": "",
            "Bl": "",
            "Ship to ID": "",
            "Sold to Number": "",
            "Order Type": "",
            "Buyer": buyer_name,
            "Delivery Address": extract_delivery_address(text),
            "Relevant dummy part number": ""
        })

    return results


def extract_description(text: str) -> str:
    """Extracts the product description line."""
    desc = re.search(r"(RNF[^\n]+)", text)
    return desc.group(1).strip() if desc else ""


def extract_delivery_address(text: str) -> str:
    """Extracts buyer/delivery address block."""
    addr = re.search(r"TESOG GmbH[^\n]+(?:\n[^\n]+){0,2}", text)
    return addr.group(0).replace("\n", " ").strip() if addr else ""


# Example usage
# if __name__ == "__main__":
#     with open("/mnt/data/IBH Ingenieurbüro Harm.pdf.txt", "r", encoding="utf-8") as f:
#         text = f.read()
#     data = parse_ibh(text, source_file="IBH Ingenieurbüro Harm.pdf")
#     import json
#     print(json.dumps(data, indent=2, ensure_ascii=False))


def detect_ibh(text: str) -> bool:
    # Detects Ibh purchase orders.
    # Adjust placeholders below for higher precision (company email domain, unique address line).
    t = (text or "").upper()
    return any([
        "IBH" in t,                 # company name
        "@IBH.COM" in t,          # brand email domain (replace with real domain)
        "ADDRESS OR CITY FRAGMENT" in t       # optional: unique address/city marker
    ])
