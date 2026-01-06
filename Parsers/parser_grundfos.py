# ============================================================
# parser_grundfos.py – V12.5 (2025-12-09)
#
# Customer: GRUNDFOS OPERATIONS A/S
#
# Modelled on parser_antalis:
#  - EU number helpers
#  - Robust detection
#  - Header extraction (PO no, date, buyer, delivery address)
#  - Line extraction with EU quantity/price handling
#
# IMPORTANT CUSTOMER-SPECIFIC RULE:
#   - System UoM is the numeric denominator (e.g. 1000), not "PC".
#   - Price is per UoM (e.g. 70.27 per 1000).
#   - Check: quantity * price / uom == line_value (within rounding).
#
# Example line:
#   1 4.400 PC 97515861 27.02.2025         70,27 /           309,19
#   Vend.mat.no.: 160181-2 1.000  PC
#   Cable Shoe Ring Tongue 160181-2
#
# → quantity = 4400
#   uom      = "1000"
#   price    = 70.27
#   line_val = 309.19
# ============================================================

import re
from typing import List, Dict, Any


# ------------------------------------------------------------
# Helpers for EU number formats
# ------------------------------------------------------------

def eu_to_float(value: str) -> float:
    """Convert EU number format to float: '3.834,60' -> 3834.60"""
    if not value:
        return 0.0
    return float(value.replace(".", "").replace(",", "."))


def eu_to_int(value: str) -> int:
    """
    Convert EU formatted integer with dot separators to int:
        '4.400' -> 4400
        '1.000' -> 1000
    """
    if not value:
        return 0
    return int(round(float(value.replace(".", "").replace(",", "."))))


# ------------------------------------------------------------
# Parser detection
# ------------------------------------------------------------

def detect_grundfos(text: str) -> bool:
    """
    Minimal stable rule for Grundfos Operations POs:
      - must contain 'GRUNDFOS OPERATIONS A/S'
      - must contain 'Poul Due Jensens Vej' (HQ address)
    """
    t = text.upper()
    return "GRUNDFOS OPERATIONS A/S" in t and "POUL DUE JENSENS VEJ" in t


# ------------------------------------------------------------
# Header helpers
# ------------------------------------------------------------

def _extract_po_number(text: str) -> str:
    """
    Typical patterns:
      'Order No. 4517095789'
      or 'Order No.: 4517095789'
    """
    m = re.search(r"Order\s+No\.?\s*[: ]\s*(\d+)", text, flags=re.I)
    if m:
        return m.group(1).strip()

    # Fallback: long 8–12 digit sequence near 'Order No'
    m = re.search(r"Order\s+No.*?(\b\d{8,12}\b)", text, flags=re.I | re.S)
    return m.group(1).strip() if m else ""


def _extract_po_date(text: str) -> str:
    """
    Pattern:
      'Date: 19.02.2025'
    """
    m = re.search(r"Date\s*[: ]\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.I)
    return m.group(1).strip() if m else ""


def _extract_customer_name(text: str) -> str:
    """
    Grundfos header always has:
      GRUNDFOS OPERATIONS A/S
    """
    return "Grundfos Operations A/S"


def _extract_buyer(text: str) -> str:
    """
    From line like:
      Our ref.: Signe Drongesen / 4517095789
    """
    m = re.search(
        r"Our\s+ref\.\s*:\s*([^\n/]+)",
        text,
        flags=re.I,
    )
    if not m:
        return ""
    return m.group(1).strip()


def _extract_delivery_address(text: str) -> str:
    """
    Block between:
        Place of delivery:
    and the next 'Marking of shipment' / VAT / Vendor or end.
    """
    m = re.search(
        r"Place of delivery\s*:\s*(.*?)(?:Marking of shipment|VAT no\.|Vendor No\.|$)",
        text,
        flags=re.I | re.S,
    )
    if not m:
        return ""

    block = m.group(1)
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    return " ".join(lines)


# ------------------------------------------------------------
# Line-level helpers
# ------------------------------------------------------------

def _extract_lines(text: str) -> List[Dict[str, Any]]:
    """
    Grundfos line example:

        1 4.400 PC 97515861 27.02.2025         70,27 /           309,19
        Vend.mat.no.: 160181-2 1.000  PC
        Cable Shoe Ring Tongue 160181-2

    We assume:
      - position:   int at start of line
      - qty:        EU number
      - base UoM printed as 'PC' but our system UoM is numeric denominator (1000)
      - product no: first number after base UoM (here: 97515861)
      - delivery date: dd.mm.yyyy
      - the pattern 'price / total' at end of first line:
            70,27 / 309,19
      - Vend.mat.no.: TE part (trusted as given)
      - same line as Vend.mat.no. contains numeric denominator and 'PC':
            160181-2 1.000  PC
        → denominator = 1000 → our UoM
      - next non-empty description line: description
    """

    lines: List[Dict[str, Any]] = []

    all_lines = [ln.rstrip() for ln in text.splitlines()]

    # Item line: position, qty, base UoM, customer product, delivery date, then price / total at the tail
    item_pattern = re.compile(
        r"^\s*(?P<pos>\d+)\s+"
        r"(?P<qty>[\d\.,]+)\s+"
        r"(?P<base_uom>[A-Z]{2,3})\s+"
        r"(?P<cust>\d+)\s+"
        r"(?P<date>\d{2}\.\d{2}\.\d{4})"
        r"(?P<rest>.*)$"
    )

    for idx, ln in enumerate(all_lines):
        m = item_pattern.match(ln)
        if not m:
            continue

        pos = m.group("pos").strip()
        qty_raw = m.group("qty").strip()
        base_uom = m.group("base_uom").strip()  # not used in our system, but kept if ever needed
        cust_mat = m.group("cust").strip()
        deliv_date = m.group("date").strip()
        rest = m.group("rest") or ""

        # Extract price and line total from "rest" using 'price / total'
        price = 0.0
        line_total = 0.0
        mt = re.search(
            r"([\d\.,]+)\s*/\s*([\d\.,]+)",
            rest,
            flags=re.I,
        )
        if mt:
            price = eu_to_float(mt.group(1))
            line_total = eu_to_float(mt.group(2))

        qty = eu_to_int(qty_raw)

        # Defaults in case we can't see a denominator line
        uom_num = 1  # fallback; will be overridden in Grundfos files

        # Look ahead for Vend.mat.no., denominator and description
        te_part = ""
        desc = ""

        for j in range(idx + 1, min(idx + 6, len(all_lines))):
            ln2 = all_lines[j].strip()
            if not ln2:
                continue

            # Vend.mat.no. and denominator on same line
            vm = re.search(r"Vend\.mat\.no\.\s*:\s*([A-Za-z0-9\-\./]+)(.*)$", ln2, flags=re.I)
            if vm:
                te_part = vm.group(1).strip()
                tail = vm.group(2) or ""

                # Try to find numeric denominator (e.g. 1.000)
                # Example tail: " 1.000  PC"
                parts = tail.split()
                for p in parts:
                    # EU thousands numeric pattern
                    if re.match(r"^\d{1,3}(\.\d{3})*$", p):
                        uom_num = eu_to_int(p)
                        break

                # Description is usually next non-empty line
                for k in range(j + 1, min(j + 5, len(all_lines))):
                    ln3 = all_lines[k].strip()
                    if ln3:
                        desc = ln3
                        break
                break

        # If denominator not found, fall back to 1 so we don't divide by zero later
        if uom_num <= 0:
            uom_num = 1

        # Optional validation / recomputation:
        # If line_total is zero but we have price & qty & uom_num, compute it.
        if line_total == 0.0 and price and qty:
            line_total = round(qty * price / uom_num, 2)

        line_dict: Dict[str, Any] = {
            "item_no": pos,
            "customer_product_no": cust_mat,
            "description": desc,
            "quantity": qty,
            # IMPORTANT: system UoM is numeric denominator
            "uom": str(uom_num),
            # Price per UoM (e.g. per 1000)
            "price": price,
            "line_value": line_total,
            "te_part_number": te_part,
            "manufacturer_part_no": te_part,
            "delivery_date": deliv_date,
        }

        lines.append(line_dict)

    # Fallback if nothing parsed
    if not lines:
        lines.append({
            "item_no": "1",
            "customer_product_no": "",
            "description": "Fallback (no Grundfos line parsed)",
            "quantity": 1,
            "uom": "1",
            "price": 0.0,
            "line_value": 0.0,
            "te_part_number": "",
            "manufacturer_part_no": "",
            "delivery_date": "",
        })

    return lines


# ------------------------------------------------------------
# Main entry point (used by engine)
# ------------------------------------------------------------

def parse_grundfos(text: str) -> Dict[str, Any]:
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": _extract_customer_name(text),
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    lines = _extract_lines(text)

    return {
        "header": header,
        "lines": lines,
    }
