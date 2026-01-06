# Parsers/parser_phoenix_contact.py
# Parser for Phoenix Contact GmbH & Co. KG Purchase Orders
# Works with unified process_purchase_orders.py
# Detects Phoenix Contact POs and emits standardized RPA output

import re
import os

def detect_phoenix_contact(text: str) -> bool:
    """
    Detects Phoenix Contact purchase orders.
    Triggers on:
      - 'Phoenix Contact GmbH' or '@phoenixcontact.com'
      - 'Bestellnr.' or 'Bestellung' (German for order)
    """
    t = (text or "").upper()
    return any([
        "PHOENIX CONTACT" in t,
        "@PHOENIXCONTACT.COM" in t,
        "BESTELLNR" in t,
        "BESTELLUNG" in t
    ])


def parse_phoenix_contact(text: str, source_file: str = "") -> list:
    """
    Extracts Phoenix Contact PO data into the unified RPA schema.
    Produces a list of line-item dicts matching TLA Distribution Order Entry Automation headers.
    """
    source_name = os.path.basename(source_file)
    results = []

    # --- HEADER EXTRACTION ---
    po_number = _search(r"Bestellnr\.\s*/\s*Datum\s*([0-9]{10})", text)
    po_date = _search(r"Bestellnr\.\s*/\s*Datum\s*[0-9]{10}\s*/\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})", text) or _search(r"Datum\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})", text)
    buyer = _search(r"Ansprechpartner\s*([A-Za-zÄÖÜäöüß\.\s-]+)", text)
    buyer = buyer.replace("Fr.", "").strip() if buyer else ""
    delivery_address = _extract_delivery_address(text)
    delivery_date = _search(r"Liefertermin\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})", text)
    currency = "EUR"

    # --- LINE ITEM EXTRACTION ---
    pattern = re.compile(
        r"(?P<item>\d{3})\s+(?P<qty>[\d\.,]+)\s+\w+\s+(?P<date>[0-9]{2}\.[0-9]{2}\.[0-9]{4})\s+(?P<price>[\d\.,]+)\s*/1\.000\s+(?P<total>[\d\.,]+)\s+"
        r"(?P<mat>\d{7})\s+(?P<desc>[A-Za-z0-9/\-\s]+)",
        re.MULTILINE
    )

    for m in pattern.finditer(text):
        # TE product extraction
        te_prod_pattern = rf"{m.group('mat')}[^\n]*TE Connectivity\s*:\s*([A-Za-z0-9\-\.;]+)"
        te_prod = _search(te_prod_pattern, text)
        results.append({
            "Purchase Order": po_number,
            "Date on PO": po_date,
            "Source.Name": source_name,
            "Quantity": m.group("qty"),
            "UoM": "Stück",
            "Customer Product number": m.group("mat"),
            "Description": m.group("desc").strip(),
            "TE Product No.": te_prod,
            "Manufacturer's Part No.": "",
            "Delivery Date": delivery_date,
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


def _search(pattern: str, text: str) -> str:
    """Utility regex search returning first group or empty string."""
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    """Extracts delivery address block."""
    addr = re.search(r"Anlieferadresse:\s*(Phoenix Contact[^\n]+(?:\n[^\n]+){0,3})", text)
    if addr:
        return addr.group(1).replace("\n", " ").strip()
    return ""


# Example usage
# if __name__ == "__main__":
#     with open("/mnt/data/Phoenix Contact GmbH & Co.KG.pdf.txt", "r", encoding="utf-8") as f:
#         text = f.read()
#     data = parse_phoenix_contact(text, source_file="Phoenix Contact GmbH & Co.KG.pdf")
#     import json
#     print(json.dumps(data, indent=2, ensure_ascii=False))


def detect_phoenix_contact(text: str) -> bool:
    # Detects Phoenix Contact purchase orders.
    # Adjust placeholders below for higher precision (company email domain, unique address line).
    t = (text or "").upper()
    return any([
        "PHOENIX CONTACT" in t,                 # company name
        "@PHOENIXCONTACT.COM" in t,          # brand email domain (replace with real domain)
        "ADDRESS OR CITY FRAGMENT" in t       # optional: unique address/city marker
    ])
