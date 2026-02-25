import re
from typing import Dict, List, Any, Optional


def detect_grundfos(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return "GRUNDFOS" in t and "PURCHASE ORDER" in t


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


def _norm_num(x: str) -> str:
    if not x:
        return "Not found"
    s = x.strip().replace(" ", "")
    if re.match(r"^\d{1,3}(?:\.\d{3})+(?:,\d+)?$", s):
        s = s.replace(".", "").replace(",", ".")
        return s
    return s.replace(",", ".")


def _parse_lines(text: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    # Primary format: pos qty uom productno deldate unitprice / total
    main = re.compile(
        r"^\s*(?P<pos>\d{1,4})\s+"
        r"(?P<qty>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s+"
        r"(?P<uom>[A-Z]{1,6})\s+"
        r"(?P<prod>\d{4,})\s+"
        r"(?P<del>\d{2}\.\d{2}\.\d{4})\s+"
        r"(?P<unit>[\d.,]+)\s*/\s*(?P<tot>[\d.,]+)\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    for m in main.finditer(text):
        pos = m.group("pos").strip()
        qty = _norm_num(m.group("qty"))
        uom = m.group("uom").upper().strip()
        prod = m.group("prod").strip()

        # Look shortly after for Vend.mat.no and description
        tail = text[m.end(): m.end() + 800]
        vend = _find_first([r"Vend\.mat\.no\.?\s*:\s*([A-Z0-9\-]+)",
                            r"Ihre Materialnummer\s*([A-Z0-9\-]+)"],
                           tail, flags=re.IGNORECASE)

        # Description heuristic: first non-empty meaningful line
        desc = None
        for ln in tail.splitlines():
            s = ln.strip()
            if not s:
                continue
            if re.search(r"^(Vend\.mat\.no|Document:|ECM No\.|Total net value|Bitte)", s, re.IGNORECASE):
                continue
            if re.match(r"^\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?\s+[A-Z]{1,6}\b", s, re.IGNORECASE):
                continue
            desc = s
            break

        rows.append({
            "item_no": pos,
            "te_part_number": vend if vend else prod,
            "description": _clean_ws(desc) if desc else (vend if vend else prod),
            "quantity": qty,
            "uom": uom,
        })

    if rows:
        return rows

    # Fallback: Vend.mat.no blocks
    for m in re.finditer(r"(?:Vend\.mat\.no\.?\s*:\s*|Herstellerteilenummer\s*)([A-Z0-9\-]+)\s+(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s+([A-Z]{1,6})",
                         text, flags=re.IGNORECASE):
        rows.append({
            "item_no": str(len(rows) + 1),
            "te_part_number": m.group(1).strip(),
            "description": m.group(1).strip(),
            "quantity": _norm_num(m.group(2)),
            "uom": m.group(3).upper().strip(),
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


def _extract_delivery_address(text: str) -> Optional[str]:
    """
    Look for Place of delivery / Marking of shipment / Deliver to anchors and extract
    the following address block (up to a stop clause).
    """
    anchors = [
        r"Place of delivery\s*:\s*",
        r"Place of delivery\b",
        r"Place of delivery\s*\n",
        r"Marking of shipment\s*:\s*",
        r"Deliver(?:y)?\s*to\s*:\s*",
        r"Ship To\s*:\s*",
    ]

    stop_tokens = r"(?:\n\s*(?:Phone:|Our ref\.|Vendor No\.|VAT no\.|Terms of payment|Total net value|Please return the order confirmation))"

    for a in anchors:
        pat = re.compile(a + r"(?P<block>.*?)(?:" + stop_tokens + r"|\\n\\s*\\n)", re.IGNORECASE | re.DOTALL)
        m = pat.search(text)
        if m:
            raw = m.group("block")
            # keep up to 6 non-empty lines
            lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
            if not lines:
                continue
            lines = lines[:6]
            return _clean_ws("\n".join(lines))

    # Fallback: find company name plus address sequence from the file
    m2 = re.search(r"(Grundfos Operations A/S.*?)(?:\n\s*TE Connectivity|Phone:|\n\s*Our ref:|\n\s*Date:)", text, flags=re.IGNORECASE | re.DOTALL)
    if m2:
        return _clean_ws(m2.group(1))

    return None


def parse_grundfos(text: str) -> Dict[str, Any]:
    header = {
        "po_number": "Not found",
        "po_date": "Not found",
        "customer_name": "Grundfos Operations A/S",
        "buyer": "Not found",
        "delivery_address": "Not found",
    }

    if not text:
        return {"header": header, "lines": []}

    header["po_number"] = _nf(_find_first([r"PURCHASE\s+ORDER\s+No\.\s*(\d+)", r"No\.\s*(\d{7,})"], text, flags=re.IGNORECASE))
    header["po_date"] = _nf(_find_first([r"Date\s*:\s*(\d{2}\.\d{2}\.\d{4})", r"\b(\d{2}\.\d{2}\.\d{4})\b"], text, flags=re.IGNORECASE))

    buyer = _find_first([r"Our ref\.\s*:\s*([^\n\r]+)", r"Our ref\.\:\s*([^\n\r]+)"], text, flags=re.IGNORECASE)
    header["buyer"] = _nf(_clean_ws(buyer) if buyer else None)

    delivery = _extract_delivery_address(text)
    if delivery:
        header["delivery_address"] = _nf(delivery)
    else:
        # last-resort: pick nearby lines under company header
        possible = _find_first([r"GRUNDFOS OPERATIONS A/S\s*(.*?)\n\s*TE Connectivity", r"Poul Due Jensens Vej.*?\n\s*DK"], text, flags=re.IGNORECASE | re.DOTALL)
        header["delivery_address"] = _nf(_clean_ws(possible) if possible else None)

    lines = _parse_lines(text)

    for k in REQUIRED_HEADER_KEYS:
        header[k] = _nf(header.get(k))

    return {"header": header, "lines": lines}
