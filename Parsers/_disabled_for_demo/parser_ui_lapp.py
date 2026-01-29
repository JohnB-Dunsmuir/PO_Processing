
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    # Remove spaces and thousands separators, then convert comma to dot
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# U.I. Lapp GmbH parser

def detect_ui_lapp(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "u.i. lapp gmbh" in t and "purchase order" in t

def _extract_po_number(text: str) -> str:
    m = re.search(r"PO number/date\s*(\d+)\s*/", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"PO number/date\s*\d+\s*/\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_buyer(text: str) -> str:
    m = re.search(r"Contact person / Telephone / Fax\s*([A-Za-z \.-]+)\s*/", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Consignee:\s*(.*?)\s*_{5,}", text, flags=re.I | re.S)
    if not m:
        return "U.I. Lapp GmbH, Schulze-Delitzsch-Str. 25, 70565 Stuttgart, Germany"
    block = m.group(1)
    return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())

def _extract_lines(text: str):
    lines = []
    m = re.search(
        r"Item Material Description\s*Order qty\. Price per unit Net value\s*_{5,}(.*)Total net value",
        text,
        flags=re.I | re.S,
    )
    if not m:
        return lines
    block = m.group(1)

    # Single line in this format
    pat = re.compile(
        r"(?P<item>\d+)\s+(?P<mat>\S+)\s+(?P<desc>.+?)\s+(?P<qty>[\d\.,]+)\s+piece\s+(?P<price>[\d\.,]+)\s*/100 PC\s+(?P<total>[\d\.,]+)",
        flags=re.I | re.S,
    )
    for m2 in pat.finditer(block):
        item = m2.group("item")
        mat = m2.group("mat")
        desc = " ".join(m2.group("desc").split())
        qty_raw = m2.group("qty")
        price_raw = m2.group("price")
        total_raw = m2.group("total")

        # quantity: 3.000 -> "3000"
        quantity = qty_raw.replace(".", "").replace(",", "").replace(" ", "")
        # price is per 100 PC -> convert to per piece
        price_per_100 = _to_float_eu(price_raw)
        price = round(price_per_100 / 100.0, 5) if price_per_100 else 0.0
        line_value = _to_float_eu(total_raw)

        # TE part from "Your material number"
        m_te = re.search(r"Your material number\s*([\d,\.]+)", text, flags=re.I)
        te_part = m_te.group(1).replace(",", ".").strip() if m_te else ""

        lines.append({
            "item_no": item,
            "customer_product_no": mat,
            "description": desc,
            "quantity": quantity,
            "uom": "PC",
            "price": price,
            "line_value": line_value,
            "te_part_number": te_part,
            "manufacturer_part_no": "",
            "delivery_date": "",
        })
    return lines

def parse_ui_lapp(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "U.I. Lapp GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
