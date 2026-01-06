# Parsers/parser_netze_bw.py
# Parser for Netze BW GmbH Purchase Orders
# Works with unified process_purchase_orders.py
# Detects Netze BW GmbH or EnBW references

import re
import os

def detect_netze_bw(text: str) -> bool:
    """
    Detects Netze BW GmbH purchase orders.
    Triggers on:
      - 'Netze BW GmbH'
      - '@netze-bw.de' email domain
      - 'EnBW' group references
      - 'Bestellnummer' keyword
    """
    t = (text or "").upper()
    return any([
        "NETZE BW GMBH" in t,
        "@NETZE-BW.DE" in t,
        "ENBW" in t,
        "BESTELLNUMMER" in t
    ])


def parse_netze_bw(text: str, source_file: str = "") -> list:
    """
    Extracts Netze BW PO data into the unified RPA schema.
    Produces a list of line-item dicts matching TLA Distribution Order Entry Automation headers.
    """
    source_name = os.path.basename(source_file)
    results = []

    # --- HEADER EXTRACTION ---
    po_number = _search(r"Bestellnummer\s*(\d+)", text)
    po_date = _search(r"Datum\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})", text)
    buyer = _search(r"Name:\s*([A-Za-zÄÖÜäöüß.\s-]+)", text)
    delivery_address = _extract_delivery_address(text)
    delivery_date = _search(r"Liefertermin:\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})", text)
    currency = "EUR"

    # --- LINE ITEM EXTRACTION ---
    pattern = re.compile(
        r"(?P<item>\d{5})\s+(?P<mat>\d{12})\s+(?P<desc>[^\n]+)\n(?P<qty>[\d\.,]+)\s+(?P<uom>[A-Z]{1,3})\s+(?P<price>[\d\.,]+)\s+[A-Z]{1,3}\s+(?P<total>[\d\.,]+)",
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
            "Description": m.group("desc").strip(),
            "TE Product No.": _search(r"Ihre Materialnummer\s*([A-Za-z0-9/\(\)\-]+)", text),
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
            "Order Type": "",
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
    addr = re.search(r"Anlieferadresse:\s*(Netze BW GmbH[^\n]+(?:\n[^\n]+){0,3})", text)
    if addr:
        return addr.group(1).replace("\n", " ").strip()
    return ""


# Example usage
# if __name__ == "__main__":
#     with open("/mnt/data/Netze BW GmbH2.pdf.txt", "r", encoding="utf-8") as f:
#         text = f.read()
#     data = parse_netze_bw(text, source_file="Netze BW GmbH2.pdf")
#     import json
#     print(json.dumps(data, indent=2, ensure_ascii=False))


def detect_netze_bw(text: str) -> bool:
    # Detects Netze Bw purchase orders.
    # Adjust placeholders below for higher precision (company email domain, unique address line).
    t = (text or "").upper()
    return any([
        "NETZE BW" in t,                 # company name
        "@NETZEBW.COM" in t,          # brand email domain (replace with real domain)
        "ADDRESS OR CITY FRAGMENT" in t       # optional: unique address/city marker
    ])
