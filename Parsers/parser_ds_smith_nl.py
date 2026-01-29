# Parsers/parser_ds_smith_nl.py

import re
from typing import Dict, List, Any, Optional


def detect_ds_smith_nl(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "ds smith packaging netherlands" in t and "purchase order no." in t and "dss" in t


def _nf(v: Optional[str]) -> str:
    if v is None:
        return "Not found"
    s = str(v).strip()
    return s if s else "Not found"


def _clean_ws(s: str) -> str:
    return " ".join((s or "").split()).strip()


def _to_float_eu(num: str) -> float:
    if not num:
        return 0.0
    n = num.strip().replace(" ", "")
    if "." in n and "," in n and n.rfind(",") > n.rfind("."):
        n = n.replace(".", "").replace(",", ".")
    else:
        if re.match(r"^\d{1,3}(,\d{3})+(\.\d+)?$", n):
            n = n.replace(",", "")
        else:
            n = n.replace(",", ".")
    try:
        return float(n)
    except Exception:
        return 0.0


def _extract_po_number(text: str) -> str:
    m = re.search(r"Purchase Order No\.\s*(DSS\d+)", text, flags=re.IGNORECASE)
    return m.group(1).strip() if m else "Not found"


def _extract_po_date(text: str) -> str:
    m = re.search(r"\bDate\s*(\d{2}\.\d{2}\.\d{4})\b", text, flags=re.IGNORECASE)
    return m.group(1).strip() if m else "Not found"



def _extract_buyer(text: str) -> str:
    """
    DS Smith NL POs usually contain a contact block like:
      Name: Claude DEPEUX
      Email: ...
    """
    if not text:
        return "Not found"
    m = re.search(r"(?im)^\s*Name\s*:\s*(?P<name>[^\n\r]+)", text)
    if m:
        return m.group("name").strip()

    # fallback: sometimes "Our ref.: <name>"
    m = re.search(r"(?im)^\s*Our\s+ref\.?\s*:\s*(?P<name>[^\n\r]+)", text)
    return m.group("name").strip() if m else "Not found"


def _extract_delivery_address(text: str) -> str:
    """
    For DS Smith NL PDFs we treat the 'Please Address Invoice to:' block
    as the delivery/invoice address needed for SAP routing.

    We stop at the 'Please Submit Invoice to' line to avoid pulling the entire document.
    """
    if not text:
        return "Not found"

    m = re.search(
        r"(?is)Please\s+Address\s+Invoice\s+to\s*:\s*(?P<blk>.+?)(?:\n\s*Please\s+Submit\s+Invoice\s+to\b|\Z)",
        text,
    )
    if m:
        blk = _clean_ws(m.group("blk"))
        return blk if blk else "Not found"

    # fallback: first 5 non-empty lines
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    blk = " ".join(lines[:5]).strip()
    return blk if blk else "Not found"



def _extract_delivery_date(text: str) -> str:
    # Example: "Delivery Date: 18.09.2025"
    m = re.search(r"(?im)^\s*Delivery\s+Date\s*:\s*(\d{2}\.\d{2}\.\d{4})\b", text)
    return m.group(1).strip() if m else "Not found"


def _extract_lines(text: str):
    """
    Extract the main line-item table.

    Observed layout:
      Pos
      10
      469604
      GB2 ETIQUET AUTOCOLLANTE
      51.000
      PCS
      24,56/1.000
      1.252,56

    TE's identifier typically appears in:
      Your Material:
      W403762940111::04
    """
    if not text:
        return []

    # --- TE / supplier material ---
    te_part = "Not found"
    m = re.search(r"(?is)Your\s+Material\s*:\s*(?P<code>[^\n\r]+)", text)
    if m:
        te_part = m.group("code").strip()
        te_part = re.split(r"::|\s+Revision\b", te_part, maxsplit=1)[0].strip()

    # --- isolate the table section ---
    start = re.search(r"(?im)^\s*Pos\s*$", text)
    if not start:
        return []

    end = re.search(r"(?im)^\s*Your\s+Material\s*:\s*$", text)
    section = text[start.start(): end.start()] if end else text[start.start():]

    raw_lines = [ln.strip() for ln in section.splitlines() if ln.strip()]

    items = []
    i = 0

    def is_pos(v: str) -> bool:
        return bool(re.fullmatch(r"\d{1,4}", v))

    def is_qty(v: str) -> bool:
        return bool(re.fullmatch(r"\d[\d.,]*", v))

    def is_uom(v: str) -> bool:
        return bool(re.fullmatch(r"[A-Z]{1,6}", v))

    def is_price_like(v: str) -> bool:
        return bool(re.search(r"\d", v)) and ("/" in v or "," in v or "." in v)

    while i < len(raw_lines) and not is_pos(raw_lines[i]):
        i += 1

    while i < len(raw_lines):
        if not is_pos(raw_lines[i]):
            i += 1
            continue

        pos = raw_lines[i]; i += 1
        if i >= len(raw_lines):
            break

        cust_code = raw_lines[i]; i += 1

        desc_parts = []
        while i < len(raw_lines) and not is_qty(raw_lines[i]):
            if is_pos(raw_lines[i]) and not desc_parts:
                break
            desc_parts.append(raw_lines[i])
            i += 1

        qty = raw_lines[i] if i < len(raw_lines) and is_qty(raw_lines[i]) else "Not found"
        if qty != "Not found":
            # normalize thousand separators (51.000 -> 51000, 1.900,000 -> 1900000)
            qty = re.sub(r"[^0-9]", "", qty)

            i += 1

        uom = raw_lines[i] if i < len(raw_lines) and is_uom(raw_lines[i]) else "Not found"
        if uom != "Not found":
            i += 1

        price = raw_lines[i] if i < len(raw_lines) and is_price_like(raw_lines[i]) else "Not found"
        if price != "Not found":
            i += 1

        description = _clean_ws(" ".join(desc_parts)) if desc_parts else "Not found"

        items.append(
            {
                "item_no": pos,
                "customer_product_no": cust_code if cust_code else "Not found",
                "te_part_number": te_part if te_part else "Not found",
                "manufacturer_part_no": te_part if te_part else "Not found",
                "description": description,
                "quantity": qty,
                "uom": uom,
                "delivery_date": _extract_delivery_date(text),
            }
        )

        while i < len(raw_lines) and not is_pos(raw_lines[i]):
            i += 1

    for r in items:
        for k, v in list(r.items()):
            r[k] = _nf(v)

    return items

def parse_ds_smith_nl(text: str) -> Dict[str, Any]:
    header = {
        "po_number": _extract_po_number(text),
        "po_date": _extract_po_date(text),
        "customer_name": "DS Smith Packaging Netherlands BV",
        "buyer": _extract_buyer(text),
        "delivery_address": _extract_delivery_address(text),
    }

    for k in list(header.keys()):
        header[k] = _nf(header.get(k))

    return {"header": header, "lines": _extract_lines(text)}
