# Parsers/parser_uk_power_networks.py
# Parser for UK Power Networks (Operations) Ltd Purchase Orders
# Works with unified process_purchase_orders.py
# Detects UKPN purchase orders and emits standardized RPA output

import re
import os

def detect_uk_power_networks(text: str) -> bool:
    """
    Detects UK Power Networks purchase orders.
    Triggers on:
      - 'UK Power Networks' in header or logo
      - '@ukpowernetworks.co.uk' email domain
      - 'Purchase Order' or 'Order number' keywords
    """
    t = (text or "").upper()
    return any([
        "UK POWER NETWORKS" in t,
        "@UKPOWERNETWORKS.CO.UK" in t,
        "PURCHASE ORDER" in t,
        "ORDER NUMBER" in t
    ])


def parse_uk_power_networks(text: str, source_file: str = "") -> list:
    """
    Extracts UK Power Networks PO data into the unified RPA schema.
    Produces a list of line-item dicts matching TLA Distribution Order Entry Automation headers.
    """
    source_name = os.path.basename(source_file)
    results = []

    # --- HEADER EXTRACTION ---
    po_number = _search(r"Order number\s*([0-9]+)", text)
    po_date = _search(r"Date\s*([0-9]{2}/[0-9]{2}/[0-9]{4}|[0-9]{2}/[A-Z]{3}/[0-9]{4}|[0-9]{2}\.[0-9]{2}\.[0-9]{4}|[0-9]{2}\-[A-Z]{3}\-[0-9]{4})", text)
    contact = _search(r"Contact\s*/\s*Phone\s*([A-Za-z ]+)", text)
    buyer = contact or ""
    delivery_date = _search(r"Delivery date\s*([0-9]{2}/[0-9]{2}/[0-9]{4}|[0-9]{2}\-[A-Z]{3}\-[0-9]{4})", text)
    currency = "GBP"
    delivery_address = _extract_delivery_address(text)
    payment_terms = _search(r"Payment terms\s*(.+)", text)

    # --- LINE ITEM EXTRACTION ---
    pattern = re.compile(
        r"(?P<item>\d+)\s+(?P<mat>[A-Z0-9]+)\s+(?P<qty>[\d\.,]+)\s+(?P<uom>[A-Z]{2,4})\s+(?P<price>[\d\.,]+)\s+(?P<total>[\d\.,]+)",
        re.MULTILINE
    )

    for m in pattern.finditer(text):
        desc = _extract_description(text, m.group("mat"))
        results.append({
            "Purchase Order": po_number or "",
            "Date on PO": po_date or "",
            "Source.Name": source_name,
            "Quantity": m.group("qty"),
            "UoM": m.group("uom"),
            "Customer Product number": m.group("mat"),
            "Description": desc,
            "TE Product No.": "",
            "Manufacturer's Part No.": _search(r"Suppliers ref[:;]?\s*([A-Za-z0-9\-/]+)", text),
            "Delivery Date": delivery_date or "",
            "Currency": currency,
            "Net Price": m.group("price"),
            "Total Net Value": m.group("total"),
            "Item Number": m.group("item"),
            "Distribution Channel": "",
            "Sales Org": "",
            "Bl": "",
            "Ship to ID": "",
            "Sold to Number": "",
            "Order Type": "Standard",
            "Buyer": buyer,
            "Delivery Address": delivery_address,
            "Relevant dummy part number": ""
        })

    return results


# -------------------- helpers --------------------

def _search(pattern: str, text: str) -> str:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str) -> str:
    """Extracts delivery address block starting from 'Delivery address'."""
    m = re.search(r"Delivery address\s*([A-Za-z0-9,\.\-\s\n]+?)Page\s*1", text, re.IGNORECASE)
    if not m:
        m = re.search(r"Delivery address\s*([A-Za-z0-9,\.\-\s\n]+)", text, re.IGNORECASE)
    return m.group(1).replace("\n", " ").strip() if m else ""

def _extract_description(text: str, material: str) -> str:
    """Extracts the description for a given material code."""
    m = re.search(rf"{material}\s+[^\n]*\n([A-Z].+)", text)
    if m:
        desc = m.group(1).strip()
        # Stop at next 'Total' or new section
        desc = re.split(r"Total|GBP", desc)[0].strip()
        return desc
    return ""


# Example usage
# if __name__ == "__main__":
#     with open("/mnt/data/UK Power Networks.PDF.txt", "r", encoding="utf-8") as f:
#         text = f.read()
#     data = parse_uk_power_networks(text, source_file="UK Power Networks.PDF")
#     import json
#     print(json.dumps(data, indent=2, ensure_ascii=False))


def detect_uk_power_networks(text: str) -> bool:
    # Detects Uk Power Networks purchase orders.
    # Adjust placeholders below for higher precision (company email domain, unique address line).
    t = (text or "").upper()
    return any([
        "UK POWER NETWORKS" in t,                 # company name
        "@UKPOWERNETWORKS.COM" in t,          # brand email domain (replace with real domain)
        "ADDRESS OR CITY FRAGMENT" in t       # optional: unique address/city marker
    ])
