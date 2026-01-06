# parser_westnetz.py
# Repaired: 2025-11-24
# Notes: Safe, brand-specific detection; valid parse skeleton to prevent import errors.

import os
import re

def detect_westnetz(text: str) -> bool:
    """
    Detects WESTNETZ purchase orders.
    Narrow, brand-specific matching to avoid over-detection.
    Replace placeholders with real address/domain markers when available.
    """
    t = (text or "").upper()
    return any([
        "WESTNETZ" in t,
        "@WESTNETZ.COM" in t,
        "ADDRESS OR CITY FRAGMENT" in t  # replace with a known unique address/city snippet if available
    ])

def parse_westnetz(text: str, source_file: str = "") -> dict:
    """
    Minimal, resilient parser stub.
    Returns a structure compatible with the main runner:
      {"header": {...}, "lines": [{...}, ...] }
    Extend this to extract real values as you iterate each customer.
    """
    source_name = os.path.basename(source_file) if source_file else ""
    header = {
        "Purchase Order": "",
        "Date on PO": "",
        "Source.Name": source_name,
        "Buyer": "Westnetz",
        "Order Type": "Standard",
        "Delivery Address": ""
    }
    lines = []  # TODO: implement line extraction for this customer
    return {"header": header, "lines": lines}
