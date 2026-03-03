from typing import Dict, Any
import re
from Parsers.engines.german_table_type1 import parse_lines as _parse_lines_engine


# ---------------------------------------------------------------------------
# DETECT
# ---------------------------------------------------------------------------

def detect_schweiger(text: str) -> bool:
    if not text:
        return False
    return "SCHWEIGER" in text.upper()


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _nf(value):
    if value is None:
        return "Not found"
    s = str(value).strip()
    return s if s else "Not found"


def _find_first(pattern: str, text: str, flags=0):
    m = re.search(pattern, text, flags)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# PARSE
# ---------------------------------------------------------------------------

def parse_schweiger(text: str) -> Dict[str, Any]:

    header = {
        "po_number": "Not found",
        "po_date": "Not found",
        "customer_name": "Schweiger",
        "buyer": "Not found",
        "delivery_address": "Not found",
    }

    if not text:
        return {"header": header, "lines": []}

        # PO number
    header["po_number"] = _nf(
        _find_first(
            r"Bestell-Nr\.:\s*(\d+)",
            text,
            flags=re.IGNORECASE,
        )
    )

    # PO date
    header["po_date"] = _nf(
        _find_first(
            r"Beleg-Datum:\s*(\d{2}\.\d{2}\.\d{4})",
            text,
            flags=re.IGNORECASE,
        )
    )

    # Buyer
    header["buyer"] = _nf(
        _find_first(
            r"Sachbearbeiter:\s*(.+)",
            text,
            flags=re.IGNORECASE,
        )
    )
    # Extract PO date (German format dd.mm.yyyy)
    header["po_date"] = _nf(
        _find_first(
            r"\b(\d{2}\.\d{2}\.\d{4})\b",
            text,
        )
    )

    # Line extraction via shared engine
    lines = _parse_lines_engine(text)

    return {
        "header": header,
        "lines": lines,
    }