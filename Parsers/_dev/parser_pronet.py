# Parsers/parser_pronet.py
import re
from typing import Dict, List, Any, Optional

# ---------------------------
# DETECTION
# ---------------------------
def detect_pronet(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    # Strong signals: PRONET + OTTO-HAHN or RODGAU or "PRONET GMBH"
    return "PRONET" in t and ("OTTO-HAHN" in t or "RODGAU" in t or "PRONET GMBH" in t)


REQUIRED_HEADER_KEYS = ["po_number", "po_date", "customer_name", "buyer", "delivery_address"]


# ---------------------------
# HELPERS
# ---------------------------
def _nf(v: Optional[str]) -> str:
    if v is None:
        return "Not found"
    s = str(v).strip()
    return s if s else "Not found"


def _clean_ws(s: Optional[str]) -> str:
    if not s:
        return "Not found"
    return " ".join(s.split()).strip()


def _find_first(patterns, text: str, flags=0) -> Optional[str]:
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            # prefer captured group if present
            if m.lastindex:
                return m.group(m.lastindex).strip()
            return m.group(0).strip()
    return None


def _norm_qty(q: str) -> str:
    if not q:
        return "Not found"
    x = q.strip().replace(" ", "")
    if re.match(r"^\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?$", x):
        x = x.replace(".", "").replace(",", ".")
    else:
        x = x.replace(",", ".")
    return x


# ---------------------------
# LINES PARSING
# ---------------------------
def _parse_lines(text: str) -> List[Dict[str, Any]]:
    """
    Pronet pinned: TE part number is often NOT provided.
    We must at least extract the customer part number when present (e.g. 10.449.02).
    """
    rows: List[Dict[str, Any]] = []

    sane_uom = {"EA", "EACH", "PCS", "PC", "ST", "STK", "PCE", "SET", "M"}

    # Anchor region after "Pos" / "Position"
    region = text
    mstart = re.search(r"\b(Pos\.?|Position)\b", text, flags=re.IGNORECASE)
    if mstart:
        region = text[mstart.start():]

    # Typical: item + customer pn like 10.449.02 + desc + qty + uom
    pat = re.compile(
        r"^\s*(?P<item>\d{1,4})\s+"
        r"(?P<custpn>\d{1,3}\.\d{3}\.\d{2}|\d{1,3}\.\d{3}\.\d{2}\.\d{2}|[A-Z0-9][A-Z0-9\-/\.]{3,})\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<qty>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s+"
        r"(?P<uom>[A-Za-z]{1,6})\b.*$",
        re.IGNORECASE | re.MULTILINE,
    )

    seen = set()
    for m in pat.finditer(region):
        item = m.group("item").strip()
        custpn = (m.group("custpn") or "").strip()
        desc = (m.group("desc") or "").strip()
        qty_raw = (m.group("qty") or "").strip()
        uom = (m.group("uom") or "").upper().strip().rstrip(".")

        if uom and uom not in sane_uom:
            continue
        if not qty_raw:
            continue

        qty = _norm_qty(qty_raw)

        key = (item, custpn, qty, uom)
        if key in seen:
            continue
        seen.add(key)

        # Basic guard against header lines
        if re.search(r"(Seite|Page|Gesamt|Total|Bestellung|Bestellnummer|Lieferadresse|Rechnung)", desc, re.IGNORECASE):
            continue

        rows.append({
            "item_no": item,
            "customer_product_no": custpn if custpn else "Not found",
            "te_part_number": "Not found",
            "manufacturer_part_no": "Not found",
            "description": desc if desc else "Not found",
            "quantity": qty,
            "uom": uom if uom else "Not found",
        })

    if rows:
        return rows

    # Fallback: if we can find a customer pn anywhere (10.449.02 style), emit one minimal line
    mcpn = re.search(r"\b(\d{1,3}\.\d{3}\.\d{2})\b", text)
    if mcpn:
        return [{
            "item_no": "1",
            "customer_product_no": mcpn.group(1),
            "te_part_number": "Not found",
            "manufacturer_part_no": "Not found",
            "description": "Not found",
            "quantity": "1",
            "uom": "EA",
        }]

    # Final fallback: placeholder
    return [{
        "item_no": "1",
        "customer_product_no": "Not found",
        "te_part_number": "Not found",
        "manufacturer_part_no": "Not found",
        "description": "Not found",
        "quantity": "1",
        "uom": "EA",
    }]

def parse_pronet(text: str) -> Dict[str, Any]:
    header = {
        "po_number": "Not found",
        "po_date": "Not found",
        "customer_name": "Pronet GmbH",
        "buyer": "Not found",
        "delivery_address": "Not found",
    }

    if not text:
        return {"header": header, "lines": []}

    # PO number / date
    
po = _find_first([
    r"\bBestell(?:nummer|nr)\b\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]{3,})\b",
    r"\bOrder\s+No\.?\b\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]{3,})\b",
    r"\bPO\s*No\.?\b\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]{3,})\b",
    r"\b(B\d{5,})\b",
], text, flags=re.IGNORECASE)
    header["po_number"] = _nf(po)

    date = _find_first([
        r"\b(Datum|Date|Bestelldatum)\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})\b",
        r"\b(\d{2}[./-]\d{2}[./-]\d{4})\b",
        r"\b(\d{2}-[A-Z]{3}-\d{4})\b",
    ], text, flags=re.IGNORECASE)
    header["po_date"] = _nf(date)

    # Buyer: prefer "Ihr/e Ansprechpartner/in" or "Contact" or "FAO"
    buyer = _find_first([
        r"Ihr\/e Ansprechpartner\/in\s*[:\-]?\s*([^\n\r]+)",
        r"Ihr Ansprechpartner\s*[:\-]?\s*([^\n\r]+)",
        r"Contact\s*[:\-]?\s*([^\n\r]+)",
        r"FAO\s*[:\-]?\s*([^\n\r]+)",
    ], text, flags=re.IGNORECASE)
    header["buyer"] = _nf(_clean_ws(buyer) if buyer else None)

    # Delivery address: look for Deliver/Ship/TE Connectivity blocks
    delivery = _find_first([
        r"(?:Deliver(?:y)?\s*(?:To|Address)\s*[:\-]?\s*(.*?)(?:\n\s*\n|Buyer\b|Order\b|Bestellung\b))",
        r"(TE\s+Connectivity\s+Solutions\s+GmbH.*?CH-\s*\d{4}\s+\w+)",
        r"(Mühlenstrasse\s*\d+.*?CH-?\s*\d{4}\s+\w+)",
    ], text, flags=re.IGNORECASE | re.DOTALL)
    header["delivery_address"] = _nf(_clean_ws(delivery) if delivery else None)

    # Defensive: if delivery or buyer still missing, try localized patterns
    if header["buyer"] == "Not found":
        alt = _find_first([r"Ansprechpartner\s*[:\-]?\s*([^\n\r]+)"], text, flags=re.IGNORECASE)
        header["buyer"] = _nf(_clean_ws(alt) if alt else None)

    if header["delivery_address"] == "Not found":
        alt2 = _find_first([r"(Lieferadresse\s*[:\-]?\s*(.*?)(?:\n\s*\n|Rechnung|Invoice))"], text, flags=re.IGNORECASE | re.DOTALL)
        header["delivery_address"] = _nf(_clean_ws(alt2) if alt2 else None)

    # Lines
    lines = _parse_lines(text)

    # Ensure required keys are explicit "Not found" rather than None
    for k in REQUIRED_HEADER_KEYS:
        header[k] = _nf(header.get(k))

    return {"header": header, "lines": lines}
