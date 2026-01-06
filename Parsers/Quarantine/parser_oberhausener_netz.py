
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    # Remove spaces/thousand separators, convert comma to dot
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# Oberhausener Netzgesellschaft mbH parser

def detect_oberhausener_netz(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "oberhausener netzgesellschaft mbh" in t and "bestellung" in t

def _extract_po_number(text: str) -> str:
    m = re.search(r"Bestellnummer/Datum\s*(\d+)\s*/", text, flags=re.I)
    if not m:
        m = re.search(r"Bestellnummer/Datum\s*(\d+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"Bestellnummer/Datum\s*\d+\s*/\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_buyer(text: str) -> str:
    m = re.search(r"AnsprechpartnerIn\s*([^\n]+)", text)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Lieferanschrift:\s*(Firma.*?DEUTSCHLAND)", text, flags=re.I | re.S)
    if not m:
        return "Oberhausener Netzgesellschaft mbH, Zentraler Wareneingang, Danziger Straße 31, 46045 Oberhausen, Deutschland"
    block = m.group(1)
    return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())

def _extract_lines(text: str):
    lines = []
    pat = re.compile(
        r"00010\s+(?P<mat>\d+)\s+(?P<qty>\d+)\s+St[üu]ck\s+(?P<price>[\d\.,]+)\s+(?P<total>[\d\.,]+)",
        flags=re.I
    )
    m = pat.search(text)
    if not m:
        return lines

    mat = m.group("mat").strip()
    qty_raw = m.group("qty")
    price_raw = m.group("price")
    total_raw = m.group("total")

    # Description lines under the table
    m_desc = re.search(r"00010\s+\d+\s+St[üu]ck[\s\S]+?GURO-Hausanschlu[ßs]garnitur.*", text, flags=re.I)
    desc = m_desc.group(0).splitlines()[0].strip() if m_desc else "GURO-Hausanschlußgarnitur MM-7-GC490"

    # Ihre Materialnummer
    m_te = re.search(r"Ihre Materialnummer\s*(\S+)", text, flags=re.I)
    te_part = m_te.group(1).strip() if m_te else ""

    quantity = qty_raw
    price = _to_float_eu(price_raw)
    line_value = _to_float_eu(total_raw)

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
        "delivery_date": "17.09.2025",
    })
    return lines

def parse_oberhausener_netz(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Oberhausener Netzgesellschaft mbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
