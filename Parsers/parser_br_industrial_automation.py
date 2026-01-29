import re
from typing import Dict, List, Any, Optional


def detect_br_industrial_automation(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return "B&R INDUSTRIAL AUTOMATION" in t or "EGGELSBERG" in t or "B&R STRASSE" in t


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
            # prefer captured group if present
            if m.lastindex:
                return m.group(m.lastindex).strip()
            return m.group(0).strip()
    return None


def _norm_qty(x: str) -> str:
    if not x:
        return "Not found"
    s = x.strip().replace(" ", "")
    if re.match(r"^\d{1,3}(?:\.\d{3})+(?:,\d+)?$", s):
        s = s.replace(".", "").replace(",", ".")
        return s
    return s.replace(",", ".")


def _extract_address_block(text: str) -> Optional[str]:
    """
    Look for common delivery anchors and grab the following 1-6 lines,
    stopping at a clear delimiter (Liefertermin, Liefertermin Tag, Seite, Page, Rechnung, Invoice).
    Return cleaned address or None.
    """
    anchors = [
        r"Bitte liefern Sie an\s*:\s*",
        r"Bitte liefern Sie\s*:\s*",
        r"Please deliver to\s*:\s*",
        r"Deliver(?:y)?\s*To\s*:\s*",
        r"Lieferadresse\s*[:\-]?\s*",
        r"Ship To\s*:\s*",
    ]

    # Build a combined regex to find an anchor and capture the following block (up to 6 lines)
    for a in anchors:
        pat = re.compile(a + r"(?P<block>.*?)(?:\n\s*\n|Liefertermin\b|Liefertermin Tag\b|Liefertermin|Seite\b|Page\b|Rechnung\b|Invoice\b|Unsere UStIdentNummer\b|Bestellnummer\b)", re.IGNORECASE | re.DOTALL)
        m = pat.search(text)
        if m:
            raw = m.group("block")
            # keep up to 6 non-empty lines
            lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
            if not lines:
                continue
            lines = lines[:6]
            return _clean_ws("\n".join(lines))

    # Fallback: scan for a block that contains "B&R Industrial Automation" and some address lines nearby
    m2 = re.search(r"(B&R Industrial Automation GmbH.*?)(?:\n\s*\n|Liefertermin\b|Seite\b|Page\b)", text, flags=re.IGNORECASE | re.DOTALL)
    if m2:
        return _clean_ws(m2.group(1))

    return None


def _parse_lines(text: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    # Attempt to capture lines that look like:
    # 00010 050002708-H01 3-5353652-6(18 TRAY)TE
    #  1.008 Stück 4.753,00/1.000 4.791,02
    pat = re.compile(
        r"^\s*(?P<item>\d{5})\s+(?P<mat>[A-Z0-9\-]+)\s+(?P<tail>.+?)\s*$"
        r"(?:\r?\n|\r)\s*(?P<qty>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s+Stück\b",
        re.IGNORECASE | re.MULTILINE,
    )

    for m in pat.finditer(text):
        item = m.group("item").strip()
        mat = m.group("mat").strip()
        tail = _clean_ws(m.group("tail"))
        qty = _norm_qty(m.group("qty"))

        # Look for TE-like code in tail (e.g., 3-5353652-6)
        te = _find_first([r"\b\d-\d{6,}-\d\b", r"\b[0-9]{1}-[0-9]{3,}-[0-9]\b", r"\b[0-9\-]{6,}\b"], tail, flags=re.IGNORECASE)
        te_part = te if te else mat

        rows.append({
            "item_no": item,
            "te_part_number": te_part,
            "description": tail if tail != "Not found" else te_part,
            "quantity": qty,
            "uom": "ST",
        })

    if rows:
        return rows

    # Fallback: if TE code present anywhere, create single row
    te2 = _find_first([r"\b\d-\d{6,}-\d\b", r"\b[0-9]{3,}-[0-9]{1,}\b"], text, flags=re.IGNORECASE)
    if te2:
        return [{
            "item_no": "1",
            "te_part_number": te2,
            "description": te2,
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


def parse_br_industrial_automation(text: str) -> Dict[str, Any]:
    header = {
        "po_number": "Not found",
        "po_date": "Not found",
        "customer_name": "B&R Industrial Automation GmbH",
        "buyer": "Not found",
        "delivery_address": "Not found",
    }

    if not text:
        return {"header": header, "lines": []}

    # PO number/date
    po_m = re.search(r"Bestellnummer/Datum\s*([0-9]+)\s*/\s*(\d{2}\.\d{2}\.\d{4})", text, flags=re.IGNORECASE)
    if po_m:
        header["po_number"] = _nf(po_m.group(1))
        header["po_date"] = _nf(po_m.group(2))
    else:
        header["po_number"] = _nf(_find_first([r"\b(45\d{8,})\b"], text, flags=re.IGNORECASE))
        header["po_date"] = _nf(_find_first([r"\b(\d{2}\.\d{2}\.\d{4})\b"], text, flags=re.IGNORECASE))

    # Buyer
    header["buyer"] = _nf(_find_first([r"AnsprechpartnerIn/Telefon\s*([^\n\r]+)"], text, flags=re.IGNORECASE))

    # Delivery address — improved extraction
    addr = _extract_address_block(text)
    if addr:
        header["delivery_address"] = _nf(addr)
    else:
        # As a last attempt, capture the vendor address lines near "B&R Industrial Automation" block
        addr2 = _find_first([r"(B&R Industrial Automation GmbH.*?ÖSTERREICH)", r"(B&R Industrial Automation GmbH.*?Eggelsberg)"], text, flags=re.IGNORECASE | re.DOTALL)
        header["delivery_address"] = _nf(addr2)

    lines = _parse_lines(text)

    # ensure required header keys are present
    for k in REQUIRED_HEADER_KEYS:
        header[k] = _nf(header.get(k))

    return {"header": header, "lines": lines}
