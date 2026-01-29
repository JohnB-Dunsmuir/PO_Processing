
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# Gritec GmbH parser

def detect_gritec(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "gritec gmbh" in t and "bestellung" in t

def _extract_po_number(text: str) -> str:
    m = re.search(r"Bestellnummer / Datum\s*(\d+)\s*/", text, flags=re.I)
    if not m:
        m = re.search(r"Bestellnummer / Datum\s*(\d+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"Bestellnummer / Datum\s*\d+\s*/\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_buyer(text: str) -> str:
    m = re.search(r"Rückfragen bitte an\s*(.*)", text)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Lieferanschrift:\s*(Gritec GmbH.*?Waghäusel)", text, flags=re.I | re.S)
    if not m:
        return "Gritec GmbH, Schwetzinger Straße 19-21, 68753 Waghäusel, Deutschland"
    block = m.group(1)
    return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())

def _extract_lines(text: str):
    lines = []
    pat = re.compile(
        r"10\s+(?P<code>\d+)\s*RSES,12/20KV,TYPA/250A,25-95MM2\s*\n(?P<qty>\d+)\s+SET\s+(?P<price>[\d\.,]+)\s+(?P<total>[\d\.,]+)",
        flags=re.I
    )
    m = pat.search(text)
    if not m:
        return lines

    code = m.group("code").strip()
    qty_raw = m.group("qty")
    price_raw = m.group("price")
    total_raw = m.group("total")

    quantity = qty_raw.replace(".", "").replace(",", "").replace(" ", "")
    price = _to_float_eu(price_raw)
    line_value = _to_float_eu(total_raw)

    # TE type from Tyco Winkelstecker
    m_te = re.search(r"Tyco Winkelstecker\s*(\S+)", text, flags=re.I)
    te_part = m_te.group(1).strip() if m_te else ""

    lines.append({
        "item_no": "10",
        "customer_product_no": code,
        "description": "RSES,12/20KV,TYPA/250A,25-95MM2",
        "quantity": quantity,
        "uom": "SET",
        "price": price,
        "line_value": line_value,
        "te_part_number": te_part,
        "manufacturer_part_no": "",
        "delivery_date": "",  # Anliefertermin separate
    })
    return lines

def parse_gritec(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Gritec GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
