# Parsers/parser_zollner.py
# Minimal deterministic parser for current Zollner layout

from __future__ import annotations
import re
from typing import Dict, Any, List


def detect_zollner(text: str) -> bool:
    return "Zollner Elektronik AG" in text


def _clean(v: str) -> str:
    return (v or "").strip()


def _norm_number(v: str) -> str:
    v = _clean(v)
    if not v:
        return ""
    v = v.replace(" ", "")
    v = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", v)
    v = v.replace(",", ".")
    return v


def parse_zollner(text: str) -> Dict[str, Any]:

    lines = text.splitlines()

    # ----------------------------
    # HEADER
    # ----------------------------

    po_number = ""
    po_date = ""
    buyer = ""

    # Combined PO number / date: 4505401669/11.02.2026
    for line in lines:
        m = re.match(r"\s*(\d{6,})/(\d{2}\.\d{2}\.\d{4})\s*$", line)
        if m:
            po_number = m.group(1)
            po_date = m.group(2)
            break

    # Buyer under "Contact Person"
    for i, line in enumerate(lines):
        if "Contact Person" in line:
            for j in range(i + 1, min(i + 5, len(lines))):
                candidate = _clean(lines[j])
                if candidate and not re.search(r"\d", candidate):
                    buyer = candidate
                    break
            break

    header = {
        "po_number": po_number or "Not found",
        "po_date": po_date or "Not found",
        "customer_name": "Zollner Elektronik AG",
        "buyer": buyer or "Not found",
        "delivery_address": "XX",
    }

    # ----------------------------
    # LINE ITEMS
    # ----------------------------

    lines_out: List[Dict[str, str]] = []

    for i, line in enumerate(lines):

        m = re.match(
            r"\s*(\d{5})\s+(\S+)\s+(\d+)\s+(\S+)\s+([\d,\.]+)\s+([\d,\.]+)",
            line,
        )

        if m:
            item_no = m.group(1)
            material = m.group(2)
            quantity = m.group(3)
            uom = m.group(4)
            price = m.group(5)
            line_value = m.group(6)

            description = ""
            manufacturer_part_no = ""

            # Next line = description
            if i + 1 < len(lines):
                description = _clean(lines[i + 1])

            # Manufacturer block
            for j in range(i + 1, min(i + 6, len(lines))):
                if "Manufacturer" in lines[j]:
                    if j + 1 < len(lines):
                        manu_line = _clean(lines[j + 1])
                        parts = manu_line.split()
                        if parts:
                            manufacturer_part_no = parts[-1]
                    break

            te_part_number = manufacturer_part_no

            lines_out.append({
                "item_no": item_no,
                "customer_product_no": material,
                "description": description,
                "quantity": _norm_number(quantity),
                "uom": uom,
                "price": _norm_number(price),
                "line_value": _norm_number(line_value),
                "te_part_number": te_part_number,
                "manufacturer_part_no": manufacturer_part_no,
                "delivery_date": "",
            })

    if not lines_out:
        lines_out.append({
            "item_no": "",
            "customer_product_no": "",
            "description": "",
            "quantity": "",
            "uom": "",
            "price": "",
            "line_value": "",
            "te_part_number": "",
            "manufacturer_part_no": "",
            "delivery_date": "",
        })

    return {
        "header": header,
        "lines": lines_out,
    }