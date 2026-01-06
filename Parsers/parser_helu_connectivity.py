import re

# -------------------------------------------------------------
# EU float helper
# -------------------------------------------------------------
def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    s = num.replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0


# -------------------------------------------------------------
# Detect HELU Connectivity
# -------------------------------------------------------------
def detect_helu_connectivity(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return (
        "HELU CONNECTIVITY SOLUTIONS" in t
        or "HELU KABEL" in t
        or "BECHTERDISSER STR" in t
        or "TE CONNECTIVITY SOLUTIONS GMBH" in t and "20092367" in t
    )


# -------------------------------------------------------------
# Extract Header Fields
# -------------------------------------------------------------
def _extract_po_number(text: str) -> str:
    m = re.search(r"Belegnummer[: ]*(\d+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"Datum[: ]*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_buyer(text: str) -> str:
    # Example: "Ihr Ansprechpartner: Bestelleingang" or "Marvin Hiemann"
    m = re.search(r"Ihr Ansprechpartner.*?([A-Za-zÄÖÜäöüß .-]+)", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"Marvin Hiemann", text)
    if m:
        return "Marvin Hiemann"
    return "HELU Buyer"


def _extract_delivery_address(text: str) -> str:
    # Displayed near top: "Helu Connectivity Solutions, Bechterdisser Str. 67, 33719 Bielefeld"
    m = re.search(r"Helu Connectivity Solutions.*?33719 Bielefeld", text, flags=re.I | re.S)
    if m:
        block = m.group(0)
        return " ".join(ln.strip() for ln in block.splitlines() if ln.strip())
    return "Helu Connectivity Solutions Bielefeld GmbH, Bechterdisser Str. 67, 33719 Bielefeld, Germany"


# -------------------------------------------------------------
# Extract Lines
# -------------------------------------------------------------
def _extract_lines(text: str):
    """
    HELU line format (example from page 2):

    10  0-000000-03573   31.10.2025   2.000,000 STK   120,66   2.413,20
    Leistungslamellenklemmung 9,5-14,5mm Preiseinheit 100
    Ihre Materialnummer: 50-0415-000-000
    """
    lines = []

    # Match all line blocks of form: pos, material, date, qty, UOM, price, total
    pat = re.compile(
        r"(?P<pos>\d+)\s+"
        r"(?P<mat>\S+)\s+"
        r"(?P<date>\d{2}\.\d{2}\.\d{4})\s+"
        r"(?P<qty>[\d\.,]+)\s+STK\s+"
        r"(?P<price>[\d\.,]+)\s+"
        r"(?P<total>[\d\.,]+)",
        flags=re.I
    )

    for m in pat.finditer(text):
        pos = m.group("pos")
        mat = m.group("mat")
        qty = m.group("qty").replace(".", "").replace(",", "")
        price = _to_float_eu(m.group("price"))
        total = _to_float_eu(m.group("total"))

        # Extract description after the numeric line
        desc = ""
        block_start = m.end()
        tail = text[block_start:block_start+200]
        for ln in tail.splitlines():
            if ln.strip() and not re.match(r"Ihre Materialnummer", ln, re.I):
                desc = ln.strip()
                break

        # TE / Customer Material Number
        te = ""
        m_te = re.search(r"Ihre Materialnummer[: ]*([A-Za-z0-9\-\.\_]+)", text[m.end():], flags=re.I)
        if m_te:
            te = m_te.group(1).strip()

        delivery_date = m.group("date")

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
            "delivery_date": delivery_date,
        })

    return lines


# -------------------------------------------------------------
# Final Parser
# -------------------------------------------------------------
def parse_helu_connectivity(text: str) -> dict:
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "HELU Connectivity Solutions Bielefeld GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    lines = _extract_lines(text)
    return {"header": header, "lines": lines}
