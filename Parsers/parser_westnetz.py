# Parsers/parser_westnetz.py

import re
from typing import Dict, List, Any, Optional


def detect_westnetz(text: str) -> bool:
    if not text:
        return False
    t = text.upper()
    return "WESTNETZ" in t and ("FLORIANSTRASSE" in t or "DORTMUND" in t)


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
            return m.group(1).strip()
    return None


def _norm_qty(q: str) -> str:
    q = (q or "").strip()
    if re.match(r"^\d{1,3}(\.\d{3})+$", q):
        return q.replace(".", "")
    return q.replace(",", ".")


def _extract_delivery_address(text: str) -> str:
    blk = _find_first(
        [
            r"\bLiefer(?:adresse|anschrift)\b\s*[:\-]?\s*(.*?)(?:\n\s*\n|Rechnungsadresse|Bestellnummer|Bestellung|Seite\s+\d)",
        ],
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if blk:
        return _clean_ws(blk)

    blk2 = _find_first(
        [
            r"(Westnetz\s+GmbH.*?Florianstraße\s+15-21.*?44139\s+Dortmund)",
        ],
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return _clean_ws(blk2) if blk2 else "Not found"


def _parse_lines(text: str) -> List[Dict[str, Any]]:
    lines: List[Dict[str, Any]] = []

    sane_uom = {"ST", "STK", "EA", "EACH", "PCS", "PC", "M"}

    region = text
    mstart = re.search(r"\b(Pos\.?|Position)\b|\bMenge\b|\bMaterial\b", text, flags=re.IGNORECASE)
    if mstart:
        region = text[mstart.start():]

    row = re.compile(
        r"^\s*(?P<item>\d{1,5})\s+"
        r"(?P<code>\d{6,}|\d{1,2}-\d{4,8}-\d{1,3}|[A-Z0-9][A-Z0-9\-/\.]{4,})\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<qty>\d+(?:[.,]\d+)?|\d{1,3}(?:\.\d{3})+)\s+"
        r"(?P<uom>[A-Za-z]{1,6})\b.*$",
        re.IGNORECASE | re.MULTILINE,
    )

    for m in row.finditer(region):
        uom = (m.group("uom") or "").upper().strip().rstrip(".")
        if uom not in sane_uom:
            continue

        lines.append(
            {
                "item_no": m.group("item").strip(),
                "customer_product_no": m.group("code").strip(),
                "te_part_number": "Not found",
                "manufacturer_part_no": "Not found",
                "description": _clean_ws(m.group("desc")) or "Not found",
                "quantity": _norm_qty(m.group("qty")),
                "uom": uom,
            }
        )

    if not lines:
        m2 = re.search(r"\b(\d+(?:[.,]\d+)?)\s+(STK|ST|EA|EACH|PCS|PC|M)\b", text, flags=re.IGNORECASE)
        if m2:
            lines.append(
                {
                    "item_no": "1",
                    "customer_product_no": "Not found",
                    "te_part_number": "Not found",
                    "manufacturer_part_no": "Not found",
                    "description": "Not found",
                    "quantity": _norm_qty(m2.group(1)),
                    "uom": m2.group(2).upper(),
                }
            )

    return lines


def parse_westnetz(text: str) -> Dict[str, Any]:
    header = {
        "po_number": "Not found",
        "po_date": "Not found",
        "customer_name": "Westnetz GmbH",
        "buyer": "Not found",
        "delivery_address": "Not found",
    }

    if not text:
        return {"header": header, "lines": []}

    header["po_number"] = _nf(_find_first(
        [
            r"\bBestell(?:nummer|nr\.)\b\s*[:\-]?\s*(\d{8,12})\b",
            r"\bBestellung\s+Nr\.\s*(\d{8,12})\b",
            r"\bPO\s*(?:No\.?|Number)\s*[:\-]?\s*(\d{8,12})\b",
        ],
        text,
        flags=re.IGNORECASE,
    ))

    header["po_date"] = _nf(_find_first(
        [
            r"\bDatum\b\s*[:\-]?\s*(\d{2}\.\d{2}\.\d{4})\b",
            r"\bBestelldatum\b\s*[:\-]?\s*(\d{2}\.\d{2}\.\d{4})\b",
            r"\b(\d{2}\.\d{2}\.\d{4})\b",
        ],
        text,
        flags=re.IGNORECASE,
    ))

    buyer = _find_first(
        [
            r"\bEinkaufssachbearbeiter/in\s*:\s*([^\n\r]+)",
            r"\bSachbearbeiter/in\s*:\s*([^\n\r]+)",
            r"\bAnsprechpartner\s*:\s*([^\n\r]+)",
        ],
        text,
        flags=re.IGNORECASE,
    )
    header["buyer"] = _nf(_clean_ws(buyer) if buyer else None)

    header["delivery_address"] = _nf(_extract_delivery_address(text))

    lines = _parse_lines(text)

    for k in REQUIRED_HEADER_KEYS:
        header[k] = _nf(header.get(k))

    return {"header": header, "lines": lines}
