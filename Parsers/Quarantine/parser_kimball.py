import re

# =====================================================================
# Shared helpers
# =====================================================================

def _to_float_eu(num: str) -> float:
    """Convert EU formatted numbers like 1.152,00 → 1152.00."""
    if not num:
        return 0.0
    s = num.replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0


# =====================================================================
# Canonical addresses
# =====================================================================

CANONICAL_ADDRESSES = {
    "POZNANSKA 1C": "KIMBALL ELECTRONICS POLAND, SP. Z O.O., POZNANSKA 1C, PL-62-080 TARNOWO PODGORNE",
}


# =====================================================================
# TOP-LEVEL DETECT (for loader)
# =====================================================================

def detect_kimball(text: str) -> bool:
    """
    Main detection: identifies ANY Kimball PO regardless of format.
    """
    if not text:
        return False
    t = text.upper()
    return ("KIMBALL ELECTRONICS POLAND" in t or
            "KIMBALL ELECTRONICS" in t or
            "TARNOWO PODGORNE" in t)


# =====================================================================
# NEW 2025 FORMAT DETECTION
# =====================================================================

def detect_new_kimball_format(text: str) -> bool:
    """
    Detects the new 2025 PO layout used in PO 4503705386.
    Key markers:
      - “PO Number 4503705386”
      - Item row like: 0010 <mat> 3.600 EA 320,00 1.152,00
    """
    t = text.upper()

    if "PO NUMBER 4503705386" in t:
        return True

    has_po = bool(re.search(r"PO NUMBER\s+\d{8,10}", t))
    has_0010_line = bool(
        re.search(r"\b0010\s+\S+\s+[\d\.]+\s+EA\s+[\d\.,]+\s+[\d\.,]+", t)
    )

    return has_po and has_0010_line


# =====================================================================
# PARSER: NEW 2025 FORMAT
# =====================================================================

def _extract_new_po_number(text: str) -> str:
    m = re.search(r"PO Number\s+(\d{8,10})", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_new_po_date(text: str) -> str:
    m = re.search(r"PO Date\s+(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_new_buyer(text: str) -> str:
    m = re.search(r"Buyer\s+([^\n]+)", text)
    if m:
        return m.group(1).strip()
    if "P. WIEDERA" in text.upper():
        return "P. Wiedera"
    return ""


def _extract_new_ship_to(text: str) -> str:
    """
    Ship To block appears between “Ship To:” and either “Send Date” or “Page”.
    """
    m = re.search(r"Ship To:\s*(.*?)Send Date", text, flags=re.S | re.I)
    if not m:
        m = re.search(r"Ship To:\s*(.*?)Page", text, flags=re.S | re.I)
    if not m:
        # Fallback: just search for the Poznanska 1c address
        for key, canonical in CANONICAL_ADDRESSES.items():
            if key in text.upper():
                return canonical
        return ""

    block = m.group(1)
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    up = " ".join(lines).upper()

    for key, canonical in CANONICAL_ADDRESSES.items():
        if key in up:
            return canonical

    return up


def _extract_new_te_part(text: str) -> str:
    m = re.search(r"Manufacturer Part Number.*?([\d\-]+)", text,
                  flags=re.S | re.I)
    return m.group(1).strip() if m else ""


def _extract_new_delivery_date(text: str) -> str:
    m = re.search(r"Delivery date[: ]+(\d{2}\.\d{2}\.\d{4})", text,
                  flags=re.I)
    return m.group(1) if m else ""


def _extract_new_lines(text: str):
    """
    Item pattern:
      0010 1251-9070-0001 3.600 EA 320,00 1.152,00
      CONN, POST TYP 1.27-PIN ...
    """
    lines = []

    main_pat = re.compile(
        r"\b0010\s+"
        r"(?P<mat>\S+)\s+"
        r"(?P<qty>[\d\.]+)\s+EA\s+"
        r"(?P<price>[\d\.,]+)\s+"
        r"(?P<total>[\d\.,]+)",
        flags=re.I,
    )
    m = main_pat.search(text)
    if not m:
        return lines

    mat = m.group("mat")
    qty = m.group("qty").replace(".", "")
    price = _to_float_eu(m.group("price"))
    total = _to_float_eu(m.group("total"))

    # Description line immediately after numeric row
    desc = ""
    m_desc = re.search(r"0010[^\n]*\n([^\n]+)", text)
    if m_desc:
        desc = m_desc.group(1).strip()

    te = _extract_new_te_part(text)
    delivery = _extract_new_delivery_date(text)

    lines.append({
        "item_no": "10",
        "customer_product_no": mat,
        "description": desc,
        "quantity": qty,
        "uom": "EA",
        "price": price,                # per 1,000 as on PO
        "line_value": total,
        "te_part_number": te,
        "manufacturer_part_no": te,
        "delivery_date": delivery,
    })

    return lines


def parse_new_kimball_format(text: str):
    header = {
        "po_number": _extract_new_po_number(text),
        "po_date": _extract_new_po_date(text),
        "customer_name": "Kimball Electronics Poland Sp. z o.o.",
        "buyer": _extract_new_buyer(text),
        "delivery_address": _extract_new_ship_to(text),
    }
    return {"header": header, "lines": _extract_new_lines(text)}


# =====================================================================
# LEGACY FORMAT PARSER (your original code, unmodified)
# =====================================================================

def extract_ship_to_address_legacy(text: str) -> str:
    """
    Extract legacy Ship-To block and map to canonical.
    """
    m = re.search(r"Ship To:\s*(.*?)Bill To:", text, flags=re.S | re.I)
    if not m:
        m = re.search(r"Ship To:\s*(.*?)(?:Page|\Z)", text, flags=re.S | re.I)
    if not m:
        return ""

    block = m.group(1)
    up = block.upper()

    for key, canonical in CANONICAL_ADDRESSES.items():
        if key in up:
            return canonical

    return " ".join(line.strip() for line in block.splitlines() if line.strip())


def extract_po_number_legacy(text: str) -> str:
    m = re.search(r"\bPO Number\s*[: ]+\s*(\d+)", text, flags=re.I)
    if m:
        return m.group(1)

    m = re.search(r"\b(\d{8,10})\b", text)
    return m.group(1) if m else ""


def extract_po_date_legacy(text: str) -> str:
    m = re.search(r"\bPO Date\s*[: ]+(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    if m:
        return m.group(1)

    m = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)
    return m.group(1) if m else ""


def extract_buyer_legacy(text: str) -> str:
    m = re.search(r"Buyer\s*(.*?)\n", text)
    if m:
        val = m.group(1).strip()
        if val:
            return val
    if "P. WIEDERA" in text.upper():
        return "P. Wiedera"
    return ""


def extract_line_item_legacy(text: str) -> dict:
    """
    Legacy assumptions:
    - Customer PN: 1234-5678-9012
    - TE PN: X-1234567-X
    - Quantity: 10.890 EA
    - Money: first two EU-style numbers = price & line value
    """
    # Customer PN
    cust_match = re.search(r"(\d{4}-\d{4}-\d{4})", text)
    cust = cust_match.group(1) if cust_match else ""

    # First nonempty line after PN as description
    desc = ""
    if cust_match:
        tail = text[cust_match.end(): cust_match.end() + 300]
        for line in tail.splitlines():
            ls = line.strip()
            if ls:
                desc = ls
                break

    # Quantity + UOM
    qty = ""
    uom = ""
    m_qty = re.search(r"(\d{1,3}(?:\.\d{3})*)\s*(EA|PCS?)", text, flags=re.I)
    if m_qty:
        qty = m_qty.group(1).replace(".", "")
        uom = m_qty.group(2).upper()

    # Price & Line Value
    money_pattern = r"(\d{1,3}(?:\.\d{3})*,\d{2})"
    money_values = re.findall(money_pattern, text)
    price = _to_float_eu(money_values[0]) if len(money_values) >= 1 else 0
    line_value = _to_float_eu(money_values[1]) if len(money_values) >= 2 else 0

    # TE PN
    te_match = re.search(r"(\d-\d{7}-\d)", text)
    te = te_match.group(1) if te_match else ""

    # Delivery date
    m_dd = re.search(r"Delivery date[: ]+(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    dd = m_dd.group(1) if m_dd else ""

    return {
        "item_no": "10",
        "customer_product_no": cust,
        "description": desc,
        "quantity": qty,
        "uom": uom,
        "price": price,
        "line_value": line_value,
        "te_part_number": te,
        "manufacturer_part_no": te,
        "delivery_date": dd,
    }


def parse_kimball_legacy(text: str):
    header = {
        "po_number": extract_po_number_legacy(text),
        "po_date": extract_po_date_legacy(text),
        "customer_name": "Kimball Electronics Poland",
        "buyer": extract_buyer_legacy(text),
        "delivery_address": extract_ship_to_address_legacy(text),
    }

    line = extract_line_item_legacy(text)
    return {"header": header, "lines": [line] if line.get("quantity") else []}


# =====================================================================
# FINAL PUBLIC PARSER (DISPATCHER)
# =====================================================================

def parse_kimball(text: str):
    """
    Unified dispatcher for all Kimball formats.
    """
    if detect_new_kimball_format(text):
        return parse_new_kimball_format(text)

    return parse_kimball_legacy(text)
