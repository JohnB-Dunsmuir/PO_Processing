
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    # Remove spaces/thousand separators, convert comma to dot
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# ELKO Verbindungstechnik GmbH parser

def detect_elko(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "elko verbindungstechnik gmbh" in t and "bestellung" in t

def _extract_po_number(text: str) -> str:
    m = re.search(r"Bestellung\s*(\d+)", text, flags=re.I)
    if not m:
        m = re.search(r"Bestell.-Nr\.:\s*(\d+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"Datum:\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_buyer(text: str) -> str:
    m = re.search(r"Sachbearbeiter:\s*([^\n]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str) -> str:
    # TE address appears at top; use that as delivery
    m = re.search(r"TE Connectivity Solutions GmbH\s*Muehlenstrasse 26\s*8200\s*Schaffhausen", text, flags=re.I)
    if m:
        return "TE Connectivity Solutions GmbH, Mühlenstrasse 26, 8200 Schaffhausen, Schweiz"
    return "TE Connectivity Solutions GmbH, Schaffhausen, Schweiz"

def _extract_lines(text: str):
    lines = []
    # Generic line parser for 5 positions
    pat = re.compile(
        r"(?P<pos>\d)\s+(?P<art>\S+)\s+(?P<custart>\S+)\s+(?P<qty>[\d\.,]+)\s+Stck\s+(?P<price>[\d\.,]+)\s+(?P<total>[\d\.,]+)",
        flags=re.I
    )
    for m in pat.finditer(text):
        pos = m.group("pos")
        art = m.group("art")
        cust = m.group("custart")
        qty_raw = m.group("qty")
        price_raw = m.group("price")
        total_raw = m.group("total")

        # Description is below in Bezeichnung lines; approximate by grabbing next lines around article
        desc = ""
        m_desc = re.search(art + r"\s+[^\n]*\n(.*)", text)
        if m_desc:
            desc = m_desc.group(1).strip()

        quantity = qty_raw.replace(".", "").replace(",", "").replace(" ", "")
        price = _to_float_eu(price_raw)
        line_value = _to_float_eu(total_raw)

        lines.append({
            "item_no": str(int(pos) * 10),
            "customer_product_no": art,
            "description": desc,
            "quantity": quantity,
            "uom": "STK",
            "price": price,
            "line_value": line_value,
            "te_part_number": cust,
            "manufacturer_part_no": "",
            "delivery_date": "",  # each line has Liefertermin, omitted for now
        })
    return lines

def parse_elko(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "ELKO Verbindungstechnik GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
