# Parsers/parser_abb_sa.py
# ABB SA / ABB Greece parser (loader-compatible)
#
# Required public functions (must exist with exact names):
#   - detect_abb_sa(text)
#   - parse_abb_sa(text)
#
# Notes:
# - detect_abb_sa returns a boolean (True/False). It is intentionally strict to avoid false positives.
# - parse_abb_sa returns a dict with:
#       header: {po_number, po_date, buyer, delivery_address, ...}
#       lines:  [{quantity, uom, customer_product_no, description, delivery_date, te_part_number, manufacturer_part_no, customer_material_no}, ...]
#
# This is designed to be resilient to minor layout differences across ABB Greece PDFs.

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------
# Helpers
# -----------------------------
def _norm(s: str) -> str:
    """Normalize whitespace for easier regex scanning."""
    if not s:
        return ""
    s = s.replace("\x00", " ")
    s = s.replace("\u00a0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _upper(s: str) -> str:
    return _norm(s).upper()


def _find_first(patterns: List[str], text: str, flags: int = re.IGNORECASE) -> str:
    for p in patterns:
        m = re.search(p, text, flags)
        if m:
            # Prefer first capturing group if present
            if m.lastindex and m.lastindex >= 1:
                return (m.group(1) or "").strip()
            return m.group(0).strip()
    return ""


def _find_po_number(text: str) -> str:
    # ABB POs are often 10 digits starting with 45...; keep it general but safe.
    patterns = [
        r"\bPURCHASE\s+ORDER\s*(?:NO\.?|NUMBER)?\s*[:#]?\s*(\d{8,12})\b",
        r"\bPO\s*(?:NO\.?|NUMBER)?\s*[:#]?\s*(\d{8,12})\b",
        r"\bORDER\s*(?:NO\.?|NUMBER)?\s*[:#]?\s*(\d{8,12})\b",
        r"\b(\d{10})\b",  # fallback, but used only if nothing else matches
    ]
    # Use specific first; only use the bare 10-digit fallback if it looks like ABB/SAP (45xxxxxxxx)
    v = _find_first(patterns[:-1], text)
    if v:
        return v
    m = re.search(patterns[-1], text)
    if m:
        cand = m.group(1)
        if cand.startswith("45"):
            return cand
    return ""


def _find_po_date(text: str) -> str:
    # Try common ABB formats: DD.MM.YYYY / DD/MM/YYYY / YYYY-MM-DD
    patterns = [
        r"\bDATE\s*[:#]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\b",
        r"\bORDER\s+DATE\s*[:#]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\b",
        r"\b(\d{4}-\d{2}-\d{2})\b",
    ]
    return _find_first(patterns, text)


def _find_buyer(text: str) -> str:
    patterns = [
        r"\bBUYER\s*[:#]?\s*([A-Z][A-Z .,'-]{2,60})\b",
        r"\bPURCHAS(?:ER|ING)\s+CONTACT\s*[:#]?\s*([A-Z][A-Z .,'-]{2,60})\b",
        r"\bCONTACT\s+PERSON\s*[:#]?\s*([A-Z][A-Z .,'-]{2,60})\b",
        r"\bATTN\.?\s*[:#]?\s*([A-Z][A-Z .,'-]{2,60})\b",
    ]
    v = _find_first(patterns, _upper(text))
    return v.title().strip() if v else ""


def _extract_block_after_label(text: str, label_regex: str, max_lines: int = 6) -> str:
    """
    Finds a label (e.g., 'Ship To', 'Delivery Address') and returns the next few non-empty lines.
    """
    t = _norm(text)
    m = re.search(label_regex, t, re.IGNORECASE)
    if not m:
        return ""
    start = m.end()
    tail = t[start:]
    lines = [ln.strip() for ln in tail.splitlines()]
    out: List[str] = []
    for ln in lines:
        if ln.strip() == "":
            if out:
                break
            continue
        # stop if we hit another obvious section header
        if re.match(r"^(INVOICE|BILL\s+TO|SOLD\s+TO|SHIP\s+TO|DELIVER(?:Y)?\s+TO|DELIVERY\s+ADDRESS|TERMS|PAYMENT|ITEMS?|POSITION|LINE\s*NO\.?)\b",
                    ln.strip(), re.IGNORECASE):
            if out:
                break
        out.append(ln.strip())
        if len(out) >= max_lines:
            break
    return "\n".join(out).strip()


def _parse_number(s: str) -> str:
    # Keep as string; normalize comma/space thousands.
    s = s.strip()
    s = s.replace(" ", "")
    # don't destroy decimal commas; just keep original unless it's clearly thousands commas
    return s


# -----------------------------
# Required loader functions
# -----------------------------
def detect_abb_sa(text: str) -> bool:
    """
    Detect ABB SA / ABB Greece documents.

    Strategy:
    - Require ABB indicators AND Greece indicators.
    - This prevents false positives with ABB Oy, ABB Electrification, etc.
    """
    t = _upper(text)

    # ABB indicators (at least one must match)
    abb_markers = [
        "ABB",
        "A B B",
        "ASEA BROWN BOVERI",
    ]

    # Greece indicators (at least one must match)
    greece_markers = [
        "GREECE",
        "HELLAS",
        "ATHENS",
        "THESSALONIKI",
        "MAROUSI",
        "CHALANDRI",
        "METAMORFOSI",
        "GR-",          # often appears in addresses
        "VAT GR",       # VAT No formatting
        "EL",           # EU VAT prefix used by Greece in many docs
        "ΑΘΗΝ",         # Greek for Athens (partial)
        "ΕΛΛΑΔ",        # Greek for Hellas/Greece (partial)
    ]

    # ABB SA specific markers (help avoid ABB Oy)
    abb_sa_markers = [
        "ABB S.A",
        "ABB SA",
        "ABB A.E",      # Greek abbreviation often used
        "ABB A.E.",
    ]

    has_abb = any(m in t for m in abb_markers)
    has_greece = any(m in t for m in greece_markers)
    has_abb_sa = any(m in t for m in abb_sa_markers)

    # Require ABB + Greece, and strongly prefer ABB SA naming.
    # If the document says ABB SA / ABB A.E. we accept immediately.
    if has_abb_sa and has_greece:
        return True

    # Otherwise be stricter: require ABB + Greece + PO language marker.
    if has_abb and has_greece:
        # a bit of extra safety: must look like a PO
        if re.search(r"\bPURCHASE\s+ORDER\b|\bPO\b|\bORDER\s+NO\b", t):
            return True

    return False


def parse_abb_sa(text: str) -> Dict[str, Any]:
    """
    Parse ABB SA / ABB Greece PO text into the engine-friendly structure.
    """
    raw = text or ""
    t = _norm(raw)
    tu = _upper(raw)

    header: Dict[str, Any] = {
        "po_number": _find_po_number(t),
        "po_date": _find_po_date(t),
        "buyer": _find_buyer(t),
        "delivery_address": "",
        # optional extras (engine usually ignores unknowns safely)
        "sold_to": "",
        "ship_to": "",
        "vendor": "",
    }

    # Delivery / Ship-to blocks (try multiple labels)
    ship_to = _extract_block_after_label(
        t, r"\b(?:SHIP\s+TO|DELIVER(?:Y)?\s+TO|DELIVERY\s+ADDRESS|PLACE\s+OF\s+DELIVERY)\b\s*[:#]?"
    )
    header["ship_to"] = ship_to
    header["delivery_address"] = ship_to  # engine uses delivery_address

    sold_to = _extract_block_after_label(t, r"\b(?:SOLD\s+TO|BILL\s+TO|INVOICE\s+TO)\b\s*[:#]?")
    header["sold_to"] = sold_to

    # Vendor / supplier sometimes present
    vendor = _extract_block_after_label(t, r"\b(?:VENDOR|SUPPLIER)\b\s*[:#]?", max_lines=4)
    header["vendor"] = vendor

    # -----------------------------
    # Lines parsing
    # -----------------------------
    lines: List[Dict[str, Any]] = []

    # Common ABB table patterns vary a lot. We attempt multiple heuristics.

    # Heuristic A: Rows with an explicit item/position number + material + qty + uom
    # Example-ish:
    #  10  3-5353652-6  Description ...  1.008 Stück  12.11.2025
    row_regexes: List[re.Pattern] = [
        re.compile(
            r"^\s*(?P<item>\d{1,5})\s+"
            r"(?P<mat>[A-Z0-9][A-Z0-9\-./]{3,})\s+"
            r"(?P<desc>.+?)\s+"
            r"(?P<qty>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s+"
            r"(?P<uom>[A-Z]{1,6}|PCS|PC|EA|ST|STK|STUECK|STÜCK|PIECE|PZ|NR)\b"
            r"(?:.*?\b(?P<date>\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{2}-\d{2})\b)?"
            r"\s*$",
            re.IGNORECASE,
        ),
        # Variant where qty/uom appear earlier and material after
        re.compile(
            r"^\s*(?P<item>\d{1,5})\s+"
            r"(?P<qty>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s+"
            r"(?P<uom>[A-Z]{1,6}|PCS|PC|EA|ST|STK|STUECK|STÜCK|PIECE|PZ|NR)\s+"
            r"(?P<mat>[A-Z0-9][A-Z0-9\-./]{3,})\s+"
            r"(?P<desc>.+?)"
            r"(?:\s+\b(?P<date>\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{2}-\d{2})\b)?"
            r"\s*$",
            re.IGNORECASE,
        ),
    ]

    # Scan line-by-line first
    for ln in t.splitlines():
        s = ln.strip()
        if not s:
            continue
        # Skip obvious headers/footers
        if re.search(r"\b(PURCHASE\s+ORDER|TERMS|CONDITIONS|PAGE|TOTAL|VAT|INCO)\b", s, re.IGNORECASE):
            continue

        matched = None
        for rx in row_regexes:
            m = rx.match(s)
            if m:
                matched = m
                break

        if not matched:
            continue

        mat = (matched.group("mat") or "").strip()
        desc = (matched.group("desc") or "").strip()
        qty = _parse_number(matched.group("qty") or "")
        uom = (matched.group("uom") or "").strip()
        date = (matched.group("date") or "").strip()

        # Normalize UoM quirks
        uom_u = uom.upper()
        if uom_u in {"STUECK", "STÜCK"}:
            uom = "PC"

        row: Dict[str, Any] = {
            "quantity": qty,
            "uom": uom,
            "customer_product_no": mat,        # ABB material often lands here
            "description": desc,
            "delivery_date": date,
            "te_part_number": "",
            "manufacturer_part_no": "",
            "customer_material_no": mat,
        }
        lines.append(row)

    # Heuristic B (fallback): look for "Material" + "Description" blocks with Qty/UoM nearby
    # Only used if A produced nothing.
    if not lines:
        blob = t

        # Find candidate chunks around "Material" occurrences
        for m in re.finditer(r"\bMATERIAL\b\s*[:#]?\s*([A-Z0-9][A-Z0-9\-./]{3,})", _upper(blob)):
            mat = m.group(1).strip()
            window = blob[m.start(): m.start() + 600]  # local context window

            qty = _find_first([r"\b(?:QTY|QUANTITY)\b\s*[:#]?\s*([0-9][0-9.,]*)"], window)
            uom = _find_first([r"\b(?:UOM|UNIT)\b\s*[:#]?\s*([A-Z]{1,6}|PCS|PC|EA|STK|STÜCK)\b"], window)
            date = _find_first([r"\b(?:DELIVERY\s+DATE|DEL\.?\s*DATE|DELIVERY)\b\s*[:#]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{2}-\d{2})\b"], window)
            # Try to get a description line after material
            desc = ""
            desc = _find_first(
                [
                    r"\bDESCRIPTION\b\s*[:#]?\s*(.{5,120})",
                    r"\bBEZEICHNUNG\b\s*[:#]?\s*(.{5,120})",
                ],
                window,
                flags=re.IGNORECASE,
            )

            row = {
                "quantity": qty,
                "uom": uom,
                "customer_product_no": mat,
                "description": desc,
                "delivery_date": date,
                "te_part_number": "",
                "manufacturer_part_no": "",
                "customer_material_no": mat,
            }
            # Only append if we have at least material + something else
            if mat and (qty or desc):
                lines.append(row)

    # Final cleanup: if still empty, return a single empty line to keep engine stable (optional)
    # (If your engine prefers empty list, delete this.)
    # if not lines:
    #     lines = [{
    #         "quantity": "",
    #         "uom": "",
    #         "customer_product_no": "",
    #         "description": "",
    #         "delivery_date": "",
    #         "te_part_number": "",
    #         "manufacturer_part_no": "",
    #         "customer_material_no": "",
    #     }]

    return {"header": header, "lines": lines}


__all__ = ["detect_abb_sa", "parse_abb_sa"]
