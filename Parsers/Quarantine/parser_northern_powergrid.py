import re

# ---------------------------------------------------------------------------
# DETECTION
# ---------------------------------------------------------------------------

def detect_northern_powergrid(text: str) -> bool:
    """
    Detect Northern Powergrid Purchase Orders.
    """
    if not text:
        return False

    t = text.lower()
    triggers = [
        "northern powergrid",
        "blanket release",
        "shiremoor",
        "billingham",
        "2204700-",
    ]
    return any(trig in t for trig in triggers)


# ---------------------------------------------------------------------------
# HEADER EXTRACTION
# ---------------------------------------------------------------------------

def _extract_po_number(text: str) -> str:
    m = re.search(r"Order\s+([0-9\-]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"Order Date\s+([0-9A-Z\-]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_buyer(text: str) -> str:
    # "Created By Boriboon, Phailin"
    m = re.search(r"Created By\s+([A-Za-z ,]+)", text, flags=re.I)
    if m:
        raw = m.group(1).strip()
        # Normalize "Surname, First" → "First Surname"
        if "," in raw:
            last, first = [p.strip() for p in raw.split(",", 1)]
            return f"{first} {last}"
        return raw
    return ""


def _extract_delivery_address(text: str) -> str:
    """
    Use 'Ship To:' block. If missing, use fallback HQ.
    """
    m = re.search(
        r"Ship To:\s*([\s\S]*?)Bill To:",
        text,
        flags=re.I
    )
    if m:
        block = m.group(1)
        flat = " ".join(ln.strip() for ln in block.splitlines() if ln.strip())
        return flat

    # Fallback
    return (
        "New York Road, Shiremoor, Newcastle upon Tyne, NE27 0LP, United Kingdom"
    )


# ---------------------------------------------------------------------------
# LINE EXTRACTION
# ---------------------------------------------------------------------------

def _extract_line(text: str) -> dict:
    """
    Northern Powergrid lines are extremely structured:

    35   163664   Needed: 30-SEP-2025 16:30:00
    15 EACH 94  1,410.00
    Description is multi-line above the price row.
    """

    # Match main numeric row
    row = re.search(
        r"(\d+)\s+([A-Za-z0-9]+).*?Needed[: ]+\s*(\d{2}-[A-Z]{3}-\d{4}).*?"
        r"(\d+)\s+([A-Za-z]+)\s+([\d\.]+)\s+([\d\.,]+)",
        text,
        flags=re.I | re.S
    )

    if not row:
        return {}

    item_no = row.group(1)
    part = row.group(2)
    delivery_date = row.group(3)
    qty = row.group(4)
    uom = row.group(5)
    price = row.group(6)
    amount = row.group(7).replace(",", "")

    # Extract description: take block between part number and "Ship To"
    desc_m = re.search(
        rf"{part}([\s\S]*?)Ship To:",
        text,
        flags=re.I
    )
    if desc_m:
        desc = " ".join(
            ln.strip() for ln in desc_m.group(1).splitlines() if ln.strip()
        )
    else:
        desc = ""

    return {
        "item_no": item_no,
        "customer_product_no": part,
        "description": desc,
        "quantity": qty,
        "uom": uom,
        "price": price,
        "line_value": amount,
        "te_part_number": "",
        "manufacturer_part_no": "",
        "delivery_date": delivery_date,
    }


# ---------------------------------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------------------------------

def parse_northern_powergrid(text: str) -> dict:
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Northern Powergrid",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    line = _extract_line(text)
    lines = [line] if line else []

    return {
        "header": header,
        "lines": lines,
    }
