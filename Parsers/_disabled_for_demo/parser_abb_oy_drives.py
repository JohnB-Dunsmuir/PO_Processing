# Parsers/parser_abb_oy_drives.py
"""
ABB Oy Drives parser (FIXED)

This file was failing to import due to a top-level `return` statement.
All logic is now inside functions so the module loads cleanly.

Contract (V12):
- detect_abb_oy_drives(text) -> bool
- parse_abb_oy_drives(text) -> dict | list[dict] | pandas.DataFrame
"""

import re
from typing import Any, Dict, List


# ----------------------------
# DETECTION
# ----------------------------

def detect_abb_oy_drives(text: str) -> bool:
    if not text:
        return False

    tu = (text or "").upper()

    # Hard-exclude ABB Greece / ABB SA so these can't be misrouted to Oy Drives
    if any(x in tu for x in [
        "ABB S.A", "ABB SA", "ABB A.E", "ABB A.E.",
        "GREECE", "HELLAS", "ATHENS",
        "VAT GR", "VAT: GR", "GR-"
    ]):
        return False

    # Positive signals for ABB Oy / Drives (keep strict to avoid misrouting)
    strong_triggers = [
        "ABB OY",
        "ABB OY DRIVES",
        "ABB DRIVES OY",
        "DRIVES OY",
        "ABB MOTORS AND GENERATORS",  # if your PDFs include this division wording
        "FINLAND",
        "FI-",
        "VAT FI",
        "VAT: FI",
    ]

    # Require at least one strong trigger AND ABB present
    if "ABB" not in tu:
        return False

    return any(trig in tu for trig in strong_triggers)


# ----------------------------
# PARSE (SAFE PLACEHOLDER)
# ----------------------------
# NOTE: This is intentionally conservative so we don't output garbage.
# If you have an existing working parse implementation, paste it below
# INSIDE this function body.

def parse_abb_oy_drives(text: str) -> Dict[str, Any]:
    """
    Safe placeholder parse so the module loads and won't crash the pipeline.

    Replace with your real extraction when ready.
    Must return one of:
      - dict
      - list[dict]
    """
    # Try to extract a PO number if present (very generic, low risk)
    po = ""
    m = re.search(r"\bPURCHASE\s+ORDER\b[\s\S]{0,80}?\b(\d{6,})\b", text, flags=re.I)
    if m:
        po = m.group(1).strip()

    return {
        "header": {
            "customer_name": "ABB Oy Drives",
            "po_number": po,
        },
        "lines": []  # keep empty until real line extraction is added
    }
