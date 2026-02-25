import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))


def detect_nsg_kassel(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return ("städtische werke netz + service gmbh" in t
            or "netz + service gmbh kassel" in t)


def _extract_po_number(text: str) -> str:
    m = re.search(r"Bestellnr\.\s*(\d+)", text)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"Datum\s*(\d{2}\.\d{2}\.\d{4})", text)
    return m.group(1) if m else ""


def _extract_buyer(text: str) -> str:
    m = re.search(r"Ansprechpartner\s*([A-Za-zÄÖÜäöüß .-]+)", text)
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Lieferanschrift\s*(.*?)Rechnungsanschrift", text,
                  flags=re.S | re.I)
    if not m:
        return ("Städtische Werke Netz + Service GmbH, "
                "Lager Sandershäuser Straße, 34123 Kassel, Deutschland")
    block = m.group(1)
    return " ".join(l.strip() for l in block.splitlines() if l.strip())


def _extract_lines(text: str):
    """
    Position 00010
    42041515  Kabelabzweigklemme ... 50 Stück 9,50 EUR 475,00 EUR
    """
    lines = []
    pat = re.compile(
        r"00010\s+"
        r"(?P<mat>\d+)\s+"
        r"(?P<desc>Kabelabzweigklemme.+?)\s+"
        r"(?P<qty>\d+)\s+St[üu]ck\s+"
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

    # Hersteller- / TE-Nummern
    te = ""
    manu = ""
    m_te = re.search(r"TE Connectivity\s*:\s*([A-Za-z0-9\-]+)", text,
                     flags=re.I)
    if m_te:
        te = m_te.group(1).strip()
    m_manu = re.search(r"Herstellerteile\-Nr\.\s*([A-Za-z0-9\-]+)", text,
                       flags=re.I)
    if m_manu:
        manu = m_manu.group(1).strip()

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
        "uom": "ST",
        "price": price,
        "line_value": total,
        "te_part_number": te or "F34646-000",
        "manufacturer_part_no": manu or "688850-000",
        "delivery_date": delivery_date,
    })
    return lines


def parse_nsg_kassel(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Städtische Werke Netz + Service GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    return {"header": header, "lines": _extract_lines(text)}
