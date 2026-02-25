# Parsers/parser_viteko.py
import re
from typing import Dict, List, Any, Optional


def detect_viteko(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return (
        "VITEKO" in t
        and ("LISBAAN" in t or "CAPELLE" in t or "TECHNISCH" in t or "2908 LN" in t)
    )


REQUIRED_HEADER_KEYS = ["po_number", "po_date", "customer_name", "buyer", "delivery_address"]


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
                return m.group(m.lastindex).strip()
            return m.group(0).strip()
    return None


def _norm_qty(q: str) -> str:
    if not q:
        return "Not found"
    x = q.strip().replace(" ", "")
    if re.match(r"^\d{1,3}(,\d{3})+(\.\d+)?$", x):
        x = x.replace(",", "")
    else:
        x = x.replace(",", ".")
    return x


def _extract_any_date(text: str) -> Optional[str]:
    m = re.search(r"\b(\d{2}[./-]\d{2}[./-]\d{4})\b", text)
    if m:
        return m.group(1)
    m = re.search(r"\b(\d{2}-[A-Z]{3}-\d{4})\b", text, flags=re.IGNORECASE)
    if m:
        return m.group(1).upper()
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if m:
        return m.group(1)
    return None


def _is_bad_po_token(tok: str) -> bool:
    if not tok:
        return True
    t = tok.strip().upper()
    # tokens we never want to accept as PO number
    bad = {
        "PAYMENT", "TERMS", "REFERENCE", "REFERENTIE", "INVOICE", "DELIVERY",
        "EMAIL", "TEL", "PHONE", "WEBSITE", "CUSTOMER", "CARE"
    }
    if t in bad:
        return True
    # require at least one digit (prevents grabbing words)
    if not re.search(r"\d", t):
        return True
    # require some minimum length
    if len(t) < 5:
        return True
    return False


def _extract_po_number(text: str) -> Optional[str]:
    """
    Strict PO number extraction:
    - must contain at least one digit
    - reject common garbage tokens like PAYMENT
    """
    patterns = [
        r"\b(?:Order|PO|Purchase\s+Order|Bestel(?:nr|nummer))\s*(?:No\.?|Nr\.?|Number)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]{4,})\b",
        r"\b(?:Reference|Referentie)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]{4,})\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if not _is_bad_po_token(val):
                return val

    # fallback: first long-ish digit sequence (very common for order refs)
    m = re.search(r"\b(\d{6,})\b", text)
    if m:
        val = m.group(1)
        if not _is_bad_po_token(val):
            return val
    return None


def _parse_lines(text: str) -> List[Dict[str, Any]]:
    """
    Viteko pinned rule:
      - Item Code is TE part number AND customer part number.

    Extract as many item codes as possible. If table text is weak, use robust
    regex scanning for part-like tokens followed by qty + uom.
    """
    lines: List[Dict[str, Any]] = []

    sane_uom = {
        "EA", "EACH", "PC", "PCS", "PCE", "SET", "M",
        "ST", "STK", "STUK", "STUKS"
    }

    # A) If an explicit item number exists, keep it
    pat_a = re.compile(
        r"^\s*(?P<item>\d{1,4})\s+"
        r"(?P<part>[A-Z0-9][A-Z0-9\-/\.]{3,})\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<qty>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s+"
        r"(?P<uom>[A-Za-z]{1,8})\b.*$",
        re.IGNORECASE | re.MULTILINE,
    )

    for m in pat_a.finditer(text):
        uom = (m.group("uom") or "").upper().strip().rstrip(".")
        if uom not in sane_uom:
            continue
        part = m.group("part").strip()
        desc = m.group("desc") or ""
        if re.search(r"(TE CONNECTIVITY|VITEKO|CUSTOMER CARE|INTERNET|EMAIL|TEL)", desc, re.IGNORECASE):
            continue
        lines.append({
            "item_no": m.group("item").strip(),
            "customer_product_no": part,   # customer uses TE PN
            "te_part_number": part,
            "manufacturer_part_no": "Not found",
            "description": _clean_ws(desc) if desc else "Not found",
            "quantity": _norm_qty(m.group("qty")),
            "uom": uom,
        })

    if lines:
        return lines

    # B) No explicit item numbers: scan for "Item Code" style rows.
    # Example extracted text often looks like:
    # 1SNA115116R0700  ENDSTOP  16  ST
    pat_b = re.compile(
        r"^\s*(?P<part>[A-Z0-9][A-Z0-9\-/\.]{5,})\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<qty>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s+"
        r"(?P<uom>[A-Za-z]{1,8})\b.*$",
        re.IGNORECASE | re.MULTILINE,
    )

    item_no = 1
    for m in pat_b.finditer(text):
        uom = (m.group("uom") or "").upper().strip().rstrip(".")
        if uom not in sane_uom:
            continue
        part = m.group("part").strip()
        # Guard: skip obvious non-part tokens
        if re.search(r"^(TE|VITEKO|ORDER|DELIVERY|EMAIL|TEL)$", part, re.IGNORECASE):
            continue
        desc = m.group("desc") or ""
        if re.search(r"(TE CONNECTIVITY|VITEKO|CUSTOMER CARE|INTERNET|EMAIL|TEL)", desc, re.IGNORECASE):
            continue

        lines.append({
            "item_no": str(item_no),
            "customer_product_no": part,
            "te_part_number": part,
            "manufacturer_part_no": "Not found",
            "description": _clean_ws(desc) if desc else "Not found",
            "quantity": _norm_qty(m.group("qty")),
            "uom": uom,
        })
        item_no += 1

    if lines:
        return lines

    # C) Final fallback: placeholder line (contract), but never leave all PN types missing
    return [{
        "item_no": "1",
        "customer_product_no": "Not found",
        "te_part_number": "Not found",
        "manufacturer_part_no": "Not found",
        "description": "Not found",
        "quantity": "1",
        "uom": "EA",
    }]

def parse_viteko(text: str) -> Dict[str, Any]:
    header = {
        "po_number": "Not found",
        "po_date": "Not found",
        "customer_name": "Viteko Technisch Handelsbureau B.V.",
        "buyer": "Viteko",
        "delivery_address": "Not found",
    }

    if not text:
        return {"header": header, "lines": []}

    header["po_number"] = _nf(_extract_po_number(text))
    header["po_date"] = _nf(_extract_any_date(text))

    # delivery: use the visible Viteko address block
    delivery = _find_first(
        [r"(Viteko.*?Lisbaan\s+\d+.*?Nederland)"],
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    header["delivery_address"] = _clean_ws(delivery) if delivery else "Not found"

    lines = _parse_lines(text)

    for k in REQUIRED_HEADER_KEYS:
        header[k] = _nf(header.get(k))

    return {"header": header, "lines": lines}
