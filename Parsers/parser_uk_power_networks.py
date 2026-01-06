# parser_uk_power_networks.py – V5 (engine 12.5)
# Calibrated on: "UK Power Networks.PDF"
#
# Behaviours:
# - Detects UK Power Networks PO by header text.
# - Extracts:
#     * po_number      → "Order number 4550780550"
#     * po_date        → "Date 16/09/2025"
#     * delivery_date  → "Delivery date 17/10/2025"
#     * buyer          → name before " / " after "Contact / Phone"
#     * delivery_address → block after "Delivery address" up to "Page 1 of"
# - Line items:
#     * item_no
#     * customer_product_no
#     * description (collapsed to single line)
#     * quantity
#     * uom
#     * price (unit price as float; engine formats for Excel)
#     * line_value (float)
#     * te_part_number (left blank for now)
#     * manufacturer_part_no (we reuse customer material number)
#     * delivery_date (copied from header for all lines)

import re
from typing import List, Dict, Any


# ---------- helpers ----------

def _to_float_money(val: str) -> float:
    """
    Convert a money string like "1,466.40" or "36.66" to float.
    We treat ',' as thousands separator and '.' as decimal point.
    """
    if not val:
        return 0.0
    val = val.strip()
    # remove spaces, then strip thousands commas
    val = val.replace(" ", "").replace(",", "")
    try:
        return float(val)
    except ValueError:
        return 0.0


def detect_uk_power_networks(text: str) -> bool:
    """
    Heuristic detection for UK Power Networks PO.
    """
    t = text.lower()
    return (
        "uk power networks (operations) ltd" in t
        and "purchase order" in t
        and "order number" in t
    )


# ---------- header extractors ----------

def _extract_po_number(text: str) -> str:
    """
    Look for:
        Order number
        4550780550
    or inline variants.
    """
    m = re.search(
        r"Order number\s+(\d+)",
        text,
        flags=re.I,
    )
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    """
    Look for:
        Date
        16/09/2025
    We grab the first DD/MM/YYYY after 'Date'.
    """
    m = re.search(
        r"\bDate\s+(\d{2}/\d{2}/\d{4})",
        text,
        flags=re.I,
    )
    return m.group(1) if m else ""


def _extract_delivery_date(text: str) -> str:
    """
    Look for:
        Delivery date
        17/10/2025
    """
    m = re.search(
        r"Delivery date\s+(\d{2}/\d{2}/\d{4})",
        text,
        flags=re.I,
    )
    return m.group(1) if m else ""


def _extract_buyer(text: str) -> str:
    """
    Buyer rule:
      - Find 'Contact / Phone'
      - Buyer is the next non-blank line
      - If line contains " / ", take the part before it as the name.
    """
    lines = text.splitlines()
    idx = -1
    for i, raw in enumerate(lines):
        if "Contact / Phone" in raw:
            idx = i
            break

    if idx == -1:
        return ""

    for j in range(idx + 1, len(lines)):
        candidate = lines[j].strip()
        if not candidate:
            continue
        # Example: "Nichola Hutcheon / +44 (0)1376 509560"
        if " / " in candidate:
            candidate = candidate.split(" / ", 1)[0].strip()
        return candidate

    return ""


def _extract_delivery_address(text: str) -> str:
    """
    Block between:
        Delivery date
        Delivery address
        UK PN - Maidstone Logistics Centre
        ...
    and "Page 1 of".
    """
    m = re.search(
        r"Delivery address\s*(.*?)(?:Page\s+1\s+of|\Z)",
        text,
        flags=re.S | re.I,
    )
    if not m:
        return ""

    block = m.group(1)
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    return " ".join(lines)


# ---------- line extractor ----------

def _extract_lines(text: str, default_delivery_date: str) -> List[Dict[str, Any]]:
    """
    Example (flattened) content around the line:

        10
        02758J
        LV 185 TO 300MM TRANSITION MAINS BRANCH

        40.00

        KIT

        36.66
        GBP

        1,466.40

        Suppliers ref; BAH-038081651
        Waveform to PILC Transition 240 to 300mm

    We use a fairly tolerant regex that:
      - Captures item number
      - Captures material (customer product)
      - Captures a free-form description segment
      - Captures quantity, UOM, unit price, and line total
    """
    lines: List[Dict[str, Any]] = []

    pattern = re.compile(
        r"(?P<item>\d{2})\s+"
        r"(?P<mat>\S+)\s+"
        r"(?P<desc>.+?)"
        r"(?P<qty>\d+(?:\.\d+)?)\s+"
        r"(?P<uom>[A-Z]{2,3})\s+"
        r"(?P<price>[\d,\.]+)\s+GBP\s+"
        r"(?P<total>[\d,\.]+)",
        flags=re.I | re.S,
    )

    for m in pattern.finditer(text):
        raw_desc = m.group("desc")
        desc = " ".join(
            ln.strip()
            for ln in raw_desc.splitlines()
            if ln.strip()
        )

        qty = float(m.group("qty"))
        uom = m.group("uom").upper()
        price_val = _to_float_money(m.group("price"))
        total_val = _to_float_money(m.group("total"))

        lines.append(
            {
                "item_no": m.group("item"),
                "customer_product_no": m.group("mat"),
                "description": desc,
                "quantity": qty,
                "uom": uom,
                "price": price_val,
                "line_value": total_val,
                # TE/cust part mapping not yet known; leave TE blank for now
                "te_part_number": "",
                "manufacturer_part_no": m.group("mat"),
                "delivery_date": default_delivery_date,
            }
        )

    return lines


# ---------- main entry point ----------

def parse_uk_power_networks(text: str) -> Dict[str, Any]:
    """
    Main UK Power Networks parser for V12 engine.
    Returns:
      {
        "header": {...},
        "lines": [ {...}, ... ]
      }
    """
    po_number = _extract_po_number(text)
    po_date = _extract_po_date(text)
    delivery_date = _extract_delivery_date(text)
    buyer = _extract_buyer(text)
    delivery_address = _extract_delivery_address(text)

    header = {
        "po_number": po_number,
        "po_date": po_date,               # <-- drives "Date on PO"
        "customer_name": "UK Power Networks",
        "buyer": buyer,
        "delivery_address": delivery_address,
    }

    lines = _extract_lines(text, default_delivery_date=delivery_date)

    return {
        "header": header,
        "lines": lines,
    }
