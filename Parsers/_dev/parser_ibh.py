import re

# ---------------------------------------------------------------------------
# DETECTION (Corrected)
# ---------------------------------------------------------------------------

def detect_ibh(text: str) -> bool:
    """
    Detect ONLY IBH Elektrotechnik GmbH purchase orders.

    Previously this parser matched on generic signals like "bestellung"
    which caused false positives with many German customers (Phoenix Contact, ABB, etc).

    This version uses strict positive matches + explicit negative guards
    to ensure ONLY IBH triggers this parser.
    """
    if not text:
        return False

    t = text.lower()

    # Positive identifiers unique to the real IBH customer
    positive = (
        "ibh elektrotechnik gmbh" in t
        or "ibh elektrotechnik" in t
        or "gutenbergring 35" in t      # IBH's HQ address
        or "22848 norderstedt" in t     # IBH's postal code
    )

    # Negative guardrails (avoid misdetecting other German manufacturers/utilities)
    negative = (
        "phoenix contact" in t
        or "abb" in t
        or "ds smith" in t
        or "stadtwerke" in t
        or "westnetz" in t
        or "bayernwerk" in t
        or "henrichter" in t
        or "sonepar" in t
    )

    return positive and not negative


# ---------------------------------------------------------------------------
# HEADER EXTRACTION
# ---------------------------------------------------------------------------

def _extract_po_number(text: str) -> str:
    # Expected: "Nr 6026547"
    m = re.search(r"Nr\s+([0-9]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    # Expected: "vom 08.08.2025"
    m = re.search(r"vom\s+(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_buyer(text: str) -> str:
    # "Ansprechpartner Victoria Sophie Schlüter"
    m = re.search(r"Ansprechpartner\s+([A-Za-zÄÖÜäöüß ]+)", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_delivery_address(text: str) -> str:
    """
    IBH provides no delivery address in its PO format.
    Use HQ fallback.
    """
    return "IBH Elektrotechnik GmbH, Gutenbergring 35, 22848 Norderstedt, Germany"


# ---------------------------------------------------------------------------
# LINE EXTRACTION
# ---------------------------------------------------------------------------

def _to_float_eu(num: str) -> float:
    return float(num.replace(".", "").replace(",", "."))


def _extract_line(text: str) -> dict:
    """
    Format example:

    Pos 10
    020.000038  3.003 m  49,63  1.490,39
    Ihre Referenz: 9800944001
    RNF-100-1/2-0-FSP
    """

    # Header: pos, material, qty, price, total
    hdr = re.search(
        r"(\d+)\s+([0-9\.]{5,})\s+([\d\.,]+)\s*m\s+([\d\.,]+)\s+([\d\.,]+)",
        text,
        flags=re.I
    )
    if not hdr:
        return {}

    item_no = hdr.group(1)
    mat_code = hdr.group(2)
    qty_raw = hdr.group(3)
    price_raw = hdr.group(4)
    total_raw = hdr.group(5)

    quantity = qty_raw.replace(".", "").replace(",", ".")
    price = _to_float_eu(price_raw)
    line_value = _to_float_eu(total_raw)

    # TE part via "Ihre Referenz:"
    te = ""
    te_m = re.search(r"Ihre Referenz[: ]+([A-Za-z0-9\-\/]+)", text, flags=re.I)
    if te_m:
        te = te_m.group(1).strip()

    # Description: first non-empty line after "Ihre Referenz"
    desc = ""
    seg = text[te_m.end():te_m.end()+300] if te_m else ""
    for ln in seg.splitlines():
        ls = ln.strip()
        if ls:
            desc = ls
            break

    # IBH gives KW delivery window only → leave blank
    delivery_date = ""

    return {
        "item_no": item_no,
        "customer_product_no": mat_code,
        "description": desc,
        "quantity": quantity,
        "uom": "M",
        "price": price,
        "line_value": line_value,
        "te_part_number": te,
        "manufacturer_part_no": te,
        "delivery_date": delivery_date,
    }


# ---------------------------------------------------------------------------
# MAIN PARSER
# ---------------------------------------------------------------------------

def parse_ibh(text: str) -> dict:
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "IBH Elektrotechnik GmbH",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    line = _extract_line(text)
    lines = [line] if line else []

    return {
        "header": header,
        "lines": lines,
    }
