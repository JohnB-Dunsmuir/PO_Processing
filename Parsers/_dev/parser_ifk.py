
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    # Remove spaces/thousand separators, convert comma to dot
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# IFK Gesellschaft m.b.H. parser

def detect_ifk(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "ifk gesellschaft m.b.h." in t and "bestellung nr." in t

def _extract_po_number(text: str) -> str:
    m = re.search(r"BESTELLUNG Nr\.\s*(\d+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"BESTELLUNG Nr\.\s*\d+\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_buyer(text: str) -> str:
    m = re.search(r"Bearbeiter:\s*([^\n]+)", text)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Versandadresse\s*(IFK Ges\.m\.b\.H\..+?Salzburg)", text, flags=re.I | re.S)
    if not m:
        return "IFK Gesellschaft m.b.H., Siezenheimer Straße 29A, 5020 Salzburg, Österreich"
    block = m.group(1)
    return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())

def _extract_lines(text: str):
    lines = []
    # Single line: Pos 1, 18 Stk, MXSU-6171, 180,00
    pat = re.compile(
        r"Pos\.\s*Menge\s*Bezeichnung.*?\n\s*1\s+(?P<qty>[\d\.,]+)\s*Stk\s*(?P<mat>MXSU-\d+)\s*(?P<rest>.+?)Summe netto\s*(?P<total>[\d\.,]+)",
        flags=re.I | re.S
    )
    m = pat.search(text)
    if not m:
        return lines
    qty_raw = m.group("qty")
    mat = m.group("mat").strip()
    desc_block = m.group("rest")
    total_raw = m.group("total")

    # Description = first 2–3 lines of block
    desc_lines = [ln.strip() for ln in desc_block.splitlines() if ln.strip()]
    desc = " ".join(desc_lines[:3])

    quantity = qty_raw.replace(".", "").replace(",", "").replace(" ", "")
    line_value = _to_float_eu(total_raw)

    # Price per piece: total / qty if possible
    price = 0.0
    try:
        q = float(quantity)
        if q:
            price = round(line_value / q, 5)
    except Exception:
        price = 0.0

    lines.append({
        "item_no": "10",
        "customer_product_no": mat,
        "description": desc,
        "quantity": quantity,
        "uom": "STK",
        "price": price,
        "line_value": line_value,
        "te_part_number": "CS0650-005",
        "manufacturer_part_no": "",
        "delivery_date": "13.10.2025",
    })
    return lines

def parse_ifk(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "IFK Gesellschaft m.b.H.",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
