# Parsers/parser_stadtwerke_rostock.py
# Parser for Stadtwerke Rostock AG Purchase Orders
# Works with unified process_purchase_orders.py
# Detects Stadtwerke Rostock call-offs (Abruf aus Rahmenvereinbarung) and emits standardized RPA output

import re
import os

def detect_stadtwerke_rostock(text: str) -> bool:
    """
    Triggers on:
      - 'STADTWERKE ROSTOCK AG'
      - domain 'swrag.de'
      - German PO keywords: 'Bestellung', 'Abruf aus Rahmenvereinbarung'
    """
    t = (text or "").upper()
    return any([
        "STADTWERKE ROSTOCK AG" in t,
        "SWRAG.DE" in t,
        "BESTELLUNG" in t,
        "ABRUF AUS RAHMENVEREINBARUNG" in t
    ])


def parse_stadtwerke_rostock(text: str, source_file: str = "") -> list:
    """
    Extracts Stadtwerke Rostock AG call-off PO data into the unified RPA schema.
    Returns a list of line-item dicts matching 'TLA Distribution Order Entry Automation' headers.
    """
    source_name = os.path.basename(source_file)
    results = []

    # ----- HEADER FIELDS -----
    rv = _search(r"Abruf aus Rahmenvereinbarung:\s*(RV\s*\d+)", text)        # e.g., RV 250009
    ab = _search(r"Abrufnummer:\s*([A-Z]{2}\s*\d+)", text)                    # e.g., AB 254010126
    po_number = " / ".join([v for v in [rv, ab] if v]).strip()

    po_date = _search(r"Datum:\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4})", text)       # 27.06.2025
    buyer_last = _search(r"Bearbeiter:\s*([A-Za-zÄÖÜäöüß\-]+)", text)         # Ruwolt
    buyer_mail = _search(r"E-Mail:\s*([A-Za-z0-9\.\-_]+)@swrag\.de", text)    # Heiko.Ruwolt
    buyer = ""
    if buyer_mail:
        buyer = buyer_mail.replace(".", " ").title()
    elif buyer_last:
        buyer = buyer_last

    # Delivery address: use company postal/street block on the page
    delivery_address = _extract_delivery_address(text)

    # ----- LINE ITEMS -----
    # Table columns (from the document):
    # <Material>  <Beschreibung lines>  Menge  ME  EP  GP
    # 015765  CRSM 53/13-750/239 + 'Schrumpf-Reparaturmanschette ...' + qty 30,00  St  8,97  269,10
    line_pat = re.compile(
        r"(?P<mat>\d{5,6})\s+"
        r"(?P<te>CRSM[^\n]+)\s*"
        r"(?:\n(?P<desc>Schrumpf[^\n]+(?:\n[^\n]+){0,2}))?"
        r"\s*(?P<qty>\d{1,3}(?:[\.,]\d{2})?)\s+"
        r"(?P<uom>St|ST|Stück)\s+"
        r"(?P<price>[\d\.,]+)\s+"
        r"(?P<total>[\d\.,]+)",
        re.IGNORECASE
    )

    idx = 0
    for m in line_pat.finditer(text):
        idx += 1
        # Build description fields
        te_code = _clean(m.group("te"))
        long_desc = _clean((m.group("desc") or ""))
        # Prefer human description in "Description"; put TE code in "TE Product No."
        description = long_desc if long_desc else te_code

        results.append({
            "Purchase Order": po_number or "",
            "Date on PO": po_date or "",
            "Source.Name": source_name,
            "Quantity": _comma_qty(m.group("qty")),
            "UoM": "St",
            "Customer Product number": m.group("mat"),
            "Description": description,
            "TE Product No.": te_code,
            "Manufacturer's Part No.": "",
            "Delivery Date": "",
            "Currency": "EUR",
            "Net Price": m.group("price"),
            "Total Net Value": m.group("total"),
            "Item Number": str(idx).zfill(3),
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


# -------------------- helpers --------------------

def _search(pattern: str, text: str) -> str:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else ""

def _clean(s: str) -> str:
    return " ".join((s or "").split()).strip()

def _comma_qty(s: str) -> str:
    """Ensure quantities keep European comma style where applicable."""
    s = (s or "").strip()
    # normalize '30' -> '30,00' if EP/GP have 2 decimals; keep as-is otherwise
    if re.fullmatch(r"\d+", s):
        return f"{s},00"
    return s.replace(".", ",")

def _extract_delivery_address(text: str) -> str:
    """
    Pull a one-line receiver/delivery address from the footer/header.
    Preference: company address block, else post office box line.
    """
    # Street address line at top/footer
    m = re.search(r"Schmarler Damm\s*5\s*·\s*18069\s*Rostock", text, re.IGNORECASE)
    if m:
        return "Schmarler Damm 5, 18069 Rostock"
    # Postfach fallback
    m = re.search(r"Stadtwerke Rostock AG\s*·\s*PF\s*151133\s*·\s*18063\s*Rostock", text, re.IGNORECASE)
    if m:
        return "PF 151133, 18063 Rostock"
    # As a last resort, return the label 'Zentrallager Stadtwerke Rostock AG' if present
    m = re.search(r"Zentrallager\s*Stadtwerke\s*Rostock\s*AG", text, re.IGNORECASE)
    if m:
        return "Zentrallager Stadtwerke Rostock AG"
    return ""


def detect_stadtwerke_rostock(text: str) -> bool:
    # Detects Stadtwerke Rostock purchase orders.
    # Adjust placeholders below for higher precision (company email domain, unique address line).
    t = (text or "").upper()
    return any([
        "STADTWERKE ROSTOCK" in t,                 # company name
        "@STADTWERKEROSTOCK.COM" in t,          # brand email domain (replace with real domain)
        "ADDRESS OR CITY FRAGMENT" in t       # optional: unique address/city marker
    ])
