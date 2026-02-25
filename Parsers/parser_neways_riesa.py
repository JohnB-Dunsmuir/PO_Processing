import re
from typing import Dict, List, Any, Optional


# ---------------------------------------------------------------------------
# DETECTION (STRICT) — UNCHANGED
# ---------------------------------------------------------------------------

def detect_neways_riesa(text: str) -> bool:
    if not text:
        return False

    t = text.upper()

    if "NEWAYS" not in t or "RIESA" not in t:
        return False

    return ("NEWAYS ELECTRONICS RIESA" in t) or ("BAYERN-UND-SACHSEN" in t)


# ---------------------------------------------------------------------------
# HELPERS — UNCHANGED
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


def _clean_ws(s: str) -> str:
    return " ".join((s or "").split()).strip()


def _find_first(patterns, text, flags=0) -> Optional[str]:
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            return m.group(m.lastindex) if m.lastindex else m.group(0)
    return None


def _norm_qty(q: str) -> str:
    q = (q or "").strip()
    if re.match(r"^\d{1,3}(\.\d{3})+$", q):
        return q.replace(".", "")
    return q.replace(",", ".")


# ---------------------------------------------------------------------------
# LINES — ONLY DELIVERY DATE ADDED
# ---------------------------------------------------------------------------

def _parse_lines(text: str) -> List[Dict[str, Any]]:
    lines: List[Dict[str, Any]] = []

    mstart = re.search(r"\bPos\s+EDV-Nummer\b", text, flags=re.IGNORECASE)
    region = text[mstart.start():] if mstart else text

    region = re.split(r"\bSeite\s+\d+\s+von\s+\d+\b", region, flags=re.IGNORECASE)[0]
    region = re.split(r"\bAGB\b|\bZahlungsbedingungen\b|\bGesamt\b", region, flags=re.IGNORECASE)[0]

    row_pat = re.compile(
        r"^\s*(?P<pos>\d{1,4})\s+"
        r"(?P<edv>\S+)\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<qty>\d{1,3}(?:\.\d{3})*|\d+(?:[.,]\d+)?)\s+"
        r"(?P<uom>[A-Z]{1,5})\b.*$",
        re.IGNORECASE | re.MULTILINE,
    )

    date_pat = re.compile(r"(\d{2}\.\d{2}\.\d{4})")

    matches = list(row_pat.finditer(region))
    if not matches:
        return []

    for i, mm in enumerate(matches):
        pos = mm.group("pos").strip()
        edv = mm.group("edv").strip()
        qty = _norm_qty(mm.group("qty"))
        uom = mm.group("uom").upper().strip()
        desc_inline = _clean_ws(mm.group("desc"))

        # ✅ SAFE DELIVERY DATE FIX
        prior_text = region[:mm.start()]
        dates = date_pat.findall(prior_text)
        delivery_date = dates[-1] if dates else None

        block_start = mm.end()
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(region)
        block = region[block_start:block_end]

        cust_part = _find_first(
            [r"IHRE\s+TEILENR\.\s*:\s*([A-Z0-9\-/\.]+)"],
            block,
            flags=re.IGNORECASE,
        )
        ern_part = _find_first(
            [r"\bD\s*:\s*ERN\s+([A-Z0-9\-/\.]+)\b"],
            block,
            flags=re.IGNORECASE,
        )

        lines.append(
            {
                "item_no": pos,
                "customer_product_no": edv,
                "te_part_number": _nf(cust_part),
                "manufacturer_part_no": _nf(f"D:ERN {ern_part}" if ern_part else None),
                "description": desc_inline if desc_inline else "Not found",
                "quantity": qty,
                "uom": uom if uom else "Not found",
                "delivery_date": _nf(delivery_date),
            }
        )

    return lines


# ---------------------------------------------------------------------------
# PARSE — UNCHANGED
# ---------------------------------------------------------------------------

def parse_neways_riesa(text: str) -> Dict[str, Any]:
    header = {
        "po_number": "Not found",
        "po_date": "Not found",
        "customer_name": "Neways Electronics Riesa GmbH",
        "buyer": "Not found",
        "delivery_address": "Not found",
    }

    if not text:
        return {"header": header, "lines": []}

    header["po_number"] = _nf(_find_first(
        [r"\bBestellnummer\s*:\s*([A-Z0-9]+)\b"],
        text,
        flags=re.IGNORECASE,
    ))

    header["po_date"] = _nf(_find_first(
        [
            r"\bBestelldatum\s*[: ]\s*(\d{2}\.\d{2}\.\d{4})\b",
            r"\bDruckdatum\s*[: ]\s*(\d{2}\.\d{2}\.\d{4})\b",
        ],
        text,
        flags=re.IGNORECASE,
    ))

    buyer = _find_first(
        [r"\bIhr\s+Ansprechpartner\s*:\s*([^\n\r]+)"],
        text,
        flags=re.IGNORECASE,
    )
    header["buyer"] = _nf(_clean_ws(buyer) if buyer else None)

    delivery_block = _find_first(
        [r"(TE\s+Connectivity\s+Solutions\s+GmbH.*?CH-\s*\d{4}\s+\w+)"],
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    header["delivery_address"] = _clean_ws(delivery_block) if delivery_block else "Not found"

    lines = _parse_lines(text)

    for k in REQUIRED_HEADER_KEYS:
        header[k] = _nf(header.get(k))

    return {"header": header, "lines": lines}