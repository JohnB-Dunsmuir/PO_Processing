# Parsers/parser_uk_power_networks.py

import re
from typing import Dict, List, Any, Optional


def detect_uk_power_networks(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return (
        "UK POWER NETWORKS" in t
        or "UK POWER NETWORKS (OPERATIONS) LTD" in t
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


def _extract_block_after(label_pat: str, text: str, stop_pats) -> Optional[str]:
    m = re.search(label_pat, text, re.IGNORECASE)
    if not m:
        return None
    tail = text[m.end():]

    stop_positions = []
    for sp in stop_pats:
        ms = re.search(sp, tail, re.IGNORECASE)
        if ms:
            stop_positions.append(ms.start())
    end = min(stop_positions) if stop_positions else len(tail)

    block = _clean_ws(tail[:end])
    return block if block else None


def _norm_qty(q: str) -> str:
    q = (q or "").strip()
    if re.match(r"^\d{1,3}(?:,\d{3})+(?:\.\d+)?$", q):
        return q.replace(",", "")
    return q.replace(",", ".")


def _material_looks_valid(material: str) -> bool:
    if not material:
        return False
    m = material.strip()
    if not re.search(r"\d", m):
        return False
    if not re.match(r"^[A-Z0-9][A-Z0-9\-/\.]{2,}$", m.upper()):
        return False
    return True


def _parse_lines(text: str) -> List[Dict[str, Any]]:
    lines: List[Dict[str, Any]] = []

    row_pat = re.compile(
        r"^\s*(?P<item>\d{1,4})\s+"
        r"(?P<material>\S+)\s+"
        r"(?P<desc>.*?)\s*"
        r"(?P<qty>\d+(?:[.,]\d+)?)\s+"
        r"(?P<uom>[A-Z]{1,10})\b.*$",
        re.IGNORECASE | re.MULTILINE,
    )

    bad_uom = {"DAY", "DAYS", "THIS", "ORDER", "PAGE", "PO", "INVOICE"}

    for m in row_pat.finditer(text):
        item = m.group("item").strip()
        material = m.group("material").strip()
        uom = m.group("uom").strip().upper()

        # Filter junk rows
        if uom in bad_uom:
            continue
        if material.upper() in {"PAYMENT", "TERMS", "DUE"}:
            continue
        if not _material_looks_valid(material):
            continue

        qty = _norm_qty(m.group("qty"))
        desc_inline = _clean_ws(m.group("desc"))
        description = desc_inline if desc_inline else "Not found"

        # Extra filter: if description is missing and material is only digits, it's almost always garbage
        if description == "Not found" and material.isdigit():
            continue

        # TE Part Number on UKPN is "Supplier Ref" (label-based)
        tail = text[m.end(): m.end() + 250]
        m_te = re.search(r"\bSupplier\s*Ref\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/\.]{2,})", tail, flags=re.IGNORECASE)
        m_te2 = re.search(r"\bSupplier\s*Ref\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/\.]{2,})", description, flags=re.IGNORECASE)
        te_pn = (m_te.group(1).strip() if m_te else (m_te2.group(1).strip() if m_te2 else "Not found"))


        lines.append(
            {
                "item_no": item,
                "customer_product_no": material,
                "te_part_number": te_pn,
                "manufacturer_part_no": "Not found",
                "description": description,
                "quantity": qty,
                "uom": m.group("uom").strip(),
            }
        )

    return lines


def parse_uk_power_networks(text: str) -> Dict[str, Any]:
    header = {
        "po_number": "Not found",
        "po_date": "Not found",
        "customer_name": "UK Power Networks (Operations) Ltd",
        "buyer": "Not found",
        "delivery_address": "Not found",
    }

    if not text:
        return {"header": header, "lines": []}

    po = _find_first(
        [
            r"\bORDER\s+NUMBER\s+(\d{8,})\b",
            r"\bPURCHASE\s+ORDER\s+NUMBER\s*[:\-]?\s*(\d{8,})\b",
        ],
        text,
        flags=re.IGNORECASE,
    )
    header["po_number"] = _nf(po)

    po_date = _find_first(
        [r"\bDATE\s+(\d{2}/\d{2}/\d{4})\b"],
        text,
        flags=re.IGNORECASE,
    )
    header["po_date"] = _nf(po_date)

    buyer = _find_first(
        [
            r"\bCONTACT\s*/\s*PHONE\s+([A-Z][A-Z\s'\-]+?)\s*/\s*\+?\d",
            r"\bCONTACT\s*/\s*PHONE\s+([A-Z][A-Z\s'\-]+)\b",
        ],
        text,
        flags=re.IGNORECASE,
    )
    buyer_norm = _clean_ws(buyer.title() if buyer else "")
    header["buyer"] = buyer_norm if buyer_norm else "UK Power Networks"

    delivery = _extract_block_after(
        r"\bDELIVERY\s+ADDRESS\b",
        text,
        stop_pats=[
            r"\bFOR\s+INVOICE\s+ENQUIRIES\b",
            r"\bPAGE\s+\d+\s+OF\s+\d+\b",
            r"\bTOTAL\b",
            r"\bITEM\b",
        ],
    )
    header["delivery_address"] = _nf(delivery)

    lines = _parse_lines(text)

    for k in REQUIRED_HEADER_KEYS:
        header[k] = _nf(header.get(k))

    return {"header": header, "lines": lines}
