
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# E.DIS Netz GmbH parser

def detect_edis_netz(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "e.dis netz gmbh" in t and "abrufbestellung" in t

def _extract_po_number(text: str) -> str:
    m = re.search(r"Bestellnummer\s*(\d+/\d+/\d+)", text, flags=re.I)
    if not m:
        m = re.search(r"Bestellnummer\s*(\d+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"(\d{2}\.\s*August\s*\d{4})", text)
    if not m:
        return ""
    # keep German long date as-is
    return m.group(1).replace(" ", "")

def _extract_buyer(text: str) -> str:
    m = re.search(r"Einkaufssachbearbeiter/in:\s*(.*)", text)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Lieferadresse\s*(.*?)\s*Mit freundlichem Gru", text, flags=re.I | re.S)
    if not m:
        return "Hagemann Logistik und Service GmbH, Lager E.DIS Netz GmbH, Tor 2, Kanalstr. 8, 16727 Velten, Deutschland"
    block = m.group(1)
    return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())

def _extract_lines(text: str):
    lines = []
    pat = re.compile(
        r"00010\s+(?P<mat>\d+)\s+(?P<desc>V-Muffe.+?)\n.*?Abrufbestellung.*?\n(?P<qty>\d+)\s*ST\s+(?P<price>[\d\.,]+)/ 1 ST\s+(?P<total>[\d\.,]+)",
        flags=re.I | re.S
    )
    m = pat.search(text)
    if not m:
        return lines

    mat = m.group("mat").strip()
    desc = " ".join(m.group("desc").split())
    qty_raw = m.group("qty")
    price_raw = m.group("price")
    total_raw = m.group("total")

    # supplier TE part from "Teilenummer Lieferant"
    m_te = re.search(r"Teilenummer Lieferant\s*(\S+)", text, flags=re.I)
    te_part = m_te.group(1).strip() if m_te else ""

    quantity = qty_raw.replace(".", "").replace(",", "").replace(" ", "")
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
        "delivery_date": "",  # header has Lieferdatum
    })
    return lines

def parse_edis_netz(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "E.DIS Netz GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
