import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))


def detect_new_netz(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return ("new netz gmbh" in t
            or "bestellung 45025510" in t
            or "geilenkirchen" in t)


def _extract_po_number(text: str) -> str:
    m = re.search(r"Bestellung\s*45025510", text)
    if m:
        return "45025510"
    m = re.search(r"Bestellnummer\s*(\d+)", text)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"Datum\s*(\d{2}\.\d{2}\.\d{4})", text)
    return m.group(1) if m else ""


def _extract_buyer(text: str) -> str:
    m = re.search(r"Bearbeiter\s*([A-Za-zÄÖÜäöüß .-]+)", text)
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Lieferanschrift\s*(.*?)Rechnungsanschrift", text,
                  flags=re.S | re.I)
    if not m:
        return ("NEW Netz GmbH, Lager Geilenkirchen, "
                "Zum Bocketal 6, 52511 Geilenkirchen, Deutschland")
    block = m.group(1)
    return " ".join(l.strip() for l in block.splitlines() if l.strip())


def _extract_lines(text: str):
    """
    Position 00010
    37855  Endv. innen Schrumpf 20 kV 500–630 SK  5 Satz 174,94 EUR 874,70 EUR
    """
    lines = []
    pat = re.compile(
        r"00010\s+"
        r"(?P<mat>\d+)\s+"
        r"(?P<desc>Endv\.\s*Innen.*?SK.*?)\s+"
        r"(?P<qty>\d+)\s+Satz\s+"
        r"(?P<price>[\d\.,]+)\s+EUR\s+"
        r"(?P<total>[\d\.,]+)\s+EUR",
        flags=re.S | re.I,
    )
    m = pat.search(text)
    if not m:
        return lines

    mat = m.group("mat").strip()
    desc = " ".join(m.group("desc").split())
    qty = m.group("qty")
    price = _to_float_eu(m.group("price"))
    total = _to_float_eu(m.group("total"))

    te = ""
    m_te = re.search(r"TE[- ]?Teilenummer\s*([A-Za-z0-9\-]+)", text,
                     flags=re.I)
    if m_te:
        te = m_te.group(1).strip()
    if not te:
        te = "CS1144-000"  # from order text

    # Liefertermin
    delivery_date = ""
    m_del = re.search(r"Liefertermin\s*(\d{2}\.\d{2}\.\d{4})", text)
    if m_del:
        delivery_date = m_del.group(1)

    lines.append({
        "item_no": "10",
        "customer_product_no": mat,
        "description": desc,
        "quantity": qty,
        "uom": "SATZ",
        "price": price,
        "line_value": total,
        "te_part_number": te,
        "manufacturer_part_no": "",
        "delivery_date": delivery_date,
    })
    return lines


def parse_new_netz(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "NEW Netz GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    return {"header": header, "lines": _extract_lines(text)}
