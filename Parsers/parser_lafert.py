
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    # Remove spaces and thousands separators, then convert comma to dot
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# Lafert S.p.A. Italy parser

def detect_lafert(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "lafert s.p.a" in t and "ordine di acquisto" in t

def _extract_po_number(text: str) -> str:
    m = re.search(r"NUMERO DOCUMENTO\s*(\d+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"DATA\s*(\d{2}/\d{2}/\d{2})", text, flags=re.I)
    if not m:
        return ""
    d, mo, y = m.group(1).split("/")
    # assume 20xx
    return f"{d}.{mo}.20{y}"

def _extract_buyer(text: str) -> str:
    m = re.search(r"CONTATTO\s*\n?([A-Za-z ]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Destinazione\s*(.*?)\s*Spettabile", text, flags=re.I | re.S)
    if not m:
        return "Lafert SpA, Via Maiorana 2, 30020 Noventa di Piave, Italy"
    block = m.group(1)
    return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())

def _extract_lines(text: str):
    lines = []
    pat = re.compile(
        r"\n1\s+(?P<code1>\S+)\s+(?P<desc1>.+?)PC\s+(?P<qty1>[\d\.,]+)\s+(?P<price1>[\d\.,]+)\s+(?P<total1>[\d\.,]+)\s+(?P<date1>\d{2}/\d{2}/\d{2}).*?"
        r"\n2\s+(?P<code2>\S+)\s+(?P<desc2>.+?)PC\s+(?P<qty2>[\d\.,]+)\s+(?P<price2>[\d\.,]+)\s+(?P<total2>[\d\.,]+)\s+(?P<date2>\d{2}/\d{2}/\d{2})",
        flags=re.S
    )
    m = pat.search(text)
    if not m:
        return lines

    for idx in (1, 2):
        code = m.group(f"code{idx}")
        desc = " ".join(m.group(f"desc{idx}").split())
        qty_raw = m.group(f"qty{idx}")
        price_raw = m.group(f"price{idx}")
        total_raw = m.group(f"total{idx}")
        d = m.group(f"date{idx}")

        quantity = qty_raw.replace(".", "").replace(",", "").replace(" ", "")
        price = _to_float_eu(price_raw)
        line_value = _to_float_eu(total_raw)
        dd, mm, yy = d.split("/")
        delivery_date = f"{dd}.{mm}.20{yy}"

        lines.append({
            "item_no": str(idx * 10),
            "customer_product_no": code,
            "description": desc,
            "quantity": quantity,
            "uom": "PC",
            "price": price,
            "line_value": line_value,
            "te_part_number": "",
            "manufacturer_part_no": "",
            "delivery_date": delivery_date,
        })
    return lines

def parse_lafert(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Lafert S.p.A.",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
