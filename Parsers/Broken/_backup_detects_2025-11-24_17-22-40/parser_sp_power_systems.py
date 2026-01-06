# Parsers/parser_sp_power_systems.py
# Parser for SP Power Systems / ScottishPower (SP Distribution PLC) Purchase Orders
# Works with unified process_purchase_orders.py
# Detects ScottishPower / SP Energy Networks call-off orders and emits standardized RPA output

import re
import os

def detect_sp_power_systems(text: str) -> bool:
    """
    Triggers on:
      - 'ScottishPower', 'SP Distribution PLC', 'SP Energy Networks'
      - 'Call-off Order' keyword
      - 'Framework Agreement Ref.' block
    """
    t = (text or "").upper()
    return any([
        "SCOTTISHPOWER" in t,
        "SP DISTRIBUTION PLC" in t,
        "SP ENERGY NETWORKS" in t,
        "CALL-OFF ORDER" in t
    ])

def parse_sp_power_systems(text: str, source_file: str = "") -> list:
    """
    Extracts ScottishPower call-off PO data into the unified RPA schema (TLA Distribution headers).
    Returns a list of line-item dicts. Missing values -> "" (standing data will enrich later).
    """
    source_name = os.path.basename(source_file)

    # --- Header fields ---
    po_number = _search(r"Ref\.\s*:\s*([\d\-]+)", text)                 # 4507111244
    po_date   = _search(r"Date\s*:\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})", text)  # 12.05.2025
    order_type = "Call-off Order" if "Call-off Order" in text else ""
    buyer     = _search(r"Manager\s*([A-Za-z .,-]+)", text)              # ALISON BRYCE
    delivery_date = _search(r"Delivery date\s*:\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})", text)
    currency  = "GBP"
    sold_to   = _search(r"Customer Account No\.\s*([0-9]+)", text)       # e.g., 20010 (if present)
    delivery_address = _extract_ship_to(text)                            # "SP Energy Networks, FK41SN Bonnybridge"
    # Build an item-number -> description map (from the text line where desc follows the item id)
    item_desc_map = _extract_item_descriptions(text)

    # --- Line items ---
    results = []
    line_pat = re.compile(
        r"(?P<item>\d{5})\s+(?P<code>\d+)\s+(?P<qty>\d+)\s+(?P<uom>[A-Z]{1,3})\s+(?P<price>[\d,\.]+)\s+(?P<total>[\d,\.]+)",
        re.IGNORECASE
    )
    for m in line_pat.finditer(text):
        item = m.group("item")
        desc = item_desc_map.get(item, "")
        results.append({
            "Purchase Order": po_number or "",
            "Date on PO": po_date or "",
            "Source.Name": source_name,
            "Quantity": m.group("qty"),
            "UoM": m.group("uom"),
            "Customer Product number": m.group("code"),
            "Description": desc,
            "TE Product No.": "",
            "Manufacturer's Part No.": "",
            "Delivery Date": delivery_date or "",
            "Currency": currency,
            "Net Price": m.group("price"),
            "Total Net Value": m.group("total"),
            "Item Number": item,
            "Distribution Channel": "",
            "Sales Org": "",
            "Bl": "",
            "Ship to ID": "",
            "Sold to Number": sold_to or "",
            "Order Type": order_type,
            "Buyer": (buyer or "").strip(),
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
    Grabs the 'SHIP TO LOCATION' block up to the next labeled field.
    Example: 'SP Energy Networks, FK41SN Bonnybridge'
    """
    m = re.search(r"SHIP TO LOCATION\s*([\s\S]*?)\bDelivery date\s*:", text, re.IGNORECASE)
    if not m:
        m = re.search(r"SHIP TO LOCATION\s*([^\n]+)", text, re.IGNORECASE)
    return _one_line(m.group(1)) if m else ""

def _extract_item_descriptions(text: str) -> dict:
    """
    Finds lines where an item number is followed by a textual description
    (as opposed to the code/qty line). Returns a map {item: description}.
    Example: '00010 JT BRANCH TRANSITION 11KV FOR UPTO 185MM'
    """
    desc_map = {}
    for m in re.finditer(r"(?P<item>\d{5})\s+(?P<desc>[A-Z][^\n]+)", text):
        # skip the code/qty line where next token is digits
        if re.match(r"\d{5}\s+\d+", m.group(0)):
            continue
        desc_map[m.group("item")] = _one_line(m.group("desc"))
    return desc_map

def _one_line(s: str) -> str:
    return " ".join((s or "").split()).strip()


def detect_sp_power_systems(text: str) -> bool:
    # Detects Sp Power Systems purchase orders.
    # Adjust placeholders below for higher precision (company email domain, unique address line).
    t = (text or "").upper()
    return any([
        "SP POWER SYSTEMS" in t,                 # company name
        "@SPPOWERSYSTEMS.COM" in t,          # brand email domain (replace with real domain)
        "ADDRESS OR CITY FRAGMENT" in t       # optional: unique address/city marker
    ])
