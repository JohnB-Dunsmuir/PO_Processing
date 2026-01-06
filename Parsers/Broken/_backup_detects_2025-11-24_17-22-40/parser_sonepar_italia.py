# Parsers/parser_sonepar_italia.py
# Parser for Sonepar Italia S.p.A. Purchase Orders
# Works with unified process_purchase_orders.py
# Detects Sonepar Italia POs and emits standardized RPA output

import re
import os

def detect_sonepar_italia(text: str) -> bool:
    """
    Detects Sonepar Italia purchase orders.
    Triggers on:
      - 'Sonepar Italia' in header/ship-to
      - 'Ordine d'Acquisto' keyword
      - Italian UoM 'PZ' in item rows
    """
    t = (text or "").upper()
    return any([
        "SONEPAR ITALIA" in t,
        "ORDINE D'ACQUISTO" in t or "ORDINE D’ACQUISTO" in t,
        " RIF :" in t,  # present in footer box
        " UM " in t and " PZ " in t
    ])


def parse_sonepar_italia(text: str, source_file: str = "") -> list:
    """
    Extracts Sonepar Italia PO data into the unified RPA schema.
    Produces a list of line-item dicts matching TLA Distribution Order Entry Automation headers.
    All missing fields are returned as empty strings "" (standing data will fill later).
    """
    source_name = os.path.basename(source_file)
    results = []

    # --- HEADER FIELDS ---
    po_number = _search(r"Ordine d.?Acquisto N[°º]\s*:\s*(\d+)", text)
    po_date   = _search(r"del\s*:\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})", text)
    buyer     = _search(r"RIF\s*:\s*([^\n]+)", text)  # e.g., "GdS Italia"
    currency  = "EUR"

    delivery_address = _extract_ship_to(text)

    # --- LINE ITEMS ---
    # Structure:
    # 10 Vs. cod. art. : TYC1SET411012R0000 28 PZ 26.09.2025 7,32 x 1
    # CANALINA DI CABLAGGIO PVC 40X100 GRIGIA
    item_pattern = re.compile(
        r"(?P<item>\d{2})\s+Vs\.\s*cod\.\s*art\.\s*:\s*(?P<code>\S+)\s+"
        r"(?P<qty>\d+)\s+(?P<uom>[A-Z]{2})\s+(?P<date>\d{2}\.\d{2}\.\d{4})\s+"
        r"(?P<price>[\d\.,]+)\s*x\s*1\s*\n(?P<desc>[^\n]+)",
        re.IGNORECASE
    )

    for m in item_pattern.finditer(text):
        results.append({
            "Purchase Order": po_number or "",
            "Date on PO": po_date or "",
            "Source.Name": source_name,
            "Quantity": m.group("qty"),
            "UoM": m.group("uom"),
            "Customer Product number": m.group("code"),
            "Description": _clean(m.group("desc")),
            "TE Product No.": "",
            "Manufacturer's Part No.": "",
            "Delivery Date": m.group("date"),
            "Currency": currency,
            "Net Price": m.group("price"),
            "Total Net Value": "",  # not provided per line; keep blank for standing-data calc
            "Item Number": m.group("item"),
            "Distribution Channel": "",
            "Sales Org": "",
            "Bl": "",
            "Ship to ID": "",
            "Sold to Number": "",
            "Order Type": "Standard",
            "Buyer": buyer or "",
            "Delivery Address": delivery_address,
            "Relevant dummy part number": ""
        })

    return results


# -------------------- helpers --------------------

def _search(pattern: str, text: str) -> str:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else ""

def _extract_ship_to(text: str) -> str:
    """
    Captures the 'Spedire a:' block:
    SONEPAR ITALIA SpA - Padova Sede
    ME40 Ce.Di Padova
    RIVIERA MAESTRI DEL LAVORO 24
    35127 - PADOVA (PD)
    Italia
    """
    m = re.search(r"Spedire a:\s*([^\n]+(?:\n[^\n]+){1,6})\nRIF\s*:", text, re.IGNORECASE)
    if not m:
        # fallback: up to blank line
        m = re.search(r"Spedire a:\s*([^\n]+(?:\n[^\n]+){1,6})\n\s*\n", text, re.IGNORECASE)
    return m.group(1).replace("\n", " ").strip() if m else ""

def _clean(s: str) -> str:
    return " ".join((s or "").split()).strip()


def detect_sonepar_italia(text: str) -> bool:
    # Detects Sonepar Italia purchase orders.
    # Adjust placeholders below for higher precision (company email domain, unique address line).
    t = (text or "").upper()
    return any([
        "SONEPAR ITALIA" in t,                 # company name
        "@SONEPARITALIA.COM" in t,          # brand email domain (replace with real domain)
        "ADDRESS OR CITY FRAGMENT" in t       # optional: unique address/city marker
    ])
