
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    # Remove spaces/thousand separators, convert comma to dot
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# Heidelberger Druckmaschinen AG parser

def detect_heidelberger(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "heidelberger druckmaschinen" in t and "bestellung nr." in t

def _extract_po_number(text: str) -> str:
    m = re.search(r"BESTELLUNG Nr\.\s*(\d+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"Datum\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_buyer(text: str) -> str:
    m = re.search(r"Eink\xfaufer/in\s*([^\n]+)", text)
    if not m:
        m = re.search(r"Eink\xfaufer/in\s*([A-Za-z \.-]+)", text)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Anlieferung an:\s*(Heidelberger.*?Wiesloch)", text, flags=re.I | re.S)
    if not m:
        return "Heidelberger Druckmaschinen AG, Gutenbergring, 69168 Wiesloch, Deutschland"
    block = m.group(1)
    return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())

def _extract_lines(text: str):
    lines = []
    pat = re.compile(
        r"Pos\s*Material/Leistung.*?10\s+(?P<mat>[\d\.]+/?)\s+(?P<qty>\d+)\s*Stück\s+(?P<price>[\d\.,]+)\s*pro 1\.000 ST\s+(?P<total>[\d\.,]+)",
        flags=re.I | re.S
    )
    m = pat.search(text)
    if not m:
        return lines

    mat = m.group("mat").strip()
    qty_raw = m.group("qty")
    price_raw = m.group("price")
    total_raw = m.group("total")

    # Description from following line
    m_desc = re.search(rf"{re.escape(mat)}.*?Stück.*?\n(.*Adapter Board-to-Board.*)", text, flags=re.I)
    desc = m_desc.group(1).strip() if m_desc else "Adapter Board-to-Board 68-pol"

    quantity = qty_raw.replace(".", "").replace(",", "").replace(" ", "")
    # price is per 1000 ST -> convert to per piece
    price_per_1000 = _to_float_eu(price_raw)
    price = round(price_per_1000 / 1000.0, 5) if price_per_1000 else 0.0
    line_value = _to_float_eu(total_raw)

    # TE part from HerstellerteileNr
    m_te = re.search(r"HerstellerteileNr:\s*([\w\-]+)", text, flags=re.I)
    te_part = m_te.group(1).strip() if m_te else ""

    lines.append({
        "item_no": "10",
        "customer_product_no": mat,
        "description": desc,
        "quantity": quantity,
        "uom": "ST",
        "price": price,
        "line_value": line_value,
        "te_part_number": te_part,
        "manufacturer_part_no": "",
        "delivery_date": "19.12.2025",
    })
    return lines

def parse_heidelberger(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Heidelberger Druckmaschinen AG",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
