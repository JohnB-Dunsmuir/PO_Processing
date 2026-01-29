import re

def _to_float(num: str) -> float:
    if not num:
        return 0.0
    s = num.replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0


def detect_yeinternational(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return (
        "YEINTERNATIONAL" in t
        or "YEINTERNATIONAL AS" in t
        or "PURCHASE ORDER NO 1167839" in t
    )


def _extract_po_number(text: str) -> str:
    m = re.search(r"Purchase order NO?\s*[: ]\s*(\d+)", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"Date\s*[: ]\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_buyer(text: str) -> str:
    m = re.search(r"Buyer\s*[: ]\s*([A-Za-z .-]+)", text)
    return m.group(1).strip() if m else "YEInternational Buyer"


def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Deliver to\s*[: ](.*?)(?:Invoice to|Payment terms)",
                  text, flags=re.S | re.I)
    if m:
        block = m.group(1)
        return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())
    return "YEInternational AS, Estonia"


def _extract_lines(text: str):
    """
    Format (simplified):

    1 EC0001234  ABB PART XXXXXX  10 pcs  5,50  55,00
    """
    lines = []
    pat = re.compile(
        r"\b(?P<pos>\d+)\s+"
        r"(?P<code>EC[0-9]{7})\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<qty>\d+)\s+(?P<uom>pcs?|STK)\s+"
        r"(?P<price>[\d\.,]+)\s+"
        r"(?P<total>[\d\.,]+)",
        flags=re.I
    )

    for m in pat.finditer(text):
        pos = m.group("pos")
        code = m.group("code")
        desc = m.group("desc").strip()
        qty = m.group("qty")
        uom = m.group("uom").lower()
        price = _to_float(m.group("price"))
        total = _to_float(m.group("total"))

        lines.append({
            "item_no": str(int(pos) * 10),
            "customer_product_no": code,
            "description": desc,
            "quantity": qty,
            "uom": uom,
            "price": price,
            "line_value": total,
            "te_part_number": "",
            "manufacturer_part_no": "",
            "delivery_date": "",
        })

    return lines


def parse_yeinternational(text: str) -> dict:
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "YEInternational AS",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    return {"header": header, "lines": _extract_lines(text)}
