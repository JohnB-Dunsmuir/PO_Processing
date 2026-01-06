import re

# ---------------------------------------------------------------------------
# DETECTION
# ---------------------------------------------------------------------------

def detect_sse_stock(text: str) -> bool:
    """
    Detect SSE Stock Ltd purchase orders.
    """
    if not text:
        return False

    t = text.lower()
    triggers = [
        "sse stock ltd",
        "standard purchase order",
        "inveralmond house",
        "dunn,mr ryan",
        "supplier item",
    ]
    return any(trig in t for trig in triggers)


# ---------------------------------------------------------------------------
# HEADER EXTRACTION
# ---------------------------------------------------------------------------

def _extract_po_number(text: str) -> str:
    m = re.search(r"Order\s+(\d+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    m = re.search(r"Order Date\s+([0-9]{2}-[A-Za-z]{3}-[0-9]{4})", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_buyer(text: str) -> str:
    # Buyer Dunn,Mr Ryan
    m = re.search(r"Buyer\s+([A-Za-z ,\.]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    """
    'Ship To:' block on page 1.
    If missing, use head-office fallback.
    """
    m = re.search(
        r"Ship To:\s*([\s\S]*?)Bill To:",
        text,
        flags=re.I
    )
    if m:
        block = m.group(1)
        flat = " ".join(line.strip() for line in block.splitlines() if line.strip())
        return flat

    # Fallback to head office
    return (
        "SSE Stock Ltd, Inveralmond House, 200 Dunkeld Road, Perth PH1 3AQ, Scotland"
    )


# ---------------------------------------------------------------------------
# LINE EXTRACTION
# ---------------------------------------------------------------------------

def _extract_lines(text: str):
    """
    SSE lines structure:

    Line  StockNo  RequiredBy  Qty  UoM  UnitPrice  Amount
    Supplier Item: XXXX
    Description...
    """

    # Match the line header
    line_header = re.compile(
        r"(\d+)\s+"                # item number
        r"([A-Za-z0-9]+)\s+"       # stock number
        r"Required By:\s*([0-9\-A-Za-z: ]+)\s+"
        r"(\d+)\s+"                # quantity
        r"([A-Za-z]+)\s+"          # UOM
        r"([\d\.]+)\s+"            # unit price
        r"([\d\.,]+)",             # amount
        flags=re.I
    )

    lines = []

    for m in line_header.finditer(text):
        item_no = m.group(1)
        stock_no = m.group(2)
        req_by = m.group(3).strip()
        qty = m.group(4)
        uom = m.group(5)
        price = m.group(6)
        amount = m.group(7).replace(",", "")

        # Extract TE PN if "Supplier Item:" occurs near this line
        # Search up to 200 chars after match
        slice_start = m.end()
        slice_end = slice_start + 300
        segment = text[slice_start:slice_end]

        te_m = re.search(r"Supplier Item:\s*([A-Za-z0-9\-\_]+)", segment, flags=re.I)
        te_part = te_m.group(1) if te_m else ""

        # Extract description: text until next line header or end of segment
        desc_m = re.search(
            r"Supplier Item:.*?\n([\s\S]*?)(?=\n\d+\s+[A-Za-z0-9]+|$)",
            segment,
            flags=re.I
        )
        if desc_m:
            desc_block = " ".join(line.strip() for line in desc_m.group(1).splitlines() if line.strip())
        else:
            # fallback: take one or two lines of text
            desc_block = ""

        lines.append({
            "item_no": item_no,
            "customer_product_no": stock_no,
            "description": desc_block,
            "quantity": qty,
            "uom": uom,
            "price": price,
            "line_value": amount,
            "te_part_number": te_part,
            "manufacturer_part_no": te_part,
            "delivery_date": req_by,
        })

    return lines


# ---------------------------------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------------------------------

def parse_sse_stock(text: str) -> dict:
    """
    Return header + lines dict for unified engine v11.3.2.
    """

    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "SSE Stock Ltd",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    lines = _extract_lines(text)

    return {
        "header": header,
        "lines": lines,
    }
