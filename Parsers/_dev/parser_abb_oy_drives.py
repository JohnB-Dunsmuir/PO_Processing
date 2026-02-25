
import re

def _to_float_eu(num: str) -> float:
    return float(num.replace(".", "").replace(",", ".")) if num else 0.0

# ABB Oy Drives parser

def detect_abb_oy_drives(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "abb oy, drives" in t or "abb oy, drives, abacus" in t or "po number/date" in t

def _extract_po_number(text: str) -> str:
    m = re.search(r"PO number/date\s*(\d+)\s*/", text, flags=re.I)
    if not m:
        m = re.search(r"PO number/date\s*(\d+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"PO number/date\s*\d+\s*/\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_buyer(text: str) -> str:
    m = re.search(r"Contact person/Telephone\s*([A-Za-zÄÖÜäöüß\. ]+)/", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Please deliver to:\s*(.*?)\s*Delivery date:", text, flags=re.I | re.S)
    if not m:
        return "ABB Oy, Drives, c/o ABB Logistic Centre Europe GmbH, Bräukerweg 132, 58708 Menden, Germany"
    block = m.group(1)
    return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())

def _extract_lines(text: str):
    lines = []

    m = re.search(
        r"00010\s+([A-Z0-9]+)\s+(.+?)\s+(\d+)\s+pieces\s+([\d\.,]+)\s+([\d\.,]+)",
        text,
        flags=re.I | re.S
    )
    if not m:
        return lines

    customer_mat = m.group(1).strip()
    desc = " ".join(m.group(2).split())
    qty_raw = m.group(3)
    price_raw = m.group(4)
    total_raw = m.group(5)

    m_te = re.search(r"Your material number\s*([A-Za-z0-9\-\.]+)", text, flags=re.I)
    te_part = m_te.group(1).strip() if m_te else ""

    m_del = re.search(r"Delivery date:\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    delivery_date = m_del.group(1).strip() if m_del else ""

    quantity = qty_raw.strip()
    uom = "PCS"

    price = _to_float_eu(price_raw)
    line_value = _to_float_eu(total_raw)

    lines.append({
        "item_no": "10",
        "customer_product_no": customer_mat,
        "description": desc,
        "quantity": quantity,
        "uom": uom,
        "price": price,
        "line_value": line_value,
        "te_part_number": te_part,
        "manufacturer_part_no": "",
        "delivery_date": delivery_date,
    })

    return lines

def parse_abb_oy_drives(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "ABB Oy, Drives",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
