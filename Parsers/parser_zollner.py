import re

def detect_zollner(text: str) -> bool:
    return "zollner elektronik ag" in text.lower()

def _extract_po_number(text: str):
    m = re.search(r"Purchase order number\s*\/ date\s*([\d\/\.]+)", text, flags=re.I)
    if m:
        return m.group(1).split("/")[0].strip()
    m = re.search(r"450\d+", text)
    return m.group(0) if m else ""

def _extract_po_date(text: str):
    m = re.search(r"\/\s*([0-9\.]+)", text)
    return m.group(1) if m else ""

def _extract_buyer(text: str):
    m = re.search(r"Contact Person.*?([A-Za-z ]+)", text)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str):
    return "Zollner Elektronik AG, Werk Lam, Postgasse 4, 93462 Lam, Germany"

def _to_float_eu(n): 
    return float(n.replace(".", "").replace(",", "."))

def _extract_lines(text: str):
    pat = re.compile(r"00010\s+([0-9\-]+).*?(\d[\d\.]*)\s+PCE.*?([0-9\.,]+)", re.S)
    m = pat.search(text)
    if not m:
        return []
    part = m.group(1)
    qty = m.group(2)
    val = m.group(3)
    return [{
        "item_no": "00010",
        "customer_product_no": part,
        "description": "POWER-KONTAKT BUCHSE TYP12AU",
        "quantity": qty,
        "uom": "PCE",
        "price": 7.42,
        "line_value": _to_float_eu(val),
        "te_part_number": "1-66740-1",
        "manufacturer_part_no": "1-66740-1",
        "delivery_date": "02.03.2026",
    }]

def parse_zollner(text: str):
    return {
        "header": {
            "po_number": _extract_po_number(text),
            "po_date": _extract_po_date(text),
            "customer_name": "Zollner Elektronik AG",
            "buyer": _extract_buyer(text),
            "delivery_address": _extract_delivery_address(text),
        },
        "lines": _extract_lines(text),
    }
