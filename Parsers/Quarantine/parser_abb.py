import re

# ---------------------------------------------------------------------------
# DETECTION
# ---------------------------------------------------------------------------

def detect_abb(text: str) -> bool:
    """
    Detect ABB Inc. purchase orders.
    """
    if not text:
        return False

    t = text.lower()
    triggers = [
        "abb robotics",
        "abb inc",
        "purchase order",
        "vendor number",
        "dock date",
        "peter wisniewski",
    ]
    return any(trig in t for trig in triggers)


# ---------------------------------------------------------------------------
# HEADER EXTRACTION
# ---------------------------------------------------------------------------

def _extract_po_number(text: str) -> str:
    m = re.search(r"Purchase Order[: ]+([0-9]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"Creation Date\s*[: ]+([0-9A-Z\-]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_buyer(text: str) -> str:
    m = re.search(r"Buyer[: ]+([A-Za-z ,\.]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    """
    Extract 'Ship To:' block. If missing, fallback to header address.
    """
    m = re.search(
        r"Ship To:\s*([\s\S]*?)Sold To:",
        text,
        flags=re.I
    )

    if m:
        block = m.group(1)
        flat = " ".join(
            ln.strip() for ln in block.splitlines()
            if ln.strip() and not ln.lower().startswith("ship to")
        )
        return flat

    return (
        "ABB Robotics Supply Unit, 1250 Brown Road, Auburn Hills MI 48326, USA"
    )


# ---------------------------------------------------------------------------
# LINE EXTRACTION
# ---------------------------------------------------------------------------

def _to_float(num: str) -> float:
    return float(num.replace(",", ""))


def _extract_lines(text: str):
    """
    Extract ABB SAP-style line items.

    Pattern:
    Item 10
    Part No: X
    Description: ...
    Vendor Part No: Y
    Qty: 120.000 EA USD 8.9920 1,079.04
    Dock Date: 20-MAY-2025
    """

    # Match item header rows
    header_regex = re.compile(
        r"Item\s+(\d+)[\s\S]*?Part No[: ]+([A-Za-z0-9\-\_]+)[\s\S]*?"
        r"Description[: ]+([\s\S]*?)(?=Vendor Part No|Manufacturer Part No|Material Revision)",
        flags=re.I
    )

    lines = []

    for hdr in header_regex.finditer(text):
        item_no = hdr.group(1).strip()
        cust_pn = hdr.group(2).strip()

        # Clean description block
        desc_block = " ".join(
            ln.strip() for ln in hdr.group(3).splitlines() if ln.strip()
        )

        # Vendor Part No.
        seg = text[hdr.end(): hdr.end() + 400]
        te = ""
        te_m = re.search(r"Vendor Part No[: ]+([A-Za-z0-9\-\_]+)", seg, flags=re.I)
        if te_m:
            te = te_m.group(1).strip()

        # Quantity, price, total
        qty = uom = price = total = ""

        num_m = re.search(
            r"(\d+\.\d+)\s+([A-Z]{2})\s+USD\s+([\d\.]+)\s+([\d\.,]+)",
            seg,
            flags=re.I
        )
        if num_m:
            qty_raw = num_m.group(1)
            qty = _to_float(qty_raw)
            uom = num_m.group(2).strip()
            price = _to_float(num_m.group(3))
            total = _to_float(num_m.group(4))

        # Delivery date → ABB Dock Date
        d_m = re.search(r"Dock date[: ]+([0-9A-Z\-]+)", seg, flags=re.I)
        delivery_date = d_m.group(1).strip() if d_m else ""

        lines.append({
            "item_no": item_no,
            "customer_product_no": cust_pn,
            "description": desc_block,
            "quantity": qty,
            "uom": uom,
            "price": price,
            "line_value": total,
            "te_part_number": te,
            "manufacturer_part_no": te,
            "delivery_date": delivery_date,
        })

    return lines


# ---------------------------------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------------------------------

def parse_abb(text: str) -> dict:
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "ABB Inc.",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    lines = _extract_lines(text)

    return {
        "header": header,
        "lines": lines,
    }
