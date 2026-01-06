import re

# ---------------------------------------------------------------------------
# DETECTION
# ---------------------------------------------------------------------------

def detect_sp_power_systems(text: str) -> bool:
    """
    Detect Scottish Power / SP Power Systems POs.
    """
    if not text:
        return False

    t = text.lower()
    triggers = [
        "scottishpower",
        "sp energy networks",
        "call-off order",
        "sp distribution plc",
        "framework agreement ref",
        "4507",   # many SP orders begin 4507xxxxxx
    ]
    return any(trig in t for trig in triggers)


# ---------------------------------------------------------------------------
# HEADER EXTRACTION
# ---------------------------------------------------------------------------

def _extract_po_number(text: str) -> str:
    # Ref.: 4507111244
    m = re.search(r"Ref\.:?\s*([0-9]+)", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_po_date(text: str) -> str:
    # Date: 12.05.2025
    m = re.search(r"Date[: ]+(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_buyer(text: str) -> str:
    # Manager ALISON BRYCE
    m = re.search(r"Manager\s+([A-Za-z ]+)", text, flags=re.I)
    return m.group(1).strip().title() if m else ""


def _extract_delivery_address(text: str) -> str:
    """
    Extract delivery block under "SHIP TO LOCATION".
    If missing, use SP Distribution PLC headquarters.
    """
    m = re.search(
        r"SHIP TO LOCATION\s*([\s\S]*?)Delivery date",
        text,
        flags=re.I
    )
    if m:
        block = m.group(1)
        flat = " ".join(line.strip() for line in block.splitlines() if line.strip())
        return flat

    # Fallback
    return (
        "SP Distribution PLC, 320 St Vincent Street, Glasgow G2 5AD, Scotland"
    )


def _extract_delivery_date(text: str) -> str:
    # Delivery date: 05.06.2025
    m = re.search(r"Delivery date[: ]+(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# LINE EXTRACTION
# ---------------------------------------------------------------------------

def _extract_lines(text: str, delivery_date: str):
    """
    Line structure:

    00010 JT BRANCH...
    detailed description...
    00010 30980279 5 ST 1,378.37 6,891.85
    """
    lines = []

    # Match the numeric line row
    row_regex = re.compile(
        r"(000\d{2})\s+"                # item no
        r"([0-9]+)\s+"                  # item code
        r"(\d+)\s+ST\s+"                # quantity
        r"([\d\.,]+)\s+"                # price
        r"([\d\.,]+)",                  # amount
        flags=re.I
    )

    for m in row_regex.finditer(text):
        item_no = m.group(1)
        code = m.group(2)
        qty = m.group(3)
        price = m.group(4).replace(",", "")
        amount = m.group(5).replace(",", "")

        # Extract description = text above numeric row until previous blank line
        # We'll take 300 chars above this row and clean it.
        start = max(0, m.start() - 300)
        block = text[start:m.start()]
        block = block.strip()

        desc_lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        description = " ".join(desc_lines)

        lines.append({
            "item_no": item_no,
            "customer_product_no": code,
            "description": description,
            "quantity": qty,
            "uom": "ST",
            "price": price,
            "line_value": amount,
            "te_part_number": "",
            "manufacturer_part_no": "",
            "delivery_date": delivery_date,
        })

    return lines


# ---------------------------------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------------------------------

def parse_sp_power_systems(text: str) -> dict:
    """
    Produce v11.3.2-compliant header + lines dict.
    """

    po_number = _extract_po_number(text)
    po_date = _extract_po_date(text)
    buyer = _extract_buyer(text)
    delivery_address = _extract_delivery_address(text)
    delivery_date = _extract_delivery_date(text)

    lines = _extract_lines(text, delivery_date)

    header = {
        "po_number": po_number,
        "po_date": po_date,
        "customer_name": "SP Power Systems Ltd",
        "buyer": buyer,
        "delivery_address": delivery_address,
    }

    return {
        "header": header,
        "lines": lines,
    }
