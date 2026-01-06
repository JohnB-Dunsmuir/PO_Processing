
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    # Remove spaces as thousand separators, then convert comma to dot
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# Stadtwerke Rostock AG parser

def detect_stadtwerke_rostock(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "stadtwerke rostock ag" in t and "abruf aus rahmenvereinbarung" in t

def _extract_po_number(text: str) -> str:
    # Abrufnummer acts as PO
    m = re.search(r"Abrufnummer:?\s*([A-Z0-9 ]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"Datum:\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_buyer(text: str) -> str:
    m = re.search(r"Bearbeiter:\s*([A-Za-z\. ]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str) -> str:
    # Use company header address
    m = re.search(r"Stadtwerke Rostock AG \xb7 PF 151133 \xb7 18063 Rostock", text)
    if m:
        return "Zentrallager Stadtwerke Rostock AG, PF 151133, 18063 Rostock, Germany"
    return "Zentrallager Stadtwerke Rostock AG, Rostock, Germany"

def _extract_lines(text: str):
    lines = []
    # Lines with: article number, description lines, qty, ME, EP, GP
    pattern = re.compile(
        r"(?P<mat>0\d{5})\s+Schrumpf-Reparaturmanschette.*?\n"
        r"CRSM.*?\n"
        r"Schrumpf-Reparaturmanschette 750 mm.*?\n"
        r"vor Schrumpfung:.*?\n"
        r"nach Schrumpfung:.*?\n"
        r"(?P<qty>\d+,\d{2})\s*(?P<uom>St)\s*(?P<price>[\d\.,]+)\s*(?P<total>[\d\.,]+)",
        flags=re.I
    )
    idx = 10
    for m in pattern.finditer(text):
        mat = m.group("mat").strip()
        qty_raw = m.group("qty")
        uom = m.group("uom")
        price_raw = m.group("price")
        total_raw = m.group("total")
        desc = "Schrumpf-Reparaturmanschette CRSM"

        quantity = qty_raw.split(",")[0]
        quantity = quantity.replace(".", "").replace(",", "").replace(" ", "")
        price = _to_float_eu(price_raw)
        line_value = _to_float_eu(total_raw)

        lines.append({
            "item_no": str(idx),
            "customer_product_no": mat,
            "description": desc,
            "quantity": quantity,
            "uom": uom,
            "price": price,
            "line_value": line_value,
            "te_part_number": "",
            "manufacturer_part_no": "",
            "delivery_date": "",
        })
        idx += 10

    return lines

def parse_stadtwerke_rostock(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Stadtwerke Rostock AG",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
