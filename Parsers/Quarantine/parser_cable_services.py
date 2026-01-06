import re

# ---------------------------------------------------------------------------
# DETECTION
# ---------------------------------------------------------------------------

def detect_cable_services(text: str) -> bool:
    """
    Detect Cable Services Limited purchase orders.
    """
    if not text:
        return False

    t = text.lower()
    triggers = [
        "cable services limited",
        "hawbank house",
        "revised purchase order",
        "wrexham industrial estate",
        "purchase order number",
    ]
    return any(trig in t for trig in triggers)


# ---------------------------------------------------------------------------
# HEADER EXTRACTION
# ---------------------------------------------------------------------------

def _extract_po_number(text: str) -> str:
    m = re.search(r"Purchase Order Number\s*([0-9]+)", text, flags=re.I)
    return m.group(1) if m else ""


def _extract_po_date(text: str) -> str:
    # Date 11/02/2025 13:41:55
    m = re.search(r"Date\s*([0-9]{2}\/[0-9]{2}\/[0-9]{4})", text, flags=re.I)
    if not m:
        return ""
    d = m.group(1)
    return d.replace("/", ".")


def _extract_buyer(text: str) -> str:
    m = re.search(r"Buyer Name\s*([A-Za-z ,]+)", text, flags=re.I)
    if m:
        name = m.group(1).strip()
        if "," in name:
            last, first = [p.strip() for p in name.split(",", 1)]
            return f"{first} {last}"
        return name
    return ""


def _extract_delivery_address(text: str) -> str:
    """
    Extract 'Ship To' block; fallback to head office.
    """
    m = re.search(
        r"Ship To:\s*([\s\S]*?)Buyer Name",
        text,
        flags=re.I
    )
    if m:
        block = m.group(1)
        flat = " ".join(
            ln.strip() for ln in block.splitlines()
            if ln.strip() and not ln.lower().startswith("gb")
        )
        return flat

    return (
        "Cable Services Limited, Bridge House, Bridge Road, Wrexham Industrial Estate, Wrexham LL13 9PS, UK"
    )


# ---------------------------------------------------------------------------
# LINE EXTRACTION
# ---------------------------------------------------------------------------

def _to_float(num: str) -> float:
    return float(num.replace(",", ""))


def _extract_lines(text: str):
    """
    Cable Services multi-line SAP-like table.
    Format:

    5.00 EA 11/02/2025 027185 41.7300 EA 208.65
    BAH-038080985
    <long description>
    Part No.: EB9976-000
    """

    # Main numeric pattern
    pattern = re.compile(
        r"([\d\.,]+)\s+EA\s+(\d{2}\/\d{2}\/\d{4})\s+([A-Za-z0-9\/\-]+)\s+"
        r"([\d\.,]+)\s+EA\s+([\d\.,]+)",
        flags=re.I
    )

    lines = []
    item_counter = 1

    for m in pattern.finditer(text):
        qty_raw = m.group(1)
        date_raw = m.group(2)
        item_id = m.group(3)
        price_raw = m.group(4)
        total_raw = m.group(5)

        quantity = _to_float(qty_raw)
        price = _to_float(price_raw)
        line_value = _to_float(total_raw)
        delivery_date = date_raw.replace("/", ".")

        # Extract description + TE PN
        seg = text[m.end(): m.end() + 300]

        # First non-empty line = description
        description = ""
        desc_lines = [ln.strip() for ln in seg.splitlines() if ln.strip()]
        if desc_lines:
            description = desc_lines[0]

        # TE Part Number via "Part No.:"
        te_part = ""
        te_m = re.search(r"Part No\.\s*[: ]\s*([A-Za-z0-9\-]+)", seg, flags=re.I)
        if te_m:
            te_part = te_m.group(1).strip()

        lines.append({
            "item_no": str(item_counter),
            "customer_product_no": item_id,
            "description": description,
            "quantity": quantity,
            "uom": "EA",
            "price": price,
            "line_value": line_value,
            "te_part_number": te_part,
            "manufacturer_part_no": te_part,
            "delivery_date": delivery_date,
        })

        item_counter += 1

    return lines


# ---------------------------------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------------------------------

def parse_cable_services(text: str) -> dict:
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "Cable Services Limited",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    lines = _extract_lines(text)

    return {
        "header": header,
        "lines": lines,
    }
