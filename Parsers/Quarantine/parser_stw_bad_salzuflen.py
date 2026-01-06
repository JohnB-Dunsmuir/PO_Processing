import re

def _to_float_eu(num: str) -> float:
    """Convert EU formatted numbers like 1.152,00 → 1152.00"""
    if not num:
        return 0.0
    return float(num.replace(" ", "").replace(".", "").replace(",", "."))


def detect_stw_bad_salzuflen(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return (
        "stadtwerke bad salzuflen" in t
        or "4510001072" in t
        or "bad salzuflen" in t
    )


def _extract_po_number(text: str) -> str:
    m = re.search(r"Bestellnummer\s*(\d+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"Datum\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_buyer(text: str) -> str:
    m = re.search(r"AnsprechpartnerIn\s*([A-Za-zÄÖÜäöüß .\-]+)", text)
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Bitte liefern Sie an:\s*(.*?)Lieferdatum", text,
                  flags=re.S | re.I)
    if not m:
        return "Stadtwerke Bad Salzuflen GmbH, Uferstraße 36–44, 32108 Bad Salzuflen, Deutschland"
    block = m.group(1)
    return " ".join(line.strip() for line in block.splitlines() if line.strip())


def _extract_delivery_date(text: str) -> str:
    # Format: "Woche 36.2025"
    m = re.search(r"Lieferdatum\s*:\s*(Woche\s*\S+)", text, flags=re.I)
    if m:
        return m.group(1).strip()
    return ""


def _extract_lines(text: str):
    """
    Position 00010
    4130274 36 Stück 32,00 EUR/1 ST 1.152,00
    10 KV Verbindungsmuffe 95–240 MXSU-3131
    TE: 691269-005
    """
    lines = []

    pat = re.compile(
        r"00010\s+"
        r"(?P<mat>\d+)\s+"
        r"(?P<qty>\d+)\s+St[üu]ck\s+"
        r"(?P<price>[\d\.,]+)\s*EUR\/1\s*ST\s*"
        r"(?P<total>[\d\.,]+)\s*"
        r"(?P<desc>(?:10\s*KV.*?|MXSU.*?|[\s\S]{0,200}))",
        flags=re.I
    )

    m = pat.search(text)
    if not m:
        return lines

    mat = m.group("mat")
    qty = m.group("qty")
    price = _to_float_eu(m.group("price"))
    total = _to_float_eu(m.group("total"))

    # Clean description block
    raw_desc = m.group("desc")
    desc = " ".join(line.strip() for line in raw_desc.splitlines() if line.strip())

    # TE part number
    te = ""
    m_te = re.search(r"(\d{6}-\d{3})", text)  # 691269-005
    if m_te:
        te = m_te.group(1)

    # Delivery date
    delivery_date = _extract_delivery_date(text)

    lines.append({
        "item_no": "10",
        "customer_product_no": mat,
        "description": desc or "10 kV Verbindungsmuffe 95–240 MXSU-3131",
        "quantity": qty,
        "uom": "ST",
        "price": price,
        "line_value": total,
        "te_part_number": te,
        "manufacturer_part_no": "",
        "delivery_date": delivery_date,
    })

    return lines


def parse_stw_bad_salzuflen(text: str):
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Stadtwerke Bad Salzuflen GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
