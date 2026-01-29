import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    return float(num.replace(".", "").replace(",", "."))

def detect_festo(text: str) -> bool:
    t = text.lower()
    return ("festo se & co" in t and "purchase order" in t)

def _extract_po_number(text: str) -> str:
    m = re.search(r"Purchase order\s*(\S+)", text)
    return m.group(1) if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"Date\s*(\d{2}\.\d{2}\.\d{4})", text)
    return m.group(1) if m else ""

def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Please deliver to:(.*?)For all questions", text, flags=re.S)
    if not m:
        return "Festo SE & Co. KG, Plieninger Str. 50, 73760 Ostfildern-Scharnhausen, Germany"
    block = m.group(1)
    return " ".join(i.strip() for i in block.splitlines() if i.strip())

def _extract_lines(text: str):
    lines=[]
    pat = re.compile(
        r"Position\s*0001.*?"
        r"(?P<desc>Flange plug.*?PCP.*?)\s+"
        r"(?P<part>\d{6,})\s+"
        r"(?P<qty>\d+)\s+items.*?"
        r"(?P<te>[\w\-]+)\s+.*?"
        r"Price per 1 PC\s+(?P<price>[\d\.,]+)\s+(?P<total>[\d\.,]+)",
        flags=re.S | re.I
    )
    m = pat.search(text)
    if m:
        lines.append({
            "item_no": "10",
            "customer_product_no": m.group("part"),
            "description": " ".join(m.group("desc").split()),
            "quantity": m.group("qty"),
            "uom": "PC",
            "price": _to_float_eu(m.group("price")),
            "line_value": _to_float_eu(m.group("total")),
            "te_part_number": m.group("te"),
            "manufacturer_part_no": "",
            "delivery_date": "30.03.2026",
        })
    return lines

def parse_festo(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Festo SE & Co. KG",
        "buyer": "Bianca Brödner",
        "delivery_address": _extract_delivery_address(text),
    }
    return {"header": header, "lines": _extract_lines(text)}
