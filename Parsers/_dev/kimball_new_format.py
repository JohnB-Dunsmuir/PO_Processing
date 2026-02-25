import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    # 3.600 or 1.152,00 etc.
    s = num.replace(" ", "")
    # first strip thousands dot, then convert comma
    s = s.replace(".", "").replace(",", ".")
    return float(s)


def detect_new_format(text: str) -> bool:
    """
    Detect the 2025 Kimball format like PO 4503705386.

    Key markers:
    - 'PO Number 4503705386'
    - 'Kimball Electronics Poland Sp. z o.o.'
    - Line pattern: 0010 1251-9070-0001 3.600 EA 320,00 1.152,00
    """
    t = text.upper()
    if "KIMBALL ELECTRONICS POLAND" not in t:
        return False
    if "PO NUMBER 4503705386" in t:
        return True

    # Generic pattern: "PO Number <8-10 digits>" AND a 0010 line with EA
    has_po_number = bool(re.search(r"PO NUMBER\s+\d{8,10}", t))
    has_0010_line = bool(
        re.search(r"\b0010\s+\S+\s+[\d\.]+\s+EA\s+[\d\.,]+\s+[\d\.,]+", t)
    )
    return has_po_number and has_0010_line


def _extract_po_number(text: str) -> str:
    m = re.search(r"\bPO Number\s+(\d{8,10})", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_po_date(text: str) -> str:
    # In this format PO Date is dd.mm.yyyy
    m = re.search(r"\bPO Date\s+(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_buyer(text: str) -> str:
    m = re.search(r"Buyer\s+([^\n]+)", text)
    if m:
        return m.group(1).strip()
    # fallback: known buyer
    if "P. WIEDERA" in text.upper():
        return "P. Wiedera"
    return ""


def _extract_delivery_address(text: str) -> str:
    """
    Ship To block is very stable in this format.
    """
    m = re.search(r"Ship To:\s*(.*?)\n\s*Send Date", text, flags=re.S | re.I)
    if not m:
        # Fallback: until 'Share capital value'
        m = re.search(r"Ship To:\s*(.*?)Share capital value", text,
                      flags=re.S | re.I)
    if not m:
        return (
            "KIMBALL ELECTRONICS POLAND, SP. Z O.O., "
            "POZNANSKA 1C, PL-62-080 TARNOWO PODGORNE"
        )
    block = m.group(1)
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    return ", ".join(lines).upper()


def _extract_te_part(text: str) -> str:
    """
    In the example:
      'Manufacturer Part Number: ... 8-338069-2'
    """
    m = re.search(r"Manufacturer Part Number.*?([\d\-]+)", text,
                  flags=re.S | re.I)
    return m.group(1).strip() if m else ""


def _extract_line_delivery_date(text: str) -> str:
    m = re.search(r"Delivery date:\s*(\d{2}\.\d{2}\.\d{4})", text)
    if m:
        return m.group(1)
    # Sometimes dd.mm.yyyy is written with dots but OCR might give 26.01.2026 anyway
    m = re.search(r"Delivery date:\s*(\d{2}\.\d{2}\.\d{4})", text)
    return m.group(1) if m else ""


def _extract_lines(text: str):
    """
    Item line example (page 1):
      0010 1251-9070-0001 3.600 EA 320,00 1.152,00
      CONN, POST TYP 1.27-PIN-SPCG-MTG-END FDA per /1.000
    """
    lines = []

    # main numeric row
    line_pat = re.compile(
        r"\b0010\s+"
        r"(?P<mat>\S+)\s+"
        r"(?P<qty>[\d\.]+)\s+EA\s+"
        r"(?P<price>[\d\.,]+)\s+"
        r"(?P<total>[\d\.,]+)",
        flags=re.I,
    )
    m = line_pat.search(text)
    if not m:
        return lines

    mat = m.group("mat")
    qty_raw = m.group("qty")
    price_raw = m.group("price")
    total_raw = m.group("total")

    qty = qty_raw.replace(".", "").replace(",", "")  # 3.600 → 3600
    price = _to_float_eu(price_raw)
    total = _to_float_eu(total_raw)

    # description line directly following the numeric row
    desc = ""
    m_desc = re.search(
        r"0010[^\n]*\n([^\n]+)", text
    )
    if m_desc:
        desc = m_desc.group(1).strip()

    te_part = _extract_te_part(text)
    delivery_date = _extract_line_delivery_date(text)

    # Note: price on PO is per 1.000, but your enrichment can re-normalise if needed.
    lines.append({
        "item_no": "10",
        "customer_product_no": mat,
        "description": desc,
        "quantity": qty,
        "uom": "EA",
        "price": price,          # as shown on PO (per 1.000)
        "line_value": total,
        "te_part_number": te_part,
        "manufacturer_part_no": te_part,
        "delivery_date": delivery_date,
    })
    return lines


def parse_new_format(text: str):
    """
    Parse the 2025 Kimball Electronics Poland PO layout.
    """
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Kimball Electronics Poland Sp. z o.o.",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    return {"header": header, "lines": _extract_lines(text)}
