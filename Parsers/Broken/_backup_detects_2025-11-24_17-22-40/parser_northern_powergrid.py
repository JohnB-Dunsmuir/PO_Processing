# Parsers/parser_northern_powergrid.py
# Parser for Northern Powergrid Purchase Orders
# Works with unified process_purchase_orders.py
# Detects Northern Powergrid POs and emits standardized RPA output

import re
import os

def detect_northern_powergrid(text: str) -> bool:
    """
    Detects Northern Powergrid purchase orders.
    Triggers on:
      - 'Northern Powergrid' in the header/logo
      - 'Blanket Release' keyword
      - '@northernpowergrid.com' email domain
      - 'Order' followed by a number in the header
    """
    t = (text or "").upper()
    return any([
        "NORTHERN POWERGRID" in t,
        "BLANKET RELEASE" in t,
        "@NORTHERNPOWERGRID.COM" in t,
        "ORDER" in t and "POWERGRID" in t
    ])


def parse_northern_powergrid(text: str, source_file: str = "") -> list:
    """
    Extracts Northern Powergrid PO data into the unified RPA schema.
    Produces a list of line-item dicts matching TLA Distribution Order Entry Automation headers.
    """
    source_name = os.path.basename(source_file)
    results = []

    # --- HEADER EXTRACTION ---
    po_number = _search(r"Order\s*([0-9\-]+)", text)
    po_date = _search(r"Order Date\s*([0-9]{2}\-[A-Z]{3}\-[0-9]{4})", text)
    buyer = _search(r"Created By\s*([A-Za-z,\s]+)", text)
    order_type = _search(r"Type\s*([A-Za-z\s]+)", text)
    currency = "GBP"
    sold_to = _search(r"Customer Account No\.\s*([0-9]+)", text)
    delivery_address = _extract_shipto(text)
    description = _search(r"Termination[^\n]+", text)

    # --- LINE ITEM EXTRACTION ---
    pattern = re.compile(
        r"(?P<item>\d+)\s+(?P<mat>\d+)\s+Needed:\s*(?P<date>[0-9]{2}\-[A-Z]{3}\-[0-9]{4}\s*\d{2}:\d{2}:\d{2})\s+(?P<qty>\d+)\s+(?P<uom>[A-Z]+)\s+(?P<price>[\d\.,]+)\s+[A-Z]+\s+(?P<total>[\d\.,]+)",
        re.MULTILINE
    )

    for m in pattern.finditer(text):
        results.append({
            "Purchase Order": po_number,
            "Date on PO": po_date,
            "Source.Name": source_name,
            "Quantity": m.group("qty"),
            "UoM": m.group("uom"),
            "Customer Product number": m.group("mat"),
            "Description": description,
            "TE Product No.": "",
            "Manufacturer's Part No.": "",
            "Delivery Date": m.group("date"),
            "Currency": currency,
            "Net Price": m.group("price"),
            "Total Net Value": m.group("total"),
            "Item Number": m.group("item"),
            "Distribution Channel": "",
            "Sales Org": "",
            "Bl": "",
            "Ship to ID": "",
            "Sold to Number": sold_to,
            "Order Type": order_type,
            "Buyer": buyer,
            "Delivery Address": delivery_address,
            "Relevant dummy part number": ""
        })

    return results


def _search(pattern: str, text: str) -> str:
    """Utility regex search returning first group or empty string."""
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _extract_shipto(text: str) -> str:
    """Extracts 'Ship To' address block."""
    addr = re.search(r"Ship To:\s*([A-Za-z0-9 ,\.\-:\n]+?)Bill To:", text, re.IGNORECASE | re.DOTALL)
    if addr:
        return addr.group(1).replace("\n", " ").strip()
    return ""


# Example usage
# if __name__ == "__main__":
#     with open("/mnt/data/Northern Powergrid.pdf.txt", "r", encoding="utf-8") as f:
#         text = f.read()
#     data = parse_northern_powergrid(text, source_file="Northern Powergrid.pdf")
#     import json
#     print(json.dumps(data, indent=2, ensure_ascii=False))


def detect_northern_powergrid(text: str) -> bool:
    # Detects Northern Powergrid purchase orders.
    # Adjust placeholders below for higher precision (company email domain, unique address line).
    t = (text or "").upper()
    return any([
        "NORTHERN POWERGRID" in t,                 # company name
        "@NORTHERNPOWERGRID.COM" in t,          # brand email domain (replace with real domain)
        "ADDRESS OR CITY FRAGMENT" in t       # optional: unique address/city marker
    ])
