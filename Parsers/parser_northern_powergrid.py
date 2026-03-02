import re
from typing import Dict, List, Any, Optional


# ---------------------------------------------------------------------------
# DETECT
# ---------------------------------------------------------------------------

def detect_northern_powergrid(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return "NORTHERN POWERGRID" in t


# ---------------------------------------------------------------------------
# HEADER HELPERS
# ---------------------------------------------------------------------------

REQUIRED_HEADER_KEYS = [
    "po_number",
    "po_date",
    "customer_name",
    "buyer",
    "delivery_address",
]


def _nf(v: Optional[str]) -> str:
    if v is None:
        return "Not found"
    s = str(v).strip()
    return s if s else "Not found"


def _find_first(pattern: str, text: str, flags=0) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# LINES (YOUR ORIGINAL LOGIC — UNCHANGED)
# ---------------------------------------------------------------------------

def _extract_lines(text: str):
    lines = text.splitlines()
    results = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        m = re.match(
            r"^(\d+)\s+(\d+)\s+Needed:\s+(\d+)\s+([A-Z]+)\s+([\d,\.]+)\s+[A-Z]\s+([\d,\.]+)",
            line,
        )

        if m:
            item_no = m.group(1)
            part = m.group(2)
            quantity = m.group(3)
            uom = m.group(4)
            unit_price = m.group(5)
            line_total = m.group(6)

            delivery_date = ""
            description_lines = []

            if i + 1 < len(lines):
                dt_line = lines[i + 1].strip()
                d = re.match(r"^(\d{2}-[A-Z]{3}-\d{4})", dt_line)
                if d:
                    delivery_date = d.group(1)
                    i += 1

            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()

                if re.match(r"^\d+\s+\d+", next_line):
                    break
                if next_line.startswith("Total:"):
                    break

                if next_line:
                    description_lines.append(next_line)

                j += 1

            description = " ".join(description_lines).strip()

            results.append({
                "item_no": item_no,
                "customer_product_no": part,
                "description": description,
                "quantity": float(quantity),
                "uom": uom,
                "price": float(unit_price.replace(",", "")),
                "line_value": float(line_total.replace(",", "")),
                "te_part_number": part,
                "manufacturer_part_no": part,
                "delivery_date": delivery_date,
            })

            i = j
            continue

        i += 1

    return results


# ---------------------------------------------------------------------------
# PARSE (FRAMEWORK ENTRY POINT)
# ---------------------------------------------------------------------------

def parse_northern_powergrid(text: str) -> Dict[str, Any]:

    header = {
        "po_number": "Not found",
        "po_date": "Not found",
        "customer_name": "Northern Powergrid",
        "buyer": "Not found",
        "delivery_address": "Not found",
    }

    if not text:
        return {"header": header, "lines": []}

    # Basic PO number extraction (adjust if needed)
    header["po_number"] = _nf(_find_first(r"\bPO\s*Number\s*[: ]\s*([A-Z0-9\-]+)", text, re.IGNORECASE))

    # Basic date extraction (adjust if needed)
    header["po_date"] = _nf(_find_first(r"\b(\d{2}-[A-Z]{3}-\d{4})\b", text))

    lines = _extract_lines(text)

    for k in REQUIRED_HEADER_KEYS:
        header[k] = _nf(header.get(k))

    return {
        "header": header,
        "lines": lines,
    }