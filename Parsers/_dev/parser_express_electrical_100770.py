
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    # Remove spaces and thousands separators, then convert comma to dot
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# Common helpers for Express Electrical POs

def _extract_express_header(text: str):
    po_no = ""
    po_date = ""
    m_no = re.search(r"PO Number:\s*(\d+)", text, flags=re.I)
    if m_no:
        po_no = m_no.group(1).strip()
    m_dt = re.search(r"PO Date:\s*([0-9/]{10})", text, flags=re.I)
    if m_dt:
        # dd/mm/yyyy -> dd.mm.yyyy
        d, m, y = m_dt.group(1).split("/")
        po_date = f"{d}.{m}.{y}"
    m_buyer = re.search(r"Tel No:\s*[^\n]*", text)
    buyer = ""
    if m_buyer:
        buyer = "Express Electrical Buyer"
    m_del = re.search(r"Deliver To:\s*(Express Electrical.*?G81 1UY)", text, flags=re.I | re.S)
    delivery_address = ""
    if m_del:
        delivery_address = " ".join(ln.strip() for ln in m_del.group(1).splitlines() if ln.strip())
    else:
        delivery_address = "Express Electrical and Engineering Supplies Ltd, 37 Cable Depot Road, Clydebank, G81 1UY, UK"
    return po_no, po_date, buyer, delivery_address

def _extract_express_lines(text: str):
    lines = []
    # Generic row: product code, description, unit, quantity, price, value
    pat = re.compile(
        r"(?P<code>\S+)\s+(?P<desc>.+?)\s+(?P<unit>\w+)\s+(?P<qty>[\d\.,]+)\s+(?P<price>[\d\.,]+)\s+(?P<value>[\d\.,]+)\s+20\.00",
        flags=re.I
    )
    idx = 10
    for m in pat.finditer(text):
        code = m.group("code")
        desc = " ".join(m.group("desc").split())
        unit = m.group("unit")
        qty_raw = m.group("qty")
        price_raw = m.group("price")
        value_raw = m.group("value")

        quantity = qty_raw.replace(",", "").replace(".", "").replace(" ", "")
        price = _to_float_eu(price_raw)
        line_value = _to_float_eu(value_raw)

        lines.append({
            "item_no": str(idx),
            "customer_product_no": code,
            "description": desc,
            "quantity": quantity,
            "uom": unit,
            "price": price,
            "line_value": line_value,
            "te_part_number": "",
            "manufacturer_part_no": "",
            "delivery_date": "",
        })
        idx += 10
    return lines

def detect_express_electrical_100770(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "express electrical and engineering supplies" in t and "po number: 100770" in t

def parse_express_electrical_100770(text: str):
    po_no, po_date, buyer, delivery_address = _extract_express_header(text)
    header = {
        "po_number": po_no,
        "po_date": po_date,
        "customer_name": "Express Electrical and Engineering Supplies Ltd",
        "buyer": buyer,
        "delivery_address": delivery_address,
    }
    lines = _extract_express_lines(text)
    return {"header": header, "lines": lines}
