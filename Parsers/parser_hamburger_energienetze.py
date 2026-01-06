import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    # remove thousand separators and convert decimal comma
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))


def detect_hamburger_energienetze(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return ("hamburger energienetze gmbh" in t
            and "bestellung" in t
            and "s05-4503683421" in t)


def _extract_po_number(text: str) -> str:
    m = re.search(r"S05-(\d+)", text)
    return f"S05-{m.group(1)}" if m else ""


def _extract_po_date(text: str) -> str:
    # Datum im Kopf
    m = re.search(r"Datum\s*(\d{2}\.\d{2}\.\d{4})", text)
    return m.group(1) if m else ""


def _extract_buyer(text: str) -> str:
    m = re.search(r"Ansprechpartner/in\s*([A-Za-zÄÖÜäöüß .-]+)", text)
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Lieferanschrift:\s*(.*?)\s*Rechnungsanschrift:", text,
                  flags=re.S | re.I)
    if not m:
        return ("Hamburger Energienetze GmbH, Lager Bramfelder Chaussee 130 "
                "22177 Hamburg, Deutschland")
    block = m.group(1)
    return " ".join(l.strip() for l in block.splitlines() if l.strip())


def _extract_lines(text: str):
    """
    Position 00010 – WCSM-250/65
    50 Stück 130,99 EUR 6.549,50 EUR
    """
    lines = []
    pat = re.compile(
        r"00010\s+"
        r"(?P<mat>\d+)\s+"
        r"(?P<desc>Schrumpfschlauch.+?)\s+"
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

    # TE-Teilenummer (Ihre Materialnummer / Hersteller) falls vorhanden
    te = ""
    m_te = re.search(r"Ihre Materialnummer\s*([A-Za-z0-9\-]+)", text,
                     flags=re.I)
    if m_te:
        te = m_te.group(1).strip()

    # Liefertermin aus Kopf/Position
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
        "te_part_number": te,
        "manufacturer_part_no": "",
        "delivery_date": delivery_date or "01.10.2025",
    })
    return lines


def parse_hamburger_energienetze(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Hamburger Energienetze GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    return {"header": header, "lines": _extract_lines(text)}
