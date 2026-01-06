# Parsers/parser_cable_services.py
# Cable Services Ltd Purchase Order Parser
# Handles English-language POs with optional field label variants
# Works with unified process_purchase_orders.py

import re
from datetime import datetime

def detect_cable_services(text: str) -> bool:
    """
    Detects Cable Services Ltd purchase orders.
    Triggers on:
      - 'Cable Services Ltd' in the header
      - 'Purchase Order' or 'Order Number'
    """
    t = (text or "").upper()
    return ("CABLE SERVICES" in t and "PURCHASE ORDER" in t) or ("CABLE SERVICES LTD" in t)


def parse_cable_services(text: str) -> dict:
    """
    Parses Cable Services Ltd POs into the standard schema.
    Expected fields:
      header: po_number, po_date, buyer, delivery_address, customer_name
      lines: position, material_number, description, quantity, unit_price, net_value
    """
    header = {}
    lines = []

    # --- HEADER EXTRACTION ---
    header["customer_name"] = "Cable Services Ltd"

    # PO number
    po_match = re.search(r"Purchase\s*Order\s*(?:No\.?|Number|#|:)\s*([A-Z0-9\-\/]+)", text, re.IGNORECASE)
    header["po_number"] = po_match.group(1).strip() if po_match else ""

    # Order date
    date_match = re.search(r"Order\s*Date\s*[:\-]?\s*(\d{1,2}[\/\.\-]\d{1,2}[\/\.\-]\d{2,4})", text, re.IGNORECASE)
    if date_match:
        raw = date_match.group(1).replace(".", "/").replace("-", "/")
        try:
            d, m, y = [int(x) for x in raw.split("/")]
            if y < 100: y += 2000
            header["po_date"] = datetime(y, m, d).strftime("%Y-%m-%d")
        except Exception:
            header["po_date"] = ""
    else:
        header["po_date"] = ""

    # Buyer / Contact
    buyer_match = re.search(r"(?:Buyer|Contact|Requested\s*By)\s*[:\-]\s*([^\n\r]+)", text, re.IGNORECASE)
    header["buyer"] = buyer_match.group(1).strip() if buyer_match else ""

    # Delivery Address
    delivery_match = re.search(r"Deliver\s*To\s*[:\-]?\s*([\s\S]{0,200}?)(?:\n{2,}|Terms|Qty)", text, re.IGNORECASE)
    header["delivery_address"] = " ".join(delivery_match.group(1).split()) if delivery_match else ""

    # --- LINE EXTRACTION ---
    # Typical structure:
    # 10  PartNo  Description  Qty  Unit Price / Price Each / Cost per Unit  Total / Amount
    line_pattern = re.compile(
        r"(?P<pos>\d{1,5})\s+"
        r"(?P<mat>[A-Za-z0-9\-\_\/\.]+)\s+"
        r"(?P<desc>[A-Za-z0-9 ,\.\-\(\)\/]+?)\s+"
        r"(?P<qty>\d+(?:\.\d+)?)\s+"
        r"(?:(?:Unit\s*Price|Price\s*Each|Cost\s*per\s*Unit)\s*)?"
        r"(?P<price>[\d,\.]+)\s+"
        r"(?:(?:Total|Amount)\s*)?"
        r"(?P<total>[\d,\.]+)",
        re.IGNORECASE
    )

    for m in line_pattern.finditer(text):
        lines.append({
            "position": m.group("pos").zfill(5),
            "material_number": m.group("mat").strip(),
            "description": m.group("desc").strip(),
            "quantity": float(m.group("qty").replace(",", "")),
            "unit_price": _to_float(m.group("price")),
            "net_value": _to_float(m.group("total")),
        })

    return {"header": header, "lines": lines}


def _to_float(val):
    if val is None:
        return 0.0
    s = str(val).strip()
    s = s.replace(",", "").replace(" ", "")
    try:
        return float(s)
    except Exception:
        return 0.0


def detect_cable_services(text: str) -> bool:
    # Detects Cable Services purchase orders.
    # Adjust placeholders below for higher precision (company email domain, unique address line).
    t = (text or "").upper()
    return any([
        "CABLE SERVICES" in t,                 # company name
        "@CABLESERVICES.COM" in t,          # brand email domain (replace with real domain)
        "ADDRESS OR CITY FRAGMENT" in t       # optional: unique address/city marker
    ])
