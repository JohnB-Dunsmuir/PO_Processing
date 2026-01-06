import re

def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    s = num.replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0


def detect_viteko(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return (
        "VITEKO TECHNISCH HANDELSBUREAU" in t
        or "VITEKO B.V." in t
        or "PO NUMBER: 2313" in t
    )


def _extract_po_number(text: str) -> str:
    m = re.search(r"PO\s*(?:NUMBER|No\.?)\s*[: ]\s*(\S+)", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"Date\s*[: ]\s*(\d{2}-\d{2}-\d{4})", text, flags=re.I)
    if not m:
        return ""
    d, mo, y = m.group(1).split("-")
    return f"{d}.{mo}.{y}"


def _extract_buyer(text: str) -> str:
    m = re.search(r"Contact\s*[: ]\s*([A-Za-z .-]+)", text)
    return m.group(1).strip() if m else "VITEKO Buyer"


def _extract_delivery_address(text: str) -> str:
    m = re.search(r"Deliver to\s*[: ](.*?)(?:Invoice to|Payment terms)",
                  text, flags=re.S | re.I)
    if m:
        block = m.group(1)
        return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())
    return "VITEKO Technisch Handelsbureau B.V., Netherlands"


def _extract_lines(text: str):
    """
    Typical line:

    10 1SNA199864R2400  50 PC  3,45  172,50
    ABB XXXXXX ...
    """
    lines = []
    pat = re.compile(
        r"\b(?P<pos>\d{1,3})\s+"
        r"(?P<mat>1S[A-Z0-9]+R[0-9]{4})\s+"
        r"(?P<qty>\d+)\s+(?P<uom>PC|ST|PCS)\s+"
        r"(?P<price>[\d\.,]+)\s+"
        r"(?P<total>[\d\.,]+)",
        flags=re.I
    )

    for m in pat.finditer(text):
        pos = m.group("pos")
        mat = m.group("mat")
        qty = m.group("qty")
        uom = m.group("uom").upper()
        price = _to_float_eu(m.group("price"))
        total = _to_float_eu(m.group("total"))

        # Description: next non-empty line
        tail = text[m.end(): m.end() + 200]
        desc = ""
        for ln in tail.splitlines():
            ln = ln.strip()
            if ln:
                desc = ln
                break

        lines.append({
            "item_no": str(int(pos) * 10),
            "customer_product_no": mat,
            "description": desc,
            "quantity": qty,
            "uom": uom,
            "price": price,
            "line_value": total,
            "te_part_number": mat,
            "manufacturer_part_no": "",
            "delivery_date": "",
        })

    return lines


def parse_viteko(text: str) -> dict:
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "VITEKO Technisch Handelsbureau B.V.",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }
    return {"header": header, "lines": _extract_lines(text)}
