import re
from typing import List, Dict, Any


# ---------------------------------------------------------------------------
# ROW PATTERN
# ---------------------------------------------------------------------------

ROW_PATTERN = re.compile(
    r"^\s*(?P<item>\d{1,4})\s+"
    r"(?P<part>\S+)\s+"
    r"(?P<desc>.+?)\s+"
    r"(?P<qty>\d+(?:[.,]\d+)?)\s+"
    r"(?P<uom>Stck|STK|[A-Z]{2,5})\s+"
    r"(?P<total>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s*$",
    re.IGNORECASE | re.MULTILINE
)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _to_float(value: str) -> float:
    if value is None:
        return 0.0
    value = value.replace(".", "").replace(",", ".")
    return float(value)


# ---------------------------------------------------------------------------
# MAIN ENGINE
# ---------------------------------------------------------------------------

def parse_lines(text: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    lines_split = text.splitlines()

    for match in ROW_PATTERN.finditer(text):

        item_no = match.group("item")
        part_no = match.group("part")
        raw_desc = match.group("desc").strip()
        qty = match.group("qty")
        uom = match.group("uom")
        total = match.group("total")

        # -------------------------------------------------------------------
        # DELIVERY DATE (look 3 lines above for Liefertermin)
        # -------------------------------------------------------------------
        delivery_date = ""
        match_line_text = match.group(0).strip()

        for i, line in enumerate(lines_split):
            if match_line_text in line:
                for j in range(max(0, i - 3), i):
                    dt_match = re.search(
                        r"Liefertermin\s*:\s*(\d{2}\.\d{2}\.\d{4})",
                        lines_split[j],
                        flags=re.IGNORECASE,
                    )
                    if dt_match:
                        delivery_date = dt_match.group(1)
                        break
                break

        # -------------------------------------------------------------------
        # UNIT PRICE (last decimal number inside description)
        # -------------------------------------------------------------------
        unit_price = None
        unit_price_match = re.search(r"(\d+(?:[.,]\d+))\s*$", raw_desc)
        if unit_price_match:
            unit_price = _to_float(unit_price_match.group(1))

        # -------------------------------------------------------------------
        # BUILD RESULT ROW
        # -------------------------------------------------------------------
        results.append({
            "item_no": item_no,
            "customer_product_no": part_no,
            "description": raw_desc,
            "quantity": _to_float(qty),
            "uom": uom,
            "price": unit_price,
            "line_value": _to_float(total),
            "te_part_number": part_no,
            "manufacturer_part_no": part_no,
            "delivery_date": delivery_date,
        })

    return results