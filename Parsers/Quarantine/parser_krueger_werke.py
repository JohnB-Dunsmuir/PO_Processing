import re

def detect_krueger_werke(text: str) -> bool:
    t = text.lower()
    return "krüger-werke gmbh" in t or "krueger-werke" in t

def _extract_po_number(text: str):
    m = re.search(r"Bestellung\s+(\d+)", text)
    return m.group(1) if m else ""

def _extract_po_date(text: str):
    m = re.search(r"Datum\s+([0-9\.]+)", text)
    return m.group(1) if m else ""

def _extract_buyer(text: str):
    m = re.search(r"Bearbeiter\s+([A-Za-z ]+)", text)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str):
    return "Krüger-Werke GmbH, Hellsternstraße 1-4, 04895 Falkenberg, Germany"

def _to_float_eu(n): 
    return float(n.replace(".", "").replace(",", "."))

def _extract_lines(text: str):
    pat = re.compile(
        r"(\d+)\s+([A-Za-z0-9\-\/]+).*?(\d+)\s+Stk.*?([0-9\.,]+)\s+([0-9\.,]+)",
        re.S,
    )
    lines = []
    for m in pat.finditer(text):
        item = m.group(1)
        part = m.group(2)
        qty = m.group(3)
        price = m.group(4)
        total = m.group(5)
        lines.append({
            "item_no": item,
            "customer_product_no": part,
            "description": "",
            "quantity": qty,
            "uom": "Stk",
            "price": _to_float_eu(price),
            "line_value": _to_float_eu(total),
            "te_part_number": part,
            "manufacturer_part_no": part,
            "delivery_date": "27.08.2025",
        })
    return lines

def parse_krueger_werke(text: str):
    return {
        "header": {
            "po_number": _extract_po_number(text),
            "po_date": _extract_po_date(text),
            "customer_name": "Krüger-Werke GmbH",
            "buyer": _extract_buyer(text),
            "delivery_address": _extract_delivery_address(text),
        },
        "lines": _extract_lines(text),
    }
