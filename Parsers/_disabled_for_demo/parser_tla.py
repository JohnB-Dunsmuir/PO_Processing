# Parsers/parser_tla.py

import re
from typing import Dict, Any, List, Optional


def detect_tla(text: str) -> bool:
    """
    STRICT detection.
    Prevents false positives on other distributors (e.g. Viteko).
    """
    if not text:
        return False
    t = text.upper()

    strong = (
        "TLA DISTRIBUTION" in t
        or "TLA DISTRIBUTION LTD" in t
        or "TLA DISTRIBUTION LIMITED" in t
    )

    # Add a second strong indicator seen on real TLA docs
    # (address, VAT, or website patterns can vary; keep it simple & strict)
    second = (
        "BRACKMILLS" in t
        or "NN4 7DY" in t
        or "OSYTH CLOSE" in t
        or re.search(r"\bTLA\b.*\bNORTHAMPTON\b", t) is not None
    )

    return bool(strong and second)


def parse_tla(text: str) -> Dict[str, Any]:
    """
    Minimal, safe parser (kept intentionally simple).
    If this ever triggers, it's truly TLA.
    """
    header = {
        "po_number": "Not found",
        "po_date": "Not found",
        "customer_name": "TLA Distribution Ltd",
        "buyer": "Not found",
        "delivery_address": "Not found",
    }

    # Basic extraction (won't hurt anything)
    if text:
        m = re.search(r"\bPO\s*(?:NUMBER|NO\.?)\s*[:\-]?\s*([A-Z0-9\-\/]+)\b", text, re.IGNORECASE)
        if m:
            header["po_number"] = m.group(1).strip()

        d = re.search(r"\bDATE\s*[:\-]?\s*(\d{2}[./]\d{2}[./]\d{4})\b", text, re.IGNORECASE)
        if d:
            header["po_date"] = d.group(1).strip()

        b = re.search(r"\bBUYER\s*[:\-]?\s*([^\n\r]+)", text, re.IGNORECASE)
        if b:
            header["buyer"] = b.group(1).strip()

        # Fallback address (if present)
        a = re.search(r"(?:DELIVER\s+TO|DELIVERY\s+ADDRESS)\s*[:\-]?\s*(.*?)(?:\n\s*\n|TOTAL|INVOICE)", text, re.IGNORECASE | re.DOTALL)
        if a:
            header["delivery_address"] = " ".join(a.group(1).split())

    return {"header": header, "lines": []}
