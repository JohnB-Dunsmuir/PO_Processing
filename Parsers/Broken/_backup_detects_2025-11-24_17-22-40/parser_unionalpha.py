# Parsers/parser_unionalpha.py
# Parser for Union Alpha S.p.A. Purchase Orders
# Works with unified process_purchase_orders.py
# Detects Union Alpha POs and emits standardized RPA output

import re
import os

def detect_unionalpha(text: str) -> bool:
    """
    Detects Union Alpha S.p.A. purchase orders.
    Triggers on:
      - 'UNION ALPHA SPA' or '@unionalpha.global'
      - Italian PO format ('ORDINE ACQUISTO')
      - 'Cod.Fiscale e Partita IVA' line
    """
    t = (text or "").upper()
    return any([
        "UNION ALPHA" in t,
        "ORDINE ACQUISTO" in t,
        "@UNIONALPHA.GLOBAL" in t,
        "PARTITA IVA" in t
    ])


def parse_unionalpha(text: str, source_file: str = "") -> list:
    """
    Extracts Union Alpha PO data into the unified RPA schema.
    Produces a list of line-item dicts matching TLA Distribution Order Entry Automation headers.
    """
    source_name = os.path.basename(source_file)
    results = []

    # --- HEADER EXTRACTION ---
    po_number = _search(r"NUMERO DOCUMENTO\s*([0-9]+)", text)
    po_date = _search(r"DATA DOCUMENTO\s*([0-9]{2}/[0-9]{2}/[0-9]{4}|[0-9]{2}\.[0-9]{2}\.[0-9]{4})", text)
    buyer = "Union Alpha S.p.A."
    currency = "EUR"
    delivery_date = _search(r"CONSEGNA\s*([0-9]{2}/[0-9]{2}/[0-9]{4}|[0-9]{2}\.[0-9]{2}\.[0-9]{4})", text)
    delivery_address = "Loc. Pianerie snc, 63087 Comunanza (AP), Italy"
    order_type = "Standard"

    # --- LINE ITEM EXTRACTION ---
    pattern = re.compile(
        r"(?P<code>[A-Z0-9\.\-]+)\s+(?P<vs_code>[A-Z0-9\.\-]+)\s+(?P<desc>CON[^\n]+)\s+(?P<uom>[A-Z]{1,3})\s+(?P<qty>[\d\.,]+)\s+(?P<price>[\d\.,]+)\s+(?P<date>[0-9]{2}/[0-9]{2}/[0-9]{4}|[0-9]{2}\.[0-9]{2}\.[0-9]{4})\s+(?P<total>[\d\.,]+)",
        re.IGNORECASE
    )

    for i, m in enumerate(pattern.finditer(text), start=1):
        results.append({
            "Purchase Order": po_number or "",
            "Date on PO": po_date or "",
            "Source.Name": source_name,
            "Quantity": m.group("qty"),
            "UoM": m.group("uom"),
            "Customer Product number": m.group("code"),
            "Description": _clean(m.group("desc")),
            "TE Product No.": m.group("vs_code"),
            "Manufacturer's Part No.": "",
            "Delivery Date": m.group("date") or delivery_date or "",
            "Currency": currency,
            "Net Price": m.group("price"),
            "Total Net Value": m.group("total"),
            "Item Number": str(i).zfill(3),
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

def _clean(s: str) -> str:
    return " ".join((s or "").split()).strip()


# Example usage
# if __name__ == "__main__":
#     with open("/mnt/data/UNION ALPHA S.p.A..pdf.txt", "r", encoding="utf-8") as f:
#         text = f.read()
#     data = parse_unionalpha(text, source_file="UNION ALPHA S.p.A..pdf")
#     import json
#     print(json.dumps(data, indent=2, ensure_ascii=False))


def detect_unionalpha(text: str) -> bool:
    # Detects Unionalpha purchase orders.
    # Adjust placeholders below for higher precision (company email domain, unique address line).
    t = (text or "").upper()
    return any([
        "UNIONALPHA" in t,                 # company name
        "@UNIONALPHA.COM" in t,          # brand email domain (replace with real domain)
        "ADDRESS OR CITY FRAGMENT" in t       # optional: unique address/city marker
    ])
