# Parsers/parser_kempston_controls.py
# Parser for Kempston Controls Purchase Orders
# Works with unified process_purchase_orders.py
# Detects Kempston POs and emits standardized RPA output

import re
import os

def detect_kempston_controls(text: str) -> bool:
    """
    Triggers on:
      - 'Kempston Controls' header/logo
      - UK layout with 'Purchase Order No.' and 'Deliver To:'
    """
    t = (text or "").upper()
    return any([
        "KEMPSTON CONTROLS" in t,
        "PURCHASE ORDER NO." in t,
        "DELIVER TO:" in t
    ])

def parse_kempston_controls(text: str, source_file: str = "") -> list:
    """
    Extracts Kempston Controls PO data into the unified RPA schema.
    - 'Purchase Order' -> Purchase Order No. (e.g., PO387376)
    - 'Date on PO'     -> Date (e.g., 27/06/2025)
    - Per-line fields from the items table (#, Your Item Number, Req. Date, UOM, Qty, Unit Price, Ext. Price)
    - Description line follows each item row
    """
    source_name = os.path.basename(source_file)
    results = []

    # ---------- HEADER ----------
    po_number = _search(r"Purchase Order No\.\s*([A-Z0-9\/\-]+)", text)
    po_date   = _search(r"Date\s*([0-9]{2}/[0-9]{2}/[0-9]{4})", text)
    buyer     = _search(r"Please contact\s+([A-Za-z ]+)\s+on", text)  # e.g., Chloe Barnard
    delivery_address = _extract_delivery_address(text)
    currency  = "GBP"
    order_type = "Standard"

    # ---------- LINE ITEMS ----------
    # Columns: # | Your Item Number | Our Item Number | Manufacturer's Item | Req. Date | UOM | Qty | Unit Price | Ext. Price
    line_pat = re.compile(
        r"(?P<item>\d+)\s+"
        r"(?P<your>[A-Z0-9\-\.]+)\s+"
        r"(?P<our>[0-9 ]+\.[0-9]{2})\s+"
        r"(?P<mfg>[A-Z0-9\-\.]+)\s+"
        r"(?P<date>[0-9]{2}/[0-9]{2}/[0-9]{4})\s+"
        r"(?P<uom>[A-Z]+)\s+"
        r"(?P<qty>[0-9,]+)\s+"
        r"£?(?P<price>[\d\.,]+)\s+"
        r"£?(?P<total>[\d\.,]+)",
        re.IGNORECASE
    )

    for m in line_pat.finditer(text):
        # Description is on the next line after each row (often starts with ENTRELEC ... )
        desc = _extract_description_after(text, m.group(0)) or ""
        results.append({
            "Purchase Order": po_number or "",
            "Date on PO": po_date or "",
            "Source.Name": source_name,
            "Quantity": m.group("qty").replace(",", ""),   # keep plain number for RPA math
            "UoM": m.group("uom"),
            "Customer Product number": m.group("your"),
            "Description": desc,
            "TE Product No.": "",                          # not explicitly provided; left for standing data
            "Manufacturer's Part No.": m.group("mfg"),
            "Delivery Date": m.group("date"),
            "Currency": currency,
            "Net Price": m.group("price"),
            "Total Net Value": m.group("total"),
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

def _extract_delivery_address(text: str) -> str:
    """
    Grabs the 'Deliver To:' block (page 1/2).
    Example (from the PO): Distribution Centre, Unit D4 Baron Avenue, Earls Barton, Northamptonshire NN6 0JE, UNITED KINGDOM
    """
    m = re.search(r"Deliver To:\s*([A-Za-z0-9 ,\.\-\n]+?)(?:\n\s*#|\n\s*VAT|\n\s*Your Item Number|\Z)", text, re.IGNORECASE)
    return " ".join(m.group(1).split()) if m else ""

def _extract_description_after(text: str, anchor_row: str) -> str:
    """
    Takes the text of a matched row and returns the following line as description.
    """
    idx = text.find(anchor_row)
    if idx == -1:
        return ""
    tail = text[idx:].splitlines()
    if len(tail) >= 2:
        cand = tail[1].strip()
        # Clean common prefixes like 'ENTRELEC ...'
        return re.sub(r"\s{2,}", " ", cand)
    return ""


def detect_kempston_controls(text: str) -> bool:
    # Detects Kempston Controls purchase orders.
    # Adjust placeholders below for higher precision (company email domain, unique address line).
    t = (text or "").upper()
    return any([
        "KEMPSTON CONTROLS" in t,                 # company name
        "@KEMPSTONCONTROLS.COM" in t,          # brand email domain (replace with real domain)
        "ADDRESS OR CITY FRAGMENT" in t       # optional: unique address/city marker
    ])
