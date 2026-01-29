
import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    # Remove spaces as thousand separators, then convert comma to dot
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))

# Yaskawa Europe GmbH parser

def detect_yaskawa(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "yaskawa europe gmbh" in t and "bestellnummer" in t

def _extract_po_number(text: str) -> str:
    m = re.search(r"Bestellnummer\s*(\d+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_po_date(text: str) -> str:
    m = re.search(r"Datum\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_buyer(text: str) -> str:
    m = re.search(r"Ansprechpartner\s*([A-Za-zÄÖÜäöüß \.-]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""

def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Liefern Sie an:\s*(.*?)\s*Zahlungsbedingungen", text, flags=re.I | re.S)
    if not m:
        return "ERNST SCHMITZ Logistics & Technical Service GmbH, Warehouse 4, Black & Decker-Strasse 40, 65510 Idstein, Germany"
    block = m.group(1)
    return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())

def _extract_lines(text: str):
    lines = []
    # Positions 00010, 00020, 00030...
    pattern = re.compile(
        r"Position\s*(?P<item>\d{5}).*?Material\s*(?P<mat>[A-Z0-9\-]+).*?Bezeichnung\s*(?P<desc>.+?)Bestellmenge\s*(?P<qty>\d+)\s*Einheit\s*(?P<uom>\w+).*?Nettopreis\s*([ ]*)(?P<price>[\d\.,']+)\s*Nettowert\s*(?P<total>[\d\.,']+)",
        flags=re.I | re.S
    )
    for m in pattern.finditer(text):
        item = m.group("item").lstrip("0")
        mat = m.group("mat").strip()
        desc = " ".join(m.group("desc").split())
        qty_raw = m.group("qty")
        uom = m.group("uom")
        price_raw = m.group("price").replace("'", "")
        total_raw = m.group("total").replace("'", "")

        quantity = qty_raw
        price = _to_float_eu(price_raw)
        line_value = _to_float_eu(total_raw)

        # Delivery date per position: look ahead for "Liefertermin" after this match
        post = text[m.end():]
        m_del = re.search(r"Liefertermin\s*(\d{2}\.\d{2}\.\d{4})", post)
        delivery_date = m_del.group(1) if m_del else ""

        # TE material from "Ihre Materialnr."
        pre = text[m.start():m.end()]
        m_te = re.search(r"Ihre Materialnr\.\s*([A-Za-z0-9\-]+)", pre, flags=re.I)
        te_part = m_te.group(1).strip() if m_te else ""

        lines.append({
            "item_no": item,
            "customer_product_no": mat,
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

def parse_yaskawa(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Yaskawa Europe GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
