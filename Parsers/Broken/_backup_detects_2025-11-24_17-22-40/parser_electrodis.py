# Parsers/parser_electrodis.py
# Parser for Electrodis Regelec Ste Luce Purchase Orders
# Works with unified process_purchase_orders.py
# Detects Electrodis Nantes POs and emits standardized RPA output

import re
import os

def detect_electrodis(text: str) -> bool:
    """
    Triggers on:
      - 'ELECTRODIS' or 'Regelec Ste Luce'
      - French purchase order terms ('Commande', 'Offre', 'Total HT')
    """
    t = (text or "").upper()
    return any([
        "ELECTRODIS" in t,
        "STE LUCE" in t,
        "COMMANDE" in t,
        "TOTAL HT" in t
    ])


def parse_electrodis(text: str, source_file: str = "") -> list:
    """
    Extracts Electrodis PO data into the unified RPA schema.
    Returns a list of line-item dicts matching TLA Distribution Order Entry Automation headers.
    """
    source_name = os.path.basename(source_file)
    results = []

    # ---------- HEADER ----------
    po_number = _search(r"Commande\s*[:\s]*([0-9]+)", text)
    po_date   = _search(r"le\s*[:\s]*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    buyer     = _search(r"Contact\s*[:\s]*([A-Za-zÉÈéè\s\-]+)", text)
    delivery_address = _extract_delivery_address(text)
    currency  = "EUR"
    order_type = "Standard"

    # ---------- LINE ITEMS ----------
    # Table structure: Num | Quantité | Référence | Désignation | Prix HT | Délai | Échéance
    line_pat = re.compile(
        r"(?P<item>\d+)\s+"
        r"(?P<qty>[\d\.,]+)\s+"
        r"(?P<ref>[A-Z0-9]+)\s+[^\n]*?\s+"
        r"(?P<price>[\d\.,]+)\s+C\s+(?P<date>[0-9]{2}/[0-9]{2}/[0-9]{4})",
        re.IGNORECASE
    )

    for m in line_pat.finditer(text):
        desc = _extract_description_after(text, m.group("ref"))
        results.append({
            "Purchase Order": po_number or "",
            "Date on PO": po_date or "",
            "Source.Name": source_name,
            "Quantity": m.group("qty"),
            "UoM": "U",
            "Customer Product number": m.group("ref"),
            "Description": desc,
            "TE Product No.": "",
            "Manufacturer's Part No.": "",
            "Delivery Date": m.group("date"),
            "Currency": currency,
            "Net Price": m.group("price"),
            "Total Net Value": "",
            "Item Number": m.group("item"),
            "Distribution Channel": "",
            "Sales Org": "",
            "Bl": "",
            "Ship to ID": "",
            "Sold to Number": "",
            "Order Type": order_type,
            "Buyer": buyer or "",
            "Delivery Address": delivery_address,
            "Relevant dummy part number": ""
        })

    return results


# -------------------- helpers --------------------

def _search(pat: str, text: str) -> str:
    m = re.search(pat, text, re.IGNORECASE)
    return m.group(1).strip() if m else ""

def _extract_description_after(text: str, ref: str) -> str:
    """Finds the line immediately after the reference code as item description."""
    idx = text.find(ref)
    if idx == -1:
        return ""
    lines = text[idx:].splitlines()
    return lines[1].strip() if len(lines) > 1 else ""

def _extract_delivery_address(text: str) -> str:
    """
    Extracts Electrodis' shipping address block.
    Example: Parc d’activités de la Maison Neuve, 3 rue Louis Bréguet, 44980 Sainte Luce sur Loire, France
    """
    m = re.search(r"Parc d'activités de la maison neuve.*?Sainte Luce sur Loire", text, re.IGNORECASE | re.DOTALL)
    if m:
        block = m.group(0)
        # Clean up line breaks
        return " ".join(block.split())
    return "Parc d’activités de la Maison Neuve, 3 rue Louis Bréguet, 44980 Sainte Luce sur Loire, France"


def detect_electrodis(text: str) -> bool:
    # Detects Electrodis purchase orders.
    # Adjust placeholders below for higher precision (company email domain, unique address line).
    t = (text or "").upper()
    return any([
        "ELECTRODIS" in t,                 # company name
        "@ELECTRODIS.COM" in t,          # brand email domain (replace with real domain)
        "ADDRESS OR CITY FRAGMENT" in t       # optional: unique address/city marker
    ])
