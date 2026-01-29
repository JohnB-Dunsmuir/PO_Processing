
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    # Remove spaces and thousands separators, then convert comma to dot
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# ABB AG Electrification (Germany) parser

def detect_abb_electrification(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "abb ag - electrification" in t and "purchase order" in t

def _extract_po_number(text: str) -> str:
    m = re.search(r"PO number date Page 1/3\s*(\d+)\s", text, flags=re.I)
    if not m:
        m = re.search(r"PO number date\s*(\d+)\s", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"PO number date.*?(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_buyer(text: str) -> str:
    m = re.search(r"Contact Person/ PG\s*([A-Za-zÄÖÜäöüß \.-]+)EPDS", text, flags=re.I)
    if not m:
        m = re.search(r"Contact Person/ PG\s*([A-Za-zÄÖÜäöüß \.-]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Please deliver to:\s*(.*?)\s*Invoicing Address:", text, flags=re.I | re.S)
    if not m:
        return "ABB AG – Electrification, Distribution Solutions, Oberhausener Strasse 33, 40472 Ratingen, Germany"
    block = m.group(1)
    return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())

def _extract_lines(text: str):
    lines = []
    pat = re.compile(
        r"00010\s+(?P<qty>[\d\.,]+)\s*m\s+(?P<price>[\d\.,]+)\s+(?P<total>[\d\.,]+)\s+\*\*\*.*?\nGCE0045320P0100\s*(?P<desc>.+?)\nYour material number\s*(?P<te>\S+)",
        flags=re.I | re.S,
    )
    m = pat.search(text)
    if not m:
        return lines

    qty_raw = m.group("qty")
    price_raw = m.group("price")
    total_raw = m.group("total")
    desc = " ".join(m.group("desc").split())
    te_part = m.group("te").strip()

    quantity = qty_raw.replace(".", "").replace(",", "").replace(" ", "")
    price = _to_float_eu(price_raw)
    line_value = _to_float_eu(total_raw)

    lines.append({
        "item_no": "10",
        "customer_product_no": "GCE0045320P0100",
        "description": desc,
        "quantity": quantity,
        "uom": "M",
        "price": price,
        "line_value": line_value,
        "te_part_number": te_part,
        "manufacturer_part_no": "",
        "delivery_date": "",  # Delivery date in header only
    })
    return lines

def parse_abb_electrification(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "ABB AG – Electrification",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
