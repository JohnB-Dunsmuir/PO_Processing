# Parsers/parser_kempston_controls.py

import re
from typing import Dict, List, Any, Optional


def detect_kempston_controls(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return (
        "KEMPSTON" in t
        or "KEMPSTON CONTROLS" in t
        or "PURCHASE ORDER NO." in t
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


def _has_letter(s: str) -> bool:
    return bool(re.search(r"[A-Z]", (s or "").upper()))


def _parse_lines(text: str) -> List[Dict[str, Any]]:
    """
    Kempston Controls:
      - "Our Item Number"     -> TE Part Number (wins if present)
      - "Your Item Number"    -> Customer Part Number
      - "Manufacturer's Item" -> Manufacturer Part Number

    Extract all three separately. On some POs values may match, but we must not collapse them.
    """
    lines: List[Dict[str, Any]] = []

    region = text
    mstart = re.search(r"\bOur\s+Item\s+Number\b", text, flags=re.IGNORECASE)
    if mstart:
        region = text[mstart.start():]

    # Strong row: item + our + your + mfr + description + qty + uom
    row = re.compile(
        r"^\s*(?P<item>\d{1,4})\s+"
        r"(?P<our>[A-Z0-9][A-Z0-9\-/\.]*)\s+"
        r"(?P<your>[A-Z0-9][A-Z0-9\-/\.]*)\s+"
        r"(?P<mfr>[A-Z0-9][A-Z0-9\-/\.]*)\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<qty>\d+(?:[\.,]\d+)?)"
        r"(?:\s+(?P<uom>[A-Z]{1,6}))?\b.*$",
        re.IGNORECASE | re.MULTILINE,
    )

    for m in row.finditer(region):
        item = m.group("item").strip()
        our = (m.group("our") or "").strip()
        your = (m.group("your") or "").strip()
        mfr = (m.group("mfr") or "").strip()
        desc = _clean_ws(m.group("desc") or "") or "Not found"
        qty = (m.group("qty") or "").replace(",", ".").strip() or "Not found"
        uom = (m.group("uom") or "").strip() or "Not found"

        te_pn = our if our else "Not found"

        lines.append({
            "item_no": item,
            "customer_product_no": your if your else "Not found",
            "te_part_number": te_pn,
            "manufacturer_part_no": mfr if mfr else "Not found",
            "description": desc,
            "quantity": qty,
            "uom": uom,
        })

    if lines:
        return lines

    # Fallback: previous loose extraction (keeps backward compatibility)
    pat_fallback = re.compile(
        r"^\s*(?P<item>\d{1,4})\s+"
        r"(?P<part>[A-Z0-9][A-Z0-9\-/\.]{{3,}})\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<qty>\d+(?:[\.,]\d+)?)"
        r"(?:\s+(?P<uom>[A-Z]{{1,6}}))?\b.*$",
        re.IGNORECASE | re.MULTILINE,
    )

    for m in pat_fallback.finditer(region):
        qty = (m.group("qty") or "").replace(",", ".").strip() or "Not found"
        uom = (m.group("uom") or "").strip() or "Not found"
        part = (m.group("part") or "").strip()
        if part.isdigit() or not _has_letter(part):
            continue

        lines.append({
            "item_no": m.group("item").strip(),
            "customer_product_no": "Not found",
            "te_part_number": part,
            "manufacturer_part_no": "Not found",
            "description": _clean_ws(m.group("desc")) or "Not found",
            "quantity": qty,
            "uom": uom,
        })

    return lines


def parse_kempston_controls(text: str) -> Dict[str, Any]:
    header = {
        "po_number": "Not found",
        "po_date": "Not found",
        "customer_name": "Kempston Controls",
        "buyer": "Not found",
        "delivery_address": "Not found",
    }

    if not text:
        return {"header": header, "lines": []}

    header["po_number"] = _nf(_find_first(
        [
            r"PURCHASE\s+ORDER\s+NO\.?\s*([A-Z0-9\-\/]+)",
            r"PURCHASE\s+ORDER\s+NUMBER\s*[:\-]?\s*([A-Z0-9\-\/]+)",
        ],
        text,
        flags=re.IGNORECASE,
    ))

    header["po_date"] = _nf(_find_first(
        [
            r"\bDATE\s+(\d{2}/\d{2}/\d{4})\b",
            r"\bORDER\s*DATE\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})\b",
            r"\bPO\s*DATE\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})\b",
        ],
        text,
        flags=re.IGNORECASE,
    ))

    # BUYER / CONTACT PERSON:
    # "Please contact Lorraine Swingler on 01933 414518 with any queries"
    contact_name = _find_first(
        [
            r"PLEASE\s+CONTACT\s+([A-Z][A-Z\s'\-]+?)\s+ON\s+\d",
            r"PLEASE\s+CONTACT\s+([A-Z][A-Z\s'\-]+?)\s+WITH\s+ANY\s+QUERIES",
        ],
        text,
        flags=re.IGNORECASE,
    )
    if contact_name:
        header["buyer"] = _clean_ws(contact_name.title())
    else:
        # fallback that avoids 'Not found'
        header["buyer"] = "Kempston Controls"

    header["delivery_address"] = _nf(_extract_block_after(
        r"\bDELIVER\s+TO\s*:\s*",
        text,
        stop_pats=[
            r"\bPLEASE\s+SUPPLY\b",
            r"\bSEND\s+ALL\s+ITEMS\b",
            r"\bITEM\b",
            r"\bDESCRIPTION\b",
            r"\bTOTAL\b",
            r"\bPAGE\s+\d+\b",
            r"\bSUPPLIER\s*:\b",
        ],
    ))

    lines = _parse_lines(text)

    for k in REQUIRED_HEADER_KEYS:
        header[k] = _nf(header.get(k))

    return {"header": header, "lines": lines}
