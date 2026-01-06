# Parsers/parser_wolseley_uk.py
# Parser for Wolseley UK Limited Purchase Orders
# Works with unified process_purchase_orders.py
# Detects Wolseley POs and emits standardized RPA output

import re
import os

def detect_wolseley_uk(text: str) -> bool:
    """
    Detects Wolseley UK Limited purchase orders.
    Triggers on:
      - 'Wolseley UK Limited'
      - '@jointingtech-terms.co.uk'
      - 'Purchase Order' header
    """
    t = (text or "").upper()
    return any([
        "WOLSELEY UK LIMITED" in t,
        "@JOINTINGTECH-TERMS.CO.UK" in t,
        "PURCHASE ORDER" in t
    ])


def parse_wolseley_uk(text: str, source_file: str = "") -> list:
    """
    Extracts Wolseley UK Limited PO data into the unified RPA schema.
    Produces a list of line-item dicts matching TLA Distribution Order Entry Automation headers.
    """
    source_name = os.path.basename(source_file)
    results = []

    # --- HEADER EXTRACTION ---
    po_number = _search(r"Document Ref[:\s]*([A-Z0-9\/\-]+)", text)
    po_date = _search(r"Raised Date[:\s]*([0-9]{1,2}\s*[A-Za-z]{3}\s*[0-9]{4})", text)
    buyer = "Wolseley UK Limited"
    currency = "GBP"
    delivery_date = _search(r"Due Date[:\s]*([0-9]{1,2}\s*[A-Za-z]{3}\s*[0-9]{4})", text)
    delivery_address = _extract_delivery_address(text)
    order_type = "Standard"

    # --- LINE ITEM EXTRACTION ---
    pattern = re.compile(
        r"(?P<product>[A-Z0-9\/\-\(\)]+)\s+(?P<supplier>[A-Z0-9\/\-\(\)]+)\s+(?P<desc>[A-Z0-9 ,\-\(\)/]+)\s+(?P<qty>\d+)\s+£?(?P<price>[\d\.,]+)",
        re.IGNORECASE
    )

    for idx, m in enumerate(pattern.finditer(text), start=1):
        results.append({
            "Purchase Order": po_number or "",
            "Date on PO": po_date or "",
            "Source.Name": source_name,
            "Quantity": m.group("qty"),
            "UoM": "EA",
            "Customer Product number": m.group("product"),
            "Description": _clean(m.group("desc")),
            "TE Product No.": m.group("supplier"),
            "Manufacturer's Part No.": "",
            "Delivery Date": delivery_date or "",
            "Currency": currency,
            "Net Price": m.group("price"),
            "Total Net Value": "",  # No explicit line totals; RPA fills via standing data
            "Item Number": str(idx).zfill(3),
            "Distribution Channel": "",
            "Sales Org": "",
            "Bl": "",
            "Ship to ID": "",
            "Sold to Number": "",
            "Order Type": order_type,
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
    """Extracts delivery address block beginning with 'Deliveries To:'."""
    m = re.search(r"Deliveries To:\s*(?:[A-Z0-9]+\s*)?([A-Za-z0-9 ,\-\n]+?)Due Date", text, re.IGNORECASE)
    if m:
        return " ".join(m.group(1).split())
    return ""

def _clean(s: str) -> str:
    return " ".join((s or "").split()).strip()


# Example usage
# if __name__ == "__main__":
#     with open("/mnt/data/Wolseley UK Limited.pdf.txt", "r", encoding="utf-8") as f:
#         text = f.read()
#     data = parse_wolseley_uk(text, source_file="Wolseley UK Limited.pdf")
#     import json
#     print(json.dumps(data, indent=2, ensure_ascii=False))


def detect_wolseley_uk(text: str) -> bool:
    # Detects Wolseley Uk purchase orders.
    # Adjust placeholders below for higher precision (company email domain, unique address line).
    t = (text or "").upper()
    return any([
        "WOLSELEY UK" in t,                 # company name
        "@WOLSELEYUK.COM" in t,          # brand email domain (replace with real domain)
        "ADDRESS OR CITY FRAGMENT" in t       # optional: unique address/city marker
    ])
