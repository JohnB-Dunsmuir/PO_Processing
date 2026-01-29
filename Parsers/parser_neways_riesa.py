# Parsers/parser_neways_riesa.py

import re
from typing import Dict, List, Any, Optional


# ---------------------------------------------------------------------------
# DETECTION (STRICT)
# ---------------------------------------------------------------------------

def detect_neways_riesa(text: str) -> bool:
    """
    STRICT: Only match real Neways Riesa POs.
    Prevents misrouting other German POs (e.g. Westnetz).
    """
    if not text:
        return False

    t = text.upper()

    # Must contain BOTH NEWAYS and RIESA (strong vendor identity)
    if "NEWAYS" not in t or "RIESA" not in t:
        return False

    # And at least one very specific anchor seen on these docs
    return ("NEWAYS ELECTRONICS RIESA" in t) or ("BAYERN-UND-SACHSEN" in t)


# ---------------------------------------------------------------------------
# HELPERS
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
            if m.lastindex:
                return m.group(m.lastindex)
            return m.group(0)
    return None


def _norm_qty(q: str) -> str:
    q = (q or "").strip()
    if re.match(r"^\d{1,3}(\.\d{3})+$", q):
        return q.replace(".", "")
    return q.replace(",", ".")


# ---------------------------------------------------------------------------
# LINES
# ---------------------------------------------------------------------------

def _parse_lines(text: str) -> List[Dict[str, Any]]:
    lines: List[Dict[str, Any]] = []

    mstart = re.search(r"\bPos\s+EDV-Nummer\b", text, flags=re.IGNORECASE)
    region = text[mstart.start():] if mstart else text

    region = re.split(r"\bSeite\s+\d+\s+von\s+\d+\b", region, flags=re.IGNORECASE)[0] or region
    region = re.split(r"\bAGB\b|\bZahlungsbedingungen\b|\bGesamt\b", region, flags=re.IGNORECASE)[0] or region

    row_pat = re.compile(
        r"^\s*(?P<pos>\d{1,4})\s+"
        r"(?P<edv>\S+)\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<qty>\d{1,3}(?:\.\d{3})*|\d+(?:[.,]\d+)?)\s+"
        r"(?P<uom>[A-Z]{1,5})\b.*$",
        re.IGNORECASE | re.MULTILINE,
    )

    matches = list(row_pat.finditer(region))
    if not matches:
        return []

    for i, mm in enumerate(matches):
        pos = mm.group("pos").strip()
        edv = mm.group("edv").strip()
        qty = _norm_qty(mm.group("qty"))
        uom = mm.group("uom").upper().strip()
        desc_inline = _clean_ws(mm.group("desc"))

        block_start = mm.end()
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(region)
        block = region[block_start:block_end]

        cust_part = _find_first(
            [r"IHRE\s+TEILENR\.\s*:\s*([A-Z0-9\-/\.]+)"],
            block,
            flags=re.IGNORECASE,
        )
        tyc_part = _find_first(
            [r"\bD\s*:\s*TYC\s+([A-Z0-9\-/\.]+)\b"],
            block,
            flags=re.IGNORECASE,
        )
        ern_part = _find_first(
            [r"\bD\s*:\s*ERN\s+([A-Z0-9\-/\.]+)\b"],
            block,
            flags=re.IGNORECASE,
        )

        tyc_full = (f"D:TYC {tyc_part}" if tyc_part else None)
        ern_full = (f"D:ERN {ern_part}" if ern_part else None)

        # If TE is present it wins; do not fall back TE to customer/manufacturer
        te_part = tyc_full or "Not found"
        mfr_part = ern_full or "Not found"

        lines.append(
            {
                "item_no": pos,
                "customer_product_no": edv,
                "te_part_number": _nf(te_part),
                "manufacturer_part_no": _nf(mfr_part),
                "description": desc_inline if desc_inline else "Not found",
                "quantity": qty,
                "uom": uom if uom else "Not found",
            }
        )

    return lines


# ---------------------------------------------------------------------------
# PARSE
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
        [
            r"\bIhr\s+Ansprechpartner\s*:\s*([^\n\r]+)",
            r"\bAnsprechpartner\s*:\s*([^\n\r]+)",
        ],
        text,
        flags=re.IGNORECASE,
    )
    header["buyer"] = _nf(_clean_ws(buyer) if buyer else None)

    delivery_block = _find_first(
        [
            r"(TE\s+Connectivity\s+Solutions\s+GmbH.*?CH-\s*\d{4}\s+\w+)",
        ],
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    header["delivery_address"] = _clean_ws(delivery_block) if delivery_block else "Not found"

    lines = _parse_lines(text)

    for k in REQUIRED_HEADER_KEYS:
        header[k] = _nf(header.get(k))

    return {"header": header, "lines": lines}
