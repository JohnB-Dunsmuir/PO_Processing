import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    s = num.replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0


def detect_hengstler(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return (
        "HENGSTLER GMBH" in t
        or "ORDER NR. 4501168802" in t
        or "AM ROTEN WEG" in t
    )


def _extract_po_number(text: str) -> str:
    m = re.search(r"Order Nr\.?\s*([0-9]+)", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_po_date(text: str) -> str:
    # e.g. 19.08.2025
    m = re.search(r"am\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    if m:
        return m.group(1)
    m = re.search(r"Date\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_buyer(text: str) -> str:
    m = re.search(r"Your contact\s*[:\-]?\s*([A-Za-zÄÖÜäöüß .-]+)", text)
    return m.group(1).strip() if m else "Hengstler Buyer"


def _extract_delivery_address(text: str) -> str:
    """
    Use the 'Delivery address' block if present, else standard Hengstler.
    """
    m = re.search(r"Delivery address\s*:\s*(.*?)(?:Invoice address|Pos\.)",
                  text, flags=re.S | re.I)
    if m:
        block = m.group(1)
        return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())
    return "Hengstler GmbH, Am Roten Weg 1, 78604 Rietheim-Weilheim, Germany"


def _extract_lines(text: str):
    """
    Typical line pattern (example):
      10  12345678  1,000 STK  45,67 EUR  45,67
      RESOLVER CONNECTOR ABC...
      Your Mat.-No.: 123456-000
    """
    lines = []
    pat = re.compile(
        r"\b(?P<pos>\d{1,3})\s+"
        r"(?P<mat>\d{6,})\s+"
        r"(?P<qty>[\d\.,]+)\s+STK\s+"
        r"(?P<price>[\d\.,]+)\s+EUR\s+"
        r"(?P<total>[\d\.,]+)",
        flags=re.I
    )

    for m in pat.finditer(text):
        pos = m.group("pos")
        mat = m.group("mat")
        qty = m.group("qty").replace(".", "").replace(",", "")
        price = _to_float_eu(m.group("price"))
        total = _to_float_eu(m.group("total"))

        # Description: first non-empty line after numeric block
        tail = text[m.end(): m.end() + 300]
        desc = ""
        for ln in tail.splitlines():
            ln = ln.strip()
            if ln and not ln.lower().startswith("your mat"):
                desc = ln
                break

        # TE / customer PN after "Your Mat.-No."
        te = ""
        m_te = re.search(r"Your Mat\.-No\.?:\s*([A-Za-z0-9\-]+)", tail, flags=re.I)
        if m_te:
            te = m_te.group(1).strip()

        # Delivery date after the line (if present)
        delivery = ""
        m_del = re.search(r"Delivery date\s*[: ]*(\d{2}\.\d{2}\.\d{4})", tail)
        if m_del:
            delivery = m_del.group(1)

        lines.append({
            "item_no": str(int(pos) * 10),
            "customer_product_no": mat,
            "description": desc,
            "quantity": qty,
            "uom": "STK",
            "price": price,
            "line_value": total,
            "te_part_number": te,
            "manufacturer_part_no": "",
            "delivery_date": delivery,
        })

    return lines


def parse_hengstler(text: str) -> dict:
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Hengstler GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    return {"header": header, "lines": _extract_lines(text)}
