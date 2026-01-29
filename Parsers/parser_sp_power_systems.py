import re
from typing import Dict, List, Any, Optional


def detect_sp_power_systems(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return ("SP DISTRIBUTION PLC" in t) or ("SCOTTISHPOWER" in t) or ("CALL-OFF ORDER" in t)


REQUIRED_HEADER_KEYS = ["po_number", "po_date", "customer_name", "buyer", "delivery_address"]


def _nf(v: Optional[str]) -> str:
    if v is None:
        return "Not found"
    s = str(v).strip()
    return s if s else "Not found"


def _clean_ws(s: Optional[str]) -> str:
    if not s:
        return "Not found"
    return " ".join(str(s).split()).strip()


def _find_first(patterns, text: str, flags=0) -> Optional[str]:
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            return m.group(m.lastindex).strip() if m.lastindex else m.group(0).strip()
    return None


def _norm_num(x: str) -> str:
    if not x:
        return "Not found"
    s = x.strip().replace(" ", "")
    # 1,378.37 -> 1378.37
    if re.match(r"^\d{1,3}(?:,\d{3})+(?:\.\d+)?$", s):
        s = s.replace(",", "")
        return s
    # 1.378,37 -> 1378.37
    if re.match(r"^\d{1,3}(?:\.\d{3})+(?:,\d+)?$", s):
        s = s.replace(".", "").replace(",", ".")
        return s
    return s.replace(",", ".")


def _parse_lines(text: str) -> List[Dict[str, Any]]:
    """
    Typical SP call-off order:
      Item Code Quantity / Unit Unit price Base Quantity Amount
      00010 JT BRANCH TRANSITION ...
      ...
      00010 30980279 5 ST 1,378.37 6,891.85
    We merge:
      - item_no = 00010 (or as printed)
      - te_part_number = numeric item code (e.g., 30980279) if present
      - description = text between the item header line and the numeric detail line (best-effort)
      - quantity, uom from detail line
    """
    rows: List[Dict[str, Any]] = []

    # Build a map of item_no -> description block
    desc_map = {}

    # Find lines that look like: "00010 JT BRANCH TRANSITION ..."
    header_item_pat = re.compile(r"^\s*(\d{5})\s+([A-Z].+)$", re.IGNORECASE | re.MULTILINE)
    for m in header_item_pat.finditer(text):
        item = m.group(1).strip()
        rest = m.group(2).strip()

        # collect subsequent lines until we hit a detail numeric line or Total/FRAMEWORK section
        tail = text[m.end():]
        stop = re.search(r"\n\s*\d{5}\s+\d{5,}\s+\d", tail)  # next detail line
        stop2 = re.search(r"\n\s*Total\b|\n\s*FRAMEWORK\b", tail, flags=re.IGNORECASE)
        candidates = [x.start() for x in [stop, stop2] if x]
        end = min(candidates) if candidates else 300
        block = (rest + "\n" + tail[:end]).strip()

        # keep meaningful lines
        lines = []
        for ln in block.splitlines():
            s = ln.strip()
            if not s:
                continue
            if re.search(r"^(Description|Item Code|Quantity|Unit price|Amount|Dear Sirs)$", s, re.IGNORECASE):
                continue
            lines.append(s)

        desc_map[item] = _clean_ws(" ".join(lines)) if lines else item

    # Detail line: "00010 30980279 5 ST 1,378.37 6,891.85"
    detail_pat = re.compile(
        r"^\s*(?P<item>\d{5})\s+(?P<code>\d{5,})\s+"
        r"(?P<qty>\d+(?:[.,]\d+)?)\s+(?P<uom>[A-Z]{1,6})\s+"
        r"(?P<unit>[\d.,]+)\s+(?P<amt>[\d.,]+)\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    for m in detail_pat.finditer(text):
        item = m.group("item").strip()
        code = m.group("code").strip()
        qty = _norm_num(m.group("qty"))
        uom = m.group("uom").upper().strip()
        desc = desc_map.get(item, code)

        rows.append({
            "item_no": item,
            "te_part_number": code,
            "description": desc,
            "quantity": qty,
            "uom": uom,
        })

    if rows:
        return rows

    # Fallback: try any "Total GBP" doc with one numeric line
    fb = re.search(r"Total\s+GBP\s+([\d.,]+)", text, flags=re.IGNORECASE)
    if fb:
        return [{
            "item_no": "1",
            "te_part_number": "Not found",
            "description": "Not found",
            "quantity": "1",
            "uom": "EA",
        }]

    return [{
        "item_no": "1",
        "te_part_number": "Not found",
        "description": "Not found",
        "quantity": "1",
        "uom": "EA",
    }]


def parse_sp_power_systems(text: str) -> Dict[str, Any]:
    header = {
        "po_number": "Not found",
        "po_date": "Not found",
        "customer_name": "SP Distribution PLC",
        "buyer": "Not found",
        "delivery_address": "Not found",
    }

    if not text:
        return {"header": header, "lines": []}

    header["po_number"] = _nf(_find_first(
        [r"\bRef\.\s*:\s*(\d+)\b", r"\bCall-off Order\s*Ref\.\s*:\s*(\d+)\b"],
        text,
        flags=re.IGNORECASE,
    ))

    header["po_date"] = _nf(_find_first(
        [r"\bDate:\s*(\d{2}\.\d{2}\.\d{4})\b"],
        text,
        flags=re.IGNORECASE,
    ))

    buyer = _find_first(
        [r"\bManager\s*\n\s*([A-Z][A-Z\s'\-]+)\b", r"\bManager\s+([A-Z][A-Z\s'\-]+)\b"],
        text,
        flags=re.IGNORECASE,
    )
    header["buyer"] = _nf(_clean_ws(buyer) if buyer else None)

    delivery = _find_first(
        [r"\bSHIP TO LOCATION\s*(.*?)(?:\n\s*Delivery date:|\n\s*Subject|\n\s*Dear\s+Sirs)"],
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    header["delivery_address"] = _nf(_clean_ws(delivery) if delivery else None)

    lines = _parse_lines(text)

    for k in REQUIRED_HEADER_KEYS:
        header[k] = _nf(header.get(k))

    return {"header": header, "lines": lines}
