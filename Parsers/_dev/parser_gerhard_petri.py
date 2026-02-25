
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    # Remove spaces as thousand separators, then convert comma to dot
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# UAB Gerhard Petri Vilnius parser

def detect_gerhard_petri(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "uab \"gerhard petri vilnius\"" in t or "pr-07-fr-03" in t

def _extract_po_number(text: str) -> str:
    m = re.search(r"ORDER Nr\.\s*(\d+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if not m:
        return ""
    d = m.group(1)
    y, mo, da = d.split("-")
    return f"{da}.{mo}.{y}"

def _extract_buyer(text: str) -> str:
    m = re.search(r"Vadybininkas\s+([A-Za-z ]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Adresas:Naugarduko 96,\s*(.+?)\s+Order To:", text, flags=re.S)
    if not m:
        return "Naugarduko 96, Vilnius, Lithuania"
    block = m.group(1)
    addr = "Naugarduko 96, " + " ".join(ln.strip() for ln in block.splitlines() if ln.strip())
    return addr

def _extract_lines(text: str):
    lines = []
    # Lines: idx code desc price qty unit sum date
    pattern = re.compile(
        r"^(?P<item>\d+)\s+(?P<code>\S+)\s+(?P<desc>\S.+?)\s+(?P<price>[\d\.,]+)\s+(?P<qty>\d+)\s+(?P<uom>\w+)\s+(?P<sum>[\d\.,]+)\s+(?P<date>\d{4}-\d{2}-\d{2})",
        flags=re.M
    )
    for m in pattern.finditer(text):
        code = m.group("code")
        desc = m.group("desc")
        price_raw = m.group("price")
        qty_raw = m.group("qty")
        uom = m.group("uom")
        sum_raw = m.group("sum")
        d = m.group("date")

        quantity = qty_raw
        price = _to_float_eu(price_raw)
        line_value = _to_float_eu(sum_raw)

        y, mo, da = d.split("-")
        delivery_date = f"{da}.{mo}.{y}"

        lines.append({
            "item_no": m.group("item"),
            "customer_product_no": code,
            "description": desc,
            "quantity": quantity,
            "uom": uom,
            "price": price,
            "line_value": line_value,
            "te_part_number": "",
            "manufacturer_part_no": "",
            "delivery_date": delivery_date,
        })
    return lines

def parse_gerhard_petri(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "UAB Gerhard Petri Vilnius",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
