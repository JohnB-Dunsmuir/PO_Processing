"""
Parsers/parsers_common.py
Shared helpers for all vendor parsers to normalize outputs to TE's schema.

Standard header keys expected downstream:
- "Purchase Order"
- "Date on PO"
- "Source.Name"
- "Buyer"
- "Delivery Address"

Standard line keys:
- "Item Number"
- "Customer Product number"
- "Description"
- "Quantity"
- "Price/Unit"
- "Line value"
- "Delivery Address"
"""

import re
from datetime import datetime
from typing import Dict, List, Any

# --- Canonical TE-exclusion terms (supplier address we must ignore) ---
TE_SUPPLIER_TERMS = [
    "TE CONNECTIVITY", "MÜHLENSTR", "MUHLENSTR", "SCHAFFHAUSEN", "SCHWEIZ",
    "TE CONNECTIVITY SOLUTIONS", "TE CONNECTIVITY SOLUTIONS GMBH"
]

# --- Common header patterns ---
PO_PATTERNS = [
    r"Bestell[-\s]*Nr\.?",
    r"Bestellnummer",
    r"Bestell[-\s]*No\.?",
    r"Order\s*No\.?",
    r"Order\s*Number",
    r"PO\s*Number",
    r"PO\s*No\.?",
    r"Auftragsnummer",
]

DATE_PATTERNS = [
    r"Beleg[-\s]*Datum",
    r"Bestell[-\s]*Datum",
    r"Order\s*Date",
    r"Date",
]

DELIVERY_HEADERS = [
    r"Lieferadresse",
    r"Lieferanschrift",
    r"Warenempf[aä]nger",
    r"Versand an",
    r"Delivery Address",
    r"Ship\s*to",
    r"Shipping Address",
    r"Consignee",
    r"Indirizzo di consegna",
    r"Consegna a",
    r"Destinatario",
]


def extract_po_number(text: str) -> str:
    for hp in PO_PATTERNS:
        m = re.search(hp + r".{0,30}?\b([A-Z0-9\/\-]+)\b", text or "", re.IGNORECASE)
        if m:
            return m.group(1).strip()
    m2 = re.search(r"\bPO[:\s\-]*([A-Z0-9\/\-]{4,})", text or "", re.IGNORECASE)
    return m2.group(1).strip() if m2 else ""


def extract_po_date(text: str) -> str:
    t = text or ""
    for dh in DATE_PATTERNS:
        m = re.search(dh + r".{0,10}?(?P<d>\d{1,2}[./-]\d{1,2}[./-]\d{2,4})", t, re.IGNORECASE)
        if not m:
            continue
        raw = m.group("d").replace("-", ".").replace("/", ".")
        for fmt in ("%d.%m.%Y", "%d.%m.%y"):
            try:
                return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
            except Exception:
                pass
    return ""


def _looks_like_te(addr: str) -> bool:
    a = (addr or "").upper()
    return any(term in a for term in TE_SUPPLIER_TERMS)


def _clean_block(block: str, max_lines: int = 8) -> str:
    lines = [re.sub(r"\s+", " ", ln).strip(" ,") for ln in (block or "").splitlines()]
    lines = [ln for ln in lines if ln]
    return ", ".join(lines[:max_lines])


def extract_delivery_after_anchor(text: str, anchor: str, stop_on_te: bool = True) -> str:
    """
    Capture lines directly AFTER a known customer name anchor (e.g., 'A. Schweiger GmbH'),
    until a blank line or (optionally) a TE Connectivity block appears.
    """
    if not text or not anchor:
        return ""
    pattern = re.compile(re.escape(anchor) + r"[^\n]*\n(?P<block>(?:.+\n){0,12})", re.IGNORECASE)
    m = pattern.search(text)
    if not m:
        return ""
    block = m.group("block")
    if stop_on_te:
        te = re.search(r"(TE\s+CONNECTIVITY|^\s*$)", block, re.IGNORECASE | re.MULTILINE)
        if te:
            block = block[:te.start()]
    addr = _clean_block(block, max_lines=8)
    if _looks_like_te(addr):
        return ""
    return addr


def extract_delivery_by_header(text: str) -> str:
    """
    Generic header-based delivery extraction (Ship-to / Lieferadresse etc.).
    """
    t = text or ""
    for hp in DELIVERY_HEADERS:
        m = re.search(hp + r".{0,40}?\n(?P<block>(?:.+\S.*\n){1,12})", t, re.IGNORECASE)
        if m:
            block = m.group("block")
            block = block.split("\n\n")[0]
            addr = _clean_block(block, max_lines=8)
            if not _looks_like_te(addr):
                return addr
    return ""


def standardize_output(customer_name: str, header: Dict[str, Any], lines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Map arbitrary header/lines into TE's canonical schema. Fills missing keys with ''.
    """
    std_header = {
        "Purchase Order": header.get("Purchase Order") or header.get("po_number") or header.get("PO") or "",
        "Date on PO": header.get("Date on PO") or header.get("po_date") or "",
        "Source.Name": header.get("Source.Name") or header.get("customer_name") or customer_name or "",
        "Buyer": header.get("Buyer") or header.get("buyer") or "",
        "Delivery Address": header.get("Delivery Address") or header.get("delivery_address") or "",
    }

    std_lines = []
    if not lines:
        lines = [{}]

    for ln in lines:
        std_lines.append({
            "Item Number": ln.get("Item Number") or ln.get("position") or "",
            "Customer Product number": ln.get("Customer Product number") or ln.get("material_number") or "",
            "Description": ln.get("Description") or ln.get("description") or "",
            "Quantity": ln.get("Quantity") or ln.get("quantity") or "",
            "Price/Unit": ln.get("Price/Unit") or ln.get("unit_price") or "",
            "Line value": ln.get("Line value") or ln.get("net_value") or "",
            "Delivery Address": ln.get("Delivery Address") or std_header["Delivery Address"] or "",
        })

    return {"header": std_header, "lines": std_lines}


def ensure_min_header(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    After a parser returns, enforce presence of the five canonical header keys.
    """
    parsed = parsed or {}
    header = parsed.get("header") or {}
    lines = parsed.get("lines") or []

    keys = ["Purchase Order", "Date on PO", "Source.Name", "Buyer", "Delivery Address"]
    for k in keys:
        header.setdefault(k, "")

    # Propagate header Delivery Address to lines if missing
    for ln in (lines or []):
        ln.setdefault("Delivery Address", header.get("Delivery Address", ""))

    return {"header": header, "lines": lines}
