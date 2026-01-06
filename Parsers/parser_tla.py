import re

# ---------------------------------------------------------------------------
# DETECTION
# ---------------------------------------------------------------------------

def detect_tla(text: str) -> bool:
    """
    Detect TLA Distribution Ltd purchase orders.
    """
    if not text:
        return False

    t = text.lower()
    triggers = [
        "tla distribution ltd",
        "brackmills industrial estate",
        "our order no",
        "printed: monday",
        "1sna",
    ]
    return any(trig in t for trig in triggers)


# ---------------------------------------------------------------------------
# HEADER EXTRACTION
# ---------------------------------------------------------------------------

def _extract_po_number(text: str) -> str:
    m = re.search(r"Our Order No[: ]+([0-9]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    # Order Date: 07/04/2025
    m = re.search(r"Order Date[: ]+(\d{2}\/\d{2}\/\d{4})", text, flags=re.I)
    if m:
        d = m.group(1)
        return d.replace("/", ".")
    return ""


def _extract_buyer(text: str) -> str:
    m = re.search(r"Ordered By[: ]+([A-Za-z ]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    """
    Look for Delivery Address block. If missing, fallback to HQ.
    """
    m = re.search(
        r"Delivery Address\s*([\s\S]*?)Order Date",
        text,
        flags=re.I
    )
    if m:
        block = m.group(1)
        flat = " ".join([ln.strip() for ln in block.splitlines() if ln.strip()])
        return flat

    return "TLA Distribution Ltd, 22 Osyth Close, Brackmills Industrial Estate, Northampton NN4 7DY, UK"


# ---------------------------------------------------------------------------
# LINE EXTRACTION
# ---------------------------------------------------------------------------

def _to_float(num: str) -> float:
    return float(num.replace(",", ""))


def _extract_lines(text: str):
    """
    Line pattern:

    Qty  UoM  Our Code  Date Required  Price  Per  Line Total
    Description lines...
    Manufacturers Part No.: XXXX
    """
    pattern = re.compile(
        r"([\d\.]+)\s+ea\s+([A-Za-z0-9\-\/]+)\s+(\d{2}\/\d{2}\/\d{4})\s+([\d\.]+)\s+1\s+([\d\.]+)",
        flags=re.I
    )

    lines = []
    item_no_counter = 1

    for m in pattern.finditer(text):
        qty_raw = m.group(1)
        code = m.group(2)
        date_raw = m.group(3)
        price_raw = m.group(4)
        total_raw = m.group(5)

        quantity = _to_float(qty_raw)
        price = _to_float(price_raw)
        total = _to_float(total_raw)
        delivery_date = date_raw.replace("/", ".")

        # Extract description and TE PN
        seg = text[m.end(): m.end() + 400]
        desc_lines = [ln.strip() for ln in seg.splitlines() if ln.strip()]
        description = desc_lines[0] if desc_lines else ""

        te_part = ""
        te_m = re.search(r"Part No\.\s*[: ]\s*([A-Za-z0-9\-\/]+)", seg, flags=re.I)
        if te_m:
            te_part = te_m.group(1).strip()

        lines.append({
            "item_no": str(item_no_counter),
            "customer_product_no": code,
            "description": description,
            "quantity": quantity,
            "uom": "EA",
            "price": price,
            "line_value": total,
            "te_part_number": te_part,
            "manufacturer_part_no": te_part,
            "delivery_date": delivery_date,
        })

        item_no_counter += 1

    return lines


# ---------------------------------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------------------------------

def parse_tla(text: str) -> dict:
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "TLA Distribution Ltd",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    lines = _extract_lines(text)

    return {
        "header": header,
        "lines": lines,
    }
