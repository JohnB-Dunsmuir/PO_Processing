import re
from typing import Dict, List, Any, Optional


def detect_northern_powergrid(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return "NORTHERN POWERGRID" in t or "BLANKET RELEASE" in t


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


def _parse_lines(text: str) -> List[Dict[str, Any]]:
    """
    Expected layout:
      Line Part Number / Description Delivery Date/Time Quantity UOM Unit Price ...
      35 163664 Needed:
      30-SEP-2025 16:30:00
      15 EACH 94 N 1,410.00
      <description lines...>
    We'll parse:
      - item_no = line number
      - te_part_number = part number (as printed)
      - quantity, uom
      - description collected from subsequent lines until "Ship To:" or "Total:"
    """
    rows: List[Dict[str, Any]] = []

    # Anchor after "Line Part Number" if present
    start = 0
    mstart = re.search(r"\bLine\s+Part\s+Number\b", text, flags=re.IGNORECASE)
    if mstart:
        start = mstart.start()
    region = text[start:]

    # Capture a block per line item
    # Pattern is robust to newlines and optional "Needed:"
    item_pat = re.compile(
        r"^\s*(?P<line>\d{1,4})\s+(?P<part>\d{3,})\s*(?:Needed:\s*)?\s*"
        r"(?P<ddate>\d{2}-[A-Z]{3}-\d{4})\s+(?P<dtime>\d{2}:\d{2}:\d{2})\s*"
        r"(?P<qty>\d+(?:[.,]\d+)?)\s+(?P<uom>[A-Z]{2,6})\b",
        re.IGNORECASE | re.MULTILINE,
    )

    for m in item_pat.finditer(region):
        line_no = m.group("line").strip()
        part = m.group("part").strip()
        qty = m.group("qty").replace(",", ".").strip()
        uom = m.group("uom").upper().strip()

        # description: capture from end of match until next "Total:" or "Ship To:" or next line item
        tail = region[m.end():]
        stop_m = re.search(r"\n\s*Total:\b|\n\s*Ship To:\b|\n\s*\d{1,4}\s+\d{3,}\b", tail, flags=re.IGNORECASE)
        desc_block = tail[: stop_m.start()] if stop_m else tail[:400]

        # Keep meaningful lines only
        desc_lines = []
        for ln in desc_block.splitlines():
            s = ln.strip()
            if not s:
                continue
            if re.search(r"^(Ship To:|Use the ship-to address|Total:|Tax|Amount|Needed:)$", s, re.IGNORECASE):
                continue
            # Avoid repeating delivery/qty fragments
            if re.match(r"^\d{2}-[A-Z]{3}-\d{4}\b", s, re.IGNORECASE):
                continue
            if re.match(r"^\d+(?:[.,]\d+)?\s+[A-Z]{2,6}\b", s, re.IGNORECASE):
                continue
            desc_lines.append(s)

        desc = _clean_ws(" ".join(desc_lines)) if desc_lines else part

        rows.append({
            "item_no": line_no,
            "te_part_number": part,
            "description": desc,
            "quantity": qty,
            "uom": uom,
        })

    if rows:
        return rows

    return [{
        "item_no": "1",
        "te_part_number": "Not found",
        "description": "Not found",
        "quantity": "1",
        "uom": "EA",
    }]


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

    header["po_number"] = _nf(_find_first(
        [r"\bOrder\s+(\d{6,}-\d+)\b", r"\bBlanket Release\s+(\d{6,}-\d+)\b"],
        text,
        flags=re.IGNORECASE,
    ))

    header["po_date"] = _nf(_find_first(
        [r"\bOrder Date\s+(\d{2}-[A-Z]{3}-\d{4})\b"],
        text,
        flags=re.IGNORECASE,
    ))

    buyer = _find_first(
        [r"\bCreated By\s+([^\n\r]+)"],
        text,
        flags=re.IGNORECASE,
    )
    header["buyer"] = _nf(_clean_ws(buyer) if buyer else None)

    delivery = _find_first(
        [r"\bShip To:\s*(.*?United Kingdom)"],
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    header["delivery_address"] = _nf(_clean_ws(delivery) if delivery else None)

    lines = _parse_lines(text)

    for k in REQUIRED_HEADER_KEYS:
        header[k] = _nf(header.get(k))

    return {"header": header, "lines": lines}
