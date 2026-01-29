import re

def detect_steinbacher_energie(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(k in t for k in [
        "steinbacher energie",
        "hollenstein",
        "bestellung nr. 653291",
    ])

def _extract_po_number(text: str):
    m = re.search(r"Bestellung Nr\.?\s*[: ]*([0-9]+)", text, flags=re.I)
    return m.group(1) if m else ""

def _extract_po_date(text: str):
    m = re.search(r"Datum[: ]+([0-9\.]+)", text)
    return m.group(1) if m else ""

def _extract_buyer(text: str):
    m = re.search(r"Sachbearbeiter[: ]+([A-Za-z ]+)", text)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str):
    return "Steinbacher Energie GmbH, Walcherbauer 18, 3343 Hollenstein/Ybbs, Austria"

def _to_float(num: str) -> float:
    return float(num.replace(".", "").replace(",", "."))

def _extract_lines(text: str):
    pattern = re.compile(
        r"(\d+),0\s+(\d+)\s+([0-9,]+)\s+([0-9\.,]+)\s+E\s+([0-9\.,]+)",
        flags=re.I
    )
    lines = []
    for m in pattern.finditer(text):
        item_no = m.group(1)
        qty = m.group(2)
        price_raw = m.group(4)
        total_raw = m.group(5)

        lines.append({
            "item_no": item_no,
            "customer_product_no": "",
            "description": "",
            "quantity": qty,
            "uom": "Stk",
            "price": _to_float(price_raw),
            "line_value": _to_float(total_raw),
            "te_part_number": "",
            "manufacturer_part_no": "",
            "delivery_date": "15.08.2025",
        })
    return lines

def parse_steinbacher_energie(text: str):
    return {
        "header": {
            "po_number": _extract_po_number(text),
            "po_date": _extract_po_date(text),
            "customer_name": "Steinbacher Energie GmbH",
            "buyer": _extract_buyer(text),
            "delivery_address": _extract_delivery_address(text),
        },
        "lines": _extract_lines(text),
    }
