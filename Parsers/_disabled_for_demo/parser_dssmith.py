# Parsers/parser_dssmith.py

import re
from typing import Dict, List, Any, Optional


def detect_dssmith(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return (
        "DS SMITH" in t
        or "DS SMITH PACKAGING" in t
        or ("PURCHASE ORDER" in t and "DS" in t and "SMITH" in t)
    )


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


def _clean_ws(s: str) -> str:
    return " ".join((s or "").split()).strip()


def _find_first(patterns, text, flags=0) -> Optional[str]:
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            if m.lastindex:
                return m.group(m.lastindex)
            return m.group(0)
    return None


def _norm_qty(q: str) -> str:
    q = (q or "").strip()
    # 1,000 -> 1000 ; 1.000 -> 1000 ; 10,50 -> 10.50 (best effort)
    if re.match(r"^\d{1,3}(?:,\d{3})+(?:\.\d+)?$", q):
        return q.replace(",", "")
    if re.match(r"^\d{1,3}(?:\.\d{3})+(?:,\d+)?$", q):
        return q.replace(".", "").replace(",", ".")
    return q.replace(",", ".")


def _parse_lines(text: str) -> List[Dict[str, Any]]:
    """
    DS Smith POs often have lines like:
      1  <code> <description> <qty> <uom> <price> <amount>

    We accept:
      item_no + product/code + description + qty + uom + trailing stuff
    """
    lines: List[Dict[str, Any]] = []

    # Try to anchor at a likely header row
    start = re.search(r"\b(Item|Line)\b.*\b(Quantity|Qty)\b", text, flags=re.IGNORECASE)
    region = text[start.start():] if start else text

    # Stop at totals-ish sections
    region = re.split(r"\bTOTAL\b|\bSUBTOTAL\b|\bGRAND\s+TOTAL\b", region, flags=re.IGNORECASE)[0] or region

    row_pat = re.compile(
        r"^\s*(?P<item>\d{1,4})\s+"
        r"(?P<code>[A-Z0-9][A-Z0-9\-/\.]{2,})\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<qty>\d+(?:[.,]\d+)?|\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?)\s+"
        r"(?P<uom>[A-Z]{1,6})\b.*$",
        re.IGNORECASE | re.MULTILINE,
    )

    for m in row_pat.finditer(region):
        code = m.group("code").strip()
        qty = _norm_qty(m.group("qty"))
        uom = m.group("uom").strip().upper()
        desc = _clean_ws(m.group("desc"))

        # Filter obvious junk
        if uom in {"DAY", "DAYS"}:
            continue

        lines.append(
            {
                "item_no": m.group("item").strip(),
                "customer_product_no": code,
                "te_part_number": "Not found",
                "description": desc if desc else "Not found",
                "quantity": qty,
                "uom": uom if uom else "Not found",
            }
        )

    # Fallback: simpler pattern if code column missing
    if not lines:
        row_pat2 = re.compile(
            r"^\s*(?P<item>\d{1,4})\s+"
            r"(?P<desc>.+?)\s+"
            r"(?P<qty>\d+(?:[.,]\d+)?)\s+"
            r"(?P<uom>[A-Z]{1,6})\b.*$",
            re.IGNORECASE | re.MULTILINE,
        )
        for m in row_pat2.finditer(region):
            qty = _norm_qty(m.group("qty"))
            uom = m.group("uom").strip().upper()
            desc = _clean_ws(m.group("desc"))
            if uom in {"DAY", "DAYS"}:
                continue
            lines.append(
                {
                    "item_no": m.group("item").strip(),
                    "customer_product_no": "Not found",
                    "te_part_number": "Not found",
                    "description": desc if desc else "Not found",
                    "quantity": qty,
                    "uom": uom if uom else "Not found",
                }
            )

    return lines


def parse_dssmith(text: str) -> Dict[str, Any]:
    header = {
        "po_number": "Not found",
        "po_date": "Not found",
        "customer_name": "DS Smith",
        "buyer": "Not found",
        "delivery_address": "Not found",
    }

    if not text:
        return {"header": header, "lines": []}

    # PO number
    header["po_number"] = _nf(_find_first(
        [
            r"\bPURCHASE\s+ORDER\s*(?:NO\.?|NUMBER)\s*[:\-]?\s*([A-Z0-9\-\/]+)\b",
            r"\bPO\s*(?:NO\.?|NUMBER)\s*[:\-]?\s*([A-Z0-9\-\/]+)\b",
            r"\bORDER\s+NO\.?\s*[:\-]?\s*([A-Z0-9\-\/]+)\b",
        ],
        text,
        flags=re.IGNORECASE,
    ))

    # PO date (dd/mm/yyyy or dd.mm.yyyy)
    header["po_date"] = _nf(_find_first(
        [
            r"\b(?:ORDER\s*DATE|DATE)\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})\b",
            r"\b(?:ORDER\s*DATE|DATE)\s*[:\-]?\s*(\d{2}\.\d{2}\.\d{4})\b",
        ],
        text,
        flags=re.IGNORECASE,
    ))

    # Buyer / contact
    buyer = _find_first(
        [
            r"\bBUYER\s*[:\-]?\s*([^\n\r]+)",
            r"\bCONTACT\s*[:\-]?\s*([^\n\r]+)",
            r"\bATTN\.?\s*[:\-]?\s*([^\n\r]+)",
        ],
        text,
        flags=re.IGNORECASE,
    )
    header["buyer"] = _nf(_clean_ws(buyer) if buyer else None)

    # Delivery address
    delivery = _find_first(
        [
            r"(DELIVER\s+TO\s*[:\-]?\s*.*?)(?:\n\s*\n|INVOICE\s+TO|BILL\s+TO|TOTAL)",
            r"(DELIVERY\s+ADDRESS\s*[:\-]?\s*.*?)(?:\n\s*\n|INVOICE\s+ADDRESS|TOTAL)",
        ],
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    header["delivery_address"] = _clean_ws(delivery) if delivery else "Not found"

    lines = _parse_lines(text)

    for k in REQUIRED_HEADER_KEYS:
        header[k] = _nf(header.get(k))

    return {"header": header, "lines": lines}
